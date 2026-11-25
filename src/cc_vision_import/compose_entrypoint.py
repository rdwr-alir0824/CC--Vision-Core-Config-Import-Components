"""Compose shortcuts delegating to existing master CLI operations."""

import argparse
import json
import os
import sys
from collections.abc import Sequence
from pathlib import Path
from tempfile import TemporaryDirectory

from .master_cli import main as master_main


def main(argv: Sequence[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    if arguments and arguments[0] == "destination" and len(arguments) > 1 and arguments[1].startswith("--"):
        return master_main(arguments[1:])
    parser = argparse.ArgumentParser(
        description="Compose: source backup, or destination preflight (offline profile syntax only).",
    )
    parser.add_argument("role", choices=("source", "destination"))
    parser.add_argument("command", nargs="?", choices=("backup", "preflight"))
    args = parser.parse_args(arguments)
    if args.command is None:
        parser.print_help()
        return 0
    expected = "backup" if args.role == "source" else "preflight"
    if args.command != expected:
        parser.error("Use source backup or destination preflight; destination preflight is offline only.")

    def required(name: str) -> str:
        value = os.environ.get(name, "")
        if not value:
            parser.error(f"{name} must be set; connection values must not contain credentials.")
        return value

    source = {
        "role": "source", "name": os.environ.get("CCV_SOURCE_NAME", "vision-source"),
        "product": "vision", "version": "5.4.9", "base_url": required("CCV_VISION_URL"),
    }
    if args.role == "source":
        verify = os.environ.get("CCV_TLS_VERIFY", "true").lower()
        if verify not in ("true", "false"):
            parser.error("CCV_TLS_VERIFY must be true or false.")
        ca = os.environ.get("CCV_TRUSTED_CA", "")
        payload = {
            "source": source, "tls": {"verify": verify == "true", **({"trusted_ca": ca} if ca else {})},
            "backup_mode": "full-supported", "controller_objects": {"discovery": True},
            "output_directory": "/backups",
        }
    else:
        destination = {
            "role": "destination", "name": os.environ.get("CCV_DESTINATION_NAME", "cyber-controller-destination"),
            "product": "cyber-controller", "version": required("CCV_DESTINATION_VERSION"),
            "base_url": required("CCV_DESTINATION_URL"),
        }
    try:
        with TemporaryDirectory(prefix="ccv-compose-") as directory:
            profile = Path(directory) / "source.json"
            profile.write_text(json.dumps(payload if args.role == "source" else source), encoding="utf-8")
            if args.role == "source":
                return master_main([
                    "--operation", "backup-vision", "--backup-profile", str(profile),
                    "--credentials-file", "/run/secrets/credentials.json",
                ])
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
