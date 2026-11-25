"""Explicit HTTPS dispatch adapter; construction never connects or grants capabilities."""

import copy
import http.client
import math
import re
import ssl
import time
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


def _response_headers(response: _Response) -> tuple[dict[str, str], Message]:
    parsed = getattr(response, "headers", None)
    if isinstance(parsed, Message) and (
        parsed.defects or any(getattr(value, "defects", ()) for value in parsed.values())
    ):
        raise ValueError("Defective response headers.")
    message = Message()
    headers: dict[str, str] = {}
    seen: set[str] = set()
    pairs = response.getheaders()
    if not isinstance(pairs, list):
        raise ValueError("Invalid response headers.")
    for pair in pairs:
        if not isinstance(pair, tuple) or len(pair) != 2:
            raise ValueError("Invalid response header pair.")
        name, value = pair
        if not isinstance(name, str) or not isinstance(value, str):
            raise ValueError("Invalid response header type.")
        _headers({name: value}, for_request=False)
        key = name.lower()
        if key in seen and key != "set-cookie":
            raise ValueError("Repeated response headers are not qualified.")
        seen.add(key)
        message[name] = value
        # Set-Cookie is multi-valued and session-owned, not a flattened public header.
        if key != "set-cookie":
            headers[name] = value
    length = message.get("Content-Length")
    transfer = message.get("Transfer-Encoding")
    if (
        length is not None and (not re.fullmatch(r"[0-9]+", length) or transfer is not None)
        or transfer is not None and transfer.lower() != "chunked"
    ):
        raise ValueError("Unqualified response framing.")
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
        allow_insecure_lab: bool = False,
    ) -> None:
        if type(allow_live) is not bool or allow_live and connection_factory is not None:
            raise ValueError("Live dispatch must use the built-in HTTPS connection.")
        if type(allow_insecure_lab) is not bool:
            raise ValueError("Lab TLS selection must be explicit.")
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
        self._allow_insecure_lab = allow_insecure_lab
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
        outcome = self._attempt(request)
        if isinstance(outcome, BackendFailure):
            raise outcome
        return outcome

    def _attempt(self, request: BackendRequest) -> HttpResponse | BackendFailure:
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
                or type(request.lab_insecure_tls) is not bool
            ):
                raise ValueError("Unsafe backend request.")
            verified = (
                request.tls_context.verify_mode == ssl.CERT_REQUIRED
                and request.tls_context.check_hostname is True
            )
            lab_tls = (
                self._allow_insecure_lab and request.lab_insecure_tls
                and request.tls_context.verify_mode == ssl.CERT_NONE
                and request.tls_context.check_hostname is False
            )
            if not verified and not lab_tls:
                raise ValueError("Unverified TLS is not authorized.")
            _timeouts(request.connect_timeout, request.read_timeout)
            if (
                self._authorization is None or self._max_response_bytes is None
                or not isinstance(request.deadline, OperationDeadline)
            ):
                raise BackendFailure(ErrorCategory.SAFETY_POLICY)
            deadline = request.deadline
            deadline.remaining()
            outgoing = _headers(request.headers)
            if any(name.lower() in ("proxy-authorization", "proxy-connection") for name in outgoing):
                raise ValueError("Proxy headers are not supported.")
            parts = urlsplit(request.url)
            _origin(f"{parts.scheme}://{parts.netloc}")
            target = parts.path or "/"
            if "?" in request.url:
                target += "?" + parts.query
            if lab_tls and not (
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
            cookie_request = Request(request.url, headers=outgoing, method=request.method.value)
            self._cookies.add_cookie_header(cookie_request)
            outgoing = _headers(dict(cookie_request.header_items()))
            outgoing["Connection"] = "close"
            connection = factory(
                host, port, timeout=min(request.connect_timeout, deadline.remaining()),
                context=request.tls_context,
            )
            resources.append(connection)
            # Explicit connect plus disabled auto-open prevents http.client reconnecting.
            connection.auto_open = 0
            connection.set_debuglevel(0)
            deadline.remaining()
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
            connection.request(request.method.value, target, body=request.body, headers=outgoing)
            deadline.remaining()
            if connection.sock is not None:
                connection.sock.settimeout(min(request.read_timeout, deadline.remaining()))
            raw = connection.getresponse()
            resources.append(raw)
            if type(raw.status) is not int or not 200 <= raw.status <= 599:
                raise ValueError("Invalid response status.")
            status = raw.status
            if status == 401:
                self._cookies.clear()
            deadline.remaining()
            headers, cookie_message = _response_headers(raw)
            deadline.remaining()
            if tracker.failed:
                raise RuntimeError("Local cleanup failed.")
            length = cookie_message.get("Content-Length")
            if length is not None and int(length) > self._max_response_bytes:
                raise ValueError("Response exceeds byte budget.")
            if cookie_message.get("Content-Encoding", "identity").lower() != "identity":
                raise ValueError("Response transformations are not qualified.")
            body_buffer = bytearray()
            while True:
                deadline.remaining()
                if connection.sock is not None:
                    connection.sock.settimeout(min(request.read_timeout, deadline.remaining()))
                size = min(65536, self._max_response_bytes - len(body_buffer) + 1)
                chunk = _read_response_body(raw, size)
                deadline.remaining()
                if not isinstance(chunk, bytes) or len(chunk) > size:
                    raise ValueError("Invalid bounded response read.")
                if len(body_buffer) + len(chunk) > self._max_response_bytes:
                    raise ValueError("Response exceeds byte budget.")
                if not chunk:
                    break
                body_buffer.extend(chunk)
            body = bytes(body_buffer)
            if raw.status not in (204, 304) and length is not None and len(body) != int(length):
                raise ValueError("Incomplete response body.")
            if tracker.failed:
                raise RuntimeError("Local cleanup failed.")
            if 200 <= status < 300:
                candidate = _StrictCookieJar()
                for cookie in self._cookies:
                    candidate.set_cookie(copy.deepcopy(cookie))
                candidate.extract_cookies(_CookieResponse(cookie_message), cookie_request)
            response = HttpResponse(raw.status, body, headers)
            deadline.remaining()
        except BackendFailure as exc:
            failure = exc.category
        except ssl.SSLError:
            failure = ErrorCategory.TLS
        except TimeoutError:
            failure = ErrorCategory.TIMEOUT
        except (http.client.RemoteDisconnected, OSError):
            failure = ErrorCategory.CONNECTION
        except (http.client.HTTPException, ContractValidationError, ValueError, UnicodeError):
            failure = ErrorCategory.MALFORMED_RESPONSE
        except Exception:
            failure = ErrorCategory.BACKEND
        finally:
            failed = _release(resources) + tracker.failed
            self._pending.extend(failed)
        # Raise only in send(), after raw library exceptions and cleanup contexts end.
        if failure is not None or failed:
            return BackendFailure(
                failure or ErrorCategory.BACKEND, status=status, cleanup_failed=bool(failed),
            )
        if response is None:
            return BackendFailure(ErrorCategory.BACKEND)
        try:
            deadline.remaining()
        except BackendFailure as exc:
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
