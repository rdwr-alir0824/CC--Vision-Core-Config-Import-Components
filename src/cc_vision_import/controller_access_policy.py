"""Identity- and snapshot-bound offline access acknowledgement, not import approval."""

import hashlib
import json
import re
from dataclasses import dataclass, field, replace

from ._contract_validation import ContractReader
from .artifacts import ArtifactValidationInformation, ConfigurationArtifact
from .contracts import ContractValidationError, JsonValue
from .controller_objects import (
    ControllerDevice, ControllerInventory, ControllerObjectKind, DeviceAccessLocation,
    SourceObjectReference, TreeName,
    has_uncertain_controller_credentials, has_uncertain_controller_object_credentials,
    parse_controller_artifact,
)


RECONCILIATION_FIELD = "offlineDeviceReconciliation"
DEVICE_ACCESS_POLICY = "qualified-offline-device-access-v1"


def _digest(value: object) -> str:
    encoded = json.dumps(value, separators=(",", ":"), ensure_ascii=True, allow_nan=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def source_snapshot_digest(inventory: ControllerInventory) -> str:
    """Hash the structurally normalized source snapshot, retaining configuration order."""
    return _digest(inventory.to_artifact().to_dict())


def _evidence(value: object) -> str:
    if not isinstance(value, str) or re.fullmatch(r"evidence-[0-9a-f]{32}", value) is None:
        ContractReader("controller-access-policy").fail(
            "invalid_evidence_reference", "$.acknowledgement",
            "Expected an opaque local evidence catalogue identifier, not configuration or credentials.",
        )
    return value


@dataclass(frozen=True)
class DeviceAccessAcknowledgement:
    device: SourceObjectReference = field(repr=False)
    source_artifact_sha256: str = field(repr=False)
    access_sha256: str = field(repr=False)
    evidence_reference: str = field(repr=False)
    policy_version: str = DEVICE_ACCESS_POLICY

    def to_dict(self) -> dict[str, JsonValue]:
        reader = ContractReader("controller-access-policy")
        reader.checksum(self.source_artifact_sha256, "$.acknowledgement")
        reader.checksum(self.access_sha256, "$.acknowledgement")
        _evidence(self.evidence_reference)
        if not isinstance(self.device, SourceObjectReference) or self.policy_version != DEVICE_ACCESS_POLICY:
            reader.fail("invalid_acknowledgement", "$.acknowledgement", "Unsupported acknowledgement identity or policy.")
        if (
            not isinstance(self.device.tree, TreeName)
            or not isinstance(self.device.kind, ControllerObjectKind)
            or self.device.kind != ControllerObjectKind.DEVICE
        ):
            reader.fail("invalid_acknowledgement", "$.acknowledgement", "Expected an explicit qualified device identity.")
        reader.text(self.device.controller_id, "$.acknowledgement")
        reader.text(self.device.object_id, "$.acknowledgement")
        return {
            "device": self.device.to_dict(),
            "source_artifact_sha256": self.source_artifact_sha256,
            "access_sha256": self.access_sha256, "evidence_reference": self.evidence_reference,
            "policy_version": self.policy_version, "scope": "offline-planning-only",
        }


def _access_digest(device: ControllerDevice, provenance: dict[str, JsonValue] | None) -> str:
    return _digest({
        "device_access": {"location": device.device_access.location.value, "value": device.device_access.value},
        "inputs": {
            key: provenance[key] for key in (
                "detail_record", "detail", "access_record", "separate_access", "tree_access",
            )
        } if provenance is not None else None,
    })


def _provenance(device: ControllerDevice) -> dict[str, JsonValue] | None:
    value = device.configuration.get(RECONCILIATION_FIELD)
    required = {
        "schema_version", "detail_record", "detail", "access_record", "tree_access",
        "separate_access", "source_artifact_sha256", "policy_version", "acknowledgement",
        "scope", "completeness",
    }
    if not isinstance(value, dict) or value.keys() != required:
        return None
    if (
        type(value["schema_version"]) is not int or value["schema_version"] != 2
        or value["policy_version"] != DEVICE_ACCESS_POLICY
        or value["scope"] != "offline-planning-only" or value["completeness"] != "unverified"
    ):
        return None
    return value


def device_access_acknowledgement_issues(
    inventory: ControllerInventory,
    acknowledgements: tuple[DeviceAccessAcknowledgement, ...] = (),
) -> dict[SourceObjectReference, tuple[str, ...]]:
    """Recheck gates at planning time, including post-reconciliation mutation."""
    devices = [
        item for item in inventory.objects
        if isinstance(item, ControllerDevice) and (
            RECONCILIATION_FIELD in item.configuration or item.device_access.location != DeviceAccessLocation.ABSENT
        )
    ]
    if not devices:
        return {}
    restored = inventory.to_artifact().to_dict()
    rows = list(inventory.to_artifact().objects)
    structurally_restorable = True
    for index, item in enumerate(inventory.objects):
        if not isinstance(item, ControllerDevice) or RECONCILIATION_FIELD not in item.configuration:
            continue
        provenance = _provenance(item)
        if provenance is None:
            structurally_restorable = False
            continue
        configuration = rows[index]["configuration"]
        if not isinstance(configuration, dict):
            structurally_restorable = False
            continue
        del configuration[RECONCILIATION_FIELD]
        rows[index]["device_access"] = provenance["tree_access"]
    restored["objects"] = rows
    original_digest = None
    if structurally_restorable:
        try:
            original_digest = source_snapshot_digest(parse_controller_artifact(restored))
        except ContractValidationError:
            structurally_restorable = False
    issues: dict[SourceObjectReference, tuple[str, ...]] = {}
    supplied = {item.device: item.to_dict() for item in acknowledgements}
    current_digest = source_snapshot_digest(inventory)
    for device in devices:
        if RECONCILIATION_FIELD not in device.configuration:
            acknowledgement = supplied.get(device.reference)
            code = None
            if acknowledgement is None:
                code = "unacknowledged_device_access"
            elif (
                acknowledgement["source_artifact_sha256"] != current_digest
                or acknowledgement["access_sha256"] != _access_digest(device, None)
            ):
                code = "stale_device_access_acknowledgement"
            issues[device.reference] = () if code is None else (code,)
            continue
        provenance = _provenance(device)
        code = None
        if provenance is None or not structurally_restorable:
            code = "invalid_device_access_acknowledgement"
        else:
            acknowledgement = provenance["acknowledgement"]
            if acknowledgement is None:
                code = "unacknowledged_device_access"
            elif not isinstance(acknowledgement, dict) or acknowledgement.keys() != {
                "device", "source_artifact_sha256", "access_sha256",
                "evidence_reference", "policy_version", "scope",
            }:
                code = "invalid_device_access_acknowledgement"
            elif (
                acknowledgement["device"] != device.reference.to_dict()
                or acknowledgement["policy_version"] != DEVICE_ACCESS_POLICY
                or acknowledgement["scope"] != "offline-planning-only"
            ):
                code = "mismatched_device_access_acknowledgement"
            else:
                try:
                    _evidence(acknowledgement["evidence_reference"])
                except ContractValidationError:
                    code = "invalid_device_access_acknowledgement"
                if code is None and (
                    provenance["source_artifact_sha256"] != original_digest
                    or acknowledgement["source_artifact_sha256"] != original_digest
                    or acknowledgement["access_sha256"] != _access_digest(device, provenance)
                ):
                    code = "stale_device_access_acknowledgement"
        issues[device.reference] = () if code is None else (code,)
    for device in devices:
        codes = list(issues[device.reference])
        if device.device_access.location != DeviceAccessLocation.ABSENT and (
            device.device_access.value is None or device.device_access.value == {}
        ):
            codes.append("incomplete_device_access")
        if has_uncertain_controller_object_credentials(device):
            codes.append("unresolved_credentials")
        issues[device.reference] = tuple(sorted(set(codes)))
    return issues


def acknowledge_device_access(
    source: ConfigurationArtifact, reconciled: ConfigurationArtifact,
    device: SourceObjectReference, *, evidence_reference: str,
) -> DeviceAccessAcknowledgement:
    """Explicit operator acknowledgement of a reviewed preview; no secrets are resolved."""
    reader = ContractReader("controller-access-policy")
    evidence_reference = _evidence(evidence_reference)
    if not isinstance(source, ConfigurationArtifact) or not isinstance(reconciled, ConfigurationArtifact):
        reader.fail("invalid_type", "$", "Expected source and reconciled controller artifacts.")
    if source.validation.status == "invalid" and set(source.validation.issue_codes) != {"incomplete_device_access"}:
        reader.fail("invalid_artifact", "$", "Unrelated invalid source status cannot be acknowledged.")
    original = parse_controller_artifact(replace(
        source, validation=ArtifactValidationInformation("valid"),
    ).to_dict())
    inventory = parse_controller_artifact(reconciled.to_dict())
    target = next((item for item in inventory.objects if item.reference == device), None)
    if not isinstance(target, ControllerDevice):
        reader.fail("invalid_identity", "$", "Acknowledgement requires a specific qualified device.")
    provenance = _provenance(target)
    original_digest = source_snapshot_digest(original)
    if inventory.source.version != "0.0-test" or (
        provenance is None and (
            RECONCILIATION_FIELD in target.configuration or source_snapshot_digest(inventory) != original_digest
        )
    ) or (provenance is not None and provenance["source_artifact_sha256"] != original_digest):
        reader.fail("mismatched_device_access_acknowledgement", "$", "Preview and source snapshot must agree.")
    row: dict[str, JsonValue] = {
        "configuration": target.configuration, "access": target.device_access.value,
        "name": target.name, "device_type": target.device_type,
    }
    if (
        target.device_access.location == DeviceAccessLocation.ABSENT
        or target.device_access.value is None or target.device_access.value == {}
        or has_uncertain_controller_credentials(row)
    ):
        reader.fail("ineligible_device_access", "$", "Incomplete or uncertain access cannot be acknowledged.")
    return DeviceAccessAcknowledgement(
        target.reference, original_digest,
        _access_digest(target, provenance), evidence_reference,
    )
