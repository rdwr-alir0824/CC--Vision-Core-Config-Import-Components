import ast
import importlib
import json
import struct
import traceback
from dataclasses import FrozenInstanceError, asdict, replace
from pathlib import Path
from unittest.mock import Mock, patch
from uuid import UUID

from offline_support import OfflineTestCase


class WorkerDouble:
    """Only explicit logical events; cannot execute a request or launch a worker."""

    def __init__(self, coordinator):
        self.coordinator = coordinator
        self.events = []

    def ready(self):
        self.events.append("startup")
        self.coordinator.start_worker()
        self.events.append("ready")
        return self.coordinator.worker_ready(self.coordinator.snapshot().worker)

    def run(self):
        self.events.append("running")
        return self.coordinator.dispatch()

    def result(self, candidate):
        self.events.append("candidate")
        return self.coordinator.receive_candidate(candidate)

    def release(self):
        self.events.extend(("exit", "reap", "release"))
        worker = self.coordinator.snapshot().worker
        self.coordinator.confirm_exit(worker, normal=True)
        self.coordinator.confirm_reaping(worker, succeeded=True)
        return self.coordinator.confirm_disposition(
            worker,
            self.coordinator.snapshot().disposition.__class__.RELEASED,
        )


class SupervisedOperationTests(OfflineTestCase):
    cases = 0
    guarded_observations = 0
    guarded_attempts = 0
    dispatch_calls = 0
    accepted_dispatches = 0

    @classmethod
    def tearDownClass(cls):
        print(
            f"\nSUPERVISED_OFFLINE cases={cls.cases} "
            f"guard_observations={cls.guarded_observations} "
            f"network_process_live_dispatch_attempts={cls.guarded_attempts} "
            f"explicit_simulated_dispatch_calls={cls.dispatch_calls} "
            f"accepted_simulated_dispatches={cls.accepted_dispatches}"
        )

    def setUp(self):
        super().setUp()
        self.extra_guards = []
        for target in (
            "ssl.SSLContext.wrap_socket", "ssl.SSLContext.wrap_bio",
            "ssl.SSLSocket.connect", "ssl.SSLObject.do_handshake",
            "subprocess.Popen", "multiprocessing.Process",
            "cc_vision_import.http_backend.StdlibHttpBackend.send",
            "cc_vision_import.transport.HttpTransport.request",
            "cc_vision_import.sessions.SessionManager.authenticate",
            "cc_vision_import.product_clients._ReadClient._read",
        ):
            self.extra_guards.append(self.stack.enter_context(
                patch(target, side_effect=AssertionError("Live dispatch/process is forbidden.")),
            ))
        self.m = importlib.import_module("cc_vision_import.supervised_operations")
        self.clock = Mock(return_value=100.0)
        self._next_ref = 0
        self.ledger = self.m.RecoveryLedger(capacity=16)
        self.c = self.m.Coordinator(self.ledger, clock=self.clock)
        self.spies = []
        self.ledgers = []
        self.spy(self.c)
        self.authorization = self.identity()
        self.c.authorize(self.authorization)
        self.request = self.make_request()
        self.worker = WorkerDouble(self.c)
        self.addCleanup(self.measure)

    def measure(self):
        guards = self.network_guards + self.extra_guards
        cls = type(self)
        cls.cases += 1
        cls.guarded_observations += len(guards)
        cls.guarded_attempts += sum(guard.call_count for guard in guards)
        cls.dispatch_calls += sum(spy.call_count for spy in self.spies)
        cls.accepted_dispatches += sum(
            item.snapshot.simulated_dispatches
            for ledger in self.ledgers for item in ledger._operations.values()
        )
        for guard in guards:
            guard.assert_not_called()

    def spy(self, coordinator):
        spy = Mock(wraps=coordinator.dispatch)
        coordinator.dispatch = spy
        self.spies.append(spy)
        if coordinator._ledger not in self.ledgers:
            self.ledgers.append(coordinator._ledger)

    def ref(self):
        self._next_ref += 1
        return UUID(int=self._next_ref, version=4)

    def identity(self, generation=1):
        return self.m.Identity(self.ref(), generation)

    def make_request(self, generation=1, **overrides):
        return self.m.OperationRequest(**{
            "operation": self.identity(generation),
            "authorization": self.authorization,
            "worker": self.identity(generation),
            "request_ref": self.ref(),
            "timeout": 10.0,
            "admission_expires_at": 200.0,
            **overrides,
        })

    def candidate(self, **overrides):
        return self.m.Candidate(**{
            "operation": self.request.operation,
            "authorization": self.request.authorization,
            "worker": self.request.worker,
            "candidate_ref": self.ref(),
            "result_ref": self.ref(),
            "complete": True, "validated": True,
            **overrides,
        })

    def running(self):
        self.c.admit(self.request)
        self.worker.ready()
        self.worker.run()

    def staged(self):
        self.running()
        candidate = self.candidate()
        self.worker.result(candidate)
        self.c.begin_validation()
        self.c.validate_candidate()
        return candidate

    def evidence(self, **overrides):
        return self.m.RecoveryEvidence(**{
            "operation": self.request.operation, "worker": self.request.worker,
            "evidence_ref": self.ref(), "exit_confirmed": True, "reaped": True,
            "disposition": self.m.ResourceDisposition.ABORTED, **overrides,
        })

    def rejects(self, category, action, *args, **kwargs):
        with self.assertRaises(self.m.ModelError) as caught:
            action(*args, **kwargs)
        self.assertEqual(caught.exception.category, category)
        return caught.exception

    def limits(self, **overrides):
        return self.m.ProtocolLimits(**{
            "request_bytes": 2048, "result_bytes": 2048, "frame_bytes": 4096,
            "aggregate_bytes": 16384, "wire_bytes": 16416,
            "frame_count": 8, "nesting": 4, **overrides,
        })

    def codec(self, **limits):
        return self.m.FrameCodec(self.request, self.m.Deadline(100.0, 110.0),
                                 self.limits(**limits))

    def request_payload(self):
        return {
            "request_ref": str(self.request.request_ref), "admitted_at": 100.0,
            "expires_at": 110.0, "clock_domain": "injected-monotonic",
        }

    def candidate_payload(self):
        candidate = self.candidate()
        return {
            "schema_version": 1, "candidate_ref": str(candidate.candidate_ref),
            "result_ref": str(candidate.result_ref), "complete": True, "validated": True,
        }

    def wire(self, data):
        raw = json.dumps(data, separators=(",", ":")).encode("utf-8")
        return struct.pack("!I", len(raw)) + raw

    def prime(self, codec):
        for kind, payload in (
            (self.m.MessageType.REQUEST, self.request_payload()),
            (self.m.MessageType.READY, {}),
            (self.m.MessageType.PERMIT, {}),
        ):
            codec.decode(self.wire(codec.envelope(kind, payload)))

    def test_normal_admission_completion_and_immutable_success(self):
        candidate = self.staged()
        self.assertEqual(self.c.snapshot().state, self.m.OperationState.READY_TO_COMMIT)
        self.worker.release()
        result = self.c.commit()
        self.assertEqual(result.state, self.m.OperationState.COMPLETED)
        self.assertEqual(result.committed_ref, candidate.result_ref)
        self.assertEqual(result.deadline.expires_at, 110.0)
        self.assertEqual(result.simulated_dispatches, 1)
        self.assertIsNone(result.failure)
        with self.assertRaises(FrozenInstanceError):
            result.state = self.m.OperationState.RUNNING
        self.clock.return_value = 200.0
        self.assertEqual(self.c.snapshot(), result)
        self.rejects(self.m.Failure.STATE, self.c.start_worker)
        self.rejects(self.m.Failure.STATE, self.c.worker_error, self.request.worker)
        self.rejects(self.m.Failure.STATE, self.c.confirm_disposition,
                     self.request.worker, self.m.ResourceDisposition.ABORTED)

    def test_expiry_before_admission_never_starts_worker(self):
        request = replace(self.request, admission_expires_at=100.0)
        snapshot = self.c.admit(request)
        self.assertEqual(snapshot.state, self.m.OperationState.TIMED_OUT)
        self.assertEqual(snapshot.failure, self.m.Failure.TIMEOUT)
        self.rejects(self.m.Failure.TIMEOUT, self.c.start_worker)
        self.c.dispatch.assert_not_called()

    def test_admission_validation_time_uses_original_deadline(self):
        self.clock.side_effect = [100.0, 110.0]
        result = self.c.admit(self.request)
        self.assertEqual(result.failure, self.m.Failure.TIMEOUT)
        self.assertEqual(result.deadline.expires_at, 110.0)

    def test_expiry_during_startup_rejects_ready_and_requests_termination(self):
        self.c.admit(self.request)
        self.c.start_worker()
        self.clock.return_value = 110.0
        self.rejects(self.m.Failure.TIMEOUT, self.c.worker_ready, self.request.worker)
        snapshot = self.c.snapshot()
        self.assertEqual(snapshot.termination, self.m.TerminationState.REQUESTED)
        self.assertEqual(snapshot.exit, self.m.ExitState.UNCONFIRMED)
        self.assertEqual(snapshot.quarantine, self.m.QuarantineState.REQUIRED)

    def test_readiness_does_not_renew_deadline_or_allow_expired_dispatch(self):
        self.c.admit(self.request)
        self.clock.return_value = 109.0
        self.worker.ready()
        self.assertEqual(self.c.snapshot().deadline.expires_at, 110.0)
        self.clock.return_value = 110.0
        self.rejects(self.m.Failure.TIMEOUT, self.worker.run)
        self.assertEqual(self.c.snapshot().simulated_dispatches, 0)
        self.assertEqual(self.c.snapshot().failure, self.m.Failure.TIMEOUT)

    def test_expiry_during_execution_and_late_success(self):
        self.running()
        self.clock.return_value = 110.0
        self.rejects(self.m.Failure.TIMEOUT, self.worker.result, self.candidate())
        self.c.request_termination()
        self.c.quarantine()
        self.rejects(self.m.Failure.TIMEOUT, self.c.commit)
        self.assertEqual(self.c.snapshot().state, self.m.OperationState.QUARANTINED)
        self.assertEqual(self.c.snapshot().failure, self.m.Failure.TIMEOUT)

    def test_expiry_before_commit_discards_candidate(self):
        self.staged()
        self.worker.release()
        self.clock.return_value = 110.0
        self.rejects(self.m.Failure.TIMEOUT, self.c.commit)
        self.assertIsNone(self.c.snapshot().committed_ref)
        self.assertIsNone(self.c.snapshot().candidate_ref)

    def test_final_commit_clock_check_cannot_publish_expired_success(self):
        self.staged()
        self.worker.release()
        self.clock.side_effect = [109.0, 110.0]
        self.rejects(self.m.Failure.TIMEOUT, self.c.commit)
        self.assertEqual(self.c.snapshot().failure, self.m.Failure.TIMEOUT)

    def test_revocation_before_dispatch(self):
        self.c.admit(self.request)
        self.worker.ready()
        self.c.revoke(self.authorization)
        self.rejects(self.m.Failure.AUTHORIZATION, self.worker.run)
        self.assertEqual(self.c.snapshot().failure, self.m.Failure.AUTHORIZATION)
        self.assertEqual(self.c.snapshot().simulated_dispatches, 0)

    def test_revocation_before_commit(self):
        self.staged()
        self.worker.release()
        self.c.revoke(self.authorization)
        self.rejects(self.m.Failure.AUTHORIZATION, self.c.commit)
        self.assertIsNone(self.c.snapshot().committed_ref)

    def test_revoked_authorization_cannot_be_regranted_or_replayed(self):
        self.c.revoke(self.authorization)
        self.rejects(self.m.Failure.GENERATION, self.c.authorize, self.authorization)
        replacement = replace(self.authorization, generation=2)
        self.c.authorize(replacement)
        result = self.c.admit(self.request)
        self.assertEqual(result.failure, self.m.Failure.AUTHORIZATION)
        self.rejects(self.m.Failure.AUTHORIZATION, self.c.revoke, self.authorization)

    def test_superseded_authorization_fences_inflight_dispatch(self):
        self.c.admit(self.request)
        self.worker.ready()
        self.c.authorize(replace(self.authorization, generation=2))
        self.rejects(self.m.Failure.AUTHORIZATION, self.worker.run)
        self.assertEqual(self.c.snapshot().failure, self.m.Failure.AUTHORIZATION)

    def test_stale_candidate_operation_authorization_and_worker_generations(self):
        for name in ("operation", "authorization", "worker"):
            with self.subTest(name=name):
                ledger = self.m.RecoveryLedger(capacity=2)
                coordinator = self.m.Coordinator(ledger, clock=self.clock)
                self.spy(coordinator)
                coordinator.authorize(self.authorization)
                coordinator.admit(self.request)
                worker = WorkerDouble(coordinator)
                worker.ready()
                worker.run()
                identity = getattr(self.request, name)
                candidate = self.candidate(**{name: replace(identity, generation=2)})
                self.rejects(self.m.Failure.GENERATION, worker.result, candidate)
                self.assertIsNone(coordinator.snapshot().committed_ref)

    def test_illegal_state_transitions_and_duplicate_dispatch(self):
        self.rejects(self.m.Failure.STATE, self.c.dispatch)
        self.c.admit(self.request)
        self.rejects(self.m.Failure.STATE, self.c.worker_ready, self.request.worker)
        for action in (self.c.dispatch, self.c.commit,
                       self.c.begin_validation, self.c.validate_candidate):
            self.rejects(self.m.Failure.STATE, action)
        self.worker.ready()
        self.worker.run()
        self.rejects(self.m.Failure.STATE, self.worker.run)
        self.rejects(self.m.Failure.STATE, self.c.admit, self.make_request(2))
        self.assertEqual(self.c.snapshot().simulated_dispatches, 1)

    def test_duplicate_candidate_and_commit_rejected(self):
        candidate = self.staged()
        self.rejects(self.m.Failure.STATE, self.worker.result, candidate)
        self.worker.release()
        completed = self.c.commit()
        self.rejects(self.m.Failure.STATE, self.c.commit)
        self.assertEqual(self.c.snapshot(), completed)

    def test_partial_or_failed_validation_never_commits(self):
        for complete, validated in ((False, True), (True, False), (False, False)):
            with self.subTest(complete=complete, validated=validated):
                coordinator = self.m.Coordinator(
                    self.m.RecoveryLedger(capacity=2), clock=self.clock,
                )
                self.spy(coordinator)
                coordinator.authorize(self.authorization)
                coordinator.admit(self.request)
                worker = WorkerDouble(coordinator)
                worker.ready()
                worker.run()
                worker.result(self.candidate(complete=complete, validated=validated))
                coordinator.begin_validation()
                self.rejects(self.m.Failure.VALIDATION, coordinator.validate_candidate)
                self.rejects(self.m.Failure.VALIDATION, coordinator.commit)

    def test_candidate_schema_checked_at_boundary(self):
        self.running()
        self.rejects(self.m.Failure.VALIDATION, self.worker.result,
                     {"schema_version": 1, "credentials": "sensitive-marker"})
        self.assertEqual(self.c.snapshot().failure, self.m.Failure.VALIDATION)

    def test_worker_error_and_timeout_classification_preservation(self):
        self.running()
        self.c.worker_error(self.request.worker)
        self.clock.return_value = 120.0
        self.c.worker_error(self.request.worker, self.m.Failure.TIMEOUT)
        self.c.request_termination()
        self.c.confirm_exit(self.request.worker, normal=False)
        self.c.confirm_reaping(self.request.worker, succeeded=False)
        self.c.quarantine()
        self.assertEqual(self.c.snapshot().failure, self.m.Failure.WORKER)
        self.assertEqual(self.c.snapshot().reaping, self.m.ReapingState.FAILED)
        self.assertIsNone(self.c.snapshot().committed_ref)

    def test_observed_timeout_precedes_late_worker_error(self):
        self.running()
        self.clock.return_value = 110.0
        self.c.worker_error(self.request.worker)
        self.assertEqual(self.c.snapshot().failure, self.m.Failure.TIMEOUT)

    def test_failed_release_prevents_successful_commit(self):
        self.staged()
        self.c.confirm_exit(self.request.worker, normal=True)
        self.c.confirm_reaping(self.request.worker, succeeded=True)
        self.c.confirm_disposition(self.request.worker, self.m.ResourceDisposition.FAILED)
        self.rejects(self.m.Failure.DISPOSITION, self.c.commit)
        self.assertEqual(self.c.snapshot().quarantine, self.m.QuarantineState.REQUIRED)

    def test_exit_is_not_reaping_or_resource_release(self):
        self.staged()
        self.c.confirm_exit(self.request.worker, normal=True)
        snapshot = self.c.snapshot()
        self.assertEqual(snapshot.reaping, self.m.ReapingState.UNCONFIRMED)
        self.assertEqual(snapshot.disposition, self.m.ResourceDisposition.UNCONFIRMED)
        self.rejects(self.m.Failure.DISPOSITION, self.c.commit)

    def test_reaping_failure_quarantines_even_after_normal_exit(self):
        self.staged()
        self.c.confirm_exit(self.request.worker, normal=True)
        self.c.confirm_reaping(self.request.worker, succeeded=False)
        self.rejects(self.m.Failure.DISPOSITION, self.c.commit)
        self.rejects(self.m.Failure.QUARANTINE, self.c.admit, self.make_request(2))

    def test_termination_request_does_not_confirm_exit(self):
        self.running()
        self.c.worker_error(self.request.worker)
        snapshot = self.c.request_termination()
        self.assertEqual(snapshot.exit, self.m.ExitState.UNCONFIRMED)
        self.assertEqual(snapshot.reaping, self.m.ReapingState.UNCONFIRMED)
        self.rejects(self.m.Failure.STATE, self.c.confirm_reaping,
                     self.request.worker, succeeded=True)
        self.c.quarantine()
        self.rejects(self.m.Failure.QUARANTINE, self.c.admit, self.make_request(2))

    def test_abnormal_exit_after_candidate_is_not_success(self):
        self.staged()
        self.c.confirm_exit(self.request.worker, normal=False)
        self.c.confirm_reaping(self.request.worker, succeeded=True)
        self.c.confirm_disposition(self.request.worker, self.m.ResourceDisposition.ABORTED)
        self.rejects(self.m.Failure.WORKER, self.c.commit)
        self.assertEqual(self.c.snapshot().quarantine, self.m.QuarantineState.REQUIRED)

    def test_successful_release_cannot_substitute_for_abort_disposition(self):
        self.running()
        self.c.worker_error(self.request.worker)
        self.c.confirm_exit(self.request.worker, normal=False)
        self.c.confirm_reaping(self.request.worker, succeeded=True)
        snapshot = self.c.confirm_disposition(
            self.request.worker, self.m.ResourceDisposition.RELEASED,
        )
        self.assertEqual(snapshot.disposition, self.m.ResourceDisposition.FAILED)
        self.assertEqual(snapshot.failure, self.m.Failure.WORKER)

    def test_quarantine_recovery_requires_all_exact_owner_evidence(self):
        self.running()
        self.c.worker_error(self.request.worker)
        self.c.quarantine()
        for changes in (
            {"worker": self.identity(2)}, {"exit_confirmed": False}, {"reaped": False},
            {"disposition": self.m.ResourceDisposition.RELEASED},
            {"disposition": self.m.ResourceDisposition.FAILED},
        ):
            with self.subTest(changes=changes):
                self.rejects(self.m.Failure.QUARANTINE, self.c.recover,
                             self.evidence(**changes))
                self.assertEqual(self.c.snapshot().quarantine, self.m.QuarantineState.REQUIRED)
        self.rejects(self.m.Failure.GENERATION, self.c.recover,
                     self.evidence(operation=self.identity(2)))
        recovered = self.c.recover(self.evidence())
        self.assertEqual(recovered.quarantine, self.m.QuarantineState.RECOVERED)
        self.assertEqual(recovered.failure, self.m.Failure.WORKER)
        self.rejects(self.m.Failure.WORKER, self.c.commit)
        self.rejects(self.m.Failure.QUARANTINE, self.c.recover, self.evidence())
        self.c.admit(self.make_request(2))
        self.worker.ready()
        self.worker.run()
        self.assertEqual(self.c.snapshot().simulated_dispatches, 1)

    def test_generation_and_identity_reuse_prohibited_after_recovery(self):
        self.running()
        self.c.worker_error(self.request.worker)
        self.c.recover(self.evidence())
        for request in (
            self.request, self.make_request(1),
            self.make_request(2, operation=replace(self.request.operation, generation=2)),
            self.make_request(2, worker=replace(self.request.worker, generation=2)),
        ):
            self.rejects(self.m.Failure.GENERATION, self.c.admit, request)

    def test_replacement_preserves_unresolved_quarantine_and_fences_old_owner(self):
        self.running()
        self.c.worker_error(self.request.worker)
        replacement = self.m.Coordinator(self.ledger, clock=self.clock)
        self.spy(replacement)
        self.rejects(self.m.Failure.OWNERSHIP, self.c.snapshot)
        self.rejects(self.m.Failure.OWNERSHIP, self.c.dispatch)
        self.rejects(self.m.Failure.QUARANTINE, replacement.admit, self.make_request(2))
        self.assertEqual(replacement.snapshot(self.request.operation).failure, self.m.Failure.WORKER)
        replacement.recover(self.evidence())
        replacement.admit(self.make_request(2))
        WorkerDouble(replacement).ready()
        replacement.dispatch()

    def test_replacement_of_running_supervisor_creates_quarantine(self):
        self.running()
        replacement = self.m.Coordinator(self.ledger, clock=self.clock)
        snapshot = replacement.snapshot(self.request.operation)
        self.assertEqual(snapshot.failure, self.m.Failure.OWNERSHIP)
        self.assertEqual(snapshot.quarantine, self.m.QuarantineState.REQUIRED)
        self.rejects(self.m.Failure.QUARANTINE, replacement.admit, self.make_request(2))
        self.rejects(self.m.Failure.OWNERSHIP, self.worker.result, self.candidate())

    def test_registry_capacity_never_evicts_required_history(self):
        ledger = self.m.RecoveryLedger(capacity=1)
        coordinator = self.m.Coordinator(ledger, clock=self.clock)
        self.spy(coordinator)
        coordinator.authorize(self.authorization)
        self.rejects(self.m.Failure.CAPACITY, coordinator.authorize, self.identity())
        coordinator.admit(replace(self.request, admission_expires_at=100))
        self.rejects(self.m.Failure.CAPACITY, coordinator.admit, self.make_request(2))

    def test_invalid_and_backward_clocks_fail_closed_without_secret_tracebacks(self):
        self.running()
        for value in (True, float("nan"), float("inf"), "sensitive-marker", 99.0):
            self.clock.return_value = value
            self.rejects(self.m.Failure.CLOCK, self.c._now)
        self.clock.side_effect = RuntimeError("sensitive-marker")
        error = self.rejects(self.m.Failure.CLOCK, self.c.snapshot)
        text = "".join(traceback.format_exception(error))
        self.assertNotIn("sensitive-marker", text)
        self.clock.side_effect = None
        self.clock.return_value = 100.0
        self.assertEqual(self.c.snapshot().failure, self.m.Failure.CLOCK)
        self.assertEqual(self.c.snapshot().quarantine, self.m.QuarantineState.REQUIRED)

    def test_contracts_reject_wrong_versions_types_and_unbounded_values(self):
        for changes in (
            {"schema_version": True}, {"schema_version": 2}, {"generation": True},
            {"generation": 0}, {"reference": "native-controller-1"},
        ):
            self.rejects(self.m.Failure.CONTRACT, replace, self.authorization, **changes)
        for changes in (
            {"timeout": 0}, {"timeout": float("inf")}, {"timeout": True},
            {"timeout": 301}, {"admission_expires_at": float("nan")},
            {"request_ref": "sensitive-marker"}, {"operation": {}},
        ):
            self.rejects(self.m.Failure.CONTRACT, replace, self.request, **changes)
        for changes in ({"schema_version": 2}, {"complete": 1}, {"validated": "yes"}):
            self.rejects(self.m.Failure.CONTRACT, self.candidate, **changes)

    def test_sanitized_snapshots_and_no_retry_authentication_or_write_replay(self):
        self.running()
        self.c.worker_error(self.request.worker)
        for _ in range(3):
            self.c.snapshot()
        self.c.dispatch.assert_called_once_with()
        self.assertEqual(self.worker.events, ["startup", "ready", "running"])
        snapshot = self.c.snapshot()
        self.assertEqual(snapshot.simulated_dispatches, 1)
        report = repr(asdict(snapshot))
        for forbidden in ("password", "credentials", "cookie", "token", "sensitive-marker"):
            self.assertNotIn(forbidden, report)
        self.assertIsNone(snapshot.committed_ref)
        self.rejects(self.m.Failure.WORKER, self.c.start_worker)

    def test_prototype_imports_no_application_network_or_process_modules(self):
        tree = ast.parse(Path(self.m.__file__).read_text(encoding="utf-8"))
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                self.assertEqual(node.level, 0)
                imported.add(node.module)
        self.assertLessEqual(imported, {
            "json", "math", "struct", "collections.abc", "dataclasses", "enum", "uuid",
        })
        root = Path(self.m.__file__).parent
        for name in ("__init__.py", "__main__.py", "cli.py", "transport.py",
                     "http_backend.py", "sessions.py", "authentication.py", "product_clients.py"):
            self.assertNotIn("supervised_operations", (root / name).read_text(encoding="utf-8"))

    def test_ipc_round_trip_network_order_frozen_payload_and_defensive_copy(self):
        sender, receiver = self.codec(), self.codec()
        payload = self.request_payload()
        request = sender.envelope(self.m.MessageType.REQUEST, payload)
        payload["request_ref"] = "mutated"
        wire = sender.encode(request)
        self.assertEqual(struct.unpack("!I", wire[:4])[0], len(wire) - 4)
        frame = receiver.decode(wire)
        self.assertEqual(frame.kind, self.m.MessageType.REQUEST)
        self.assertEqual(dict(frame.payload)["request_ref"], str(self.request.request_ref))
        for kind, payload in (
            (self.m.MessageType.READY, {}), (self.m.MessageType.PERMIT, {}),
            (self.m.MessageType.CANDIDATE,
             {**self.candidate_payload(), "evidence_ref": str(self.ref())}),
        ):
            envelope = sender.envelope(kind, payload)
            frame = receiver.decode(sender.encode(envelope))
            self.assertEqual(frame.kind, kind)
        self.assertIsInstance(frame.payload, tuple)
        with self.assertRaises(FrozenInstanceError):
            frame.sequence = 20
        self.rejects(self.m.Failure.PROTOCOL, receiver.decode, wire)

    def test_ipc_malformed_truncated_and_oversized_frames(self):
        for wire in (
            b"", b"\x00", b"\x00\x00\x00", struct.pack("!I", 0),
            struct.pack("!I", 4097), struct.pack("!I", 2) + b"{",
            struct.pack("!I", 1) + b"{}",
            struct.pack("!I", 1) + b"{",
            struct.pack("!I", 5000) + b" " * 5000,
            struct.pack("!I", 2**32 - 1),
        ):
            with self.subTest(wire_length=len(wire)):
                self.rejects(self.m.Failure.PROTOCOL, self.codec().decode, wire)

    def test_ipc_invalid_utf8_json_values_and_excessive_nesting(self):
        for raw in (
            b"\xff", b"[]", b"null", b"true", b"42", b'"text"', b"NaN", b"Infinity",
            b'{"a":NaN}', b'{"a":1e9999}', b"[[[[[0]]]]]",
            b'{"a":"unterminated}', b'{"a":1} trailing',
        ):
            with self.subTest(raw=raw):
                self.rejects(self.m.Failure.PROTOCOL, self.codec().decode,
                             struct.pack("!I", len(raw)) + raw)

    def test_ipc_duplicate_and_unknown_fields_at_both_levels(self):
        codec = self.codec()
        data = codec.envelope(self.m.MessageType.REQUEST, self.request_payload())
        valid = self.wire(data)[4:]
        for raw in (
            valid.replace(b'"version":1', b'"version":1,"version":1'),
            valid.replace(b'"clock_domain":', b'"clock_domain":"injected-monotonic","clock_domain":'),
        ):
            self.rejects(self.m.Failure.PROTOCOL, self.codec().decode,
                         struct.pack("!I", len(raw)) + raw)
        for mutation in (
            {**data, "raw_credentials": "sensitive-marker"},
            {**data, "payload": {**self.request_payload(), "cookies": "sensitive-marker"}},
            {key: value for key, value in data.items() if key != "worker_id"},
            {**data, "payload": {}},
        ):
            self.rejects(self.m.Failure.PROTOCOL, self.codec().decode, self.wire(mutation))

    def test_ipc_version_sequence_and_identity_mismatches(self):
        codec = self.codec()
        data = codec.envelope(self.m.MessageType.REQUEST, self.request_payload())
        for key, value in (
            ("version", 2), ("version", True), ("sequence", 0), ("sequence", 2),
            ("sequence", True), ("operation_generation", 2),
            ("worker_generation", 2), ("authorization_generation", 2),
            ("operation_id", str(self.ref())), ("worker_id", str(self.ref())),
            ("authorization_id", str(self.ref())), ("type", "execute_code"),
        ):
            with self.subTest(key=key, value=value):
                self.rejects(self.m.Failure.PROTOCOL, self.codec().decode,
                             self.wire({**data, key: value}))

    def test_ipc_order_and_duplicate_terminal_messages(self):
        for kind in (self.m.MessageType.READY, self.m.MessageType.PERMIT,
                     self.m.MessageType.CANDIDATE):
            codec = self.codec()
            self.rejects(self.m.Failure.PROTOCOL, codec.decode,
                         self.wire(codec.envelope(kind, {})))
        codec = self.codec()
        self.prime(codec)
        data = codec.envelope(self.m.MessageType.CANDIDATE, self.candidate_payload())
        codec.decode(self.wire(data))
        self.rejects(self.m.Failure.PROTOCOL, codec.decode,
                     self.wire(codec.envelope(self.m.MessageType.CANDIDATE, self.candidate_payload())))

    def test_ipc_failure_and_cancellation_are_terminal_not_retry(self):
        for kind in (self.m.MessageType.FAILURE, self.m.MessageType.CANCEL):
            codec = self.codec()
            codec.decode(self.wire(codec.envelope(self.m.MessageType.REQUEST, self.request_payload())))
            codec.decode(self.wire(codec.envelope(kind, {"category": self.m.Failure.TIMEOUT.value})))
            self.rejects(self.m.Failure.PROTOCOL, codec.decode,
                         self.wire(codec.envelope(self.m.MessageType.READY, {})))

    def test_ipc_encoder_rejects_unsupported_python_values_without_serializing(self):
        for value in (b"bytes", object(), ("tuple",), [], {}, None, float("nan"),
                      float("inf"), 1, "sensitive-marker"):
            codec = self.codec()
            self.prime(codec)
            payload = {**self.candidate_payload(), "complete": value}
            error = self.rejects(self.m.Failure.PROTOCOL, codec.encode,
                                 codec.envelope(self.m.MessageType.CANDIDATE, payload))
            self.assertNotIn("sensitive-marker", "".join(traceback.format_exception(error)))

    def test_ipc_request_result_and_frame_limits_exact_boundaries(self):
        initial = self.codec()
        data = initial.envelope(self.m.MessageType.REQUEST, self.request_payload())
        size = len(self.wire(data)) - 4
        self.codec(request_bytes=size).decode(self.wire(data))
        self.rejects(self.m.Failure.PROTOCOL, self.codec(request_bytes=size - 1).decode,
                     self.wire(data))
        self.codec(request_bytes=size, result_bytes=size, frame_bytes=size).decode(self.wire(data))
        self.rejects(self.m.Failure.PROTOCOL,
                     self.codec(request_bytes=size - 1, result_bytes=size - 1, frame_bytes=size - 1).decode,
                     self.wire(data))
        codec = self.codec()
        self.prime(codec)
        candidate = codec.envelope(self.m.MessageType.CANDIDATE, self.candidate_payload())
        size = len(self.wire(candidate)) - 4
        exact = self.codec(result_bytes=size)
        self.prime(exact)
        exact.decode(self.wire(candidate))
        below = self.codec(result_bytes=size - 1)
        self.prime(below)
        self.rejects(self.m.Failure.PROTOCOL, below.decode, self.wire(candidate))

    def test_ipc_aggregate_payload_and_prefix_bytes_are_both_charged(self):
        template = self.codec()
        self.prime(template)
        candidate = template.envelope(self.m.MessageType.CANDIDATE, self.candidate_payload())
        size = len(self.wire(candidate)) - 4
        aggregate = template._payload_bytes + size
        wire = template._wire_bytes + size + 4
        for changes, accepted in (
            ({"aggregate_bytes": aggregate}, True),
            ({"aggregate_bytes": aggregate - 1}, False),
            ({"wire_bytes": wire}, True), ({"wire_bytes": wire - 1}, False),
        ):
            with self.subTest(changes=changes):
                codec = self.codec(request_bytes=1024, result_bytes=1024,
                                   frame_bytes=1024, **changes)
                self.prime(codec)
                if accepted:
                    codec.decode(self.wire(candidate))
                else:
                    self.rejects(self.m.Failure.PROTOCOL, codec.decode, self.wire(candidate))

    def test_ipc_frame_count_and_nesting_limits(self):
        codec = self.codec(frame_count=3)
        self.prime(codec)
        self.rejects(self.m.Failure.PROTOCOL, codec.decode,
                     self.wire(codec.envelope(self.m.MessageType.CANDIDATE, self.candidate_payload())))
        codec = self.codec(nesting=1)
        self.rejects(self.m.Failure.PROTOCOL, codec.decode,
                     self.wire(codec.envelope(self.m.MessageType.REQUEST, self.request_payload())))
        codec = self.codec(nesting=2)
        self.prime(codec)

    def test_ipc_invalid_limits_rejected_before_use(self):
        for changes in (
            {"request_bytes": 0}, {"result_bytes": True}, {"frame_bytes": 65537},
            {"aggregate_bytes": 262145}, {"wire_bytes": 262273},
            {"frame_count": 33}, {"nesting": 9}, {"nesting": 0},
            {"request_bytes": 4097}, {"wire_bytes": 4096},
        ):
            self.rejects(self.m.Failure.CONTRACT, self.limits, **changes)

    def test_ipc_rejection_poisoning_prevents_reuse(self):
        codec = self.codec()
        valid = codec.envelope(self.m.MessageType.REQUEST, self.request_payload())
        self.rejects(self.m.Failure.PROTOCOL, codec.decode, b"bad")
        self.rejects(self.m.Failure.PROTOCOL, codec.decode, self.wire(valid))
        self.rejects(self.m.Failure.PROTOCOL, codec.encode, valid)

    def test_ipc_deadline_is_bound_and_cannot_be_renewed(self):
        codec = self.codec()
        payload = {**self.request_payload(), "admitted_at": 200.0, "expires_at": 210.0}
        self.rejects(self.m.Failure.PROTOCOL, codec.decode,
                     self.wire(codec.envelope(self.m.MessageType.REQUEST, payload)))
        request = replace(self.request, timeout=0.1)
        deadline = self.m.Deadline(100.0, 100.1)
        codec = self.m.FrameCodec(request, deadline, self.limits())
        payload = {**self.request_payload(), "expires_at": 100.1}
        codec.decode(self.wire(codec.envelope(self.m.MessageType.REQUEST, payload)))
        self.rejects(self.m.Failure.CONTRACT, self.m.FrameCodec, request,
                     self.m.Deadline(100.0, 101.0), self.limits())

    def test_clock_failure_at_admission_and_final_commit_retires_operation(self):
        self.clock.side_effect = [100.0, RuntimeError("sensitive-clock")]
        self.rejects(self.m.Failure.CLOCK, self.c.admit, self.request)
        self.assertEqual(self.c.snapshot().failure, self.m.Failure.CLOCK)
        self.clock.side_effect = None
        self.clock.return_value = 100.0
        self.request = self.make_request(2)
        self.staged()
        self.worker.release()
        self.clock.side_effect = [100.0, RuntimeError("sensitive-clock")]
        error = self.rejects(self.m.Failure.CLOCK, self.c.commit)
        self.assertNotIn("sensitive-clock", "".join(traceback.format_exception(error)))
        self.assertEqual(self.c.snapshot().failure, self.m.Failure.CLOCK)
        self.assertIsNone(self.c.snapshot().committed_ref)

    def test_replacement_observes_expiry_without_overwriting_timeout(self):
        self.running()
        self.clock.return_value = 110.0
        replacement = self.m.Coordinator(self.ledger, clock=self.clock)
        snapshot = replacement.snapshot(self.request.operation)
        self.assertEqual(snapshot.failure, self.m.Failure.TIMEOUT)
        self.assertEqual(snapshot.termination, self.m.TerminationState.REQUESTED)

    def test_decoded_candidate_scope_survives_through_logical_commit(self):
        self.running()
        codec = self.codec()
        self.prime(codec)
        frame = codec.decode(self.wire(codec.envelope(
            self.m.MessageType.CANDIDATE, self.candidate_payload(),
        )))
        payload = dict(frame.payload)
        candidate = self.m.Candidate(
            frame.operation, frame.authorization, frame.worker,
            UUID(payload["candidate_ref"]), UUID(payload["result_ref"]),
            payload["complete"], payload["validated"], payload["schema_version"],
        )
        self.worker.result(candidate)
        self.c.begin_validation()
        self.c.validate_candidate()
        self.worker.release()
        self.assertEqual(self.c.commit().committed_ref, candidate.result_ref)

    def test_retired_worker_evidence_cannot_change_replacement_operation(self):
        self.running()
        old_candidate = self.candidate()
        old_worker = self.request.worker
        self.c.worker_error(old_worker)
        self.c.recover(self.evidence())
        self.request = self.make_request(2)
        self.staged()
        before = self.c.snapshot()
        for action, args, kwargs in (
            (self.c.worker_ready, (old_worker,), {}),
            (self.c.worker_error, (old_worker,), {}),
            (self.c.confirm_exit, (old_worker,), {"normal": True}),
            (self.c.confirm_reaping, (old_worker,), {"succeeded": True}),
            (self.c.confirm_disposition, (old_worker, self.m.ResourceDisposition.RELEASED), {}),
            (self.c.receive_candidate, (old_candidate,), {}),
        ):
            self.rejects(self.m.Failure.GENERATION, action, *args, **kwargs)
            self.assertEqual(self.c.snapshot(), before)
        self.rejects(self.m.Failure.DISPOSITION, self.c.commit)

    def test_expiry_during_validation_preserves_timeout_classification(self):
        self.running()
        self.worker.result(self.candidate())
        self.c.begin_validation()
        self.clock.return_value = 110.0
        self.rejects(self.m.Failure.TIMEOUT, self.c.validate_candidate)
        snapshot = self.c.snapshot()
        self.assertEqual(snapshot.failure, self.m.Failure.TIMEOUT)
        self.assertIsNone(snapshot.committed_ref)
        self.assertEqual(snapshot.termination, self.m.TerminationState.REQUESTED)

    def test_abort_before_worker_start_never_requests_physical_termination(self):
        self.c.admit(self.request)
        self.clock.return_value = 110.0
        self.rejects(self.m.Failure.TIMEOUT, self.c.start_worker)
        snapshot = self.c.snapshot()
        self.assertEqual(snapshot.termination, self.m.TerminationState.NOT_REQUESTED)
        self.assertEqual(snapshot.quarantine, self.m.QuarantineState.CLEAR)
        self.assertEqual(snapshot.simulated_dispatches, 0)

    def test_ipc_ready_sequence_replay_and_unknown_candidate_fields(self):
        codec = self.codec()
        codec.decode(self.wire(codec.envelope(self.m.MessageType.REQUEST, self.request_payload())))
        ready = codec.envelope(self.m.MessageType.READY, {})
        codec.decode(self.wire(ready))
        self.rejects(self.m.Failure.PROTOCOL, codec.decode, self.wire(ready))
        codec = self.codec()
        self.prime(codec)
        payload = {**self.candidate_payload(), "raw_body": "sensitive-marker"}
        self.rejects(self.m.Failure.PROTOCOL, codec.decode,
                     self.wire(codec.envelope(self.m.MessageType.CANDIDATE, payload)))

    def test_ipc_encoder_applies_the_same_exact_byte_budgets_as_decoder(self):
        template = self.codec()
        data = template.envelope(self.m.MessageType.REQUEST, self.request_payload())
        size = len(self.wire(data)) - 4
        self.codec(request_bytes=size).encode(data)
        codec = self.codec(request_bytes=size - 1)
        self.rejects(self.m.Failure.PROTOCOL, codec.encode, data)
        self.rejects(self.m.Failure.PROTOCOL, codec.encode, data)

    def test_reentrant_admission_reserves_slot_before_clock_callbacks(self):
        for trigger in (1, 2):
            with self.subTest(clock_call=trigger):
                ledger = self.m.RecoveryLedger(capacity=4)
                nested = self.make_request(2)
                calls, errors = 0, []

                def clock():
                    nonlocal calls
                    calls += 1
                    if calls == trigger:
                        try:
                            coordinator.admit(nested)
                            coordinator.start_worker()
                            coordinator.worker_ready(nested.worker)
                            coordinator.dispatch()
                        except self.m.ModelError as error:
                            errors.append(error.category)
                    return 100.0

                coordinator = self.m.Coordinator(ledger, clock=clock)
                self.spy(coordinator)
                coordinator.authorize(self.authorization)
                result = coordinator.admit(self.request)
                self.assertEqual(errors, [self.m.Failure.STATE])
                self.assertEqual(result.state, self.m.OperationState.ADMITTED)
                self.assertEqual(coordinator.snapshot().operation, self.request.operation)
                self.assertEqual(len(ledger._operations), 1)
                self.assertEqual(
                    sum(item.snapshot.state in self.m._ACTIVE
                        for item in ledger._operations.values()), 1,
                )
                coordinator.dispatch.assert_not_called()

    def test_failed_reentrant_clock_releases_reservation_without_active_work(self):
        ledger = self.m.RecoveryLedger(capacity=4)
        nested = self.make_request(2)
        calls = 0

        def clock():
            nonlocal calls
            calls += 1
            if calls == 2:
                try:
                    coordinator.admit(nested)
                finally:
                    raise RuntimeError("sensitive-reentrant-clock")
            return 100.0

        coordinator = self.m.Coordinator(ledger, clock=clock)
        self.spy(coordinator)
        coordinator.authorize(self.authorization)
        error = self.rejects(self.m.Failure.CLOCK, coordinator.admit, self.request)
        self.assertNotIn("sensitive-reentrant-clock", "".join(traceback.format_exception(error)))
        self.assertEqual(coordinator.snapshot().operation, self.request.operation)
        self.assertEqual(coordinator.snapshot().failure, self.m.Failure.CLOCK)
        self.assertFalse(any(item.snapshot.state in self.m._ACTIVE
                             for item in ledger._operations.values()))
        self.assertEqual(coordinator.admit(nested).state, self.m.OperationState.ADMITTED)
        coordinator.dispatch.assert_not_called()

    def test_replacement_during_admission_clock_fences_inflight_supervisor(self):
        for trigger in (1, 2):
            with self.subTest(clock_call=trigger):
                ledger = self.m.RecoveryLedger(capacity=4)
                nested = self.make_request(2)
                calls, replacements, errors = 0, [], []

                def clock():
                    nonlocal calls
                    calls += 1
                    if calls == trigger:
                        replacements.append(self.m.Coordinator(ledger, clock=clock))
                        try:
                            replacements[0].admit(nested)
                        except self.m.ModelError as error:
                            errors.append(error.category)
                    return 100.0

                coordinator = self.m.Coordinator(ledger, clock=clock)
                self.spy(coordinator)
                coordinator.authorize(self.authorization)
                self.rejects(self.m.Failure.OWNERSHIP, coordinator.admit, self.request)
                self.assertEqual(errors, [self.m.Failure.STATE])
                replacement = replacements[0]
                self.spy(replacement)
                self.rejects(self.m.Failure.OWNERSHIP, coordinator.start_worker)
                self.rejects(self.m.Failure.OWNERSHIP, coordinator.commit)
                self.assertFalse(any(item.snapshot.state in self.m._ACTIVE
                                     for item in ledger._operations.values()))
                if trigger == 2:
                    snapshot = replacement.snapshot(self.request.operation)
                    self.assertEqual(snapshot.failure, self.m.Failure.OWNERSHIP)
                    self.assertEqual(snapshot.state, self.m.OperationState.FAILED)
                self.assertEqual(
                    replacement.admit(nested).state, self.m.OperationState.ADMITTED,
                )

    def test_authorization_generation_is_rechecked_after_admission_clock(self):
        ledger = self.m.RecoveryLedger(capacity=4)
        calls = 0

        def clock():
            nonlocal calls
            calls += 1
            if calls == 2:
                coordinator.authorize(replace(self.authorization, generation=2))
            return 100.0

        coordinator = self.m.Coordinator(ledger, clock=clock)
        self.spy(coordinator)
        coordinator.authorize(self.authorization)
        result = coordinator.admit(self.request)
        self.assertEqual(result.failure, self.m.Failure.AUTHORIZATION)
        self.assertEqual(result.state, self.m.OperationState.FAILED)
        self.rejects(self.m.Failure.AUTHORIZATION, coordinator.start_worker)
        self.assertIsNone(result.committed_ref)
        coordinator.dispatch.assert_not_called()

    def test_replacement_during_commit_clock_cannot_publish_stale_success(self):
        self.staged()
        self.worker.release()
        replacements = []

        def clock():
            replacements.append(self.m.Coordinator(
                self.ledger, clock=Mock(return_value=100.0),
            ))
            return 100.0

        self.clock.side_effect = clock
        self.rejects(self.m.Failure.OWNERSHIP, self.c.commit)
        snapshot = replacements[0].snapshot(self.request.operation)
        self.assertEqual(snapshot.failure, self.m.Failure.OWNERSHIP)
        self.assertEqual(snapshot.state, self.m.OperationState.FAILED)
        self.assertEqual(snapshot.quarantine, self.m.QuarantineState.REQUIRED)
        self.assertIsNone(snapshot.committed_ref)
        self.rejects(self.m.Failure.OWNERSHIP, self.c.commit)

    def retarget_during_clock(self, action, *, trigger=1, failure=None, clock_error=False):
        self.clock.side_effect = None
        self.clock.return_value = 100.0
        self.ledger = self.m.RecoveryLedger(capacity=4)
        self.c = self.m.Coordinator(self.ledger, clock=self.clock)
        self.spy(self.c)
        self.c.authorize(self.authorization)
        self.worker = WorkerDouble(self.c)
        self.request = self.make_request()
        if action == "commit":
            self.staged()
            self.worker.release()
        else:
            self.c.admit(self.request)
            self.worker.ready()
        original = self.request
        evidence = self.evidence()
        replacement = self.make_request(2)
        outer_action = getattr(self.c, action)
        failure = self.m.Failure.WORKER if failure is None else failure
        calls, replacements = 0, []

        def clock():
            nonlocal calls
            calls += 1
            if calls == trigger:
                self.clock.side_effect = None
                if failure == self.m.Failure.TIMEOUT:
                    self.clock.return_value = 110.0
                    self.c.worker_error(original.worker)
                elif failure == self.m.Failure.AUTHORIZATION:
                    self.c.revoke(self.authorization)
                    self.authorization = replace(
                        self.authorization, generation=self.authorization.generation + 1,
                    )
                    self.c.authorize(self.authorization)
                elif failure == self.m.Failure.OWNERSHIP:
                    self.c = self.m.Coordinator(self.ledger, clock=self.clock)
                    self.spy(self.c)
                    self.worker = WorkerDouble(self.c)
                else:
                    self.c.worker_error(original.worker)
                self.c.recover(evidence)
                self.request = replace(replacement, authorization=self.authorization)
                if action == "commit":
                    self.staged()
                    self.worker.release()
                else:
                    self.c.admit(self.request)
                    self.worker.ready()
                replacements.append(self.c.snapshot())
                if clock_error:
                    raise RuntimeError("sensitive-retarget-clock")
            return self.clock.return_value

        self.clock.side_effect = clock
        expected = self.m.Failure.CLOCK if clock_error else failure
        error = self.rejects(expected, outer_action)
        self.assertNotIn("sensitive-retarget-clock", "".join(traceback.format_exception(error)))
        self.assertEqual(len(replacements), 1)
        self.assertEqual(self.c.snapshot(), replacements[0])
        self.assertEqual(self.c.snapshot().operation, self.request.operation)
        self.assertIsNone(self.c.snapshot().committed_ref)
        retired = self.c.snapshot(original.operation)
        self.assertEqual(retired.failure, failure)
        self.assertEqual(retired.quarantine, self.m.QuarantineState.RECOVERED)
        self.assertIsNone(retired.committed_ref)
        self.assertFalse(self.ledger._admission_reserved)
        self.assertEqual(
            sum(item.snapshot.state in self.m._ACTIVE for item in self.ledger._operations.values()),
            1,
        )

    def test_dispatch_callback_cannot_retarget_recovered_operation(self):
        for trigger in (1, 2):
            with self.subTest(clock_call=trigger):
                self.retarget_during_clock("dispatch", trigger=trigger)
                self.assertEqual(self.c.snapshot().state, self.m.OperationState.READY)
                self.assertEqual(self.c.snapshot().simulated_dispatches, 0)
                self.assertEqual(self.c.dispatch.call_count, 1)
                result = self.worker.run()
                self.assertEqual(result.operation, self.request.operation)
                self.assertEqual(result.simulated_dispatches, 1)

    def test_commit_callback_cannot_retarget_recovered_operation(self):
        for trigger in (1, 2):
            with self.subTest(clock_call=trigger):
                self.retarget_during_clock("commit", trigger=trigger)
                self.assertEqual(self.c.snapshot().state, self.m.OperationState.READY_TO_COMMIT)
                result = self.c.commit()
                self.assertEqual(result.operation, self.request.operation)
                self.assertEqual(result.state, self.m.OperationState.COMPLETED)
                self.assertIsNotNone(result.committed_ref)

    def test_retargeting_clock_exception_preserves_original_failure_and_recovery(self):
        for action in ("dispatch", "commit"):
            for trigger in (1, 2):
                with self.subTest(action=action, clock_call=trigger):
                    self.retarget_during_clock(action, trigger=trigger, clock_error=True)

    def test_deadline_authorization_and_owner_callbacks_cannot_retarget_actions(self):
        for action in ("dispatch", "commit"):
            for trigger in (1, 2):
                for failure in (
                    self.m.Failure.TIMEOUT, self.m.Failure.AUTHORIZATION, self.m.Failure.OWNERSHIP,
                ):
                    with self.subTest(action=action, clock_call=trigger, failure=failure):
                        self.retarget_during_clock(action, trigger=trigger, failure=failure)

    def test_current_snapshot_callback_cannot_switch_to_recovered_replacement(self):
        self.retarget_during_clock("snapshot")
        self.assertEqual(self.c.snapshot().state, self.m.OperationState.READY)
        self.assertEqual(self.c.snapshot().simulated_dispatches, 0)
