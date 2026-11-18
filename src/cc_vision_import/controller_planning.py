"""Offline planning validation, separate from strict existing-target resolution."""

from dataclasses import dataclass, field

from ._contract_validation import ContractReader
from .contracts import ContractValidationError, ValidationIssue, ValidationResult
from .controller_objects import ControllerInventory, ControllerRoot, TreeName, parse_controller_artifact
from .mappings import IdentityMapping, MappingState, dependency_order, parse_mapping


@dataclass(frozen=True)
class ControllerPlanningEntry:
    source_index: int
    destination_index: int | None
    mapping: IdentityMapping | None = field(repr=False)
    parent_index: int | None
    depends_on: tuple[int, ...]
    issue_codes: tuple[str, ...]


@dataclass(frozen=True)
class ControllerPlanningValidation:
    source: ControllerInventory = field(repr=False)
    destination: ControllerInventory = field(repr=False)
    entries: tuple[ControllerPlanningEntry, ...] = field(repr=False)
    complete_trees: tuple[TreeName, ...]
    order: tuple[int, ...]
    validation: ValidationResult


def _mapping(payload: object) -> IdentityMapping:
    try:
        return parse_mapping(payload)
    except ContractValidationError as error:
        result = error.result
    raise ContractValidationError(ValidationResult("controller-planning", "invalid", issues=result.issues))


def validate_controller_planning(
    source: ControllerInventory, destination: ControllerInventory, mappings: object, *,
    complete_trees: tuple[TreeName, ...] = (),
) -> ControllerPlanningValidation:
    reader = ContractReader("controller-planning")
    if not isinstance(source, ControllerInventory) or not isinstance(destination, ControllerInventory):
        reader.fail("invalid_type", "$", "Validated source and destination inventories are required.")
    source = parse_controller_artifact(source.to_artifact().to_dict())
    destination = parse_controller_artifact(destination.to_artifact().to_dict())
    if source.objects[0].reference.controller_id == destination.objects[0].reference.controller_id:
        reader.fail("context_mismatch", "$", "Source and destination controller identities must differ.")
    if (
        not isinstance(complete_trees, tuple)
        or any(not isinstance(tree, TreeName) for tree in complete_trees)
        or len(set(complete_trees)) != len(complete_trees)
    ):
        reader.fail("invalid_coverage", "$.complete_trees", "Expected distinct explicit tree completeness declarations.")
    destination_roots = {
        item.reference.tree for item in destination.objects if isinstance(item, ControllerRoot)
    }
    if not set(complete_trees) <= destination_roots:
        reader.fail("invalid_coverage", "$.complete_trees", "A declared-complete tree must contain its destination root.")
    if not isinstance(mappings, list):
        reader.fail("invalid_type", "$.mappings", "Expected explicit mapping records.")
    parsed = tuple(_mapping(item) for item in mappings)
    by_index = {item.source_index: item for item in parsed}
    by_id = {item.mapping_id: item for item in parsed}
    if len(by_index) != len(parsed) or len(by_id) != len(parsed):
        reader.fail("duplicate_mapping", "$.mappings", "Source indices and mapping identifiers must be unique.")
    for mapping in parsed:
        if mapping.source_index >= len(source.objects):
            reader.fail("invalid_identity", "$.mappings", "Mapping source index is outside the inventory.")
        if (
            mapping.domain != "controller-objects"
            or mapping.source != source.objects[mapping.source_index].reference.as_identity()
            or mapping.source_context != source.source
            or mapping.destination_context != destination.source
        ):
            reader.fail("context_mismatch", "$.mappings", "Mapping identities and contexts must match the inventories.")

    source_indices = {item.reference: index for index, item in enumerate(source.objects)}
    destination_indices = {
        item.reference.as_identity(): index for index, item in enumerate(destination.objects)
    }
    targets: list[int | None] = [None] * len(source.objects)
    issues: list[list[str]] = [[] for _ in source.objects]
    parents: list[int | None] = []
    dependencies: list[set[int]] = []
    for index, item in enumerate(source.objects):
        parent = None if isinstance(item, ControllerRoot) else source_indices[item.parent]
        parents.append(parent)
        dependencies.append(set() if parent is None else {parent})
        mapping = by_index.get(index)
        if mapping is None:
            issues[index].append("mapping_absent")
        elif mapping.state == MappingState.RESOLVED:
            target_index = None if mapping.destination is None else destination_indices.get(mapping.destination)
            if target_index is None:
                issues[index].append("destination_absent")
            else:
                target = destination.objects[target_index]
                if target.reference.tree != item.reference.tree or target.reference.kind != item.reference.kind:
                    issues[index].append("context_mismatch")
                else:
                    targets[index] = target_index
        elif mapping.state == MappingState.MISSING:
            if item.reference.tree not in complete_trees:
                issues[index].append("incomplete_destination")
        else:
            issues[index].append("mapping_" + mapping.state.value)
        if isinstance(item, ControllerRoot) and (
            mapping is None or mapping.state != MappingState.RESOLVED or targets[index] is None
        ):
            issues[index].append("root_unresolved")

    owners: dict[int, list[int]] = {}
    for index, target in enumerate(targets):
        if target is not None:
            owners.setdefault(target, []).append(index)
    for indices in owners.values():
        if len(indices) > 1:
            for index in indices:
                issues[index].append("destination_collision")

    for index, item in enumerate(source.objects):
        mapping = by_index.get(index)
        if mapping is None:
            continue
        parent = parents[index]
        parent_mapping = None if parent is None else by_index.get(parent)
        expected_parent = None if parent_mapping is None else parent_mapping.mapping_id
        if parent is not None and parent_mapping is None:
            issues[index].append("unresolved_parent")
        if mapping.parent_mapping != expected_parent or (
            expected_parent is not None and expected_parent not in mapping.depends_on
        ):
            issues[index].append("invalid_dependency")
        for key in mapping.depends_on:
            dependency = by_id.get(key)
            if dependency is None:
                issues[index].append("invalid_dependency")
            elif source.objects[dependency.source_index].reference.tree != item.reference.tree:
                issues[index].append("cross_tree_dependency")
            else:
                dependencies[index].add(dependency.source_index)
        target_index = targets[index]
        if parent is not None and target_index is not None:
            parent_target = targets[parent]
            target = destination.objects[target_index]
            if parent_target is None:
                issues[index].append("unresolved_parent")
            elif isinstance(target, ControllerRoot) or target.parent != destination.objects[parent_target].reference:
                issues[index].append("hierarchy_mismatch")

    order = tuple(int(key) for key in dependency_order(
        {str(index): {str(key) for key in values} for index, values in enumerate(dependencies)}, reader,
    ))
    entries = tuple(
        ControllerPlanningEntry(
            index, targets[index], by_index.get(index), parents[index],
            tuple(sorted(dependencies[index])), tuple(sorted(set(issues[index]))),
        )
        for index in range(len(source.objects))
    )
    validation_issues = tuple(
        ValidationIssue(code, f"$.objects[{entry.source_index}]", "Controller planning requires explicit resolution.")
        for entry in entries for code in entry.issue_codes
    )
    return ControllerPlanningValidation(
        source, destination, entries, tuple(sorted(complete_trees)), order,
        ValidationResult(
            "controller-planning", "invalid" if validation_issues else "valid",
            len(source.objects), validation_issues,
        ),
    )
