import re
from ipaddress import ip_address
from typing import NoReturn
from urllib.parse import urlsplit

from .contracts import ContractValidationError, ProductName, ValidationIssue, ValidationResult


class ContractReader:
    def __init__(self, module: str) -> None:
        self.module = module

    def fail(self, code: str, path: str, message: str) -> NoReturn:
        raise ContractValidationError(
            ValidationResult(
                self.module, "invalid", issues=(ValidationIssue(code, path, message),)
            )
        )

    def mapping(
        self, value: object, path: str, fields: set[str] | None = None
    ) -> dict[str, object]:
        if not isinstance(value, dict):
            self.fail("invalid_type", path, "Expected a JSON object.")
        result: dict[str, object] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                self.fail("invalid_type", path, "JSON object keys must be strings.")
            result[key] = item
        if fields is not None and result.keys() - fields:
            self.fail("unknown_fields", path, "Unrecognized contract fields are not allowed.")
        return result

    def required(self, data: dict[str, object], key: str, path: str) -> object:
        if key not in data:
            self.fail("missing_field", f"{path}.{key}", "Required field is missing.")
        return data[key]

    def text(self, value: object, path: str) -> str:
        if (
            not isinstance(value, str)
            or not value
            or value != value.strip()
            or any(not character.isprintable() for character in value)
        ):
            self.fail("invalid_value", path, "Expected nonempty text without surrounding whitespace or controls.")
        return value

    def identifier(self, value: object, path: str) -> str:
        text = self.text(value, path)
        if not re.fullmatch(r"[a-z][a-z0-9]*(?:-[a-z0-9]+)*", text):
            self.fail("invalid_value", path, "Expected a lowercase hyphen-separated identifier.")
        return text

    def reference(self, value: object, path: str) -> str:
        text = self.text(value, path)
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._/-]*", text):
            self.fail("invalid_value", path, "Expected an opaque secret reference, not a credential or URL.")
        return text

    def product(self, value: object, path: str) -> ProductName:
        if value == "vision":
            return "vision"
        if value == "cyber-controller":
            return "cyber-controller"
        self.fail("invalid_product", path, "Expected vision or cyber-controller; compatibility is not certified.")

    def version(self, value: object, path: str) -> str:
        if not isinstance(value, str) or not re.fullmatch(
            r"[0-9]+(?:\.[0-9]+)+(?:[-+][A-Za-z0-9]+(?:[._-][A-Za-z0-9]+)*)?", value
        ):
            self.fail("invalid_version", path, "Expected a dotted numeric version with an optional build suffix.")
        return value

    def base_url(self, value: object, path: str) -> str:
        url = self.text(value, path)
        try:
            parsed = urlsplit(url)
            host, port = parsed.hostname, parsed.port
        except ValueError:
            self.fail("invalid_value", path, "Expected a valid HTTPS base URL.")
        if (
            parsed.scheme != "https"
            or not host
            or parsed.username is not None
            or parsed.password is not None
            or parsed.path not in ("", "/")
            or "?" in url
            or "#" in url
            or any(character.isspace() for character in url)
            or port == 0
        ):
            self.fail("invalid_value", path, "Use an HTTPS origin without credentials, path, query, or fragment.")
        try:
            ip_address(host)
        except ValueError:
            if not all(
                re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?", label)
                for label in host.split(".")
            ):
                self.fail("invalid_value", path, "Expected a valid host declaration.")
        return url

    def checksum(self, value: object, path: str) -> str:
        if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value):
            self.fail("invalid_checksum", path, "Expected a lowercase SHA-256 hexadecimal digest.")
        return value

    def references(self, value: object, path: str) -> tuple[str, ...]:
        if not isinstance(value, list):
            self.fail("invalid_type", path, "Expected an array of references.")
        references = tuple(self.identifier(item, f"{path}[{i}]") for i, item in enumerate(value))
        if len(references) != len(set(references)):
            self.fail("duplicate_reference", path, "References must be unique.")
        return tuple(sorted(references))
