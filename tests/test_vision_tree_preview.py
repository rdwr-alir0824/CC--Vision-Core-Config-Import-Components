import copy
import importlib
import io
import json
from contextlib import redirect_stdout

from offline_support import OfflineTestCase


class VisionTreePreviewTests(OfflineTestCase):
    def setUp(self):
        super().setUp()
        self.cli = importlib.import_module("cc_vision_import.master_cli")
        self.preview = importlib.import_module("cc_vision_import.vision_tree_preview")
        self.payload = {
            "schema_version": 1, "domain": "vision-physical-tree",
            "source": {"product": "vision", "version": "5.4.9", "name": "private-name-marker"},
            "collected_at": "2026-11-25T12:00:00+00:00",
            "request": {"method": "GET", "path": "/mgmt/system/config/tree/Physical"},
            "scope": {"complete_configuration_backup": False, "migration_input": False},
            "evidence": {"master_live_tested": False}, "record_count": 1,
            "record_count_basis": "top_level_json_records", "redacted_fields": 2, "issue_codes": [],
            "tree": {
                "meIdentifier": {"managedElementID": "private-root-marker"},
                "children": [{
                    "meIdentifier": {
                        "managedElementID": "private-site-marker",
                        "managedElementClass": "com.radware.insite.model.device.Site",
                    },
                    "name": "private-name-marker", "parentOrmID": "private-root-marker",
                    "children": [{
                        "meIdentifier": {
                            "managedElementID": "private-device-marker",
                            "managedElementClass": "com.radware.insite.model.device.Device",
                        },
                        "name": "private-name-marker", "managementIp": "192.0.2.44", "children": [],
                        "password": "private-secret-marker",
                    }],
                }],
            },
        }

    def invoke_preview(self, *extra):
        self.input_path.write_text(json.dumps(self.payload), encoding="utf-8")
        raw = self.input_path.read_bytes()
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            status = self.cli.main([
                "--operation", "tree-readiness-preview", "--input", str(self.input_path), *extra,
            ])
        self.assertEqual(self.input_path.read_bytes(), raw)
        for marker in ("private-", "192.0.2.44"):
            self.assertNotIn(marker, stdout.getvalue())
        return status, stdout.getvalue()

    def test_both_real_envelopes_have_safe_structured_and_text_reports(self):
        for tree in ("Physical", "Organization"):
            self.payload["domain"] = "vision-" + tree.lower() + "-tree"
            self.payload["request"]["path"] = "/mgmt/system/config/tree/" + tree
            before = copy.deepcopy(self.payload)
            status, text = self.invoke_preview()
            self.assertEqual(status, 1)
            self.assertIn("node candidates inspected: 3", text)
            self.assertIn("BLOCKED", text)
            output = self.directory / (tree + "-preview.json")
            status, serialized = self.invoke_preview("--report-format", "json", "--output", str(output))
            report = json.loads(serialized)
            self.assertEqual(report, json.loads(output.read_text()))
            self.assertEqual(report["counts"], {"root-candidate": 1, "site": 1, "device": 1, "unknown": 0})
            self.assertEqual(report["verified_semantic_parent_relationships"], 0)
            self.assertEqual(report["nodes"][1]["depends_on"], ["node-1"])
            self.assertEqual(report["nodes"][2]["depends_on"], ["node-2"])
            self.assertEqual(report["nodes"][1]["parent_relationship"], "inferred-from-legacy-nesting")
            self.assertEqual(report["nodes"][0]["destination_mapping"], "required")
            self.assertFalse(report["migration_ready"])
            self.assertFalse(report["execution_authorized"])
            self.assertTrue(report["offline_only"])
            self.assertEqual(self.payload, before)
            status, serialized = self.invoke_preview("--report-format", "json", "--output", str(output))
            self.assertEqual(status, 3)
            self.assertEqual(json.loads(serialized)["errors"][0]["code"], "output_exists")

    def test_unknown_duplicate_missing_and_conflicting_fields_remain_blockers(self):
        site = self.payload["tree"]["children"][0]
        device = site["children"][0]
        site["meIdentifier"]["managedElementID"] = "private-root-marker"
        site["parentOrmID"] = "private-missing-marker"
        device["meIdentifier"]["managedElementID"] = None
        device["parentOrmID"] = "private-root-marker"
        site["children"].append({
            "meIdentifier": {"managedElementID": "private-other-marker", "managedElementClass": "private-unknown-marker"},
            "children": None, "private-secret-field": "private-secret-marker",
        })
        self.payload["tree"]["children"].append(None)
        status, text = self.invoke_preview("--report-format", "json")
        self.assertEqual(status, 1)
        report = json.loads(text)
        for code in (
            "duplicate_identity", "identity_missing_or_unverified_type", "unknown_node_class",
            "explicit_parent_unresolved", "parent_dependency_unresolved", "unknown_fields_unverified",
            "children_missing_or_unverified_type", "invalid_node",
        ):
            self.assertIn(code, report["issue_codes"])
        self.assertEqual(report["node_candidates_inspected"], 5)
        self.assertEqual(report["nodes"][2]["depends_on"], [])

    def test_explicit_parent_mismatch_is_not_used_to_reparent(self):
        site = self.payload["tree"]["children"][0]
        site["children"][0]["parentOrmID"] = "private-root-marker"
        report = self.preview.inspect_vision_tree(self.payload)
        self.assertIn("explicit_parent_conflicts_with_nesting", report["nodes"][2]["issue_codes"])
        self.assertEqual(report["nodes"][2]["observed_container_parent"], "node-2")
        self.assertEqual(report["nodes"][2]["depends_on"], [])
        self.assertEqual(report["nodes"][2]["parent_relationship"], "unresolved-explicit-parent")

    def test_array_roots_and_unrecognized_structure_do_not_become_complete_trees(self):
        for native in ([], [{"opaque": "private-secret-marker"}], {"children": "private-secret-marker"}):
            self.payload["tree"] = native
            self.payload["record_count"] = len(native) if isinstance(native, list) else 1
            status, text = self.invoke_preview("--report-format", "json")
            self.assertEqual(status, 1)
            report = json.loads(text)
            self.assertFalse(report["migration_ready"])
            self.assertEqual(report["verified_semantic_parent_relationships"], 0)
            if isinstance(native, list):
                self.assertIn("array_root_semantics_unverified", report["issue_codes"])

    def test_invalid_envelopes_and_nonlocal_inputs_fail_without_raw_echo(self):
        original = copy.deepcopy(self.payload)
        for key, bad in (
            ("tree", None), ("schema_version", True), ("source", {"product": "cyber-controller"}),
            ("domain", "private-secret-marker"), ("request", {"method": "POST", "path": "private-secret-marker"}),
            ("record_count", 3), ("redacted_fields", -1), ("scope", {"migration_input": True}),
        ):
            self.payload = copy.deepcopy(original)
            self.payload[key] = bad
            status, text = self.invoke_preview("--report-format", "json")
            self.assertEqual(status, 4)
            self.assertEqual(json.loads(text)["status"], "error")
        for path in ("https://private.invalid/tree.json", r"\\private-host\share\tree.json"):
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                status = self.cli.main(["--operation", "tree-readiness-preview", "--input", path, "--report-format", "json"])
            self.assertEqual(status, 3)
            self.assertEqual(json.loads(stdout.getvalue())["errors"][0]["code"], "nonlocal_input")

    def test_strict_json_and_depth_limits_are_safe_failures(self):
        self.input_path.write_text('{"password":"private-secret-marker","password":null}', encoding="utf-8")
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            status = self.cli.main(["--operation", "tree-readiness-preview", "--input", str(self.input_path), "--report-format", "json"])
        self.assertEqual(status, 3)
        self.assertNotIn("private-secret-marker", stdout.getvalue())
        node = self.payload["tree"]
        for _ in range(66):
            child = {"children": []}
            node["children"] = [child]
            node = child
        status, text = self.invoke_preview("--report-format", "json")
        self.assertEqual(status, 4)
        self.assertEqual(json.loads(text)["errors"][0]["code"], "preview_limit_exceeded")

    def test_legacy_flat_contract_assessment_does_not_require_inventory_crosswalk(self):
        self.payload["tree"]["children"][0]["children"][0]["type"] = "private-type-marker"
        before = copy.deepcopy(self.payload)
        report = self.preview.inspect_legacy_tree_compatibility(self.payload)
        self.assertEqual(report["compatibility_counts"]["site_records_assessed"], 1)
        self.assertEqual(report["compatibility_counts"]["device_records_assessed"], 1)
        self.assertEqual(report["compatibility_counts"]["devices_without_access"], 1)
        device = report["legacy_field_assessments"][1]
        self.assertEqual(device["legacy_fields_missing"], ["deviceAccess"])
        self.assertEqual(device["source_parent_reference"], "node-2")
        self.assertIn("id", device["legacy_fields_available"])
        self.assertFalse(report["inventory_identity_crosswalk_required_for_tree_subset"])
        self.assertFalse(report["source_ids_reassigned"])
        self.assertFalse(report["import_file_compatible"])
        self.assertFalse(report["execution_authorized"])
        self.assertNotIn("sites", report)
        self.assertNotIn("devices", report)
        self.assertEqual(self.payload, before)
        self.assertNotIn("private-", json.dumps(report))
        parse = importlib.import_module("cc_vision_import.controller_objects").parse_controller_artifact
        error = importlib.import_module("cc_vision_import.contracts").ContractValidationError
        with self.assertRaises(error):
            parse(report)

    def test_legacy_access_and_credentials_are_inspected_without_enrichment_or_mutation(self):
        device = self.payload["tree"]["children"][0]["children"][0]
        device["type"] = "private-type-marker"
        for field in ("deviceAccess", "deviceSetup"):
            access = {"cliUsername": None, "cliPassword": "*****", "ormID": "private-access-marker"}
            device[field] = access if field == "deviceAccess" else {"deviceAccess": access}
            before = copy.deepcopy(self.payload)
            report = self.preview.inspect_legacy_tree_compatibility(self.payload)
            result = report["legacy_field_assessments"][1]
            self.assertEqual(result["legacy_fields_missing"], [])
            self.assertIn("credential_values_missing_redacted_or_masked", result["issue_codes"])
            self.assertIn("device_access_ids_preserved_not_aliased_or_deleted", result["issue_codes"])
            self.assertIn("device_type_and_form_factor_passthrough_unqualified", result["issue_codes"])
            self.assertFalse(report["migration_ready"])
            self.assertEqual(self.payload, before)
            self.assertNotIn("private-", json.dumps(report))
            del device[field]
        device["deviceAccess"] = {"ormID": "private-direct-marker"}
        device["deviceSetup"] = {"deviceAccess": {"ormID": "private-nested-marker"}}
        report = self.preview.inspect_legacy_tree_compatibility(self.payload)
        self.assertIn("device_access_representations_conflict", report["issue_codes"])
        self.assertEqual(report["compatibility_counts"]["devices_without_access"], 1)

    def test_legacy_global_name_lookup_and_unknown_nodes_are_reported_not_normalized(self):
        site = self.payload["tree"]["children"][0]
        nested = copy.deepcopy(site)
        nested["meIdentifier"]["managedElementID"] = "private-other-site-marker"
        nested["parentOrmID"] = "private-site-marker"
        nested["children"] = []
        site["children"].append(nested)
        site["children"].append({
            "meIdentifier": {"managedElementID": "private-unknown-marker", "managedElementClass": "private-class-marker"},
            "children": [], "private-field": "private-secret-marker",
        })
        site["children"][0].pop("type", None)
        report = self.preview.inspect_legacy_tree_compatibility(self.payload)
        self.assertIn("legacy_global_site_name_lookup_ambiguous", report["issue_codes"])
        self.assertIn("unsupported_node_not_dropped", report["issue_codes"])
        self.assertEqual(len(report["legacy_field_assessments"]), 4)
        self.assertIn("type", report["legacy_field_assessments"][1]["legacy_fields_missing"])
        self.assertNotIn("private-", json.dumps(report))

    def test_legacy_cli_report_is_non_importable_for_both_trees(self):
        for tree in ("Physical", "Organization"):
            self.payload["domain"] = "vision-" + tree.lower() + "-tree"
            self.payload["request"]["path"] = "/mgmt/system/config/tree/" + tree
            output = self.directory / (tree + "-legacy-preview.json")
            status, text = self.invoke_preview("--legacy-compatibility", "--report-format", "json", "--output", str(output))
            self.assertEqual(status, 1)
            report = json.loads(text)
            self.assertEqual(report["domain"], "vision-legacy-compatibility-report")
            self.assertEqual(report, json.loads(output.read_text()))
            self.assertNotIn("sites", report)
            self.assertNotIn("devices", report)
            status, text = self.invoke_preview("--legacy-compatibility")
            self.assertEqual(status, 1)
            self.assertIn("not a legacy sites/devices import file", text)

    def test_legacy_array_roots_and_invalid_child_arrays_keep_node_alignment(self):
        self.payload["tree"]["children"].insert(0, [])
        report = self.preview.inspect_legacy_tree_compatibility(self.payload)
        self.assertEqual(report["legacy_field_assessments"][0]["kind"], "unknown")
        self.assertEqual(report["legacy_field_assessments"][1]["kind"], "site")
        self.assertEqual(report["legacy_field_assessments"][2]["kind"], "device")
        self.assertEqual(report["legacy_field_assessments"][2]["source_parent_reference"], "node-3")
        self.payload["tree"] = [self.payload["tree"]]
        report = self.preview.inspect_legacy_tree_compatibility(self.payload)
        self.assertIn("array_root_semantics_unverified", report["issue_codes"])
        self.assertFalse(report["migration_ready"])

    def organization_sites(self):
        self.payload["domain"] = "vision-organization-tree"
        self.payload["request"]["path"] = "/mgmt/system/config/tree/Organization"
        root = self.payload["tree"]
        root["name"] = "private-root-name-marker"
        root["meIdentifier"]["managedElementClass"] = "com.radware.insite.model.device.Site"
        site = root["children"][0]
        child = copy.deepcopy(site)
        child["meIdentifier"]["managedElementID"] = "private-child-site-marker"
        child["parentOrmID"] = "private-site-marker"
        child["name"] = "private-child-name-marker"
        child["children"] = []
        site["children"].append(child)
        return root, site, child

    def test_sites_project_source_reference_fields_and_order_without_destination_payloads(self):
        root, site, child = self.organization_sites()
        child["private-unknown-field"] = "private-secret-marker"
        before = copy.deepcopy(self.payload)
        report = self.preview.inspect_site_migration_readiness(self.payload)
        self.assertEqual(self.payload, before)
        self.assertEqual(report["counts"]["site_candidates_inspected"], 2)
        self.assertEqual(report["counts"]["sites_with_sufficient_source_fields"], 2)
        self.assertEqual(report["counts"]["sites_orderable_from_source_root"], 2)
        self.assertEqual(report["counts"]["sites_with_unprojected_fields"], 1)
        self.assertEqual(report["source_dependency_order"], ["node-2", "node-4"])
        self.assertTrue(report["root_assessment"]["source_fields_usable"])
        self.assertFalse(report["root_assessment"]["emitted_as_site"])
        self.assertEqual(report["site_candidates"][1]["source_parent_reference"], "node-2")
        for row in report["site_candidates"]:
            self.assertEqual(set(row["legacy_fields_available"]), {"id", "name", "parentOrmID", "parent_site_name"})
            self.assertEqual(row["destination_mapping"], "required")
        self.assertFalse(report["migration_ready"])
        self.assertFalse(report["import_file_compatible"])
        self.assertFalse(report["execution_authorized"])
        self.assertNotIn("sites", report)
        self.assertNotIn("devices", report)
        self.assertNotIn("private-", json.dumps(report))
        parse = importlib.import_module("cc_vision_import.controller_objects").parse_controller_artifact
        error = importlib.import_module("cc_vision_import.contracts").ContractValidationError
        with self.assertRaises(error):
            parse(report)
        original = copy.deepcopy(report)
        device = site["children"][0]
        device["meIdentifier"]["managedElementID"] = None
        device["name"] = None
        device["managementIp"] = "private-unused-marker"
        self.assertEqual(self.preview.inspect_site_migration_readiness(self.payload), original)

    def test_sites_keep_name_ambiguity_separate_from_source_fields_and_ordering(self):
        root, site, child = self.organization_sites()
        child["name"] = site["name"]
        report = self.preview.inspect_site_migration_readiness(self.payload)
        self.assertEqual(report["counts"]["sites_with_sufficient_source_fields"], 2)
        self.assertEqual(report["counts"]["sites_orderable_from_source_root"], 2)
        self.assertEqual(report["counts"]["sites_with_duplicate_names"], 2)
        self.assertEqual(report["counts"]["sites_with_ambiguous_parent_names"], 1)
        self.assertIn("legacy_global_parent_name_lookup_ambiguous", report["issue_codes"])
        self.assertFalse(report["migration_ready"])
        self.assertNotIn("private-", json.dumps(report))

    def test_sites_missing_names_duplicate_ids_and_parent_conflicts_block_without_fallback(self):
        root, site, child = self.organization_sites()
        site["name"] = None
        report = self.preview.inspect_site_migration_readiness(self.payload)
        self.assertEqual(report["counts"]["sites_with_missing_source_fields"], 2)
        self.assertEqual(report["source_dependency_order"], [])
        self.assertIn("name", report["site_candidates"][0]["legacy_fields_missing"])
        self.assertIn("parent_site_name", report["site_candidates"][1]["legacy_fields_missing"])
        site["name"] = "private-site-name-marker"
        child["parentOrmID"] = "private-root-marker"
        report = self.preview.inspect_site_migration_readiness(self.payload)
        self.assertEqual(report["source_dependency_order"], ["node-2"])
        self.assertIsNone(report["site_candidates"][1]["source_parent_reference"])
        self.assertIn("explicit_parent_conflicts_with_nesting", report["issue_codes"])
        child["parentOrmID"] = "private-site-marker"
        child["meIdentifier"]["managedElementID"] = "private-site-marker"
        report = self.preview.inspect_site_migration_readiness(self.payload)
        self.assertEqual(report["source_dependency_order"], [])
        self.assertEqual(report["counts"]["sites_with_sufficient_source_fields"], 0)
        self.assertIn("duplicate_identity", report["issue_codes"])
        self.assertNotIn("private-", json.dumps(report))

    def test_sites_require_a_named_identified_site_root_and_report_unknown_parent_structure(self):
        root, site, child = self.organization_sites()
        for change in ("name", "class", "identity", "array"):
            payload = copy.deepcopy(self.payload)
            if change == "name":
                del payload["tree"]["name"]
            elif change == "class":
                del payload["tree"]["meIdentifier"]["managedElementClass"]
            elif change == "identity":
                del payload["tree"]["meIdentifier"]["managedElementID"]
            else:
                payload["tree"] = [payload["tree"]]
            report = self.preview.inspect_site_migration_readiness(payload)
            self.assertFalse(report["root_assessment"]["source_fields_usable"])
            self.assertEqual(report["source_dependency_order"], [])
        site["meIdentifier"]["managedElementClass"] = "private-unknown-class"
        report = self.preview.inspect_site_migration_readiness(self.payload)
        self.assertEqual(report["counts"]["site_candidates_inspected"], 1)
        self.assertEqual(report["counts"]["unclassified_structure_nodes"], 1)
        self.assertEqual(report["counts"]["sites_with_unresolved_parent_dependencies"], 1)
        self.assertEqual(report["source_dependency_order"], [])
        self.assertIn("unclassified_structure_nodes_present", report["issue_codes"])

    def test_sites_cli_text_json_exclusive_reports_and_physical_tree_rejection(self):
        self.organization_sites()
        output = self.directory / "site-readiness.json"
        status, text = self.invoke_preview("--site-readiness")
        self.assertEqual(status, 1)
        self.assertIn("Source Site assessment", text)
        self.assertNotIn("credential", text)
        status, text = self.invoke_preview("--site-readiness", "--report-format", "json", "--output", str(output))
        self.assertEqual(status, 1)
        self.assertEqual(json.loads(text), json.loads(output.read_text()))
        status, text = self.invoke_preview("--site-readiness", "--report-format", "json", "--output", str(output))
        self.assertEqual(status, 3)
        self.assertEqual(json.loads(text)["errors"][0]["code"], "output_exists")
        self.payload["domain"] = "vision-physical-tree"
        self.payload["request"]["path"] = "/mgmt/system/config/tree/Physical"
        status, text = self.invoke_preview("--site-readiness", "--report-format", "json")
        self.assertEqual(status, 4)
        self.assertEqual(json.loads(text)["errors"][0]["code"], "unsupported_site_tree")
        with self.assertRaises(SystemExit) as caught:
            self.cli.main(["--operation", "operations", "--site-readiness"])
        self.assertEqual(caught.exception.code, 2)
