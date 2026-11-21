"""Network-incapable, single-owner offline control model, not process supervision."""

import json
import math
import struct
from collections.abc import Callable
from dataclasses import dataclass, field, replace
from enum import StrEnum
from uuid import UUID


SCHEMA_VERSION = 1
PROTOCOL_VERSION = 1


class Failure(StrEnum):
    CONTRACT = "invalid_contract"
    STATE = "invalid_state"
    TIMEOUT = "timeout"
    AUTHORIZATION = "authorization_revoked_or_stale"
    GENERATION = "stale_or_reused_generation"
    VALIDATION = "candidate_validation_failed"
    WORKER = "worker_error"
    DISPOSITION = "resource_disposition_failed"
    QUARANTINE = "quarantine_required"
    OWNERSHIP = "supervisor_replaced"
    CLOCK = "invalid_monotonic_clock"
    PROTOCOL = "invalid_protocol"
    CAPACITY = "offline_registry_full"


class ModelError(Exception):
    def __init__(self, category: Failure) -> None:
        super().__init__(f"Offline supervision rejected: {category.value}.")
        self.category = category


def _require(condition: bool, category: Failure = Failure.CONTRACT) -> None:
    if not condition:
        raise ModelError(category)


def _version(value: object) -> None:
    _require(type(value) is int and value == SCHEMA_VERSION)


def _generation(value: object) -> None:
    _require(type(value) is int and 1 <= value <= 2**31 - 1)


def _reference(value: object) -> None:
    _require(type(value) is UUID and value.version == 4)


def _finite(value: object) -> bool:
    return type(value) in (int, float) and -1e15 < value < 1e15 and math.isfinite(value)


@dataclass(frozen=True)
class Identity:
    """Local random UUID plus generation; never a native controller ID or PID."""

    reference: UUID
    generation: int
    schema_version: int = SCHEMA_VERSION

    def __post_init__(self) -> None:
        _version(self.schema_version)
        _reference(self.reference)
        _generation(self.generation)


@dataclass(frozen=True)
class OperationRequest:
    operation: Identity
    authorization: Identity
    worker: Identity
    request_ref: UUID
    timeout: float
    admission_expires_at: float
    schema_version: int = SCHEMA_VERSION

    def __post_init__(self) -> None:
        _version(self.schema_version)
        for identity in (self.operation, self.authorization, self.worker):
            _require(type(identity) is Identity)
            identity.__post_init__()
        _reference(self.request_ref)
        _require(_finite(self.timeout) and 0 < self.timeout <= 300)
        _require(_finite(self.admission_expires_at))


@dataclass(frozen=True)
class Deadline:
    admitted_at: float
    expires_at: float
    schema_version: int = SCHEMA_VERSION

    def __post_init__(self) -> None:
        _version(self.schema_version)
        _require(
            _finite(self.admitted_at) and _finite(self.expires_at)
            and self.admitted_at < self.expires_at
        )


class OperationState(StrEnum):
    NOT_ADMITTED = "not_admitted"
    ADMITTED = "admitted"
    STARTING = "starting"
    READY = "ready"
    RUNNING = "running"
    CANDIDATE_RECEIVED = "candidate_received"
    VALIDATING = "validating"
    READY_TO_COMMIT = "ready_to_commit"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMED_OUT = "timed_out"
    TERMINATION_REQUESTED = "termination_requested"
    QUARANTINED = "quarantined"


class TerminationState(StrEnum):
    NOT_REQUESTED = "not_requested"
    REQUESTED = "requested"


class ExitState(StrEnum):
    UNCONFIRMED = "unconfirmed"
    CONFIRMED = "exit_confirmed_status_unknown"
    NORMAL = "normal_exit_confirmed"
    ABNORMAL = "abnormal_exit_confirmed"


class ReapingState(StrEnum):
    UNCONFIRMED = "unconfirmed"
    CONFIRMED = "confirmed"
    FAILED = "failed"


class ResourceDisposition(StrEnum):
    UNCONFIRMED = "unconfirmed"
    RELEASED = "successful_release"
    ABORTED = "failure_abort_disposition"
    FAILED = "failed"


class QuarantineState(StrEnum):
    CLEAR = "clear"
    REQUIRED = "required"
    RECOVERED = "recovered"


@dataclass(frozen=True)
class Candidate:
    operation: Identity
    authorization: Identity
    worker: Identity
    candidate_ref: UUID
    result_ref: UUID = field(repr=False)
    complete: bool
    validated: bool
    schema_version: int = SCHEMA_VERSION

    def __post_init__(self) -> None:
        _version(self.schema_version)
        for identity in (self.operation, self.authorization, self.worker):
            _require(type(identity) is Identity)
            identity.__post_init__()
        _reference(self.candidate_ref)
        _reference(self.result_ref)
        _require(type(self.complete) is bool and type(self.validated) is bool)


@dataclass(frozen=True)
class RecoveryEvidence:
    """Trusted offline owner's observations, not worker self-attestation."""

    operation: Identity
    worker: Identity
    evidence_ref: UUID
    exit_confirmed: bool
    reaped: bool
    disposition: ResourceDisposition
    schema_version: int = SCHEMA_VERSION

    def __post_init__(self) -> None:
        _version(self.schema_version)
        for identity in (self.operation, self.worker):
            _require(type(identity) is Identity)
            identity.__post_init__()
        _reference(self.evidence_ref)
        _require(type(self.exit_confirmed) is bool and type(self.reaped) is bool)
        _require(type(self.disposition) is ResourceDisposition)


@dataclass(frozen=True)
class OperationSnapshot:
    operation: Identity
    worker: Identity
    deadline: Deadline
    state: OperationState = OperationState.NOT_ADMITTED
    failure: Failure | None = None
    termination: TerminationState = TerminationState.NOT_REQUESTED
    exit: ExitState = ExitState.UNCONFIRMED
    reaping: ReapingState = ReapingState.UNCONFIRMED
    disposition: ResourceDisposition = ResourceDisposition.UNCONFIRMED
    quarantine: QuarantineState = QuarantineState.CLEAR
    simulated_dispatches: int = 0
    candidate_ref: UUID | None = None
    committed_ref: UUID | None = field(default=None, repr=False)
    completed_at: float | None = None
    schema_version: int = SCHEMA_VERSION


@dataclass(frozen=True)
class ProtocolLimits:
    """Mandatory proposed offline limits; no production-approved defaults."""

    request_bytes: int
    result_bytes: int
    frame_bytes: int
    aggregate_bytes: int
    wire_bytes: int
    frame_count: int
    nesting: int
    schema_version: int = SCHEMA_VERSION

    def __post_init__(self) -> None:
        _version(self.schema_version)
        for value, ceiling in (
            (self.request_bytes, 16384), (self.result_bytes, 65536),
            (self.frame_bytes, 65536), (self.aggregate_bytes, 262144),
            (self.wire_bytes, 262272), (self.frame_count, 32), (self.nesting, 8),
        ):
            _require(type(value) is int and 0 < value <= ceiling)
        _require(
            self.request_bytes <= self.frame_bytes
            and self.result_bytes <= self.frame_bytes <= self.aggregate_bytes
            and self.wire_bytes >= self.frame_bytes + 4
        )


class MessageType(StrEnum):
    REQUEST = "request"
    READY = "ready"
    PERMIT = "permit"
    CANDIDATE = "candidate"
    FAILURE = "failure"
    CANCEL = "cancel"


@dataclass(frozen=True)
class Frame:
    kind: MessageType
    sequence: int
    operation: Identity
    authorization: Identity
    worker: Identity
    payload: tuple[tuple[str, object], ...] = field(repr=False)
    protocol_version: int = PROTOCOL_VERSION


def _unique_pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        _require(key not in result, Failure.PROTOCOL)
        result[key] = value
    return result


def _invalid_constant(_: str) -> object:
    raise ModelError(Failure.PROTOCOL)


class FrameCodec:
    """One bounded bidirectional transcript. Each call consumes one whole frame.

    REQUEST is parent->worker; READY/CANDIDATE/FAILURE are worker->parent;
    PERMIT/CANCEL are parent->worker. No endpoints or dispatch hooks exist.
    """

    def __init__(
        self, request: OperationRequest, deadline: Deadline, limits: ProtocolLimits,
    ) -> None:
        _require(type(request) is OperationRequest and type(limits) is ProtocolLimits
                 and type(deadline) is Deadline)
        request.__post_init__()
        deadline.__post_init__()
        limits.__post_init__()
        _require(deadline.expires_at == deadline.admitted_at + request.timeout)
        self._request = request
        self._deadline = deadline
        self._limits = limits
        self._phase = "initial"
        self._sequence = 0
        self._payload_bytes = 0
        self._wire_bytes = 0
        self._poisoned = False

    def envelope(
        self, kind: MessageType, payload: dict[str, object],
    ) -> dict[str, object]:
        _require(type(kind) is MessageType and type(payload) is dict
                 and len(payload) <= 6, Failure.PROTOCOL)
        r = self._request
        return {
            "version": PROTOCOL_VERSION, "type": kind.value,
            "sequence": self._sequence + 1,
            "operation_id": str(r.operation.reference),
            "operation_generation": r.operation.generation,
            "authorization_id": str(r.authorization.reference),
            "authorization_generation": r.authorization.generation,
            "worker_id": str(r.worker.reference),
            "worker_generation": r.worker.generation,
            "payload": dict(payload),
        }

    def _budget(self, size: int) -> None:
        limits = self._limits
        _require(
            not self._poisoned and 0 < size <= limits.frame_bytes
            and self._sequence < limits.frame_count
            and self._payload_bytes + size <= limits.aggregate_bytes
            and self._wire_bytes + size + 4 <= limits.wire_bytes,
            Failure.PROTOCOL,
        )

    def _depth(self, text: str) -> None:
        depth, quoted, escaped = 0, False, False
        for character in text:
            if quoted:
                if escaped:
                    escaped = False
                elif character == "\\":
                    escaped = True
                elif character == '"':
                    quoted = False
            elif character == '"':
                quoted = True
            elif character in "[{":
                depth += 1
                _require(depth <= self._limits.nesting, Failure.PROTOCOL)
            elif character in "]}":
                depth -= 1
                _require(depth >= 0, Failure.PROTOCOL)
        _require(not quoted and depth == 0, Failure.PROTOCOL)

    def _check(self, data: object) -> tuple[Frame, str]:
        _require(type(data) is dict, Failure.PROTOCOL)
        expected = self.envelope(MessageType.READY, {})
        _require(len(data) == len(expected), Failure.PROTOCOL)
        _require(set(data) == set(expected), Failure.PROTOCOL)
        for key in expected.keys() - {"type", "payload"}:
            _require(
                type(data[key]) is type(expected[key]) and data[key] == expected[key],
                Failure.PROTOCOL,
            )
        _require(type(data["type"]) is str, Failure.PROTOCOL)
        kind = next((item for item in MessageType if item.value == data["type"]), None)
        _require(kind is not None, Failure.PROTOCOL)
        assert kind is not None
        allowed = {
            "initial": {MessageType.REQUEST: "requested"},
            "requested": {MessageType.READY: "ready", MessageType.FAILURE: "terminal",
                          MessageType.CANCEL: "terminal"},
            "ready": {MessageType.PERMIT: "running", MessageType.CANCEL: "terminal",
                      MessageType.FAILURE: "terminal"},
            "running": {MessageType.CANDIDATE: "terminal", MessageType.FAILURE: "terminal",
                        MessageType.CANCEL: "terminal"},
            "terminal": {},
        }
        _require(kind in allowed[self._phase], Failure.PROTOCOL)
        payload = data["payload"]
        _require(type(payload) is dict, Failure.PROTOCOL)
        _require(len(payload) <= 6, Failure.PROTOCOL)
        fields = {
            MessageType.REQUEST: {"request_ref", "admitted_at", "expires_at", "clock_domain"},
            MessageType.READY: set(),
            MessageType.PERMIT: set(),
            MessageType.CANDIDATE: {
                "schema_version", "candidate_ref", "result_ref", "complete", "validated",
            },
            MessageType.FAILURE: {"category"},
            MessageType.CANCEL: {"category"},
        }[kind]
        optional = {"evidence_ref"} if kind == MessageType.CANDIDATE else set()
        _require(fields <= set(payload) <= fields | optional, Failure.PROTOCOL)
        for key, value in payload.items():
            if key.endswith("_ref"):
                valid_ref = False
                if type(value) is str and len(value) == 36:
                    try:
                        reference = UUID(value)
                        valid_ref = str(reference) == value and reference.version == 4
                    except ValueError:
                        pass
                _require(valid_ref, Failure.PROTOCOL)
            elif key in ("complete", "validated"):
                _require(type(value) is bool, Failure.PROTOCOL)
            elif key in ("admitted_at", "expires_at"):
                _require(_finite(value), Failure.PROTOCOL)
            elif key == "schema_version":
                _require(type(value) is int and value == SCHEMA_VERSION, Failure.PROTOCOL)
            elif key == "clock_domain":
                _require(type(value) is str and value == "injected-monotonic", Failure.PROTOCOL)
            elif key == "category":
                _require(type(value) is str and len(value) <= 64
                         and value in {item.value for item in Failure},
                         Failure.PROTOCOL)
        if kind == MessageType.REQUEST:
            _require(
                payload["request_ref"] == str(self._request.request_ref)
                and payload["admitted_at"] == self._deadline.admitted_at
                and payload["expires_at"] == self._deadline.expires_at,
                Failure.PROTOCOL,
            )
        request = self._request
        return Frame(
            kind, self._sequence + 1, request.operation, request.authorization,
            request.worker, tuple(payload.items()),
        ), allowed[self._phase][kind]

    def _consume(self, frame: Frame, phase: str, size: int) -> Frame:
        cap = (
            self._limits.request_bytes if frame.kind == MessageType.REQUEST else
            self._limits.result_bytes if frame.kind == MessageType.CANDIDATE else
            self._limits.frame_bytes
        )
        _require(size <= cap, Failure.PROTOCOL)
        self._sequence += 1
        self._payload_bytes += size
        self._wire_bytes += size + 4
        self._phase = phase
        return frame

    def encode(self, data: dict[str, object]) -> bytes:
        try:
            _require(not self._poisoned, Failure.PROTOCOL)
            frame, phase = self._check(data)
            raw = json.dumps(data, ensure_ascii=True, allow_nan=False, separators=(",", ":")).encode("utf-8")
            self._budget(len(raw))
            self._depth(raw.decode("utf-8"))
            self._consume(frame, phase, len(raw))
            return struct.pack("!I", len(raw)) + raw
        except ModelError:
            self._poisoned = True
            raise

    def decode(self, wire: bytes) -> Frame:
        try:
            _require(type(wire) is bytes and 4 <= len(wire) <= self._limits.frame_bytes + 4,
                     Failure.PROTOCOL)
            size = struct.unpack("!I", wire[:4])[0]
            self._budget(size)
            _require(len(wire) == size + 4, Failure.PROTOCOL)
            data: object = None
            parsed = False
            try:
                text = wire[4:].decode("utf-8", errors="strict")
                self._depth(text)
                data = json.loads(text, object_pairs_hook=_unique_pairs,
                                  parse_constant=_invalid_constant)
                parsed = True
            except (UnicodeDecodeError, ValueError, RecursionError):
                pass
            _require(parsed, Failure.PROTOCOL)
            frame, phase = self._check(data)
            return self._consume(frame, phase, size)
        except ModelError:
            self._poisoned = True
            raise


_ACTIVE = frozenset({
    OperationState.ADMITTED, OperationState.STARTING, OperationState.READY,
    OperationState.RUNNING, OperationState.CANDIDATE_RECEIVED,
    OperationState.VALIDATING, OperationState.READY_TO_COMMIT,
})
_TRANSITIONS = {
    OperationState.NOT_ADMITTED: {OperationState.ADMITTED, OperationState.FAILED,
                                 OperationState.TIMED_OUT},
    OperationState.ADMITTED: {OperationState.STARTING},
    OperationState.STARTING: {OperationState.READY},
    OperationState.READY: {OperationState.RUNNING},
    OperationState.RUNNING: {OperationState.CANDIDATE_RECEIVED},
    OperationState.CANDIDATE_RECEIVED: {OperationState.VALIDATING},
    OperationState.VALIDATING: {OperationState.READY_TO_COMMIT},
    OperationState.READY_TO_COMMIT: {OperationState.COMPLETED},
    OperationState.FAILED: {OperationState.TERMINATION_REQUESTED, OperationState.QUARANTINED},
    OperationState.TIMED_OUT: {OperationState.TERMINATION_REQUESTED, OperationState.QUARANTINED},
    OperationState.TERMINATION_REQUESTED: {OperationState.QUARANTINED},
    OperationState.QUARANTINED: set(),
    OperationState.COMPLETED: set(),
}
for _state in _ACTIVE:
    _TRANSITIONS[_state].update({OperationState.FAILED, OperationState.TIMED_OUT})


@dataclass
class _Operation:
    request: OperationRequest
    snapshot: OperationSnapshot
    candidate: Candidate | None = None


class RecoveryLedger:
    """Explicitly shared, bounded, in-memory recovery owner.

    Never reconstruct this ledger to clear a restriction. Persistence and
    proving recovery after interpreter/owner loss are deliberately not modeled.
    """

    def __init__(self, *, capacity: int) -> None:
        _require(type(capacity) is int and 1 <= capacity <= 128)
        self._capacity = capacity
        self._epoch = 0
        self._last_now: float | None = None
        self._authorizations: dict[UUID, tuple[int, bool]] = {}
        self._operations: dict[Identity, _Operation] = {}
        self._operation_ids: set[UUID] = set()
        self._worker_ids: set[UUID] = set()
        self._last_generation = 0
        self._last_worker_generation = 0
        self._admission_reserved = False


class Coordinator:
    """Serialized logical events only; dispatch just increments a counter.

    Callers must supply the same ledger and clock domain on replacement. This
    is not thread-safe, a Python sandbox, an approval authority or a live adapter.
    """

    def __init__(self, ledger: RecoveryLedger, *, clock: Callable[[], float]) -> None:
        _require(type(ledger) is RecoveryLedger and callable(clock))
        self._ledger = ledger
        self._clock = clock
        ledger._epoch += 1
        self._epoch = ledger._epoch
        self._current: _Operation | None = None
        for operation in ledger._operations.values():
            if operation.snapshot.state == OperationState.NOT_ADMITTED:
                self._abort(operation, Failure.OWNERSHIP)
            elif operation.snapshot.state in _ACTIVE:
                self._observe(operation)
                self._abort(operation, Failure.OWNERSHIP)

    def _owner(self) -> None:
        _require(self._epoch == self._ledger._epoch, Failure.OWNERSHIP)

    def _now(self) -> float:
        self._owner()
        value: object = None
        try:
            value = self._clock()
        except Exception:
            # Clock callbacks are a trusted seam; report only a fixed category.
            pass
        self._owner()
        _require(
            _finite(value)
            and (self._ledger._last_now is None or value >= self._ledger._last_now),
            Failure.CLOCK,
        )
        assert isinstance(value, (int, float))
        self._ledger._last_now = value
        return value

    def authorize(self, authorization: Identity) -> None:
        self._owner()
        _require(type(authorization) is Identity)
        authorization.__post_init__()
        previous = self._ledger._authorizations.get(authorization.reference)
        _require(previous is None or authorization.generation > previous[0], Failure.GENERATION)
        _require(previous is not None or len(self._ledger._authorizations) < self._ledger._capacity,
                 Failure.CAPACITY)
        self._ledger._authorizations[authorization.reference] = (authorization.generation, True)

    def revoke(self, authorization: Identity) -> None:
        self._owner()
        _require(type(authorization) is Identity)
        current = self._ledger._authorizations.get(authorization.reference)
        _require(current == (authorization.generation, True), Failure.AUTHORIZATION)
        self._ledger._authorizations[authorization.reference] = (authorization.generation, False)
        for operation in self._ledger._operations.values():
            if operation.request.authorization == authorization and operation.snapshot.state in _ACTIVE:
                self._observe(operation)
                self._abort(operation, Failure.AUTHORIZATION)

    def _authorized(self, operation: _Operation) -> bool:
        identity = operation.request.authorization
        return self._ledger._authorizations.get(identity.reference) == (identity.generation, True)

    def _abort(self, operation: _Operation, failure: Failure) -> None:
        snapshot = operation.snapshot
        if snapshot.state == OperationState.COMPLETED:
            raise ModelError(Failure.STATE)
        if snapshot.failure is not None:
            return
        state = OperationState.TIMED_OUT if failure == Failure.TIMEOUT else OperationState.FAILED
        _require(state in _TRANSITIONS[snapshot.state], Failure.STATE)
        worker_possible = snapshot.state in _ACTIVE - {OperationState.ADMITTED}
        operation.candidate = None
        operation.snapshot = replace(
            snapshot,
            state=state,
            failure=failure, candidate_ref=None,
            termination=TerminationState.REQUESTED if worker_possible else snapshot.termination,
            quarantine=QuarantineState.REQUIRED if worker_possible else snapshot.quarantine,
        )

    def _observe(self, operation: _Operation) -> None:
        if operation.snapshot.state not in _ACTIVE:
            return
        try:
            now = self._now()
        except ModelError as error:
            self._abort(operation, error.category)
            raise
        if now >= operation.snapshot.deadline.expires_at:
            self._abort(operation, Failure.TIMEOUT)
        elif not self._authorized(operation):
            self._abort(operation, Failure.AUTHORIZATION)

    def _operation(self) -> _Operation:
        self._owner()
        _require(self._current is not None, Failure.STATE)
        assert self._current is not None
        operation = self._current
        identity = operation.request.operation
        self._observe(operation)
        self._owner()
        _require(
            self._current is operation and operation.snapshot.operation == identity,
            operation.snapshot.failure or Failure.GENERATION,
        )
        return operation

    def _worker_operation(self, worker: Identity) -> _Operation:
        operation = self._operation()
        _require(type(worker) is Identity and worker == operation.request.worker, Failure.GENERATION)
        return operation

    def _advance(self, operation: _Operation, state: OperationState) -> None:
        self._owner()
        self._observe(operation)
        snapshot = operation.snapshot
        if snapshot.failure is not None and state not in (
            OperationState.TERMINATION_REQUESTED, OperationState.QUARANTINED,
        ):
            raise ModelError(snapshot.failure)
        _require(state in _TRANSITIONS[snapshot.state], Failure.STATE)
        operation.snapshot = replace(snapshot, state=state)

    def admit(self, request: OperationRequest) -> OperationSnapshot:
        self._owner()
        ledger = self._ledger
        _require(not ledger._admission_reserved, Failure.STATE)
        ledger._admission_reserved = True
        try:
            return self._admit(request)
        finally:
            ledger._admission_reserved = False

    def _admit(self, request: OperationRequest) -> OperationSnapshot:
        now = self._now()
        _require(type(request) is OperationRequest)
        request.__post_init__()
        ledger = self._ledger
        _require(not any(
            item.snapshot.quarantine == QuarantineState.REQUIRED
            for item in ledger._operations.values()
        ), Failure.QUARANTINE)
        _require(not any(item.snapshot.state in _ACTIVE for item in ledger._operations.values()),
                 Failure.STATE)
        _require(len(ledger._operations) < ledger._capacity, Failure.CAPACITY)
        _require(
            request.operation.reference not in ledger._operation_ids
            and request.worker.reference not in ledger._worker_ids
            and request.operation.generation > ledger._last_generation
            and request.worker.generation > ledger._last_worker_generation,
            Failure.GENERATION,
        )
        operation = _Operation(request, OperationSnapshot(
            request.operation, request.worker, Deadline(now, now + request.timeout),
        ))
        ledger._operations[request.operation] = operation
        ledger._operation_ids.add(request.operation.reference)
        ledger._worker_ids.add(request.worker.reference)
        ledger._last_generation = request.operation.generation
        ledger._last_worker_generation = request.worker.generation
        self._current = operation
        try:
            checked = self._now()
        except ModelError as error:
            self._abort(operation, error.category)
            raise
        self._owner()
        if checked >= request.admission_expires_at or checked >= operation.snapshot.deadline.expires_at:
            self._abort(operation, Failure.TIMEOUT)
        elif not self._authorized(operation):
            self._abort(operation, Failure.AUTHORIZATION)
        else:
            self._advance(operation, OperationState.ADMITTED)
        return operation.snapshot

    def snapshot(self, identity: Identity | None = None) -> OperationSnapshot:
        self._owner()
        if identity is None:
            return self._operation().snapshot
        _require(identity in self._ledger._operations, Failure.GENERATION)
        operation = self._ledger._operations[identity]
        self._observe(operation)
        return operation.snapshot

    def start_worker(self) -> OperationSnapshot:
        operation = self._operation()
        self._advance(operation, OperationState.STARTING)
        return operation.snapshot

    def worker_ready(self, worker: Identity) -> OperationSnapshot:
        operation = self._worker_operation(worker)
        self._advance(operation, OperationState.READY)
        return operation.snapshot

    def dispatch(self) -> OperationSnapshot:
        operation = self._operation()
        if operation.snapshot.failure is not None:
            raise ModelError(operation.snapshot.failure)
        _require(not any(
            item.snapshot.quarantine == QuarantineState.REQUIRED
            for item in self._ledger._operations.values()
        ), Failure.QUARANTINE)
        self._advance(operation, OperationState.RUNNING)
        operation.snapshot = replace(operation.snapshot, simulated_dispatches=1)
        return operation.snapshot

    def receive_candidate(self, candidate: Candidate) -> OperationSnapshot:
        operation = self._operation()
        if operation.snapshot.failure is not None:
            raise ModelError(operation.snapshot.failure)
        valid = type(candidate) is Candidate
        if valid:
            try:
                candidate.__post_init__()
            except ModelError:
                valid = False
        if not valid:
            self._abort(operation, Failure.VALIDATION)
            raise ModelError(Failure.VALIDATION)
        if candidate.operation != operation.request.operation:
            raise ModelError(Failure.GENERATION)
        _require(operation.snapshot.state == OperationState.RUNNING, Failure.STATE)
        if (
            candidate.worker != operation.request.worker
            or candidate.authorization != operation.request.authorization
        ):
            self._abort(operation, Failure.GENERATION)
            raise ModelError(Failure.GENERATION)
        self._advance(operation, OperationState.CANDIDATE_RECEIVED)
        operation.candidate = candidate
        operation.snapshot = replace(operation.snapshot, candidate_ref=candidate.candidate_ref)
        return operation.snapshot

    def begin_validation(self) -> OperationSnapshot:
        operation = self._operation()
        self._advance(operation, OperationState.VALIDATING)
        return operation.snapshot

    def validate_candidate(self) -> OperationSnapshot:
        operation = self._operation()
        if operation.snapshot.failure is not None:
            raise ModelError(operation.snapshot.failure)
        _require(operation.snapshot.state == OperationState.VALIDATING, Failure.STATE)
        candidate = operation.candidate
        if candidate is None or not candidate.complete or not candidate.validated:
            self._abort(operation, Failure.VALIDATION)
            raise ModelError(Failure.VALIDATION)
        self._advance(operation, OperationState.READY_TO_COMMIT)
        return operation.snapshot

    def worker_error(
        self, worker: Identity, category: Failure = Failure.WORKER,
    ) -> OperationSnapshot:
        operation = self._worker_operation(worker)
        _require(type(category) is Failure and category in (
            Failure.WORKER, Failure.PROTOCOL, Failure.TIMEOUT,
        ))
        _require(operation.snapshot.state != OperationState.COMPLETED, Failure.STATE)
        self._abort(operation, category)
        return operation.snapshot

    def request_termination(self) -> OperationSnapshot:
        operation = self._operation()
        _require(operation.snapshot.failure is not None, Failure.STATE)
        self._advance(operation, OperationState.TERMINATION_REQUESTED)
        operation.snapshot = replace(operation.snapshot, termination=TerminationState.REQUESTED)
        return operation.snapshot

    def confirm_exit(self, worker: Identity, *, normal: bool) -> OperationSnapshot:
        operation = self._worker_operation(worker)
        _require(type(normal) is bool)
        snapshot = operation.snapshot
        _require(
            snapshot.state not in (OperationState.ADMITTED, OperationState.NOT_ADMITTED,
                                   OperationState.COMPLETED)
            and snapshot.exit == ExitState.UNCONFIRMED,
            Failure.STATE,
        )
        if not normal or snapshot.state not in (
            OperationState.CANDIDATE_RECEIVED, OperationState.VALIDATING,
            OperationState.READY_TO_COMMIT,
        ):
            self._abort(operation, Failure.WORKER)
        operation.snapshot = replace(
            operation.snapshot, exit=ExitState.NORMAL if normal else ExitState.ABNORMAL,
        )
        return operation.snapshot

    def confirm_reaping(self, worker: Identity, *, succeeded: bool) -> OperationSnapshot:
        operation = self._worker_operation(worker)
        _require(type(succeeded) is bool)
        _require(
            operation.snapshot.exit != ExitState.UNCONFIRMED
            and operation.snapshot.reaping == ReapingState.UNCONFIRMED
            and operation.snapshot.state != OperationState.COMPLETED,
            Failure.STATE,
        )
        if not succeeded:
            self._abort(operation, Failure.DISPOSITION)
        operation.snapshot = replace(
            operation.snapshot,
            reaping=ReapingState.CONFIRMED if succeeded else ReapingState.FAILED,
        )
        return operation.snapshot

    def confirm_disposition(
        self, worker: Identity, disposition: ResourceDisposition,
    ) -> OperationSnapshot:
        operation = self._worker_operation(worker)
        _require(type(disposition) is ResourceDisposition
                 and disposition != ResourceDisposition.UNCONFIRMED)
        snapshot = operation.snapshot
        _require(snapshot.state != OperationState.COMPLETED
                 and snapshot.disposition == ResourceDisposition.UNCONFIRMED, Failure.STATE)
        expected = (
            ResourceDisposition.ABORTED if snapshot.failure is not None
            else ResourceDisposition.RELEASED
        )
        if (
            disposition != expected or snapshot.exit == ExitState.UNCONFIRMED
            or snapshot.reaping != ReapingState.CONFIRMED
        ):
            self._abort(operation, Failure.DISPOSITION)
            disposition = ResourceDisposition.FAILED
        operation.snapshot = replace(operation.snapshot, disposition=disposition)
        return operation.snapshot

    def commit(self) -> OperationSnapshot:
        operation = self._operation()
        snapshot = operation.snapshot
        _require(snapshot.state != OperationState.COMPLETED, Failure.STATE)
        if snapshot.failure is not None:
            raise ModelError(snapshot.failure)
        _require(snapshot.state == OperationState.READY_TO_COMMIT, Failure.STATE)
        if (
            snapshot.exit != ExitState.NORMAL or snapshot.reaping != ReapingState.CONFIRMED
            or snapshot.disposition != ResourceDisposition.RELEASED
            or snapshot.quarantine == QuarantineState.REQUIRED or operation.candidate is None
        ):
            self._abort(operation, Failure.DISPOSITION)
            raise ModelError(Failure.DISPOSITION)
        self._advance(operation, OperationState.COMPLETED)
        operation.snapshot = replace(
            operation.snapshot, committed_ref=operation.candidate.result_ref,
            completed_at=self._ledger._last_now,
        )
        return operation.snapshot

    def quarantine(self) -> OperationSnapshot:
        operation = self._operation()
        _require(operation.snapshot.quarantine == QuarantineState.REQUIRED, Failure.STATE)
        self._advance(operation, OperationState.QUARANTINED)
        return operation.snapshot

    def recover(self, evidence: RecoveryEvidence) -> OperationSnapshot:
        self._owner()
        _require(type(evidence) is RecoveryEvidence)
        evidence.__post_init__()
        _require(evidence.operation in self._ledger._operations, Failure.GENERATION)
        operation = self._ledger._operations[evidence.operation]
        self._observe(operation)
        _require(
            operation.snapshot.quarantine == QuarantineState.REQUIRED
            and evidence.worker == operation.request.worker and evidence.exit_confirmed
            and evidence.reaped and evidence.disposition == ResourceDisposition.ABORTED,
            Failure.QUARANTINE,
        )
        if operation.snapshot.state != OperationState.QUARANTINED:
            self._advance(operation, OperationState.QUARANTINED)
        operation.snapshot = replace(
            operation.snapshot,
            quarantine=QuarantineState.RECOVERED,
            exit=operation.snapshot.exit if operation.snapshot.exit != ExitState.UNCONFIRMED
            else ExitState.CONFIRMED,
            reaping=ReapingState.CONFIRMED, disposition=ResourceDisposition.ABORTED,
        )
        operation.candidate = None
        return operation.snapshot

