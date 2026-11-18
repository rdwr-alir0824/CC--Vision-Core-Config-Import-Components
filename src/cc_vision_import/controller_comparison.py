"""Conservative exact comparison of explicitly acknowledged offline semantics."""

import hashlib
import json
import re
from copy import deepcopy
from dataclasses import asdict, dataclass
from enum import StrEnum

from ._contract_validation import ContractReader
from .contracts import JsonValue
from .controller_objects import (
    ControllerDevice, ControllerInventory, ControllerObject, ControllerRoot, DeviceAccessLocation,
    SourceObjectReference, TreeName, is_controller_credential_field,
)
from .controller_planning import validate_controller_planning
from .mappings import MappingState
from .plans import ActionKind, Comparison


def _canonical(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)


def _digest(value: object) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _ordered(value: object) -> str:
    return json.dumps(value, separators=(",", ":"), ensure_ascii=True, allow_nan=False)


class ControllerComparisonRule(StrEnum):
    NATIVE_IDENTITY_PROVENANCE = "validated-native-identity-provenance-v1"


@dataclass(frozen=True)
class ControllerComparisonPolicy:
    policy_id: str
    evidence: tuple[str, ...]
    rules: tuple[ControllerComparisonRule, ...]
    rule_evidence: tuple[str, ...]
    ignored_fields: tuple[str, ...]
    field_order: str = "preserved"
    credential_values: str = "block-unresolved-or-masked"
    authorization: str = "offline-comparison-only"


def _policy(rules: tuple[ControllerComparisonRule, ...]) -> ControllerComparisonPolicy:
    if (
        not isinstance(rules, tuple)
        or any(not isinstance(rule, ControllerComparisonRule) for rule in rules)
        or len(set(rules)) != len(rules)
    ):
        ContractReader("controller-comparison").fail(
            "invalid_comparison_rule", "$.comparison_rules", "Expected distinct supported evidence-backed rules.",
        )
    return ControllerComparisonPolicy(
        "acknowledged-normalized-exact-v2",
        ("owner-policy-option-1:2026-11-18", "synthetic-tests:test_controller_comparison"),
        tuple(sorted(rules)),
        (
            "offline-contract:controller_objects._native_bindings",
            "offline-contract:controller_planning.validate_controller_planning",
        ) if rules else (),
        (
            "configuration.ormID", "configuration.parentOrmID",
            "configuration.meIdentifier.managedElementID",
        ) if rules else (),
    )


@dataclass(frozen=True)
class ControllerPlannedAction:
    action_id: str
    source_index: int
    destination_index: int | None
    tree: TreeName
    object_type: str
    semantics_acknowledged: bool
    kind: ActionKind
    comparison: Comparison
    parent_action: str | None
    depends_on: tuple[str, ...]
    issue_codes: tuple[str, ...]


@dataclass(frozen=True)
class ControllerMigrationPlan:
    schema_version: int
    stage: str
    source_sha256: str
    destination_sha256: str
    declarations_sha256: str
    comparison_policy: ControllerComparisonPolicy
    actions: tuple[ControllerPlannedAction, ...]
    plan_id: str
    integrity_sha256: str

    def to_dict(self) -> dict[str, object]:
        data = asdict(self)
        plan_id = data.pop("plan_id")
        integrity = data.pop("integrity_sha256")
        if (
            plan_id != "controller-plan-" + _digest(data)
            or integrity != _digest({"plan_id": plan_id, **data})
        ):
            ContractReader("controller-comparison").fail(
                "integrity_mismatch", "$", "Controller comparison plan contents have changed.",
            )
        return json.loads(_canonical({"plan_id": plan_id, "integrity_sha256": integrity, **data}))

    def to_json(self) -> str:
        return _canonical(self.to_dict())

    def summary(self) -> str:
        self.to_dict()
        lines = [
            "Offline controller comparison; no execution is authorized.",
            f"Policy: {self.comparison_policy.policy_id}; configuration field order preserved.",
            "Evidence: " + ", ".join(self.comparison_policy.evidence),
            "Rules: " + (", ".join(self.comparison_policy.rules) or "none"),
        ]
        if self.comparison_policy.rule_evidence:
            lines.append("Rule evidence: " + ", ".join(self.comparison_policy.rule_evidence))
        for tree in TreeName:
            actions = [item for item in self.actions if item.tree == tree]
            if actions:
                counts = ", ".join(
                    f"{kind.value.upper()}={sum(item.kind == kind for item in actions)}"
                    for kind in ActionKind
                )
                lines.append(f"{tree.value}: {counts}")
        for action in self.actions:
            reason = ",".join(action.issue_codes) or "none"
            lines.append(
                f"{action.action_id} {action.tree.value} {action.object_type} "
                f"{action.kind.value.upper()} issues={reason}"
            )
        return "\n".join(lines)


def _configuration(
    item: ControllerObject, rules: tuple[ControllerComparisonRule, ...],
) -> dict[str, JsonValue]:
    configuration = deepcopy(item.configuration)
    if ControllerComparisonRule.NATIVE_IDENTITY_PROVENANCE in rules:
        configuration.pop("ormID", None)
        configuration.pop("parentOrmID", None)
        identifier = configuration.get("meIdentifier")
        if isinstance(identifier, dict):
            identifier.pop("managedElementID", None)
    result: dict[str, JsonValue] = {"configuration": configuration}
    if not isinstance(item, ControllerRoot):
        result["name"] = item.name
    if isinstance(item, ControllerDevice):
        result.update(
            device_type=item.device_type, management_ip=item.management_ip,
            device_access={"location": item.device_access.location.value, "value": item.device_access.value},
        )
    return result


def _uncertain_credentials(value: JsonValue) -> bool:
    if isinstance(value, dict):
        return any(is_controller_credential_field(key) for key in value) or any(
            _uncertain_credentials(item) for item in value.values()
        )
    if isinstance(value, list):
        return any(_uncertain_credentials(item) for item in value)
    if isinstance(value, str):
        return bool(re.fullmatch(r"[*#\u2022\u25cf]{3,}", value)) or value.casefold() in (
            "redacted", "<redacted>", "[redacted]", "masked", "<masked>", "[masked]",
            "hidden", "<hidden>", "[hidden]",
        )
    return False


def _credential_uncertainty(item: ControllerObject) -> bool:
    return _uncertain_credentials(_configuration(item, ())) or (
        isinstance(item, ControllerDevice)
        and item.device_access.location != DeviceAccessLocation.ABSENT
        and item.device_access.value is None
    )


def compare_controller_inventories(
    source: ControllerInventory, destination: ControllerInventory, mappings: object, *,
    complete_trees: tuple[TreeName, ...] = (),
    semantics_known_for: tuple[SourceObjectReference, ...] = (),
    comparison_rules: tuple[ControllerComparisonRule, ...] = (),
) -> ControllerMigrationPlan:
    reader = ContractReader("controller-comparison")
    policy = _policy(comparison_rules)
    validated = validate_controller_planning(source, destination, mappings, complete_trees=complete_trees)
    source, destination = validated.source, validated.destination
    if (
        not isinstance(semantics_known_for, tuple)
        or any(not isinstance(item, SourceObjectReference) for item in semantics_known_for)
    ):
        reader.fail("invalid_semantics", "$.semantics_known_for", "Expected explicit qualified object acknowledgements.")
    references = tuple(item.reference for item in source.objects)
    if (
        any(item not in references for item in semantics_known_for)
        or len(set(semantics_known_for)) != len(semantics_known_for)
    ):
        reader.fail("invalid_semantics", "$.semantics_known_for", "Acknowledgements must identify distinct source objects.")
    known = set(semantics_known_for)
    actions: dict[int, ControllerPlannedAction] = {}
    for index in validated.order:
        entry = validated.entries[index]
        item = source.objects[index]
        codes = list(entry.issue_codes)
        comparison = Comparison.UNKNOWN
        target = None if entry.destination_index is None else destination.objects[entry.destination_index]
        if _credential_uncertainty(item) or (target is not None and _credential_uncertainty(target)):
            codes.append("unresolved_credentials")
        if item.reference not in known:
            codes.append("unknown_semantics")
        elif not codes:
            if entry.mapping is not None and entry.mapping.state == MappingState.MISSING:
                comparison = Comparison.MISSING
            elif entry.destination_index is not None:
                target = destination.objects[entry.destination_index]
                comparison = (
                    Comparison.IDENTICAL if _ordered(_configuration(item, policy.rules))
                    == _ordered(_configuration(target, policy.rules))
                    else Comparison.DIFFERENT
                )
        if any(actions[key].kind in (ActionKind.BLOCKED, ActionKind.CONFLICT) for key in entry.depends_on):
            codes.append("dependency_blocked")
        if codes or comparison == Comparison.UNKNOWN:
            kind = ActionKind.BLOCKED
        elif comparison == Comparison.MISSING:
            kind = ActionKind.CREATE
        elif comparison == Comparison.IDENTICAL:
            kind = ActionKind.SKIP
        else:
            kind = ActionKind.CONFLICT
            codes.append("configuration_differs")
        actions[index] = ControllerPlannedAction(
            f"object-{index}", index, entry.destination_index, item.reference.tree, item.reference.kind.value,
            item.reference in known,
            kind, comparison, None if entry.parent_index is None else f"object-{entry.parent_index}",
            tuple(f"object-{key}" for key in entry.depends_on), tuple(sorted(set(codes))),
        )
    source_digest = hashlib.sha256(_ordered(source.to_artifact().to_dict()).encode("utf-8")).hexdigest()
    destination_digest = hashlib.sha256(_ordered(destination.to_artifact().to_dict()).encode("utf-8")).hexdigest()
    declarations_digest = _digest({
        "mappings": [None if entry.mapping is None else asdict(entry.mapping) for entry in validated.entries],
        "complete_trees": validated.complete_trees,
        "semantics_known_for": [index for index, item in enumerate(source.objects) if item.reference in known],
        "comparison_policy": asdict(policy),
    })
    body = {
        "schema_version": 2, "stage": "offline-controller-candidate", "source_sha256": source_digest,
        "destination_sha256": destination_digest, "declarations_sha256": declarations_digest,
        "comparison_policy": asdict(policy),
        "actions": [asdict(item) for item in actions.values()],
    }
    plan_id = "controller-plan-" + _digest(body)
    return ControllerMigrationPlan(
        2, "offline-controller-candidate", source_digest, destination_digest,
        declarations_digest, policy, tuple(actions.values()), plan_id,
        _digest({"plan_id": plan_id, **body}),
    )


def verify_controller_plan(
    payload: object, source: ControllerInventory, destination: ControllerInventory, mappings: object, *,
    complete_trees: tuple[TreeName, ...] = (),
    semantics_known_for: tuple[SourceObjectReference, ...] = (),
    comparison_rules: tuple[ControllerComparisonRule, ...] = (),
) -> ControllerMigrationPlan:
    """Recompute the offline candidate from retained inputs; this is not import approval."""
    expected = compare_controller_inventories(
        source, destination, mappings, complete_trees=complete_trees, semantics_known_for=semantics_known_for,
        comparison_rules=comparison_rules,
    )
    try:
        unchanged = isinstance(payload, dict) and _canonical(payload) == expected.to_json()
    except (TypeError, ValueError, RecursionError):
        unchanged = False
    if not unchanged:
        ContractReader("controller-comparison").fail(
            "integrity_mismatch", "$", "Plan does not match the retained inventories and declarations.",
        )
    return expected
