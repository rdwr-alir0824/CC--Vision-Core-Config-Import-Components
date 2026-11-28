import base64
import io
import json
import ssl
import traceback
import tempfile
import warnings
from contextlib import contextmanager, redirect_stderr, redirect_stdout
from dataclasses import replace
from unittest.mock import Mock, patch

from offline_support import OfflineTestCase
from test_http_backend import MemoryConnection, MemoryResponse

from cc_vision_import.client import ApiClient, ClientError
from cc_vision_import.config import ConfigError, ControllerConfig, prompt_config
from cc_vision_import.files import JsonFileError, load_json, save_json
from cc_vision_import.http_backend import DestinationAuthorization, StdlibHttpBackend
from cc_vision_import.tls_policy import TLSPolicy, TLSPolicyError
from cc_vision_import.transport import (
    BackendFailure, BackendRequest, ErrorCategory, HttpMethod, OperationDeadline,
)


SECRET = 'synthetic-secret-"\\&'
PATH = ("synthetic", "name with spaces")


class LegacyFoundationTests(OfflineTestCase):
    def setUp(self):
        super().setUp()
        self.config = ControllerConfig(
            address="source.example.invalid:8443", username='synthetic-user-"\\',
            password=SECRET, product="vision",
        )
        self.operations = tuple((method, PATH) for method in (
            HttpMethod.GET, HttpMethod.POST, HttpMethod.PUT,
        ))

    def login_response(self, **kwargs):
        return MemoryResponse(
            body=b'{"status":"ok"}',
            headers=[("Set-Cookie", "JSESSIONID=synthetic-cookie; Secure; Path=/")],
            **kwargs,
        )

    def client(self, *responses, config=None, **kwargs):
        connections = [
            response if isinstance(response, MemoryConnection) else MemoryConnection(response)
            for response in responses
        ]
        factory = Mock(side_effect=connections)
        client = ApiClient(
            self.config if config is None else config, operations=self.operations,
            connection_factory=factory, **kwargs,
        )
        self.addCleanup(client.close)
        return client, connections, factory

    def test_successful_vision_login_cookie_requests_and_cleanup(self):
        client, connections, factory = self.client(
            self.login_response(), MemoryResponse(body=b'{"value":1}'),
        )
        with client:
            self.assertEqual(client.get(PATH), {"value": 1})
            self.assertIn("synthetic-cookie", connections[1].requests[0][3]["Cookie"])
        self.assertEqual(factory.call_count, 2)
        for connection in connections:
            self.assertEqual(connection.close_calls, 1)
            self.assertEqual(connection.response.close_calls, 1)
        self.assertEqual(len(client._backend._cookies), 0)
        self.assertIsNone(client._credentials)
        with self.assertRaises(ClientError):
            client.get(PATH)
        client.close()
        self.assertEqual(factory.call_count, 2)

    def test_cyber_controller_special_characters_are_safe_in_json_and_basic(self):
        config = replace(self.config, product="cyber-controller")
        client, connections, _ = self.client(
            self.login_response(), MemoryResponse(body=b"{}"), config=config,
        )
        with client:
            client.get(PATH)
        request = connections[0].requests[0]
        self.assertEqual(json.loads(request[2]), {
            "username": config.username, "password": config.password,
        })
        for connection in connections:
            encoded = connection.requests[0][3]["Authorization"].split()[1]
            self.assertEqual(
                base64.b64decode(encoded).decode("latin-1"),
                config.username + ":" + config.password,
            )

    def test_vision_unicode_credentials_are_preserved(self):
        config = replace(self.config, username="user-\u00e9", password="secret-\u2603")
        client, connections, _ = self.client(self.login_response(), config=config)
        with client:
            pass
        self.assertEqual(json.loads(connections[0].requests[0][2])["password"], config.password)

    def test_unrepresentable_basic_credentials_fail_before_dispatch(self):
        for fields in ({"username": "user:private-marker"}, {"password": "private-marker-\u2603"}):
            with self.subTest(fields=fields):
                config = replace(self.config, product="cyber-controller", **fields)
                client, _, factory = self.client(self.login_response(), config=config)
                with self.assertRaises(ClientError) as caught:
                    client.login()
                self.assertEqual(caught.exception.code, "invalid_credentials")
                self.assertNotIn("private-marker", "".join(traceback.format_exception(caught.exception)))
                factory.assert_not_called()
                self.assertTrue(client._closed)

    def test_documented_returned_session_id_is_used_without_logging(self):
        response = MemoryResponse(body=b'{"status":"ok","jsessionid":"synthetic-returned-id"}')
        client, connections, _ = self.client(response, MemoryResponse(body=b"[]"))
        with client:
            self.assertEqual(client.get(PATH), [])
            self.assertEqual(
                connections[1].requests[0][3]["Cookie"], "JSESSIONID=synthetic-returned-id",
            )
        self.assertFalse(client._has_documented_session)

    def test_rejected_and_malformed_authentication_closes_without_retry(self):
        for product in ("vision", "cyber-controller"):
            for status, body in (
                (401, SECRET.encode()), (403, b"{}"), (500, b"{}"),
                (200, b'{"status":"error","message":"private-login-marker"}'),
                (200, b"{}"), (200, b"not-json"),
                (200, b'{"status":"ok","jsessionid":"invalid cookie;"}'),
                (200, b'{"status":"ok","status":"ok"}'),
            ):
                with self.subTest(product=product, status=status, body=body):
                    client, connections, factory = self.client(
                        MemoryResponse(status=status, body=body),
                        config=replace(self.config, product=product),
                    )
                    with self.assertRaises(ClientError) as caught:
                        client.login()
                    rendered = "".join(traceback.format_exception(caught.exception))
                    self.assertNotIn(SECRET, rendered)
                    self.assertNotIn("private-login-marker", rendered)
                    self.assertEqual(factory.call_count, 1)
                    self.assertEqual(connections[0].close_calls, 1)
                    self.assertTrue(client._closed)
                    self.assertIsNone(client._credentials)

    def test_tls_verified_by_default_and_timeouts_are_finite(self):
        config = replace(self.config, connect_timeout=2, read_timeout=4, operation_timeout=6)
        client, connections, factory = self.client(
            self.login_response(), MemoryResponse(body=b"{}"), config=config,
        )
        with client:
            client.get(PATH)
        for call in factory.call_args_list:
            context = call.kwargs["context"]
            self.assertEqual(context.verify_mode, ssl.CERT_REQUIRED)
            self.assertTrue(context.check_hostname)
            self.assertGreater(call.kwargs["timeout"], 0)
            self.assertLessEqual(call.kwargs["timeout"], 2)
        for connection in connections:
            self.assertTrue(connection.sock._resource.timeouts)
            self.assertTrue(all(0 < timeout <= 4 for timeout in connection.sock._resource.timeouts))

    def test_unverified_tls_requires_new_client_consent_and_expires_on_close(self):
        config = replace(self.config, verify_tls=False)
        with self.assertRaises(ClientError):
            ApiClient(config)
        with warnings.catch_warnings(record=True) as emitted:
            warnings.simplefilter("always")
            client, _, factory = self.client(
                self.login_response(), MemoryResponse(body=b"{}"), config=config,
                tls_exception_authorized=True,
            )
            with client:
                client.post(PATH, {"name": "runtime-name"})
            self.assertEqual(len(emitted), 1)
            self.assertIn("NOT VERIFIED", str(emitted[0].message))
            for call in factory.call_args_list:
                self.assertEqual(call.kwargs["context"].verify_mode, ssl.CERT_NONE)
                self.assertFalse(call.kwargs["context"].check_hostname)
            self.assertIsNone(client._backend._session_tls_policy)
        with self.assertRaises(ClientError):
            ApiClient(config)
        self.assertTrue(self.config.verify_tls)

    def test_expired_operation_deadline_prevents_dispatch_and_closes_session(self):
        client, _, factory = self.client(self.login_response())
        client._transport._clock = Mock(side_effect=[0.0, 0.0, 61.0])
        with self.assertRaises(ClientError) as caught:
            client.login()
        self.assertTrue(caught.exception.indeterminate)
        factory.assert_not_called()
        self.assertTrue(client._closed)

    def test_shared_backend_omitted_policy_keeps_unverified_write_denied(self):
        authorization = DestinationAuthorization(
            self.config.origin, ((HttpMethod.POST, "/synthetic"),),
        )
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        factory = Mock()
        backend = StdlibHttpBackend(
            authorization=authorization, max_response_bytes=100,
            connection_factory=factory,
        )
        self.addCleanup(backend.close)
        request = BackendRequest(
            HttpMethod.POST, self.config.origin + "/synthetic", {}, b"{}",
            2, 4, context, deadline=OperationDeadline(1e100),
        )
        with self.assertRaises(BackendFailure):
            backend.send(request)
        factory.assert_not_called()

    def test_shared_backend_rejects_unapproved_or_wrong_origin_policy(self):
        authorization = DestinationAuthorization(
            self.config.origin, ((HttpMethod.GET, "/synthetic"),),
        )
        for policy in (
            TLSPolicy(False, False, self.config.origin),
            TLSPolicy(False, True, "https://destination.example.invalid"),
            TLSPolicy(False, True, None),
        ):
            with self.subTest(policy=policy), self.assertRaises(TLSPolicyError):
                StdlibHttpBackend(
                    authorization=authorization, session_tls_policy=policy,
                    max_response_bytes=100,
                )
        with self.assertRaises(ValueError):
            StdlibHttpBackend(session_tls_policy=TLSPolicy(False, True, self.config.origin))

    def test_tls_failure_does_not_automatically_downgrade_or_retry(self):
        failed = MemoryConnection(failure=("connect", ssl.SSLError(SECRET)))
        client, _, factory = self.client(failed)
        with self.assertRaises(ClientError) as caught:
            client.login()
        self.assertEqual(factory.call_count, 1)
        self.assertTrue(client._closed)
        self.assertNotIn(SECRET, "".join(traceback.format_exception(caught.exception)))

    def test_context_cleanup_on_operator_failure_and_no_remote_logout(self):
        client, _, factory = self.client(self.login_response())
        with self.assertRaisesRegex(RuntimeError, "operator failure"):
            with client:
                raise RuntimeError("operator failure")
        self.assertTrue(client._closed)
        self.assertEqual(factory.call_count, 1)

    def test_cleanup_failure_is_explicit_and_preserves_primary_error(self):
        client, _, _ = self.client(self.login_response())
        failure = BackendFailure(ErrorCategory.BACKEND, cleanup_failed=True)
        with patch.object(client._backend, "close", side_effect=failure):
            with self.assertRaises(ClientError) as caught:
                with client:
                    pass
            self.assertEqual(caught.exception.code, "local_cleanup_failed")
        client.close()
        client, _, _ = self.client(MemoryResponse(status=401, body=b"{}"))
        with patch.object(client._backend, "close", side_effect=failure):
            with self.assertRaises(ClientError) as caught:
                client.login()
            self.assertEqual(caught.exception.status, 401)
            self.assertIn("Local API session cleanup failed.", caught.exception.__notes__)
        client.close()

    def test_get_post_and_put_json_and_encoded_runtime_path(self):
        client, connections, _ = self.client(
            self.login_response(), MemoryResponse(body=b'{"sites":[]}'),
            MemoryResponse(body=b'{"created":true}'), MemoryResponse(status=204),
        )
        with client:
            self.assertEqual(client.get(PATH), {"sites": []})
            self.assertEqual(client.post(PATH, {"name": "runtime-name"}), {"created": True})
            self.assertIsNone(client.put(PATH, {"enabled": False}, expect_json=False))
        self.assertEqual(connections[1].requests[0][1], "/synthetic/name%20with%20spaces")
        self.assertEqual(json.loads(connections[2].requests[0][2]), {"name": "runtime-name"})
        self.assertEqual(json.loads(connections[3].requests[0][2]), {"enabled": False})

    def test_http_and_json_failures_are_explicit_and_secret_free(self):
        for status, body in (
            (404, SECRET.encode()), (500, SECRET.encode()), (302, b""),
            (200, b"not-json"), (200, b"\xff"),
            (200, b'{"key":1,"key":2}'), (200, b'{"number":NaN}'),
            (200, b'{"number":1e999}'),
            (200, b'{"status":"error","message":"private-response-marker"}'),
        ):
            with self.subTest(status=status, body=body):
                client, _, factory = self.client(
                    self.login_response(), MemoryResponse(status=status, body=body),
                )
                with self.assertRaises(ClientError) as caught:
                    with client:
                        client.get(PATH)
                rendered = "".join(traceback.format_exception(caught.exception))
                self.assertNotIn(SECRET, rendered)
                self.assertNotIn("private-response-marker", rendered)
                self.assertEqual(factory.call_count, 2)
                self.assertTrue(client._closed)

    def test_post_timeout_server_error_and_malformed_reply_never_retry(self):
        for response in (
            MemoryConnection(failure=("request", TimeoutError(SECRET))),
            MemoryResponse(status=500, body=SECRET.encode()),
            MemoryResponse(status=200, body=b"not-json"),
            MemoryResponse(status=200, body=b'{"value":1e999}'),
        ):
            with self.subTest(response=response):
                client, _, factory = self.client(self.login_response(), response)
                with self.assertRaises(ClientError) as caught:
                    with client:
                        client.post(PATH, {"name": "runtime-name"})
                self.assertTrue(caught.exception.indeterminate)
                self.assertEqual(factory.call_count, 2)

    def test_session_expiration_rejection_closes_without_login_replay(self):
        client, _, factory = self.client(
            self.login_response(), MemoryResponse(status=401, body=b"{}"),
        )
        client.login()
        with self.assertRaises(ClientError):
            client.get(PATH)
        with self.assertRaises(ClientError):
            client.get(PATH)
        self.assertTrue(client._closed)
        self.assertEqual(factory.call_count, 2)

    def test_wrong_origin_and_unapproved_write_cannot_dispatch(self):
        client, _, factory = self.client(self.login_response())
        with client:
            for segments in (("other",), ("..",), ("https://destination.example.invalid",)):
                with self.subTest(segments=segments), self.assertRaises(ClientError):
                    client.post(segments, {})
        self.assertEqual(factory.call_count, 1)

    def test_invalid_configuration_is_secret_free_and_timeouts_are_bounded(self):
        for field, value in (
            ("address", "http://invalid.example"), ("address", "https://user:private-marker@invalid.example"),
            ("verify_tls", "false"), ("product", "unknown"),
            ("username", ""), ("password", "private-marker\n"),
            ("connect_timeout", 0), ("read_timeout", float("inf")),
            ("operation_timeout", 301), ("operation_timeout", float("nan")),
        ):
            with self.subTest(field=field, value=value):
                with self.assertRaises(ConfigError) as caught:
                    replace(self.config, **{field: value})
                self.assertNotIn("private-marker", "".join(traceback.format_exception(caught.exception)))
        self.assertNotIn(SECRET, repr(self.config))

    def test_interactive_input_uses_hidden_password_and_runtime_address(self):
        input_fn = Mock(side_effect=[" destination.example.invalid ", "runtime-user"])
        password_fn = Mock(return_value=SECRET)
        with redirect_stdout(io.StringIO()) as output, redirect_stderr(io.StringIO()) as errors:
            config = prompt_config("cyber-controller", input_fn=input_fn, password_fn=password_fn)
        self.assertEqual(config.origin, "https://destination.example.invalid")
        self.assertEqual(config.password, SECRET)
        password_fn.assert_called_once_with("Password: ")
        self.assertEqual(output.getvalue() + errors.getvalue(), "")

    def test_json_round_trip_preserves_portable_access_and_different_ids(self):
        data = {
            "source_root": {"id": "source-root-17", "name": "Source Hierarchy"},
            "sites": [{"id": "source-site-18", "name": "Branch Alpha", "parentOrmID": "source-root-17"}],
            "devices": [{
                "id": "source-device-19", "name": "Node Beta", "type": "runtime-model",
                "deviceAccess": {"cliPassword": SECRET, "snmpV3PrivacyPassword": "synthetic-privacy"},
            }],
            "destination": {"id": "destination-root-93", "name": "Destination Hierarchy"},
        }
        save_json(self.input_path, data)
        self.assertEqual(load_json(self.input_path), data)

    def test_missing_malformed_and_unreadable_files(self):
        with self.assertRaisesRegex(JsonFileError, "not found"):
            load_json(self.input_path)
        for content in ("not-json", '{"password":"private-marker",}', "\ud800"):
            with self.subTest(content=content):
                self.input_path.write_bytes(content.encode("utf-8", errors="surrogatepass"))
                with self.assertRaises(JsonFileError) as caught:
                    load_json(self.input_path)
                self.assertNotIn("private-marker", "".join(traceback.format_exception(caught.exception)))
        with self.assertRaisesRegex(JsonFileError, "Cannot read"):
            load_json(self.directory)
        with self.assertRaisesRegex(JsonFileError, "Cannot write"):
            save_json(self.directory / "missing" / "data.json", {})

    def test_duplicate_keys_and_unsupported_numeric_values(self):
        for text in (
            '{"a":1,"a":2}', '{"nested":{"a":1,"a":2}}',
            '{"a":NaN}', '{"a":Infinity}', '{"a":-Infinity}', '{"a":1e999}',
        ):
            with self.subTest(text=text):
                self.input_path.write_text(text)
                with self.assertRaises(JsonFileError):
                    load_json(self.input_path)
        for value in (float("nan"), float("inf"), -float("inf")):
            with self.subTest(value=value), self.assertRaises(JsonFileError):
                save_json(self.input_path, {"value": value})

    def test_invalid_outbound_json_does_not_truncate_file_or_send(self):
        save_json(self.input_path, {"preserved": True})
        with self.assertRaises(JsonFileError):
            save_json(self.input_path, {"value": float("nan")})
        self.assertEqual(load_json(self.input_path), {"preserved": True})
        client, _, factory = self.client(self.login_response())
        with client:
            with self.assertRaises(ClientError):
                client.post(PATH, {"value": float("inf")})
        self.assertEqual(factory.call_count, 1)

    def test_atomic_save_replaces_existing_output_and_leaves_no_temporary_file(self):
        save_json(self.input_path, {"previous": True})
        save_json(self.input_path, {"replacement": [1, 2]})
        self.assertEqual(load_json(self.input_path), {"replacement": [1, 2]})
        self.assertEqual(list(self.directory.iterdir()), [self.input_path])

    def test_atomic_save_partial_write_failure_preserves_previous_output(self):
        save_json(self.input_path, {"previous": True})
        original = tempfile.NamedTemporaryFile

        @contextmanager
        def fail_write(*args, **kwargs):
            with original(*args, **kwargs) as stream:
                write = stream.write

                def partial_write(text):
                    write(text[:4])
                    raise OSError(SECRET)

                with patch.object(stream, "write", side_effect=partial_write):
                    yield stream

        with patch("cc_vision_import.files.tempfile.NamedTemporaryFile", side_effect=fail_write):
            with self.assertRaises(JsonFileError) as caught:
                save_json(self.input_path, {"replacement": True})
        self.assertNotIn(SECRET, "".join(traceback.format_exception(caught.exception)))
        self.assertEqual(load_json(self.input_path), {"previous": True})
        self.assertEqual(list(self.directory.iterdir()), [self.input_path])

    def test_atomic_replace_failure_preserves_output_and_cleans_temporary_file(self):
        save_json(self.input_path, {"previous": True})
        with patch("cc_vision_import.files.os.replace", side_effect=OSError(SECRET)):
            with self.assertRaises(JsonFileError):
                save_json(self.input_path, {"replacement": True})
        self.assertEqual(load_json(self.input_path), {"previous": True})
        self.assertEqual(list(self.directory.iterdir()), [self.input_path])

    def test_atomic_save_failure_does_not_create_invalid_new_output(self):
        with patch("cc_vision_import.files.os.replace", side_effect=OSError(SECRET)):
            with self.assertRaises(JsonFileError):
                save_json(self.input_path, {"replacement": True})
        self.assertEqual(list(self.directory.iterdir()), [])
