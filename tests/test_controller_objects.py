import copy
import importlib
import io
import json
import traceback
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import asdict
from pathlib import Path
from unittest.mock import patch

from offline_support import OfflineTestCase


_DEFAULT_TREE = object()


class ControllerObjectTests(OfflineTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.o = importlib.import_module("cc_vision_import.controller_objects")
        self.m = importlib.import_module("cc_vision_import.controller_mapping")
        self.contracts = importlib.import_module("cc_vision_import.contracts")
        self.plans = importlib.import_module("cc_vision_import.plans")
        fixtures = Path(__file__).parent / "fixtures"
        self.physical = json.loads((fixtures / "controller-physical.json").read_text(encoding="utf-8"))
        self.organization = json.loads((fixtures / "controller-organization.json").read_text(encoding="utf-8"))

    def normalize(self, payload=_DEFAULT_TREE, *, tree=None, controller="synthetic-source"):
        return self.o.normalize_tree(
            self.physical if payload is _DEFAULT_TREE else payload, controller_id=controller,
            tree=self.o.TreeName.PHYSICAL if tree is None else tree,
            version="0.0-test", exported_at="2026-11-17T00:00:00Z",
        )

    def error(self, code, function, *args, **kwargs):
        with self.assertRaises(self.contracts.ContractValidationError) as caught:
            function(*args, **kwargs)
        self.assertEqual(caught.exception.result.status, "invalid")
        self.assertEqual(caught.exception.result.issues[0].code, code)
        return caught.exception

    def inventories(self, *, same_ids=False):
        destination_tree = copy.deepcopy(self.physical)

        def rename(node):
            if not same_ids:
                node["meIdentifier"]["managedElementID"] = "destination-" + node["meIdentifier"]["managedElementID"]
            if "name" in node:
                node["name"] = "Different destination " + node["name"]
            for child in node.get("children", []):
                rename(child)

        rename(destination_tree)
        return self.normalize(), self.normalize(destination_tree, controller="synthetic-destination")

    def mappings(self, source, destination):
        source_indices = {item.reference: index for index, item in enumerate(source.objects)}
        result = []
        for index, (item, target) in enumerate(zip(source.objects, destination.objects, strict=True)):
            parent_id = None
            if not isinstance(item, self.o.ControllerRoot):
                parent_id = f"map-{source_indices[item.parent]}"
            result.append({
                "mapping_id": f"map-{index}", "domain": "controller-objects", "source_index": index,
                "source": asdict(item.reference.as_identity()),
                "source_context": asdict(source.source), "destination_context": asdict(destination.source),
                "state": "resolved", "destination": asdict(target.reference.as_identity()),
                "candidates": [], "parent_mapping": parent_id,
                "depends_on": [] if parent_id is None else [parent_id],
            })
        return result

    def add_duplicate_site(self) -> None:
        duplicate = copy.deepcopy(self.physical["children"][0])
        duplicate["meIdentifier"]["managedElementID"] = "another-site"
        duplicate["children"] = []
        duplicate["opaqueSite"]["color"] = "duplicate-purple"
        self.physical["children"].append(duplicate)

    def test_simple_physical_tree_and_typed_source_references(self) -> None:
        simple = copy.deepcopy(self.physical)
        simple["children"] = [simple["children"][0]]
        simple["children"][0]["children"] = []
        inventory = self.normalize(simple)
        root, site = inventory.objects
        self.assertIsInstance(root, self.o.ControllerRoot)
        self.assertIsInstance(site, self.o.ControllerSite)
        self.assertEqual(site.parent, root.reference)
        self.assertEqual(site.reference.controller_id, "synthetic-source")
        self.assertEqual(site.reference.kind, self.o.ControllerObjectKind.SITE)
        self.assertEqual(site.reference.tree, self.o.TreeName.PHYSICAL)

    def test_nested_hierarchy_multiple_devices_and_configuration_are_preserved(self) -> None:
        original = copy.deepcopy(self.physical)
        inventory = self.normalize()
        root, region, nested, first_device, sibling, second_device = inventory.objects
        self.assertEqual(len(inventory.objects), 6)
        self.assertEqual(nested.parent, region.reference)
        self.assertEqual(first_device.parent, nested.reference)
        self.assertEqual(second_device.parent, sibling.reference)
        self.assertEqual(root.configuration["opaqueRoot"], self.physical["opaqueRoot"])
        self.assertEqual(region.configuration["opaqueSite"], {"color": "blue"})
        self.assertEqual(region.configuration["meIdentifier"]["extraIdentity"], "retained")
        self.assertEqual(first_device.device_type, "synthetic-device-type")
        self.assertEqual(second_device.management_ip, "2001:db8::20")
        self.assertEqual(first_device.configuration["deviceSetup"], {"opaqueSetup": {"keep": True}})
        self.assertEqual(first_device.device_access.value["ormID"], "access-provenance-only")
        self.assertEqual(first_device.device_access.value["connectionTimeout"], 7)
        self.assertEqual(first_device.device_access.value["opaqueAccess"], ["retained"])
        self.assertEqual(self.physical, original)
        self.assertEqual(first_device.device_access.location, self.o.DeviceAccessLocation.DEVICE_SETUP)
        self.assertEqual(second_device.device_access.location, self.o.DeviceAccessLocation.ABSENT)

    def test_organization_and_identical_native_ids_do_not_merge_with_physical(self) -> None:
        physical = self.normalize().to_artifact().to_dict()
        organization = self.normalize(self.organization, tree=self.o.TreeName.ORGANIZATION)
        physical["objects"].extend(organization.to_artifact().to_dict()["objects"])
        combined = self.o.parse_controller_artifact(physical)
        roots = [item for item in combined.objects if isinstance(item, self.o.ControllerRoot)]
        self.assertEqual(len(roots), 2)
        self.assertEqual(roots[0].reference.object_id, roots[1].reference.object_id)
        self.assertNotEqual(roots[0].reference.as_identity(), roots[1].reference.as_identity())
        self.assertEqual(len(combined.objects), 9)
        self.assertEqual(self.o.assess_controller_identity(combined).status, "valid")

    def test_duplicate_sites_are_preserved_but_same_names_under_different_parents_are_unambiguous(self) -> None:
        self.assertEqual(self.o.assess_controller_identity(self.normalize()).status, "valid")
        self.add_duplicate_site()
        original = copy.deepcopy(self.physical)
        inventory = self.normalize()
        self.assertEqual(len(inventory.objects), 7)
        self.assertEqual(inventory.objects[1].name, inventory.objects[-1].name)
        self.assertNotEqual(inventory.objects[1].reference, inventory.objects[-1].reference)
        self.assertEqual(inventory.objects[1].configuration["opaqueSite"]["color"], "blue")
        self.assertEqual(inventory.objects[-1].configuration["opaqueSite"]["color"], "duplicate-purple")
        artifact = inventory.to_artifact()
        restored = self.o.parse_controller_artifact(json.loads(artifact.to_json()))
        self.assertEqual(restored, inventory)
        self.assertEqual(len(artifact.objects), 7)
        self.assertEqual(self.o.validate_controller_artifact(artifact.to_dict()).status, "valid")
        assessment = self.o.assess_controller_identity(restored)
        self.assertEqual(assessment.status, "invalid")
        self.assertEqual(assessment.object_count, 7)
        self.assertEqual([issue.code for issue in assessment.issues], ["ambiguous_name"] * 2)
        self.assertEqual([issue.path for issue in assessment.issues], ["$.objects[1].name", "$.objects[6].name"])
        self.assertEqual(self.physical, original)

    def test_duplicate_device_sibling_names_are_preserved_and_flagged(self) -> None:
        device = self.physical["children"][1]["children"][0]
        duplicate = copy.deepcopy(device)
        duplicate["meIdentifier"]["managedElementID"] = "another-device"
        self.physical["children"][1]["children"].append(duplicate)
        inventory = self.normalize()
        self.assertEqual(len(inventory.to_artifact().objects), 7)
        assessment = self.o.assess_controller_identity(inventory)
        self.assertEqual(assessment.status, "invalid")
        self.assertEqual([issue.path for issue in assessment.issues], ["$.objects[5].name", "$.objects[6].name"])

    def test_same_sibling_name_across_object_types_is_not_ambiguous(self) -> None:
        device = copy.deepcopy(self.physical["children"][1]["children"][0])
        device["meIdentifier"]["managedElementID"] = "another-device"
        device["name"] = self.physical["children"][0]["name"]
        self.physical["children"].append(device)
        inventory = self.normalize()
        self.assertEqual(len(inventory.to_artifact().objects), 7)
        self.assertEqual(self.o.assess_controller_identity(inventory).status, "valid")

    def test_missing_parent_never_falls_back_to_root(self) -> None:
        payload = self.normalize().to_artifact().to_dict()
        payload["objects"][2]["parent"]["object_id"] = "missing-parent"
        self.error("missing_parent", self.o.parse_controller_artifact, payload)

    def test_cycle_and_self_parent_are_rejected_offline(self) -> None:
        for self_parent in (False, True):
            with self.subTest(self_parent=self_parent):
                payload = self.normalize().to_artifact().to_dict()
                payload["objects"][1]["parent"] = copy.deepcopy(payload["objects"][1 if self_parent else 2]["reference"])
                self.error("invalid_dependency", self.o.parse_controller_artifact, payload)

    def test_duplicate_and_conflicting_native_identifiers_are_rejected(self) -> None:
        for conflict in (False, True):
            with self.subTest(conflict=conflict):
                self.setUp_tree()
                child = self.physical["children"][1]
                child["meIdentifier"]["managedElementID"] = "site-a"
                if conflict:
                    child["meIdentifier"]["managedElementClass"] = "com.radware.insite.model.device.Device"
                    child.update(type="synthetic-type", managementIp="192.0.2.30", children=[])
                self.error("conflicting_reference" if conflict else "duplicate_identity", self.normalize)

    def setUp_tree(self) -> None:
        fixture = Path(__file__).parent / "fixtures" / "controller-physical.json"
        self.physical = json.loads(fixture.read_text(encoding="utf-8"))

    def test_cross_tree_cross_controller_and_device_parents_are_rejected(self) -> None:
        for field, value, code in (
            ("tree", "Organization", "cross_context_parent"),
            ("controller_id", "another-controller", "cross_context_parent"),
            ("kind", "device", "invalid_parent"),
            ("kind", "root", "conflicting_reference"),
        ):
            with self.subTest(field=field, value=value):
                payload = self.normalize().to_artifact().to_dict()
                payload["objects"][2]["parent"][field] = value
                self.error(code, self.o.parse_controller_artifact, payload)

    def test_missing_duplicate_and_parented_roots_are_invalid(self) -> None:
        for case in ("missing", "duplicate", "parented", "empty"):
            with self.subTest(case=case):
                payload = self.normalize().to_artifact().to_dict()
                if case == "missing":
                    payload["objects"].pop(0)
                elif case == "duplicate":
                    root = copy.deepcopy(payload["objects"][0])
                    root["reference"]["object_id"] = "second-root"
                    root["configuration"] = {}
                    payload["objects"].append(root)
                elif case == "parented":
                    payload["objects"][0]["parent"] = payload["objects"][1]["reference"]
                else:
                    payload["objects"] = []
                self.error(
                    "duplicate_root" if case == "duplicate" else "invalid_hierarchy"
                    if case == "parented" else "missing_root",
                    self.o.parse_controller_artifact, payload,
                )

    def test_unknown_node_kinds_and_device_children_are_not_discarded(self) -> None:
        self.physical["children"][0]["meIdentifier"]["managedElementClass"] = "unsupported-class"
        self.error("unsupported_object_kind", self.normalize)
        self.setUp_tree()
        self.physical["children"][1]["children"][0]["children"] = [copy.deepcopy(self.organization)]
        self.error("invalid_hierarchy", self.normalize)

    def test_device_children_must_be_absent_or_an_empty_list(self) -> None:
        for children in (None, {}, "", [1]):
            with self.subTest(children=children):
                self.setUp_tree()
                self.physical["children"][1]["children"][0]["children"] = children
                self.error("invalid_hierarchy", self.normalize)

    def test_known_site_and_device_classes_cannot_be_relabelled_as_roots(self) -> None:
        for kind in ("Site", "Device"):
            with self.subTest(kind=kind):
                self.setUp_tree()
                self.physical["meIdentifier"]["managedElementClass"] = f"com.radware.insite.model.device.{kind}"
                self.error("conflicting_reference", self.normalize)

    def test_malformed_structures_and_unknown_normalized_fields_fail(self) -> None:
        for payload in (None, [], {}, {"meIdentifier": {}}, {"meIdentifier": {"managedElementID": "root"}, "children": {}}):
            with self.subTest(payload=payload):
                with self.assertRaises(self.contracts.ContractValidationError):
                    self.normalize(payload)
        payload = self.normalize().to_artifact().to_dict()
        payload["objects"][1]["unsupported"] = True
        self.error("unknown_fields", self.o.parse_controller_artifact, payload)
        self.error("unsupported_tree", self.normalize, tree="Invented")

    def test_native_parent_and_identifier_alias_conflicts_are_explicit(self) -> None:
        for field in ("parentOrmID", "ormID"):
            with self.subTest(field=field):
                self.setUp_tree()
                self.physical["children"][0][field] = "conflicting-provenance"
                self.error("conflicting_reference", self.normalize)
        self.setUp_tree()
        self.physical["children"][0].update(parentOrmID="root-source", ormID="site-a")
        site = self.normalize().objects[1]
        self.assertEqual(site.configuration["parentOrmID"], "root-source")
        self.assertEqual(site.configuration["ormID"], "site-a")

    def test_access_absence_explicit_null_and_origin_are_distinct(self) -> None:
        absent = self.normalize().objects[-1].device_access
        self.assertEqual(absent.location, self.o.DeviceAccessLocation.ABSENT)
        self.assertIsNone(absent.value)
        for nested in (False, True):
            with self.subTest(nested=nested):
                self.setUp_tree()
                device = self.physical["children"][1]["children"][0]
                device.update({"deviceSetup": {"deviceAccess": None}} if nested else {"deviceAccess": None})
                access = self.normalize().objects[-1].device_access
                self.assertEqual(
                    access.location, self.o.DeviceAccessLocation.DEVICE_SETUP
                    if nested else self.o.DeviceAccessLocation.TOP_LEVEL,
                )
                self.assertIsNone(access.value)

    def test_conflicting_access_locations_are_never_merged(self) -> None:
        self.physical["children"][0]["children"][0]["children"][0]["deviceAccess"] = {}
        self.error("conflicting_reference", self.normalize)

    def test_invalid_access_shapes_and_duplicate_configuration_fields_are_rejected(self) -> None:
        for case in ("access-list", "absent-with-value", "duplicate-name", "duplicate-children", "duplicate-access"):
            with self.subTest(case=case):
                payload = self.normalize().to_artifact().to_dict()
                device = payload["objects"][3]
                code = "conflicting_reference"
                if case == "access-list":
                    device["device_access"]["value"] = []
                    code = "invalid_device_access"
                elif case == "absent-with-value":
                    device["device_access"]["location"] = "absent"
                    code = "invalid_device_access"
                elif case == "duplicate-name":
                    device["configuration"]["name"] = "unreconciled-name"
                elif case == "duplicate-children":
                    device["configuration"]["children"] = []
                else:
                    device["configuration"]["deviceSetup"]["deviceAccess"] = {}
                self.error(code, self.o.parse_controller_artifact, payload)

    def test_non_json_values_and_excessive_nesting_fail_safely(self) -> None:
        self.physical["opaqueRoot"] = float("inf")
        self.error("invalid_value", self.normalize)
        self.setUp_tree()
        nested = {}
        self.physical["opaqueRoot"] = nested
        for _ in range(70):
            nested["nested"] = {}
            nested = nested["nested"]
        self.error("invalid_value", self.normalize)
        self.setUp_tree()
        site = self.physical["children"][0]
        site["children"] = [site]
        self.error("invalid_hierarchy", self.normalize)

    def test_previously_invalid_artifacts_are_not_silently_promoted(self) -> None:
        payload = self.normalize().to_artifact().to_dict()
        payload["validation"].update(status="invalid", issue_codes=["unresolved_source_issue"])
        self.error("invalid_artifact", self.o.parse_controller_artifact, payload)
        self.assertEqual(self.o.validate_controller_artifact(payload).status, "invalid")

    def test_credentials_fail_without_appearing_in_errors_or_reports(self) -> None:
        marker = "synthetic-raw-credential-marker"
        for key in (
            "cliUsername", "httpUsername", "httpsUsername", "snmpV3Username",
            "cliPassword", "httpPassword", "httpsPassword",
            "snmpV3AuthenticationPassword", "snmpV3PrivacyPassword",
            "authKey", "privKey", "community", "sessionToken", "passphrase",
        ):
            with self.subTest(key=key):
                self.setUp_tree()
                access = self.physical["children"][0]["children"][0]["children"][0]["deviceSetup"]["deviceAccess"]
                access[key] = marker
                error = self.error("secret_value_not_allowed", self.normalize)
                self.assertNotIn(marker, "".join(traceback.format_exception(error)))
                self.assertNotIn(marker, repr(error.result))
                self.assertIsNone(error.__context__)

    def test_roundtrip_revalidation_and_deep_copy_preserve_non_sensitive_fields(self) -> None:
        inventory = self.normalize()
        artifact = inventory.to_artifact()
        restored = self.o.parse_controller_artifact(json.loads(artifact.to_json()))
        self.assertEqual(restored, inventory)
        self.assertEqual(self.o.validate_controller_artifact(artifact.to_dict()).status, "valid")
        inventory.objects[0].configuration["opaqueRoot"]["retained"].append("local-change")
        self.assertNotIn("local-change", artifact.to_json())
        inventory.objects[3].device_access.value["cliUsername"] = "synthetic-raw-user"
        self.error("secret_value_not_allowed", inventory.to_artifact)

    def test_reports_and_representations_hide_names_addresses_ids_and_references(self) -> None:
        stdout, stderr = io.StringIO(), io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr), patch("logging.Logger._log") as log:
            inventory = self.normalize()
            report = self.o.validate_controller_artifact(inventory.to_artifact().to_dict())
        log.assert_not_called()
        self.assertEqual((stdout.getvalue(), stderr.getvalue()), ("", ""))
        text = repr(inventory) + repr(inventory.objects) + repr(report)
        for value in ("synthetic-source", "root-source", "site-a", "Region", "192.0.2.10", "synthetic/device-one/user"):
            self.assertNotIn(value, text)

    def test_explicit_mappings_use_destination_inventory_not_names(self) -> None:
        source, destination = self.inventories()
        records = self.mappings(source, destination)
        before = copy.deepcopy(records)
        result = self.m.resolve_controller_mappings(source, destination, records)
        self.assertEqual(result.validation.status, "valid")
        self.assertEqual(len(result.mappings), len(source.objects))
        self.assertEqual(records, before)
        self.assertNotEqual(source.objects[1].name, destination.objects[1].name)
        self.assertEqual(result.mappings[1].destination.object_id, "destination-site-a")
        self.assertNotIn("destination-site-a", repr(result))

    def test_explicit_qualified_mappings_resolve_duplicate_siblings_without_losing_objects(self) -> None:
        self.add_duplicate_site()
        source, destination = self.inventories()
        records = self.mappings(source, destination)
        for inventory in (source, destination):
            self.assertEqual(self.o.assess_controller_identity(inventory).status, "invalid")
        destination_payload = destination.to_artifact().to_dict()
        destination_payload["objects"].reverse()
        destination = self.o.parse_controller_artifact(destination_payload)
        result = self.m.resolve_controller_mappings(source, destination, list(reversed(records)))
        self.assertEqual(result.validation.status, "valid")
        self.assertEqual(result.validation.object_count, 7)
        self.assertEqual(result.mappings[1].destination.object_id, "destination-site-a")
        self.assertEqual(result.mappings[-1].destination.object_id, "destination-another-site")
        self.assertEqual(len({item.destination for item in result.mappings}), 7)
        self.assertEqual(len(source.to_artifact().objects), 7)
        self.assertEqual(len(destination.to_artifact().objects), 7)

    def test_unresolved_duplicate_mappings_block_without_changing_the_artifact(self) -> None:
        self.add_duplicate_site()
        source, destination = self.inventories()
        before = source.to_artifact().to_json()
        for state in ("unresolved", "ambiguous"):
            with self.subTest(state=state):
                records = self.mappings(source, destination)
                records[1].update(state=state, destination=None)
                if state == "ambiguous":
                    records[1]["candidates"] = [
                        asdict(destination.objects[1].reference.as_identity()),
                        asdict(destination.objects[-1].reference.as_identity()),
                    ]
                self.error("mapping_" + state, self.m.resolve_controller_mappings, source, destination, records)
                self.assertEqual(source.to_artifact().to_json(), before)

    def test_duplicate_names_never_supply_destination_identity_or_copy_source_ids(self) -> None:
        self.add_duplicate_site()
        source, destination = self.inventories()
        for object_id in (source.objects[1].name, source.objects[1].reference.object_id):
            with self.subTest(object_id=object_id):
                records = self.mappings(source, destination)
                records[1]["destination"]["object_id"] = object_id
                self.error("missing_destination", self.m.resolve_controller_mappings, source, destination, records)

    def test_name_ambiguity_reports_do_not_expose_names_or_configuration(self) -> None:
        self.add_duplicate_site()
        marker = "synthetic-sensitive-name-marker"
        self.physical["children"][0]["name"] = marker
        self.physical["children"][-1]["name"] = marker
        inventory = self.normalize()
        assessment = self.o.assess_controller_identity(inventory)
        self.assertEqual(assessment.status, "invalid")
        self.assertNotIn(marker, repr(assessment))
        self.assertNotIn("duplicate-purple", repr(assessment))
        self.assertNotIn("synthetic-source", repr(assessment))

    def test_same_id_strings_require_independent_explicit_destination_references(self) -> None:
        source, destination = self.inventories(same_ids=True)
        records = self.mappings(source, destination)
        self.assertEqual(records[1]["source"]["object_id"], records[1]["destination"]["object_id"])
        self.assertNotEqual(records[1]["source"]["namespace"], records[1]["destination"]["namespace"])
        self.assertEqual(self.m.resolve_controller_mappings(source, destination, records).validation.status, "valid")
        records[1]["destination"] = records[1]["source"]
        self.error("missing_destination", self.m.resolve_controller_mappings, source, destination, records)

    def test_missing_unresolved_and_ambiguous_mappings_never_select_candidates(self) -> None:
        for state, code in (("absent", "missing_mapping"), ("missing", "mapping_missing"), ("unresolved", "mapping_unresolved"), ("ambiguous", "mapping_ambiguous")):
            with self.subTest(state=state):
                source, destination = self.inventories()
                records = self.mappings(source, destination)
                if state == "absent":
                    records.pop()
                else:
                    records[1].update(state=state, destination=None)
                    if state == "ambiguous":
                        records[1]["candidates"] = [
                            asdict(destination.objects[1].reference.as_identity()),
                            asdict(destination.objects[4].reference.as_identity()),
                        ]
                self.error(code, self.m.resolve_controller_mappings, source, destination, records)

    def test_mapping_source_context_and_target_presence_are_checked(self) -> None:
        for case in ("source-index", "source-id", "source-context", "destination-context", "missing-target", "same-controller"):
            with self.subTest(case=case):
                source, destination = self.inventories()
                records = self.mappings(source, destination)
                code = "context_mismatch"
                if case == "source-index":
                    records[1]["source_index"] = 99
                    code = "duplicate_identity"
                elif case == "source-id":
                    records[1]["source"]["object_id"] = "wrong-source"
                elif case in ("source-context", "destination-context"):
                    records[1][case.replace("-", "_")]["version"] = "9.9"
                elif case == "missing-target":
                    records[1]["destination"]["object_id"] = "not-in-destination"
                    code = "missing_destination"
                else:
                    destination = source
                self.error(code, self.m.resolve_controller_mappings, source, destination, records)

    def test_collisions_parent_dependencies_and_relocations_are_rejected(self) -> None:
        for case, code in (
            ("collision", "destination_collision"), ("parent", "invalid_dependency"),
            ("dependency", "invalid_dependency"), ("relocation", "hierarchy_mismatch"),
            ("cycle", "invalid_dependency"),
        ):
            with self.subTest(case=case):
                source, destination = self.inventories()
                records = self.mappings(source, destination)
                if case == "collision":
                    records[2]["destination"] = records[1]["destination"]
                elif case == "parent":
                    records[2]["parent_mapping"] = None
                elif case == "dependency":
                    records[2]["depends_on"] = []
                elif case == "relocation":
                    records[1]["destination"], records[4]["destination"] = records[4]["destination"], records[1]["destination"]
                else:
                    records[0]["depends_on"] = ["map-2"]
                self.error(code, self.m.resolve_controller_mappings, source, destination, records)

    def test_cross_tree_and_cross_type_mappings_do_not_merge_objects(self) -> None:
        source, destination = self.inventories()
        organization = self.normalize(
            self.organization, tree=self.o.TreeName.ORGANIZATION, controller="synthetic-destination",
        )
        destination_payload = destination.to_artifact().to_dict()
        destination_payload["objects"].extend(organization.to_artifact().to_dict()["objects"])
        destination = self.o.parse_controller_artifact(destination_payload)
        records = self.mappings(source, self.inventories()[1])
        records[1]["destination"] = asdict(organization.objects[1].reference.as_identity())
        self.error("context_mismatch", self.m.resolve_controller_mappings, source, destination, records)
        records[1]["destination"] = asdict(destination.objects[3].reference.as_identity())
        self.error("context_mismatch", self.m.resolve_controller_mappings, source, destination, records)

    def test_invalid_mapping_status_is_sanitized_without_parser_chaining(self) -> None:
        source, destination = self.inventories()
        records = self.mappings(source, destination)
        records[0]["state"] = "synthetic-sensitive-state-marker"
        error = self.error("invalid_mapping", self.m.resolve_controller_mappings, source, destination, records)
        self.assertNotIn("synthetic-sensitive-state-marker", "".join(traceback.format_exception(error)))
        self.assertIsNone(error.__context__)

    def test_resolved_mappings_require_controller_specific_offline_plans(self) -> None:
        source, destination = self.inventories()
        mappings = self.m.resolve_controller_mappings(source, destination, self.mappings(source, destination))
        request = {
            "destination": {
                "controller_id": "synthetic-destination", "product": "cyber-controller",
                "version": "0.0-test", "base_url": "https://destination.invalid",
            },
            "mappings": json.loads(json.dumps([asdict(item) for item in mappings.mappings])),
            "actions": [{
                "action_id": f"action-{index}", "mapping_id": item.mapping_id,
                "comparison": "unknown", "semantics_known": False,
                "depends_on": [f"action-{int(key.split('-')[1])}" for key in item.depends_on],
            } for index, item in enumerate(mappings.mappings)],
        }
        artifact = source.to_artifact().to_json().encode("utf-8")
        self.error("controller_planning_required", self.plans.create_plan, artifact, request)
        comparison = importlib.import_module("cc_vision_import.controller_comparison")
        plan = comparison.compare_controller_inventories(source, destination, request["mappings"])
        self.assertEqual(plan.stage, "offline-controller-candidate")
        self.assertTrue(all(action.kind == "blocked" for action in plan.actions))
        self.assertEqual(
            comparison.verify_controller_plan(plan.to_dict(), source, destination, request["mappings"]),
            plan,
        )
