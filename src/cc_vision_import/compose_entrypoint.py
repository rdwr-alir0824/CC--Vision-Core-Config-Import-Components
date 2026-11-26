"""Compose shortcuts delegating to existing master CLI operations."""

import argparse
import json
import os
import sys
from collections.abc import Sequence
from pathlib import Path
from tempfile import TemporaryDirectory

from .master_cli import main as master_main
from .tls_policy import TLSPolicyError, read_exception


def main(argv: Sequence[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    if arguments and arguments[0] == "destination" and len(arguments) > 1 and arguments[1].startswith("--"):
        return master_main(arguments[1:])
    parser = argparse.ArgumentParser(
        description="Compose: source backup, offline preflight, destination reads or explicitly authorized experimental single-Site creation.",
    )
    parser.add_argument("role", choices=("source", "destination", "discovery"))
    parser.add_argument("command", nargs="?", choices=(
        "backup", "preflight", "discover-sites", "site-dry-run", "site-create",
        "sites-dry-run", "sites-execute", "sites-resume",
    ))
    parser.add_argument("--qualify-default-root", action="store_true")
    parser.add_argument("--input")
    parser.add_argument("--comparison")
    parser.add_argument("--destination-snapshot")
    parser.add_argument("--site-reference")
    parser.add_argument("--target-version")
    parser.add_argument("--operation-delay", type=float)
    parser.add_argument("--readback-interval", type=float)
    parser.add_argument("--readback-attempts", type=int)
    args = parser.parse_args(arguments)
    single_site = args.role == "discovery" and args.command in ("site-dry-run", "site-create")
    site_batch = args.role == "discovery" and args.command in ("sites-dry-run", "sites-execute", "sites-resume")
    site_operation = single_site or site_batch
    site_values = (args.input, args.comparison, args.destination_snapshot, args.site_reference)
    if site_operation:
        if any(value is None for value in site_values[:3]) or (
            single_site and args.site_reference is None
        ) or (site_batch and args.site_reference is not None) or args.qualify_default_root:
            parser.error("Single-Site mode requires input/comparison/destination-snapshot/site-reference.")
        for value, prefix in ((args.input, "/incoming/"), (args.comparison, "/reports/"),
                              (args.destination_snapshot, "/reports/")):
            if not value.startswith(prefix) or ".." in Path(value).parts:
                parser.error("Use existing container-visible incoming/report paths.")
    elif any(value is not None for value in (*site_values, args.target_version)):
        parser.error("Single-Site options require discovery site-dry-run or site-create.")
    if not site_batch and any(value is not None for value in (
        args.operation_delay, args.readback_interval, args.readback_attempts,
    )):
        parser.error("Batch timing requires a sites-dry-run, sites-execute or sites-resume command.")
    if args.qualify_default_root and (args.role != "discovery" or args.command != "discover-sites"):
        parser.error("--qualify-default-root requires discovery discover-sites.")
    if args.command is None:
        parser.print_help()
        return 0
    expected = {"source": "backup", "destination": "preflight", "discovery": "discover-sites"}[args.role]
    if args.command != expected and not site_operation:
        parser.error("Use the selected role's backup, preflight or discover-sites command.")

    def required(name: str) -> str:
        value = os.environ.get(name, "")
        if not value:
            parser.error(f"{name} must be set; connection values must not contain credentials.")
        return value

    def tls(role: str, origin: str) -> dict[str, object]:
        source = role == "source"
        variable = "CCV_TLS_VERIFY" if source else "CCV_DESTINATION_TLS_VERIFY"
        requested = os.environ.get(variable, "").lower()
        try:
            policy = read_exception(
                Path("/run/secrets/tls-exception.json"), origin, requested,
                os.environ.get("CCV_ALLOW_INSECURE_TLS_EXCEPTION", "true"),
            )
        except TLSPolicyError as error:
            parser.error(str(error))
        ca = os.environ.get("CCV_TRUSTED_CA" if source else "CCV_DESTINATION_TRUSTED_CA", "")
        fields = {"verify": policy.verify} if source else policy.to_dict()
        if policy.verify and ca:
            fields["trusted_ca"] = ca
        return fields

    destination = None
    if args.role == "discovery":
        origin = required("CCV_DESTINATION_URL")
        payload = {
            "destination": {
                "name": os.environ.get("CCV_DESTINATION_NAME", "cyber-controller-destination"),
                "base_url": origin,
            },
            "tls": tls("discovery", origin),
            "output_directory": "/reports",
        }
    else:
        payload = {
            "role": "source", "name": os.environ.get("CCV_SOURCE_NAME", "vision-source"),
            "product": "vision", "version": "5.4.9", "base_url": required("CCV_VISION_URL"),
        }
    if args.role == "source":
        payload = {
            "source": payload, "tls": tls("source", required("CCV_VISION_URL")),
            "backup_mode": "full-supported", "controller_objects": {"discovery": True},
            "output_directory": "/backups",
        }
    elif args.role == "destination":
        destination = {
            "role": "destination", "name": os.environ.get("CCV_DESTINATION_NAME", "cyber-controller-destination"),
            "product": "cyber-controller", "version": required("CCV_DESTINATION_VERSION"),
            "base_url": required("CCV_DESTINATION_URL"),
        }
    try:
        with TemporaryDirectory(prefix="ccv-compose-") as directory:
            profile = Path(directory) / "source.json"
            profile.write_text(json.dumps(payload), encoding="utf-8")
            if args.role == "source":
                return master_main([
                    "--operation", "backup-vision", "--backup-profile", str(profile),
                    "--credentials-file", "/run/secrets/credentials.json",
                ])
            if args.role == "discovery":
                return master_main([
                    "--operation", ("site-batch-" + args.command.removeprefix("sites-")) if site_batch else (
                        ("single-site-create" if args.command == "site-create" else "single-site-dry-run")
                        if single_site else "destination-discovery"
                    ), "--discovery-profile", str(profile),
                    "--credentials-file", "/run/secrets/credentials.json",
                    *(["--qualify-default-root"] if args.qualify_default_root else []),
                    *([
                        "--input", args.input, "--comparison", args.comparison,
                        "--destination-snapshot", args.destination_snapshot,
                        *(["--site-reference", args.site_reference] if single_site else []),
                        *(["--target-version", args.target_version] if args.target_version else []),
                        *[part for option, value in (
                            ("--operation-delay", args.operation_delay), ("--readback-interval", args.readback_interval),
                            ("--readback-attempts", args.readback_attempts),
                        ) if value is not None for part in (option, str(value))],
                    ] if site_operation else []),
                ])
            assert destination is not None
            destination_profile = Path(directory) / "destination.json"
            destination_profile.write_text(json.dumps(destination), encoding="utf-8")
            return master_main([
                "--operation", "profiles", "--source-product", "vision",
                "--source-profile", str(profile), "--destination-profile", str(destination_profile),
            ])
    except OSError:
        print(json.dumps({
            "operation": args.command, "status": "error",
            "errors": [{"code": "compose_io_error"}],
        }))
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
