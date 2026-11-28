"""Thin interactive entry point for the independent legacy-first application."""

import argparse
import warnings
import os
from collections.abc import Callable, Sequence
from dataclasses import replace
from getpass import GetPassWarning, getpass
from pathlib import Path

from .tls_policy import TLSPolicyError, exceptions_allowed
from .config import ConfigError, ControllerConfig, prompt_config
from .contracts import JsonValue
from .http_backend import ConnectionFactory
from .objects import (
    ExportError, ImportError, ImportSummary, export_objects, import_objects, inspect_import,
)


MENU = """CC-Vision Core Config Import Components

1. Export Sites and Devices
2. Import Sites and Devices
3. Modify exported credentials (Not implemented)
4. Export LDAP configuration (Not implemented)
5. Import LDAP configuration (Not implemented)
6. Export Scheduler configuration (Not implemented)
7. Import Scheduler configuration (Not implemented)
8. Exit"""


class CliInputError(ValueError):
    pass


class OperationCancelled(Exception):
    pass


def _hidden_password(prompt: str) -> str:
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", GetPassWarning)
            return getpass(prompt)
    except GetPassWarning:
        raise CliInputError("Hidden password input unavailable; use an interactive terminal.") from None


def _required(reader: Callable[[str], str], prompt: str) -> str:
    value = reader(prompt).strip()
    if not value:
        raise CliInputError("A required input was empty.")
    return value


def _confirm(reader: Callable[[str], str], prompt: str) -> bool:
    return reader(prompt).strip().lower() in ("y", "yes")


def _tree(reader: Callable[[str], str], *, both: bool = False) -> tuple[str, ...]:
    choices = {"1": ("Physical",), "2": ("Organization",)}
    if both:
        choices["3"] = ("Physical", "Organization")
    prompt = "Tree: 1 Physical, 2 Organization" + (", 3 Both" if both else "") + ": "
    choice = reader(prompt).strip()
    if choice not in choices:
        raise CliInputError("Invalid tree selection.")
    return choices[choice]



def _config(
    reader: Callable[[str], str], password_reader: Callable[[str], str],
    output: Callable[[str], None], *, source: bool,
) -> tuple[ControllerConfig, bool]:
    try:
        allow_exceptions = exceptions_allowed(
            os.environ.get(
                "CCV_ALLOW_INSECURE_TLS_EXCEPTION", "true"
            )
        )
    except TLSPolicyError as error:
        raise CliInputError(str(error)) from None

    product = "cyber-controller"

    if source:
        choice = reader(
            "Source product: 1 Vision, 2 Cyber Controller: "
        ).strip()

        if choice not in ("1", "2"):
            raise CliInputError("Invalid source product selection.")

        product = "vision" if choice == "1" else "cyber-controller"

    config = prompt_config(
        product,
        input_fn=reader,
        password_fn=password_reader,
    )

    trusted_ca = os.environ.get("CCV_TRUSTED_CA") or None

    if trusted_ca is not None:
        config = replace(config, trusted_ca=trusted_ca)

    verify = reader(
        "Verify TLS certificates? [Y/n]: "
    ).strip().lower()

    if verify in ("", "y", "yes"):
        return config, False

    if verify not in ("n", "no"):
        raise CliInputError("Invalid TLS verification selection.")

    if not allow_exceptions:
        raise CliInputError(
            "This deployment prohibits insecure TLS exceptions."
        )

    output(
        "WARNING: Controller identity is NOT VERIFIED "
        "with unverified TLS."
    )

    if not _confirm(
        reader,
        "Authorize unverified TLS for this operation/session only? [y/N]: ",
    ):
        raise OperationCancelled

    return replace(config, verify_tls=False), True

def _path(value: str) -> Path:
    try:
        path = Path(value).expanduser().resolve()
        if path.is_dir():
            raise CliInputError("Select a JSON filename, not a directory.")
        return path
    except (ValueError, OSError):
        raise CliInputError("Cannot access the selected file path.") from None


def _export(
    reader: Callable[[str], str], password_reader: Callable[[str], str],
    output: Callable[[str], None], factory: ConnectionFactory | None, allow_live: bool,
) -> None:
    config, tls_authorized = _config(reader, password_reader, output, source=True)
    trees = _tree(reader, both=True)
    paths: dict[str, Path] = {}
    output("WARNING: Exported JSON may contain sensitive Device credentials. Protect these files.")
    for tree in trees:
        default = tree.lower() + ".json"
        path = _path(reader(f"{tree} output filename [{default}]: ").strip() or default)
        if path.exists() and not _confirm(reader, f"Replace existing export {path}? [y/N]: "):
            raise OperationCancelled
        paths[tree] = path
    try:
        results = export_objects(
            config, paths, tls_exception_authorized=tls_authorized,
            connection_factory=factory, allow_live=allow_live,
        )
    except (KeyboardInterrupt, EOFError):
        output("Export interrupted; no complete result is confirmed. Check the selected output files.")
        raise
    for tree, result in results.items():
        output(
            f"{tree}: {result.status}; output={paths[tree]}; "
            f"Sites={result.site_count}, Devices={result.device_count}"
        )
        if result.status == "FAILED":
            output(f"  Incomplete export: {result.error_code} at {result.failed_step}.")
        if result.cleanup_failed:
            output("  Local API session cleanup failed.")


def _summary(
    output: Callable[[str], None], config: ControllerConfig, tree: str,
    path: Path, summary: ImportSummary,
) -> None:
    output(f"Destination controller: {config.origin}")
    output(f"Destination tree: {tree}")
    output(f"Input JSON: {path}")
    output(f"Source root: {summary.source_root_name!r}; ID={summary.source_root_id!r}")
    output(f"Sites={summary.site_count}, Devices={summary.device_count}")
    if summary.destination_root_id is not None:
        output(
            f"Destination root: {summary.destination_root_name!r}; "
            f"ID={summary.destination_root_id!r}"
        )
    output("WARNING: Import creates objects on the selected destination.")
    output("Conflicting objects will not be automatically updated, moved or deleted.")
    output("Automatic rollback is not supported.")


def _import(
    reader: Callable[[str], str], password_reader: Callable[[str], str],
    output: Callable[[str], None], factory: ConnectionFactory | None, allow_live: bool,
) -> None:
    path = _path(_required(reader, "Input JSON filename: "))
    source_root: dict[str, JsonValue] | None = None
    try:
        summary = inspect_import(path)
    except ImportError as error:
        if error.code != "source_root_required":
            raise
        output("This older file requires explicit source-root identification.")
        source_root = {
            "id": _required(reader, "Source root ID: "),
            "name": _required(reader, "Source root name: "),
        }
        summary = inspect_import(path, source_root=source_root)
    config, tls_authorized = _config(reader, password_reader, output, source=False)
    tree = _tree(reader)[0]
    _summary(output, config, tree, path, summary)
    if not _confirm(reader, "Proceed to destination login/discovery? [y/N]: "):
        raise OperationCancelled

    def confirm_destination(actual: ImportSummary) -> bool:
        _summary(output, config, tree, path, actual)
        return _confirm(reader, "Create objects under this destination root? [y/N]: ")

    try:
        result = import_objects(
            config, path, tree, source_root=source_root,
            tls_exception_authorized=tls_authorized,
            connection_factory=factory, allow_live=allow_live,
            confirm_destination=confirm_destination,
        )
    except (KeyboardInterrupt, EOFError):
        output("Import interrupted. Any attempted writes need destination review; no automatic rollback.")
        raise
    if result.error_code == "import_cancelled":
        output("Import cancelled before object writes.")
    else:
        output(f"Import: {result.status}")
    for kind, counts in result.counts.items():
        output(
            f"{kind}s: SUCCESS={counts['SUCCESS']}, SKIPPED={counts['SKIPPED']}, "
            f"FAILED={counts['FAILED']}"
        )
    for item in result.objects:
        if item.status == "FAILED":
            output(f"  {item.object_type} ID={item.source_id!r}: FAILED; {item.reason}")
    if result.error_code and result.error_code != "import_cancelled":
        output(f"  Operation failure: {result.error_code} at {result.failed_step}.")
    if result.cleanup_failed:
        output("  Local API session cleanup failed.")


def main(
    argv: Sequence[str] | None = None, *,
    input_fn: Callable[[str], str] | None = None,
    password_fn: Callable[[str], str] | None = None,
    output_fn: Callable[[str], None] | None = None,
    connection_factory: ConnectionFactory | None = None,
) -> int:
    parser = argparse.ArgumentParser(description="CCV Core - Interactive configuration export/import.")
    parser.add_argument(
        "--allow-live", action="store_true",
        help="Enable live dispatch only after separate authorization; does not grant permission.",
    )
    args = parser.parse_args(argv)
    reader = input if input_fn is None else input_fn
    password_reader = _hidden_password if password_fn is None else password_fn
    output = print if output_fn is None else output_fn
    if not args.allow_live and connection_factory is None:
        output("Live API dispatch disabled. --allow-live requires separate authorization.")
    while True:
        try:
            output(MENU)
            choice = reader("Select option: ").strip()
            if choice == "8":
                output("Goodbye.")
                return 0
            if choice in ("3", "4", "5", "6", "7"):
                output("Not implemented. No network requests or file changes performed.")
            elif choice in ("1", "2"):
                try:
                    operation = _export if choice == "1" else _import
                    operation(reader, password_reader, output, connection_factory, args.allow_live)
                except OperationCancelled:
                    output("Operation cancelled before new writes were requested.")
                except CliInputError as error:
                    output(f"Invalid input: {error}")
                except ConfigError:
                    output("Invalid controller settings or credentials.")
                except (ExportError, ImportError) as error:
                    output(f"Operation failed: {error.code} at {error.step}.")
                except OSError:
                    output("Cannot access the selected input/output file.")
            else:
                output("Invalid menu choice; enter a number from 1 to 8.")
        except (KeyboardInterrupt, EOFError) as error:
            output("\nCancelled; exiting.")
            if "Local API session cleanup failed." in getattr(error, "__notes__", ()):
                output("Local API session cleanup failed.")
            return 0


if __name__ == "__main__":
    raise SystemExit(main())
