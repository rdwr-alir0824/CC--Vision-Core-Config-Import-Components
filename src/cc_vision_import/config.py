"""Runtime connection settings for the independent legacy-first application."""

from collections.abc import Callable
from dataclasses import dataclass, field
from getpass import getpass
from typing import Literal

from .authentication import AuthenticationError, ResolvedCredentials
from .contracts import ContractValidationError
from .transport import TransportConfig, build_url


class ConfigError(ValueError):
    pass


@dataclass(frozen=True)
class ControllerConfig:
    address: str = field(repr=False)
    username: str = field(repr=False)
    password: str = field(repr=False)
    product: Literal["vision", "cyber-controller"]
    verify_tls: bool = True
    connect_timeout: float = 10
    read_timeout: float = 30
    operation_timeout: float = 60

    def __post_init__(self) -> None:
        try:
            if (
                not isinstance(self.address, str) or not self.address
                or self.product not in ("vision", "cyber-controller")
                or type(self.verify_tls) is not bool
            ):
                raise ValueError
            ResolvedCredentials(self.username, self.password)
            TransportConfig(
                base_url=self.origin, connect_timeout=self.connect_timeout,
                read_timeout=self.read_timeout, operation_timeout=self.operation_timeout,
            )
        except (ValueError, AuthenticationError, ContractValidationError):
            raise ConfigError("Invalid controller settings or credentials.") from None

    @property
    def origin(self) -> str:
        address = self.address if "://" in self.address else "https://" + self.address
        return build_url(address, ("mgmt",)).removesuffix("/mgmt")


def prompt_config(
    product: Literal["vision", "cyber-controller"], *, verify_tls: bool = True,
    input_fn: Callable[[str], str] = input,
    password_fn: Callable[[str], str] = getpass,
) -> ControllerConfig:
    return ControllerConfig(
        address=input_fn("Controller address: ").strip(),
        username=input_fn("Username: "),
        password=password_fn("Password: "),
        product=product, verify_tls=verify_tls,
    )
