"""Offline controller-object contracts; no product compatibility or write authority."""

import json
import re
from dataclasses import asdict, dataclass, field
from enum import StrEnum

from ._contract_validation import ContractReader
from .artifacts import ConfigurationArtifact, ExportMetadata, ProductDeclaration, parse_artifact
from .contracts import ContractValidationError, JsonValue, ValidationIssue, ValidationResult
from .mappings import ObjectIdentity, dependency_order


class TreeName(StrEnum):
    PHYSICAL = "Physical"
    ORGANIZATION = "Organization"


class ControllerObjectKind(StrEnum):
    ROOT = "root"
    SITE = "site"
    DEVICE = "device"


class DeviceAccessLocation(StrEnum):
    ABSENT = "absent"
    TOP_LEVEL = "deviceAccess"
    DEVICE_SETUP = "deviceSetup.deviceAccess"


@dataclass(frozen=True)
class SourceObjectReference:
    controller_id: str = field(repr=False)
    tree: TreeName
    kind: ControllerObjectKind
    object_id: str = field(repr=False)

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "controller_id": self.controller_id, "tree": self.tree.value,
            "kind": self.kind.value, "object_id": self.object_id,
        }

    def as_identity(self) -> ObjectIdentity:
        namespace = json.dumps([self.controller_id, self.tree.value], separators=(",", ":"))
        return ObjectIdentity(namespace, self.kind.value, self.object_id)


@dataclass(frozen=True)
class DeviceAccessConfiguration:
    location: DeviceAccessLocation
    value: dict[str, JsonValue] | None = field(repr=False)


@dataclass(frozen=True)
class ControllerRoot:
    reference: SourceObjectReference
    configuration: dict[str, JsonValue] = field(repr=False)


@dataclass(frozen=True)
class ControllerSite:
    reference: SourceObjectReference
    parent: SourceObjectReference
    name: str = field(repr=False)
    configuration: dict[str, JsonValue] = field(repr=False)


@dataclass(frozen=True)
class ControllerDevice:
    reference: SourceObjectReference
    parent: SourceObjectReference
    name: str = field(repr=False)
    device_type: str = field(repr=False)
    management_ip: str = field(repr=False)
    device_access: DeviceAccessConfiguration
    configuration: dict[str, JsonValue] = field(repr=False)


type ControllerObject = ControllerRoot | ControllerSite | ControllerDevice


def _record(item: ControllerObject) -> dict[str, JsonValue]:
    result: dict[str, JsonValue] = {
        "reference": item.reference.to_dict(), "parent": None,
        "configuration": item.configuration,
    }
    if not isinstance(item, ControllerRoot):
        result.update(parent=item.parent.to_dict(), name=item.name)
    if isinstance(item, ControllerDevice):
        result.update(
            device_type=item.device_type, management_ip=item.management_ip,
            device_access={
                "location": item.device_access.location.value, "value": item.device_access.value,
            },
        )
    return result


@dataclass(frozen=True)
class ControllerInventory:
    source: ProductDeclaration = field(repr=False)
    metadata: ExportMetadata = field(repr=False)
    objects: tuple[ControllerObject, ...] = field(repr=False)

    def to_artifact(self) -> ConfigurationArtifact:
        artifact = _artifact({
            "schema_version": 1, "domain": "controller-objects",
            "source": asdict(self.source), "metadata": asdict(self.metadata),
            "objects": [_record(item) for item in self.objects],
            "validation": {"scope": "offline-contract", "status": "valid", "issue_codes": []},
        })
        parse_controller_artifact(artifact.to_dict())
        return artifact


_SITE_CLASS = "com.radware.insite.model.device.Site"
_DEVICE_CLASS = "com.radware.insite.model.device.Device"
_ABSENT = object()


def _artifact(payload: object) -> ConfigurationArtifact:
    try:
        return parse_artifact(payload)
    except ContractValidationError as error:
        result = error.result
    raise ContractValidationError(ValidationResult("controller-objects", "invalid", issues=result.issues))


def _tree(value: object, reader: ContractReader, path: str) -> TreeName:
    for candidate in TreeName:
        if value == candidate.value:
            return candidate
    reader.fail("unsupported_tree", path, "Only Physical and Organization trees are modeled.")


def _reference(value: object, reader: ContractReader, path: str) -> SourceObjectReference:
    data = reader.mapping(value, path, {"controller_id", "tree", "kind", "object_id"})
    raw_kind = reader.required(data, "kind", path)
    kind = next((item for item in ControllerObjectKind if raw_kind == item.value), None)
    if kind is None:
        reader.fail("unsupported_object_kind", path, "Expected root, site, or device.")
    return SourceObjectReference(
        reader.text(reader.required(data, "controller_id", path), path + ".controller_id"),
        _tree(reader.required(data, "tree", path), reader, path + ".tree"), kind,
        reader.text(reader.required(data, "object_id", path), path + ".object_id"),
    )


def is_controller_credential_field(key: str) -> bool:
    normalized = re.sub(r"[^a-z0-9]", "", key.lower())
    return normalized in ("pwd", "user", "login") or any(
        marker in normalized for marker in (
            "password", "passwd", "secret", "token", "credential", "community",
            "cookie", "authorization", "privatekey", "apikey", "sessionid",
            "username", "securityname", "passphrase", "authkey", "privkey",
        )
    )


def _credential_references(value: JsonValue, reader: ContractReader, path: str) -> None:
    if isinstance(value, list):
        for index, item in enumerate(value):
            _credential_references(item, reader, f"{path}[{index}]")
    elif isinstance(value, dict):
        for index, (key, item) in enumerate(value.items()):
            item_path = f"{path}.fields[{index}]"
            if key != "secret_ref" and is_controller_credential_field(key) and item is not None and not (
                isinstance(item, dict) and item.keys() == {"secret_ref"}
            ):
                reader.fail("secret_value_not_allowed", item_path, "Credential fields require null or a secret reference.")
            _credential_references(item, reader, item_path)


def _native_bindings(item: ControllerObject, reader: ContractReader, path: str) -> None:
    data = item.configuration
    if "children" in data:
        reader.fail("conflicting_reference", path, "Hierarchy must use normalized parent references.")
    if "meIdentifier" in data:
        identifier = reader.mapping(data["meIdentifier"], path)
        if identifier.get("managedElementID") != item.reference.object_id:
            reader.fail("conflicting_reference", path, "Native and normalized object references disagree.")
        if isinstance(item, ControllerRoot) and identifier.get("managedElementClass") in (_SITE_CLASS, _DEVICE_CLASS):
            reader.fail("conflicting_reference", path, "Known site/device classes cannot represent tree roots.")
        expected = (
            _SITE_CLASS if isinstance(item, ControllerSite) else
            _DEVICE_CLASS if isinstance(item, ControllerDevice) else None
        )
        if expected is not None and identifier.get("managedElementClass") != expected:
            reader.fail("conflicting_reference", path, "Native and normalized object types disagree.")
    if "ormID" in data and data["ormID"] != item.reference.object_id:
        reader.fail("conflicting_reference", path, "Unresolved native identifier aliases are not supported.")
    parent = None if isinstance(item, ControllerRoot) else item.parent.object_id
    if "parentOrmID" in data and data["parentOrmID"] != parent:
        reader.fail("conflicting_reference", path, "Native and normalized parent references disagree.")
    reserved = set() if isinstance(item, ControllerRoot) else {"name"}
    if isinstance(item, ControllerDevice):
        reserved |= {"type", "managementIp", "deviceAccess"}
        if "deviceSetup" in data:
            setup = reader.mapping(data["deviceSetup"], path)
            if "deviceAccess" in setup:
                reader.fail("conflicting_reference", path, "Device access must use its normalized field.")
    if reserved & data.keys():
        reader.fail("conflicting_reference", path, "Configuration duplicates normalized fields.")


def _object(
    item: dict[str, JsonValue], reader: ContractReader, path: str,
) -> ControllerObject:
    data = reader.mapping(item, path)
    reference = _reference(reader.required(data, "reference", path), reader, path + ".reference")
    allowed = {"reference", "parent", "configuration"}
    if reference.kind != ControllerObjectKind.ROOT:
        allowed.add("name")
    if reference.kind == ControllerObjectKind.DEVICE:
        allowed |= {"device_type", "management_ip", "device_access"}
    reader.mapping(item, path, allowed)
    reader.required(data, "configuration", path)
    configuration = item["configuration"]
    if not isinstance(configuration, dict):
        reader.fail("invalid_type", path + ".configuration", "Expected a configuration object.")
    parent_value = reader.required(data, "parent", path)
    result: ControllerObject
    if reference.kind == ControllerObjectKind.ROOT:
        if parent_value is not None:
            reader.fail("invalid_hierarchy", path, "A tree root cannot have a parent.")
        result = ControllerRoot(reference, configuration)
    else:
        parent = _reference(parent_value, reader, path + ".parent")
        name = reader.text(reader.required(data, "name", path), path + ".name")
        if reference.kind == ControllerObjectKind.SITE:
            result = ControllerSite(reference, parent, name, configuration)
        else:
            access = reader.mapping(
                reader.required(data, "device_access", path), path + ".device_access",
                {"location", "value"},
            )
            location_value = reader.required(access, "location", path + ".device_access")
            location = next((item for item in DeviceAccessLocation if location_value == item.value), None)
            reader.required(access, "value", path + ".device_access")
            access_record = item["device_access"]
            if not isinstance(access_record, dict):
                reader.fail("invalid_type", path, "Expected a device-access record.")
            value = access_record["value"]
            if (
                location is None or value is not None and not isinstance(value, dict)
                or location == DeviceAccessLocation.ABSENT and value is not None
            ):
                reader.fail("invalid_device_access", path, "Device-access location and value are inconsistent.")
            result = ControllerDevice(
                reference, parent, name,
                reader.text(reader.required(data, "device_type", path), path + ".device_type"),
                reader.text(reader.required(data, "management_ip", path), path + ".management_ip"),
                DeviceAccessConfiguration(location, value), configuration,
            )
    _native_bindings(result, reader, path + ".configuration")
    _credential_references(item, reader, path)
    return result


def _hierarchy(objects: tuple[ControllerObject, ...], reader: ContractReader) -> None:
    if not objects:
        reader.fail("missing_root", "$.objects", "At least one explicit tree root is required.")
    controller = objects[0].reference.controller_id
    by_reference: dict[SourceObjectReference, int] = {}
    by_native_id: dict[tuple[TreeName, str], SourceObjectReference] = {}
    roots: set[TreeName] = set()
    for index, item in enumerate(objects):
        reference = item.reference
        if reference.controller_id != controller:
            reader.fail("context_mismatch", "$.objects", "One inventory must describe one controller.")
        key = (reference.tree, reference.object_id)
        if key in by_native_id:
            code = "duplicate_identity" if reference == by_native_id[key] else "conflicting_reference"
            reader.fail(code, f"$.objects[{index}]", "Object references must be unique within a tree.")
        by_native_id[key] = reference
        by_reference[reference] = index
        if isinstance(item, ControllerRoot):
            if reference.tree in roots:
                reader.fail("duplicate_root", "$.objects", "Each tree requires exactly one root.")
            roots.add(reference.tree)
    if {item.reference.tree for item in objects} != roots:
        reader.fail("missing_root", "$.objects", "Each represented tree requires an explicit root.")
    graph: dict[str, set[str]] = {}
    for index, item in enumerate(objects):
        dependencies: set[str] = set()
        if not isinstance(item, ControllerRoot):
            if item.parent.controller_id != controller or item.parent.tree != item.reference.tree:
                reader.fail("cross_context_parent", f"$.objects[{index}].parent", "Parents must belong to the same controller and tree.")
            if item.parent.kind not in (ControllerObjectKind.ROOT, ControllerObjectKind.SITE):
                reader.fail("invalid_parent", f"$.objects[{index}].parent", "Only roots and sites may contain objects.")
            if item.parent not in by_reference:
                code = "conflicting_reference" if (item.parent.tree, item.parent.object_id) in by_native_id else "missing_parent"
                reader.fail(code, f"$.objects[{index}].parent", "Parent reference is missing or has the wrong type.")
            dependencies.add(str(by_reference[item.parent]))
        graph[str(index)] = dependencies
    dependency_order(graph, reader)


def parse_controller_artifact(payload: object) -> ControllerInventory:
    reader = ContractReader("controller-objects")
    artifact = _artifact(payload)
    if artifact.domain != "controller-objects" or artifact.source.product != "cyber-controller":
        reader.fail("unsupported_context", "$", "Expected a controller-objects artifact for Cyber Controller.")
    if artifact.validation.status == "invalid":
        reader.fail("invalid_artifact", "$.validation", "Previously invalid artifacts cannot be accepted as controller inventories.")
    objects = tuple(_object(item, reader, f"$.objects[{index}]") for index, item in enumerate(artifact.objects))
    _hierarchy(objects, reader)
    return ControllerInventory(artifact.source, artifact.metadata, objects)


def validate_controller_artifact(payload: object) -> ValidationResult:
    try:
        inventory = parse_controller_artifact(payload)
    except ContractValidationError as error:
        return error.result
    return ValidationResult("controller-objects", "valid", len(inventory.objects))


def assess_controller_identity(inventory: ControllerInventory) -> ValidationResult:
    """Flag ambiguous same-type sibling names; a valid result grants no mapping authority."""
    reader = ContractReader("controller-identity")
    if not isinstance(inventory, ControllerInventory):
        reader.fail("invalid_type", "$", "A validated controller inventory is required.")
    inventory = parse_controller_artifact(inventory.to_artifact().to_dict())
    siblings: dict[tuple[SourceObjectReference, ControllerObjectKind, str], list[int]] = {}
    for index, item in enumerate(inventory.objects):
        if not isinstance(item, ControllerRoot):
            siblings.setdefault((item.parent, item.reference.kind, item.name), []).append(index)
    ambiguous = {
        index for indices in siblings.values() if len(indices) > 1 for index in indices
    }
    issues = tuple(
        ValidationIssue(
            "ambiguous_name", f"$.objects[{index}].name",
            "Same-type sibling names are ambiguous; an explicit qualified destination mapping is required.",
        )
        for index in sorted(ambiguous)
    )
    return ValidationResult(
        "controller-identity", "invalid" if issues else "valid", len(inventory.objects), issues,
    )


def normalize_tree(
    payload: object, *, controller_id: str, tree: TreeName, version: str, exported_at: str,
) -> ControllerInventory:
    """Normalize an explicitly supplied synthetic tree, without fetching or writing it."""
    reader = ContractReader("controller-objects")
    controller_id = reader.text(controller_id, "$.controller_id")
    tree = _tree(tree, reader, "$.tree")
    version = reader.version(version, "$.version")
    records: list[dict[str, object]] = []

    def visit(value: object, parent: SourceObjectReference | None, depth: int) -> None:
        if depth > 64:
            reader.fail("invalid_hierarchy", "$.objects", "Tree nesting exceeds the offline normalization limit.")
        data = reader.mapping(value, "$.objects")
        identifier = reader.mapping(reader.required(data, "meIdentifier", "$.objects"), "$.objects")
        object_id = reader.text(reader.required(identifier, "managedElementID", "$.objects"), "$.objects")
        kind = ControllerObjectKind.ROOT
        if parent is not None:
            native_class = identifier.get("managedElementClass")
            if native_class == _SITE_CLASS:
                kind = ControllerObjectKind.SITE
            elif native_class == _DEVICE_CLASS:
                kind = ControllerObjectKind.DEVICE
            else:
                reader.fail("unsupported_object_kind", "$.objects", "Unrecognized managed-element classes cannot be discarded.")
        reference = SourceObjectReference(controller_id, tree, kind, object_id)
        children = data.pop("children", _ABSENT)
        if kind == ControllerObjectKind.DEVICE:
            if children is not _ABSENT and children != []:
                reader.fail("invalid_hierarchy", "$.objects", "Devices cannot contain child objects.")
            children = []
        if not isinstance(children, list):
            reader.fail("invalid_hierarchy", "$.objects", "Roots and sites require explicit child arrays.")
        record: dict[str, object] = {
            "reference": reference.to_dict(), "parent": None if parent is None else parent.to_dict(),
        }
        if parent is not None:
            record["name"] = reader.required(data, "name", "$.objects")
            del data["name"]
        if kind == ControllerObjectKind.DEVICE:
            record["device_type"] = reader.required(data, "type", "$.objects")
            record["management_ip"] = reader.required(data, "managementIp", "$.objects")
            del data["type"], data["managementIp"]
            location = DeviceAccessLocation.ABSENT
            access: object = None
            setup = reader.mapping(data["deviceSetup"], "$.objects") if "deviceSetup" in data else {}
            if "deviceAccess" in data and "deviceAccess" in setup:
                reader.fail("conflicting_reference", "$.objects", "Multiple device-access locations require explicit reconciliation.")
            if "deviceAccess" in data:
                location, access = DeviceAccessLocation.TOP_LEVEL, data.pop("deviceAccess")
            elif "deviceAccess" in setup:
                location, access = DeviceAccessLocation.DEVICE_SETUP, setup.pop("deviceAccess")
                data["deviceSetup"] = setup
            record["device_access"] = {"location": location.value, "value": access}
        record["configuration"] = data
        records.append(record)
        for child in children:
            visit(child, reference, depth + 1)

    visit(payload, None, 0)
    return parse_controller_artifact({
        "schema_version": 1, "domain": "controller-objects",
        "source": {"product": "cyber-controller", "version": version},
        "metadata": {"exported_at": exported_at, "exporter": "controller-object-normalizer"},
        "objects": records,
        "validation": {"scope": "offline-contract", "status": "valid", "issue_codes": []},
    })
