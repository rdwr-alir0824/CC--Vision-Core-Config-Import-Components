from dataclasses import dataclass
from enum import StrEnum

from ._contract_validation import ContractReader
from .artifacts import ProductDeclaration


class MappingState(StrEnum):
    RESOLVED = "resolved"
    MISSING = "missing"
    UNRESOLVED = "unresolved"
    AMBIGUOUS = "ambiguous"


@dataclass(frozen=True)
class ObjectIdentity:
    namespace: str
    object_type: str
    object_id: str


@dataclass(frozen=True)
class IdentityMapping:
    mapping_id: str
    domain: str
    source_index: int
    source: ObjectIdentity
    source_context: ProductDeclaration
    destination_context: ProductDeclaration
    state: MappingState
    destination: ObjectIdentity | None
    candidates: tuple[ObjectIdentity, ...]
    parent_mapping: str | None
    depends_on: tuple[str, ...]


def product_declaration(value: object, reader: ContractReader, path: str) -> ProductDeclaration:
    data = reader.mapping(value, path, {"product", "version"})
    return ProductDeclaration(
        reader.product(reader.required(data, "product", path), f"{path}.product"),
        reader.version(reader.required(data, "version", path), f"{path}.version"),
    )


def _identity(value: object, reader: ContractReader, path: str) -> ObjectIdentity:
    data = reader.mapping(value, path, {"namespace", "object_type", "object_id"})
    return ObjectIdentity(
        reader.text(reader.required(data, "namespace", path), f"{path}.namespace"),
        reader.identifier(reader.required(data, "object_type", path), f"{path}.object_type"),
        reader.text(reader.required(data, "object_id", path), f"{path}.object_id"),
    )


def parse_mapping(payload: object) -> IdentityMapping:
    reader = ContractReader("plan")
    data = reader.mapping(
        payload, "$.mapping",
        {"mapping_id", "domain", "source_index", "source", "source_context",
         "destination_context", "state", "destination", "candidates", "parent_mapping", "depends_on"},
    )
    index = reader.required(data, "source_index", "$.mapping")
    if type(index) is not int or index < 0:
        reader.fail("invalid_identity", "$.mapping.source_index", "Expected a nonnegative source-object index.")
    raw_state = reader.text(reader.required(data, "state", "$.mapping"), "$.mapping.state")
    try:
        state = MappingState(raw_state)
    except ValueError:
        reader.fail("invalid_mapping", "$.mapping.state", "Unsupported mapping resolution state.")
    destination_value = reader.required(data, "destination", "$.mapping")
    destination = None if destination_value is None else _identity(destination_value, reader, "$.mapping.destination")
    values = reader.required(data, "candidates", "$.mapping")
    if not isinstance(values, list):
        reader.fail("invalid_type", "$.mapping.candidates", "Expected candidate identity objects.")
    candidates = tuple(_identity(item, reader, "$.mapping.candidates") for item in values)
    if len(set(candidates)) != len(candidates):
        reader.fail("duplicate_identity", "$.mapping.candidates", "Candidate identities must be distinct.")
    if (
        (state == MappingState.RESOLVED) != (destination is not None)
        or (state == MappingState.AMBIGUOUS and len(candidates) < 2)
        or (state != MappingState.AMBIGUOUS and candidates)
    ):
        reader.fail("invalid_mapping", "$.mapping", "Resolution state, destination, and candidates are inconsistent.")
    parent = reader.required(data, "parent_mapping", "$.mapping")
    return IdentityMapping(
        reader.identifier(reader.required(data, "mapping_id", "$.mapping"), "$.mapping.mapping_id"),
        reader.identifier(reader.required(data, "domain", "$.mapping"), "$.mapping.domain"),
        index,
        _identity(reader.required(data, "source", "$.mapping"), reader, "$.mapping.source"),
        product_declaration(reader.required(data, "source_context", "$.mapping"), reader, "$.mapping.source_context"),
        product_declaration(reader.required(data, "destination_context", "$.mapping"), reader, "$.mapping.destination_context"),
        state, destination, tuple(sorted(candidates, key=lambda item: (item.namespace, item.object_type, item.object_id))),
        None if parent is None else reader.identifier(parent, "$.mapping.parent_mapping"),
        reader.references(reader.required(data, "depends_on", "$.mapping"), "$.mapping.depends_on"),
    )


def dependency_order(graph: dict[str, set[str]], reader: ContractReader) -> tuple[str, ...]:
    if any(not dependencies <= graph.keys() for dependencies in graph.values()):
        reader.fail("invalid_dependency", "$.dependencies", "Dependency reference is missing.")
    remaining = {key: set(value) for key, value in graph.items()}
    ordered: list[str] = []
    while remaining:
        ready = sorted(key for key, dependencies in remaining.items() if not dependencies)
        if not ready:
            reader.fail("invalid_dependency", "$.dependencies", "Dependencies contain a cycle or self-reference.")
        ordered.extend(ready)
        for key in ready:
            del remaining[key]
        for dependencies in remaining.values():
            dependencies.difference_update(ready)
    return tuple(ordered)
