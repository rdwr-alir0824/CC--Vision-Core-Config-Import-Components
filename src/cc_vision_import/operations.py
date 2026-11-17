import json
import re
from dataclasses import asdict, dataclass, field
from enum import StrEnum

from ._contract_validation import ContractReader
from ._json import load_json
from .plans import ActionKind, MigrationPlan, parse_plan


class ResultState(StrEnum):
    PLANNED = "planned"
    SKIPPED = "skipped"
    BLOCKED = "blocked"
    FAILED = "failed"
    COMPLETED = "completed"
    VERIFICATION_PENDING = "verification_pending"
    INDETERMINATE = "indeterminate"


@dataclass(frozen=True)
class VerificationEvidence:
    reference: str
    sha256: str
    matched: bool


@dataclass(frozen=True)
class OperationResult:
    operation_id: str
    plan_id: str
    plan_integrity_sha256: str
    action_id: str
    state: ResultState
    issue_codes: tuple[str, ...]
    verified: bool
    evidence: tuple[VerificationEvidence, ...] = field(repr=False)

    def to_json(self, plan: MigrationPlan) -> str:
        payload = load_json(json.dumps(asdict(self), allow_nan=False))
        parse_operation_result(payload, plan)
        return json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False)


def parse_operation_result(payload: object, plan: MigrationPlan) -> OperationResult:
    reader = ContractReader("operation-result")
    plan = parse_plan(plan.to_dict())
    fields = {
        "operation_id", "plan_id", "plan_integrity_sha256", "action_id", "state",
        "issue_codes", "verified", "evidence",
    }
    data = reader.mapping(payload, "$", fields)
    for key in sorted(fields):
        reader.required(data, key, "$")
    if data["plan_id"] != plan.plan_id or data["plan_integrity_sha256"] != plan.integrity_sha256:
        reader.fail("plan_mismatch", "$.plan_id", "Result must bind to the supplied plan identity and digest.")
    action_id = reader.identifier(data["action_id"], "$.action_id")
    action = next((item for item in plan.actions if item.proposal.action_id == action_id), None)
    if action is None:
        reader.fail("missing_action", "$.action_id", "Result references an action absent from the plan.")
    raw_state = reader.text(data["state"], "$.state")
    try:
        state = ResultState(raw_state)
    except ValueError:
        reader.fail("invalid_state", "$.state", "Unsupported operation result state.")
    codes = data["issue_codes"]
    if not isinstance(codes, list) or any(
        not isinstance(code, str) or not re.fullmatch(r"[a-z][a-z0-9_]*", code) for code in codes
    ):
        reader.fail("invalid_value", "$.issue_codes", "Expected an array of stable issue codes.")
    issue_codes = tuple(reader.text(code, "$.issue_codes") for code in codes)
    if state in (ResultState.BLOCKED, ResultState.FAILED, ResultState.INDETERMINATE) and not issue_codes:
        reader.fail("missing_reason", "$.issue_codes", "Blocked, failed, and indeterminate results require a reason.")
    verified = data["verified"]
    if type(verified) is not bool:
        reader.fail("invalid_type", "$.verified", "Verification status must be a boolean.")
    values = data["evidence"]
    if not isinstance(values, list):
        reader.fail("invalid_type", "$.evidence", "Expected structured verification evidence.")
    evidence: list[VerificationEvidence] = []
    for value in values:
        item = reader.mapping(value, "$.evidence", {"reference", "sha256", "matched"})
        matched = reader.required(item, "matched", "$.evidence")
        if type(matched) is not bool:
            reader.fail("invalid_type", "$.evidence.matched", "Evidence must declare whether intended state matched.")
        evidence.append(
            VerificationEvidence(
                reader.reference(reader.required(item, "reference", "$.evidence"), "$.evidence.reference"),
                reader.checksum(reader.required(item, "sha256", "$.evidence"), "$.evidence.sha256"),
                matched,
            )
        )
    if verified and (state != ResultState.COMPLETED or not evidence or not all(item.matched for item in evidence)):
        reader.fail("missing_verification_evidence", "$.verified", "Verified results require completed state and matching verification evidence.")
    if state in (ResultState.COMPLETED, ResultState.VERIFICATION_PENDING, ResultState.INDETERMINATE) and action.kind != ActionKind.CREATE:
        reader.fail("invalid_state", "$.state", "Only a proposed create can have an execution outcome.")
    if state == ResultState.SKIPPED and action.kind != ActionKind.SKIP:
        reader.fail("invalid_state", "$.state", "Skipped results require a skip action.")
    return OperationResult(
        reader.identifier(data["operation_id"], "$.operation_id"),
        plan.plan_id, plan.integrity_sha256, action_id, state, issue_codes, verified, tuple(evidence),
    )
