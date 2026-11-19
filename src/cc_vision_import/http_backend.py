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
from urllib.parse import urlsplit
from urllib.request import Request

from .contracts import ContractValidationError
from .transport import (
    BackendFailure, BackendRequest, ErrorCategory, HttpMethod, HttpResponse,
    _headers, _origin, _timeouts,
)


class _Closable(Protocol):
    def close(self) -> None: ...


class _Socket(_Closable, Protocol):
    def settimeout(self, value: float) -> None: ...
    def makefile(self, mode: Literal["rb"]) -> BinaryIO: ...


class _Response(_Closable, Protocol):
    @property
    def status(self) -> int: ...

    def getheaders(self) -> list[tuple[str, str]]: ...
    def read(self) -> bytes: ...


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
    """Injection seam for offline doubles, not a mock-capability declaration."""

    def __call__(
        self, host: str, port: int, *, timeout: float, context: ssl.SSLContext,
    ) -> _Connection: ...


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
    def __init__(self, resource: BinaryIO, tracker: _CleanupTracker) -> None:
        self._resource = resource
        self._tracker = tracker

    def __getattr__(self, name: str) -> object:
        return getattr(self._resource, name)

    def read(self, size: int = -1) -> bytes:
        return self._resource.read(size)

    def readline(self, size: int = -1) -> bytes:
        return self._resource.readline(size)

    def close(self) -> None:
        self._tracker.close(self._resource)


class _SocketGuard:
    def __init__(self, resource: _Socket, tracker: _CleanupTracker) -> None:
        self._resource = resource
        self._tracker = tracker

    def __getattr__(self, name: str) -> object:
        return getattr(self._resource, name)

    def makefile(self, mode: Literal["rb"]) -> _FileGuard:
        return _FileGuard(self._resource.makefile(mode), self._tracker)

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


class StdlibHttpBackend:
    """One origin and private cookie jar per session; not thread-safe or a mock backend."""

    def __init__(self, *, connection_factory: ConnectionFactory | None = None) -> None:
        self._factory: ConnectionFactory = (
            http.client.HTTPSConnection if connection_factory is None else connection_factory
        )
        self._cookies = _StrictCookieJar()
        self._origin: tuple[str, int] | None = None
        self._pending: list[_Closable] = []
        self._closed = False

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
                or request.tls_context.verify_mode != ssl.CERT_REQUIRED
                or request.tls_context.check_hostname is not True
                or request.tls_context.keylog_filename is not None
            ):
                raise ValueError("Unsafe backend request.")
            _timeouts(request.connect_timeout, request.read_timeout)
            outgoing = _headers(request.headers)
            if any(name.lower() in ("proxy-authorization", "proxy-connection") for name in outgoing):
                raise ValueError("Proxy headers are not supported.")
            parts = urlsplit(request.url)
            _origin(f"{parts.scheme}://{parts.netloc}")
            target = parts.path or "/"
            if parts.query:
                target += "?" + parts.query
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
            self._origin = origin
            cookie_request = Request(request.url, headers=outgoing, method=request.method.value)
            self._cookies.add_cookie_header(cookie_request)
            outgoing = _headers(dict(cookie_request.header_items()))
            outgoing["Connection"] = "close"
            connection = self._factory(
                host, port, timeout=request.connect_timeout, context=request.tls_context,
            )
            resources.append(connection)
            # Explicit connect plus disabled auto-open prevents http.client reconnecting.
            connection.auto_open = 0
            connection.set_debuglevel(0)
            connection.connect()
            if connection.sock is None:
                raise http.client.NotConnected()
            connection.sock.settimeout(request.read_timeout)
            # The public sock attribute is writable on http.client connections;
            # retain the factory protocol's covariant, read-only socket view.
            setattr(connection, "sock", _SocketGuard(connection.sock, tracker))
            connection.request(request.method.value, target, body=request.body, headers=outgoing)
            raw = connection.getresponse()
            resources.append(raw)
            if type(raw.status) is not int or not 200 <= raw.status <= 599:
                raise ValueError("Invalid response status.")
            status = raw.status
            if status == 401:
                self._cookies.clear()
            headers, cookie_message = _response_headers(raw)
            if tracker.failed:
                raise RuntimeError("Local cleanup failed.")
            body = raw.read()
            if not isinstance(body, bytes):
                raise ValueError("Invalid response body.")
            length = cookie_message.get("Content-Length")
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
        if candidate is not None:
            self._cookies = candidate
        return response

    def close(self) -> None:
        self._closed = True
        self._cookies.clear()
        self._pending = _release(self._pending)
        if self._pending:
            raise BackendFailure(ErrorCategory.BACKEND, cleanup_failed=True)
