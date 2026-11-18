"""Offline adapters for source-observed Cyber Controller export representations."""

from dataclasses import dataclass, field, replace

from ._contract_validation import ContractReader
from .artifacts import ArtifactValidationInformation, ConfigurationArtifact, parse_artifact
from .capabilities import CapabilityDeclaration, ReadCapability, require_capability
from .contracts import ContractValidationError, JsonValue, ValidationIssue, ValidationResult
from .controller_objects import (
    ControllerDevice, ControllerInventory, ControllerObjectKind, DeviceAccessLocation,
    SourceObjectReference, TreeName, assess_controller_identity, normalize_tree,
    parse_controller_artifact,
)
from .product_clients import ReadResult


@dataclass(frozen=True)
class ControllerExportResult:
    artifact: ConfigurationArtifact = field(repr=False)
    validation: ValidationResult
    identity_assessment: ValidationResult
    evidence: str = "source-observed; synthetic-mock-tested; live-unverified"
    completeness: str = "unverified"

    def to_inventory(self) -> ControllerInventory:
        """Incomplete artifacts fail the existing controller planning input contract."""
        return parse_controller_artifact(self.artifact.to_dict())


def _response(
    payload: object, *, version: str, exported_at: str,
) -> dict[str, JsonValue]:
    reader = ContractReader("controller-export")
    if version != "0.0-test":
        reader.fail("unsupported_version", "$.version", "Only synthetic offline development is enabled.")
    try:
        artifact = parse_artifact({
            "schema_version": 1, "domain": "controller-objects",
            "source": {"product": "cyber-controller", "version": version},
            "metadata": {"exported_at": exported_at, "exporter": "offline-controller-adapter"},
            "objects": [payload],
            "validation": {"scope": "offline-contract", "status": "not_validated", "issue_codes": []},
        })
    except ContractValidationError as error:
        result = error.result
    else:
        return artifact.objects[0]
    raise ContractValidationError(result)


def _result(inventory: ControllerInventory) -> ControllerExportResult:
    issues: list[ValidationIssue] = []
    for index, item in enumerate(inventory.objects):
        if not isinstance(item, ControllerDevice):
            continue
        access = item.device_access
        if access.location == DeviceAccessLocation.ABSENT or access.value is None or access.value == {}:
            issues.append(ValidationIssue(
                "incomplete_device_access", f"$.objects[{index}].device_access",
                "Device-access data is absent, null, or empty; export completeness is not established.",
            ))
    validation = ValidationResult(
        "controller-export", "invalid" if issues else "valid", len(inventory.objects), tuple(issues),
    )
    artifact = inventory.to_artifact()
    if issues:
        artifact = replace(
            artifact, validation=ArtifactValidationInformation("invalid", ("incomplete_device_access",)),
        )
    return ControllerExportResult(artifact, validation, assess_controller_identity(inventory))


def adapt_tree_response(
    payload: object, *, controller_id: str, tree: TreeName, version: str, exported_at: str,
) -> ControllerExportResult:
    """Adapt one supplied recursive tree; never fetch/enrich omitted access data."""
    data = _response(payload, version=version, exported_at=exported_at)
    return _result(normalize_tree(
        data, controller_id=controller_id, tree=tree, version=version, exported_at=exported_at,
    ))


def adapt_flat_export(
    payload: object, *, root_response: object, controller_id: str,
    tree: TreeName, version: str, exported_at: str,
) -> ControllerExportResult:
    """Require the source root omitted by legacy flat files; never infer it by name."""
    reader = ContractReader("controller-export")
    data = _response(payload, version=version, exported_at=exported_at)
    reader.mapping(data, "$", {"sites", "devices"})
    root = normalize_tree(
        _response(root_response, version=version, exported_at=exported_at),
        controller_id=controller_id, tree=tree, version=version, exported_at=exported_at,
    )
    if len(root.objects) != 1:
        reader.fail("invalid_root_context", "$.root_response", "Supply only the explicit source root with empty children.")
    root_reference = root.objects[0].reference
    rows: list[tuple[ControllerObjectKind, dict[str, object], SourceObjectReference]] = []
    references = {root_reference.object_id: root_reference}
    for key, kind in (("sites", ControllerObjectKind.SITE), ("devices", ControllerObjectKind.DEVICE)):
        values = reader.required(data, key, "$")
        if not isinstance(values, list):
            reader.fail("invalid_type", f"$.{key}", "Expected an array of exported objects.")
        for index, value in enumerate(values):
            path = f"$.{key}[{index}]"
            row = reader.mapping(value, path)
            object_id = reader.text(reader.required(row, "id", path), path + ".id")
            if object_id in references:
                reader.fail("duplicate_identity", path, "Stable object identifiers must be unique within a tree.")
            reference = SourceObjectReference(controller_id, root_reference.tree, kind, object_id)
            references[object_id] = reference
            rows.append((kind, row, reference))
    artifact: dict[str, object] = dict(root.to_artifact().to_dict())
    records: list[object] = list(root.to_artifact().objects)
    for index, (kind, row, reference) in enumerate(rows):
        path = f"$.objects[{index + 1}]"
        parent_id = reader.text(reader.required(row, "parentOrmID", path), path + ".parentOrmID")
        parent = references.get(parent_id)
        if parent is None:
            reader.fail("missing_parent", path, "Parent identifier does not resolve in the supplied source tree.")
        record: dict[str, object] = {
            "reference": reference.to_dict(), "parent": parent.to_dict(),
            "name": reader.required(row, "name", path),
        }
        del row["name"]
        if kind == ControllerObjectKind.DEVICE:
            record.update(
                device_type=reader.required(row, "type", path),
                management_ip=reader.required(row, "managementIp", path),
            )
            del row["type"], row["managementIp"]
            location = DeviceAccessLocation.ABSENT
            access = None
            if "deviceAccess" in row:
                location, access = DeviceAccessLocation.TOP_LEVEL, row.pop("deviceAccess")
            record["device_access"] = {"location": location.value, "value": access}
        record["configuration"] = row
        records.append(record)
    artifact["objects"] = records
    return _result(parse_controller_artifact(artifact))


def adapt_controller_read(
    result: ReadResult, *, controller_id: str, exported_at: str,
) -> ControllerExportResult:
    """Consume an existing mock client's tree result, without granting API permissions."""
    reader = ContractReader("controller-export")
    if not isinstance(result, ReadResult):
        reader.fail("invalid_type", "$", "Expected an explicit controller read result.")
    capability = result.capability
    if not isinstance(capability, CapabilityDeclaration) or not isinstance(result.objects, tuple):
        reader.fail("invalid_read_result", "$", "Expected a typed capability and an explicit object tuple.")
    if capability.product != "cyber-controller" or capability.operation not in (
        ReadCapability.PHYSICAL_TREE, ReadCapability.ORGANIZATION_TREE,
    ):
        reader.fail("unsupported_context", "$", "Only Cyber Controller tree reads can be adapted.")
    expected = require_capability(
        capability.product, capability.version, capability.operation, mock_only=True,
    )
    if capability != expected or len(result.objects) != 1:
        reader.fail("invalid_read_result", "$", "Expected one root and an unchanged mock capability declaration.")
    return adapt_tree_response(
        result.objects[0], controller_id=controller_id,
        tree=TreeName.PHYSICAL if capability.operation == ReadCapability.PHYSICAL_TREE else TreeName.ORGANIZATION,
        version=capability.version, exported_at=exported_at,
    )
