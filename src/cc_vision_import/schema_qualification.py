"""Offline document subsets, never product capabilities or migration permission."""

import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Literal

from ._contract_validation import ContractReader
from ._json import load_json
from .artifacts import ConfigurationArtifact, parse_artifact
from .contracts import JsonValue, ProductName, ValidationIssue
from .controller_objects import (
    has_uncertain_controller_credentials, is_controller_credential_field,
    validate_controller_credentials,
)
from .transport import HttpResponse, build_url


_reader = ContractReader("schema-qualification")


@dataclass(frozen=True)
class DocumentEvidence:
    reference: str
    product: ProductName
    version: str
    title: str
    date: str
    sha256: str
    metadata_version: str

    @property
    def limitations(self) -> tuple[ValidationIssue, ...]:
        if self.version != self.metadata_version:
            return (ValidationIssue(
                "document_version_conflict", "$.evidence",
                "Cover and overview version conflict with PDF metadata; applicability is unresolved.",
            ),)
        return ()


_DOCUMENTS = (
    DocumentEvidence(
        "DOC-V549", "vision", "5.4.9", "APSolute Vision 5.4.9 REST API", "April 2025",
        "827d4954cf5390f3a242e8bbb0af4dc7dd9ce68f5c17eba19449cf45a8d9d5c4", "5.4.9",
    ),
    DocumentEvidence(
        "DOC-CC10107", "cyber-controller", "10.10.7",
        "Cyber Controller 10.10.7 REST API", "September 2026",
        "f6c7e474cb2df25d5d1b7b52da94f13f9b5013649419fc4276f49bd153e2d587", "10.10.6",
    ),
)


def require_document(product: str, version: str, reference: str) -> DocumentEvidence:
    for document in _DOCUMENTS:
        if document.product == product and document.version == version:
            if document.reference != reference:
                _reader.fail("invalid_evidence", "$.evidence", "Evidence must match the declared product and exact version.")
            return document
    _reader.fail("unsupported_version", "$.source", "No approved document binding exists for this product and exact version.")


@dataclass(frozen=True)
class OperationEvidence:
    document: DocumentEvidence
    record: str
    method: str
    path: str | None
    classification: Literal["documented", "not-found", "unresolved-binding"]
    pdf_pages: tuple[int, ...]
    candidate_path: str | None = None


def operation_evidence(
    product: str, version: str, reference: str, record: str,
) -> OperationEvidence:
    document = require_document(product, version, reference)
    _reader.text(record, "$.operation")
    original_record = record
    if record == "VISION-MANAGED-DEVICES":
        if product != "vision":
            _reader.fail("product_mismatch", "$.operation", "Discovery evidence is bound only to Vision.")
        return OperationEvidence(
            document, record, "GET", "/mgmt/system/config/itemlist/alldevices",
            "documented", (119, 120, 263),
        )
    if record in ("API-01-V", "API-01-C"):
        expected = "vision" if record == "API-01-V" else "cyber-controller"
        if product != expected:
            _reader.fail("product_mismatch", "$.operation", "Legacy authentication record belongs to the other product.")
        record = "API-01"
    pages = {
        "API-01": (156, 157, 158),
        "API-04": (141,) if document.product == "vision" else (152,),
        "API-05": (146,), "API-06": (143, 144),
        "API-08": (148, 149, 150) if document.product == "vision" else (141, 142, 143),
    }
    pairs = {
        "API-01": ("POST", "/mgmt/system/user/login"),
        "API-02": ("GET", "/mgmt/system/config/tree/Physical"),
        "API-03": ("GET", "/mgmt/system/config/tree/Organization"),
        "API-04": ("GET", "/mgmt/system/config/tree/site/byname/{name}"),
        "API-05": ("GET", "/mgmt/system/config/tree/site/byid/{id}"),
        "API-06": ("GET", "/mgmt/system/config/tree/device/byip/{ip}"),
        "API-07": ("POST", "/mgmt/system/config/tree/site"),
        "API-08": ("POST", "/mgmt/system/config/tree/device"),
        "API-09": ("PUT", "/mgmt/system/config/tree/device"),
        "API-10": ("GET", "/mgmt/system/config/itemlist/ldapobjectpermission"),
        "API-11": ("POST", "/mgmt/system/config/itemlist/ldapobjectpermission"),
        "API-12": ("PUT", "/{index}/_doc/{document_id}"),
    }
    if record in pages:
        return OperationEvidence(document, original_record, *pairs[record], "documented", pages[record])
    if record in pairs:
        return OperationEvidence(document, record, *pairs[record], "not-found", ())
    if record in ("CFG-01", "CFG-02", "CFG-03", "CFG-04"):
        candidates = {"CFG-01": "/mgmt/system/user/login", "CFG-02": "/mgmt/system/user/logout"}
        return OperationEvidence(
            document, record, "GET" if record == "CFG-03" else "POST", None,
            "unresolved-binding", (), candidates.get(record),
        )
    _reader.fail("unknown_operation", "$.operation", "Operation has no reviewed evidence record.")


class SchemaSubset(StrEnum):
    SITE = "site-lookup"
    DEVICE = "device-lookup"
    DEVICE_ACCESS = "device-access-model"


@dataclass(frozen=True)
class SubsetQualification:
    document: DocumentEvidence
    subset: SchemaSubset
    pdf_pages: tuple[int, ...]
    artifact: ConfigurationArtifact = field(repr=False)
    unqualified: tuple[ValidationIssue, ...] = ()

    @property
    def status(self) -> Literal["documented-subset", "unqualified"]:
        return "unqualified" if self.unqualified else "documented-subset"


_ACCESS_INTEGERS = (
    "cliPort", "httpsSocketTimeout", "httpsPort", "httpSocketTimout", "ormVersion",
    "httpPort", "httpsConnectionTimeout", "httpConnectionTimeout",
)
_ACCESS_BOOLEANS = (
    "useHttpsAuthentication", "useSnmpV3Authentication", "isSsh", "verifyHttpCredentials",
    "useSnmpV3Privacy", "exclusivelyReceiveDeviceEvents", "useHttpAuthentication",
    "verifyHttpsCredentials", "registerDeviceEvents",
)
_ACCESS_STRINGS = (
    "description", "cliUsername", "ormID", "snmpV3PrivacyPassword", "httpsUsername",
    "snmpV3AuthenticationPassword", "snmpV2WriteCommunity", "snmpV3Username",
    "httpPassword", "managementIp", "httpsPassword", "name", "httpUsername",
    "cliPassword", "snmpV2ReadCommunity", "snmpV1WriteCommunity", "mgt2Ip",
    "snmpV1ReadCommunity", "mgt1Ip",
)
_ACCESS_ENUMS = (
    "snmpV3PrivacyProtocol", "snmpV3AuthenticationProtocol", "visionMgtPort", "snmpVersion",
)


def _fields(names: tuple[str, ...], kind: str) -> dict[str, str]:
    return dict.fromkeys(names, kind)


_ACCESS = (
    _fields(_ACCESS_INTEGERS, "int32") | _fields(_ACCESS_BOOLEANS, "boolean")
    | _fields(_ACCESS_STRINGS, "string") | _fields(_ACCESS_ENUMS, "enum")
)
_SETUP = (
    _fields(("license", "deviceSoftware", "deviceDriver", "hardware"), "object")
    | _fields(("ormID", "name", "description"), "string")
    | {"ormVersion": "int32", "deviceAccess": "access"}
)
_DEVICE = (
    _fields((
        "ormID", "name", "description", "type", "treeType", "physicalParentId",
        "externalId", "hierarchyPath",
    ), "string")
    | {"ormVersion": "int32", "deviceSetup": "setup"}
)
_SITE = _fields(("ormID", "name", "type", "description", "parentOrmID"), "string")


def _model(
    data: dict[str, JsonValue], fields: dict[str, str], path: str,
    unqualified: list[ValidationIssue],
) -> None:
    for index, (key, value) in enumerate(data.items()):
        if key not in fields:
            continue
        location = f"{path}.fields[{index}]"
        if value is None:
            unqualified.append(ValidationIssue(
                "unverified_nullability", location,
                "Null is preserved; the reference does not establish whether the product accepts it.",
            ))
            continue
        if is_controller_credential_field(key) and isinstance(value, dict) and value.keys() == {"secret_ref"}:
            continue
        kind = fields[key]
        if kind == "enum":
            unqualified.append(ValidationIssue(
                "unverified_enum", location, "The referenced enum value set is not qualified.",
            ))
        elif kind == "string" and not isinstance(value, str):
            _reader.fail("invalid_type", location, "Documented subset field must be a string.")
        elif kind == "boolean" and type(value) is not bool:
            _reader.fail("invalid_type", location, "Documented subset field must be a boolean.")
        elif kind == "int32" and (type(value) is not int or not -(2 ** 31) <= value < 2 ** 31):
            _reader.fail("invalid_type", location, "Documented subset field must be a signed 32-bit integer.")
        elif kind in ("access", "setup", "object"):
            if not isinstance(value, dict):
                _reader.fail("invalid_type", location, "Documented subset field must be an object.")
            if kind != "object":
                _model(value, _ACCESS if kind == "access" else _SETUP, location, unqualified)


def qualify_schema(
    payload: object, subset: SchemaSubset, *, evidence_reference: str,
) -> SubsetQualification:
    """Validate an explicit artifact envelope, not a complete vendor wire schema."""
    if not isinstance(subset, SchemaSubset):
        _reader.fail("unsupported_schema", "$.subset", "Only the reviewed lookup/model subsets are available.")
    artifact = parse_artifact(payload)
    document = require_document(artifact.source.product, artifact.source.version, evidence_reference)
    if artifact.domain != "api-schema-evidence":
        _reader.fail("invalid_domain", "$.domain", "Qualification requires an api-schema-evidence artifact.")
    validate_controller_credentials(artifact)
    issues = list(document.limitations)
    fields = {SchemaSubset.SITE: _SITE, SchemaSubset.DEVICE: _DEVICE, SchemaSubset.DEVICE_ACCESS: _ACCESS}[subset]
    for index, data in enumerate(artifact.objects):
        path = f"$.objects[{index}]"
        if subset == SchemaSubset.SITE:
            for key in ("ormID", "name", "type"):
                _reader.required(data, key, path)
        _model(data, fields, path, issues)
        if has_uncertain_controller_credentials(data):
            issues.append(ValidationIssue(
                "credential_representation_unqualified", path,
                "Protected or uncertain credentials do not establish vendor wire representation or portability.",
            ))
    pages = {
        SchemaSubset.SITE: (255,),
        SchemaSubset.DEVICE: (219, 220, 224) if document.product == "vision" else (219, 220, 221, 224),
        SchemaSubset.DEVICE_ACCESS: (220, 221, 222) if document.product == "vision" else (221, 222),
    }[subset]
    return SubsetQualification(document, subset, pages, artifact, tuple(issues))


def _response(response: HttpResponse) -> None:
    if (
        not isinstance(response, HttpResponse) or type(response.status) is not int
        or not 100 <= response.status <= 599 or not isinstance(response.body, bytes)
        or not isinstance(response.headers, Mapping)
    ):
        _reader.fail("malformed_response", "$.response", "Expected an offline HTTP response.")


def _json_value(response: HttpResponse) -> object:
    try:
        value = load_json(response.body.decode("utf-8"))
    except (ValueError, UnicodeError, RecursionError):
        pass
    else:
        return value
    _reader.fail("malformed_response", "$.response.body", "Expected strict UTF-8 JSON content.")


@dataclass(frozen=True)
class LoginQualification:
    document: DocumentEvidence
    outcome: Literal["reported-login", "reported-rejection"]
    unqualified: tuple[ValidationIssue, ...]
    pdf_pages: tuple[int, ...] = (156, 157, 158)


def qualify_login_response(
    response: HttpResponse, *, product: str, version: str, evidence_reference: str,
) -> LoginQualification:
    document = require_document(product, version, evidence_reference)
    _response(response)
    body = _reader.mapping(_json_value(response), "$.response.body")
    status = _reader.required(body, "status", "$.response.body")
    if response.status == 200 and status == "ok":
        _reader.text(_reader.required(body, "jsessionid", "$.response.body"), "$.response.body.jsessionid")
        outcome: Literal["reported-login", "reported-rejection"] = "reported-login"
    elif response.status == 401 and status == "error":
        _reader.text(_reader.required(body, "message", "$.response.body"), "$.response.body.message")
        outcome = "reported-rejection"
    else:
        _reader.fail("unqualified_login", "$.response", "Response does not match the reviewed login examples.")
    return LoginQualification(document, outcome, document.limitations)


@dataclass(frozen=True)
class AsyncQualification:
    document: DocumentEvidence
    phase: Literal["accepted", "in-progress", "result-available", "result-received"]
    outcome: Literal["not-complete", "http-failure", "reported-failure", "reported-success-unverified", "unqualified-result"]
    final_status: int | None
    unqualified: tuple[ValidationIssue, ...]
    pdf_pages: tuple[int, ...] = (11,)


def _tracking_id(
    response: HttpResponse, origin: str, stage: str, *, required: bool = True,
) -> str | None:
    if any(not isinstance(key, str) for key in response.headers):
        _reader.fail("invalid_tracking", "$.response.headers", "Tracking headers must have string names.")
    locations = [value for key, value in response.headers.items() if key.lower() == "location"]
    if not locations and not required:
        return None
    if len(locations) != 1 or not isinstance(locations[0], str):
        _reader.fail("invalid_tracking", "$.response.headers", "A single tracking Location is required.")
    # Exact trusted origin and conservative opaque IDs are local safety policy.
    match = re.fullmatch(
        re.escape(origin.rstrip("/")) + "/mgmt/asyncoperations/" + stage + r"/([A-Za-z0-9_-]+)",
        locations[0],
    )
    if match is None:
        _reader.fail("invalid_tracking", "$.response.headers", "Tracking Location is outside the permitted origin/path shape.")
    return match.group(1)


def qualify_async_trace(
    responses: tuple[HttpResponse, ...], *, origin: str,
    product: str, version: str, evidence_reference: str,
) -> AsyncQualification:
    """Observe supplied responses only; never poll, redirect, retry, or dispatch."""
    document = require_document(product, version, evidence_reference)
    origin = build_url(origin, ()).rstrip("/")
    if not isinstance(responses, tuple) or not responses:
        _reader.fail("invalid_trace", "$.responses", "Supply a nonempty tuple of offline responses.")
    for response in responses:
        _response(response)
    if responses[0].status != 202:
        _reader.fail("invalid_trace", "$.responses[0]", "The documented asynchronous sequence begins with 202.")
    identity = _tracking_id(responses[0], origin, "status")
    phase: Literal["accepted", "in-progress", "result-available", "result-received"] = "accepted"
    outcome: Literal["not-complete", "http-failure", "reported-failure", "reported-success-unverified", "unqualified-result"] = "not-complete"
    final_status = None
    issues = list(document.limitations)
    for response in responses[1:]:
        if phase in ("accepted", "in-progress"):
            if response.status == 200:
                returned = _tracking_id(response, origin, "status", required=False)
                if returned is not None and returned != identity:
                    _reader.fail("invalid_tracking", "$.response.headers", "Tracking identity changed.")
                phase = "in-progress"
            elif response.status == 303:
                if _tracking_id(response, origin, "result") != identity:
                    _reader.fail("invalid_tracking", "$.response.headers", "Result identity differs from the accepted operation.")
                phase = "result-available"
            else:
                _reader.fail("unqualified_tracking", "$.response", "Tracking failed or returned an undocumented state.")
        elif phase == "result-available":
            final_status = response.status
            if 400 <= response.status <= 599:
                outcome = "http-failure"
            elif 200 <= response.status <= 299 and response.status != 202:
                if response.body:
                    body = _json_value(response)
                    reported = body.get("status") if isinstance(body, dict) else None
                else:
                    reported = None
                # This reports example-style body semantics, never verified configuration.
                outcome = (
                    "reported-failure" if reported == "error" else
                    "reported-success-unverified" if reported == "ok" else "unqualified-result"
                )
                if outcome == "unqualified-result":
                    issues.append(ValidationIssue(
                        "result_semantics_unverified", "$.response",
                        "The final HTTP result does not establish operation semantics.",
                    ))
            else:
                _reader.fail("incomplete_result", "$.response", "Acceptance or redirection is not a terminal result.")
            phase = "result-received"
        else:
            _reader.fail("invalid_trace", "$.responses", "Responses after a final result are not permitted.")
    return AsyncQualification(document, phase, outcome, final_status, tuple(issues))
