import copy
import hashlib
import importlib
import json
import traceback
from dataclasses import asdict, replace
from pathlib import Path

from offline_support import OfflineTestCase, device_access_acknowledgements
import test_controller_exports as export_tests


class ControllerReconciliationTests(OfflineTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.r = importlib.import_module("cc_vision_import.controller_reconciliation")
        self.p = importlib.import_module("cc_vision_import.controller_access_policy")
        self.v = importlib.import_module("cc_vision_import.controller_planning")
        self.o = importlib.import_module("cc_vision_import.controller_objects")
        self.e = importlib.import_module("cc_vision_import.controller_exports")
        self.c = importlib.import_module("cc_vision_import.controller_comparison")
        self.a = importlib.import_module("cc_vision_import.artifacts")
        self.contracts = importlib.import_module("cc_vision_import.contracts")
        path = Path(__file__).parent / "fixtures" / "controller-export-responses.json"
        self.fixtures = json.loads(path.read_text(encoding="utf-8"))
        self.options = {
            "controller_id": "synthetic-source", "tree": self.o.TreeName.PHYSICAL,
            "version": "0.0-test", "exported_at": "2026-11-18T10:00:00Z",
        }

    def case(self, name="incomplete_access", **options):
        settings = self.options | options
        raw = copy.deepcopy(self.fixtures[name])
        original = self.o.normalize_tree(copy.deepcopy(raw), **settings)

        def strip_access(node):
            node.pop("deviceAccess", None)
            if "deviceSetup" in node:
                node["deviceSetup"].pop("deviceAccess", None)
            for child in node.get("children", []):
                strip_access(child)

        strip_access(raw)
        artifact = self.e.adapt_tree_response(raw, **settings).artifact
        inventory = self.o.normalize_tree(copy.deepcopy(raw), **settings)
        originals = {item.reference: item for item in original.objects}
        details, associations = [], []
        for index, item in enumerate(inventory.objects):
            if not isinstance(item, self.o.ControllerDevice):
                continue
            setup = copy.deepcopy(item.configuration.get("deviceSetup", {}))
            setup["deviceAccess"] = originals[item.reference].device_access.value or {
                "connectionTimeout": 7, "futureAccess": {"second": [True, 1, None], "first": False},
            }
            details.append({
                "record_id": f"detail-{index}",
                "payload": {
                    "ormID": item.reference.object_id, "type": item.device_type,
                    "managementIp": item.management_ip, "deviceSetup": setup,
                    "futureDetail": {"second": [None, True, 1], "first": {"z": 2, "a": 1}},
                },
            })
            associations.append(self.r.DeviceReconciliationAssociation(
                item.reference, f"detail-{index}",
            ))
        return self.acknowledged((artifact, details, [], tuple(associations)))

    def acknowledged(self, case):
        artifact, details, accesses, associations = case
        unsigned = tuple(replace(item, acknowledgement=None) for item in associations)
        preview = self.r.reconcile_controller_devices(artifact, details, accesses, unsigned)
        acknowledged = tuple(replace(item, acknowledgement=self.p.acknowledge_device_access(
            artifact, preview.artifact, item.source,
            evidence_reference="evidence-" + "1" * 32,
        )) for item in unsigned)
        return artifact, details, accesses, acknowledged

    def rules(self):
        return (self.c.ControllerComparisonRule.DEVICE_ACCESS_ACKNOWLEDGEMENT,)

    def reconcile(self, case):
        return self.r.reconcile_controller_devices(*case)

    def error(self, code, case):
        with self.assertRaises(self.contracts.ContractValidationError) as caught:
            self.reconcile(case)
        self.assertEqual(caught.exception.result.issues[0].code, code)
        return caught.exception

    def roundtrip(self, result):
        return self.o.parse_controller_artifact(json.loads(result.artifact.to_json()))

    mapped_destination = export_tests.ControllerExportTests.mapped_destination
    def plan(self, source, destination, mappings):
        return self.c.compare_controller_inventories(
            source, destination, mappings,
            complete_trees=(source.objects[0].reference.tree,),
            semantics_known_for=tuple(item.reference for item in source.objects),
            comparison_rules=self.rules(),
        )

    def generic_request(self, mappings):
        return {
            "destination": {
                "product": "cyber-controller", "version": "0.0-test",
                "controller_id": "synthetic-destination", "base_url": "https://destination.invalid",
            },
            "mappings": mappings,
            "actions": [
                {
                    "action_id": f"action-{index}", "mapping_id": row["mapping_id"],
                    "comparison": "missing" if row["state"] == "missing" else "identical",
                    "semantics_known": True,
                    "depends_on": [key.replace("map-", "action-") for key in row["depends_on"]],
                }
                for index, row in enumerate(mappings)
            ],
        }

    def planning_pair(self, origin, tree):
        inventories = []
        for controller in ("synthetic-source", "synthetic-destination"):
            options = self.options | {"controller_id": controller, "tree": tree}
            if origin == "A/B-normalized":
                inventory = self.o.normalize_tree(copy.deepcopy(self.fixtures["organization"]), **options)
            elif origin == "C1-recursive":
                inventory = self.e.adapt_tree_response(self.fixtures["organization"], **options).to_inventory()
            elif origin == "C1-flat":
                inventory = self.e.adapt_flat_export(
                    self.fixtures["flat"], root_response=self.fixtures["root"], **options,
                ).to_inventory()
            else:
                artifact, details, accesses, associations = self.case(
                    "organization", controller_id=controller, tree=tree,
                )
                unsigned = tuple(replace(item, acknowledgement=None) for item in associations)
                inventory = self.roundtrip(self.reconcile((artifact, details, accesses, unsigned)))
            inventories.append(inventory)
        return tuple(inventories)

    def test_explicit_reconciliation_repairs_c1_incomplete_artifact_without_mutation(self) -> None:
        case = self.case()
        before = copy.deepcopy(case)
        self.assertEqual(case[0].validation.status, "invalid")
        result = self.reconcile(case)
        inventory = self.roundtrip(result)
        self.assertEqual(result.validation.status, "valid")
        self.assertEqual(result.completeness, "unverified")
        self.assertEqual(inventory.objects[1].device_access.value["connectionTimeout"], 7)
        self.assertEqual(inventory.objects[1].configuration["deviceSetup"], {"futureField": None})
        self.assertEqual(
            inventory.objects[1].configuration["offlineDeviceReconciliation"]["tree_access"],
            {"location": "absent", "value": None},
        )
        self.assertEqual(case, before)

    def test_missing_details_preserve_all_objects_and_block_serialized_inventory(self) -> None:
        artifact, _, _, _ = self.case("physical")
        result = self.reconcile((artifact, [], [], ()))
        self.assertEqual(len(result.artifact.objects), 5)
        self.assertEqual({issue.code for issue in result.validation.issues}, {"missing_device_details"})
        with self.assertRaises(self.contracts.ContractValidationError):
            self.roundtrip(result)
        with self.assertRaises(self.contracts.ContractValidationError):
            result.to_inventory()

    def test_duplicate_ip_addresses_are_distinct_with_explicit_associations(self) -> None:
        raw = self.fixtures["physical"]["children"][0]["children"][0]["children"]
        raw[1]["managementIp"] = raw[0]["managementIp"]
        result = self.reconcile(self.case("physical"))
        devices = [item for item in result.to_inventory().objects if isinstance(item, self.o.ControllerDevice)]
        self.assertEqual(len(devices), 2)
        self.assertEqual(devices[0].management_ip, devices[1].management_ip)
        self.assertNotEqual(devices[0].reference, devices[1].reference)

    def test_ip_and_names_never_supply_missing_associations(self) -> None:
        artifact, details, accesses, _ = self.case()
        self.error("unmatched_record", (artifact, details, accesses, ()))
        raw = self.fixtures["physical"]["children"][0]["children"][0]["children"]
        raw[1]["managementIp"] = raw[0]["managementIp"]
        artifact, details, accesses, _ = self.case("physical")
        self.error("ambiguous_ip_reference", (artifact, details, accesses, ()))

    def test_duplicate_detail_record_ids_and_duplicate_associations_fail(self) -> None:
        artifact, details, accesses, associations = self.case()
        self.error("duplicate_record", (artifact, details + copy.deepcopy(details), accesses, associations))
        self.error("duplicate_association", (artifact, details, accesses, associations + associations))

    def test_reusing_one_detail_across_devices_fails(self) -> None:
        artifact, details, accesses, associations = self.case("physical")
        changed = replace(associations[1], detail_record=associations[0].detail_record)
        self.error("duplicate_association", (artifact, details, accesses, (associations[0], changed)))

    def test_missing_linked_records_and_unmatched_records_fail(self) -> None:
        artifact, details, accesses, associations = self.case()
        self.error("missing_detail_record", (artifact, [], accesses, associations))
        changed = replace(associations[0], access_record="absent-access")
        self.error("missing_access_record", (artifact, details, accesses, (changed,)))
        accesses.append({"record_id": "unmatched-access", "payload": {"port": 443}})
        self.error("unmatched_record", (artifact, details, accesses, associations))

    def test_conflicting_native_identifiers_types_ips_and_names_are_rejected(self) -> None:
        for key, value, code in (
            ("ormID", "other", "conflicting_attribute"),
            ("id", "other", "conflicting_attribute"),
            ("type", "other", "conflicting_attribute"),
            ("managementIp", "192.0.2.99", "conflicting_attribute"),
            ("name", "other", "conflicting_attribute"),
            ("parentOrmID", "other", "conflicting_attribute"),
            ("meIdentifier", {"managedElementID": "other"}, "conflicting_identifier"),
            ("children", [{}], "unsupported_structure"),
        ):
            with self.subTest(key=key):
                case = self.case()
                case[1][0]["payload"][key] = value
                self.error(code, case)

    def test_unknown_overlapping_configuration_must_match_exactly(self) -> None:
        for value in ({"first": [1, False], "second": [{"second": None, "first": True}]}, None, True):
            case = self.case("physical")
            case[1][0]["payload"]["unknownDevice"] = value
            self.error("conflicting_configuration", case)

    def test_nested_order_arrays_types_and_null_survive_standard_roundtrip(self) -> None:
        case = self.case()
        result = self.reconcile(case)
        device = self.roundtrip(result).objects[1]
        provenance = device.configuration["offlineDeviceReconciliation"]
        self.assertEqual(
            json.dumps(provenance["detail"]), json.dumps(case[1][0]["payload"]),
        )
        self.assertEqual(list(provenance["detail"]["futureDetail"]), ["second", "first"])
        self.assertEqual(list(provenance["detail"]["futureDetail"]["first"]), ["z", "a"])
        values = provenance["detail"]["futureDetail"]["second"]
        self.assertIsNone(values[0])
        self.assertIs(type(values[1]), bool)
        self.assertIs(type(values[2]), int)
        self.assertEqual(list(device.device_access.value["futureAccess"]), ["second", "first"])
        self.assertNotIn("missing", provenance["detail"])

    def test_separate_access_can_supply_missing_detail_access(self) -> None:
        artifact, details, accesses, associations = self.case()
        access = details[0]["payload"]["deviceSetup"].pop("deviceAccess")
        access["ormID"] = "retained-access-native-provenance"
        accesses.append({"record_id": "access-one", "payload": access})
        associations = (replace(associations[0], access_record="access-one"),)
        result = self.reconcile(self.acknowledged((artifact, details, accesses, associations)))
        device = self.roundtrip(result).objects[1]
        self.assertEqual(device.device_access.location, self.o.DeviceAccessLocation.TOP_LEVEL)
        self.assertEqual(device.device_access.value["ormID"], "retained-access-native-provenance")
        self.assertEqual(device.configuration["offlineDeviceReconciliation"]["separate_access"], access)

    def test_conflicting_detail_and_separate_access_is_not_overwritten(self) -> None:
        artifact, details, _, associations = self.case()
        accesses = [{"record_id": "access-one", "payload": {"connectionTimeout": 99}}]
        self.error("conflicting_access", (
            artifact, details, accesses, (replace(associations[0], access_record="access-one"),),
        ))

    def test_existing_tree_access_is_preserved_and_conflicts_reject(self) -> None:
        _, details, accesses, associations = self.case()
        artifact = self.e.adapt_tree_response(self.fixtures["incomplete_access"], **self.options).artifact
        data = artifact.to_dict()
        data["validation"] = {"scope": "offline-contract", "status": "valid", "issue_codes": []}
        data["objects"][1]["device_access"] = {"location": "deviceAccess", "value": {"port": 443}}
        artifact = self.a.parse_artifact(data)
        self.error("conflicting_access", (artifact, details, accesses, associations))
        details[0]["payload"]["deviceSetup"]["deviceAccess"] = {"port": 443}
        device = self.reconcile(self.acknowledged((artifact, details, accesses, associations))).to_inventory().objects[1]
        self.assertEqual(device.device_access.location, self.o.DeviceAccessLocation.TOP_LEVEL)

    def test_explicit_null_access_cannot_be_filled_silently(self) -> None:
        artifact, details, accesses, associations = self.case()
        data = artifact.to_dict()
        data["objects"][1]["device_access"] = {"location": "deviceAccess", "value": None}
        artifact = self.a.parse_artifact(data)
        self.error("conflicting_access", (artifact, details, accesses, associations))

    def test_missing_null_empty_access_stays_invalid(self) -> None:
        for value in ("absent", None, {}):
            case = self.case()
            setup = case[1][0]["payload"]["deviceSetup"]
            if value == "absent":
                del setup["deviceAccess"]
            else:
                setup["deviceAccess"] = value
            result = self.reconcile(case)
            self.assertIn("incomplete_device_access", result.artifact.validation.issue_codes)
            with self.assertRaises(self.contracts.ContractValidationError):
                self.roundtrip(result)

    def test_evidence_is_required_and_bound_in_preserved_artifact(self) -> None:
        artifact, details, accesses, associations = self.case()
        result = self.reconcile((artifact, details, accesses, (replace(associations[0], acknowledgement=None),)))
        self.assertEqual(result.artifact.validation.status, "valid")
        self.assertEqual(result.validation.issues[0].code, "unacknowledged_device_access")
        result.to_inventory()
        good = self.roundtrip(self.reconcile((artifact, details, accesses, associations)))
        provenance = good.objects[1].configuration["offlineDeviceReconciliation"]
        self.assertEqual(provenance["acknowledgement"]["evidence_reference"], "evidence-" + "1" * 32)
        self.assertEqual(provenance["scope"], "offline-planning-only")
        self.assertEqual(provenance["completeness"], "unverified")

    def test_raw_credentials_are_rejected_without_payload_leakage(self) -> None:
        for key in ("password", "username", "community", "authKey"):
            case = self.case()
            case[1][0]["payload"]["deviceSetup"]["deviceAccess"][key] = "RAW-SENSITIVE-MARKER"
            error = self.error("secret_value_not_allowed", case)
            report = "".join(traceback.format_exception(error)) + repr(error.result)
            self.assertNotIn("RAW-SENSITIVE-MARKER", report)

    def test_secret_references_null_credentials_and_masks_block_but_ordinary_null_does_not(self) -> None:
        for key, value in (
            ("password", {"secret_ref": "approved/vault/item"}),
            ("password", None), ("status", "*****"), ("status", "<masked>"),
        ):
            with self.subTest(key=key, value=value):
                case = self.case()
                case[1][0]["payload"]["deviceSetup"]["deviceAccess"][key] = value
                result = self.reconcile(case)
                self.assertIn("unresolved_credentials", result.artifact.validation.issue_codes)
                with self.assertRaises(self.contracts.ContractValidationError):
                    self.roundtrip(result)
        self.assertEqual(self.reconcile(self.case()).validation.status, "valid")

    def test_qualified_associations_cannot_cross_tree_controller_or_kind(self) -> None:
        artifact, details, accesses, associations = self.case()
        for reference in (
            replace(associations[0].source, tree=self.o.TreeName.ORGANIZATION),
            replace(associations[0].source, controller_id="other-controller"),
            replace(associations[0].source, kind=self.o.ControllerObjectKind.SITE),
        ):
            changed = replace(associations[0], source=reference)
            code = "invalid_association" if reference.kind == self.o.ControllerObjectKind.SITE else "context_mismatch"
            self.error(code, (artifact, details, accesses, (changed,)))

    def test_same_native_id_in_two_trees_needs_distinct_record_associations(self) -> None:
        physical, details, accesses, associations = self.case()
        organization, other_details, _, other_associations = self.case(tree=self.o.TreeName.ORGANIZATION)
        data = physical.to_dict()
        data["objects"] += list(organization.objects)
        both = self.a.parse_artifact(data)
        other_details[0]["record_id"] = "organization-detail"
        other = replace(other_associations[0], detail_record="organization-detail")
        result = self.reconcile(self.acknowledged((both, details + other_details, accesses, associations + (other,))))
        self.assertEqual(len(result.to_inventory().objects), 4)
        self.assertEqual({item.reference.tree for item in result.to_inventory().objects}, set(self.o.TreeName))
        self.error("duplicate_association", (both, details, accesses, associations + other_associations))

    def test_malformed_records_unsupported_versions_and_invalid_artifacts_reject(self) -> None:
        artifact, details, accesses, associations = self.case()
        self.error("invalid_type", (artifact, {}, accesses, associations))
        self.error("unknown_fields", (artifact, [{"record_id": "x", "payload": {}, "extra": 1}], [], ()))
        self.error("invalid_type", (artifact, [{"record_id": "x", "payload": []}], [], ()))
        self.error("unsupported_version", (
            replace(artifact, source=replace(artifact.source, version="1.0")), details, accesses, associations,
        ))
        self.error("invalid_artifact", (
            replace(artifact, validation=self.a.ArtifactValidationInformation("invalid", ("other_failure",))),
            details, accesses, associations,
        ))
        self.error("invalid_association", (artifact, details, accesses, ("ip-only",)))

    def test_full_workflow_plans_verify_and_detect_configuration_or_evidence_tampering(self) -> None:
        for tree in self.o.TreeName:
            source = self.roundtrip(self.reconcile(self.case(tree=tree)))
            destination = self.roundtrip(self.reconcile(self.case(tree=tree, controller_id="synthetic-destination")))
            mappings = self.mapped_destination(source, destination)
            plan = self.plan(source, destination, mappings)
            self.assertEqual([action.kind for action in plan.actions], ["skip", "skip"])
            verified = self.c.verify_controller_plan(
                json.loads(plan.to_json()), source, destination, mappings,
                complete_trees=(tree,), semantics_known_for=tuple(item.reference for item in source.objects),
                comparison_rules=self.rules(),
            )
            self.assertEqual(plan, verified)
            self.assertEqual(plan.plan_id, self.plan(self.roundtrip(self.reconcile(self.case(tree=tree))), destination, mappings).plan_id)
            for key, changed in (
                ("acknowledgement", None),
                ("detail", {"futureDetail": {"first": 1, "second": 2}}),
            ):
                altered = self.roundtrip(self.reconcile(self.case(tree=tree)))
                altered.objects[1].configuration["offlineDeviceReconciliation"][key] = changed
                self.assertEqual(self.plan(altered, destination, mappings).actions[1].kind, "blocked")
                with self.assertRaises(self.contracts.ContractValidationError):
                    self.c.verify_controller_plan(
                        json.loads(plan.to_json()), altered, destination, mappings,
                        complete_trees=(tree,), semantics_known_for=tuple(item.reference for item in altered.objects),
                        comparison_rules=self.rules(),
                    )

    def test_nested_order_difference_cannot_turn_into_skip_after_serialization(self) -> None:
        for value in (
            {"first": {"z": 2, "a": 1}, "second": [None, True, 1]},
            {"second": [None, 1, True], "first": {"z": 2, "a": 1}},
            {"second": [None, True, True], "first": {"z": 2, "a": 1}},
            {"second": [None, True, 1], "first": {"z": 2, "a": None}},
            {"second": [None, True, 1], "first": {"z": 2}},
        ):
            source = self.roundtrip(self.reconcile(self.case()))
            case = self.case(controller_id="synthetic-destination")
            case[1][0]["payload"]["futureDetail"] = value
            destination = self.roundtrip(self.reconcile(self.acknowledged(case)))
            plan = self.plan(source, destination, self.mapped_destination(source, destination))
            self.assertEqual(plan.actions[1].kind, "conflict")

    def test_external_sorting_of_reconciled_configuration_invalidates_bound_plan(self) -> None:
        source = self.roundtrip(self.reconcile(self.case()))
        destination = self.roundtrip(self.reconcile(self.case(controller_id="synthetic-destination")))
        mappings = self.mapped_destination(source, destination)
        plan = self.plan(source, destination, mappings)
        sorted_source = self.o.parse_controller_artifact(json.loads(json.dumps(source.to_artifact().to_dict(), sort_keys=True)))
        with self.assertRaises(self.contracts.ContractValidationError):
            self.c.verify_controller_plan(
                json.loads(plan.to_json()), sorted_source, destination, mappings,
                complete_trees=(self.o.TreeName.PHYSICAL,),
                semantics_known_for=tuple(item.reference for item in source.objects),
                comparison_rules=self.rules(),
            )

    def test_create_candidate_keeps_destination_id_unassigned(self) -> None:
        source = self.roundtrip(self.reconcile(self.case()))
        destination = self.o.normalize_tree(
            {"meIdentifier": {"managedElementID": "root-one"}, "children": []},
            **(self.options | {"controller_id": "synthetic-destination"}),
        )
        full = self.roundtrip(self.reconcile(self.case(controller_id="synthetic-destination")))
        mappings = self.mapped_destination(source, full)
        mappings[1].update(state="missing", destination=None)
        plan = self.plan(source, destination, mappings)
        self.assertEqual([action.kind for action in plan.actions], ["skip", "create"])
        self.assertIsNone(plan.actions[1].destination_index)
        self.c.verify_controller_plan(
            json.loads(plan.to_json()), source, destination, mappings,
            complete_trees=(self.o.TreeName.PHYSICAL,),
            semantics_known_for=tuple(item.reference for item in source.objects),
            comparison_rules=self.rules(),
        )

    def test_result_association_and_reports_hide_payloads(self) -> None:
        case = self.case()
        result = self.reconcile(case)
        rendered = repr(result) + repr(case[3])
        for marker in ("synthetic-source", "192.0.2.50", "futureDetail", "evidence-" + "1" * 32):
            self.assertNotIn(marker, rendered)

    def test_reconciliation_cannot_be_reapplied_or_hide_existing_reserved_fields(self) -> None:
        case = self.case()
        result = self.reconcile(case)
        self.error("reserved_configuration", (result.artifact, case[1], case[2], case[3]))

    def test_missing_acknowledgement_blocks_only_affected_controller_device(self) -> None:
        artifact, details, accesses, associations = self.case("physical")
        associations = (replace(associations[0], acknowledgement=None), associations[1])
        result = self.reconcile((artifact, details, accesses, associations))
        self.assertEqual(result.artifact.validation.status, "valid")
        self.assertEqual(result.validation.status, "invalid")
        source = self.roundtrip(result)
        destination = self.roundtrip(self.reconcile(self.case("physical", controller_id="synthetic-destination")))
        plan = self.plan(source, destination, self.mapped_destination(source, destination))
        self.assertEqual([item.kind for item in plan.actions], ["skip", "skip", "skip", "blocked", "skip"])
        self.assertIn("unacknowledged_device_access", plan.actions[3].issue_codes)
        self.assertIn("futureDetail", result.artifact.to_json())

    def test_valid_acknowledgement_binds_identity_source_access_policy_and_stays_protected(self) -> None:
        case = self.case()
        acknowledgement = case[3][0].acknowledgement
        provenance = self.reconcile(case).artifact.objects[1]["configuration"]["offlineDeviceReconciliation"]
        self.assertEqual(acknowledgement.device, case[3][0].source)
        self.assertEqual(acknowledgement.source_artifact_sha256, provenance["source_artifact_sha256"])
        self.assertEqual(acknowledgement.policy_version, self.p.DEVICE_ACCESS_POLICY)
        self.assertEqual(len(acknowledgement.access_sha256), 64)
        self.assertEqual(self.p.device_access_acknowledgement_issues(self.roundtrip(self.reconcile(case))), {
            acknowledgement.device: (),
        })
        self.assertNotIn(acknowledgement.evidence_reference, repr(acknowledgement))
        destination = self.roundtrip(self.reconcile(self.case(controller_id="synthetic-destination")))
        source = self.roundtrip(self.reconcile(case))
        mappings = self.mapped_destination(source, destination)
        strict = self.c.compare_controller_inventories(
            source, destination, mappings, semantics_known_for=tuple(item.reference for item in source.objects),
        )
        self.assertEqual(strict.actions[1].kind, "conflict")
        selected = self.plan(source, destination, mappings)
        self.assertEqual(selected.actions[1].kind, "skip")
        self.assertEqual(len(selected.comparison_policy.ignored_fields), 2)
        self.assertTrue(any("controller_access_policy" in value for value in selected.comparison_policy.rule_evidence))
        self.assertNotIn(acknowledgement.evidence_reference, selected.to_json() + selected.summary())

    def test_mismatched_device_acknowledgements_are_blocked(self) -> None:
        artifact, details, accesses, associations = self.case()
        acknowledgement = associations[0].acknowledgement
        for reference in (
            replace(acknowledgement.device, controller_id="different-controller"),
            replace(acknowledgement.device, tree=self.o.TreeName.ORGANIZATION),
            replace(acknowledgement.device, object_id="different-device"),
        ):
            changed = replace(acknowledgement, device=reference)
            result = self.reconcile((artifact, details, accesses, (replace(associations[0], acknowledgement=changed),)))
            self.assertEqual(result.validation.issues[0].code, "mismatched_device_access_acknowledgement")
            source = self.roundtrip(result)
            destination = self.roundtrip(self.reconcile(self.case(controller_id="synthetic-destination")))
            plan = self.plan(source, destination, self.mapped_destination(source, destination))
            self.assertEqual(plan.actions[1].kind, "blocked")

    def test_changed_access_values_order_types_and_null_stale_prior_acknowledgement(self) -> None:
        for access in (
            {"connectionTimeout": 99},
            {"futureAccess": {"second": [True, 1, None], "first": False}, "connectionTimeout": 7},
            {"connectionTimeout": 7, "futureAccess": {"second": [1, True, None], "first": False}},
            {"connectionTimeout": 7, "futureAccess": {"second": [True, True, None], "first": False}},
            {"connectionTimeout": 7, "futureAccess": {"second": [True, 1, None]}},
        ):
            case = self.case()
            case[1][0]["payload"]["deviceSetup"]["deviceAccess"] = access
            result = self.reconcile(case)
            self.assertIn("stale_device_access_acknowledgement", [item.code for item in result.validation.issues])
            source = self.roundtrip(result)
            destination = self.roundtrip(self.reconcile(self.case(controller_id="synthetic-destination")))
            self.assertEqual(self.plan(source, destination, self.mapped_destination(source, destination)).actions[1].kind, "blocked")
            renewed = self.reconcile(self.acknowledged(case))
            self.assertEqual(renewed.validation.status, "valid")

    def test_changed_source_artifact_stales_acknowledgement(self) -> None:
        artifact, details, accesses, associations = self.case()
        data = artifact.to_dict()
        data["objects"][0]["configuration"]["additionalRootField"] = [True, 1]
        changed = self.a.parse_artifact(data)
        result = self.reconcile((changed, details, accesses, associations))
        self.assertEqual(result.validation.issues[0].code, "stale_device_access_acknowledgement")
        inventory = self.roundtrip(self.reconcile((artifact, details, accesses, associations)))
        inventory.objects[0].configuration["additionalRootField"] = [True, 1]
        self.assertEqual(self.p.device_access_acknowledgement_issues(inventory)[associations[0].source], (
            "stale_device_access_acknowledgement",
        ))

    def test_post_reconciliation_access_mutation_is_blocked_and_invalidates_plan(self) -> None:
        source = self.roundtrip(self.reconcile(self.case()))
        destination = self.roundtrip(self.reconcile(self.case(controller_id="synthetic-destination")))
        mappings = self.mapped_destination(source, destination)
        plan = self.plan(source, destination, mappings)
        source.objects[1].device_access.value["connectionTimeout"] = 99
        self.assertIn("stale_device_access_acknowledgement", self.plan(source, destination, mappings).actions[1].issue_codes)
        with self.assertRaises(self.contracts.ContractValidationError):
            self.c.verify_controller_plan(
                json.loads(plan.to_json()), source, destination, mappings,
                complete_trees=(self.o.TreeName.PHYSICAL,), comparison_rules=self.rules(),
                semantics_known_for=tuple(item.reference for item in source.objects),
            )

    def test_policy_mismatch_legacy_provenance_and_bad_evidence_are_blocked_after_roundtrip(self) -> None:
        for mutation, code in (
            ("policy", "mismatched_device_access_acknowledgement"),
            ("legacy", "invalid_device_access_acknowledgement"),
            ("evidence", "invalid_device_access_acknowledgement"),
        ):
            result = self.reconcile(self.case())
            data = result.artifact.to_dict()
            provenance = data["objects"][1]["configuration"]["offlineDeviceReconciliation"]
            if mutation == "policy":
                provenance["acknowledgement"]["policy_version"] = "previous-policy-v0"
            elif mutation == "legacy":
                provenance["schema_version"] = 1
            else:
                provenance["acknowledgement"]["evidence_reference"] = "192.0.2.50"
            inventory = self.o.parse_controller_artifact(json.loads(self.a.parse_artifact(data).to_json()))
            self.assertEqual(self.p.device_access_acknowledgement_issues(inventory)[inventory.objects[1].reference], (code,))
            destination = self.roundtrip(self.reconcile(self.case(controller_id="synthetic-destination")))
            plan = self.plan(inventory, destination, self.mapped_destination(inventory, destination))
            self.assertEqual(plan.actions[1].kind, "blocked")
            self.assertIn(code, plan.actions[1].issue_codes)

    def test_evidence_reference_rejects_addresses_credentials_and_session_tokens_without_echo(self) -> None:
        case = self.case()
        preview = self.reconcile(case)
        for value in ("192.0.2.50", "2001:db8::50", "RAW-PASSWORD-MARKER", "session-token-secret", "https://host/path"):
            with self.assertRaises(self.contracts.ContractValidationError) as caught:
                self.p.acknowledge_device_access(
                    case[0], preview.artifact, case[3][0].source, evidence_reference=value,
                )
            self.assertEqual(caught.exception.result.issues[0].code, "invalid_evidence_reference")
            self.assertNotIn(value, str(caught.exception) + repr(caught.exception.result))

    def test_acknowledgement_cannot_override_structural_or_sensitive_failures(self) -> None:
        for value in (None, {}, {"password": None}, {"password": {"secret_ref": "approved/vault/item"}}, {"status": "*****"}):
            case = self.case()
            case[1][0]["payload"]["deviceSetup"]["deviceAccess"] = value
            result = self.reconcile(case)
            self.assertEqual(result.artifact.validation.status, "invalid")
            with self.assertRaises(self.contracts.ContractValidationError):
                result.to_inventory()
        for field in ("name", "parent"):
            case = self.case()
            data = case[0].to_dict()
            if field == "name":
                del data["objects"][1]["name"]
            else:
                data["objects"][1]["parent"]["object_id"] = "absent-parent"
            with self.assertRaises(self.contracts.ContractValidationError):
                self.reconcile((self.a.parse_artifact(data), case[1], case[2], case[3]))

    def test_generic_planner_cannot_bypass_missing_device_acknowledgement(self) -> None:
        module = importlib.import_module("cc_vision_import.plans")
        case = self.case()
        unsigned = (replace(case[3][0], acknowledgement=None),)
        result = self.reconcile((case[0], case[1], case[2], unsigned))
        source = self.roundtrip(result)
        destination = self.roundtrip(self.reconcile(self.case(controller_id="synthetic-destination")))
        mappings = self.mapped_destination(source, destination)
        with self.assertRaises(self.contracts.ContractValidationError) as caught:
            module.create_plan(result.artifact.to_json().encode("utf-8"), self.generic_request(mappings))
        self.assertEqual(caught.exception.result.issues[0].code, "controller_planning_required")

    def test_generic_planner_rejects_even_fully_acknowledged_controller_artifacts(self) -> None:
        generic = importlib.import_module("cc_vision_import.plans")
        source = self.roundtrip(self.reconcile(self.case()))
        destination = self.roundtrip(self.reconcile(self.case(controller_id="synthetic-destination")))
        self.assertFalse(any(self.p.device_access_acknowledgement_issues(source).values()))
        for root_missing in (False, True):
            with self.subTest(root_missing=root_missing):
                mappings = self.mapped_destination(source, destination)
                if root_missing:
                    mappings[0].update(state="missing", destination=None)
                controller = self.plan(source, destination, mappings)
                self.assertEqual(controller.actions[0].kind, "blocked" if root_missing else "skip")
                if root_missing:
                    self.assertIn("root_unresolved", controller.actions[0].issue_codes)
                with self.assertRaises(self.contracts.ContractValidationError) as caught:
                    generic.create_plan(source.to_artifact().to_json().encode("utf-8"), self.generic_request(mappings))
                self.assertEqual(caught.exception.result.issues[0].code, "controller_planning_required")

    def test_legacy_generic_controller_plans_fail_closed_at_every_envelope_boundary(self) -> None:
        generic = importlib.import_module("cc_vision_import.plans")
        source = self.roundtrip(self.reconcile(self.case()))
        destination = self.roundtrip(self.reconcile(self.case(controller_id="synthetic-destination")))
        mappings = self.mapped_destination(source, destination)
        mappings[0].update(state="missing", destination=None)
        request = self.generic_request(mappings)
        raw = source.to_artifact().to_json().encode("utf-8")
        surrogate = source.to_artifact().to_dict()
        surrogate["source"]["product"] = "vision"
        surrogate_request = copy.deepcopy(request)
        for mapping in surrogate_request["mappings"]:
            mapping["source_context"]["product"] = "vision"
        plan = generic.create_plan(self.a.parse_artifact(surrogate).to_json().encode("utf-8"), surrogate_request)
        payload = plan.to_dict()
        source_identity = {
            **payload["source_artifact"], "source": asdict(source.source),
            "sha256": hashlib.sha256(raw).hexdigest(),
            "artifact_id": "sha256:" + hashlib.sha256(raw).hexdigest(),
        }
        payload["source_artifact"] = source_identity
        payload["mappings"] = mappings
        body = {key: value for key, value in payload.items() if key not in ("plan_id", "integrity_sha256")}

        def digest(value):
            encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)
            return hashlib.sha256(encoded.encode("utf-8")).hexdigest()

        payload["plan_id"] = "plan-" + digest(body)
        payload["integrity_sha256"] = digest({"plan_id": payload["plan_id"], **body})
        legacy = replace(
            plan,
            source_artifact=replace(
                plan.source_artifact, source=source.source,
                sha256=source_identity["sha256"], artifact_id=source_identity["artifact_id"],
            ),
            mappings=tuple(replace(item, source_context=source.source) for item in plan.mappings),
            plan_id=payload["plan_id"], integrity_sha256=payload["integrity_sha256"],
        )
        for function, args in (
            (generic.parse_plan, (payload,)),
            (generic.verify_plan, (payload, raw, request["destination"], payload["integrity_sha256"])),
            (legacy.to_dict, ()),
            (legacy.to_json, ()),
        ):
            with self.subTest(boundary=function.__name__):
                with self.assertRaises(self.contracts.ContractValidationError) as caught:
                    function(*args)
                self.assertEqual(caught.exception.result.issues[0].code, "controller_planning_required")
        validation = generic.validate_plan(payload)
        self.assertEqual(validation.status, "invalid")
        self.assertEqual(validation.issues[0].code, "controller_planning_required")

    def test_acknowledgement_rule_preserves_unknown_root_and_site_configuration(self) -> None:
        raw = copy.deepcopy(self.fixtures["organization"])
        raw["children"][0]["children"] = []
        for tree in self.o.TreeName:
            for index in (0, 1):
                for changed in ("acknowledgement", "source_artifact_sha256", "ordering"):
                    with self.subTest(tree=tree, index=index, changed=changed):
                        inventories = []
                        for controller in ("synthetic-source", "synthetic-destination"):
                            inventory = self.o.normalize_tree(
                                copy.deepcopy(raw), **(self.options | {"tree": tree, "controller_id": controller}),
                            )
                            inventory.objects[index].configuration[self.p.RECONCILIATION_FIELD] = {
                                "acknowledgement": {"second": [None, True, 1], "first": False},
                                "source_artifact_sha256": "1" * 64,
                            }
                            inventories.append(inventory)
                        source, destination = inventories
                        mappings = self.mapped_destination(source, destination)
                        identical = self.plan(source, destination, mappings)
                        self.assertTrue(all(action.kind == "skip" for action in identical.actions))
                        metadata = destination.objects[index].configuration[self.p.RECONCILIATION_FIELD]
                        if changed == "acknowledgement":
                            metadata["acknowledgement"]["first"] = True
                        elif changed == "ordering":
                            metadata["acknowledgement"] = dict(reversed(list(metadata["acknowledgement"].items())))
                        else:
                            metadata["source_artifact_sha256"] = "2" * 64
                        source, destination = (
                            self.o.parse_controller_artifact(json.loads(item.to_artifact().to_json()))
                            for item in (source, destination)
                        )
                        plan = self.plan(source, destination, mappings)
                        self.assertEqual(plan.actions[index].kind, "conflict")
                        keywords = {
                            "complete_trees": (tree,), "comparison_rules": self.rules(),
                            "semantics_known_for": tuple(item.reference for item in source.objects),
                        }
                        self.c.verify_controller_plan(plan.to_dict(), source, destination, mappings, **keywords)
                        with self.assertRaises(self.contracts.ContractValidationError):
                            self.c.verify_controller_plan(identical.to_dict(), source, destination, mappings, **keywords)

    def test_unreconciled_controller_access_also_requires_current_explicit_acknowledgements(self) -> None:
        source_result = self.e.adapt_tree_response(self.fixtures["organization"], **self.options)
        destination_result = self.e.adapt_tree_response(
            self.fixtures["organization"],
            **(self.options | {"controller_id": "synthetic-destination"}),
        )
        source, destination = self.roundtrip(source_result), self.roundtrip(destination_result)
        mappings = self.mapped_destination(source, destination)
        without = self.plan(source, destination, mappings)
        self.assertEqual([item.kind for item in without.actions], ["skip", "skip", "blocked"])
        self.assertIn("unacknowledged_device_access", without.actions[2].issue_codes)
        acknowledgements = tuple(
            self.p.acknowledge_device_access(
                inventory.to_artifact(), inventory.to_artifact(), item.reference,
                evidence_reference="evidence-" + "3" * 32,
            )
            for inventory in (source, destination) for item in inventory.objects
            if isinstance(item, self.o.ControllerDevice)
        )
        keywords = {
            "semantics_known_for": tuple(item.reference for item in source.objects),
            "device_access_acknowledgements": acknowledgements,
        }
        plan = self.c.compare_controller_inventories(source, destination, mappings, **keywords)
        self.assertTrue(all(item.kind == "skip" for item in plan.actions))
        self.assertEqual(plan.comparison_policy.device_access_policy, self.p.DEVICE_ACCESS_POLICY)
        self.c.verify_controller_plan(json.loads(plan.to_json()), source, destination, mappings, **keywords)
        source.objects[2].device_access.value["connectionTimeout"] = 99
        stale = self.c.compare_controller_inventories(source, destination, mappings, **keywords)
        self.assertIn("stale_device_access_acknowledgement", stale.actions[2].issue_codes)
        self.assertEqual(stale.actions[2].kind, "blocked")

    def test_shared_boundary_blocks_all_unacknowledged_inventory_and_export_paths(self) -> None:
        generic = importlib.import_module("cc_vision_import.plans")
        for origin in ("A/B-normalized", "C1-recursive", "C1-flat", "C2-reconciled"):
            for tree in self.o.TreeName:
                with self.subTest(origin=origin, tree=tree):
                    source, destination = self.planning_pair(origin, tree)
                    before = (source.to_artifact().to_json(), destination.to_artifact().to_json())
                    mappings = self.mapped_destination(source, destination)
                    validated = self.v.validate_controller_planning(
                        source, destination, mappings, complete_trees=(tree,),
                    )
                    self.assertEqual(validated.validation.status, "invalid")
                    plan = self.plan(source, destination, mappings)
                    by_index = {action.source_index: action for action in plan.actions}
                    for index, item in enumerate(source.objects):
                        if isinstance(item, self.o.ControllerDevice):
                            self.assertIn("unacknowledged_device_access", validated.entries[index].issue_codes)
                            self.assertEqual(by_index[index].kind, "blocked")
                        else:
                            self.assertEqual(validated.entries[index].issue_codes, ())
                    self.c.verify_controller_plan(
                        json.loads(plan.to_json()), source, destination, mappings,
                        complete_trees=(tree,), comparison_rules=self.rules(),
                        semantics_known_for=tuple(item.reference for item in source.objects),
                    )
                    with self.assertRaises(self.contracts.ContractValidationError) as caught:
                        generic.create_plan(source.to_artifact().to_json().encode("utf-8"), self.generic_request(mappings))
                    self.assertEqual(caught.exception.result.issues[0].code, "controller_planning_required")
                    self.assertEqual(source.to_artifact().schema_version, 1)
                    self.assertEqual(plan.schema_version, 2)
                    self.assertEqual((source.to_artifact().to_json(), destination.to_artifact().to_json()), before)

    def test_shared_boundary_accepts_current_and_rejects_stale_source_or_destination_acknowledgements(self) -> None:
        for changed in ("source", "destination"):
            source, destination = self.planning_pair("A/B-normalized", self.o.TreeName.PHYSICAL)
            mappings = self.mapped_destination(source, destination)
            acknowledgements = device_access_acknowledgements(source, destination)
            valid = self.v.validate_controller_planning(
                source, destination, mappings, device_access_acknowledgements=acknowledgements,
            )
            self.assertEqual(valid.validation.status, "valid")
            inventory = source if changed == "source" else destination
            inventory.objects[-1].device_access.value["connectionTimeout"] = 99
            invalid = self.v.validate_controller_planning(
                source, destination, mappings, device_access_acknowledgements=acknowledgements,
            )
            self.assertIn("stale_device_access_acknowledgement", invalid.entries[-1].issue_codes)
            self.assertEqual(invalid.validation.status, "invalid")

    def test_shared_boundary_never_authorizes_same_named_device_in_another_tree(self) -> None:
        physical = self.planning_pair("A/B-normalized", self.o.TreeName.PHYSICAL)
        organization = self.planning_pair("A/B-normalized", self.o.TreeName.ORGANIZATION)
        inventories = []
        for first, second in zip(physical, organization, strict=True):
            payload = first.to_artifact().to_dict()
            payload["objects"].extend(second.to_artifact().objects)
            inventories.append(self.o.parse_controller_artifact(payload))
        source, destination = inventories
        mappings = self.mapped_destination(source, destination)
        for mapping, target in zip(mappings, destination.objects, strict=True):
            mapping["destination"] = asdict(target.reference.as_identity())
        # Cross-tree fixtures deliberately share names, addresses, and native IDs.
        self.assertEqual(source.objects[2].name, source.objects[5].name)
        self.assertEqual(source.objects[2].reference.object_id, source.objects[5].reference.object_id)
        for allowed in ("physical-source-only", "physical-both-controllers"):
            acknowledgements = tuple(
                item for item in device_access_acknowledgements(source, destination)
                if item.device.tree == self.o.TreeName.PHYSICAL and (
                    allowed == "physical-both-controllers" or item.device.controller_id == "synthetic-source"
                )
            )
            validated = self.v.validate_controller_planning(
                source, destination, mappings, device_access_acknowledgements=acknowledgements,
            )
            self.assertIn("unacknowledged_device_access", validated.entries[5].issue_codes)
            expected = () if allowed == "physical-both-controllers" else ("unacknowledged_device_access",)
            self.assertEqual(validated.entries[2].issue_codes, expected)

    def test_shared_boundary_acknowledgement_never_overrides_unsafe_or_invalid_configuration(self) -> None:
        for access in ({}, {"status": "*****"}, {"password": None}, {"password": {"secret_ref": "approved/vault/item"}}):
            source, destination = self.planning_pair("A/B-normalized", self.o.TreeName.PHYSICAL)
            mappings = self.mapped_destination(source, destination)
            acknowledgements = device_access_acknowledgements(source, destination)
            source.objects[-1].device_access.value.clear()
            source.objects[-1].device_access.value.update(access)
            validated = self.v.validate_controller_planning(
                source, destination, mappings, device_access_acknowledgements=acknowledgements,
            )
            self.assertEqual(validated.validation.status, "invalid")
            expected = "incomplete_device_access" if access == {} else "unresolved_credentials"
            self.assertIn(expected, validated.entries[-1].issue_codes)
        for failure in ("missing-name", "invalid-parent", "conflicting-identity", "raw-password"):
            source, destination = self.planning_pair("A/B-normalized", self.o.TreeName.PHYSICAL)
            mappings = self.mapped_destination(source, destination)
            acknowledgements = device_access_acknowledgements(source, destination)
            device = source.objects[-1]
            if failure == "missing-name":
                source = replace(source, objects=source.objects[:-1] + (replace(device, name=""),))
            elif failure == "invalid-parent":
                parent = replace(device.parent, object_id="absent-parent")
                source = replace(source, objects=source.objects[:-1] + (replace(device, parent=parent),))
            elif failure == "conflicting-identity":
                device.configuration["ormID"] = "different-native-device"
            else:
                device.device_access.value["password"] = "RAW-SENSITIVE-MARKER"
            with self.assertRaises(self.contracts.ContractValidationError):
                self.v.validate_controller_planning(
                    source, destination, mappings, device_access_acknowledgements=acknowledgements,
                )
