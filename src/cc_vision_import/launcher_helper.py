"""Offline-only utilities for the Bash/Docker launcher; no HTTP or authentication."""

import argparse
import ipaddress
import json
import os
import re
import ssl
import stat
import sys
from pathlib import Path

from ._json import load_json
from .backup_policy import SUPPORTED_DOMAINS
from .backup_setup import SetupError, _credentials, _operator_summary
from .tls_policy import TLSPolicy, TLSPolicyError, exceptions_allowed, warning


def origin(value: str) -> str:
    if not value or value != value.strip() or any(c in value for c in "/@?#%\\"):
        raise SetupError("Enter an IP address or DNS hostname only.")
    address = value[1:-1] if value.startswith("[") and value.endswith("]") else value
    try:
        native = ipaddress.ip_address(address)
    except ValueError:
        if ":" in value or "[" in value or "]" in value or re.fullmatch(r"[0-9.]+", value):
            raise SetupError("Invalid IP address.")
        if len(value) > 253 or not all(
            re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?", label)
            for label in value.split(".")
        ):
            raise SetupError("Invalid DNS hostname.")
        return "https://" + value
    return "https://" + (f"[{native}]" if native.version == 6 else str(native))


def _private_file(path: Path) -> None:
    info = path.lstat()
    if (
        not stat.S_ISREG(info.st_mode) or stat.S_IMODE(info.st_mode) != 0o600
        or info.st_uid != 10001 or info.st_gid != 10001
    ):
        raise SetupError("Temporary files require UID/GID 10001 and mode 0600.")


def _read() -> str:
    raw = sys.stdin.buffer.read(16 * 1024 * 1024 + 1)
    if len(raw) > 16 * 1024 * 1024:
        raise SetupError("Input exceeds the offline helper budget.")
    return raw.decode("utf-8")


def settings(payload: object, selection: str) -> list[str]:
    if not isinstance(payload, dict) or not isinstance(payload.get("services"), dict):
        raise SetupError("Normalized Compose services are required.")
    services = payload["services"]
    name = {"1": "ccv-source", "2": "ccv-destination-discovery", "3": "ccv-destination"}[selection]
    service = services[name]
    if not isinstance(service, dict):
        raise SetupError("Expected a normalized Compose service.")
    if service.get("user") != "10001:10001" or not service.get("read_only"):
        raise SetupError("Preserve the approved non-root, read-only container.")
    if (
        service.get("privileged") or service.get("ports") or service.get("network_mode") == "host"
        or "ALL" not in service.get("cap_drop", [])
        or "no-new-privileges:true" not in service.get("security_opt", [])
    ):
        raise SetupError("Preserve the approved container security restrictions.")
    if selection == "3" and service.get("network_mode") != "none":
        raise SetupError("Offline destination must have networking disabled.")
    if selection == "2" and set(service.get("networks", {})) != {"destination-discovery"}:
        raise SetupError("Preserve the approved destination discovery network.")
    image = service["image"]
    if any(row.get("image") != image for row in services.values()):
        raise SetupError("All roles must use the same image.")
    mounts = {row["target"]: row for row in service["volumes"]}
    expected_mounts = {"/run/secrets", "/reports"} if selection == "2" else {
        "/run/secrets", "/run/config", "/backups",
    } if selection == "1" else {"/incoming", "/reports"}
    if set(mounts) != expected_mounts:
        raise SetupError("Unexpected Compose bind mounts.")
    output = mounts["/backups" if selection == "1" else "/reports"]["source"]
    if selection == "3":
        if not mounts["/incoming"].get("read_only"):
            raise SetupError("Incoming backups must be read-only.")
        config = mounts["/incoming"]["source"]
    elif selection == "1":
        config = mounts["/run/config"]["source"]
    else:
        config = mounts["/run/secrets"]["source"]
    for value in (image, output, config):
        if not isinstance(value, str) or not value or any(c in value for c in "\r\n,"):
            raise SetupError("Unsafe image or bind path.")
    context = service.get("build", {}).get("context")
    if isinstance(context, str) and (output == context or output.startswith(context.rstrip("/") + "/")):
        raise SetupError("Backups/reports must remain outside the application checkout.")
    variable = "CCV_TRUSTED_CA" if selection == "1" else "CCV_DESTINATION_TRUSTED_CA"
    ca = service.get("environment", {}).get(variable) or "-"
    if selection != "3" and ca != "-":
        prefix = "/run/config/" if selection == "1" else "/run/secrets/"
        if not isinstance(ca, str) or not ca.startswith(prefix) or not re.fullmatch(r"[A-Za-z0-9_-]+\.pem", ca[len(prefix):]):
            raise SetupError("Custom CA must be a PEM basename in the existing CA mount.")
        ca = ca[len(prefix):]
    allowed = "false" if selection == "3" else service.get("environment", {}).get(
        "CCV_ALLOW_INSECURE_TLS_EXCEPTION", "true",
    )
    exceptions_allowed(allowed)
    return [image, output, config, ca, allowed]


def prepare(
    value: str, selection: str, directory: Path, admin: Path,
    requested: str = "-",
) -> str:
    result = origin(value)
    if requested != "-" and not re.fullmatch(r"[A-Za-z0-9_-]+\.pem", requested):
        raise SetupError("Custom CA must be a PEM basename.")
    destination = directory / "ca.pem"
    _private_file(destination)
    ca = admin / (requested if requested != "-" else "vision-ca.pem" if selection == "1" else "cc-ca.pem")
    if ca.is_symlink():
        raise SetupError("CA must be an administrator-managed regular file.")
    if ca.exists():
        if not ca.is_file():
            raise SetupError("CA must be a regular PEM bundle.")
        context = ssl.create_default_context(cafile=str(ca))
    else:
        if requested != "-":
            raise SetupError("Required custom CA is missing.")
        context = ssl.create_default_context()
    # Copy certificates only, never private keys or arbitrary PEM-file contents.
    certificates = context.get_ca_certs(binary_form=True)
    if not certificates:
        raise SetupError("No trusted CA certificates available.")
    destination.write_text("".join(ssl.DER_cert_to_PEM_cert(cert) for cert in certificates), encoding="ascii")
    return result


def approve_exception(value: str, directory: Path, allowed: str) -> None:
    if not exceptions_allowed(allowed):
        raise TLSPolicyError("This deployment prohibits insecure TLS exceptions.")
    policy = TLSPolicy.from_dict({
        "verify": False, "lab_authorized": True, "authorized_origin": value,
    }, value)
    path = directory / "tls-exception.json"
    _private_file(path)
    path.write_text(json.dumps(policy.to_dict()), encoding="utf-8")


def certificate_exception_available(report: dict, selection: str, status: int) -> bool:
    tls = report.get("tls")
    codes = report.get("failure_codes" if selection == "1" else "issue_codes")
    if not (
        selection in ("1", "2") and status == 1
        and isinstance(tls, dict) and tls.get("verify") is True
        and report.get("authenticated") is False
        and report.get("read_only") is True
        and report.get("configuration_writes_authorized") is False
        and isinstance(codes, list) and "tls_certificate_failure" in codes
    ):
        return False
    return (
        report.get("overall_status") == "failed_collection"
        and report.get("completed_modules") == []
        and not any(row.get("status") == "collected" for row in report.get("results", []))
    ) if selection == "1" else (
        report.get("status") == "error" and "snapshot_directory" not in report
    )


def check_backup(folder: Path) -> None:
    if not re.fullmatch(r"vision-backup-[A-Za-z0-9_-]+", folder.name) or folder.is_symlink() or not folder.is_dir():
        raise SetupError("Select a native Vision backup directory.")
    count = 0
    def unreadable(error: OSError) -> None:
        raise SetupError("Backup contains an unreadable directory.") from error

    for root, directories, files in os.walk(folder, followlinks=False, onerror=unreadable):
        count += len(directories) + len(files)
        if count > 10000 or any((Path(root) / name).is_symlink() for name in directories + files):
            raise SetupError("Backup contains links or exceeds the inspection budget.")
        if any(not (Path(root) / name).is_file() for name in files):
            raise SetupError("Backup contains non-regular files.")
    for domain in SUPPORTED_DOMAINS:
        directory = folder / domain
        if not directory.is_dir() or not any(path.is_file() for path in directory.glob("*.json")):
            raise SetupError("Every supported module directory must contain its JSON artifacts.")
    with (folder / "summary.json").open("rb") as stream:
        raw = stream.read(16 * 1024 * 1024 + 1)
    if len(raw) > 16 * 1024 * 1024:
        raise SetupError("Summary exceeds the inspection budget.")
    report = load_json(raw.decode("utf-8"))
    _operator_summary(json.dumps(report), folder.parent)
    if (
        report.get("overall_status") != "supported_collection_succeeded"
        or set(report.get("completed_modules", [])) != set(SUPPORTED_DOMAINS)
        or report.get("failed_modules")
    ):
        raise SetupError("Source collection is incomplete; review its summary.")
    for domain in ("organization-tree", "physical-tree"):
        if not (folder / domain / "tree.json").is_file():
            raise SetupError("Both native tree artifacts must be present.")


def summary(report: object, selection: str, status: int, output: str, filename: str) -> int:
    if not isinstance(report, dict):
        raise SetupError("Expected a structured application result.")
    if selection != "3":
        tls = report.get("tls")
        if tls is not None:
            if not isinstance(tls, dict) or type(tls.get("verify")) is not bool:
                raise SetupError("Invalid TLS result.")
            print(f"TLS certificate/hostname verification: {'TRUE' if tls['verify'] else 'FALSE'} (HTTPS).")
            message = warning(tls["verify"])
            if message is not None:
                print(message)
        codes = report.get("failure_codes", []) if selection == "1" else report.get("issue_codes", [])
        if isinstance(codes, list) and "tls_certificate_failure" in codes:
            print("TLS certificate verification failed: untrusted chain or hostname mismatch. No automatic downgrade.")
    if selection == "1":
        if status == 0 and report.get("overall_status") != "supported_collection_succeeded":
            raise SetupError("Incomplete source collection cannot have a successful launcher status.")
        print(_operator_summary(json.dumps(report), Path(output)))
    else:
        expected = "destination-discovery" if selection == "2" else "site-migration-readiness"
        if report.get("operation") != expected:
            raise SetupError("Unexpected application operation.")
        state = report.get("status")
        allowed = ("collected-unqualified", "partial", "error") if selection == "2" else ("blocked", "error")
        if state not in allowed:
            raise SetupError("Unexpected application status.")
        counts = report.get("counts", {})
        allowed_counts = {
            "root_candidates", "site_candidates", "sites_with_usable_identity",
            "sites_with_unresolved_dependencies", "unclassified_nodes",
        } if selection == "2" else {
            "site_candidates_inspected", "sites_with_sufficient_source_fields",
            "sites_with_missing_source_fields", "sites_with_unresolved_parent_dependencies",
            "sites_orderable_from_source_root", "sites_with_unprojected_fields",
            "sites_with_duplicate_names", "sites_with_ambiguous_parent_names",
            "sites_requiring_destination_mapping", "unclassified_structure_nodes",
        }
        if not isinstance(counts, dict) or any(
            key not in allowed_counts or type(value) is not int or value < 0
            for key, value in counts.items()
        ):
            raise SetupError("Invalid aggregate counts.")
        print("CC Site discovery: " + state if selection == "2" else "Offline Site readiness: " + state.upper())
        for key, value in sorted(counts.items()):
            print(f"{key.replace('_', ' ')}: {value}")
        if selection == "2":
            print("CC version unknown/unverified; hierarchy and completeness unqualified.")
            redactions = report.get("redacted_fields")
            if redactions is not None:
                if type(redactions) is not int or redactions < 0:
                    raise SetupError("Invalid redaction count.")
                print(f"Redacted fields: {redactions} (full response before Site projection).")
            folder = report.get("snapshot_directory")
            if folder is not None:
                if not isinstance(folder, str) or not re.fullmatch(r"cc-destination-[A-Za-z0-9-]+", folder):
                    raise SetupError("Invalid snapshot directory.")
                if report.get("snapshot_file") != "organization-sites.json":
                    raise SetupError("Invalid snapshot filename.")
                print(f"Private snapshot: {Path(output) / folder / 'organization-sites.json'}")
        else:
            print(f"Report: {Path(output) / filename}")
            if (
                status == 1 and state == "blocked" and report.get("offline_only") is True
                and report.get("migration_ready") is False and report.get("execution_authorized") is False
            ):
                print("Assessment completed; migration BLOCKED, not an application failure. No imports available.")
                return 10
            if state == "blocked":
                raise SetupError("Blocked readiness must retain its explicit non-executable failure status.")
    print(f"Application exit status: {status}; no configuration imported.")
    if status == 0 and report.get("status") in ("partial", "error"):
        raise SetupError("Failure report cannot be successful.")
    return 11 if certificate_exception_available(report, selection, status) else 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("settings", "prepare", "approve-exception", "credentials", "backups", "check-backup", "summary"))
    parser.add_argument("values", nargs="*")
    args = parser.parse_args(argv)
    try:
        directory = Path("/run/setup")
        if args.action == "settings":
            print("\n".join(settings(load_json(_read()), args.values[0])))
        elif args.action == "prepare":
            print(prepare(_read(), args.values[0], directory, Path("/run/admin"), args.values[1]))
        elif args.action == "approve-exception":
            approve_exception(_read(), directory, args.values[0])
        elif args.action == "credentials":
            parts = _read().split("\0")
            if len(parts) != 3 or parts[-1] != "":
                raise SetupError("Invalid credential input.")
            credentials = _credentials({"username": parts[0], "password": parts[1]})
            path = directory / "credentials.json"
            _private_file(path)
            path.write_text(json.dumps(credentials), encoding="utf-8")
        elif args.action == "backups":
            print("\n".join(sorted(
                path.name for path in Path("/incoming").iterdir()
                if path.is_dir() and not path.is_symlink() and re.fullmatch(r"vision-backup-[A-Za-z0-9_-]+", path.name)
            )))
        elif args.action == "check-backup":
            if not re.fullmatch(r"vision-backup-[A-Za-z0-9_-]+", args.values[0]):
                raise SetupError("Select a backup basename only.")
            check_backup(Path("/incoming") / args.values[0])
        else:
            return summary(load_json(_read()), args.values[0], int(args.values[1]), args.values[2], args.values[3])
        return 0
    except TLSPolicyError as error:
        print(str(error), file=sys.stderr)
        return 3
    except (SetupError, OSError, ValueError, KeyError, IndexError, TypeError, RecursionError):
        print("Offline launcher helper failed: invalid input, permissions, incomplete backup or CA trust configuration; values withheld.", file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
