"""Small session-owning API client, independent of experimental migration."""

import os
import ssl
import warnings
from dataclasses import dataclass
from typing import Self
from urllib.parse import urlsplit

from .authentication import (
    AuthenticationError, AuthenticationStrategy, CyberControllerAuthenticationStrategy,
    DocumentedVisionAuthenticationStrategy, ResolvedCredentials,
    VisionAuthenticationStrategy,
)
from .config import ControllerConfig
from .contracts import ContractValidationError, JsonValue
from .files import parse_json, serialize_json
from .http_backend import ConnectionFactory, DestinationAuthorization, StdlibHttpBackend
from .tls_policy import (
    TLSPolicy,
    TLSPolicyError,
    exceptions_allowed,
    warning,
)
from .transport import (
    BackendFailure, HttpMethod, HttpResponse, HttpTransport, TransportConfig,
    TransportError, _unverified_tls_context, build_url,
)


class ClientError(Exception):
    def __init__(
        self, code: str, *, status: int | None = None, indeterminate: bool = False,
    ) -> None:
        super().__init__(f"API/session failure: {code}.")
        self.code = code
        self.status = status
        self.indeterminate = indeterminate


@dataclass(frozen=True, kw_only=True)
class _SessionTransportConfig(TransportConfig):
    policy: TLSPolicy

    def _validate_tls(self) -> None:
        TLSPolicy.from_dict({
            "verify": self.policy.verify,
            "lab_authorized": self.policy.lab_authorized,
            "authorized_origin": self.policy.authorized_origin,
        }, self.base_url)
        if self.verify_tls != self.policy.verify:
            raise TLSPolicyError("Session TLS settings disagree.")

    def tls_context(self) -> ssl.SSLContext:
        return super().tls_context() if self.verify_tls else _unverified_tls_context()


_LOGIN = ("mgmt", "system", "user", "login")


class ApiClient:
    def __init__(
        self, config: ControllerConfig, *,
        operations: tuple[tuple[HttpMethod, tuple[str, ...]], ...] = (),
        tls_exception_authorized: bool = False,
        connection_factory: ConnectionFactory | None = None,
        allow_live: bool = False,
    ) -> None:
        if not isinstance(config, ControllerConfig) or type(tls_exception_authorized) is not bool:
            raise ClientError("invalid_configuration")
        self._origin = config.origin
        try:
            allow_exceptions = exceptions_allowed(
                os.environ.get(
                    "CCV_ALLOW_INSECURE_TLS_EXCEPTION", "true"
                )
            )

            if not config.verify_tls and not allow_exceptions:
                raise TLSPolicyError(
                    "This deployment prohibits insecure TLS exceptions."
                )

            policy = TLSPolicy.from_dict({
                "verify": config.verify_tls,
                "lab_authorized": tls_exception_authorized,
                "authorized_origin": self._origin if tls_exception_authorized else None,
            }, self._origin)
            transport_config = _SessionTransportConfig(
                base_url=self._origin, connect_timeout=config.connect_timeout,
                read_timeout=config.read_timeout, operation_timeout=config.operation_timeout,
                trusted_ca=config.trusted_ca,
                verify_tls=config.verify_tls, policy=policy, read_retries=0,
            )
            scope = tuple(dict.fromkeys((
                (HttpMethod.POST, urlsplit(build_url(self._origin, _LOGIN)).path),
                *((method, urlsplit(build_url(self._origin, segments)).path)
                  for method, segments in operations),
            )))
            authorization = DestinationAuthorization(self._origin, scope)
            message = warning(policy.verify)
            if message is not None:
                warnings.warn(message, RuntimeWarning, stacklevel=2)
            self._backend = StdlibHttpBackend(
                authorization=authorization, max_response_bytes=16 * 1024 * 1024,
                connection_factory=connection_factory, allow_live=allow_live,
                session_tls_policy=policy if not policy.verify else None,
            )
        except (ValueError, TypeError, ContractValidationError):
            raise ClientError("invalid_configuration_or_tls_authorization") from None
        self._transport = HttpTransport(transport_config, self._backend)
        self._credentials: ResolvedCredentials | None = ResolvedCredentials(
            config.username, config.password,
        )
        self._strategy: AuthenticationStrategy = (
            VisionAuthenticationStrategy() if config.product == "vision"
            else CyberControllerAuthenticationStrategy()
        )
        self._documented_session = DocumentedVisionAuthenticationStrategy()
        self._has_documented_session = False
        self._authenticated = False
        self._closed = False

    def __enter__(self) -> Self:
        self.login()
        return self

    def __exit__(self, _type: object, error: BaseException | None, _tb: object) -> None:
        try:
            self.close()
        except ClientError:
            if error is None:
                raise
            error.add_note("Local API session cleanup failed.")

    def _send(
        self, method: HttpMethod, segments: tuple[str, ...], *,
        headers: dict[str, str], body: bytes | None = None, expect_json: bool = True,
    ) -> HttpResponse:
        try:
            return self._transport.request(
                method, segments, headers=headers, body=body, expect_json=expect_json,
            )
        except TransportError as error:
            raise ClientError(
                error.category.value, status=error.status,
                indeterminate=error.category.value == "indeterminate_write_outcome",
            ) from None
        except ContractValidationError:
            raise ClientError("invalid_request") from None

    def login(self) -> None:
        if self._closed or self._authenticated or self._credentials is None:
            raise ClientError("invalid_session_state")
        try:
            try:
                login = self._strategy.login_request(self._credentials)
            except AuthenticationError:
                raise ClientError("invalid_credentials") from None
            response = self._send(
                HttpMethod.POST, login.segments, headers=login.headers, body=login.body,
            )
            data = self._decode(response)
            if (
                response.status != 200 or not isinstance(data, dict)
                or data.get("status") != "ok"
                or not self._strategy.interpret(response).authenticated
            ):
                raise ClientError("authentication_rejected", status=response.status)
            if "jsessionid" in data:
                if not self._documented_session.interpret(response).authenticated:
                    raise ClientError("invalid_login_session", status=response.status)
                self._has_documented_session = True
            self._authenticated = True
            if not self._strategy.retain_credentials:
                self._credentials = None
        except (ClientError, KeyboardInterrupt, EOFError) as error:
            try:
                self.close()
            except ClientError:
                error.add_note("Local API session cleanup failed.")
            raise

    @staticmethod
    def _decode(response: HttpResponse, *, write: bool = False) -> JsonValue:
        try:
            return parse_json(response.body.decode("utf-8"))
        except (UnicodeError, ValueError):
            raise ClientError(
                "malformed_json_response", status=response.status, indeterminate=write,
            ) from None

    def request(
        self, method: HttpMethod, segments: tuple[str, ...], *,
        data: JsonValue = None, expect_json: bool = True,
    ) -> JsonValue:
        if self._closed or not self._authenticated:
            raise ClientError("not_authenticated")
        if not isinstance(method, HttpMethod) or method not in (HttpMethod.GET, HttpMethod.POST, HttpMethod.PUT):
            raise ClientError("unsupported_method")
        if method == HttpMethod.GET and data is not None:
            raise ClientError("get_body_not_supported")
        try:
            headers = self._strategy.request_headers(self._credentials)
            if self._has_documented_session:
                headers.update(self._documented_session.request_headers(None))
            body = None if method == HttpMethod.GET or data is None else serialize_json(data).encode("utf-8")
        except (AuthenticationError, ValueError):
            raise ClientError("invalid_request_data") from None
        headers.update({"Accept": "application/json", "Content-Type": "application/json"})
        try:
            response = self._send(
                method, segments, headers=headers, body=body, expect_json=expect_json,
            )
        except ClientError as error:
            if error.status in (401, 403):
                try:
                    self.close()
                except ClientError:
                    error.add_note("Local API session cleanup failed.")
            raise
        if not expect_json:
            return None
        result = self._decode(response, write=method != HttpMethod.GET)
        if isinstance(result, dict) and result.get("status") == "error":
            raise ClientError("application_rejected", status=response.status)
        return result

    def get(self, segments: tuple[str, ...]) -> JsonValue:
        return self.request(HttpMethod.GET, segments)

    def authorize_gets(self, paths: tuple[tuple[str, ...], ...]) -> None:
        if self._closed or not self._authenticated:
            raise ClientError("not_authenticated")
        try:
            targets = tuple(urlsplit(build_url(self._origin, path)).path for path in paths)
            self._backend.authorize_get_targets(targets)
        except (ValueError, ContractValidationError, BackendFailure):
            raise ClientError("invalid_read_authorization") from None

    def post(
        self, segments: tuple[str, ...], data: JsonValue = None, *, expect_json: bool = True,
    ) -> JsonValue:
        return self.request(HttpMethod.POST, segments, data=data, expect_json=expect_json)

    def put(
        self, segments: tuple[str, ...], data: JsonValue, *, expect_json: bool = True,
    ) -> JsonValue:
        return self.request(HttpMethod.PUT, segments, data=data, expect_json=expect_json)

    def close(self) -> None:
        self._authenticated = False
        self._credentials = None
        self._has_documented_session = False
        self._documented_session.clear()
        if not self._closed:
            try:
                self._backend.close()
            except BackendFailure:
                raise ClientError("local_cleanup_failed") from None
            self._closed = True
