"""Small host-side Docker launcher; Python 3.8+, no controller network code."""

from __future__ import annotations

import argparse
import getpass
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.parse import urlsplit

from ._json import load_json
from .backup_policy import TLS_WARNING, BackupPolicyError, SUPPORTED_DOMAINS, backup_domains


DEFAULT_IMAGE = "cc-vision-master:0.3"
REPOSITORY = Path(__file__).resolve().parents[2]


class SetupError(Exception):
    pass


def _answer(prompt: str, default: bool) -> bool:
    while True:
        value = input(prompt).strip().lower()
        if not value:
            return default
        if value in ("y", "yes"):
            return True
        if value in ("n", "no"):
            return False
        print("Enter y or n.", file=sys.stderr)


def _credentials(value: object) -> dict[str, str]:
    if not isinstance(value, dict) or set(value) != {"username", "password"}:
        raise SetupError("Credentials must contain only username and password.")
    result: dict[str, str] = {}
    for key in ("username", "password"):
        item = value[key]
        if not isinstance(item, str) or not item or any(not c.isprintable() for c in item):
            raise SetupError("Username and password must be nonempty printable strings.")
        result[key] = item
    return result


def _read_credentials(path: Path) -> dict[str, str]:
    info = path.stat()
    if not stat.S_ISREG(info.st_mode) or info.st_mode & 0o077:
        raise SetupError("Credentials must be a regular owner-private file (chmod 600).")
    with path.open("rb") as stream:
        opened = os.fstat(stream.fileno())
        if not stat.S_ISREG(opened.st_mode) or opened.st_mode & 0o077:
            raise SetupError("Credential permissions changed before reading.")
        raw = stream.read(16385)
    if len(raw) > 16384:
        raise SetupError("Credentials file exceeds the size limit.")
    return _credentials(load_json(raw.decode("utf-8")))


def _settings(payload: object, base: Path) -> tuple[dict[str, object], Path, Path | None]:
    if not isinstance(payload, dict) or set(payload) - {
        "source", "tls", "domains", "backup_mode", "controller_objects", "output_directory",
    }:
        raise SetupError("Config accepts only source, tls, backup_mode, domains, controller_objects and output_directory; no secrets.")
    source = payload.get("source")
    if not isinstance(source, dict) or set(source) - {"role", "name", "product", "version", "base_url"}:
        raise SetupError("Source profile is required and must not contain credentials.")
    if source.get("product") != "vision" or source.get("version") != "5.4.9" or source.get("role") != "source":
        raise SetupError("Source must be Vision 5.4.9 with role source.")
    url = source.get("base_url")
    if not isinstance(url, str):
        raise SetupError("Source HTTPS URL is required.")
    parsed = urlsplit(url)
    if (
        parsed.scheme != "https" or not parsed.hostname
        or parsed.username is not None or parsed.password is not None
        or parsed.path not in ("", "/") or parsed.query or parsed.fragment
        or any(not c.isprintable() or c.isspace() for c in url)
        or parsed.port == 0
    ):
        raise SetupError("Use an HTTPS origin without credentials, path, query or fragment.")
    tls = payload.get("tls", {})
    if not isinstance(tls, dict) or set(tls) - {"verify", "trusted_ca"}:
        raise SetupError("TLS accepts verify and optional trusted_ca only.")
    verify = tls.get("verify", True)
    if type(verify) is not bool:
        raise SetupError("tls.verify must be true or false, not a string or number.")
    ca = tls.get("trusted_ca")
    if ca is not None and (not isinstance(ca, str) or not ca or not verify):
        raise SetupError("Optional trusted_ca must be a local filename and requires verify=true.")
    ca_path = None if ca is None else (base / ca).resolve()
    if ca_path is not None and not ca_path.is_file():
        raise SetupError("Optional CA file is missing.")
    output = payload.get("output_directory")
    if not isinstance(output, str) or not output:
        raise SetupError("output_directory is required.")
    output_path = (base / output).resolve()
    if (
        output_path == REPOSITORY or REPOSITORY in output_path.parents
        or output_path in REPOSITORY.parents or output_path == Path.home()
        or sys.platform == "linux" and len(output_path.parts) < 3
    ):
        raise SetupError("Choose a dedicated backup output directory, not a workspace/home/root directory.")
    selection = payload.get("controller_objects", {"discovery": True})
    if not isinstance(selection, dict) or set(selection) - {"discovery", "site_names", "site_ids", "device_ips"}:
        raise SetupError("Controller selection accepts only discovery or explicit advanced target arrays.")
    backup_domains(payload)
    profile = {
        **payload, "source": dict(source),
        "tls": {"verify": verify, **({"trusted_ca": ca} if ca is not None else {})},
        "controller_objects": selection,
        "output_directory": str(output_path),
    }
    return profile, output_path, ca_path


def _output_permissions(path: Path, uid: int, gid: int) -> None:
    created = not path.exists()
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    if not path.is_dir():
        raise SetupError("Output path must be a directory.")
    if os.geteuid() == 0:
        info = path.stat()
        if created or info.st_uid == 0 and not any(path.iterdir()):
            os.chown(path, uid, gid)
            path.chmod(0o700)
        elif info.st_uid != uid or not info.st_mode & stat.S_IWUSR or not info.st_mode & stat.S_IXUSR:
            raise SetupError("Existing output directory is not writable by UID 10001; provision its ownership explicitly.")
    elif not os.access(path, os.W_OK | os.X_OK):
        raise SetupError("Output directory is not writable by the current non-root user.")


def _docker_mount(source: Path, target: str, *, readonly: bool) -> str:
    if "," in str(source) or any(not c.isprintable() for c in str(source)):
        raise SetupError("Docker mount paths must not contain commas or control characters.")
    return f"type=bind,source={source},target={target}" + (",readonly" if readonly else "")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Interactive or JSON Vision backup using the existing Docker image.")
    parser.add_argument("--config", help="Reusable non-secret JSON configuration.")
    parser.add_argument("--non-interactive", action="store_true", help="No prompts; requires config and credentials file.")
    parser.add_argument("--credentials-file", help="Owner-private external JSON credentials file; never saved to the profile.")
    args = parser.parse_args(argv)
    try:
        if sys.platform != "linux":
            raise SetupError("Run this host launcher on Linux with Bash, Python 3.8+ and Docker.")
        if os.geteuid() not in (0, 10001):
            raise SetupError("Run the launcher with sudo to provision UID 10001 inputs/output, or run as UID 10001.")
        if args.non_interactive and (not args.config or not args.credentials_file):
            raise SetupError("Unattended mode requires --config and --credentials-file; credentials are never saved in config.")
        if not args.non_interactive and not sys.stdin.isatty():
            raise SetupError("Interactive mode requires a terminal; use --non-interactive with secure credentials for unattended runs.")
        if shutil.which("docker") is None:
            raise SetupError("Docker is unavailable; install/configure it before running the launcher.")
        credentials = None
        if args.config:
            config_path = Path(args.config).resolve()
            payload = load_json(config_path.read_text(encoding="utf-8"))
            base = config_path.parent
        else:
            print(
                "=================================\n"
                "       CC-VISION MASTER\n"
                "=================================\n\n"
                "1. Full Supported Backup\n2. Select Backup Components\n3. Backup from JSON Configuration\n4. Exit"
            )
            menu = input("Select option: ").strip()
            if menu == "4":
                print("Exited; no controller connection attempted.")
                return 0
            if menu == "3":
                config_path = Path(input("Configuration filename [backup.json]: ").strip() or "backup.json").resolve()
                payload = load_json(config_path.read_text(encoding="utf-8"))
                base = config_path.parent
                args.config = str(config_path)
            elif menu in ("1", "2"):
                mode: dict[str, object] = {"backup_mode": "full-supported"}
                if menu == "2":
                    print("Available backup components:\n\n1. Controller Objects\n2. Device Access")
                    selected = (input("Select components [1,2]: ").strip() or "1,2").split(",")
                    if any(item.strip() not in ("1", "2") for item in selected):
                        raise SetupError("Select only supported component numbers 1 and 2.")
                    mode = {"backup_mode": "selected", "domains": [SUPPORTED_DOMAINS[int(item.strip()) - 1] for item in selected]}
                print("Source: APSolute Vision 5.4.9")
                payload, credentials = _interactive_profile(mode)
                base = Path.cwd()
            else:
                raise SetupError("Select menu option 1, 2, 3 or 4.")
        profile, output, ca = _settings(payload, base)
        if not profile["tls"]["verify"] and args.config:
            print(TLS_WARNING, file=sys.stderr)
        if args.credentials_file:
            credentials = _read_credentials(Path(args.credentials_file).resolve())
        elif credentials is None:
            credentials = _credentials({"username": input("Username: "), "password": getpass.getpass("Password: ")})
        if not args.config and _answer("Save reusable settings? [y/N]: ", False):
            filename = input("Settings filename [backup.json]: ").strip() or "backup.json"
            with Path(filename).open("x", encoding="utf-8") as stream:
                json.dump(profile, stream, indent=2)
            print("Non-secret settings saved; credentials were not saved.")
        print("Discovery uses the documented managed-device list; full configuration completeness is unverified.")
        if not args.non_interactive and not _answer("Start read-only Vision backup? [y/N]: ", False):
            print("Cancelled; no controller connection attempted.")
            return 0
        image_reference = os.environ.get("CC_VISION_IMAGE", DEFAULT_IMAGE)
        if not image_reference or "://" in image_reference or image_reference.startswith("-") or any(
            not c.isprintable() or c.isspace() for c in image_reference
        ):
            raise SetupError("CC_VISION_IMAGE must be a nonempty Docker image reference without whitespace or options.")
        image = subprocess.run(
            ["docker", "image", "inspect", image_reference],
            stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True, check=False,
        )
        if image.returncode != 0:
            raise SetupError(
                f"Docker cannot access image {image_reference}; build/load that image or set CC_VISION_IMAGE explicitly."
            )
        uid = gid = 10001
        _output_permissions(output, uid, gid)
        with tempfile.TemporaryDirectory(prefix="cc-vision-settings-") as temporary:
            runtime_profile = Path(temporary) / "profile.json"
            container_profile = {
                **profile, "output_directory": "/data",
                "tls": {"verify": profile["tls"]["verify"], **({"trusted_ca": "/run/config/vision-ca.pem"} if ca else {})},
            }
            runtime_profile.write_text(json.dumps(container_profile), encoding="utf-8")
            runtime_profile.chmod(0o400)
            runtime_credentials = Path(temporary) / "credentials.json"
            runtime_credentials.write_text(json.dumps(credentials), encoding="utf-8")
            runtime_credentials.chmod(0o400)
            if os.geteuid() == 0:
                os.chown(runtime_profile, uid, gid)
                os.chown(runtime_credentials, uid, gid)
            command = [
                "docker", "run", "--rm", "--network", "bridge", "--name", "cc-vision-master",
                "--user", "10001:10001",
                "--mount", _docker_mount(runtime_profile, "/run/config/profile.json", readonly=True),
                "--mount", _docker_mount(runtime_credentials, "/run/secrets/credentials.json", readonly=True),
                "--mount", _docker_mount(output, "/data", readonly=False),
            ]
            if ca:
                runtime_ca = Path(temporary) / "vision-ca.pem"
                shutil.copyfile(ca, runtime_ca)
                runtime_ca.chmod(0o400)
                if os.geteuid() == 0:
                    os.chown(runtime_ca, uid, gid)
                command.extend(["--mount", _docker_mount(runtime_ca, "/run/config/vision-ca.pem", readonly=True)])
            command.extend([image_reference, "--operation", "backup-vision", "--backup-profile", "/run/config/profile.json",
                            "--credentials-file", "/run/secrets/credentials.json"])
            result = subprocess.run(command, check=False, stderr=subprocess.PIPE, text=True)
            for line in result.stderr.splitlines(keepends=True):
                # This exact warning was already displayed before confirmation.
                if not profile["tls"]["verify"] and line.rstrip("\r\n") == TLS_WARNING:
                    continue
                sys.stderr.write(line)
            print(f"Backup output directory: {output}; exit status: {result.returncode}")
            return result.returncode
    except BackupPolicyError as error:
        print(f"Setup failed: {error}", file=sys.stderr)
        return 2
    except SetupError as error:
        print(f"Setup failed: {error}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("Cancelled; temporary credential/settings files were removed.", file=sys.stderr)
        return 130
    except (OSError, ValueError, UnicodeError, EOFError, RecursionError):
        print("Setup failed: file, JSON, input, permissions or Docker error; no credentials are printed.", file=sys.stderr)
        return 3


def _interactive_profile(mode: dict[str, object]) -> tuple[dict[str, object], dict[str, str]]:
    address = input("Vision IP/URL: ").strip()
    username = input("Username: ")
    password = getpass.getpass("Password: ")
    credentials = _credentials({"username": username, "password": password})
    verify = _answer("Verify HTTPS certificate? [Y/n]: ", True)
    if not verify:
        print(TLS_WARNING, file=sys.stderr)
    default = str(REPOSITORY.parent / "cc-vision-backups")
    output = input(f"Backup output directory [{default}]: ").strip() or default
    payload = {
        "source": {
            "role": "source", "name": "vision-source", "product": "vision",
            "version": "5.4.9",
            "base_url": address if "://" in address else "https://" + address,
        },
        "tls": {"verify": verify}, "output_directory": output, **mode,
    }
    return payload, credentials


if __name__ == "__main__":
    raise SystemExit(main())
