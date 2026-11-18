import json
import math
import re
from copy import deepcopy
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Literal

from ._contract_validation import ContractReader
from .contracts import ContractValidationError, JsonValue, ProductName, ValidationResult


@dataclass(frozen=True)
class ProductDeclaration:
    product: ProductName
    version: str


@dataclass(frozen=True)
class ExportMetadata:
    exported_at: str
    exporter: str


@dataclass(frozen=True)
class ArtifactValidationInformation:
    status: Literal["not_validated", "valid", "invalid"]
    issue_codes: tuple[str, ...] = ()
    scope: Literal["offline-contract"] = "offline-contract"


@dataclass(frozen=True)
class ConfigurationArtifact:
    schema_version: int
    domain: str
    source: ProductDeclaration
    metadata: ExportMetadata
    objects: tuple[dict[str, JsonValue], ...] = field(repr=False)
    validation: ArtifactValidationInformation

    def to_dict(self) -> dict[str, JsonValue]:
        payload: dict[str, JsonValue] = {
            "schema_version": self.schema_version,
            "domain": self.domain,
            "source": asdict(self.source),
            "metadata": asdict(self.metadata),
            "objects": [deepcopy(item) for item in self.objects],
            "validation": {
                "status": self.validation.status,
                "issue_codes": list(self.validation.issue_codes),
                "scope": self.validation.scope,
            },
        }
        parse_artifact(payload)
        return payload

    def to_json(self) -> str:
        # Controller comparison treats retained configuration-member order as significant.
        return json.dumps(self.to_dict(), allow_nan=False, sort_keys=self.domain != "controller-objects")


def _metadata(value: object, reader: ContractReader) -> ExportMetadata:
    data = reader.mapping(value, "$.metadata", {"exported_at", "exporter"})
    timestamp = reader.text(
        reader.required(data, "exported_at", "$.metadata"), "$.metadata.exported_at"
    )
    if not re.fullmatch(
        r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}"
        r"(?:\.[0-9]{1,6})?(?:Z|[+-](?:[01][0-9]|2[0-3]):[0-5][0-9])",
        timestamp,
    ):
        reader.fail("invalid_metadata", "$.metadata.exported_at", "Expected an ISO-8601 timestamp with seconds and timezone.")
    try:
        datetime.fromisoformat(timestamp)
    except ValueError:
        reader.fail("invalid_metadata", "$.metadata.exported_at", "Export timestamp is not a valid date/time.")
    exporter = reader.identifier(
        reader.required(data, "exporter", "$.metadata"), "$.metadata.exporter"
    )
    return ExportMetadata(timestamp, exporter)


def _validation_information(value: object, reader: ContractReader) -> ArtifactValidationInformation:
    data = reader.mapping(value, "$.validation", {"scope", "status", "issue_codes"})
    if reader.required(data, "scope", "$.validation") != "offline-contract":
        reader.fail("invalid_validation_info", "$.validation.scope", "Only offline-contract validation scope is supported.")
    status = reader.required(data, "status", "$.validation")
    if status not in ("not_validated", "valid", "invalid"):
        reader.fail("invalid_validation_info", "$.validation.status", "Expected not_validated, valid, or invalid.")
    codes = reader.required(data, "issue_codes", "$.validation")
    if not isinstance(codes, list):
        reader.fail("invalid_type", "$.validation.issue_codes", "Expected an array of issue codes.")
    parsed_codes: list[str] = []
    for index, code in enumerate(codes):
        if not isinstance(code, str) or not re.fullmatch(r"[a-z][a-z0-9_]*", code):
            reader.fail("invalid_validation_info", f"$.validation.issue_codes[{index}]", "Expected a stable issue code, not free-form error text.")
        parsed_codes.append(code)
    if (status == "invalid") != bool(parsed_codes):
        reader.fail("invalid_validation_info", "$.validation", "Only invalid status must have one or more issue codes.")
    if status == "not_validated":
        return ArtifactValidationInformation("not_validated")
    if status == "valid":
        return ArtifactValidationInformation("valid")
    return ArtifactValidationInformation("invalid", tuple(parsed_codes))


def _configuration_value(
    value: object, reader: ContractReader, path: str, depth: int = 0
) -> JsonValue:
    if depth > 64:
        reader.fail("invalid_value", path, "Configuration nesting exceeds the offline contract limit.")
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            reader.fail("invalid_value", path, "Nonfinite numbers are not valid configuration values.")
        return value
    if isinstance(value, list):
        return [
            _configuration_value(item, reader, f"{path}[{index}]", depth + 1)
            for index, item in enumerate(value)
        ]
    if not isinstance(value, dict):
        reader.fail("invalid_type", path, "Expected JSON-compatible configuration values.")
    data = reader.mapping(value, path)
    if "secret_ref" in data:
        if data.keys() != {"secret_ref"}:
            reader.fail("unknown_fields", path, "A secret reference must be the entire value object.")
        return {"secret_ref": reader.reference(data["secret_ref"], path)}
    result: dict[str, JsonValue] = {}
    for index, (key, item) in enumerate(data.items()):
        # Positional field paths avoid exposing arbitrary keys from sensitive payloads.
        item_path = f"{path}.fields[{index}]"
        normalized = re.sub(r"[^a-z0-9]", "", key.lower())
        sensitive = any(
            term in normalized
            for term in (
                "password", "passwd", "secret", "token", "credential", "community",
                "cookie", "authorization", "privatekey", "apikey", "sessionid",
            )
        ) or normalized == "pwd"
        if sensitive and item is not None and not (
            isinstance(item, dict) and item.keys() == {"secret_ref"}
        ):
            reader.fail("secret_value_not_allowed", item_path, "Credential fields must be null or contain only a secret_ref.")
        result[key] = _configuration_value(item, reader, item_path, depth + 1)
    return result


def parse_artifact(payload: object) -> ConfigurationArtifact:
    reader = ContractReader("artifact")
    data = reader.mapping(
        payload, "$", {"schema_version", "domain", "source", "metadata", "objects", "validation"}
    )
    schema = reader.required(data, "schema_version", "$")
    if type(schema) is not int or schema != 1:
        reader.fail("unsupported_schema", "$.schema_version", "Only integer artifact schema version 1 is supported.")
    domain = reader.identifier(reader.required(data, "domain", "$"), "$.domain")
    source = reader.mapping(
        reader.required(data, "source", "$"), "$.source", {"product", "version"}
    )
    declaration = ProductDeclaration(
        reader.product(reader.required(source, "product", "$.source"), "$.source.product"),
        reader.version(reader.required(source, "version", "$.source"), "$.source.version"),
    )
    metadata = _metadata(reader.required(data, "metadata", "$"), reader)
    objects = reader.required(data, "objects", "$")
    if not isinstance(objects, list):
        reader.fail("invalid_type", "$.objects", "Expected an array of configuration objects.")
    parsed_objects: list[dict[str, JsonValue]] = []
    for index, item in enumerate(objects):
        path = f"$.objects[{index}]"
        reader.mapping(item, path)
        parsed = _configuration_value(item, reader, path)
        if not isinstance(parsed, dict):
            reader.fail("invalid_type", path, "Expected a configuration object.")
        parsed_objects.append(parsed)
    validation = _validation_information(reader.required(data, "validation", "$"), reader)
    return ConfigurationArtifact(1, domain, declaration, metadata, tuple(parsed_objects), validation)


def validate_artifact(payload: object) -> ValidationResult:
    try:
        artifact = parse_artifact(payload)
    except ContractValidationError as exc:
        return exc.result
    return ValidationResult("artifact", "valid", object_count=len(artifact.objects))
