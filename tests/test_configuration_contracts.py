import copy
import importlib
import json
import math
import unittest
from dataclasses import replace
from pathlib import Path

from offline_support import OfflineTestCase


class ConfigurationContractTests(OfflineTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.profiles = importlib.import_module("cc_vision_import.profiles")
        self.artifacts = importlib.import_module("cc_vision_import.artifacts")
        self.contracts = importlib.import_module("cc_vision_import.contracts")

    def fixture(self, name: str) -> dict:
        path = Path(__file__).parent / "fixtures" / f"{name}.json"
        return json.loads(path.read_text(encoding="utf-8"))

    def assert_cli_result(self, module: str, payload: object, code: str | None = None) -> dict:
        self.input_path.write_text(json.dumps(payload), encoding="utf-8")
        status, result, stderr = self.validate_file(module)
        self.assertEqual(stderr, "")
        self.assertEqual(status, 1 if code else 0)
        self.assertEqual(result["status"], "invalid" if code else "valid")
        if code:
            self.assertEqual(result["issues"][0]["code"], code)
            self.assertTrue(result["issues"][0]["path"].startswith("$"))
            self.assertTrue(result["issues"][0]["message"])
        else:
            self.assertEqual(result["issues"], [])
        return result

    def test_valid_profiles_are_separate_and_do_not_resolve_hosts_or_secrets(self) -> None:
        source_data = self.fixture("source-profile")
        destination_data = self.fixture("destination-profile")
        source = self.profiles.SourceProfile.from_dict(source_data)
        destination = self.profiles.DestinationProfile.from_dict(destination_data)
        self.assertEqual(source.role, "source")
        self.assertEqual(destination.role, "destination")
        self.assertNotEqual(type(source), type(destination))
        self.assertEqual(source.product, "vision")
        self.assertEqual(destination.product, "cyber-controller")
        self.assertEqual(source.secret_ref, "synthetic/source")
        self.assertIsNone(destination.secret_ref)
        self.assertNotIn(source.base_url, repr(source))
        self.assertNotIn(source.secret_ref, repr(source))
        for name, data in (("source-profile", source_data), ("destination-profile", destination_data)):
            with self.subTest(module=name):
                result = self.assert_cli_result(name, data)
                self.assertNotIn(data["base_url"], json.dumps(result))

    def test_profiles_require_fields_and_matching_role(self) -> None:
        for module in ("source-profile", "destination-profile"):
            for field in ("role", "name", "product", "version", "base_url"):
                with self.subTest(module=module, field=field):
                    payload = self.fixture(module)
                    del payload[field]
                    result = self.assert_cli_result(module, payload, "missing_field")
                    self.assertEqual(result["issues"][0]["path"], f"$.{field}")
        payload = self.fixture("source-profile")
        payload["role"] = "destination"
        self.assert_cli_result("source-profile", payload, "role_mismatch")
        self.assert_cli_result("destination-profile", self.fixture("source-profile"), "role_mismatch")
        self.assert_cli_result("source-profile", [], "invalid_type")

    def test_invalid_product_and_version_declarations(self) -> None:
        for module in ("source-profile", "destination-profile", "artifact"):
            for field, value, code in (
                ("product", "unknown", "invalid_product"),
                ("product", None, "invalid_product"),
                ("product", "Vision", "invalid_product"),
                ("version", "", "invalid_version"),
                ("version", "latest", "invalid_version"),
                ("version", 1.0, "invalid_version"),
                ("version", True, "invalid_version"),
                ("version", "1.0\n", "invalid_version"),
            ):
                with self.subTest(module=module, field=field, value_type=type(value).__name__):
                    payload = self.fixture("artifact-v1" if module == "artifact" else module)
                    declaration = payload["source"] if module == "artifact" else payload
                    declaration[field] = value
                    self.assert_cli_result(module, payload, code)
        payload = self.fixture("source-profile")
        payload["version"] = "99.1.2-build.3"
        self.assert_cli_result("source-profile", payload)

    def test_profile_credentials_and_invalid_origins_are_rejected_without_echo(self) -> None:
        marker = "sensitive-fixture-marker"
        for field in ("password", "token", "credentials", marker):
            payload = self.fixture("source-profile")
            payload[field] = marker
            result = self.assert_cli_result("source-profile", payload, "unknown_fields")
            self.assertNotIn(marker, json.dumps(result))
        for url in (
            "http://source.example.invalid",
            f"https://user:{marker}@source.example.invalid",
            f"https://source.example.invalid/?token={marker}",
            "https://source.example.invalid/path",
            "https://source.example.invalid:99999",
            "https://source.example.invalid:0",
            "https://",
            "https://bad host.invalid",
        ):
            with self.subTest(origin_kind="invalid"):
                payload = self.fixture("source-profile")
                payload["base_url"] = url
                result = self.assert_cli_result("source-profile", payload, "invalid_value")
                self.assertNotIn(marker, json.dumps(result))
        payload = self.fixture("source-profile")
        payload["secret_ref"] = "https://provider.invalid/value"
        self.assert_cli_result("source-profile", payload, "invalid_value")

    def test_artifact_round_trip_preserves_unknown_configuration_fields(self) -> None:
        payload = self.fixture("artifact-v1")
        before = copy.deepcopy(payload)
        artifact = self.artifacts.parse_artifact(payload)
        self.assertNotIn("futureVendorField", repr(artifact))
        encoded = artifact.to_json()
        self.assertEqual(json.loads(encoded), before)
        self.assertEqual(payload, before)
        self.assertEqual(self.assert_cli_result("artifact", payload)["object_count"], 1)
        payload["objects"][0]["futureVendorField"]["enabled"] = False
        self.assertEqual(json.loads(artifact.to_json()), before)
        with self.assertRaises(self.contracts.ContractValidationError):
            replace(artifact, schema_version=2).to_json()

    def test_artifact_required_fields_and_unknown_envelope_are_explicit(self) -> None:
        for field in ("schema_version", "domain", "source", "metadata", "objects", "validation"):
            with self.subTest(field=field):
                payload = self.fixture("artifact-v1")
                del payload[field]
                result = self.assert_cli_result("artifact", payload, "missing_field")
                self.assertEqual(result["issues"][0]["path"], f"$.{field}")
        payload = self.fixture("artifact-v1")
        payload["future-envelope-field"] = {}
        self.assert_cli_result("artifact", payload, "unknown_fields")
        payload = self.fixture("artifact-v1")
        payload["source"]["base_url"] = "https://source.example.invalid"
        self.assert_cli_result("artifact", payload, "unknown_fields")
        self.assert_cli_result("artifact", [], "invalid_type")

    def test_artifact_schema_domain_and_object_types(self) -> None:
        for field, value, code in (
            ("schema_version", 2, "unsupported_schema"),
            ("schema_version", True, "unsupported_schema"),
            ("schema_version", "1", "unsupported_schema"),
            ("domain", "", "invalid_value"),
            ("domain", "Unsupported Domain", "invalid_value"),
            ("source", [], "invalid_type"),
            ("objects", {}, "invalid_type"),
            ("objects", [None], "invalid_type"),
            ("objects", [["not-an-object"]], "invalid_type"),
        ):
            with self.subTest(field=field, value_type=type(value).__name__):
                payload = self.fixture("artifact-v1")
                payload[field] = value
                self.assert_cli_result("artifact", payload, code)
        payload = self.fixture("artifact-v1")
        payload["objects"] = []
        self.assertEqual(self.assert_cli_result("artifact", payload)["object_count"], 0)

    def test_metadata_rejects_malformed_and_missing_values(self) -> None:
        for field in ("exported_at", "exporter"):
            payload = self.fixture("artifact-v1")
            del payload["metadata"][field]
            self.assert_cli_result("artifact", payload, "missing_field")
        for metadata, code in (
            ([], "invalid_type"),
            ({"exported_at": None, "exporter": "fixture"}, "invalid_value"),
            ({"exported_at": "2026-11-17", "exporter": "fixture"}, "invalid_metadata"),
            ({"exported_at": "2026-11-17T17:00:00", "exporter": "fixture"}, "invalid_metadata"),
            ({"exported_at": "2026-02-30T17:00:00Z", "exporter": "fixture"}, "invalid_metadata"),
            ({"exported_at": "2026-11-17T17:00:00Z", "exporter": ""}, "invalid_value"),
        ):
            with self.subTest(code=code):
                payload = self.fixture("artifact-v1")
                payload["metadata"] = metadata
                self.assert_cli_result("artifact", payload, code)
        payload = self.fixture("artifact-v1")
        payload["metadata"]["exported_at"] = "2026-11-17T12:00:00-05:00"
        self.assert_cli_result("artifact", payload)

    def test_validation_metadata_is_consistent_and_does_not_override_checks(self) -> None:
        for information in (
            {"scope": "live-tested", "status": "valid", "issue_codes": []},
            {"scope": "offline-contract", "status": "complete", "issue_codes": []},
            {"scope": "offline-contract", "status": "invalid", "issue_codes": []},
            {"scope": "offline-contract", "status": "valid", "issue_codes": ["invalid_type"]},
            {"scope": "offline-contract", "status": "invalid", "issue_codes": ["free form message"]},
        ):
            payload = self.fixture("artifact-v1")
            payload["validation"] = information
            self.assert_cli_result("artifact", payload, "invalid_validation_info")
        payload = self.fixture("artifact-v1")
        payload["validation"] = {
            "scope": "offline-contract", "status": "invalid", "issue_codes": ["missing_field"]
        }
        artifact = self.artifacts.parse_artifact(payload)
        self.assertEqual(json.loads(artifact.to_json()), payload)
        payload["validation"] = {"scope": "offline-contract", "status": "valid", "issue_codes": []}
        payload["objects"] = [None]
        self.assert_cli_result("artifact", payload, "invalid_type")

    def test_inline_secrets_are_rejected_at_any_depth_including_on_serialization(self) -> None:
        marker = "sensitive-fixture-marker"
        for key in ("password", "cliPassword", "SNMP-community", "api_key", "accessToken", "credentials"):
            payload = self.fixture("artifact-v1")
            payload["objects"][0]["nested"] = [{"inner": {key: marker}}]
            with self.subTest(field_kind="credential"):
                result = self.assert_cli_result("artifact", payload, "secret_value_not_allowed")
                self.assertNotIn(marker, json.dumps(result))
        artifact = self.artifacts.parse_artifact(self.fixture("artifact-v1"))
        artifact.objects[0]["password"] = marker
        with self.assertRaises(self.contracts.ContractValidationError) as caught:
            artifact.to_json()
        self.assertNotIn(marker, str(caught.exception))
        self.assertEqual(caught.exception.result.issues[0].code, "secret_value_not_allowed")

    def test_secret_references_and_null_are_preserved_but_mixed_wrappers_fail(self) -> None:
        payload = self.fixture("artifact-v1")
        payload["objects"][0]["password"] = None
        payload["objects"][0]["apiToken"] = {"secret_ref": "synthetic/token"}
        self.assertEqual(
            json.loads(self.artifacts.parse_artifact(payload).to_json()), payload
        )
        payload["objects"][0]["apiToken"]["value"] = "sensitive-fixture-marker"
        self.assert_cli_result("artifact", payload, "secret_value_not_allowed")
        payload["objects"][0]["apiToken"] = {"secret_ref": ""}
        self.assert_cli_result("artifact", payload, "invalid_value")

    def test_direct_contract_parser_rejects_non_json_values_and_excessive_depth(self) -> None:
        for value in (object(), (1, 2), math.nan, math.inf, {1: "not-a-json-key"}):
            payload = self.fixture("artifact-v1")
            payload["objects"][0]["extra"] = value
            with self.subTest(value_type=type(value).__name__):
                with self.assertRaises(self.contracts.ContractValidationError):
                    self.artifacts.parse_artifact(payload)
        payload = self.fixture("artifact-v1")
        nested: dict = {}
        payload["objects"][0]["extra"] = nested
        for _ in range(66):
            child: dict = {}
            nested["child"] = child
            nested = child
        self.assert_cli_result("artifact", payload, "invalid_value")

    def test_new_validators_keep_json_and_file_error_exit_statuses(self) -> None:
        for module in ("source-profile", "destination-profile", "artifact"):
            with self.subTest(module=module):
                self.input_path.write_text('{"bad":', encoding="utf-8")
                status, result, stderr = self.validate_file(module)
                self.assertEqual(status, 3)
                self.assertEqual(result["issues"][0]["code"], "invalid_json")
                self.assertEqual(stderr, "")
                self.input_path.unlink()
                status, result, stderr = self.validate_file(module)
                self.assertEqual(status, 3)
                self.assertEqual(result["issues"][0]["code"], "input_unreadable")
                self.assertEqual(stderr, "")


if __name__ == "__main__":
    unittest.main()
