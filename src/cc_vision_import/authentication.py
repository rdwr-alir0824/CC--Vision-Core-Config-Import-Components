"""Mock-qualified authentication contracts, not product compatibility claims."""

import base64
import json
import math
from dataclasses import dataclass, field
from enum import StrEnum
from typing import ClassVar, Protocol

from ._contract_validation import ContractReader
from ._json import load_json
from .contracts import ProductName
from .transport import ErrorCategory, HttpResponse


class SessionRole(StrEnum):
    SOURCE = "source"
    DESTINATION = "destination"


class SessionState(StrEnum):
    INITIALIZED = "initialized"
    AUTHENTICATED = "authenticated"
    FAILED = "failed"
    EXPIRED = "expired"
    CLEANUP_FAILED = "cleanup_failed"
    CLOSED = "closed"


class ExpirationReason(StrEnum):
    LOCAL_LIFETIME = "local_lifetime"
    HTTP_REJECTION = "http_rejection"


class AuthenticationFailureCategory(StrEnum):
    HTTP_REJECTION = "http_authentication_rejection"
    AUTHORIZATION = "authorization_rejection"
    APPLICATION_REJECTION = "application_login_rejection"
    MALFORMED_RESPONSE = "malformed_login_response"
    TRANSPORT = "transport_failure"
    SECRET_RESOLUTION = "secret_resolution_failure"
    INVALID_CREDENTIALS = "invalid_credentials"
    INVALID_STATE = "invalid_session_state"
    EXPIRED = "session_expired"
    INITIALIZATION = "session_initialization_failure"
    OWNERSHIP = "session_ownership_conflict"
    CLEANUP = "local_cleanup_failure"
    CLOCK = "session_clock_failure"


class LoginEvidence(StrEnum):
    APPLICATION_STATUS_OK = "legacy_application_status_ok"
    HTTP_200_ONLY = "legacy_http_200_only"


@dataclass(frozen=True)
class AuthenticationFailure:
    category: AuthenticationFailureCategory
    status: int | None = None
    transport_category: ErrorCategory | None = None
    transport_reason: ErrorCategory | None = None


class AuthenticationError(Exception):
    def __init__(self, failure: AuthenticationFailure) -> None:
        super().__init__(f"Authentication/session failure: {failure.category.value}.")
        self.failure = failure


@dataclass(frozen=True)
class CredentialReference:
    value: str = field(repr=False)

    def __post_init__(self) -> None:
        ContractReader("authentication").reference(self.value, "$.credential_ref")


@dataclass(frozen=True)
class ResolvedCredentials:
    username: str = field(repr=False)
    password: str = field(repr=False)

    def __post_init__(self) -> None:
        if any(
            not isinstance(value, str) or not value
            or any(not character.isprintable() for character in value)
            for value in (self.username, self.password)
        ):
            raise AuthenticationError(AuthenticationFailure(AuthenticationFailureCategory.INVALID_CREDENTIALS))


class SecretResolver(Protocol):
    def resolve(self, reference: CredentialReference) -> ResolvedCredentials:
        """Resolve in memory without logging secrets; storage policy is injected."""
        ...


@dataclass(frozen=True)
class SessionExpiration:
    """Optional operator-imposed lifetime, not a discovered server TTL."""

    max_age_seconds: float | None = None

    def __post_init__(self) -> None:
        value = self.max_age_seconds
        if value is None:
            return
        valid = False
        if type(value) in (int, float):
            try:
                valid = value > 0 and math.isfinite(value)
            except OverflowError:
                pass
        if not valid:
            ContractReader("authentication").fail(
                "invalid_expiration", "$.expiration",
                "Local lifetime must be finite and positive, or omitted.",
            )


@dataclass(frozen=True)
class AuthenticationRequest:
    role: SessionRole
    product: ProductName
    version: str
    credential_ref: CredentialReference = field(repr=False)
    expiration: SessionExpiration = field(default_factory=SessionExpiration)

    def __post_init__(self) -> None:
        reader = ContractReader("authentication")
        if not isinstance(self.role, SessionRole):
            reader.fail("invalid_role", "$.role", "Use an explicit source or destination session role.")
        reader.product(self.product, "$.product")
        reader.version(self.version, "$.version")
        if not isinstance(self.credential_ref, CredentialReference):
            reader.fail("invalid_reference", "$.credential_ref", "A credential reference is required.")
        if not isinstance(self.expiration, SessionExpiration):
            reader.fail("invalid_expiration", "$.expiration", "An explicit session expiration policy is required.")


@dataclass(frozen=True)
class AuthenticationOutcome:
    authenticated: bool
    evidence: LoginEvidence | None = None
    failure: AuthenticationFailure | None = None
    compatibility_verified: ClassVar[bool] = False


@dataclass(frozen=True)
class SessionSnapshot:
    role: SessionRole
    product: ProductName
    version: str
    state: SessionState
    expiration_reason: ExpirationReason | None
    last_authentication: AuthenticationOutcome | None


@dataclass(frozen=True)
class LoginRequest:
    segments: tuple[str, ...]
    headers: dict[str, str] = field(repr=False)
    body: bytes = field(repr=False)


_LOGIN_SEGMENTS = ("mgmt", "system", "user", "login")


def _login_body(credentials: ResolvedCredentials) -> bytes:
    return json.dumps({
        "username": credentials.username, "password": credentials.password,
    }, ensure_ascii=True, separators=(",", ":")).encode("ascii")


class AuthenticationStrategy(Protocol):
    product: ProductName
    retain_credentials: bool

    def login_request(self, credentials: ResolvedCredentials) -> LoginRequest: ...
    def request_headers(self, credentials: ResolvedCredentials | None) -> dict[str, str]: ...
    def interpret(self, response: HttpResponse) -> AuthenticationOutcome: ...


class VisionAuthenticationStrategy:
    """LDAP source profile B; scheduler paths remain unresolved and unused."""

    product: ProductName = "vision"
    retain_credentials = False

    def login_request(self, credentials: ResolvedCredentials) -> LoginRequest:
        return LoginRequest(
            _LOGIN_SEGMENTS,
            {"Accept": "application/json", "Content-Type": "application/json",
             "X-Requested-With": "XMLHttpRequest"},
            _login_body(credentials),
        )

    def request_headers(self, credentials: ResolvedCredentials | None) -> dict[str, str]:
        return {"Accept": "application/json", "X-Requested-With": "XMLHttpRequest"}

    def interpret(self, response: HttpResponse) -> AuthenticationOutcome:
        data = None
        try:
            data = load_json(response.body.decode("utf-8"))
        except (UnicodeError, ValueError, RecursionError):
            pass
        if not isinstance(data, dict) or not isinstance(data.get("status"), str):
            return AuthenticationOutcome(False, failure=AuthenticationFailure(
                AuthenticationFailureCategory.MALFORMED_RESPONSE, status=response.status,
            ))
        if data["status"] != "ok":
            return AuthenticationOutcome(False, failure=AuthenticationFailure(
                AuthenticationFailureCategory.APPLICATION_REJECTION, status=response.status,
            ))
        return AuthenticationOutcome(True, LoginEvidence.APPLICATION_STATUS_OK)


class CyberControllerAuthenticationStrategy:
    """Object source profile A; HTTP 200 alone is weak, unverified evidence."""

    product: ProductName = "cyber-controller"
    retain_credentials = True

    def request_headers(self, credentials: ResolvedCredentials | None) -> dict[str, str]:
        if credentials is None or ":" in credentials.username:
            raise AuthenticationError(AuthenticationFailure(AuthenticationFailureCategory.INVALID_CREDENTIALS))
        encoded = None
        try:
            encoded = f"{credentials.username}:{credentials.password}".encode("latin-1")
        except UnicodeError:
            pass
        if encoded is None:
            raise AuthenticationError(AuthenticationFailure(AuthenticationFailureCategory.INVALID_CREDENTIALS))
        return {"Authorization": "Basic " + base64.b64encode(encoded).decode("ascii")}

    def login_request(self, credentials: ResolvedCredentials) -> LoginRequest:
        return LoginRequest(
            _LOGIN_SEGMENTS,
            {**self.request_headers(credentials), "Accept": "application/json",
             "Content-Type": "application/json"},
            _login_body(credentials),
        )

    def interpret(self, response: HttpResponse) -> AuthenticationOutcome:
        if response.status != 200:
            return AuthenticationOutcome(False, failure=AuthenticationFailure(
                AuthenticationFailureCategory.MALFORMED_RESPONSE, status=response.status,
            ))
        return AuthenticationOutcome(True, LoginEvidence.HTTP_200_ONLY)
