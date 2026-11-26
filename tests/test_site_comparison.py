"""Synthetic Site evidence only; never a substitute for unavailable saved backups."""

import copy
import importlib
import io
import json
from contextlib import redirect_stderr, redirect_stdout
from unittest.mock import patch

from offline_support import OfflineTestCase


SITE = "com.radware.insite.model.device.Site"


def site(identity, name, *children):
    return {
        "name": name, "meIdentifier": {"managedElementID": identity, "managedElementClass": SITE},
        "children": list(children),
    }


class SiteComparisonTests(OfflineTestCase):
    def setUp(self):
        super().setUp()
        self.module = importlib.import_module("cc_vision_import.site_comparison")
        self.cli = importlib.import_module("cc_vision_import.master_cli")
        self.discovery = importlib.import_module("cc_vision_import.destination_discovery")
        self.source = {
            "schema_version": 1, "domain": "vision-organization-tree",
            "source": {"product": "vision", "version": "5.4.9", "name": "private-source"},
            "collected_at": "2026-11-25T12:00:00+00:00",
            "request": {"method": "GET", "path": "/mgmt/system/config/tree/Organization"},
            "scope": {"migration_input": False, "complete_configuration_backup": False},
            "evidence": {"master_live_tested": False}, "record_count": 1,
            "record_count_basis": "top_level_json_records", "redacted_fields": 0, "issue_codes": [],
            "tree": site("private-source-root-id", "private-source-root",
                         site("private-source-site-id", "private-site")),
        }
        self.destination = self.snapshot(site("private-destination-root-id", "private-destination-root"))
        self.root_options = {
            "source_root_name": "private-source-root", "destination_root_name": "private-destination-root",
            "confirm_root_mapping": True,
        }

    def snapshot(self, tree):
        return {
            "schema_version": 1, "domain": "cc-destination-organization-sites",
            "destination": {"product": "cyber-controller", "name": "private-controller",
                            "version": "unknown", "version_verification": "unverified"},
            "collected_at": "2026-11-26T00:00:00+00:00",
            "request": {"method": "GET", "path": "/mgmt/system/config/tree/Organization"},
            "scope": {"read_only": True, "configuration_writes_authorized": False,
                      "migration_input": False, "complete_site_enumeration": False, "devices_excluded": True},
            **self.discovery.project_site_tree(tree),
        }

    def compare(self, **options):
        before = copy.deepcopy((self.source, self.destination))
        report = self.module.compare_sites(self.source, self.destination, **{**self.root_options, **options})
        self.assertEqual((self.source, self.destination), before)
        for value in ("private-", "192.0.2.1"):
            self.assertNotIn(value, json.dumps(report))
        self.assertFalse(report["migration_ready"])
        self.assertFalse(report["execution_authorized"])
        self.assertFalse(report["configuration_writes_authorized"])
        self.assertFalse(report["import_file_compatible"])
        self.assertFalse(report["devices_processed"])
        return report

    def test_thirty_source_sites_empty_destination_and_parent_before_child_dependencies(self):
        parent = self.source["tree"]
        for number in range(30):
            child = site(f"private-site-id-{number}", f"private-site-name-{number}")
            parent["children"] = [child]
            parent = child
        parent["private-config"] = {"private-value": "private-secret"}
        report = self.compare(destination_gui_version="10.15.0-2")
        counts = report["counts"]
        self.assertEqual(counts["source_sites"], 30)
        self.assertEqual(counts["destination_sites"], 0)
        self.assertEqual(counts["candidate_for_creation"], 30)
        self.assertEqual(counts["potential_creations_if_mappings_qualified"], 30)
        self.assertEqual(counts["sites_requiring_parent_destination_identity"], 29)
        self.assertEqual(counts["source_sites_with_unprojected_fields"], 1)
        self.assertEqual(report["root_mapping"]["status"], "confirmed")
        self.assertFalse(report["identity_policy"]["root_identity_equivalence_claimed"])
        self.assertEqual(report["source_dependency_order"], [f"source:node-{number}" for number in range(2, 32)])
        self.assertEqual(report["site_comparisons"][0]["parent_destination_reference_candidate"], "destination:node-1")
        self.assertEqual(report["site_comparisons"][1]["requires_destination_identity_from_source_parent"], "source:node-2")
        self.assertEqual(report["provenance"]["destination"]["gui_observed_version"], "10.15.0-2")
        self.assertIsNone(report["provenance"]["destination"]["api_verified_version"])
        self.assertFalse(report["provenance"]["destination"]["complete_site_enumeration"])

    def test_missing_proposed_and_wrong_root_declarations_never_auto_map_or_rename(self):
        for options, expected in (
            ({"source_root_name": None, "destination_root_name": None, "confirm_root_mapping": False}, "missing"),
            ({"confirm_root_mapping": False}, "proposed"),
            ({"destination_root_name": "private-other-root"}, "mismatch"),
        ):
            report = self.compare(**options)
            self.assertEqual(report["root_mapping"]["status"], expected)
            self.assertEqual(report["counts"]["blocked_insufficient_evidence"], 1)
            self.assertEqual(report["counts"]["potential_creations_if_mappings_qualified"], 1)
            self.assertFalse(report["root_mapping"]["operator_confirmed"])
            self.assertFalse(report["root_mapping"]["roots_renamed"])

    def test_unique_name_collision_is_only_a_possible_existing_site_not_identity_mapping(self):
        self.destination = self.snapshot(site("private-destination-root-id", "private-destination-root",
                                            site("private-destination-site-id", "private-site")))
        report = self.compare()
        self.assertEqual(report["counts"]["possible_existing_destination_site"], 1)
        self.assertEqual(report["counts"]["candidate_for_creation"], 0)
        record = report["site_comparisons"][0]
        self.assertEqual(record["destination_candidates"], ["destination:node-2"])
        self.assertFalse(record["destination_identity_assigned"])
        self.assertIn("name_and_containment_candidate_not_identity_equivalence", record["issue_codes"])
        self.source["tree"]["children"][0]["name"] = "private-new-name"
        self.source["tree"]["children"][0]["meIdentifier"]["managedElementID"] = "private-destination-site-id"
        self.assertEqual(self.compare()["counts"]["candidate_for_creation"], 1)

    def test_duplicate_names_root_collisions_and_wrong_destination_parents_are_ambiguous(self):
        for children, duplicate_groups in (
            ([site("private-id-1", "private-site"), site("private-id-2", "private-site")], 1),
            ([site("private-parent-id", "private-parent", site("private-id-1", "private-site"))], 0),
        ):
            self.destination = self.snapshot(site("private-destination-root-id", "private-destination-root", *children))
            report = self.compare()
            self.assertEqual(report["counts"]["ambiguous_mapping"], 1)
            self.assertEqual(report["counts"]["destination_duplicate_name_groups"], duplicate_groups)
        self.source["tree"]["children"][0]["name"] = "private-destination-root"
        report = self.compare()
        self.assertEqual(report["counts"]["ambiguous_mapping"], 1)
        self.assertEqual(report["counts"]["candidate_for_creation"], 0)

    def test_source_parent_conflict_blocks_descendants_without_reparenting(self):
        parent = self.source["tree"]["children"][0]
        parent["parentOrmID"] = "private-nonexistent-parent"
        parent["children"] = [site("private-child-id", "private-child")]
        report = self.compare()
        self.assertEqual(report["counts"]["blocked_insufficient_evidence"], 2)
        self.assertEqual(report["source_dependency_order"], [])
        self.assertIn("source_fields_or_dependencies_insufficient", report["site_comparisons"][0]["issue_codes"])

    def test_unqualified_destination_structure_and_metadata_remain_explicit_blockers(self):
        self.destination["destination"]["version"] = "10.15.0-2"
        self.destination["destination"]["version_verification"] = "operator-GUI-observed"
        report = self.compare()
        self.assertEqual(report["counts"]["candidate_for_creation"], 1)
        self.assertIn("destination_version_api_unverified", report["blockers"])
        self.assertIsNone(report["provenance"]["destination"]["api_verified_version"])
        self.destination["counts"]["unclassified_nodes"] = 1
        report = self.compare()
        self.assertEqual(report["counts"]["blocked_insufficient_evidence"], 1)
        self.assertIn("destination_structure_or_collision_evidence_insufficient", report["blockers"])
        self.destination = self.snapshot(site("private-root", "private-destination-root",
                                            site("private-duplicate", "private-site"),
                                            site("private-duplicate", "private-other-site")))
        report = self.compare()
        self.assertEqual(report["counts"]["candidate_for_creation"], 0)
        self.assertEqual(report["counts"]["ambiguous_mapping"], 1)

    def test_possible_existing_parent_is_context_only_and_children_need_destination_resolution(self):
        self.source["tree"]["children"][0]["children"] = [site("private-child-source-id", "private-child")]
        self.destination = self.snapshot(site("private-destination-root-id", "private-destination-root",
                                            site("private-parent-destination-id", "private-site")))
        report = self.compare()
        self.assertEqual(report["counts"]["possible_existing_destination_site"], 1)
        self.assertEqual(report["counts"]["candidate_for_creation"], 1)
        child = report["site_comparisons"][1]
        self.assertEqual(child["parent_destination_reference_candidate"], "destination:node-2")
        self.assertEqual(child["requires_destination_identity_from_source_parent"], "source:node-2")
        self.assertFalse(child["destination_identity_assigned"])

    def test_orphan_and_explicit_conflict_evidence_is_not_attached_to_root_or_ignored(self):
        self.destination = self.snapshot(site("private-destination-root-id", "private-destination-root",
                                            site("private-destination-site-id", "private-site")))
        row = self.destination["site_nodes"][0]
        row["observed_container_parent"] = "node-99"
        row["parent_relationship"] = "unresolved"
        row["issue_codes"].append("private-injected-code")
        report = self.compare()
        self.assertEqual(report["counts"]["ambiguous_mapping"], 1)
        self.assertIn("destination_structure_or_collision_evidence_insufficient", report["blockers"])
        row["observed_container_parent"] = "node-1"
        row["parent_relationship"] = "legacy-nesting-inferred"
        row["issue_codes"] = []
        row["native"]["parentOrmID"] = "private-wrong-parent"
        report = self.compare()
        self.assertEqual(report["counts"]["ambiguous_mapping"], 1)

    def test_invalid_snapshot_scopes_counts_and_device_records_fail_as_invalid_evidence(self):
        error = importlib.import_module("cc_vision_import.contracts").ContractValidationError
        for change in ("scope", "count", "device"):
            snapshot = copy.deepcopy(self.destination)
            if change == "scope":
                snapshot["scope"]["migration_input"] = True
            elif change == "count":
                snapshot["counts"]["site_candidates"] = 30
            else:
                snapshot = self.snapshot(site("private-destination-root-id", "private-destination-root",
                                              site("private-site-id", "private-site")))
                snapshot["site_nodes"][0]["native"]["meIdentifier"]["managedElementClass"] = "com.radware.insite.model.device.Device"
            with self.assertRaises(error):
                self.module.compare_sites(self.source, snapshot, **self.root_options)

    def test_cli_writes_sanitized_bound_report_leaves_inputs_unchanged_and_never_overwrites(self):
        source_path, destination_path = self.directory / "source.json", self.directory / "destination.json"
        source_path.write_text(json.dumps(self.source), encoding="utf-8")
        destination_path.write_text(json.dumps(self.destination), encoding="utf-8")
        output = self.directory / "comparison.json"
        originals = (source_path.read_bytes(), destination_path.read_bytes())
        arguments = [
            "--operation", "site-comparison", "--input", str(source_path),
            "--destination-snapshot", str(destination_path), "--source-root-name", "private-source-root",
            "--destination-root-name", "private-destination-root", "--output", str(output),
        ]
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            status = self.cli.main(arguments)
        self.assertEqual(status, 1)
        self.assertIn("Root mapping: proposed", stdout.getvalue())
        self.assertNotIn("private-", stdout.getvalue())
        report = json.loads(output.read_text())
        self.assertEqual([row["slot"] for row in report["input_bindings"]],
                         ["source-organization-tree", "destination-organization-sites"])
        self.assertTrue(all(len(row["sha256"]) == 64 for row in report["input_bindings"]))
        self.assertEqual((source_path.read_bytes(), destination_path.read_bytes()), originals)
        written = output.read_bytes()
        with redirect_stdout(io.StringIO()):
            self.assertEqual(self.cli.main([*arguments, "--report-format", "json"]), 3)
        self.assertEqual(output.read_bytes(), written)
        artifacts = importlib.import_module("cc_vision_import.artifacts")
        with self.assertRaises(ValueError):
            artifacts.parse_artifact(report)

    def test_missing_snapshot_and_live_options_fail_without_substitution_or_dispatch(self):
        self.input_path.write_text(json.dumps(self.source), encoding="utf-8")
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            status = self.cli.main(["--operation", "site-comparison", "--input", str(self.input_path),
                                    "--destination-snapshot", str(self.directory / "missing.json"), "--report-format", "json"])
        self.assertEqual(status, 3)
        self.assertEqual(json.loads(stdout.getvalue())["errors"], [{"code": "input_unreadable"}])
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            self.cli.main(["--operation", "site-comparison", "--input", str(self.input_path),
                           "--destination-snapshot", str(self.input_path), "--credentials-file", "private-credentials"])
        compose = importlib.import_module("cc_vision_import.compose_entrypoint")
        with patch.object(compose, "master_main", return_value=1) as dispatch:
            self.assertEqual(compose.main(["destination", "--operation", "site-comparison", "--input", "source.json",
                                          "--destination-snapshot", "destination.json"]), 1)
        self.assertEqual(dispatch.call_args.args[0][:2], ["--operation", "site-comparison"])
