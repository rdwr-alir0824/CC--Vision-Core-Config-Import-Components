import importlib
import io
import json
import os
import shutil
import subprocess
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

from offline_support import OfflineTestCase


ROOT = Path(__file__).resolve().parents[1]


class ComposeDeploymentTests(OfflineTestCase):
    def setUp(self):
        super().setUp()
        self.module = importlib.import_module("cc_vision_import.compose_entrypoint")
        self.environment = {
            "CCV_VISION_URL": "https://vision.example.invalid",
            "CCV_DESTINATION_URL": "https://destination.example.invalid",
            "CCV_DESTINATION_VERSION": "10.7.0",
        }

    def test_compose_separates_roles_mounts_network_and_privileges(self):
        config = json.loads((ROOT / "compose.yaml").read_text())
        services = config["services"]
        source, destination = services["ccv-source"], services["ccv-destination"]
        self.assertEqual(source["build"], destination["build"])
        self.assertEqual(source["image"], destination["image"])
        self.assertEqual(source["command"], ["--help"])
        self.assertEqual(destination["command"], ["--operation", "operations"])
        self.assertEqual(destination["network_mode"], "none")
        mounts = {}
        for role, service in (("source", source), ("destination", destination)):
            self.assertEqual(service["profiles"], [role])
            self.assertEqual(service["entrypoint"], ["python", "-m", "cc_vision_import.compose_entrypoint", role])
            self.assertEqual(service["user"], "10001:10001")
            self.assertTrue(service["read_only"])
            self.assertEqual(service["cap_drop"], ["ALL"])
            self.assertEqual(service["security_opt"], ["no-new-privileges:true"])
            self.assertEqual(service["restart"], "no")
            self.assertNotIn("privileged", service)
            self.assertNotIn("ports", service)
            self.assertNotEqual(service.get("network_mode"), "host")
            for mount in service["volumes"]:
                self.assertEqual(mount["type"], "bind")
                self.assertFalse(mount["bind"]["create_host_path"])
                self.assertNotIn("docker.sock", mount["source"])
                mounts[mount["target"]] = mount
        self.assertEqual(set(mounts), {"/backups", "/run/config", "/run/secrets", "/incoming", "/reports"})
        for target in ("/run/config", "/run/secrets", "/incoming"):
            self.assertTrue(mounts[target]["read_only"])
        for target in ("/backups", "/reports"):
            self.assertFalse(mounts[target].get("read_only", False))
        self.assertEqual(len({mount["source"] for mount in mounts.values()}), 5)
        dockerfile = (ROOT / "Dockerfile").read_text()
        self.assertIn("COPY src/ ./src/", dockerfile)
        self.assertIn('ENTRYPOINT ["python", "/app/master.py"]', dockerfile)

    def test_backup_delegates_full_supported_profile_without_loading_credentials_or_starting_docker(self):
        profiles = []

        def capture(arguments):
            self.assertEqual(arguments[:2], ["--operation", "backup-vision"])
            path = Path(arguments[arguments.index("--backup-profile") + 1])
            profiles.append(path)
            payload = json.loads(path.read_text())
            self.assertEqual(payload["backup_mode"], "full-supported")
            self.assertEqual(payload["controller_objects"], {"discovery": True})
            self.assertEqual(payload["output_directory"], "/backups")
            self.assertEqual(payload["tls"], {"verify": True})
            self.assertEqual(arguments[-2:], ["--credentials-file", "/run/secrets/credentials.json"])
            profile_type = importlib.import_module("cc_vision_import.vision_backup").VisionBackupProfile
            self.assertEqual(len(profile_type.read(str(path)).domains), 6)
            self.assertNotIn("password", payload["source"])
            return 7

        with patch.dict(os.environ, self.environment, clear=True), patch.object(self.module, "master_main", side_effect=capture):
            self.assertEqual(self.module.main(["source", "backup"]), 7)
        self.assertFalse(profiles[0].exists())

    def test_preflight_validates_real_profiles_offline_and_existing_operations_pass_through(self):
        stdout = io.StringIO()
        with patch.dict(os.environ, self.environment, clear=True), redirect_stdout(stdout):
            self.assertEqual(self.module.main(["destination", "preflight"]), 0)
        report = json.loads(stdout.getvalue())
        self.assertEqual(report["operation"], "profiles")
        self.assertEqual(report["status"], "valid")
        self.assertTrue(report["offline_only"])
        self.assertFalse(report["authenticated"])
        with patch.dict(os.environ, {}, clear=True), redirect_stdout(io.StringIO()):
            self.assertEqual(self.module.main(["destination", "--operation", "operations"]), 0)
            with self.assertRaises(SystemExit) as caught:
                self.module.main(["source", "--help"])
            self.assertEqual(caught.exception.code, 0)

    def test_missing_and_invalid_environment_fails_without_exposing_values_or_dispatch(self):
        for arguments, change in (
            (["source", "backup"], {"CCV_VISION_URL": ""}),
            (["source", "backup"], {"CCV_TLS_VERIFY": "private-marker"}),
            (["destination", "preflight"], {"CCV_DESTINATION_VERSION": ""}),
            (["destination", "backup"], {}),
        ):
            stderr = io.StringIO()
            with patch.dict(os.environ, {**self.environment, **change}, clear=True), redirect_stderr(stderr):
                with patch.object(self.module, "master_main") as dispatch, self.assertRaises(SystemExit) as caught:
                    self.module.main(arguments)
                self.assertEqual(caught.exception.code, 2)
                dispatch.assert_not_called()
                self.assertNotIn("private-marker", stderr.getvalue())
        stdout = io.StringIO()
        with patch.dict(os.environ, {**self.environment, "CCV_DESTINATION_URL": "https://private-marker:private-marker@example.invalid"}, clear=True):
            with redirect_stdout(stdout):
                self.assertEqual(self.module.main(["destination", "preflight"]), 4)
        self.assertNotIn("private-marker", stdout.getvalue())

    def test_explicit_tls_settings_and_io_errors_remain_explicit(self):
        def capture(arguments):
            payload = json.loads(Path(arguments[3]).read_text())
            self.assertEqual(payload["tls"], {"verify": False})
            return 0

        policy_type = importlib.import_module("cc_vision_import.tls_policy").TLSPolicy
        with patch.dict(os.environ, {**self.environment, "CCV_TLS_VERIFY": "false"}, clear=True), patch.object(
            self.module, "read_exception", return_value=policy_type(False, True, self.environment["CCV_VISION_URL"]),
        ):
            with patch.object(self.module, "master_main", side_effect=capture):
                self.assertEqual(self.module.main(["source", "backup"]), 0)
            stdout = io.StringIO()
            with patch.object(self.module, "TemporaryDirectory", side_effect=OSError("private-marker")), redirect_stdout(stdout):
                self.assertEqual(self.module.main(["source", "backup"]), 3)
            self.assertEqual(json.loads(stdout.getvalue())["errors"], [{"code": "compose_io_error"}])
            self.assertNotIn("private-marker", stdout.getvalue())

    def test_docker_compose_configuration_when_available(self):
        if shutil.which("docker") is None:
            self.skipTest("Docker/Compose unavailable; runtime schema validation not performed.")
        version = subprocess.run(["docker", "compose", "version"], capture_output=True, text=True, check=False)
        if version.returncode:
            self.skipTest("Docker Compose plugin unavailable.")
        result = subprocess.run(
            ["docker", "compose", "--file", str(ROOT / "compose.yaml"), "--profile", "source",
             "--profile", "destination", "config", "--format", "json"],
            cwd=ROOT, capture_output=True, text=True, check=False,
        )
        self.assertEqual(result.returncode, 0, "docker compose config failed; run it locally for configuration diagnostics.")
        self.assertTrue({"ccv-source", "ccv-destination"} <= set(json.loads(result.stdout)["services"]))

    def test_single_site_routes_only_existing_discovery_with_protected_paths(self):
        for command, operation in (("site-dry-run", "single-site-dry-run"), ("site-create", "single-site-create")):
            with self.subTest(command=command):
                def inspect(arguments):
                    self.assertEqual(arguments[:2], ["--operation", operation])
                    self.assertEqual(arguments[arguments.index("--site-reference") + 1], "source:node-2")
                    payload = json.loads(Path(arguments[3]).read_text())
                    self.assertEqual(payload["destination"]["base_url"], self.environment["CCV_DESTINATION_URL"])
                    self.assertEqual(payload["tls"], {"verify": True})
                    self.assertEqual(payload["output_directory"], "/reports")
                    self.assertNotIn("password", json.dumps(payload))
                    return 0

                with patch.dict(os.environ, self.environment, clear=True), patch.object(
                    self.module, "master_main", side_effect=inspect,
                ):
                    self.assertEqual(self.module.main([
                        "discovery", command, "--input", "/incoming/backup/organization-tree/tree.json",
                        "--comparison", "/reports/comparison.json",
                        "--destination-snapshot", "/reports/snapshot.json", "--site-reference", "source:node-2",
                    ]), 0)

        with redirect_stderr(io.StringIO()), patch.object(self.module, "master_main") as dispatch:
            for role, source in (("source", "/incoming/tree.json"), ("discovery", "/incoming/../secrets/tree.json")):
                with self.assertRaises(SystemExit):
                    self.module.main([
                        role, "site-create", "--input", source, "--comparison", "/reports/comparison.json",
                        "--destination-snapshot", "/reports/snapshot.json", "--site-reference", "source:node-2",
                    ])
            dispatch.assert_not_called()

    def test_discovery_profile_is_separate_and_cannot_enable_offline_destination_networking(self):
        services = json.loads((ROOT / "compose.yaml").read_text())["services"]
        discovery = services["ccv-destination-discovery"]
        self.assertEqual(services["ccv-destination"]["network_mode"], "none")
        self.assertEqual(discovery["profiles"], ["destination-discovery"])
        self.assertEqual(discovery["command"], ["--help"])
        self.assertEqual(discovery["networks"], ["destination-discovery"])
        self.assertNotIn("depends_on", discovery)
        self.assertNotIn("ports", discovery)
        self.assertNotIn("privileged", discovery)
        self.assertNotIn("CCV_DESTINATION_VERSION", discovery["environment"])
        self.assertEqual(discovery["image"], services["ccv-destination"]["image"])
        self.assertEqual(discovery["user"], "10001:10001")
        self.assertTrue(discovery["read_only"])
        self.assertEqual(discovery["cap_drop"], ["ALL"])
        self.assertEqual(discovery["security_opt"], ["no-new-privileges:true"])
        self.assertEqual({mount["target"] for mount in discovery["volumes"]}, {"/run/secrets", "/reports", "/incoming"})
        self.assertTrue(next(m for m in discovery["volumes"] if m["target"] == "/incoming")["read_only"])
        self.assertTrue(next(m for m in discovery["volumes"] if m["target"] == "/run/secrets")["read_only"])
        captured = []

        def inspect(arguments):
            self.assertEqual(arguments[:2], ["--operation", "destination-discovery"])
            path = Path(arguments[3])
            captured.append(path)
            profile = json.loads(path.read_text())
            self.assertEqual(profile["tls"], {"verify": True})
            self.assertEqual(profile["output_directory"], "/reports")
            self.assertNotIn("version", profile["destination"])
            return 0

        with patch.dict(os.environ, {
            "CCV_DESTINATION_URL": "https://destination.example.invalid",
            "CCV_DESTINATION_VERSION": "10.10.7", "CCV_TLS_VERIFY": "false",
        }, clear=True), patch.object(self.module, "master_main", side_effect=inspect):
            self.assertEqual(self.module.main(["discovery", "discover-sites"]), 0)
        self.assertFalse(captured[0].exists())

    def test_batch_commands_reuse_discovery_role_and_forward_only_explicit_batch_options(self):
        for mode in ("dry-run", "execute", "resume", "reconcile"):
            with self.subTest(mode=mode):
                with patch.dict(os.environ, self.environment, clear=True), patch.object(
                    self.module, "master_main", return_value=0,
                ) as dispatch:
                    self.assertEqual(self.module.main([
                        "discovery", "sites-" + mode, "--input", "/incoming/backup/organization-tree/tree.json",
                        "--comparison", "/reports/comparison.json", "--destination-snapshot", "/reports/snapshot.json",
                        "--operation-delay", "0.5", "--readback-interval", "2", "--readback-attempts", "4",
                        *(["--report-format", "json"] if mode == "dry-run" else []),
                    ]), 0)
                    arguments = dispatch.call_args.args[0]
                    self.assertEqual(arguments[:2], ["--operation", "site-batch-" + mode])
                    self.assertNotIn("--site-reference", arguments)
                    self.assertEqual(arguments[arguments.index("--operation-delay") + 1], "0.5")
                    self.assertEqual(arguments[arguments.index("--readback-attempts") + 1], "4")
                    if mode == "dry-run":
                        self.assertEqual(arguments[arguments.index("--report-format") + 1], "json")
                    else:
                        self.assertNotIn("--report-format", arguments)
        with redirect_stderr(io.StringIO()), patch.object(self.module, "master_main") as dispatch:
            for role, source, extras in (
                ("source", "/incoming/tree.json", []),
                ("discovery", "/incoming/../secrets/tree.json", []),
                ("discovery", "/incoming/tree.json", ["--site-reference", "source:node-2"]),
            ):
                with self.assertRaises(SystemExit):
                    self.module.main([
                        role, "sites-execute", "--input", source, "--comparison", "/reports/comparison.json",
                        "--destination-snapshot", "/reports/snapshot.json", *extras,
                    ])
            dispatch.assert_not_called()

    def test_device_and_combined_commands_reuse_discovery_role_without_site_reference_or_timing(self):
        for command, operation in (
            ("devices-dry-run", "device-batch-dry-run"), ("devices-execute", "device-batch-execute"),
            ("devices-resume", "device-batch-resume"), ("migration-dry-run", "migration-dry-run"),
            ("migration-status", "migration-status"),
        ):
            with self.subTest(command=command), patch.dict(os.environ, self.environment, clear=True), patch.object(
                self.module, "master_main", return_value=1,
            ) as dispatch:
                self.assertEqual(self.module.main([
                    "discovery", command, "--input", "/incoming/backup/organization-tree/tree.json",
                    "--comparison", "/reports/comparison.json", "--destination-snapshot", "/reports/snapshot.json",
                    "--report-format", "json",
                ]), 1)
                arguments = dispatch.call_args.args[0]
                self.assertEqual(arguments[:2], ["--operation", operation])
                self.assertNotIn("--site-reference", arguments)
                self.assertNotIn("--operation-delay", arguments)
        with redirect_stderr(io.StringIO()), patch.object(self.module, "master_main") as dispatch:
            for extra in (["--site-reference", "source:node-2"], ["--operation-delay", "1"]):
                with self.assertRaises(SystemExit):
                    self.module.main([
                        "discovery", "devices-execute", "--input", "/incoming/backup/organization-tree/tree.json",
                        "--comparison", "/reports/comparison.json", "--destination-snapshot", "/reports/snapshot.json",
                        *extra,
                    ])
            dispatch.assert_not_called()

    def test_root_flag_is_forwarded_only_by_discovery_shortcut(self):
        with patch.dict(os.environ, {"CCV_DESTINATION_URL": "https://destination.invalid"}, clear=True):
            with patch.object(self.module, "master_main", return_value=0) as master:
                self.assertEqual(self.module.main(["discovery", "discover-sites", "--qualify-default-root"]), 0)
                self.assertIn("--qualify-default-root", master.call_args.args[0])
            with redirect_stderr(io.StringIO()):
                for arguments in (
                    ["source", "backup", "--qualify-default-root"],
                    ["destination", "preflight", "--qualify-default-root"],
                    ["discovery", "--qualify-default-root"],
                ):
                    with self.assertRaises(SystemExit) as caught:
                        self.module.main(arguments)
                    self.assertEqual(caught.exception.code, 2)
