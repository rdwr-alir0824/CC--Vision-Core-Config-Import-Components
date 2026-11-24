"""Explicit, targeted Vision 5.4.9 collection; never a migration execution path."""

import json
import os
import stat
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
from .contracts import ContractValidationError, ExitStatus
from .http_backend import DestinationAuthorization, StdlibHttpBackend
from .offline_inputs import OfflineInputs, local_path, write_local_export
from .product_clients import VisionBackupClient, vision_backup_segments
from .profiles import SourceProfile
from .sessions import SessionManager
from .transport import HttpMethod, TransportConfig, TransportError, build_url


_reader = ContractReader("vision-backup")
_SCOPE = {
    "requested_targets_only": True, "complete_inventory": False,
    "complete_configuration_backup": False, "migration_input": False,
}


@dataclass(frozen=True)
class VisionBackupProfile:
    source: SourceProfile
    transport: TransportConfig
    domains: tuple[str, ...]
    targets: tuple[tuple[LookupCapability, str], ...]
    output_directory: Path

    @classmethod
    def read(cls, path_value: str) -> "VisionBackupProfile":
        path = local_path(path_value, Path.cwd()).absolute()
        data = _reader.mapping(
            OfflineInputs(path).read(str(path), None), "$",
            {"source", "tls", "domains", "controller_objects", "output_directory"},
        )
        source = SourceProfile.from_dict(_reader.required(data, "source", "$"))
        if source.product != "vision" or source.version != "5.4.9":
            _reader.fail("unsupported_backup_source", "$.source", "Live backup supports Vision 5.4.9 only.")
        if source.secret_ref is not None:
            _reader.fail("unexpected_credential_reference", "$.source", "Supply credentials through --credentials-file only.")
        tls = _reader.mapping(_reader.required(data, "tls", "$"), "$.tls", {"verify", "trusted_ca"})
        if _reader.required(tls, "verify", "$.tls") is not True:
            _reader.fail("unsafe_tls", "$.tls.verify", "TLS verification must remain enabled.")
        ca = tls.get("trusted_ca")
        trusted_ca = None if ca is None else str(local_path(_reader.text(ca, "$.tls.trusted_ca"), path.parent))
        transport = TransportConfig(
            base_url=source.base_url.rstrip("/"), trusted_ca=trusted_ca,
            connect_timeout=10, read_timeout=30, operation_timeout=60, read_retries=0,
        )
        domains = _reader.references(_reader.required(data, "domains", "$"), "$.domains")
        if not domains:
            _reader.fail("empty_selection", "$.domains", "Select at least one backup domain.")
        selection = _reader.mapping(
            _reader.required(data, "controller_objects", "$"), "$.controller_objects",
            {"site_names", "site_ids", "device_ips"},
        )
        targets: list[tuple[LookupCapability, str]] = []
        for key, operation in (
            ("site_names", LookupCapability.SITE_BY_NAME),
            ("site_ids", LookupCapability.SITE_BY_ID),
            ("device_ips", LookupCapability.DEVICE_BY_IP),
        ):
            values = _reader.required(selection, key, "$.controller_objects")
            if not isinstance(values, list):
                _reader.fail("invalid_type", "$.controller_objects", "Target selections must be arrays.")
            for item in values:
                value = _reader.text(item, "$.controller_objects")
                if operation == LookupCapability.DEVICE_BY_IP:
                    try:
                        ip_address(value)
                    except ValueError:
                        _reader.fail("invalid_device_ip", "$.controller_objects", "Device targets must be IP addresses.")
                build_url(transport.base_url, vision_backup_segments(operation, value))
                targets.append((operation, value))
        if len(targets) > 100 or len(targets) != len(set(targets)):
            _reader.fail("invalid_target_selection", "$.controller_objects", "Use at most 100 unique operation/target pairs.")
        if "controller-objects" in domains and not targets:
            _reader.fail("empty_selection", "$.controller_objects", "Controller object collection needs explicit targets.")
        if "controller-objects" not in domains and targets:
            _reader.fail("unselected_targets", "$.controller_objects", "Do not supply targets for an unselected domain.")
        output = local_path(
            _reader.text(_reader.required(data, "output_directory", "$"), "$.output_directory"), path.parent,
        )
        return cls(source, transport, domains, tuple(targets), output)


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
    operations.extend(
        (HttpMethod.GET, build_url(profile.transport.base_url, vision_backup_segments(operation, value))[
            len(profile.transport.base_url):
        ])
        for operation, value in profile.targets
    )
    return StdlibHttpBackend(
        allow_live=True, authorization=DestinationAuthorization(profile.transport.base_url, tuple(operations)),
        max_response_bytes=16 * 1024 * 1024,
    )


def run_vision_backup(profile_path: str, credentials_path: str) -> tuple[dict[str, object], ExitStatus]:
    profile = VisionBackupProfile.read(profile_path)
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
    skipped = [{"domain": domain, "reason": "unsupported_domain"} for domain in profile.domains if domain != "controller-objects"]
    authenticated = False
    strategy = DocumentedVisionAuthenticationStrategy()
    try:
        if profile.targets:
            with SessionManager(lambda: _backend(profile), resolver) as manager:
                manager.initialize(
                    AuthenticationRequest(
                        SessionRole.SOURCE, "vision", "5.4.9", CredentialReference("vision-backup"),
                    ), profile.transport, strategy=strategy,
                )
                manager.authenticate(SessionRole.SOURCE)
                authenticated = True
                client = VisionBackupClient(manager)
                for index, (operation, value) in enumerate(profile.targets, 1):
                    entry: dict[str, object] = {"index": index, "operation": operation.value}
                    if not manager.is_authenticated(SessionRole.SOURCE):
                        entry.update(status="skipped", issue_codes=["session_unavailable"])
                        results.append(entry)
                        continue
                    try:
                        timestamp = datetime.now(timezone.utc).isoformat()
                        result = client.read(operation, value, collected_at=timestamp)
                        filename = f"{operation.value}-{index:03}.json"
                        payload = {
                            "schema_version": 1, "domain": "vision-controller-object-lookup",
                            "source": {"product": "vision", "version": "5.4.9", "name": profile.source.name},
                            "collected_at": timestamp, "scope": _SCOPE,
                            "request": {"method": "GET", "path_template": result.evidence.path, "target": value},
                            "evidence": {
                                "document": "DOC-V549", "pdf_pages": list(result.evidence.pdf_pages),
                                "live_compatibility_verified": False,
                            },
                            "objects": list(result.objects), "redacted_fields": result.redacted_fields,
                            "issue_codes": list(result.issue_codes),
                        }
                        write_local_export(str(directory / filename), json.dumps(payload, indent=2, allow_nan=False))
                        entry.update(
                            status="collected", file=filename, object_count=len(result.objects),
                            redacted_fields=result.redacted_fields, issue_codes=list(result.issue_codes),
                        )
                    except (AuthenticationError, TransportError, ProductClientError, ContractValidationError) as error:
                        entry.update(status="failed", issue_codes=_failure(error))
                    results.append(entry)
    except (AuthenticationError, TransportError, ProductClientError, ContractValidationError) as error:
        failures.extend(_failure(error))
    finally:
        strategy.clear()
    collected = sum(entry["status"] == "collected" for entry in results)
    failed = sum(entry["status"] == "failed" for entry in results)
    successful = collected == len(profile.targets) and bool(profile.targets) and not failures and not skipped
    report: dict[str, object] = {
        "operation": "backup-vision", "status": "collected" if successful else "incomplete",
        "offline_only": False, "read_only": True, "live_read_selected": True,
        "execution_authorized": False, "configuration_writes_authorized": False,
        "tls_verification_required": True, "authenticated": authenticated,
        "session_closed_locally": "local_cleanup_failure" not in failures,
        "scope": _SCOPE, "run_directory": run_id,
        "requested_targets": len(profile.targets), "collected_objects": collected,
        "failed_targets": failed, "uncollected_targets": len(profile.targets) - collected,
        "skipped_domains": skipped, "results": results, "failure_codes": failures,
        "limitations": [
            "targeted_reads_not_inventory_discovery", "credential_fields_redacted",
            "live_compatibility_unverified", "no_remote_logout",
            "dns_and_whole_run_not_hard_deadline_bounded",
        ],
    }
    write_local_export(str(directory / "summary.json"), json.dumps(report, indent=2, allow_nan=False))
    return report, ExitStatus.SUCCESS if successful else ExitStatus.VALIDATION_FAILED
