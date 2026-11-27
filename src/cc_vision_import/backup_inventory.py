"""Bounded native-backup discovery; records are not assumed to be unique objects."""

import hashlib
import json
import os
import stat
from dataclasses import asdict, dataclass, field
from pathlib import Path

from ._json import load_json
from .contracts import ContractValidationError
from .offline_inputs import local_path
from .single_site import SiteBlocked, _require, _text
from .product_clients import vision_ldap_segments, vision_scheduler_segments
from .schema_qualification import operation_evidence
from .vision_tree_preview import inspect_vision_tree


@dataclass(frozen=True)
class InventoryLimits:
    max_files: int = 4096
    max_objects: int = 10000
    max_depth: int = 48
    max_file_bytes: int = 16 * 1024 * 1024
    max_total_bytes: int = 128 * 1024 * 1024

    def validate(self) -> None:
        _require(all(type(value) is int and value > 0 for value in asdict(self).values())
                 and self.max_depth <= 64 and self.max_objects <= 10000
                 and self.max_file_bytes <= self.max_total_bytes, "invalid_backup_resource_limits")


@dataclass(frozen=True)
class ModuleHandler:
    domain: str
    member: str
    dependency: str
    blocked_reason: str
    write_policy: str = "blocked-no-qualified-write-contract"


HANDLERS = {
    "vision-organization-tree": ModuleHandler("organization-tree", "tree", "reviewed-root-and-parent-sites",
                                              "organization_device_create_contract_unqualified", "sites-only-create-no-update"),
    "vision-physical-tree": ModuleHandler("physical-tree", "tree", "reviewed-physical-root-and-parent-objects",
                                          "physical_destination_write_and_verification_contract_unqualified"),
    "vision-controller-object-lookup": ModuleHandler("controller-objects", "objects", "verified-device-and-site-identities",
                                                     "controller_attribute_write_contract_unqualified"),
    "vision-managed-device-inventory": ModuleHandler("controller-objects", "objects", "qualified-native-identity-bridge",
                                                     "controller_inventory_identity_bridge_unqualified"),
    "vision-device-access": ModuleHandler("device-access", "objects", "qualified-device-association-and-credential-reference",
                                           "device_access_write_and_credential_contract_unqualified"),
    "vision-ldap-permissions": ModuleHandler("ldap-permissions", "objects", "qualified-destination-authorization-mapping",
                                              "ldap_destination_write_scope_and_verification_unqualified"),
    "vision-scheduler": ModuleHandler("scheduler", "tasks", "qualified-task-device-and-identity-dependencies",
                                      "scheduler_destination_write_and_completion_contract_unqualified"),
}


def _request_matches(schema: str, request: dict) -> bool:
    if schema in ("vision-controller-object-lookup", "vision-device-access"):
        records = ("API-06",) if schema == "vision-device-access" else ("API-04", "API-05", "API-06")
        templates = {operation_evidence("vision", "5.4.9", "DOC-V549", record).path for record in records}
        return (set(request) == {"method", "path_template", "target"}
                and isinstance(request.get("path_template"), str)
                and request["path_template"] in templates and _text(request.get("target")))
    expected = (
        "/" + "/".join(vision_ldap_segments()) if schema == "vision-ldap-permissions" else
        "/" + "/".join(vision_scheduler_segments()) if schema == "vision-scheduler" else
        "/mgmt/system/config/itemlist/alldevices" if schema == "vision-managed-device-inventory" else
        "/mgmt/system/config/tree/Organization" if schema == "vision-organization-tree" else
        "/mgmt/system/config/tree/Physical"
    )
    return set(request) == {"method", "path"} and request.get("path") == expected


@dataclass(repr=False)
class BackupInventory:
    root: Path
    report: dict
    artifacts: list[tuple[Path, dict]] = field(repr=False)
    digest: str

    def paths(self, schema: str) -> tuple[Path, ...]:
        return tuple(path for path, payload in self.artifacts if payload.get("domain") == schema)


def _empty_module(domain: str) -> dict:
    return {
        "domain": domain, "availability": "ABSENT", "records": None, "files": [],
        "sites": 0, "devices": 0, "roots": 0, "managed_inventory_records": 0,
        "unprojected_fields": 0, "issue_codes": [], "graph": [], "known_records": 0,
        "migration_status": "NOT_IN_BACKUP", "verified_records": 0,
    }


def _bounded_json(value: object, limits: InventoryLimits) -> None:
    nodes = 0
    def visit(item: object, depth: int) -> None:
        nonlocal nodes
        nodes += 1
        _require(depth <= limits.max_depth * 4 + 16 and nodes <= limits.max_objects * 200,
                 "backup_json_resource_limit")
        if isinstance(item, dict):
            for child in item.values():
                visit(child, depth + 1)
        elif isinstance(item, list):
            for child in item:
                visit(child, depth + 1)
    visit(value, 0)


def discover_backup(folder: str, *, limits: InventoryLimits | None = None) -> BackupInventory:
    limits = limits or InventoryLimits()
    limits.validate()
    root = local_path(folder, Path.cwd()).absolute()
    _require(root.is_dir() and not root.is_symlink() and not any(parent.is_symlink() for parent in root.parents),
             "backup_directory_unavailable")
    files: list[Path] = []
    directories_seen = 0
    def unreadable(error: OSError) -> None:
        raise SiteBlocked("backup_directory_unreadable") from error
    for directory, subdirs, names in os.walk(root, followlinks=False, onerror=unreadable):
        directories_seen += 1
        _require(len(Path(directory).relative_to(root).parts) <= limits.max_depth, "backup_directory_depth_limit")
        _require(not any((Path(directory) / name).is_symlink() for name in [*subdirs, *names]),
                 "backup_links_forbidden")
        files.extend(Path(directory) / name for name in names)
        _require(len(files) <= limits.max_files, "backup_file_limit")
        _require(directories_seen + len(subdirs) <= limits.max_files + limits.max_depth + 1,
                 "backup_directory_limit")
    modules = {handler.domain: _empty_module(handler.domain) for handler in HANDLERS.values()}
    artifacts: list[tuple[Path, dict]] = []
    bindings = []
    source = None
    summary = None
    total_bytes = 0
    total_records = 0
    for index, path in enumerate(sorted(files), 1):
        _require(path.is_file(), "backup_nonregular_file")
        _require(path.stat().st_size <= limits.max_file_bytes, "backup_file_size_limit")
        descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
        with os.fdopen(descriptor, "rb") as stream:
            _require(stat.S_ISREG(os.fstat(stream.fileno()).st_mode), "backup_nonregular_file")
            raw = stream.read(limits.max_file_bytes + 1)
        _require(len(raw) <= limits.max_file_bytes, "backup_file_size_limit")
        total_bytes += len(raw)
        _require(total_bytes <= limits.max_total_bytes, "backup_total_size_limit")
        reference = f"file-{index}"
        bindings.append({"relative_path": list(path.relative_to(root).parts), "sha256": hashlib.sha256(raw).hexdigest()})
        schema = None
        payload = None
        if path.suffix.lower() == ".json":
            try:
                payload = load_json(raw.decode("utf-8"))
                _bounded_json(payload, limits)
            except (ValueError, UnicodeError, RecursionError):
                payload = None
        if isinstance(payload, dict) and payload.get("operation") == "backup-vision":
            _require(summary is None, "duplicate_backup_summary")
            summary = payload
            continue
        if isinstance(payload, dict):
            schema = payload.get("domain")
        handler = HANDLERS.get(schema) if isinstance(schema, str) else None
        if handler is None:
            domain = f"unsupported-module-{index}"
            module = modules.setdefault(domain, _empty_module(domain))
            module.update(availability="MALFORMED" if payload is None and path.suffix.lower() == ".json" else "UNSUPPORTED",
                          records=None, migration_status="BLOCKED", files=[reference],
                          issue_codes=["backup_json_malformed" if payload is None and path.suffix.lower() == ".json"
                                       else "backup_module_schema_unqualified"])
            continue
        module = modules[handler.domain]
        module["files"].append(reference)
        if module["availability"] == "ABSENT":
            module["availability"] = "AVAILABLE"
        module["migration_status"] = "BLOCKED"
        module["issue_codes"].append(handler.blocked_reason)
        if payload.get("schema_version") != 1 or type(payload.get("schema_version")) is not int:
            module.update(availability="UNSUPPORTED", records=None)
            module["issue_codes"].append("backup_schema_version_unqualified")
            continue
        provenance = payload.get("source")
        if not isinstance(provenance, dict) or provenance.get("product") != "vision" or not _text(provenance.get("name")):
            module.update(availability="MALFORMED", records=None)
            module["issue_codes"].append("backup_source_provenance_invalid")
            continue
        if source is None:
            source = provenance
        _require(provenance == source, "backup_mixed_source_provenance")
        if provenance.get("version") != "5.4.9":
            module.update(availability="UNSUPPORTED", records=None)
            module["issue_codes"].append("backup_source_version_unqualified")
            continue
        request = payload.get("request")
        if not isinstance(request, dict) or request.get("method") != "GET" or not _request_matches(schema, request):
            module.update(availability="MALFORMED", records=None)
            module["issue_codes"].append("backup_request_provenance_invalid")
            continue
        member = payload.get(handler.member)
        module["unprojected_fields"] += len(set(payload) - {
            "schema_version", "domain", "source", "collected_at", "request", "scope", "evidence",
            "tree", "objects", "tasks", "record_count", "record_count_basis", "redacted_fields",
            "issue_codes", "identity_binding",
        })
        try:
            if handler.member == "tree":
                tree = inspect_vision_tree(payload)
                count = len(tree["nodes"]) - tree["counts"]["root-candidate"]
                if tree["nodes"]:
                    count = len(tree["nodes"]) - tree["counts"]["root-candidate"]
                    nodes = tree["nodes"]
                    _require(len(nodes) <= limits.max_objects, "backup_object_limit")
                    depth_by_ref = {}
                    for node in nodes:
                        parent = node["observed_container_parent"]
                        depth = 0 if parent is None else depth_by_ref[parent] + 1
                        _require(depth <= limits.max_depth, "backup_hierarchy_depth_limit")
                        depth_by_ref[node["reference"]] = depth
                        module["graph"].append({
                            "reference": handler.domain + ":" + node["reference"], "kind": node["kind"],
                            "depends_on": [handler.domain + ":" + item for item in node["depends_on"]],
                            "issue_codes": node["issue_codes"],
                            "creation_contract": "experimental-site-only" if node["kind"] == "site" else "blocked",
                        })
                    module["sites"] += tree["counts"]["site"]
                    module["devices"] += tree["counts"]["device"]
                    module["roots"] += tree["counts"]["root-candidate"]
                    module["unprojected_fields"] += sum(node["unknown_field_count"] for node in nodes)
                    if handler.domain == "organization-tree" and isinstance(member, dict):
                        identifier = member.get("meIdentifier")
                        if not (isinstance(identifier, dict)
                                and identifier.get("managedElementClass") == "com.radware.insite.model.device.Site"
                                and _text(identifier.get("managedElementID")) and _text(member.get("name"))
                                and isinstance(member.get("children"), list)):
                            module["availability"] = "MALFORMED"
                            module["issue_codes"].append("source_root_identity_or_class_unqualified")
            else:
                _require(isinstance(member, list) and all(isinstance(item, dict) for item in member),
                         "backup_record_array_malformed")
                count = len(member)
                if "record_count" in payload:
                    _require(type(payload["record_count"]) is int and payload["record_count"] == count,
                             "backup_record_array_malformed")
                _require(count <= limits.max_objects, "backup_object_limit")
                if schema == "vision-managed-device-inventory":
                    module["managed_inventory_records"] += count
            total_records += count
            _require(total_records <= limits.max_objects, "backup_object_limit")
            if schema == "vision-managed-device-inventory":
                count = 0
            module["known_records"] += count
            if module["availability"] == "AVAILABLE":
                module["records"] = module["known_records"]
            artifacts.append((path, payload))
        except ContractValidationError:
            module.update(availability="MALFORMED", records=None)
            module["issue_codes"].append("backup_tree_schema_malformed")
        except SiteBlocked as error:
            if error.code != "backup_record_array_malformed":
                raise
            module.update(availability="MALFORMED", records=None)
            module["issue_codes"].append(error.code)
    _require(bool(files), "backup_empty_directory_not_an_empty_module")
    if summary is not None:
        requested = summary.get("requested_modules", [])
        failed = summary.get("failed_modules", [])
        _require(isinstance(requested, list) and all(isinstance(item, str) for item in requested)
                 and isinstance(failed, list) and all(isinstance(item, str) for item in failed),
                 "backup_summary_schema_malformed")
        for index, raw_domain in enumerate(requested):
            domain = raw_domain if raw_domain in modules else f"unsupported-summary-module-{index}"
            module = modules.setdefault(domain, _empty_module(domain))
            if module["availability"] == "ABSENT":
                module.update(availability="MISSING_REQUIRED", migration_status="BLOCKED")
                module["issue_codes"].append("requested_backup_module_missing")
        for index, raw_domain in enumerate(failed):
            domain = raw_domain if raw_domain in modules else f"unsupported-failed-module-{index}"
            module = modules.setdefault(domain, _empty_module(domain))
            module.update(availability="INCOMPLETE", migration_status="BLOCKED")
            module["issue_codes"].append("source_module_collection_failed")
    for module in modules.values():
        if module["domain"] == "organization-tree" and not module["devices"]:
            module["issue_codes"] = [
                code for code in module["issue_codes"] if code != "organization_device_create_contract_unqualified"
            ]
            if module["sites"]:
                module["issue_codes"].append("destination_root_mapping_and_fresh_preflight_required")
        if module["availability"] == "AVAILABLE" and module["records"] == 0:
            if module["managed_inventory_records"]:
                module["issue_codes"].append("controller_details_missing_for_inventory")
            elif module["unprojected_fields"] == 0 and not (
                module["domain"] == "physical-tree" and module["roots"]
            ):
                module.update(availability="EMPTY", migration_status="COMPLETED", issue_codes=[])
        module["issue_codes"] = sorted(set(module["issue_codes"]))
    organization = modules["organization-tree"]
    controllers, access = modules["controller-objects"], modules["device-access"]
    if organization["devices"] and not controllers["known_records"]:
        organization["issue_codes"].append("controller_detail_dependency_missing")
    if organization["devices"] and not access["known_records"]:
        organization["issue_codes"].append("device_access_dependency_missing")
    if access["known_records"] and not controllers["known_records"]:
        access["issue_codes"].append("device_access_controller_dependency_missing")
    for domain, module in modules.items():
        if (module["availability"] == "ABSENT" and (root / domain).is_dir()):
            module.update(availability="MISSING_REQUIRED", migration_status="BLOCKED")
            module["issue_codes"].append("declared_backup_module_has_no_artifact")
    digest = hashlib.sha256(json.dumps(bindings, sort_keys=True).encode()).hexdigest()
    report = {
        "schema_version": 1, "operation": "backup-inventory", "offline_only": True,
        "configuration_writes_authorized": False, "backup_sha256": digest,
        "units": "domain-records-not-cross-inventory-unique-objects",
        "file_count": len(files), "total_bytes": total_bytes, "limits": asdict(limits),
        "modules": list(modules.values()),
        "known_records": sum(module["known_records"] for module in modules.values()),
        "unknown_record_counts": sum(module["records"] is None and module["availability"] != "ABSENT"
                                     for module in modules.values()),
        "module_contracts": [
            {**asdict(handler), "identity_mapping": "fresh-destination-native-only",
             "collision_policy": "verify-never-overwrite-or-reparent", "recovery": "reconcile-never-retry-unknown-writes",
             "verification": "qualified-site-by-id-and-tree" if handler.domain == "organization-tree"
             else "blocked-unqualified-destination-verification",
             "unsupported_fields": "reported-not-applied"} for handler in HANDLERS.values()
        ],
    }
    return BackupInventory(root, report, artifacts, digest)
