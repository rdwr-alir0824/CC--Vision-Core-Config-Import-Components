"""Separate read-only product interfaces over caller-owned managed sessions."""

from dataclasses import dataclass, field
from ipaddress import ip_address
from typing import ClassVar

from ._contract_validation import ContractReader
from ._json import load_json
from .artifacts import ConfigurationArtifact, parse_artifact
from .authentication import SessionRole
from .capabilities import (
    CapabilityDeclaration, ClientErrorCategory, LookupCapability, ProductClientError,
    ReadCapability, capabilities_for, require_capability,
)
from .contracts import JsonValue, ProductName
from .controller_objects import is_controller_credential_field
from .schema_qualification import OperationEvidence, SchemaSubset, operation_evidence, qualify_schema
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


@dataclass(frozen=True)
class VisionBackupRead:
    evidence: OperationEvidence
    objects: tuple[dict[str, JsonValue], ...] = field(repr=False)
    redacted_fields: int
    issue_codes: tuple[str, ...]


@dataclass(frozen=True)
class VisionDiscoveryRead(VisionBackupRead):
    device_ips: tuple[str, ...]
    object_count: int


def _discovery_nodes(payload: object, depth: int = 0) -> tuple[list[str], int, set[str]]:
    if not isinstance(payload, list) or depth > 64:
        raise ProductClientError(ClientErrorCategory.MALFORMED_RESPONSE)
    addresses: list[str] = []
    count = 0
    codes: set[str] = set()
    string_fields = (
        "formFactor", "treeType", "deviceVersion", "type", "managementIp",
        "ormId", "name", "parentOrmId", "status",
    )
    for value in payload:
        row = _object(value)
        if not row:
            raise ProductClientError(ClientErrorCategory.MALFORMED_RESPONSE)
        count += 1
        for key in (*string_fields, "supportTemplate", "deleted"):
            if key not in row:
                continue
            item = row[key]
            if item is None:
                codes.add("unverified_nullability")
            elif key in string_fields and not isinstance(item, str) or key not in string_fields and type(item) is not bool:
                raise ProductClientError(ClientErrorCategory.MALFORMED_RESPONSE)
        address = row.get("managementIp")
        if isinstance(address, str) and address:
            try:
                ip_address(address)
            except ValueError:
                codes.add("invalid_discovered_ip")
            else:
                addresses.append(address)
        children = row.get("children", [])
        if children is None:
            codes.add("unverified_nullability")
        else:
            nested, total, issues = _discovery_nodes(children, depth + 1)
            addresses.extend(nested)
            count += total
            codes.update(issues)
    return addresses, count, codes


def _redact_credentials(value: object, depth: int = 0) -> tuple[object, int]:
    if depth > 64:
        raise ProductClientError(ClientErrorCategory.MALFORMED_RESPONSE)
    count = 0
    if isinstance(value, dict):
        result: dict[str, object] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise ProductClientError(ClientErrorCategory.MALFORMED_RESPONSE)
            if is_controller_credential_field(key):
                result[key] = None
                count += int(item is not None)
            else:
                result[key], removed = _redact_credentials(item, depth + 1)
                count += removed
        return result, count
    if isinstance(value, list):
        rows: list[object] = []
        for item in value:
            row, removed = _redact_credentials(item, depth + 1)
            rows.append(row)
            count += removed
        return rows, count
    return value, 0


_VISION_BACKUP_RECORDS = {
    LookupCapability.SITE_BY_NAME: "API-04",
    LookupCapability.SITE_BY_ID: "API-05",
    LookupCapability.DEVICE_BY_IP: "API-06",
}


def vision_backup_segments(operation: LookupCapability, value: str) -> tuple[str, ...]:
    evidence = operation_evidence("vision", "5.4.9", "DOC-V549", _VISION_BACKUP_RECORDS[operation])
    assert evidence.path is not None and evidence.classification == "documented"
    return (*evidence.path.strip("/").split("/")[:-1], value)


class VisionBackupClient:
    """Document-bound targeted reads, separate from migration capability activation."""

    def __init__(self, manager: SessionManager) -> None:
        snapshot = manager.snapshot(SessionRole.SOURCE)
        if snapshot.product != "vision" or snapshot.version != "5.4.9":
            raise ProductClientError(ClientErrorCategory.SESSION_MISMATCH)
        self._manager = manager

    def discover(self, *, collected_at: str) -> VisionDiscoveryRead:
        evidence = operation_evidence("vision", "5.4.9", "DOC-V549", "VISION-MANAGED-DEVICES")
        assert evidence.path is not None
        response = self._manager.request(
            SessionRole.SOURCE, HttpMethod.GET, tuple(evidence.path.strip("/").split("/")), expect_json=True,
        )
        if response.status != 200:
            raise ProductClientError(ClientErrorCategory.MALFORMED_RESPONSE)
        try:
            payload = load_json(response.body.decode("utf-8"))
        except (ValueError, UnicodeError, RecursionError):
            raise ProductClientError(ClientErrorCategory.MALFORMED_RESPONSE) from None
        addresses, count, codes = _discovery_nodes(payload)
        redacted, removed = _redact_credentials(payload)
        if removed:
            codes.add("credential_fields_redacted")
        artifact = parse_artifact({
            "schema_version": 1, "domain": "api-schema-evidence",
            "source": {"product": "vision", "version": "5.4.9"},
            "metadata": {"exported_at": collected_at, "exporter": "vision-read-only-backup"},
            "objects": redacted,
            "validation": {"scope": "offline-contract", "status": "valid", "issue_codes": []},
        })
        return VisionDiscoveryRead(
            evidence, artifact.objects, removed, tuple(sorted(codes)),
            tuple(dict.fromkeys(addresses)), count,
        )

    def read(self, operation: LookupCapability, value: str, *, collected_at: str) -> VisionBackupRead:
        segments = vision_backup_segments(operation, value)
        record = _VISION_BACKUP_RECORDS[operation]
        evidence = operation_evidence("vision", "5.4.9", "DOC-V549", record)
        response = self._manager.request(
            SessionRole.SOURCE, HttpMethod.GET, segments, expect_json=True,
        )
        if response.status != 200:
            raise ProductClientError(ClientErrorCategory.MALFORMED_RESPONSE)
        try:
            payload = load_json(response.body.decode("utf-8"))
        except (ValueError, UnicodeError, RecursionError):
            raise ProductClientError(ClientErrorCategory.MALFORMED_RESPONSE) from None
        row = _object(payload)
        if row.get("status") == "error" or any(
            not isinstance(item, str) or not item.strip()
            for item in (row.get("ormID"), row.get("name"))
        ):
            raise ProductClientError(ClientErrorCategory.MALFORMED_RESPONSE)
        if (
            operation == LookupCapability.SITE_BY_NAME and row["name"] != value
            or operation == LookupCapability.SITE_BY_ID and row["ormID"] != value
        ):
            raise ProductClientError(ClientErrorCategory.MALFORMED_RESPONSE)
        redacted, count = _redact_credentials(row)
        subset = SchemaSubset.DEVICE if operation == LookupCapability.DEVICE_BY_IP else SchemaSubset.SITE
        qualified = qualify_schema({
            "schema_version": 1, "domain": "api-schema-evidence",
            "source": {"product": "vision", "version": "5.4.9"},
            "metadata": {"exported_at": collected_at, "exporter": "vision-read-only-backup"},
            "objects": [redacted],
            "validation": {"scope": "offline-contract", "status": "valid", "issue_codes": []},
        }, subset, evidence_reference="DOC-V549")
        codes = {issue.code for issue in qualified.unqualified}
        if count:
            codes.add("credential_fields_redacted")
        if operation == LookupCapability.DEVICE_BY_IP:
            codes.add("device_query_binding_unverified")
        return VisionBackupRead(evidence, qualified.artifact.objects, count, tuple(sorted(codes)))
