"""Explicit Vision 5.4.9 discovery/read collection; never a migration execution path."""

import json
import os
import stat
import ssl
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from ipaddress import ip_address
from pathlib import Path
from uuid import uuid4

from ._contract_validation import ContractReader
from ._json import load_json
from .authentication import (
    AuthenticationError, AuthenticationRequest, CredentialReference,
    DocumentedVisionAuthenticationStrategy, ResolvedCredentials, SessionRole,
)
from .capabilities import LookupCapability, ProductClientError
from .backup_policy import TLS_WARNING, BackupPolicyError, UNSUPPORTED_DOMAINS, backup_domains
from .contracts import ContractValidationError, ExitStatus
from .http_backend import DestinationAuthorization, StdlibHttpBackend
from .offline_inputs import OfflineInputs, local_path, write_local_export
from .product_clients import (
    VisionBackupClient, vision_backup_segments, vision_ldap_segments, vision_scheduler_segments, vision_tree_segments,
)
from .profiles import SourceProfile
from .sessions import SessionManager
from .transport import HttpMethod, TransportConfig, TransportError, _unverified_tls_context, build_url


_reader = ContractReader("vision-backup")
_SCOPE = {
    "requested_targets_only": True, "complete_inventory": False,
    "complete_configuration_backup": False, "migration_input": False,
}
_TREE_DOMAINS = ("physical-tree", "organization-tree")


@dataclass(frozen=True, kw_only=True)
class _UnverifiedVisionBackupTransportConfig(TransportConfig):
    def _validate_tls(self) -> None:
        if self.verify_tls is not False:
            _reader.fail("unsafe_tls", "$.tls", "Unverified backup TLS requires explicit verify=false.")
        if self.trusted_ca is not None:
            _reader.fail("invalid_ca", "$.tls", "Custom CA trust cannot be combined with verify=false.")

    def tls_context(self) -> ssl.SSLContext:
        return _unverified_tls_context()

    @property
    def unverified_vision_backup(self) -> bool:
        return True


@dataclass(frozen=True)
class VisionBackupProfile:
    source: SourceProfile
    transport: TransportConfig
    domains: tuple[str, ...]
    targets: tuple[tuple[LookupCapability, str], ...]
    output_directory: Path
    discovery: bool = False

    @classmethod
    def read(cls, path_value: str) -> "VisionBackupProfile":
        path = local_path(path_value, Path.cwd()).absolute()
        data = _reader.mapping(
            OfflineInputs(path).read(str(path), None), "$",
            {"source", "tls", "domains", "backup_mode", "controller_objects", "output_directory"},
        )
        source = SourceProfile.from_dict(_reader.required(data, "source", "$"))
        if source.product != "vision" or source.version != "5.4.9":
            _reader.fail("unsupported_backup_source", "$.source", "Live backup supports Vision 5.4.9 only.")
        if source.secret_ref is not None:
            _reader.fail("unexpected_credential_reference", "$.source", "Supply credentials through --credentials-file only.")
        tls = _reader.mapping(data.get("tls", {}), "$.tls", {"verify", "trusted_ca"})
        verify = tls.get("verify", True)
        if type(verify) is not bool:
            _reader.fail("invalid_type", "$.tls.verify", "Use true or false, not text or numbers.")
        ca = tls.get("trusted_ca")
        trusted_ca = None if ca is None else str(local_path(_reader.text(ca, "$.tls.trusted_ca"), path.parent))
        options = dict(
            base_url=source.base_url.rstrip("/"), trusted_ca=trusted_ca,
            connect_timeout=10, read_timeout=30, operation_timeout=60, read_retries=0,
        )
        transport = (
            TransportConfig(**options) if verify
            else _UnverifiedVisionBackupTransportConfig(**options, verify_tls=False)
        )
        try:
            domains = backup_domains(data)
        except BackupPolicyError as error:
            _reader.fail(error.code, "$.domains", str(error))
        selection = _reader.mapping(
            data.get("controller_objects", {"discovery": True}), "$.controller_objects",
            {"discovery", "site_names", "site_ids", "device_ips"},
        )
        discovery = selection.get("discovery", False)
        if type(discovery) is not bool:
            _reader.fail("invalid_type", "$.controller_objects.discovery", "Discovery selection must be boolean.")
        targets: list[tuple[LookupCapability, str]] = []
        for key, operation in (
            ("site_names", LookupCapability.SITE_BY_NAME),
            ("site_ids", LookupCapability.SITE_BY_ID),
            ("device_ips", LookupCapability.DEVICE_BY_IP),
        ):
            values = selection.get(key, [])
            if not isinstance(values, list):
                _reader.fail("invalid_type", "$.controller_objects", "Target selections must be arrays.")
            for item in values:
                value = _reader.text(item, "$.controller_objects")
                if operation == LookupCapability.DEVICE_BY_IP:
                    try:
                        value = str(ip_address(value))
                    except ValueError:
                        _reader.fail("invalid_device_ip", "$.controller_objects", "Device targets must be IP addresses.")
                build_url(transport.base_url, vision_backup_segments(operation, value))
                targets.append((operation, value))
        if len(targets) > 100 or len(targets) != len(set(targets)):
            _reader.fail("invalid_target_selection", "$.controller_objects", "Use at most 100 unique operation/target pairs.")
        if discovery and targets:
            _reader.fail("invalid_target_selection", "$.controller_objects", "Discovery and targeted lookup lists are separate modes.")
        controller_selected = any(domain in ("controller-objects", "device-access") for domain in domains)
        if not controller_selected:
            targets = []
            discovery = False
        if controller_selected and not targets and not discovery:
            _reader.fail("empty_selection", "$.controller_objects", "Controller object collection needs explicit targets.")
        if "device-access" in domains and not discovery and not any(
            operation == LookupCapability.DEVICE_BY_IP for operation, _ in targets
        ):
            _reader.fail("empty_selection", "$.controller_objects", "Device-access collection requires discovery or device IP targets.")
        output = local_path(
            _reader.text(_reader.required(data, "output_directory", "$"), "$.output_directory"), path.parent,
        )
        return cls(source, transport, domains, tuple(targets), output, discovery)


class _FileCredentials:
    def __init__(self, path_value: str) -> None:
        self.path = local_path(path_value, Path.cwd())

    def resolve(self, reference: CredentialReference) -> ResolvedCredentials:
        if reference.value != "vision-backup":
            _reader.fail("invalid_reference", "$", "Credentials are bound to this backup source only.")
        try:
            info = self.path.stat()
        except OSError:
            _reader.fail("credentials_unreadable", "$", "Cannot inspect the supplied local credentials file.")
        if not stat.S_ISREG(info.st_mode) or os.name == "posix" and info.st_mode & 0o077:
            _reader.fail("unsafe_credentials_file", "$", "Use a regular credentials file readable only by its owner.")
        try:
            with self.path.open("rb") as stream:
                info = os.fstat(stream.fileno())
                if not stat.S_ISREG(info.st_mode) or os.name == "posix" and info.st_mode & 0o077:
                    _reader.fail("unsafe_credentials_file", "$", "Credentials permissions changed before reading.")
                raw = stream.read(16385)
        except OSError:
            _reader.fail("credentials_unreadable", "$", "Cannot read the supplied local credentials file.")
        if len(raw) > 16384:
            _reader.fail("invalid_credentials_file", "$", "Credentials file exceeds the local size limit.")
        try:
            payload = load_json(raw.decode("utf-8"))
        except (ValueError, UnicodeError, RecursionError):
            _reader.fail("invalid_credentials_file", "$", "Credentials file must contain strict UTF-8 JSON.")
        data = _reader.mapping(payload, "$", {"username", "password"})
        username = _reader.required(data, "username", "$")
        password = _reader.required(data, "password", "$")
        if not isinstance(username, str) or not isinstance(password, str):
            _reader.fail("invalid_credentials_file", "$", "Credential values must be strings.")
        return ResolvedCredentials(
            username, password,
        )


def _failure(error: AuthenticationError | TransportError | ProductClientError | ContractValidationError) -> list[str]:
    if isinstance(error, AuthenticationError):
        failure = error.failure
        return [failure.category.value, *(
            [failure.transport_reason.value] if failure.transport_reason is not None else []
        )]
    if isinstance(error, ContractValidationError):
        return sorted({issue.code for issue in error.result.issues})
    return [error.category.value]


def _backend(profile: VisionBackupProfile) -> StdlibHttpBackend:
    operations = [(HttpMethod.POST, "/mgmt/system/user/login")]
    if profile.discovery:
        operations.append((HttpMethod.GET, "/mgmt/system/config/itemlist/alldevices"))
    if "ldap-permissions" in profile.domains:
        operations.append((HttpMethod.GET, "/" + "/".join(vision_ldap_segments())))
    if "scheduler" in profile.domains:
        operations.append((HttpMethod.GET, "/" + "/".join(vision_scheduler_segments())))
    operations.extend(
        (HttpMethod.GET, "/" + "/".join(vision_tree_segments(domain)))
        for domain in _TREE_DOMAINS if domain in profile.domains
    )
    operations.extend(
        (HttpMethod.GET, build_url(profile.transport.base_url, vision_backup_segments(operation, value))[
            len(profile.transport.base_url):
        ])
        for operation, value in profile.targets
    )
    try:
        authorization = DestinationAuthorization(profile.transport.base_url, tuple(operations))
    except ValueError:
        _reader.fail("invalid_target_authorization", "$", "A target is outside the exact supported read scope.")
    return StdlibHttpBackend(
        allow_live=True, authorization=authorization, max_response_bytes=16 * 1024 * 1024,
        allow_unverified_vision_backup=profile.transport.unverified_vision_backup,
        diagnose_failures=True,
    )


def run_vision_backup(
    profile_path: str, credentials_path: str,
) -> tuple[dict[str, object], ExitStatus]:
    profile = VisionBackupProfile.read(profile_path)
    if not profile.transport.verify_tls:
        print(TLS_WARNING, file=sys.stderr)
    resolver = _FileCredentials(credentials_path)
    if not profile.output_directory.is_dir():
        _reader.fail("output_unwritable", "$", "Output directory must already exist on the external mount.")
    run_id = "vision-backup-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ-") + uuid4().hex[:12]
    directory = profile.output_directory / run_id
    try:
        directory.mkdir(mode=0o700)
    except OSError:
        _reader.fail("output_unwritable", "$", "Cannot create a private run directory on the output mount.")
    results: list[dict[str, object]] = []
    failures: list[str] = []
    skipped: list[dict[str, object]] = []
    authenticated = False
    strategy = DocumentedVisionAuthenticationStrategy()
    targets = list(profile.targets)
    inventory: dict[str, object] = {"status": "not_requested", "object_count": 0}
    scope = {**_SCOPE, "requested_targets_only": not profile.discovery}
    module_failures: set[str] = set()
    access_count = 0
    ldap: dict[str, object] = {"status": "not_requested", "record_count": 0}
    ldap_failures: list[str] = []
    if "ldap-permissions" in profile.domains:
        ldap["status"] = "skipped"
        ldap["issue_codes"] = ["session_unavailable"]
    trees: dict[str, dict[str, object]] = {
        domain: {
            "status": "skipped" if domain in profile.domains else "not_requested",
            "record_count": 0, "record_count_basis": "top_level_json_records",
            "schema_completeness_verified": False, "enumeration_completeness_verified": False,
            "issue_codes": ["session_unavailable"] if domain in profile.domains else [],
        } for domain in _TREE_DOMAINS
    }
    tree_failures: list[str] = []
    scheduler: dict[str, object] = {
        "status": "skipped" if "scheduler" in profile.domains else "not_requested",
        "record_count": 0, "schema_completeness_verified": False,
        "enumeration_completeness_verified": False,
        "issue_codes": ["session_unavailable"] if "scheduler" in profile.domains else [],
    }
    scheduler_failures: list[str] = []
    module_directories = {domain: directory / domain for domain in profile.domains}
    try:
        for folder in module_directories.values():
            folder.mkdir(mode=0o700)
    except OSError:
        _reader.fail("output_unwritable", "$", "Cannot create selected module output directories.")
    try:
        if profile.domains:
            backend = _backend(profile)
            with SessionManager(lambda: backend, resolver) as manager:
                manager.initialize(
                    AuthenticationRequest(
                        SessionRole.SOURCE, "vision", "5.4.9", CredentialReference("vision-backup"),
                    ), profile.transport, strategy=strategy,
                )
                manager.authenticate(SessionRole.SOURCE)
                authenticated = True
                client = VisionBackupClient(manager)
                if profile.discovery:
                    inventory["status"] = "failed"
                    try:
                        collected_at = datetime.now(timezone.utc).isoformat()
                        discovered = client.discover(collected_at=collected_at)
                        if "controller-objects" in module_directories:
                            inventory_filename = str(Path("controller-objects") / "inventory.json")
                            write_local_export(str(directory / inventory_filename), json.dumps({
                                "schema_version": 1, "domain": "vision-managed-device-inventory",
                                "source": {"product": "vision", "version": "5.4.9", "name": profile.source.name},
                                "collected_at": collected_at,
                                "request": {"method": "GET", "path": "/mgmt/system/config/itemlist/alldevices"},
                                "scope": scope, "objects": list(discovered.objects),
                                "redacted_fields": discovered.redacted_fields,
                                "issue_codes": list(discovered.issue_codes),
                                "evidence": {"document": "DOC-V549", "pdf_pages": list(discovered.evidence.pdf_pages)},
                            }, indent=2, allow_nan=False))
                            inventory["file"] = inventory_filename
                        inventory.update(
                            status="collected", object_count=discovered.object_count,
                            issue_codes=list(discovered.issue_codes),
                        )
                        if "invalid_discovered_ip" in discovered.issue_codes:
                            failures.append("invalid_discovered_ip")
                        targets = [(LookupCapability.DEVICE_BY_IP, address) for address in discovered.device_ips]
                        backend.authorize_get_targets(tuple(
                            build_url(profile.transport.base_url, vision_backup_segments(operation, value))[
                                len(profile.transport.base_url):
                            ] for operation, value in targets
                        ))
                    except (AuthenticationError, TransportError, ProductClientError, ContractValidationError) as error:
                        failures.extend(_failure(error))
                        targets = []
                for index, (operation, value) in enumerate(targets, 1):
                    entry: dict[str, object] = {"index": index, "operation": operation.value}
                    if not manager.is_authenticated(SessionRole.SOURCE):
                        entry.update(status="skipped", issue_codes=["session_unavailable"])
                        module_failures.update(
                            domain for domain in profile.domains if domain in ("controller-objects", "device-access")
                        )
                        results.append(entry)
                        continue
                    try:
                        timestamp = datetime.now(timezone.utc).isoformat()
                        result = client.read(operation, value, collected_at=timestamp)
                        filename = f"{operation.value}-{index:03}.json"
                        payload = {
                            "schema_version": 1, "domain": "vision-controller-object-lookup",
                            "source": {"product": "vision", "version": "5.4.9", "name": profile.source.name},
                            "collected_at": timestamp, "scope": scope,
                            "request": {"method": "GET", "path_template": result.evidence.path, "target": value},
                            "evidence": {
                                "document": "DOC-V549", "pdf_pages": list(result.evidence.pdf_pages),
                                "live_compatibility_verified": False,
                            },
                            "objects": list(result.objects), "redacted_fields": result.redacted_fields,
                            "issue_codes": list(result.issue_codes),
                        }
                        if operation == LookupCapability.DEVICE_BY_IP:
                            payload["identity_binding"] = "queried_management_ip_and_unique_response_id"
                        written: list[str] = []
                        if "controller-objects" in profile.domains:
                            object_filename = str(Path("controller-objects") / filename)
                            write_local_export(str(directory / object_filename), json.dumps(payload, indent=2, allow_nan=False))
                            written.append(object_filename)
                        if "device-access" in profile.domains and operation == LookupCapability.DEVICE_BY_IP:
                            setup = result.objects[0].get("deviceSetup")
                            access = setup.get("deviceAccess") if isinstance(setup, dict) else None
                            if not isinstance(access, dict):
                                module_failures.add("device-access")
                                entry["device_access_issue_codes"] = ["device_access_unavailable"]
                            else:
                                access_filename = str(Path("device-access") / filename)
                                access_payload = {
                                    **payload, "domain": "vision-device-access",
                                    "objects": [{"ormID": result.objects[0]["ormID"], "deviceAccess": access}],
                                }
                                write_local_export(
                                    str(directory / access_filename), json.dumps(access_payload, indent=2, allow_nan=False),
                                )
                                written.append(access_filename)
                                access_count += 1
                        entry.update(
                            status="collected", files=written, object_count=len(result.objects),
                            redacted_fields=result.redacted_fields, issue_codes=list(result.issue_codes),
                        )
                    except (AuthenticationError, TransportError, ProductClientError, ContractValidationError) as error:
                        entry.update(status="failed", issue_codes=_failure(error))
                        module_failures.update(
                            domain for domain in profile.domains if domain in ("controller-objects", "device-access")
                        )
                    results.append(entry)
                if "ldap-permissions" in profile.domains:
                    if not manager.is_authenticated(SessionRole.SOURCE):
                        module_failures.add("ldap-permissions")
                    else:
                        try:
                            collected_at = datetime.now(timezone.utc).isoformat()
                            permissions = client.list_ldap_permissions(collected_at=collected_at)
                            filename = str(Path("ldap-permissions") / "permissions.json")
                            write_local_export(str(directory / filename), json.dumps({
                                "schema_version": 1, "domain": "vision-ldap-permissions",
                                "source": {"product": "vision", "version": "5.4.9", "name": profile.source.name},
                                "collected_at": collected_at,
                                "request": {"method": "GET", "path": permissions.evidence.path},
                                "scope": {
                                    "complete_configuration_backup": False,
                                    "schema_completeness_verified": False,
                                    "enumeration_completeness_verified": False,
                                    "migration_input": False,
                                },
                                "evidence": {
                                    "api_record": "API-10", "request_verification": "legacy-source-observed",
                                    "response_contract": "legacy-array-object-subset",
                                    "officially_documented": False, "live_tested": False,
                                },
                                "objects": list(permissions.objects),
                                "redacted_fields": permissions.redacted_fields,
                                "issue_codes": list(permissions.issue_codes),
                            }, indent=2, allow_nan=False))
                            ldap.update(
                                status="collected", record_count=len(permissions.objects), file=filename,
                                redacted_fields=permissions.redacted_fields, issue_codes=list(permissions.issue_codes),
                            )
                        except (AuthenticationError, TransportError, ProductClientError, ContractValidationError) as error:
                            ldap_failures = _failure(error)
                            ldap.update(status="failed", issue_codes=ldap_failures)
                            module_failures.add("ldap-permissions")
                for domain in _TREE_DOMAINS:
                    if domain not in profile.domains:
                        continue
                    if not manager.is_authenticated(SessionRole.SOURCE):
                        module_failures.add(domain)
                        continue
                    try:
                        tree = client.read_tree(domain)
                        filename = str(Path(domain) / "tree.json")
                        write_local_export(str(directory / filename), json.dumps({
                            "schema_version": 1, "domain": "vision-" + domain,
                            "source": {"product": "vision", "version": "5.4.9", "name": profile.source.name},
                            "collected_at": datetime.now(timezone.utc).isoformat(),
                            "request": {"method": "GET", "path": "/" + "/".join(vision_tree_segments(domain))},
                            "scope": {
                                "complete_configuration_backup": False,
                                "schema_completeness_verified": False,
                                "enumeration_completeness_verified": False, "migration_input": False,
                            },
                            "evidence": {
                                "request_verification": "owner-reported-vision-5.4.9-live-get",
                                "officially_documented": False, "operator_live_read_verified": True,
                                "master_live_tested": False, "response_contract": "opaque-json-container",
                            },
                            "tree": tree.tree, "record_count": tree.record_count,
                            "record_count_basis": "top_level_json_records",
                            "redacted_fields": tree.redacted_fields, "issue_codes": list(tree.issue_codes),
                        }, indent=2, allow_nan=False))
                        trees[domain].update(
                            status="collected", record_count=tree.record_count, file=filename,
                            redacted_fields=tree.redacted_fields, issue_codes=list(tree.issue_codes),
                        )
                    except (AuthenticationError, TransportError, ProductClientError, ContractValidationError) as error:
                        codes = _failure(error)
                        tree_failures.extend(codes)
                        trees[domain].update(status="failed", issue_codes=codes)
                        module_failures.add(domain)
                if "scheduler" in profile.domains:
                    if not manager.is_authenticated(SessionRole.SOURCE):
                        module_failures.add("scheduler")
                    else:
                        try:
                            collected_at = datetime.now(timezone.utc).isoformat()
                            tasks = client.list_scheduler_tasks(collected_at=collected_at)
                            filename = str(Path("scheduler") / "tasks.json")
                            write_local_export(str(directory / filename), json.dumps({
                                "schema_version": 1, "domain": "vision-scheduler",
                                "source": {"product": "vision", "version": "5.4.9", "name": profile.source.name},
                                "collected_at": collected_at,
                                "request": {"method": "GET", "path": "/" + "/".join(vision_scheduler_segments())},
                                "scope": {
                                    "complete_configuration_backup": False,
                                    "schema_completeness_verified": False,
                                    "enumeration_completeness_verified": False, "migration_input": False,
                                },
                                "evidence": {
                                    "request_verification": "legacy-source-and-ini-observed",
                                    "source_config_key": "API.scheduler_endpoint",
                                    "response_contract": "legacy-array-object-subset",
                                    "vendor_contract_verified": False, "master_live_tested": False,
                                },
                                "tasks": list(tasks.tasks), "record_count": len(tasks.tasks),
                                "redacted_fields": tasks.redacted_fields, "issue_codes": list(tasks.issue_codes),
                            }, indent=2, allow_nan=False))
                            scheduler.update(
                                status="collected", record_count=len(tasks.tasks), file=filename,
                                redacted_fields=tasks.redacted_fields, issue_codes=list(tasks.issue_codes),
                            )
                        except (AuthenticationError, TransportError, ProductClientError, ContractValidationError) as error:
                            scheduler_failures = _failure(error)
                            scheduler.update(status="failed", issue_codes=scheduler_failures)
                            module_failures.add("scheduler")
    except (AuthenticationError, TransportError, ProductClientError, ContractValidationError) as error:
        if (
            isinstance(error, AuthenticationError) and error.failure.transport_reason is None
            and strategy.failure_reason is not None
        ):
            backend.report_login_failure(strategy.failure_reason)
        failures.extend(_failure(error))
    finally:
        strategy.clear()
    collected = sum(entry["status"] == "collected" for entry in results)
    failed = sum(entry["status"] == "failed" for entry in results)
    trees_collected = any(tree["status"] == "collected" for tree in trees.values())
    scheduler_collected = scheduler["status"] == "collected"
    successful = (
        collected == len(targets) and (
            bool(targets) or inventory["status"] == "collected" or ldap["status"] == "collected"
            or trees_collected or scheduler_collected
        )
        and not failures and not skipped and not module_failures
    )
    if failures:
        module_failures.update(
            domain for domain in profile.domains
            if not (
                domain == "ldap-permissions" and ldap["status"] == "collected"
                or domain in trees and trees[domain]["status"] == "collected"
                or domain == "scheduler" and scheduler_collected
            )
        )
    report: dict[str, object] = {
        "operation": "backup-vision", "status": "collected" if successful else "incomplete",
        "offline_only": False, "read_only": True, "live_read_selected": True,
        "execution_authorized": False, "configuration_writes_authorized": False,
        "tls_verification_required": profile.transport.verify_tls, "authenticated": authenticated,
        "tls": {"verify": profile.transport.verify_tls},
        "session_closed_locally": "local_cleanup_failure" not in failures,
        "scope": scope, "run_directory": run_id, "inventory": inventory,
        "overall_status": "supported_collection_succeeded" if successful else (
            "partial_collection" if collected or inventory["status"] == "collected" or ldap["status"] == "collected" or trees_collected or scheduler_collected else "failed_collection"
        ),
        "discovery_completeness": "partial-unverified" if profile.discovery else "targeted-only",
        "requested_targets": len(targets), "collected_objects": inventory["object_count"] if profile.discovery else collected,
        "device_details_collected": sum(
            entry["status"] == "collected" and entry["operation"] == LookupCapability.DEVICE_BY_IP.value
            for entry in results
        ),
        "device_access_objects": access_count,
        "ldap_permissions": ldap,
        "ldap_permission_records": ldap["record_count"],
        "trees": trees,
        "scheduler": scheduler,
        "requested_modules": list(profile.domains),
        "completed_modules": [domain for domain in profile.domains if domain not in module_failures],
        "failed_modules": sorted(module_failures),
        "unsupported_modules": UNSUPPORTED_DOMAINS,
        "failed_targets": failed, "uncollected_targets": len(targets) - collected,
        "skipped_domains": skipped, "results": results,
        "failure_codes": [*failures, *ldap_failures, *tree_failures, *scheduler_failures],
        "limitations": [
            "inventory_completeness_unverified" if profile.discovery else "targeted_reads_not_inventory_discovery",
            "empty_sites_and_other_trees_not_proven_complete", "credential_fields_redacted",
            "live_compatibility_unverified", "no_remote_logout",
            "dns_and_whole_run_not_hard_deadline_bounded",
        ],
    }
    write_local_export(str(directory / "summary.json"), json.dumps(report, indent=2, allow_nan=False))
    return report, ExitStatus.SUCCESS if successful else ExitStatus.VALIDATION_FAILED
