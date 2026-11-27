"""Read-only assessment of bound historical Site attempts; never resets guards."""

import hashlib
import os
import sys
from pathlib import Path
from urllib.parse import urlsplit
from uuid import uuid4

from ._json import load_json
from .authentication import AuthenticationError, CredentialReference, SessionRole
from .backup_inventory import InventoryLimits, discover_backup
from .contracts import ContractValidationError, ExitStatus
from .destination_discovery import DiscoveryProfile, _Credentials, _DiscoveryAuthentication, _UnknownVersionRequest, _TREE
from .migration import _context, _organization, _read_state
from .sessions import SessionManager
from .site_comparison import _destination
from .single_site import (
    SiteBlocked, _close_backend, _get, _json, _lookup_candidate, _name, _parent_in_tree,
    _require, _segments, _site_object, _site_parent_matches, _tree, site_attempt_guard,
)
from .site_migration import (
    BatchSiteBackend, _fresh_root, _journal_context, _origin_lock, _private_descriptor,
    _read_journal, _row_id, _write_private, load_plan,
)
from .tls_policy import execution_tls, require_execution_exception, warning
from .transport import TransportError


_BLOCKERS = {
    "organization_enumeration_completeness_unqualified":
        "Qualify complete, unfiltered Organization enumeration for the destination release/account, including pagination and lazy children.",
    "site_by_id_absence_contract_unqualified":
        "Qualify definitive absence semantics for the exact Site-by-ID GET; an HTTP miss alone is insufficient.",
    "prior_operation_settlement_contract_unqualified":
        "Establish that each historical POST is settled and cannot create an object after the assessment.",
}


class _RecoveryBackend(BatchSiteBackend):
    def _select_read_scope(self, selection) -> None:
        super()._select_read_scope(selection)
        self.candidate_http_status = None

    def send(self, request):
        response = super().send(request)
        if request.url == self._candidate_lookup_url:
            self.candidate_http_status = response.status
        return response

    def arm_create(self) -> None:
        raise SiteBlocked("recovery_configuration_writes_prohibited")


def _protected_json(path: Path) -> dict:
    with os.fdopen(_private_descriptor(path, os.O_RDONLY), "r", encoding="utf-8") as stream:
        _require(os.fstat(stream.fileno()).st_size <= 16 * 1024 * 1024, "recovery_evidence_size_limit")
        try:
            value = load_json(stream.read())
        except (UnicodeError, ValueError, RecursionError):
            raise SiteBlocked("recovery_evidence_malformed") from None
    _require(isinstance(value, dict), "recovery_evidence_malformed")
    return value


def _origin(url: str) -> list:
    parsed = urlsplit(url)
    return [parsed.scheme, parsed.hostname, parsed.port or 443]


def _guard(profile, selection, plan) -> bool:
    path = site_attempt_guard(profile, selection)
    if not path.exists():
        return False
    guard = _protected_json(path)
    _require(set(guard) == {"source_reference", "state", "report_file"}
             and guard["source_reference"] == selection.reference
             and guard["state"] == "reserved-reconcile-before-reuse", "recovery_guard_invalid")
    filename = guard["report_file"]
    _require(isinstance(filename, str) and filename not in ("", ".", "..")
             and Path(filename).name == filename and "/" not in filename and "\\" not in filename,
             "recovery_guard_report_path_invalid")
    evidence = _protected_json(profile.output_directory / filename)
    _require(isinstance(evidence.get("target_origin"), str)
             and _origin(evidence["target_origin"]) == _origin(profile.transport.base_url),
             "recovery_guard_destination_binding_mismatch")
    if evidence.get("domain") == "site-batch-migration-report":
        matches = evidence.get("input_bindings") == plan.binding and evidence.get("plan_sha256") == plan.digest
    else:
        matches = (
            evidence.get("domain") == "single-site-migration-report"
            and evidence.get("source_reference") == selection.reference
            and evidence.get("input_bindings") == {
                "source": selection.source_digest, "comparison": selection.comparison_digest,
                "destination_snapshot": selection.snapshot_digest,
            }
        )
    _require(matches, "recovery_guard_original_plan_binding_mismatch")
    return True


def _read_id(manager, backend, identity, name, record):
    backend.authorize_readback(identity)
    try:
        response = _get(manager, _segments("byid", identity))
    except TransportError as error:
        record["by_id_checks"].append({"http_status": error.status, "classification": "unqualified-miss"
                                       if error.status == 404 and not error.backend_failure
                                       and not error.cleanup_failed else "error"})
        if error.status != 404 or error.backend_failure or error.cleanup_failed:
            raise
        return None
    record["by_id_checks"].append({"http_status": response.status, "classification": "response"})
    _require(response.status == 200, "recovery_by_id_http_unqualified")
    found = _site_object(_json(response), name)
    _require(found["ormID"] == identity and found.get("type") == "Site", "recovery_by_id_identity_mismatch")
    record["by_id_checks"][-1]["classification"] = "identity-matched"
    return found


def _assess_site(manager, backend, site, journal, tree, record):
    entry = journal["sites"][site.selection.reference]
    selection = site.selection
    identities = list(dict.fromkeys(
        [value for value in [entry["destination_identity"], *[
            row["destination_identity"] for row in journal.get("reconciliation_history", [])
            if row["reference"] == selection.reference
        ]] if value is not None]
    ))
    record["historical_identity_known"] = bool(identities)
    record["historical_operation_verified"] = entry["verified"]
    if not identities:
        record["issue_codes"].append("historical_destination_identity_unknown")
    if not entry["verified"]:
        record["issue_codes"].append("historical_operation_indeterminate")
    backend.select(selection)
    diagnostic = {}
    candidate = _lookup_candidate(manager, selection, diagnostic, backend)
    record["by_name"] = {
        "classification": "absence-candidate" if candidate is None else "response",
        "http_status": backend.candidate_http_status,
    }
    # By-name misses are only candidates. In particular, never convert M_00734 to 404.
    known = [_read_id(manager, backend, identity, selection.name, record) for identity in identities]
    matches = [row for row in tree if isinstance(row["name"], str)
               and _name(row["name"]) == _name(selection.name)]
    if candidate is None:
        _require(not matches and not any(row is not None for row in known),
                 "recovery_lookup_tree_or_identity_inconsistent")
        record["absence_candidate"] = True
        record["issue_codes"].extend(_BLOCKERS)
        return
    found = _site_object(_json(candidate), selection.name)
    _require(found.get("type") == "Site", "recovery_candidate_type_unqualified")
    _require(len(matches) == 1 and matches[0]["site"] and matches[0]["name"] == selection.name
             and _row_id(matches[0]) == found["ormID"], "recovery_tree_identity_mismatch")
    _require(not identities or identities == [found["ormID"]], "recovery_historical_identity_changed")
    if not identities:
        known = [_read_id(manager, backend, found["ormID"], selection.name, record)]
    _require(len(known) == 1 and known[0] is not None, "recovery_by_name_by_id_inconsistent")
    parent_id = entry["parent_identity"]
    _require(parent_id is not None, "recovery_historical_parent_identity_unknown")
    parent = _parent_in_tree(tree, selection, parent_id)
    _require(matches[0]["parent"] == parent["identity"]
             and all(_site_parent_matches(row, parent_id, selection.parent_is_root, tree_parent=parent)
                     for row in (found, known[0]))
             and (not matches[0]["parent_field_present"]
                  or _site_parent_matches(matches[0], parent_id, selection.parent_is_root, tree_parent=parent)),
             "recovery_parent_identity_mismatch")
    record["classification"] = "confirmed-existing"
    record["issue_codes"].append("attempted_site_still_exists")


def run_recovery_assessment(
    profile_path: str, credentials_path: str, backup: str, *,
    source_path: str | None = None, comparison_path: str | None = None, snapshot_path: str | None = None,
    target_version: str | None = None, limits: InventoryLimits | None = None, terminal: bool = False,
) -> tuple[dict, ExitStatus]:
    inventory = discover_backup(backup, limits=limits)
    profile = DiscoveryProfile.read(profile_path)
    require_execution_exception(profile.transport.base_url, profile.transport.verify_tls, credentials_path)
    message = warning(profile.transport.verify_tls)
    if message:
        print(message, file=sys.stderr)
    binding, state_path, lock_path = _context(profile, inventory)
    report = {
        "schema_version": 1, "operation": "migration-recovery-assess", "mode": "recovery-assess",
        "migration_status": "BLOCKED", "preflight_status": "NOT_RUN", "reset_eligible": False,
        "read_only": True, "configuration_writes_authorized": False, "create_attempts": 0,
        "authenticated": False, "target_origin": profile.transport.base_url, "target_version": target_version,
        "target_version_evidence": "operator-declared-not-api-verified", "tls": execution_tls(profile.transport.verify_tls),
        "counts": {"attempted": 0, "confirmed_existing": 0, "confirmed_absent": 0, "unresolved": 0, "indeterminate": 0},
        "objects": [], "issue_codes": list(_BLOCKERS), "required_evidence": dict(_BLOCKERS),
        "bindings": {"backup": "NOT_CHECKED", "original_plan": "NOT_CHECKED", "destination": "NOT_CHECKED"},
        "report_file": "ccv-recovery-report-" + uuid4().hex + ".json",
    }
    backend = None
    profile.output_directory.mkdir(parents=True, exist_ok=True)
    try:
        with _origin_lock(lock_path):
            organization = _organization(inventory)
            _require(organization is not None, "recovery_original_organization_backup_required")
            explicit = any(value is not None for value in (source_path, comparison_path, snapshot_path))
            _require(not explicit or all(value is not None for value in (source_path, comparison_path, snapshot_path)),
                     "recovery_original_plan_requires_all_three_inputs")
            state = _read_state(state_path, binding) if state_path.exists() else None
            if not explicit:
                _require(state is not None and state["comparison_file"] is not None
                         and state["snapshot_file"] is not None, "recovery_original_plan_missing_supply_bound_inputs")
                source_path = str(organization[0])
                comparison_path = str(profile.output_directory / state["comparison_file"])
                snapshot_path = str(profile.output_directory / state["snapshot_file"])
            assert source_path is not None and comparison_path is not None and snapshot_path is not None
            _protected_json(Path(comparison_path))
            original_snapshot = _protected_json(Path(snapshot_path))
            plan = load_plan(source_path, comparison_path, snapshot_path)
            _require(hashlib.sha256(organization[0].read_bytes()).hexdigest() == plan.binding["source_sha256"],
                     "recovery_original_backup_binding_mismatch")
            if state is not None and plan.digest == state.get("site_plan_sha256"):
                report["bindings"]["backup"] = "FULL_BACKUP_MATCHED"
            else:
                report["bindings"]["backup"] = "ORGANIZATION_SOURCE_ONLY"
                report["issue_codes"].append("historical_full_backup_binding_unrecorded")
                report["required_evidence"]["historical_full_backup_binding_unrecorded"] = (
                    "The legacy Site journal binds its source/comparison/snapshot, not the entire backup; retain this limitation."
                )
            site_binding, journal_path, _ = _journal_context(profile, plan)
            _require(journal_path.exists(), "recovery_original_site_journal_missing")
            journal = _read_journal(journal_path, site_binding, plan)
            original_root = _destination(original_snapshot)[1]["native"]
            _require(journal["root_identity"] == original_root.get(
                "ormID", original_root["meIdentifier"]["managedElementID"]),
                "recovery_original_root_binding_mismatch")
            report["bindings"]["original_plan"] = "MATCHED"
            for site in plan.sites:
                entry = journal["sites"][site.selection.reference]
                record = {"reference": site.selection.reference, "classification": (
                    "unresolved" if entry["verified"] else "indeterminate"
                ), "guard_validated": False, "by_name": None, "by_id_checks": [], "absence_candidate": False,
                          "issue_codes": []}
                guarded = site_attempt_guard(profile, site.selection).exists()
                if not entry["create_attempts"] and not guarded:
                    continue
                report["objects"].append(record)
                try:
                    record["guard_validated"] = _guard(profile, site.selection, plan)
                    _require(record["guard_validated"], "recovery_post_guard_missing")
                except SiteBlocked as error:
                    record["issue_codes"].append(error.code)
                except OSError:
                    record["issue_codes"].append("recovery_guard_evidence_io_failure")
            report["counts"]["attempted"] = len(report["objects"])
            backend = _RecoveryBackend(profile, plan.selection)
            with SessionManager(lambda: backend, _Credentials(credentials_path)) as manager:
                manager.initialize(
                    _UnknownVersionRequest(SessionRole.DESTINATION, "cyber-controller", "unknown",
                                           CredentialReference("cc-destination-discovery")),
                    profile.transport, strategy=_DiscoveryAuthentication(),
                )
                manager.authenticate(SessionRole.DESTINATION)
                report["authenticated"] = True
                root = _fresh_root(manager, backend, plan)
                _require(root == journal["root_identity"] and (state is None or root == state["root_identity"]),
                         "recovery_destination_root_identity_changed")
                report["bindings"]["destination"] = "ORIGIN_AND_ROOT_MATCHED"
                response = _get(manager, _TREE)
                _require(response.status == 200, "recovery_tree_http_unqualified")
                tree = _tree(_json(response))
                _require(tree[0]["name"] == plan.root_name and _row_id(tree[0]) == root,
                         "recovery_destination_root_identity_changed")
                attempted_refs = {row["reference"] for row in report["objects"]}
                names = {site.selection.name for site in plan.sites
                         if site.selection.reference in attempted_refs}
                report["organization_tree"] = {
                    "completeness": "UNQUALIFIED", "observed_sites": sum(row["site"] for row in tree[1:]),
                    "observed_devices": sum(not row["site"] for row in tree),
                    "unexpected_children": sum(not row["site"] or row["name"] not in names for row in tree[1:]),
                }
                if report["organization_tree"]["unexpected_children"]:
                    report["issue_codes"].append("recovery_unexpected_children_or_devices")
                sites = {site.selection.reference: site for site in plan.sites}
                report["counts"]["attempted"] = len(report["objects"])
                for record in report["objects"]:
                    if not record["guard_validated"]:
                        continue
                    try:
                        _assess_site(manager, backend, sites[record["reference"]], journal, tree, record)
                    except (SiteBlocked, TransportError) as error:
                        record["issue_codes"].append(error.code if isinstance(error, SiteBlocked) else error.category.value)
                _require(discover_backup(backup, limits=limits).digest == inventory.digest,
                         "recovery_backup_changed_during_assessment")
                report["preflight_status"] = "ASSESSED_RESET_BLOCKED"
    except (SiteBlocked, AuthenticationError, TransportError, ContractValidationError, OSError, KeyboardInterrupt) as error:
        if isinstance(error, SiteBlocked):
            code = error.code
        elif isinstance(error, (AuthenticationError, TransportError)):
            code = "recovery_authenticated_read_failed"
        elif isinstance(error, ContractValidationError):
            code = "recovery_evidence_contract_invalid"
        elif isinstance(error, KeyboardInterrupt):
            code = "recovery_assessment_interrupted"
        else:
            code = "recovery_protected_evidence_io_failure"
        report["issue_codes"].append(code)
        report["preflight_status"] = "BLOCKED"
    finally:
        if backend is not None:
            _close_backend(backend, report)
    for record in report["objects"]:
        report["counts"][record["classification"].replace("-", "_")] += 1
        record["issue_codes"] = sorted(set(record["issue_codes"]))
        report["issue_codes"].extend(record["issue_codes"])
    report["issue_codes"] = sorted(set(report["issue_codes"]))
    _write_private(profile.output_directory / report["report_file"], report)
    if terminal:
        print(f"Destination: {report['target_origin']}; operation: recovery assessment; preflight: {report['preflight_status']}")
        counts = report["counts"]
        print(f"Attempted {counts['attempted']}; Existing {counts['confirmed_existing']}; "
              f"Absent {counts['confirmed_absent']}; Unresolved {counts['unresolved']}; Indeterminate {counts['indeterminate']}")
        print("Local reset BLOCKED. Issues: " + ", ".join(report["issue_codes"]))
        print("Report: " + report["report_file"])
    return report, ExitStatus.VALIDATION_FAILED
