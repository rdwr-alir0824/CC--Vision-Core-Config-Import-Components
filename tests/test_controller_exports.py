import copy
import importlib
import json
import traceback
from dataclasses import asdict, replace
from pathlib import Path
from unittest.mock import Mock, patch

from offline_support import OfflineTestCase


class ControllerExportTests(OfflineTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.e = importlib.import_module("cc_vision_import.controller_exports")
        self.o = importlib.import_module("cc_vision_import.controller_objects")
        self.c = importlib.import_module("cc_vision_import.controller_comparison")
        self.contracts = importlib.import_module("cc_vision_import.contracts")
        self.caps = importlib.import_module("cc_vision_import.capabilities")
        self.clients = importlib.import_module("cc_vision_import.product_clients")
        self.a = importlib.import_module("cc_vision_import.artifacts")
        fixture = Path(__file__).parent / "fixtures" / "controller-export-responses.json"
        self.fixtures = json.loads(fixture.read_text(encoding="utf-8"))
        self.options = {
            "controller_id": "synthetic-source", "tree": self.o.TreeName.PHYSICAL,
            "version": "0.0-test", "exported_at": "2026-11-18T09:00:00Z",
        }

    def tree(self, name="physical", **options):
        return self.e.adapt_tree_response(self.fixtures[name], **(self.options | options))

    def flat(self, name="flat", **options):
        return self.e.adapt_flat_export(
            self.fixtures[name], root_response=self.fixtures["root"], **(self.options | options),
        )

    def error(self, code, function, *args, **kwargs):
        with self.assertRaises(self.contracts.ContractValidationError) as caught:
            function(*args, **kwargs)
        self.assertEqual(caught.exception.result.issues[0].code, code)
        return caught.exception

    def roundtrip(self, result):
        return self.o.parse_controller_artifact(json.loads(result.artifact.to_json()))

    def mapped_destination(self, source, destination):
        source_indices = {item.reference: index for index, item in enumerate(source.objects)}
        targets = {item.reference.object_id: item for item in destination.objects}
        records = []
        for index, item in enumerate(source.objects):
            parent = None if isinstance(item, self.o.ControllerRoot) else f"map-{source_indices[item.parent]}"
            records.append({
                "mapping_id": f"map-{index}", "domain": "controller-objects", "source_index": index,
                "source": asdict(item.reference.as_identity()), "source_context": asdict(source.source),
                "destination_context": asdict(destination.source), "state": "resolved",
                "destination": asdict(targets[item.reference.object_id].reference.as_identity()),
                "candidates": [], "parent_mapping": parent,
                "depends_on": [] if parent is None else [parent],
            })
        return records

    def plan(self, source, destination, mappings):
        return self.c.compare_controller_inventories(
            source, destination, mappings,
            complete_trees=(source.objects[0].reference.tree,),
            semantics_known_for=tuple(item.reference for item in source.objects),
        )

    def test_recursive_adapters_preserve_hierarchy_objects_and_separate_trees(self) -> None:
        before = copy.deepcopy(self.fixtures)
        physical = self.tree()
        organization = self.tree("organization", tree=self.o.TreeName.ORGANIZATION)
        source = physical.to_inventory()
        self.assertEqual(len(source.objects), 5)
        self.assertEqual(source.objects[3].parent, source.objects[2].reference)
        self.assertEqual(source.objects[4].parent, source.objects[2].reference)
        self.assertEqual(source.objects[3].device_type, "synthetic-device-type")
        self.assertNotEqual(source.objects[0].reference, organization.to_inventory().objects[0].reference)
        self.assertEqual(physical.completeness, "unverified")
        self.assertEqual(physical.validation.status, "valid")
        self.assertEqual(self.fixtures, before)

    def test_flat_adapter_preserves_ids_parent_provenance_unknown_fields_and_order(self) -> None:
        before = copy.deepcopy(self.fixtures)
        result = self.flat()
        inventory = self.roundtrip(result)
        self.assertEqual(len(inventory.objects), 5)
        self.assertEqual(inventory.objects[3].parent, inventory.objects[2].reference)
        self.assertEqual(inventory.objects[1].configuration["id"], "site-one")
        self.assertEqual(inventory.objects[1].configuration["parent_site_name"], "Synthetic root")
        self.assertEqual(list(inventory.objects[1].configuration["futureSite"]), ["second", "first"])
        self.assertEqual(inventory.objects[4].configuration["futureDevice"], [None, True, 1])
        self.assertEqual(self.fixtures, before)

    def test_flat_hierarchy_does_not_depend_on_site_record_order_or_parent_names(self) -> None:
        self.fixtures["flat"]["sites"].reverse()
        self.fixtures["flat"]["sites"][0]["parent_site_name"] = "Deliberately wrong name"
        inventory = self.flat().to_inventory()
        nested, region = inventory.objects[1:3]
        self.assertEqual(nested.parent, region.reference)
        self.assertEqual(nested.configuration["parent_site_name"], "Deliberately wrong name")

    def test_standard_serialization_preserves_nested_and_access_order_and_types(self) -> None:
        inventory = self.roundtrip(self.tree())
        device = inventory.objects[3]
        self.assertEqual(list(device.configuration["unknownDevice"]), ["second", "first"])
        self.assertEqual(list(device.configuration["unknownDevice"]["second"][0]), ["second", "first"])
        self.assertEqual(list(device.device_access.value["futureAccess"]), ["second", "first"])
        self.assertEqual(device.device_access.value["ormID"], "retained-access-provenance")
        self.assertIsNone(device.device_access.value["futureAccess"]["first"])
        self.assertIs(type(inventory.objects[0].configuration["unknownRoot"]["first"][0]), bool)
        self.assertIs(type(inventory.objects[0].configuration["unknownRoot"]["first"][1]), int)

    def test_complete_adapter_to_candidate_workflow_for_both_representations_and_trees(self) -> None:
        for adapter in (self.tree, self.flat):
            for tree in self.o.TreeName:
                with self.subTest(adapter=adapter.__name__, tree=tree):
                    source_result = adapter(tree=tree)
                    destination_result = adapter(tree=tree, controller_id="synthetic-destination")
                    source, destination = self.roundtrip(source_result), self.roundtrip(destination_result)
                    mappings = self.mapped_destination(source, destination)
                    plan = self.plan(source, destination, mappings)
                    self.assertTrue(all(action.kind == "skip" for action in plan.actions))
                    verified = self.c.verify_controller_plan(
                        json.loads(plan.to_json()), source, destination, mappings,
                        complete_trees=(tree,),
                        semantics_known_for=tuple(item.reference for item in source.objects),
                    )
                    self.assertEqual(verified, plan)
                    self.assertEqual(plan.to_json(), self.plan(source, destination, list(reversed(mappings))).to_json())

    def test_order_differences_stay_conflicts_after_full_adapter_workflow(self) -> None:
        source = self.roundtrip(self.tree())
        destination_data = copy.deepcopy(self.fixtures["physical"])
        destination_data["unknownRoot"] = {"first": [True, 1], "second": None}
        destination = self.roundtrip(self.e.adapt_tree_response(
            destination_data, **(self.options | {"controller_id": "synthetic-destination"}),
        ))
        mappings = self.mapped_destination(source, destination)
        plan = self.plan(source, destination, mappings)
        self.assertEqual(plan.actions[0].kind, "conflict")
        self.assertTrue(all(action.kind == "blocked" for action in plan.actions[1:]))
        self.assertNotEqual(plan.source_sha256, plan.destination_sha256)

    def test_confirmed_missing_nested_objects_feed_existing_create_planning(self) -> None:
        source = self.roundtrip(self.tree())
        destination_data = copy.deepcopy(self.fixtures["physical"])
        destination_data["children"][0]["children"] = []
        destination = self.roundtrip(self.e.adapt_tree_response(
            destination_data, **(self.options | {"controller_id": "synthetic-destination"}),
        ))
        mappings = self.mapped_destination(source, self.roundtrip(self.tree(controller_id="synthetic-destination")))
        for record in mappings[2:]:
            record.update(state="missing", destination=None)
        plan = self.plan(source, destination, mappings)
        self.assertEqual([action.kind for action in plan.actions], ["skip", "skip", "create", "create", "create"])
        self.assertTrue(all(action.destination_index is None for action in plan.actions[2:]))
        self.assertIn("object-2", plan.actions[3].depends_on)

    def test_incomplete_access_artifacts_preserve_data_but_fail_closed_after_roundtrip(self) -> None:
        for value in ("absent", None, {}):
            with self.subTest(value=value):
                data = copy.deepcopy(self.fixtures["incomplete_access"])
                if value != "absent":
                    data["children"][0]["deviceAccess"] = value
                result = self.e.adapt_tree_response(data, **self.options)
                self.assertEqual(result.validation.status, "invalid")
                self.assertEqual(result.validation.issues[0].code, "incomplete_device_access")
                self.assertEqual(result.validation.object_count, 2)
                self.assertEqual(len(result.artifact.objects), 2)
                artifact = self.a.parse_artifact(json.loads(result.artifact.to_json()))
                self.assertEqual(artifact.validation.status, "invalid")
                self.error("invalid_artifact", self.o.parse_controller_artifact, artifact.to_dict())
                self.error("invalid_artifact", result.to_inventory)
                self.assertIn("futureField", json.dumps(artifact.to_dict()))

    def test_flat_missing_access_is_reported_without_empty_object_substitution(self) -> None:
        del self.fixtures["flat"]["devices"][0]["deviceAccess"]
        result = self.flat()
        self.assertEqual(result.validation.status, "invalid")
        record = result.artifact.objects[3]["device_access"]
        self.assertEqual(record, {"location": "absent", "value": None})
        self.error("invalid_artifact", result.to_inventory)

    def test_duplicate_names_preserved_and_flagged_but_explicit_mappings_can_resolve(self) -> None:
        source_result = self.tree("duplicate_siblings")
        destination_result = self.tree("duplicate_siblings", controller_id="synthetic-destination")
        self.assertEqual(source_result.validation.status, "valid")
        self.assertEqual(len(source_result.identity_assessment.issues), 2)
        self.assertEqual({issue.code for issue in source_result.identity_assessment.issues}, {"ambiguous_name"})
        source, destination = self.roundtrip(source_result), self.roundtrip(destination_result)
        self.assertEqual(len(source.objects), 3)
        records = self.mapped_destination(source, destination)
        plan = self.plan(source, destination, records)
        self.assertTrue(all(action.kind == "skip" for action in plan.actions))
        records[1].update(state="unresolved", destination=None)
        self.assertEqual(self.plan(source, destination, records).actions[1].kind, "blocked")

    def test_missing_and_invalid_parents_never_fall_back_to_root(self) -> None:
        self.error("missing_parent", self.flat, "missing_parent")
        self.fixtures["flat"]["sites"][0]["parentOrmID"] = "device-one"
        self.error("invalid_parent", self.flat)

    def test_flat_missing_context_unknown_envelope_and_nonempty_root_fail(self) -> None:
        self.fixtures["flat"]["extraEnvelope"] = {"preserveOrReject": True}
        self.error("unknown_fields", self.flat)
        del self.fixtures["flat"]["extraEnvelope"]
        self.fixtures["root"] = self.fixtures["physical"]
        self.error("invalid_root_context", self.flat)

    def test_duplicate_native_id_and_flat_cycles_are_rejected(self) -> None:
        self.fixtures["flat"]["devices"][1]["id"] = "device-one"
        self.error("duplicate_identity", self.flat)
        self.fixtures["flat"]["devices"][1]["id"] = "device-two"
        self.fixtures["flat"]["sites"][0]["parentOrmID"] = "site-two"
        self.error("invalid_dependency", self.flat)

    def test_malformed_missing_fields_and_unknown_classes_reject_without_discard(self) -> None:
        self.error("invalid_hierarchy", self.tree, "malformed")
        self.error("invalid_type", self.e.adapt_tree_response, [], **self.options)
        for change, code in (("name", "missing_field"), ("class", "unsupported_object_kind"), ("parent", "conflicting_reference")):
            data = copy.deepcopy(self.fixtures["physical"])
            node = data["children"][0]
            if change == "name":
                del node["name"]
            elif change == "class":
                node["meIdentifier"]["managedElementClass"] = "synthetic-unsupported"
            else:
                node["parentOrmID"] = "unresolved-parent"
            self.error(code, self.e.adapt_tree_response, data, **self.options)

    def test_unsafe_credentials_rejected_in_both_representations_without_error_leakage(self) -> None:
        marker = "synthetic-sensitive-value-must-not-leak"
        for adapter, access in (
            (self.tree, self.fixtures["physical"]["children"][0]["children"][0]["children"][0]["deviceSetup"]["deviceAccess"]),
            (self.flat, self.fixtures["flat"]["devices"][0]["deviceAccess"]),
        ):
            for key in ("cliUsername", "cliPassword", "authorization", "snmpV3PrivacyPassword"):
                with self.subTest(adapter=adapter.__name__, key=key):
                    access[key] = marker
                    error = self.error("secret_value_not_allowed", adapter)
                    self.assertNotIn(marker, "".join(traceback.format_exception(error)))
                    self.assertIsNone(error.__context__)
                    del access[key]

    def test_secret_references_and_null_placeholders_preserved_but_comparison_blocked(self) -> None:
        access = self.fixtures["physical"]["children"][0]["children"][0]["children"][0]["deviceSetup"]["deviceAccess"]
        access.update(cliPassword={"secret_ref": "synthetic/device-one/password"}, cliUsername=None)
        with patch("logging.Logger._log") as log:
            source_result = self.tree()
            source, destination = self.roundtrip(source_result), self.roundtrip(self.tree(controller_id="synthetic-destination"))
            plan = self.plan(source, destination, self.mapped_destination(source, destination))
        log.assert_not_called()
        action = next(action for action in plan.actions if action.source_index == 3)
        self.assertEqual(action.kind, "blocked")
        text = repr(source_result) + repr(source) + plan.summary() + plan.to_json()
        self.assertNotIn("synthetic/device-one/password", text)
        self.assertIn("synthetic/device-one/password", source_result.artifact.to_json())

    def test_existing_mock_read_results_adapt_without_new_capabilities(self) -> None:
        for operation, fixture, tree in (
            (self.caps.ReadCapability.PHYSICAL_TREE, "physical", self.o.TreeName.PHYSICAL),
            (self.caps.ReadCapability.ORGANIZATION_TREE, "organization", self.o.TreeName.ORGANIZATION),
        ):
            capability = self.caps.require_capability("cyber-controller", "0.0-test", operation, mock_only=True)
            result = self.clients.ReadResult(capability, (self.fixtures[fixture],))
            adapted = self.e.adapt_controller_read(
                result, controller_id="synthetic-source", exported_at=self.options["exported_at"],
            )
            self.assertEqual(adapted.to_inventory().objects[0].reference.tree, tree)
            self.error("invalid_read_result", self.e.adapt_controller_read,
                       replace(result, objects=()), controller_id="synthetic-source", exported_at=self.options["exported_at"])
        self.assertEqual(self.caps.VERIFIED_CAPABILITIES, ())

    def test_unsupported_versions_vision_and_forged_mock_declarations_rejected(self) -> None:
        self.error("unsupported_version", self.tree, version="10.0")
        capability = self.caps.require_capability(
            "vision", "0.0-test", self.caps.ReadCapability.LDAP_PERMISSIONS, mock_only=True,
        )
        self.error("unsupported_context", self.e.adapt_controller_read,
                   self.clients.ReadResult(capability, ()), controller_id="synthetic-source", exported_at=self.options["exported_at"])
        capability = self.caps.require_capability(
            "cyber-controller", "0.0-test", self.caps.ReadCapability.PHYSICAL_TREE, mock_only=True,
        )
        self.error("invalid_read_result", self.e.adapt_controller_read,
                   self.clients.ReadResult(replace(capability, live_tested=True), (self.fixtures["physical"],)),
                   controller_id="synthetic-source", exported_at=self.options["exported_at"])

    def test_injected_mock_client_sessions_feed_adapter_and_plan_with_cleanup(self) -> None:
        from test_authentication import FakeOwnedBackend

        authentication = importlib.import_module("cc_vision_import.authentication")
        sessions = importlib.import_module("cc_vision_import.sessions")
        transport = importlib.import_module("cc_vision_import.transport")

        class Backend(FakeOwnedBackend, sessions.MockSessionBackend):
            pass

        backends = [
            Backend(
                transport.HttpResponse(200, b"{}"),
                transport.HttpResponse(200, json.dumps(self.fixtures["physical"]).encode("utf-8")),
            )
            for _ in range(2)
        ]
        factory = Mock(side_effect=backends)
        resolver = Mock()
        resolver.resolve.side_effect = lambda reference: authentication.ResolvedCredentials(
            reference.value + "-user", reference.value + "-password",
        )
        inventories = []
        with sessions.SessionManager(factory, resolver, mock_only=True) as manager:
            for role in authentication.SessionRole:
                manager.initialize(
                    authentication.AuthenticationRequest(
                        role, "cyber-controller", "0.0-test",
                        authentication.CredentialReference("synthetic/" + role.value),
                    ),
                    transport.TransportConfig(
                        base_url="https://" + role.value + ".invalid",
                        connect_timeout=2, read_timeout=4,
                    ),
                )
                manager.authenticate(role)
                read = self.clients.CyberControllerClient(manager, role, "0.0-test").export_physical_tree()
                adapted = self.e.adapt_controller_read(
                    read, controller_id="synthetic-" + role.value,
                    exported_at=self.options["exported_at"],
                )
                inventories.append(self.roundtrip(adapted))
        source, destination = inventories
        plan = self.plan(source, destination, self.mapped_destination(source, destination))
        self.assertTrue(all(action.kind == "skip" for action in plan.actions))
        self.assertEqual([backend.close_calls for backend in backends], [1, 1])
        self.assertTrue(all(len(backend.requests) == 2 for backend in backends))
        self.assertEqual([backend.requests[-1].method for backend in backends], [transport.HttpMethod.GET] * 2)

    def test_client_adapter_failure_keeps_session_cleanup_exception_safe(self) -> None:
        authentication = importlib.import_module("cc_vision_import.authentication")
        sessions = importlib.import_module("cc_vision_import.sessions")
        transport = importlib.import_module("cc_vision_import.transport")
        from test_authentication import FakeOwnedBackend

        class Backend(FakeOwnedBackend, sessions.MockSessionBackend):
            pass

        data = copy.deepcopy(self.fixtures["physical"])
        del data["children"][0]["name"]
        backend = Backend(
            transport.HttpResponse(200, b"{}"),
            transport.HttpResponse(200, json.dumps(data).encode("utf-8")),
        )
        resolver = Mock()
        resolver.resolve.return_value = authentication.ResolvedCredentials("synthetic-user", "synthetic-password")
        with self.assertRaises(self.contracts.ContractValidationError):
            with sessions.SessionManager(lambda: backend, resolver, mock_only=True) as manager:
                manager.initialize(
                    authentication.AuthenticationRequest(
                        authentication.SessionRole.SOURCE, "cyber-controller", "0.0-test",
                        authentication.CredentialReference("synthetic/source"),
                    ),
                    transport.TransportConfig(base_url="https://source.invalid", connect_timeout=2, read_timeout=4),
                )
                manager.authenticate(authentication.SessionRole.SOURCE)
                read = self.clients.CyberControllerClient(
                    manager, authentication.SessionRole.SOURCE, "0.0-test",
                ).export_physical_tree()
                self.e.adapt_controller_read(
                    read, controller_id="synthetic-source", exported_at=self.options["exported_at"],
                )
        self.assertEqual(backend.close_calls, 1)

    def test_access_array_and_absent_null_differences_remain_significant_in_plans(self) -> None:
        self.fixtures["physical"]["children"][0]["children"][0]["children"][1]["deviceAccess"] = {
            "futureAccess": {"sequence": [1, None], "nullable": None},
        }
        source = self.roundtrip(self.tree())
        for value in (
            {"futureAccess": {"sequence": [None, 1], "nullable": None}},
            {"futureAccess": {"sequence": [True, None], "nullable": None}},
            {"futureAccess": {"sequence": [1, None]}},
        ):
            with self.subTest(value=value):
                data = copy.deepcopy(self.fixtures["physical"])
                data["children"][0]["children"][0]["children"][1]["deviceAccess"] = value
                destination = self.roundtrip(self.e.adapt_tree_response(
                    data, **(self.options | {"controller_id": "synthetic-destination"}),
                ))
                plan = self.plan(source, destination, self.mapped_destination(source, destination))
                action = next(action for action in plan.actions if action.source_index == 4)
                self.assertEqual(action.kind, "conflict")
                self.assertNotIn("unresolved_credentials", action.issue_codes)

    def test_conflicting_access_locations_and_non_json_configuration_fail(self) -> None:
        data = copy.deepcopy(self.fixtures["physical"])
        data["children"][0]["children"][0]["children"][0]["deviceAccess"] = {"connectionTimeout": 2}
        self.error("conflicting_reference", self.e.adapt_tree_response, data, **self.options)
        data = copy.deepcopy(self.fixtures["physical"])
        data["unrecognized"] = {1, 2}
        self.error("invalid_type", self.e.adapt_tree_response, data, **self.options)

    def test_flat_required_fields_are_not_filled_with_guessed_defaults(self) -> None:
        original = copy.deepcopy(self.fixtures["flat"])
        for field in ("parentOrmID", "id", "name", "type", "managementIp"):
            with self.subTest(field=field):
                self.fixtures["flat"] = copy.deepcopy(original)
                del self.fixtures["flat"]["devices"][0][field]
                self.error("missing_field", self.flat)

    def test_malformed_read_result_contract_is_rejected_with_fixed_errors(self) -> None:
        self.error("invalid_type", self.e.adapt_controller_read, None,
                   controller_id="synthetic-source", exported_at=self.options["exported_at"])
        self.error("invalid_read_result", self.e.adapt_controller_read,
                   self.clients.ReadResult(None, ()), controller_id="synthetic-source",
                   exported_at=self.options["exported_at"])
