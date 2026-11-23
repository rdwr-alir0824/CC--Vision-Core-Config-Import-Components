import copy
import importlib
import json
import traceback
from unittest.mock import Mock, patch

from offline_support import OfflineTestCase
from test_authentication import FakeOwnedBackend


class ProductClientTestSupport(OfflineTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.c = importlib.import_module("cc_vision_import.capabilities")
        self.p = importlib.import_module("cc_vision_import.product_clients")
        self.a = importlib.import_module("cc_vision_import.authentication")
        self.s = importlib.import_module("cc_vision_import.sessions")

        class ExplicitMockBackend(FakeOwnedBackend, self.s.MockSessionBackend):
            pass

        self.mock_backend = ExplicitMockBackend
        self.t = importlib.import_module("cc_vision_import.transport")
        self.contracts = importlib.import_module("cc_vision_import.contracts")
        self.clock = Mock(return_value=100.0)
        self.credentials = {
            "synthetic/source": self.a.ResolvedCredentials("source-user", "source-password"),
            "synthetic/destination": self.a.ResolvedCredentials("destination-user", "destination-password"),
        }
        self.resolver = Mock()
        self.resolver.resolve.side_effect = lambda reference: self.credentials[reference.value]

    def response(self, payload):
        return self.t.HttpResponse(200, json.dumps(payload).encode("utf-8"))

    def tree(self):
        return {
            "meIdentifier": {"managedElementID": "source-root"},
            "children": [{
                "meIdentifier": {"managedElementID": "source-child"},
                "children": [], "opaqueField": {"preserved": True},
            }],
        }

    def open_client(self, product, *outcomes, role=None, version="0.0-test", lifetime=None):
        role = self.a.SessionRole.SOURCE if role is None else role
        backend = self.mock_backend(self.response({"status": "ok"}), *outcomes)
        manager = self.s.SessionManager(lambda: backend, self.resolver, clock=self.clock)
        self.addCleanup(manager.close_all)
        manager.initialize(
            self.a.AuthenticationRequest(
                role, product, version, self.a.CredentialReference(f"synthetic/{role.value}"),
                self.a.SessionExpiration(lifetime),
            ),
            self.t.TransportConfig(
                base_url=f"https://{role.value}.invalid",
                connect_timeout=2, read_timeout=4, read_retries=3,
            ),
        )
        manager.authenticate(role)
        client_type = self.p.VisionClient if product == "vision" else self.p.CyberControllerClient
        return client_type(manager, role, "0.0-test"), manager, backend


class ProductClientTests(ProductClientTestSupport):
    def test_controller_lookups_reuse_session_get_and_preserve_partial_response(self) -> None:
        payload = {
            "ormID": "synthetic-object", "name": "Existing site",
            "unknown": {"second": [None, True, 1], "first": False},
        }
        client, _, backend = self.open_client(
            "cyber-controller", *(self.response(payload) for _ in range(3)),
        )
        for index, (method, value, suffix, record) in enumerate((
            (client.get_site_by_name, "Existing site", "site/byname/Existing%20site", "API-04"),
            (client.get_site_by_id, "synthetic-object", "site/byid/synthetic-object", "API-05"),
            (client.get_device_by_ip, "192.0.2.10", "device/byip/192.0.2.10", "API-06"),
        ), start=1):
            result = method(value)
            self.assertEqual(result.objects, (payload,))
            self.assertEqual(result.capability.source_record, record)
            self.assertFalse(result.capability.live_tested)
            request = backend.requests[index]
            self.assertEqual(request.url, "https://source.invalid/mgmt/system/config/tree/" + suffix)
            self.assertEqual(request.method, self.t.HttpMethod.GET)
            self.assertIsNone(request.body)
            self.assertTrue(request.tls_context.check_hostname)
            artifact = result.to_artifact(exported_at="2026-11-22T00:00:00Z")
            self.assertNotEqual(artifact.domain, "controller-objects")
            self.assertEqual(list(artifact.objects), [payload])
        self.assertEqual(len(backend.requests), 4)

    def test_controller_lookup_capabilities_remain_mock_only_and_parameters_are_guarded(self) -> None:
        for operation in self.c.LookupCapability:
            for product, version, mock_only in (
                ("cyber-controller", "0.0-test", False),
                ("cyber-controller", "10.10.7", False),
                ("cyber-controller", "10.10.7", True),
                ("vision", "0.0-test", True),
            ):
                with self.assertRaises(self.c.ProductClientError):
                    self.c.require_capability(product, version, operation, mock_only=mock_only)
        client, _, backend = self.open_client("cyber-controller")
        for value in ("", "..", "name/other", "name%2Fother", "name\\other"):
            with self.assertRaises(self.contracts.ContractValidationError):
                client.get_site_by_name(value)
        self.assertEqual(len(backend.requests), 1)

    def test_controller_lookup_malformed_results_are_not_absence_or_empty_inventory(self) -> None:
        for payload in (
            None, [], "There is no site with name", {}, {"ormID": "", "name": "Site"},
            {"name": "Site", "meIdentifier": {"managedElementID": "ambiguous-alias"}},
        ):
            client, _, _ = self.open_client("cyber-controller", self.response(payload))
            with self.assertRaises(self.c.ProductClientError) as caught:
                client.get_site_by_id("synthetic-object")
            self.assertEqual(caught.exception.category, self.c.ClientErrorCategory.MALFORMED_RESPONSE)

    def test_default_lookup_does_not_grant_synthetic_capabilities(self) -> None:
        for product, operation in (
            ("vision", self.c.ReadCapability.LDAP_PERMISSIONS),
            ("cyber-controller", self.c.ReadCapability.PHYSICAL_TREE),
        ):
            with self.subTest(product=product):
                with self.assertRaises(self.c.ProductClientError):
                    self.c.require_capability(product, "0.0-test", operation)

    def test_unmarked_injected_backend_cannot_use_synthetic_clients(self) -> None:
        for product, client_type in (
            ("vision", self.p.VisionClient), ("cyber-controller", self.p.CyberControllerClient),
        ):
            with self.subTest(product=product):
                backend = FakeOwnedBackend()
                backend.is_mock = True
                manager = self.s.SessionManager(lambda: backend, self.resolver)
                self.addCleanup(manager.close_all)
                manager.initialize(
                    self.a.AuthenticationRequest(
                        self.a.SessionRole.SOURCE, product, "0.0-test",
                        self.a.CredentialReference("synthetic/source"),
                    ),
                    self.t.TransportConfig(
                        base_url="https://source.invalid", connect_timeout=2, read_timeout=4,
                    ),
                )
                with self.assertRaises(self.c.ProductClientError):
                    client_type(manager, self.a.SessionRole.SOURCE, "0.0-test")
                self.assertEqual(backend.requests, [])
                self.resolver.resolve.assert_not_called()

    def test_unapproved_real_versions_are_rejected_in_both_catalogue_modes(self) -> None:
        for product, operation in (
            ("vision", self.c.ReadCapability.LDAP_PERMISSIONS),
            ("cyber-controller", self.c.ReadCapability.PHYSICAL_TREE),
        ):
            for version in ("1.0", "2.0", "9.9", "0.0", "0.0-test-extra"):
                for mock_only in (False, True):
                    with self.subTest(product=product, version=version, mock_only=mock_only):
                        with self.assertRaises(self.c.ProductClientError) as caught:
                            self.c.require_capability(product, version, operation, mock_only=mock_only)
                        self.assertEqual(caught.exception.category, self.c.ClientErrorCategory.UNSUPPORTED_CAPABILITY)

    def test_synthetic_version_cannot_be_enabled_by_production_catalogue_entries(self) -> None:
        declaration = self.c.require_capability(
            "vision", "0.0-test", self.c.ReadCapability.LDAP_PERMISSIONS, mock_only=True,
        )
        with patch.object(self.c, "VERIFIED_CAPABILITIES", (declaration,)):
            with self.assertRaises(self.c.ProductClientError):
                self.c.require_capability("vision", "0.0-test", self.c.ReadCapability.LDAP_PERMISSIONS)

    def test_mock_backend_binding_is_rechecked_after_role_reinitialization(self) -> None:
        client, manager, previous = self.open_client("vision")
        role = self.a.SessionRole.SOURCE
        manager.close(role)
        unmarked = FakeOwnedBackend()
        manager._factory = lambda: unmarked
        manager.initialize(
            self.a.AuthenticationRequest(
                role, "vision", "0.0-test", self.a.CredentialReference("synthetic/source"),
            ),
            self.t.TransportConfig(
                base_url="https://source.invalid", connect_timeout=2, read_timeout=4,
            ),
        )
        with self.assertRaises(self.c.ProductClientError) as caught:
            client.list_ldap_permissions()
        self.assertEqual(caught.exception.category, self.c.ClientErrorCategory.MOCK_BACKEND_REQUIRED)
        self.assertEqual(previous.close_calls, 1)
        self.assertEqual(unmarked.requests, [])

    def test_controller_reads_use_only_the_two_observed_paths(self) -> None:
        payload = self.tree()
        client, _, backend = self.open_client(
            "cyber-controller", self.response(payload), self.response(payload),
        )
        for result, suffix, record in (
            (client.export_physical_tree(), "Physical", "API-02"),
            (client.export_organization_tree(), "Organization", "API-03"),
        ):
            self.assertEqual(result.objects, (payload,))
            self.assertEqual(result.capability.source_record, record)
            self.assertEqual(result.capability.qualification, "synthetic-mock-only")
            self.assertEqual(result.capability.response_schema, "synthetic-unverified")
            self.assertFalse(result.capability.compatibility_verified)
            self.assertFalse(result.capability.officially_documented)
            self.assertFalse(result.capability.live_tested)
            request = backend.requests[1 if suffix == "Physical" else 2]
            self.assertEqual(request.method, self.t.HttpMethod.GET)
            self.assertEqual(request.url, f"https://source.invalid/mgmt/system/config/tree/{suffix}")
            self.assertIsNone(request.body)
            self.assertEqual((request.connect_timeout, request.read_timeout), (2, 4))
            self.assertTrue(request.tls_context.check_hostname)
            self.assertFalse(request.follow_redirects)
        self.assertEqual(len(backend.requests), 3)

    def test_vision_list_preserves_opaque_fields_and_builds_validated_artifact(self) -> None:
        payload = [{"attributeValue": "synthetic-group", "unknown": [1, {"flag": False}]}]
        original = copy.deepcopy(payload)
        client, _, backend = self.open_client("vision", self.response(payload))
        result = client.list_ldap_permissions()
        artifact = result.to_artifact(exported_at="2026-11-17T00:00:00Z")
        self.assertEqual(list(result.objects), original)
        self.assertEqual(list(artifact.objects), original)
        self.assertEqual(artifact.source.product, "vision")
        self.assertEqual(artifact.domain, "ldap-permissions")
        self.assertEqual(artifact.validation.status, "valid")
        self.assertEqual(artifact.schema_version, 1)
        self.assertEqual(
            backend.requests[-1].url,
            "https://source.invalid/mgmt/system/config/itemlist/ldapobjectpermission",
        )
        self.assertNotIn("Authorization", backend.requests[-1].headers)
        result.objects[0]["attributeValue"] = "changed"
        self.assertEqual(list(artifact.objects), original)

    def test_empty_ldap_list_is_valid_not_a_fallback_for_malformed_data(self) -> None:
        client, _, _ = self.open_client("vision", self.response([]))
        self.assertEqual(client.list_ldap_permissions().objects, ())

    def test_unknown_versions_products_and_cross_product_capabilities_are_rejected(self) -> None:
        for product, version, operation in (
            ("vision", "1.0", self.c.ReadCapability.LDAP_PERMISSIONS),
            ("cyber-controller", "2.0", self.c.ReadCapability.PHYSICAL_TREE),
            ("vision", "0.0-test-extra", self.c.ReadCapability.LDAP_PERMISSIONS),
            ("unknown-sensitive-marker", "0.0-test", self.c.ReadCapability.PHYSICAL_TREE),
            ("vision", "0.0-test", self.c.ReadCapability.PHYSICAL_TREE),
            ("cyber-controller", "0.0-test", self.c.ReadCapability.LDAP_PERMISSIONS),
            ("vision", "0.0-test", "scheduler"),
            ("cyber-controller", "0.0-test", "arbitrary-tree"),
        ):
            with self.subTest(product=product, version=version, operation=operation):
                with self.assertRaises(self.c.ProductClientError) as caught:
                    self.c.require_capability(product, version, operation, mock_only=True)
                self.assertEqual(caught.exception.category, self.c.ClientErrorCategory.UNSUPPORTED_CAPABILITY)
                self.assertNotIn("sensitive-marker", str(caught.exception))
        manager = Mock()
        for client_type in (self.p.VisionClient, self.p.CyberControllerClient):
            with self.assertRaises(self.c.ProductClientError):
                client_type(manager, self.a.SessionRole.SOURCE, "1.0")
        manager.snapshot.assert_not_called()
        manager.request.assert_not_called()

    def test_clients_reject_product_and_version_session_mismatches(self) -> None:
        _, manager, backend = self.open_client("vision")
        with self.assertRaises(self.c.ProductClientError) as caught:
            self.p.CyberControllerClient(manager, self.a.SessionRole.SOURCE, "0.0-test")
        self.assertEqual(caught.exception.category, self.c.ClientErrorCategory.SESSION_MISMATCH)
        self.assertEqual(len(backend.requests), 1)
        with self.assertRaises(self.c.ProductClientError) as caught:
            self.open_client("vision", version="9.9-test")
        self.assertEqual(caught.exception.category, self.c.ClientErrorCategory.SESSION_MISMATCH)

    def test_session_binding_is_rechecked_before_each_read(self) -> None:
        client, manager, backend = self.open_client("vision")
        manager.close(self.a.SessionRole.SOURCE)
        replacement = self.mock_backend(self.response({"status": "ok"}))
        manager._factory = lambda: replacement
        manager.initialize(
            self.a.AuthenticationRequest(
                self.a.SessionRole.SOURCE, "cyber-controller", "0.0-test",
                self.a.CredentialReference("synthetic/source"),
            ),
            self.t.TransportConfig(base_url="https://source.invalid", connect_timeout=2, read_timeout=4),
        )
        manager.authenticate(self.a.SessionRole.SOURCE)
        with self.assertRaises(self.c.ProductClientError):
            client.list_ldap_permissions()
        self.assertEqual(backend.close_calls, 1)
        self.assertEqual(len(replacement.requests), 1)

    def test_malformed_tree_shapes_include_nested_nodes_and_depth_limit(self) -> None:
        deep = self.tree()
        for _ in range(65):
            deep = {"meIdentifier": {"managedElementID": "nested"}, "children": [deep]}
        for payload in (
            [], None, {}, {"children": [], "meIdentifier": None},
            {"children": {}, "meIdentifier": {"managedElementID": "root"}},
            {"children": [], "meIdentifier": {"managedElementID": 3}},
            {"children": [], "meIdentifier": {"managedElementID": " "}},
            {"children": ["sensitive-payload"], "meIdentifier": {"managedElementID": "root"}},
            deep,
        ):
            with self.subTest(shape=type(payload).__name__):
                client, _, backend = self.open_client("cyber-controller", self.response(payload))
                with self.assertRaises(self.c.ProductClientError) as caught:
                    client.export_physical_tree()
                self.assertEqual(caught.exception.category, self.c.ClientErrorCategory.MALFORMED_RESPONSE)
                self.assertNotIn("sensitive-payload", str(caught.exception))
                self.assertEqual(len(backend.requests), 2)

    def test_malformed_ldap_shapes_are_not_treated_as_empty_lists(self) -> None:
        for payload in ({}, None, [None], [1], ["sensitive-payload"]):
            with self.subTest(payload=payload):
                client, _, backend = self.open_client("vision", self.response(payload))
                with self.assertRaises(self.c.ProductClientError) as caught:
                    client.list_ldap_permissions()
                self.assertEqual(caught.exception.category, self.c.ClientErrorCategory.MALFORMED_RESPONSE)
                self.assertEqual(len(backend.requests), 2)

    def test_invalid_json_uses_sanitized_transport_errors_without_retry(self) -> None:
        for body in (
            b"sensitive-response", b"\xff", b'[{"id":1,"id":2}]', b"[NaN]",
        ):
            with self.subTest(body=body):
                client, _, backend = self.open_client("vision", self.t.HttpResponse(200, body))
                with self.assertRaises(self.t.TransportError) as caught:
                    client.list_ldap_permissions()
                self.assertEqual(caught.exception.category, self.t.ErrorCategory.MALFORMED_RESPONSE)
                self.assertEqual(caught.exception.attempts, 1)
                self.assertEqual(len(backend.requests), 2)
                self.assertNotIn("sensitive-response", "".join(traceback.format_exception(caught.exception)))

    def test_http_errors_do_not_renew_and_401_expires_the_session(self) -> None:
        for status in (401, 403, 500):
            with self.subTest(status=status):
                client, manager, backend = self.open_client("vision", self.t.HttpResponse(status, b"secret-body"))
                error_type = self.a.AuthenticationError if status == 401 else self.t.TransportError
                with self.assertRaises(error_type):
                    client.list_ldap_permissions()
                if status == 401:
                    self.assertEqual(manager.snapshot(self.a.SessionRole.SOURCE).state, self.a.SessionState.EXPIRED)
                    with self.assertRaises(self.a.AuthenticationError):
                        client.list_ldap_permissions()
                else:
                    self.assertTrue(manager.is_authenticated(self.a.SessionRole.SOURCE))
                self.assertEqual(len(backend.requests), 2)
                self.assertEqual([item.method for item in backend.requests], [self.t.HttpMethod.POST, self.t.HttpMethod.GET])

    def test_local_expiration_blocks_read_before_backend_dispatch(self) -> None:
        client, manager, backend = self.open_client("cyber-controller", lifetime=5)
        self.clock.return_value = 105.0
        with self.assertRaises(self.a.AuthenticationError) as caught:
            client.export_organization_tree()
        self.assertEqual(caught.exception.failure.category, self.a.AuthenticationFailureCategory.EXPIRED)
        self.assertEqual(manager.snapshot(self.a.SessionRole.SOURCE).state, self.a.SessionState.EXPIRED)
        self.assertEqual(len(backend.requests), 1)

    def test_client_401_does_not_expire_or_reuse_destination_session(self) -> None:
        source = self.mock_backend(self.response({"status": "ok"}), self.t.HttpResponse(401))
        destination = self.mock_backend(self.response({"status": "ok"}), self.response([]))
        manager = self.s.SessionManager(Mock(side_effect=[source, destination]), self.resolver)
        self.addCleanup(manager.close_all)
        for role, product in (
            (self.a.SessionRole.SOURCE, "cyber-controller"),
            (self.a.SessionRole.DESTINATION, "vision"),
        ):
            manager.initialize(
                self.a.AuthenticationRequest(
                    role, product, "0.0-test", self.a.CredentialReference(f"synthetic/{role.value}"),
                ),
                self.t.TransportConfig(
                    base_url=f"https://{role.value}.invalid", connect_timeout=2, read_timeout=4,
                ),
            )
            manager.authenticate(role)
        source_client = self.p.CyberControllerClient(manager, self.a.SessionRole.SOURCE, "0.0-test")
        destination_client = self.p.VisionClient(manager, self.a.SessionRole.DESTINATION, "0.0-test")
        with self.assertRaises(self.a.AuthenticationError):
            source_client.export_physical_tree()
        self.assertEqual(manager.snapshot(self.a.SessionRole.SOURCE).state, self.a.SessionState.EXPIRED)
        self.assertTrue(manager.is_authenticated(self.a.SessionRole.DESTINATION))
        self.assertEqual(destination_client.list_ldap_permissions().objects, ())
        self.assertEqual(len(source.requests), 2)
        self.assertEqual(len(destination.requests), 2)
        self.assertNotIn("Authorization", destination.requests[-1].headers)
        manager.close_all()
        self.assertEqual((source.close_calls, destination.close_calls), (1, 1))

    def test_read_representations_hide_payload_and_artifacts_reject_raw_secrets(self) -> None:
        payload = [{"nested": {"sessionToken": "sensitive-token-marker"}}]
        client, _, _ = self.open_client("vision", self.response(payload))
        result = client.list_ldap_permissions()
        self.assertNotIn("sensitive-token-marker", repr(result))
        with self.assertRaises(self.contracts.ContractValidationError) as caught:
            result.to_artifact(exported_at="2026-11-17T00:00:00Z")
        self.assertEqual(caught.exception.result.issues[0].code, "secret_value_not_allowed")
        self.assertNotIn("sensitive-token-marker", "".join(traceback.format_exception(caught.exception)))

    def test_nonfinite_json_numbers_cannot_enter_artifacts(self) -> None:
        client, _, _ = self.open_client("vision", self.t.HttpResponse(200, b'[{"value":1e999}]'))
        result = client.list_ldap_permissions()
        with self.assertRaises(self.contracts.ContractValidationError) as caught:
            result.to_artifact(exported_at="2026-11-17T00:00:00Z")
        self.assertEqual(caught.exception.result.issues[0].code, "invalid_value")
