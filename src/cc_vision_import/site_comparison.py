"""Sanitized, non-executable comparison of saved Organization Site evidence."""

import copy
import re
from collections import Counter, defaultdict
from datetime import datetime

from ._contract_validation import ContractReader
from .destination_discovery import project_site_tree
from .vision_tree_preview import _tree_rows, inspect_site_migration_readiness


_READER = ContractReader("source-destination-site-comparison")
_SITE = "com.radware.insite.model.device.Site"
_CLASSIFICATIONS = (
    "candidate_for_creation", "possible_existing_destination_site",
    "ambiguous_mapping", "blocked_insufficient_evidence",
)
_DESTINATION_CODES = {
    "native_identity_missing_or_unverified_type", "site_name_missing_or_unverified_type",
    "root_site_class_unverified", "duplicate_native_identity", "duplicate_site_name",
    "site_parent_dependency_unresolved", "ancestor_dependency_unresolved",
    "explicit_parent_conflicts_with_containment", "explicit_parent_type_unverified",
    "children_missing_or_unverified_type", "additional_fields_not_projected",
}


def _timestamp(value: object) -> str:
    text = _READER.text(value, "$.collected_at")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        _READER.fail("invalid_collection_timestamp", "$.collected_at", "Expected an ISO-8601 collection timestamp.")
    if parsed.tzinfo is None:
        _READER.fail("invalid_collection_timestamp", "$.collected_at", "Collection timestamp requires a timezone.")
    return parsed.isoformat()


def _destination(payload: object) -> tuple[dict, dict, list[dict]]:
    snapshot = _READER.mapping(payload, "$")
    if type(snapshot.get("schema_version")) is not int or snapshot["schema_version"] != 1:
        _READER.fail("unsupported_snapshot_schema", "$", "Expected destination snapshot schema version 1.")
    if snapshot.get("domain") != "cc-destination-organization-sites":
        _READER.fail("unsupported_snapshot_domain", "$", "Supply the saved destination Site snapshot, not an import file.")
    destination = _READER.mapping(snapshot.get("destination"), "$.destination")
    if destination.get("product") != "cyber-controller":
        _READER.fail("unsupported_destination", "$", "Expected Cyber Controller discovery provenance.")
    request = _READER.mapping(snapshot.get("request"), "$.request")
    if request.get("method") != "GET" or request.get("path") != "/mgmt/system/config/tree/Organization":
        _READER.fail("snapshot_request_mismatch", "$", "Expected the evidenced Organization GET snapshot.")
    scope = _READER.mapping(snapshot.get("scope"), "$.scope")
    if (
        scope.get("read_only") is not True or scope.get("migration_input") is not False
        or scope.get("configuration_writes_authorized") is not False
        or scope.get("complete_site_enumeration") is not False
        or scope.get("devices_excluded") is not True
    ):
        _READER.fail("unsupported_snapshot_scope", "$", "Expected incomplete, Site-only read evidence.")
    sites = snapshot.get("site_nodes")
    if not isinstance(sites, list) or len(sites) > 9999:
        _READER.fail("invalid_snapshot_sites", "$", "Expected a bounded Site array.")
    rows = [_READER.mapping(snapshot.get("organization_root"), "$.organization_root")]
    rows.extend(_READER.mapping(row, "$.site_nodes") for row in sites)
    references: dict[str, dict] = {}
    for row in rows:
        reference = row.get("reference")
        if (
            not isinstance(reference, str) or not re.fullmatch(r"node-[1-9][0-9]{0,4}", reference)
            or int(reference[5:]) > 10000
        ):
            _READER.fail("invalid_snapshot_reference", "$", "Expected discovery-local node references.")
        if reference in references:
            _READER.fail("duplicate_snapshot_reference", "$", "Snapshot references must be unique.")
        references[reference] = row
        parent = row.get("observed_container_parent")
        if parent is not None and (
            not isinstance(parent, str) or not re.fullmatch(r"node-[1-9][0-9]{0,4}", parent)
            or int(parent[5:]) > 10000
        ):
            _READER.fail("invalid_snapshot_parent_reference", "$", "Expected a discovery-local containing-parent reference.")
        native = _READER.mapping(row.get("native"), "$.native")
        identifier = _READER.mapping(native.get("meIdentifier"), "$.native.meIdentifier")
        if row is not rows[0] and identifier.get("managedElementClass") != _SITE:
            _READER.fail("unsupported_snapshot_site_class", "$", "Only native Site records may appear in the Site snapshot array.")
        count = row.get("unprojected_field_count")
        if type(count) is not int or count < 0:
            _READER.fail("invalid_unprojected_count", "$", "Expected a nonnegative unprojected field count.")
        if not isinstance(row.get("issue_codes"), list):
            _READER.fail("invalid_snapshot_issues", "$", "Expected snapshot issue-code arrays.")
    root = rows[0]
    if root.get("observed_container_parent") is not None:
        _READER.fail("invalid_snapshot_root", "$", "Root context cannot have a containing parent.")

    # Reproject only observed, root-connected Site containment. Never attach orphans.
    children: dict[str, list[dict]] = defaultdict(list)
    for row in rows[1:]:
        parent = row.get("observed_container_parent")
        if isinstance(parent, str):
            children[parent].append(row)
    visited: set[str] = set()
    original_references: list[str] = []

    def native_tree(row: dict, depth: int) -> dict:
        reference = row["reference"]
        if depth > 64 or reference in visited:
            _READER.fail("snapshot_hierarchy_limit", "$", "Snapshot containment exceeds the hierarchy budget.")
        visited.add(reference)
        original_references.append(reference)
        native = row["native"]
        result = copy.deepcopy({key: native[key] for key in ("name", "meIdentifier", "parentOrmID") if key in native})
        result["children"] = [native_tree(child, depth + 1) for child in children[reference]]
        return result

    projection = project_site_tree(native_tree(root, 0))
    projected = [projection["organization_root"], *projection["site_nodes"]]
    if len(projected) != len(original_references):
        _READER.fail("snapshot_projection_mismatch", "$", "Retained Site projection must agree with observed containment.")
    derived = {reference: row for reference, row in zip(original_references, projected)}
    qualified: list[dict] = []
    for row in rows:
        checked = derived.get(row["reference"])
        codes = set(checked["issue_codes"]) if checked is not None else {"site_parent_dependency_unresolved"}
        codes.update(code for code in row["issue_codes"] if isinstance(code, str) and code in _DESTINATION_CODES)
        if any(not isinstance(code, str) or code not in _DESTINATION_CODES for code in row["issue_codes"]):
            codes.add("unrecognized_snapshot_issue_codes")
        if row.get("parent_relationship") not in ("root-context", "legacy-nesting-inferred"):
            codes.add("site_parent_dependency_unresolved")
        if row["unprojected_field_count"]:
            codes.add("additional_fields_not_projected")
        qualified.append({**row, "issue_codes": codes})
    counts = _READER.mapping(snapshot.get("counts"), "$.counts")
    if (
        type(counts.get("root_candidates")) is not int or counts["root_candidates"] != 1
        or type(counts.get("site_candidates")) is not int
        or counts["site_candidates"] != len(sites)
        or type(counts.get("unclassified_nodes")) is not int or counts["unclassified_nodes"] < 0
    ):
        _READER.fail("snapshot_count_mismatch", "$", "Snapshot counts must agree with retained Site records.")
    return snapshot, qualified[0], qualified[1:]


def compare_sites(
    source_payload: object, destination_payload: object, *,
    source_root_name: str | None = None, destination_root_name: str | None = None,
    confirm_root_mapping: bool = False, destination_gui_version: str | None = None,
) -> dict[str, object]:
    readiness = inspect_site_migration_readiness(source_payload)
    source = _READER.mapping(source_payload, "$")
    source_rows = _tree_rows(source["tree"])
    snapshot, destination_root, destination_sites = _destination(destination_payload)
    if type(confirm_root_mapping) is not bool:
        _READER.fail("invalid_root_confirmation", "$", "Root confirmation must be an explicit boolean.")
    if (source_root_name is None) != (destination_root_name is None) or (confirm_root_mapping and source_root_name is None):
        _READER.fail("incomplete_root_declaration", "$", "Supply both root names before explicitly confirming a mapping.")
    if source_root_name is not None:
        _READER.text(source_root_name, "$.source_root_name")
        _READER.text(destination_root_name, "$.destination_root_name")
    if destination_gui_version is not None and not re.fullmatch(
        r"[0-9]+\.[0-9]+\.[0-9]+(?:-[0-9]+)?", _READER.text(destination_gui_version, "$.destination_gui_version"),
    ):
        _READER.fail("invalid_gui_version", "$", "Supply a numeric GUI-observed version; it is never API verification.")
    root_assessment = readiness["root_assessment"]
    source_root_ref = root_assessment["reference"]
    source_root = source_rows[int(source_root_ref.split("-")[1]) - 1] if source_root_ref else {}
    destination_root_ref = destination_root["reference"]
    root_native = destination_root["native"]
    root_usable = root_assessment["source_fields_usable"] and not (
        destination_root["issue_codes"] - {"additional_fields_not_projected", "duplicate_site_name"}
    )
    root_status = "missing"
    if source_root_name is not None:
        names_match = source_root.get("name") == source_root_name and root_native.get("name") == destination_root_name
        root_status = "unqualified" if not root_usable else "mismatch" if not names_match else "confirmed" if confirm_root_mapping else "proposed"
    root_confirmed = root_status == "confirmed"
    by_name: dict[str, list[dict]] = defaultdict(list)
    for row in destination_sites:
        name = row["native"].get("name")
        if isinstance(name, str):
            by_name[name].append(row)
    identities = Counter(
        row["native"].get("meIdentifier", {}).get("managedElementID")
        for row in [destination_root, *destination_sites]
        if isinstance(row["native"].get("meIdentifier", {}).get("managedElementID"), str)
    )
    unsafe_destination = snapshot["counts"]["unclassified_nodes"] > 0 or any(
        row["issue_codes"] - {"additional_fields_not_projected", "duplicate_site_name"}
        for row in destination_sites
    )
    records: list[dict] = []
    resolved: dict[str, dict] = {}
    potential_creations = 0
    for candidate in readiness["site_candidates"]:
        reference = candidate["reference"]
        native = source_rows[int(reference.split("-")[1]) - 1]
        name = native.get("name")
        matches = by_name.get(name, []) if isinstance(name, str) else []
        codes = set(candidate["issue_codes"])
        parent_ref = candidate["source_parent_reference"]
        parent = resolved.get(parent_ref)
        expected_parent = destination_root_ref if parent_ref == source_root_ref and root_confirmed else (
            parent["destination_candidates"][0].removeprefix("destination:")
            if parent and parent["classification"] == "possible_existing_destination_site" else None
        )
        parent_blocked = parent_ref != source_root_ref and (
            parent is None or parent["classification"] in ("ambiguous_mapping", "blocked_insufficient_evidence")
        )
        root_collision = isinstance(name, str) and name == root_native.get("name")
        source_ambiguous = bool(codes & {"duplicate_source_site_name", "legacy_global_parent_name_lookup_ambiguous"})
        if candidate["source_order_eligible"] and not matches and not root_collision and not source_ambiguous and not unsafe_destination:
            potential_creations += 1
        classification = "blocked_insufficient_evidence"
        if not candidate["source_order_eligible"]:
            codes.add("source_fields_or_dependencies_insufficient")
        elif source_ambiguous or root_collision or len(matches) > 1:
            classification = "ambiguous_mapping"
            codes.add("site_name_collision_ambiguous")
        elif not root_confirmed:
            codes.add("confirmed_root_mapping_required")
        elif parent_blocked:
            codes.add("source_parent_mapping_blocked")
        elif matches:
            match = matches[0]
            identity = match["native"].get("meIdentifier", {}).get("managedElementID")
            if (
                not isinstance(identity, str) or identities[identity] != 1
                or match["observed_container_parent"] != expected_parent or expected_parent is None
                or match["issue_codes"] - {"additional_fields_not_projected", "duplicate_site_name"}
            ):
                classification = "ambiguous_mapping"
                codes.add("destination_identity_or_parent_collision_unresolved")
            elif unsafe_destination:
                codes.add("destination_structure_or_collision_evidence_insufficient")
            else:
                classification = "possible_existing_destination_site"
                codes.add("name_and_containment_candidate_not_identity_equivalence")
        elif unsafe_destination:
            codes.add("destination_structure_or_collision_evidence_insufficient")
        else:
            classification = "candidate_for_creation"
            codes.add("absence_in_incomplete_snapshot_not_verified_absence")
        if parent_ref != source_root_ref and parent_ref is not None:
            codes.add("parent_destination_identity_requires_future_resolution")
        record = {
            "source_reference": "source:" + reference, "classification": classification,
            "source_identity_present": "id" in candidate["legacy_fields_available"],
            "source_parent_reference": None if parent_ref is None else "source:" + parent_ref,
            "observed_source_container_parent": (
                None if candidate["observed_container_parent"] is None else "source:" + candidate["observed_container_parent"]
            ),
            "source_parent_relationship": candidate["parent_relationship"],
            "missing_source_fields": candidate["legacy_fields_missing"],
            "source_order_eligible": candidate["source_order_eligible"],
            "destination_candidates": ["destination:" + row["reference"] for row in matches],
            "destination_candidate_parents": [
                {"reference": "destination:" + row["reference"],
                 "parent_reference": None if row["observed_container_parent"] is None else "destination:" + row["observed_container_parent"]}
                for row in matches
            ],
            "destination_identity_assigned": False,
            "parent_destination_reference_candidate": None if expected_parent is None else "destination:" + expected_parent,
            "requires_destination_identity_from_source_parent": (
                None if parent_ref is None or parent_ref == source_root_ref else "source:" + parent_ref
            ),
            "unprojected_source_field_count": candidate["unprojected_field_count"],
            "issue_codes": sorted(codes),
        }
        records.append(record)
        resolved[reference] = record
    blockers = {
        "source_and_destination_enumeration_unverified", "destination_schema_and_create_contract_unqualified",
        "destination_version_api_unverified", "root_and_parent_semantics_legacy_inferred",
        "site_names_are_collision_candidates_not_identity_equivalence",
        "future_site_identity_assignment_and_readback_required", "unprojected_fields_not_transformed",
        "destination_native_identity_to_create_parent_field_unqualified",
    }
    if not root_confirmed:
        blockers.add("confirmed_root_mapping_required")
    if unsafe_destination:
        blockers.add("destination_structure_or_collision_evidence_insufficient")
    return {
        "schema_version": 1, "domain": "source-destination-site-comparison-report",
        "operation": "site-comparison", "status": "blocked", "offline_only": True,
        "migration_ready": False, "execution_authorized": False, "configuration_writes_authorized": False,
        "import_file_compatible": False, "devices_processed": False,
        "provenance": {
            "source": {"product": "vision", "version": "5.4.9", "collected_at": _timestamp(source["collected_at"])},
            "destination": {
                "product": "cyber-controller", "api_verified_version": None,
                "snapshot_version_unqualified": True, "collected_at": _timestamp(snapshot.get("collected_at")),
                "gui_observed_version": destination_gui_version, "gui_version_evidence": "operator-declared-not-api-verified",
                "complete_site_enumeration": False,
            },
        },
        "identity_policy": {
            "native_field": "meIdentifier.managedElementID", "namespaces_distinct": True,
            "identities_retained_in_immutable_inputs": True, "source_ids_reassigned": False,
            "artifact_local_references_only": True, "root_identity_equivalence_claimed": False,
        },
        "root_mapping": {
            "status": root_status, "source_reference": None if source_root_ref is None else "source:" + source_root_ref,
            "destination_reference": "destination:" + destination_root_ref,
            "operator_confirmed": root_confirmed, "roots_renamed": False,
            "source_issue_codes": root_assessment["issue_codes"],
            "destination_issue_codes": sorted(destination_root["issue_codes"]),
        },
        "counts": {
            "source_sites": len(records), "destination_sites": len(destination_sites),
            "source_orderable_sites": len(readiness["source_dependency_order"]),
            "potential_creations_if_mappings_qualified": potential_creations,
            **{kind: sum(row["classification"] == kind for row in records) for kind in _CLASSIFICATIONS},
            "destination_duplicate_name_groups": sum(len(rows) > 1 for rows in by_name.values()),
            "source_sites_with_name_collisions": sum(bool(row["destination_candidates"]) for row in records),
            "sites_requiring_parent_destination_identity": sum(row["requires_destination_identity_from_source_parent"] is not None for row in records),
            "source_sites_with_unprojected_fields": sum(bool(row["unprojected_source_field_count"]) for row in records),
            "destination_sites_with_unprojected_fields": sum(bool(row["unprojected_field_count"]) for row in destination_sites),
            "source_root_unprojected_field_count": root_assessment["unprojected_field_count"],
            "destination_root_unprojected_field_count": destination_root["unprojected_field_count"],
        },
        "source_dependency_order": ["source:" + reference for reference in readiness["source_dependency_order"]],
        "dependency_order_basis": readiness["source_dependency_order_basis"],
        "site_comparisons": records, "blockers": sorted(blockers),
        "limitations": [
            "conditional-candidates-only-not-create-payloads-or-an-executable-plan",
            "native-identities-names-and-unprojected-values-remain-only-in-protected-inputs",
            "GUI-version-declaration-does-not-qualify-API-or-schema-compatibility",
        ],
    }


def format_site_comparison(report: dict[str, object]) -> str:
    if report.get("status") == "error":
        errors = report.get("errors", [])
        assert isinstance(errors, list)
        return "Site comparison failed: " + ", ".join(row["code"] for row in errors)
    counts = report["counts"]
    root_mapping = report["root_mapping"]
    assert isinstance(counts, dict) and isinstance(root_mapping, dict)
    return "\n".join([
        "Offline Source-to-Destination Site comparison: migration BLOCKED (non-executable)",
        "Root mapping: " + str(root_mapping["status"]),
        *(f"{key.replace('_', ' ')}: {counts[key]}" for key in (
            "source_sites", "destination_sites", "source_orderable_sites",
            "potential_creations_if_mappings_qualified", *_CLASSIFICATIONS,
            "sites_requiring_parent_destination_identity",
        )),
        "Destination enumeration, API version and create/schema compatibility remain unqualified.",
        "Native identities remain distinct in unchanged inputs; no Device processing or controller writes.",
    ])
