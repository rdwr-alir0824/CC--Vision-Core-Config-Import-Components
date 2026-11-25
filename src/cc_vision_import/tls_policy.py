"""Temporary, origin-bound TLS exceptions with an optional production lock."""

import os
import stat
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

from ._json import load_json
from .backup_policy import TLS_WARNING


class TLSPolicyError(ValueError):
    pass


def _origin(value: str) -> tuple[str, int]:
    try:
        parsed = urlsplit(value)
        if (
            parsed.scheme != "https" or not parsed.hostname
            or parsed.username is not None or parsed.password is not None
            or parsed.path not in ("", "/") or parsed.query or parsed.fragment
            or any(c.isspace() or not c.isprintable() for c in value)
            or parsed.port == 0
        ):
            raise ValueError
        return parsed.hostname.lower(), parsed.port or 443
    except (ValueError, TypeError):
        raise TLSPolicyError("TLS exception requires an HTTPS origin without credentials or paths.") from None


@dataclass(frozen=True)
class TLSPolicy:
    verify: bool = True
    lab_authorized: bool = False
    authorized_origin: str | None = None

    @classmethod
    def from_dict(cls, value: object, origin: str) -> "TLSPolicy":
        if not isinstance(value, dict) or set(value) - {"verify", "lab_authorized", "authorized_origin"}:
            raise TLSPolicyError("TLS exception accepts only verify, lab_authorized and authorized_origin.")
        verify = value.get("verify", True)
        authorized = value.get("lab_authorized", False)
        permitted = value.get("authorized_origin")
        if type(verify) is not bool or type(authorized) is not bool:
            raise TLSPolicyError("TLS exception booleans must be JSON true or false.")
        if permitted is not None and not isinstance(permitted, str):
            raise TLSPolicyError("TLS authorized_origin must be an HTTPS origin.")
        current = _origin(origin)
        expected = None if permitted is None else _origin(permitted)
        if not verify and (not authorized or expected is None or expected != current):
            raise TLSPolicyError("Unverified TLS requires explicit lab authorization for this exact controller origin.")
        return cls(verify, authorized, permitted)

    def to_dict(self) -> dict[str, object]:
        return {"verify": True} if self.verify else {
            "verify": False, "lab_authorized": True, "authorized_origin": self.authorized_origin,
        }


def _private_file(path: Path) -> None:
    info = path.lstat()
    if (
        not stat.S_ISREG(info.st_mode) or stat.S_IMODE(info.st_mode) != 0o600
        or info.st_uid != 10001 or info.st_gid != 10001
    ):
        raise TLSPolicyError("Temporary TLS exception must be a regular mode-0600 file owned by UID/GID 10001.")


def exceptions_allowed(value: str = "true") -> bool:
    if value not in ("true", "false"):
        raise TLSPolicyError("CCV_ALLOW_INSECURE_TLS_EXCEPTION must be true or false.")
    return value == "true"


def read_exception(
    path: Path, origin: str, requested: str = "true", allow: str = "true",
) -> TLSPolicy:
    allowed = exceptions_allowed(allow)
    if requested not in ("", "-", "true", "false"):
        raise TLSPolicyError("TLS verification setting must be true or false.")
    if requested != "false":
        return TLSPolicy.from_dict({}, origin)
    if not allowed:
        raise TLSPolicyError("This deployment prohibits insecure TLS exceptions.")
    try:
        _private_file(path)
        with path.open("rb") as stream:
            raw = stream.read(4097)
        if len(raw) > 4096:
            raise TLSPolicyError("Temporary TLS exception exceeds the size limit.")
        policy = TLSPolicy.from_dict(load_json(raw.decode("utf-8")), origin)
    except TLSPolicyError:
        raise
    except (OSError, ValueError):
        raise TLSPolicyError("A private, operator-approved TLS exception is required for this execution.") from None
    if policy.verify:
        raise TLSPolicyError("Temporary TLS exception must explicitly authorize this unverified execution.")
    return policy


def warning(verify: bool) -> str | None:
    return None if verify else TLS_WARNING


def require_execution_exception(origin: str, verify: bool, credentials_path: str) -> None:
    if not verify:
        read_exception(
            Path(credentials_path).parent / "tls-exception.json", origin, "false",
            os.environ.get("CCV_ALLOW_INSECURE_TLS_EXCEPTION", "true"),
        )


def execution_tls(verify: bool) -> dict[str, object]:
    return {"verify": True} if verify else {
        "verify": False, "exception_scope": "selected_origin_current_execution",
    }
