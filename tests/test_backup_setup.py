import importlib
import io
import json
import os
import stat
import sys
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import Mock, patch

from offline_support import OfflineTestCase


class BackupSetupTests(OfflineTestCase):
    def setUp(self):
        super().setUp()
        self.setup = importlib.import_module("cc_vision_import.backup_setup")
        self.stack.enter_context(patch.object(sys, "platform", "linux"))
        self.stack.enter_context(patch.object(os, "geteuid", return_value=0, create=True))
        self.stack.enter_context(patch.object(os, "getegid", return_value=0, create=True))
        self.stack.enter_context(patch.object(os, "chown", create=True))
        self.stack.enter_context(patch.object(self.setup.shutil, "which", return_value="/mock/docker"))
        self.config = self.directory / "backup.json"
        self.output = self.directory / "backups"
        self.payload = {
            "source": {
                "role": "source", "name": "test-vision", "product": "vision",
                "version": "5.4.9", "base_url": "https://vision.invalid",
            },
            "output_directory": str(self.output),
        }
        self.credentials = {"username": "private-user-marker", "password": "private-password-marker"}
        self.read_credentials = self.setup._read_credentials
        self.stack.enter_context(patch.object(self.setup, "_read_credentials", return_value=self.credentials))
        self.stack.enter_context(patch.dict(os.environ, {}, clear=False))
        os.environ.pop("CC_VISION_IMAGE", None)

    def test_host_import_annotations_are_deferred_for_python38(self):
        json_module = importlib.import_module("cc_vision_import._json")
        policy = importlib.import_module("cc_vision_import.backup_policy")
        self.assertIsInstance(json_module._json_object.__annotations__["pairs"], str)
        self.assertIsInstance(policy.backup_domains.__annotations__["data"], str)
        self.assertEqual(json_module.load_json('{"valid": [true, null]}'), {"valid": [True, None]})
        with self.assertRaises(ValueError):
            json_module.load_json('{"duplicate": 1, "duplicate": 2}')
        with self.assertRaises(ValueError):
            json_module.load_json('{"invalid": NaN}')

    def test_help_exits_before_platform_docker_or_credentials_checks(self):
        stdout = io.StringIO()
        with patch.object(sys, "platform", "win32"), redirect_stdout(stdout):
            with patch.object(self.setup.subprocess, "run") as docker:
                with self.assertRaises(SystemExit) as result:
                    self.setup.main(["--help"])
        self.assertEqual(result.exception.code, 0)
        self.assertIn("--non-interactive", stdout.getvalue())
        docker.assert_not_called()
        self.setup._read_credentials.assert_not_called()

    def invoke(self, arguments, inputs=(), run_failure=False):
        self.config.write_text(json.dumps(self.payload), encoding="utf-8")
        stdout, stderr = io.StringIO(), io.StringIO()
        snapshots = []
        credential_paths = []

        def docker(command, **kwargs):
            if "run" in command:
                mount = next(value for value in command if "target=/run/config/profile.json" in value)
                filename = mount.split("source=", 1)[1].split(",target=", 1)[0]
                snapshots.append(json.loads(Path(filename).read_text()))
                secret_mount = next(value for value in command if "target=/run/secrets/credentials.json" in value)
                secret_file = secret_mount.split("source=", 1)[1].split(",target=", 1)[0]
                self.assertEqual(json.loads(Path(secret_file).read_text()), self.credentials)
                credential_paths.append(secret_file)
                if run_failure == "cancel":
                    raise KeyboardInterrupt
                if run_failure:
                    raise OSError("Mock Docker launch failure")
            return Mock(returncode=0, stderr="")

        with (
            patch.object(self.setup.subprocess, "run", side_effect=docker) as runner,
            patch.object(sys.stdin, "isatty", return_value=True),
            patch("builtins.input", side_effect=inputs) as prompts,
            patch.object(self.setup.getpass, "getpass", return_value=self.credentials["password"]),
            redirect_stdout(stdout), redirect_stderr(stderr),
        ):
            result = self.setup.main(arguments)
        self.assertTrue(all(not Path(filename).exists() for filename in credential_paths))
        for text in (stdout.getvalue(), stderr.getvalue(), json.dumps(snapshots)):
            for variant in ("AMS-alerts", "AMS_alerts", "AMS Alerts", "AMSAlert", "AMSAlerts"):
                self.assertNotIn(variant.casefold(), text.casefold())
        return result, runner, prompts, snapshots, stdout.getvalue(), stderr.getvalue()

    def test_interactive_default_tls_save_and_cancel_never_runs_docker(self):
        saved = self.directory / "saved.json"
        result, runner, prompts, snapshots, stdout, stderr = self.invoke(
            [], ["1", "192.0.2.1", self.credentials["username"], "", str(self.output), "y", str(saved), "n"],
        )
        self.assertEqual(result, 0)
        runner.assert_not_called()
        data = json.loads(saved.read_text())
        self.assertEqual(data["tls"], {"verify": True})
        self.assertEqual(data["controller_objects"], {"discovery": True})
        self.assertNotIn("private-user-marker", json.dumps(data))
        self.assertNotIn("private-password-marker", json.dumps(data))
        self.assertIn("Verify HTTPS certificate? [Y/n]: ", [call.args[0] for call in prompts.call_args_list])
        self.assertFalse(any("CA" in call.args[0] for call in prompts.call_args_list))
        self.assertIn("Cancelled", stdout)
        self.assertEqual(stderr, "")

    def test_json_unattended_uses_private_credentials_nonroot_and_cleans_runtime(self):
        result, runner, prompts, snapshots, stdout, stderr = self.invoke([
            "--config", str(self.config), "--non-interactive", "--credentials-file", "private.json",
        ])
        self.assertEqual(result, 0)
        prompts.assert_not_called()
        self.assertEqual(len(snapshots), 1)
        self.assertEqual(snapshots[0]["tls"], {"verify": True})
        self.assertEqual(snapshots[0]["output_directory"], "/data")
        run = runner.call_args_list[-1]
        self.assertIn("10001:10001", run.args[0])
        self.assertIn("--credentials-file", run.args[0])
        self.assertNotIn("private-password-marker", json.dumps(run.args[0]) + json.dumps(snapshots) + stdout + stderr)
        mount = next(value for value in run.args[0] if "target=/run/config/profile.json" in value)
        filename = mount.split("source=", 1)[1].split(",target=", 1)[0]
        self.assertFalse(Path(filename).exists())

    def test_json_tls_false_needs_no_extra_flag_and_warns_once(self):
        self.payload["tls"] = {"verify": False}
        arguments = ["--config", str(self.config), "--non-interactive", "--credentials-file", "private.json"]
        result, runner, _, snapshots, _, stderr = self.invoke(arguments)
        self.assertEqual(result, 0)
        self.assertEqual(stderr, self.setup.TLS_WARNING + "\n")
        self.assertEqual(snapshots[0]["tls"], {"verify": False})
        self.assertEqual(runner.call_args_list[-1].args[0][-1], "/run/secrets/credentials.json")

    def test_unattended_missing_credentials_and_invalid_config_fail_without_docker(self):
        result, runner, _, _, _, stderr = self.invoke(["--config", str(self.config), "--non-interactive"])
        self.assertEqual(result, 2)
        self.assertIn("--credentials-file", stderr)
        runner.assert_not_called()
        for value in ("false", 0, None):
            self.payload["tls"] = {"verify": value}
            result, runner, _, _, _, stderr = self.invoke([
                "--config", str(self.config), "--non-interactive", "--credentials-file", "private.json",
            ])
            self.assertEqual(result, 2)
            runner.assert_not_called()
            self.assertIn("true or false", stderr)

    def test_menu_selection_exit_exclusion_and_failure_cleanup(self):
        result, runner, _, _, stdout, _ = self.invoke([], ["4"])
        self.assertEqual(result, 0)
        runner.assert_not_called()
        result, runner, _, snapshots, _, _ = self.invoke(
            [], ["2", "2", "192.0.2.1", self.credentials["username"], "", str(self.output), "n", "y"],
        )
        self.assertEqual(result, 0)
        self.assertEqual(snapshots[0]["domains"], ["device-access"])
        result, runner, _, snapshots, _, _ = self.invoke(
            [], ["3", str(self.config), self.credentials["username"], "y"],
        )
        self.assertEqual(result, 0)
        self.assertEqual(snapshots[0]["controller_objects"], {"discovery": True})
        self.assertEqual(snapshots[0]["tls"], {"verify": True})
        arguments = ["--config", str(self.config), "--non-interactive", "--credentials-file", "private.json"]
        result, runner, _, _, _, _ = self.invoke(arguments, run_failure=True)
        self.assertEqual(result, 3)
        result, runner, _, _, _, _ = self.invoke(arguments, run_failure="cancel")
        self.assertEqual(result, 130)
        for name in ("AMS Alerts", "AMS_alerts", "AMSAlert", "scheduler"):
            self.payload["backup_mode"] = "selected"
            self.payload["domains"] = [name]
            result, runner, _, _, _, stderr = self.invoke(arguments)
            self.assertEqual(result, 2)
            runner.assert_not_called()

            self.assertIn("Setup failed", stderr)
        self.payload["domains"] = ["controller-objects"]
        self.payload["output_directory"] = str(self.setup.REPOSITORY / "exports")
        result, runner, _, _, _, _ = self.invoke(arguments)
        self.assertEqual(result, 2)
        runner.assert_not_called()

    def test_selected_image_is_inspected_and_executed_without_fallback(self):
        arguments = ["--config", str(self.config), "--non-interactive", "--credentials-file", "private.json"]
        with patch.dict(os.environ, {"CC_VISION_IMAGE": "cc-vision-master:0.4"}):
            result, runner, _, _, _, _ = self.invoke(arguments)
        self.assertEqual(result, 0)
        self.assertEqual(runner.call_args_list[0].args[0], ["docker", "image", "inspect", "cc-vision-master:0.4"])
        self.assertIn("cc-vision-master:0.4", runner.call_args_list[1].args[0])
        with patch.dict(os.environ, {"CC_VISION_IMAGE": "cc-vision-master:missing"}):
            with patch.object(self.setup.subprocess, "run", return_value=Mock(returncode=1)):
                with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()) as stderr:
                    result = self.setup.main(arguments)
        self.assertEqual(result, 2)
        self.assertIn("cc-vision-master:missing", stderr.getvalue())
        for value in ("", "--privileged", "invalid image", "https://registry.invalid/image"):
            with patch.dict(os.environ, {"CC_VISION_IMAGE": value}):
                result, runner, _, _, _, _ = self.invoke(arguments)
            self.assertEqual(result, 2)
            runner.assert_not_called()

    def test_interactive_tls_warning_precedes_confirmation_and_is_not_repeated(self):
        inputs = ["1", "192.0.2.1", self.credentials["username"], "n", str(self.output), "n", "y"]
        stdout, stderr = io.StringIO(), io.StringIO()

        def prompt(label):
            if label.startswith(("Backup output directory", "Start read-only")):
                self.assertEqual(stderr.getvalue(), self.setup.TLS_WARNING + "\n")
            return inputs.pop(0)

        with patch("builtins.input", side_effect=prompt), patch.object(sys.stdin, "isatty", return_value=True):
            with patch.object(self.setup.getpass, "getpass", return_value=self.credentials["password"]):
                with patch.object(self.setup.subprocess, "run", return_value=Mock(
                    returncode=0, stderr=self.setup.TLS_WARNING + "\nDocker diagnostic\n",
                )):
                    with redirect_stdout(stdout), redirect_stderr(stderr):
                        result = self.setup.main([])
        self.assertEqual(result, 0)
        self.assertEqual(stderr.getvalue(), self.setup.TLS_WARNING + "\nDocker diagnostic\n")

    def test_credentials_permission_checks_reject_public_and_changed_files(self):
        path = self.directory / "private.json"
        path.write_text(json.dumps(self.credentials), encoding="utf-8")
        private = Mock(st_mode=stat.S_IFREG | 0o600)
        public = Mock(st_mode=stat.S_IFREG | 0o644)
        with patch.object(Path, "stat", return_value=public):
            with self.assertRaises(self.setup.SetupError):
                self.read_credentials(path)
        with patch.object(Path, "stat", return_value=private):
            with patch.object(os, "fstat", return_value=public):
                with self.assertRaises(self.setup.SetupError):
                    self.read_credentials(path)
            with patch.object(os, "fstat", return_value=private):
                self.assertEqual(self.read_credentials(path), self.credentials)
