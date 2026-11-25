import copy
import importlib
import io
import json
import os
import ssl
from contextlib import redirect_stderr, redirect_stdout
from unittest.mock import Mock, patch

from offline_support import OfflineTestCase
from test_http_backend import MemoryConnection, MemoryResponse


class DestinationDiscoveryTests(OfflineTestCase):
    def setUp(self):
        super().setUp()
        self.module = importlib.import_module("cc_vision_import.destination_discovery")
        self.cli = importlib.import_module("cc_vision_import.master_cli")
        self.http = importlib.import_module("cc_vision_import.http_backend")
        self.transport = importlib.import_module("cc_vision_import.transport")
        self.auth = importlib.import_module("cc_vision_import.authentication")
        self.output = self.directory / "reports"
        self.output.mkdir()
        self.credentials = self.directory / "credentials.json"
        self.profile = {
            "destination": {"name": "cc-destination", "base_url": "https://destination.invalid"},
            "tls": {"verify": True}, "output_directory": str(self.output),
        }
        self.tree = {
            "name": "private-root-name", "meIdentifier": {
                "managedElementID": "private-root-id",
                "managedElementClass": "com.radware.insite.model.device.Site",
            },
            "password": "private-root-secret", "productVersion": "10.10.7",
            "children": [{
                "name": "private-site-name", "meIdentifier": {
                    "managedElementID": "private-site-id",
                    "managedElementClass": "com.radware.insite.model.device.Site",
                },
                "parentOrmID": "private-root-id", "token": "private-site-secret",
                "children": [{
                    "name": "private-child-name", "meIdentifier": {
                        "managedElementID": "private-child-id",
                        "managedElementClass": "com.radware.insite.model.device.Site",
                    },
                    "children": [],
                }, {
                    "name": "private-device-name", "managementIp": "192.0.2.5",
                    "meIdentifier": {
                        "managedElementID": "private-site-id",
                        "managedElementClass": "com.radware.insite.model.device.Device",
                    },
                    "deviceAccess": {"password": "private-device-secret"},
                    "children": [],
                }],
            }],
        }

    def connection(self, value, status=200):
        return MemoryConnection(MemoryResponse(
            status, json.dumps(value).encode(), [("Content-Type", "application/json")],
        ))

    def invoke(self, *connections, arguments=None, credentials_error=None):
        self.input_path.write_text(json.dumps(self.profile))
        factory = Mock(side_effect=connections)
        kwargs = (
            {"side_effect": credentials_error} if credentials_error is not None else
            {"return_value": {"username": "private-username", "password": "private-password"}}
        )
        stdout = io.StringIO()
        with (
            patch.object(self.http.http.client, "HTTPSConnection", factory),
            patch.object(self.module, "_read_credentials", **kwargs),
            redirect_stdout(stdout),
        ):
            status = self.cli.main(arguments if arguments is not None else [
                "--operation", "destination-discovery", "--discovery-profile", str(self.input_path),
                "--credentials-file", str(self.credentials),
            ])
        self.assertNotIn("private-", stdout.getvalue())
        self.assertNotIn("192.0.2.5", stdout.getvalue())
        return status, json.loads(stdout.getvalue()), factory

    def test_discovery_uses_only_login_and_tree_and_preserves_private_native_sites(self):
        connections = [
            self.connection({"status": "ok", "jsessionid": "private-session"}),
            self.connection(self.tree),
        ]
        status, report, factory = self.invoke(*connections)
        self.assertEqual(status, 0)
        self.assertFalse(report["offline_only"])
        self.assertFalse(report["configuration_writes_authorized"])
        self.assertEqual(report["product_version"], "unknown")
        self.assertFalse(report["version_discovered"])
        self.assertFalse(report["compatibility_verified"])
        self.assertEqual(report["counts"]["site_candidates"], 2)
        self.assertEqual(report["counts"]["sites_with_usable_identity"], 2)
        self.assertEqual(report["counts"]["sites_with_unresolved_dependencies"], 0)
        self.assertEqual(report["redacted_fields"], 3)
        self.assertEqual(factory.call_count, 2)
        self.assertEqual([c.requests[0][:2] for c in connections], [
            ("POST", "/mgmt/system/user/login"),
            ("GET", "/mgmt/system/config/tree/Organization"),
        ])
        self.assertIn("Authorization", connections[0].requests[0][3])
        self.assertEqual(connections[1].requests[0][3]["Cookie"], "JSESSIONID=private-session")
        for call in factory.call_args_list:
            self.assertTrue(call.kwargs["context"].check_hostname)
            self.assertEqual(call.kwargs["context"].verify_mode, ssl.CERT_REQUIRED)
        self.assertTrue(all(c.close_calls and c.response.close_calls for c in connections))
        snapshot_path = self.output / report["snapshot_directory"] / report["snapshot_file"]
        snapshot = json.loads(snapshot_path.read_text())
        self.assertEqual(snapshot["destination"]["version"], "unknown")
        self.assertEqual(snapshot["evidence"]["document_version_conflict"], "unresolved-10.10.7-versus-10.10.6")
        self.assertFalse(snapshot["scope"]["migration_input"])
        self.assertFalse(snapshot["scope"]["complete_site_enumeration"])
        self.assertEqual(snapshot["organization_root"]["native"]["meIdentifier"]["managedElementID"], "private-root-id")
        self.assertEqual(snapshot["site_nodes"][0]["native"]["parentOrmID"], "private-root-id")
        self.assertEqual(snapshot["site_nodes"][1]["observed_container_parent"], "node-2")
        raw = snapshot_path.read_text()
        for secret in ("private-root-secret", "private-site-secret", "private-device-secret", "private-session", "private-password", "private-device-name", "192.0.2.5"):
            self.assertNotIn(secret, raw)
        self.assertFalse(snapshot["scope"]["configuration_writes_authorized"])
        parser = importlib.import_module("cc_vision_import.controller_objects").parse_controller_artifact
        error = importlib.import_module("cc_vision_import.contracts").ContractValidationError
        with self.assertRaises(error):
            parser(snapshot)

    def test_login_200_alone_or_missing_cookie_does_not_allow_tree_read(self):
        for login in ({"status": "ok"}, {"status": "error", "message": "private-marker"}, {"status": "ok", "jsessionid": "bad;cookie"}):
            status, report, factory = self.invoke(self.connection(login))
            self.assertEqual(status, 1)
            self.assertEqual(report["status"], "error")
            self.assertEqual(factory.call_count, 1)
            self.assertNotIn("snapshot_directory", report)

    def test_session_cookie_is_cleared_after_success_and_authentication_failure(self):
        strategy = self.module._DiscoveryAuthentication()
        for login in (
            {"status": "ok", "jsessionid": "private-session"},
            {"status": "error", "message": "private-marker"},
        ):
            connections = [self.connection(login), self.connection(self.tree)]
            with patch.object(self.module, "_DiscoveryAuthentication", return_value=strategy):
                self.invoke(*connections)
            self.assertNotIn("Cookie", strategy.request_headers(
                self.auth.ResolvedCredentials("private-username", "private-password"),
            ))

    def test_explicit_origin_bound_lab_tls_remains_https_and_records_unverified_mode(self):
        self.profile["tls"] = {
            "verify": False, "lab_authorized": True,
            "authorized_origin": self.profile["destination"]["base_url"],
        }
        (self.directory / "tls-exception.json").write_text(json.dumps(self.profile["tls"]))
        with patch("cc_vision_import.tls_policy._private_file"), patch.dict(os.environ, {
            "CCV_ALLOW_INSECURE_TLS_EXCEPTION": "true",
        }):
            status, report, factory = self.invoke(
                self.connection({"status": "ok", "jsessionid": "private-session"}),
                self.connection(self.tree),
            )
        self.assertEqual(status, 0)
        self.assertEqual(report["tls"], {"verify": False, "exception_scope": "selected_origin_current_execution"})
        for call in factory.call_args_list:
            self.assertEqual(call.kwargs["context"].verify_mode, ssl.CERT_NONE)
            self.assertFalse(call.kwargs["context"].check_hostname)
        snapshot = json.loads((self.output / report["snapshot_directory"] / report["snapshot_file"]).read_text())
        self.assertEqual(snapshot["tls"], report["tls"])
        self.assertFalse(snapshot["scope"]["configuration_writes_authorized"])

    def test_production_rejects_even_an_explicit_unverified_profile_before_authentication(self):
        self.profile["tls"] = {
            "verify": False, "lab_authorized": True,
            "authorized_origin": self.profile["destination"]["base_url"],
        }
        with patch.dict(os.environ, {"CCV_ALLOW_INSECURE_TLS_EXCEPTION": "false"}):
            status, report, factory = self.invoke()
        self.assertEqual(status, 4)
        factory.assert_not_called()

    def test_certificate_failure_is_sanitized_and_never_retried_or_downgraded(self):
        connection = MemoryConnection(failure=("connect", ssl.SSLCertVerificationError("private-certificate-marker")))
        status, report, factory = self.invoke(connection)
        self.assertEqual(status, 1)
        self.assertEqual(report["issue_codes"], ["tls_certificate_failure"])
        self.assertEqual(report["tls"], {"verify": True})
        self.assertFalse(report["authenticated"])
        self.assertEqual(factory.call_count, 1)
        self.assertEqual(connection.requests, [])
        self.assertEqual(factory.call_args.kwargs["context"].verify_mode, ssl.CERT_REQUIRED)
        self.assertTrue(factory.call_args.kwargs["context"].check_hostname)
        self.assertNotIn("snapshot_directory", report)

    def test_lab_exception_cannot_authorize_generic_tls_or_configuration_writes(self):
        error = importlib.import_module("cc_vision_import.contracts").ContractValidationError
        with self.assertRaises(error):
            self.transport.TransportConfig(
                base_url="https://destination.invalid", connect_timeout=10, read_timeout=30, verify_tls=False,
            )
        authorization = self.http.DestinationAuthorization("https://destination.invalid", (
            (self.transport.HttpMethod.POST, "/mgmt/system/user/login"),
            (self.transport.HttpMethod.GET, "/mgmt/system/config/tree/Organization"),
            (self.transport.HttpMethod.POST, "/mgmt/system/config/tree/site"),
        ))
        backend = self.http.StdlibHttpBackend(
            allow_live=True, authorization=authorization, max_response_bytes=4096,
            allow_unverified_destination_discovery=True,
        )
        config = self.module._LabDiscoveryTransportConfig(
            base_url="https://destination.invalid", connect_timeout=10, read_timeout=30,
            operation_timeout=60, verify_tls=False, lab_authorized=True,
            authorized_origin="https://destination.invalid",
        )
        factory = Mock()
        with patch.object(self.http.http.client, "HTTPSConnection", factory), self.assertRaises(self.transport.TransportError):
            self.transport.HttpTransport(config, backend).request(
                self.transport.HttpMethod.POST, ("mgmt", "system", "config", "tree", "site"),
            )
        factory.assert_not_called()
        backend.close()

    def test_tree_rejection_and_malformed_shape_do_not_create_success_snapshots(self):
        for response, status_code in ((self.connection({"error": "private-marker"}, 403), 1), (self.connection({"status": "ok", "ormID": "private-marker"}), 4)):
            status, report, factory = self.invoke(
                self.connection({"status": "ok", "jsessionid": "private-session"}), response,
            )
            self.assertEqual(status, status_code)
            self.assertEqual(report["status"], "error")
            self.assertEqual(factory.call_count, 2)
            self.assertNotIn("snapshot_directory", report)

    def test_partial_identity_and_explicit_parent_conflicts_are_saved_as_partial(self):
        tree = copy.deepcopy(self.tree)
        site = tree["children"][0]
        child = site["children"][0]
        child["parentOrmID"] = "private-wrong-parent"
        child["meIdentifier"].pop("managedElementID")
        status, report, factory = self.invoke(
            self.connection({"status": "ok", "jsessionid": "private-session"}),
            self.connection(tree),
        )
        self.assertEqual(status, 1)
        self.assertEqual(report["status"], "partial")
        self.assertEqual(report["counts"]["sites_with_unresolved_dependencies"], 1)
        self.assertIn("native_identity_missing_or_unverified_type", report["issue_codes"])
        valid_child = copy.deepcopy(self.tree)
        valid_child["children"][0]["children"][0]["parentOrmID"] = "private-wrong-parent"
        projection = self.module.project_site_tree(valid_child)
        self.assertIn("explicit_parent_conflicts_with_containment", projection["issue_codes"])
        self.assertEqual(projection["site_nodes"][1]["native"]["parentOrmID"], "private-wrong-parent")

    def test_duplicates_unknown_nodes_and_limits_remain_explicit_without_input_mutation(self):
        tree = copy.deepcopy(self.tree)
        child = tree["children"][0]["children"][0]
        child["meIdentifier"]["managedElementID"] = "private-site-id"
        tree["children"].append({"meIdentifier": {}, "children": []})
        before = copy.deepcopy(tree)
        projection = self.module.project_site_tree(tree)
        self.assertEqual(tree, before)
        self.assertEqual(projection["status"], "partial")
        self.assertEqual(projection["counts"]["unclassified_nodes"], 1)
        self.assertIn("duplicate_native_identity", projection["issue_codes"])
        error = importlib.import_module("cc_vision_import.contracts").ContractValidationError
        with self.assertRaises(error):
            self.module.project_site_tree({**self.tree, "children": [None]})
        tree = copy.deepcopy(self.tree)
        leaf = tree
        for _ in range(66):
            leaf["children"] = [copy.deepcopy(self.tree)]
            leaf = leaf["children"][0]
        with self.assertRaises(error):
            self.module.project_site_tree(tree)
        with self.assertRaises(error):
            self.module.project_site_tree({**self.tree, "children": [self.tree["children"][0]["children"][0]] * 10000})
        root = copy.deepcopy(self.tree)
        root["meIdentifier"]["managedElementClass"] = "private-unknown-class"
        projection = self.module.project_site_tree(root)
        self.assertEqual(projection["counts"]["sites_with_unresolved_dependencies"], 2)
        self.assertIn("ancestor_dependency_unresolved", projection["site_nodes"][1]["issue_codes"])
        self.assertIsNone(projection["organization_root"]["native"]["meIdentifier"]["managedElementClass"])

    def test_invalid_profiles_and_credentials_never_send_login(self):
        for changes in (
            {"destination": {"name": "cc-destination", "base_url": "http://private-marker.invalid"}},
            {"destination": {"name": "cc-destination", "base_url": "https://destination.invalid:8443"}},
            {"destination": {**self.profile["destination"], "version": "10.10.7"}},
            {"tls": {"verify": False}},
            {"output_directory": str(self.directory / "missing")},
        ):
            original = self.profile
            self.profile = {**self.profile, **changes}
            status, report, factory = self.invoke()
            self.assertIn(status, (3, 4))
            factory.assert_not_called()
            self.profile = original
        status, report, factory = self.invoke(credentials_error=self.module.SetupError("private-marker"))
        self.assertEqual(status, 1)
        factory.assert_not_called()
        self.assertEqual(report["issue_codes"], ["secret_resolution_failure"])

    def test_backend_rejects_version_reads_source_reads_and_writes_before_connection(self):
        self.input_path.write_text(json.dumps(self.profile))
        profile = self.module.DiscoveryProfile.read(str(self.input_path))
        backend = self.module._backend(profile)
        error = self.transport.TransportError
        factory = Mock()
        with patch.object(self.http.http.client, "HTTPSConnection", factory):
            transport = self.transport.HttpTransport(profile.transport, backend)
            for method, segments in (
                (self.transport.HttpMethod.GET, ("mgmt", "system", "config", "version")),
                (self.transport.HttpMethod.GET, ("mgmt", "system", "config", "itemlist", "alldevices")),
                (self.transport.HttpMethod.POST, ("mgmt", "system", "config", "tree", "site")),
                (self.transport.HttpMethod.PUT, ("mgmt", "system", "config", "tree", "device")),
            ):
                with self.assertRaises(error):
                    transport.request(method, segments)
        factory.assert_not_called()
        backend.close()
        from dataclasses import replace
        backend = self.module._backend(profile)
        with patch.object(self.http.http.client, "HTTPSConnection", factory):
            transport = self.transport.HttpTransport(
                replace(profile.transport, base_url="https://other.invalid"), backend,
            )
            with self.assertRaises(error):
                transport.request(self.transport.HttpMethod.GET, self.module._TREE)
        factory.assert_not_called()
        backend.close()

    def test_unknown_session_metadata_is_scoped_without_weakening_existing_version_checks(self):
        error = importlib.import_module("cc_vision_import.contracts").ContractValidationError
        reference = self.auth.CredentialReference("cc-destination-discovery")
        with self.assertRaises(error):
            self.auth.AuthenticationRequest(self.auth.SessionRole.DESTINATION, "cyber-controller", "unknown", reference)
        with self.assertRaises(error):
            self.module._UnknownVersionRequest(self.auth.SessionRole.SOURCE, "cyber-controller", "unknown", reference)
        with self.assertRaises(error):
            self.module._UnknownVersionRequest(self.auth.SessionRole.DESTINATION, "cyber-controller", "0.0-test", reference)

    def test_discovery_requires_explicit_cli_selection(self):
        with patch.object(self.module, "_backend") as backend, redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            self.assertEqual(self.cli.main(["--operation", "operations"]), 0)
            backend.assert_not_called()
            with self.assertRaises(SystemExit) as caught:
                self.cli.main(["--operation", "destination-discovery"])
            self.assertEqual(caught.exception.code, 2)
