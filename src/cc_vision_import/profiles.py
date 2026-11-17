from dataclasses import dataclass, field
from typing import ClassVar, Literal, Self

from ._contract_validation import ContractReader
from .contracts import ContractValidationError, ProductName, ValidationResult


@dataclass(frozen=True)
class _ConfigurationProfile:
    name: str
    product: ProductName
    version: str
    base_url: str = field(repr=False)
    secret_ref: str | None = field(default=None, repr=False)
    role: ClassVar[Literal["source", "destination"]]

    @classmethod
    def from_dict(cls, payload: object) -> Self:
        reader = ContractReader(f"{cls.role}-profile")
        data = reader.mapping(
            payload, "$", {"role", "name", "product", "version", "base_url", "secret_ref"}
        )
        if reader.required(data, "role", "$") != cls.role:
            reader.fail("role_mismatch", "$.role", "Profile role does not match the selected contract.")
        name = reader.identifier(reader.required(data, "name", "$"), "$.name")
        product = reader.product(reader.required(data, "product", "$"), "$.product")
        version = reader.version(reader.required(data, "version", "$"), "$.version")
        base_url = reader.base_url(reader.required(data, "base_url", "$"), "$.base_url")
        secret_ref = reader.reference(data["secret_ref"], "$.secret_ref") if "secret_ref" in data else None
        return cls(name, product, version, base_url, secret_ref)


class SourceProfile(_ConfigurationProfile):
    role: ClassVar[Literal["source", "destination"]] = "source"


class DestinationProfile(_ConfigurationProfile):
    role: ClassVar[Literal["source", "destination"]] = "destination"


def _validate_profile(
    payload: object, profile_type: type[SourceProfile] | type[DestinationProfile]
) -> ValidationResult:
    try:
        profile_type.from_dict(payload)
    except ContractValidationError as exc:
        return exc.result
    return ValidationResult(f"{profile_type.role}-profile", "valid")


def validate_source_profile(payload: object) -> ValidationResult:
    return _validate_profile(payload, SourceProfile)


def validate_destination_profile(payload: object) -> ValidationResult:
    return _validate_profile(payload, DestinationProfile)
