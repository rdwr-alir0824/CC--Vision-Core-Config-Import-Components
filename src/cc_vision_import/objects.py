"""Independent legacy-compatible Site/Device export and import."""

import warnings
from collections import deque
from collections.abc import Mapping
from copy import deepcopy
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Literal

from .client import ApiClient, ClientError
from .config import ControllerConfig
from .contracts import JsonValue
from .files import JsonFileError, load_json, save_json
from .http_backend import ConnectionFactory
from .transport import HttpMethod


_TREE = ("mgmt", "system", "config", "tree")
_SITE_CLASS = "com.radware.insite.model.device.Site"
_DEVICE_CLASS = "com.radware.insite.model.device.Device"


class ExportError(Exception):
    def __init__(self, code: str, step: str) -> None:
        super().__init__(f"Export failed at {step}: {code}.")
        self.code = code
        self.step = step


@dataclass(frozen=True)
class ExportResult:
    status: Literal["SUCCESS", "FAILED"]
    path: Path | None = field(default=None, repr=False)
    site_count: int = 0
    device_count: int = 0
    error_code: str | None = None
    failed_step: str | None = None
    cleanup_failed: bool = False


def _object(value: JsonValue, step: str) -> dict[str, JsonValue]:
    if not isinstance(value, dict):
        raise ExportError("malformed_response", step)
    return value


def _text(value: JsonValue, step: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ExportError("missing_or_invalid_field", step)
    return value


def _identity(node: dict[str, JsonValue], step: str) -> tuple[str, dict[str, JsonValue]]:
    identifier = _object(node.get("meIdentifier"), step)
    return _text(identifier.get("managedElementID"), step), identifier


def _read(client: ApiClient, path: tuple[str, ...], step: str) -> JsonValue:
    try:
        client.authorize_gets((path,))
        return client.get(path)
    except ClientError as error:
        failure = ExportError(error.code, step)
        if _cleanup_failed(error):
            failure.add_note("Local API session cleanup failed.")
        raise failure from None


def _site_name(
    client: ApiClient, node: dict[str, JsonValue], identity: str, step: str,
) -> str:
    name = node.get("name")
    if name is None or name == "":
        row = _object(_read(client, (*_TREE, "site", "byid", identity), step), step)
        identifier = row.get("meIdentifier")
        if identifier is not None:
            resolved_id, _ = _identity(row, step)
            if resolved_id != identity:
                raise ExportError("ambiguous_parent_identity", step)
        name = row.get("name")
    return _text(name, step)


def _collect_tree(
    client: ApiClient, tree: str, *, include_access: bool = True,
) -> tuple[dict[str, JsonValue], int, int]:
    root = _object(_read(client, (*_TREE, tree), "hierarchy"), "hierarchy")
    root_id, _ = _identity(root, "source_root")
    root_name = _site_name(client, root, root_id, "source_root_name")
    sites: list[JsonValue] = []
    devices: list[JsonValue] = []
    seen = {root_id}

    def walk(node: dict[str, JsonValue], parent_id: str, parent_name: str) -> None:
        children = node.get("children")
        if not isinstance(children, list):
            raise ExportError("missing_or_invalid_children", "hierarchy")
        for child in children:
            item = _object(child, "hierarchy")
            identity, identifier = _identity(item, "hierarchy")
            if identity in seen:
                raise ExportError("ambiguous_hierarchy_identity", "hierarchy")
            seen.add(identity)
            kind = identifier.get("managedElementClass")
            if kind == _SITE_CLASS:
                name = _site_name(client, item, identity, f"site_name[{len(sites)}]")
                sites.append({
                    "name": name, "id": identity, "parent_site_name": parent_name,
                    "parentOrmID": parent_id,
                })
                walk(item, identity, name)
            elif kind == _DEVICE_CLASS:
                if item.get("children") not in (None, []):
                    raise ExportError("unsupported_device_children", "hierarchy")
                devices.append({
                    "name": _text(item.get("name"), "device_name"),
                    "type": _text(item.get("type"), "device_type"),
                    "managementIp": _text(item.get("managementIp"), "device_management_ip"),
                    "id": identity, "parentOrmID": parent_id,
                })
            else:
                raise ExportError("unsupported_tree_node", "hierarchy")

    walk(root, root_id, root_name)
    for index, value in enumerate(devices if include_access else []):
        device = _object(value, "hierarchy")
        step = f"device_access[{index}]"
        address = _text(device.get("managementIp"), step)
        detail = _object(_read(client, (*_TREE, "device", "byip", address), step), step)
        setup = _object(detail.get("deviceSetup"), step)
        access = deepcopy(_object(setup.get("deviceAccess"), step))
        access.pop("ormID", None)
        device["deviceAccess"] = access
    data: dict[str, JsonValue] = {
        "source_root": {"id": root_id, "name": root_name},
        "sites": sites, "devices": devices,
    }
    return data, len(sites), len(devices)


def export_objects(
    config: ControllerConfig, outputs: Mapping[str, str | Path], *,
    tls_exception_authorized: bool = False,
    connection_factory: ConnectionFactory | None = None,
    allow_live: bool = False,
) -> dict[str, ExportResult]:
    if not outputs or any(tree not in ("Physical", "Organization") for tree in outputs):
        raise ExportError("invalid_tree_selection", "configuration")
    try:
        paths = {tree: Path(path).resolve() for tree, path in outputs.items()}
    except (TypeError, ValueError, OSError):
        raise ExportError("invalid_output_path", "configuration") from None
    if len(set(paths.values())) != len(paths):
        raise ExportError("duplicate_output_path", "configuration")
    warnings.warn(
        "Exported JSON may contain sensitive device credentials. Protect the selected output files.",
        RuntimeWarning, stacklevel=2,
    )
    results: dict[str, ExportResult] = {}
    try:
        client = ApiClient(
            config, operations=tuple((HttpMethod.GET, (*_TREE, tree)) for tree in paths),
            tls_exception_authorized=tls_exception_authorized,
            connection_factory=connection_factory, allow_live=allow_live,
        )
        with client:
            for tree, path in paths.items():
                try:
                    data, site_count, device_count = _collect_tree(client, tree)
                    save_json(path, data)
                    results[tree] = ExportResult("SUCCESS", path, site_count, device_count)
                except ExportError as error:
                    results[tree] = ExportResult(
                        "FAILED", error_code=error.code, failed_step=error.step,
                        cleanup_failed=_cleanup_failed(error),
                    )
                except RecursionError:
                    results[tree] = ExportResult(
                        "FAILED", error_code="hierarchy_too_deep", failed_step="hierarchy",
                    )
                except JsonFileError:
                    results[tree] = ExportResult(
                        "FAILED", error_code="file_write_failed", failed_step="file_write",
                    )
    except ClientError as error:
        step = "session_cleanup" if results else "authentication"
        cleanup_failed = (
            step == "session_cleanup"
            or "Local API session cleanup failed." in getattr(error, "__notes__", ())
        )
        for tree in paths:
            previous = results.get(tree)
            if previous is None or previous.status == "SUCCESS":
                results[tree] = ExportResult(
                    "FAILED", path=None if previous is None else previous.path,
                    site_count=0 if previous is None else previous.site_count,
                    device_count=0 if previous is None else previous.device_count,
                    error_code=error.code, failed_step=step,
                    cleanup_failed=cleanup_failed,
                )
            elif cleanup_failed:
                results[tree] = replace(previous, cleanup_failed=True)
    return results


class ImportError(Exception):
    def __init__(self, code: str, step: str) -> None:
        super().__init__(f"Import failed at {step}: {code}.")
        self.code = code
        self.step = step


@dataclass(frozen=True)
class ObjectImportResult:
    object_type: Literal["Site", "Device"]
    source_id: str
    status: Literal["SUCCESS", "SKIPPED", "FAILED"]
    reason: str


@dataclass(frozen=True)
class ImportResult:
    objects: tuple[ObjectImportResult, ...]
    error_code: str | None = None
    failed_step: str | None = None
    cleanup_failed: bool = False

    @property
    def status(self) -> Literal["SUCCESS", "FAILED"]:
        return "FAILED" if self.error_code or any(
            item.status == "FAILED" for item in self.objects
        ) else "SUCCESS"

    @property
    def counts(self) -> dict[str, dict[str, int]]:
        return {
            kind: {
                status: sum(item.object_type == kind and item.status == status
                            for item in self.objects)
                for status in ("SUCCESS", "SKIPPED", "FAILED")
            }
            for kind in ("Site", "Device")
        }


def _cleanup_failed(error: BaseException) -> bool:
    return "Local API session cleanup failed." in getattr(error, "__notes__", ())


def _validate_import(
    data: JsonValue, explicit_root: dict[str, JsonValue] | None,
) -> tuple[dict[str, JsonValue], list[dict[str, JsonValue]], list[dict[str, JsonValue]]]:
    try:
        document = _object(data, "input")
        if explicit_root is not None:
            _object(explicit_root, "explicit_source_root")
        root = _object(document.get("source_root", explicit_root), "source_root")
        root_id = _text(root.get("id"), "source_root.id")
        _text(root.get("name"), "source_root.name")
        if explicit_root is not None and any(
            explicit_root.get(key) != root.get(key) for key in ("id", "name")
        ):
            raise ImportError("conflicting_source_root", "source_root")
        rows: dict[str, list[dict[str, JsonValue]]] = {}
        identities = {root_id}
        for kind, fields in (
            ("sites", ("id", "name", "parentOrmID", "parent_site_name")),
            ("devices", ("id", "name", "parentOrmID", "type", "managementIp")),
        ):
            values = document.get(kind)
            if not isinstance(values, list):
                raise ImportError("invalid_export_structure", kind)
            rows[kind] = []
            positions: set[tuple[str, str]] = set()
            addresses: set[str] = set()
            for index, value in enumerate(values):
                step = f"{kind}[{index}]"
                row = _object(value, step)
                for key in fields:
                    _text(row.get(key), f"{step}.{key}")
                identity = _text(row.get("id"), step)
                if identity in identities:
                    raise ImportError("duplicate_source_identity", step)
                identities.add(identity)
                position = (_text(row.get("parentOrmID"), step), _text(row.get("name"), step))
                if position in positions:
                    raise ImportError("ambiguous_source_identity", step)
                positions.add(position)
                if kind == "devices":
                    _object(row.get("deviceAccess"), f"{step}.deviceAccess")
                    address = _text(row.get("managementIp"), step)
                    if address in addresses:
                        raise ImportError("ambiguous_device_address", step)
                    addresses.add(address)
                rows[kind].append(row)
        sites, devices = rows["sites"], rows["devices"]
        parents = {root_id: root, **{_text(row.get("id"), "sites"): row for row in sites}}
        children: dict[str, list[dict[str, JsonValue]]] = {}
        for kind, values in (("sites", sites), ("devices", devices)):
            for index, row in enumerate(values):
                step = f"{kind}[{index}]"
                parent_id = _text(row.get("parentOrmID"), step)
                if parent_id not in parents:
                    raise ImportError("missing_source_parent", step)
                if kind == "sites":
                    if row["parent_site_name"] != parents[parent_id]["name"]:
                        raise ImportError("conflicting_source_parent_name", step)
                    children.setdefault(parent_id, []).append(row)
        ordered: list[dict[str, JsonValue]] = []
        pending = deque(children.get(root_id, ()))
        while pending:
            row = pending.popleft()
            ordered.append(row)
            pending.extend(children.get(_text(row.get("id"), "sites"), ()))
        if len(ordered) != len(sites):
            raise ImportError("cyclic_site_dependencies", "sites")
        return root, ordered, devices
    except ExportError as error:
        raise ImportError(error.code, error.step) from None


def _site_paths(
    root: dict[str, JsonValue], sites: list[dict[str, JsonValue]],
) -> dict[str, tuple[str, ...]]:
    paths = {_text(root.get("id"), "root"): ()}
    for row in sites:
        paths[_text(row.get("id"), "sites")] = (
            *paths[_text(row.get("parentOrmID"), "sites")],
            _text(row.get("name"), "sites"),
        )
    return paths


def _destination_rows(
    client: ApiClient, tree: str,
) -> tuple[dict[str, JsonValue], list[dict[str, JsonValue]], list[dict[str, JsonValue]]]:
    data, _, _ = _collect_tree(client, tree, include_access=False)
    sites, devices = data["sites"], data["devices"]
    if not isinstance(sites, list) or not isinstance(devices, list):
        raise ImportError("malformed_destination_hierarchy", "hierarchy")
    return (
        _object(data["source_root"], "destination_root"),
        [_object(value, "hierarchy") for value in sites],
        [_object(value, "hierarchy") for value in devices],
    )


def _find_destination(
    kind: Literal["Site", "Device"], source: dict[str, JsonValue], parent_id: str,
    destination: tuple[dict[str, JsonValue], list[dict[str, JsonValue]],
                       list[dict[str, JsonValue]]],
    expected_paths: set[tuple[str, ...]],
) -> dict[str, JsonValue] | None:
    root, sites, devices = destination
    if kind == "Site":
        matches = [row for row in sites
                   if row["name"] == source["name"] and row["parentOrmID"] == parent_id]
        if len(matches) > 1:
            raise ImportError("ambiguous_destination_site", "matching")
        if matches:
            return matches[0]
        paths = _site_paths(root, sites)
        if any(row["name"] == source["name"] and paths[_text(row.get("id"), "sites")]
               not in expected_paths for row in sites):
            raise ImportError("existing_site_wrong_placement", "matching")
    else:
        matches = [row for row in devices if row["managementIp"] == source["managementIp"]
                   or (row["name"] == source["name"] and row["parentOrmID"] == parent_id)]
        if len(matches) > 1:
            raise ImportError("ambiguous_destination_device", "matching")
        if matches:
            row = matches[0]
            if row["parentOrmID"] != parent_id:
                raise ImportError("existing_device_wrong_placement", "matching")
            if any(row[key] != source[key] for key in ("name", "type", "managementIp")):
                raise ImportError("existing_device_identity_conflict", "matching")
            return row
    return None


def import_objects(
    config: ControllerConfig, input_path: str | Path, tree: str, *,
    source_root: dict[str, JsonValue] | None = None,
    tls_exception_authorized: bool = False,
    connection_factory: ConnectionFactory | None = None,
    allow_live: bool = False,
) -> ImportResult:
    """Validate a portable file, then map its root to the explicitly selected tree."""
    if tree not in ("Physical", "Organization"):
        raise ImportError("invalid_tree_selection", "configuration")
    try:
        root, sites, devices = _validate_import(load_json(input_path), source_root)
    except JsonFileError:
        raise ImportError("invalid_json_file", "input") from None
    source_paths = _site_paths(root, sites)
    expected_paths = set(source_paths.values())
    results: list[ObjectImportResult] = []
    cleanup_failed = False
    error_code: str | None = None
    failed_step: str | None = None
    step = "authentication"
    objects: list[tuple[Literal["Site", "Device"], dict[str, JsonValue]]] = [
        *(("Site", row) for row in sites), *(("Device", row) for row in devices),
    ]
    try:
        client = ApiClient(
            config, operations=(
                (HttpMethod.GET, (*_TREE, tree)),
                (HttpMethod.POST, (*_TREE, "site")),
                (HttpMethod.POST, (*_TREE, "device")),
            ),
            tls_exception_authorized=tls_exception_authorized,
            connection_factory=connection_factory, allow_live=allow_live,
        )
        with client:
            step = "destination_hierarchy"
            destination = _destination_rows(client, tree)
            mapping = {
                _text(root.get("id"), "root"):
                _text(destination[0].get("id"), "destination_root"),
            }
            step = "objects"
            for kind, row in objects:
                identity = _text(row.get("id"), "objects")
                parent = mapping.get(_text(row.get("parentOrmID"), "objects"))
                if parent is None:
                    results.append(ObjectImportResult(kind, identity, "FAILED", "parent_failed"))
                    continue
                posted = False
                try:
                    match = _find_destination(kind, row, parent, destination, expected_paths)
                    status: Literal["SUCCESS", "SKIPPED"] = "SKIPPED"
                    if match is None:
                        payload: dict[str, JsonValue] = {"name": row["name"], "parentOrmID": parent}
                        if kind == "Device":
                            access = deepcopy(_object(row.get("deviceAccess"), "deviceAccess"))
                            access.pop("ormID", None)
                            payload.update({"type": row["type"], "deviceSetup": {"deviceAccess": access}})
                        posted = True
                        client.post((*_TREE, kind.lower()), payload, expect_json=False)
                        # Acknowledgements do not establish an object identity or its placement.
                        for _ in range(3):
                            refreshed = _destination_rows(client, tree)
                            if refreshed[0]["id"] != destination[0]["id"]:
                                raise ImportError("destination_root_changed", "readback")
                            destination = refreshed
                            match = _find_destination(kind, row, parent, destination, expected_paths)
                            if match is not None:
                                break
                        if match is None:
                            raise ImportError("creation_unconfirmed", "readback")
                        status = "SUCCESS"
                    if kind == "Site":
                        mapping[identity] = _text(match.get("id"), "destination_site")
                    results.append(ObjectImportResult(
                        kind, identity, status,
                        "creation_confirmed" if status == "SUCCESS" else "identity_and_placement_agree",
                    ))
                except (ClientError, ExportError, ImportError) as error:
                    cleanup_failed = cleanup_failed or _cleanup_failed(error)
                    reason = ("destination_outcome_uncertain:" if posted else "") + error.code
                    results.append(ObjectImportResult(kind, identity, "FAILED", reason))
                    if error.code == "destination_root_changed":
                        raise
                except RecursionError:
                    reason = ("destination_outcome_uncertain:" if posted else "") + "hierarchy_too_deep"
                    results.append(ObjectImportResult(kind, identity, "FAILED", reason))
    except (ClientError, ExportError, ImportError) as error:
        error_code = error.code
        failed_step = (
            "session_cleanup" if isinstance(error, ClientError) and step == "objects"
            else error.step if step == "objects" and isinstance(error, (ExportError, ImportError))
            else step
        )
        cleanup_failed = cleanup_failed or _cleanup_failed(error) or failed_step == "session_cleanup"
    except RecursionError:
        error_code, failed_step = "hierarchy_too_deep", step
    if error_code:
        for kind, row in objects[len(results):]:
            results.append(ObjectImportResult(
                kind, _text(row.get("id"), "objects"), "FAILED", "not_processed:" + error_code,
            ))
    return ImportResult(tuple(results), error_code, failed_step, cleanup_failed)
