import base64
import copy
import importlib
import io
import json
import traceback
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import asdict
from unittest.mock import Mock, patch

from test_authentication import FakeOwnedBackend
from test_product_clients import ProductClientTestSupport


class MockedIntegrationTests(ProductClientTestSupport):
    def setUp(self) -> None:
        super().setUp()
        self.w = importlib.import_module("cc_vision_import.mock_workflow")
        self.plans = importlib.import_module("cc_vision_import.plans")
        self.artifacts = importlib.import_module("cc_vision_import.artifacts")
        self.configure(self.c.ReadCapability.PHYSICAL_TREE)

    def configure(self, operation) -> None:
        self.operation = operation
        source_product = "vision" if operation == self.c.ReadCapability.LDAP_PERMISSIONS else "cyber-controller"
        destination_product = "cyber-controller" if source_product == "vision" else "vision"
        self.source = {
            "role": "source", "name": "synthetic-source", "product": source_product,
            "version": "0.0-test", "base_url": "https://source.invalid",
            "secret_ref": "synthetic/source",
        }
        self.destination = {
            "role": "destination", "name": "synthetic-destination", "product": destination_product,
            "version": "0.0-test", "base_url": "https://destination.invalid",
            "secret_ref": "synthetic/destination",
        }
        self.payload = [{"attributeValue": "synthetic-group"}] if source_product == "vision" else self.tree()
        self.source_backend = self.mock_backend(
            self.t.HttpResponse(200, b'{"status":"ok"}', {"Set-Cookie": "synthetic-source-cookie"}),
            self.response(self.payload),
        )
        self.destination_backend = self.mock_backend(
            self.t.HttpResponse(200, b'{"status":"ok"}', {"Set-Cookie": "synthetic-destination-cookie"}),
        )
        self.factory = Mock(side_effect=[self.source_backend, self.destination_backend])
        self.request = {
            "destination": {
                "controller_id": "explicit-synthetic-destination",
                "product": destination_product, "version": "0.0-test",
                "base_url": self.destination["base_url"],
            },
            "mappings": [{
                "mapping_id": "map-one", "domain": operation.value, "source_index": 0,
                "source": {
                    "namespace": "explicit-source-scope", "object_type": "synthetic-object",
                    "object_id": "explicit-source-identity",
                },
                "source_context": {"product": source_product, "version": "0.0-test"},
                "destination_context": {"product": destination_product, "version": "0.0-test"},
                "state": "missing", "destination": None, "candidates": [],
                "parent_mapping": None, "depends_on": [],
            }],
            "actions": [{
                "action_id": "action-one", "mapping_id": "map-one",
                "comparison": "missing", "semantics_known": True, "depends_on": [],
            }],
        }

    def run_workflow(self):
        return self.w.build_mock_plan(
            self.source, self.destination, operation=self.operation,
            planning_request=self.request, exported_at="2026-11-17T00:00:00Z",
            backend_factory=self.factory, resolver=self.resolver,
            connect_timeout=2, read_timeout=4,
        )

    def assert_closed(self) -> None:
        self.assertEqual(self.source_backend.close_calls, 1)
        self.assertEqual(self.destination_backend.close_calls, 1)
        self.assertEqual(self.source_backend.cookies, {})
        self.assertEqual(self.destination_backend.cookies, {})

    def test_all_three_reads_connect_profiles_sessions_artifact_mapping_and_plan(self) -> None:
        for operation in self.c.ReadCapability:
            with self.subTest(operation=operation):
                self.configure(operation)
                original = copy.deepcopy((self.source, self.destination, self.request))
                result = self.run_workflow()
                self.assertEqual(result.artifact.schema_version, 1)
                self.assertEqual(result.artifact.domain, operation.value)
                self.assertEqual(self.artifacts.validate_artifact(result.artifact.to_dict()).status, "valid")
                self.assertEqual(
                    list(result.artifact.objects),
                    self.payload if isinstance(self.payload, list) else [self.payload],
                )
                self.assertEqual(result.plan.stage, "offline-candidate")
                self.assertEqual(result.plan.actions[0].kind, "create")
                self.assertEqual(result.plan.mappings[0].source.object_id, "explicit-source-identity")
                self.assertIsNone(result.plan.mappings[0].destination)
                self.assertEqual(result.plan.source_artifact.object_count, 1)
                self.assertEqual(
                    self.plans.verify_plan(
                        json.loads(result.plan.to_json()), result.artifact.to_json().encode("utf-8"),
                        self.request["destination"], result.plan.integrity_sha256,
                    ),
                    result.plan,
                )
                self.assertEqual((self.source, self.destination, self.request), original)
                self.assertEqual(result.summary().plan_status, "valid")
                self.assertFalse(result.summary().compatibility_verified)
                self.assertTrue(result.summary().mock_only)
                self.assertEqual(result.summary().writes_executed, 0)
                self.assert_closed()
                self.assertEqual(self.factory.call_count, 2)
                self.assertEqual([item.value for (item,), _ in self.resolver.resolve.call_args_list[-2:]], [
                    "synthetic/source", "synthetic/destination",
                ])
                for backend, reference in (
                    (self.source_backend, "synthetic/source"),
                    (self.destination_backend, "synthetic/destination"),
                ):
                    login = json.loads(backend.requests[0].body)
                    credentials = self.credentials[reference]
                    self.assertEqual(login, {"username": credentials.username, "password": credentials.password})
                    self.assertEqual(backend.seen_cookies[0], {})
                    self.assertEqual(backend.requests[0].method, self.t.HttpMethod.POST)
                self.assertEqual([item.method for item in self.source_backend.requests[1:]], [self.t.HttpMethod.GET])
                self.assertEqual(
                    self.source_backend.seen_cookies[1],
                    {"synthetic-cookie": "synthetic-source-cookie"},
                )
                self.assertEqual(len(self.destination_backend.requests), 1)

    def test_missing_credential_references_fail_before_session_creation(self) -> None:
        for role in ("source", "destination"):
            with self.subTest(role=role):
                self.configure(self.c.ReadCapability.PHYSICAL_TREE)
                profile = self.source if role == "source" else self.destination
                del profile["secret_ref"]
                with self.assertRaises(self.contracts.ContractValidationError) as caught:
                    self.run_workflow()
                self.assertEqual(caught.exception.result.issues[0].code, "missing_reference")
                self.factory.assert_not_called()
                self.resolver.resolve.assert_not_called()

    def test_shared_backend_is_rejected_and_closed_only_by_its_source_owner(self) -> None:
        self.factory.side_effect = [self.source_backend, self.source_backend]
        with self.assertRaises(self.a.AuthenticationError) as caught:
            self.run_workflow()
        self.assertEqual(caught.exception.failure.category, self.a.AuthenticationFailureCategory.OWNERSHIP)
        self.assertEqual(self.source_backend.close_calls, 1)
        self.assertEqual(len(self.source_backend.requests), 1)
        self.assertEqual(self.destination_backend.close_calls, 0)

    def test_workflow_requires_explicit_mock_backends_before_authentication(self) -> None:
        for rejected_role in ("source", "destination"):
            for close_failure in (False, True):
                with self.subTest(role=rejected_role, close_failure=close_failure):
                    self.configure(self.c.ReadCapability.PHYSICAL_TREE)
                    self.resolver.resolve.reset_mock()
                    rejected = FakeOwnedBackend()
                    rejected.is_mock = True
                    rejected.close_failure = close_failure
                    self.factory.side_effect = (
                        [rejected, self.destination_backend] if rejected_role == "source"
                        else [self.source_backend, rejected]
                    )
                    with self.assertRaises(self.a.AuthenticationError) as caught:
                        self.run_workflow()
                    self.assertEqual(caught.exception.failure.category, self.a.AuthenticationFailureCategory.INITIALIZATION)
                    self.assertEqual(rejected.requests, [])
                    self.assertEqual(rejected.close_calls, 1)
                    self.assertNotIn("sensitive-close-marker", "".join(traceback.format_exception(caught.exception)))
                    if rejected_role == "source":
                        self.resolver.resolve.assert_not_called()
                        self.assertEqual(self.factory.call_count, 1)
                    else:
                        self.assertEqual(self.source_backend.close_calls, 1)
                        self.assertEqual(len(self.source_backend.requests), 1)
                        self.assertEqual(self.resolver.resolve.call_count, 1)

    def test_authentication_failure_closes_every_initialized_session_without_replay(self) -> None:
        for failing_role in ("source", "destination"):
            with self.subTest(role=failing_role):
                self.configure(self.c.ReadCapability.PHYSICAL_TREE)
                rejected = self.mock_backend(self.t.HttpResponse(401, b"sensitive-login-body"))
                if failing_role == "source":
                    self.source_backend = rejected
                else:
                    self.destination_backend = rejected
                self.factory.side_effect = [self.source_backend, self.destination_backend]
                with self.assertRaises(self.a.AuthenticationError) as caught:
                    self.run_workflow()
                self.assertEqual(caught.exception.failure.category, self.a.AuthenticationFailureCategory.HTTP_REJECTION)
                self.assertEqual(rejected.close_calls, 1)
                self.assertEqual(len(rejected.requests), 1)
                if failing_role == "source":
                    self.assertEqual(self.factory.call_count, 1)
                    self.assertEqual(self.destination_backend.close_calls, 0)
                else:
                    self.assert_closed()
                    self.assertEqual(len(self.source_backend.requests), 1)

    def test_vision_application_login_failure_is_not_http_success(self) -> None:
        self.configure(self.c.ReadCapability.LDAP_PERMISSIONS)
        self.source_backend = self.mock_backend(self.response({"status": "failed", "token": "secret-marker"}))
        self.factory.side_effect = [self.source_backend, self.destination_backend]
        with self.assertRaises(self.a.AuthenticationError) as caught:
            self.run_workflow()
        self.assertEqual(caught.exception.failure.category, self.a.AuthenticationFailureCategory.APPLICATION_REJECTION)
        self.assertEqual(self.source_backend.close_calls, 1)
        self.assertEqual(self.factory.call_count, 1)

    def test_expired_read_session_fails_and_cleans_both_without_renewal(self) -> None:
        self.source_backend = self.mock_backend(
            self.response({"status": "ok"}), self.t.HttpResponse(401, b"expired-secret"),
        )
        self.factory.side_effect = [self.source_backend, self.destination_backend]
        with self.assertRaises(self.a.AuthenticationError) as caught:
            self.run_workflow()
        self.assertEqual(caught.exception.failure.category, self.a.AuthenticationFailureCategory.HTTP_REJECTION)
        self.assertEqual(len(self.source_backend.requests), 2)
        self.assertEqual(len(self.destination_backend.requests), 1)
        self.assert_closed()

    def test_unsupported_capabilities_and_versions_fail_before_factory_or_resolver(self) -> None:
        for change in ("source-version", "destination-version", "cross-product", "scheduler"):
            with self.subTest(change=change):
                self.configure(self.c.ReadCapability.PHYSICAL_TREE)
                if change == "source-version":
                    self.source["version"] = "9.9"
                elif change == "destination-version":
                    self.destination["version"] = "2.0"
                elif change == "cross-product":
                    self.source["product"] = "vision"
                else:
                    self.operation = "scheduler"
                with self.assertRaises(self.c.ProductClientError):
                    self.run_workflow()
                self.factory.assert_not_called()
                self.resolver.resolve.assert_not_called()

    def test_malformed_api_response_and_secret_fields_cleanup_after_failure(self) -> None:
        for payload, expected_error in (
            ({"unexpected": "sensitive-response"}, self.c.ProductClientError),
            ({**self.tree(), "password": "sensitive-response"}, self.contracts.ContractValidationError),
        ):
            with self.subTest(error=expected_error):
                self.configure(self.c.ReadCapability.PHYSICAL_TREE)
                self.source_backend = self.mock_backend(self.response({"status": "ok"}), self.response(payload))
                self.factory.side_effect = [self.source_backend, self.destination_backend]
                with self.assertRaises(expected_error) as caught:
                    self.run_workflow()
                self.assertNotIn("sensitive-response", "".join(traceback.format_exception(caught.exception)))
                self.assert_closed()

    def test_missing_mapping_records_fail_and_unresolved_destination_blocks_plan(self) -> None:
        self.request["mappings"] = []
        with self.assertRaises(self.contracts.ContractValidationError) as caught:
            self.run_workflow()
        self.assertEqual(caught.exception.result.issues[0].code, "missing_mapping")
        self.assert_closed()
        self.configure(self.c.ReadCapability.PHYSICAL_TREE)
        self.request["mappings"][0]["state"] = "unresolved"
        result = self.run_workflow()
        self.assertEqual(result.summary().plan_status, "invalid")
        self.assertEqual(result.summary().blocked_actions, 1)
        self.assertIn("mapping_unresolved", result.plan.actions[0].issue_codes)
        self.assertEqual(result.plan.actions[0].changes, ())
        self.assert_closed()

    def test_ambiguous_identity_remains_blocked_without_destination_inference(self) -> None:
        self.request["mappings"][0].update(
            state="ambiguous",
            candidates=[
                {"namespace": "scope-a", "object_type": "synthetic-object", "object_id": "same"},
                {"namespace": "scope-b", "object_type": "synthetic-object", "object_id": "same"},
            ],
        )
        result = self.run_workflow()
        self.assertEqual(result.summary().blocked_actions, 1)
        self.assertIn("mapping_ambiguous", result.plan.actions[0].issue_codes)
        self.assertIsNone(result.plan.mappings[0].destination)
        self.assertEqual(result.summary().writes_executed, 0)
        self.assert_closed()

    def test_plan_destination_must_match_the_authenticated_profile(self) -> None:
        self.request["destination"]["base_url"] = "https://another.invalid"
        with self.assertRaises(self.contracts.ContractValidationError) as caught:
            self.run_workflow()
        self.assertEqual(caught.exception.result.issues[0].code, "context_mismatch")
        self.assert_closed()

    def test_invalid_url_parser_context_does_not_expose_supplied_port_text(self) -> None:
        marker = "sensitive-invalid-port-marker"
        for location in ("source", "destination", "planning-request"):
            with self.subTest(location=location):
                self.configure(self.c.ReadCapability.PHYSICAL_TREE)
                target = (
                    self.source if location == "source" else self.destination
                    if location == "destination" else self.request["destination"]
                )
                target["base_url"] = f"https://synthetic.invalid:{marker}"
                with self.assertRaises(self.contracts.ContractValidationError) as caught:
                    self.run_workflow()
                text = "".join(traceback.format_exception(caught.exception))
                self.assertNotIn(marker, text)
                self.assertIsNone(caught.exception.__context__)
                if location == "planning-request":
                    self.assert_closed()
                else:
                    self.factory.assert_not_called()

    def test_summary_representations_and_output_do_not_expose_credentials_or_identifiers(self) -> None:
        stdout, stderr = io.StringIO(), io.StringIO()
        with (
            redirect_stdout(stdout), redirect_stderr(stderr),
            patch("logging.Logger._log") as log,
        ):
            result = self.run_workflow()
        log.assert_not_called()
        self.assertEqual(stdout.getvalue(), "")
        self.assertEqual(stderr.getvalue(), "")
        text = repr(result) + repr(result.summary()) + json.dumps(asdict(result.summary()))
        for reference, credentials in self.credentials.items():
            basic = base64.b64encode(f"{credentials.username}:{credentials.password}".encode("latin-1")).decode("ascii")
            for value in (reference, credentials.username, credentials.password, basic):
                self.assertNotIn(value, text)
        for value in (
            "source.invalid", "destination.invalid", "explicit-source-identity",
            "explicit-synthetic-destination", "synthetic-source-cookie", "synthetic-destination-cookie",
        ):
            self.assertNotIn(value, text)
        self.assert_closed()

    def test_cleanup_failure_is_sanitized_and_does_not_skip_other_owner(self) -> None:
        self.source_backend.close_failure = True
        with self.assertRaises(self.a.AuthenticationError) as caught:
            self.run_workflow()
        self.assertEqual(caught.exception.failure.category, self.a.AuthenticationFailureCategory.CLEANUP)
        self.assertEqual(self.source_backend.close_calls, 1)
        self.assertEqual(self.destination_backend.close_calls, 1)
        self.assertNotIn("sensitive-close-marker", "".join(traceback.format_exception(caught.exception)))

    def test_encoded_basic_in_backend_failure_never_reaches_workflow_diagnostics(self) -> None:
        credentials = self.credentials["synthetic/source"]
        encoded = base64.b64encode(f"{credentials.username}:{credentials.password}".encode("latin-1")).decode("ascii")
        self.source_backend = self.mock_backend(
            self.response({"status": "ok"}), RuntimeError(f"Authorization: Basic {encoded}"),
        )
        self.factory.side_effect = [self.source_backend, self.destination_backend]
        with self.assertRaises(self.t.TransportError) as caught:
            self.run_workflow()
        text = "".join(traceback.format_exception(caught.exception)) + repr(vars(caught.exception))
        for value in (credentials.username, credentials.password, encoded):
            self.assertNotIn(value, text)
        self.assertIsNone(caught.exception.__context__)
        self.assert_closed()
