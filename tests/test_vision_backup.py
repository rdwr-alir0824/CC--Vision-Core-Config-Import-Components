import importlib
import io
import json
import os
import runpy
import ssl
import sys
import time
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import Mock, patch

from offline_support import OfflineTestCase
from test_http_backend import MemoryConnection, MemoryResponse


class VisionBackupTests(OfflineTestCase):
    def setUp(self):
        super().setUp()
        self.cli = importlib.import_module("cc_vision_import.master_cli")
        self.backup = importlib.import_module("cc_vision_import.vision_backup")
        self.http = importlib.import_module("cc_vision_import.http_backend")
        self.transport = importlib.import_module("cc_vision_import.transport")
        self.profile_path = self.directory / "profile.json"
        self.credentials = self.directory / "credentials.json"
        self.output = self.directory / "output"
        self.output.mkdir()
        self.credentials.write_text(json.dumps({
            "username": "synthetic-user-marker", "password": "synthetic-password-marker",
        }), encoding="utf-8")
        self.credentials.chmod(0o600)
        self.profile = {
            "source": {
                "role": "source", "name": "synthetic-vision", "product": "vision",
                "version": "5.4.9", "base_url": "https://vision.invalid",
            },
            "tls": {"verify": True, "trusted_ca": None},
            "domains": ["controller-objects"],
            "controller_objects": {
                "site_names": ["Default"], "site_ids": ["site-1"], "device_ips": ["192.0.2.10"],
            },
            "output_directory": str(self.output),
        }
        self.site = {"ormID": "site-1", "name": "Default", "type": "Site", "future": {"opaque": [True, None]}}
        self.device = {
            "ormID": "device-1", "name": "synthetic-device",
            "deviceSetup": {"deviceAccess": {
                "managementIp": "192.0.2.10", "cliPassword": "device-secret-marker",
                "snmpV2ReadCommunity": "community-secret-marker",
            }},
        }

    def connection(self, payload, status=200, headers=None):
        return MemoryConnection(MemoryResponse(
            status, json.dumps(payload).encode(),
            [("Content-Type", "application/json")] if headers is None else headers,
        ))

    def login(self, **overrides):
        return self.connection({"status": "ok", "jsessionid": "session-secret-marker", **overrides})

    def invoke(self, *connections, arguments=None):
        self.profile_path.write_text(json.dumps(self.profile), encoding="utf-8")
        factory = Mock(side_effect=connections)
        stdout, stderr = io.StringIO(), io.StringIO()
        if arguments is None:
            arguments = [
                "--operation", "backup-vision", "--backup-profile", str(self.profile_path),
                "--credentials-file", str(self.credentials),
            ]
        with (
            patch.object(self.http.http.client, "HTTPSConnection", factory),
            redirect_stdout(stdout), redirect_stderr(stderr),
            patch.object(sys, "argv", ["master.py", *arguments]),
        ):
            with self.assertRaises(SystemExit) as caught:
                runpy.run_path(str(Path(__file__).parent.parent / "master.py"), run_name="__main__")
            status = caught.exception.code
        self.assertEqual(stderr.getvalue(), "")
        return status, json.loads(stdout.getvalue()), factory

    def assert_secret_free(self, value):
        serialized = json.dumps(value)
        for marker in (
            "synthetic-user-marker", "synthetic-password-marker", "session-secret-marker",
            "device-secret-marker", "community-secret-marker",
        ):
            self.assertNotIn(marker, serialized)

    def test_explicit_backup_uses_documented_cookie_gets_and_preserves_redacted_objects(self):
        connections = [self.login(), self.connection(self.site), self.connection(self.site), self.connection(self.device)]
        status, report, factory = self.invoke(*connections)
        self.assertEqual(status, 0)
        self.assertEqual(report["collected_objects"], 3)
        self.assertFalse(report["scope"]["complete_configuration_backup"])
        self.assertFalse(report["scope"]["complete_inventory"])
        self.assertFalse(report["offline_only"])
        self.assertFalse(report["configuration_writes_authorized"])
        self.assertEqual(factory.call_count, 4)
        expected = [
            ("POST", "/mgmt/system/user/login"),
            ("GET", "/mgmt/system/config/tree/site/byname/Default"),
            ("GET", "/mgmt/system/config/tree/site/byid/site-1"),
            ("GET", "/mgmt/system/config/tree/device/byip/192.0.2.10"),
        ]
        for connection, pair in zip(connections, expected, strict=True):
            request = connection.requests[0]
            self.assertEqual(request[:2], pair)
            if pair[0] == "GET":
                self.assertIsNone(request[2])
                self.assertIn("JSESSIONID=session-secret-marker", request[3]["Cookie"])
            self.assertEqual(connection.close_calls, 1)
        for call in factory.call_args_list:
            context = call.kwargs["context"]
            self.assertTrue(context.check_hostname)
            self.assertEqual(context.verify_mode, importlib.import_module("ssl").CERT_REQUIRED)
            self.assertLessEqual(call.kwargs["timeout"], 10)
        directory = self.output / report["run_directory"]
        device = json.loads((directory / "device-by-ip-003.json").read_text())
        self.assertIsNone(device["objects"][0]["deviceSetup"]["deviceAccess"]["cliPassword"])
        self.assertEqual(device["redacted_fields"], 2)
        site = json.loads((directory / "site-by-name-001.json").read_text())
        self.assertEqual(site["objects"][0]["future"], self.site["future"])
        self.assertEqual(site["evidence"]["pdf_pages"], [141])
        self.assert_secret_free([report, device, site, json.loads((directory / "summary.json").read_text())])

    def test_failed_target_and_unsupported_domain_remain_explicitly_incomplete(self):
        self.profile["domains"].append("scheduler")
        status, report, factory = self.invoke(
            self.login(), self.connection(self.site), self.connection({"status": "error", "message": "device-secret-marker"}),
            self.connection(self.device),
        )
        self.assertEqual(status, 1)
        self.assertEqual(report["collected_objects"], 2)
        self.assertEqual(report["failed_targets"], 1)
        self.assertEqual(report["skipped_domains"], [{"domain": "scheduler", "reason": "unsupported_domain"}])
        self.assertEqual(factory.call_count, 4)
        self.assertEqual(len(list((self.output / report["run_directory"]).glob("site-by-id-*.json"))), 0)
        self.assert_secret_free(report)

    def test_login_failure_or_missing_session_id_never_dispatches_reads(self):
        for payload, status_code in (
            ({"status": "error", "message": "synthetic-password-marker"}, 401),
            ({"status": "ok"}, 200),
            ({"status": "ok", "jsessionid": "bad;Cookie=injection"}, 200),
        ):
            with self.subTest(payload=payload):
                connection = self.connection(payload, status_code)
                status, report, factory = self.invoke(connection)
                self.assertEqual(status, 1)
                self.assertFalse(report["authenticated"])
                self.assertTrue(report["failure_codes"])
                self.assertEqual(factory.call_count, 1)
                self.assertEqual(report["collected_objects"], 0)
                self.assert_secret_free(report)

    def test_authentication_expiry_skips_remaining_targets_without_renewal(self):
        status, report, factory = self.invoke(
            self.login(), self.connection({"status": "error"}, 401),
        )
        self.assertEqual(status, 1)
        self.assertEqual(factory.call_count, 2)
        self.assertEqual([entry["status"] for entry in report["results"]], ["failed", "skipped", "skipped"])
        self.assertEqual(report["uncollected_targets"], 3)

    def test_invalid_profile_or_missing_output_fails_before_connection(self):
        for field, value in (
            ("version", "5.4.8"), ("product", "cyber-controller"),
            ("verify", False), ("trusted_ca", str(self.directory / "missing.pem")),
            ("output_directory", str(self.directory / "absent")),
            ("device_ips", ["not-an-ip"]), ("site_names", []),
        ):
            with self.subTest(field=field):
                original = json.loads(json.dumps(self.profile))
                if field in ("version", "product"):
                    self.profile["source"][field] = value
                elif field in ("verify", "trusted_ca"):
                    self.profile["tls"][field] = value
                elif field == "output_directory":
                    self.profile[field] = value
                else:
                    self.profile["controller_objects"] = {"site_names": [], "site_ids": [], "device_ips": []}
                    self.profile["controller_objects"][field] = value
                status, report, factory = self.invoke()
                self.assertIn(status, (3, 4))
                factory.assert_not_called()
                self.assertEqual(report["status"], "error")
                self.assertFalse(report["offline_only"])
                self.profile = original

    def test_help_operations_and_unselected_credentials_do_not_connect(self):
        for arguments in (["--help"], ["--operation", "operations"]):
            stdout = io.StringIO()
            with patch.object(self.http.http.client, "HTTPSConnection") as factory, redirect_stdout(stdout):
                try:
                    result = self.cli.main(arguments)
                except SystemExit as error:
                    result = error.code
            self.assertEqual(result, 0)
            factory.assert_not_called()
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as caught:
            self.cli.main(["--operation", "operations", "--credentials-file", str(self.credentials)])
        self.assertEqual(caught.exception.code, 2)
        status, report, factory = self.invoke(arguments=["--operation", "authenticate"])
        self.assertEqual(status, 4)
        factory.assert_not_called()
        self.assertEqual(report["errors"][0]["code"], "live_execution_disabled")

    def test_transport_default_stays_blocked_and_backup_scope_cannot_write(self):
        self.profile_path.write_text(json.dumps(self.profile), encoding="utf-8")
        profile = self.backup.VisionBackupProfile.read(str(self.profile_path))
        backend = self.backup._backend(profile)
        self.addCleanup(backend.close)
        authorization = backend._authorization
        self.assertTrue(authorization.permits(
            self.transport.HttpMethod.POST, "https://vision.invalid", "/mgmt/system/user/login",
        ))
        for method in (self.transport.HttpMethod.POST, self.transport.HttpMethod.PUT, self.transport.HttpMethod.DELETE):
            self.assertFalse(authorization.permits(method, "https://vision.invalid", "/mgmt/system/config/tree/device"))
        default = self.http.StdlibHttpBackend(
            authorization=authorization, max_response_bytes=4096,
        )
        self.addCleanup(default.close)
        request = self.transport.BackendRequest(
            self.transport.HttpMethod.POST, "https://vision.invalid/mgmt/system/user/login",
            {}, b"{}", 10, 30, ssl.create_default_context(),
            deadline=self.transport.OperationDeadline(time.monotonic() + 60),
        )
        with patch.object(self.http.http.client, "HTTPSConnection") as factory:
            with self.assertRaises(self.transport.BackendFailure) as caught:
                default.send(request)
            factory.assert_not_called()
        self.assertEqual(caught.exception.category, self.transport.ErrorCategory.SAFETY_POLICY)

    def test_credentials_permissions_and_non_overwriting_run_directories(self):
        self.credentials.write_text(json.dumps({
            "username": "synthetic-user-marker", "password": ' synthetic-password-marker "\\ ',
        }), encoding="utf-8")
        if os.name == "posix":
            self.credentials.chmod(0o644)
            status, report, factory = self.invoke()
            self.assertEqual(status, 1)
            factory.assert_not_called()
            self.assertIn("secret_resolution_failure", report["failure_codes"])
            self.credentials.chmod(0o600)
        reports = []
        for _ in range(2):
            status, report, _ = self.invoke(
                self.login(), self.connection(self.site), self.connection(self.site), self.connection(self.device),
            )
            self.assertEqual(status, 0)
            reports.append(report)
        self.assertNotEqual(reports[0]["run_directory"], reports[1]["run_directory"])
        self.assertTrue(all((self.output / report["run_directory"] / "summary.json").is_file() for report in reports))
