"""Backup-bound orchestration of existing qualified migration stages."""

import copy
import hashlib
import json
import os
import sys
from pathlib import Path
from urllib.parse import urlsplit
from uuid import uuid4

from ._json import load_json
from .backup_inventory import HANDLERS, BackupInventory, InventoryLimits, discover_backup
from .contracts import ExitStatus
from .destination_discovery import DiscoveryProfile, run_destination_discovery
from .offline_inputs import OfflineInputs
from .single_site import SiteBlocked, _require, _text, site_attempt_guard
from .site_comparison import _destination, compare_sites
from .site_migration import (
    _journal_context, _origin_lock, _private_descriptor, _read_journal, _write_private,
    load_plan, run_site_migration,
)


def _context(profile: DiscoveryProfile, inventory: BackupInventory) -> tuple[dict, Path, Path]:
    parsed = urlsplit(profile.transport.base_url)
    origin = [parsed.scheme, parsed.hostname, parsed.port or 443]
    digest = hashlib.sha256(json.dumps(origin).encode()).hexdigest()[:16]
    return (
        {"backup_sha256": inventory.digest, "origin": origin},
        profile.output_directory / f"ccv-migration-{inventory.digest[:32]}-{digest}.journal.json",
        profile.output_directory / f".ccv-sites-{digest}.lock",
    )


def _read_state(path: Path, binding: dict) -> dict:
    with os.fdopen(_private_descriptor(path, os.O_RDONLY), "r", encoding="utf-8") as stream:
        _require(os.fstat(stream.fileno()).st_size <= 16 * 1024 * 1024, "backup_state_size_limit")
        try:
            state = load_json(stream.read())
        except (ValueError, RecursionError):
            raise SiteBlocked("backup_state_malformed") from None
    _require(isinstance(state, dict) and state.get("schema_version") == 1
             and state.get("domain") == "protected-backup-migration-state" and state.get("binding") == binding,
             "backup_state_binding_mismatch")
    for name in ("comparison_file", "snapshot_file"):
        value = state.get(name)
        _require(value is None or isinstance(value, str) and Path(value).name == value
                 and "/" not in value and "\\" not in value and value not in ("", ".", ".."),
                 "backup_state_artifact_path_invalid")
    _require(type(state.get("site_stage_started")) is bool, "backup_state_stage_invalid")
    _require("root_identity" in state and (state["root_identity"] is None or _text(state["root_identity"])),
             "backup_state_root_identity_invalid")
    return state


def _root_approval(source_name: str, destination_name: str) -> bool:
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        print("Root mapping needs an interactive review; no writes authorized.", file=sys.stderr)
        return False
    if os.name != "nt":
        try:
            import readline
        except ImportError:
            print("Root review cancelled: terminal editing unavailable.", file=sys.stderr)
            return False
        readline.set_auto_history(False)
    print("Review root association: " + json.dumps(source_name) + " -> " + json.dumps(destination_name))
    try:
        while True:
            answer = input("Confirm this root association? [y/N] (default No): ").strip().casefold()
            if answer in ("y", "yes"):
                return True
            if answer in ("", "n", "no"):
                return False
            print("Please enter Y/Yes or N/No.")
    except (EOFError, KeyboardInterrupt, OSError, ValueError):
        print("Root review cancelled: input ended or was interrupted.", file=sys.stderr)
        return False


def _organization(inventory: BackupInventory) -> tuple[Path, dict] | None:
    module = next(item for item in inventory.report["modules"] if item["domain"] == "organization-tree")
    paths = [(path, payload) for path, payload in inventory.artifacts
             if payload["domain"] == "vision-organization-tree"]
    if module["availability"] not in ("AVAILABLE", "EMPTY"):
        return None
    _require(len(paths) <= 1, "multiple_organization_trees_require_explicit_scope")
    return paths[0] if paths else None


def _aggregate(modules: list[dict], *, mode: str, site_report: dict | None, issues: list[str]) -> str:
    if site_report is not None:
        organization = next(item for item in modules if item["domain"] == "organization-tree")
        count = site_report.get("counts", {}).get("verified_this_run", 0)
        organization["verified_records"] = count + organization.get("verified_device_inventory_records", 0)
        if (not issues and count == organization["sites"] and organization["devices"] == 0
                and organization["unprojected_fields"] == 0
                and organization["records"] == organization["sites"]
                and site_report["status"] in ("batch-verified", "reconciled", "dry-run-ready")):
            organization.update(migration_status="COMPLETED", issue_codes=[])
        elif organization["verified_records"]:
            organization["migration_status"] = "PARTIAL"
    scoped = [item for item in modules if item["availability"] != "ABSENT"]
    complete = bool(scoped) and all(item["migration_status"] == "COMPLETED" for item in scoped) and not issues
    if complete:
        return "COMPLETED"
    if any(item["verified_records"] for item in scoped):
        return "PARTIAL"
    return "BLOCKED"


def _print_modules(modules: list[dict]) -> None:
    known = {handler.domain for handler in HANDLERS.values()}
    for module in modules:
        if module["domain"] not in known:
            continue
        print(f"{module['domain']}: records={module['records'] if module['records'] is not None else 'unknown'}; "
              f"{module['availability']}; {module['migration_status']}")
    unknown = sum(module["domain"] not in known for module in modules)
    if unknown:
        print(f"Additional unqualified modules: {unknown}; details saved in report.")


def _print_summary(report: dict) -> None:
    print(f"Destination: {report['target_origin']}; operation: {report['mode']}; preflight: {report['preflight_status']}")
    _print_modules(report["modules"])
    counts = report["counts"]
    print(f"Sites {counts['total']}; Created {counts['created']}; Verified {counts['verified']}; "
          f"Existing {counts['already_existing']}; Failed {counts['failed']}; Pending {counts['pending']}")
    print("Configuration migration: " + report["migration_status"])
    if report["issue_codes"]:
        print("Issues: " + ", ".join(report["issue_codes"]))
    print("Report: " + report["report_file"])


def run_migration(
    profile_path: str, credentials_path: str, backup: str, *, mode: str = "dry-run",
    target_version: str | None = None, limits: InventoryLimits | None = None,
    operation_delay: float = 1, readback_interval: float = 1, readback_attempts: int = 3,
    approve=None, approve_root=None, terminal: bool = False,
) -> tuple[dict, ExitStatus]:
    _require(mode in ("dry-run", "execute", "resume", "reconcile", "status", "lab-reset"), "invalid_migration_mode")
    inventory = discover_backup(backup, limits=limits)
    profile = DiscoveryProfile.read(profile_path)
    binding, state_path, lock_path = _context(profile, inventory)
    profile.output_directory.mkdir(parents=True, exist_ok=True)
    organization = _organization(inventory)
    modules = copy.deepcopy(inventory.report["modules"])
    report = {
        "schema_version": 1, "operation": "backup-driven-migration", "mode": mode,
        "read_only": True, "configuration_writes_authorized": False, "create_attempts": 0,
        "target_origin": profile.transport.base_url, "target_version": target_version,
        "compatibility": "experimental-sites-only-not-version-certified",
        "scope": "selected-backup-records-only-source-enumeration-completeness-unverified",
        "inventory": inventory.report, "modules": modules, "issue_codes": [],
        "migration_status": "BLOCKED", "preflight_status": "NOT_RUN",
        "report_file": f"ccv-migration-report-{uuid4().hex}.json", "journal_file": state_path.name,
        "counts": {"total": next(item["sites"] for item in modules if item["domain"] == "organization-tree"),
                   "created": 0, "verified": 0, "already_existing": 0, "failed": 0,
                   "pending": next(item["sites"] for item in modules if item["domain"] == "organization-tree")},
        "module_reports": {},
    }
    site_report = None
    try:
        _require(any(item["availability"] in ("AVAILABLE", "EMPTY") for item in modules),
                 "no_supported_backup_modules_available")
        if mode == "lab-reset":
            raise SiteBlocked("lab_delete_or_definitive_absence_contract_unqualified_use_reconcile")
        with _origin_lock(lock_path):
            state = _read_state(state_path, binding) if state_path.exists() else None
        if state is None:
            _require(mode in ("dry-run", "execute"), "backup_state_missing_use_original_dry_run_or_historical_site_reconcile")
            discovery_report, discovery_status = run_destination_discovery(profile_path, credentials_path)
            _require(discovery_status == ExitStatus.SUCCESS and discovery_report.get("snapshot_file"),
                     "destination_capability_discovery_failed")
            inputs = OfflineInputs(Path.cwd())
            snapshot_path = profile.output_directory / discovery_report["snapshot_directory"] / discovery_report["snapshot_file"]
            snapshot = inputs.read(str(snapshot_path), "destination", base=Path.cwd())
            destination_root = _destination(snapshot)[1]
            destination = destination_root["native"]
            _require(_text(destination.get("name"))
                     and _text(destination["meIdentifier"].get("managedElementID"))
                     and destination["meIdentifier"].get("managedElementClass") == "com.radware.insite.model.device.Site"
                     and not (set(destination_root["issue_codes"]) - {"additional_fields_not_projected"}),
                     "destination_root_capability_unqualified")
            state = {
                "schema_version": 1, "domain": "protected-backup-migration-state", "binding": binding,
                "site_stage_started": False, "comparison_file": None,
                "root_identity": destination.get("ormID", destination["meIdentifier"].get("managedElementID")),
                "snapshot_file": f"ccv-migration-snapshot-{uuid4().hex}.json",
            }
            _write_private(profile.output_directory / state["snapshot_file"], snapshot)
            if organization is not None and organization[1]["tree"] != []:
                source_path, source = organization
                root = source["tree"]
                _require(isinstance(root, dict) and _text(root.get("name"))
                         and _text(destination.get("name")), "reviewable_unique_root_required")
                source_name, destination_name = root["name"], destination["name"]
                if source_name != destination_name:
                    confirmation = _root_approval if approve_root is None else approve_root
                    _require(confirmation(source_name, destination_name), "root_mapping_review_required")
                comparison = compare_sites(source, snapshot, source_root_name=source_name,
                                           destination_root_name=destination_name, confirm_root_mapping=True)
                comparison["input_bindings"] = [
                    {"slot": "source-organization-tree", "sha256": hashlib.sha256(source_path.read_bytes()).hexdigest()},
                    {"slot": "destination-organization-sites",
                     "sha256": hashlib.sha256((profile.output_directory / state["snapshot_file"]).read_bytes()).hexdigest()},
                ]
                state["comparison_file"] = f"ccv-migration-comparison-{uuid4().hex}.json"
                _write_private(profile.output_directory / state["comparison_file"], comparison)
                plan = load_plan(str(source_path), str(profile.output_directory / state["comparison_file"]),
                                 str(profile.output_directory / state["snapshot_file"]))
                state["site_plan_sha256"] = plan.digest
                state["site_count"] = len(plan.sites)
            with _origin_lock(lock_path):
                _require(not state_path.exists(), "backup_state_initialized_concurrently_repeat_read_only_plan")
                _write_private(state_path, state)
        report["preflight_status"] = "DISCOVERED"
        if organization is not None and state["comparison_file"] is not None:
            source_path, _ = organization
            comparison_path = profile.output_directory / state["comparison_file"]
            snapshot_path = profile.output_directory / state["snapshot_file"]
            plan = load_plan(str(source_path), str(comparison_path), str(snapshot_path))
            _require(plan.digest == state.get("site_plan_sha256"), "backup_site_plan_binding_changed")
            original_snapshot = OfflineInputs(Path.cwd()).read(str(snapshot_path), "destination")
            original_root = _destination(original_snapshot)[1]["native"]
            _require(state["root_identity"] == original_root.get(
                "ormID", original_root["meIdentifier"].get("managedElementID")),
                "backup_state_root_snapshot_mismatch")
            _require(discover_backup(backup, limits=limits).digest == inventory.digest, "backup_changed_after_planning")
            report["counts"]["total"] = len(plan.sites)
            report["counts"]["pending"] = len(plan.sites)
            if terminal:
                print(f"Reviewed backup: {inventory.report['file_count']} files; {len(plan.sites)} Sites; "
                      f"destination {profile.transport.base_url}.")
                _print_modules(modules)
                print("Only qualified experimental Site creation is available; other populated domains remain BLOCKED.")
            if mode in ("execute", "resume", "reconcile"):
                site_binding, site_journal, _ = _journal_context(profile, plan)
                if mode == "execute":
                    _require(not state["site_stage_started"] and not site_journal.exists(),
                             "existing_site_stage_requires_resume_or_reconcile")
            site_mode = "dry-run" if mode == "status" else mode
            if mode == "resume" and not site_journal.exists():
                _require(not state["site_stage_started"]
                         and not any(site_attempt_guard(profile, item.selection).exists() for item in plan.sites),
                         "missing_site_journal_with_post_evidence_blocks_recovery")
                site_mode = "execute"
            observed_mapping: dict[str, str] = {}
            site_report, _ = run_site_migration(
                profile_path, credentials_path, str(source_path), str(comparison_path), str(snapshot_path),
                mode=site_mode, target_version=target_version,
                operation_delay=operation_delay, readback_interval=readback_interval,
                readback_attempts=readback_attempts, approve=approve, terminal=terminal,
                expected_root_identity=state["root_identity"], mapping_observer=observed_mapping.update,
            )
            report["module_reports"]["organization-tree"] = site_report["report_file"]
            report["counts"].update({key: site_report["counts"].get(key, 0) for key in report["counts"]})
            report.update(create_attempts=site_report["create_attempts"],
                          read_only=site_report["read_only"],
                          configuration_writes_authorized=site_report["configuration_writes_authorized"])
            report["issue_codes"].extend(site_report["issue_codes"])
            report["preflight_status"] = site_report["status"].upper()
            if mode in ("execute", "resume", "reconcile"):
                _, site_journal, _ = _journal_context(profile, plan)
                if site_journal.exists():
                    with _origin_lock(lock_path):
                        state["site_stage_started"] = True
                        _write_private(state_path, state)
            if mode == "status":
                site_binding, site_journal, _ = _journal_context(profile, plan)
                if site_journal.exists():
                    with _origin_lock(lock_path):
                        history = _read_journal(site_journal, site_binding, plan)
                    if observed_mapping:
                        _require(observed_mapping.get(plan.root_reference) == history["root_identity"]
                                 and all(not entry["verified"] or observed_mapping.get(reference) == entry["destination_identity"]
                                         for reference, entry in history["sites"].items()),
                                 "journal_destination_identity_changed")
                        for key in ("created", "verified", "already_existing"):
                            report["counts"][key] = sum(entry[key] for entry in history["sites"].values())
                    if history["incomplete_operation"] is not None:
                        report["issue_codes"].append("historical_post_requires_read_only_reconciliation")
            if any(item["domain"] == "organization-tree" and item["devices"] for item in modules):
                from .device_migration import run_device_migration

                selected = {
                    folder: tuple(path for path, payload in inventory.artifacts
                                  if payload["domain"] == schema
                                  and payload["request"].get("path_template") ==
                                  "/mgmt/system/config/tree/device/byip/{ip}")
                    for folder, schema in (
                        ("controller-objects", "vision-controller-object-lookup"),
                        ("device-access", "vision-device-access"),
                    )
                }
                try:
                    device_report, _ = run_device_migration(
                        profile_path, credentials_path, str(source_path), str(comparison_path), str(snapshot_path),
                        mode="preview", target_version=target_version, backup_artifacts=selected,
                    )
                    report["module_reports"]["devices"] = device_report["report_file"]
                    report["device_inventory"] = device_report["inventory"]
                    report["device_issue_codes"] = device_report["issue_codes"]
                    verified_devices = device_report["counts"]["verified"]
                    organization_module = next(item for item in modules if item["domain"] == "organization-tree")
                    organization_module["verified_device_inventory_records"] = verified_devices
                    organization_module["verified_records"] += verified_devices
                    if verified_devices:
                        organization_module["migration_status"] = "PARTIAL"
                except SiteBlocked as error:
                    report["device_issue_codes"] = [error.code]
        elif organization is None and any(item["domain"] == "organization-tree" and item["availability"] != "ABSENT"
                                          for item in modules):
            report["issue_codes"].append("organization_input_unavailable_or_unqualified")
        for item in modules:
            if item["unprojected_fields"]:
                item["issue_codes"].append("source_fields_unprojected_not_applied")
    except SiteBlocked as error:
        report["issue_codes"].append(error.code)
        report["preflight_status"] = "BLOCKED"
    report["migration_status"] = _aggregate(modules, mode=mode, site_report=site_report, issues=report["issue_codes"])
    if mode == "dry-run":
        report["plan_status"] = "READY" if report["preflight_status"] == "DRY-RUN-READY" else report["preflight_status"]
        if site_report is not None and site_report["counts"]["verified_this_run"] < len(plan.sites):
            organization_module = next(item for item in modules if item["domain"] == "organization-tree")
            organization_module["migration_status"] = "PLANNED" if site_report["status"] == "dry-run-ready" else "BLOCKED"
    report["issue_codes"] = sorted(set(report["issue_codes"]))
    _write_private(profile.output_directory / report["report_file"], report)
    if terminal:
        _print_summary(report)
    success = report["migration_status"] == "COMPLETED" or mode == "dry-run" and report.get("plan_status") == "READY"
    return report, ExitStatus.SUCCESS if success else ExitStatus.VALIDATION_FAILED
