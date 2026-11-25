"""Explicit tree-only CC discovery; product version and compatibility are unknown."""

import json
import os
import ssl
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit
from uuid import uuid4

from ._contract_validation import ContractReader
from ._json import load_json
from .authentication import (
    AuthenticationError, AuthenticationOutcome, AuthenticationRequest,
    CredentialReference, CyberControllerAuthenticationStrategy,
    DocumentedVisionAuthenticationStrategy, LoginEvidence, ResolvedCredentials,
    SessionExpiration, SessionRole,
)
from .backup_setup import SetupError, _read_credentials
from .capabilities import ProductClientError
from .contracts import ExitStatus
from .http_backend import DestinationAuthorization, StdlibHttpBackend
from .offline_inputs import OfflineInputs, local_path, write_local_export
from .product_clients import _redact_credentials
from .sessions import SessionManager
from .tls_policy import TLSPolicy, TLSPolicyError, warning
from .transport import HttpMethod, HttpResponse, TransportConfig, TransportError, _unverified_tls_context


_reader = ContractReader("destination-discovery")
_TREE = ("mgmt", "system", "config", "tree", "Organization")
_SITE = "com.radware.insite.model.device.Site"
_DEVICE = "com.radware.insite.model.device.Device"


@dataclass(frozen=True)
class _UnknownVersionRequest(AuthenticationRequest):
    def __post_init__(self) -> None:
        # Only this discovery context accepts unknown; normal version gates stay intact.
        if (
            not isinstance(self.role, SessionRole) or self.role != SessionRole.DESTINATION
            or self.product != "cyber-controller" or self.version != "unknown"
            or not isinstance(self.credential_ref, CredentialReference)
            or not isinstance(self.expiration, SessionExpiration)
        ):
            _reader.fail("invalid_discovery_context", "$", "Unknown version is restricted to destination tree discovery.")


class _DiscoveryAuthentication(CyberControllerAuthenticationStrategy):
    def __init__(self) -> None:
        self._validation = DocumentedVisionAuthenticationStrategy()
        self._authenticated = False

    def interpret(self, response: HttpResponse) -> AuthenticationOutcome:
        self._authenticated = False
        outcome = self._validation.interpret(response)
        if outcome.failure is not None:
            return outcome
        self._authenticated = True
        return AuthenticationOutcome(True, LoginEvidence.APPLICATION_STATUS_OK)

    def request_headers(self, credentials: ResolvedCredentials | None) -> dict[str, str]:
        headers = {**super().request_headers(credentials), "Accept": "application/json"}
        if self._authenticated:
            headers["Cookie"] = self._validation.request_headers(None)["Cookie"]
        return headers

    def clear(self) -> None:
        self._authenticated = False
        self._validation.clear()


class _Credentials:
    def __init__(self, path: str) -> None:
        self.path = local_path(path, Path.cwd())

    def resolve(self, reference: CredentialReference) -> ResolvedCredentials:
        if reference.value != "cc-destination-discovery":
            _reader.fail("invalid_reference", "$", "Credentials are scoped to destination discovery.")
        try:
            data = _read_credentials(self.path)
        except (SetupError, OSError, ValueError, UnicodeError):
            _reader.fail("credentials_unreadable", "$", "Use a regular owner-private destination credentials file.")
        return ResolvedCredentials(data["username"], data["password"])


@dataclass(frozen=True, kw_only=True)
class _LabDiscoveryTransportConfig(TransportConfig):
    lab_authorized: bool
    authorized_origin: str

    def _validate_tls(self) -> None:
        try:
            TLSPolicy.from_dict({
                "verify": self.verify_tls, "lab_authorized": self.lab_authorized,
                "authorized_origin": self.authorized_origin,
            }, self.base_url)
        except TLSPolicyError:
            _reader.fail("unsafe_tls", "$.tls", "Unverified discovery requires origin-bound lab authorization.")
        if self.verify_tls is not False or self.trusted_ca is not None:
            _reader.fail("unsafe_tls", "$.tls", "Lab discovery requires verify=false without a CA override.")

    def tls_context(self) -> ssl.SSLContext:
        return _unverified_tls_context()

    @property
    def unverified_destination_discovery(self) -> bool:
        return True


@dataclass(frozen=True)
class DiscoveryProfile:
    name: str
    transport: TransportConfig
    output_directory: Path

    @classmethod
    def read(cls, value: str) -> "DiscoveryProfile":
        path = local_path(value, Path.cwd())
        data = _reader.mapping(
            OfflineInputs(path).read(str(path), None), "$",
            {"destination", "tls", "output_directory"},
        )
        destination = _reader.mapping(
            _reader.required(data, "destination", "$"), "$.destination",
            {"name", "base_url"},
        )
        name = _reader.identifier(_reader.required(destination, "name", "$"), "$.destination.name")
        origin = _reader.base_url(_reader.required(destination, "base_url", "$"), "$.destination.base_url").rstrip("/")
        if urlsplit(origin).port not in (None, 443):
            _reader.fail("unsupported_destination_port", "$", "Discovery permits HTTPS port 443 only.")
        tls = _reader.mapping(data.get("tls", {}), "$.tls", {"verify", "trusted_ca", "lab_authorized", "authorized_origin"})
        try:
            policy = TLSPolicy.from_dict({key: value for key, value in tls.items() if key != "trusted_ca"}, origin)
        except TLSPolicyError:
            _reader.fail("unsafe_tls", "$.tls", "TLS verification defaults true; false requires origin-bound lab authorization.")
        ca = tls.get("trusted_ca")
        trusted_ca = None if ca is None else str(local_path(_reader.text(ca, "$.tls.trusted_ca"), path.parent))
        options = dict(
            base_url=origin, connect_timeout=10, read_timeout=30,
            operation_timeout=60, read_retries=0, trusted_ca=trusted_ca,
        )
        transport = TransportConfig(**options) if policy.verify else _LabDiscoveryTransportConfig(
            **options, verify_tls=False, lab_authorized=policy.lab_authorized,
            authorized_origin=origin,
        )
        return cls(
            name,
            transport,
            local_path(_reader.text(_reader.required(data, "output_directory", "$"), "$.output_directory"), path.parent),
        )


def _backend(profile: DiscoveryProfile) -> StdlibHttpBackend:
    return StdlibHttpBackend(
        allow_live=True,
        authorization=DestinationAuthorization(profile.transport.base_url, (
            (HttpMethod.POST, "/mgmt/system/user/login"),
            (HttpMethod.GET, "/" + "/".join(_TREE)),
        )),
        max_response_bytes=16 * 1024 * 1024,
        allow_unverified_destination_discovery=profile.transport.unverified_destination_discovery,
    )


@dataclass
class _Node:
    reference: str
    kind: str
    identity: str | None
    name: str | None
    native: dict[str, object]
    parent: str | None
    codes: set[str]
    unprojected: int


def project_site_tree(payload: object) -> dict[str, object]:
    if (
        not isinstance(payload, dict) or not isinstance(payload.get("meIdentifier"), dict)
        or not isinstance(payload.get("children"), list) or payload.get("status") == "error"
    ):
        _reader.fail("unsupported_destination_tree_shape", "$", "Expected the legacy-observed object tree envelope.")
    try:
        native, redactions = _redact_credentials(payload)
    except ProductClientError:
        _reader.fail("discovery_redaction_failed", "$", "Tree cannot be safely processed within shared redaction limits.")
    entries: list[_Node] = []
    issues: set[str] = set()

    def text(value: object) -> str | None:
        return value if isinstance(value, str) and value.strip() and all(c.isprintable() for c in value) else None

    def visit(value: object, parent: str | None, depth: int) -> None:
        if depth > 64 or len(entries) >= 10000:
            _reader.fail("discovery_limit_exceeded", "$", "Tree exceeds the depth or node budget.")
        if not isinstance(value, dict):
            _reader.fail("invalid_destination_tree_node", "$", "Tree children must be JSON objects.")
        identifier = value.get("meIdentifier")
        identifier = identifier if isinstance(identifier, dict) else {}
        native_class = identifier.get("managedElementClass")
        kind = "root" if parent is None else "site" if native_class == _SITE else "device" if native_class == _DEVICE else "unknown"
        codes: set[str] = set()
        if kind == "unknown":
            codes.add("unknown_node_class")
        identity = text(identifier.get("managedElementID"))
        name = text(value.get("name"))
        if identity is None:
            codes.add("native_identity_missing_or_unverified_type")
        if kind in ("root", "site") and name is None:
            codes.add("site_name_missing_or_unverified_type")
        if kind == "root" and native_class != _SITE:
            codes.add("root_site_class_unverified")
        unprojected = len(set(value) - {"meIdentifier", "children", "name", "parentOrmID"})
        unprojected += len(set(identifier) - {"managedElementID", "managedElementClass"})
        if kind in ("root", "site") and unprojected:
            codes.add("additional_fields_not_projected")
        row = _Node(
            f"node-{len(entries) + 1}", kind, identity, name,
            {
                "name": name,
                "meIdentifier": {
                    "managedElementID": identity,
                    "managedElementClass": _SITE if native_class == _SITE else None,
                },
            },
            parent, codes, unprojected,
        )
        if "parentOrmID" in value and kind in ("root", "site"):
            if isinstance(value["parentOrmID"], str):
                row.native["parentOrmID"] = value["parentOrmID"]
            else:
                codes.add("explicit_parent_type_unverified")
        entries.append(row)
        children = value.get("children")
        if not isinstance(children, list):
            codes.add("children_missing_or_unverified_type")
        else:
            for child in children:
                visit(child, row.reference, depth + 1)

    visit(native, None, 0)
    by_reference = {row.reference: row for row in entries}
    identities = Counter(
        row.identity for row in entries if row.kind in ("root", "site") and row.identity is not None
        and "root_site_class_unverified" not in row.codes
    )
    names = Counter(row.name for row in entries if row.kind in ("root", "site") and row.name)
    records: list[dict[str, object]] = []
    usable_sites = 0
    unresolved_sites = 0
    for row in entries:
        if row.kind == "device":
            continue
        codes = row.codes
        identity = row.identity
        if identity is not None and identities[identity] > 1:
            codes.add("duplicate_native_identity")
        if row.kind == "unknown":
            issues.update(codes)
            continue
        if row.name is not None and names[row.name] > 1:
            codes.add("duplicate_site_name")
        parent = by_reference.get(row.parent) if row.parent is not None else None
        inferred = parent is not None and parent.kind in ("root", "site")
        inferred = inferred and identity is not None and identities[identity] == 1
        if inferred and parent is not None:
            parent_identity = parent.identity
            inferred = parent_identity is not None and identities[parent_identity] == 1
            if "parentOrmID" in row.native and row.native["parentOrmID"] != parent_identity:
                codes.add("explicit_parent_conflicts_with_containment")
                inferred = False
        if "explicit_parent_type_unverified" in codes:
            inferred = False
        if parent is not None and parent.codes & {
            "root_site_class_unverified", "site_parent_dependency_unresolved", "ancestor_dependency_unresolved",
        }:
            codes.add("ancestor_dependency_unresolved")
            inferred = False
        if row.kind == "site" and not inferred:
            codes.add("site_parent_dependency_unresolved")
        if row.kind == "site":
            usable_sites += identity is not None and identities[identity] == 1
            unresolved_sites += not inferred
        records.append({
            "reference": row.reference, "native": row.native,
            "observed_container_parent": row.parent, "unprojected_field_count": row.unprojected,
            "parent_relationship": "legacy-nesting-inferred" if inferred else "root-context" if row.kind == "root" else "unresolved",
            "issue_codes": sorted(codes),
        })
        issues.update(codes)
    partial_codes = issues - {"additional_fields_not_projected", "duplicate_site_name"}
    return {
        "organization_root": records[0], "site_nodes": records[1:],
        "status": "partial" if partial_codes else "collected-unqualified",
        "counts": {
            "root_candidates": 1, "site_candidates": len(records) - 1,
            "sites_with_usable_identity": usable_sites,
            "sites_with_unresolved_dependencies": unresolved_sites,
            "unclassified_nodes": sum(row.kind == "unknown" for row in entries),
        },
        "redacted_fields": redactions, "redaction_count_basis": "full-response-before-site-projection",
        "issue_codes": sorted(issues),
    }


def run_destination_discovery(profile_path: str, credentials_path: str) -> tuple[dict[str, object], ExitStatus]:
    profile = DiscoveryProfile.read(profile_path)
    tls_warning = warning(profile.transport.verify_tls)
    if tls_warning is not None:
        print(tls_warning, file=sys.stderr)
    if not profile.output_directory.is_dir() or not os.access(profile.output_directory, os.W_OK | os.X_OK):
        _reader.fail("output_unwritable", "$", "Provision a private writable destination reports directory.")
    credentials = _Credentials(credentials_path)
    strategy = _DiscoveryAuthentication()
    projection = None
    failure = None
    try:
        with SessionManager(lambda: _backend(profile), credentials) as manager:
            manager.initialize(
                _UnknownVersionRequest(
                    SessionRole.DESTINATION, "cyber-controller", "unknown",
                    CredentialReference("cc-destination-discovery"),
                ), profile.transport, strategy=strategy,
            )
            manager.authenticate(SessionRole.DESTINATION)
            response = manager.request(SessionRole.DESTINATION, HttpMethod.GET, _TREE, expect_json=True)
            if response.status != 200:
                _reader.fail("unexpected_discovery_status", "$", "Organization discovery requires HTTP 200 JSON.")
            try:
                payload = load_json(response.body.decode("utf-8"))
            except (UnicodeError, ValueError, RecursionError):
                _reader.fail("invalid_discovery_json", "$", "Organization response must be strict JSON.")
            projection = project_site_tree(payload)
    except AuthenticationError as error:
        reason = error.failure.transport_reason
        failure = reason.value if reason is not None else error.failure.category.value
    except TransportError as error:
        failure = error.category.value
    finally:
        strategy.clear()
    report = {
        "operation": "destination-discovery", "offline_only": False,
        "configuration_writes_authorized": False, "read_only": True,
        "product_version": "unknown", "version_discovered": False,
        "version_verification": "unverified", "compatibility_verified": False,
        "migration_ready": False,
        "tls": {"verify": profile.transport.verify_tls},
    }
    if failure is not None:
        return {**report, "status": "error", "issue_codes": [failure]}, ExitStatus.VALIDATION_FAILED
    assert projection is not None
    directory_name = "cc-destination-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ-") + uuid4().hex[:12]
    directory = profile.output_directory / directory_name
    try:
        directory.mkdir(mode=0o700)
    except OSError:
        _reader.fail("output_unwritable", "$", "Provision a private writable destination reports directory.")
    snapshot = {
        "schema_version": 1, "domain": "cc-destination-organization-sites",
        "tls": {"verify": profile.transport.verify_tls},
        "destination": {"product": "cyber-controller", "name": profile.name, "version": "unknown", "version_verification": "unverified"},
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "request": {"method": "GET", "path": "/" + "/".join(_TREE)},
        "scope": {
            "read_only": True, "configuration_writes_authorized": False,
            "complete_site_enumeration": False, "migration_input": False, "devices_excluded": True,
        },
        "evidence": {
            "login": "API-01-C-legacy-basic-json-plus-validated-session",
            "tree": "API-03-legacy-source-observed", "exact_release_compatibility": "unverified",
            "document_version_conflict": "unresolved-10.10.7-versus-10.10.6",
            "root_and_parent_semantics": "legacy-inferred",
        },
        **projection,
    }
    write_local_export(str(directory / "organization-sites.json"), json.dumps(snapshot, allow_nan=False, indent=2))
    return {
        **report, "status": projection["status"], "counts": projection["counts"],
        "redacted_fields": projection["redacted_fields"], "issue_codes": projection["issue_codes"],
        "snapshot_directory": directory_name, "snapshot_file": "organization-sites.json",
        "session_closed_locally": True,
    }, ExitStatus.SUCCESS if projection["status"] == "collected-unqualified" else ExitStatus.VALIDATION_FAILED
