import base64
import importlib
import json
import traceback
from dataclasses import asdict
from unittest.mock import Mock
from unittest.mock import patch

from offline_support import OfflineTestCase
from test_transport import FakeSession


class FakeOwnedBackend(FakeSession):
    def __init__(self, *outcomes: object) -> None:
        super().__init__(*outcomes)
        self.close_calls = 0
        self.close_failure = False
        self.cookies = {}
        self.seen_cookies = []

    def send(self, request):
        self.seen_cookies.append(dict(self.cookies))
        response = super().send(request)
        cookie = response.headers.get("Set-Cookie")
        if cookie is not None:
            self.cookies["synthetic-cookie"] = cookie
        return response

    def close(self) -> None:
        self.close_calls += 1
        if self.close_failure:
            raise RuntimeError("sensitive-close-marker")
        self.cookies.clear()


class AuthenticationTests(OfflineTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.a = importlib.import_module("cc_vision_import.authentication")
        self.s = importlib.import_module("cc_vision_import.sessions")
        self.t = importlib.import_module("cc_vision_import.transport")
        self.contracts = importlib.import_module("cc_vision_import.contracts")
        self.username = 'synthetic-user-"\\'
        self.password = 'synthetic-password-"\\:'
        self.credentials = self.a.ResolvedCredentials(self.username, self.password)
        self.reference = self.a.CredentialReference("synthetic/source")
        self.resolver = Mock()
        self.resolver.resolve.return_value = self.credentials
        self.clock = Mock(return_value=100.0)

    def auth_request(self, product="vision", role=None, lifetime=None):
        return self.a.AuthenticationRequest(
            self.a.SessionRole.SOURCE if role is None else role, product, "0.0-test",
            self.reference, self.a.SessionExpiration(lifetime),
        )

    def config(self, role=None):
        host = "source.invalid" if role != self.a.SessionRole.DESTINATION else "destination.invalid"
        return self.t.TransportConfig(
            base_url=f"https://{host}", connect_timeout=2, read_timeout=4, read_retries=3,
        )

    def manager(self, *outcomes, request=None):
        backend = FakeOwnedBackend(*outcomes)
        manager = self.s.SessionManager(lambda: backend, self.resolver, clock=self.clock)
        self.addCleanup(manager.close_all)
        manager.initialize(self.auth_request() if request is None else request, self.config())
        return manager, backend

    def ok(self, *, cookie="synthetic-cookie-value"):
        return self.t.HttpResponse(200, b'{"status":"ok"}', {"Set-Cookie": cookie})

    def assert_auth_failure(self, manager, category):
        with self.assertRaises(self.a.AuthenticationError) as caught:
            manager.authenticate(self.a.SessionRole.SOURCE)
        self.assertEqual(caught.exception.failure.category, category)
        self.assertEqual(manager.snapshot(self.a.SessionRole.SOURCE).state, self.a.SessionState.FAILED)
        self.assertFalse(manager.is_authenticated(self.a.SessionRole.SOURCE))
        return caught.exception

    def test_vision_authentication_uses_json_status_without_basic(self) -> None:
        manager, backend = self.manager(self.ok())
        role = self.a.SessionRole.SOURCE
        self.assertEqual(manager.snapshot(role).state, self.a.SessionState.INITIALIZED)
        outcome = manager.authenticate(role)
        self.assertTrue(outcome.authenticated)
        self.assertFalse(outcome.compatibility_verified)
        self.assertEqual(outcome.evidence, self.a.LoginEvidence.APPLICATION_STATUS_OK)
        self.assertTrue(manager.is_authenticated(role))
        self.resolver.resolve.assert_called_once_with(self.reference)
        request = backend.requests[0]
        self.assertEqual(request.method, self.t.HttpMethod.POST)
        self.assertEqual(request.url, "https://source.invalid/mgmt/system/user/login")
        self.assertEqual(json.loads(request.body), {"username": self.username, "password": self.password})
        self.assertNotIn("Authorization", request.headers)
        self.assertEqual(request.headers["X-Requested-With"], "XMLHttpRequest")

    def test_controller_basic_plus_json_and_http_only_evidence_are_distinct(self) -> None:
        manager, backend = self.manager(
            self.t.HttpResponse(200, b"not-json"), self.t.HttpResponse(200),
            request=self.auth_request("cyber-controller"),
        )
        role = self.a.SessionRole.SOURCE
        outcome = manager.authenticate(role)
        self.assertEqual(outcome.evidence, self.a.LoginEvidence.HTTP_200_ONLY)
        self.assertFalse(outcome.compatibility_verified)
        manager.request(role, self.t.HttpMethod.GET, ("synthetic",))
        for request in backend.requests:
            scheme, encoded = request.headers["Authorization"].split()
            self.assertEqual(scheme, "Basic")
            self.assertEqual(base64.b64decode(encoded).decode("latin-1"), f"{self.username}:{self.password}")
        self.assertEqual(json.loads(backend.requests[0].body)["password"], self.password)

    def test_controller_does_not_invent_application_status_schema(self) -> None:
        manager, _ = self.manager(
            self.t.HttpResponse(200, b'{"status":"not-ok"}'),
            request=self.auth_request("cyber-controller"),
        )
        outcome = manager.authenticate(self.a.SessionRole.SOURCE)
        self.assertEqual(outcome.evidence, self.a.LoginEvidence.HTTP_200_ONLY)
        self.assertFalse(outcome.compatibility_verified)

    def test_controller_does_not_expand_success_statuses(self) -> None:
        manager, backend = self.manager(
            self.t.HttpResponse(201, b'{"status":"ok"}'),
            request=self.auth_request("cyber-controller"),
        )
        self.assert_auth_failure(manager, self.a.AuthenticationFailureCategory.MALFORMED_RESPONSE)
        self.assertEqual(len(backend.requests), 1)

    def test_http_authentication_and_authorization_rejection_never_renew(self) -> None:
        for status, category in (
            (401, self.a.AuthenticationFailureCategory.HTTP_REJECTION),
            (403, self.a.AuthenticationFailureCategory.AUTHORIZATION),
        ):
            for product in ("vision", "cyber-controller"):
                with self.subTest(status=status, product=product):
                    manager, backend = self.manager(
                        self.t.HttpResponse(status, b"sensitive-response-marker"),
                        request=self.auth_request(product),
                    )
                    error = self.assert_auth_failure(manager, category)
                    self.assertEqual(error.failure.status, status)
                    self.assertEqual(len(backend.requests), 1)
                    with self.assertRaises(self.a.AuthenticationError):
                        manager.authenticate(self.a.SessionRole.SOURCE)
                    self.assertEqual(len(backend.requests), 1)

    def test_application_login_rejection_is_not_http_success(self) -> None:
        manager, backend = self.manager(self.t.HttpResponse(200, b'{"status":"error","message":"sensitive-marker"}'))
        error = self.assert_auth_failure(manager, self.a.AuthenticationFailureCategory.APPLICATION_REJECTION)
        self.assertNotIn("sensitive-marker", str(error) + repr(error.failure))
        self.assertEqual(len(backend.requests), 1)

    def test_malformed_vision_login_responses_fail_without_raw_content(self) -> None:
        for body in (
            b"", b"sensitive-marker", b"\xff", b"[]", b"null", b"{}", b'{"status":null}',
            b'{"status":1}', b'{"status":"ok","status":"error"}', b'{"status":NaN}',
        ):
            with self.subTest(body_kind="malformed"):
                manager, backend = self.manager(self.t.HttpResponse(200, body))
                error = self.assert_auth_failure(manager, self.a.AuthenticationFailureCategory.MALFORMED_RESPONSE)
                self.assertNotIn("sensitive-marker", str(error) + repr(error.failure))
                self.assertEqual(len(backend.requests), 1)

    def test_login_transport_failures_keep_uncertain_reason_without_retry(self) -> None:
        for reason in (
            self.t.ErrorCategory.CONNECTION, self.t.ErrorCategory.TIMEOUT, self.t.ErrorCategory.TLS,
        ):
            with self.subTest(reason=reason):
                manager, backend = self.manager(self.t.BackendFailure(reason))
                error = self.assert_auth_failure(manager, self.a.AuthenticationFailureCategory.TRANSPORT)
                self.assertEqual(error.failure.transport_category, self.t.ErrorCategory.INDETERMINATE_WRITE)
                self.assertEqual(error.failure.transport_reason, reason)
                self.assertIsNone(error.__context__)
                self.assertEqual(len(backend.requests), 1)

    def test_resolver_errors_and_invalid_results_fail_before_login(self) -> None:
        for result in (None, {}, "sensitive-marker", RuntimeError("sensitive-marker")):
            with self.subTest(result_kind=type(result).__name__):
                self.resolver.resolve.reset_mock(side_effect=True)
                if isinstance(result, Exception):
                    self.resolver.resolve.side_effect = result
                    expected = self.a.AuthenticationFailureCategory.SECRET_RESOLUTION
                else:
                    self.resolver.resolve.return_value = result
                    expected = self.a.AuthenticationFailureCategory.INVALID_CREDENTIALS
                manager, backend = self.manager()
                error = self.assert_auth_failure(manager, expected)
                self.assertIsNone(error.__context__)
                self.assertNotIn("sensitive-marker", "".join(traceback.format_exception(error)))
                self.assertEqual(backend.requests, [])

    def test_invalid_credential_values_are_not_echoed(self) -> None:
        for username, password in (("", "p"), ("u", ""), ("u\n", "sensitive-marker"), (None, "p")):
            with self.subTest(input_kind="invalid-credential"):
                with self.assertRaises(self.a.AuthenticationError) as caught:
                    self.a.ResolvedCredentials(username, password)
                self.assertNotIn("sensitive-marker", str(caught.exception))
        for username in ("not:basic", "non-latin-\u6d4b"):
            self.resolver.resolve.return_value = self.a.ResolvedCredentials(username, "synthetic-password")
            manager, backend = self.manager(request=self.auth_request("cyber-controller"))
            self.assert_auth_failure(manager, self.a.AuthenticationFailureCategory.INVALID_CREDENTIALS)
            self.assertEqual(backend.requests, [])

    def test_explicit_local_lifetime_expires_at_exact_deadline_without_dispatch(self) -> None:
        manager, backend = self.manager(self.ok(), request=self.auth_request(lifetime=10))
        role = self.a.SessionRole.SOURCE
        manager.authenticate(role)
        self.clock.return_value = 109.999
        self.assertTrue(manager.is_authenticated(role))
        self.clock.return_value = 110.0
        self.assertFalse(manager.is_authenticated(role))
        snapshot = manager.snapshot(role)
        self.assertEqual(snapshot.state, self.a.SessionState.EXPIRED)
        self.assertEqual(snapshot.expiration_reason, self.a.ExpirationReason.LOCAL_LIFETIME)
        with self.assertRaises(self.a.AuthenticationError) as caught:
            manager.request(role, self.t.HttpMethod.POST, ("synthetic",))
        self.assertEqual(caught.exception.failure.category, self.a.AuthenticationFailureCategory.EXPIRED)
        self.assertEqual(len(backend.requests), 1)

    def test_no_server_ttl_is_inferred_from_login_body(self) -> None:
        manager, backend = self.manager(self.t.HttpResponse(200, b'{"status":"ok","expires_in":1}'))
        manager.authenticate(self.a.SessionRole.SOURCE)
        self.clock.return_value = 100000000.0
        self.assertTrue(manager.is_authenticated(self.a.SessionRole.SOURCE))
        self.assertEqual(len(backend.requests), 1)

    def test_401_marks_expired_and_never_renews_or_replays_any_write(self) -> None:
        for method in tuple(self.t.HttpMethod)[1:]:
            with self.subTest(method=method):
                manager, backend = self.manager(self.ok(), self.t.HttpResponse(401))
                role = self.a.SessionRole.SOURCE
                manager.authenticate(role)
                with self.assertRaises(self.a.AuthenticationError) as caught:
                    manager.request(role, method, ("synthetic",), body=b"synthetic-payload")
                self.assertEqual(caught.exception.failure.category, self.a.AuthenticationFailureCategory.HTTP_REJECTION)
                self.assertEqual(manager.snapshot(role).state, self.a.SessionState.EXPIRED)
                self.assertEqual(manager.snapshot(role).expiration_reason, self.a.ExpirationReason.HTTP_REJECTION)
                self.assertEqual(len(backend.requests), 2)
                with self.assertRaises(self.a.AuthenticationError):
                    manager.request(role, method, ("synthetic",))
                self.assertEqual(len(backend.requests), 2)

    def test_uncertain_writes_keep_transport_errors_and_are_never_replayed(self) -> None:
        for method in tuple(self.t.HttpMethod)[1:]:
            with self.subTest(method=method):
                manager, backend = self.manager(
                    self.ok(), self.t.BackendFailure(self.t.ErrorCategory.TIMEOUT),
                )
                role = self.a.SessionRole.SOURCE
                manager.authenticate(role)
                with self.assertRaises(self.t.TransportError) as caught:
                    manager.request(role, method, ("synthetic",))
                self.assertEqual(caught.exception.category, self.t.ErrorCategory.INDETERMINATE_WRITE)
                self.assertEqual(len(backend.requests), 2)

    def test_403_does_not_guess_session_expiration(self) -> None:
        manager, backend = self.manager(self.ok(), self.t.HttpResponse(403))
        role = self.a.SessionRole.SOURCE
        manager.authenticate(role)
        with self.assertRaises(self.t.TransportError) as caught:
            manager.request(role, self.t.HttpMethod.GET, ("synthetic",))
        self.assertEqual(caught.exception.category, self.t.ErrorCategory.AUTHORIZATION)
        self.assertTrue(manager.is_authenticated(role))
        self.assertEqual(len(backend.requests), 2)

    def test_source_destination_own_separate_backends_cookies_and_references(self) -> None:
        source = FakeOwnedBackend(self.ok(cookie="synthetic-source-cookie"), self.t.HttpResponse(200))
        destination = FakeOwnedBackend(self.ok(cookie="synthetic-destination-cookie"), self.t.HttpResponse(200))
        source_role, destination_role = self.a.SessionRole
        destination_ref = self.a.CredentialReference("synthetic/destination")
        destination_credentials = self.a.ResolvedCredentials("synthetic-destination-user", "synthetic-destination-password")
        secrets = {self.reference: self.credentials, destination_ref: destination_credentials}
        self.resolver.resolve.side_effect = secrets.__getitem__
        factory = Mock(side_effect=[source, destination])
        manager = self.s.SessionManager(factory, self.resolver, clock=self.clock)
        self.addCleanup(manager.close_all)
        manager.initialize(self.auth_request(), self.config())
        manager.initialize(self.a.AuthenticationRequest(
            destination_role, "cyber-controller", "0.0-test", destination_ref,
        ), self.config(destination_role))
        for role in (source_role, destination_role):
            manager.authenticate(role)
            manager.request(role, self.t.HttpMethod.GET, ("synthetic",))
        self.assertEqual(source.seen_cookies[1], {"synthetic-cookie": "synthetic-source-cookie"})
        self.assertEqual(destination.seen_cookies[1], {"synthetic-cookie": "synthetic-destination-cookie"})
        self.assertNotIn("Authorization", source.requests[1].headers)
        destination_basic = destination.requests[1].headers["Authorization"].split()[1]
        self.assertIn(b"synthetic-destination-user:", base64.b64decode(destination_basic))
        manager.close(source_role)
        self.assertTrue(manager.is_authenticated(destination_role))
        self.assertEqual(destination.close_calls, 0)
        self.assertEqual(len(source.requests), 2)

    def test_shared_backend_and_duplicate_role_are_rejected_without_closing_other_owner(self) -> None:
        manager, backend = self.manager(self.ok())
        for request in (self.auth_request(), self.auth_request(role=self.a.SessionRole.DESTINATION)):
            with self.subTest(role=request.role):
                with self.assertRaises(self.a.AuthenticationError) as caught:
                    manager.initialize(request, self.config())
                self.assertEqual(caught.exception.failure.category, self.a.AuthenticationFailureCategory.OWNERSHIP)
        self.assertEqual(backend.close_calls, 0)
        self.assertEqual(backend.requests, [])

    def test_context_cleanup_is_local_idempotent_and_blocks_reuse(self) -> None:
        backend = FakeOwnedBackend(self.ok())
        role = self.a.SessionRole.SOURCE
        with self.s.SessionManager(lambda: backend, self.resolver) as manager:
            manager.initialize(self.auth_request(), self.config())
            manager.authenticate(role)
            self.assertTrue(backend.cookies)
        self.assertEqual(backend.close_calls, 1)
        self.assertEqual(backend.cookies, {})
        self.assertEqual(len(backend.requests), 1)
        self.assertEqual(manager.snapshot(role).state, self.a.SessionState.CLOSED)
        manager.close_all()
        self.assertEqual(backend.close_calls, 1)
        with self.assertRaises(self.a.AuthenticationError):
            manager.request(role, self.t.HttpMethod.POST, ("synthetic",))

    def test_context_cleanup_also_runs_after_login_failure(self) -> None:
        backend = FakeOwnedBackend(self.t.HttpResponse(401))
        with self.assertRaises(self.a.AuthenticationError):
            with self.s.SessionManager(lambda: backend, self.resolver) as manager:
                manager.initialize(self.auth_request(), self.config())
                manager.authenticate(self.a.SessionRole.SOURCE)
        self.assertEqual(backend.close_calls, 1)

    def test_cleanup_error_does_not_format_sensitive_body_exception(self) -> None:
        backend = FakeOwnedBackend()
        backend.close_failure = True
        manager = self.s.SessionManager(lambda: backend, self.resolver)
        with self.assertRaises(self.a.AuthenticationError) as caught:
            with manager:
                manager.initialize(self.auth_request(), self.config())
                raise RuntimeError("sensitive-context-marker")
        self.assertNotIn("sensitive-context-marker", "".join(traceback.format_exception(caught.exception)))
        self.assertTrue(caught.exception.__suppress_context__)
        backend.close_failure = False
        manager.close_all()

    def test_cleanup_failure_is_explicit_and_other_role_is_still_closed(self) -> None:
        source = FakeOwnedBackend()
        destination = FakeOwnedBackend()
        source.close_failure = True
        manager = self.s.SessionManager(Mock(side_effect=[source, destination]), self.resolver)
        manager.initialize(self.auth_request(), self.config())
        manager.initialize(self.auth_request(role=self.a.SessionRole.DESTINATION), self.config())
        with self.assertRaises(self.a.AuthenticationError) as caught:
            manager.close_all()
        self.assertNotIn("sensitive-close-marker", "".join(traceback.format_exception(caught.exception)))
        self.assertEqual(manager.snapshot(self.a.SessionRole.SOURCE).state, self.a.SessionState.CLEANUP_FAILED)
        self.assertEqual(destination.close_calls, 1)
        source.close_failure = False
        manager.close_all()
        self.assertEqual(source.close_calls, 2)
        self.assertEqual(destination.close_calls, 1)

    def test_closed_role_can_be_reinitialized_with_fresh_backend(self) -> None:
        first, second = FakeOwnedBackend(), FakeOwnedBackend(self.ok())
        manager = self.s.SessionManager(Mock(side_effect=[first, second]), self.resolver)
        self.addCleanup(manager.close_all)
        manager.initialize(self.auth_request(), self.config())
        manager.close(self.a.SessionRole.SOURCE)
        manager.initialize(self.auth_request(), self.config())
        manager.authenticate(self.a.SessionRole.SOURCE)
        self.assertEqual(first.requests, [])
        self.assertEqual(first.close_calls, 1)
        self.assertEqual(len(second.requests), 1)

    def test_authentication_headers_cannot_be_overridden_by_callers(self) -> None:
        manager, backend = self.manager(self.ok())
        role = self.a.SessionRole.SOURCE
        manager.authenticate(role)
        for headers in ({"authorization": "sensitive-marker"}, {"Cookie": "sensitive-marker"}, {"Proxy-Authorization": "x"}):
            with self.subTest(header_kind="authentication"):
                with self.assertRaises(self.a.AuthenticationError):
                    manager.request(role, self.t.HttpMethod.GET, (), headers=headers)
        self.assertEqual(len(backend.requests), 1)

    def test_secrets_are_absent_from_representations_snapshots_and_failure_chains(self) -> None:
        marker = "sensitive-marker"
        self.credentials = self.a.ResolvedCredentials(marker, marker)
        self.resolver.resolve.return_value = self.credentials
        manager, backend = self.manager(
            self.t.HttpResponse(200, b'{"status":"ok","jsessionid":"sensitive-marker"}', {"Set-Cookie": marker}),
            RuntimeError(marker),
        )
        role = self.a.SessionRole.SOURCE
        outcome = manager.authenticate(role)
        with self.assertRaises(self.t.TransportError) as caught:
            manager.request(role, self.t.HttpMethod.GET, ("synthetic",))
        error = caught.exception
        visible = (
            repr(self.credentials) + repr(outcome) + repr(backend.requests[0])
            + repr(manager.snapshot(role)) + repr(asdict(manager.snapshot(role)))
            + "".join(traceback.format_exception(error)) + repr(vars(error))
        )
        self.assertNotIn(marker, visible)
        self.assertIsNone(error.__context__)
        self.assertIsNone(error.__cause__)

    def test_invalid_contracts_and_missing_session_are_explicit(self) -> None:
        for value in ("", "https://secret.invalid", "inline password", None):
            with self.subTest(reference_kind="invalid"):
                with self.assertRaises(self.contracts.ContractValidationError):
                    self.a.CredentialReference(value)
        for value in (0, -1, True, float("inf"), float("nan"), "10", 10 ** 1000):
            with self.subTest(expiration_kind="invalid"):
                with self.assertRaises(self.contracts.ContractValidationError):
                    self.a.SessionExpiration(value)
        manager = self.s.SessionManager(lambda: FakeOwnedBackend(), self.resolver)
        with self.assertRaises(self.a.AuthenticationError):
            manager.authenticate(self.a.SessionRole.SOURCE)
        with self.assertRaises(self.contracts.ContractValidationError):
            self.auth_request(product="unknown")

    def test_factory_and_clock_failures_are_sanitized_and_fail_closed(self) -> None:
        manager = self.s.SessionManager(Mock(side_effect=RuntimeError("sensitive-marker")), self.resolver)
        with self.assertRaises(self.a.AuthenticationError) as caught:
            manager.initialize(self.auth_request(), self.config())
        self.assertIsNone(caught.exception.__context__)
        self.assertNotIn("sensitive-marker", "".join(traceback.format_exception(caught.exception)))
        for value in (float("nan"), RuntimeError("sensitive-marker")):
            with self.subTest(clock_kind="invalid"):
                manager, backend = self.manager(self.ok())
                self.clock.side_effect = value if isinstance(value, Exception) else None
                self.clock.return_value = value
                self.assert_auth_failure(manager, self.a.AuthenticationFailureCategory.CLOCK)
                self.assertEqual(len(backend.requests), 1)
        self.clock.side_effect = None

    def test_clock_failure_during_expiry_check_blocks_dispatch(self) -> None:
        manager, backend = self.manager(self.ok(), request=self.auth_request(lifetime=10))
        role = self.a.SessionRole.SOURCE
        manager.authenticate(role)
        self.clock.side_effect = RuntimeError("sensitive-clock-marker")
        with self.assertRaises(self.a.AuthenticationError) as caught:
            manager.request(role, self.t.HttpMethod.POST, ("synthetic",))
        self.assertEqual(caught.exception.failure.category, self.a.AuthenticationFailureCategory.CLOCK)
        self.assertEqual(manager.snapshot(role).state, self.a.SessionState.FAILED)
        self.assertEqual(len(backend.requests), 1)
        self.clock.side_effect = None

    def test_failed_transport_initialization_closes_newly_owned_backend(self) -> None:
        backend = FakeOwnedBackend()
        manager = self.s.SessionManager(lambda: backend, self.resolver)
        with patch.object(self.s, "HttpTransport", side_effect=RuntimeError("sensitive-init-marker")):
            with self.assertRaises(self.a.AuthenticationError) as caught:
                manager.initialize(self.auth_request(), self.config())
        self.assertEqual(caught.exception.failure.category, self.a.AuthenticationFailureCategory.INITIALIZATION)
        self.assertEqual(backend.close_calls, 1)
        self.assertEqual(manager.snapshot(self.a.SessionRole.SOURCE).state, self.a.SessionState.CLOSED)
        self.assertNotIn("sensitive-init-marker", "".join(traceback.format_exception(caught.exception)))

    def test_invalid_closeable_backend_is_closed_once_without_registration(self) -> None:
        for send_kind in ("missing", "none", "non-callable"):
            with self.subTest(send_kind=send_kind):
                backend = Mock(spec=["close"])
                if send_kind != "missing":
                    backend.send = None if send_kind == "none" else "not-callable"
                manager = self.s.SessionManager(lambda: backend, self.resolver)
                with self.assertRaises(self.a.AuthenticationError) as caught:
                    with manager:
                        manager.initialize(self.auth_request(), self.config())
                self.assertEqual(caught.exception.failure.category, self.a.AuthenticationFailureCategory.INITIALIZATION)
                backend.close.assert_called_once_with()
                manager.close_all()
                backend.close.assert_called_once_with()
                self.resolver.resolve.assert_not_called()
                with self.assertRaises(self.a.AuthenticationError):
                    manager.snapshot(self.a.SessionRole.SOURCE)

    def test_invalid_closeable_backend_cleanup_failure_preserves_initialization_error(self) -> None:
        marker = "sensitive-rejected-close-marker"
        backend = Mock(spec=["close"])
        backend.close.side_effect = RuntimeError(marker)
        manager = self.s.SessionManager(lambda: backend, self.resolver)
        with self.assertRaises(self.a.AuthenticationError) as caught:
            with manager:
                manager.initialize(self.auth_request(), self.config())
        error = caught.exception
        self.assertEqual(error.failure.category, self.a.AuthenticationFailureCategory.INITIALIZATION)
        self.assertTrue(error.__notes__)
        self.assertIn("cleanup", " ".join(error.__notes__).lower())
        self.assertNotIn(marker, "".join(traceback.format_exception(error)) + repr(vars(error)))
        self.assertIsNone(error.__context__)
        self.assertIsNone(error.__cause__)
        backend.close.assert_called_once_with()
        manager.close_all()
        backend.close.assert_called_once_with()

    def test_rejected_shared_backend_leaves_authenticated_source_usable(self) -> None:
        manager, backend = self.manager(self.ok(), self.t.HttpResponse(200))
        source, destination = self.a.SessionRole
        manager.authenticate(source)
        with self.assertRaises(self.a.AuthenticationError) as caught:
            manager.initialize(self.auth_request(role=destination), self.config(destination))
        self.assertEqual(caught.exception.failure.category, self.a.AuthenticationFailureCategory.OWNERSHIP)
        self.assertEqual(backend.close_calls, 0)
        self.assertTrue(manager.is_authenticated(source))
        self.assertEqual(manager.request(source, self.t.HttpMethod.GET, ("synthetic",)).status, 200)
        self.assertEqual(len(backend.requests), 2)
        manager.close_all()
        manager.close_all()
        self.assertEqual(backend.close_calls, 1)

    def test_source_401_expiration_leaves_destination_authenticated(self) -> None:
        source_backend = FakeOwnedBackend(self.ok(), self.t.HttpResponse(401))
        destination_backend = FakeOwnedBackend(self.ok(), self.t.HttpResponse(200))
        manager = self.s.SessionManager(
            Mock(side_effect=[source_backend, destination_backend]), self.resolver,
        )
        self.addCleanup(manager.close_all)
        source, destination = self.a.SessionRole
        for role in (source, destination):
            manager.initialize(self.auth_request(role=role), self.config(role))
            manager.authenticate(role)
        with self.assertRaises(self.a.AuthenticationError) as caught:
            manager.request(source, self.t.HttpMethod.GET, ("synthetic",))
        self.assertEqual(caught.exception.failure.category, self.a.AuthenticationFailureCategory.HTTP_REJECTION)
        self.assertEqual(manager.snapshot(source).state, self.a.SessionState.EXPIRED)
        self.assertFalse(manager.is_authenticated(source))
        self.assertTrue(manager.is_authenticated(destination))
        self.assertEqual(manager.request(destination, self.t.HttpMethod.GET, ("synthetic",)).status, 200)
        self.assertEqual(len(source_backend.requests), 2)
        self.assertEqual(len(destination_backend.requests), 2)
        self.assertEqual(source_backend.close_calls, 0)
        self.assertEqual(destination_backend.close_calls, 0)

    def test_controller_authentication_failure_blocks_reuse_and_cleans_up(self) -> None:
        manager, backend = self.manager(
            self.t.HttpResponse(401), request=self.auth_request("cyber-controller"),
        )
        role = self.a.SessionRole.SOURCE
        with manager:
            self.assert_auth_failure(manager, self.a.AuthenticationFailureCategory.HTTP_REJECTION)
            for operation in (
                lambda: manager.authenticate(role),
                lambda: manager.request(role, self.t.HttpMethod.POST, ("synthetic",)),
            ):
                with self.assertRaises(self.a.AuthenticationError):
                    operation()
            self.assertEqual(len(backend.requests), 1)
            self.assertIn("Authorization", backend.requests[0].headers)
        self.assertEqual(backend.close_calls, 1)
        self.assertEqual(backend.cookies, {})
        self.assertEqual(manager.snapshot(role).state, self.a.SessionState.CLOSED)

    def test_controller_expiration_blocks_writes_and_cleans_up(self) -> None:
        role = self.a.SessionRole.SOURCE
        for reason in ("http-401", "local-lifetime"):
            with self.subTest(reason=reason):
                self.clock.return_value = 100.0
                outcomes = (
                    (self.ok(), self.t.HttpResponse(401))
                    if reason == "http-401" else (self.ok(),)
                )
                manager, backend = self.manager(
                    *outcomes,
                    request=self.auth_request(
                        "cyber-controller", lifetime=10 if reason == "local-lifetime" else None,
                    ),
                )
                with manager:
                    manager.authenticate(role)
                    if reason == "local-lifetime":
                        self.clock.return_value = 110.0
                    with self.assertRaises(self.a.AuthenticationError):
                        manager.request(role, self.t.HttpMethod.POST, ("synthetic",))
                    snapshot = manager.snapshot(role)
                    self.assertEqual(snapshot.state, self.a.SessionState.EXPIRED)
                    expected_reason = (
                        self.a.ExpirationReason.HTTP_REJECTION if reason == "http-401"
                        else self.a.ExpirationReason.LOCAL_LIFETIME
                    )
                    self.assertEqual(snapshot.expiration_reason, expected_reason)
                    self.assertFalse(manager.is_authenticated(role))
                    with self.assertRaises(self.a.AuthenticationError):
                        manager.request(role, self.t.HttpMethod.POST, ("synthetic",))
                    self.assertEqual(len(backend.requests), len(outcomes))
                manager.close_all()
                self.assertEqual(backend.close_calls, 1)
                self.assertEqual(backend.cookies, {})
                self.assertEqual(manager.snapshot(role).state, self.a.SessionState.CLOSED)

    def test_encoded_basic_credentials_are_absent_from_errors_snapshots_and_representations(self) -> None:
        encoded = base64.b64encode(f"{self.username}:{self.password}".encode("latin-1")).decode("ascii")
        authorization = "Basic " + encoded
        for failed_login in (True, False):
            with self.subTest(failed_login=failed_login):
                outcomes = (
                    (self.t.HttpResponse(401, authorization.encode("ascii")),)
                    if failed_login else (self.ok(cookie=encoded), RuntimeError(authorization))
                )
                manager, backend = self.manager(
                    *outcomes, request=self.auth_request("cyber-controller"),
                )
                role = self.a.SessionRole.SOURCE
                if failed_login:
                    error = self.assert_auth_failure(manager, self.a.AuthenticationFailureCategory.HTTP_REJECTION)
                else:
                    manager.authenticate(role)
                    with self.assertRaises(self.t.TransportError) as caught:
                        manager.request(role, self.t.HttpMethod.POST, ("synthetic",))
                    error = caught.exception
                    self.assertEqual(error.category, self.t.ErrorCategory.INDETERMINATE_WRITE)
                self.assertEqual(backend.requests[0].headers["Authorization"], authorization)
                snapshot = manager.snapshot(role)
                visible = (
                    str(error) + repr(error) + repr(vars(error))
                    + "".join(traceback.format_exception(error))
                    + repr(snapshot) + repr(asdict(snapshot))
                    + repr(self.credentials) + repr(self.auth_request("cyber-controller"))
                    + repr(manager) + "".join(repr(request) for request in backend.requests)
                )
                manager.close_all()
                visible += repr(manager.snapshot(role)) + repr(asdict(manager.snapshot(role)))
                for secret in (self.username, self.password, encoded, authorization):
                    self.assertNotIn(secret, visible)
                self.assertIsNone(error.__context__)
                self.assertIsNone(error.__cause__)
                self.assertEqual(len(backend.requests), len(outcomes))
                self.assertEqual(backend.close_calls, 1)
