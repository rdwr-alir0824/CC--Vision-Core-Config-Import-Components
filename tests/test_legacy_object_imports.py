import copy
import json
import traceback
import warnings
from unittest.mock import Mock, patch

from offline_support import OfflineTestCase
from test_http_backend import MemoryConnection, MemoryResponse
from test_legacy_object_exports import TREE, SECRET, access, device, site

from cc_vision_import.client import ApiClient, ClientError
from cc_vision_import.config import ControllerConfig
from cc_vision_import.files import load_json, save_json
from cc_vision_import.objects import ImportError, export_objects, import_objects


class LegacyObjectImportTests(OfflineTestCase):
    def setUp(self):
        super().setUp()
        self.config = ControllerConfig(
            address="destination.example.invalid", username="synthetic-user",
            password="synthetic-controller-secret", product="cyber-controller",
        )
        self.input_path = self.directory / "portable-synthetic.json"
        self.data = {
            "source_root": {"id": "src-root-41", "name": "Export Canopy"},
            "sites": [
                {"id": "src-site-43", "name": "Lower Branch", "parentOrmID": "src-site-42",
                 "parent_site_name": "Upper Branch"},
                {"id": "src-site-42", "name": "Upper Branch", "parentOrmID": "src-root-41",
                 "parent_site_name": "Export Canopy"},
            ],
            "devices": [
                {"id": "src-device-44", "name": "Canopy Device", "type": "synthetic-runtime-model",
                 "managementIp": "192.0.2.121", "parentOrmID": "src-root-41",
                 "deviceAccess": access()["deviceSetup"]["deviceAccess"]},
                {"id": "src-device-45", "name": "Lower Device", "type": "synthetic-runtime-model",
                 "managementIp": "192.0.2.122", "parentOrmID": "src-site-43",
                 "deviceAccess": access()["deviceSetup"]["deviceAccess"]},
            ],
        }
        self.destination = site("dst-root-91", "Import Canopy")
        self.client = Mock(spec=ApiClient)
        self.client.__enter__ = Mock(return_value=self.client)
        self.client.__exit__ = Mock(return_value=False)
        self.client.get.side_effect = self.read
        self.client.post.side_effect = self.create
        self.next_id = 100
        self.get_responses = []

    def read(self, path):
        self.assertIn(path, ((*TREE, "Physical"), (*TREE, "Organization")))
        if self.get_responses:
            value = self.get_responses.pop(0)
            if isinstance(value, Exception):
                raise value
            return copy.deepcopy(value)
        return copy.deepcopy(self.destination)

    def find(self, identity):
        def walk(node):
            if node["meIdentifier"]["managedElementID"] == identity:
                return node
            for child in node.get("children", []):
                found = walk(child)
                if found is not None:
                    return found
            return None
        return walk(self.destination)

    def create(self, path, payload, *, expect_json):
        self.assertFalse(expect_json)
        self.next_id += 1
        identity = f"dst-created-{self.next_id}"
        if path == (*TREE, "site"):
            node = site(identity, payload["name"])
        else:
            self.assertEqual(path, (*TREE, "device"))
            row = next(row for row in self.data["devices"] if row["name"] == payload["name"])
            node = device(identity, payload["name"], row["managementIp"])
            node["type"] = payload["type"]
        parent = self.find(payload["parentOrmID"])
        self.assertIsNotNone(parent)
        parent.setdefault("children", []).append(node)
        return None

    def run_import(self, tree="Physical", *, write=True, **kwargs):
        if write:
            save_json(self.input_path, self.data)
        with patch("cc_vision_import.objects.ApiClient", return_value=self.client) as constructor:
            result = import_objects(self.config, self.input_path, tree, **kwargs)
        constructor.assert_called_once()
        self.client.__enter__.assert_called_once()
        self.client.__exit__.assert_called_once()
        return result

    def assert_invalid(self, code=None, *, write=True, **kwargs):
        if write:
            save_json(self.input_path, self.data)
        with patch("cc_vision_import.objects.ApiClient") as constructor:
            with self.assertRaises(ImportError) as caught:
                import_objects(self.config, self.input_path, "Physical", **kwargs)
        constructor.assert_not_called()
        self.client.post.assert_not_called()
        if code:
            self.assertEqual(caught.exception.code, code)
        self.assertNotIn(SECRET, "".join(traceback.format_exception(caught.exception)))

    def test_unordered_nested_sites_and_direct_root_devices_minimal_payloads(self):
        result = self.run_import()
        self.assertEqual(result.status, "SUCCESS")
        self.assertEqual([item.source_id for item in result.objects],
                         ["src-site-42", "src-site-43", "src-device-44", "src-device-45"])
        calls = self.client.post.call_args_list
        self.assertEqual(calls[0].args, ((*TREE, "site"), {
            "name": "Upper Branch", "parentOrmID": "dst-root-91"}))
        self.assertEqual(calls[1].args, ((*TREE, "site"), {
            "name": "Lower Branch", "parentOrmID": "dst-created-101"}))
        expected = copy.deepcopy(self.data["devices"][0]["deviceAccess"])
        expected.pop("ormID")
        self.assertEqual(calls[2].args, ((*TREE, "device"), {
            "name": "Canopy Device", "parentOrmID": "dst-root-91",
            "type": "synthetic-runtime-model", "deviceSetup": {"deviceAccess": expected}}))
        self.assertEqual(calls[3].args[1]["parentOrmID"], "dst-created-102")
        self.assertEqual(result.counts, {
            "Site": {"SUCCESS": 2, "SKIPPED": 0, "FAILED": 0},
            "Device": {"SUCCESS": 2, "SKIPPED": 0, "FAILED": 0},
        })
        self.assertNotIn("src-", json.dumps([call.args[1] for call in calls]))

    def test_organization_import_runtime_tree_root_and_model(self):
        self.destination = site("dst-root-777", "Another Destination Canopy")
        self.data["devices"][0]["type"] = "another-runtime-model"
        result = self.run_import("Organization")
        self.assertEqual(result.status, "SUCCESS")
        self.assertTrue(all(call.args[0] == (*TREE, "Organization")
                            for call in self.client.get.call_args_list))
        self.assertEqual(self.client.post.call_args_list[0].args[1]["parentOrmID"], "dst-root-777")
        self.assertEqual(self.client.post.call_args_list[2].args[1]["type"], "another-runtime-model")

    def test_fresh_export_consumed_directly_without_source_connection(self):
        source = Mock(spec=ApiClient)
        source.__enter__ = Mock(return_value=source)
        source.__exit__ = Mock(return_value=False)
        source.get.side_effect = lambda path: (
            site("src-new-root-301", "Fresh Canopy",
                 site("src-new-site-302", "Fresh Branch",
                      device("src-new-device-303", "Fresh Device", "198.51.100.44")))
            if path[-1] == "Physical" else access()
        )
        with patch("cc_vision_import.objects.ApiClient", return_value=source):
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                exported = export_objects(self.config, {"Physical": self.input_path})
        self.assertEqual(exported["Physical"].status, "SUCCESS")
        self.data = load_json(self.input_path)
        self.assertEqual(self.run_import(write=False).status, "SUCCESS")
        self.assertTrue(all("byip" not in call.args[0] for call in self.client.get.call_args_list))

    def test_credentials_and_opaque_fields_preserved_without_mutating_input(self):
        before = copy.deepcopy(self.data)
        self.run_import()
        for call in self.client.post.call_args_list[2:]:
            expected = copy.deepcopy(before["devices"][0]["deviceAccess"])
            expected.pop("ormID")
            self.assertEqual(call.args[1]["deviceSetup"]["deviceAccess"], expected)
        self.assertEqual(self.data, before)
        self.assertEqual(load_json(self.input_path), before)

    def test_existing_correct_sites_devices_skip_and_use_destination_ids(self):
        self.destination["children"] = [
            site("dst-existing-upper-201", "Upper Branch",
                 site("dst-existing-lower-202", "Lower Branch",
                      device("dst-existing-device-203", "Lower Device", "192.0.2.122"))),
            device("dst-existing-device-204", "Canopy Device", "192.0.2.121"),
        ]
        result = self.run_import()
        self.client.post.assert_not_called()
        self.assertEqual(result.counts["Site"]["SKIPPED"], 2)
        self.assertEqual(result.counts["Device"]["SKIPPED"], 2)
        self.assertEqual(result.status, "SUCCESS")

    def test_duplicate_site_names_under_different_parents_are_not_global_matches(self):
        self.data["devices"] = []
        self.data["sites"] = [
            {"id": "src-a", "name": "Branch A", "parentOrmID": "src-root-41",
             "parent_site_name": "Export Canopy"},
            {"id": "src-b", "name": "Branch B", "parentOrmID": "src-root-41",
             "parent_site_name": "Export Canopy"},
            {"id": "src-a-leaf", "name": "Shared Leaf", "parentOrmID": "src-a",
             "parent_site_name": "Branch A"},
            {"id": "src-b-leaf", "name": "Shared Leaf", "parentOrmID": "src-b",
             "parent_site_name": "Branch B"},
        ]
        self.destination["children"] = [
            site("dst-a", "Branch A", site("dst-a-leaf", "Shared Leaf")),
            site("dst-b", "Branch B"),
        ]
        result = self.run_import()
        self.assertEqual(result.status, "SUCCESS")
        self.assertEqual(result.counts["Site"], {"SUCCESS": 1, "SKIPPED": 3, "FAILED": 0})
        self.assertEqual(self.client.post.call_args.args[1],
                         {"name": "Shared Leaf", "parentOrmID": "dst-b"})

    def test_existing_site_wrong_placement_blocks_children_not_root_device(self):
        self.destination["children"] = [
            site("dst-foreign", "Other Branch", site("dst-wrong", "Upper Branch")),
        ]
        result = self.run_import()
        self.assertEqual([item.status for item in result.objects],
                         ["FAILED", "FAILED", "SUCCESS", "FAILED"])
        self.assertEqual(result.objects[0].reason, "existing_site_wrong_placement")
        self.assertEqual(self.client.post.call_count, 1)

    def test_ambiguous_destination_site_does_not_block_unrelated_device(self):
        self.destination["children"] = [
            site("dst-duplicate-a", "Upper Branch"), site("dst-duplicate-b", "Upper Branch"),
        ]
        result = self.run_import()
        self.assertEqual(result.objects[0].reason, "ambiguous_destination_site")
        self.assertEqual(self.client.post.call_count, 1)

    def test_existing_device_wrong_placement(self):
        self.destination["children"] = [
            site("dst-wrong-parent", "Other Branch",
                 device("dst-device", "Canopy Device", "192.0.2.121")),
        ]
        result = self.run_import()
        self.assertEqual(result.objects[2].reason, "existing_device_wrong_placement")
        self.assertEqual(result.counts["Device"], {"SUCCESS": 1, "SKIPPED": 0, "FAILED": 1})

    def test_existing_device_identity_conflicts(self):
        self.data["sites"] = []
        self.data["devices"] = [self.data["devices"][0]]
        for key, value in (("name", "Another Device"), ("type", "another-model"),
                           ("managementIp", "198.51.100.17")):
            with self.subTest(key=key):
                self.client.reset_mock()
                existing = device("dst-conflict", "Canopy Device", "192.0.2.121")
                existing[key] = value
                self.destination["children"] = [existing]
                result = self.run_import()
                self.assertEqual(result.objects[0].reason, "existing_device_identity_conflict")
                self.client.post.assert_not_called()

    def test_ambiguous_destination_device(self):
        self.destination["children"] = [
            device("dst-a", "Canopy Device", "192.0.2.121"),
            device("dst-b", "Different Device", "192.0.2.121"),
        ]
        self.assertEqual(self.run_import().objects[2].reason, "ambiguous_destination_device")

    def test_failed_parent_prevents_dependents_and_unrelated_branch_continues(self):
        self.data["sites"].append({
            "id": "src-independent", "name": "Independent Branch",
            "parentOrmID": "src-root-41", "parent_site_name": "Export Canopy",
        })
        original = self.create
        def fail_one(path, payload, **kwargs):
            if payload["name"] == "Upper Branch":
                raise ClientError("indeterminate_write_outcome", indeterminate=True)
            return original(path, payload, **kwargs)
        self.client.post.side_effect = fail_one
        result = self.run_import()
        statuses = {item.source_id: item.status for item in result.objects}
        self.assertEqual(statuses["src-independent"], "SUCCESS")
        self.assertEqual(statuses["src-site-43"], "FAILED")
        self.assertEqual(statuses["src-device-45"], "FAILED")
        self.assertEqual(statuses["src-device-44"], "SUCCESS")
        self.assertEqual(self.client.post.call_count, 3)

    def test_async_acknowledgement_requires_readback_and_can_complete_later(self):
        before = copy.deepcopy(self.destination)
        self.get_responses = [before, before]
        result = self.run_import()
        self.assertEqual(result.status, "SUCCESS")
        self.assertEqual(self.client.get.call_count, 6)
        self.assertEqual(self.client.post.call_count, 4)

    def test_unresolved_async_completion_is_failed_and_bounded(self):
        self.data["devices"] = []
        self.data["sites"] = [self.data["sites"][1]]
        self.client.post.side_effect = None
        result = self.run_import()
        self.assertEqual(result.objects[0].reason, "destination_outcome_uncertain:creation_unconfirmed")
        self.assertEqual(self.client.post.call_count, 1)
        self.assertEqual(self.client.get.call_count, 4)

    def test_exactly_one_post_after_timeout_or_server_error(self):
        self.data["sites"] = [self.data["sites"][1]]
        self.data["devices"] = []
        for error in (
            ClientError("indeterminate_write_outcome", indeterminate=True),
            ClientError("indeterminate_write_outcome", status=500, indeterminate=True),
        ):
            with self.subTest(status=error.status):
                self.client.reset_mock()
                self.client.post.side_effect = error
                result = self.run_import()
                self.assertEqual(self.client.post.call_count, 1)
                self.assertEqual(self.client.get.call_count, 1)
                self.assertIn("destination_outcome_uncertain", result.objects[0].reason)

    def test_failed_readback_is_uncertain_without_resubmitting(self):
        self.data["sites"] = [self.data["sites"][1]]
        self.data["devices"] = []
        self.get_responses = [self.destination, ClientError("http_error", status=503)]
        result = self.run_import()
        self.assertEqual(self.client.post.call_count, 1)
        self.assertEqual(result.objects[0].status, "FAILED")
        self.assertIn("destination_outcome_uncertain", result.objects[0].reason)

    def test_malformed_readback_and_changed_root_are_not_success(self):
        for response in ([], site("dst-changed-root", "Changed Canopy")):
            with self.subTest(response=response):
                self.client.reset_mock()
                self.destination = site("dst-root-91", "Import Canopy")
                self.get_responses = [self.destination, response]
                result = self.run_import()
                self.assertEqual(result.objects[0].status, "FAILED")
                self.assertIn("destination_outcome_uncertain", result.objects[0].reason)
                if isinstance(response, dict):
                    self.assertEqual(self.client.post.call_count, 1)

    def test_malformed_destination_prevents_writes_and_cleans_session(self):
        self.get_responses = [None]
        result = self.run_import()
        self.assertEqual(result.status, "FAILED")
        self.assertEqual(result.failed_step, "destination_hierarchy")
        self.assertEqual(len(result.objects), 4)
        self.client.post.assert_not_called()

    def test_empty_portable_hierarchy(self):
        self.data["sites"] = []
        self.data["devices"] = []
        result = self.run_import()
        self.assertEqual(result.status, "SUCCESS")
        self.assertEqual(result.objects, ())
        self.client.post.assert_not_called()

    def test_older_file_requires_explicit_source_root(self):
        root = self.data.pop("source_root")
        self.assert_invalid()
        self.assertEqual(self.run_import(source_root=root).status, "SUCCESS")

    def test_conflicting_explicit_source_root(self):
        self.assert_invalid("conflicting_source_root", source_root={"id": "another-root", "name": "Other"})

    def test_missing_source_parent(self):
        self.data["sites"][0]["parentOrmID"] = "missing-parent"
        self.assert_invalid("missing_source_parent")

    def test_missing_device_parent(self):
        self.data["devices"][0]["parentOrmID"] = "missing-parent"
        self.assert_invalid("missing_source_parent")

    def test_conflicting_parent_name(self):
        self.data["sites"][0]["parent_site_name"] = "Wrong Branch"
        self.assert_invalid("conflicting_source_parent_name")

    def test_duplicate_ids_across_sites_devices_and_root(self):
        for identity in ("src-root-41", "src-site-42", "src-device-45"):
            with self.subTest(identity=identity):
                self.data["devices"][0]["id"] = identity
                self.assert_invalid("duplicate_source_identity")

    def test_ambiguous_source_site_placement(self):
        self.data["sites"].append({**self.data["sites"][1], "id": "src-duplicate-name"})
        self.assert_invalid("ambiguous_source_identity")

    def test_ambiguous_source_device_address(self):
        self.data["devices"][1]["managementIp"] = self.data["devices"][0]["managementIp"]
        self.assert_invalid("ambiguous_device_address")

    def test_cyclic_sites(self):
        self.data["sites"][1]["parentOrmID"] = "src-site-43"
        self.data["sites"][1]["parent_site_name"] = "Lower Branch"
        self.assert_invalid("cyclic_site_dependencies")

    def test_required_fields_and_access_object(self):
        before = copy.deepcopy(self.data)
        for section, field in (
            ("source_root", "id"), ("source_root", "name"), ("sites", "name"),
            ("sites", "id"), ("sites", "parentOrmID"), ("sites", "parent_site_name"),
            ("devices", "id"), ("devices", "name"), ("devices", "parentOrmID"), ("devices", "type"),
            ("devices", "managementIp"), ("devices", "deviceAccess"),
        ):
            with self.subTest(section=section, field=field):
                self.data = copy.deepcopy(before)
                row = self.data[section] if section == "source_root" else self.data[section][0]
                del row[field]
                self.assert_invalid()
        self.data = copy.deepcopy(before)
        self.data["devices"][0]["deviceAccess"] = SECRET
        self.assert_invalid()

    def test_no_invented_protocol_credential_requirements(self):
        self.data["devices"][0]["deviceAccess"] = {}
        self.assertEqual(self.run_import().status, "SUCCESS")

    def test_malformed_json_duplicate_keys_and_nonfinite_numbers_before_login(self):
        for text in ('{', '{"sites":[],"sites":[]}', '{"value":NaN}', '{"value":1e999}'):
            with self.subTest(text=text):
                self.input_path.write_text(text, encoding="utf-8")
                self.assert_invalid("invalid_json_file", write=False)

    def test_invalid_export_structures(self):
        for value in (None, [], {}, {"source_root": {"id": "x", "name": "y"},
                                     "sites": {}, "devices": []}):
            with self.subTest(value=value):
                self.data = value
                self.assert_invalid()

    def test_missing_input_file_before_login(self):
        self.assert_invalid("invalid_json_file", write=False)

    def test_invalid_tree_selection_before_login(self):
        with patch("cc_vision_import.objects.ApiClient") as constructor:
            with self.assertRaises(ImportError):
                import_objects(self.config, self.input_path, "Unsupported")
        constructor.assert_not_called()

    def test_secret_free_result_and_failure_traceback(self):
        self.get_responses = [{"message": SECRET, "cookie": "synthetic-session-cookie"}]
        result = self.run_import()
        text = repr(result)
        for secret in (SECRET, self.config.password, "synthetic-session-cookie"):
            self.assertNotIn(secret, text)

    def test_session_cleanup_failure_does_not_hide_confirmed_results(self):
        self.client.__exit__.side_effect = ClientError("local_cleanup_failed")
        result = self.run_import()
        self.assertTrue(result.cleanup_failed)
        self.assertEqual(result.status, "FAILED")
        self.assertEqual(result.counts["Site"]["SUCCESS"], 2)
        self.assertEqual(result.failed_step, "session_cleanup")

    def test_cleanup_note_retained_on_read_failure(self):
        error = ClientError("http_error", status=401)
        error.add_note("Local API session cleanup failed.")
        self.get_responses = [error]
        result = self.run_import()
        self.assertTrue(result.cleanup_failed)
        self.client.post.assert_not_called()

    def test_actual_client_single_login_payload_and_session_cleanup(self):
        self.data["sites"] = []
        self.data["devices"] = [self.data["devices"][0]]
        save_json(self.input_path, self.data)
        after = site("dst-memory-root", "Memory Canopy",
                     device("dst-memory-device", "Canopy Device", "192.0.2.121"))
        responses = [
            MemoryResponse(body=b'{"status":"ok","jsessionid":"synthetic-session-cookie"}'),
            MemoryResponse(body=json.dumps(site("dst-memory-root", "Memory Canopy")).encode()),
            MemoryResponse(status=202, body=b'{"job":"synthetic-ack"}'),
            MemoryResponse(body=json.dumps(after).encode()),
        ]
        connections = []
        def factory(_host, _port, *, timeout, context):
            connection = MemoryConnection(responses.pop(0))
            connections.append(connection)
            return connection
        result = import_objects(self.config, self.input_path, "Physical", connection_factory=factory)
        self.assertEqual(result.status, "SUCCESS")
        self.assertEqual(len(connections), 4)
        self.assertTrue(all(connection.close_calls == 1 for connection in connections))
        self.assertEqual(connections[0].requests[0][1], "/mgmt/system/user/login")
        self.assertEqual(connections[2].requests[0][1], "/mgmt/system/config/tree/device")
        self.assertNotIn("synthetic-session-cookie", repr(result))

    def test_actual_client_rejected_login_cleans_without_object_writes(self):
        save_json(self.input_path, self.data)
        connections = []
        def factory(_host, _port, *, timeout, context):
            connection = MemoryConnection(MemoryResponse(body=b'{"status":"error","message":"secret"}'))
            connections.append(connection)
            return connection
        result = import_objects(self.config, self.input_path, "Physical", connection_factory=factory)
        self.assertEqual(result.status, "FAILED")
        self.assertEqual(len(connections), 1)
        self.assertEqual(connections[0].close_calls, 1)
        self.assertEqual(result.failed_step, "authentication")

    def test_actual_client_timeout_and_server_error_make_one_object_post(self):
        self.data["sites"] = [self.data["sites"][1]]
        self.data["devices"] = []
        save_json(self.input_path, self.data)
        for timeout in (True, False):
            with self.subTest(timeout=timeout):
                connections = []
                responses = [
                    MemoryResponse(body=b'{"status":"ok"}'),
                    MemoryResponse(body=json.dumps(self.destination).encode()),
                    MemoryResponse(status=500, body=SECRET.encode()),
                ]
                def factory(_host, _port, *, timeout, context):
                    connection = MemoryConnection(responses.pop(0))
                    if len(connections) == 2 and fail_with_timeout:
                        connection.failure = ("getresponse", TimeoutError(SECRET))
                    connections.append(connection)
                    return connection
                fail_with_timeout = timeout
                result = import_objects(
                    self.config, self.input_path, "Physical", connection_factory=factory,
                )
                self.assertEqual(result.status, "FAILED")
                self.assertIn("destination_outcome_uncertain", result.objects[0].reason)
                requests = [request for connection in connections for request in connection.requests]
                self.assertEqual([request[1] for request in requests], [
                    "/mgmt/system/user/login", "/mgmt/system/config/tree/Physical",
                    "/mgmt/system/config/tree/site",
                ])
                self.assertEqual(json.loads(requests[2][2]), {
                    "name": "Upper Branch", "parentOrmID": "dst-root-91",
                })
                self.assertTrue(all(connection.close_calls == 1 for connection in connections))
                self.assertNotIn(SECRET, repr(result))
