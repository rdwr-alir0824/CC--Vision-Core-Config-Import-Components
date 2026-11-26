"""Ordered Site-only migration with durable reservations and remote reconciliation."""

import hashlib
import copy
import json
import math
import os
import re
import stat
import sys
import time
from contextlib import ExitStack, contextmanager
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit
from uuid import uuid4

from ._json import load_json
from .authentication import AuthenticationError, CredentialReference, SessionRole
from .contracts import ContractValidationError, ExitStatus
from .destination_discovery import DiscoveryProfile, _Credentials, _DiscoveryAuthentication, _UnknownVersionRequest, _TREE
from .http_backend import SingleSiteAuthorization
from .sessions import SessionManager
from .single_site import (
    SiteBlocked, SiteSelection, SingleSiteBackend, _RISKS, _SITE_PATH, _close_backend,
    _get, _json, _lookup_candidate, _name, _parent_in_tree, _persist, _readback,
    _require, _segments, _site_object, _site_parent_matches, _text, _tree, _verify_created_site, load_site_evidence,
    reserve_site_attempt, site_attempt_guard,
)
from .tls_policy import execution_tls, require_execution_exception, warning
from .transport import HttpMethod, TransportError, build_url


@dataclass(frozen=True, repr=False)
class BatchSite:
    selection: SiteSelection
    parent_reference: str


@dataclass(frozen=True, repr=False)
class SitePlan:
    sites: tuple[BatchSite, ...]
    root_reference: str
    root_name: str
    binding: dict
    digest: str


def load_plan(source_path: str, comparison_path: str, snapshot_path: str) -> SitePlan:
    evidence = load_site_evidence(source_path, comparison_path, snapshot_path)
    expected = evidence.comparison
    _require(evidence.report["site_comparisons"] == expected["site_comparisons"],
             "batch_comparison_evidence_mismatch")
    order = expected["source_dependency_order"]
    _require(evidence.report.get("source_dependency_order") == order, "batch_dependency_order_mismatch")
    records = {row["source_reference"]: row for row in expected["site_comparisons"]}
    _require(bool(records) and len(order) == len(set(order)) == len(records)
             and set(order) == set(records), "batch_sites_not_completely_orderable")
    root_ref = expected["root_mapping"]["source_reference"]
    root_name = evidence.destination_root["native"]["name"]
    _require(_text(root_name), "unsupported_site_name")
    seen = {root_ref}
    names = {_name(root_name)}
    sites = []
    for reference in order:
        row = records[reference]
        _require(row["classification"] in ("candidate_for_creation", "possible_existing_destination_site")
                 and row["source_order_eligible"] and not row["missing_source_fields"],
                 "batch_contains_blocked_or_ambiguous_site")
        parent_ref = row["source_parent_reference"]
        _require(parent_ref in seen and row["observed_source_container_parent"] == parent_ref,
                 "batch_parent_dependency_unresolved")
        name = evidence.rows[int(reference.split("-")[-1]) - 1]["name"]
        parent_name = root_name if parent_ref == root_ref else (
            evidence.rows[int(parent_ref.split("-")[-1]) - 1]["name"]
        )
        _require(_text(name) and _text(parent_name) and _name(name) not in names,
                 "batch_site_name_ambiguous")
        _segments("byname", name)
        _segments("byname", parent_name)
        names.add(_name(name))
        seen.add(reference)
        sites.append(BatchSite(SiteSelection(
            reference, name, parent_name, parent_ref == root_ref,
            *evidence.digests, evidence.source_identities,
        ), parent_ref))
    binding = {
        "source_sha256": evidence.digests[0], "comparison_sha256": evidence.digests[1],
        "snapshot_sha256": evidence.digests[2], "root_reference": root_ref,
        "ordered_sites": [[site.selection.reference, site.parent_reference] for site in sites],
    }
    digest = hashlib.sha256(json.dumps(binding, sort_keys=True).encode()).hexdigest()
    return SitePlan(tuple(sites), root_ref, root_name, binding, digest)


class BatchSiteBackend(SingleSiteBackend):
    """Same finite Site API; one armed request per journal-reserved selection."""

    def select(self, selection: SiteSelection) -> None:
        self._select_read_scope(selection)
        self.create_armed = False
        self.create_count = 0
        self._authorization = SingleSiteAuthorization(self._site_origin, self._operations)

    def authorize_readback(self, identity: str) -> None:
        path = urlsplit(build_url(self._site_origin, _segments("byid", identity))).path
        self._authorization = SingleSiteAuthorization(
            self._site_origin, (*self._operations, (HttpMethod.GET, path)),
        )


def _private_descriptor(path: Path, flags: int) -> int:
    _require(not path.is_symlink(), "unsafe_migration_journal_file")
    descriptor = os.open(path, flags | getattr(os, "O_NOFOLLOW", 0), 0o600)
    info = os.fstat(descriptor)
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or (
        os.name != "nt" and (stat.S_IMODE(info.st_mode) != 0o600 or info.st_uid != os.geteuid())
    ):
        os.close(descriptor)
        raise SiteBlocked("unsafe_migration_journal_permissions")
    return descriptor


def _sync_directory(path: Path) -> None:
    if os.name != "nt":
        descriptor = os.open(path, os.O_RDONLY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)


def _write_private(path: Path, payload: dict) -> None:
    temporary = path.with_name("." + uuid4().hex + ".tmp")
    try:
        descriptor = _private_descriptor(temporary, os.O_CREAT | os.O_EXCL | os.O_RDWR)
        with os.fdopen(descriptor, "w+", encoding="utf-8") as stream:
            _persist(stream, payload)
        for attempt in range(5):
            try:
                os.replace(temporary, path)
                break
            except PermissionError:
                if os.name != "nt" or attempt == 4:
                    raise
                time.sleep(0.02)
        _sync_directory(path.parent)
    finally:
        if temporary.exists():
            temporary.unlink()


@contextmanager
def _origin_lock(path: Path):
    descriptor = _private_descriptor(path, os.O_CREAT | os.O_RDWR)
    try:
        if os.fstat(descriptor).st_size == 0:
            os.write(descriptor, b"\0")
            os.fsync(descriptor)
        os.lseek(descriptor, 0, os.SEEK_SET)
        try:
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(descriptor, msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            raise SiteBlocked("batch_operation_already_running") from None
        yield
    finally:
        os.close(descriptor)


def _new_entries(plan: SitePlan) -> dict:
    return {site.selection.reference: {
        "status": "pending", "destination_identity": None, "parent_identity": None,
        "create_attempts": 0, "created": False, "verified": False, "already_existing": False,
        "reconciled": False,
    } for site in plan.sites}


def _read_journal(path: Path, binding: dict, plan: SitePlan) -> dict:
    descriptor = _private_descriptor(path, os.O_RDONLY)
    try:
        with os.fdopen(descriptor, "r", encoding="utf-8") as stream:
            raw = stream.read(16 * 1024 * 1024 + 1)
    except UnicodeError:
        raise SiteBlocked("invalid_migration_journal") from None
    _require(len(raw) <= 16 * 1024 * 1024, "migration_journal_size_limit")
    try:
        data = load_json(raw)
    except (ValueError, RecursionError):
        raise SiteBlocked("invalid_migration_journal") from None
    _require(isinstance(data, dict) and data.get("schema_version") == 1
             and data.get("domain") == "protected-site-migration-journal"
             and data.get("binding") == binding and _text(data.get("root_identity")),
             "migration_journal_binding_mismatch")
    entries = data.get("sites")
    template = _new_entries(plan)
    _require(isinstance(entries, dict) and set(entries) == set(template), "invalid_journal_sites")
    entries = {reference: entries[reference] for reference in template}
    data["sites"] = entries
    pending_seen = False
    for reference in template:
        entry = entries[reference]
        _require(isinstance(entry, dict) and set(entry) == set(template[reference])
                 and entry["status"] in (
                     "pending", "attempting", "verified", "already-existing", "blocked", "failed", "indeterminate",
                 ) and type(entry["create_attempts"]) is int and entry["create_attempts"] in (0, 1)
                 and all(type(entry[key]) is bool for key in ("created", "verified", "already_existing", "reconciled"))
                 and all(entry[key] is None or _text(entry[key]) for key in ("destination_identity", "parent_identity")),
                 "invalid_journal_site_state")
        if entry["verified"]:
            _require(not pending_seen and _text(entry["destination_identity"]) and _text(entry["parent_identity"]),
                     "invalid_journal_verified_order")
        else:
            pending_seen = True
        _require(not entry["created"] or entry["create_attempts"] == 1, "invalid_journal_attempt_count")
        _require(
            (entry["status"] not in ("verified", "already-existing") or entry["verified"])
            and (not entry["already_existing"] or (
                entry["verified"] and not entry["create_attempts"] and not entry["created"]
            ))
            and (not entry["reconciled"] or entry["verified"] and entry["created"])
            and (not entry["verified"] or entry["created"] or entry["already_existing"]),
            "invalid_journal_site_state",
        )
    active = data.get("incomplete_operation")
    if active is not None:
        _require(isinstance(active, dict)
                 and set(active) == {"reference", "prior_identities", "http_status"}
                 and isinstance(active.get("reference"), str) and active["reference"] in entries
                 and entries[active["reference"]]["create_attempts"] == 1
                 and not entries[active["reference"]]["verified"]
                 and isinstance(active.get("prior_identities"), list)
                 and len(active["prior_identities"]) <= 20000
                 and (active["http_status"] is None or (
                     type(active["http_status"]) is int and 100 <= active["http_status"] <= 599
                 ))
                 and all(_text(value) for value in active["prior_identities"]), "invalid_journal_incomplete_operation")
    uncertain = [reference for reference, entry in entries.items() if entry["create_attempts"] and not entry["verified"]]
    _require(uncertain == ([] if active is None else [active["reference"]]), "invalid_journal_incomplete_operation")
    if active is not None:
        _require(next(reference for reference, entry in entries.items() if not entry["verified"])
                 == active["reference"], "invalid_journal_incomplete_operation")
    history = data.get("reconciliation_history", [])
    _require(isinstance(history, list) and len(history) <= len(entries), "invalid_journal_reconciliation_history")
    for item in history:
        _require(isinstance(item, dict) and set(item) == {
            "reference", "previous_status", "create_attempts", "incomplete_operation",
            "destination_identity", "parent_identity",
        } and isinstance(item["reference"], str) and item["reference"] in entries and item["create_attempts"] == 1
                 and item["previous_status"] in ("attempting", "indeterminate", "failed", "blocked")
                 and _text(item["destination_identity"]) and _text(item["parent_identity"]),
                 "invalid_journal_reconciliation_history")
        previous = item["incomplete_operation"]
        _require(isinstance(previous, dict)
                 and set(previous) == {"reference", "prior_identities", "http_status"}
                 and previous["reference"] == item["reference"]
                 and isinstance(previous["prior_identities"], list) and len(previous["prior_identities"]) <= 20000
                 and all(_text(identity) for identity in previous["prior_identities"])
                 and (previous["http_status"] is None or (
                     type(previous["http_status"]) is int and 100 <= previous["http_status"] <= 599
                 )), "invalid_journal_reconciliation_history")
    return data


def _row_id(row: dict) -> str:
    return row["ormID"] if row["ormID"] is not None else row["identity"]


def _validate_mappings(tree: list[dict], plan: SitePlan, mapping: dict[str, str]) -> None:
    _require(tree[0]["name"] == plan.root_name and _row_id(tree[0]) == mapping[plan.root_reference],
             "batch_root_identity_changed")
    by_ref = {site.selection.reference: site for site in plan.sites}
    _require(len(set(mapping.values())) == len(mapping), "batch_destination_identity_reused")
    matched = {plan.root_reference: tree[0]}
    for reference, identity in mapping.items():
        if reference == plan.root_reference:
            continue
        site = by_ref[reference]
        rows = [row for row in tree if row["site"] and isinstance(row["name"], str)
                and _name(row["name"]) == _name(site.selection.name)]
        _require(len(rows) == 1 and rows[0]["name"] == site.selection.name and _row_id(rows[0]) == identity,
                 "batch_verified_identity_changed")
        parent = matched.get(site.parent_reference)
        _require(parent is not None and rows[0]["parent"] == parent["identity"]
                 and (not rows[0]["parent_field_present"]
                      or _site_parent_matches(rows[0], mapping[site.parent_reference],
                                              site.selection.parent_is_root)), "batch_verified_parent_changed")
        matched[reference] = rows[0]


def _fresh_root(manager: SessionManager, backend: BatchSiteBackend, plan: SitePlan) -> str:
    selection = plan.sites[0].selection
    backend.select(selection)
    response = _get(manager, _segments("byname", plan.root_name))
    _require(response.status == 200, "destination_parent_lookup_failed")
    root = _site_object(_json(response), plan.root_name)
    _require(root["ormID"] not in selection.source_identities
             and "parentOrmID" in root and root["parentOrmID"] is None, "destination_root_parent_unverified")
    response = _get(manager, _TREE)
    _require(response.status == 200, "tree_preflight_failed")
    tree = _tree(_json(response))
    _parent_in_tree(tree, selection, root["ormID"])
    return root["ormID"]


def _inspect(
    manager: SessionManager, backend: BatchSiteBackend, plan: SitePlan, site: BatchSite,
    mapping: dict[str, str], report: dict, attempts: int, interval: float,
) -> tuple[str | None, frozenset[str]]:
    selection = site.selection
    backend.select(selection)
    parent_id = mapping.get(site.parent_reference)
    if parent_id is not None:
        report["failure_stage"] = "parent_lookup"
        response = _get(manager, _segments("byname", selection.parent_name))
        _require(response.status == 200, "destination_parent_lookup_failed")
        parent = _site_object(_json(response), selection.parent_name)
        _require(parent["ormID"] == parent_id, "batch_parent_identity_changed")
        if selection.parent_is_root:
            _require("parentOrmID" in parent and parent["parentOrmID"] is None, "destination_root_parent_unverified")
    candidate = _lookup_candidate(manager, selection, report, backend)
    report["failure_stage"] = "organization_tree_lookup"
    response = _get(manager, _TREE)
    _require(response.status == 200, "tree_preflight_failed")
    tree = _tree(_json(response))
    _validate_mappings(tree, plan, mapping)
    if parent_id is not None:
        _parent_in_tree(tree, selection, parent_id)
    identity = None
    if candidate is None:
        _require(not any(isinstance(row["name"], str) and _name(row["name"]) == _name(selection.name)
                         for row in tree), "fresh_tree_collision")
    else:
        _require(parent_id is not None, "existing_site_parent_dependency_unverified")
        _require(candidate.status == 200, "candidate_lookup_http_unqualified")
        report["failure_stage"] = "candidate_identity"
        found = _site_object(_json(candidate), selection.name)
        _require(found.get("type") == "Site", "candidate_site_type_unverified")
        _require(_site_parent_matches(found, parent_id, selection.parent_is_root), "existing_site_parent_mismatch")
        identity = found["ormID"]
        _require(_readback(manager, backend, selection, parent_id, identity, attempts=attempts, interval=interval),
                 "bounded_readback_incomplete")
    report.pop("failure_stage", None)
    return identity, frozenset(value for row in tree for value in (row["identity"], row["ormID"])
                               if isinstance(value, str))


def _approval(origin: str, count: int, digest: str) -> bool:
    print(f"Destination: {origin}; total Sites: {count}.")
    print("Experimental compatibility. No retries or rollback; approval covers only this list and destination.")
    try:
        if not sys.stdin.isatty() or not sys.stdout.isatty():
            print("Authorization cancelled: an interactive terminal is required.", file=sys.stderr)
            return False
        if os.name != "nt":
            try:
                import readline
            except ImportError:
                print("Authorization cancelled: terminal line editing is unavailable.", file=sys.stderr)
                return False
            readline.set_auto_history(False)
        while True:
            answer = input(f"Proceed with creating {count} Sites? [Y/n] (default Yes): ").strip().casefold()
            if answer in ("", "y", "yes"):
                return True
            if answer in ("n", "no"):
                return False
            print("Please enter Y/Yes or N/No.")
    except (EOFError, KeyboardInterrupt, OSError, ValueError):
        print("\nAuthorization cancelled: terminal input ended or was interrupted.", file=sys.stderr)
        return False


def _refresh_report(report: dict, entries: dict) -> None:
    report["sites"] = [{
        "source_reference": reference,
        "verified_this_run": reference in report["verified_this_run"],
        **{key: entry[key] for key in (
            "status", "create_attempts", "created", "verified", "already_existing", "reconciled",
        )},
    } for reference, entry in entries.items()]
    report["counts"] = {
        "total": len(entries),
        "verified_this_run": len(report["verified_this_run"]),
        **{key: sum(entry[key] for entry in entries.values())
           for key in ("created", "verified", "already_existing", "reconciled")},
        **{key: sum(entry["status"] == key for entry in entries.values()) for key in ("blocked", "pending")},
        "failed": sum(entry["status"] in ("failed", "indeterminate") for entry in entries.values()),
    }
    report["create_attempts"] = sum(entry["create_attempts"] for entry in entries.values())


def _journal_context(profile: DiscoveryProfile, plan: SitePlan) -> tuple[dict, Path, Path]:
    origin = urlsplit(profile.transport.base_url)
    canonical = [origin.scheme, origin.hostname, origin.port or 443]
    digest = hashlib.sha256(json.dumps(canonical).encode()).hexdigest()[:16]
    return (
        {"origin": canonical, "plan": plan.binding},
        profile.output_directory / f"ccv-sites-{plan.digest[:32]}-{digest}.journal.json",
        profile.output_directory / f".ccv-sites-{digest}.lock",
    )


def run_site_migration(
    profile_path: str, credentials_path: str, source_path: str, comparison_path: str, snapshot_path: str, *,
    mode: str = "dry-run", target_version: str | None = None, operation_delay: float = 1,
    readback_interval: float = 1, readback_attempts: int = 3, approve=None,
    terminal: bool = False,
) -> tuple[dict, ExitStatus]:
    _require(mode in ("dry-run", "execute", "resume", "reconcile"), "invalid_batch_mode")
    _require(all(type(value) in (int, float) and math.isfinite(value) and 0 <= value <= 60
                 for value in (operation_delay, readback_interval))
             and type(readback_attempts) is int and 1 <= readback_attempts <= 10, "invalid_batch_timing")
    _require(target_version is None or bool(re.fullmatch(r"10\.[0-9]+(?:\.[0-9]+)*(?:-[0-9]+)?", target_version)),
             "unsupported_target_declaration")
    plan = load_plan(source_path, comparison_path, snapshot_path)
    profile = DiscoveryProfile.read(profile_path)
    require_execution_exception(profile.transport.base_url, profile.transport.verify_tls, credentials_path)
    message = warning(profile.transport.verify_tls)
    if message:
        print(message, file=sys.stderr)
    binding, journal_path, lock_path = _journal_context(profile, plan)
    report_path = profile.output_directory / f"ccv-sites-report-{uuid4().hex}.json"
    entries = _new_entries(plan)
    report = {
        "schema_version": 1, "domain": "site-batch-migration-report", "operation": "site-batch-migration",
        "status": "error", "mode": mode, "read_only": True, "offline_only": False,
        "authenticated": False, "configuration_writes_authorized": False, "execution_authorized": False,
        "migration_ready": False, "compatibility": "experimental-unverified", "risk_codes": list(_RISKS),
        "target_origin": profile.transport.base_url, "target_version": target_version,
        "target_version_evidence": "operator-declared-not-api-verified",
        "tls": execution_tls(profile.transport.verify_tls), "plan_sha256": plan.digest,
        "input_bindings": plan.binding, "report_file": report_path.name, "journal_file": journal_path.name,
        "manual_reconciliation_required": False, "issue_codes": [], "create_attempts": 0,
        "operation_delay": operation_delay, "readback_interval": readback_interval,
        "readback_attempts": readback_attempts,
        "request_preview": {"method": "POST", "path": "/mgmt/system/config/tree/site",
                            "body": {"name": "<selected source Site>", "parentOrmID": "<fresh verified destination parent>"}},
        "dependency_order": plan.binding["ordered_sites"],
        "verified_this_run": [],
    }
    backend = BatchSiteBackend(profile, plan.sites[0].selection)
    strategy = _DiscoveryAuthentication()
    journal = None
    current = None
    resources = ExitStack()
    status = ExitStatus.VALIDATION_FAILED
    if terminal:
        print(f"Destination: {profile.transport.base_url}")
        print(f"Operation: Sites {mode}; total Sites: {len(plan.sites)}; preflight: CHECKING", flush=True)
    try:
        _refresh_report(report, entries)
        _write_private(report_path, report)
        resources.enter_context(_origin_lock(lock_path))
        if mode in ("resume", "reconcile"):
            journal = _read_journal(journal_path, binding, plan)
            entries = journal["sites"]
        elif mode == "execute":
            _require(not journal_path.exists(), "batch_journal_exists_resume_required")
        with SessionManager(lambda: backend, _Credentials(credentials_path)) as manager:
            manager.initialize(
                _UnknownVersionRequest(SessionRole.DESTINATION, "cyber-controller", "unknown",
                                       CredentialReference("cc-destination-discovery")),
                profile.transport, strategy=strategy,
            )
            manager.authenticate(SessionRole.DESTINATION)
            report["authenticated"] = True
            report["failure_stage"] = "root_qualification"
            root_id = _fresh_root(manager, backend, plan)
            if journal is not None:
                _require(journal["root_identity"] == root_id, "batch_root_identity_changed")
            report.pop("failure_stage", None)
            mapping = {plan.root_reference: root_id}
            if mode in ("execute", "resume"):
                preflight_mapping = dict(mapping)
                for site in plan.sites:
                    identity, _ = _inspect(
                        manager, backend, plan, site, preflight_mapping, report, readback_attempts, readback_interval,
                    )
                    if identity is not None:
                        preflight_mapping[site.selection.reference] = identity
                if terminal:
                    print("Preflight: PASSED", flush=True)
                if not (approve or _approval)(profile.transport.base_url, len(plan.sites), plan.digest):
                    raise SiteBlocked("batch_operator_declined_or_no_terminal")
                report.update(execution_authorized=True, configuration_writes_authorized=True)
                if journal is None:
                    journal = {
                        "schema_version": 1, "domain": "protected-site-migration-journal",
                        "binding": binding, "root_identity": root_id, "sites": entries,
                        "incomplete_operation": None,
                    }
                _write_private(journal_path, journal)
            for index, site in enumerate(plan.sites):
                current = site.selection.reference
                entry = entries[current]
                if mode == "reconcile" and not entry["create_attempts"] and not entry["verified"]:
                    current = None
                    break
                report["current_source_reference"] = current
                report.pop("candidate_collision_diagnostic", None)
                if index and operation_delay:
                    time.sleep(operation_delay)
                identity, prior_ids = _inspect(
                    manager, backend, plan, site, mapping, report, readback_attempts, readback_interval,
                )
                parent_id = mapping.get(site.parent_reference)
                if identity is not None:
                    if entry["destination_identity"] is not None:
                        _require(identity == entry["destination_identity"]
                                 and parent_id == entry["parent_identity"], "journal_destination_identity_changed")
                    if entry["create_attempts"] and not entry["verified"]:
                        active = journal["incomplete_operation"]
                        _require(active is not None and active["reference"] == current
                                 and identity not in active["prior_identities"], "incomplete_create_identity_ambiguous")
                        journal.setdefault("reconciliation_history", []).append({
                            "reference": current, "previous_status": entry["status"],
                            "create_attempts": entry["create_attempts"],
                            "incomplete_operation": copy.deepcopy(active),
                            "destination_identity": identity, "parent_identity": parent_id,
                        })
                        entry.update(created=True, reconciled=True)
                    entry.update(
                        status="verified" if entry["create_attempts"] else "already-existing",
                        destination_identity=identity, parent_identity=parent_id, verified=True,
                        already_existing=not bool(entry["create_attempts"]),
                    )
                    mapping[current] = identity
                    report["verified_this_run"].append(current)
                else:
                    _require(not entry["create_attempts"] and not entry["verified"]
                             and not site_attempt_guard(profile, site.selection).exists(),
                             "prior_attempt_requires_manual_reconciliation")
                    if mode in ("execute", "resume"):
                        _require(parent_id is not None, "destination_parent_dependency_unresolved")
                        entry.update(status="attempting", create_attempts=1)
                        journal["incomplete_operation"] = {
                            "reference": current, "prior_identities": sorted(prior_ids), "http_status": None,
                        }
                        _write_private(journal_path, journal)
                        reserve_site_attempt(profile, site.selection, report_path.name)
                        backend.arm_create()
                        report["read_only"] = False
                        report["failure_stage"] = "site_create_request"
                        response = manager.request(
                            SessionRole.DESTINATION, HttpMethod.POST, _SITE_PATH,
                            headers={"Content-Type": "application/json"},
                            body=json.dumps({"name": site.selection.name, "parentOrmID": parent_id}).encode(),
                        )
                        journal["incomplete_operation"]["http_status"] = response.status
                        _require(response.status in (200, 201), "create_http_outcome_unqualified")
                        def checkpoint(identity: str) -> None:
                            entry.update(destination_identity=identity, parent_identity=parent_id, created=True)
                            _write_private(journal_path, journal)

                        report["failure_stage"] = "site_identity_readback"
                        identity = _verify_created_site(
                            manager, backend, site.selection, parent_id, response, prior_ids | frozenset(mapping.values()), report,
                            attempts=readback_attempts, interval=readback_interval, checkpoint=checkpoint,
                        )
                        entry.update(status="verified", verified=True)
                        mapping[current] = identity
                        report["verified_this_run"].append(current)
                if journal is not None:
                    active = journal["incomplete_operation"]
                    if active is not None and active["reference"] == current and entry["verified"]:
                        journal["incomplete_operation"] = None
                    _write_private(journal_path, journal)
                _refresh_report(report, entries)
                _write_private(report_path, report)
                if terminal and mode != "dry-run":
                    print(f"Site {index + 1}/{len(plan.sites)}: {entry['status'].upper()}", flush=True)
            report["failure_stage"] = "final_hierarchy_readback"
            response = _get(manager, _TREE)
            _require(response.status == 200, "hierarchy_readback_failed")
            _validate_mappings(_tree(_json(response)), plan, mapping)
            report["status"] = (
                "dry-run-ready" if mode == "dry-run" else "reconciled" if mode == "reconcile" else "batch-verified"
            )
            report.pop("failure_stage", None)
            status = ExitStatus.SUCCESS
    except (SiteBlocked, AuthenticationError, TransportError, ContractValidationError, OSError, KeyboardInterrupt) as error:
        if isinstance(error, SiteBlocked):
            code = error.code
        elif isinstance(error, TransportError):
            code = error.category.value
            if error.status is not None:
                report["http_status"] = error.status
                if (journal is not None and journal["incomplete_operation"] is not None
                        and report.get("failure_stage") == "site_create_request"):
                    journal["incomplete_operation"]["http_status"] = error.status
            if report.get("failure_stage") == "candidate_collision_lookup" and backend.candidate_collision_diagnostic:
                report["candidate_collision_diagnostic"] = dict(backend.candidate_collision_diagnostic)
        elif isinstance(error, AuthenticationError):
            reason = error.failure.transport_reason
            code = reason.value if reason is not None else error.failure.category.value
        elif isinstance(error, ContractValidationError):
            code = "response_or_path_contract_failure"
        elif isinstance(error, KeyboardInterrupt):
            code = "batch_execution_interrupted"
        else:
            code = "migration_journal_or_report_io_failure"
        report["issue_codes"] = [code]
        if current is not None:
            entry = entries[current]
            if not entry["verified"]:
                entry["status"] = "indeterminate" if entry["create_attempts"] else (
                    "blocked" if isinstance(error, SiteBlocked) else "failed"
                )
            report["manual_reconciliation_required"] = bool(entry["create_attempts"] and not entry["verified"]) or (
                code == "prior_attempt_requires_manual_reconciliation"
            )
        report["status"] = "indeterminate" if report["manual_reconciliation_required"] else "blocked"
        if not report["authenticated"]:
            report["status"] = "error"
        if journal is not None:
            try:
                _write_private(journal_path, journal)
            except OSError:
                report["issue_codes"].append("migration_journal_persistence_failed")
    finally:
        strategy.clear()
        _refresh_report(report, entries)
        _close_backend(backend, report)
        try:
            _write_private(report_path, report)
        except OSError:
            report["issue_codes"].append("migration_report_persistence_failed")
            report["status"] = "error"
            status = ExitStatus.INPUT_ERROR
        resources.close()
    if report["status"] not in ("dry-run-ready", "batch-verified", "reconciled"):
        status = ExitStatus.VALIDATION_FAILED if status == ExitStatus.SUCCESS else status
    if terminal:
        from .launcher_helper import summary

        summary(report, "2", int(status), str(profile.output_directory), "")
    return report, status
