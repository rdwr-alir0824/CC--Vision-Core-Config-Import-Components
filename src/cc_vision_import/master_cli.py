"""Small offline master interface over the existing configuration components."""

import argparse
import json
from collections.abc import Sequence
from pathlib import Path

from ._contract_validation import ContractReader
from .contracts import ContractValidationError, ExitStatus
from .controller_workflow import plan_offline_request
from .offline_inputs import OfflineInputs, local_path
from .profiles import DestinationProfile, SourceProfile


_OPERATIONS = (
    "operations", "profiles", "export", "compare", "plan", "import-preview",
    "authenticate", "import",
)
_VISION_LIMITATION = "Vision controller export schemas and Vision-to-CC mappings are not established."
_DOMAIN_LIMITATIONS = {
    "ldap-permissions": "Vision LDAP code exists, but CC LDAP contracts and permission mappings are unresolved.",
    "scheduler": "Legacy Scheduler paths are INI-configured and unresolved; CC task contracts are absent.",
}


def _report(operation: str, status: str, **fields: object) -> dict[str, object]:
    return {
        "operation": operation, "status": status, "offline_only": True,
        "execution_authorized": False, "tls_verification_required": True, **fields,
    }


def _unavailable(operation: str, code: str, message: str) -> tuple[dict[str, object], ExitStatus]:
    return _report(operation, "unavailable", errors=[{"code": code, "message": message}]), ExitStatus.CONTRACT_ERROR


def _profiles(
    inputs: OfflineInputs, manifest: dict[str, object] | None,
    source_path: str | None, destination_path: str | None, source_product: str,
) -> tuple[SourceProfile, DestinationProfile]:
    profiles: list[SourceProfile | DestinationProfile] = []
    for role, path, profile_type, product in (
        ("source", source_path, SourceProfile, source_product),
        ("destination", destination_path, DestinationProfile, "cyber-controller"),
    ):
        declared = None
        if manifest is not None:
            side = inputs.reader.mapping(manifest[role], "$")
            declared = profile_type.from_dict(inputs.read(inputs.reader.required(side, "profile", "$"), None))
        if path is not None:
            profile = profile_type.from_dict(inputs.read(path, None, base=Path.cwd()))
            if declared is not None and profile != declared:
                inputs.reader.fail("profile_mismatch", "$", "CLI and manifest profiles must agree; inputs are never silently retargeted.")
        elif declared is not None:
            profile = declared
        else:
            inputs.reader.fail("missing_profile", "$", "Supply both profile files or a request containing both profiles.")
        if profile.product != product:
            inputs.reader.fail("product_mismatch", "$", "Selected products and connection profiles must agree.")
        profiles.append(profile)
    source, destination = profiles
    assert isinstance(source, SourceProfile) and isinstance(destination, DestinationProfile)
    return source, destination


def _write_export(path_value: str, serialized: str) -> None:
    path = local_path(path_value, Path.cwd())
    reader = ContractReader("master-export")
    created = False
    try:
        with path.open("x", encoding="utf-8") as output:
            created = True
            output.write(serialized)
    except FileExistsError:
        reader.fail("output_exists", "$", "Export output already exists; choose a new file.")
    except (OSError, ValueError, UnicodeError):
        if created:
            try:
                path.unlink()
            except OSError:
                reader.fail("output_cleanup_failed", "$", "Export failed and its partial output could not be removed.")
        reader.fail("output_unwritable", "$", "Cannot write the local export output.")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python master.py",
        description="Offline configuration consolidation. Never authenticates or writes to controllers.",
    )
    parser.add_argument("--operation", choices=_OPERATIONS, required=True)
    parser.add_argument("--module", choices=("controller-objects", "ldap-permissions", "scheduler"), default="controller-objects")
    parser.add_argument("--source-product", choices=("vision", "cyber-controller"), default="cyber-controller")
    parser.add_argument("--destination-product", choices=("cyber-controller",), default="cyber-controller")
    parser.add_argument("--source-profile", help="Local source profile JSON; must agree with a supplied manifest.")
    parser.add_argument("--destination-profile", help="Local destination profile JSON; must agree with a supplied manifest.")
    parser.add_argument("--request", help="Existing offline-controller request JSON; paths inside it are relative to its directory.")
    parser.add_argument("--output", help="New local artifact file for export only; never overwritten.")
    args = parser.parse_args(argv)
    if args.output is not None and args.operation != "export":
        parser.error("--output is supported only for offline export.")
    if args.operation == "export" and args.output is None:
        parser.error("offline export requires --output.")
    if args.operation in ("export", "compare", "plan", "import-preview") and args.request is None:
        parser.error("this operation requires --request.")

    status = ExitStatus.SUCCESS
    try:
        if args.operation == "operations":
            report = _report("operations", "available", operations={
                "profiles": "offline validation for Vision/CC source and CC destination",
                "export": "CC 0.0-test supplied source inventory to local artifact",
                "compare": "CC-to-CC offline comparison and candidate actions",
                "plan": "CC-to-CC offline planning",
                "import-preview": "same offline plan; not a legacy dry-run or write authorization",
                "authenticate": "unavailable: shared authentication exists but is not wired to live execution",
                "import": "unavailable: no live writes, even after offline planning",
                "vision-to-cc": _VISION_LIMITATION,
                **_DOMAIN_LIMITATIONS,
            })
        elif args.operation in ("authenticate", "import"):
            report, status = _unavailable(
                args.operation, "live_execution_disabled",
                "Live execution is not wired. Import requires separate controller-execution authorization and explicit action approval.",
            )
        elif args.module in _DOMAIN_LIMITATIONS and args.operation != "profiles":
            report, status = _unavailable(args.operation, "unresolved_contract", _DOMAIN_LIMITATIONS[args.module])
        else:
            inputs = OfflineInputs(args.request if args.request is not None else Path.cwd())
            manifest = inputs.manifest() if args.request is not None else None
            source, destination = _profiles(
                inputs, manifest, args.source_profile, args.destination_profile, args.source_product,
            )
            if args.operation == "profiles":
                report = _report("profiles", "valid", profiles=[
                    {
                        "role": profile.role, "product": profile.product, "version": profile.version,
                        "credential_reference_configured": profile.secret_ref is not None,
                    }
                    for profile in (source, destination)
                ], authenticated=False, note="Profile syntax only; connectivity and compatibility are not tested.")
            elif source.product == "vision":
                report, status = _unavailable(args.operation, "vision_controller_contract_unavailable", _VISION_LIMITATION)
            elif args.operation == "export":
                assert manifest is not None
                inventory = inputs.side(manifest["source"], "source")
                artifact = inventory.to_artifact()
                _write_export(args.output, artifact.to_json())
                report = _report(
                    "export", "exported", object_count=len(artifact.objects),
                    note="Local source adaptation only; not a controller fetch. Completeness and credential portability remain unverified.",
                )
            else:
                assert args.request is not None
                result = plan_offline_request(args.request)
                report = {
                    **result.report, "operation": args.operation, "offline_only": True,
                    "tls_verification_required": True,
                    "import_execution_available": False, "approval_required_before_changes": True,
                }
                status = result.exit_status
    except ContractValidationError as error:
        codes = sorted({issue.code for issue in error.result.issues})
        status = ExitStatus.INPUT_ERROR if set(codes) & {
            "input_unreadable", "invalid_encoding", "invalid_json", "nonlocal_input",
            "output_exists", "output_unwritable", "output_cleanup_failed",
        } else ExitStatus.CONTRACT_ERROR
        report = _report(args.operation, "error", errors=[{"code": code} for code in codes])
    print(json.dumps(report, allow_nan=False))
    return int(status)
