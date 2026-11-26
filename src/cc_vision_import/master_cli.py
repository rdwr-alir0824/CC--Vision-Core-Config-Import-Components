"""Master interface for offline consolidation and explicitly selected Vision reads."""

import argparse
import json
from collections.abc import Sequence
from pathlib import Path

from .capabilities import LookupCapability, ProductClientError, require_capability
from .contracts import ContractValidationError, ExitStatus
from .controller_exports import adapt_flat_export, adapt_tree_response
from .controller_objects import TreeName
from .controller_workflow import plan_offline_request
from .offline_inputs import OfflineInputs, write_local_export as _write_export
from .product_clients import adapt_read_response, read_request_segments
from .profiles import DestinationProfile, SourceProfile
from .transport import build_url


_LOOKUPS = {
    "lookup-site-by-name": LookupCapability.SITE_BY_NAME,
    "lookup-site-by-id": LookupCapability.SITE_BY_ID,
    "lookup-device-by-ip": LookupCapability.DEVICE_BY_IP,
}
_OPERATIONS = (
    "operations", "profiles", "export", "compare", "plan", "import-preview",
    "authenticate", "import", "backup-vision", "destination-discovery", "tree-readiness-preview", "site-comparison", *_LOOKUPS,
    "single-site-dry-run", "single-site-create",
    "site-batch-dry-run", "site-batch-execute", "site-batch-resume", "site-batch-reconcile",
    "device-batch-dry-run", "device-batch-execute", "device-batch-resume",
    "migration-dry-run", "migration-status",
)
_VISION_LIMITATION = "Vision controller export schemas and Vision-to-CC mappings are not established."
_DOMAIN_LIMITATIONS = {
    "ldap-permissions": "Vision LDAP code exists, but CC LDAP contracts and permission mappings are unresolved.",
    "scheduler": "Legacy Scheduler paths are INI-configured and unresolved; CC task contracts are absent.",
}


def _report(operation: str, status: str, **fields: object) -> dict[str, object]:
    return {
        "operation": operation, "status": status, "offline_only": operation not in ("backup-vision", "destination-discovery"),
        "execution_authorized": False, "tls_verification_required": True, **fields,
    }


def _unavailable(operation: str, code: str, message: str) -> tuple[dict[str, object], ExitStatus]:
    return _report(operation, "unavailable", errors=[{"code": code, "message": message}]), ExitStatus.CONTRACT_ERROR


def _profile(
    inputs: OfflineInputs, manifest: dict[str, object] | None,
    role: str, path: str | None, product: str,
) -> SourceProfile | DestinationProfile:
    profile_type = SourceProfile if role == "source" else DestinationProfile
    declared = None
    if manifest is not None:
        side = inputs.reader.mapping(manifest[role], "$")
        declared = profile_type.from_dict(inputs.read(inputs.reader.required(side, "profile", "$"), None))
    if path is not None:
        profile = profile_type.from_dict(inputs.read(path, None, base=Path.cwd()))
        if declared is not None and profile != declared:
            inputs.reader.fail("profile_mismatch", "$", "CLI and manifest profiles must agree; inputs are never silently retargeted.")
    elif declared is not None:
        profile = declared
    else:
        inputs.reader.fail("missing_profile", "$", "Supply a profile file or a request containing its profile.")
    if profile.product != product:
        inputs.reader.fail("product_mismatch", "$", "Selected products and connection profiles must agree.")
    return profile


def _profiles(
    inputs: OfflineInputs, manifest: dict[str, object] | None,
    source_path: str | None, destination_path: str | None, source_product: str,
) -> tuple[SourceProfile, DestinationProfile]:
    source = _profile(inputs, manifest, "source", source_path, source_product)
    destination = _profile(inputs, manifest, "destination", destination_path, "cyber-controller")
    assert isinstance(source, SourceProfile) and isinstance(destination, DestinationProfile)
    return source, destination


def _lookup(
    inputs: OfflineInputs, source: SourceProfile, operation: str, value: str,
    input_path: str | None, exported_at: str | None, output_path: str | None,
) -> dict[str, object]:
    capability = require_capability(source.product, source.version, _LOOKUPS[operation], mock_only=True)
    build_url(source.base_url, read_request_segments(capability, lookup_value=value))
    report = _report(
        operation, "request-preview", request_method="GET",
        path_template="/" + "/".join(capability.segments), source_record=capability.source_record,
        complete_configuration_export=False, compatibility_verified=False,
        query_response_binding_verified=False, live_dispatch_available=False,
    )
    if input_path is not None:
        assert exported_at is not None
        result = adapt_read_response(capability, inputs.read(input_path, None))
        artifact = result.to_artifact(exported_at=exported_at)
        if output_path is not None:
            _write_export(output_path, artifact.to_json())
        report.update(
            status="lookup-response-inspected", object_count=len(artifact.objects),
            artifact_written=output_path is not None,
            note="Supplied synthetic response only; identity aliases, query binding, absence semantics and export completeness are unverified.",
        )
    return report


def _export_input(
    inputs: OfflineInputs, source: SourceProfile, args: argparse.Namespace,
) -> tuple[dict[str, object], ExitStatus]:
    payload = inputs.read(args.input, None)
    context = {
        "controller_id": args.controller_id, "tree": TreeName(args.tree),
        "version": source.version, "exported_at": args.exported_at,
    }
    if args.format == "flat":
        result = adapt_flat_export(payload, root_response=inputs.read(args.root, None), **context)
    else:
        result = adapt_tree_response(payload, **context)
    _write_export(args.output, result.artifact.to_json())
    valid = result.validation.status == "valid"
    return _report(
        "export", "exported" if valid else "exported-incomplete",
        object_count=len(result.artifact.objects), completeness=result.completeness,
        planning_input_valid=valid,
        issue_codes=[issue.code for issue in result.validation.issues],
        note="Supplied local data only; no missing device access is fetched or inferred. Offline validity does not establish completeness or authorize import.",
    ), ExitStatus.SUCCESS if valid else ExitStatus.VALIDATION_FAILED


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python master.py",
        description="Offline tools, selected controller reads, or explicitly authorized experimental Site migration.",
    )
    parser.add_argument("--operation", choices=_OPERATIONS, required=True)
    parser.add_argument("--report-format", choices=("text", "json"), help="Tree/Site report format; batch JSON emits only a compact launcher result.")
    parser.add_argument("--legacy-compatibility", action="store_true", help="Assess tree fields against the legacy flat input contract; report only.")
    parser.add_argument("--site-readiness", action="store_true", help="Assess Organization Site source fields and dependencies only; report only.")
    parser.add_argument("--module", choices=("controller-objects", "ldap-permissions", "scheduler"), default="controller-objects")
    parser.add_argument("--source-product", choices=("vision", "cyber-controller"), default="cyber-controller")
    parser.add_argument("--destination-product", choices=("cyber-controller",), default="cyber-controller")
    parser.add_argument("--source-profile", help="Local source profile JSON; must agree with a supplied manifest.")
    parser.add_argument("--destination-profile", help="Local destination profile JSON; must agree with a supplied manifest.")
    parser.add_argument("--request", help="Existing offline-controller request JSON; paths inside it are relative to its directory.")
    parser.add_argument("--output", help="New local export or lookup artifact file; never overwritten.")
    parser.add_argument("--input", help="Supplied local tree/flat export or single lookup-response JSON.")
    parser.add_argument("--lookup-value", help="Site name/ID or device IP for a lookup request preview.")
    parser.add_argument("--format", choices=("tree", "flat"), help="Standalone export format; defaults to tree.")
    parser.add_argument("--tree", choices=("Physical", "Organization"), help="Explicit standalone export tree.")
    parser.add_argument("--controller-id", help="Explicit source identity for standalone export.")
    parser.add_argument("--root", help="Explicit local root response required for flat export.")
    parser.add_argument("--exported-at", help="ISO-8601 timestamp for supplied export/lookup data.")
    parser.add_argument("--backup-profile", help="External JSON profile for explicit Vision 5.4.9 live backup.")
    parser.add_argument("--discovery-profile", help="External JSON profile for selected CC discovery or Site operation; version unknown.")
    parser.add_argument("--qualify-default-root", action="store_true", help="Destination discovery: read only Default by name instead of the Organization tree.")
    parser.add_argument("--credentials-file", help="Read-only mounted owner-private JSON credentials file; never a password argument.")
    parser.add_argument("--destination-snapshot", help="Saved read-only destination Organization Site snapshot for offline comparison.")
    parser.add_argument("--source-root-name", help="Reviewed source root name for a proposed offline root association.")
    parser.add_argument("--destination-root-name", help="Reviewed destination root name for a proposed offline root association.")
    parser.add_argument("--confirm-root-mapping", action="store_true", help="Explicitly confirm the proposed root association; never renames roots or authorizes writes.")
    parser.add_argument("--destination-gui-version", help="Optional operator-declared GUI version; never API qualification.")
    parser.add_argument("--comparison", help="Confirmed hash-bound Site comparison report for a Site operation.")
    parser.add_argument("--site-reference", help="Exactly one source:node-N reference; never a native identifier.")
    parser.add_argument("--target-version", help="Optional exact operator-declared CC 10.x release; not API verification.")
    parser.add_argument("--operation-delay", type=float, help="Site batch: delay between Sites, 0-60 seconds.")
    parser.add_argument("--readback-interval", type=float, help="Site batch: delay between bounded readback rounds, 0-60 seconds.")
    parser.add_argument("--readback-attempts", type=int, help="Site batch: 1-10 readback rounds.")
    args = parser.parse_args(argv)
    single_site = args.operation in ("single-site-dry-run", "single-site-create")
    site_batch = args.operation in ("site-batch-dry-run", "site-batch-execute", "site-batch-resume", "site-batch-reconcile")
    device_batch = args.operation in (
        "device-batch-dry-run", "device-batch-execute", "device-batch-resume", "migration-dry-run", "migration-status",
    )
    migration_batch = site_batch or device_batch
    site_operation = single_site or migration_batch
    if site_operation:
        if any(value is None for value in (
            args.input, args.comparison, args.destination_snapshot,
            args.discovery_profile, args.credentials_file,
        )) or (single_site and args.site_reference is None) or (migration_batch and args.site_reference is not None) or args.module != "controller-objects" or any(value is not None for value in (
            args.request, args.source_profile, args.destination_profile, args.lookup_value,
            args.format, args.tree, args.controller_id, args.root, args.exported_at, args.backup_profile,
            args.output, args.source_root_name, args.destination_root_name, args.destination_gui_version,
        )) or args.confirm_root_mapping or args.qualify_default_root:
            parser.error("Site operations require source, comparison, snapshot and discovery profile/credentials; a Site reference is required only for single-Site mode.")
    elif any(value is not None for value in (args.comparison, args.site_reference, args.target_version)):
        parser.error("Single-Site options require an explicit single-site-dry-run or single-site-create operation.")
    if not site_batch and any(value is not None for value in (
        args.operation_delay, args.readback_interval, args.readback_attempts,
    )):
        parser.error("Batch timing options require an explicit site-batch operation.")
    site_comparison = args.operation == "site-comparison"
    if site_comparison:
        if args.input is None or args.destination_snapshot is None or args.module != "controller-objects" or any(
            value is not None for value in (
                args.request, args.source_profile, args.destination_profile, args.lookup_value,
                args.format, args.tree, args.controller_id, args.root, args.exported_at,
                args.backup_profile, args.discovery_profile, args.credentials_file,
            )
        ):
            parser.error("site-comparison requires --input and --destination-snapshot; no profiles, credentials or live options.")
        if (args.source_root_name is None) != (args.destination_root_name is None) or (
            args.confirm_root_mapping and args.source_root_name is None
        ):
            parser.error("Supply both root names before explicitly confirming their proposed association.")
    elif not site_operation and (args.confirm_root_mapping or any(value is not None for value in (
        args.destination_snapshot, args.source_root_name, args.destination_root_name, args.destination_gui_version,
    ))):
        parser.error("Root mapping and destination snapshot options require site-comparison.")
    destination_discovery = args.operation == "destination-discovery"
    if args.qualify_default_root and not destination_discovery:
        parser.error("--qualify-default-root requires destination-discovery.")
    if destination_discovery:
        if args.discovery_profile is None or args.credentials_file is None:
            parser.error("destination-discovery requires --discovery-profile and --credentials-file.")
        if args.module != "controller-objects" or any(value is not None for value in (
            args.backup_profile, args.source_profile, args.destination_profile, args.request,
            args.output, args.input, args.lookup_value, args.format, args.tree,
            args.controller_id, args.root, args.exported_at,
        )):
            parser.error("destination-discovery uses only its discovery profile and credentials file.")
    elif args.discovery_profile is not None and not site_operation:
        parser.error("--discovery-profile requires destination-discovery.")
    tree_preview = args.operation == "tree-readiness-preview"
    if args.report_format is not None and not (tree_preview or site_comparison or migration_batch):
        parser.error("--report-format is supported only for tree-readiness-preview, site-comparison or Site batch operations.")
    if args.legacy_compatibility and not tree_preview:
        parser.error("--legacy-compatibility requires tree-readiness-preview.")
    if args.site_readiness and (not tree_preview or args.legacy_compatibility):
        parser.error("--site-readiness requires tree-readiness-preview and cannot combine with --legacy-compatibility.")
    if tree_preview:
        if args.input is None or args.module != "controller-objects" or any(
            value is not None for value in (
                args.request, args.source_profile, args.destination_profile, args.lookup_value,
                args.format, args.tree, args.controller_id, args.root, args.exported_at,
            )
        ):
            parser.error("tree-readiness-preview requires --input and optional --output/--report-format only.")
    live_backup = args.operation == "backup-vision"
    if live_backup:
        if args.backup_profile is None or args.credentials_file is None:
            parser.error("backup-vision requires --backup-profile and --credentials-file.")
        if args.module != "controller-objects" or any(
            value is not None for value in (
                args.source_profile, args.destination_profile, args.request, args.output,
                args.input, args.lookup_value, args.format, args.tree, args.controller_id,
                args.root, args.exported_at,
            )
        ):
            parser.error("backup-vision uses only its backup profile and credentials file, not offline input options.")
    elif args.backup_profile is not None or (args.credentials_file is not None and not destination_discovery and not site_operation):
        parser.error("backup profile/credentials options require explicit --operation backup-vision.")
    lookup = args.operation in _LOOKUPS
    standalone_export = args.operation == "export" and args.input is not None
    if args.output is not None and args.operation != "export" and not lookup and not tree_preview and not site_comparison:
        parser.error("--output is supported only for offline export or lookup artifacts.")
    if args.operation == "export" and args.output is None:
        parser.error("offline export requires --output.")
    if args.operation in ("export", "compare", "plan", "import-preview") and args.request is None and not standalone_export:
        parser.error("this operation requires --request.")
    if args.input is not None and not (lookup or standalone_export or tree_preview or site_comparison or site_operation):
        parser.error("--input is supported only for export or lookup.")
    if args.request is not None and (lookup or standalone_export):
        parser.error("standalone export/lookup cannot be combined with --request.")
    if (lookup or standalone_export) and args.destination_profile is not None:
        parser.error("standalone source reads do not use a destination profile.")
    if lookup and args.lookup_value is None:
        parser.error("lookup requires --lookup-value.")
    if args.lookup_value is not None and not lookup:
        parser.error("--lookup-value is supported only for lookup.")
    if lookup and args.output is not None and args.input is None:
        parser.error("writing a lookup artifact requires --input.")
    if (standalone_export or lookup and args.input is not None) and args.exported_at is None:
        parser.error("supplied export/lookup data requires --exported-at.")
    if any(value is not None for value in (args.format, args.tree, args.controller_id, args.root)) and not standalone_export:
        parser.error("export format/tree/controller/root arguments require standalone --input export.")
    if args.exported_at is not None and not (standalone_export or lookup and args.input is not None):
        parser.error("--exported-at requires supplied export/lookup data.")
    if standalone_export:
        args.format = args.format or "tree"
        if args.tree is None or args.controller_id is None:
            parser.error("standalone export requires --tree and --controller-id.")
        if args.format == "flat" and args.root is None:
            parser.error("flat export requires --root; no root is inferred.")
        if args.format != "flat" and args.root is not None:
            parser.error("--root is supported only for flat export.")

    status = ExitStatus.SUCCESS
    try:
        if args.operation == "operations":
            report = _report("operations", "available", operations={
                "profiles": "offline validation for Vision/CC source and CC destination",
                "backup-vision": "explicit live read-only Vision 5.4.9 inventory discovery or targeted reads; completeness unverified",
                "destination-discovery": "explicit CC Organization root/Site read; product version unknown, compatibility unverified; no writes",
                "single-site-dry-run": "explicit authenticated read-only preflight of one hash-bound Site candidate; sanitized preview; no configuration writes",
                "single-site-create": "experimental one-Site create/readback; separate interactive authorization, no retries or bulk; target compatibility unverified",
                "site-batch-dry-run": "authenticated full hierarchical Site preflight; no configuration writes",
                "site-batch-execute": "experimental ordered Site migration; one explicit batch authorization, durable journal, no write retries",
                "site-batch-resume": "fresh identity/parent reconciliation before continuing the same hash-bound Site batch",
                "site-batch-reconcile": "read-only reconciliation of attempted Sites; preserves POST history and never creates pending Sites",
                "device-batch-dry-run": "full Organization Device inventory and fresh read-only collision/parent checks; create contract blocked",
                "device-batch-execute": "guarded Device stage; no writes while inventory-only create contract remains unqualified",
                "device-batch-resume": "fresh read-only Device reconciliation using protected journal; no writes while contract blocked",
                "migration-dry-run": "combined Sites preflight and Device inventory/parent/collision preview; no writes",
                "migration-status": "fresh read-only Site journal verification and Device status; no writes",
                "export": "CC 0.0-test supplied source inventory to local artifact",
                **{operation: "CC 0.0-test request preview / supplied single-response inspection; not a complete export" for operation in _LOOKUPS},
                "compare": "CC-to-CC offline comparison and candidate actions",
                "plan": "CC-to-CC offline planning",
                "import-preview": "same offline plan; not a legacy dry-run or write authorization",
                "tree-readiness-preview": "offline inspection of real Vision tree backup envelopes; no import plan",
                "site-comparison": "offline Vision Organization Sites versus saved CC Site snapshot; proposed/confirmed root association, no executable plan",
                "authenticate": "unavailable: shared authentication exists but is not wired to live execution",
                "import": "unavailable: offline planning never enables imports; controlled Site migration uses separate explicit operations",
                "vision-to-cc": _VISION_LIMITATION,
                **_DOMAIN_LIMITATIONS,
            })
        elif live_backup:
            from .vision_backup import run_vision_backup

            report, status = run_vision_backup(args.backup_profile, args.credentials_file)
        elif site_operation:
            from .single_site import SiteBlocked, run_single_site
            from .tls_policy import TLSPolicyError

            try:
                if device_batch:
                    from .device_migration import run_device_migration

                    report, status = run_device_migration(
                        args.discovery_profile, args.credentials_file, args.input, args.comparison,
                        args.destination_snapshot, mode=(
                            "preview" if args.operation == "migration-dry-run" else
                            "status" if args.operation == "migration-status" else
                            args.operation.removeprefix("device-batch-")
                        ), target_version=args.target_version, terminal=args.report_format != "json",
                    )
                elif site_batch:
                    from .site_migration import run_site_migration

                    report, status = run_site_migration(
                        args.discovery_profile, args.credentials_file, args.input, args.comparison,
                        args.destination_snapshot, mode=args.operation.removeprefix("site-batch-"),
                        target_version=args.target_version,
                        operation_delay=1 if args.operation_delay is None else args.operation_delay,
                        readback_interval=1 if args.readback_interval is None else args.readback_interval,
                        readback_attempts=3 if args.readback_attempts is None else args.readback_attempts,
                        terminal=args.report_format != "json",
                    )
                else:
                    report, status = run_single_site(
                        args.discovery_profile, args.credentials_file, args.input, args.comparison,
                        args.destination_snapshot, args.site_reference,
                        execute=args.operation == "single-site-create", target_version=args.target_version,
                    )
            except (SiteBlocked, TLSPolicyError) as error:
                code = error.code if isinstance(error, SiteBlocked) else "tls_execution_approval_required"
                report = _report(
                    "device-batch-migration" if device_batch else "site-batch-migration" if site_batch else "single-site-migration",
                    "error", issue_codes=[code], migration_ready=False,
                    create_attempts=0, source_reference=None, configuration_writes_authorized=False,
                    **({"counts": {"total": 0}} if migration_batch else {}),
                )
                status = ExitStatus.VALIDATION_FAILED
        elif destination_discovery:
            from .destination_discovery import run_destination_discovery

            report, status = run_destination_discovery(
                args.discovery_profile, args.credentials_file, qualify_default_root=args.qualify_default_root,
            )
        elif site_comparison:
            from .site_comparison import compare_sites

            inputs = OfflineInputs(Path.cwd())
            report = compare_sites(
                inputs.read(args.input, "source-organization-tree", base=Path.cwd()),
                inputs.read(args.destination_snapshot, "destination-organization-sites", base=Path.cwd()),
                source_root_name=args.source_root_name, destination_root_name=args.destination_root_name,
                confirm_root_mapping=args.confirm_root_mapping, destination_gui_version=args.destination_gui_version,
            )
            report["input_bindings"] = inputs.bindings
            status = ExitStatus.VALIDATION_FAILED
            if args.output is not None:
                _write_export(args.output, json.dumps(report, allow_nan=False, indent=2))
        elif tree_preview:
            from .vision_tree_preview import inspect_legacy_tree_compatibility, inspect_site_migration_readiness, inspect_vision_tree

            inputs = OfflineInputs(Path.cwd())
            inspect = (
                inspect_site_migration_readiness if args.site_readiness else
                inspect_legacy_tree_compatibility if args.legacy_compatibility else inspect_vision_tree
            )
            report = inspect(inputs.read(args.input, None, base=Path.cwd()))
            status = ExitStatus.VALIDATION_FAILED
            if args.output is not None:
                _write_export(args.output, json.dumps(report, allow_nan=False, indent=2))
        elif args.operation in ("authenticate", "import"):
            report, status = _unavailable(
                args.operation, "live_execution_disabled",
                "Live execution is not wired. Import requires separate controller-execution authorization and explicit action approval.",
            )
        elif args.module in _DOMAIN_LIMITATIONS and args.operation != "profiles":
            report, status = _unavailable(args.operation, "unresolved_contract", _DOMAIN_LIMITATIONS[args.module])
        else:
            inputs = OfflineInputs(args.request if args.request is not None else Path.cwd())
            manifest = inputs.manifest() if args.request is not None else None
            if lookup or standalone_export:
                source = _profile(inputs, None, "source", args.source_profile, args.source_product)
                assert isinstance(source, SourceProfile)
            else:
                source, destination = _profiles(
                    inputs, manifest, args.source_profile, args.destination_profile, args.source_product,
                )
            if args.operation == "profiles":
                report = _report("profiles", "valid", profiles=[
                    {
                        "role": profile.role, "product": profile.product, "version": profile.version,
                        "credential_reference_configured": profile.secret_ref is not None,
                    }
                    for profile in (source, destination)
                ], authenticated=False, note="Profile syntax only; connectivity and compatibility are not tested.")
            elif source.product == "vision":
                report, status = _unavailable(args.operation, "vision_controller_contract_unavailable", _VISION_LIMITATION)
            elif (lookup or standalone_export) and source.version != "0.0-test":
                report, status = _unavailable(
                    args.operation, "unsupported_controller_version",
                    "Only synthetic 0.0-test controller reads are enabled; real-version capabilities remain default-deny.",
                )
            elif lookup:
                report = _lookup(
                    inputs, source, args.operation, args.lookup_value, args.input, args.exported_at, args.output,
                )
            elif standalone_export:
                report, status = _export_input(inputs, source, args)
            elif args.operation == "export":
                assert manifest is not None
                inventory = inputs.side(manifest["source"], "source")
                artifact = inventory.to_artifact()
                _write_export(args.output, artifact.to_json())
                report = _report(
                    "export", "exported", object_count=len(artifact.objects),
                    note="Local source adaptation only; not a controller fetch. Completeness and credential portability remain unverified.",
                )
            else:
                assert args.request is not None
                result = plan_offline_request(args.request)
                report = {
                    **result.report, "operation": args.operation, "offline_only": True,
                    "tls_verification_required": True,
                    "import_execution_available": False, "approval_required_before_changes": True,
                }
                status = result.exit_status
    except ProductClientError as error:
        status = ExitStatus.CONTRACT_ERROR
        report = _report(args.operation, "error", errors=[{"code": error.category.value}])
    except ContractValidationError as error:
        codes = sorted({issue.code for issue in error.result.issues})
        status = ExitStatus.INPUT_ERROR if set(codes) & {
            "input_unreadable", "invalid_encoding", "invalid_json", "nonlocal_input",
            "output_exists", "output_unwritable", "output_cleanup_failed",
        } else ExitStatus.CONTRACT_ERROR
        report = _report(args.operation, "error", errors=[{"code": code} for code in codes])
    if migration_batch:
        report.setdefault("configuration_writes_authorized", False)
        report.setdefault("execution_authorized", False)
        report.setdefault("read_only", True)
        batch_operation = "device-batch-migration" if device_batch else "site-batch-migration"
        batch_mode = (
            "preview" if args.operation == "migration-dry-run" else "status" if args.operation == "migration-status"
            else args.operation.removeprefix("device-batch-" if device_batch else "site-batch-")
        )
        if args.report_format == "json":
            result = {key: report[key] for key in (
                "operation", "status", "mode", "target_origin", "counts", "authenticated", "read_only",
                "migration_ready", "execution_authorized", "configuration_writes_authorized", "tls",
                "issue_codes", "manual_reconciliation_required", "report_file", "sites", "unsupported_configuration_fields",
            ) if key in report}
            result.update(
                operation=batch_operation, mode=batch_mode,
                migration_ready=False, counts=report.get("counts", {"total": 0}),
                issue_codes=report.get("issue_codes", [row["code"] for row in report.get("errors", [])]),
            )
            print(json.dumps(result, allow_nan=False))
        elif "report_file" not in report:
            from .launcher_helper import summary

            summary({
                **report, "operation": batch_operation, "mode": batch_mode,
                "counts": report.get("counts", {"total": 0}), "migration_ready": False,
                "issue_codes": report.get("issue_codes", [row["code"] for row in report.get("errors", [])]),
            }, "2", int(status), "", "")
    elif site_comparison and args.report_format != "json":
        from .site_comparison import format_site_comparison

        print(format_site_comparison(report))
    elif tree_preview and args.report_format != "json":
        from .vision_tree_preview import format_tree_preview

        print(format_tree_preview(report))
    else:
        print(json.dumps(report, allow_nan=False))
    return int(status)
