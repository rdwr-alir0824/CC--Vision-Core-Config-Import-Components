import copy
import hashlib
import importlib
import json
import unittest
from pathlib import Path

from offline_support import OfflineTestCase


class PlanningContractTests(OfflineTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.plans = importlib.import_module("cc_vision_import.plans")
        self.operations = importlib.import_module("cc_vision_import.operations")
        self.contracts = importlib.import_module("cc_vision_import.contracts")
        fixtures = Path(__file__).parent / "fixtures"
        self.raw = (fixtures / "artifact-v1.json").read_bytes()
        self.request = json.loads((fixtures / "planning-request.json").read_text(encoding="utf-8"))

    def plan(self):
        return self.plans.create_plan(self.raw, self.request)

    def assert_contract_error(self, code: str, function, *args) -> None:
        with self.assertRaises(self.contracts.ContractValidationError) as caught:
            function(*args)
        self.assertEqual(caught.exception.result.status, "invalid")
        self.assertEqual(caught.exception.result.issues[0].code, code)
        self.assertTrue(caught.exception.result.issues[0].path.startswith("$"))

    def two_objects(self) -> None:
        artifact = json.loads(self.raw)
        artifact["objects"].append({"id": "sample-2", "name": "Same name is not an identity"})
        self.raw = json.dumps(artifact).encode("utf-8")
        second = copy.deepcopy(self.request["mappings"][0])
        second.update(mapping_id="map-two", source_index=1)
        second["source"]["object_id"] = "source-two"
        self.request["mappings"].append(second)
        proposal = copy.deepcopy(self.request["actions"][0])
        proposal.update(action_id="action-two", mapping_id="map-two")
        self.request["actions"].append(proposal)

    def resolved(self, index: int = 0, comparison: str = "identical") -> None:
        mapping = self.request["mappings"][index]
        mapping["state"] = "resolved"
        mapping["destination"] = {
            "namespace": "Organization/root", "object_type": "device", "object_id": f"destination-{index}"
        }
        self.request["actions"][index]["comparison"] = comparison

    def result_payload(self, plan, state: str = "planned") -> dict:
        return {
            "operation_id": "operation-one", "plan_id": plan.plan_id,
            "plan_integrity_sha256": plan.integrity_sha256,
            "action_id": "action-one", "state": state, "issue_codes": [],
            "verified": False, "evidence": [],
        }

    def test_explicit_mapping_and_source_bytes_are_bound_without_id_inference(self) -> None:
        before = copy.deepcopy(self.request)
        plan = self.plan()
        self.assertEqual(plan.mappings[0].source.object_id, "source-one")
        self.assertIsNone(plan.mappings[0].destination)
        self.assertEqual(plan.actions[0].kind, "create")
        self.assertEqual(plan.actions[0].changes, ("create-from-source",))
        self.assertEqual(plan.source_artifact.sha256, hashlib.sha256(self.raw).hexdigest())
        self.assertEqual(plan.stage, "offline-candidate")
        self.assertEqual(self.request, before)
        verified = self.plans.verify_plan(
            json.loads(plan.to_json()), self.raw, self.request["destination"], plan.integrity_sha256
        )
        self.assertEqual(verified, plan)

    def test_cyber_controller_non_controller_domains_keep_generic_planning(self) -> None:
        artifact = json.loads(self.raw)
        artifact["source"]["product"] = "cyber-controller"
        artifact["domain"] = "synthetic-domain"
        self.raw = json.dumps(artifact).encode("utf-8")
        self.request["mappings"][0]["source_context"]["product"] = "cyber-controller"
        self.request["mappings"][0]["domain"] = "synthetic-domain"
        plan = self.plan()
        self.assertEqual(plan.actions[0].kind, "create")
        self.assertEqual(
            self.plans.verify_plan(plan.to_dict(), self.raw, self.request["destination"], plan.integrity_sha256),
            plan,
        )

    def test_missing_and_duplicate_mapping_records_fail_explicitly(self) -> None:
        self.request["mappings"] = []
        self.assert_contract_error("missing_mapping", self.plan)
        self.setUp_request()
        self.request["mappings"].append(copy.deepcopy(self.request["mappings"][0]))
        self.assert_contract_error("duplicate_mapping", self.plan)
        self.setUp_request()
        self.two_objects()
        self.request["mappings"][1]["source"] = copy.deepcopy(self.request["mappings"][0]["source"])
        self.assert_contract_error("duplicate_identity", self.plan)

    def setUp_request(self) -> None:
        fixtures = Path(__file__).parent / "fixtures"
        self.raw = (fixtures / "artifact-v1.json").read_bytes()
        self.request = json.loads((fixtures / "planning-request.json").read_text(encoding="utf-8"))

    def test_qualified_namespaces_prevent_global_identity_assumptions(self) -> None:
        self.two_objects()
        self.request["mappings"][1]["source"]["object_id"] = "source-one"
        self.request["mappings"][1]["source"]["namespace"] = "Physical/another-parent"
        self.assertEqual(len(self.plan().mappings), 2)
        self.resolved()
        self.request["mappings"][0]["destination"]["object_id"] = "explicit-destination"
        self.assertEqual(self.plan().mappings[0].destination.object_id, "explicit-destination")

    def test_unresolved_ambiguous_and_unknown_semantics_block(self) -> None:
        self.request["mappings"][0]["state"] = "unresolved"
        plan = self.plan()
        self.assertEqual(plan.actions[0].kind, "blocked")
        self.assertIn("mapping_unresolved", plan.actions[0].issue_codes)
        self.request["mappings"][0].update(
            state="ambiguous",
            candidates=[
                {"namespace": "Physical/a", "object_type": "device", "object_id": "same"},
                {"namespace": "Physical/b", "object_type": "device", "object_id": "same"},
            ],
        )
        plan = self.plan()
        self.assertIn("mapping_ambiguous", plan.actions[0].issue_codes)
        self.assertEqual(plan.validation.status, "invalid")
        self.setUp_request()
        self.request["actions"][0]["semantics_known"] = False
        plan = self.plan()
        self.assertEqual(plan.actions[0].kind, "blocked")
        self.assertIn("unknown_semantics", plan.actions[0].issue_codes)
        self.request["actions"][0]["comparison"] = "unknown"
        self.assertIn("unknown_comparison", self.plan().actions[0].issue_codes)

    def test_duplicate_destination_targets_are_reported_as_ambiguity(self) -> None:
        self.two_objects()
        self.resolved(0)
        self.resolved(1)
        self.request["mappings"][1]["destination"] = copy.deepcopy(self.request["mappings"][0]["destination"])
        plan = self.plan()
        self.assertTrue(all(action.kind == "blocked" for action in plan.actions))
        self.assertTrue(all("destination_collision" in action.issue_codes for action in plan.actions))

    def test_identical_skips_differences_conflict_and_no_replacement_is_proposed(self) -> None:
        self.resolved()
        plan = self.plan()
        self.assertEqual(plan.actions[0].kind, "skip")
        self.assertEqual(plan.actions[0].changes, ())
        self.request["actions"][0]["comparison"] = "different"
        plan = self.plan()
        self.assertEqual(plan.actions[0].kind, "conflict")
        self.assertEqual(plan.actions[0].issue_codes, ("configuration_differs",))
        self.assertEqual(plan.actions[0].changes, ())
        self.assertEqual(plan.validation.status, "invalid")
        self.request["actions"][0]["comparison"] = "missing"
        self.assertIn("comparison_mismatch", self.plan().actions[0].issue_codes)

    def test_invalid_identity_shapes_and_contexts_fail(self) -> None:
        cases = (
            ("source_index", True, "invalid_identity"),
            ("source_index", 5, "missing_mapping"),
            ("domain", "other-domain", "context_mismatch"),
            ("destination_context", {"product": "vision", "version": "2.0"}, "context_mismatch"),
            ("state", "guessed", "invalid_mapping"),
            ("state", "resolved", "invalid_mapping"),
            ("state", "ambiguous", "invalid_mapping"),
        )
        for field, value, code in cases:
            with self.subTest(field=field):
                self.setUp_request()
                self.request["mappings"][0][field] = value
                self.assert_contract_error(code, self.plan)

    def test_parent_and_dependency_validation_and_blocking_propagation(self) -> None:
        self.two_objects()
        self.request["mappings"][1]["parent_mapping"] = "map-one"
        self.assert_contract_error("invalid_dependency", self.plan)
        self.request["actions"][1]["depends_on"] = ["action-one"]
        plan = self.plan()
        self.assertEqual([item.proposal.action_id for item in plan.actions], ["action-one", "action-two"])
        self.resolved(0, comparison="different")
        self.assertIn("dependency_blocked", self.plan().actions[1].issue_codes)
        self.request["actions"][0]["semantics_known"] = False
        plan = self.plan()
        self.assertIn("dependency_blocked", plan.actions[1].issue_codes)
        self.request["mappings"][0]["depends_on"] = ["map-two"]
        self.assert_contract_error("invalid_dependency", self.plan)

    def test_dangling_cyclic_and_duplicate_action_dependencies_fail(self) -> None:
        self.request["actions"][0]["depends_on"] = ["absent"]
        self.assert_contract_error("invalid_dependency", self.plan)
        self.request["actions"][0]["depends_on"] = ["action-one"]
        self.assert_contract_error("invalid_dependency", self.plan)
        self.request["actions"][0]["depends_on"] = ["absent", "absent"]
        self.assert_contract_error("duplicate_reference", self.plan)
        self.setUp_request()
        self.request["actions"] = []
        self.assert_contract_error("missing_action", self.plan)
        self.setUp_request()
        self.request["actions"].append(copy.deepcopy(self.request["actions"][0]))
        self.assert_contract_error("duplicate_action", self.plan)

    def test_plan_is_deterministic_across_mapping_proposal_and_json_key_order(self) -> None:
        self.two_objects()
        first = self.plan()
        self.request["mappings"].reverse()
        self.request["actions"].reverse()
        self.request = dict(reversed(list(self.request.items())))
        second = self.plan()
        self.assertEqual(first.to_json(), second.to_json())
        self.assertEqual(first.plan_id, second.plan_id)
        self.assertEqual(first.integrity_sha256, second.integrity_sha256)
        self.assertEqual(self.plans.parse_plan(json.loads(first.to_json())), first)

    def test_external_source_and_destination_changes_invalidate_bound_plan(self) -> None:
        plan = self.plan()
        payload = json.loads(plan.to_json())
        self.assert_contract_error(
            "source_changed", self.plans.verify_plan, payload, self.raw + b"\n",
            self.request["destination"], plan.integrity_sha256,
        )
        for field, value in (
            ("controller_id", "another-controller"), ("version", "2.1"),
            ("product", "vision"), ("base_url", "https://another.example.invalid"),
        ):
            with self.subTest(field=field):
                destination = {**self.request["destination"], field: value}
                self.assert_contract_error(
                    "destination_changed", self.plans.verify_plan, payload,
                    self.raw, destination, plan.integrity_sha256,
                )
        self.request["mappings"][0]["source"]["namespace"] = "Physical/changed"
        changed = self.plan()
        self.assertNotEqual(changed.plan_id, plan.plan_id)
        self.assert_contract_error(
            "integrity_mismatch", self.plans.verify_plan, json.loads(changed.to_json()),
            self.raw, self.request["destination"], plan.integrity_sha256,
        )

    def test_plan_tampering_and_unsupported_actions_are_rejected(self) -> None:
        plan = self.plan()
        for field, value in (
            ("plan_id", "changed"),
            ("domain", "changed"),
            ("validation", {"status": "valid"}),
            ("dependencies", {}),
            ("integrity_sha256", "0" * 64),
        ):
            with self.subTest(field=field):
                payload = json.loads(plan.to_json())
                payload[field] = value
                # Domain changes also invalidate mapping context.
                code = "context_mismatch" if field == "domain" else "integrity_mismatch"
                self.assert_contract_error(code, self.plans.parse_plan, payload)
        for kind in ("delete", "replace", "overwrite", "update"):
            payload = json.loads(plan.to_json())
            payload["actions"][0]["kind"] = kind
            self.assert_contract_error("unsupported_action", self.plans.parse_plan, payload)
        payload = json.loads(plan.to_json())
        payload["actions"][0]["proposal"]["semantics_known"] = False
        self.assert_contract_error("integrity_mismatch", self.plans.parse_plan, payload)
        payload = json.loads(plan.to_json())
        payload["actions"][0]["changes"] = ["replace"]
        self.assert_contract_error("integrity_mismatch", self.plans.parse_plan, payload)
        payload = json.loads(plan.to_json())
        payload["source_artifact"]["object_count"] = 10**30
        self.assert_contract_error("missing_mapping", self.plans.parse_plan, payload)
        payload = json.loads(plan.to_json())
        payload["schema_version"] = True
        self.assert_contract_error("unsupported_schema", self.plans.parse_plan, payload)
        plan.dependencies.clear()
        self.assert_contract_error("integrity_mismatch", plan.to_json)

    def test_invalid_source_json_and_invalid_validation_metadata_block(self) -> None:
        self.assert_contract_error("invalid_type", self.plans.create_plan, "not-bytes", self.request)
        for raw in (b'{"schema_version":1,"schema_version":1}', b"\xff", b'{"value":NaN}'):
            self.assert_contract_error("invalid_json", self.plans.create_plan, raw, self.request)
        artifact = json.loads(self.raw)
        artifact["validation"] = {
            "scope": "offline-contract", "status": "invalid", "issue_codes": ["missing_field"]
        }
        self.raw = json.dumps(artifact).encode("utf-8")
        self.assertIn("source_validation_invalid", self.plan().actions[0].issue_codes)

    def test_cli_plan_validation_reports_blocking_and_integrity_failures(self) -> None:
        for blocked in (False, True):
            self.request["actions"][0]["semantics_known"] = not blocked
            self.input_path.write_text(self.plan().to_json(), encoding="utf-8")
            status, result, stderr = self.validate_file("plan")
            self.assertEqual(status, 1 if blocked else 0)
            self.assertEqual(result["status"], "invalid" if blocked else "valid")
            self.assertEqual(stderr, "")
        payload = json.loads(self.plan().to_json())
        payload["integrity_sha256"] = "0" * 64
        self.input_path.write_text(json.dumps(payload), encoding="utf-8")
        status, result, stderr = self.validate_file("plan")
        self.assertEqual(status, 1)
        self.assertEqual(result["issues"][0]["code"], "integrity_mismatch")
        self.assertEqual(stderr, "")

    def test_result_states_do_not_imply_verification(self) -> None:
        plan = self.plan()
        for state in ("planned", "blocked", "failed", "completed", "verification_pending", "indeterminate"):
            with self.subTest(state=state):
                payload = self.result_payload(plan, state)
                if state in ("blocked", "failed", "indeterminate"):
                    payload["issue_codes"] = ["synthetic_reason"]
                result = self.operations.parse_operation_result(payload, plan)
                self.assertEqual(result.state, state)
                self.assertFalse(result.verified)
                self.assertEqual(json.loads(result.to_json(plan)), payload)
        self.resolved()
        plan = self.plan()
        result = self.operations.parse_operation_result(self.result_payload(plan, "skipped"), plan)
        self.assertEqual(result.state, "skipped")

    def test_verification_requires_explicit_matching_evidence_and_result_binding(self) -> None:
        plan = self.plan()
        payload = self.result_payload(plan, "completed")
        payload["verified"] = True
        self.assert_contract_error(
            "missing_verification_evidence", self.operations.parse_operation_result, payload, plan
        )
        payload["evidence"] = [{"reference": "synthetic/readback", "sha256": "a" * 64, "matched": False}]
        self.assert_contract_error(
            "missing_verification_evidence", self.operations.parse_operation_result, payload, plan
        )
        payload["evidence"][0]["matched"] = True
        self.assertTrue(self.operations.parse_operation_result(payload, plan).verified)
        payload["plan_id"] = "another-plan"
        self.assert_contract_error("plan_mismatch", self.operations.parse_operation_result, payload, plan)

    def test_invalid_result_states_reasons_and_blocked_execution_are_rejected(self) -> None:
        plan = self.plan()
        payload = self.result_payload(plan, "verified")
        self.assert_contract_error("invalid_state", self.operations.parse_operation_result, payload, plan)
        payload = self.result_payload(plan, "failed")
        self.assert_contract_error("missing_reason", self.operations.parse_operation_result, payload, plan)
        payload = self.result_payload(plan)
        payload["action_id"] = "absent"
        self.assert_contract_error("missing_action", self.operations.parse_operation_result, payload, plan)
        self.request["actions"][0]["semantics_known"] = False
        plan = self.plan()
        self.assert_contract_error(
            "invalid_state", self.operations.parse_operation_result, self.result_payload(plan, "completed"), plan
        )


if __name__ == "__main__":
    unittest.main()
