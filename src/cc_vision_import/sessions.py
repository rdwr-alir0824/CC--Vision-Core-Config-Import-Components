"""Explicit local session ownership over injected, mock-qualified backends."""

import math
import time
from abc import ABC, abstractmethod
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Protocol, Self

from .authentication import (
    AuthenticationError, AuthenticationFailure, AuthenticationFailureCategory,
    AuthenticationOutcome, AuthenticationRequest, AuthenticationStrategy,
    CyberControllerAuthenticationStrategy, ExpirationReason, ResolvedCredentials,
    SecretResolver, SessionRole, SessionSnapshot, SessionState,
    VisionAuthenticationStrategy,
)
from .transport import (
    BackendRequest, ErrorCategory, HttpBackend, HttpMethod, HttpResponse, HttpTransport,
    TransportConfig, TransportError,
)


class SessionBackend(HttpBackend, Protocol):
    def close(self) -> None:
        """Release local connections and discard all cookies/authentication state.

        No remote logout is authorized by this method. Each instance must belong
        to one owner and maintain its own cookie jar; no ambient credentials.
        """
        ...


class MockSessionBackend(ABC):
    """Nominal opt-in for in-memory development/test backends, never network adapters."""

    @abstractmethod
    def send(self, request: BackendRequest) -> HttpResponse: ...

    @abstractmethod
    def close(self) -> None: ...


def _call[T](
    action: Callable[[], T], category: AuthenticationFailureCategory,
) -> T | AuthenticationFailure:
    try:
        return action()
    except Exception:
        return AuthenticationFailure(category)


def _transport_failure(error: TransportError) -> AuthenticationFailure:
    category = (
        AuthenticationFailureCategory.HTTP_REJECTION if error.status == 401 else
        AuthenticationFailureCategory.AUTHORIZATION if error.status == 403 else
        AuthenticationFailureCategory.TRANSPORT
    )
    return AuthenticationFailure(category, error.status, error.category, error.reason)


@dataclass
class _OwnedSession:
    request: AuthenticationRequest
    strategy: AuthenticationStrategy
    backend: SessionBackend | None = field(repr=False)
    transport: HttpTransport | None = field(repr=False)
    state: SessionState = SessionState.INITIALIZED
    credentials: ResolvedCredentials | None = field(default=None, repr=False)
    deadline: float | None = None
    expiration_reason: ExpirationReason | None = None
    outcome: AuthenticationOutcome | None = None


class SessionManager:
    def __init__(
        self, backend_factory: Callable[[], SessionBackend], resolver: SecretResolver, *,
        clock: Callable[[], float] = time.monotonic, mock_only: bool = False,
    ) -> None:
        if type(mock_only) is not bool:
            raise AuthenticationError(AuthenticationFailure(AuthenticationFailureCategory.INITIALIZATION))
        self._factory = backend_factory
        self._resolver = resolver
        self._clock = clock
        self._mock_only = mock_only
        self._sessions: dict[SessionRole, _OwnedSession] = {}

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close_all()

    def initialize(self, request: AuthenticationRequest, config: TransportConfig) -> SessionSnapshot:
        if not isinstance(request, AuthenticationRequest) or not isinstance(config, TransportConfig):
            raise AuthenticationError(AuthenticationFailure(AuthenticationFailureCategory.INITIALIZATION))
        request.__post_init__()
        config.__post_init__()
        previous = self._sessions.get(request.role)
        if previous is not None and previous.state != SessionState.CLOSED:
            raise AuthenticationError(AuthenticationFailure(AuthenticationFailureCategory.OWNERSHIP))
        backend = _call(self._factory, AuthenticationFailureCategory.INITIALIZATION)
        if isinstance(backend, AuthenticationFailure):
            raise AuthenticationError(backend)
        if any(item.backend is backend for item in self._sessions.values()):
            raise AuthenticationError(AuthenticationFailure(AuthenticationFailureCategory.OWNERSHIP))
        close = getattr(backend, "close", None)
        if (
            not callable(getattr(backend, "send", None)) or not callable(close)
            or self._mock_only and not isinstance(backend, MockSessionBackend)
        ):
            error = AuthenticationError(AuthenticationFailure(AuthenticationFailureCategory.INITIALIZATION))
            if callable(close):
                cleanup = _call(close, AuthenticationFailureCategory.CLEANUP)
                if isinstance(cleanup, AuthenticationFailure):
                    error.add_note("Local cleanup of rejected backend failed.")
            raise error
        strategy: AuthenticationStrategy = (
            VisionAuthenticationStrategy() if request.product == "vision"
            else CyberControllerAuthenticationStrategy()
        )
        self._sessions[request.role] = _OwnedSession(request, strategy, backend, None)
        transport = _call(
            lambda: HttpTransport(config, backend),
            AuthenticationFailureCategory.INITIALIZATION,
        )
        if isinstance(transport, AuthenticationFailure):
            self._sessions[request.role].state = SessionState.FAILED
            self.close(request.role)
            raise AuthenticationError(transport)
        self._sessions[request.role].transport = transport
        return self.snapshot(request.role)

    def _session(self, role: SessionRole) -> _OwnedSession:
        if not isinstance(role, SessionRole) or role not in self._sessions:
            raise AuthenticationError(AuthenticationFailure(AuthenticationFailureCategory.INVALID_STATE))
        return self._sessions[role]

    def uses_mock_backend(self, role: SessionRole) -> bool:
        return isinstance(self._session(role).backend, MockSessionBackend)

    def _now(self) -> float:
        value = _call(self._clock, AuthenticationFailureCategory.CLOCK)
        if isinstance(value, AuthenticationFailure):
            raise AuthenticationError(value)
        if type(value) not in (int, float) or not math.isfinite(value):
            raise AuthenticationError(AuthenticationFailure(AuthenticationFailureCategory.CLOCK))
        return value

    def _refresh(self, session: _OwnedSession) -> None:
        if session.state == SessionState.AUTHENTICATED and session.deadline is not None:
            now = _call(self._now, AuthenticationFailureCategory.CLOCK)
            if isinstance(now, AuthenticationFailure):
                self._fail(session, now)
                raise AuthenticationError(now)
            if now >= session.deadline:
                session.state = SessionState.EXPIRED
                session.expiration_reason = ExpirationReason.LOCAL_LIFETIME
                session.credentials = None

    def snapshot(self, role: SessionRole) -> SessionSnapshot:
        session = self._session(role)
        self._refresh(session)
        return SessionSnapshot(
            role, session.request.product, session.request.version, session.state,
            session.expiration_reason, session.outcome,
        )

    def is_authenticated(self, role: SessionRole) -> bool:
        return self.snapshot(role).state == SessionState.AUTHENTICATED

    @staticmethod
    def _fail(session: _OwnedSession, failure: AuthenticationFailure) -> None:
        session.credentials = None
        session.deadline = None
        session.state = SessionState.FAILED
        session.outcome = AuthenticationOutcome(False, failure=failure)

    def authenticate(self, role: SessionRole) -> AuthenticationOutcome:
        session = self._session(role)
        if session.state != SessionState.INITIALIZED or session.transport is None:
            raise AuthenticationError(AuthenticationFailure(AuthenticationFailureCategory.INVALID_STATE))
        credentials = _call(
            lambda: self._resolver.resolve(session.request.credential_ref),
            AuthenticationFailureCategory.SECRET_RESOLUTION,
        )
        if isinstance(credentials, AuthenticationFailure):
            self._fail(session, credentials)
            raise AuthenticationError(credentials)
        if not isinstance(credentials, ResolvedCredentials):
            failure = AuthenticationFailure(AuthenticationFailureCategory.INVALID_CREDENTIALS)
            self._fail(session, failure)
            raise AuthenticationError(failure)
        login = _call(
            lambda: session.strategy.login_request(credentials),
            AuthenticationFailureCategory.INVALID_CREDENTIALS,
        )
        if isinstance(login, AuthenticationFailure):
            self._fail(session, login)
            raise AuthenticationError(login)
        failure = None
        try:
            response = session.transport.request(
                HttpMethod.POST, login.segments, headers=login.headers, body=login.body,
            )
        except TransportError as error:
            failure = _transport_failure(error)
        if failure is not None:
            self._fail(session, failure)
            raise AuthenticationError(failure)
        outcome = session.strategy.interpret(response)
        if outcome.failure is not None:
            self._fail(session, outcome.failure)
            raise AuthenticationError(outcome.failure)
        now = _call(self._now, AuthenticationFailureCategory.CLOCK)
        if isinstance(now, AuthenticationFailure):
            self._fail(session, now)
            raise AuthenticationError(now)
        lifetime = session.request.expiration.max_age_seconds
        session.deadline = None if lifetime is None else now + lifetime
        session.credentials = credentials if session.strategy.retain_credentials else None
        session.state = SessionState.AUTHENTICATED
        session.outcome = outcome
        return outcome

    def request(
        self, role: SessionRole, method: HttpMethod, segments: tuple[str, ...], *,
        query: tuple[tuple[str, str], ...] = (),
        headers: Mapping[str, str] | None = None, body: bytes | None = None,
        expect_json: bool = False,
    ) -> HttpResponse:
        session = self._session(role)
        self._refresh(session)
        if session.state == SessionState.EXPIRED:
            raise AuthenticationError(AuthenticationFailure(AuthenticationFailureCategory.EXPIRED))
        if session.state != SessionState.AUTHENTICATED or session.transport is None:
            raise AuthenticationError(AuthenticationFailure(AuthenticationFailureCategory.INVALID_STATE))
        if headers is not None and (
            not isinstance(headers, Mapping) or any(
                not isinstance(name, str)
                or name.lower() in ("authorization", "cookie", "proxy-authorization")
                for name in headers
            )
        ):
            raise AuthenticationError(AuthenticationFailure(AuthenticationFailureCategory.INVALID_CREDENTIALS))
        managed_headers = session.strategy.request_headers(session.credentials)
        combined = {**managed_headers, **({} if headers is None else headers)}
        rejection = None
        try:
            return session.transport.request(
                method, segments, query=query, headers=combined,
                body=body, expect_json=expect_json,
            )
        except TransportError as error:
            if error.category != ErrorCategory.AUTHENTICATION:
                raise
            rejection = _transport_failure(error)
        session.credentials = None
        session.deadline = None
        session.state = SessionState.EXPIRED
        session.expiration_reason = ExpirationReason.HTTP_REJECTION
        session.outcome = AuthenticationOutcome(False, failure=rejection)
        raise AuthenticationError(rejection)

    def close(self, role: SessionRole) -> None:
        session = self._session(role)
        if session.state == SessionState.CLOSED:
            return
        session.credentials = None
        session.deadline = None
        backend = session.backend
        result = None if backend is None else _call(backend.close, AuthenticationFailureCategory.CLEANUP)
        if isinstance(result, AuthenticationFailure):
            session.state = SessionState.CLEANUP_FAILED
            raise AuthenticationError(result)
        session.backend = None
        session.transport = None
        session.state = SessionState.CLOSED

    def close_all(self) -> None:
        failures = []
        for role in self._sessions:
            failure = _call(lambda: self.close(role), AuthenticationFailureCategory.CLEANUP)
            if isinstance(failure, AuthenticationFailure):
                failures.append(failure)
        if failures:
            raise AuthenticationError(AuthenticationFailure(AuthenticationFailureCategory.CLEANUP)) from None
