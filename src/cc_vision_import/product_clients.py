"""Separate read-only product interfaces over caller-owned managed sessions."""

from dataclasses import dataclass, field
from typing import ClassVar

from ._contract_validation import ContractReader
from ._json import load_json
from .artifacts import ConfigurationArtifact, parse_artifact
from .authentication import SessionRole
from .capabilities import (
    CapabilityDeclaration, ClientErrorCategory, LookupCapability, ProductClientError,
    ReadCapability, capabilities_for, require_capability,
)
from .contracts import ProductName
from .sessions import SessionManager
from .transport import HttpMethod


@dataclass(frozen=True)
class ReadResult:
    capability: CapabilityDeclaration
    objects: tuple[dict[str, object], ...] = field(repr=False)

    def to_artifact(self, *, exported_at: str) -> ConfigurationArtifact:
        """Preserve opaque objects; do not infer portable identities or semantics."""
        return parse_artifact({
            "schema_version": 1,
            "domain": self.capability.operation.value,
            "source": {
                "product": self.capability.product, "version": self.capability.version,
            },
            "metadata": {
                "exported_at": exported_at, "exporter": "synthetic-mock-client",
            },
            "objects": list(self.objects),
            "validation": {
                "scope": "offline-contract", "status": "valid", "issue_codes": [],
            },
        })


def _object(value: object) -> dict[str, object]:
    if not isinstance(value, dict) or any(not isinstance(key, str) for key in value):
        raise ProductClientError(ClientErrorCategory.MALFORMED_RESPONSE)
    return dict(value)


def _tree(value: object, depth: int = 0) -> dict[str, object]:
    node = _object(value)
    identifier = _object(node.get("meIdentifier"))
    identity = identifier.get("managedElementID")
    children = node.get("children")
    if (
        depth > 64 or not isinstance(identity, str) or not identity.strip()
        or not isinstance(children, list)
    ):
        raise ProductClientError(ClientErrorCategory.MALFORMED_RESPONSE)
    for child in children:
        _tree(child, depth + 1)
    return node


def read_request_segments(
    capability: CapabilityDeclaration, *, lookup_value: str | None = None,
) -> tuple[str, ...]:
    """Bind a single lookup parameter without authorizing a live request."""
    expected = require_capability(
        capability.product, capability.version, capability.operation, mock_only=True,
    )
    if capability != expected:
        raise ProductClientError(ClientErrorCategory.UNSUPPORTED_CAPABILITY)
    reader = ContractReader("controller-read")
    if isinstance(capability.operation, LookupCapability):
        value = reader.text(lookup_value, "$.lookup_value")
        return (*capability.segments[:-1], value)
    if lookup_value is not None:
        reader.fail("unexpected_lookup_value", "$", "Tree/list reads do not accept a lookup parameter.")
    return capability.segments


def adapt_read_response(capability: CapabilityDeclaration, payload: object) -> ReadResult:
    """Share response processing between mock clients and supplied local JSON."""
    expected = require_capability(
        capability.product, capability.version, capability.operation, mock_only=True,
    )
    if capability != expected:
        raise ProductClientError(ClientErrorCategory.UNSUPPORTED_CAPABILITY)
    if capability.operation == ReadCapability.LDAP_PERMISSIONS:
        if not isinstance(payload, list):
            raise ProductClientError(ClientErrorCategory.MALFORMED_RESPONSE)
        objects = tuple(_object(item) for item in payload)
    elif isinstance(capability.operation, LookupCapability):
        row = _object(payload)
        # Minimum local identity evidence, not a complete vendor response schema.
        if any(not isinstance(value, str) or not value.strip() for value in (row.get("ormID"), row.get("name"))):
            raise ProductClientError(ClientErrorCategory.MALFORMED_RESPONSE)
        objects = (row,)
    else:
        objects = (_tree(payload),)
    return ReadResult(capability, objects)


class _ReadClient:
    product: ClassVar[ProductName]

    def __init__(self, manager: SessionManager, role: SessionRole, version: str) -> None:
        capabilities_for(self.product, version, mock_only=True)
        self._manager = manager
        self._role = role
        self._version = version
        self._check_session()

    def _check_session(self) -> None:
        snapshot = self._manager.snapshot(self._role)
        if snapshot.product != self.product or snapshot.version != self._version:
            raise ProductClientError(ClientErrorCategory.SESSION_MISMATCH)
        if not self._manager.uses_mock_backend(self._role):
            raise ProductClientError(ClientErrorCategory.MOCK_BACKEND_REQUIRED)

    def _read(
        self, operation: ReadCapability | LookupCapability, *, lookup_value: str | None = None,
    ) -> ReadResult:
        capability = require_capability(self.product, self._version, operation, mock_only=True)
        self._check_session()
        response = self._manager.request(
            self._role, HttpMethod.GET, read_request_segments(capability, lookup_value=lookup_value), expect_json=True,
        )
        data = load_json(response.body.decode("utf-8"))
        return adapt_read_response(capability, data)


class VisionClient(_ReadClient):
    product: ClassVar[ProductName] = "vision"

    def list_ldap_permissions(self) -> ReadResult:
        return self._read(ReadCapability.LDAP_PERMISSIONS)


class CyberControllerClient(_ReadClient):
    product: ClassVar[ProductName] = "cyber-controller"

    def export_physical_tree(self) -> ReadResult:
        return self._read(ReadCapability.PHYSICAL_TREE)

    def export_organization_tree(self) -> ReadResult:
        return self._read(ReadCapability.ORGANIZATION_TREE)

    def get_site_by_name(self, name: str) -> ReadResult:
        return self._read(LookupCapability.SITE_BY_NAME, lookup_value=name)

    def get_site_by_id(self, site_id: str) -> ReadResult:
        return self._read(LookupCapability.SITE_BY_ID, lookup_value=site_id)

    def get_device_by_ip(self, device_ip: str) -> ReadResult:
        return self._read(LookupCapability.DEVICE_BY_IP, lookup_value=device_ip)
