"""Legacy-compatible source Site/Device export; no destination operations."""

import warnings
from collections.abc import Mapping
from copy import deepcopy
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Literal

from .client import ApiClient, ClientError
from .config import ControllerConfig
from .contracts import JsonValue
from .files import JsonFileError, save_json
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
        raise ExportError(error.code, step) from None


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


def _collect_tree(client: ApiClient, tree: str) -> tuple[dict[str, JsonValue], int, int]:
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
    for index, value in enumerate(devices):
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
