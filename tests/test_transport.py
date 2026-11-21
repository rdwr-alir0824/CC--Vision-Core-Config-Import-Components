import importlib
import ssl
import traceback
import unittest
from unittest.mock import Mock, patch

from offline_support import OfflineTestCase


class FakeSession:
    def __init__(self, *outcomes: object) -> None:
        self.outcomes = list(outcomes)
        self.requests: list = []

    def send(self, request):
        self.requests.append(request)
        if not self.outcomes:
            raise AssertionError("Unexpected HTTP attempt.")
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


class TransportTests(OfflineTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.t = importlib.import_module("cc_vision_import.transport")
        self.contracts = importlib.import_module("cc_vision_import.contracts")

    def config(self, **overrides):
        values = {
            "base_url": "https://transport.invalid:8443/",
            "connect_timeout": 2.5,
            "read_timeout": 9,
            **overrides,
        }
        return self.t.TransportConfig(**values)

    def transport(self, *outcomes, **configuration):
        session = FakeSession(*outcomes)
        return self.t.HttpTransport(self.config(**configuration), session), session

    def test_deadline_retries_share_absolute_budget_and_clock_domain(self):
        clock = Mock(return_value=10.0)
        requests, remaining = [], []
        def send(request):
            requests.append(request)
            remaining.append(request.deadline.remaining())
            clock.return_value += 2.0
            if len(requests) == 1:
                raise self.t.BackendFailure(self.t.ErrorCategory.CONNECTION)
            return self.t.HttpResponse(200, b"ok")
        transport = self.t.HttpTransport(
            self.config(operation_timeout=5, read_retries=3),
            Mock(send=Mock(side_effect=send)), clock=clock,
        )
        self.assertEqual(transport.request(self.t.HttpMethod.GET, ()).body, b"ok")
        self.assertEqual(remaining, [5.0, 3.0])
        self.assertIs(requests[0].deadline, requests[1].deadline)
        self.assertEqual(requests[0].deadline.expires_at, 15.0)

    def test_deadline_expired_get_cannot_retry_after_timeout_or_connection_failure(self):
        for reason in (self.t.ErrorCategory.CONNECTION, self.t.ErrorCategory.TIMEOUT):
            clock = Mock(return_value=0.0)
            def send(request):
                clock.return_value = 5.0
                raise self.t.BackendFailure(reason)
            backend = Mock(send=Mock(side_effect=send))
            transport = self.t.HttpTransport(
                self.config(operation_timeout=5, read_retries=3), backend, clock=clock,
            )
            with self.assertRaises(self.t.TransportError) as caught:
                transport.request(self.t.HttpMethod.GET, ())
            self.assertEqual(caught.exception.category, self.t.ErrorCategory.TIMEOUT)
            self.assertEqual(caught.exception.attempts, 1)
            self.assertEqual(backend.send.call_count, 1)

    def test_deadline_expiry_during_tls_setup_prevents_backend_dispatch(self):
        clock = Mock(return_value=0.0)
        backend = Mock()
        transport = self.t.HttpTransport(
            self.config(operation_timeout=5, read_retries=3), backend, clock=clock,
        )
        original = self.t._tls_context
        def slow_context(trusted_ca):
            context = original(trusted_ca)
            clock.return_value = 5.0
            return context
        with patch.object(self.t, "_tls_context", side_effect=slow_context):
            with self.assertRaises(self.t.TransportError) as caught:
                transport.request(self.t.HttpMethod.GET, ())
        self.assertEqual(caught.exception.category, self.t.ErrorCategory.TIMEOUT)
        self.assertEqual(caught.exception.attempts, 1)
        backend.send.assert_not_called()

    def test_deadline_late_success_is_not_accepted_and_writes_remain_indeterminate(self):
        for method in (self.t.HttpMethod.GET, self.t.HttpMethod.POST):
            clock = Mock(return_value=0.0)
            def send(request):
                clock.return_value = 5.0
                return self.t.HttpResponse(200, b"ok")
            backend = Mock(send=Mock(side_effect=send))
            transport = self.t.HttpTransport(
                self.config(operation_timeout=5, read_retries=3), backend, clock=clock,
            )
            with self.assertRaises(self.t.TransportError) as caught:
                transport.request(method, ())
            self.assertEqual(caught.exception.reason, self.t.ErrorCategory.TIMEOUT)
            self.assertEqual(caught.exception.category, (
                self.t.ErrorCategory.TIMEOUT if method == self.t.HttpMethod.GET
                else self.t.ErrorCategory.INDETERMINATE_WRITE
            ))
            self.assertEqual(backend.send.call_count, 1)

    def test_deadline_known_rejection_and_cleanup_failure_remain_primary(self):
        for status in (401, 403, 500):
            clock = Mock(return_value=0.0)
            def send(request):
                clock.return_value = 5.0
                raise self.t.BackendFailure(
                    self.t.ErrorCategory.TIMEOUT, status=status, cleanup_failed=True,
                )
            backend = Mock(send=Mock(side_effect=send))
            transport = self.t.HttpTransport(
                self.config(operation_timeout=5, read_retries=3), backend, clock=clock,
            )
            with self.assertRaises(self.t.TransportError) as caught:
                transport.request(self.t.HttpMethod.GET, ())
            self.assertEqual(caught.exception.status, status)
            self.assertTrue(caught.exception.cleanup_failed)
            self.assertEqual(caught.exception.category, {
                401: self.t.ErrorCategory.AUTHENTICATION,
                403: self.t.ErrorCategory.AUTHORIZATION, 500: self.t.ErrorCategory.HTTP,
            }[status])
            self.assertEqual(backend.send.call_count, 1)

    def test_deadline_invalid_clock_values_and_exceptions_fail_sanitized(self):
        for value in (None, True, float("inf"), float("nan"), "secret"):
            backend = Mock()
            clock = Mock(return_value=value)
            transport = self.t.HttpTransport(
                self.config(operation_timeout=5), backend, clock=clock,
            )
            with self.assertRaises(self.t.TransportError) as caught:
                transport.request(self.t.HttpMethod.GET, ())
            self.assertEqual(caught.exception.category, self.t.ErrorCategory.BACKEND)
            self.assertNotIn("secret", "".join(traceback.format_exception(caught.exception)))
            backend.send.assert_not_called()
        backend = Mock()
        transport = self.t.HttpTransport(
            self.config(operation_timeout=5), backend,
            clock=Mock(side_effect=RuntimeError("secret")),
        )
        with self.assertRaises(self.t.TransportError) as caught:
            transport.request(self.t.HttpMethod.GET, ())
        self.assertIsNone(caught.exception.__context__)
        self.assertNotIn("secret", "".join(traceback.format_exception(caught.exception)))
        backend.send.assert_not_called()

    def test_deadline_configuration_requires_finite_positive_bounded_seconds(self):
        for value in (0, -1, True, "5", float("inf"), float("nan"), 301):
            with self.assertRaises(self.contracts.ContractValidationError) as caught:
                self.config(operation_timeout=value)
            self.assertEqual(caught.exception.result.issues[0].path, "$.operation_timeout")

    def test_deadline_expiry_during_creation_remains_a_timeout_without_dispatch(self):
        for method in (self.t.HttpMethod.GET, self.t.HttpMethod.POST):
            backend = Mock()
            transport = self.t.HttpTransport(
                self.config(operation_timeout=5, read_retries=3), backend,
                clock=Mock(side_effect=[0.0, 5.0]),
            )
            with self.assertRaises(self.t.TransportError) as caught:
                transport.request(method, ())
            self.assertEqual(caught.exception.reason, self.t.ErrorCategory.TIMEOUT)
            self.assertEqual(caught.exception.category, (
                self.t.ErrorCategory.TIMEOUT if method == self.t.HttpMethod.GET
                else self.t.ErrorCategory.INDETERMINATE_WRITE
            ))
            self.assertEqual(caught.exception.attempts, 1)
            backend.send.assert_not_called()

    def test_all_five_methods_forward_exactly_once_and_protect_representations(self) -> None:
        marker = "sensitive-fixture-marker"
        for method in self.t.HttpMethod:
            with self.subTest(method=method):
                response = self.t.HttpResponse(200, b'{"ok":true}', {"Set-Cookie": marker})
                transport, session = self.transport(response, read_retries=3)
                body = None if method == self.t.HttpMethod.GET else marker.encode()
                result = transport.request(
                    method, ("synthetic", marker), headers={"Authorization": marker},
                    query=(("filter", marker),), body=body, expect_json=True,
                )
                self.assertIs(result, response)
                self.assertEqual(len(session.requests), 1)
                request = session.requests[0]
                self.assertEqual(request.method, method)
                self.assertEqual(request.body, body)
                self.assertEqual(request.headers["Authorization"], marker)
                self.assertEqual(request.connect_timeout, 2.5)
                self.assertEqual(request.read_timeout, 9)
                self.assertFalse(request.follow_redirects)
                self.assertTrue(request.tls_context.check_hostname)
                self.assertEqual(request.tls_context.verify_mode, ssl.CERT_REQUIRED)
                self.assertNotIn(marker, repr(request) + repr(response) + repr(self.config()))
                self.assertNotIn("transport.invalid", repr(self.config()))

    def test_default_get_failures_have_structured_categories_without_retry(self) -> None:
        for category in (
            self.t.ErrorCategory.CONNECTION, self.t.ErrorCategory.TIMEOUT, self.t.ErrorCategory.TLS,
        ):
            with self.subTest(category=category):
                transport, session = self.transport(self.t.BackendFailure(category))
                with self.assertRaises(self.t.TransportError) as caught:
                    transport.request(self.t.HttpMethod.GET, ())
                self.assertEqual(caught.exception.category, category)
                self.assertEqual(caught.exception.reason, category)
                self.assertEqual(caught.exception.attempts, 1)
                self.assertEqual(len(session.requests), 1)

    def test_timeout_and_connection_get_retries_are_opt_in_and_bounded(self) -> None:
        for category in (self.t.ErrorCategory.CONNECTION, self.t.ErrorCategory.TIMEOUT):
            with self.subTest(category=category):
                failures = [self.t.BackendFailure(category) for _ in range(4)]
                transport, session = self.transport(*failures, read_retries=3)
                with self.assertRaises(self.t.TransportError) as caught:
                    transport.request(self.t.HttpMethod.GET, ("synthetic",))
                self.assertEqual(caught.exception.attempts, 4)
                self.assertEqual(len(session.requests), 4)

    def test_safe_read_retry_can_succeed(self) -> None:
        response = self.t.HttpResponse(200, b"success")
        transport, session = self.transport(
            self.t.BackendFailure(self.t.ErrorCategory.TIMEOUT), response, read_retries=1,
        )
        self.assertIs(transport.request(self.t.HttpMethod.GET, ()), response)
        self.assertEqual(len(session.requests), 2)

    def test_tls_errors_never_retry_or_downgrade(self) -> None:
        transport, session = self.transport(
            self.t.BackendFailure(self.t.ErrorCategory.TLS), read_retries=3,
        )
        with self.assertRaises(self.t.TransportError) as caught:
            transport.request(self.t.HttpMethod.GET, ())
        self.assertEqual(caught.exception.category, self.t.ErrorCategory.TLS)
        self.assertEqual(len(session.requests), 1)
        self.assertTrue(session.requests[0].tls_context.check_hostname)

    def test_all_writes_are_indeterminate_on_io_failure_and_never_replayed(self) -> None:
        for method in tuple(self.t.HttpMethod)[1:]:
            for reason in (
                self.t.ErrorCategory.CONNECTION, self.t.ErrorCategory.TIMEOUT, self.t.ErrorCategory.TLS,
            ):
                with self.subTest(method=method, reason=reason):
                    transport, session = self.transport(self.t.BackendFailure(reason), read_retries=3)
                    with self.assertRaises(self.t.TransportError) as caught:
                        transport.request(method, ("synthetic",))
                    self.assertEqual(caught.exception.category, self.t.ErrorCategory.INDETERMINATE_WRITE)
                    self.assertEqual(caught.exception.reason, reason)
                    self.assertEqual(len(session.requests), 1)

    def test_http_status_classification_no_redirect_or_authentication_renewal(self) -> None:
        cases = (
            (301, self.t.ErrorCategory.HTTP), (307, self.t.ErrorCategory.HTTP),
            (400, self.t.ErrorCategory.HTTP), (401, self.t.ErrorCategory.AUTHENTICATION),
            (403, self.t.ErrorCategory.AUTHORIZATION), (404, self.t.ErrorCategory.HTTP),
            (408, self.t.ErrorCategory.HTTP), (429, self.t.ErrorCategory.HTTP),
            (500, self.t.ErrorCategory.HTTP), (503, self.t.ErrorCategory.HTTP),
        )
        for status, category in cases:
            for method in (self.t.HttpMethod.GET, self.t.HttpMethod.POST):
                with self.subTest(status=status, method=method):
                    response = self.t.HttpResponse(status, b"sensitive-response", {"Location": "https://other.invalid"})
                    transport, session = self.transport(response, read_retries=3)
                    with self.assertRaises(self.t.TransportError) as caught:
                        transport.request(method, ())
                    expected = (
                        self.t.ErrorCategory.INDETERMINATE_WRITE
                        if (status == 408 or status >= 500) and method != self.t.HttpMethod.GET else category
                    )
                    self.assertEqual(caught.exception.category, expected)
                    self.assertEqual(caught.exception.reason, category)
                    self.assertEqual(caught.exception.status, status)
                    self.assertEqual(len(session.requests), 1)
                    self.assertNotIn("sensitive-response", str(caught.exception))

    def test_success_without_body_and_acceptance_do_not_require_json(self) -> None:
        for status in (202, 204):
            with self.subTest(status=status):
                transport, _ = self.transport(self.t.HttpResponse(status))
                self.assertEqual(transport.request(self.t.HttpMethod.POST, ()).status, status)

    def test_malformed_json_is_explicit_and_never_retried(self) -> None:
        for body in (b"secret-body", b"\xff", b'{"x":1,"x":2}', b'{"x":NaN}', b""):
            for method in (self.t.HttpMethod.GET, self.t.HttpMethod.PUT):
                with self.subTest(body_kind="malformed", method=method):
                    transport, session = self.transport(self.t.HttpResponse(200, body), read_retries=3)
                    with self.assertRaises(self.t.TransportError) as caught:
                        transport.request(method, (), expect_json=True)
                    expected = (
                        self.t.ErrorCategory.MALFORMED_RESPONSE if method == self.t.HttpMethod.GET
                        else self.t.ErrorCategory.INDETERMINATE_WRITE
                    )
                    self.assertEqual(caught.exception.category, expected)
                    self.assertEqual(caught.exception.reason, self.t.ErrorCategory.MALFORMED_RESPONSE)
                    self.assertEqual(len(session.requests), 1)
                    self.assertNotIn("secret-body", str(caught.exception))

    def test_invalid_backend_response_is_not_success(self) -> None:
        for response in (None, {}, self.t.HttpResponse(True), self.t.HttpResponse(600), self.t.HttpResponse(100)):
            with self.subTest(response_type=type(response).__name__):
                transport, session = self.transport(response)
                with self.assertRaises(self.t.TransportError) as caught:
                    transport.request(self.t.HttpMethod.GET, ())
                self.assertEqual(caught.exception.category, self.t.ErrorCategory.MALFORMED_RESPONSE)
                self.assertEqual(len(session.requests), 1)

    def test_unexpected_backend_exception_is_sanitized_without_chaining(self) -> None:
        marker = "sensitive-fixture-marker"
        for method in (self.t.HttpMethod.GET, self.t.HttpMethod.DELETE):
            with self.subTest(method=method):
                transport, session = self.transport(RuntimeError(marker), read_retries=3)
                with self.assertRaises(self.t.TransportError) as caught:
                    transport.request(method, (marker,), headers={"Cookie": marker})
                error = caught.exception
                self.assertEqual(error.reason, self.t.ErrorCategory.BACKEND)
                self.assertIsNone(error.__context__)
                self.assertIsNone(error.__cause__)
                self.assertNotIn(marker, "".join(traceback.format_exception(error)) + repr(vars(error)))
                self.assertEqual(len(session.requests), 1)

    def test_sensitive_and_custom_header_values_are_all_redacted(self) -> None:
        marker = "sensitive-fixture-marker"
        headers = {
            key: marker for key in (
                "Authorization", "pRoXy-Authorization", "Cookie", "Set-Cookie",
                "X-API-Key", "X-Session-ID", "X-Custom", "Accept",
                "Content-Length", "Host", "Connection",
            )
        }
        redacted = self.t.redact_headers(headers)
        self.assertEqual(set(redacted), set(headers))
        self.assertEqual(set(redacted.values()), {"[REDACTED]"})
        self.assertNotIn(marker, repr(redacted))
        self.assertTrue(all(value == marker for value in headers.values()))

    def test_invalid_tls_timeouts_and_retry_settings_rejected(self) -> None:
        cases = [
            {"verify_tls": value} for value in (False, None, 1, "true")
        ] + [
            {key: value} for key in ("connect_timeout", "read_timeout")
            for value in (0, -1, True, None, "5", float("inf"), float("nan"), 301)
        ] + [
            {"read_retries": value} for value in (-1, 4, True, 1.5, None)
        ]
        for values in cases:
            with self.subTest(field=next(iter(values))):
                with self.assertRaises(self.contracts.ContractValidationError):
                    self.config(**values)

    def test_unsafe_origins_rejected_without_disclosing_values(self) -> None:
        for url in (
            "http://transport.invalid", "https://user:secret@transport.invalid",
            "https://transport.invalid/path", "https://transport.invalid?secret",
            "https://transport.invalid/#secret", "https://transport.invalid:0",
            "https://transport.invalid:65536", "https://transport.invalid\n",
            "https://transport.invalid:secret",
            "//transport.invalid", "https://transport.invalid\\other", None,
        ):
            with self.subTest(url_kind="invalid"):
                with self.assertRaises(self.contracts.ContractValidationError) as caught:
                    self.config(base_url=url)
                self.assertNotIn("secret", str(caught.exception) + repr(caught.exception.result))
                self.assertIsNone(caught.exception.__context__)
                self.assertNotIn("secret", "".join(traceback.format_exception(caught.exception)))

    def test_ca_configuration_must_be_local_readable_and_loadable(self) -> None:
        self.input_path.write_text("not a certificate", encoding="utf-8")
        for path in (
            "", str(self.directory / "missing.pem"), str(self.directory), str(self.input_path),
            r"\\transport.invalid\share\ca.pem", "//transport.invalid/share/ca.pem",
            "https://transport.invalid/ca.pem", 3, "bad\x00path",
        ):
            with self.subTest(ca_kind="invalid"):
                with self.assertRaises(self.contracts.ContractValidationError) as caught:
                    self.config(trusted_ca=path)
                self.assertEqual(caught.exception.result.issues[0].code, "invalid_ca")

    def test_remote_ca_paths_are_rejected_before_filesystem_access(self) -> None:
        for path in (
            r"\\transport.invalid\share\ca.pem", "//transport.invalid/share/ca.pem",
            "/\\transport.invalid\\share\\ca.pem", "\\/transport.invalid\\share\\ca.pem",
            "https://transport.invalid/ca.pem",
        ):
            with self.subTest(ca_kind="remote"):
                with patch("pathlib.Path.is_file") as is_file:
                    with self.assertRaises(self.contracts.ContractValidationError):
                        self.config(trusted_ca=path)
                is_file.assert_not_called()

    def test_optional_ca_is_forwarded_to_verified_context_loader(self) -> None:
        self.input_path.write_text("synthetic CA input; loader mocked", encoding="utf-8")
        context = ssl.create_default_context()
        with patch.object(self.t.ssl, "create_default_context", return_value=context) as loader:
            transport, session = self.transport(self.t.HttpResponse(200), trusted_ca=str(self.input_path))
            transport.request(self.t.HttpMethod.GET, ())
        self.assertTrue(loader.call_args_list)
        for call in loader.call_args_list:
            self.assertEqual(call.kwargs, {"cafile": str(self.input_path)})
        self.assertIs(session.requests[0].tls_context, context)
        self.assertTrue(context.check_hostname)
        self.assertEqual(context.verify_mode, ssl.CERT_REQUIRED)

    def test_url_components_are_encoded_without_origin_override(self) -> None:
        url = self.t.build_url(
            "https://transport.invalid:8443/", ("synthetic", "name ?#:@"),
            (("filter", "x&next=https://other.invalid/#fragment"),),
        )
        self.assertEqual(
            url, "https://transport.invalid:8443/synthetic/name%20%3F%23%3A%40"
            "?filter=x%26next%3Dhttps%3A%2F%2Fother.invalid%2F%23fragment",
        )

    def test_unsafe_path_and_query_inputs_fail_before_dispatch(self) -> None:
        for segments, query in (
            ((".",), ()), (("..",), ()), (("//other.invalid",), ()),
            (("https://other.invalid",), ()), (("a\\b",), ()),
            (("%2e%2e",), ()), (("a/b",), ()), (("a\nb",), ()), (("",), ()),
            ("synthetic", ()), ((), (("key", "x\r\nsecret"),)),
            ((), (("key",),)), ((), [("key", "value")]),
        ):
            with self.subTest(input_kind="unsafe-component"):
                transport, session = self.transport()
                with self.assertRaises(self.contracts.ContractValidationError):
                    transport.request(self.t.HttpMethod.GET, segments, query=query)
                self.assertEqual(session.requests, [])

    def test_invalid_headers_method_and_body_fail_before_dispatch(self) -> None:
        cases = [
            {"headers": value} for value in (
                {"Authorization": "secret\r\nInjected: value"}, {"bad name": "secret"},
                {"X-Key": "secret", "x-key": "other"}, {"Host": "other.invalid"},
                {"Content-Length": "3"}, {"Transfer-Encoding": "chunked"},
                {"Connection": "keep-alive"}, {"X-Key": None}, [],
            )
        ] + [{"body": "secret"}, {"body": b"GET body"}, {"expect_json": "yes"}]
        for kwargs in cases:
            with self.subTest(input_kind="invalid-request"):
                transport, session = self.transport()
                with self.assertRaises(self.contracts.ContractValidationError):
                    transport.request(self.t.HttpMethod.GET, (), **kwargs)
                self.assertEqual(session.requests, [])
        transport, session = self.transport()
        with self.assertRaises(self.contracts.ContractValidationError):
            transport.request("GET", ())
        self.assertEqual(session.requests, [])

    def test_no_default_or_invalid_backend_is_accepted(self) -> None:
        with self.assertRaises(TypeError):
            self.t.HttpTransport(self.config())
        with self.assertRaises(self.contracts.ContractValidationError):
            self.t.HttpTransport(self.config(), object())
        self.assert_no_network_attempts()


if __name__ == "__main__":
    unittest.main()
