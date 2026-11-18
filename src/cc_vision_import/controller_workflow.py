"""Controller-only offline orchestration and redacted reports; never execution."""

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path

from ._contract_validation import ContractReader
from .artifacts import parse_artifact
from .contracts import ContractValidationError, ExitStatus
from .controller_comparison import ControllerMigrationPlan, compare_controller_inventories, verify_controller_plan
from .controller_objects import validate_controller_credentials
from .offline_inputs import OfflineInputs, _versioned
from .plans import ActionKind


_STAGES = ("manifest", "source", "destination", "declarations", "comparison", "verification")
_INPUT_ERRORS = {"input_unreadable", "invalid_encoding", "invalid_json", "nonlocal_input"}
_LIMITATIONS = (
    "access_completeness_unverified", "credential_portability_unverified",
    "import_execution_not_authorized", "live_compatibility_unverified",
)


def _json(value: object) -> str:
    return json.dumps(value, separators=(",", ":"), ensure_ascii=True, allow_nan=False)


def _digest(value: object) -> str:
    return hashlib.sha256(_json(value).encode("utf-8")).hexdigest()


def _status_fields(status: ExitStatus) -> dict[str, object]:
    categories = {
        ExitStatus.SUCCESS: "success",
        ExitStatus.VALIDATION_FAILED: "blocked_plan",
        ExitStatus.INPUT_ERROR: "input_output_error",
        ExitStatus.CONTRACT_ERROR: "invalid_input",
        ExitStatus.INTEGRITY_ERROR: "integrity_failure",
        ExitStatus.INTERNAL_ERROR: "internal_failure",
    }
    return {"exit_code": int(status), "status": categories[status]}


@dataclass(frozen=True)
class OfflineWorkflowResult:
    report: dict[str, object]
    record: dict[str, object] | None = field(repr=False)
    exit_status: ExitStatus

    def record_json(self) -> str:
        if self.record is None:
            ContractReader("offline-workflow").fail(
                "record_unavailable", "$", "This failure cannot produce a protected planning record.",
            )
        body = {key: value for key, value in self.record.items() if key != "integrity_sha256"}
        try:
            unchanged = self.record.get("integrity_sha256") == _digest(body)
        except (TypeError, ValueError, RecursionError):
            unchanged = False
        if not unchanged:
            ContractReader("offline-workflow").fail(
                "integrity_mismatch", "$", "Protected record contents have changed.",
            )
        artifacts = ContractReader("offline-workflow").mapping(self.record["artifacts"], "$.artifacts")
        for artifact in artifacts.values():
            validate_controller_credentials(parse_artifact(artifact))
        return _json(self.record)


def _result(
    inputs: OfflineInputs | None, plan: ControllerMigrationPlan | None,
    completed: list[str], failure: str | None = None, codes: tuple[str, ...] = (),
) -> OfflineWorkflowResult:
    counts = {kind.value.upper(): 0 for kind in ActionKind}
    action_reports: list[dict[str, object]] = []
    action_records: list[dict[str, object]] = []
    prerequisites = set(_LIMITATIONS) | set(codes)
    if plan is not None:
        for action in plan.actions:
            counts[action.kind.value.upper()] += 1
            reference = "action-" + _digest([plan.plan_id, action.action_id])
            action_reports.append({
                "reference": reference, "kind": action.kind.value.upper(), "issue_codes": list(action.issue_codes),
            })
            action_records.append({
                "reference": reference, "action_id": action.action_id, "source_index": action.source_index,
                "destination_index": action.destination_index,
            })
            prerequisites.update(action.issue_codes)
    blocked = counts["BLOCKED"] > 0 or counts["CONFLICT"] > 0
    if "internal_error" in codes:
        status = ExitStatus.INTERNAL_ERROR
    elif set(codes) & _INPUT_ERRORS:
        status = ExitStatus.INPUT_ERROR
    elif failure == "verification" or "integrity_mismatch" in codes:
        status = ExitStatus.INTEGRITY_ERROR
    elif failure:
        status = ExitStatus.CONTRACT_ERROR
    else:
        status = ExitStatus.VALIDATION_FAILED if blocked else ExitStatus.SUCCESS
    record_available = not set(codes) & {"secret_value_not_allowed", "internal_error"}
    failures: list[dict[str, str]] = [{"stage": failure, "code": code} for code in codes] if failure else []
    if plan is not None:
        failures.extend(
            {"stage": "comparison", "code": code, "action_reference": row["reference"]}
            for row, action in zip(action_reports, plan.actions, strict=True)
            for code in action.issue_codes
        )
    report: dict[str, object] = {
        "schema_version": 1,
        "workflow_result": "failed" if failure else "blocked" if blocked else "planned",
        **_status_fields(status),
        "record_available": record_available,
        "execution_authorized": False,
        "plan_id": None if plan is None else plan.plan_id,
        "source_snapshot_sha256": None if plan is None else plan.source_sha256,
        "total_objects_evaluated": 0 if plan is None else len(plan.actions),
        "counts": counts, "actions": action_reports,
        "validation_failures": failures,
        "remaining_prerequisites": sorted(prerequisites),
        "stages": [
            {"stage": stage, "status": "failed" if stage == failure else "complete" if stage in completed else "blocked"}
            for stage in _STAGES
        ],
    }
    if not record_available:
        return OfflineWorkflowResult(report, None, status)
    artifacts: dict[str, object] = {}
    if inputs is not None:
        for role, artifact in inputs.artifacts.items():
            validate_controller_credentials(artifact)
            artifacts[role] = artifact.to_dict()
    body: dict[str, object] = {
        "schema_version": 1, "scope": "offline-controller-planning",
        "input_bindings": [] if inputs is None else inputs.bindings,
        "artifacts": artifacts,
        "plan": None if plan is None else plan.to_dict(),
        "action_records": action_records, "report": report,
    }
    body["integrity_sha256"] = _digest(body)
    return OfflineWorkflowResult(report, body, status)


def plan_offline_request(
    request: str | Path, *, verify_record: str | Path | None = None,
) -> OfflineWorkflowResult:
    """Recompute every stage and, optionally, verify a retained protected record."""
    inputs = None
    plan = None
    completed: list[str] = []
    stage = "manifest"
    try:
        try:
            inputs = OfflineInputs(request)
            manifest = inputs.manifest()
            completed.append(stage)
            stage = "source"
            source = inputs.side(manifest["source"], "source")
            completed.append(stage)
            stage = "destination"
            destination = inputs.side(manifest["destination"], "destination")
            completed.append(stage)
            stage = "declarations"
            declarations = inputs.declarations(manifest)
            completed.append(stage)
            stage = "comparison"
            plan = compare_controller_inventories(
                source, destination, declarations.mappings,
                complete_trees=declarations.complete_trees,
                semantics_known_for=declarations.semantics,
                comparison_rules=declarations.rules,
                device_access_acknowledgements=declarations.acknowledgements,
            )
            completed.append(stage)
            stage = "verification"
            retained = None
            candidate = plan.to_dict()
            if verify_record is not None:
                retained = inputs.read(str(verify_record), None, base=Path.cwd())
                reader = ContractReader("offline-workflow")
                saved = _versioned(
                    retained, {"scope", "input_bindings", "artifacts", "plan", "action_records", "report", "integrity_sha256"},
                    reader,
                )
                if saved["scope"] != "offline-controller-planning":
                    reader.fail("invalid_scope", "$", "Only offline controller planning records can be verified.")
                candidate = saved["plan"]
            verify_controller_plan(
                candidate, source, destination, declarations.mappings,
                complete_trees=declarations.complete_trees,
                semantics_known_for=declarations.semantics,
                comparison_rules=declarations.rules,
                device_access_acknowledgements=declarations.acknowledgements,
            )
            completed.append(stage)
            result = _result(inputs, plan, completed)
            if verify_record is not None:
                if _json(retained) != result.record_json():
                    ContractReader("offline-workflow").fail(
                        "integrity_mismatch", "$", "Retained record does not match the current inputs and declarations.",
                    )
            return result
        except ContractValidationError as error:
            codes = tuple(sorted({issue.code for issue in error.result.issues}))
        return _result(inputs, plan, completed, stage, codes)
    except Exception:
        # This boundary deliberately discards exception text, traceback, and partial state.
        return _result(None, None, completed, stage, ("internal_error",))
