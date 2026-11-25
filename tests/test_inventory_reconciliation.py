import copy
import importlib
import io
import json
from contextlib import redirect_stdout

import test_vision_tree_preview
from offline_support import OfflineTestCase


class InventoryReconciliationTests(OfflineTestCase):
    def setUp(self):
        super().setUp()
        self.module = importlib.import_module("cc_vision_import.inventory_reconciliation")
        # Reuse the native Vision backup envelope fixture, not a CC migration artifact.
        fixture = test_vision_tree_preview.VisionTreePreviewTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        self.physical = copy.deepcopy(fixture.payload)
        self.physical["tree"]["children"] = []
        self.organization = copy.deepcopy(fixture.payload)
        self.organization["domain"] = "vision-organization-tree"
        self.organization["request"]["path"] = "/mgmt/system/config/tree/Organization"
        self.inventory = {
            "schema_version": 1, "domain": "vision-managed-device-inventory",
            "source": copy.deepcopy(fixture.payload["source"]),
            "request": {"method": "GET", "path": "/mgmt/system/config/itemlist/alldevices"},
            "objects": [
                {"ormId": "private-device-marker", "name": "private-name-marker", "managementIp": "192.0.2.44", "children": []},
                {"ormId": "private-inventory-only-marker", "children": []},
            ],
        }

    def reconcile(self):
        before = copy.deepcopy([self.inventory, self.organization, self.physical])
        report = self.module.reconcile_inventory(self.inventory, self.organization, self.physical)
        self.assertEqual(before, [self.inventory, self.organization, self.physical])
        raw = json.dumps(report)
        for marker in ("private-", "192.0.2.44"):
            self.assertNotIn(marker, raw)
        return report

    def test_equal_cross_namespace_values_names_and_addresses_never_establish_identity(self):
        report = self.reconcile()
        org = report["trees"]["organization"]
        comparison = org["comparison"]
        self.assertEqual(comparison["verified_match_count"], 0)
        self.assertIsNone(comparison["inventory_only"])
        self.assertIsNone(comparison["tree_only"])
        self.assertEqual(len(comparison["inventory_records_unresolved"]), 2)
        self.assertEqual(len(comparison["tree_device_records_unresolved"]), 1)
        self.assertEqual(comparison["inventory_minus_tree_record_count"], 1)
        self.assertEqual(len(org["recognized_site_associations"]), 1)
        self.assertFalse(org["recognized_site_associations"][0]["semantic_parent_verified"])
        self.assertEqual(report["trees"]["physical"]["devices"]["records"], 0)
        self.assertEqual(report["inventory"]["records_without_usable_parentOrmId"], 2)

    def test_duplicates_missing_identities_and_parent_conflict_are_separate(self):
        self.inventory["objects"].extend([
            {"ormId": "private-device-marker"}, {"ormId": None},
        ])
        site = self.organization["tree"]["children"][0]
        device = site["children"][0]
        site["children"].append(copy.deepcopy(device))
        site["children"].append({
            "meIdentifier": {"managedElementClass": "com.radware.insite.model.device.Device"},
            "parentOrmID": "private-missing-marker", "children": [],
        })
        report = self.reconcile()
        self.assertEqual(report["inventory"]["ambiguous_identity_records"], 2)
        self.assertEqual(len(report["inventory"]["missing_identity_references"]), 1)
        org = report["trees"]["organization"]
        self.assertEqual(org["devices"]["ambiguous_identity_records"], 2)
        self.assertEqual(len(org["devices"]["missing_identity_references"]), 1)
        self.assertEqual(len(org["device_site_associations_unresolved"]), 3)
        self.assertTrue(org["unresolved_hierarchy_dependencies"])

    def test_cli_writes_safe_report_exclusively_and_rejects_bad_context_and_urls(self):
        paths = []
        for name, payload in (("inventory", self.inventory), ("organization", self.organization), ("physical", self.physical)):
            path = self.directory / (name + ".json")
            path.write_text(json.dumps(payload))
            paths.extend(["--" + name, str(path)])
        before = {path: path.read_bytes() for path in self.directory.glob("*.json")}
        output = self.directory / "safe-report.json"
        for expected in (1, 3):
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                status = self.module.main([*paths, "--output", str(output)])
            self.assertEqual(status, expected)
            self.assertNotIn("private-", stdout.getvalue())
        self.assertTrue(json.loads(output.read_text())["offline_only"])
        for path, raw in before.items():
            self.assertEqual(path.read_bytes(), raw)
        self.organization["source"]["name"] = "private-wrong-controller-marker"
        with self.assertRaises(importlib.import_module("cc_vision_import.contracts").ContractValidationError):
            self.reconcile()
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            status = self.module.main([
                "--inventory", "https://private.invalid/a.json",
                "--organization", paths[3], "--physical", paths[5],
            ])
        self.assertEqual(status, 3)
        self.assertEqual(json.loads(stdout.getvalue())["issue_codes"], ["nonlocal_input"])

    def test_malformed_children_and_swapped_trees_do_not_silently_disappear(self):
        self.inventory["objects"][0]["children"] = None
        error = importlib.import_module("cc_vision_import.contracts").ContractValidationError
        with self.assertRaises(error):
            self.reconcile()
        self.inventory["objects"][0]["children"] = []
        with self.assertRaises(error):
            self.module.reconcile_inventory(self.inventory, self.physical, self.organization)
