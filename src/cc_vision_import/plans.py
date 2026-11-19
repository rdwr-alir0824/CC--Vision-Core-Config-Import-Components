import hashlib
import json
from dataclasses import asdict, dataclass, field
from enum import StrEnum

from ._contract_validation import ContractReader
from ._json import load_json
from .artifacts import ProductDeclaration, parse_artifact
from .contracts import ContractValidationError, ProductName, ValidationIssue, ValidationResult
from .mappings import IdentityMapping, MappingState, dependency_order, parse_mapping, product_declaration


class ActionKind(StrEnum):
    CREATE = "create"
    SKIP = "skip"
    CONFLICT = "conflict"
    BLOCKED = "blocked"


class Comparison(StrEnum):
    MISSING = "missing"
    IDENTICAL = "identical"
    DIFFERENT = "different"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class DestinationDeclaration:
    controller_id: str
    product: ProductName
    version: str
    base_url: str = field(repr=False)


@dataclass(frozen=True)
class SourceArtifactIdentity:
    artifact_id: str
    sha256: str
    schema_version: int
    source: ProductDeclaration
    object_count: int
    validation_status: str


@dataclass(frozen=True)
class ActionProposal:
    action_id: str
    mapping_id: str
    comparison: Comparison
    semantics_known: bool
    depends_on: tuple[str, ...]


@dataclass(frozen=True)
class MigrationAction:
    proposal: ActionProposal
    kind: ActionKind
    changes: tuple[str, ...]
    issue_codes: tuple[str, ...]


@dataclass(frozen=True)
class MigrationPlan:
    schema_version: int
    stage: str
    plan_id: str
    source_artifact: SourceArtifactIdentity
    destination: DestinationDeclaration
    domain: str
    mappings: tuple[IdentityMapping, ...]
    actions: tuple[MigrationAction, ...]
    dependencies: dict[str, tuple[str, ...]] = field(repr=False)
    validation: ValidationResult
    integrity_sha256: str

    def to_dict(self) -> dict[str, object]:
        payload = ContractReader("plan").mapping(load_json(_canonical(asdict(self)).decode("utf-8")), "$")
        parse_plan(payload)
        return payload

    def to_json(self) -> str:
        return _canonical(self.to_dict()).decode("utf-8")


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("utf-8")


def _destination(value: object, reader: ContractReader) -> DestinationDeclaration:
    data = reader.mapping(value, "$.destination", {"controller_id", "product", "version", "base_url"})
    return DestinationDeclaration(
        reader.text(reader.required(data, "controller_id", "$.destination"), "$.destination.controller_id"),
        reader.product(reader.required(data, "product", "$.destination"), "$.destination.product"),
        reader.version(reader.required(data, "version", "$.destination"), "$.destination.version"),
        reader.base_url(reader.required(data, "base_url", "$.destination"), "$.destination.base_url"),
    )


def _artifact_identity(raw: bytes) -> tuple[SourceArtifactIdentity, str]:
    reader = ContractReader("plan")
    if not isinstance(raw, bytes):
        reader.fail("invalid_type", "$.source_artifact", "Source artifact identity requires the exact input bytes.")
    try:
        payload = load_json(raw.decode("utf-8"))
    except (UnicodeError, ValueError, RecursionError):
        reader.fail("invalid_json", "$.source_artifact", "Source artifact must contain strict UTF-8 JSON.")
    try:
        artifact = parse_artifact(payload)
    except ContractValidationError as exc:
        raise ContractValidationError(
            ValidationResult("plan", "invalid", issues=exc.result.issues)
        ) from None
    checksum = hashlib.sha256(raw).hexdigest()
    return SourceArtifactIdentity(
        "sha256:" + checksum, checksum, artifact.schema_version, artifact.source,
        len(artifact.objects), artifact.validation.status,
    ), artifact.domain


def _source(value: object, reader: ContractReader) -> SourceArtifactIdentity:
    data = reader.mapping(
        value, "$.source_artifact",
        {"artifact_id", "sha256", "schema_version", "source", "object_count", "validation_status"},
    )
    checksum = reader.checksum(reader.required(data, "sha256", "$.source_artifact"), "$.source_artifact.sha256")
    if reader.required(data, "artifact_id", "$.source_artifact") != "sha256:" + checksum:
        reader.fail("integrity_mismatch", "$.source_artifact.artifact_id", "Artifact identity must match its checksum.")
    schema = reader.required(data, "schema_version", "$.source_artifact")
    count = reader.required(data, "object_count", "$.source_artifact")
    status = reader.required(data, "validation_status", "$.source_artifact")
    if type(schema) is not int or schema != 1:
        reader.fail("unsupported_schema", "$.source_artifact.schema_version", "Only artifact schema version 1 is supported.")
    if type(count) is not int or count < 0:
        reader.fail("invalid_type", "$.source_artifact.object_count", "Expected a nonnegative object count.")
    if not isinstance(status, str) or status not in ("not_validated", "valid", "invalid"):
        reader.fail("invalid_validation_info", "$.source_artifact.validation_status", "Unsupported artifact validation status.")
    return SourceArtifactIdentity(
        "sha256:" + checksum, checksum, 1,
        product_declaration(reader.required(data, "source", "$.source_artifact"), reader, "$.source_artifact.source"),
        count, status,
    )


def _proposal(value: object, reader: ContractReader) -> ActionProposal:
    data = reader.mapping(
        value, "$.proposal", {"action_id", "mapping_id", "comparison", "semantics_known", "depends_on"}
    )
    raw_comparison = reader.text(reader.required(data, "comparison", "$.proposal"), "$.proposal.comparison")
    try:
        comparison = Comparison(raw_comparison)
    except ValueError:
        reader.fail("invalid_comparison", "$.proposal.comparison", "Unsupported comparison declaration.")
    known = reader.required(data, "semantics_known", "$.proposal")
    if type(known) is not bool:
        reader.fail("invalid_type", "$.proposal.semantics_known", "Semantics knowledge must be explicitly declared as a boolean.")
    return ActionProposal(
        reader.identifier(reader.required(data, "action_id", "$.proposal"), "$.proposal.action_id"),
        reader.identifier(reader.required(data, "mapping_id", "$.proposal"), "$.proposal.mapping_id"),
        comparison, known,
        reader.references(reader.required(data, "depends_on", "$.proposal"), "$.proposal.depends_on"),
    )


def _items(value: object, reader: ContractReader, path: str) -> list[object]:
    if not isinstance(value, list):
        reader.fail("invalid_type", path, "Expected an array.")
    return list(value)


def _assemble(
    source: SourceArtifactIdentity, destination: DestinationDeclaration, domain: str,
    mappings: tuple[IdentityMapping, ...], proposals: tuple[ActionProposal, ...],
) -> MigrationPlan:
    reader = ContractReader("plan")
    if domain == "api-schema-evidence":
        reader.fail(
            "evidence_only_artifact", "$.domain",
            "Offline schema evidence cannot authorize migration planning.",
        )
    if domain == "controller-objects" and source.source.product == "cyber-controller":
        reader.fail(
            "controller_planning_required", "$.domain",
            "Cyber Controller objects require controller-specific planning and verification.",
        )
    mapping_by_id = {item.mapping_id: item for item in mappings}
    if len(mapping_by_id) != len(mappings):
        reader.fail("duplicate_mapping", "$.mappings", "Mapping identifiers must be unique.")
    if len({item.source_index for item in mappings}) != len(mappings) or len({item.source for item in mappings}) != len(mappings):
        reader.fail("duplicate_identity", "$.mappings", "Source indices and qualified identities must be unique.")
    if len(mappings) != source.object_count or any(item.source_index >= source.object_count for item in mappings):
        reader.fail("missing_mapping", "$.mappings", "Every artifact object requires exactly one explicit mapping, including unresolved objects.")
    for item in mappings:
        if (
            item.domain != domain or item.source_context != source.source
            or item.destination_context != ProductDeclaration(destination.product, destination.version)
        ):
            reader.fail("context_mismatch", "$.mappings", "Mapping domain and product/version contexts must match the plan.")
    mapping_graph = {
        item.mapping_id: set(item.depends_on) | ({item.parent_mapping} if item.parent_mapping else set())
        for item in mappings
    }
    dependency_order(mapping_graph, reader)
    by_id = {item.action_id: item for item in proposals}
    by_mapping = {item.mapping_id: item.action_id for item in proposals}
    if len(by_id) != len(proposals) or len(by_mapping) != len(proposals):
        reader.fail("duplicate_action", "$.actions", "Action identifiers and mapping references must be unique.")
    if by_mapping.keys() != mapping_by_id.keys():
        reader.fail("missing_action", "$.actions", "Every mapping requires exactly one action proposal.")
    graph = {item.action_id: set(item.depends_on) for item in proposals}
    order = dependency_order(graph, reader)
    for item in proposals:
        required = {by_mapping[key] for key in mapping_graph[item.mapping_id]}
        if not required <= graph[item.action_id]:
            reader.fail("invalid_dependency", "$.actions", "Actions must explicitly depend on their parent/dependency mapping actions.")
    targets: dict[object, list[str]] = {}
    for item in mappings:
        if item.destination is not None:
            targets.setdefault(item.destination, []).append(item.mapping_id)
    collisions = {key for values in targets.values() if len(values) > 1 for key in values}
    actions: dict[str, MigrationAction] = {}
    issues: list[ValidationIssue] = []
    for index, key in enumerate(order):
        proposal = by_id[key]
        mapping = mapping_by_id[proposal.mapping_id]
        codes: list[str] = []
        if mapping.state in (MappingState.UNRESOLVED, MappingState.AMBIGUOUS):
            codes.append("mapping_" + mapping.state.value)
        if mapping.mapping_id in collisions:
            codes.append("destination_collision")
        if not proposal.semantics_known:
            codes.append("unknown_semantics")
        if proposal.comparison == Comparison.UNKNOWN:
            codes.append("unknown_comparison")
        if source.validation_status == "invalid":
            codes.append("source_validation_invalid")
        if any(actions[dependency].kind in (ActionKind.BLOCKED, ActionKind.CONFLICT) for dependency in proposal.depends_on):
            codes.append("dependency_blocked")
        if (
            mapping.state == MappingState.MISSING and proposal.comparison not in (Comparison.MISSING, Comparison.UNKNOWN)
            or mapping.state == MappingState.RESOLVED and proposal.comparison == Comparison.MISSING
        ):
            codes.append("comparison_mismatch")
        if codes:
            kind = ActionKind.BLOCKED
        elif mapping.state == MappingState.MISSING:
            kind = ActionKind.CREATE
        elif proposal.comparison == Comparison.IDENTICAL:
            kind = ActionKind.SKIP
        else:
            kind = ActionKind.CONFLICT
            codes.append("configuration_differs")
        actions[key] = MigrationAction(
            proposal, kind, ("create-from-source",) if kind == ActionKind.CREATE else (), tuple(codes)
        )
        issues.extend(
            ValidationIssue(code, f"$.actions[{index}]", "Offline action requires explicit resolution; no write is authorized.")
            for code in codes
        )
    validation = ValidationResult("plan", "invalid" if issues else "valid", source.object_count, tuple(issues))
    body = {
        "schema_version": 1, "stage": "offline-candidate", "source_artifact": asdict(source),
        "destination": asdict(destination), "domain": domain,
        "mappings": [asdict(item) for item in sorted(mappings, key=lambda item: item.mapping_id)],
        "actions": [asdict(item) for item in actions.values()],
        "dependencies": {key: tuple(sorted(value)) for key, value in graph.items()},
        "validation": asdict(validation),
    }
    plan_id = "plan-" + hashlib.sha256(_canonical(body)).hexdigest()
    digest = hashlib.sha256(_canonical({"plan_id": plan_id, **body})).hexdigest()
    return MigrationPlan(
        1, "offline-candidate", plan_id, source, destination, domain,
        tuple(sorted(mappings, key=lambda item: item.mapping_id)), tuple(actions.values()),
        {key: tuple(sorted(value)) for key, value in graph.items()}, validation, digest,
    )


def create_plan(artifact_bytes: bytes, request: object) -> MigrationPlan:
    """Classify explicit offline declarations, without matching or executing objects."""
    reader = ContractReader("plan")
    data = reader.mapping(request, "$", {"destination", "mappings", "actions"})
    source, domain = _artifact_identity(artifact_bytes)
    destination = _destination(reader.required(data, "destination", "$"), reader)
    mappings = tuple(parse_mapping(item) for item in _items(reader.required(data, "mappings", "$"), reader, "$.mappings"))
    proposals = tuple(_proposal(item, reader) for item in _items(reader.required(data, "actions", "$"), reader, "$.actions"))
    return _assemble(source, destination, domain, mappings, proposals)


def parse_plan(payload: object) -> MigrationPlan:
    reader = ContractReader("plan")
    fields = {
        "schema_version", "stage", "plan_id", "source_artifact", "destination", "domain",
        "mappings", "actions", "dependencies", "validation", "integrity_sha256",
    }
    data = reader.mapping(payload, "$", fields)
    for key in sorted(fields):
        reader.required(data, key, "$")
    if type(data["schema_version"]) is not int or data["schema_version"] != 1:
        reader.fail("unsupported_schema", "$.schema_version", "Only integer plan schema version 1 is supported.")
    if data["stage"] != "offline-candidate":
        reader.fail("invalid_stage", "$.stage", "Only offline candidate plans are supported.")
    proposals: list[ActionProposal] = []
    for item in _items(data["actions"], reader, "$.actions"):
        action = reader.mapping(item, "$.actions", {"proposal", "kind", "changes", "issue_codes"})
        if reader.required(action, "kind", "$.actions") not in tuple(ActionKind):
            reader.fail("unsupported_action", "$.actions", "Only create, skip, conflict, and blocked actions are supported.")
        proposals.append(_proposal(reader.required(action, "proposal", "$.actions"), reader))
    plan = _assemble(
        _source(data["source_artifact"], reader), _destination(data["destination"], reader),
        reader.identifier(data["domain"], "$.domain"),
        tuple(parse_mapping(item) for item in _items(data["mappings"], reader, "$.mappings")),
        tuple(proposals),
    )
    reader.checksum(data["integrity_sha256"], "$.integrity_sha256")
    try:
        unchanged = _canonical(data) == _canonical(asdict(plan))
    except (TypeError, ValueError, RecursionError):
        reader.fail("invalid_type", "$", "Plan contents must be JSON-compatible.")
    if not unchanged:
        reader.fail("integrity_mismatch", "$", "Plan identity, contents, derived actions, or validation results have changed.")
    return plan


def verify_plan(
    payload: object, artifact_bytes: bytes, destination: object, expected_integrity: str
) -> MigrationPlan:
    reader = ContractReader("plan")
    plan = parse_plan(payload)
    reader.checksum(expected_integrity, "$.expected_integrity")
    if plan.integrity_sha256 != expected_integrity:
        reader.fail("integrity_mismatch", "$.integrity_sha256", "Plan does not match the independently retained digest.")
    source, domain = _artifact_identity(artifact_bytes)
    if plan.source_artifact != source or plan.domain != domain:
        reader.fail("source_changed", "$.source_artifact", "Source artifact bytes or declarations differ from the bound input.")
    if plan.destination != _destination(destination, reader):
        reader.fail("destination_changed", "$.destination", "Destination differs from the bound declaration.")
    return plan


def validate_plan(payload: object) -> ValidationResult:
    try:
        return parse_plan(payload).validation
    except ContractValidationError as exc:
        return exc.result
