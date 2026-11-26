"""Organization Device inventory and fail-closed, read-only migration qualification."""

import hashlib
import json
import os
import re
import sys
from collections import Counter
from contextlib import ExitStack
from dataclasses import dataclass
from ipaddress import ip_address
from pathlib import Path
from urllib.parse import urlsplit
from uuid import uuid4

from ._json import load_json
from .authentication import AuthenticationError, CredentialReference, SessionRole
from .contracts import ContractValidationError, ExitStatus
from .destination_discovery import DiscoveryProfile, _Credentials, _DiscoveryAuthentication, _UnknownVersionRequest, _TREE
from .http_backend import DestinationReadAuthorization, StdlibHttpBackend
from .offline_inputs import OfflineInputs
from .sessions import SessionManager
from .single_site import (
    SiteBlocked, _close_backend, _get, _json, _name, _require, _text, _tree, load_site_evidence,
)
from .site_migration import (
    BatchSiteBackend, SitePlan, _fresh_root, _inspect, _journal_context, _origin_lock,
    _private_descriptor, _read_journal, _row_id, _validate_mappings, _write_private, load_plan,
)
from .tls_policy import execution_tls, require_execution_exception, warning
from .transport import HttpMethod, TransportError, build_url
from .vision_tree_preview import _tree_rows, inspect_vision_tree


_DEVICE_PATH = ("mgmt", "system", "config", "tree", "device", "byip")
_DEVICE_CLASS = "com.radware.insite.model.device.Device"
_CONTRACT_BLOCK = "device_inventory_only_create_contract_unqualified"


def _ip(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    try:
        return str(ip_address(value))
    except ValueError:
        return None


@dataclass(frozen=True, repr=False)
class Device:
    reference: str
    parent_reference: str | None
    name: str | None
    kind: str | None
    address: str | None
    controller_reference: str | None
    access_reference: str | None
    unsupported_fields: int
    unprojected_fields: int
    issues: tuple[str, ...]


@dataclass(frozen=True, repr=False)
class DevicePlan:
    sites: SitePlan
    devices: tuple[Device, ...]
    binding: dict
    digest: str
    inventory: dict
    source_identities: frozenset[str]


def load_device_plan(source_path: str, comparison_path: str, snapshot_path: str) -> DevicePlan:
    sites = load_plan(source_path, comparison_path, snapshot_path)
    evidence = load_site_evidence(source_path, comparison_path, snapshot_path)
    inputs = OfflineInputs(Path.cwd())
    source = inputs.read(source_path, "organization", base=Path.cwd())
    _require(inputs.bindings[0]["sha256"] == evidence.digests[0] == sites.binding["source_sha256"]
             and evidence.digests[1] == sites.binding["comparison_sha256"]
             and evidence.digests[2] == sites.binding["snapshot_sha256"], "device_source_binding_changed")
    inspection = inspect_vision_tree(source)
    root = Path(source_path).absolute().parent.parent
    records: dict[str, list[dict]] = {}
    byte_count = 0
    for folder, domain in (("controller-objects", "vision-controller-object-lookup"),
                           ("device-access", "vision-device-access")):
        directory = root / folder
        _require(not directory.is_symlink(), "unsafe_device_backup_directory")
        paths = sorted(directory.glob("device-by-ip-*.json"))
        _require(len(paths) <= 10000, "device_inventory_limit")
        records[folder] = []
        for index, path in enumerate(paths):
            _require(not path.is_symlink() and path.is_file(), "unsafe_device_backup_file")
            byte_count += path.stat().st_size
            _require(path.stat().st_size <= 4 * 1024 * 1024 and byte_count <= 64 * 1024 * 1024,
                     "device_inventory_size_limit")
            payload = inputs.read(str(path), f"{folder}-{index + 1}")
            _require(isinstance(payload, dict) and payload.get("schema_version") == 1
                     and payload.get("domain") == domain and payload.get("source") == source["source"],
                     "device_backup_provenance_mismatch")
            request = payload.get("request")
            rows = payload.get("objects")
            _require(isinstance(request, dict) and request.get("method") == "GET"
                     and request.get("path_template") == "/" + "/".join((*_DEVICE_PATH, "{ip}"))
                     and isinstance(rows, list) and len(rows) == 1 and isinstance(rows[0], dict),
                     "device_backup_contract_mismatch")
            row = rows[0]
            setup = row.get("deviceSetup")
            access = row.get("deviceAccess") if folder == "device-access" else (
                setup.get("deviceAccess") if isinstance(setup, dict) else None
            )
            target = _ip(request.get("target"))
            _require(target is not None and _text(row.get("ormID")) and isinstance(access, dict)
                     and _ip(access.get("managementIp")) == target, "device_backup_identity_unqualified")
            records[folder].append({
                "reference": f"{folder}-record-{index + 1}", "address": target,
                "identity": row["ormID"], "name": row.get("name"), "type": row.get("type"),
                "unsupported_fields": len(set(access) - {"managementIp"}),
                "unprojected_fields": len(set(row) - {"ormID", "name", "type", "deviceSetup", "deviceAccess"}),
            })
    controllers, access = records["controller-objects"], records["device-access"]
    controller_ids = Counter(row["identity"] for row in controllers)
    access_ids = Counter(row["identity"] for row in access)
    native = [(node, row) for node, row in zip(inspection["nodes"], evidence.rows, strict=True)
              if node["kind"] == "device"]
    addresses = Counter(_ip(row.get("managementIp")) for _, row in native)
    names = Counter(_name(row["name"]) for _, row in native if _text(row.get("name")))
    devices = []
    associated_controllers, associated_access = set(), set()
    parent_refs = {sites.root_reference, *(site.selection.reference for site in sites.sites)}
    for node, row in native:
        address = _ip(row.get("managementIp"))
        name, kind = row.get("name"), row.get("type")
        parent = node["observed_container_parent"]
        parent_ref = None if parent is None else "source:" + parent
        issues = set(node["issue_codes"]) - {
            "unknown_fields_unverified", "device_type_access_and_identity_association_unverified",
            "explicit_parent_semantics_unverified",
        }
        if address is None:
            issues.add("device_management_ip_missing_or_invalid")
        elif addresses[address] != 1:
            issues.add("duplicate_source_device_ip")
        if not _text(name) or not _text(kind):
            issues.add("device_name_or_type_missing")
        elif names[_name(name)] != 1:
            issues.add("duplicate_source_device_name")
        if parent_ref not in parent_refs:
            issues.add("device_source_parent_unresolved")
        candidates = [record for record in controllers if address is not None and record["address"] == address]
        controller = candidates[0] if len(candidates) == 1 else None
        if controller is None:
            issues.add("device_controller_association_missing_or_ambiguous")
        elif (controller_ids[controller["identity"]] != 1 or controller["name"] != name
              or controller["type"] != kind):
            issues.add("device_controller_association_conflict")
            controller = None
        access_candidates = [] if controller is None else [
            record for record in access if record["address"] == address and record["identity"] == controller["identity"]
        ]
        access_record = access_candidates[0] if len(access_candidates) == 1 else None
        if access_record is None or access_ids[access_record["identity"]] != 1:
            issues.add("device_access_association_missing_or_ambiguous")
            access_record = None
        if controller is not None:
            associated_controllers.add(controller["reference"])
        if access_record is not None:
            associated_access.add(access_record["reference"])
        devices.append(Device(
            "source:" + node["reference"], parent_ref, name if _text(name) else None,
            kind if _text(kind) else None, address,
            None if controller is None else controller["reference"],
            None if access_record is None else access_record["reference"],
            0 if access_record is None else access_record["unsupported_fields"],
            node["unknown_field_count"] + (0 if controller is None else controller["unprojected_fields"]),
            tuple(sorted(issues)),
        ))
    binding = {"site_plan": sites.binding, "backup_inputs": inputs.bindings}
    digest = hashlib.sha256(json.dumps(binding, sort_keys=True).encode()).hexdigest()
    inventory = {
        "organization_devices": len(devices), "controller_object_records": len(controllers),
        "device_access_records": len(access),
        "controller_minus_organization_record_count": len(controllers) - len(devices),
        "access_minus_organization_record_count": len(access) - len(devices),
        "unmatched_controller_records": sorted(set(row["reference"] for row in controllers) - associated_controllers),
        "unmatched_access_records": sorted(set(row["reference"] for row in access) - associated_access),
        "source_associations": "corroborated-name-type-query-ip-candidates-not-native-id-equivalence",
        "cross_namespace_identity_bridge_verified": False,
    }
    return DevicePlan(
        sites, tuple(devices), binding, digest, inventory,
        evidence.source_identities | frozenset(record["identity"] for record in [*controllers, *access]),
    )


class DeviceReadBackend(BatchSiteBackend):
    def __init__(self, profile: DiscoveryProfile, selection) -> None:
        self._site_origin = profile.transport.base_url
        self.create_armed = False
        self.create_count = 0
        self._select_read_scope(selection)
        StdlibHttpBackend.__init__(
            self, allow_live=True, authorization=DestinationReadAuthorization(self._site_origin, self._operations),
            max_response_bytes=16 * 1024 * 1024,
            allow_unverified_destination_discovery=profile.transport.unverified_destination_discovery,
        )

    def arm_create(self) -> None:
        raise SiteBlocked("device_configuration_write_forbidden")

    def select(self, selection) -> None:
        super().select(selection)
        self._authorization = DestinationReadAuthorization(self._site_origin, self._operations)

    def authorize_get_targets(self, targets: tuple[str, ...]) -> None:
        operations = tuple(dict.fromkeys((
            *self._authorization.operations, *((HttpMethod.GET, target) for target in targets),
        )))
        try:
            authorization = DestinationReadAuthorization(self._site_origin, operations)
        except ValueError:
            raise SiteBlocked("device_configuration_write_forbidden") from None
        self._authorization = authorization

    def authorize_readback(self, identity: str) -> None:
        super().authorize_readback(identity)
        self._authorization = DestinationReadAuthorization(self._site_origin, self._authorization.operations)


def _check_destination(manager, backend, plan: DevicePlan, device: Device, mapping: dict[str, str]) -> str | None:
    path = urlsplit(build_url(backend._site_origin, (*_DEVICE_PATH, device.address))).path
    backend.authorize_get_targets((path,))
    try:
        response = _get(manager, (*_DEVICE_PATH, device.address))
        _require(response.status == 200, "device_lookup_http_unqualified")
        found = _json(response)
    except TransportError as error:
        if error.status != 404 or error.backend_failure is not None or error.cleanup_failed:
            raise
        found = None
    response = _get(manager, _TREE)
    _require(response.status == 200, "device_tree_lookup_failed")
    payload = _json(response)
    tree = _tree(payload)
    _validate_mappings(tree, plan.sites, mapping)
    rows = _tree_rows(payload)
    candidates = [(node, row) for node, row in zip(tree, rows, strict=True)
                  if _ip(row.get("managementIp")) == device.address or (
                      _text(row.get("name")) and _name(row["name"]) == _name(device.name)
                  )]
    if found is None:
        _require(not candidates, "device_fresh_tree_collision")
        return None
    _require(isinstance(found, dict) and found.get("status", "ok") == "ok"
             and found.get("name") == device.name and found.get("type") == device.kind
             and _text(found.get("ormID")), "device_lookup_identity_conflict")
    setup = found.get("deviceSetup")
    access = setup.get("deviceAccess") if isinstance(setup, dict) else None
    _require(isinstance(access, dict) and _ip(access.get("managementIp")) == device.address,
             "device_lookup_address_unverified")
    identity = found["ormID"]
    _require(identity not in plan.source_identities
             and identity not in mapping.values(), "device_destination_identity_reused")
    _require(len(candidates) == 1, "device_tree_identity_missing_or_ambiguous")
    node, native = candidates[0]
    parent_id = mapping.get(device.parent_reference)
    parents = [row for row in tree if _row_id(row) == parent_id and row["site"]]
    _require(not node["site"] and native["meIdentifier"]["managedElementClass"] == _DEVICE_CLASS
             and _row_id(node) == identity and native.get("name") == device.name
             and native.get("type") == device.kind and _ip(native.get("managementIp")) == device.address
             and len(parents) == 1 and node["parent"] == parents[0]["identity"]
             and found.get("parentOrmID") == parent_id
             and (not node["parent_field_present"] or node["parentOrmID"] == parent_id),
             "device_identity_or_site_association_unverified")
    return identity


def _load_device_journal(path: Path, binding: dict, references: list[str]) -> dict:
    descriptor = _private_descriptor(path, os.O_RDONLY)
    with os.fdopen(descriptor, "r", encoding="utf-8") as stream:
        try:
            raw = stream.read(16 * 1024 * 1024 + 1)
            data = load_json(raw)
        except (UnicodeError, ValueError, RecursionError):
            raise SiteBlocked("invalid_device_journal") from None
    _require(len(raw) <= 16 * 1024 * 1024 and isinstance(data, dict)
             and data.get("schema_version") == 1 and data.get("domain") == "protected-device-migration-journal"
             and data.get("binding") == binding and isinstance(data.get("devices"), dict)
             and set(data["devices"]) == set(references), "device_journal_binding_mismatch")
    _require(data.get("incomplete_operation") is None, "device_prior_attempt_requires_manual_reconciliation")
    for entry in data["devices"].values():
        _require(isinstance(entry, dict) and set(entry) == {
            "status", "destination_identity", "parent_identity", "create_attempts", "verified", "last_safe_checkpoint",
        } and type(entry["create_attempts"]) is int and entry["create_attempts"] == 0
                 and type(entry["verified"]) is bool
                 and entry["status"] in ("pending", "blocked", "failed", "already_existing")
                 and entry["last_safe_checkpoint"] in ("inventory", "read_only_preflight")
                 and all(entry[key] is None or _text(entry[key]) for key in ("destination_identity", "parent_identity"))
                 and (not entry["verified"] or entry["status"] == "already_existing"
                      and _text(entry["destination_identity"]) and _text(entry["parent_identity"])),
                 "device_prior_attempt_requires_manual_reconciliation")
    return data


def run_device_migration(
    profile_path: str, credentials_path: str, source_path: str, comparison_path: str, snapshot_path: str,
    *, mode: str = "dry-run", target_version: str | None = None, terminal: bool = False,
) -> tuple[dict, ExitStatus]:
    _require(mode in ("dry-run", "execute", "resume", "preview", "status"), "invalid_device_batch_mode")
    _require(target_version is None or bool(re.fullmatch(r"10\.[0-9]+(?:\.[0-9]+)*(?:-[0-9]+)?", target_version)),
             "unsupported_target_declaration")
    plan = load_device_plan(source_path, comparison_path, snapshot_path)
    profile = DiscoveryProfile.read(profile_path)
    require_execution_exception(profile.transport.base_url, profile.transport.verify_tls, credentials_path)
    message = warning(profile.transport.verify_tls)
    if message:
        print(message, file=sys.stderr)
    site_binding, site_path, lock_path = _journal_context(profile, plan.sites)
    binding = {"origin": site_binding["origin"], "plan": plan.binding}
    origin_digest = lock_path.stem.removeprefix(".ccv-sites-")
    journal_path = profile.output_directory / f"ccv-devices-{plan.digest[:32]}-{origin_digest}.journal.json"
    report_path = profile.output_directory / f"ccv-devices-report-{uuid4().hex}.json"
    entries = {device.reference: {
        "status": "pending", "destination_identity": None, "parent_identity": None,
        "create_attempts": 0, "verified": False, "last_safe_checkpoint": "inventory",
    } for device in plan.devices}
    report = {
        "schema_version": 1, "domain": "device-batch-migration-report", "operation": "device-batch-migration",
        "mode": mode, "status": "blocked", "authenticated": False, "read_only": True, "offline_only": False,
        "migration_ready": False, "execution_authorized": False, "configuration_writes_authorized": False,
        "manual_reconciliation_required": False,
        "target_origin": profile.transport.base_url, "target_version": target_version,
        "compatibility": "experimental-unverified", "target_version_evidence": "operator-declared-not-api-verified",
        "tls": execution_tls(profile.transport.verify_tls), "create_attempts": 0,
        "device_access_writes_authorized": False, "fully_configured_devices": 0,
        "unsupported_configuration_fields": sum(device.unsupported_fields + device.unprojected_fields for device in plan.devices),
        "input_bindings": plan.binding, "inventory": plan.inventory,
        "report_file": report_path.name, "journal_file": journal_path.name, "issue_codes": [],
        "sites": {"total": len(plan.sites.sites), "verified": 0, "pending": len(plan.sites.sites)},
        "contract_blockers": [_CONTRACT_BLOCK, "device_create_response_and_readback_contract_unqualified",
                              "device_access_write_contract_not_authorized"],
        "devices": [{
            "source_reference": device.reference, "parent_source_reference": device.parent_reference,
            "controller_association": device.controller_reference, "access_association": device.access_reference,
            "supported_read_fields": ["name", "type", "managementIp"],
            "unsupported_access_fields": device.unsupported_fields, "issue_codes": list(device.issues),
            "unprojected_fields": device.unprojected_fields,
        } for device in plan.devices],
    }
    backend = DeviceReadBackend(profile, plan.sites.sites[0].selection)
    strategy = _DiscoveryAuthentication()
    journal = None
    journal_dirty = False
    persist_journal = mode in ("execute", "resume")
    status = ExitStatus.VALIDATION_FAILED
    current = None
    if terminal:
        print(f"Destination: {profile.transport.base_url}")
        print(f"Operation: Devices {mode}; total Sites: {len(plan.sites.sites)}; total Devices: {len(plan.devices)}")
        print("Read-only preflight: CHECKING. Device creation BLOCKED: inventory-only write contract unqualified.", flush=True)
    with ExitStack() as resources:
        try:
            resources.enter_context(_origin_lock(lock_path))
            if mode == "resume" or mode == "status" and journal_path.exists():
                journal = _load_device_journal(journal_path, binding, list(entries))
                entries = journal["devices"]
            elif mode == "execute":
                _require(not journal_path.exists(), "device_journal_exists_resume_required")
                journal = {
                    "schema_version": 1, "domain": "protected-device-migration-journal", "binding": binding,
                    "devices": entries, "incomplete_operation": None,
                }
            site_journal = _read_journal(site_path, site_binding, plan.sites) if site_path.exists() else None
            with SessionManager(lambda: backend, _Credentials(credentials_path)) as manager:
                manager.initialize(
                    _UnknownVersionRequest(SessionRole.DESTINATION, "cyber-controller", "unknown",
                                           CredentialReference("cc-destination-discovery")),
                    profile.transport, strategy=strategy,
                )
                manager.authenticate(SessionRole.DESTINATION)
                report["authenticated"] = True
                report["failure_stage"] = "site_journal_verification"
                root_id = _fresh_root(manager, backend, plan.sites)
                mapping = {plan.sites.root_reference: root_id}
                if site_journal is not None:
                    _require(site_journal["root_identity"] == root_id, "batch_root_identity_changed")
                    for site in plan.sites.sites:
                        entry = site_journal["sites"][site.selection.reference]
                        if not entry["verified"]:
                            break
                        identity, _ = _inspect(manager, backend, plan.sites, site, mapping, report, 3, 0)
                        _require(identity == entry["destination_identity"]
                                 and mapping[site.parent_reference] == entry["parent_identity"],
                                 "journal_destination_identity_changed")
                        mapping[site.selection.reference] = identity
                    report["sites"].update(verified=len(mapping) - 1, pending=len(plan.sites.sites) - len(mapping) + 1)
                if mode == "preview":
                    report["failure_stage"] = "full_site_preflight"
                    preview_mapping = dict(mapping)
                    for site in plan.sites.sites:
                        identity, _ = _inspect(manager, backend, plan.sites, site, preview_mapping, report, 3, 0)
                        if identity is not None:
                            preview_mapping[site.selection.reference] = identity
                    report["site_preflight"] = "passed"
                for index, (device, row) in enumerate(zip(plan.devices, report["devices"], strict=True)):
                    current = device.reference
                    entry = entries[current]
                    report["failure_stage"] = "device_collision_and_parent_lookup"
                    if device.issues:
                        entry.update(status="blocked", verified=False)
                    elif site_journal is None or device.parent_reference not in mapping:
                        row["issue_codes"].append("device_destination_parent_dependency_unresolved")
                        entry.update(status="blocked", verified=False)
                    else:
                        identity = _check_destination(manager, backend, plan, device, mapping)
                        if entry["destination_identity"] is not None:
                            _require(identity == entry["destination_identity"]
                                     and mapping[device.parent_reference] == entry["parent_identity"],
                                     "device_journal_identity_changed")
                        entry.update(
                            status="already_existing" if identity is not None else "blocked",
                            destination_identity=identity, parent_identity=mapping[device.parent_reference],
                            verified=identity is not None, last_safe_checkpoint="read_only_preflight",
                        )
                        if identity is None:
                            row["issue_codes"].append(_CONTRACT_BLOCK)
                    if journal is not None and persist_journal:
                        journal_dirty = True
                        _write_private(journal_path, journal)
                        journal_dirty = False
                    if terminal:
                        print(f"Device {index + 1}/{len(plan.devices)}: {entry['status'].upper()}", flush=True)
                report.pop("failure_stage", None)
                report["issue_codes"].append(_CONTRACT_BLOCK)
        except (SiteBlocked, AuthenticationError, TransportError, ContractValidationError, OSError, KeyboardInterrupt) as error:
            if isinstance(error, SiteBlocked):
                code = error.code
            elif isinstance(error, TransportError):
                code = error.category.value
                if error.status is not None:
                    report["http_status"] = error.status
            elif isinstance(error, AuthenticationError):
                reason = error.failure.transport_reason
                code = reason.value if reason is not None else error.failure.category.value
            elif isinstance(error, ContractValidationError):
                code = "device_response_or_path_contract_failure"
            elif isinstance(error, KeyboardInterrupt):
                code = "device_batch_interrupted"
            else:
                code = "device_journal_or_report_io_failure"
            report["issue_codes"].append(code)
            report["manual_reconciliation_required"] = code in (
                "device_prior_attempt_requires_manual_reconciliation", "device_journal_identity_changed",
            )
            if current is not None:
                entries[current].update(status="failed", verified=False)
                journal_dirty = journal is not None and persist_journal
            report["status"] = "blocked" if report["authenticated"] else "error"
        finally:
            strategy.clear()
            _close_backend(backend, report)
            report["counts"] = {
                "total": len(entries), "created": 0, "verified": sum(entry["verified"] for entry in entries.values()),
                "already_existing": sum(entry["verified"] for entry in entries.values()),
                **{key: sum(entry["status"] == key for entry in entries.values()) for key in ("blocked", "failed", "pending")},
            }
            for row in report["devices"]:
                entry = entries[row["source_reference"]]
                row.update(status=entry["status"], verified=entry["verified"], create_attempts=0)
            try:
                if journal_dirty:
                    _write_private(journal_path, journal)
                _write_private(report_path, report)
            except OSError:
                report["issue_codes"].append("device_evidence_persistence_failed")
                report["status"] = "error"
                status = ExitStatus.INPUT_ERROR
    if terminal:
        from .launcher_helper import summary
        summary(report, "2", int(status), str(profile.output_directory), "")
    return report, status
