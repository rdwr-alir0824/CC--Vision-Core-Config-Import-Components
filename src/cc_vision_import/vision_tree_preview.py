"""Local Vision tree evidence inspection; no migration artifacts or API requests."""

from ._contract_validation import ContractReader
from .controller_objects import is_controller_credential_field
from .mappings import dependency_order


_READER = ContractReader("vision-tree-readiness")
_DOMAINS = {
    "vision-physical-tree": ("Physical", "/mgmt/system/config/tree/Physical"),
    "vision-organization-tree": ("Organization", "/mgmt/system/config/tree/Organization"),
}
_CLASSES = {
    "com.radware.insite.model.device.Site": "site",
    "com.radware.insite.model.device.Device": "device",
}


def inspect_vision_tree(payload: object) -> dict[str, object]:
    envelope = _READER.mapping(payload, "$")
    if type(envelope.get("schema_version")) is not int or envelope["schema_version"] != 1:
        _READER.fail("unsupported_schema", "$", "Expected Vision backup schema version 1.")
    domain = envelope.get("domain")
    if not isinstance(domain, str) or domain not in _DOMAINS:
        _READER.fail("unsupported_domain", "$", "Expected a Physical or Organization Vision tree backup.")
    source = _READER.mapping(_READER.required(envelope, "source", "$"), "$.source")
    if source.get("product") != "vision" or source.get("version") != "5.4.9":
        _READER.fail("unsupported_source", "$.source", "Expected Vision 5.4.9 provenance.")
    _READER.text(_READER.required(source, "name", "$.source"), "$.source.name")
    _READER.text(_READER.required(envelope, "collected_at", "$"), "$.collected_at")
    request = _READER.mapping(_READER.required(envelope, "request", "$"), "$.request")
    tree_name, path = _DOMAINS[domain]
    if request.get("method") != "GET" or request.get("path") != path:
        _READER.fail("request_mismatch", "$.request", "Tree domain and recorded GET must agree.")
    scope = _READER.mapping(_READER.required(envelope, "scope", "$"), "$.scope")
    if scope.get("migration_input") is not False or scope.get("complete_configuration_backup") is not False:
        _READER.fail("unsupported_scope", "$.scope", "Expected an evidence-only, incomplete backup.")
    native = _READER.required(envelope, "tree", "$")
    if not isinstance(native, (dict, list)):
        _READER.fail("invalid_tree", "$.tree", "Expected native JSON object or array.")
    expected_count = len(native) if isinstance(native, list) else 1
    if (
        envelope.get("record_count_basis") != "top_level_json_records"
        or type(envelope.get("record_count")) is not int or envelope["record_count"] != expected_count
    ):
        _READER.fail("record_count_mismatch", "$", "Backup count must describe top-level JSON records.")
    if type(envelope.get("redacted_fields")) is not int or envelope["redacted_fields"] < 0:
        _READER.fail("invalid_redaction_count", "$", "Expected a nonnegative redaction count.")
    _READER.mapping(_READER.required(envelope, "evidence", "$"), "$.evidence")
    if not isinstance(envelope.get("issue_codes"), list):
        _READER.fail("invalid_issue_codes", "$", "Expected backup issue-code array.")

    nodes: list[dict[str, object]] = []
    identities: list[str | None] = []
    explicit_parents: list[tuple[object, bool]] = []
    issues = {"destination_mappings_required", "schema_completeness_unverified", "enumeration_completeness_unverified"}

    def visit(value: object, parent: int | None, depth: int, single_root: bool) -> None:
        if depth > 64 or len(nodes) >= 10000:
            _READER.fail("preview_limit_exceeded", "$.tree", "Tree exceeds preview depth or node budget.")
        index = len(nodes)
        codes: set[str] = set()
        row = value if isinstance(value, dict) else {}
        if not isinstance(value, dict):
            codes.add("invalid_node")
        identifier = row.get("meIdentifier")
        identifier = identifier if isinstance(identifier, dict) else {}
        identity = identifier.get("managedElementID")
        valid_identity = (
            isinstance(identity, str) and bool(identity.strip())
            and identity == identity.strip() and all(c.isprintable() for c in identity)
        )
        if not valid_identity:
            codes.add("identity_missing_or_unverified_type")
        native_class = identifier.get("managedElementClass")
        kind = _CLASSES.get(native_class, "unknown") if isinstance(native_class, str) else "unknown"
        if single_root and isinstance(value, dict):
            kind = "root-candidate"
            codes.add("root_role_inferred_from_position")
        elif kind == "unknown":
            codes.add("unknown_node_class")
        if kind in ("site", "device"):
            name = row.get("name")
            if not isinstance(name, str) or not name.strip():
                codes.add("name_missing_or_unverified_type")
        if kind == "device":
            codes.add("device_type_access_and_identity_association_unverified")
        unknown = len(set(row) - {"meIdentifier", "children", "name", "type", "managementIp", "parentOrmID"})
        unknown += len(set(identifier) - {"managedElementID", "managedElementClass"})
        if unknown:
            codes.add("unknown_fields_unverified")
        parent_value = row.get("parentOrmID")
        if "parentOrmID" in row:
            codes.add("explicit_parent_semantics_unverified")
        node: dict[str, object] = {
            "reference": f"node-{index + 1}", "kind": kind,
            "identity_present": valid_identity, "unknown_field_count": unknown,
            "observed_container_parent": None if parent is None else f"node-{parent + 1}",
            "parent_relationship": "unresolved" if parent is None else "nesting-observed-only",
            "destination_mapping": "required", "issue_codes": codes,
        }
        nodes.append(node)
        identities.append(identity if valid_identity else None)
        explicit_parents.append((parent_value, "parentOrmID" in row))
        children = row.get("children")
        if isinstance(children, list):
            if kind == "device" and children:
                codes.add("device_children_unverified")
            for child in children:
                visit(child, index, depth + 1, False)
        else:
            codes.add("children_missing_or_unverified_type")

    if isinstance(native, dict):
        visit(native, None, 0, True)
    else:
        issues.add("array_root_semantics_unverified")
        for item in native:
            visit(item, None, 0, False)
    owners: dict[str, list[int]] = {}
    for index, identity in enumerate(identities):
        if identity is not None:
            owners.setdefault(identity, []).append(index)
    graph: dict[str, set[str]] = {}
    for index, node in enumerate(nodes):
        codes = node["issue_codes"]
        assert isinstance(codes, set)
        identity = identities[index]
        if identity is not None and len(owners[identity]) != 1:
            codes.add("duplicate_identity")
        parent_reference = node["observed_container_parent"]
        dependencies: set[str] = set()
        if isinstance(parent_reference, str):
            parent_index = int(parent_reference.split("-")[1]) - 1
            parent = nodes[parent_index]
            parent_identity = identities[parent_index]
            if (
                identity is not None and len(owners[identity]) == 1
                and parent_identity is not None and len(owners[parent_identity]) == 1
                and parent["kind"] in ("root-candidate", "site")
                and node["kind"] in ("site", "device")
            ):
                dependencies.add(parent_reference)
                node["parent_relationship"] = "inferred-from-legacy-nesting"
            else:
                codes.add("parent_dependency_unresolved")
        explicit, present = explicit_parents[index]
        if present:
            if not isinstance(explicit, str) or len(owners.get(explicit, [])) != 1:
                codes.add("explicit_parent_unresolved")
            else:
                explicit_index = owners[explicit][0]
                if parent_reference != nodes[explicit_index]["reference"]:
                    codes.add("explicit_parent_conflicts_with_nesting")
            if "explicit_parent_unresolved" in codes or "explicit_parent_conflicts_with_nesting" in codes:
                dependencies.clear()
                node["parent_relationship"] = "unresolved-explicit-parent"
        graph[str(node["reference"])] = dependencies
        node["depends_on"] = sorted(dependencies)
        node["issue_codes"] = sorted(codes)
        issues.update(codes)
    order = dependency_order(graph, _READER)
    return {
        "operation": "tree-readiness-preview", "status": "blocked", "offline_only": True,
        "execution_authorized": False, "migration_ready": False,
        "source": {"product": "vision", "version": "5.4.9"}, "tree": tree_name,
        "top_level_json_records": expected_count, "node_candidates_inspected": len(nodes),
        "counts": {kind: sum(node["kind"] == kind for node in nodes) for kind in ("root-candidate", "site", "device", "unknown")},
        "verified_semantic_parent_relationships": 0,
        "dependency_order_basis": "legacy-nesting-inference-not-destination-order",
        "dependency_order": list(order), "nodes": nodes, "issue_codes": sorted(issues),
        "unknown_envelope_field_count": len(set(envelope) - {
            "schema_version", "domain", "source", "collected_at", "request", "scope",
            "evidence", "tree", "record_count", "record_count_basis", "redacted_fields", "issue_codes",
        }),
        "limitations": [
            "root_role_and_parent_links_not_vendor_schema_verified",
            "no_destination_snapshot_or_mappings", "redacted_credentials_not_restorable",
            "unknown_field_values_not_interpreted", "no_executable_plan_or_write_recommendations",
        ],
    }


def _tree_rows(native: object) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []

    def retain(value: object) -> None:
        row = value if isinstance(value, dict) else {}
        rows.append(row)
        children = row.get("children")
        if isinstance(children, list):
            for child in children:
                retain(child)

    if isinstance(native, list):
        for item in native:
            retain(item)
    else:
        retain(native)
    return rows


def inspect_site_migration_readiness(payload: object) -> dict[str, object]:
    """Assess source Site fields and ordering, without producing import data."""
    preview = inspect_vision_tree(payload)
    if preview["tree"] != "Organization":
        _READER.fail("unsupported_site_tree", "$.domain", "Site readiness requires an Organization tree backup.")
    envelope = _READER.mapping(payload, "$")
    rows = _tree_rows(envelope["tree"])
    nodes = preview["nodes"]
    assert isinstance(nodes, list)
    entries = {node["reference"]: (row, node) for row, node in zip(rows, nodes)}
    roots = [(row, node) for row, node in zip(rows, nodes) if node["kind"] == "root-candidate"]

    def usable_name(row: dict[str, object]) -> bool:
        value = row.get("name")
        return isinstance(value, str) and bool(value.strip()) and all(c.isprintable() for c in value)

    root_codes: set[str] = set()
    root_reference = None
    root_usable = False
    if len(roots) == 1:
        root_row, root = roots[0]
        root_reference = root["reference"]
        identifier = root_row.get("meIdentifier")
        if not isinstance(identifier, dict) or identifier.get("managedElementClass") != "com.radware.insite.model.device.Site":
            root_codes.add("root_site_class_unverified")
        if not usable_name(root_row):
            root_codes.add("root_name_missing_or_unusable")
        root_codes.update(set(root["issue_codes"]) - {"root_role_inferred_from_position", "unknown_fields_unverified"})
        root_usable = not root_codes
    else:
        root_codes.add("single_object_site_root_required")
    names: dict[str, int] = {}
    for row, node in zip(rows, nodes):
        if node["kind"] in ("root-candidate", "site") and usable_name(row):
            name = row["name"]
            assert isinstance(name, str)
            names[name] = names.get(name, 0) + 1
    orderable = {root_reference: root_usable}
    records: list[dict[str, object]] = []
    issues = {
        "destination_root_mapping_required", "destination_site_identity_mapping_required",
        "destination_parent_resolution_required", "destination_site_schema_and_version_unqualified",
        "destination_name_matching_and_collision_rules_unverified",
        "parent_name_projection_not_verified_against_legacy_site_lookup",
        "root_role_and_parent_semantics_legacy_inferred",
        "legacy_root_fallback_and_rename_not_adopted", "site_enumeration_completeness_unverified",
    } | root_codes
    unclassified = sum(node["kind"] == "unknown" for node in nodes)
    if unclassified:
        issues.add("unclassified_structure_nodes_present")
    for row, node in zip(rows, nodes):
        if node["kind"] != "site":
            continue
        codes = set(node["issue_codes"])
        parent_ref = node["observed_container_parent"]
        parent_entry = entries.get(parent_ref)
        parent_supported = parent_entry is not None and parent_entry[1]["kind"] in ("site", "root-candidate")
        parent_resolved = parent_supported and bool(node["depends_on"])
        fields = {
            "id": bool(node["identity_present"]) and "duplicate_identity" not in codes,
            "name": usable_name(row),
            "parentOrmID": parent_resolved,
            "parent_site_name": parent_resolved and usable_name(parent_entry[0]),
        }
        missing = [key for key, available in fields.items() if not available]
        sufficient = not missing
        eligible = sufficient and bool(orderable.get(parent_ref, False))
        orderable[node["reference"]] = eligible
        if not parent_resolved:
            codes.add("source_site_parent_dependency_unresolved")
        if not eligible:
            codes.add("source_site_order_blocked")
        if missing:
            codes.add("legacy_site_source_fields_unavailable")
        if not usable_name(row):
            codes.add("site_name_missing_or_unusable")
        if node["unknown_field_count"]:
            codes.add("additional_site_fields_not_projected")
        own_name = row.get("name")
        if isinstance(own_name, str) and names.get(own_name, 0) > 1:
            codes.add("duplicate_source_site_name")
        if parent_supported:
            parent_name = parent_entry[0].get("name")
            if isinstance(parent_name, str) and names.get(parent_name, 0) > 1:
                codes.add("legacy_global_parent_name_lookup_ambiguous")
        records.append({
            "reference": node["reference"],
            "observed_container_parent": parent_ref,
            "source_parent_reference": parent_ref if parent_resolved else None,
            "parent_relationship": node["parent_relationship"],
            "legacy_fields_available": [key for key, available in fields.items() if available],
            "legacy_fields_missing": missing,
            "source_fields_sufficient": sufficient, "source_order_eligible": eligible,
            "unprojected_field_count": node["unknown_field_count"],
            "destination_mapping": "required", "issue_codes": sorted(codes),
        })
        issues.update(codes)
    return {
        "operation": "site-migration-readiness", "domain": "vision-site-readiness-report",
        "status": "blocked", "offline_only": True, "execution_authorized": False,
        "migration_ready": False, "import_file_compatible": False,
        "source": preview["source"], "tree": "Organization",
        "source_ids_reassigned": False, "source_backup_unchanged": True,
        "root_assessment": {
            "reference": root_reference, "source_fields_usable": root_usable,
            "role": "legacy-inferred-not-vendor-qualified",
            "emitted_as_site": False, "destination_mapping": "required",
            "unprojected_field_count": roots[0][1]["unknown_field_count"] if roots else 0,
            "issue_codes": sorted(root_codes),
        },
        "legacy_uploader_site_fields_consumed": ["name", "parent_site_name"],
        "legacy_flat_source_reference_fields": ["id", "parentOrmID"],
        "legacy_site_projection": {
            "id": "copy-native-meIdentifier.managedElementID-without-aliasing",
            "name": "copy-native-name-without-renaming",
            "parentOrmID": "derive-source-parent-managedElementID-from-observed-containment",
            "parent_site_name": "derive-containing-site-name-lookup-equivalence-unverified",
        },
        "counts": {
            "site_candidates_inspected": len(records),
            "sites_with_sufficient_source_fields": sum(row["source_fields_sufficient"] for row in records),
            "sites_with_missing_source_fields": sum(bool(row["legacy_fields_missing"]) for row in records),
            "sites_with_unresolved_parent_dependencies": sum(row["source_parent_reference"] is None for row in records),
            "sites_orderable_from_source_root": sum(row["source_order_eligible"] for row in records),
            "sites_with_unprojected_fields": sum(bool(row["unprojected_field_count"]) for row in records),
            "sites_with_duplicate_names": sum("duplicate_source_site_name" in row["issue_codes"] for row in records),
            "sites_with_ambiguous_parent_names": sum("legacy_global_parent_name_lookup_ambiguous" in row["issue_codes"] for row in records),
            "sites_requiring_destination_mapping": len(records),
            "unclassified_structure_nodes": unclassified,
        },
        "site_candidates": records,
        "source_dependency_order": [row["reference"] for row in records if row["source_order_eligible"]],
        "source_dependency_order_basis": "observed-depth-first-parent-before-child-not-destination-write-order",
        "issue_codes": sorted(issues),
        "limitations": [
            "source-field-sufficiency-is-not-schema-completeness-or-destination-readiness",
            "unprojected-fields-remain-in-unchanged-source-backup",
            "root-is-context-not-a-source-site-to-create",
            "no-destination-ids-assigned-no-parent-fallback-no-import-payloads",
        ],
    }


def inspect_legacy_tree_compatibility(payload: object) -> dict[str, object]:
    """Assess flat legacy field availability; never construct a legacy import file."""
    preview = inspect_vision_tree(payload)
    envelope = _READER.mapping(payload, "$")
    rows = _tree_rows(envelope["tree"])
    nodes = preview["nodes"]
    assert isinstance(nodes, list)
    by_reference = {node["reference"]: (row, node) for row, node in zip(rows, nodes)}
    names: dict[str, int] = {}
    for row, node in zip(rows, nodes):
        name = row.get("name")
        if node["kind"] in ("root-candidate", "site") and isinstance(name, str) and name:
            names[name] = names.get(name, 0) + 1
    records: list[dict[str, object]] = []
    issues = {
        "native_envelope_not_flat_legacy_input", "destination_root_and_parent_resolution_required",
        "legacy_root_fallback_not_adopted", "root_rename_not_implemented_in_reviewed_scripts",
        "target_version_and_api_semantics_unverified", "complete_inventory_coverage_unverified",
    }

    def text_present(row: dict[str, object], key: str) -> bool:
        value = row.get(key)
        return isinstance(value, str) and bool(value.strip())

    def credential_gaps(value: object) -> int:
        if isinstance(value, dict):
            return sum(
                int(
                    not isinstance(item, str) or (
                        not item.strip() or item.strip().lower() in ("redacted", "[redacted]", "<redacted>")
                        or all(character in "*#\u2022\u25cf" for character in item)
                    )
                ) if is_controller_credential_field(key) else credential_gaps(item)
                for key, item in value.items()
            )
        if isinstance(value, list):
            return sum(credential_gaps(item) for item in value)
        return 0

    for row, node in zip(rows, nodes):
        kind = node["kind"]
        codes = set(node["issue_codes"])
        if kind == "root-candidate":
            continue
        available: list[str] = []
        missing: list[str] = []
        if kind not in ("site", "device"):
            codes.add("unsupported_node_not_dropped")
        else:
            for target, present in (
                ("id", node["identity_present"]),
                ("name", text_present(row, "name")),
                ("parentOrmID", bool(node["depends_on"])),
            ):
                (available if present else missing).append(target)
            parent_entry = by_reference.get(node["observed_container_parent"])
            if kind == "site":
                parent_name_present = (
                    bool(node["depends_on"]) and parent_entry is not None
                    and text_present(parent_entry[0], "name")
                )
                (available if parent_name_present else missing).append("parent_site_name")
                if parent_name_present:
                    codes.add("parent_site_name_available_from_containment_only")
                name = row.get("name")
                if isinstance(name, str) and names.get(name, 0) > 1:
                    codes.add("legacy_global_site_name_lookup_ambiguous")
            else:
                for key in ("type", "managementIp"):
                    (available if text_present(row, key) else missing).append(key)
                codes.update({
                    "device_type_and_form_factor_passthrough_unqualified",
                    "credential_requirements_and_portability_unverified",
                    "legacy_post_import_update_requires_destination_snapshot",
                })
                direct = row.get("deviceAccess")
                setup = row.get("deviceSetup")
                nested = setup.get("deviceAccess") if isinstance(setup, dict) else None
                access = direct if isinstance(direct, dict) else nested if isinstance(nested, dict) else None
                if isinstance(direct, dict) and isinstance(nested, dict) and direct != nested:
                    access = None
                    codes.add("device_access_representations_conflict")
                if not access:
                    missing.append("deviceAccess")
                    codes.add("device_access_missing_no_automatic_enrichment")
                    codes.add("device_credentials_unavailable")
                else:
                    available.append("deviceAccess")
                    if credential_gaps(access):
                        codes.add("credential_values_missing_redacted_or_masked")
                    codes.add("device_access_ids_preserved_not_aliased_or_deleted")
            if missing:
                codes.add("legacy_required_fields_unavailable")
        records.append({
            "reference": node["reference"], "kind": kind,
            "source_parent_reference": node["observed_container_parent"],
            "parent_relationship": node["parent_relationship"],
            "legacy_fields_available": sorted(available), "legacy_fields_missing": sorted(missing),
            "issue_codes": sorted(codes),
        })
        issues.update(codes)
    return {
        **preview, "operation": "tree-legacy-compatibility-preview",
        "domain": "vision-legacy-compatibility-report", "import_file_compatible": False,
        "source_backup_unchanged": True, "source_ids_reassigned": False,
        "legacy_processing_order": ["Physical", "Organization"],
        "inventory_identity_crosswalk_required_for_tree_subset": False,
        "legacy_contract": {
            "site_fields": ["name", "id", "parent_site_name", "parentOrmID"],
            "device_fields": ["name", "type", "managementIp", "id", "parentOrmID", "deviceAccess"],
            "root_record_omitted_by_original_flat_export": True,
            "site_order": "source-depth-first-parent-before-child",
            "device_access_enrichment": "legacy-by-IP-not-reproduced",
        },
        "compatibility_counts": {
            "site_records_assessed": sum(row["kind"] == "site" for row in records),
            "device_records_assessed": sum(row["kind"] == "device" for row in records),
            "records_with_missing_legacy_fields": sum(bool(row["legacy_fields_missing"]) for row in records),
            "devices_without_access": sum("deviceAccess" in row["legacy_fields_missing"] for row in records),
            "credential_gap_records": sum(
                bool(set(row["issue_codes"]) & {"device_credentials_unavailable", "credential_values_missing_redacted_or_masked"})
                for row in records
            ),
        },
        "legacy_field_assessments": records,
        "issue_codes": sorted(set(preview["issue_codes"]) | issues),
    }


def format_tree_preview(report: dict[str, object]) -> str:
    if report.get("status") != "blocked":
        errors = report.get("errors", [])
        if not isinstance(errors, list):
            errors = []
        codes = [row["code"] for row in errors if isinstance(row, dict) and isinstance(row.get("code"), str)]
        return "Vision tree readiness preview failed: " + ", ".join(codes) + ". No configuration values displayed."
    if report.get("operation") == "site-migration-readiness":
        return "\n".join([
            "Vision Organization Site readiness: BLOCKED (offline only)",
            f"Source Site assessment: {report['counts']}",
            "Source-only parent-before-child order: " + ", ".join(report["source_dependency_order"]),
            "Root is context only; source IDs and hierarchy are unchanged.",
            "Issues: " + ", ".join(report["issue_codes"]),
            "Destination root/site identities, parent resolution and version-specific schema require qualification.",
            "Report only: no Sites import file, executable plan or Device association.",
        ])
    lines = [
        f"Vision {report['tree']} tree readiness: BLOCKED (offline only)",
        f"Top-level JSON records: {report['top_level_json_records']}; node candidates inspected: {report['node_candidates_inspected']}",
        f"Hierarchy candidates: {report['counts']}",
        "Nesting is observed; root/parent meanings are legacy-based inference, not verified destination mappings.",
        "Issues: " + ", ".join(report["issue_codes"]),
        "Destination mappings, schema qualification and credential readiness remain unresolved.",
        "No executable import plan or write recommendations.",
    ]
    if "compatibility_counts" in report:
        lines.extend([
            f"Legacy flat-format assessment: {report['compatibility_counts']}",
            "Inventory ID crosswalk is not required for this tree subset; full inventory coverage remains unverified.",
            "Report only: not a legacy sites/devices import file; no root fallback, enrichment or credential changes.",
        ])
    return "\n".join(lines)
