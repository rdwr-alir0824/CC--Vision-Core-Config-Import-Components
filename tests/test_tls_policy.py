import importlib
import json
import stat
from pathlib import Path
from unittest.mock import Mock, patch

from offline_support import OfflineTestCase


class TLSPolicyTests(OfflineTestCase):
    def setUp(self):
        super().setUp()
        self.module = importlib.import_module("cc_vision_import.tls_policy")
        self.source = self.directory / "source"
        self.destination = self.directory / "destination"
        self.source.mkdir()
        self.destination.mkdir()
        self.origin = "https://controller.example.invalid"

    def write(self, folder, data):
        filename = folder / "tls-policy.json"
        filename.write_text(json.dumps(data))
        return filename

    def test_default_true_and_separate_role_policies(self):
        with patch.object(self.module, "_private_file"):
            self.assertTrue(self.module.read_policy(self.source / "tls-policy.json", self.origin).verify)
            filename = self.write(self.destination, {
                "verify": False, "lab_authorized": True, "authorized_origin": self.origin,
            })
            self.assertFalse(self.module.read_policy(filename, self.origin).verify)
            self.assertTrue(self.module.read_policy(self.source / "tls-policy.json", self.origin).verify)

    def test_false_requires_explicit_authorization_and_matching_https_origin(self):
        error = self.module.TLSPolicyError
        for fields in (
            {"verify": False},
            {"verify": False, "lab_authorized": False, "authorized_origin": self.origin},
            {"verify": False, "lab_authorized": True, "authorized_origin": "https://another.invalid"},
            {"verify": False, "lab_authorized": True, "authorized_origin": self.origin + ":8443"},
            {"verify": False, "lab_authorized": True, "authorized_origin": "http://controller.example.invalid"},
        ):
            with self.assertRaises(error):
                self.module.TLSPolicy.from_dict(fields, self.origin)
        policy = self.module.TLSPolicy.from_dict({
            "verify": False, "lab_authorized": True,
            "authorized_origin": "https://CONTROLLER.example.invalid:443",
        }, self.origin)
        self.assertFalse(policy.verify)

    def test_invalid_types_and_conflicting_environment_fail_without_downgrade(self):
        error = self.module.TLSPolicyError
        for fields in ({"verify": "false"}, {"verify": 0}, {"lab_authorized": 1}, {"password": "private-marker"}):
            with self.assertRaises(error) as caught:
                self.module.TLSPolicy.from_dict(fields, self.origin)
            self.assertNotIn("private-marker", str(caught.exception))
        filename = self.source / "tls-policy.json"
        for setting in ("false", "private-marker", " true ", "0"):
            with self.assertRaises(error):
                self.module.read_policy(filename, self.origin, setting)
        self.assertTrue(self.module.read_policy(filename, self.origin, "true").verify)

    def test_private_policy_ownership_permissions_and_unreadable_or_oversized_policy(self):
        info = Mock(st_mode=stat.S_IFREG | 0o600, st_uid=10001, st_gid=10001)
        filename = self.write(self.source, {"verify": True})
        with patch.object(Path, "lstat", return_value=info):
            self.module._private_file(filename)
            for field, value in (("st_mode", stat.S_IFREG | 0o644), ("st_mode", stat.S_IFLNK | 0o600), ("st_uid", 0), ("st_gid", 0)):
                old = getattr(info, field)
                setattr(info, field, value)
                with self.assertRaises(self.module.TLSPolicyError):
                    self.module._private_file(filename)
                setattr(info, field, old)
        with patch.object(Path, "lstat", side_effect=PermissionError("private-marker")):
            with self.assertRaises(self.module.TLSPolicyError) as caught:
                self.module.read_policy(filename, self.origin)
            self.assertNotIn("private-marker", str(caught.exception))
        filename.write_text(" " * 4097)
        with patch.object(self.module, "_private_file"), self.assertRaises(self.module.TLSPolicyError):
            self.module.read_policy(filename, self.origin)

    def test_compose_requires_private_lab_policy_not_a_boolean_environment_alone(self):
        compose = importlib.import_module("cc_vision_import.compose_entrypoint")
        with patch.object(compose, "read_policy", wraps=self.module.read_policy) as reader:
            from contextlib import redirect_stderr
            import io
            import os

            for role, setting, command, url in (
                ("source", "CCV_TLS_VERIFY", "backup", "CCV_VISION_URL"),
                ("discovery", "CCV_DESTINATION_TLS_VERIFY", "discover-sites", "CCV_DESTINATION_URL"),
            ):
                with patch.dict(os.environ, {setting: "false", url: self.origin}, clear=True), redirect_stderr(io.StringIO()):
                    with patch.object(compose, "master_main") as dispatch, self.assertRaises(SystemExit):
                        compose.main([role, command])
                    dispatch.assert_not_called()

