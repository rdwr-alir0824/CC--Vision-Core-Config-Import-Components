"""Offline, explicitly associated device enrichment; never a by-IP lookup."""

import json
from copy import deepcopy
from dataclasses import dataclass, field, replace

from ._contract_validation import ContractReader
from .artifacts import ArtifactValidationInformation, ConfigurationArtifact, parse_artifact
from .contracts import ContractValidationError, JsonValue, ValidationIssue, ValidationResult
from .controller_access_policy import (
    DEVICE_ACCESS_POLICY, RECONCILIATION_FIELD, DeviceAccessAcknowledgement,
    device_access_acknowledgement_issues, source_snapshot_digest,
)
from .controller_exports import ControllerExportResult
from .controller_objects import (
    ControllerDevice, ControllerObjectKind, DeviceAccessLocation, SourceObjectReference, TreeName,
    assess_controller_identity, has_uncertain_controller_credentials, parse_controller_artifact,
)


_PROVENANCE = RECONCILIATION_FIELD


@dataclass(frozen=True)
class DeviceReconciliationAssociation:
    source: SourceObjectReference = field(repr=False)
    detail_record: str = field(repr=False)
    access_record: str | None = field(default=None, repr=False)
    acknowledgement: DeviceAccessAcknowledgement | None = field(default=None, repr=False)


def _exact(left: JsonValue, right: JsonValue) -> bool:
    return json.dumps(left, allow_nan=False) == json.dumps(right, allow_nan=False)


def _records(
    payload: object, artifact: ConfigurationArtifact, reader: ContractReader, path: str,
) -> dict[str, dict[str, JsonValue]]:
    if not isinstance(payload, list):
        reader.fail("invalid_type", path, "Expected supplied record envelopes.")
    result: dict[str, dict[str, JsonValue]] = {}
    for index, value in enumerate(payload):
        position = f"{path}[{index}]"
        row = reader.mapping(value, position, {"record_id", "payload"})
        record_id = reader.reference(reader.required(row, "record_id", position), position)
        if record_id in result:
            reader.fail("duplicate_record", position, "Record identifiers must be unique.")
        raw = reader.required(row, "payload", position)
        reader.mapping(raw, position)
        try:
            checked = parse_artifact({
                **artifact.to_dict(), "objects": [raw],
                "validation": {"scope": "offline-contract", "status": "valid", "issue_codes": []},
            })
        except ContractValidationError as error:
            validation = error.result
        else:
            result[record_id] = checked.objects[0]
            continue
        raise ContractValidationError(validation)
    return result


def _detail(
    payload: dict[str, JsonValue], device: ControllerDevice, reader: ContractReader, path: str,
) -> tuple[DeviceAccessLocation, dict[str, JsonValue] | None]:
    expected: dict[str, JsonValue] = {
        "id": device.reference.object_id, "ormID": device.reference.object_id,
        "name": device.name, "type": device.device_type, "managementIp": device.management_ip,
        "parentOrmID": device.parent.object_id,
    }
    for key, value in expected.items():
        if key in payload and not _exact(payload[key], value):
            reader.fail("conflicting_attribute", path, "Detail attributes disagree with the qualified tree object.")
    if "children" in payload and payload["children"] != []:
        reader.fail("unsupported_structure", path, "Device detail cannot introduce child objects.")
    identifier = payload.get("meIdentifier")
    if "meIdentifier" in payload:
        values = reader.mapping(identifier, path)
        if values.get("managedElementID") != device.reference.object_id or (
            "managedElementClass" in values
            and values["managedElementClass"] != "com.radware.insite.model.device.Device"
        ):
            reader.fail("conflicting_identifier", path, "Detail native identity disagrees with the association.")
    setup = payload.get("deviceSetup", {})
    reader.mapping(setup, path)
    if not isinstance(setup, dict):
        reader.fail("invalid_type", path, "Expected device setup configuration.")
    if "deviceAccess" in payload and "deviceAccess" in setup:
        reader.fail("conflicting_access", path, "Multiple detail access locations are not supported.")
    for key, value in payload.items():
        if key in device.configuration:
            retained = device.configuration[key]
            if key == "deviceSetup" and isinstance(value, dict):
                value = {name: item for name, item in value.items() if name != "deviceAccess"}
            if not _exact(retained, value):
                reader.fail("conflicting_configuration", path, "Overlapping configuration differs in value, type, or order.")
    location = DeviceAccessLocation.ABSENT
    access: JsonValue = None
    if "deviceAccess" in payload:
        location, access = DeviceAccessLocation.TOP_LEVEL, payload["deviceAccess"]
    elif "deviceAccess" in setup:
        location, access = DeviceAccessLocation.DEVICE_SETUP, setup["deviceAccess"]
    if access is not None and not isinstance(access, dict):
        reader.fail("invalid_device_access", path, "Expected null or a device-access object.")
    return location, access


def reconcile_controller_devices(
    artifact: ConfigurationArtifact, details: object, accesses: object,
    associations: tuple[DeviceReconciliationAssociation, ...],
) -> ControllerExportResult:
    """Reconcile supplied synthetic records; evidence authorizes offline planning only."""
    reader = ContractReader("controller-reconciliation")
    if not isinstance(artifact, ConfigurationArtifact):
        reader.fail("invalid_type", "$", "Expected a controller configuration artifact.")
    artifact = parse_artifact(artifact.to_dict())
    if artifact.source.version != "0.0-test":
        reader.fail("unsupported_version", "$.source", "Only synthetic offline development is enabled.")
    if artifact.validation.status == "invalid" and set(artifact.validation.issue_codes) != {"incomplete_device_access"}:
        reader.fail("invalid_artifact", "$.validation", "Only C1's incomplete-access status can be reconciled.")
    # Revalidate structure independently; clearing this one C1 issue grants no planning eligibility.
    structural = replace(artifact, validation=ArtifactValidationInformation("valid"))
    inventory = parse_controller_artifact(structural.to_dict())
    source_digest = source_snapshot_digest(inventory)
    detail_records = _records(details, artifact, reader, "$.details")
    access_records = _records(accesses, artifact, reader, "$.accesses")
    devices = {
        item.reference: item for item in inventory.objects if isinstance(item, ControllerDevice)
    }
    if not isinstance(associations, tuple):
        reader.fail("invalid_association", "$.associations", "Expected explicit qualified associations.")
    by_source: dict[SourceObjectReference, DeviceReconciliationAssociation] = {}
    used_details: set[str] = set()
    used_accesses: set[str] = set()
    for index, association in enumerate(associations):
        path = f"$.associations[{index}]"
        if not isinstance(association, DeviceReconciliationAssociation) or not isinstance(
            association.source, SourceObjectReference,
        ):
            reader.fail("invalid_association", path, "Expected an explicit qualified device association.")
        if (
            not isinstance(association.source.tree, TreeName)
            or not isinstance(association.source.kind, ControllerObjectKind)
            or association.source.kind != ControllerObjectKind.DEVICE
        ):
            reader.fail("invalid_association", path, "Expected a qualified device in an explicit tree.")
        reader.text(association.source.controller_id, path)
        reader.text(association.source.object_id, path)
        if association.source not in devices:
            reader.fail("context_mismatch", path, "Association must identify a device in the supplied controller and tree.")
        reader.reference(association.detail_record, path)
        if association.source in by_source or association.detail_record in used_details:
            reader.fail("duplicate_association", path, "Devices and detail records require one-to-one associations.")
        if association.detail_record not in detail_records:
            reader.fail("missing_detail_record", path, "Associated detail record is unavailable.")
        if association.access_record is not None:
            reader.reference(association.access_record, path)
            if association.access_record not in access_records:
                reader.fail("missing_access_record", path, "Associated access record is unavailable.")
            if association.access_record in used_accesses:
                reader.fail("duplicate_association", path, "Access records cannot be shared across device identities.")
            used_accesses.add(association.access_record)
        if association.acknowledgement is not None and not isinstance(
            association.acknowledgement, DeviceAccessAcknowledgement,
        ):
            reader.fail("invalid_acknowledgement", path, "Expected an explicit bound acknowledgement.")
        by_source[association.source] = association
        used_details.add(association.detail_record)
    if used_details != detail_records.keys() or used_accesses != access_records.keys():
        if any(
            "managementIp" in payload and sum(
                _exact(payload["managementIp"], item.management_ip) for item in devices.values()
            ) > 1
            for record_id, payload in detail_records.items() if record_id not in used_details
        ):
            reader.fail("ambiguous_ip_reference", "$", "An unmatched IP reference has multiple qualified devices; explicit associations are required.")
        reader.fail("unmatched_record", "$", "Every supplied detail and access record requires an explicit association.")

    data = structural.to_dict()
    rows = list(structural.objects)
    issues: list[ValidationIssue] = []
    for index, item in enumerate(inventory.objects):
        if not isinstance(item, ControllerDevice):
            continue
        path = f"$.objects[{index}]"
        row = deepcopy(rows[index])
        configuration = deepcopy(item.configuration)
        if _PROVENANCE in configuration:
            reader.fail("reserved_configuration", path, "Already reconciled or reserved provenance requires explicit review.")
        association = by_source.get(item.reference)
        if association is None:
            issues.append(ValidationIssue(
                "missing_device_details", path, "An explicit device-detail association is required.",
            ))
            continue
        detail = detail_records[association.detail_record]
        location, access = _detail(detail, item, reader, path)
        separate = None if association.access_record is None else access_records[association.access_record]
        if separate is not None:
            if location != DeviceAccessLocation.ABSENT and not _exact(access, separate):
                reader.fail("conflicting_access", path, "Detail and separately supplied access disagree.")
            if location == DeviceAccessLocation.ABSENT:
                location, access = DeviceAccessLocation.TOP_LEVEL, separate
        retained = item.device_access
        if retained.location != DeviceAccessLocation.ABSENT:
            if location != DeviceAccessLocation.ABSENT and not _exact(retained.value, access):
                reader.fail("conflicting_access", path, "Tree and supplied access disagree; no value is overwritten.")
            location, access = retained.location, retained.value
        configuration[_PROVENANCE] = {
            "schema_version": 2, "detail_record": association.detail_record, "detail": detail,
            "access_record": association.access_record,
            "tree_access": {"location": retained.location.value, "value": retained.value},
            "separate_access": separate,
            "source_artifact_sha256": source_digest,
            "policy_version": DEVICE_ACCESS_POLICY,
            "acknowledgement": None if association.acknowledgement is None else association.acknowledgement.to_dict(),
            "scope": "offline-planning-only", "completeness": "unverified",
        }
        row["configuration"] = configuration
        row["device_access"] = {"location": location.value, "value": access}
        rows[index] = row
        if location == DeviceAccessLocation.ABSENT or access is None or access == {}:
            issues.append(ValidationIssue(
                "incomplete_device_access", path, "Nonempty device-access information is required.",
            ))
        if has_uncertain_controller_credentials(row):
            issues.append(ValidationIssue(
                "unresolved_credentials", path, "Masked, null, or unresolved credential information blocks reconciliation.",
            ))
    data["objects"] = rows
    validated = parse_controller_artifact(data)
    result_artifact = validated.to_artifact()
    if issues:
        result_artifact = replace(result_artifact, validation=ArtifactValidationInformation(
            "invalid", tuple(sorted({issue.code for issue in issues})),
        ))
    acknowledgement_issues = device_access_acknowledgement_issues(validated)
    reported = {(issue.path, issue.code) for issue in issues}
    for index, item in enumerate(validated.objects):
        for code in acknowledgement_issues.get(item.reference, ()):
            if (f"$.objects[{index}]", code) in reported:
                continue
            issues.append(ValidationIssue(
                code, f"$.objects[{index}]",
                "A current identity-, source-, access-, and policy-bound offline acknowledgement is required.",
            ))
    return ControllerExportResult(
        result_artifact,
        ValidationResult("controller-reconciliation", "invalid" if issues else "valid", len(rows), tuple(issues)),
        assess_controller_identity(validated),
    )
