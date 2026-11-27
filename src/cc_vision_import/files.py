"""Strict JSON handling without migration envelopes or persistent state."""

import json
import math
import os
from pathlib import Path
from typing import TypeGuard

from ._json import load_json as _load_json
from .contracts import JsonValue


class JsonFileError(ValueError):
    pass


def _is_json(value: object) -> TypeGuard[JsonValue]:
    if value is None or type(value) in (str, bool, int):
        return True
    if isinstance(value, float):
        return math.isfinite(value)
    if isinstance(value, list):
        return all(_is_json(item) for item in value)
    if isinstance(value, dict):
        return all(isinstance(key, str) and _is_json(item) for key, item in value.items())
    return False


def parse_json(text: str) -> JsonValue:
    try:
        value = _load_json(text)
        if not _is_json(value):
            raise ValueError
        return value
    except (ValueError, RecursionError):
        raise ValueError("Invalid or unsupported JSON data.") from None


def serialize_json(data: JsonValue) -> str:
    try:
        if not _is_json(data):
            raise ValueError
        return json.dumps(data, indent=2, ensure_ascii=True, allow_nan=False)
    except (ValueError, TypeError, RecursionError):
        raise ValueError("Invalid or unsupported JSON data.") from None


def load_json(path: str | Path) -> JsonValue:
    try:
        return parse_json(Path(path).read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise JsonFileError("JSON file not found.") from None
    except (OSError, UnicodeError):
        raise JsonFileError("Cannot read JSON file.") from None
    except ValueError:
        raise JsonFileError("Invalid or unsupported JSON file.") from None


def save_json(path: str | Path, data: JsonValue) -> None:
    try:
        text = serialize_json(data)
    except ValueError:
        raise JsonFileError("Invalid or unsupported JSON data.") from None
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(text + "\n")
    except (OSError, UnicodeError):
        raise JsonFileError("Cannot write JSON file.") from None
