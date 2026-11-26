import importlib
import io
import json
import os
import shutil
import ssl
import stat
import subprocess
import sys
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import Mock, patch

from offline_support import OfflineTestCase


ROOT = Path(__file__).resolve().parents[1]
BASH = shutil.which("bash") or r"C:\Program Files\Git\bin\bash.exe"
SECRET = "private-password-marker"
USERNAME = "private-user-marker"

MOCK_DOCKER = r'''
import json, os, pathlib, subprocess, sys
from unittest.mock import patch
from cc_vision_import import launcher_helper as helper
from cc_vision_import import tls_policy
from cc_vision_import.destination_discovery import project_default_root

root = pathlib.Path(os.environ["MOCK_ROOT"])
sys.stdout.reconfigure(newline="\n")
sys.stderr.reconfigure(newline="\n")
args = sys.argv[1:]
mode = os.environ.get("MOCK_MODE", "")
with (root / "calls.jsonl").open("a") as stream:
    stream.write(json.dumps({"args": args, "env": {
        k: v for k, v in os.environ.items() if k.startswith("CCV_") or k in ("ccv_password", "ccv_username")
    }}) + "\n")
if args[:2] == ["compose", "version"]:
    sys.exit(1 if mode == "compose-missing" else 0)
if args[:2] == ["image", "inspect"]:
    sys.exit(1 if mode == "image-missing" else 0)
if args[:2] == ["container", "inspect"]:
    state = root / "active.json"
    if not state.exists():
        sys.exit(1)
    print(json.loads(state.read_text())["label"])
    sys.exit(0)
if args[:2] == ["container", "rm"]:
    (root / "active.json").unlink(missing_ok=True)
    sys.exit(0)
if args[0] == "compose" and "config" in args:
    config = json.loads((root / "compose.json").read_text())
    if "--images" in args:
        print("cc-vision-master:test")
    else:
        print(json.dumps(config))
    sys.exit(0)
if args[0] == "run":
    action_index = args.index("cc_vision_import.launcher_helper") + 1
    action, values = args[action_index], args[action_index + 1:]
    mounts = [args[i + 1] for i, value in enumerate(args) if value == "--mount"]
    setup_value = next(m.split("source=", 1)[1].split(",target=", 1)[0] for m in mounts if "target=/run/setup" in m)
    if os.name == "nt" and setup_value.startswith("/"):
        setup_value = subprocess.run(
            [os.environ["MOCK_BASH"], "-c", 'cygpath -w "$1"', "_", setup_value],
            capture_output=True, check=True,
        ).stdout.decode().strip()
    setup = pathlib.Path(setup_value)
    raw = sys.stdin.read()
    if action == "settings":
        print("\n".join(helper.settings(json.loads(raw), values[0])))
    elif action == "prepare":
        if mode == "tls-invalid":
            sys.exit(3)
        current = helper.origin(raw)
        print(current)
        (setup / "ca.pem").write_text("PUBLIC-CA")
    elif action == "approve-exception":
        with patch.object(helper, "_private_file"):
            helper.approve_exception(raw, setup, values[0])
    elif action == "credentials":
        parts = raw.split("\0")
        data = helper._credentials({"username": parts[0], "password": parts[1]})
        (setup / "credentials.json").write_text(json.dumps(data))
        (root / "credential-path.txt").write_text(str(setup / "credentials.json"))
    elif action == "backups":
        print("vision-backup-synthetic")
    elif action == "check-backup":
        helper.check_backup(root / "incoming" / values[0])
    else:
        sys.exit(helper.summary(json.loads(raw), values[0], int(values[1]), values[2], values[3]))
    sys.exit(0)
if args[0] == "compose" and "run" in args:
    if mode in ("interrupt", "interrupt-int") or (
        mode == "certificate-interrupt" and os.environ.get("CCV_DESTINATION_TLS_VERIFY") == "false"
    ):
        label = args[args.index("--label") + 1].split("=", 1)[1]
        (root / "active.json").write_text(json.dumps({"label": label}))
        signal_name = "-INT" if mode == "interrupt-int" else "-TERM"
        subprocess.run([os.environ["MOCK_BASH"], "-c", 'kill "$1" "$2"', "_", signal_name, os.environ["MOCK_LAUNCHER_PID"]], check=True)
        sys.exit(143)
    if mode == "bad-output":
        print("private-password-marker")
        sys.exit(0)
    if mode == "failure":
        print(json.dumps({"operation": "destination-discovery", "status": "error"}))
        print("private-password-marker", file=sys.stderr)
        sys.exit(1)
    service = next(name for name in ("ccv-source", "ccv-destination", "ccv-destination-discovery") if name in args)
    report = json.loads((root / ("source.json" if service == "ccv-source" else "discovery.json" if service.endswith("discovery") else "readiness.json")).read_text())
    if service == "ccv-destination-discovery" and "--qualify-default-root" in args:
        report = {
            "operation": "destination-discovery", "discovery_mode": "default-root",
            "migration_ready": False, "execution_authorized": False,
            "import_file_compatible": False, "configuration_writes_authorized": False,
            "read_only": True, "snapshot_directory": "cc-destination-synthetic",
            "snapshot_file": "root-qualification.json",
            **project_default_root({"name": "Default", "ormID": "private-native-id"}),
        }
    exit_status = 1 if service == "ccv-destination" else 0
    if service != "ccv-destination":
        variable = "CCV_TLS_VERIFY" if service == "ccv-source" else "CCV_DESTINATION_TLS_VERIFY"
        verify = os.environ[variable] == "true"
        report["tls"] = tls_policy.execution_tls(verify)
        report["authenticated"] = True
        if not verify:
            key = "CCV_SOURCE_SECRETS_DIR" if service == "ccv-source" else "CCV_DESTINATION_SECRETS_DIR"
            value = os.environ[key]
            if os.name == "nt" and value.startswith("/"):
                value = subprocess.run([os.environ["MOCK_BASH"], "-c", 'cygpath -w "$1"', "_", value], capture_output=True, check=True).stdout.decode().strip()
            address = os.environ["CCV_VISION_URL" if service == "ccv-source" else "CCV_DESTINATION_URL"]
            with patch.object(tls_policy, "_private_file"):
                tls_policy.read_exception(pathlib.Path(value) / "tls-exception.json", address, "false", os.environ["CCV_ALLOW_INSECURE_TLS_EXCEPTION"])
        if mode in ("certificate-failure", "certificate-after-auth", "certificate-retry-failure", "certificate-interrupt") and verify:
            report.update(authenticated=mode == "certificate-after-auth", read_only=True, configuration_writes_authorized=False)
            exit_status = 1
            if service == "ccv-source":
                report.update(
                    overall_status="failed_collection", completed_modules=[], results=[],
                    failed_modules=report["requested_modules"], failure_codes=["tls_certificate_failure"],
                    device_details_collected=0, device_access_objects=0,
                    run_directory="vision-backup-certificate-failed",
                )
                report["inventory"]["status"] = "not_collected"
                for row in [report["ldap_permissions"], report["scheduler"], *report["trees"].values()]:
                    row.update(status="skipped", record_count=0, redacted_fields=0)
            else:
                report.update(status="error", issue_codes=["tls_certificate_failure"])
                report.pop("snapshot_directory", None)
                report.pop("snapshot_file", None)
        elif mode == "certificate-retry-failure" and not verify:
            report.update(status="error", authenticated=False, issue_codes=["login_rejected"])
            report.pop("snapshot_directory", None)
            report.pop("snapshot_file", None)
            exit_status = 1
    if service == "ccv-destination":
        output = args[args.index("--output") + 1]
        (root / "reports" / pathlib.Path(output).name).write_text(json.dumps({k: v for k, v in report.items() if k != "opaque"}))
    elif service == "ccv-source":
        folder = root / "backups" / report["run_directory"]
        folder.mkdir(exist_ok=True)
        (folder / "summary.json").write_text(json.dumps(report))
    elif "snapshot_directory" in report:
        folder = root / "reports" / report["snapshot_directory"]
        folder.mkdir(exist_ok=True)
        filename = report.get("snapshot_file", "organization-sites.json")
        (folder / filename).write_text(json.dumps(report if filename == "root-qualification.json" else {
            "domain": "cc-destination-organization-sites", "migration_ready": False, "tls": report["tls"],
        }))
    print(json.dumps(report))
    sys.exit(exit_status)
sys.exit(2)
'''


class UnifiedLauncherTests(OfflineTestCase):
    def setUp(self):
        super().setUp()
        self.helper = importlib.import_module("cc_vision_import.launcher_helper")
        self.bin = self.directory / "bin"
        self.bin.mkdir()
        self.runtime = self.directory / "temporary"
        self.runtime.mkdir()
        self.backups = self.directory / "backups"
        self.incoming = self.directory / "incoming"
        self.reports = self.directory / "reports"
        self.admin = self.directory / "admin"
        self.source_admin = self.directory / "source-admin"
        for folder in (self.backups, self.incoming, self.reports, self.admin, self.source_admin):
            folder.mkdir()
        (self.admin / "credentials.json").write_text("ADMINISTRATOR-SECRET-UNCHANGED")
        compose = json.loads((ROOT / "compose.yaml").read_text())
        for service in compose["services"].values():
            service["image"] = "cc-vision-master:test"
            service["environment"] = {
                name: value.rsplit(":-", 1)[-1].removesuffix("}") if name == "CCV_ALLOW_INSECURE_TLS_EXCEPTION" else ""
                for name, value in service.get("environment", {}).items()
            }
            for mount in service["volumes"]:
                mount["source"] = str({
                    "/backups": self.backups, "/incoming": self.incoming, "/reports": self.reports,
                    "/run/config": self.source_admin, "/run/secrets": self.admin,
                }[mount["target"]]).replace("\\", "/")
        (self.directory / "compose.json").write_text(json.dumps(compose))
        self.source = {
            "operation": "backup-vision", "requested_modules": list(self.helper.SUPPORTED_DOMAINS),
            "completed_modules": list(self.helper.SUPPORTED_DOMAINS), "failed_modules": [],
            "run_directory": "vision-backup-synthetic", "overall_status": "supported_collection_succeeded",
            "inventory": {"status": "collected"}, "device_details_collected": 36, "device_access_objects": 36,
            "results": [{"status": "collected", "operation": "device-by-ip", "redacted_fields": 2}],
            "ldap_permissions": {"status": "collected", "record_count": 13, "redacted_fields": 0},
            "trees": {domain: {"status": "collected", "record_count": 1, "redacted_fields": 0}
                      for domain in ("physical-tree", "organization-tree")},
            "scheduler": {"status": "collected", "record_count": 23, "redacted_fields": 46},
            "tls": {"verify": True},
            "authenticated": True, "read_only": True, "configuration_writes_authorized": False,
        }
        (self.directory / "source.json").write_text(json.dumps(self.source))
        (self.directory / "discovery.json").write_text(json.dumps({
            "operation": "destination-discovery", "status": "collected-unqualified",
            "counts": {"site_candidates": 2}, "snapshot_directory": "cc-destination-synthetic",
            "snapshot_file": "organization-sites.json", "opaque": SECRET,
        }))
        (self.directory / "readiness.json").write_text(json.dumps({
            "operation": "site-migration-readiness", "status": "blocked", "offline_only": True,
            "migration_ready": False, "execution_authorized": False,
            "counts": {"site_candidates_inspected": 30}, "opaque": SECRET,
        }))
        folder = self.incoming / "vision-backup-synthetic"
        folder.mkdir()
        for domain in self.helper.SUPPORTED_DOMAINS:
            module = folder / domain
            module.mkdir()
            (module / "tree.json").write_text("{}")
        (folder / "summary.json").write_text(json.dumps(self.source))
        (self.directory / "mock.py").write_text(MOCK_DOCKER)
        (self.bin / "docker").write_text('#!/usr/bin/env bash\nexport MOCK_LAUNCHER_PID="$PPID"\nexec "$MOCK_PYTHON" "$MOCK_SCRIPT" "$@"\n', newline="\n")
        (self.bin / "id").write_text('#!/usr/bin/env bash\nprintf "%s\\n" "${MOCK_UID:-10001}"\n', newline="\n")
        (self.bin / "sudo").write_text(
            '#!/usr/bin/env bash\nprintf "%s\\n" "$*" >> "$MOCK_ROOT/sudo.txt"\n'
            '[[ "${MOCK_MODE:-}" != "sudo-denied" ]]\n', newline="\n",
        )
        (self.directory / "functions.sh").write_text(
            'rm() {\n'
            '  if [[ "${MOCK_MODE:-}" == "cleanup-failure" ]]; then return 1; fi\n'
            '  command rm "$@"\n'
            '}\n', newline="\n",
        )
        for filename in ("docker", "id", "sudo"):
            (self.bin / filename).chmod(0o755)

    def launch(self, selection="2", mode="", inputs=None, uid="10001", arguments=()):
        environment = {
            **os.environ, "PATH": str(self.bin).replace("\\", "/") + os.pathsep + os.environ.get("PATH", ""),
            "PYTHONPATH": str(ROOT / "src"), "MOCK_ROOT": str(self.directory),
            "MOCK_PYTHON": sys.executable.replace("\\", "/"),
            "MOCK_SCRIPT": str(self.directory / "mock.py").replace("\\", "/"),
            "MOCK_MODE": mode, "TMPDIR": str(self.runtime).replace("\\", "/"),
            "MOCK_BASH": BASH.replace("\\", "/"),
            "MOCK_UID": uid,
            "BASH_ENV": str(self.directory / "functions.sh").replace("\\", "/"),
        }
        for key in list(environment):
            if key.startswith("CCV_") or key in ("ccv_username", "ccv_password"):
                del environment[key]
        result = subprocess.run(
            [BASH, str(ROOT / "ccv.sh").replace("\\", "/"), *arguments],
            input=(inputs if inputs is not None else f"{selection}\ncontroller.invalid\n{USERNAME}\n{SECRET}\n").encode(),
            capture_output=True, env=environment, timeout=30,
        )
        result.stdout = result.stdout.decode()
        result.stderr = result.stderr.decode()
        calls_path = self.directory / "calls.jsonl"
        calls = [json.loads(line) for line in calls_path.read_text().splitlines()] if calls_path.exists() else []
        for text in (result.stdout, result.stderr, json.dumps(calls)):
            self.assertNotIn(SECRET, text)
            self.assertNotIn(USERNAME, text)
        if mode != "cleanup-failure":
            self.assertEqual(list(self.runtime.iterdir()), [])
        self.assertEqual((self.admin / "credentials.json").read_text(), "ADMINISTRATOR-SECRET-UNCHANGED")
        return result, calls

    def test_menu_exit_does_not_require_docker_and_invalid_selection_is_explicit(self):
        result, calls = self.launch(inputs="4\n")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(calls, [])
        result, calls = self.launch(inputs="9\n")
        self.assertEqual(result.returncode, 2)
        self.assertIn("Select 1, 2, 3 or 4", result.stderr)

    def test_root_flag_routes_through_existing_discovery_and_sanitized_summary(self):
        result, calls = self.launch(arguments=("--qualify-default-root",))
        self.assertEqual(result.returncode, 0, result.stderr)
        operations = [row for row in calls if row["args"][0] == "compose" and "run" in row["args"]]
        self.assertEqual(len(operations), 1)
        self.assertIn("discover-sites", operations[0]["args"])
        self.assertIn("--qualify-default-root", operations[0]["args"])
        self.assertIn("Name matches Default: True", result.stdout)
        self.assertNotIn("[y/N]", result.stderr)
        self.assertIn("Site-create parent acceptance remain unverified", result.stdout)
        self.assertNotIn("private-native-id", result.stdout + result.stderr)
        report = self.reports / "cc-destination-synthetic" / "root-qualification.json"
        self.assertNotIn("private-native-id", report.read_text())
        self.assertFalse((self.reports / "cc-destination-synthetic" / "organization-sites.json").exists())

    def test_root_flag_rejects_other_menu_roles_before_credentials_or_docker(self):
        for selection in ("1", "3"):
            result, calls = self.launch(selection, arguments=("--qualify-default-root",))
            self.assertEqual(result.returncode, 2)
            self.assertIn("requires menu choice 2", result.stderr)
            self.assertEqual(calls, [])

    def test_root_flag_preserves_tls_consent_and_origin_scope_on_retry(self):
        result, calls = self.launch(
            mode="certificate-failure", arguments=("--qualify-default-root",),
            inputs=f"2\ncontroller.invalid\n{USERNAME}\n{SECRET}\ny\n",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        operations = [row for row in calls if row["args"][0] == "compose" and "run" in row["args"]]
        self.assertEqual(len(operations), 2)
        self.assertTrue(all("--qualify-default-root" in row["args"] for row in operations))
        self.assertEqual([row["env"]["CCV_DESTINATION_TLS_VERIFY"] for row in operations], ["true", "false"])
        self.assertEqual(operations[0]["env"]["CCV_DESTINATION_URL"], operations[1]["env"]["CCV_DESTINATION_URL"])
        self.assertEqual(result.stderr.count("Continue without certificate verification for this session only?"), 1)
        report = json.loads((self.reports / "cc-destination-synthetic" / "root-qualification.json").read_text())
        self.assertEqual(report["tls"], {"verify": False, "exception_scope": "selected_origin_current_execution"})

    def test_root_flag_decline_and_production_lock_prevent_insecure_retry(self):
        result, calls = self.launch(
            mode="certificate-failure", arguments=("--qualify-default-root",),
            inputs=f"2\ncontroller.invalid\n{USERNAME}\n{SECRET}\n\n",
        )
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(len(self.operation_calls(calls)), 1)
        self.assertFalse(any("approve-exception" in row["args"] for row in calls))
        (self.directory / "calls.jsonl").unlink()
        self.production_lock()
        result, calls = self.launch(mode="certificate-failure", arguments=("--qualify-default-root",))
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertNotIn("[y/N]", result.stderr)
        self.assertEqual(len(self.operation_calls(calls)), 1)

    def test_root_summary_rejects_server_values_disguised_as_types_without_printing_them(self):
        module = importlib.import_module("cc_vision_import.destination_discovery")
        report = {
            "operation": "destination-discovery", "discovery_mode": "default-root",
            "migration_ready": False, "configuration_writes_authorized": False,
            "import_file_compatible": False,
            **module.project_default_root({"name": "Default", "ormID": SECRET}),
        }
        report["field_assessments"]["ormID"]["python_type"] = SECRET
        stream = io.StringIO()
        with redirect_stdout(stream), self.assertRaises(self.helper.SetupError):
            self.helper.summary(report, "2", 0, str(self.reports), "")
        self.assertNotIn(SECRET, stream.getvalue())

    def test_source_and_discovery_route_to_existing_roles_with_private_stdin_credentials(self):
        for selection, profile, service, operation in (
            ("1", "source", "ccv-source", "backup"),
            ("2", "destination-discovery", "ccv-destination-discovery", "discover-sites"),
        ):
            result, calls = self.launch(selection)
            self.assertEqual(result.returncode, 0, result.stderr)
            command = next(call for call in reversed(calls) if call["args"][0] == "compose" and "run" in call["args"])
            self.assertIn(profile, command["args"])
            self.assertIn(service, command["args"])
            self.assertIn(operation, command["args"])
            self.assertNotIn("--user", command["args"])
            self.assertNotIn("--network", command["args"])
            if selection == "1":
                self.assertEqual(command["env"]["CCV_TLS_VERIFY"], "true")
                artifact = self.backups / self.source["run_directory"] / "summary.json"
                self.assertEqual(json.loads(artifact.read_text()), self.source)
            else:
                artifact = self.reports / "cc-destination-synthetic" / "organization-sites.json"
            self.assertNotIn(SECRET, artifact.read_text())
            self.assertNotIn(USERNAME, artifact.read_text())
            self.assertTrue(all(
                call["args"][call["args"].index("--network") + 1] == "none"
                and call["args"][call["args"].index("--user") + 1] == "10001:10001"
                and call["args"][call["args"].index("--pull") + 1] == "never"
                for call in calls if call["args"][0] == "run"
            ))
            self.assertFalse(Path((self.directory / "credential-path.txt").read_text()).exists())
            (self.directory / "calls.jsonl").unlink()

    def test_offline_selection_never_collects_credentials_and_reports_blocked_distinctly(self):
        result, calls = self.launch(inputs="3\n1\n")
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn("Assessment completed; migration BLOCKED, not an application failure", result.stdout)
        self.assertEqual(len(list(self.reports.glob("*-sites.json"))), 1)
        self.assertNotIn(SECRET, next(self.reports.glob("*-sites.json")).read_text())
        self.assertFalse(any("credentials" in call["args"] for call in calls))
        command = next(call["args"] for call in calls if call["args"][0] == "compose" and "run" in call["args"])
        self.assertIn("ccv-destination", command)
        self.assertIn("--site-readiness", command)

    def test_failures_bad_output_and_interrupt_cleanup_without_secret_output(self):
        for mode, expected in (("failure", 1), ("bad-output", 3), ("interrupt", 143), ("interrupt-int", 130)):
            result, calls = self.launch(mode=mode)
            self.assertEqual(result.returncode, expected, result.stderr)
            self.assertFalse(Path((self.directory / "credential-path.txt").read_text()).exists())
            if mode.startswith("interrupt"):
                self.assertTrue(any(call["args"][:2] == ["container", "rm"] for call in calls))
            (self.directory / "calls.jsonl").unlink()

    def test_missing_compose_image_tls_and_output_directory_are_actionable(self):
        for mode in ("compose-missing", "image-missing", "tls-invalid"):
            result, calls = self.launch(mode=mode)
            self.assertEqual(result.returncode, 2, result.stderr)
            self.assertFalse(any("credentials" in call["args"] for call in calls))
            (self.directory / "calls.jsonl").unlink()
        self.reports.rmdir()
        result, calls = self.launch()
        self.assertEqual(result.returncode, 2)
        self.assertIn("runtime directory is missing", result.stderr)

    def test_missing_docker_and_incomplete_or_invalid_backup_selection(self):
        (self.bin / "docker").unlink()
        result, calls = self.launch()
        self.assertEqual(result.returncode, 2)
        self.assertIn("Docker is missing", result.stderr)
        (self.bin / "docker").write_text('#!/usr/bin/env bash\nexport MOCK_LAUNCHER_PID="$PPID"\nexec "$MOCK_PYTHON" "$MOCK_SCRIPT" "$@"\n', newline="\n")
        (self.bin / "docker").chmod(0o755)
        result, calls = self.launch(inputs="3\n2\n")
        self.assertEqual(result.returncode, 2)
        (self.incoming / "vision-backup-synthetic" / "summary.json").unlink()
        result, calls = self.launch(inputs="3\n1\n")
        self.assertEqual(result.returncode, 2)
        self.assertIn("Backup is missing/incomplete", result.stderr)

    def test_sudo_is_authorized_before_credentials_and_not_needed_for_cleanup_or_offline(self):
        result, calls = self.launch(uid="2000")
        self.assertEqual(result.returncode, 0, result.stderr)
        commands = (self.directory / "sudo.txt").read_text().splitlines()
        self.assertEqual(commands[0], "-v")
        self.assertEqual(len(commands), 3)
        self.assertTrue(commands[1].startswith("-n chgrp 10001 "))
        self.assertTrue(commands[2].startswith("-n chown 10001:10001 "))
        self.assertNotIn(str(self.admin), "\n".join(commands))
        (self.directory / "sudo.txt").unlink()
        result, calls = self.launch(inputs="3\n1\n", uid="2000")
        self.assertEqual(result.returncode, 1)
        self.assertFalse((self.directory / "sudo.txt").exists())
        result, calls = self.launch(mode="sudo-denied", uid="2000")
        self.assertEqual(result.returncode, 2)
        self.assertFalse(any("credentials" in call["args"] for call in calls[-4:]))

    def test_cleanup_failure_is_not_reported_as_success_and_names_only_its_private_directory(self):
        result, calls = self.launch(mode="cleanup-failure")
        self.assertEqual(result.returncode, 3, result.stderr)
        self.assertIn("temporary-file cleanup failed", result.stderr)
        folders = list(self.runtime.iterdir())
        self.assertEqual(len(folders), 1)
        self.assertNotIn(str(self.admin), result.stderr)
        for name in ("credentials.json", "ca.pem", "tls-exception.json", "stdout", "stderr"):
            (folders[0] / name).unlink()
        folders[0].rmdir()

    def test_native_host_validation_rejects_injection_and_noncanonical_numeric_hosts(self):
        for value, expected in (("192.0.2.5", "https://192.0.2.5"), ("cc-host.example", "https://cc-host.example"), ("2001:db8::1", "https://[2001:db8::1]"), ("[2001:db8::1]", "https://[2001:db8::1]")):
            self.assertEqual(self.helper.origin(value), expected)
        for value in ("https://host", "host:443", "user@host", "host/path", "127.1", "999.1.1.1", "192.168.001.1", "host;echo", "host\n", "-host", "fe80::1%eth0", "host_1"):
            with self.assertRaises(self.helper.SetupError):
                self.helper.origin(value)

    def test_private_file_checks_exact_permissions_and_identity_and_required_ca_fails_closed(self):
        filename = self.directory / "ca.pem"
        filename.write_text("not a certificate")
        info = Mock(st_mode=stat.S_IFREG | 0o600, st_uid=10001, st_gid=10001)
        with patch.object(Path, "lstat", return_value=info):
            self.helper._private_file(filename)
            for field, value in (("st_mode", stat.S_IFREG | 0o644), ("st_uid", 0), ("st_gid", 0)):
                previous = getattr(info, field)
                setattr(info, field, value)
                with self.assertRaises(self.helper.SetupError):
                    self.helper._private_file(filename)
                setattr(info, field, previous)
        with patch.object(self.helper, "_private_file"):
            with self.assertRaises(self.helper.SetupError):
                self.helper.prepare("cc.invalid", "2", self.directory, self.admin, "missing.pem")
            (self.admin / "cc-ca.pem").write_text("INVALID-CA")
            with self.assertRaises(ssl.SSLError):
                self.helper.prepare("cc.invalid", "2", self.directory, self.admin)
            context = Mock()
            context.get_ca_certs.return_value = [b"public-cert"]
            with patch.object(self.helper.ssl, "create_default_context", return_value=context):
                self.helper.prepare("cc.invalid", "2", self.directory, self.admin)
            self.assertIn("BEGIN CERTIFICATE", filename.read_text())
            self.assertNotIn("INVALID-CA", filename.read_text())

    def production_lock(self):
        path = self.directory / "compose.json"
        config = json.loads(path.read_text())
        for name in ("ccv-source", "ccv-destination-discovery"):
            config["services"][name]["environment"]["CCV_ALLOW_INSECURE_TLS_EXCEPTION"] = "false"
        path.write_text(json.dumps(config))

    def operation_calls(self, calls):
        return [call for call in calls if call["args"][0] == "compose" and "run" in call["args"]]

    def test_trusted_certificate_in_lab_does_not_prompt_or_create_exception(self):
        (self.admin / "tls-policy.json").write_text('{"verify":false}')
        result, calls = self.launch()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("[y/N]", result.stderr)
        self.assertNotIn("approve-exception", json.dumps(calls))
        self.assertEqual(len(self.operation_calls(calls)), 1)
        self.assertEqual((self.admin / "tls-policy.json").read_text(), '{"verify":false}')

    def test_production_certificate_failure_prohibits_prompt_and_retry(self):
        self.production_lock()
        for selection in ("1", "2"):
            result, calls = self.launch(selection, mode="certificate-failure")
            self.assertEqual(result.returncode, 1, result.stderr)
            self.assertIn("prohibits insecure exceptions", result.stderr)
            self.assertNotIn("[y/N]", result.stderr)
            self.assertEqual(len(self.operation_calls(calls)), 1)
            self.assertFalse(any("approve-exception" in row["args"] for row in calls))
            (self.directory / "calls.jsonl").unlink()

    def test_lab_decline_default_no_and_eof_stop_without_unverified_authentication(self):
        for answer in ("n\n", "\n", ""):
            result, calls = self.launch(mode="certificate-failure", inputs=f"2\ncontroller.invalid\n{USERNAME}\n{SECRET}\n{answer}")
            self.assertEqual(result.returncode, 1, result.stderr)
            self.assertIn("TLS exception declined", result.stderr)
            self.assertIn("impersonate", result.stderr)
            self.assertIn("intercept credentials", result.stderr)
            self.assertEqual(len(self.operation_calls(calls)), 1)
            self.assertFalse(any("approve-exception" in row["args"] for row in calls))
            (self.directory / "calls.jsonl").unlink()

    def test_lab_approval_retries_once_same_origin_after_approval_without_persistence(self):
        for selection, variable, address in (
            ("1", "CCV_TLS_VERIFY", "CCV_VISION_URL"),
            ("2", "CCV_DESTINATION_TLS_VERIFY", "CCV_DESTINATION_URL"),
        ):
            result, calls = self.launch(selection, mode="certificate-failure", inputs=f"{selection}\ncontroller.invalid\n{USERNAME}\n{SECRET}\ny\n")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stderr.count("[y/N]"), 1)
            self.assertIn("Untrusted/self-signed certificate. Continue without certificate verification for this session only? [y/N]", result.stderr)
            operations = self.operation_calls(calls)
            self.assertEqual(len(operations), 2)
            self.assertEqual([row["env"][variable] for row in operations], ["true", "false"])
            self.assertEqual([row["env"][address] for row in operations], ["https://controller.invalid"] * 2)
            approved = next(i for i, row in enumerate(calls) if "approve-exception" in row["args"])
            retried = next(i for i, row in enumerate(calls) if row is operations[1])
            self.assertLess(approved, retried)
            self.assertEqual(sum("credentials" in row["args"] for row in calls), 1)
            artifact = self.backups / "vision-backup-synthetic" / "summary.json" if selection == "1" else self.reports / "cc-destination-synthetic" / "organization-sites.json"
            self.assertEqual(json.loads(artifact.read_text())["tls"], {
                "verify": False, "exception_scope": "selected_origin_current_execution",
            })
            self.assertFalse((self.source_admin / "tls-exception.json").exists())
            self.assertFalse((self.admin / "tls-exception.json").exists())
            (self.directory / "calls.jsonl").unlink()
            result, calls = self.launch(selection, inputs=f"{selection}\nanother.invalid\n{USERNAME}\n{SECRET}\n")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(self.operation_calls(calls)[0]["env"][variable], "true")
            self.assertFalse(any("approve-exception" in row["args"] for row in calls))
            (self.directory / "calls.jsonl").unlink()

    def test_certificate_failure_after_authentication_never_restarts_operation(self):
        result, calls = self.launch(mode="certificate-after-auth")
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertNotIn("[y/N]", result.stderr)
        self.assertEqual(len(self.operation_calls(calls)), 1)

    def test_approved_retry_failure_and_interruption_cleanup_without_second_prompt(self):
        for mode, expected in (("certificate-retry-failure", 1), ("certificate-interrupt", 143)):
            result, calls = self.launch(mode=mode, inputs=f"2\ncontroller.invalid\n{USERNAME}\n{SECRET}\ny\n")
            self.assertEqual(result.returncode, expected, result.stderr)
            self.assertEqual(result.stderr.count("[y/N]"), 1)
            self.assertEqual(len(self.operation_calls(calls)), 2)
            self.assertFalse(Path((self.directory / "credential-path.txt").read_text()).exists())
            (self.directory / "calls.jsonl").unlink()

    def test_unsafe_compose_and_success_shaped_readiness_are_rejected(self):
            compose = json.loads((self.directory / "compose.json").read_text())
            service = compose["services"]["ccv-destination"]
            service["network_mode"] = "bridge"
            with self.assertRaises(self.helper.SetupError):
                self.helper.settings(compose, "3")
            report = json.loads((self.directory / "readiness.json").read_text())
            with redirect_stdout(io.StringIO()), self.assertRaises(self.helper.SetupError):
                self.helper.summary(report, "3", 0, str(self.reports), "report.json")
            discovery = json.loads((self.directory / "discovery.json").read_text())
            discovery["counts"][SECRET] = 1
            output = io.StringIO()
            with redirect_stdout(output), self.assertRaises(self.helper.SetupError):
                self.helper.summary(discovery, "2", 0, str(self.reports), "")
            self.assertNotIn(SECRET, output.getvalue())
            source = {**self.source, "overall_status": "partial_collection"}
            with redirect_stdout(io.StringIO()), self.assertRaises(self.helper.SetupError):
                self.helper.summary(source, "1", 0, str(self.backups), "")
