import copy
import hashlib
import importlib
import io
import json
import traceback
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import asdict, replace
from pathlib import Path
from unittest.mock import patch

from offline_support import OfflineTestCase, device_access_acknowledgements


class ControllerComparisonTests(OfflineTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.o = importlib.import_module("cc_vision_import.controller_objects")
        self.p = importlib.import_module("cc_vision_import.controller_planning")
        self.c = importlib.import_module("cc_vision_import.controller_comparison")
        self.m = importlib.import_module("cc_vision_import.controller_mapping")
        self.contracts = importlib.import_module("cc_vision_import.contracts")
        fixtures = Path(__file__).parent / "fixtures"
        self.native = json.loads((fixtures / "controller-physical.json").read_text(encoding="utf-8"))
        # General comparison cases use credential-free synthetic settings.
        access = self.native["children"][0]["children"][0]["children"][0]["deviceSetup"]["deviceAccess"]
        del access["cliUsername"]
        del access["cliPassword"]
        self.provenance_rules = (self.c.ControllerComparisonRule.NATIVE_IDENTITY_PROVENANCE,)
        self.source = self.normalize(self.native, self.o.TreeName.PHYSICAL)
        self.initialize_destination()

    def normalize(self, native, tree):
        return self.o.normalize_tree(
            native, controller_id="synthetic-source", tree=tree, version="0.0-test",
            exported_at="2026-11-18T00:00:00Z",
        )

    def initialize_destination(self) -> None:
        payload = self.source.to_artifact().to_dict()
        for item in payload["objects"]:
            for key in ("reference", "parent"):
                if item[key] is not None:
                    item[key]["controller_id"] = "synthetic-destination"
                    item[key]["object_id"] = "dst-" + item[key]["object_id"]
            config = item["configuration"]
            if "meIdentifier" in config:
                config["meIdentifier"]["managedElementID"] = item["reference"]["object_id"]
            if "ormID" in config:
                config["ormID"] = item["reference"]["object_id"]
            if "parentOrmID" in config:
                config["parentOrmID"] = None if item["parent"] is None else item["parent"]["object_id"]
        self.destination = self.o.parse_controller_artifact(payload)
        indices = {item.reference: index for index, item in enumerate(self.source.objects)}
        self.records = []
        for index, (source, destination) in enumerate(zip(self.source.objects, self.destination.objects, strict=True)):
            parent = None if isinstance(source, self.o.ControllerRoot) else f"map-{indices[source.parent]}"
            self.records.append({
                "mapping_id": f"map-{index}", "domain": "controller-objects", "source_index": index,
                "source": asdict(source.reference.as_identity()), "source_context": asdict(self.source.source),
                "destination_context": asdict(self.destination.source), "state": "resolved",
                "destination": asdict(destination.reference.as_identity()), "candidates": [],
                "parent_mapping": parent, "depends_on": [] if parent is None else [parent],
            })

    def missing(self, *indices) -> None:
        targets = {self.destination.objects[index].reference for index in indices}
        payload = self.destination.to_artifact().to_dict()
        payload["objects"] = [
            item for index, item in enumerate(payload["objects"])
            if self.destination.objects[index].reference not in targets
        ]
        self.destination = self.o.parse_controller_artifact(payload)
        for index in indices:
            self.records[index].update(state="missing", destination=None)

    def plan(self, *, known=True, complete=True, records=None, rules=None):
        return self.c.compare_controller_inventories(
            self.source, self.destination, self.records if records is None else records,
            complete_trees=tuple(sorted({item.reference.tree for item in self.destination.objects})) if complete else (),
            semantics_known_for=tuple(item.reference for item in self.source.objects) if known else (),
            comparison_rules=self.provenance_rules if rules is None else rules,
            device_access_acknowledgements=device_access_acknowledgements(self.source, self.destination),
        )

    def actions(self, plan):
        return {item.source_index: item for item in plan.actions}

    def standard_artifact_roundtrip(self) -> None:
        artifacts = importlib.import_module("cc_vision_import.artifacts")
        for attribute in ("source", "destination"):
            encoded = getattr(self, attribute).to_artifact().to_json()
            artifact = artifacts.parse_artifact(json.loads(encoded))
            setattr(self, attribute, self.o.parse_controller_artifact(json.loads(artifact.to_json())))

    def verify_candidate(self, plan):
        return self.c.verify_controller_plan(
            json.loads(plan.to_json()), self.source, self.destination, self.records,
            complete_trees=tuple(sorted({item.reference.tree for item in self.destination.objects})),
            semantics_known_for=tuple(item.reference for item in self.source.objects),
            comparison_rules=self.provenance_rules,
            device_access_acknowledgements=device_access_acknowledgements(self.source, self.destination),
        )

    def error(self, code, function, *args, **kwargs):
        with self.assertRaises(self.contracts.ContractValidationError) as caught:
            function(*args, **kwargs)
        self.assertEqual(caught.exception.result.issues[0].code, code)
        return caught.exception

    def combine_trees(self) -> None:
        fixture = Path(__file__).parent / "fixtures" / "controller-organization.json"
        organization = self.normalize(json.loads(fixture.read_text(encoding="utf-8")), self.o.TreeName.ORGANIZATION)
        payload = self.source.to_artifact().to_dict()
        payload["objects"].extend(organization.to_artifact().to_dict()["objects"])
        self.source = self.o.parse_controller_artifact(payload)
        self.initialize_destination()

    def test_identical_settings_skip_despite_independently_resolved_native_ids(self) -> None:
        plan = self.plan()
        self.assertTrue(all(item.kind == "skip" for item in plan.actions))
        self.assertNotEqual(self.source.objects[1].reference.object_id, self.destination.objects[1].reference.object_id)
        self.assertEqual(len(plan.actions), len(self.source.objects))

    def test_confirmed_missing_device_uses_existing_mapped_parent_without_destination_id(self) -> None:
        self.missing(5)
        actions = self.actions(self.plan())
        self.assertEqual(actions[5].kind, "create")
        self.assertIsNone(actions[5].destination_index)
        self.assertEqual(actions[5].parent_action, "object-4")
        self.assertEqual(actions[4].kind, "skip")
        self.assertEqual(actions[5].depends_on, ("object-4",))

    def test_nested_creates_depend_on_parent_creates_and_existing_root(self) -> None:
        self.missing(1, 2, 3)
        plan = self.plan()
        actions = self.actions(plan)
        self.assertEqual([actions[index].kind for index in (0, 1, 2, 3)], ["skip", "create", "create", "create"])
        for index, parent in ((1, 0), (2, 1), (3, 2)):
            self.assertEqual(actions[index].parent_action, f"object-{parent}")
            self.assertIn(f"object-{parent}", actions[index].depends_on)
            self.assertIsNone(actions[index].destination_index)
            self.assertLess(plan.actions.index(actions[parent]), plan.actions.index(actions[index]))

    def test_missing_mapping_records_are_blocked_not_assumed_missing(self) -> None:
        records = [item for item in self.records if item["source_index"] != 5]
        action = self.actions(self.plan(records=records))[5]
        self.assertEqual(action.kind, "blocked")
        self.assertIn("mapping_absent", action.issue_codes)
        self.assertNotEqual(action.comparison, "missing")

    def test_unknown_and_ambiguous_mappings_do_not_become_creates(self) -> None:
        for state in ("unresolved", "ambiguous"):
            with self.subTest(state=state):
                records = copy.deepcopy(self.records)
                records[1].update(state=state, destination=None)
                if state == "ambiguous":
                    records[1]["candidates"] = [self.records[1]["destination"], self.records[4]["destination"]]
                actions = self.actions(self.plan(records=records))
                self.assertEqual(actions[1].kind, "blocked")
                self.assertIn("mapping_" + state, actions[1].issue_codes)
                self.assertEqual(actions[2].kind, "blocked")
                self.assertEqual(actions[4].kind, "skip")

    def test_incomplete_destination_tree_blocks_explicit_missing(self) -> None:
        self.missing(1, 2, 3)
        actions = self.actions(self.plan(complete=False))
        self.assertEqual(actions[1].kind, "blocked")
        self.assertIn("incomplete_destination", actions[1].issue_codes)
        self.assertTrue(all(actions[index].kind == "blocked" for index in (1, 2, 3)))
        self.assertEqual(actions[4].kind, "skip")

    def test_completeness_is_independent_for_each_tree(self) -> None:
        self.combine_trees()
        self.missing(5, 8)
        plan = self.c.compare_controller_inventories(
            self.source, self.destination, self.records,
            complete_trees=(self.o.TreeName.PHYSICAL,),
            semantics_known_for=tuple(item.reference for item in self.source.objects),
            comparison_rules=self.provenance_rules,
        )
        actions = self.actions(plan)
        self.assertEqual(actions[5].kind, "create")
        self.assertEqual(actions[8].kind, "blocked")
        self.assertIn("incomplete_destination", actions[8].issue_codes)

    def test_existing_mapping_to_absent_target_is_not_reclassified_as_missing(self) -> None:
        payload = self.destination.to_artifact().to_dict()
        payload["objects"].pop(5)
        self.destination = self.o.parse_controller_artifact(payload)
        action = self.actions(self.plan())[5]
        self.assertEqual(action.kind, "blocked")
        self.assertIn("destination_absent", action.issue_codes)

    def test_roots_must_resolve_to_existing_destination_roots(self) -> None:
        for state in ("missing", "unresolved", "absent", "missing-target"):
            with self.subTest(state=state):
                records = copy.deepcopy(self.records)
                if state == "absent":
                    records.pop(0)
                elif state == "missing-target":
                    records[0]["destination"]["object_id"] = "not-in-destination"
                else:
                    records[0].update(state=state, destination=None)
                actions = self.actions(self.plan(records=records))
                self.assertIn("root_unresolved", actions[0].issue_codes)
                self.assertTrue(all(item.kind == "blocked" for item in actions.values()))

    def test_forged_and_rehashed_root_creates_fail_controller_verification(self) -> None:
        keywords = {
            "complete_trees": (self.o.TreeName.PHYSICAL,),
            "semantics_known_for": tuple(item.reference for item in self.source.objects),
            "comparison_rules": self.provenance_rules,
            "device_access_acknowledgements": device_access_acknowledgements(self.source, self.destination),
        }

        def digest(value):
            encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)
            return hashlib.sha256(encoded.encode("utf-8")).hexdigest()

        for root_missing in (False, True):
            records = copy.deepcopy(self.records)
            if root_missing:
                records[0].update(state="missing", destination=None)
            plan = self.plan(records=records)
            self.assertEqual(self.actions(plan)[0].kind, "blocked" if root_missing else "skip")
            self.c.verify_controller_plan(plan.to_dict(), self.source, self.destination, records, **keywords)
            actions = tuple(
                replace(
                    item, kind=self.c.ActionKind.CREATE, comparison=self.c.Comparison.MISSING,
                    destination_index=None, issue_codes=(),
                ) if item.source_index == 0 else item
                for item in plan.actions
            )
            for rehashed in (False, True):
                with self.subTest(root_missing=root_missing, rehashed=rehashed):
                    forged = replace(plan, actions=actions)
                    if rehashed:
                        body = asdict(forged)
                        del body["plan_id"], body["integrity_sha256"]
                        plan_id = "controller-plan-" + digest(body)
                        forged = replace(
                            forged, plan_id=plan_id,
                            integrity_sha256=digest({"plan_id": plan_id, **body}),
                        )
                        payload = forged.to_dict()
                    else:
                        payload = asdict(forged)
                    self.error(
                        "integrity_mismatch", self.c.verify_controller_plan,
                        payload, self.source, self.destination, records, **keywords,
                    )

    def test_missing_root_in_one_tree_does_not_block_the_other_tree(self) -> None:
        self.combine_trees()
        payload = self.destination.to_artifact().to_dict()
        payload["objects"] = payload["objects"][:6]
        self.destination = self.o.parse_controller_artifact(payload)
        plan = self.plan()
        self.assertTrue(all(item.kind == "skip" for item in plan.actions if item.tree == "Physical"))
        self.assertTrue(all(item.kind == "blocked" for item in plan.actions if item.tree == "Organization"))

    def test_comparison_semantics_default_to_blocked_even_for_equal_configurations(self) -> None:
        plan = self.c.compare_controller_inventories(self.source, self.destination, self.records)
        self.assertTrue(all(item.kind == "blocked" for item in plan.actions))
        self.assertTrue(all("unknown_semantics" in item.issue_codes for item in plan.actions))

    def test_semantics_acknowledgement_is_per_object(self) -> None:
        plan = self.c.compare_controller_inventories(
            self.source, self.destination, self.records,
            semantics_known_for=tuple(item.reference for index, item in enumerate(self.source.objects) if index != 5),
            comparison_rules=self.provenance_rules,
        )
        actions = self.actions(plan)
        self.assertEqual(actions[4].kind, "skip")
        self.assertEqual(actions[5].kind, "blocked")
        self.assertIn("unknown_semantics", actions[5].issue_codes)

    def test_unknown_configuration_is_compared_only_with_explicit_acknowledgement(self) -> None:
        self.destination.objects[5].configuration["opaqueDevice"]["preserved"] = [7]
        self.assertEqual(self.actions(self.plan())[5].kind, "conflict")
        self.assertEqual(self.actions(self.plan(known=False))[5].kind, "blocked")

    def test_names_are_compared_as_settings_but_never_used_for_identity(self) -> None:
        payload = self.destination.to_artifact().to_dict()
        payload["objects"][5]["name"] = "Different destination name"
        self.destination = self.o.parse_controller_artifact(payload)
        action = self.actions(self.plan())[5]
        self.assertEqual(action.kind, "conflict")
        self.assertEqual(action.destination_index, 5)

    def test_json_types_list_order_and_absent_versus_null_are_not_silently_normalized(self) -> None:
        self.source.objects[5].configuration["opaqueDevice"] = {"preserved": [1, None]}
        for configuration in ({"preserved": [True, None]}, {"preserved": [None, 1]}):
            with self.subTest(configuration=configuration):
                self.destination.objects[5].configuration["opaqueDevice"] = configuration
                self.assertEqual(self.actions(self.plan())[5].kind, "conflict")
        self.source.objects[5].configuration["opaqueDevice"] = {}
        self.destination.objects[5].configuration["opaqueDevice"] = {"additional": None}
        self.assertEqual(self.actions(self.plan())[5].kind, "conflict")

    def test_parent_conflict_blocks_descendants_but_not_other_branches(self) -> None:
        self.destination.objects[1].configuration["opaqueSite"]["color"] = "changed"
        actions = self.actions(self.plan())
        self.assertEqual(actions[1].kind, "conflict")
        for index in (2, 3):
            self.assertEqual(actions[index].kind, "blocked")
            self.assertIn("dependency_blocked", actions[index].issue_codes)
        self.assertEqual(actions[4].kind, "skip")

    def test_create_under_unresolved_parent_is_blocked(self) -> None:
        self.missing(3)
        self.records[2].update(state="unresolved", destination=None)
        action = self.actions(self.plan())[3]
        self.assertEqual(action.kind, "blocked")
        self.assertIn("dependency_blocked", action.issue_codes)

    def test_existing_child_cannot_be_relocated_beneath_a_planned_parent(self) -> None:
        payload = self.destination.to_artifact().to_dict()
        payload["objects"][3]["parent"] = copy.deepcopy(payload["objects"][1]["reference"])
        payload["objects"].pop(2)
        self.destination = self.o.parse_controller_artifact(payload)
        self.records[2].update(state="missing", destination=None)
        action = self.actions(self.plan())[3]
        self.assertEqual(action.kind, "blocked")
        self.assertIn("unresolved_parent", action.issue_codes)

    def test_target_collisions_block_all_affected_mappings(self) -> None:
        self.records[4]["destination"] = copy.deepcopy(self.records[1]["destination"])
        actions = self.actions(self.plan())
        for index in (1, 4):
            self.assertEqual(actions[index].kind, "blocked")
            self.assertIn("destination_collision", actions[index].issue_codes)

    def test_explicit_mappings_preserve_and_compare_duplicate_siblings(self) -> None:
        duplicate = copy.deepcopy(self.native["children"][0])
        duplicate["meIdentifier"]["managedElementID"] = "duplicate-site"
        duplicate["children"] = []
        self.native["children"].append(duplicate)
        self.source = self.normalize(self.native, self.o.TreeName.PHYSICAL)
        self.initialize_destination()
        plan = self.plan()
        self.assertEqual(len(plan.actions), 7)
        self.assertTrue(all(item.kind == "skip" for item in plan.actions))
        self.assertEqual(len(self.source.to_artifact().objects), 7)

    def test_cross_tree_targets_and_dependencies_are_blocked(self) -> None:
        self.combine_trees()
        self.records[1]["destination"] = copy.deepcopy(self.records[7]["destination"])
        self.records[4]["depends_on"].append("map-7")
        actions = self.actions(self.plan())
        self.assertIn("context_mismatch", actions[1].issue_codes)
        self.assertIn("cross_tree_dependency", actions[4].issue_codes)
        self.assertEqual(actions[7].kind, "skip")

    def test_inconsistent_parent_dependencies_are_blocked_and_cycles_rejected(self) -> None:
        for case in ("parent", "dependency", "unknown"):
            with self.subTest(case=case):
                records = copy.deepcopy(self.records)
                if case == "parent":
                    records[5]["parent_mapping"] = "map-0"
                elif case == "dependency":
                    records[5]["depends_on"] = []
                else:
                    records[5]["depends_on"].append("unknown-mapping")
                action = self.actions(self.plan(records=records))[5]
                self.assertEqual(action.kind, "blocked")
                self.assertIn("invalid_dependency", action.issue_codes)
        self.records[0]["depends_on"] = ["map-3"]
        self.error("invalid_dependency", self.plan)

    def test_invalid_source_identity_context_and_duplicate_mappings_fail_safely(self) -> None:
        for case, code in (("identity", "context_mismatch"), ("context", "context_mismatch"), ("duplicate", "duplicate_mapping")):
            with self.subTest(case=case):
                records = copy.deepcopy(self.records)
                if case == "identity":
                    records[5]["source"]["object_id"] = "wrong-source"
                elif case == "context":
                    records[5]["destination_context"]["version"] = "9.9"
                else:
                    records.append(copy.deepcopy(records[5]))
                self.error(code, self.plan, records=records)

    def test_determinism_and_input_preservation(self) -> None:
        self.missing(1, 2, 3)
        before = (self.source.to_artifact().to_json(), self.destination.to_artifact().to_json(), copy.deepcopy(self.records))
        first = self.plan()
        second = self.plan(records=list(reversed(self.records)))
        self.assertEqual(first.to_json(), second.to_json())
        self.assertEqual(first.summary(), second.summary())
        self.assertEqual(
            before, (self.source.to_artifact().to_json(), self.destination.to_artifact().to_json(), self.records),
        )

    def test_plan_identity_binds_destination_configuration_and_policy_assertions(self) -> None:
        first = self.plan()
        self.destination.objects[5].configuration["opaqueDevice"]["preserved"] = ["changed"]
        second = self.plan()
        self.assertNotEqual(first.plan_id, second.plan_id)
        self.assertNotEqual(first.destination_sha256, second.destination_sha256)
        self.assertNotEqual(second.plan_id, self.plan(known=False).plan_id)
        self.assertNotEqual(second.plan_id, self.plan(complete=False).plan_id)

    def test_redacted_plans_summaries_and_representations_never_contain_payloads(self) -> None:
        stdout, stderr = io.StringIO(), io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr), patch("logging.Logger._log") as log:
            plan = self.plan()
            text = plan.to_json() + plan.summary() + repr(plan)
        log.assert_not_called()
        self.assertEqual((stdout.getvalue(), stderr.getvalue()), ("", ""))
        for value in ("synthetic-source", "synthetic-destination", "root-source", "site-a", "map-0",
                      "Region", "192.0.2.10", "opaqueSite", "synthetic/device-one/user", "access-provenance-only"):
            self.assertNotIn(value, text)
        self.assertIn("SKIP=6", plan.summary())
        self.assertIn("no execution is authorized", plan.summary())

    def test_strict_existing_target_resolver_is_not_weakened(self) -> None:
        self.missing(5)
        self.assertEqual(self.actions(self.plan())[5].kind, "create")
        self.error("mapping_missing", self.m.resolve_controller_mappings, self.source, self.destination, self.records)

    def test_plan_integrity_and_recomputation_bind_retained_inputs(self) -> None:
        plan = self.plan()
        keywords = {
            "complete_trees": (self.o.TreeName.PHYSICAL,),
            "semantics_known_for": tuple(item.reference for item in self.source.objects),
            "comparison_rules": self.provenance_rules,
            "device_access_acknowledgements": device_access_acknowledgements(self.source, self.destination),
        }
        verified = self.c.verify_controller_plan(plan.to_dict(), self.source, self.destination, self.records, **keywords)
        self.assertEqual(verified, plan)
        changed = replace(plan, actions=plan.actions[:-1])
        self.error("integrity_mismatch", changed.to_json)
        payload = plan.to_dict()
        payload["schema_version"] = True
        self.error("integrity_mismatch", self.c.verify_controller_plan, payload, self.source, self.destination, self.records, **keywords)
        payload["schema_version"] = {"synthetic-sensitive-marker"}
        error = self.error(
            "integrity_mismatch", self.c.verify_controller_plan,
            payload, self.source, self.destination, self.records, **keywords,
        )
        self.assertNotIn("synthetic-sensitive-marker", "".join(traceback.format_exception(error)))
        self.assertIsNone(error.__context__)
        self.destination.objects[5].configuration["opaqueDevice"] = {}
        self.error("integrity_mismatch", self.c.verify_controller_plan, plan.to_dict(), self.source, self.destination, self.records, **keywords)

    def test_invalid_coverage_and_semantics_declarations_are_rejected(self) -> None:
        for coverage in ((self.o.TreeName.ORGANIZATION,), ("Physical",), (self.o.TreeName.PHYSICAL,) * 2):
            self.error(
                "invalid_coverage", self.p.validate_controller_planning,
                self.source, self.destination, self.records, complete_trees=coverage,
            )
        reference = self.source.objects[0].reference
        for acknowledgement in (
            (reference, reference), (replace(reference, controller_id="foreign"),),
            (replace(reference, object_id=[]),), ("not-a-reference",),
        ):
            self.error(
                "invalid_semantics", self.c.compare_controller_inventories,
                self.source, self.destination, self.records, semantics_known_for=acknowledgement,
            )

    def test_malformed_mapping_error_chains_and_raw_credentials_are_sanitized(self) -> None:
        records = copy.deepcopy(self.records)
        records[0]["state"] = "synthetic-sensitive-marker"
        error = self.error("invalid_mapping", self.plan, records=records)
        self.assertNotIn("synthetic-sensitive-marker", "".join(traceback.format_exception(error)))
        self.assertIsNone(error.__context__)
        self.source.objects[5].configuration["password"] = "synthetic-sensitive-marker"
        error = self.error("secret_value_not_allowed", self.plan)
        self.assertNotIn("synthetic-sensitive-marker", "".join(traceback.format_exception(error)))

    def test_native_identity_fields_are_not_implicitly_excluded(self) -> None:
        plan = self.c.compare_controller_inventories(
            self.source, self.destination, self.records,
            semantics_known_for=tuple(item.reference for item in self.source.objects),
        )
        self.assertEqual(self.actions(plan)[0].kind, "conflict")

    def test_unknown_dictionary_field_order_is_preserved_and_bound(self) -> None:
        self.source.objects[5].configuration["opaqueDevice"] = {"first": 1, "second": 2}
        self.destination.objects[5].configuration["opaqueDevice"] = {"first": 1, "second": 2}
        original = self.plan()
        self.destination.objects[5].configuration["opaqueDevice"] = {"second": 2, "first": 1}
        reordered = self.plan()
        self.assertEqual(self.actions(reordered)[5].kind, "conflict")
        self.assertNotEqual(original.destination_sha256, reordered.destination_sha256)
        self.assertNotEqual(original.plan_id, reordered.plan_id)

    def test_equal_credential_references_are_not_assumed_equivalent(self) -> None:
        for inventory in (self.source, self.destination):
            inventory.objects[5].configuration["password"] = {"secret_ref": "synthetic/unresolved"}
        action = self.actions(self.plan())[5]
        self.assertEqual(action.kind, "blocked")
        self.assertEqual(action.comparison, "unknown")
        self.assertIn("unresolved_credentials", action.issue_codes)

    def test_equal_null_credentials_and_masked_unknown_fields_are_blocked(self) -> None:
        for value in (None, "********", "<redacted>", "[MASKED]"):
            with self.subTest(value=value):
                for inventory in (self.source, self.destination):
                    inventory.objects[5].configuration["opaqueDevice"] = (
                        {"password": None} if value is None else {"unverifiedValue": value}
                    )
                action = self.actions(self.plan())[5]
                self.assertEqual(action.kind, "blocked")
                self.assertIn("unresolved_credentials", action.issue_codes)

    def test_unresolved_credentials_prevent_create_and_do_not_disappear(self) -> None:
        self.source.objects[5].configuration["password"] = {"secret_ref": "synthetic/unresolved"}
        before = self.source.to_artifact().to_json()
        self.missing(5)
        action = self.actions(self.plan())[5]
        self.assertEqual(action.kind, "blocked")
        self.assertIn("unresolved_credentials", action.issue_codes)
        self.assertEqual(self.source.to_artifact().to_json(), before)

    def test_comparison_policy_and_evidence_are_visible_in_the_redacted_plan(self) -> None:
        plan = self.plan()
        data = plan.to_dict()
        self.assertIn("comparison_policy", data)
        policy = data["comparison_policy"]
        self.assertEqual(policy["field_order"], "preserved")
        self.assertEqual(policy["credential_values"], "block-unresolved-or-masked")
        self.assertEqual(policy["authorization"], "offline-comparison-only")
        self.assertTrue(policy["evidence"])
        self.assertTrue(all(action["semantics_acknowledged"] for action in data["actions"]))
        self.assertIn(policy["policy_id"], plan.summary())

    def test_only_the_explicit_validated_identity_rule_excludes_fields(self) -> None:
        selected = self.plan()
        default = self.plan(rules=())
        self.assertEqual(self.actions(selected)[0].kind, "skip")
        self.assertEqual(self.actions(default)[0].kind, "conflict")
        self.assertEqual(default.to_dict()["comparison_policy"]["ignored_fields"], [])
        policy = selected.to_dict()["comparison_policy"]
        self.assertEqual(len(policy["ignored_fields"]), 3)
        self.assertEqual(policy["rules"], ["validated-native-identity-provenance-v1"])
        self.assertTrue(all(value.startswith("offline-contract:") for value in policy["rule_evidence"]))
        self.assertNotEqual(selected.plan_id, default.plan_id)
        self.assertNotEqual(selected.declarations_sha256, default.declarations_sha256)

    def test_unknown_server_managed_fields_and_native_extras_are_not_ignored(self) -> None:
        baseline = copy.deepcopy(self.destination.objects[5].configuration)
        for case in ("server-managed", "native-extra", "empty-identifier"):
            with self.subTest(case=case):
                configuration = self.destination.objects[5].configuration
                configuration.clear()
                configuration.update(copy.deepcopy(baseline))
                if case == "server-managed":
                    configuration["serverManagedRevision"] = "different"
                elif case == "native-extra":
                    configuration["meIdentifier"]["unverifiedExtra"] = "different"
                else:
                    del configuration["meIdentifier"]
                self.assertEqual(self.actions(self.plan())[5].kind, "conflict")

    def test_access_identity_provenance_is_not_excluded_by_the_native_identity_rule(self) -> None:
        self.destination.objects[3].device_access.value["ormID"] = "different-access-provenance"
        self.assertEqual(self.actions(self.plan())[3].kind, "conflict")

    def test_destination_only_credentials_and_unknown_access_values_block(self) -> None:
        self.destination.objects[5].configuration["password"] = {"secret_ref": "synthetic/destination-only"}
        self.assertIn("unresolved_credentials", self.actions(self.plan())[5].issue_codes)
        self.combine_trees()
        self.assertIn("unresolved_credentials", self.actions(self.plan())[8].issue_codes)

    def test_unknown_rules_are_rejected_without_leaking_caller_values(self) -> None:
        for rules in (
            ("synthetic-sensitive-marker",), (["synthetic-sensitive-marker"],),
            self.provenance_rules * 2, list(self.provenance_rules),
        ):
            with self.subTest(rules=rules):
                error = self.error("invalid_comparison_rule", self.plan, rules=rules)
                self.assertNotIn("synthetic-sensitive-marker", "".join(traceback.format_exception(error)))
                self.assertIsNone(error.__context__)

    def test_policy_tampering_and_changed_order_fail_recomputation(self) -> None:
        self.destination.objects[5].configuration["ordered"] = {"first": 1, "second": 2}
        plan = self.plan()
        keywords = {
            "complete_trees": (self.o.TreeName.PHYSICAL,),
            "semantics_known_for": tuple(item.reference for item in self.source.objects),
            "comparison_rules": self.provenance_rules,
        }
        payload = plan.to_dict()
        payload["comparison_policy"]["field_order"] = "ignored"
        self.error(
            "integrity_mismatch", self.c.verify_controller_plan,
            payload, self.source, self.destination, self.records, **keywords,
        )
        self.destination.objects[5].configuration["ordered"] = {"second": 2, "first": 1}
        self.error(
            "integrity_mismatch", self.c.verify_controller_plan,
            plan.to_dict(), self.source, self.destination, self.records, **keywords,
        )

    def test_credential_blocking_is_redacted_and_cannot_be_overridden_by_acknowledgement(self) -> None:
        reference = "synthetic/credential-marker-do-not-report"
        self.source.objects[5].configuration["password"] = {"secret_ref": reference}
        plan = self.plan()
        self.assertTrue(self.actions(plan)[5].semantics_acknowledged)
        self.assertEqual(self.actions(plan)[5].kind, "blocked")
        self.assertNotIn(reference, plan.to_json() + plan.summary() + repr(plan))

    def test_original_fixture_credential_references_are_preserved_but_block_comparison(self) -> None:
        fixture = Path(__file__).parent / "fixtures" / "controller-physical.json"
        self.source = self.normalize(json.loads(fixture.read_text(encoding="utf-8")), self.o.TreeName.PHYSICAL)
        self.initialize_destination()
        before = self.source.to_artifact().to_json()
        plan = self.plan()
        self.assertIn("unresolved_credentials", self.actions(plan)[3].issue_codes)
        self.assertEqual(before, self.source.to_artifact().to_json())
        self.assertIn("synthetic/device-one/password", before)
        self.assertNotIn("synthetic/device-one/password", plan.to_json() + plan.summary() + repr(plan))

    def test_raw_masked_credential_fields_remain_invalid_and_errors_are_sanitized(self) -> None:
        self.source.objects[5].configuration["password"] = "********"
        error = self.error("secret_value_not_allowed", self.plan)
        self.assertNotIn("********", "".join(traceback.format_exception(error)))

    def test_order_preserving_artifact_roundtrip_keeps_comparison_and_snapshot_binding(self) -> None:
        self.source.objects[5].configuration["opaqueDevice"] = {"second": 2, "first": 1}
        self.destination.objects[5].configuration["opaqueDevice"] = {"first": 1, "second": 2}
        original = self.plan()
        self.source = self.o.parse_controller_artifact(json.loads(json.dumps(self.source.to_artifact().to_dict())))
        self.destination = self.o.parse_controller_artifact(json.loads(json.dumps(self.destination.to_artifact().to_dict())))
        self.assertEqual(self.actions(self.plan())[5].kind, "conflict")
        self.assertEqual(original.to_json(), self.plan().to_json())

    def test_standard_serialization_cannot_turn_dictionary_order_conflict_into_skip(self) -> None:
        self.source.objects[5].configuration.update(second=2, first=1)
        self.destination.objects[5].configuration.update(first=1, second=2)
        original = self.plan()
        self.assertEqual(self.actions(original)[5].kind, "conflict")
        self.standard_artifact_roundtrip()
        restored = self.plan()
        self.assertEqual(self.actions(restored)[5].kind, "conflict")
        self.assertEqual(original.to_json(), restored.to_json())
        self.assertEqual(self.verify_candidate(original), restored)

    def test_standard_serialization_preserves_nested_dictionary_order_including_array_members(self) -> None:
        for in_array in (False, True):
            with self.subTest(in_array=in_array):
                source_value = {"second": None, "first": [True, 1]}
                destination_value = {"first": [True, 1], "second": None}
                self.source.objects[5].configuration["opaqueDevice"] = {
                    "futureField": [source_value] if in_array else source_value,
                }
                self.destination.objects[5].configuration["opaqueDevice"] = {
                    "futureField": [destination_value] if in_array else destination_value,
                }
                original = self.plan()
                self.assertEqual(self.actions(original)[5].kind, "conflict")
                self.standard_artifact_roundtrip()
                self.assertEqual(self.actions(self.plan())[5].kind, "conflict")
                self.assertEqual(self.verify_candidate(original).to_json(), original.to_json())

    def test_standard_serialization_preserves_array_types_and_missing_versus_null(self) -> None:
        for source_value, destination_value in (
            ({"values": [1, True, None]}, {"values": [True, 1, None]}),
            ({"value": 1}, {"value": True}),
            ({}, {"value": None}),
        ):
            with self.subTest(source_value=source_value, destination_value=destination_value):
                self.source.objects[5].configuration["opaqueDevice"] = source_value
                self.destination.objects[5].configuration["opaqueDevice"] = destination_value
                original = self.plan()
                self.assertEqual(self.actions(original)[5].kind, "conflict")
                self.standard_artifact_roundtrip()
                self.assertEqual(self.actions(self.plan())[5].kind, "conflict")
                self.assertEqual(self.verify_candidate(original), original)

    def test_identical_settings_skip_after_standard_serialization_with_the_same_plan_identity(self) -> None:
        for inventory in (self.source, self.destination):
            inventory.objects[5].configuration["opaqueDevice"] = {
                "second": None, "first": [True, 1, {"unknownField": "retained"}],
            }
        original = self.plan()
        self.standard_artifact_roundtrip()
        restored = self.plan()
        self.assertTrue(all(action.kind == "skip" for action in restored.actions))
        self.assertEqual(original.to_json(), restored.to_json())
        self.assertEqual(self.verify_candidate(original), restored)
        self.assertEqual(restored.to_json(), self.plan(records=list(reversed(self.records))).to_json())

    def test_external_lossy_reserialization_cannot_verify_against_retained_order(self) -> None:
        self.source.objects[5].configuration["opaqueDevice"] = {"second": 2, "first": 1}
        self.destination.objects[5].configuration["opaqueDevice"] = {"first": 1, "second": 2}
        self.standard_artifact_roundtrip()
        retained_source, retained_destination = self.source, self.destination
        original = self.plan()
        for attribute in ("source", "destination"):
            payload = getattr(self, attribute).to_artifact().to_dict()
            encoded = json.dumps(payload, sort_keys=True)
            setattr(self, attribute, self.o.parse_controller_artifact(json.loads(encoded)))
        self.error("integrity_mismatch", self.verify_candidate, original)
        untrusted_candidate = self.plan()
        self.source, self.destination = retained_source, retained_destination
        self.error("integrity_mismatch", self.verify_candidate, untrusted_candidate)

    def test_generic_serialization_context_cannot_bypass_controller_artifact_validation(self) -> None:
        artifact = replace(self.source.to_artifact(), domain="synthetic-generic")
        self.error("unsupported_context", self.o.parse_controller_artifact, json.loads(artifact.to_json()))

    def test_credentials_still_block_after_standard_artifact_serialization(self) -> None:
        marker = "synthetic/serialization-sensitive-marker"
        self.source.objects[5].configuration["password"] = {"secret_ref": marker}
        original = self.plan()
        self.standard_artifact_roundtrip()
        restored = self.verify_candidate(original)
        self.assertEqual(self.actions(restored)[5].kind, "blocked")
        self.assertIn("unresolved_credentials", self.actions(restored)[5].issue_codes)
        self.assertNotIn(marker, restored.to_json() + restored.summary() + repr(restored))
