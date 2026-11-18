"""Resolve explicit mappings against independent offline controller inventories."""

from dataclasses import dataclass, field

from ._contract_validation import ContractReader
from .contracts import ContractValidationError, ValidationResult
from .controller_objects import ControllerInventory, ControllerObject, ControllerRoot, parse_controller_artifact
from .mappings import IdentityMapping, MappingState, ObjectIdentity, dependency_order, parse_mapping


@dataclass(frozen=True)
class ControllerIdentityResolution:
    mappings: tuple[IdentityMapping, ...] = field(repr=False)
    validation: ValidationResult


def _mapping(payload: object) -> IdentityMapping:
    try:
        return parse_mapping(payload)
    except ContractValidationError as error:
        result = error.result
    raise ContractValidationError(ValidationResult("controller-mapping", "invalid", issues=result.issues))


def resolve_controller_mappings(
    source: ControllerInventory, destination: ControllerInventory, payload: object,
) -> ControllerIdentityResolution:
    reader = ContractReader("controller-mapping")
    if not isinstance(source, ControllerInventory) or not isinstance(destination, ControllerInventory):
        reader.fail("invalid_type", "$", "Validated source and destination inventories are required.")
    source = parse_controller_artifact(source.to_artifact().to_dict())
    destination = parse_controller_artifact(destination.to_artifact().to_dict())
    if source.objects[0].reference.controller_id == destination.objects[0].reference.controller_id:
        reader.fail("context_mismatch", "$", "Source and destination require distinct declared controller identities.")
    if not isinstance(payload, list):
        reader.fail("invalid_type", "$.mappings", "Expected explicit mapping records.")
    mappings = tuple(_mapping(item) for item in payload)
    if len(mappings) != len(source.objects):
        reader.fail("missing_mapping", "$.mappings", "Every source root, site, and device needs an explicit mapping.")
    by_index = {item.source_index: item for item in mappings}
    if len(by_index) != len(mappings) or by_index.keys() != set(range(len(source.objects))):
        reader.fail("duplicate_identity", "$.mappings", "Source mapping indices must cover each object exactly once.")
    if len({item.mapping_id for item in mappings}) != len(mappings):
        reader.fail("duplicate_mapping", "$.mappings", "Mapping identifiers must be unique.")
    destination_objects = {item.reference.as_identity(): item for item in destination.objects}
    source_indices = {item.reference: index for index, item in enumerate(source.objects)}
    targets: set[ObjectIdentity] = set()
    resolved: dict[int, ControllerObject] = {}
    for index, item in enumerate(source.objects):
        mapping = by_index[index]
        if (
            mapping.domain != "controller-objects" or mapping.source != item.reference.as_identity()
            or mapping.source_context != source.source or mapping.destination_context != destination.source
        ):
            reader.fail("context_mismatch", "$.mappings", "Mapping identities and contexts must match the supplied inventories.")
        if mapping.state != MappingState.RESOLVED or mapping.destination is None:
            reader.fail("mapping_" + mapping.state.value, "$.mappings", "Destination resolution must be explicit and unambiguous.")
        target = destination_objects.get(mapping.destination)
        if target is None:
            reader.fail("missing_destination", "$.mappings", "Destination identity is absent from the supplied destination inventory.")
        if target.reference.tree != item.reference.tree or target.reference.kind != item.reference.kind:
            reader.fail("context_mismatch", "$.mappings", "Cross-tree or cross-type mapping is not supported.")
        if mapping.destination in targets:
            reader.fail("destination_collision", "$.mappings", "Multiple source objects cannot share one destination identity.")
        targets.add(mapping.destination)
        resolved[index] = target
    graph: dict[str, set[str]] = {}
    for index, item in enumerate(source.objects):
        mapping = by_index[index]
        expected_parent = None
        if not isinstance(item, ControllerRoot):
            parent_index = source_indices[item.parent]
            expected_parent = by_index[parent_index].mapping_id
            target = resolved[index]
            if isinstance(target, ControllerRoot) or target.parent != resolved[parent_index].reference:
                reader.fail("hierarchy_mismatch", "$.mappings", "Destination parent must match the explicitly mapped source parent.")
        if mapping.parent_mapping != expected_parent or (
            expected_parent is not None and expected_parent not in mapping.depends_on
        ):
            reader.fail("invalid_dependency", "$.mappings", "Mappings must explicitly preserve parent dependencies.")
        graph[mapping.mapping_id] = set(mapping.depends_on)
    dependency_order(graph, reader)
    return ControllerIdentityResolution(
        tuple(by_index[index] for index in range(len(source.objects))),
        ValidationResult("controller-mapping", "valid", len(source.objects)),
    )
