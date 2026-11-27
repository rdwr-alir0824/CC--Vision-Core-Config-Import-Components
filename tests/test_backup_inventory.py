import copy
import importlib
import json
import os
from pathlib import Path

from offline_support import OfflineTestCase
from test_site_comparison import site


def envelope(domain, member, value):
    from cc_vision_import.product_clients import vision_ldap_segments, vision_scheduler_segments
    from cc_vision_import.schema_qualification import operation_evidence
    tree_name = "Organization" if domain == "vision-organization-tree" else "Physical"
    result = {
        "schema_version": 1, "domain": domain,
        "source": {"product": "vision", "version": "5.4.9", "name": "private-customer"},
        "collected_at": "2026-11-25T12:00:00+00:00",
        "request": {"method": "GET", "path": "/mgmt/system/config/tree/" + tree_name},
        "scope": {"migration_input": False, "complete_configuration_backup": False},
        "evidence": {}, "redacted_fields": 0, "issue_codes": [], member: value,
    }
    if member == "tree":
        result.update(record_count=len(value) if isinstance(value, list) else 1,
                      record_count_basis="top_level_json_records")
    elif domain == "vision-ldap-permissions":
        result["request"]["path"] = "/" + "/".join(vision_ldap_segments())
    elif domain == "vision-scheduler":
        result["request"]["path"] = "/" + "/".join(vision_scheduler_segments())
    elif domain == "vision-managed-device-inventory":
        result["request"]["path"] = "/mgmt/system/config/itemlist/alldevices"
    elif domain in ("vision-device-access", "vision-controller-object-lookup"):
        result["request"] = {"method": "GET", "path_template":
                             operation_evidence("vision", "5.4.9", "DOC-V549", "API-06").path,
                             "target": "192.0.2.1"}
    return result


class BackupInventoryTests(OfflineTestCase):
    def setUp(self):
        super().setUp()
        self.module = importlib.import_module("cc_vision_import.backup_inventory")
        self.backup = self.directory / "customer-selected-backup"
        self.backup.mkdir()

    def write(self, filename, payload):
        path = self.backup / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload))
        return path

    def scan(self, **kwargs):
        return self.module.discover_backup(str(self.backup), **kwargs)

    def test_arbitrary_files_and_varied_dynamic_hierarchies(self):
        for index, (size, deep) in enumerate(((0, False), (5, False), (23, True), (200, False))):
            root = site("private-root", f"private-tenant-{index}")
            parent = root
            for item in range(size):
                child = site(f"private-id-{item}", f"private-name-{item}")
                parent["children"].append(child)
                parent = child if deep else root
            path = self.write("unusual-location/arbitrary-customer-export.json",
                              envelope("vision-organization-tree", "tree", root))
            inventory = self.scan()
            module = next(row for row in inventory.report["modules"] if row["domain"] == "organization-tree")
            self.assertEqual(module["sites"], size)
            self.assertEqual(module["records"], size)
            self.assertEqual(len(module["graph"]), size + 1)
            refs = set()
            for node in module["graph"]:
                self.assertTrue(set(node["depends_on"]) <= refs)
                refs.add(node["reference"])
            self.assertEqual(inventory.paths("vision-organization-tree"), (path,))
            serialized = json.dumps(inventory.report)
            self.assertNotIn("private-name", serialized)
            self.assertNotIn("private-tenant", serialized)
            self.assertNotIn("private-id", serialized)

    def test_empty_absent_malformed_and_required_missing_are_distinct(self):
        self.write("empty.json", envelope("vision-ldap-permissions", "objects", []))
        self.write("bad.json", envelope("vision-scheduler", "tasks", {"password": "private-secret"}))
        self.write("summary.json", {"operation": "backup-vision", "requested_modules": ["physical-tree"],
                                    "failed_modules": []})
        modules = {item["domain"]: item for item in self.scan().report["modules"]}
        self.assertEqual(modules["ldap-permissions"]["availability"], "EMPTY")
        self.assertEqual(modules["scheduler"]["availability"], "MALFORMED")
        self.assertIsNone(modules["scheduler"]["records"])
        self.assertEqual(modules["organization-tree"]["availability"], "ABSENT")
        self.assertEqual(modules["physical-tree"]["availability"], "MISSING_REQUIRED")
        self.assertNotIn("private-secret", json.dumps(modules))

    def test_unequal_controller_access_and_device_records_are_independent(self):
        root = site("private-root", "private-root-name")
        for index, kind in enumerate(("DefensePro", "Alteon", "different-model")):
            root["children"].append({
                "meIdentifier": {"managedElementClass": "com.radware.insite.model.device.Device",
                                 "managedElementID": f"private-device-{index}"},
                "name": f"private-device-name-{index}", "type": kind,
                "managementIp": f"192.0.2.{index + 1}", "children": [],
            })
        self.write("tree.json", envelope("vision-organization-tree", "tree", root))
        self.write("details.json", envelope("vision-controller-object-lookup", "objects", [{}, {}]))
        self.write("access.json", envelope("vision-device-access", "objects", [{}]))
        self.write("inventory.json", envelope("vision-managed-device-inventory", "objects", [{}, {}, {}, {}]))
        modules = {item["domain"]: item for item in self.scan().report["modules"]}
        self.assertEqual(modules["organization-tree"]["devices"], len(root["children"]))
        self.assertEqual(modules["controller-objects"]["records"], 2)
        self.assertEqual(modules["controller-objects"]["managed_inventory_records"], 4)
        self.assertEqual(modules["device-access"]["records"], 1)
        self.assertEqual(modules["device-access"]["migration_status"], "BLOCKED")

    def test_unknown_settings_and_unknown_schema_are_not_empty_success(self):
        payload = envelope("vision-ldap-permissions", "objects", [])
        payload["private-setting"] = "private-password"
        self.write("known.json", payload)
        self.write("unknown.json", {"domain": "private-unknown", "token": "private-token"})
        self.write("malformed.json", [])
        inventory = self.scan()
        module = next(item for item in inventory.report["modules"] if item["domain"] == "ldap-permissions")
        self.assertEqual(module["availability"], "AVAILABLE")
        self.assertEqual(module["migration_status"], "BLOCKED")
        self.assertGreater(inventory.report["unknown_record_counts"], 0)
        self.assertNotIn("private-", json.dumps(inventory.report))

    def test_malformed_record_is_not_hidden_by_a_later_valid_file(self):
        self.write("a.json", envelope("vision-scheduler", "tasks", "malformed"))
        self.write("z.json", envelope("vision-scheduler", "tasks", [{}]))
        module = next(item for item in self.scan().report["modules"] if item["domain"] == "scheduler")
        self.assertEqual(module["availability"], "MALFORMED")
        self.assertIsNone(module["records"])
        self.assertEqual(module["known_records"], 1)

    def test_bounds_provenance_and_version_fail_closed(self):
        root = site("root-id", "root-name")
        root["children"].append(site("child-id", "child-name"))
        self.write("tree.json", envelope("vision-organization-tree", "tree", root))
        with self.assertRaisesRegex(self.module.SiteBlocked, "backup_object_limit"):
            self.scan(limits=self.module.InventoryLimits(max_objects=1))
        with self.assertRaisesRegex(self.module.SiteBlocked, "backup_file_size_limit"):
            self.scan(limits=self.module.InventoryLimits(max_file_bytes=10))
        other = envelope("vision-ldap-permissions", "objects", [])
        other["source"]["name"] = "different-customer"
        path = self.write("other.json", other)
        with self.assertRaisesRegex(self.module.SiteBlocked, "backup_mixed_source_provenance"):
            self.scan()
        other["source"]["name"] = "private-customer"
        other["source"]["version"] = "future-version"
        path.write_text(json.dumps(other))
        with self.assertRaisesRegex(self.module.SiteBlocked, "backup_mixed_source_provenance"):
            self.scan()

    def test_binding_changes_with_any_domain_not_only_organization(self):
        path = self.write("ldap.json", envelope("vision-ldap-permissions", "objects", [{}]))
        original = self.scan().digest
        path.write_text(json.dumps(envelope("vision-ldap-permissions", "objects", [{}, {}])))
        self.assertNotEqual(self.scan().digest, original)

    def test_empty_directory_is_not_an_intentionally_empty_module(self):
        with self.assertRaisesRegex(self.module.SiteBlocked, "backup_empty_directory"):
            self.scan()

    def test_empty_root_object_and_malformed_request_are_not_empty_modules(self):
        self.write("root.json", envelope("vision-organization-tree", "tree", {}))
        malformed = envelope("vision-device-access", "objects", [])
        malformed["request"]["path_template"] = {"password": "private-password"}
        self.write("access.json", malformed)
        modules = {item["domain"]: item for item in self.scan().report["modules"]}
        self.assertEqual(modules["organization-tree"]["availability"], "MALFORMED")
        self.assertEqual(modules["device-access"]["availability"], "MALFORMED")
        self.assertNotIn("private-password", json.dumps(modules))
