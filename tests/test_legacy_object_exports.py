import copy
import io
import json
import ssl
import traceback
import warnings
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import replace
from unittest.mock import Mock, patch

from offline_support import OfflineTestCase
from test_http_backend import MemoryConnection, MemoryResponse

from cc_vision_import.client import ApiClient, ClientError
from cc_vision_import.config import ControllerConfig
from cc_vision_import.files import JsonFileError, load_json
from cc_vision_import.objects import ExportError, export_objects


SITE = "com.radware.insite.model.device.Site"
DEVICE = "com.radware.insite.model.device.Device"
TREE = ("mgmt", "system", "config", "tree")
SECRET = "synthetic-device-secret"


def site(identity, name, *children):
    return {
        "name": name,
        "meIdentifier": {"managedElementID": identity, "managedElementClass": SITE},
        "children": list(children),
    }


def device(identity, name, address):
    return {
        "name": name, "type": "synthetic-runtime-model", "managementIp": address,
        "meIdentifier": {"managedElementID": identity, "managedElementClass": DEVICE},
    }


def access():
    return {
        "deviceSetup": {"deviceAccess": {
            "ormID": "server-owned-access-901",
            "cliUsername": "synthetic-cli", "cliPassword": SECRET,
            "httpUsername": "synthetic-http", "httpPassword": "synthetic-http-secret",
            "httpsUsername": "synthetic-https", "httpsPassword": "synthetic-https-secret",
            "snmpV3Username": "synthetic-snmp",
            "snmpV3AuthenticationPassword": "synthetic-auth-secret",
            "snmpV3PrivacyPassword": "synthetic-privacy-secret",
            "supportedOpaqueSetting": {"values": [False, None, "synthetic-value"]},
        }},
    }


class LegacyObjectExportTests(OfflineTestCase):
    def setUp(self):
        super().setUp()
        self.config = ControllerConfig(
            address="source.example.invalid", username="synthetic-operator",
            password="synthetic-controller-secret", product="vision",
        )
        self.root = site(
            "source-root-11", "Source Canopy",
            device("source-device-12", "Root Node", "192.0.2.41"),
            site("source-site-13", "Branch Alder",
                 site("source-site-14", "Branch Birch",
                      device("source-device-15", "Nested Node", "192.0.2.42"))),
        )
        self.responses = {
            (*TREE, "Physical"): copy.deepcopy(self.root),
            (*TREE, "Organization"): site("source-root-71", "Organization Canopy"),
            (*TREE, "device", "byip", "192.0.2.41"): access(),
            (*TREE, "device", "byip", "192.0.2.42"): access(),
        }
        self.outputs = {"Physical": self.directory / "physical-synthetic.json"}
        self.client = Mock(spec=ApiClient)
        self.client.__enter__ = Mock(return_value=self.client)
        self.client.__exit__ = Mock(return_value=False)
        self.client.get.side_effect = self.read

    def read(self, path):
        response = self.responses[path]
        if isinstance(response, Exception):
            raise response
        return response

    def export(self, outputs=None):
        with warnings.catch_warnings(record=True) as emitted:
            warnings.simplefilter("always")
            with patch("cc_vision_import.objects.ApiClient", return_value=self.client) as constructor:
                results = export_objects(self.config, self.outputs if outputs is None else outputs)
        self.assertTrue(any("sensitive device credentials" in str(item.message) for item in emitted))
        constructor.assert_called_once()
        self.client.__enter__.assert_called_once()
        self.client.__exit__.assert_called_once()
        return results

    def test_physical_export_exact_fields_nested_and_root_devices(self):
        results = self.export()
        result = results["Physical"]
        self.assertEqual((result.status, result.site_count, result.device_count), ("SUCCESS", 2, 2))
        data = load_json(self.outputs["Physical"])
        self.assertEqual(set(data), {"source_root", "sites", "devices"})
        self.assertEqual(data["source_root"], {"id": "source-root-11", "name": "Source Canopy"})
        self.assertEqual(data["sites"], [
            {"name": "Branch Alder", "id": "source-site-13",
             "parent_site_name": "Source Canopy", "parentOrmID": "source-root-11"},
            {"name": "Branch Birch", "id": "source-site-14",
             "parent_site_name": "Branch Alder", "parentOrmID": "source-site-13"},
        ])
        expected_access = access()["deviceSetup"]["deviceAccess"]
        expected_access.pop("ormID")
        self.assertEqual(data["devices"], [
            {"name": "Root Node", "type": "synthetic-runtime-model", "managementIp": "192.0.2.41",
             "id": "source-device-12", "parentOrmID": "source-root-11", "deviceAccess": expected_access},
            {"name": "Nested Node", "type": "synthetic-runtime-model", "managementIp": "192.0.2.42",
             "id": "source-device-15", "parentOrmID": "source-site-14", "deviceAccess": expected_access},
        ])
        self.assertFalse(any("byid" in call.args[0] for call in self.client.get.call_args_list))

    def test_organization_export_dynamic_ids_names_types_and_ip(self):
        self.responses[(*TREE, "Organization")] = site(
            "source-root-88", "Different Canopy",
            device("source-device-89", "Different Node", "198.51.100.22"),
        )
        self.responses[(*TREE, "Organization")]["children"][0]["type"] = "another-runtime-model"
        self.responses[(*TREE, "device", "byip", "198.51.100.22")] = access()
        output = self.directory / "arbitrary-organization-name.json"
        results = self.export({"Organization": output})
        self.assertEqual(results["Organization"].status, "SUCCESS")
        data = load_json(output)
        self.assertEqual(data["source_root"], {"id": "source-root-88", "name": "Different Canopy"})
        self.assertEqual(data["devices"][0]["type"], "another-runtime-model")
        self.assertEqual(data["devices"][0]["parentOrmID"], "source-root-88")

    def test_original_responses_and_supported_credentials_preserved(self):
        original = copy.deepcopy(self.responses)
        self.export()
        self.assertEqual(self.responses, original)
        data = load_json(self.outputs["Physical"])
        for row in data["devices"]:
            self.assertEqual(row["deviceAccess"]["cliPassword"], SECRET)
            self.assertEqual(row["deviceAccess"]["snmpV3AuthenticationPassword"], "synthetic-auth-secret")
            self.assertEqual(row["deviceAccess"]["snmpV3PrivacyPassword"], "synthetic-privacy-secret")
            self.assertNotIn("ormID", row["deviceAccess"])
        self.assertIn("ormID", self.responses[(*TREE, "device", "byip", "192.0.2.41")]["deviceSetup"]["deviceAccess"])

    def test_parent_site_by_id_fallback_for_missing_root_and_site_names(self):
        del self.responses[(*TREE, "Physical")]["name"]
        del self.responses[(*TREE, "Physical")]["children"][1]["name"]
        self.responses[(*TREE, "site", "byid", "source-root-11")] = {"name": "Recovered Canopy"}
        self.responses[(*TREE, "site", "byid", "source-site-13")] = {"name": "Recovered Alder"}
        self.export()
        data = load_json(self.outputs["Physical"])
        self.assertEqual(data["source_root"]["name"], "Recovered Canopy")
        self.assertEqual(data["sites"][0]["parent_site_name"], "Recovered Canopy")
        self.assertEqual(data["sites"][1]["parent_site_name"], "Recovered Alder")
        self.client.authorize_gets.assert_any_call(((*TREE, "site", "byid", "source-root-11"),))

    def test_empty_hierarchy_is_successful_with_root_metadata(self):
        self.responses[(*TREE, "Physical")] = site("empty-root-3", "Empty Canopy")
        result = self.export()["Physical"]
        self.assertEqual((result.status, result.site_count, result.device_count), ("SUCCESS", 0, 0))
        self.assertEqual(load_json(self.outputs["Physical"]), {
            "source_root": {"id": "empty-root-3", "name": "Empty Canopy"}, "sites": [], "devices": [],
        })
        self.assertEqual(self.client.get.call_count, 1)

    def test_both_exports_use_one_context_and_independent_files(self):
        outputs = {**self.outputs, "Organization": self.directory / "organization-other.json"}
        results = self.export(outputs)
        self.assertEqual(set(results), {"Physical", "Organization"})
        self.assertTrue(all(result.status == "SUCCESS" for result in results.values()))
        self.assertNotEqual(
            load_json(outputs["Physical"])["source_root"],
            load_json(outputs["Organization"])["source_root"],
        )

    def test_missing_and_ambiguous_parent_identities_fail_without_output(self):
        for root in (
            {"name": "Missing Identity", "children": []},
            site("same-id", "Root", site("same-id", "Child")),
            site("root", "Root", site("duplicate", "First"), site("duplicate", "Second")),
        ):
            with self.subTest(root=root):
                self.responses[(*TREE, "Physical")] = root
                self.client.reset_mock()
                result = self.export()["Physical"]
                self.assertEqual(result.status, "FAILED")
                self.assertIsNone(result.path)
                self.assertFalse(self.outputs["Physical"].exists())

    def test_ambiguous_or_missing_by_id_parent_name_fails(self):
        for fallback in (
            {},
            {"name": "Wrong Parent", "meIdentifier": {"managedElementID": "different-id"}},
            ClientError("http_error", status=404),
        ):
            with self.subTest(fallback=fallback):
                self.responses[(*TREE, "Physical")] = site("root", "", site("child", "Child"))
                self.responses[(*TREE, "site", "byid", "root")] = fallback
                self.client.reset_mock()
                result = self.export()["Physical"]
                self.assertEqual((result.status, result.failed_step), ("FAILED", "source_root_name"))
                self.assertFalse(self.outputs["Physical"].exists())

    def test_malformed_hierarchy_and_unknown_nodes_fail_explicitly(self):
        for root in (
            [], {}, {"name": "Root", "meIdentifier": {"managedElementID": "root"}},
            site("root", "Root", None),
            site("root", "Root", {"name": "Unknown", "meIdentifier": {
                "managedElementID": "unknown", "managedElementClass": "unrecognized-class"}}),
            site("root", "Root", site("child", "Child")),
        ):
            with self.subTest(root=root):
                if isinstance(root, dict) and root.get("children") and isinstance(root["children"][0], dict):
                    if root["children"][0].get("name") == "Child":
                        del root["children"][0]["children"]
                self.responses[(*TREE, "Physical")] = root
                self.client.reset_mock()
                result = self.export()["Physical"]
                self.assertEqual(result.status, "FAILED")
                self.assertFalse(self.outputs["Physical"].exists())

    def test_device_access_failure_never_silently_drops_device(self):
        for response in (
            ClientError("http_error", status=500), None, {}, {"deviceSetup": {}},
            {"deviceSetup": {"deviceAccess": []}},
        ):
            with self.subTest(response=response):
                self.responses[(*TREE, "device", "byip", "192.0.2.42")] = response
                self.client.reset_mock()
                result = self.export()["Physical"]
                self.assertEqual((result.status, result.failed_step), ("FAILED", "device_access[1]"))
                self.assertIsNone(result.path)
                self.assertFalse(self.outputs["Physical"].exists())

    def test_missing_device_field_fails_without_root_substitution(self):
        del self.responses[(*TREE, "Physical")]["children"][0]["managementIp"]
        result = self.export()["Physical"]
        self.assertEqual((result.status, result.failed_step), ("FAILED", "device_management_ip"))
        self.assertEqual(self.client.get.call_count, 1)

    def test_missing_server_owned_access_id_is_allowed(self):
        self.responses[(*TREE, "device", "byip", "192.0.2.41")]["deviceSetup"]["deviceAccess"].pop("ormID")
        self.assertEqual(self.export()["Physical"].status, "SUCCESS")

    def test_each_tree_failure_is_independent(self):
        outputs = {**self.outputs, "Organization": self.directory / "independent.json"}
        self.responses[(*TREE, "Physical")] = ClientError("http_error", status=500)
        results = self.export(outputs)
        self.assertEqual(results["Physical"].status, "FAILED")
        self.assertEqual(results["Organization"].status, "SUCCESS")
        self.assertEqual(load_json(outputs["Organization"])["devices"], [])
        self.assertFalse(outputs["Physical"].exists())
        self.client.reset_mock()
        self.responses[(*TREE, "Physical")] = self.root
        self.responses[(*TREE, "Organization")] = ClientError("malformed_json_response")
        results = self.export(outputs)
        self.assertEqual(results["Physical"].status, "SUCCESS")
        self.assertEqual(results["Organization"].status, "FAILED")

    def test_file_write_failure_is_independent_and_explicit(self):
        outputs = {"Physical": self.directory / "missing" / "cannot-write.json",
                   "Organization": self.directory / "writable.json"}
        results = self.export(outputs)
        self.assertEqual(
            (results["Physical"].status, results["Physical"].failed_step), ("FAILED", "file_write"),
        )
        self.assertEqual(results["Organization"].status, "SUCCESS")

    def test_secrets_never_appear_in_results_errors_or_warnings(self):
        self.responses[(*TREE, "device", "byip", "192.0.2.41")] = ClientError("malformed_json_response")
        with redirect_stdout(io.StringIO()) as out, redirect_stderr(io.StringIO()) as err:
            result = self.export()["Physical"]
        rendered = repr(result) + out.getvalue() + err.getvalue()
        self.assertNotIn(SECRET, rendered)
        self.assertNotIn(self.config.password, rendered)
        self.assertEqual(result.status, "FAILED")

    def test_invalid_selection_and_duplicate_output_paths_do_not_authenticate(self):
        for outputs in ({}, {"Unknown": self.input_path},
                        {"Physical": self.input_path, "Organization": self.input_path}):
            with self.subTest(outputs=outputs):
                with patch("cc_vision_import.objects.ApiClient") as constructor:
                    with self.assertRaises(ExportError):
                        export_objects(self.config, outputs)
                    constructor.assert_not_called()

    def memory_export(self, responses, outputs=None, **kwargs):
        connections = [MemoryConnection(response) for response in responses]
        factory = Mock(side_effect=connections)
        with warnings.catch_warnings(record=True):
            results = export_objects(
                self.config, self.outputs if outputs is None else outputs,
                connection_factory=factory, **kwargs,
            )
        return results, connections, factory

    def wire(self, value):
        return MemoryResponse(body=json.dumps(value).encode("utf-8"))

    def test_real_client_both_trees_dynamic_gets_one_login_and_cleanup(self):
        outputs = {**self.outputs, "Organization": self.directory / "second-tree.json"}
        login = self.wire({"status": "ok"})
        login.headers = [("Set-Cookie", "JSESSIONID=synthetic-export-cookie; Secure; Path=/")]
        results, connections, factory = self.memory_export([
            login, self.wire(self.root), self.wire(access()), self.wire(access()),
            self.wire(site("other-root-73", "Other Canopy")),
        ], outputs)
        self.assertTrue(all(result.status == "SUCCESS" for result in results.values()))
        requests = [request for connection in connections for request in connection.requests]
        self.assertEqual([request[0] for request in requests], ["POST", "GET", "GET", "GET", "GET"])
        self.assertEqual(requests[0][1], "/mgmt/system/user/login")
        self.assertEqual(requests[2][1], "/mgmt/system/config/tree/device/byip/192.0.2.41")
        self.assertEqual(factory.call_count, 5)
        self.assertTrue(all("synthetic-export-cookie" in request[3]["Cookie"] for request in requests[1:]))
        self.assertTrue(all(connection.close_calls == 1 for connection in connections))
        self.assertTrue(all(connection.response.close_calls == 1 for connection in connections))

    def test_real_client_dynamic_site_fallback(self):
        root = site("lookup-root-7", "", site("lookup-child-8", "Child"))
        results, connections, _ = self.memory_export([
            self.wire({"status": "ok"}), self.wire(root), self.wire({"name": "Resolved Canopy"}),
        ])
        self.assertEqual(results["Physical"].status, "SUCCESS")
        self.assertEqual(connections[2].requests[0][1], "/mgmt/system/config/tree/site/byid/lookup-root-7")

    def test_real_client_login_failure_marks_both_trees_failed_and_closes(self):
        outputs = {**self.outputs, "Organization": self.directory / "other.json"}
        results, connections, factory = self.memory_export([
            MemoryResponse(status=401, body=b"private-server-marker"),
        ], outputs)
        self.assertTrue(all(result.status == "FAILED" for result in results.values()))
        self.assertTrue(all(result.failed_step == "authentication" for result in results.values()))
        self.assertEqual(factory.call_count, 1)
        self.assertEqual(connections[0].close_calls, 1)

    def test_real_client_access_failure_closes_and_does_not_retry(self):
        results, connections, factory = self.memory_export([
            self.wire({"status": "ok"}), self.wire(self.root),
            MemoryResponse(status=500, body=b"private-server-marker"),
        ])
        self.assertEqual(results["Physical"].status, "FAILED")
        self.assertEqual(factory.call_count, 3)
        self.assertTrue(all(connection.close_calls == 1 for connection in connections))

    def test_real_client_malformed_json_fails_without_retry_or_secret_output(self):
        with redirect_stdout(io.StringIO()) as out, redirect_stderr(io.StringIO()) as err:
            results, connections, factory = self.memory_export([
                self.wire({"status": "ok"}), MemoryResponse(body=b'{"private-response-marker":'),
            ])
        result = results["Physical"]
        self.assertEqual((result.status, result.failed_step), ("FAILED", "hierarchy"))
        self.assertNotIn("private-response-marker", repr(result) + out.getvalue() + err.getvalue())
        self.assertEqual(factory.call_count, 2)
        self.assertTrue(all(connection.close_calls == 1 for connection in connections))

    def test_real_client_unverified_session_supports_dynamic_export_reads(self):
        self.config = replace(self.config, verify_tls=False)
        results, _, factory = self.memory_export([
            self.wire({"status": "ok"}), self.wire(site("tls-root-4", "")),
            self.wire({"name": "TLS Canopy"}),
        ], tls_exception_authorized=True)
        self.assertEqual(results["Physical"].status, "SUCCESS")
        self.assertTrue(all(
            call.kwargs["context"].verify_mode == ssl.CERT_NONE for call in factory.call_args_list
        ))

    def test_real_client_read_authorization_cannot_add_write_or_change_origin(self):
        connection = MemoryConnection(self.wire({"status": "ok"}))
        factory = Mock(return_value=connection)
        with ApiClient(self.config, connection_factory=factory) as client:
            client.authorize_gets(((*TREE, "device", "byip", "192.0.2.60"),))
            with self.assertRaises(ClientError):
                client.post((*TREE, "device", "byip", "192.0.2.60"), {})
            with self.assertRaises(ClientError):
                client.authorize_gets((("https://other.example.invalid",),))
        self.assertEqual(factory.call_count, 1)

    def test_cleanup_failure_is_not_reported_as_export_success(self):
        client = ApiClient(self.config, connection_factory=Mock())
        with (
            patch("cc_vision_import.objects.ApiClient", return_value=client),
            patch.object(client, "login"),
            patch.object(client, "get", side_effect=self.read),
            patch.object(client, "authorize_gets"),
            patch.object(client, "close", side_effect=ClientError("local_cleanup_failed")),
            warnings.catch_warnings(record=True),
        ):
            result = export_objects(self.config, self.outputs)["Physical"]
        client.close()
        self.assertEqual((result.status, result.failed_step), ("FAILED", "session_cleanup"))
        self.assertTrue(result.cleanup_failed)
        self.assertEqual((result.site_count, result.device_count), (2, 2))
        self.assertTrue(self.outputs["Physical"].exists())

    def test_cleanup_failure_preserves_primary_tree_error(self):
        client = ApiClient(self.config, connection_factory=Mock())
        with (
            patch("cc_vision_import.objects.ApiClient", return_value=client),
            patch.object(client, "login"),
            patch.object(client, "get", side_effect=ClientError("http_error", status=500)),
            patch.object(client, "authorize_gets"),
            patch.object(client, "close", side_effect=ClientError("local_cleanup_failed")),
            warnings.catch_warnings(record=True),
        ):
            result = export_objects(self.config, self.outputs)["Physical"]
        client.close()
        self.assertEqual((result.status, result.failed_step), ("FAILED", "hierarchy"))
        self.assertEqual(result.error_code, "http_error")
        self.assertTrue(result.cleanup_failed)

    def test_authentication_cleanup_failure_note_is_preserved_in_results(self):
        error = ClientError("authentication_rejected")
        error.add_note("Local API session cleanup failed.")
        self.client.__enter__.side_effect = error
        with patch("cc_vision_import.objects.ApiClient", return_value=self.client), warnings.catch_warnings(record=True):
            result = export_objects(self.config, self.outputs)["Physical"]
        self.assertEqual((result.status, result.failed_step), ("FAILED", "authentication"))
        self.assertEqual(result.error_code, "authentication_rejected")
        self.assertTrue(result.cleanup_failed)
        self.client.get.assert_not_called()

    def test_saved_file_error_message_is_not_echoed(self):
        with patch("cc_vision_import.objects.save_json", side_effect=JsonFileError(SECRET)):
            result = self.export()["Physical"]
        self.assertNotIn(SECRET, repr(result))
        self.assertEqual(result.error_code, "file_write_failed")

    def test_invalid_selection_error_is_secret_free(self):
        with self.assertRaises(ExportError) as caught:
            export_objects(self.config, {SECRET: self.input_path})
        self.assertNotIn(SECRET, "".join(traceback.format_exception(caught.exception)))
