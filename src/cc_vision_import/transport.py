"""Backend-independent HTTP mechanics; no network implementation or product APIs."""

import math
import re
import ssl
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Protocol
from urllib.parse import quote, urlencode

from ._contract_validation import ContractReader
from ._json import load_json
from .contracts import ContractValidationError


class HttpMethod(StrEnum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"


class ErrorCategory(StrEnum):
    CONNECTION = "connection_failure"
    TIMEOUT = "timeout"
    TLS = "tls_certificate_failure"
    AUTHENTICATION = "authentication_rejection"
    AUTHORIZATION = "authorization_failure"
    HTTP = "http_error"
    MALFORMED_RESPONSE = "malformed_response"
    INDETERMINATE_WRITE = "indeterminate_write_outcome"
    BACKEND = "backend_failure"
    SAFETY_POLICY = "safety_policy_rejection"


class TransportError(Exception):
    def __init__(
        self, category: ErrorCategory, *, reason: ErrorCategory | None = None,
        status: int | None = None, attempts: int = 1,
    ) -> None:
        super().__init__(f"HTTP transport failed: {category.value}.")
        self.category = category
        self.reason = reason or category
        self.status = status
        self.attempts = attempts
        self.cleanup_failed = False
        self.backend_failure: ErrorCategory | None = None


class BackendFailure(Exception):
    """Adapters map library errors here, never retaining raw exception text."""

    def __init__(
        self, category: ErrorCategory, *, cleanup_failed: bool = False,
        status: int | None = None,
    ) -> None:
        if category not in (
            ErrorCategory.CONNECTION, ErrorCategory.TIMEOUT, ErrorCategory.TLS,
            ErrorCategory.MALFORMED_RESPONSE, ErrorCategory.BACKEND,
            ErrorCategory.SAFETY_POLICY,
        ) or type(cleanup_failed) is not bool or (
            status is not None and (type(status) is not int or not 200 <= status <= 599)
        ):
            raise ValueError("Unsupported backend failure category.")
        super().__init__("HTTP backend failed.")
        self.category = category
        self.cleanup_failed = cleanup_failed
        self.status = status


_reader = ContractReader("transport")


def _origin(value: object) -> str:
    origin = None
    try:
        origin = _reader.base_url(value, "$.base_url")
    except ContractValidationError:
        pass
    if origin is None:
        _reader.fail("invalid_url", "$.base_url", "Use a valid HTTPS origin without credentials, path, query, or fragment.")
    return origin


def _tls_context(trusted_ca: str | None) -> ssl.SSLContext:
    if trusted_ca is not None:
        if (
            not isinstance(trusted_ca, str)
            or not trusted_ca
            or trusted_ca.replace("/", "\\").startswith("\\\\")
            or "://" in trusted_ca
            or any(not c.isprintable() for c in trusted_ca)
        ):
            _reader.fail("invalid_ca", "$.trusted_ca", "Use a trusted local CA bundle file.")
    context = None
    try:
        if trusted_ca is None or Path(trusted_ca).is_file():
            context = ssl.create_default_context(cafile=trusted_ca)
    except (OSError, ValueError):
        pass
    if context is None:
        _reader.fail("invalid_ca", "$.trusted_ca", "CA trust could not be loaded; TLS verification remains required.")
    return context


def _timeout(value: float, name: str) -> None:
    if (
        type(value) not in (int, float)
        or not 0 < value <= 300
        or not math.isfinite(value)
    ):
        _reader.fail("invalid_timeout", f"$.{name}", "Timeout must be finite and greater than zero, at most 300 seconds.")


def _timeouts(connect_timeout: float, read_timeout: float) -> None:
    _timeout(connect_timeout, "connect_timeout")
    _timeout(read_timeout, "read_timeout")


@dataclass(frozen=True)
class OperationDeadline:
    """One monotonic clock domain and absolute expiry shared by every attempt."""

    expires_at: float
    clock: Callable[[], float] = field(default=time.monotonic, repr=False, compare=False)

    def remaining(self) -> float:
        failure = ErrorCategory.BACKEND
        remaining = None
        try:
            now = self.clock()
            if (
                type(now) in (int, float) and math.isfinite(now)
                and type(self.expires_at) in (int, float) and math.isfinite(self.expires_at)
            ):
                remaining = self.expires_at - now
                if not math.isfinite(remaining):
                    remaining = None
                elif remaining <= 0:
                    failure = ErrorCategory.TIMEOUT
                    remaining = None
        except Exception:
            pass
        if remaining is None:
            raise BackendFailure(failure)
        return remaining


@dataclass(frozen=True, kw_only=True)
class TransportConfig:
    base_url: str = field(repr=False)
    connect_timeout: float
    read_timeout: float
    trusted_ca: str | None = field(default=None, repr=False)
    verify_tls: bool = True
    read_retries: int = 0
    operation_timeout: float | None = None

    def __post_init__(self) -> None:
        _origin(self.base_url)
        self._validate_tls()
        _timeouts(self.connect_timeout, self.read_timeout)
        if self.operation_timeout is not None:
            _timeout(self.operation_timeout, "operation_timeout")
        if type(self.read_retries) is not int or not 0 <= self.read_retries <= 3:
            _reader.fail("invalid_retry_policy", "$.read_retries", "GET retries must be an integer from zero through three.")
        self.tls_context()

    def _validate_tls(self) -> None:
        if self.verify_tls is not True:
            _reader.fail("unsafe_tls", "$.verify_tls", "TLS verification is mandatory.")

    def tls_context(self) -> ssl.SSLContext:
        return _tls_context(self.trusted_ca)

    @property
    def unverified_vision_backup(self) -> bool:
        return False


def build_url(
    base_url: str, segments: tuple[str, ...],
    query: tuple[tuple[str, str], ...] = (),
) -> str:
    """Encode untrusted components rather than joining caller-supplied URLs."""
    origin = _origin(base_url).rstrip("/")
    if not isinstance(segments, tuple) or not isinstance(query, tuple):
        _reader.fail("invalid_url", "$.url", "Use tuples of path segments and query pairs.")
    encoded: list[str] = []
    for segment in segments:
        text = _reader.text(segment, "$.path")
        if text in (".", "..") or any(c in text for c in "/\\%"):
            _reader.fail("unsafe_path", "$.path", "Path segments cannot contain traversal, separators, or pre-encoding.")
        encoded.append(quote(text, safe=""))
    pairs: list[tuple[str, str]] = []
    for pair in query:
        if not isinstance(pair, tuple) or len(pair) != 2:
            _reader.fail("invalid_url", "$.query", "Expected query key/value pairs.")
        key, value = pair
        pairs.append((_reader.text(key, "$.query"), _reader.text(value, "$.query")))
    url = origin + "/" + "/".join(encoded)
    return url + ("?" + urlencode(pairs) if pairs else "")


def _headers(values: Mapping[str, str], *, for_request: bool = True) -> dict[str, str]:
    if not isinstance(values, Mapping):
        _reader.fail("invalid_headers", "$.headers", "Expected a header mapping.")
    result: dict[str, str] = {}
    seen: set[str] = set()
    for name, value in values.items():
        if (
            not isinstance(name, str)
            or not re.fullmatch(r"[!#$%&'*+.^_`|~0-9A-Za-z-]+", name)
            or not isinstance(value, str)
            or any(ord(c) < 32 or ord(c) > 126 for c in value)
            or name.lower() in seen
            or (for_request and name.lower() in ("host", "content-length", "transfer-encoding", "connection"))
        ):
            _reader.fail("invalid_headers", "$.headers", "Header syntax, duplicates, or transport-owned headers are invalid.")
        seen.add(name.lower())
        result[name] = value
    return result


def redact_headers(values: Mapping[str, str]) -> dict[str, str]:
    # Unknown/custom headers can carry secrets too; never allowlist their values.
    return {name: "[REDACTED]" for name in _headers(values, for_request=False)}


@dataclass(frozen=True)
class BackendRequest:
    method: HttpMethod
    url: str = field(repr=False)
    headers: Mapping[str, str] = field(repr=False)
    body: bytes | None = field(repr=False)
    connect_timeout: float
    read_timeout: float
    tls_context: ssl.SSLContext = field(repr=False)
    follow_redirects: bool = False
    deadline: OperationDeadline | None = None
    unverified_vision_backup: bool = False


@dataclass(frozen=True)
class HttpResponse:
    status: int
    body: bytes = field(default=b"", repr=False)
    headers: Mapping[str, str] = field(default_factory=dict, repr=False)


class HttpBackend(Protocol):
    def send(self, request: BackendRequest) -> HttpResponse:
        """One attempt only: no retries, redirects, auth renewal, or secret logging.

        Honor TLS hostname/certificate checks, both timeouts and an optional shared
        deadline. Concrete adapters must require finite body/deadline budgets and
        fail closed for operations they cannot bound. Incrementally consume
        and close the response; map IO failures to BackendFailure. The caller
        owns backend/session cleanup. Never use ambient proxy/auth settings.
        """
        ...


class HttpTransport:
    def __init__(
        self, config: TransportConfig, backend: HttpBackend, *,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if not isinstance(config, TransportConfig) or not callable(getattr(backend, "send", None)):
            _reader.fail("invalid_transport", "$", "A validated configuration and injected backend are required.")
        config.__post_init__()
        self._config = config
        self._backend = backend
        self._clock = clock

    def request(
        self, method: HttpMethod, segments: tuple[str, ...], *,
        query: tuple[tuple[str, str], ...] = (),
        headers: Mapping[str, str] | None = None, body: bytes | None = None,
        expect_json: bool = False,
    ) -> HttpResponse:
        if not isinstance(method, HttpMethod):
            _reader.fail("invalid_method", "$.method", "Use a supported HTTP method.")
        if body is not None and (not isinstance(body, bytes) or method == HttpMethod.GET):
            _reader.fail("invalid_body", "$.body", "Use bytes for write bodies; GET bodies are not allowed.")
        if type(expect_json) is not bool:
            _reader.fail("invalid_response_policy", "$.expect_json", "JSON expectation must be boolean.")
        deadline = None
        if self._config.operation_timeout is not None:
            failure = None
            try:
                now = self._clock()
                if type(now) not in (int, float) or not math.isfinite(now):
                    raise ValueError("Invalid monotonic clock.")
                deadline = OperationDeadline(now + self._config.operation_timeout, self._clock)
                deadline.remaining()
            except BackendFailure as exc:
                failure = self._error(method, exc.category, 1)
            except Exception:
                failure = self._error(method, ErrorCategory.BACKEND, 1)
            if failure is not None:
                raise failure
        request = BackendRequest(
            method, build_url(self._config.base_url, segments, query),
            _headers({} if headers is None else headers), body,
            self._config.connect_timeout, self._config.read_timeout,
            self._config.tls_context(),
            deadline=deadline,
            unverified_vision_backup=self._config.unverified_vision_backup,
        )
        limit = 1 + (self._config.read_retries if method == HttpMethod.GET else 0)
        for attempt in range(1, limit + 1):
            outcome = self._send(request, expect_json, attempt)
            if isinstance(outcome, HttpResponse):
                return outcome
            if (
                attempt < limit and not outcome.cleanup_failed
                and outcome.category in (ErrorCategory.CONNECTION, ErrorCategory.TIMEOUT)
            ):
                expired = self._deadline_failure(request, attempt)
                if expired is not None:
                    raise expired
                continue
            raise outcome
        raise AssertionError("Unreachable transport retry state.")

    def _send(
        self, request: BackendRequest, expect_json: bool, attempt: int,
    ) -> HttpResponse | TransportError:
        # Return sanitized failures, then raise outside the except scope so raw
        # backend exceptions cannot be exposed through exception chaining.
        try:
            if request.deadline is not None:
                request.deadline.remaining()
            response = self._backend.send(request)
        except BackendFailure as exc:
            error = (
                self._http_error(request.method, exc.status, attempt)
                if exc.status is not None and not 200 <= exc.status < 300
                else self._error(request.method, exc.category, attempt, exc.status)
            )
            error.backend_failure = exc.category
            if exc.cleanup_failed:
                error.cleanup_failed = True
                error.add_note("Local backend resource cleanup failed.")
            return error
        except Exception:
            return self._error(request.method, ErrorCategory.BACKEND, attempt)
        if (
            not isinstance(response, HttpResponse)
            or type(response.status) is not int
            or not 200 <= response.status <= 599
            or not isinstance(response.body, bytes)
        ):
            return self._error(request.method, ErrorCategory.MALFORMED_RESPONSE, attempt)
        status = response.status
        if not 200 <= status < 300:
            return self._http_error(request.method, status, attempt)
        expired = self._deadline_failure(request, attempt, status)
        if expired is not None:
            return expired
        if expect_json:
            valid = True
            try:
                load_json(response.body.decode("utf-8"))
            except (UnicodeError, ValueError, RecursionError):
                valid = False
            if not valid:
                return self._error(request.method, ErrorCategory.MALFORMED_RESPONSE, attempt, status)
        expired = self._deadline_failure(request, attempt, status)
        if expired is not None:
            return expired
        return response

    def _deadline_failure(
        self, request: BackendRequest, attempt: int, status: int | None = None,
    ) -> TransportError | None:
        failure = None
        try:
            if request.deadline is not None:
                request.deadline.remaining()
        except BackendFailure as exc:
            failure = self._error(request.method, exc.category, attempt, status)
        return failure

    @classmethod
    def _http_error(cls, method: HttpMethod, status: int, attempt: int) -> TransportError:
        category = (
            ErrorCategory.AUTHENTICATION if status == 401 else
            ErrorCategory.AUTHORIZATION if status == 403 else ErrorCategory.HTTP
        )
        # Server errors may occur after a mutation has already taken effect.
        if status == 408 or status >= 500:
            return cls._error(method, category, attempt, status)
        return TransportError(category, status=status, attempts=attempt)

    @staticmethod
    def _error(
        method: HttpMethod, reason: ErrorCategory, attempt: int, status: int | None = None,
    ) -> TransportError:
        category = reason if method == HttpMethod.GET else ErrorCategory.INDETERMINATE_WRITE
        return TransportError(category, reason=reason, status=status, attempts=attempt)
