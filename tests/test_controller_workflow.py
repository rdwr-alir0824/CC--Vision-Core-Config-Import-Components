import copy
import hashlib
import importlib
import io
import json
import runpy
import sys
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

from offline_support import OfflineTestCase, device_access_acknowledgements


class ControllerWorkflowTests(OfflineTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.w = importlib.import_module("cc_vision_import.controller_workflow")
        self.o = importlib.import_module("cc_vision_import.controller_objects")
        self.e = importlib.import_module("cc_vision_import.controller_exports")
        self.p = importlib.import_module("cc_vision_import.controller_access_policy")
        self.examples = Path(__file__).parent.parent / "examples" / "offline-controller"
        for path in self.examples.glob("*.json"):
            (self.directory / path.name).write_bytes(path.read_bytes())
        self.request = self.directory / "request.json"

    def read(self, name):
        return json.loads((self.directory / name).read_text(encoding="utf-8"))

    def write(self, name, value):
        (self.directory / name).write_text(json.dumps(value, allow_nan=False), encoding="utf-8")

    def run_plan(self, **kwargs):
        return self.w.plan_offline_request(self.request, **kwargs)

    def codes(self, result):
        return {issue["code"] for issue in result.report["validation_failures"]}

    def root_only(self):
        manifest = self.read("request.json")
        for role in ("source", "destination"):
            tree = self.read(role + "-tree.json")
            tree["children"] = []
            self.write(role + "-tree.json", tree)
            manifest[role]["reconciliation"] = None
        self.write("request.json", manifest)
        self.write("mappings.json", self.read("mappings.json")[:1])
        policy = self.read("policy.json")
        policy["semantics_known_for"] = policy["semantics_known_for"][:1]
        self.write("policy.json", policy)

    def retain(self, result):
        path = self.directory / "retained.json"
        path.write_text(result.record_json(), encoding="utf-8")
        return path

    def invoke_master(self, *args):
        stdout, stderr = io.StringIO(), io.StringIO()
        entry = self.examples.parent.parent / "master.py"
        with (
            redirect_stdout(stdout), redirect_stderr(stderr),
            patch.object(sys, "argv", ["master.py", *args]),
            patch.object(sys, "path", list(sys.path)),
        ):
            with self.assertRaises(SystemExit) as caught:
                runpy.run_path(str(entry), run_name="__main__")
        return caught.exception.code, json.loads(stdout.getvalue()), stderr.getvalue()

    def test_master_profiles_and_selection_do_not_authenticate(self):
        status, report, stderr = self.invoke_master(
            "--operation", "profiles",
            "--source-profile", str(self.directory / "source-profile.json"),
            "--destination-profile", str(self.directory / "destination-profile.json"),
        )
        self.assertEqual((status, stderr), (0, ""))
        self.assertFalse(report["authenticated"])
        self.assertNotIn("source.invalid", json.dumps(report))
        status, report, _ = self.invoke_master("--operation", "operations")
        self.assertEqual(status, 0)
        self.assertIn("scheduler", report["operations"])

    def test_master_export_preserves_source_and_refuses_overwrite(self):
        output = self.directory / "exported.json"
        status, report, stderr = self.invoke_master(
            "--operation", "export", "--request", str(self.request), "--output", str(output),
        )
        self.assertEqual((status, stderr, report["status"]), (0, "", "exported"))
        expected = self.run_plan().record["artifacts"]["source"]
        exported = output.read_text(encoding="utf-8")
        self.assertEqual(json.loads(exported), expected)
        self.assertEqual(
            list(json.loads(exported)["objects"][0]["configuration"]["unknownRoot"]), ["second", "first"],
        )
        status, report, _ = self.invoke_master(
            "--operation", "export", "--request", str(self.request), "--output", str(output),
        )
        self.assertEqual(status, 3)
        self.assertEqual(report["errors"], [{"code": "output_exists"}])
        self.assertEqual(output.read_text(encoding="utf-8"), exported)

    def test_master_comparison_plan_and_import_preview_reuse_existing_results(self):
        for operation in ("compare", "plan", "import-preview"):
            status, report, stderr = self.invoke_master(
                "--operation", operation, "--request", str(self.request),
            )
            self.assertEqual((status, stderr), (1, ""))
            self.assertEqual(report["counts"], {"CREATE": 3, "SKIP": 3, "CONFLICT": 1, "BLOCKED": 1})
            self.assertFalse(report["execution_authorized"])
            self.assertTrue(report["approval_required_before_changes"])
        self.root_only()
        status, report, _ = self.invoke_master("--operation", "plan", "--request", str(self.request))
        self.assertEqual(status, 0)
        self.assertFalse(report["import_execution_available"])
        status, report, _ = self.invoke_master("--operation", "import", "--request", str(self.request))
        self.assertEqual((status, report["status"]), (4, "unavailable"))

    def test_master_unresolved_domains_and_vision_are_explicitly_unavailable(self):
        for domain in ("ldap-permissions", "scheduler"):
            status, report, _ = self.invoke_master(
                "--operation", "plan", "--module", domain, "--request", str(self.request),
            )
            self.assertEqual((status, report["errors"][0]["code"]), (4, "unresolved_contract"))
        profile = self.read("source-profile.json")
        profile["product"] = "vision"
        self.write("source-profile.json", profile)
        status, report, _ = self.invoke_master(
            "--operation", "plan", "--source-product", "vision", "--request", str(self.request),
        )
        self.assertEqual((status, report["errors"][0]["code"]), (4, "vision_controller_contract_unavailable"))
        status, report, _ = self.invoke_master("--operation", "authenticate")
        self.assertEqual((status, report["errors"][0]["code"]), (4, "live_execution_disabled"))

    def test_master_rejects_profile_retargeting_and_secret_export_without_output(self):
        alternate = self.read("source-profile.json")
        alternate["base_url"] = "https://other.invalid"
        self.write("alternate.json", alternate)
        output = self.directory / "exported.json"
        status, report, _ = self.invoke_master(
            "--operation", "export", "--request", str(self.request), "--output", str(output),
            "--source-profile", str(self.directory / "alternate.json"),
        )
        self.assertEqual((status, report["errors"][0]["code"]), (4, "profile_mismatch"))
        self.assertFalse(output.exists())
        tree = self.read("source-tree.json")
        tree["password"] = "must-never-be-reported"
        self.write("source-tree.json", tree)
        status, report, _ = self.invoke_master(
            "--operation", "export", "--request", str(self.request), "--output", str(output),
        )
        self.assertEqual((status, report["errors"][0]["code"]), (4, "secret_value_not_allowed"))
        self.assertNotIn("must-never-be-reported", json.dumps(report))
        self.assertFalse(output.exists())

    def test_synthetic_demonstration_all_classifications_and_nested_dependencies(self):
        with patch("cc_vision_import.plans.create_plan", side_effect=AssertionError("Generic planner forbidden.")) as generic:
            result = self.run_plan()
        generic.assert_not_called()
        self.assertEqual(result.exit_status, 1)
        self.assertEqual(result.report["workflow_result"], "blocked")
        self.assertEqual(result.report["counts"], {"CREATE": 3, "SKIP": 3, "CONFLICT": 1, "BLOCKED": 1})
        self.assertEqual(result.report["total_objects_evaluated"], 8)
        self.assertFalse(result.report["execution_authorized"])
        actions = {row["source_index"]: row for row in result.record["plan"]["actions"]}
        self.assertEqual(actions[6]["parent_action"], "object-5")
        self.assertEqual(actions[7]["parent_action"], "object-6")
        self.assertIn("object-6", actions[7]["depends_on"])
        self.assertIsNone(actions[7]["destination_index"])
        self.assertIn("unacknowledged_device_access", actions[3]["issue_codes"])
        self.assertTrue(all(stage["status"] == "complete" for stage in result.report["stages"]))
        self.assertEqual(self.run_plan(verify_record=self.retain(result)).record_json(), result.record_json())

    def test_successful_existing_root_plan_and_cli_record_verification(self):
        self.root_only()
        record = self.directory / "protected.json"
        status, stdout, stderr = self.invoke("plan", "--request", str(self.request), "--record", str(record))
        self.assertEqual((status, stderr), (0, ""))
        report = json.loads(stdout)
        self.assertEqual(report["workflow_result"], "planned")
        self.assertEqual(report["counts"], {"CREATE": 0, "SKIP": 1, "CONFLICT": 0, "BLOCKED": 0})
        status, verified, stderr = self.invoke("plan", "--request", str(self.request), "--verify", str(record))
        self.assertEqual((status, json.loads(verified), stderr), (0, report, ""))

    def test_successful_nested_create_plan_uses_existing_root_and_exit_zero(self):
        mappings = self.read("mappings.json")
        policy = self.read("policy.json")
        branch = self.read("source-tree.json")["children"][2]
        branch["children"][0]["children"] = []
        self.root_only()
        tree = self.read("source-tree.json")
        tree["children"] = [branch]
        self.write("source-tree.json", tree)
        records = [mappings[0]]
        for index, original in enumerate((5, 6), start=1):
            row = mappings[original]
            row.update(
                mapping_id=f"map-{index}", source_index=index,
                parent_mapping=f"map-{index - 1}", depends_on=[f"map-{index - 1}"],
            )
            records.append(row)
        self.write("mappings.json", records)
        policy["semantics_known_for"] = [policy["semantics_known_for"][index] for index in (0, 5, 6)]
        self.write("policy.json", policy)
        status, output, error = self.invoke("plan", "--request", str(self.request))
        self.assertEqual((status, error), (0, ""))
        self.assertEqual(json.loads(output)["counts"], {"CREATE": 2, "SKIP": 1, "CONFLICT": 0, "BLOCKED": 0})

    def test_reports_are_redacted_and_opaque_references_correlate_with_protected_records(self):
        result = self.run_plan()
        rendered = json.dumps(result.report) + repr(result)
        for marker in (
            "synthetic-source", "synthetic-destination", "192.0.2.10", "src-identical",
            "Identical device", "futureDetail", "evidence-33333333333333333333333333333333",
            "source.invalid", str(self.directory),
        ):
            self.assertNotIn(marker, rendered)
        for action, protected in zip(result.report["actions"], result.record["action_records"], strict=True):
            self.assertRegex(action["reference"], r"^action-[0-9a-f]{64}$")
            self.assertEqual(action["reference"], protected["reference"])
            source = result.record["artifacts"]["source"]["objects"][protected["source_index"]]
            self.assertIn("controller_id", source["reference"])
        self.assertEqual(len({row["reference"] for row in result.report["actions"]}), 8)

    def test_deterministic_order_preserving_records_and_configuration(self):
        first, second = self.run_plan(), self.run_plan()
        self.assertEqual(first.record_json(), second.record_json())
        artifact = json.loads(first.record_json())["artifacts"]["source"]
        detail = artifact["objects"][2]["configuration"]["offlineDeviceReconciliation"]["detail"]["futureDetail"]
        self.assertEqual(list(detail), ["second", "first"])
        self.assertEqual(detail["second"], [None, True, 1])
        self.assertIs(type(detail["second"][1]), bool)
        self.assertIs(type(detail["second"][2]), int)
        self.assertEqual(list(artifact["objects"][0]["configuration"]["unknownRoot"]), ["second", "first"])
        self.assertNotIn("missing", detail)

    def test_mutated_protected_result_cannot_be_serialized_as_integrity_valid(self):
        result = self.run_plan()
        result.record["report"]["execution_authorized"] = True
        contracts = importlib.import_module("cc_vision_import.contracts")
        with self.assertRaises(contracts.ContractValidationError) as caught:
            result.record_json()
        self.assertEqual(caught.exception.result.issues[0].code, "integrity_mismatch")

    def test_stale_access_acknowledgement_is_blocked_after_complete_workflow(self):
        tree = self.read("source-tree.json")
        tree["children"][0]["children"][0]["deviceAccess"]["connectionTimeout"] = 99
        self.write("source-tree.json", tree)
        result = self.run_plan()
        self.assertEqual(result.report["workflow_result"], "blocked")
        self.assertIn("stale_device_access_acknowledgement", self.codes(result))
        self.assertEqual(result.record["artifacts"]["source"]["validation"]["status"], "valid")
        action = next(item for item in result.record["plan"]["actions"] if item["source_index"] == 2)
        self.assertEqual(action["kind"], "blocked")

    def test_changed_source_destination_policy_or_completeness_invalidates_retained_record(self):
        retained = self.retain(self.run_plan())
        for name, change in (
            ("source-tree.json", lambda value: value.update(extraUnknown={"second": 2, "first": 1})),
            ("destination-profile.json", lambda value: value.update(base_url="https://changed.invalid")),
            ("policy.json", lambda value: value.update(evidence_reference="evidence-" + "4" * 32)),
            ("completeness.json", lambda value: value["trees"][0].update(evidence_reference="evidence-" + "4" * 32)),
        ):
            with self.subTest(input=name):
                original = self.read(name)
                changed = copy.deepcopy(original)
                change(changed)
                self.write(name, changed)
                result = self.run_plan(verify_record=retained)
                self.assertEqual(result.report["workflow_result"], "failed")
                self.assertIn("integrity_mismatch", self.codes(result))
                self.write(name, original)

    def test_forged_and_rehashed_protected_record_does_not_authorize_root_create(self):
        result = self.run_plan()
        body = copy.deepcopy(result.record)
        body["plan"]["actions"][0].update(kind="create", comparison="missing", issue_codes=[])

        def digest(value, *, canonical=False):
            encoded = json.dumps(value, sort_keys=canonical, separators=(",", ":"), ensure_ascii=True, allow_nan=False)
            return hashlib.sha256(encoded.encode()).hexdigest()

        plan = body["plan"]
        original = {key: value for key, value in plan.items() if key not in ("plan_id", "integrity_sha256")}
        plan["plan_id"] = "controller-plan-" + digest(original, canonical=True)
        plan["integrity_sha256"] = digest({"plan_id": plan["plan_id"], **original}, canonical=True)
        del body["integrity_sha256"]
        body["integrity_sha256"] = digest(body)
        self.write("retained.json", body)
        checked = self.run_plan(verify_record=self.directory / "retained.json")
        self.assertEqual(checked.report["workflow_result"], "failed")
        self.assertIn("integrity_mismatch", self.codes(checked))

    def test_missing_acknowledgements_preserve_artifacts_and_block_all_earlier_input_paths(self):
        manifest = self.read("request.json")
        inventories = []
        for role in ("source", "destination"):
            manifest[role]["reconciliation"] = None
            inventory = self.e.adapt_tree_response(
                self.read(role + "-tree.json"), controller_id=manifest[role]["controller_id"],
                tree=self.o.TreeName.PHYSICAL, version="0.0-test", exported_at="2026-11-18T00:00:00Z",
            ).to_inventory()
            inventories.append(inventory)
            self.write(role + "-artifact.json", inventory.to_artifact().to_dict())
            manifest[role]["input"] = {"format": "artifact", "path": role + "-artifact.json"}
        self.write("request.json", manifest)
        blocked = self.run_plan()
        self.assertIn("unacknowledged_device_access", self.codes(blocked))
        self.assertEqual(blocked.record["artifacts"]["source"]["validation"]["status"], "valid")
        self.write("empty.json", [item.to_dict() for item in device_access_acknowledgements(*inventories)])
        acknowledged = self.run_plan()
        self.assertNotIn("unacknowledged_device_access", self.codes(acknowledged))
        self.assertEqual(acknowledged.report["counts"]["BLOCKED"], 0)

    def test_invalid_root_mappings_cannot_become_create(self):
        mappings = self.read("mappings.json")
        mappings[0].update(state="missing", destination=None)
        self.write("mappings.json", mappings)
        result = self.run_plan()
        self.assertEqual(result.record["plan"]["actions"][0]["kind"], "blocked")
        self.assertIn("root_unresolved", self.codes(result))
        self.assertEqual(result.report["counts"]["CREATE"], 0)

    def test_unknown_root_metadata_is_never_excluded(self):
        tree = self.read("source-tree.json")
        tree["offlineDeviceReconciliation"] = {"acknowledgement": {"unknownSetting": True}}
        self.write("source-tree.json", tree)
        result = self.run_plan()
        self.assertEqual(result.record["plan"]["actions"][0]["kind"], "conflict")
        self.assertIn("configuration_differs", self.codes(result))

    def test_incomplete_destination_declaration_blocks_missing_objects(self):
        self.write("completeness.json", {"schema_version": 1, "trees": []})
        result = self.run_plan()
        self.assertIn("incomplete_destination", self.codes(result))
        self.assertEqual(result.report["counts"]["CREATE"], 0)

    def test_flat_inputs_require_and_use_explicit_root_context(self):
        self.root_only()
        manifest = self.read("request.json")
        self.write("flat.json", {"sites": [], "devices": []})
        for role in ("source", "destination"):
            manifest[role]["input"].update(format="flat", path="flat.json", root=role + "-tree.json")
        self.write("request.json", manifest)
        self.assertEqual(self.run_plan().exit_status, 0)
        del manifest["source"]["input"]["root"]
        self.write("request.json", manifest)
        self.assertIn("missing_field", self.codes(self.run_plan()))

    def test_structural_reconciliation_failure_retains_diagnostic_artifact(self):
        details = self.read("source-details.json")
        self.write("source-details.json", details[:-1])
        associations = self.read("source-associations.json")
        self.write("source-associations.json", associations[:-1])
        result = self.run_plan()
        self.assertEqual(result.report["workflow_result"], "failed")
        self.assertEqual(result.record["artifacts"]["source"]["validation"]["status"], "invalid")
        self.assertIn("missing_device_details", result.record["artifacts"]["source"]["validation"]["issue_codes"])
        self.assertEqual(result.report["stages"][-1]["status"], "blocked")

    def test_invalid_mapping_and_controller_identity_are_explicit_failures(self):
        original = self.read("mappings.json")
        changed = copy.deepcopy(original)
        changed[1]["source"]["object_id"] = "unknown-sensitive-id"
        self.write("mappings.json", changed)
        result = self.run_plan()
        self.assertIn("context_mismatch", self.codes(result))
        self.assertNotIn("unknown-sensitive-id", json.dumps(result.report))
        self.write("mappings.json", original)
        manifest = self.read("request.json")
        manifest["source"]["controller_id"] = "wrong-sensitive-controller"
        self.write("request.json", manifest)
        result = self.run_plan()
        self.assertEqual(result.report["workflow_result"], "failed")
        self.assertNotIn("wrong-sensitive-controller", json.dumps(result.report))

    def test_bad_manifests_and_schemas_fail_before_dependent_stages(self):
        original = self.read("request.json")
        for value, code in (
            ({**original, "schema_version": True}, "unsupported_schema"),
            ({**original, "schema_version": 2}, "unsupported_schema"),
            ({**original, "scope": "apply"}, "invalid_scope"),
            ({key: value for key, value in original.items() if key != "source"}, "missing_field"),
            ({**original, "password": "RAW-PASSWORD-MARKER"}, "unknown_fields"),
            ([], "invalid_type"),
        ):
            with self.subTest(code=code):
                self.write("request.json", value)
                result = self.run_plan()
                self.assertIn(code, self.codes(result))
                self.assertEqual(result.report["stages"][1]["status"], "blocked")
                self.assertNotIn("RAW-PASSWORD-MARKER", json.dumps(result.report) + result.record_json())

    def test_local_file_failures_are_safe_and_use_input_exit_status(self):
        for path in (
            self.directory / "missing-sensitive-name.json",
            "https://sensitive.invalid/secret",
            "\\\\sensitive-server\\private\\request.json",
        ):
            with self.subTest(path=path):
                result = self.w.plan_offline_request(path)
                self.assertEqual(result.exit_status, 3)
                self.assertEqual(result.report["workflow_result"], "failed")
                self.assertNotIn(str(path), json.dumps(result.report))
        for raw, code in (
            (b'{"schema_version":1,"schema_version":1}', "invalid_json"),
            (b'{"secret":NaN}', "invalid_json"),
            (b"\xff", "invalid_encoding"),
        ):
            self.request.write_bytes(raw)
            self.assertIn(code, self.codes(self.run_plan()))

    def test_raw_credentials_and_unsafe_evidence_never_enter_reports_or_records(self):
        tree = self.read("source-tree.json")
        tree["children"][0]["children"][0]["deviceAccess"]["password"] = "RAW-PASSWORD-MARKER"
        self.write("source-tree.json", tree)
        result = self.run_plan()
        self.assertIn("secret_value_not_allowed", self.codes(result))
        self.assertIsNone(result.record)
        self.assertNotIn("RAW-PASSWORD-MARKER", repr(result))
        self.write("source-tree.json", json.loads((self.examples / "source-tree.json").read_text()))
        policy = self.read("policy.json")
        policy["evidence_reference"] = "SESSION-TOKEN-MARKER"
        self.write("policy.json", policy)
        result = self.run_plan()
        self.assertIn("invalid_evidence_reference", self.codes(result))
        self.assertNotIn("SESSION-TOKEN-MARKER", repr(result) + result.record_json())

    def test_cli_partial_result_and_output_failures_never_overwrite_existing_files(self):
        protected = self.directory / "protected.json"
        protected.write_text("KEEP", encoding="utf-8")
        status, output, error = self.invoke("plan", "--request", str(self.request), "--record", str(protected))
        report = json.loads(output)
        self.assertEqual((status, error), (3, ""))
        self.assertEqual(report["workflow_result"], "failed")
        self.assertEqual(report["output_failure"], "output_exists")
        self.assertTrue(report["validation_failures"])
        self.assertEqual(protected.read_text(), "KEEP")
        status, output, error = self.invoke("plan", "--request", str(self.request))
        self.assertEqual((status, error), (1, ""))
        self.assertEqual(json.loads(output)["counts"]["CREATE"], 3)

    def test_absent_retained_record_and_tampered_record_fail_verification(self):
        result = self.run_plan(verify_record=self.directory / "absent.json")
        self.assertEqual(result.exit_status, 3)
        self.assertIn("input_unreadable", self.codes(result))
        retained = self.retain(self.run_plan())
        body = json.loads(retained.read_text())
        for field, value, code in (
            ("schema_version", 2, "unsupported_schema"),
            ("schema_version", True, "unsupported_schema"),
            ("scope", "apply", "invalid_scope"),
            ("report", {**body["report"], "execution_authorized": True}, "integrity_mismatch"),
        ):
            with self.subTest(field=field, value=value):
                self.write("retained.json", {**body, field: value})
                self.assertIn(code, self.codes(self.run_plan(verify_record=retained)))

    def test_artifact_credentials_fail_closed_without_records_or_secret_diagnostics(self):
        baseline = self.run_plan().record
        original = self.read("request.json")
        for role in ("source", "destination"):
            for field in ("passphrase", "authKey", "privKey", "username"):
                with self.subTest(role=role, field=field):
                    artifact = copy.deepcopy(baseline["artifacts"][role])
                    artifact["objects"][2]["device_access"]["value"][field] = "REJECTED-CREDENTIAL-MARKER"
                    self.write("unsafe-artifact.json", artifact)
                    manifest = copy.deepcopy(original)
                    manifest[role]["input"] = {"format": "artifact", "path": "unsafe-artifact.json"}
                    manifest[role]["reconciliation"] = None
                    self.write("request.json", manifest)
                    result = self.run_plan()
                    self.assertEqual(result.exit_status, 4)
                    self.assertIsNone(result.record)
                    self.assertFalse(result.report["record_available"])
                    self.assertIn("secret_value_not_allowed", self.codes(result))
                    self.assertEqual(
                        next(row["stage"] for row in result.report["stages"] if row["status"] == "failed"),
                        role,
                    )
                    contracts = importlib.import_module("cc_vision_import.contracts")
                    with self.assertRaises(contracts.ContractValidationError) as caught:
                        result.record_json()
                    self.assertEqual(caught.exception.result.issues[0].code, "record_unavailable")
                    rendered = repr(result) + repr(result.record) + repr(caught.exception) + repr(caught.exception.result)
                    self.assertNotIn("REJECTED-CREDENTIAL-MARKER", rendered)
                    for existing in (False, True):
                        output = self.directory / "rejected-record.json"
                        if existing:
                            output.write_text("KEEP", encoding="utf-8")
                        status, stdout, stderr = self.invoke(
                            "plan", "--request", str(self.request), "--record", str(output),
                        )
                        self.assertEqual((status, stderr), (4, ""))
                        self.assertEqual(json.loads(stdout), result.report)
                        self.assertNotIn("REJECTED-CREDENTIAL-MARKER", stdout + stderr)
                        if existing:
                            self.assertEqual(output.read_text(), "KEEP")
                            output.unlink()
                        else:
                            self.assertFalse(output.exists())

    def test_safe_incomplete_artifact_remains_available_for_diagnostics(self):
        details = self.read("source-details.json")
        self.write("source-details.json", details[:-1])
        self.write("source-associations.json", self.read("source-associations.json")[:-1])
        output = self.directory / "incomplete-record.json"
        status, stdout, stderr = self.invoke(
            "plan", "--request", str(self.request), "--record", str(output),
        )
        self.assertEqual((status, stderr), (4, ""))
        self.assertTrue(json.loads(stdout)["record_available"])
        saved = json.loads(output.read_text())
        self.assertEqual(saved["artifacts"]["source"]["validation"]["status"], "invalid")
        self.assertIn("missing_device_details", saved["artifacts"]["source"]["validation"]["issue_codes"])

    def test_cli_distinguishes_blocked_invalid_and_integrity_statuses(self):
        retained = self.retain(self.run_plan())
        manifest = self.read("request.json")
        self.write("request.json", {**manifest, "schema_version": 2})
        for expected, category in ((4, "invalid_input"), (1, "blocked_plan"), (5, "integrity_failure")):
            if expected == 1:
                self.write("request.json", manifest)
            args = ("--verify", str(retained)) if expected == 5 else ()
            if expected == 5:
                saved = self.read("retained.json")
                saved["report"]["execution_authorized"] = True
                self.write("retained.json", saved)
            status, stdout, stderr = self.invoke("plan", "--request", str(self.request), *args)
            report = json.loads(stdout)
            self.assertEqual((status, report["exit_code"], report["status"], stderr), (expected, expected, category, ""))
            self.assertFalse(report["execution_authorized"])
            if expected == 5:
                self.assertEqual(report["workflow_result"], "failed")
                self.assertIn("integrity_mismatch", {row["code"] for row in report["validation_failures"]})

    def test_unexpected_internal_errors_are_sanitized_and_never_persisted(self):
        for target in (
            "cc_vision_import.offline_inputs.OfflineInputs.manifest",
            "cc_vision_import.controller_workflow.compare_controller_inventories",
            "cc_vision_import.controller_workflow.verify_controller_plan",
        ):
            with self.subTest(target=target), patch(target, side_effect=RuntimeError("INTERNAL-SECRET-MARKER")):
                result = self.run_plan()
                self.assertEqual(result.exit_status, 6)
                self.assertIsNone(result.record)
                self.assertEqual(self.codes(result), {"internal_error"})
                output = self.directory / "internal-record.json"
                status, stdout, stderr = self.invoke(
                    "plan", "--request", str(self.request), "--record", str(output),
                )
                report = json.loads(stdout)
                self.assertEqual((status, report["status"], report["exit_code"], stderr), (6, "internal_failure", 6, ""))
                self.assertEqual(report["workflow_result"], "failed")
                self.assertFalse(output.exists())
                self.assertNotIn("INTERNAL-SECRET-MARKER", stdout + stderr + repr(result))
                self.assertNotIn("Traceback", stdout + stderr)

    def test_record_validation_finishes_before_output_file_creation(self):
        contracts = importlib.import_module("cc_vision_import.contracts")
        error = contracts.ContractValidationError(contracts.ValidationResult(
            "offline-workflow", "invalid",
            issues=(contracts.ValidationIssue("integrity_mismatch", "$", "Fixed safe error."),),
        ))
        output = self.directory / "uncreated-record.json"
        with patch.object(self.w.OfflineWorkflowResult, "record_json", side_effect=error):
            status, stdout, stderr = self.invoke(
                "plan", "--request", str(self.request), "--record", str(output),
            )
        self.assertEqual((status, stderr), (5, ""))
        self.assertEqual(json.loads(stdout)["status"], "integrity_failure")
        self.assertFalse(output.exists())

    def test_internal_error_during_failure_record_construction_is_sanitized(self):
        self.write("mappings.json", {})
        with patch("cc_vision_import.controller_workflow._digest", side_effect=RuntimeError("DIAGNOSTIC-SECRET")):
            result = self.run_plan()
        self.assertEqual(result.exit_status, 6)
        self.assertIsNone(result.record)
        self.assertEqual(self.codes(result), {"internal_error"})
        self.assertNotIn("DIAGNOSTIC-SECRET", repr(result))

    def test_rehashed_record_with_raw_credentials_cannot_be_serialized_or_written(self):
        result = self.run_plan()
        body = result.record
        body["artifacts"]["source"]["objects"][2]["device_access"]["value"]["passphrase"] = "REHASHED-SECRET"
        unsigned = {key: value for key, value in body.items() if key != "integrity_sha256"}
        body["integrity_sha256"] = hashlib.sha256(json.dumps(
            unsigned, separators=(",", ":"), ensure_ascii=True, allow_nan=False,
        ).encode()).hexdigest()
        contracts = importlib.import_module("cc_vision_import.contracts")
        with self.assertRaises(contracts.ContractValidationError) as caught:
            result.record_json()
        self.assertEqual(caught.exception.result.issues[0].code, "secret_value_not_allowed")
        self.assertNotIn("REHASHED-SECRET", repr(caught.exception) + repr(caught.exception.result))
        output = self.directory / "rehash-rejected.json"
        with patch("cc_vision_import.cli.plan_offline_request", return_value=result):
            status, stdout, stderr = self.invoke("plan", "--request", str(self.request), "--record", str(output))
        self.assertEqual((status, stderr), (4, ""))
        self.assertFalse(output.exists())
        self.assertFalse(json.loads(stdout)["record_available"])
        self.assertNotIn("REHASHED-SECRET", stdout)

    def test_partial_output_is_cleaned_up_after_write_failures(self):
        output = self.directory / "partial-record.json"
        real_open = Path.open
        for failure, expected in ((OSError("WRITE-SECRET-MARKER"), 3), (RuntimeError("WRITE-SECRET-MARKER"), 6)):
            with self.subTest(expected=expected):
                def failing_open(path, *args, **kwargs):
                    stream = real_open(path, *args, **kwargs)
                    if path == output and args and args[0] == "x":
                        write = stream.write
                        def write_then_fail(value):
                            write(value[:32])
                            raise failure
                        stream.write = write_then_fail
                    return stream

                with patch.object(Path, "open", failing_open):
                    status, stdout, stderr = self.invoke(
                        "plan", "--request", str(self.request), "--record", str(output),
                    )
                self.assertEqual((status, stderr), (expected, ""))
                self.assertEqual(json.loads(stdout)["workflow_result"], "failed")
                self.assertFalse(output.exists())
                self.assertNotIn("WRITE-SECRET-MARKER", stdout + stderr)

    def test_cleanup_failures_remain_structured_and_sanitized(self):
        output = self.directory / "cleanup-failed-record.json"
        real_open = Path.open
        for write_error, error, expected, category in (
            (OSError("WRITE-SECRET-MARKER"), PermissionError("CLEANUP-SECRET-MARKER"), 3, "input_output_error"),
            (OSError("WRITE-SECRET-MARKER"), RuntimeError("CLEANUP-SECRET-MARKER"), 6, "internal_failure"),
            (RuntimeError("WRITE-SECRET-MARKER"), RuntimeError("CLEANUP-SECRET-MARKER"), 6, "internal_failure"),
        ):
            with self.subTest(write_error=type(write_error).__name__, error=type(error).__name__):
                streams = []
                def failing_open(path, *args, **kwargs):
                    stream = real_open(path, *args, **kwargs)
                    if path == output and args and args[0] == "x":
                        streams.append(stream)
                        write = stream.write
                        def write_then_fail(value):
                            write(value[:32])
                            raise write_error
                        stream.write = write_then_fail
                    return stream

                try:
                    with patch.object(Path, "open", failing_open), patch.object(Path, "unlink", side_effect=error):
                        status, stdout, stderr = self.invoke(
                            "plan", "--request", str(self.request), "--record", str(output),
                        )
                    report = json.loads(stdout)
                    self.assertEqual((status, report["exit_code"], report["status"], stderr), (expected, expected, category, ""))
                    self.assertEqual(report["workflow_result"], "failed")
                    self.assertEqual(report["output_cleanup_failure"], "output_cleanup_failed")
                    self.assertEqual(report["output_failure"], "internal_error" if expected == 6 else "output_unwritable")
                    if expected == 6:
                        self.assertEqual(
                            report["original_output_failure"],
                            "output_unwritable" if isinstance(write_error, OSError) else "internal_error",
                        )
                    else:
                        self.assertNotIn("original_output_failure", report)
                    self.assertFalse(report["record_available"])
                    self.assertFalse(report["execution_authorized"])
                    self.assertTrue(output.exists())
                    self.assertTrue(all(stream.closed for stream in streams))
                    self.assertNotIn("SECRET-MARKER", stdout + stderr)
                    self.assertNotIn(output.name, stdout + stderr)
                    self.assertNotIn("Traceback", stdout + stderr)
                finally:
                    output.unlink(missing_ok=True)
