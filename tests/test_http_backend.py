import base64
import http.client
import gzip
import importlib
import io
import json
import ssl
import traceback
import warnings
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import replace
from unittest.mock import Mock, patch

from offline_support import OfflineTestCase


SECRET = "synthetic-sensitive-backend-marker"


class MemorySocket:
    def __init__(self, events):
        self.events = events
        self.timeouts = []
        self.writes = []

    def settimeout(self, value):
        self.events.append("read-timeout")
        self.timeouts.append(value)

    def sendall(self, data):
        self.writes.append(data)


class MemoryResponse:
    def __init__(self, status=200, body=b"", headers=None, *, failure=None, close_failures=0):
        self.status = status
        self.body = body
        self.headers = [] if headers is None else headers
        self.failure = failure
        self.close_failures = close_failures
        self.close_calls = 0
        self.events = []
        self.offset = 0
        self.read_sizes = []

    def getheaders(self):
        if self.failure is not None and self.failure[0] == "headers":
            raise self.failure[1]
        return self.headers

    def read(self, size):
        self.events.append("read")
        self.read_sizes.append(size)
        if self.failure is not None and self.failure[0] == "read":
            raise self.failure[1]
        chunk = self.body[self.offset:self.offset + size]
        self.offset += len(chunk)
        return chunk

    def close(self):
        self.events.append("response-close")
        self.close_calls += 1
        if self.close_failures:
            self.close_failures -= 1
            raise RuntimeError(SECRET)


class MemoryConnection:
    """No inheritance, delegation, sockets, or other dispatch-capable operations."""

    def __init__(self, response=None, *, failure=None, close_failures=0):
        self.response = MemoryResponse() if response is None else response
        self.events = []
        self.response.events = self.events
        self.sock = MemorySocket(self.events)
        self.auto_open = 1
        self.debuglevel = 9
        self.failure = failure
        self.close_failures = close_failures
        self.close_calls = 0
        self.requests = []

    def set_debuglevel(self, level):
        self.debuglevel = level

    def fail(self, stage):
        if self.failure is not None and self.failure[0] == stage:
            raise self.failure[1]

    def connect(self):
        self.events.append("connect")
        self.fail("connect")

    def request(self, method, url, body=None, headers=None):
        self.events.append("request")
        self.requests.append((method, url, body, headers))
        self.fail("request")

    def getresponse(self):
        self.events.append("getresponse")
        self.fail("getresponse")
        return self.response

    def close(self):
        self.events.append("connection-close")
        self.close_calls += 1
        if self.close_failures:
            self.close_failures -= 1
            raise RuntimeError(SECRET)


class IncrementalResponse(MemoryResponse):
    def __init__(self, *args, clock=None, delay=0, chunk_size=1, **kwargs):
        super().__init__(*args, **kwargs)
        self.clock = clock
        self.delay = delay
        self.chunk_size = chunk_size

    def read(self, size):
        if self.clock is not None:
            self.clock.return_value += self.delay
        return super().read(min(size, self.chunk_size))


class WireFile(io.BytesIO):
    def __init__(self, wire, *, read_error=None, close_failures=0):
        super().__init__(wire)
        self.read_error = read_error
        self.close_failures = close_failures
        self.close_calls = 0

    def read(self, *args):
        if self.read_error is not None:
            raise self.read_error
        return super().read(*args)

    def close(self):
        self.close_calls += 1
        if self.close_failures:
            self.close_failures -= 1
            raise OSError(SECRET)
        super().close()


class WireSocket:
    def __init__(self, stream, *, close_failures=0):
        self.stream = stream
        self.close_failures = close_failures
        self.close_calls = 0
        self.timeouts = []

    def settimeout(self, value):
        self.timeouts.append(value)

    def makefile(self, mode):
        assert mode == "rb"
        return self.stream

    def close(self):
        self.close_calls += 1
        if self.close_failures:
            self.close_failures -= 1
            raise OSError(SECRET)


class WireConnection:
    """Run stdlib response/close state machines with no socket or dispatch capability."""

    response_class = http.client.HTTPResponse
    getresponse = http.client.HTTPConnection.getresponse
    close = http.client.HTTPConnection.close

    def __init__(self, wire, *, read_error=None, file_failures=0, socket_failures=0):
        self.stream = WireFile(wire, read_error=read_error, close_failures=file_failures)
        self.original_socket = WireSocket(self.stream, close_failures=socket_failures)
        self.sock = self.original_socket
        self.auto_open = 1
        self.debuglevel = 0
        self.requests = []
        self._HTTPConnection__state = http.client._CS_IDLE
        self._HTTPConnection__response = None

    def set_debuglevel(self, level):
        self.debuglevel = level

    def connect(self):
        pass

    def request(self, method, url, body=None, headers=None):
        self.requests.append((method, url, body, headers))
        self._method = method
        self._HTTPConnection__state = http.client._CS_REQ_SENT


class HttpBackendTests(OfflineTestCase):
    guard_observations = 0
    guard_attempts = 0
    dispatch_observations = 0
    dispatch_attempts = 0
    measured_tests = 0

    def setUp(self):
        super().setUp()
        self.b = importlib.import_module("cc_vision_import.http_backend")
        self.t = importlib.import_module("cc_vision_import.transport")
        self.a = importlib.import_module("cc_vision_import.authentication")
        self.s = importlib.import_module("cc_vision_import.sessions")
        self.p = importlib.import_module("cc_vision_import.product_clients")
        self.c = importlib.import_module("cc_vision_import.capabilities")
        self.contracts = importlib.import_module("cc_vision_import.contracts")
        self.dispatch_guards = [
            self.stack.enter_context(patch(target, side_effect=AssertionError(
                "Concrete network dispatch is forbidden.",
            ))) for target in (
                "http.client.HTTPSConnection.connect", "http.client.HTTPSConnection",
            )
        ]
        self.addCleanup(self.measure_guards)
        self.context = ssl.create_default_context()

    def measure_guards(self):
        cls = type(self)
        cls.measured_tests += 1
        cls.guard_observations += len(self.network_guards)
        cls.guard_attempts += sum(guard.call_count for guard in self.network_guards)
        cls.dispatch_observations += len(self.dispatch_guards)
        cls.dispatch_attempts += sum(guard.call_count for guard in self.dispatch_guards)
        for guard in self.dispatch_guards:
            guard.assert_not_called()

    @classmethod
    def tearDownClass(cls):
        print(
            f"\nHTTP backend scope: tests={cls.measured_tests}; "
            f"network attempts={cls.guard_attempts}/{cls.guard_observations} observations; "
            f"real dispatch attempts={cls.dispatch_attempts}/{cls.dispatch_observations} observations."
        )
        super().tearDownClass()

    def request(self, **overrides):
        values = dict(
            method=self.t.HttpMethod.GET, url="https://backend.invalid/",
            headers={}, body=None, connect_timeout=2, read_timeout=4,
            tls_context=self.context,
            deadline=self.t.OperationDeadline(float("1e100")),
        )
        values.update(overrides)
        return self.t.BackendRequest(**values)

    def backend(self, *connections):
        factory = Mock(side_effect=connections)
        backend = self.b.StdlibHttpBackend(
            connection_factory=factory, authorization=self.authorization(),
            max_response_bytes=4096,
        )
        self.addCleanup(backend.close)
        return backend, factory

    def authorization(self):
        # Exact synthetic fixture scope only; no product capabilities are consulted.
        return self.b.DestinationAuthorization(
            "https://backend.invalid",
            tuple((method, target) for method in self.t.HttpMethod for target in (
                "/", "/api", "/restricted/item", "/mgmt/system/user/login",
                "/?marker=" + SECRET,
                "/api/name%20%3F%23%3A%40?filter=x%26next%3Dhttps%3A%2F%2Fother.invalid",
            )),
        )

    def bounded_backend(self, *connections, maximum=4, authorization=None, clock=None):
        clock = Mock(return_value=0.0) if clock is None else clock
        factory = Mock(side_effect=connections)
        backend = self.b.StdlibHttpBackend(
            connection_factory=factory, max_response_bytes=maximum,
            authorization=self.authorization() if authorization is None else authorization,
        )
        self.addCleanup(backend.close)
        return backend, factory, self.t.OperationDeadline(5.0, clock), clock

    def transport(self, *connections, **overrides):
        backend, factory = self.backend(*connections)
        values = dict(
            base_url="https://backend.invalid", connect_timeout=2, read_timeout=4,
            operation_timeout=30,
        )
        values.update(overrides)
        backend._authorization = replace(self.authorization(), origin=values["base_url"])
        return self.t.HttpTransport(self.t.TransportConfig(**values), backend), backend, factory

    def safe(self, error):
        self.assertNotIn(SECRET, str(error) + repr(error) + repr(vars(error)))
        self.assertNotIn(SECRET, "".join(traceback.format_exception(error)))
        self.assertIsNone(error.__context__)
        self.assertIsNone(error.__cause__)

    def cookie(self, connection):
        return {key.lower(): value for key, value in connection.requests[0][3].items()}.get("cookie", "")

    def manager(
        self, source_connections, destination_connections=None, *,
        source_product="vision", read_retries=0,
    ):
        source, source_factory = self.backend(*source_connections)
        backends = [source]
        destination = destination_factory = None
        if destination_connections is not None:
            destination, destination_factory = self.backend(*destination_connections)
            backends.append(destination)
        resolver = Mock()
        resolver.resolve.side_effect = lambda ref: self.a.ResolvedCredentials(
            ref.value + "-user", ref.value + "-password",
        )
        manager = self.s.SessionManager(Mock(side_effect=backends), resolver)
        self.addCleanup(manager.close_all)
        roles = [(self.a.SessionRole.SOURCE, source_product)]
        if destination is not None:
            roles.append((self.a.SessionRole.DESTINATION, "cyber-controller"))
        for role, product in roles:
            manager.initialize(
                self.a.AuthenticationRequest(
                    role, product, "0.0-test", self.a.CredentialReference("synthetic/" + role.value),
                ),
                self.t.TransportConfig(
                    base_url="https://backend.invalid", connect_timeout=2, read_timeout=4,
                    read_retries=read_retries,
                    operation_timeout=30,
                ),
            )
        return manager, source, destination, source_factory, destination_factory, resolver

    def login(self, cookie):
        return MemoryConnection(MemoryResponse(
            body=b'{"status":"ok"}',
            headers=[("Set-Cookie", f"JSESSIONID={cookie}; Secure; HttpOnly; Path=/")],
        ))

    def test_default_construction_and_local_close_are_inert_and_not_mock(self):
        backend = self.b.StdlibHttpBackend()
        self.assertNotIsInstance(backend, self.s.MockSessionBackend)
        backend.close()
        backend.close()
        with self.assertRaises(self.t.BackendFailure) as caught:
            backend.send(self.request())
        self.assertEqual(caught.exception.category, self.t.ErrorCategory.BACKEND)
        self.safe(caught.exception)

    def test_verified_tls_and_distinct_socket_timeouts_precede_request(self):
        connection = MemoryConnection()
        backend, factory = self.backend(connection)
        backend.send(self.request(connect_timeout=1.5, read_timeout=7.25))
        self.assertEqual(factory.call_args.args, ("backend.invalid", 443))
        self.assertEqual(factory.call_args.kwargs, {"timeout": 1.5, "context": self.context})
        self.assertTrue(connection.sock.timeouts)
        self.assertTrue(all(timeout == 7.25 for timeout in connection.sock.timeouts))
        self.assertEqual(self.context.verify_mode, ssl.CERT_REQUIRED)
        self.assertTrue(self.context.check_hostname)
        self.assertEqual(connection.events[:3], ["connect", "read-timeout", "request"])
        self.assertEqual(connection.auto_open, 0)
        self.assertEqual(connection.debuglevel, 0)

    def test_unverified_hostname_or_certificate_context_is_rejected(self):
        context = ssl.create_default_context()
        context.check_hostname = False
        contexts = [context, None, object()]
        unverified = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        unverified.check_hostname = False
        unverified.verify_mode = ssl.CERT_NONE
        contexts.append(unverified)
        for context in contexts:
            backend, factory = self.backend()
            with self.assertRaises(self.t.BackendFailure) as caught:
                backend.send(self.request(tls_context=context))
            self.assertEqual(caught.exception.category, self.t.ErrorCategory.MALFORMED_RESPONSE)
            factory.assert_not_called()

    def test_tls_key_logging_is_not_accepted(self):
        self.context.keylog_filename = str(self.directory / "synthetic-keylog")
        self.addCleanup(setattr, self.context, "keylog_filename", None)
        backend, factory = self.backend()
        with self.assertRaises(self.t.BackendFailure):
            backend.send(self.request())
        factory.assert_not_called()

    def test_actual_local_ca_round_trip_uses_verified_context(self):
        certificates = self.context.get_ca_certs(binary_form=True)
        if not certificates:
            self.skipTest("No installed local CA available for offline PEM round-trip.")
        path = self.directory / "synthetic-trust-bundle.pem"
        path.write_text(ssl.DER_cert_to_PEM_cert(certificates[0]), encoding="ascii")
        connection = MemoryConnection()
        transport, _, factory = self.transport(connection, trusted_ca=str(path))
        transport.request(self.t.HttpMethod.GET, ())
        context = factory.call_args.kwargs["context"]
        self.assertEqual(context.verify_mode, ssl.CERT_REQUIRED)
        self.assertTrue(context.check_hostname)
        self.assertGreater(context.cert_store_stats()["x509_ca"], 0)

    def test_bad_or_remote_ca_never_reaches_connection_factory(self):
        self.input_path.write_text(SECRET, encoding="utf-8")
        backend, factory = self.backend()
        for value in (str(self.input_path), str(self.directory / "missing.pem")):
            with self.assertRaises(self.contracts.ContractValidationError) as caught:
                self.t.HttpTransport(self.t.TransportConfig(
                    base_url="https://backend.invalid", connect_timeout=2, read_timeout=4,
                    trusted_ca=value,
                ), backend)
            self.safe(caught.exception)
        with patch("pathlib.Path.is_file") as is_file:
            for value in (r"\\backend.invalid\share\ca.pem", "https://backend.invalid/ca.pem"):
                with self.assertRaises(self.contracts.ContractValidationError):
                    self.t.TransportConfig(
                        base_url="https://backend.invalid", connect_timeout=2,
                        read_timeout=4, trusted_ca=value,
                    )
            is_file.assert_not_called()
        factory.assert_not_called()

    def test_direct_backend_timeout_limits_and_redirect_option_are_validated(self):
        backend, factory = self.backend()
        for name in ("connect_timeout", "read_timeout"):
            for value in (None, True, 0, -1, 301, float("inf"), float("nan"), "3"):
                with self.subTest(field=name, kind=type(value).__name__):
                    with self.assertRaises(self.t.BackendFailure):
                        backend.send(replace(self.request(), **{name: value}))
        with self.assertRaises(self.t.BackendFailure):
            backend.send(self.request(follow_redirects=True))
        factory.assert_not_called()

    def test_all_methods_construct_origin_form_encoded_targets_and_exact_bytes(self):
        for method in self.t.HttpMethod:
            with self.subTest(method=method):
                connection = MemoryConnection()
                transport, _, factory = self.transport(
                    connection, base_url="https://backend.invalid:8443",
                )
                body = None if method == self.t.HttpMethod.GET else SECRET.encode()
                transport.request(
                    method, ("api", "name ?#:@"), query=(("filter", "x&next=https://other.invalid"),),
                    headers={"Authorization": SECRET, "X-Custom": SECRET}, body=body,
                )
                sent = connection.requests[0]
                self.assertEqual(sent[:3], (
                    method.value,
                    "/api/name%20%3F%23%3A%40?filter=x%26next%3Dhttps%3A%2F%2Fother.invalid",
                    body,
                ))
                self.assertEqual(sent[3]["Authorization"], SECRET)
                self.assertEqual(sent[3]["Connection"], "close")
                self.assertEqual(factory.call_args.args, ("backend.invalid", 8443))
                self.assertEqual(factory.call_count, 1)

    def test_unsafe_direct_urls_headers_bodies_and_envelopes_fail_before_dispatch(self):
        backend, factory = self.backend()
        requests = [
            self.request(url=url) for url in (
                "http://backend.invalid", "https://user:password@backend.invalid",
                "https://backend.invalid/#" + SECRET, "https://backend.invalid:0/",
                "https://backend.invalid:65536/", "https://backend.invalid//other.invalid",
                "\nhttps://backend.invalid", "https://backend.invalid/a\r\n" + SECRET,
                "https://backend.invalid/a\\b", "https://backend.invalid/%zz", None,
            )
        ] + [
            self.request(headers=headers) for headers in (
                {"Host": "other.invalid"}, {"Content-Length": "3"}, {"Connection": "keep-alive"},
                {"Transfer-Encoding": "chunked"}, {"Proxy-Authorization": SECRET},
                {"Authorization": SECRET + "\r\ninjected: value"},
                {"Authorization": "a", "authorization": "b"}, {"bad name": SECRET},
            )
        ] + [
            self.request(body=SECRET.encode()), self.request(method="GET"),
            self.request(method=self.t.HttpMethod.POST, body=SECRET), None, {},
        ]
        for request in requests:
            with self.assertRaises(self.t.BackendFailure) as caught:
                backend.send(request)
            self.assertEqual(caught.exception.category, self.t.ErrorCategory.MALFORMED_RESPONSE)
            self.safe(caught.exception)
        factory.assert_not_called()

    def test_origin_is_pinned_but_default_port_and_case_are_equivalent(self):
        backend, factory = self.backend(MemoryConnection(), MemoryConnection())
        backend.send(self.request())
        backend.send(self.request(url="https://BACKEND.invalid:443/api"))
        for url in ("https://other.invalid/", "https://backend.invalid:8443/"):
            with self.assertRaises(self.t.BackendFailure):
                backend.send(self.request(url=url))
        self.assertEqual(factory.call_count, 2)

    def test_redirects_are_returned_to_transport_without_following_or_retrying(self):
        for status in (301, 302, 303, 307, 308):
            for headers in ([], [("Location", "https://other.invalid/" + SECRET)]):
                connection = MemoryConnection(MemoryResponse(status, headers=headers))
                transport, _, factory = self.transport(connection, read_retries=3)
                with self.assertRaises(self.t.TransportError) as caught:
                    transport.request(self.t.HttpMethod.GET, ())
                self.assertEqual(caught.exception.category, self.t.ErrorCategory.HTTP)
                self.assertEqual(caught.exception.status, status)
                self.safe(caught.exception)
                self.assertEqual(factory.call_count, 1)
                self.assertEqual(connection.response.close_calls, 1)
                self.assertEqual(connection.close_calls, 1)

    def test_get_retry_is_owned_only_by_transport_and_bounded(self):
        connections = [
            MemoryConnection(failure=("connect", ConnectionError(SECRET))),
            MemoryConnection(MemoryResponse(failure=("read", TimeoutError(SECRET)))),
            MemoryConnection(),
        ]
        transport, _, factory = self.transport(*connections, read_retries=2)
        self.assertEqual(transport.request(self.t.HttpMethod.GET, ()).status, 200)
        self.assertEqual(factory.call_count, 3)
        self.assertTrue(all(connection.close_calls == 1 for connection in connections))
        connections = [
            MemoryConnection(failure=("connect", TimeoutError(SECRET))) for _ in range(4)
        ]
        transport, _, factory = self.transport(*connections, read_retries=3)
        with self.assertRaises(self.t.TransportError) as caught:
            transport.request(self.t.HttpMethod.GET, ())
        self.assertEqual(caught.exception.attempts, 4)
        self.assertEqual(factory.call_count, 4)

    def test_direct_send_never_retries_and_tls_failure_is_not_transport_retried(self):
        for failure, category in (
            (ConnectionError(SECRET), self.t.ErrorCategory.CONNECTION),
            (TimeoutError(SECRET), self.t.ErrorCategory.TIMEOUT),
            (ssl.SSLError(SECRET), self.t.ErrorCategory.TLS),
        ):
            backend, factory = self.backend(MemoryConnection(failure=("connect", failure)))
            with self.assertRaises(self.t.BackendFailure) as caught:
                backend.send(self.request())
            self.assertEqual(caught.exception.category, category)
            self.safe(caught.exception)
            self.assertEqual(factory.call_count, 1)
        transport, _, factory = self.transport(
            MemoryConnection(failure=("connect", ssl.SSLCertVerificationError(SECRET))),
            read_retries=3,
        )
        with self.assertRaises(self.t.TransportError) as caught:
            transport.request(self.t.HttpMethod.GET, ())
        self.assertEqual(caught.exception.category, self.t.ErrorCategory.TLS)
        self.safe(caught.exception)
        self.assertEqual(factory.call_count, 1)

    def test_writes_are_indeterminate_without_replay_on_every_io_phase(self):
        for method in self.t.HttpMethod:
            if method == self.t.HttpMethod.GET:
                continue
            for stage in ("connect", "request", "getresponse", "read"):
                response = MemoryResponse(
                    failure=("read", TimeoutError(SECRET)) if stage == "read" else None,
                )
                connection = MemoryConnection(
                    response, failure=(stage, TimeoutError(SECRET)) if stage != "read" else None,
                )
                transport, _, factory = self.transport(connection, read_retries=3)
                with self.assertRaises(self.t.TransportError) as caught:
                    transport.request(method, ("api",), body=SECRET.encode())
                self.assertEqual(caught.exception.category, self.t.ErrorCategory.INDETERMINATE_WRITE)
                self.assertEqual(caught.exception.reason, self.t.ErrorCategory.TIMEOUT)
                self.assertEqual(factory.call_count, 1)
                self.assertEqual(connection.close_calls, 1)
                self.safe(caught.exception)

    def test_malformed_responses_and_ambiguous_framing_fail_closed_and_release(self):
        responses = [
            MemoryResponse(status=True), MemoryResponse(status=199), MemoryResponse(status=600),
            MemoryResponse(body=SECRET), MemoryResponse(headers={}), MemoryResponse(headers=[None]),
            MemoryResponse(headers=[([], SECRET)]), MemoryResponse(headers=[("X-Info", None)]),
            MemoryResponse(headers=[("X-Info", SECRET + "\r\ninjected: value")]),
            MemoryResponse(headers=[("Content-Length", "0"), ("content-length", "0")]),
            MemoryResponse(headers=[("Content-Length", "-1")]),
            MemoryResponse(headers=[("Content-Length", "2")], body=b"x"),
            MemoryResponse(headers=[("Transfer-Encoding", "gzip")]),
            MemoryResponse(headers=[("Content-Length", "0"), ("Transfer-Encoding", "chunked")]),
            MemoryResponse(headers=[("X-Info", "a"), ("x-info", "b")]),
            MemoryResponse(failure=("read", http.client.IncompleteRead(SECRET.encode()))),
            MemoryResponse(failure=("headers", http.client.BadStatusLine(SECRET))),
        ]
        for response in responses:
            connection = MemoryConnection(response)
            transport, _, factory = self.transport(connection, read_retries=3)
            with self.assertRaises(self.t.TransportError) as caught:
                transport.request(self.t.HttpMethod.GET, ())
            self.assertEqual(caught.exception.category, self.t.ErrorCategory.MALFORMED_RESPONSE)
            self.assertEqual(factory.call_count, 1)
            self.assertEqual(response.close_calls, 1)
            self.assertEqual(connection.close_calls, 1)
            self.safe(caught.exception)

    def test_multiple_session_cookies_are_processed_individually_not_flattened(self):
        first = MemoryConnection(MemoryResponse(headers=[
            ("Set-Cookie", "JSESSIONID=synthetic-session; Secure; HttpOnly; Path=/"),
            ("Set-Cookie", "theme=synthetic-theme; Secure; Path=/"),
            ("Set-Cookie", "wrong=synthetic-wrong; Domain=other.invalid; Path=/"),
            ("X-Info", "synthetic-info"),
        ]))
        second = MemoryConnection()
        backend, _ = self.backend(first, second)
        response = backend.send(self.request())
        backend.send(self.request(url="https://backend.invalid/api"))
        self.assertEqual(response.headers, {"X-Info": "synthetic-info"})
        self.assertIn("JSESSIONID=synthetic-session", self.cookie(second))
        self.assertIn("theme=synthetic-theme", self.cookie(second))
        self.assertNotIn("wrong", self.cookie(second))
        self.assertNotIn("Set-Cookie", repr(response))

    def test_gzip_and_harmless_repeated_headers_preserve_body_and_cookies(self):
        body = b'{"status":"ok","jsessionid":"synthetic-session"}'
        compressed = gzip.compress(body)
        first = MemoryConnection(MemoryResponse(body=compressed, headers=[
            ("Content-Type", "application/json"), ("Content-Encoding", "gzip"),
            ("Content-Length", str(len(compressed))),
            ("Cache-Control", "no-cache"), ("cache-control", "no-store"),
            ("Vary", "Accept-Encoding"), ("vary", "Accept"),
            ("Set-Cookie", "JSESSIONID=synthetic-session; Secure; Path=/"),
            ("Set-Cookie", "theme=synthetic-theme; Secure; Path=/"),
        ]))
        second = MemoryConnection()
        backend, _ = self.backend(first, second)
        response = backend.send(self.request())
        self.assertEqual(response.body, body)
        self.assertEqual(response.headers["Cache-Control"], "no-cache, no-store")
        self.assertEqual(response.headers["Vary"], "Accept-Encoding, Accept")
        self.assertFalse(any(name.lower() in ("content-length", "content-encoding", "set-cookie") for name in response.headers))
        backend.send(self.request(url="https://backend.invalid/api"))
        self.assertIn("JSESSIONID=synthetic-session", self.cookie(second))
        self.assertIn("theme=synthetic-theme", self.cookie(second))

    def test_gzip_decoded_limit_corruption_and_trailing_data_fail_closed(self):
        valid = gzip.compress(b"x" * 512)
        backend, _, deadline, _ = self.bounded_backend(
            MemoryConnection(MemoryResponse(body=valid, headers=[("Content-Encoding", "gzip")])),
            maximum=512,
        )
        self.assertEqual(len(backend.send(self.request(deadline=deadline)).body), 512)
        for status in (204, 304):
            backend, _ = self.backend(MemoryConnection(MemoryResponse(
                status=status, headers=[("Content-Encoding", "gzip")],
            )))
            self.assertEqual(backend.send(self.request()).body, b"")
        for body in (
            gzip.compress(b"x" * 513), valid[:-1], valid[:-8] + b"\x00" * 8,
            valid + b"trailing", valid + valid, SECRET.encode(),
        ):
            with self.subTest(size=len(body)):
                connection = MemoryConnection(MemoryResponse(body=body, headers=[
                    ("Content-Encoding", "gzip"), ("Content-Length", str(len(body))),
                    ("Set-Cookie", "JSESSIONID=uncommitted; Secure; Path=/"),
                ]))
                backend, _, deadline, _ = self.bounded_backend(connection, maximum=512)
                with self.assertRaises(self.t.BackendFailure) as caught:
                    backend.send(self.request(deadline=deadline))
                self.assertEqual(caught.exception.category, self.t.ErrorCategory.MALFORMED_RESPONSE)
                self.assertEqual(list(backend._cookies), [])
                self.assertEqual(connection.close_calls, 1)
                self.safe(caught.exception)

    def test_gzip_stdlib_chunked_response_is_decoded_after_framing_validation(self):
        body = b'{"status":"ok","jsessionid":"synthetic-session"}'
        compressed = gzip.compress(body)
        wire_body = f"{len(compressed):x}\r\n".encode() + compressed + b"\r\n0\r\n\r\n"
        connection = WireConnection(
            b"HTTP/1.1 200 OK\r\nTransfer-Encoding: chunked\r\nContent-Encoding: gzip\r\n\r\n" + wire_body,
        )
        self.addCleanup(connection.stream.close)
        backend, _ = self.backend(connection)
        self.assertEqual(backend.send(self.request()).body, body)
        self.assertTrue(connection.stream.closed)

    def test_sensitive_duplicate_headers_remain_rejected(self):
        for name in ("Content-Type", "Content-Encoding", "Transfer-Encoding", "Location", "WWW-Authenticate", "Authorization"):
            connection = MemoryConnection(MemoryResponse(headers=[
                (name, "identity"), (name.lower(), "identity"),
            ]))
            backend, _ = self.backend(connection)
            with self.assertRaises(self.t.BackendFailure):
                backend.send(self.request())
            self.assertEqual(connection.response.read_sizes, [])

    def test_failure_diagnostics_are_sanitized_stage_specific_and_opt_in(self):
        for response, failure, stage, reason in (
            (MemoryResponse(headers=[("Content-Encoding", SECRET)]), None, "content_encoding_validation", "unsupported_content_encoding"),
            (MemoryResponse(body=b"bad gzip", headers=[("Content-Encoding", "gzip")]), None, "gzip_decompression", "invalid_gzip_stream"),
            (MemoryResponse(headers=[("Cache-Control", SECRET + "\r\ninjected: value")]), None, "response_headers", "invalid_header_syntax"),
            (MemoryResponse(headers=[("Content-Length", "0"), ("content-length", "0")]), None, "response_headers", "unsafe_repeated_response_header"),
            (MemoryResponse(headers=[("Set-Cookie", "JSESSIONID=" + SECRET + "; Max-Age=" + SECRET)]), None, "response_cookie_extraction", "invalid_cookie_attributes"),
            (MemoryResponse(), ("request", OSError(SECRET)), "request_transmission", None),
        ):
            with self.subTest(stage=stage, reason=reason):
                connection = MemoryConnection(response, failure=failure)
                factory = Mock(return_value=connection)
                backend = self.b.StdlibHttpBackend(
                    connection_factory=factory, authorization=self.authorization(),
                    max_response_bytes=4096, diagnose_failures=True,
                )
                self.addCleanup(backend.close)
                stderr = io.StringIO()
                with redirect_stderr(stderr), self.assertRaises(self.t.BackendFailure) as caught:
                    backend.send(self.request(
                        method=self.t.HttpMethod.POST, url="https://backend.invalid/mgmt/system/user/login",
                        headers={"Authorization": SECRET}, body=SECRET.encode(),
                    ))
                diagnostic = json.loads(stderr.getvalue())
                self.assertNotIn(SECRET, stderr.getvalue())
                self.assertEqual(diagnostic["endpoint_path"], "/mgmt/system/user/login")
                self.assertEqual(diagnostic["http_method"], "POST")
                self.assertEqual(diagnostic["failure_stage"], stage)
                self.assertEqual(diagnostic["validation_reason"], reason)
                self.assertEqual(diagnostic["http_status"], None if failure else 200)
                self.safe(caught.exception)
        connection = MemoryConnection()
        backend = self.b.StdlibHttpBackend(
            connection_factory=Mock(return_value=connection), authorization=self.authorization(),
            max_response_bytes=4096, diagnose_failures=True,
        )
        self.addCleanup(backend.close)
        stderr = io.StringIO()
        with redirect_stderr(stderr):
            backend.send(self.request())
        self.assertEqual(stderr.getvalue(), "")

    def test_cookie_paths_and_expiration_are_respected(self):
        login = MemoryConnection(MemoryResponse(headers=[
            ("Set-Cookie", "scoped=synthetic-scope; Secure; Path=/restricted"),
            ("Set-Cookie", "expired=synthetic-old; Max-Age=0; Path=/"),
        ]))
        outside, inside = MemoryConnection(), MemoryConnection()
        backend, _ = self.backend(login, outside, inside)
        backend.send(self.request())
        backend.send(self.request(url="https://backend.invalid/api"))
        backend.send(self.request(url="https://backend.invalid/restricted/item"))
        self.assertEqual(self.cookie(outside), "")
        self.assertEqual(self.cookie(inside), "scoped=synthetic-scope")

    def test_stdlib_response_parser_consumes_chunked_and_eof_bodies_in_memory(self):
        for framing, wire_body in (
            (b"Transfer-Encoding: chunked\r\n", b"4\r\ntest\r\n0\r\n\r\n"),
            (b"Content-Length: 4\r\n", b"test"),
            (b"", b"test"),
        ):
            stream = io.BytesIO(
                b"HTTP/1.1 200 OK\r\n" + framing + b"Connection: close\r\n\r\n" + wire_body,
            )
            socket_double = Mock(spec=["makefile"])
            socket_double.makefile.return_value = stream
            response = http.client.HTTPResponse(socket_double, method="GET", debuglevel=0)
            response.begin()
            connection = MemoryConnection(response)
            backend, factory = self.backend(connection)
            self.assertEqual(backend.send(self.request()).body, b"test")
            self.assertTrue(stream.closed)
            self.assertEqual(factory.call_count, 1)
            self.assertEqual(connection.close_calls, 1)

    def test_stdlib_truncated_fixed_and_chunked_bodies_fail_safely_in_memory(self):
        for framing, wire_body in (
            (b"Content-Length: 999\r\n", SECRET.encode()),
            (b"Transfer-Encoding: chunked\r\n", b"ff\r\n" + SECRET.encode()),
        ):
            stream = io.BytesIO(b"HTTP/1.1 200 OK\r\n" + framing + b"\r\n" + wire_body)
            socket_double = Mock(spec=["makefile"])
            socket_double.makefile.return_value = stream
            response = http.client.HTTPResponse(socket_double, method="GET", debuglevel=0)
            response.begin()
            connection = MemoryConnection(response)
            transport, _, factory = self.transport(connection, read_retries=3)
            with self.assertRaises(self.t.TransportError) as caught:
                transport.request(self.t.HttpMethod.GET, ())
            self.assertEqual(caught.exception.category, self.t.ErrorCategory.MALFORMED_RESPONSE)
            self.safe(caught.exception)
            self.assertTrue(stream.closed)
            self.assertEqual(factory.call_count, 1)
            self.assertEqual(connection.close_calls, 1)

    def test_same_origin_roles_have_independent_cookies_and_credentials(self):
        source_login, source_read = self.login("synthetic-source"), MemoryConnection()
        destination_login, destination_read = self.login("synthetic-destination"), MemoryConnection()
        manager, _, _, _, _, resolver = self.manager(
            [source_login, source_read], [destination_login, destination_read],
        )
        source, destination = self.a.SessionRole.SOURCE, self.a.SessionRole.DESTINATION
        manager.authenticate(source)
        manager.authenticate(destination)
        manager.request(source, self.t.HttpMethod.GET, ("api",))
        manager.request(destination, self.t.HttpMethod.GET, ("api",))
        self.assertEqual(self.cookie(source_read), "JSESSIONID=synthetic-source")
        self.assertEqual(self.cookie(destination_read), "JSESSIONID=synthetic-destination")
        self.assertNotIn("Authorization", source_login.requests[0][3])
        self.assertNotIn("Authorization", source_read.requests[0][3])
        expected = "Basic " + base64.b64encode(
            b"synthetic/destination-user:synthetic/destination-password",
        ).decode("ascii")
        self.assertEqual(destination_login.requests[0][3]["Authorization"], expected)
        self.assertEqual(destination_read.requests[0][3]["Authorization"], expected)
        self.assertNotIn(b"destination", source_login.requests[0][2])
        self.assertNotIn(b"source", destination_login.requests[0][2])
        self.assertEqual(resolver.resolve.call_count, 2)

    def test_401_expires_only_its_role_without_renewal_or_retry(self):
        source_read = MemoryConnection(MemoryResponse(401))
        destination_read = MemoryConnection()
        manager, source_backend, _, source_factory, destination_factory, resolver = self.manager(
            [self.login("synthetic-source"), source_read],
            [self.login("synthetic-destination"), destination_read],
        )
        source, destination = self.a.SessionRole.SOURCE, self.a.SessionRole.DESTINATION
        manager.authenticate(source)
        manager.authenticate(destination)
        for _ in range(2):
            with self.assertRaises(self.a.AuthenticationError):
                manager.request(source, self.t.HttpMethod.GET, ("api",))
        self.assertEqual(manager.snapshot(source).state, self.a.SessionState.EXPIRED)
        self.assertTrue(manager.is_authenticated(destination))
        manager.request(destination, self.t.HttpMethod.GET, ("api",))
        self.assertEqual(tuple(source_backend._cookies), ())
        self.assertEqual(source_factory.call_count, 2)
        self.assertEqual(destination_factory.call_count, 2)
        self.assertEqual(resolver.resolve.call_count, 2)

    def test_403_does_not_expire_or_renew_the_session(self):
        denied, allowed = MemoryConnection(MemoryResponse(403)), MemoryConnection()
        manager, _, _, factory, _, resolver = self.manager(
            [self.login("synthetic-source"), denied, allowed],
        )
        role = self.a.SessionRole.SOURCE
        manager.authenticate(role)
        with self.assertRaises(self.t.TransportError) as caught:
            manager.request(role, self.t.HttpMethod.GET, ("api",))
        self.assertEqual(caught.exception.category, self.t.ErrorCategory.AUTHORIZATION)
        self.assertTrue(manager.is_authenticated(role))
        manager.request(role, self.t.HttpMethod.GET, ("api",))
        self.assertEqual(self.cookie(allowed), "JSESSIONID=synthetic-source")
        self.assertEqual(factory.call_count, 3)
        self.assertEqual(resolver.resolve.call_count, 1)

    def test_statuses_and_body_bytes_are_delegated_without_product_interpretation(self):
        for status in (200, 202, 204, 400, 408, 500, 503):
            body = b"" if status == 204 else b'{"synthetic":"not-a-completion-claim"}'
            transport, _, factory = self.transport(
                MemoryConnection(MemoryResponse(status, body)), read_retries=3,
            )
            if status < 300:
                self.assertEqual(transport.request(self.t.HttpMethod.GET, ()).body, body)
            else:
                with self.assertRaises(self.t.TransportError) as caught:
                    transport.request(self.t.HttpMethod.GET, ())
                self.assertEqual(caught.exception.status, status)
            self.assertEqual(factory.call_count, 1)

    def test_normal_cleanup_orders_response_before_connection(self):
        connection = MemoryConnection(MemoryResponse(body=b"synthetic"))
        backend, factory = self.backend(connection)
        self.assertEqual(backend.send(self.request()).body, b"synthetic")
        self.assertEqual(connection.events[-2:], ["response-close", "connection-close"])
        self.assertEqual(connection.response.read_sizes, [4097, 4088])
        backend.close()
        backend.close()
        self.assertEqual(connection.close_calls, 1)
        self.assertEqual(connection.response.close_calls, 1)
        self.assertEqual(factory.call_count, 1)

    def test_cleanup_failure_blocks_success_and_dispatch_until_explicit_local_cleanup(self):
        response = MemoryResponse(close_failures=2)
        connection = MemoryConnection(response, close_failures=1)
        transport, backend, factory = self.transport(connection, read_retries=3)
        with self.assertRaises(self.t.TransportError) as caught:
            transport.request(self.t.HttpMethod.GET, ())
        self.assertEqual(caught.exception.category, self.t.ErrorCategory.BACKEND)
        self.assertIn("Local backend resource cleanup failed.", caught.exception.__notes__)
        self.safe(caught.exception)
        self.assertEqual(connection.close_calls, 1)
        with self.assertRaises(self.t.TransportError):
            transport.request(self.t.HttpMethod.GET, ())
        self.assertEqual(factory.call_count, 1)
        with self.assertRaises(self.t.BackendFailure) as caught:
            backend.close()
        self.assertTrue(caught.exception.cleanup_failed)
        self.safe(caught.exception)
        backend.close()
        self.assertEqual(response.close_calls, 3)
        self.assertEqual(connection.close_calls, 2)

    def test_primary_failure_survives_cleanup_failure_and_writes_stay_indeterminate(self):
        for method in (self.t.HttpMethod.GET, self.t.HttpMethod.POST):
            connection = MemoryConnection(
                MemoryResponse(failure=("read", TimeoutError(SECRET)), close_failures=1),
            )
            transport, _, factory = self.transport(connection, read_retries=3)
            with self.assertRaises(self.t.TransportError) as caught:
                transport.request(method, (), body=None)
            self.assertEqual(caught.exception.reason, self.t.ErrorCategory.TIMEOUT)
            self.assertEqual(caught.exception.category, (
                self.t.ErrorCategory.TIMEOUT if method == self.t.HttpMethod.GET
                else self.t.ErrorCategory.INDETERMINATE_WRITE
            ))
            self.assertIn("Local backend resource cleanup failed.", caught.exception.__notes__)
            self.assertEqual(caught.exception.attempts, 1)
            self.assertEqual(factory.call_count, 1)
            self.assertEqual(connection.close_calls, 1)
            self.safe(caught.exception)

    def test_unexpected_factory_and_io_exceptions_are_sanitized_without_secret_logging(self):
        stdout, stderr = io.StringIO(), io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr), patch("logging.Logger._log") as log:
            for stage in ("factory", "connect", "request", "getresponse", "headers", "read"):
                failure = RuntimeError(SECRET)
                failure.add_note(SECRET)
                if stage == "factory":
                    backend = self.b.StdlibHttpBackend(
                        connection_factory=Mock(side_effect=failure),
                        authorization=self.authorization(), max_response_bytes=4096,
                    )
                    self.addCleanup(backend.close)
                else:
                    response = MemoryResponse(
                        failure=(stage, failure) if stage in ("headers", "read") else None,
                    )
                    backend, _ = self.backend(MemoryConnection(
                        response, failure=(stage, failure) if stage not in ("headers", "read") else None,
                    ))
                with self.assertRaises(self.t.BackendFailure) as caught:
                    backend.send(self.request(
                        url="https://backend.invalid/?marker=" + SECRET,
                        headers={"Authorization": SECRET, "Cookie": SECRET},
                    ))
                self.assertEqual(caught.exception.category, self.t.ErrorCategory.BACKEND)
                self.safe(caught.exception)
                self.assertNotIn(SECRET, repr(backend) + repr(self.request(body=None)))
            log.assert_not_called()
        self.assertEqual(stdout.getvalue() + stderr.getvalue(), "")

    def test_session_context_normal_and_exceptional_exit_clear_local_state_only(self):
        for exceptional in (False, True):
            manager, backend, _, factory, _, _ = self.manager([self.login("synthetic-source")])
            role = self.a.SessionRole.SOURCE
            try:
                with manager:
                    manager.authenticate(role)
                    if exceptional:
                        raise LookupError("synthetic application failure")
            except LookupError:
                self.assertTrue(exceptional)
            self.assertEqual(manager.snapshot(role).state, self.a.SessionState.CLOSED)
            self.assertEqual(tuple(backend._cookies), ())
            self.assertEqual(factory.call_count, 1)
            with self.assertRaises(self.a.AuthenticationError):
                manager.request(role, self.t.HttpMethod.GET, ())

    def test_session_cleanup_failure_does_not_prevent_other_role_cleanup(self):
        source_login = self.login("synthetic-source")
        source_login.response.close_failures = 2
        manager, _, _, source_factory, destination_factory, _ = self.manager(
            [source_login], [self.login("synthetic-destination")],
        )
        source, destination = self.a.SessionRole.SOURCE, self.a.SessionRole.DESTINATION
        with self.assertRaises(self.a.AuthenticationError):
            manager.authenticate(source)
        manager.authenticate(destination)
        with self.assertRaises(self.a.AuthenticationError) as caught:
            manager.close_all()
        self.assertEqual(caught.exception.failure.category, self.a.AuthenticationFailureCategory.CLEANUP)
        self.safe(caught.exception)
        self.assertEqual(manager.snapshot(source).state, self.a.SessionState.CLEANUP_FAILED)
        self.assertEqual(manager.snapshot(destination).state, self.a.SessionState.CLOSED)
        manager.close_all()
        self.assertEqual(manager.snapshot(source).state, self.a.SessionState.CLOSED)
        self.assertEqual(source_factory.call_count, 1)
        self.assertEqual(destination_factory.call_count, 1)

    def test_mock_only_manager_and_product_clients_reject_concrete_backend(self):
        backend, factory = self.backend()
        resolver = Mock()
        manager = self.s.SessionManager(lambda: backend, resolver, mock_only=True)
        self.addCleanup(manager.close_all)
        with self.assertRaises(self.a.AuthenticationError):
            manager.initialize(
                self.a.AuthenticationRequest(
                    self.a.SessionRole.SOURCE, "vision", "0.0-test",
                    self.a.CredentialReference("synthetic/source"),
                ),
                self.t.TransportConfig(
                    base_url="https://backend.invalid", connect_timeout=2, read_timeout=4,
                ),
            )
        factory.assert_not_called()
        resolver.resolve.assert_not_called()
        for product, client, version in (
            ("vision", self.p.VisionClient, "5.4.9"),
            ("cyber-controller", self.p.CyberControllerClient, "10.10.7"),
        ):
            manager, _, _, factory, _, resolver = self.manager([], source_product=product)
            for candidate in ("0.0-test", version):
                with self.assertRaises(self.c.ProductClientError):
                    client(manager, self.a.SessionRole.SOURCE, candidate)
            factory.assert_not_called()
            resolver.resolve.assert_not_called()

    def wire(self, status=200, *, headers=(), body=b"", **faults):
        wire = (
            f"HTTP/1.1 {status} Synthetic\r\nConnection: close\r\n".encode("ascii")
            + b"".join(f"{name}: {value}\r\n".encode("ascii") for name, value in headers)
            + f"Content-Length: {len(body)}\r\n\r\n".encode("ascii") + body
        )
        connection = WireConnection(wire, **faults)
        self.addCleanup(connection.stream.close)
        return connection

    def test_correction_401_body_timeout_expires_only_affected_role_without_retry(self):
        for affected in self.a.SessionRole:
            rejected = self.wire(401, body=b"x", read_error=TimeoutError(SECRET))
            source_connections = [self.login("synthetic-source"), MemoryConnection()]
            destination_connections = [self.login("synthetic-destination"), MemoryConnection()]
            target = source_connections if affected == self.a.SessionRole.SOURCE else destination_connections
            target.insert(1, rejected)
            manager, source, destination, sf, df, _ = self.manager(
                source_connections, destination_connections, read_retries=3,
            )
            for role in self.a.SessionRole:
                manager.authenticate(role)
            with self.assertRaises(self.a.AuthenticationError) as caught:
                manager.request(affected, self.t.HttpMethod.GET, ("api",))
            self.assertEqual(caught.exception.failure.status, 401)
            self.assertEqual(caught.exception.failure.transport_category, self.t.ErrorCategory.AUTHENTICATION)
            self.assertEqual(manager.snapshot(affected).state, self.a.SessionState.EXPIRED)
            self.safe(caught.exception)
            with self.assertRaises(self.a.AuthenticationError):
                manager.request(affected, self.t.HttpMethod.GET, ("api",))
            self.assertEqual((sf if affected == self.a.SessionRole.SOURCE else df).call_count, 2)
            self.assertEqual(tuple((source if affected == self.a.SessionRole.SOURCE else destination)._cookies), ())
            other = self.a.SessionRole.DESTINATION if affected == self.a.SessionRole.SOURCE else self.a.SessionRole.SOURCE
            self.assertTrue(manager.is_authenticated(other))
            manager.request(other, self.t.HttpMethod.GET, ("api",))

    def test_correction_401_explicit_cleanup_failures_preserve_status_and_reporting(self):
        for phase in ("response", "connection"):
            rejected = MemoryConnection(
                MemoryResponse(401, close_failures=int(phase == "response")),
                close_failures=int(phase == "connection"),
            )
            manager, _, _, factory, _, _ = self.manager(
                [self.login("synthetic-source"), rejected, MemoryConnection()], read_retries=3,
            )
            role = self.a.SessionRole.SOURCE
            manager.authenticate(role)
            with self.assertRaises(self.a.AuthenticationError) as caught:
                manager.request(role, self.t.HttpMethod.GET, ("api",))
            self.assertEqual(caught.exception.failure.status, 401)
            self.assertIn("Local backend resource cleanup failed.", caught.exception.__notes__)
            self.assertEqual(manager.snapshot(role).state, self.a.SessionState.EXPIRED)
            self.assertEqual(factory.call_count, 2)
            self.safe(caught.exception)

    def test_correction_403_body_timeout_preserves_authorization_without_expiration(self):
        rejected = self.wire(403, body=b"x", read_error=TimeoutError(SECRET))
        manager, _, _, factory, _, _ = self.manager(
            [self.login("synthetic-source"), rejected, MemoryConnection()], read_retries=3,
        )
        role = self.a.SessionRole.SOURCE
        manager.authenticate(role)
        with self.assertRaises(self.t.TransportError) as caught:
            manager.request(role, self.t.HttpMethod.GET, ("api",))
        self.assertEqual(caught.exception.category, self.t.ErrorCategory.AUTHORIZATION)
        self.assertEqual(caught.exception.status, 403)
        self.assertEqual(caught.exception.backend_failure, self.t.ErrorCategory.TIMEOUT)
        self.assertTrue(manager.is_authenticated(role))
        self.assertEqual(factory.call_count, 2)
        manager.request(role, self.t.HttpMethod.GET, ("api",))
        self.safe(caught.exception)

    def test_correction_known_server_failure_keeps_http_priority_and_write_uncertainty(self):
        for phase in ("read", "cleanup"):
            rejected = (
                self.wire(500, body=b"x", read_error=TimeoutError(SECRET))
                if phase == "read" else MemoryConnection(MemoryResponse(500, close_failures=1))
            )
            transport, _, factory = self.transport(rejected, MemoryConnection(), read_retries=3)
            with self.assertRaises(self.t.TransportError) as caught:
                transport.request(self.t.HttpMethod.POST, ("api",), body=SECRET.encode())
            self.assertEqual(caught.exception.category, self.t.ErrorCategory.INDETERMINATE_WRITE)
            self.assertEqual(caught.exception.reason, self.t.ErrorCategory.HTTP)
            self.assertEqual(caught.exception.status, 500)
            self.assertEqual(caught.exception.cleanup_failed, phase == "cleanup")
            self.assertEqual(factory.call_count, 1)
            self.safe(caught.exception)

    def test_correction_stdlib_implicit_socket_close_failure_blocks_retry_and_reuse(self):
        connection = self.wire(socket_failures=1)
        transport, backend, factory = self.transport(connection, MemoryConnection(), read_retries=3)
        with self.assertRaises(self.t.TransportError) as caught:
            transport.request(self.t.HttpMethod.GET, ())
        self.assertEqual(caught.exception.category, self.t.ErrorCategory.BACKEND)
        self.assertEqual(caught.exception.status, 200)
        self.assertTrue(caught.exception.cleanup_failed)
        self.assertEqual(caught.exception.attempts, 1)
        self.assertEqual(factory.call_count, 1)
        with self.assertRaises(self.t.TransportError):
            transport.request(self.t.HttpMethod.GET, ())
        self.assertEqual(factory.call_count, 1)
        self.assertEqual(connection.original_socket.close_calls, 1)
        backend.close()
        self.assertEqual(connection.original_socket.close_calls, 2)
        self.safe(caught.exception)

    def test_correction_401_implicit_socket_close_failure_still_expires_session(self):
        rejected = self.wire(401, socket_failures=1)
        manager, _, _, factory, _, _ = self.manager(
            [self.login("synthetic-source"), rejected, MemoryConnection()], read_retries=3,
        )
        role = self.a.SessionRole.SOURCE
        manager.authenticate(role)
        with self.assertRaises(self.a.AuthenticationError) as caught:
            manager.request(role, self.t.HttpMethod.GET, ("api",))
        self.assertEqual(caught.exception.failure.status, 401)
        self.assertIn("Local backend resource cleanup failed.", caught.exception.__notes__)
        self.assertEqual(manager.snapshot(role).state, self.a.SessionState.EXPIRED)
        self.assertEqual(factory.call_count, 2)
        self.safe(caught.exception)

    def test_correction_stdlib_file_close_failure_during_body_blocks_success(self):
        connection = self.wire(body=b"abc", file_failures=1)
        transport, backend, factory = self.transport(connection, MemoryConnection(), read_retries=3)
        with self.assertRaises(self.t.TransportError) as caught:
            transport.request(self.t.HttpMethod.GET, ())
        self.assertEqual(caught.exception.category, self.t.ErrorCategory.BACKEND)
        self.assertTrue(caught.exception.cleanup_failed)
        self.assertEqual(caught.exception.status, 200)
        self.assertEqual(factory.call_count, 1)
        self.assertFalse(connection.stream.closed)
        backend.close()
        self.assertTrue(connection.stream.closed)
        self.safe(caught.exception)

    def test_correction_primary_read_and_parse_errors_survive_implicit_cleanup_failure(self):
        for phase in ("read", "parse"):
            connection = self.wire(
                body=b"x", file_failures=1,
                read_error=TimeoutError(SECRET) if phase == "read" else None,
            )
            if phase == "parse":
                connection.stream.seek(0)
                connection.stream.write(b"BAD-STATUS " + SECRET.encode() + b"\r\n\r\n")
                connection.stream.truncate()
                connection.stream.seek(0)
            transport, _, factory = self.transport(connection, MemoryConnection(), read_retries=3)
            with self.assertRaises(self.t.TransportError) as caught:
                transport.request(self.t.HttpMethod.GET, ())
            expected = self.t.ErrorCategory.TIMEOUT if phase == "read" else self.t.ErrorCategory.MALFORMED_RESPONSE
            self.assertEqual(caught.exception.category, expected)
            self.assertEqual(caught.exception.status, 200 if phase == "read" else None)
            self.assertTrue(caught.exception.cleanup_failed)
            self.assertEqual(factory.call_count, 1)
            self.safe(caught.exception)

    def test_correction_malformed_max_age_cookie_updates_are_atomic_and_sanitized(self):
        for attribute in ("Max-Age", "Max-Age=", "Max-Age=not-an-integer", "Max-Age=" + "9" * 1000):
            initial = MemoryConnection(MemoryResponse(headers=[
                ("Set-Cookie", "JSESSIONID=synthetic-old; Secure; Path=/"),
                ("Set-Cookie", "theme=synthetic-old-theme; Path=/"),
            ]))
            update = self.wire(headers=(
                ("Set-Cookie", "theme=deleted; Max-Age=0; Path=/"),
                ("Set-Cookie", "JSESSIONID=synthetic-new; Secure; Path=/"),
                ("Set-Cookie", "broken=" + SECRET + "; " + attribute),
            ))
            next_connection = MemoryConnection()
            backend, _ = self.backend(initial, update, next_connection)
            backend.send(self.request())
            before = [(cookie.name, cookie.value) for cookie in backend._cookies]
            stdout, stderr = io.StringIO(), io.StringIO()
            with warnings.catch_warnings(), redirect_stdout(stdout), redirect_stderr(stderr):
                warnings.simplefilter("always")
                with self.assertRaises(self.t.BackendFailure) as caught:
                    backend.send(self.request())
            self.assertEqual(caught.exception.category, self.t.ErrorCategory.MALFORMED_RESPONSE)
            self.safe(caught.exception)
            self.assertEqual(stdout.getvalue() + stderr.getvalue(), "")
            self.assertEqual([(cookie.name, cookie.value) for cookie in backend._cookies], before)
            backend.send(self.request())
            self.assertIn("JSESSIONID=synthetic-old", self.cookie(next_connection))
            self.assertIn("theme=synthetic-old-theme", self.cookie(next_connection))
            self.assertNotIn(SECRET, self.cookie(next_connection))

    def test_correction_unexpected_cookie_parser_failure_is_explicit_not_warning_fallback(self):
        initial = self.login("synthetic-old")
        update = self.wire(headers=(("Set-Cookie", "JSESSIONID=" + SECRET + "; Path=/"),))
        backend, _ = self.backend(initial, update)
        backend.send(self.request())
        before = [(cookie.name, cookie.value) for cookie in backend._cookies]
        stderr = io.StringIO()
        with (
            patch("http.cookiejar.CookieJar._cookies_from_attrs_set", side_effect=RuntimeError(SECRET)),
            warnings.catch_warnings(), redirect_stderr(stderr),
        ):
            warnings.simplefilter("always")
            with self.assertRaises(self.t.BackendFailure) as caught:
                backend.send(self.request())
        self.assertEqual(caught.exception.category, self.t.ErrorCategory.BACKEND)
        self.assertEqual(stderr.getvalue(), "")
        self.assertEqual([(cookie.name, cookie.value) for cookie in backend._cookies], before)
        self.safe(caught.exception)

    def test_correction_malformed_wire_header_defects_fail_closed(self):
        for fields in (
            b"Colonless\r\n",
            b"X-Info: " + SECRET.encode() + b"\r\nColonless\r\nX-Info: second\r\n",
            b"Content-Length: 0\r\nColonless\r\nContent-Length: 9\r\n",
            b" leading-continuation\r\nX-Info: value\r\n",
        ):
            connection = WireConnection(b"HTTP/1.1 200 OK\r\n" + fields + b"\r\n")
            self.addCleanup(connection.stream.close)
            transport, _, factory = self.transport(connection, MemoryConnection(), read_retries=3)
            with self.assertRaises(self.t.TransportError) as caught:
                transport.request(self.t.HttpMethod.GET, ())
            self.assertEqual(caught.exception.category, self.t.ErrorCategory.MALFORMED_RESPONSE)
            self.assertEqual(factory.call_count, 1)
            self.assertTrue(connection.stream.closed)
            self.safe(caught.exception)

    def test_correction_valid_wire_headers_and_repeated_header_policy_are_preserved(self):
        connection = self.wire(headers=(
            ("Set-Cookie", "JSESSIONID=synthetic-valid; Secure; Path=/"),
            ("Set-Cookie", "theme=synthetic-theme; Path=/"),
            ("X-Info", "synthetic-valid"),
        ))
        following = MemoryConnection()
        backend, _ = self.backend(connection, following)
        response = backend.send(self.request())
        self.assertEqual(response.headers["X-Info"], "synthetic-valid")
        backend.send(self.request())
        self.assertIn("JSESSIONID=synthetic-valid", self.cookie(following))
        self.assertIn("theme=synthetic-theme", self.cookie(following))
        duplicate = self.wire(headers=(("X-Info", "one"), ("x-info", "two")))
        backend, _ = self.backend(duplicate)
        with self.assertRaises(self.t.BackendFailure) as caught:
            backend.send(self.request())
        self.assertEqual(caught.exception.category, self.t.ErrorCategory.MALFORMED_RESPONSE)
        self.safe(caught.exception)

    def test_correction_login_401_retains_status_and_cleanup_diagnostics(self):
        rejected = self.wire(401, body=b"x", read_error=TimeoutError(SECRET), file_failures=1)
        manager, _, _, factory, _, _ = self.manager([rejected, MemoryConnection()], read_retries=3)
        with self.assertRaises(self.a.AuthenticationError) as caught:
            manager.authenticate(self.a.SessionRole.SOURCE)
        self.assertEqual(caught.exception.failure.status, 401)
        self.assertEqual(caught.exception.failure.category, self.a.AuthenticationFailureCategory.HTTP_REJECTION)
        self.assertIn("Local backend resource cleanup failed.", caught.exception.__notes__)
        self.assertEqual(factory.call_count, 1)
        self.safe(caught.exception)

    def test_correction_failed_cookie_update_preserves_role_and_origin_isolation(self):
        for cleanup_failure in (False, True):
            update = MemoryConnection(MemoryResponse(
                headers=[("Set-Cookie", "JSESSIONID=" + SECRET + "; Secure; Path=/"
                          + ("" if cleanup_failure else "; Max-Age"))],
                close_failures=int(cleanup_failure),
            ))
            destination_request = MemoryConnection()
            manager, source, destination, sf, df, _ = self.manager(
                [self.login("synthetic-source"), update, MemoryConnection()],
                [self.login("synthetic-destination"), destination_request],
                read_retries=3,
            )
            for role in self.a.SessionRole:
                manager.authenticate(role)
            with self.assertRaises(self.t.TransportError) as caught:
                manager.request(self.a.SessionRole.SOURCE, self.t.HttpMethod.GET, ("api",))
            self.assertEqual(caught.exception.cleanup_failed, cleanup_failure)
            self.assertEqual(caught.exception.category, (
                self.t.ErrorCategory.BACKEND if cleanup_failure
                else self.t.ErrorCategory.MALFORMED_RESPONSE
            ))
            self.assertEqual([(c.name, c.value) for c in source._cookies],
                             [("JSESSIONID", "synthetic-source")])
            self.assertEqual([(c.name, c.value) for c in destination._cookies],
                             [("JSESSIONID", "synthetic-destination")])
            manager.request(self.a.SessionRole.DESTINATION, self.t.HttpMethod.GET, ("api",))
            self.assertIn("JSESSIONID=synthetic-destination", self.cookie(destination_request))
            self.assertNotIn("synthetic-source", self.cookie(destination_request))
            self.assertNotIn(SECRET, self.cookie(destination_request))
            self.assertEqual((sf.call_count, df.call_count), (2, 2))
            with self.assertRaises(self.t.BackendFailure):
                source.send(self.request(url="https://other.invalid/"))
            self.assertEqual(sf.call_count, 2)
            self.safe(caught.exception)

    def test_safety_actual_byte_limit_with_missing_and_misleading_lengths(self):
        for body, length, accepted in (
            (b"1234", None, True), (b"1234", "4", True),
            (b"12345", None, False), (b"12345", "4", False),
            (b"1234", "3", False), (b"123", "4", False),
        ):
            response = MemoryResponse(
                body=body, headers=[] if length is None else [("Content-Length", length)],
            )
            connection = MemoryConnection(response)
            backend, factory, deadline, _ = self.bounded_backend(connection)
            if accepted:
                self.assertEqual(backend.send(self.request(deadline=deadline)).body, body)
            else:
                with self.assertRaises(self.t.BackendFailure) as caught:
                    backend.send(self.request(deadline=deadline))
                self.assertEqual(caught.exception.category, self.t.ErrorCategory.MALFORMED_RESPONSE)
                self.safe(caught.exception)
            self.assertTrue(all(0 < size <= 5 for size in response.read_sizes))
            self.assertEqual(factory.call_count, 1)
            self.assertEqual((response.close_calls, connection.close_calls), (1, 1))

    def test_safety_declared_oversize_is_rejected_without_reading_or_retaining_body(self):
        response = MemoryResponse(
            body=SECRET.encode(), headers=[("Content-Length", "1000000000")],
        )
        connection = MemoryConnection(response)
        backend, _, deadline, _ = self.bounded_backend(connection)
        with self.assertRaises(self.t.BackendFailure) as caught:
            backend.send(self.request(deadline=deadline))
        self.safe(caught.exception)
        self.assertEqual(response.read_sizes, [])
        self.assertEqual(backend._pending, [])
        self.assertNotIn(SECRET, repr(vars(backend)))
        self.assertEqual((response.close_calls, connection.close_calls), (1, 1))

    def test_safety_binary_incremental_reads_preserve_exact_limit(self):
        body = bytes(range(256)) * 257
        response = IncrementalResponse(body=body, chunk_size=1000)
        backend, _, deadline, _ = self.bounded_backend(
            MemoryConnection(response), maximum=len(body),
        )
        self.assertEqual(backend.send(self.request(deadline=deadline)).body, body)
        self.assertGreater(len(response.read_sizes), 2)
        self.assertLessEqual(max(response.read_sizes), 65536)
        self.assertEqual(response.read_sizes[-1], 1)

    def test_safety_framing_and_content_transformations_are_conservatively_rejected(self):
        for headers in (
            [("Content-Length", "4, 4")], [("Content-Length", "+4")],
            [("Content-Length", "4"), ("content-length", "5")],
            [("Content-Length", "4"), ("Transfer-Encoding", "chunked")],
            [("Transfer-Encoding", "chunked, gzip")],
            [("Content-Encoding", "deflate")], [("Content-Encoding", "br")],
            [("Content-Encoding", "identity, gzip")],
        ):
            response = MemoryResponse(body=SECRET.encode(), headers=headers)
            backend, _, deadline, _ = self.bounded_backend(MemoryConnection(response))
            with self.assertRaises(self.t.BackendFailure) as caught:
                backend.send(self.request(deadline=deadline))
            self.safe(caught.exception)
            self.assertEqual(response.read_sizes, [])
            self.assertEqual(caught.exception.category, self.t.ErrorCategory.MALFORMED_RESPONSE)

    def test_safety_wire_chunked_and_eof_limits_close_streams(self):
        for size in (4, 5):
            for framing, payload in (
                (b"", b"x" * size),
                (b"Transfer-Encoding: chunked\r\n",
                 b"".join(b"1\r\nx\r\n" for _ in range(size)) + b"0\r\n\r\n"),
            ):
                connection = WireConnection(b"HTTP/1.1 200 OK\r\n" + framing + b"\r\n" + payload)
                self.addCleanup(connection.stream.close)
                backend, _, deadline, _ = self.bounded_backend(connection)
                if size == 4:
                    self.assertEqual(backend.send(self.request(deadline=deadline)).body, b"xxxx")
                else:
                    with self.assertRaises(self.t.BackendFailure) as caught:
                        backend.send(self.request(deadline=deadline))
                    self.assertEqual(caught.exception.category, self.t.ErrorCategory.MALFORMED_RESPONSE)
                self.assertTrue(connection.stream.closed)
                self.assertEqual(backend._pending, [])

    def test_safety_chunk_delimiters_are_validated_before_success(self):
        for delimiter in (b"\r\n", b"XY", b"\rX", b"\n"):
            payload = b"\x00\xff"
            connection = WireConnection(
                b"HTTP/1.1 200 OK\r\nTransfer-Encoding: chunked\r\n\r\n"
                + b"1\r\n" + payload[:1] + delimiter
                + b"1\r\n" + payload[1:] + delimiter + b"0\r\n\r\n",
            )
            self.addCleanup(connection.stream.close)
            backend, factory, deadline, _ = self.bounded_backend(connection, maximum=2)
            if delimiter == b"\r\n":
                self.assertEqual(backend.send(self.request(deadline=deadline)).body, payload)
            else:
                with self.assertRaises(self.t.BackendFailure) as caught:
                    backend.send(self.request(deadline=deadline))
                self.assertEqual(caught.exception.category, self.t.ErrorCategory.MALFORMED_RESPONSE)
                self.assertEqual(caught.exception.status, 200)
                self.safe(caught.exception)
            self.assertTrue(connection.stream.closed)
            self.assertEqual(factory.call_count, 1)
            self.assertEqual(backend._pending, [])

    def test_safety_deadline_expired_before_factory_has_no_resources(self):
        backend, factory, deadline, clock = self.bounded_backend()
        clock.return_value = 5.0
        with self.assertRaises(self.t.BackendFailure) as caught:
            backend.send(self.request(deadline=deadline))
        self.assertEqual(caught.exception.category, self.t.ErrorCategory.TIMEOUT)
        factory.assert_not_called()
        self.assertEqual(backend._pending, [])
        self.safe(caught.exception)

    def test_safety_deadline_checks_factory_connect_dispatch_and_headers(self):
        for stage in ("factory", "connect", "request", "getresponse", "getheaders"):
            connection = MemoryConnection()
            backend, factory, deadline, clock = self.bounded_backend(connection)
            if stage == "factory":
                def expired_factory(*args, **kwargs):
                    clock.return_value = 5.0
                    return connection
                factory.side_effect = expired_factory
            else:
                owner = connection.response if stage == "getheaders" else connection
                original = getattr(owner, stage)
                def expire(*args, **kwargs):
                    result = original(*args, **kwargs)
                    clock.return_value = 5.0
                    return result
                self.stack.enter_context(patch.object(owner, stage, side_effect=expire))
            with self.assertRaises(self.t.BackendFailure) as caught:
                backend.send(self.request(deadline=deadline))
            self.assertEqual(caught.exception.category, self.t.ErrorCategory.TIMEOUT)
            self.assertEqual(connection.close_calls, 1)
            self.assertEqual(connection.requests == [], stage in ("factory", "connect"))
            self.assertEqual(connection.response.read_sizes, [])
            self.safe(caught.exception)

    def test_safety_slow_incremental_chunks_cannot_renew_deadline(self):
        clock = Mock(return_value=0.0)
        response = IncrementalResponse(
            body=b"x" * 100, clock=clock, delay=1.0,
            headers=[("Set-Cookie", "new=" + SECRET + "; Path=/")],
        )
        backend, _, deadline, _ = self.bounded_backend(
            MemoryConnection(response), maximum=100, clock=clock,
        )
        with self.assertRaises(self.t.BackendFailure) as caught:
            backend.send(self.request(deadline=deadline))
        self.assertEqual(caught.exception.category, self.t.ErrorCategory.TIMEOUT)
        self.assertEqual(len(response.read_sizes), 5)
        self.assertEqual(tuple(backend._cookies), ())
        self.safe(caught.exception)

    def test_safety_wire_reads_recheck_deadline_inside_stdlib_chunk_loop(self):
        clock = Mock(return_value=0.0)
        connection = WireConnection(
            b"HTTP/1.1 200 OK\r\nTransfer-Encoding: chunked\r\n\r\n"
            + b"1\r\nx\r\n" * 20 + b"0\r\n\r\n",
        )
        self.addCleanup(connection.stream.close)
        original = connection.stream.read
        def slow_read(size):
            clock.return_value += 2.0
            return original(size)
        self.stack.enter_context(patch.object(connection.stream, "read", side_effect=slow_read))
        backend, _, deadline, _ = self.bounded_backend(connection, maximum=100, clock=clock)
        with self.assertRaises(self.t.BackendFailure) as caught:
            backend.send(self.request(deadline=deadline))
        self.assertEqual(caught.exception.category, self.t.ErrorCategory.TIMEOUT)
        self.assertLessEqual(clock.return_value, 6.0)
        self.assertTrue(connection.stream.closed)
        self.safe(caught.exception)

    def test_safety_remaining_budget_is_recalculated_between_phases(self):
        connection = MemoryConnection()
        backend, factory, deadline, clock = self.bounded_backend(connection)
        def connect():
            clock.return_value = 2.0
        def dispatch(*args, **kwargs):
            clock.return_value = 4.0
        self.stack.enter_context(patch.object(connection, "connect", side_effect=connect))
        self.stack.enter_context(patch.object(connection, "request", side_effect=dispatch))
        backend.send(self.request(deadline=deadline))
        self.assertEqual(factory.call_args.kwargs["timeout"], 2)
        self.assertEqual(connection.sock.timeouts[:2], [3.0, 1.0])
        self.assertTrue(all(0 < timeout <= 1 for timeout in connection.sock.timeouts[1:]))

    def test_safety_deadline_and_cleanup_failures_preserve_known_401_and_403(self):
        for status in (200, 401, 403, 500):
            connection = MemoryConnection(MemoryResponse(status, close_failures=1))
            backend, factory, deadline, clock = self.bounded_backend(connection)
            original = connection.response.read
            def expired_read(size):
                result = original(size)
                clock.return_value = 5.0
                return result
            self.stack.enter_context(patch.object(connection.response, "read", side_effect=expired_read))
            transport = self.t.HttpTransport(self.t.TransportConfig(
                base_url="https://backend.invalid", connect_timeout=2, read_timeout=4,
                read_retries=3, operation_timeout=5,
            ), backend, clock=clock)
            with self.assertRaises(self.t.TransportError) as caught:
                transport.request(self.t.HttpMethod.GET, ())
            self.assertEqual(caught.exception.status, status)
            self.assertTrue(caught.exception.cleanup_failed)
            self.assertEqual(caught.exception.category, {
                200: self.t.ErrorCategory.TIMEOUT, 401: self.t.ErrorCategory.AUTHENTICATION,
                403: self.t.ErrorCategory.AUTHORIZATION, 500: self.t.ErrorCategory.HTTP,
            }[status])
            self.assertEqual(caught.exception.backend_failure, self.t.ErrorCategory.TIMEOUT)
            self.assertEqual(caught.exception.attempts, 1)
            self.assertEqual(factory.call_count, 1)
            self.safe(caught.exception)

    def test_safety_cleanup_deadline_expiry_blocks_cookie_commit_and_success(self):
        connection = self.login("synthetic-new")
        backend, _, deadline, clock = self.bounded_backend(connection, maximum=100)
        original = connection.close
        def slow_close():
            original()
            clock.return_value = 5.0
        self.stack.enter_context(patch.object(connection, "close", side_effect=slow_close))
        with self.assertRaises(self.t.BackendFailure) as caught:
            backend.send(self.request(deadline=deadline))
        self.assertEqual(caught.exception.category, self.t.ErrorCategory.TIMEOUT)
        self.assertEqual(tuple(backend._cookies), ())
        self.safe(caught.exception)

    def test_safety_expired_401_still_expires_session_without_other_role_loss(self):
        clock = Mock(return_value=0.0)
        rejected = MemoryConnection(MemoryResponse(401, close_failures=1))
        manager, _, _, sf, _, _ = self.manager(
            [self.login("synthetic-source"), rejected],
            [self.login("synthetic-destination"), MemoryConnection()], read_retries=3,
        )
        for role in self.a.SessionRole:
            manager.authenticate(role)
        source = self.a.SessionRole.SOURCE
        transport = manager._sessions[source].transport
        transport._clock = clock
        transport._config = replace(transport._config, operation_timeout=5)
        def expire(size):
            clock.return_value = 5.0
            return b""
        self.stack.enter_context(patch.object(rejected.response, "read", side_effect=expire))
        with self.assertRaises(self.a.AuthenticationError) as caught:
            manager.request(source, self.t.HttpMethod.GET, ("api",))
        self.assertEqual(caught.exception.failure.status, 401)
        self.assertEqual(manager.snapshot(source).state, self.a.SessionState.EXPIRED)
        self.assertIn("Local backend resource cleanup failed.", caught.exception.__notes__)
        self.assertTrue(manager.is_authenticated(self.a.SessionRole.DESTINATION))
        manager.request(self.a.SessionRole.DESTINATION, self.t.HttpMethod.GET, ("api",))
        self.assertEqual(sf.call_count, 2)
        self.safe(caught.exception)

    def test_safety_absent_policy_budget_or_deadline_is_default_deny(self):
        for missing in ("authorization", "max_response_bytes", "deadline"):
            factory = Mock()
            values = dict(
                connection_factory=factory, authorization=self.authorization(),
                max_response_bytes=4,
            )
            request = self.request()
            if missing == "deadline":
                request = replace(request, deadline=None)
            else:
                values[missing] = None
            backend = self.b.StdlibHttpBackend(**values)
            self.addCleanup(backend.close)
            with self.assertRaises(self.t.BackendFailure) as caught:
                backend.send(request)
            self.assertEqual(caught.exception.category, self.t.ErrorCategory.SAFETY_POLICY)
            factory.assert_not_called()

    def test_safety_builtin_dispatch_fails_before_dns_for_host_ipv4_and_ipv6(self):
        for origin in (
            "https://backend.invalid", "https://192.0.2.1", "https://[2001:db8::1]",
        ):
            backend = self.b.StdlibHttpBackend(
                authorization=self.b.DestinationAuthorization(origin, ((self.t.HttpMethod.GET, "/"),)),
                max_response_bytes=4,
            )
            self.addCleanup(backend.close)
            with self.assertRaises(self.t.BackendFailure) as caught:
                backend.send(self.request(url=origin + "/"))
            self.assertEqual(caught.exception.category, self.t.ErrorCategory.SAFETY_POLICY)
            self.assertEqual(backend._pending, [])
            self.assertIsNone(backend._origin)
            self.safe(caught.exception)

    def test_safety_resolution_failure_double_releases_connection_without_dispatch(self):
        for failure, category in (
            (TimeoutError(SECRET), self.t.ErrorCategory.TIMEOUT),
            (OSError(SECRET), self.t.ErrorCategory.CONNECTION),
        ):
            connection = MemoryConnection(failure=("connect", failure))
            backend, factory, deadline, _ = self.bounded_backend(connection)
            with self.assertRaises(self.t.BackendFailure) as caught:
                backend.send(self.request(deadline=deadline))
            self.assertEqual(caught.exception.category, category)
            self.assertEqual(connection.close_calls, 1)
            self.assertEqual(connection.requests, [])
            self.assertEqual(factory.call_count, 1)
            self.assertEqual(backend._pending, [])
            self.safe(caught.exception)

    def test_safety_exact_operation_scope_denies_origin_method_path_and_query_changes(self):
        authorization = self.b.DestinationAuthorization(
            "https://backend.invalid", ((self.t.HttpMethod.GET, "/api?id=1"),),
        )
        connection = MemoryConnection()
        backend, factory, deadline, _ = self.bounded_backend(
            connection, authorization=authorization,
        )
        for overrides in (
            {"url": "https://other.invalid/api?id=1"},
            {"url": "https://backend.invalid:8443/api?id=1"},
            {"url": "https://backend.invalid/other?id=1"},
            {"url": "https://backend.invalid/api?id=2"},
            {"url": "https://backend.invalid/api?id=1&extra=1"},
            {"url": "https://backend.invalid/api?id=1", "method": self.t.HttpMethod.POST},
        ):
            with self.assertRaises(self.t.BackendFailure):
                backend.send(self.request(deadline=deadline, **overrides))
        factory.assert_not_called()
        backend.send(self.request(url="https://backend.invalid/api?id=1", deadline=deadline))
        self.assertEqual(factory.call_count, 1)

    def test_safety_ambiguous_authorization_paths_cannot_be_granted_or_dispatched(self):
        for target in (
            "//api", "/a/../api", "/a/./api", "/%61pi", "/%2e%2e/api",
            "/%2Fapi", "/%2fapi", "/%252fapi", "/api\\x", "/api;x=1",
            "/api/", "/api//x", "/api?", "/api?id=%31", "/api?id=1#fragment",
            "/api?id=%0a", "/api?id=%0A", "/api?id=%252F", "/api*",
        ):
            with self.assertRaises(ValueError):
                self.b.DestinationAuthorization(
                    "https://backend.invalid", ((self.t.HttpMethod.GET, target),),
                )
            backend, factory, deadline, _ = self.bounded_backend()
            with self.assertRaises(self.t.BackendFailure) as caught:
                backend.send(self.request(url="https://backend.invalid" + target, deadline=deadline))
            factory.assert_not_called()
            self.safe(caught.exception)

    def test_safety_invalid_byte_budgets_are_rejected_without_dispatch(self):
        for maximum in (0, -1, True, 1.5, float("inf"), "4"):
            with self.assertRaises(ValueError):
                self.b.StdlibHttpBackend(max_response_bytes=maximum)

    def test_safety_each_socket_write_receives_only_remaining_budget(self):
        connection = MemoryConnection()
        backend, _, deadline, clock = self.bounded_backend(connection)
        def dispatch(*args, **kwargs):
            connection.sock.sendall(b"synthetic-headers")
            clock.return_value = 4.0
            connection.sock.sendall(b"synthetic-body")
            clock.return_value = 5.0
            connection.sock.sendall(b"forbidden-late-write")
        self.stack.enter_context(patch.object(connection, "request", side_effect=dispatch))
        with self.assertRaises(self.t.BackendFailure) as caught:
            backend.send(self.request(deadline=deadline, method=self.t.HttpMethod.POST))
        self.assertEqual(caught.exception.category, self.t.ErrorCategory.TIMEOUT)
        self.assertEqual(connection.sock.writes, [b"synthetic-headers", b"synthetic-body"])
        self.assertEqual(connection.sock.timeouts[-2:], [4.0, 1.0])
        self.assertEqual(connection.close_calls, 1)

    def test_safety_injected_builtin_factory_is_not_an_authorization_escape(self):
        backend = self.b.StdlibHttpBackend(
            connection_factory=self.b.http.client.HTTPSConnection,
            authorization=self.authorization(), max_response_bytes=4,
        )
        self.addCleanup(backend.close)
        with self.assertRaises(self.t.BackendFailure) as caught:
            backend.send(self.request())
        self.assertEqual(caught.exception.category, self.t.ErrorCategory.SAFETY_POLICY)
        self.dispatch_guards[1].assert_not_called()

    def test_safety_failure_during_deadline_clock_read_is_sanitized_and_releases(self):
        for value in (float("nan"), float("inf"), True, None, RuntimeError(SECRET)):
            connection = MemoryConnection()
            backend, _, deadline, clock = self.bounded_backend(connection)
            def connect():
                if isinstance(value, Exception):
                    clock.side_effect = value
                else:
                    clock.return_value = value
            self.stack.enter_context(patch.object(connection, "connect", side_effect=connect))
            with self.assertRaises(self.t.BackendFailure) as caught:
                backend.send(self.request(deadline=deadline))
            self.assertEqual(caught.exception.category, self.t.ErrorCategory.BACKEND)
            self.assertEqual(connection.close_calls, 1)
            self.assertEqual(connection.requests, [])
            self.safe(caught.exception)
