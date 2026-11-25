"""Explicit HTTPS dispatch adapter; construction never connects or grants capabilities."""

import copy
import http.client
import json
import math
import re
import ssl
import sys
import time
import zlib
from dataclasses import dataclass, field
from email.message import Message
from http.cookiejar import Cookie, CookieJar, DefaultCookiePolicy, parse_ns_headers
from typing import BinaryIO, Literal, Protocol
from urllib.parse import parse_qsl, quote, unquote, urlencode, urlsplit
from urllib.request import Request

from .contracts import ContractValidationError
from .transport import (
    BackendFailure, BackendRequest, ErrorCategory, HttpMethod, HttpResponse,
    OperationDeadline, _headers, _origin, _timeouts,
)


class _Closable(Protocol):
    def close(self) -> None: ...


class _Socket(_Closable, Protocol):
    def settimeout(self, value: float) -> None: ...
    def makefile(self, mode: Literal["rb"]) -> BinaryIO: ...
    def sendall(self, data: bytes) -> None: ...


class _Response(_Closable, Protocol):
    @property
    def status(self) -> int: ...

    def getheaders(self) -> list[tuple[str, str]]: ...
    def read(self, size: int) -> bytes: ...


class _Connection(_Closable, Protocol):
    auto_open: int

    @property
    def sock(self) -> _Socket | None: ...

    def set_debuglevel(self, level: int) -> None: ...
    def connect(self) -> None: ...
    def request(
        self, method: str, url: str, body: bytes | None = None,
        headers: dict[str, str] = ...,
    ) -> None: ...
    def getresponse(self) -> _Response: ...


class ConnectionFactory(Protocol):
    """Trusted offline-double seam, not a resolver or live-dispatch authorization."""

    def __call__(
        self, host: str, port: int, *, timeout: float, context: ssl.SSLContext,
    ) -> _Connection: ...


def _target(value: str) -> str:
    if (
        not isinstance(value, str) or not value.startswith("/") or "#" in value
        or "\\" in value or ";" in value or "*" in value
        or any(not 33 <= ord(c) <= 126 for c in value)
    ):
        raise ValueError("Unsafe authorized target.")
    path, separator, query = value.partition("?")
    if path != "/":
        for segment in path[1:].split("/"):
            decoded = unquote(segment)
            if (
                not decoded or decoded in (".", "..")
                or any(c in decoded for c in "/\\%;")
                or any(not c.isprintable() for c in decoded)
                or quote(decoded, safe="") != segment
            ):
                raise ValueError("Ambiguous authorized path.")
    if separator and (
        not query or any("=" not in pair for pair in query.split("&"))
        or urlencode(parse_qsl(query, keep_blank_values=True)) != query
        or any(
            not character.isprintable() or character in "%;\\"
            for pair in parse_qsl(query, keep_blank_values=True)
            for component in pair for character in component
        )
    ):
        raise ValueError("Ambiguous authorized query.")
    return value


@dataclass(frozen=True)
class DestinationAuthorization:
    """Caller-supplied exact scope; never derived from capabilities or product versions."""

    origin: str = field(repr=False)
    operations: tuple[tuple[HttpMethod, str], ...] = field(repr=False)

    def __post_init__(self) -> None:
        _origin(self.origin)
        if self.origin.endswith("/") or not isinstance(self.operations, tuple) or not self.operations:
            raise ValueError("An exact origin and finite operations are required.")
        for operation in self.operations:
            if (
                not isinstance(operation, tuple) or len(operation) != 2
                or not isinstance(operation[0], HttpMethod)
            ):
                raise ValueError("Invalid authorized operation.")
            _target(operation[1])
        if len(set(self.operations)) != len(self.operations):
            raise ValueError("Repeated authorized operation.")

    def permits(self, method: HttpMethod, origin: str, target: str) -> bool:
        approved, actual = urlsplit(self.origin), urlsplit(origin)
        return (
            (actual.scheme, actual.hostname, actual.port or 443)
            == (approved.scheme, approved.hostname, approved.port or 443)
            and (method, _target(target)) in self.operations
        )


@dataclass(frozen=True)
class _CookieResponse:
    message: Message = field(repr=False)

    def info(self) -> Message:
        return self.message


class _StrictCookieJar(CookieJar):
    """Keep the existing Netscape policy without make_cookies' warn-and-drop fallback."""

    def __init__(self) -> None:
        super().__init__(DefaultCookiePolicy(
            strict_ns_domain=DefaultCookiePolicy.DomainStrict,
        ))

    def make_cookies(self, response: _CookieResponse, request: Request) -> list[Cookie]:
        self._policy._now = self._now = int(time.time())
        attributes = parse_ns_headers(response.info().get_all("Set-Cookie", []))
        for cookie_attributes in attributes:
            for name, value in cookie_attributes[1:]:
                if name.lower() == "max-age":
                    if value is None or re.fullmatch(r"-?[0-9]+", value) is None:
                        raise ValueError("Invalid cookie lifetime.")
                    try:
                        finite = math.isfinite(float(self._now + int(value)))
                    except (ValueError, OverflowError):
                        finite = False
                    if not finite:
                        raise ValueError("Invalid cookie lifetime.")
        cookies = self._cookies_from_attrs_set(attributes, request)
        self._process_rfc2109_cookies(cookies)
        return cookies


def _release(resources: list[_Closable]) -> list[_Closable]:
    failed = []
    for resource in reversed(resources):
        try:
            resource.close()
        except Exception:
            failed.append(resource)
    return failed


class _CleanupTracker:
    def __init__(self) -> None:
        self.failed: list[_Closable] = []

    def close(self, resource: _Closable) -> None:
        # http.client drops socket/fp ownership before closing. Retain failures
        # here and report them at the adapter boundary, preserving primary errors.
        for failed in _release([resource]):
            if not any(item is failed for item in self.failed):
                self.failed.append(failed)


class _FileGuard:
    def __init__(
        self, resource: BinaryIO, tracker: _CleanupTracker,
        deadline: OperationDeadline, socket: _Socket, timeout: float,
    ) -> None:
        self._resource = resource
        self._tracker = tracker
        self._deadline = deadline
        self._socket = socket
        self._timeout = timeout

    def __getattr__(self, name: str) -> object:
        return getattr(self._resource, name)

    def read(self, size: int = -1) -> bytes:
        if size < 0:
            raise ValueError("Unbounded reads are forbidden.")
        self._socket.settimeout(min(self._timeout, self._deadline.remaining()))
        result = self._resource.read(size)
        self._deadline.remaining()
        return result

    def readline(self, size: int = -1) -> bytes:
        if size < 0:
            raise ValueError("Unbounded reads are forbidden.")
        self._socket.settimeout(min(self._timeout, self._deadline.remaining()))
        result = self._resource.readline(size)
        self._deadline.remaining()
        return result

    def close(self) -> None:
        self._tracker.close(self._resource)


class _SocketGuard:
    def __init__(
        self, resource: _Socket, tracker: _CleanupTracker,
        deadline: OperationDeadline, timeout: float,
    ) -> None:
        self._resource = resource
        self._tracker = tracker
        self._deadline = deadline
        self._timeout = timeout

    def __getattr__(self, name: str) -> object:
        return getattr(self._resource, name)

    def makefile(self, mode: Literal["rb"]) -> _FileGuard:
        self._deadline.remaining()
        return _FileGuard(
            self._resource.makefile(mode), self._tracker,
            self._deadline, self._resource, self._timeout,
        )

    def sendall(self, data: bytes) -> None:
        self._resource.settimeout(min(self._timeout, self._deadline.remaining()))
        self._resource.sendall(data)
        self._deadline.remaining()

    def close(self) -> None:
        self._tracker.close(self._resource)


class _ResponseValidationError(ValueError):
    def __init__(self, reason: str) -> None:
        super().__init__("Response validation failed.")
        self.reason = reason


def _response_metadata(trace: dict[str, object], pairs: list[tuple[str, str]]) -> None:
    for header, field_name in (
        ("content-type", "content_type"), ("content-encoding", "content_encoding"),
    ):
        values = [
            pair[1] for pair in pairs
            if isinstance(pair, tuple) and len(pair) == 2
            and isinstance(pair[0], str) and pair[0].lower() == header
        ]
        safe_values = (
            {"application/json", "application/problem+json", "text/html", "text/plain",
             "application/xml", "text/xml", "application/octet-stream"}
            if header == "content-type" else {"identity", "gzip", "deflate", "br", "compress", "zstd"}
        )
        value = values[0].partition(";")[0].strip().lower() if len(values) == 1 and isinstance(values[0], str) else None
        trace[field_name] = (
            None if not values else "multiple" if len(values) > 1
            else value if value in safe_values else "unrecognized"
        )


def _response_headers(
    response: _Response, trace: dict[str, object] | None = None,
) -> tuple[dict[str, str], Message]:
    parsed = getattr(response, "headers", None)
    if trace is not None and isinstance(parsed, Message):
        _response_metadata(trace, [
            (name, value) for name in ("Content-Type", "Content-Encoding")
            for value in parsed.get_all(name, [])
        ])
    if isinstance(parsed, Message) and (
        parsed.defects or any(getattr(value, "defects", ()) for value in parsed.values())
    ):
        raise _ResponseValidationError("defective_response_headers")
    message = Message()
    headers: dict[str, str] = {}
    seen: set[str] = set()
    pairs = response.getheaders()
    if not isinstance(pairs, list):
        raise _ResponseValidationError("invalid_response_headers")
    if trace is not None:
        _response_metadata(trace, pairs)
    for pair in pairs:
        if not isinstance(pair, tuple) or len(pair) != 2:
            raise _ResponseValidationError("invalid_response_header_pair")
        name, value = pair
        if not isinstance(name, str) or not isinstance(value, str):
            raise _ResponseValidationError("invalid_response_header_type")
        _headers({name: value}, for_request=False)
        key = name.lower()
        if key in seen and key not in ("set-cookie", "cache-control", "vary"):
            raise _ResponseValidationError("unsafe_repeated_response_header")
        seen.add(key)
        message[name] = value
        # Set-Cookie is multi-valued and session-owned, not a flattened public header.
        if key != "set-cookie":
            existing = next((original for original in headers if original.lower() == key), None)
            if existing is None:
                headers[name] = value
            else:
                headers[existing] += ", " + value
    length = message.get("Content-Length")
    transfer = message.get("Transfer-Encoding")
    if (
        length is not None and (not re.fullmatch(r"[0-9]+", length) or transfer is not None)
        or transfer is not None and transfer.lower() != "chunked"
    ):
        raise _ResponseValidationError("ambiguous_or_unsupported_response_framing")
    return headers, message


def _read_response_body(response: _Response, size: int) -> bytes:
    if not isinstance(response, http.client.HTTPResponse) or not response.chunked:
        return response.read(size)
    if response.fp is None:
        return b""
    # Stdlib's chunk decoder discards two bytes without verifying the CRLF.
    # Keep its bounded reads and ownership, but validate that framing explicitly.
    chunks: list[bytes] = []
    remaining = size
    while remaining:
        chunk_left = response.chunk_left
        if not chunk_left:
            if chunk_left == 0 and response._safe_read(2) != b"\r\n":
                raise http.client.HTTPException("Invalid chunk delimiter.")
            chunk_left = response._read_next_chunk_size()
            if chunk_left < 0:
                raise http.client.HTTPException("Invalid chunk size.")
            if chunk_left == 0:
                response._read_and_discard_trailer()
                response._close_conn()
                response.chunk_left = None
                break
        count = min(remaining, chunk_left)
        chunks.append(response._safe_read(count))
        response.chunk_left = chunk_left - count
        remaining -= count
    return b"".join(chunks)


class StdlibHttpBackend:
    """Exact-scope HTTPS adapter; built-in dispatch requires explicit live opt-in.

    Injected factories remain trusted offline doubles. Live DNS resolution is not
    hard-deadline bounded; socket timeouts and checked deadlines are not process
    containment guarantees. Each instance owns one origin/private cookie jar.
    """

    def __init__(
        self, *, connection_factory: ConnectionFactory | None = None,
        authorization: DestinationAuthorization | None = None,
        max_response_bytes: int | None = None,
        allow_live: bool = False,
        allow_unverified_vision_backup: bool = False,
        allow_unverified_destination_discovery: bool = False,
        diagnose_failures: bool = False,
    ) -> None:
        if type(allow_live) is not bool or allow_live and connection_factory is not None:
            raise ValueError("Live dispatch must use the built-in HTTPS connection.")
        if type(allow_unverified_vision_backup) is not bool:
            raise ValueError("Backup TLS selection must be explicit.")
        if type(allow_unverified_destination_discovery) is not bool:
            raise ValueError("Destination discovery TLS selection must be explicit.")
        if type(diagnose_failures) is not bool:
            raise ValueError("Failure diagnostics must be explicitly selected.")
        if authorization is not None:
            if not isinstance(authorization, DestinationAuthorization):
                raise ValueError("Invalid destination authorization.")
            authorization.__post_init__()
        if max_response_bytes is not None and (
            type(max_response_bytes) is not int or max_response_bytes <= 0
        ):
            raise ValueError("A positive finite byte budget is required.")
        self._factory = connection_factory
        self._allow_live = allow_live
        self._allow_unverified_vision_backup = allow_unverified_vision_backup
        self._allow_unverified_destination_discovery = allow_unverified_destination_discovery
        self._diagnose_failures = diagnose_failures
        self._last_diagnostic: dict[str, object] | None = None
        self._authorization = authorization
        self._max_response_bytes = max_response_bytes
        self._cookies = _StrictCookieJar()
        self._origin: tuple[str, int] | None = None
        self._pending: list[_Closable] = []
        self._closed = False

    def authorize_get_targets(self, targets: tuple[str, ...]) -> None:
        if self._closed or self._authorization is None or not isinstance(targets, tuple):
            raise BackendFailure(ErrorCategory.SAFETY_POLICY)
        operations = tuple(dict.fromkeys((
            *self._authorization.operations, *((HttpMethod.GET, target) for target in targets),
        )))
        self._authorization = DestinationAuthorization(self._authorization.origin, operations)

    def send(self, request: BackendRequest) -> HttpResponse:
        trace: dict[str, object] = {
            "http_method": request.method.value if isinstance(request, BackendRequest) and isinstance(request.method, HttpMethod) else "invalid",
            "endpoint_path": "unrecognized", "http_status": None,
            "content_type": None, "content_encoding": None,
            "failure_stage": "request_validation", "exception_class": None,
            "validation_reason": None,
        }
        if isinstance(request, BackendRequest) and isinstance(request.url, str):
            path = "/" + request.url.partition("://")[2].partition("/")[2].partition("?")[0].partition("#")[0]
            for endpoint in ("/mgmt/system/user/login", "/mgmt/system/config/itemlist/alldevices"):
                if path == endpoint:
                    trace["endpoint_path"] = endpoint
            for prefix, template in (
                ("/mgmt/system/config/tree/site/byname/", "/mgmt/system/config/tree/site/byname/{name}"),
                ("/mgmt/system/config/tree/site/byid/", "/mgmt/system/config/tree/site/byid/{id}"),
                ("/mgmt/system/config/tree/device/byip/", "/mgmt/system/config/tree/device/byip/{ip}"),
            ):
                if path.startswith(prefix):
                    trace["endpoint_path"] = template
        outcome = self._attempt(request, trace)
        self._last_diagnostic = trace if self._diagnose_failures else None
        if isinstance(outcome, BackendFailure):
            self._report_failure(outcome.category.value)
            raise outcome
        if not 200 <= outcome.status < 300:
            trace.update(failure_stage="response_status", validation_reason="http_status_rejected")
            self._report_failure(ErrorCategory.HTTP.value)
        return outcome

    def _report_failure(self, category: str) -> None:
        if self._last_diagnostic is not None:
            print(json.dumps({
                "event": "vision_http_failure", **self._last_diagnostic,
                "error_category": category,
            }, sort_keys=True), file=sys.stderr)

    def report_login_failure(self, reason: str) -> None:
        if self._last_diagnostic is not None:
            safe_reason = reason if reason in {
                "invalid_login_json_or_status", "login_status_not_ok",
                "unexpected_login_status", "missing_or_non_string_jsessionid", "invalid_jsessionid",
            } else "unrecognized_login_validation_reason"
            self._last_diagnostic.update(
                failure_stage="login_response_validation", validation_reason=safe_reason,
            )
            self._report_failure("authentication_failure")

    def _attempt(
        self, request: BackendRequest, trace: dict[str, object] | None = None,
    ) -> HttpResponse | BackendFailure:
        trace = {} if trace is None else trace
        trace.setdefault("failure_stage", "request_validation")
        resources: list[_Closable] = []
        failure: ErrorCategory | None = None
        response: HttpResponse | None = None
        failed: list[_Closable] = []
        tracker = _CleanupTracker()
        status: int | None = None
        candidate: _StrictCookieJar | None = None
        try:
            if self._closed or self._pending:
                return BackendFailure(ErrorCategory.BACKEND, cleanup_failed=bool(self._pending))
            if (
                not isinstance(request, BackendRequest) or not isinstance(request.method, HttpMethod)
                or not isinstance(request.url, str)
                or any(not 33 <= ord(c) <= 126 for c in request.url)
                or request.follow_redirects is not False
                or request.body is not None and (
                    not isinstance(request.body, bytes) or request.method == HttpMethod.GET
                )
                or not isinstance(request.tls_context, ssl.SSLContext)
                or request.tls_context.keylog_filename is not None
                or type(request.unverified_vision_backup) is not bool
                or type(request.unverified_destination_discovery) is not bool
            ):
                raise ValueError("Unsafe backend request.")
            verified = (
                request.tls_context.verify_mode == ssl.CERT_REQUIRED
                and request.tls_context.check_hostname is True
            )
            backup_tls = (
                self._allow_unverified_vision_backup and request.unverified_vision_backup
                and request.tls_context.verify_mode == ssl.CERT_NONE
                and request.tls_context.check_hostname is False
            )
            discovery_tls = (
                self._allow_unverified_destination_discovery and request.unverified_destination_discovery
                and request.tls_context.verify_mode == ssl.CERT_NONE
                and request.tls_context.check_hostname is False
                and self._authorization is not None
                and set(self._authorization.operations) == {
                    (HttpMethod.POST, "/mgmt/system/user/login"),
                    (HttpMethod.GET, "/mgmt/system/config/tree/Organization"),
                }
            )
            if not verified and not backup_tls and not discovery_tls:
                raise ValueError("Unverified TLS is not authorized.")
            _timeouts(request.connect_timeout, request.read_timeout)
            if (
                self._authorization is None or self._max_response_bytes is None
                or not isinstance(request.deadline, OperationDeadline)
            ):
                raise BackendFailure(ErrorCategory.SAFETY_POLICY)
            deadline = request.deadline
            deadline.remaining()
            trace["failure_stage"] = "request_headers"
            outgoing = _headers(request.headers)
            if any(name.lower() in ("proxy-authorization", "proxy-connection") for name in outgoing):
                raise ValueError("Proxy headers are not supported.")
            trace["failure_stage"] = "request_target_authorization"
            parts = urlsplit(request.url)
            _origin(f"{parts.scheme}://{parts.netloc}")
            target = parts.path or "/"
            if "?" in request.url:
                target += "?" + parts.query
            if backup_tls and not (
                request.method == HttpMethod.GET
                or request.method == HttpMethod.POST and target == "/mgmt/system/user/login"
            ):
                raise BackendFailure(ErrorCategory.SAFETY_POLICY)
            if (
                parts.fragment or "#" in request.url or target.startswith("//")
                or "\\" in target or any(not 33 <= ord(c) <= 126 for c in target)
                or re.search(r"%(?![0-9a-fA-F]{2})", target)
            ):
                raise ValueError("Unsafe request target.")
            host = parts.hostname
            if host is None:
                raise ValueError("Missing origin.")
            port = parts.port or 443
            origin = (host.lower(), port)
            if self._origin is not None and self._origin != origin:
                raise ValueError("A backend cannot change origins.")
            if not self._authorization.permits(
                request.method, f"{parts.scheme}://{parts.netloc}", target,
            ):
                raise BackendFailure(ErrorCategory.SAFETY_POLICY)
            factory = self._factory
            if factory is None or factory is http.client.HTTPSConnection:
                if not self._allow_live:
                    raise BackendFailure(ErrorCategory.SAFETY_POLICY)
                factory = http.client.HTTPSConnection
            self._origin = origin
            trace["failure_stage"] = "request_cookies"
            cookie_request = Request(request.url, headers=outgoing, method=request.method.value)
            self._cookies.add_cookie_header(cookie_request)
            outgoing = _headers(dict(cookie_request.header_items()))
            outgoing["Connection"] = "close"
            trace["failure_stage"] = "connection_creation"
            connection = factory(
                host, port, timeout=min(request.connect_timeout, deadline.remaining()),
                context=request.tls_context,
            )
            resources.append(connection)
            # Explicit connect plus disabled auto-open prevents http.client reconnecting.
            connection.auto_open = 0
            connection.set_debuglevel(0)
            deadline.remaining()
            trace["failure_stage"] = "connection_connect"
            connection.connect()
            deadline.remaining()
            if connection.sock is None:
                raise http.client.NotConnected()
            connection.sock.settimeout(min(request.read_timeout, deadline.remaining()))
            # The public sock attribute is writable on http.client connections;
            # retain the factory protocol's covariant, read-only socket view.
            setattr(connection, "sock", _SocketGuard(
                connection.sock, tracker, deadline, request.read_timeout,
            ))
            trace["failure_stage"] = "request_transmission"
            connection.request(request.method.value, target, body=request.body, headers=outgoing)
            deadline.remaining()
            if connection.sock is not None:
                connection.sock.settimeout(min(request.read_timeout, deadline.remaining()))
            trace["failure_stage"] = "response_status_header_parsing"
            raw = connection.getresponse()
            resources.append(raw)
            trace["failure_stage"] = "response_status_validation"
            if type(raw.status) is int and 100 <= raw.status <= 599:
                trace["http_status"] = raw.status
            if type(raw.status) is not int or not 200 <= raw.status <= 599:
                raise ValueError("Invalid response status.")
            status = raw.status
            if status == 401:
                self._cookies.clear()
            deadline.remaining()
            trace["failure_stage"] = "response_headers"
            headers, cookie_message = _response_headers(raw, trace)
            deadline.remaining()
            if tracker.failed:
                raise RuntimeError("Local cleanup failed.")
            length = cookie_message.get("Content-Length")
            trace["failure_stage"] = "encoded_size_validation"
            if length is not None and (len(length) > 20 or int(length) > self._max_response_bytes):
                raise _ResponseValidationError("encoded_response_size_limit")
            trace["failure_stage"] = "content_encoding_validation"
            encoding = cookie_message.get("Content-Encoding", "identity").strip().lower()
            if encoding not in ("identity", "gzip"):
                raise _ResponseValidationError("unsupported_content_encoding")
            trace["failure_stage"] = "bounded_response_read"
            body_buffer = bytearray()
            while True:
                deadline.remaining()
                if connection.sock is not None:
                    connection.sock.settimeout(min(request.read_timeout, deadline.remaining()))
                size = min(65536, self._max_response_bytes - len(body_buffer) + 1)
                chunk = _read_response_body(raw, size)
                deadline.remaining()
                if not isinstance(chunk, bytes) or len(chunk) > size:
                    raise _ResponseValidationError("invalid_bounded_response_read")
                if len(body_buffer) + len(chunk) > self._max_response_bytes:
                    raise _ResponseValidationError("encoded_response_size_limit")
                if not chunk:
                    break
                body_buffer.extend(chunk)
            body = bytes(body_buffer)
            trace["failure_stage"] = "body_length_validation"
            if raw.status not in (204, 304) and length is not None and len(body) != int(length):
                raise _ResponseValidationError("content_length_mismatch")
            if encoding == "gzip" and status not in (204, 304):
                trace["failure_stage"] = "gzip_decompression"
                deadline.remaining()
                decoder = zlib.decompressobj(16 + zlib.MAX_WBITS)
                body = decoder.decompress(body, self._max_response_bytes + 1)
                deadline.remaining()
                if len(body) > self._max_response_bytes or decoder.unconsumed_tail:
                    raise _ResponseValidationError("decoded_response_size_limit")
                if not decoder.eof:
                    raise _ResponseValidationError("truncated_gzip_response")
                if decoder.unused_data:
                    raise _ResponseValidationError("gzip_trailing_data_or_multiple_members")
                headers = {
                    name: value for name, value in headers.items()
                    if name.lower() not in ("content-encoding", "content-length")
                }
            if tracker.failed:
                raise RuntimeError("Local cleanup failed.")
            if 200 <= status < 300:
                trace["failure_stage"] = "response_cookie_extraction"
                candidate = _StrictCookieJar()
                for cookie in self._cookies:
                    candidate.set_cookie(copy.deepcopy(cookie))
                candidate.extract_cookies(_CookieResponse(cookie_message), cookie_request)
            trace["failure_stage"] = "http_response_construction"
            response = HttpResponse(raw.status, body, headers)
            deadline.remaining()
        except BackendFailure as exc:
            failure = exc.category
            trace["exception_class"] = "BackendFailure"
        except ssl.SSLError:
            failure = ErrorCategory.TLS
            trace["exception_class"] = "SSLError"
        except TimeoutError:
            failure = ErrorCategory.TIMEOUT
            trace["exception_class"] = "TimeoutError"
        except (http.client.RemoteDisconnected, OSError):
            failure = ErrorCategory.CONNECTION
            trace["exception_class"] = "ConnectionError"
        except (http.client.HTTPException, ContractValidationError, ValueError, UnicodeError, zlib.error) as exc:
            failure = ErrorCategory.MALFORMED_RESPONSE
            trace["exception_class"] = (
                "ZlibError" if isinstance(exc, zlib.error)
                else type(exc).__name__ if isinstance(exc, http.client.HTTPException) and type(exc).__name__ in {
                    "HTTPException", "BadStatusLine", "IncompleteRead", "InvalidURL",
                    "NotConnected", "CannotSendRequest", "CannotSendHeader", "ResponseNotReady",
                    "LineTooLong", "UnknownProtocol", "UnknownTransferEncoding",
                }
                else "HTTPException" if isinstance(exc, http.client.HTTPException)
                else "ContractValidationError" if isinstance(exc, ContractValidationError)
                else "UnicodeError" if isinstance(exc, UnicodeError) else "ValueError"
            )
            trace["validation_reason"] = (
                exc.reason if isinstance(exc, _ResponseValidationError)
                else "invalid_gzip_stream" if isinstance(exc, zlib.error)
                else "invalid_header_syntax" if isinstance(exc, ContractValidationError)
                else "malformed_http_response" if isinstance(exc, http.client.HTTPException)
                else "invalid_text_encoding" if isinstance(exc, UnicodeError)
                else "invalid_cookie_attributes" if trace["failure_stage"] == "response_cookie_extraction"
                else "invalid_transport_contract"
            )
        except Exception:
            failure = ErrorCategory.BACKEND
            trace["exception_class"] = "UnexpectedException"
        finally:
            failed = _release(resources) + tracker.failed
            self._pending.extend(failed)
        # Raise only in send(), after raw library exceptions and cleanup contexts end.
        if failure is not None or failed:
            if failed and failure is None:
                trace.update(failure_stage="resource_cleanup", validation_reason="local_cleanup_failed")
            return BackendFailure(
                failure or ErrorCategory.BACKEND, status=status, cleanup_failed=bool(failed),
            )
        if response is None:
            return BackendFailure(ErrorCategory.BACKEND)
        try:
            trace["failure_stage"] = "deadline_validation"
            deadline.remaining()
        except BackendFailure as exc:
            trace["exception_class"] = "BackendFailure"
            return BackendFailure(exc.category, status=status)
        if candidate is not None:
            self._cookies = candidate
        return response

    def close(self) -> None:
        self._closed = True
        self._cookies.clear()
        self._pending = _release(self._pending)
        if self._pending:
            raise BackendFailure(ErrorCategory.BACKEND, cleanup_failed=True)
