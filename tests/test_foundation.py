import copy
import importlib
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from offline_support import OfflineTestCase


class OfflineFoundationTests(OfflineTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.payload = {
            "schema_version": 1,
            "module": "synthetic",
            "objects": [{"id": "sample-1", "name": "Synthetic example"}],
        }

    def test_help_and_module_inventory(self) -> None:
        for args in (("--help",), ("validate", "--help")):
            with self.subTest(args=args):
                status, stdout, stderr = self.invoke(*args)
                self.assertEqual(status, 0)
                self.assertIn("usage:", stdout)
                self.assertEqual(stderr, "")
        status, stdout, stderr = self.invoke("modules")
        self.assertEqual(status, 0)
        self.assertEqual(stderr, "")
        inventory = json.loads(stdout)["modules"]
        self.assertEqual(
            [item["name"] for item in inventory],
            ["synthetic", "source-profile", "destination-profile", "artifact", "plan"],
        )
        self.assertEqual(inventory[0]["operations"], ["validate"])

    def test_valid_fixture_produces_structured_result(self) -> None:
        self.input_path.write_text(json.dumps(self.payload), encoding="utf-8")
        status, result, stderr = self.validate_file()
        self.assertEqual(status, 0)
        self.assertEqual(stderr, "")
        self.assertEqual(
            result,
            {"module": "synthetic", "status": "valid", "object_count": 1, "issues": []},
        )

    def test_invalid_fixtures_report_explicit_issues(self) -> None:
        cases = (
            ([], "invalid_type", "$"),
            ({}, "unsupported_schema", "$.schema_version"),
            ({**self.payload, "schema_version": True}, "unsupported_schema", "$.schema_version"),
            ({**self.payload, "schema_version": 2}, "unsupported_schema", "$.schema_version"),
            ({**self.payload, "module": "controller-objects"}, "module_mismatch", "$.module"),
            ({**self.payload, "objects": {}}, "invalid_type", "$.objects"),
            ({**self.payload, "objects": [None]}, "invalid_type", "$.objects[0]"),
            ({**self.payload, "objects": [{}]}, "invalid_value", "$.objects[0].id"),
            (
                {**self.payload, "objects": [{"id": "a", "name": " "}]},
                "invalid_value",
                "$.objects[0].name",
            ),
            (
                {**self.payload, "objects": [{"id": " a", "name": "Example"}]},
                "invalid_value",
                "$.objects[0].id",
            ),
            (
                {**self.payload, "objects": self.payload["objects"] * 2},
                "duplicate_id",
                "$.objects[1].id",
            ),
        )
        for payload, code, path in cases:
            with self.subTest(code=code, path=path, payload_type=type(payload).__name__):
                self.input_path.write_text(json.dumps(payload), encoding="utf-8")
                status, result, stderr = self.validate_file()
                self.assertEqual(status, 1)
                self.assertEqual(result["status"], "invalid")
                self.assertEqual(stderr, "")
                matches = [
                    issue for issue in result["issues"]
                    if issue["code"] == code and issue["path"] == path
                ]
                self.assertTrue(matches)
                self.assertTrue(matches[0]["message"])

    def test_unrecognized_fields_fail_without_echoing_values(self) -> None:
        marker = "sensitive-fixture-marker"
        for payload in (
            {**self.payload, marker: marker},
            {**self.payload, "objects": [{"id": "a", "name": "Example", marker: marker}]},
        ):
            with self.subTest(top_level=marker in payload):
                self.input_path.write_text(json.dumps(payload), encoding="utf-8")
                status, result, stderr = self.validate_file()
                self.assertEqual(status, 1)
                self.assertEqual(result["issues"][0]["code"], "unknown_fields")
                self.assertNotIn(marker, json.dumps(result) + stderr)

    def test_malformed_and_ambiguous_json_fail_without_raw_content(self) -> None:
        for text in (
            '{"sensitive-fixture-marker":',
            '{"schema_version": 2, "schema_version": 1, "module": "synthetic", "objects": []}',
            '{"schema_version": NaN, "module": "synthetic", "objects": []}',
        ):
            with self.subTest(text_type="malformed-or-ambiguous"):
                self.input_path.write_text(text, encoding="utf-8")
                status, result, stderr = self.validate_file()
                self.assertEqual(status, 3)
                self.assertEqual(result["status"], "error")
                self.assertEqual(result["issues"][0]["code"], "invalid_json")
                self.assertNotIn("sensitive-fixture-marker", json.dumps(result) + stderr)

    def test_missing_unreadable_and_non_utf8_files_fail_explicitly(self) -> None:
        status, result, stderr = self.validate_file()
        self.assertEqual(status, 3)
        self.assertEqual(result["issues"][0]["code"], "input_unreadable")
        self.assertEqual(stderr, "")
        with patch("pathlib.Path.read_text", side_effect=PermissionError("fixture-denied")):
            status, result, stderr = self.validate_file()
        self.assertEqual(status, 3)
        self.assertEqual(result["issues"][0]["code"], "input_unreadable")
        self.assertNotIn("fixture-denied", json.dumps(result) + stderr)
        self.input_path.write_bytes(b"\xff")
        status, result, stderr = self.validate_file()
        self.assertEqual(status, 3)
        self.assertEqual(result["issues"][0]["code"], "invalid_encoding")
        self.assertEqual(stderr, "")

    def test_remote_input_is_rejected_before_file_access(self) -> None:
        for value in ("https://example.invalid/fixture.json", r"\\example.invalid\share\fixture.json"):
            with self.subTest(input_kind="remote"):
                with patch("pathlib.Path.read_text") as read_text:
                    status, stdout, stderr = self.invoke(
                        "validate", "--module", "synthetic", "--input", value
                    )
                self.assertEqual(status, 3)
                self.assertEqual(json.loads(stdout)["issues"][0]["code"], "nonlocal_input")
                self.assertEqual(stderr, "")
                read_text.assert_not_called()

    def test_cli_usage_errors_have_nonzero_status(self) -> None:
        for args in (
            (),
            ("export",),
            ("import",),
            ("plan",),
            ("validate",),
            ("validate", "--module", "synthetic"),
            ("validate", "--module", "unknown", "--input", str(self.input_path)),
        ):
            with self.subTest(args=args):
                status, stdout, stderr = self.invoke(*args)
                self.assertEqual(status, 2)
                self.assertEqual(stdout, "")
                self.assertIn("error:", stderr)

    def test_registry_validation_preserves_input_and_has_no_legacy_imports(self) -> None:
        registry = importlib.import_module("cc_vision_import.registry")
        before = copy.deepcopy(self.payload)
        module = registry.get_module("synthetic")
        self.assertIsNotNone(module)
        result = module.validate(self.payload)
        self.assertEqual(result.status, "valid")
        self.assertEqual(self.payload, before)
        self.assertIsNone(registry.get_module("unknown"))
        legacy_root = Path(__file__).resolve().parents[1] / "legacy"
        for loaded in tuple(sys.modules.values()):
            filename = getattr(loaded, "__file__", None)
            if isinstance(filename, str):
                self.assertFalse(Path(filename).resolve().is_relative_to(legacy_root))


if __name__ == "__main__":
    unittest.main()
