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
    "authenticate", "import", "backup-vision", "tree-readiness-preview", *_LOOKUPS,
)
_VISION_LIMITATION = "Vision controller export schemas and Vision-to-CC mappings are not established."
_DOMAIN_LIMITATIONS = {
    "ldap-permissions": "Vision LDAP code exists, but CC LDAP contracts and permission mappings are unresolved.",
    "scheduler": "Legacy Scheduler paths are INI-configured and unresolved; CC task contracts are absent.",
}


def _report(operation: str, status: str, **fields: object) -> dict[str, object]:
    return {
        "operation": operation, "status": status, "offline_only": operation != "backup-vision",
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
        description="Offline consolidation, or explicitly selected read-only Vision backup. Never writes controller configuration.",
    )
    parser.add_argument("--operation", choices=_OPERATIONS, required=True)
    parser.add_argument("--report-format", choices=("text", "json"), help="Tree readiness stdout format; defaults to text.")
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
    parser.add_argument("--credentials-file", help="Read-only mounted owner-private JSON credentials file; never a password argument.")
    args = parser.parse_args(argv)
    tree_preview = args.operation == "tree-readiness-preview"
    if args.report_format is not None and not tree_preview:
        parser.error("--report-format is supported only for tree-readiness-preview.")
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
    elif args.backup_profile is not None or args.credentials_file is not None:
        parser.error("backup profile/credentials options require explicit --operation backup-vision.")
    lookup = args.operation in _LOOKUPS
    standalone_export = args.operation == "export" and args.input is not None
    if args.output is not None and args.operation != "export" and not lookup and not tree_preview:
        parser.error("--output is supported only for offline export or lookup artifacts.")
    if args.operation == "export" and args.output is None:
        parser.error("offline export requires --output.")
    if args.operation in ("export", "compare", "plan", "import-preview") and args.request is None and not standalone_export:
        parser.error("this operation requires --request.")
    if args.input is not None and not (lookup or standalone_export or tree_preview):
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
                "export": "CC 0.0-test supplied source inventory to local artifact",
                **{operation: "CC 0.0-test request preview / supplied single-response inspection; not a complete export" for operation in _LOOKUPS},
                "compare": "CC-to-CC offline comparison and candidate actions",
                "plan": "CC-to-CC offline planning",
                "import-preview": "same offline plan; not a legacy dry-run or write authorization",
                "tree-readiness-preview": "offline inspection of real Vision tree backup envelopes; no import plan",
                "authenticate": "unavailable: shared authentication exists but is not wired to live execution",
                "import": "unavailable: no live writes, even after offline planning",
                "vision-to-cc": _VISION_LIMITATION,
                **_DOMAIN_LIMITATIONS,
            })
        elif live_backup:
            from .vision_backup import run_vision_backup

            report, status = run_vision_backup(args.backup_profile, args.credentials_file)
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
    if tree_preview and args.report_format != "json":
        from .vision_tree_preview import format_tree_preview

        print(format_tree_preview(report))
    else:
        print(json.dumps(report, allow_nan=False))
    return int(status)
