"""Production lookup fails closed; synthetic declarations require explicit opt-in."""

from dataclasses import dataclass
from enum import StrEnum

from .contracts import ProductName


class ReadCapability(StrEnum):
    PHYSICAL_TREE = "physical-tree"
    ORGANIZATION_TREE = "organization-tree"
    LDAP_PERMISSIONS = "ldap-permissions"


class LookupCapability(StrEnum):
    SITE_BY_NAME = "site-by-name"
    SITE_BY_ID = "site-by-id"
    DEVICE_BY_IP = "device-by-ip"


class ClientErrorCategory(StrEnum):
    UNSUPPORTED_CAPABILITY = "unsupported_capability"
    MOCK_BACKEND_REQUIRED = "mock_backend_required"
    SESSION_MISMATCH = "session_declaration_mismatch"
    MALFORMED_RESPONSE = "malformed_api_response"


class ProductClientError(Exception):
    def __init__(self, category: ClientErrorCategory) -> None:
        super().__init__(f"Product client failed: {category.value}.")
        self.category = category


@dataclass(frozen=True)
class CapabilityDeclaration:
    product: ProductName
    version: str
    operation: ReadCapability | LookupCapability
    segments: tuple[str, ...]
    source_record: str
    evidence: str = "source-observed"
    qualification: str = "unverified"
    response_schema: str = "unverified"
    officially_documented: bool = False
    live_tested: bool = False
    compatibility_verified: bool = False


VERIFIED_CAPABILITIES: tuple[CapabilityDeclaration, ...] = ()


def capabilities_for(
    product: str, version: str, *, mock_only: bool = False,
) -> tuple[CapabilityDeclaration, ...]:
    if type(mock_only) is not bool or not mock_only and version == "0.0-test":
        raise ProductClientError(ClientErrorCategory.UNSUPPORTED_CAPABILITY)
    catalogue = VERIFIED_CAPABILITIES
    if mock_only:
        from .mock_capabilities import MOCK_CAPABILITIES

        catalogue = MOCK_CAPABILITIES
    declarations = tuple(
        item for item in catalogue
        if item.product == product and item.version == version
    )
    if not declarations:
        raise ProductClientError(ClientErrorCategory.UNSUPPORTED_CAPABILITY)
    return declarations


def require_capability(
    product: str, version: str, operation: ReadCapability | LookupCapability, *, mock_only: bool = False,
) -> CapabilityDeclaration:
    if isinstance(operation, (ReadCapability, LookupCapability)):
        for item in capabilities_for(product, version, mock_only=mock_only):
            if item.operation == operation:
                return item
    raise ProductClientError(ClientErrorCategory.UNSUPPORTED_CAPABILITY)
