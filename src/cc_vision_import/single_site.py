"""One experimental Site transaction; no bulk, fallback, retry or rollback."""

import hashlib
import json
import os
import re
import sys
import time
import unicodedata
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import TextIO
from urllib.parse import urlsplit
from uuid import uuid4

from ._contract_validation import ContractReader
from ._json import load_json
from .authentication import AuthenticationError, CredentialReference, SessionRole
from .contracts import ContractValidationError, ExitStatus
from .destination_discovery import (
    DiscoveryProfile, _Credentials, _DiscoveryAuthentication, _UnknownVersionRequest, _TREE, _SITE,
)
from .http_backend import SingleSiteAuthorization, StdlibHttpBackend
from .offline_inputs import OfflineInputs
from .sessions import SessionManager
from .site_comparison import _destination, compare_sites
from .tls_policy import execution_tls, require_execution_exception, warning
from .transport import BackendFailure, BackendRequest, ErrorCategory, HttpMethod, HttpResponse, TransportError, build_url
from .vision_tree_preview import _tree_rows, inspect_site_migration_readiness


_READER = ContractReader("single-site")
_SITE_PATH = ("mgmt", "system", "config", "tree", "site")
_RISKS = (
    "experimental_target_create_contract",
    "four_field_omission_and_root_parent_acceptance_unverified",
    "collision_not_found_semantics_and_enumeration_unverified",
    "readback_identity_and_tree_correspondence_experimental",
    "no_write_retry_or_automatic_rollback",
)


class SiteBlocked(Exception):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def _require(condition: bool, code: str) -> None:
    if not condition:
        raise SiteBlocked(code)


def _text(value: object) -> bool:
    return (
        isinstance(value, str) and bool(value) and value == value.strip()
        and all(character.isprintable() for character in value)
    )


def _name(value: str) -> str:
    return unicodedata.normalize("NFKC", value).casefold()


def _segments(kind: str, value: str) -> tuple[str, ...]:
    result = (*_SITE_PATH, kind, value)
    build_url("https://validation.invalid", result)
    return result


@dataclass(frozen=True, repr=False)
class SiteSelection:
    reference: str
    name: str
    parent_name: str
    parent_is_root: bool
    source_digest: str
    comparison_digest: str
    snapshot_digest: str
    source_identities: frozenset[str] = field(repr=False)


@dataclass(frozen=True, repr=False)
class SiteEvidence:
    rows: list[dict]
    report: dict
    comparison: dict
    destination_root: dict
    destination_sites: list[dict]
    digests: tuple[str, str, str]
    source_identities: frozenset[str]


def load_site_evidence(source_path: str, comparison_path: str, snapshot_path: str) -> SiteEvidence:
    inputs = OfflineInputs(Path.cwd())
    source = inputs.read(source_path, "source-organization-tree", base=Path.cwd())
    snapshot = inputs.read(snapshot_path, "destination-organization-sites", base=Path.cwd())
    report = _READER.mapping(inputs.read(comparison_path, "comparison", base=Path.cwd()), "$")
    _require(
        report.get("domain") == "source-destination-site-comparison-report"
        and report.get("schema_version") == 1
        and report.get("execution_authorized") is False
        and report.get("configuration_writes_authorized") is False
        and report.get("devices_processed") is False,
        "invalid_comparison",
    )
    bindings = report.get("input_bindings")
    _require(isinstance(bindings, list), "missing_input_bindings")
    for current in inputs.bindings[:2]:
        matches = [row for row in bindings if isinstance(row, dict) and row.get("slot") == current["slot"]]
        _require(len(matches) == 1 and matches[0].get("sha256") == current["sha256"], "input_binding_mismatch")
    readiness = inspect_site_migration_readiness(source)
    rows = _tree_rows(source["tree"])
    root_ref = readiness["root_assessment"]["reference"]
    _require(isinstance(root_ref, str), "source_root_unresolved")
    source_root = rows[int(root_ref[5:]) - 1]
    _, destination_root, destination_sites = _destination(snapshot)
    expected = compare_sites(
        source, snapshot, source_root_name=source_root["name"],
        destination_root_name=destination_root["native"]["name"], confirm_root_mapping=True,
    )
    _require(report.get("root_mapping") == expected["root_mapping"]
             and expected["root_mapping"]["status"] == "confirmed", "root_mapping_unconfirmed")
    records = report.get("site_comparisons")
    _require(isinstance(records, list), "invalid_comparison_records")
    identities: set[str] = set()
    for row in rows:
        identifier = row.get("meIdentifier", {})
        for value in (row.get("ormID"), identifier.get("managedElementID"), identifier.get("dbId")):
            if isinstance(value, (str, int)) and not isinstance(value, bool):
                identities.add(str(value))
    return SiteEvidence(
        rows, report, expected, destination_root, destination_sites,
        (inputs.bindings[0]["sha256"], inputs.bindings[2]["sha256"], inputs.bindings[1]["sha256"]),
        frozenset(identities),
    )


def load_selection(source_path: str, comparison_path: str, snapshot_path: str, reference: str) -> SiteSelection:
    _require(bool(re.fullmatch(r"source:node-[1-9][0-9]{0,4}", reference)), "invalid_site_reference")
    evidence = load_site_evidence(source_path, comparison_path, snapshot_path)
    records, expected, rows = evidence.report["site_comparisons"], evidence.comparison, evidence.rows
    destination_root, destination_sites = evidence.destination_root, evidence.destination_sites
    selected = [row for row in records if isinstance(row, dict) and row.get("source_reference") == reference]
    recomputed = [row for row in expected["site_comparisons"] if row["source_reference"] == reference]
    _require(len(selected) == len(recomputed) == 1 and selected[0] == recomputed[0], "candidate_evidence_mismatch")
    record = recomputed[0]
    _require(
        record["classification"] == "candidate_for_creation" and record["source_order_eligible"]
        and not record["missing_source_fields"] and not record["destination_candidates"],
        "candidate_not_eligible",
    )
    parent_ref = record["parent_destination_reference_candidate"]
    _require(isinstance(parent_ref, str), "destination_parent_dependency_unresolved")
    parents = [row for row in [destination_root, *destination_sites]
               if "destination:" + row["reference"] == parent_ref]
    _require(len(parents) == 1, "destination_parent_mapping_ambiguous")
    name = rows[int(reference.split("-")[-1]) - 1]["name"]
    parent_name = parents[0]["native"]["name"]
    _require(_text(name) and _text(parent_name), "unsupported_site_name")
    _segments("byname", name)
    _segments("byname", parent_name)
    _require(_name(name) != _name(parent_name), "candidate_parent_name_collision")
    return SiteSelection(
        reference, name, parent_name, parents[0] is destination_root,
        *evidence.digests, evidence.source_identities,
    )


def _candidate_error_diagnostic(response: HttpResponse, name: str) -> dict[str, object]:
    try:
        payload = load_json(response.body.decode("utf-8"))
    except (UnicodeError, ValueError, RecursionError):
        return {"classification": "malformed_json"}
    if not isinstance(payload, dict):
        return {"classification": "unexpected_json_shape"}
    matches = (
        set(payload) == {"status", "message"} and payload.get("status") == "error"
        and payload.get("message") == "There is no site with name " + name
    )
    m_00734_matches = response.status == 400 and payload == {
        "status": "error",
        "message": f"M_00734: There is no device with name {name} configured in Cyber Controller.",
    }
    return {
        "classification": "m_00734_absence_candidate" if m_00734_matches else
                          "legacy_absence_signature_unqualified" if matches else "unqualified_http_400",
        "http_status": response.status,
        "m_00734_absence_signature_matches": m_00734_matches,
        **({"signature_evidence_version": "10.15.0-2"} if m_00734_matches else {}),
        "status_is_error": payload.get("status") == "error",
        "message_is_string": isinstance(payload.get("message"), str),
        "only_status_message_keys": set(payload) == {"status", "message"},
        "candidate_name_in_message": (
            isinstance(payload.get("message"), str) and name in payload["message"]
        ),
        "message_mentions_no_site": (
            isinstance(payload.get("message"), str) and "no site" in payload["message"].casefold()
        ),
        "message_mentions_not_found": (
            isinstance(payload.get("message"), str) and "not found" in payload["message"].casefold()
        ),
        "message_mentions_invalid": (
            isinstance(payload.get("message"), str) and "invalid" in payload["message"].casefold()
        ),
        "legacy_absence_signature_matches": matches,
        "site_fields_present": any(key in payload for key in (
            "name", "ormID", "parentOrmID", "managedElementID", "meIdentifier", "type",
        )),
    }


class SingleSiteBackend(StdlibHttpBackend):
    """Fresh exact read scope; write permission is armed once after approval."""

    def __init__(self, profile: DiscoveryProfile, selection: SiteSelection) -> None:
        self._site_origin = profile.transport.base_url
        self._select_read_scope(selection)
        self.create_armed = False
        self.create_count = 0
        super().__init__(
            allow_live=True, authorization=SingleSiteAuthorization(self._site_origin, self._operations),
            max_response_bytes=16 * 1024 * 1024,
            allow_unverified_single_site=profile.transport.unverified_destination_discovery,
        )

    def _select_read_scope(self, selection: SiteSelection) -> None:
        self._candidate_lookup_url = build_url(self._site_origin, _segments("byname", selection.name))
        self._candidate_name = selection.name
        self.candidate_collision_diagnostic: dict[str, object] | None = None
        self._operations = (
            (HttpMethod.POST, "/mgmt/system/user/login"),
            (HttpMethod.GET, "/" + "/".join(_TREE)),
            *((HttpMethod.GET, urlsplit(build_url(self._site_origin, _segments("byname", value))).path)
              for value in (selection.parent_name, selection.name)),
        )
    def arm_create(self) -> None:
        _require(not self.create_armed and self.create_count == 0, "create_already_authorized")
        self.create_armed = True
        self._operations = (*self._operations, (HttpMethod.POST, "/" + "/".join(_SITE_PATH)))
        self._authorization = SingleSiteAuthorization(self._site_origin, self._operations)

    def authorize_readback(self, identity: str) -> None:
        _require(self.create_count == 1, "readback_before_create")
        path = urlsplit(build_url(self._site_origin, _segments("byid", identity))).path
        self._authorization = SingleSiteAuthorization(
            self._site_origin, (*self._operations, (HttpMethod.GET, path)),
        )

    def send(self, request: BackendRequest) -> HttpResponse:
        if request.method == HttpMethod.POST and urlsplit(request.url).path == "/" + "/".join(_SITE_PATH):
            if not self.create_armed or self.create_count:
                raise BackendFailure(ErrorCategory.SAFETY_POLICY)
            self.create_count += 1
        response = super().send(request)
        if (
            request.method == HttpMethod.GET and request.url == self._candidate_lookup_url
            and response.status == 400
        ):
            self.candidate_collision_diagnostic = _candidate_error_diagnostic(response, self._candidate_name)
        return response


def _json(response: HttpResponse) -> object:
    try:
        return load_json(response.body.decode("utf-8"))
    except (UnicodeError, ValueError, RecursionError):
        raise SiteBlocked("unexpected_response_json") from None


def _get(manager: SessionManager, segments: tuple[str, ...]) -> HttpResponse:
    return manager.request(SessionRole.DESTINATION, HttpMethod.GET, segments)


def _site_object(payload: object, name: str) -> dict[str, object]:
    _require(
        isinstance(payload, dict) and ("status" not in payload or payload["status"] == "ok")
        and payload.get("name") == name and _text(payload.get("ormID")),
        "site_identity_missing_or_ambiguous",
    )
    return payload


def _site_parent_matches(payload: dict, parent_id: str, parent_is_root: bool) -> bool:
    return "parentOrmID" in payload and (
        payload["parentOrmID"] == parent_id or parent_is_root and payload["parentOrmID"] is None
    )


def _tree(payload: object) -> list[dict]:
    _require(isinstance(payload, dict), "unexpected_tree_response")
    records: list[dict] = []

    def visit(row: object, parent: str | None, depth: int) -> None:
        _require(isinstance(row, dict) and depth <= 64 and len(records) < 10000, "invalid_tree_or_limit")
        identifier = row.get("meIdentifier")
        _require(isinstance(identifier, dict), "tree_identity_missing")
        kind = identifier.get("managedElementClass")
        _require(kind in (_SITE, "com.radware.insite.model.device.Device"), "unclassified_tree_node")
        identity = identifier.get("managedElementID")
        _require(_text(identity) and isinstance(row.get("children"), list), "tree_identity_missing")
        _require(kind != _SITE or _text(row.get("name")), "tree_site_name_missing")
        _require("ormID" not in row or _text(row["ormID"]), "tree_native_identity_invalid")
        records.append({
            "identity": identity, "ormID": row.get("ormID"), "name": row.get("name"),
            "parent": parent, "parentOrmID": row.get("parentOrmID"),
            "parent_field_present": "parentOrmID" in row, "site": kind == _SITE,
        })
        for child in row["children"]:
            visit(child, identity, depth + 1)

    visit(payload, None, 0)
    counts = Counter(row["identity"] for row in records)
    _require(all(count == 1 for count in counts.values()), "duplicate_tree_identity")
    native_counts = Counter(row["ormID"] for row in records if row["ormID"] is not None)
    _require(all(count == 1 for count in native_counts.values()), "duplicate_tree_native_identity")
    _require(records[0]["site"], "tree_root_not_site")
    return records


def _lookup_candidate(
    manager: SessionManager, selection: SiteSelection, report: dict, backend: SingleSiteBackend,
) -> HttpResponse | None:
    report["failure_stage"] = "candidate_collision_lookup"
    try:
        response = _get(manager, _segments("byname", selection.name))
    except TransportError as error:
        if error.status == 400:
            diagnostic = backend.candidate_collision_diagnostic
            if (
                error.backend_failure is not None or error.cleanup_failed
                or diagnostic is None or diagnostic.get("m_00734_absence_signature_matches") is not True
            ):
                raise
            report["candidate_collision_diagnostic"] = diagnostic
        elif error.status != 404:
            raise
        response = None
    collision = None if response is None else _json(response)
    # Neither qualified M_00734, a 404 nor the legacy signature replaces the fresh tree check.
    absent = (
        response is None or (
            response.status == 200 and isinstance(collision, dict)
            and collision.get("status") == "error"
            and collision.get("message") == "There is no site with name " + selection.name
        )
    )
    return None if absent else response


def _parent_in_tree(tree: list[dict], selection: SiteSelection, parent_id: str) -> None:
    parents = [row for row in tree if row["site"] and row["name"] == selection.parent_name
               and (row["ormID"] if row["ormID"] is not None else row["identity"]) == parent_id]
    _require(len(parents) == 1, "parent_tree_identity_unverified")
    _require(sum(row["site"] and isinstance(row["name"], str)
                 and _name(row["name"]) == _name(selection.parent_name) for row in tree) == 1,
             "parent_name_ambiguous")
    if selection.parent_is_root:
        _require(parents[0] is tree[0], "parent_not_organization_root")


def _preflight(
    manager: SessionManager, selection: SiteSelection, report: dict, backend: SingleSiteBackend,
) -> tuple[str, frozenset[str]]:
    report["failure_stage"] = "parent_lookup"
    response = _get(manager, _segments("byname", selection.parent_name))
    _require(response.status == 200, "destination_parent_lookup_failed")
    parent = _site_object(_json(response), selection.parent_name)
    parent_id = parent["ormID"]
    _require(parent_id not in selection.source_identities, "destination_identity_matches_source_identity")
    if selection.parent_is_root:
        _require("parentOrmID" in parent and parent["parentOrmID"] is None, "destination_root_parent_unverified")
    _require(_lookup_candidate(manager, selection, report, backend) is None,
             "site_collision_or_absence_unqualified")
    report["failure_stage"] = "organization_tree_lookup"
    response = _get(manager, _TREE)
    _require(response.status == 200, "tree_preflight_failed")
    tree = _tree(_json(response))
    _parent_in_tree(tree, selection, parent_id)
    _require(not any(isinstance(row["name"], str) and _name(row["name"]) == _name(selection.name)
                     for row in tree), "fresh_tree_collision")
    identities = frozenset(value for row in tree for value in (row["identity"], row["ormID"])
                           if isinstance(value, str))
    report.pop("failure_stage")
    return parent_id, identities


def _readback(manager: SessionManager, backend: SingleSiteBackend, selection: SiteSelection, parent_id: str,
              identity: str, *, attempts: int = 3, interval: float = 0) -> bool:
    _require(identity not in selection.source_identities and identity != parent_id, "created_identity_invalid")
    backend.authorize_readback(identity)
    for attempt in range(attempts):
        if attempt and interval:
            time.sleep(interval)
        try:
            response = _get(manager, _segments("byid", identity))
        except TransportError as error:
            if error.status == 404:
                continue
            raise
        _require(response.status == 200, "readback_http_failure")
        site = _site_object(_json(response), selection.name)
        _require(site["ormID"] == identity and _site_parent_matches(site, parent_id, selection.parent_is_root)
                 and ("type" not in site or site["type"] == "Site"), "readback_identity_or_parent_mismatch")
        response = _get(manager, _TREE)
        _require(response.status == 200, "hierarchy_readback_failed")
        tree = _tree(_json(response))
        matches = [row for row in tree if row["site"] and row["name"] == selection.name]
        if not matches:
            continue
        _require(len(matches) == 1, "readback_ambiguous")
        site_row = matches[0]
        parent_rows = [row for row in tree if row["identity"] == site_row["parent"]]
        _require(
            (site_row["ormID"] if site_row["ormID"] is not None else site_row["identity"]) == identity
            and len(parent_rows) == 1 and parent_rows[0]["name"] == selection.parent_name
            and (parent_rows[0]["ormID"] if parent_rows[0]["ormID"] is not None
                 else parent_rows[0]["identity"]) == parent_id
            and (not site_row["parent_field_present"] or _site_parent_matches(site_row, parent_id, selection.parent_is_root))
            and (not selection.parent_is_root or parent_rows[0] is tree[0])
            and sum(isinstance(row["name"], str) and _name(row["name"]) == _name(selection.name)
                    for row in tree) == 1,
            "hierarchy_identity_or_parent_mismatch",
        )
        return True
    return False


def _interactive_approval(origin: str, reference: str) -> bool:
    print(f"EXPERIMENTAL single Site create: target {origin}; candidate {reference}.", file=sys.stderr)
    print("Unverified payload/omission, parent-ID, collision completeness and completion semantics. No retries or rollback.",
          file=sys.stderr)
    print(f"Authorize at most ONE Site create now? Type CREATE {reference} (default NO): ", end="", file=sys.stderr, flush=True)
    return sys.stdin.isatty() and sys.stdin.readline().rstrip("\r\n") == "CREATE " + reference


def _persist(stream: TextIO, report: dict) -> None:
    stream.seek(0)
    json.dump(report, stream, indent=2, allow_nan=False)
    stream.truncate()
    stream.flush()
    os.fsync(stream.fileno())


def _close_backend(backend: SingleSiteBackend, report: dict) -> None:
    try:
        backend.close()
    except BackendFailure:
        report["issue_codes"].append("local_session_cleanup_failed")
        report["status"] = "indeterminate" if report["create_attempts"] else "error"
        report["manual_reconciliation_required"] = bool(report["create_attempts"])


def site_attempt_guard(profile: DiscoveryProfile, selection: SiteSelection) -> Path:
    origin = urlsplit(profile.transport.base_url)
    key = hashlib.sha256(json.dumps([
        [origin.scheme, origin.hostname, origin.port or 443], _name(selection.name),
    ], separators=(",", ":")).encode()).hexdigest()
    return profile.output_directory / (".ccv-site-attempt-" + key + ".json")


def reserve_site_attempt(profile: DiscoveryProfile, selection: SiteSelection, filename: str) -> None:
    descriptor = os.open(site_attempt_guard(profile, selection), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as reservation:
        json.dump({"source_reference": selection.reference, "state": "reserved-reconcile-before-reuse",
                   "report_file": filename}, reservation)
        reservation.flush()
        os.fsync(reservation.fileno())
    if os.name != "nt":
        descriptor = os.open(profile.output_directory, os.O_RDONLY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)


def run_single_site(
    profile_path: str, credentials_path: str, source_path: str, comparison_path: str,
    snapshot_path: str, reference: str, *, execute: bool = False, target_version: str | None = None,
    approve: Callable[[str, str], bool] | None = None,
) -> tuple[dict, ExitStatus]:
    selection = load_selection(source_path, comparison_path, snapshot_path, reference)
    profile = DiscoveryProfile.read(profile_path)
    _require(target_version is None or bool(re.fullmatch(r"10\.[0-9]+(?:\.[0-9]+)*(?:-[0-9]+)?", target_version)),
             "unsupported_target_declaration")
    require_execution_exception(profile.transport.base_url, profile.transport.verify_tls, credentials_path)
    message = warning(profile.transport.verify_tls)
    if message:
        print(message, file=sys.stderr)
    report = {
        "schema_version": 1, "domain": "single-site-migration-report", "operation": "single-site-migration",
        "status": "error", "read_only": True, "offline_only": False,
        "migration_ready": False, "import_file_compatible": False,
        "configuration_writes_authorized": False, "authenticated": False,
        "execution_authorized": False, "create_attempts": 0, "manual_reconciliation_required": False,
        "source_reference": reference, "target_origin": profile.transport.base_url,
        "target_version": target_version, "target_version_evidence": "operator-declared-not-api-verified",
        "compatibility": "experimental-unverified", "risk_codes": list(_RISKS),
        "tls": execution_tls(profile.transport.verify_tls),
        "input_bindings": {
            "source": selection.source_digest, "comparison": selection.comparison_digest,
            "destination_snapshot": selection.snapshot_digest,
        },
        "request_preview": {
            "method": "POST", "path": "/" + "/".join(_SITE_PATH), "body_generated": False,
            "fields": {"name": "unchanged-protected-source-name", "parentOrmID": "fresh-protected-destination-ormID"},
        },
        "issue_codes": [],
        "collected_at": datetime.now(timezone.utc).isoformat(),
    }
    backend = SingleSiteBackend(profile, selection)
    strategy = _DiscoveryAuthentication()
    filename = "ccv-single-site-" + uuid4().hex + ".json"
    report["report_file"] = filename
    guard = site_attempt_guard(profile, selection)
    status = ExitStatus.VALIDATION_FAILED
    try:
        descriptor = os.open(profile.output_directory / filename, os.O_CREAT | os.O_EXCL | os.O_RDWR, 0o600)
        with os.fdopen(descriptor, "w+", encoding="utf-8") as output:
            try:
                _persist(output, report)
                _require(not guard.exists(), "prior_attempt_requires_manual_reconciliation")
                with SessionManager(lambda: backend, _Credentials(credentials_path)) as manager:
                    manager.initialize(
                        _UnknownVersionRequest(SessionRole.DESTINATION, "cyber-controller", "unknown",
                                               CredentialReference("cc-destination-discovery")),
                        profile.transport, strategy=strategy,
                    )
                    manager.authenticate(SessionRole.DESTINATION)
                    report["authenticated"] = True
                    parent_id, _ = _preflight(manager, selection, report, backend)
                    report.update(status="dry-run-ready", parent_resolved=True, collision_check_passed=True)
                    if not execute:
                        status = ExitStatus.SUCCESS
                    elif not (approve or _interactive_approval)(profile.transport.base_url, reference):
                        report.update(status="cancelled", issue_codes=["operator_declined_or_no_terminal"])
                    else:
                        # Recheck after the human decision, within the same authenticated session.
                        fresh_parent_id, prior_identities = _preflight(manager, selection, report, backend)
                        _require(fresh_parent_id == parent_id, "parent_changed_after_approval")
                        reserve_site_attempt(profile, selection, filename)
                        report.update(execution_authorized=True, configuration_writes_authorized=True,
                                      read_only=False, status="indeterminate", create_attempts=1,
                                      manual_reconciliation_required=True)
                        _persist(output, report)
                        backend.arm_create()
                        response = manager.request(
                            SessionRole.DESTINATION, HttpMethod.POST, _SITE_PATH,
                            headers={"Content-Type": "application/json"},
                            body=json.dumps({"name": selection.name, "parentOrmID": parent_id}).encode(),
                        )
                        report["create_http_status"] = response.status
                        _require(response.status in (200, 201), "create_http_outcome_unqualified")
                        created = _site_object(_json(response), selection.name)
                        _require(created["ormID"] not in prior_identities, "created_identity_preexisted")
                        if "parentOrmID" in created:
                            _require(_site_parent_matches(created, parent_id, selection.parent_is_root),
                                     "create_response_parent_mismatch")
                        verified = _readback(manager, backend, selection, parent_id, created["ormID"])
                        _require(verified, "bounded_readback_incomplete")
                        report.update(status="single-site-verified", manual_reconciliation_required=False,
                                      readback_verified=True)
                        status = ExitStatus.SUCCESS
            except SiteBlocked as error:
                report["issue_codes"] = [error.code]
                report["status"] = "indeterminate" if report["create_attempts"] else "blocked"
            except AuthenticationError as error:
                reason = error.failure.transport_reason
                report["issue_codes"] = [reason.value if reason is not None else error.failure.category.value]
                report["status"] = "indeterminate" if report["create_attempts"] else "error"
            except TransportError as error:
                report["issue_codes"] = [error.category.value]
                if error.status is not None:
                    report["http_status"] = error.status
                if (
                    error.status == 400 and report.get("failure_stage") == "candidate_collision_lookup"
                    and backend.candidate_collision_diagnostic is not None
                ):
                    report["candidate_collision_diagnostic"] = backend.candidate_collision_diagnostic
                report["status"] = "indeterminate" if report["create_attempts"] else "error"
            except ContractValidationError:
                report["issue_codes"] = ["response_or_path_contract_failure"]
                report["status"] = "indeterminate" if report["create_attempts"] else "error"
            except KeyboardInterrupt:
                report["issue_codes"] = ["execution_interrupted"]
                report["status"] = "indeterminate" if report["create_attempts"] else "cancelled"
            finally:
                strategy.clear()
                _close_backend(backend, report)
            _persist(output, report)
    except OSError:
        _close_backend(backend, report)
        report["issue_codes"] = ["local_report_or_attempt_guard_failure"]
        report["status"] = "indeterminate" if report["create_attempts"] else "error"
        status = ExitStatus.INPUT_ERROR
    if report["status"] not in ("dry-run-ready", "single-site-verified"):
        status = ExitStatus.VALIDATION_FAILED if status == ExitStatus.SUCCESS else status
    return report, status
