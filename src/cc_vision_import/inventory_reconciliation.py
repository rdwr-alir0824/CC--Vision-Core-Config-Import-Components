"""Offline namespace-aware inventory/tree reconciliation; never matches by name/IP."""

import argparse
import json
from pathlib import Path

from ._contract_validation import ContractReader
from .contracts import ContractValidationError, ExitStatus
from .offline_inputs import OfflineInputs, write_local_export
from .vision_tree_preview import inspect_vision_tree


_READER = ContractReader("inventory-reconciliation")


def _identity(value: object) -> str | None:
    if isinstance(value, str) and value and value == value.strip() and all(c.isprintable() for c in value):
        return value
    return None


def _rows(value: object, *, depth: int = 0) -> list[dict[str, object]]:
    if depth > 64:
        _READER.fail("inspection_limit", "$", "Native hierarchy exceeds inspection bounds.")
    if isinstance(value, dict):
        values = [value]
    elif isinstance(value, list):
        values = value
    else:
        _READER.fail("invalid_native_nodes", "$", "Native nodes must be objects or arrays.")
    result: list[dict[str, object]] = []
    for item in values:
        row = _READER.mapping(item, "$")
        result.append(row)
        if "children" in row:
            children = row["children"]
            if not isinstance(children, list):
                _READER.fail("invalid_children", "$", "Children must be an explicit array when present.")
            result.extend(_rows(children, depth=depth + 1))
        if len(result) > 10000:
            _READER.fail("inspection_limit", "$", "Native hierarchy exceeds inspection bounds.")
    return result


def _identity_summary(values: list[str | None], references: list[str]) -> dict[str, object]:
    owners: dict[str, list[str]] = {}
    missing: list[str] = []
    for identity, reference in zip(values, references, strict=True):
        if identity is None:
            missing.append(reference)
        else:
            owners.setdefault(identity, []).append(reference)
    duplicates = [group for group in owners.values() if len(group) > 1]
    return {
        "records": len(values), "unique_native_identities": len(owners),
        "missing_identity_references": missing, "duplicate_groups": duplicates,
        "ambiguous_identity_records": sum(len(group) for group in duplicates),
    }


def reconcile_inventory(inventory: object, organization: object, physical: object) -> dict[str, object]:
    data = _READER.mapping(inventory, "$")
    if type(data.get("schema_version")) is not int or data["schema_version"] != 1:
        _READER.fail("invalid_inventory_schema", "$", "Expected inventory backup schema version 1.")
    source = _READER.mapping(data.get("source"), "$.source")
    if source.get("product") != "vision" or source.get("version") != "5.4.9":
        _READER.fail("invalid_inventory_source", "$", "Expected Vision 5.4.9 inventory provenance.")
    _READER.text(source.get("name"), "$.source.name")
    request = _READER.mapping(data.get("request"), "$.request")
    if (
        data.get("domain") != "vision-managed-device-inventory" or request.get("method") != "GET"
        or request.get("path") != "/mgmt/system/config/itemlist/alldevices"
        or not isinstance(data.get("objects"), list)
    ):
        _READER.fail("invalid_inventory_contract", "$", "Expected the managed-device inventory backup envelope.")
    inventory_rows = _rows(data["objects"])
    inventory_references = [f"inventory-record-{index + 1}" for index in range(len(inventory_rows))]
    inventory_ids = [_identity(row.get("ormId")) for row in inventory_rows]
    report: dict[str, object] = {
        "operation": "inventory-reconciliation", "status": "identity-bridge-unverified",
        "offline_only": True, "execution_authorized": False, "migration_ready": False,
        "inventory": {
            "identity_field": "ormId", **_identity_summary(inventory_ids, inventory_references),
            "records_without_usable_parentOrmId": sum(_identity(row.get("parentOrmId")) is None for row in inventory_rows),
            "site_association_status": "unverified-no-cross-representation-parent-link",
        },
        "trees": {},
        "limitations": [
            "ormId_to_managedElementID_equivalence_not_established",
            "no_name_address_dbId_or_detail_id_matching",
            "source_name_equality_is_not_controller_identity_certification",
            "snapshots_not_proven_atomic_or_complete", "no_destination_mappings_or_write_plan",
        ],
    }
    trees: dict[str, object] = {}
    for label, payload, expected in (
        ("organization", organization, "Organization"), ("physical", physical, "Physical"),
    ):
        preview = inspect_vision_tree(payload)
        if preview["tree"] != expected:
            _READER.fail("tree_context_mismatch", "$", "Supply the correctly selected tree envelope.")
        envelope = _READER.mapping(payload, "$")
        tree_source = _READER.mapping(envelope["source"], "$")
        if any(tree_source.get(key) != source.get(key) for key in ("product", "version", "name")):
            _READER.fail("source_context_mismatch", "$", "Input source declarations must agree.")
        rows = _rows(envelope["tree"])
        nodes = preview["nodes"]
        assert isinstance(nodes, list)
        selected: list[tuple[dict[str, object], dict[str, object]]] = [
            (row, node) for row, node in zip(rows, nodes, strict=True) if node["kind"] == "device"
        ]
        ids = [
            _identity(_READER.mapping(row.get("meIdentifier"), "$").get("managedElementID"))
            for row, _ in selected
        ]
        refs = [f"{label}-{node['reference']}" for _, node in selected]
        associations: list[dict[str, object]] = []
        unresolved: list[str] = []
        by_reference = {node["reference"]: node for node in nodes}
        for (_, node), reference in zip(selected, refs, strict=True):
            parent = by_reference.get(node["observed_container_parent"])
            if (
                parent is not None and parent["kind"] == "site"
                and node["parent_relationship"] == "inferred-from-legacy-nesting"
            ):
                associations.append({
                    "device_reference": reference, "site_reference": f"{label}-{parent['reference']}",
                    "basis": "observed-containment-legacy-parent-inference",
                    "semantic_parent_verified": False,
                })
            else:
                unresolved.append(reference)
        dependency_issues = {
            "parent_dependency_unresolved", "explicit_parent_unresolved",
            "explicit_parent_conflicts_with_nesting", "identity_missing_or_unverified_type", "duplicate_identity",
        }
        trees[label] = {
            "identity_field": "meIdentifier.managedElementID", "hierarchy_counts": preview["counts"],
            "devices": _identity_summary(ids, refs), "recognized_site_associations": associations,
            "device_site_associations_unresolved": unresolved,
            "unresolved_hierarchy_dependencies": [
                {"reference": f"{label}-{node['reference']}", "issue_codes": sorted(set(node["issue_codes"]) & dependency_issues)}
                for node in nodes if set(node["issue_codes"]) & dependency_issues
            ],
            "comparison": {
                "status": "not-comparable-with-verified-identity",
                "verified_matches": [], "verified_match_count": 0,
                "inventory_only": None, "tree_only": None,
                "inventory_records_unresolved": inventory_references,
                "tree_device_records_unresolved": refs,
                "inventory_minus_tree_record_count": len(inventory_rows) - len(selected),
                "difference_is_not_evidence_of_missing_device": True,
            },
            "issue_codes": preview["issue_codes"],
        }
    report["trees"] = trees
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Offline Vision inventory/tree identity reconciliation; no live access.")
    parser.add_argument("--inventory", required=True)
    parser.add_argument("--organization", required=True)
    parser.add_argument("--physical", required=True)
    parser.add_argument("--output", help="Optional new safe JSON report; never overwritten.")
    args = parser.parse_args(argv)
    try:
        inputs = OfflineInputs(Path.cwd())
        report = reconcile_inventory(*(
            inputs.read(path, None, base=Path.cwd()) for path in (args.inventory, args.organization, args.physical)
        ))
        if args.output is not None:
            write_local_export(args.output, json.dumps(report, indent=2, allow_nan=False))
        status = ExitStatus.VALIDATION_FAILED
    except ContractValidationError as error:
        codes = sorted({issue.code for issue in error.result.issues})
        report = {
            "operation": "inventory-reconciliation", "status": "error",
            "offline_only": True, "execution_authorized": False, "issue_codes": codes,
        }
        status = ExitStatus.INPUT_ERROR if set(codes) & {
            "input_unreadable", "invalid_encoding", "invalid_json", "nonlocal_input",
            "output_exists", "output_unwritable", "output_cleanup_failed",
        } else ExitStatus.CONTRACT_ERROR
    print(json.dumps(report, allow_nan=False))
    return int(status)


if __name__ == "__main__":
    raise SystemExit(main())
