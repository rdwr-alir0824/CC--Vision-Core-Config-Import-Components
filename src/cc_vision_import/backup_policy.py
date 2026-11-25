"""Shared operator-facing backup selection; compatible with host Python 3.8."""

from __future__ import annotations

import re


TLS_WARNING = "WARNING: HTTPS certificate verification is disabled."
SUPPORTED_DOMAINS = ("controller-objects", "device-access")
UNSUPPORTED_DOMAINS = {
    "physical-tree": "Vision Physical tree GET/enumeration contract is not documented.",
    "organization-tree": "Vision Organization tree GET/enumeration contract is not documented.",
    "credential-configuration": "Credential backup/portability is not qualified; sensitive fields are redacted.",
    "ldap-permissions": "Legacy Vision read is source-observed; its exact-version response contract is unverified.",
    "scheduler": "Legacy API.scheduler_endpoint binding/configuration is missing.",
}


class BackupPolicyError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def backup_domains(data: dict[str, object]) -> tuple[str, ...]:
    mode = data.get("backup_mode", "selected" if "domains" in data else "full-supported")
    if mode not in ("full-supported", "selected"):
        raise BackupPolicyError("unsupported_backup_mode", "Use backup_mode full-supported or selected.")
    if mode == "full-supported":
        if "domains" in data:
            raise BackupPolicyError("conflicting_domain_selection", "Full Supported Backup must not specify a separate domains list.")
        return SUPPORTED_DOMAINS
    values = data.get("domains")
    if not isinstance(values, list) or not values:
        raise BackupPolicyError("empty_selection", "Selected backup requires a nonempty domains array.")
    result: list[str] = []
    for value in values:
        if not isinstance(value, str):
            raise BackupPolicyError("invalid_type", "Backup domains must be strings.")
        if re.sub(r"[^a-z0-9]", "", value.casefold()).startswith("amsalert"):
            raise BackupPolicyError("unsupported_backup_domain", "Unsupported backup component.")
        if value not in SUPPORTED_DOMAINS:
            reason = UNSUPPORTED_DOMAINS.get(value, "No implemented backup module exists for this selection.")
            raise BackupPolicyError("unsupported_backup_domain", reason)
        if value in result:
            raise BackupPolicyError("duplicate_reference", "Do not repeat backup domains.")
        result.append(value)
    return tuple(result)
