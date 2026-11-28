"""Strict JSON handling without migration envelopes or persistent state."""

import json
import math
import os
import tempfile
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
    temporary: Path | None = None
    error: JsonFileError | None = None
    try:
        destination = Path(path)
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=destination.parent,
            prefix=".ccv-json-", suffix=".tmp", delete=False,
        ) as stream:
            temporary = Path(stream.name)
            payload = text + "\n"
            if stream.write(payload) != len(payload):
                raise OSError("Incomplete temporary JSON write.")
        os.replace(temporary, destination)
        temporary = None
    except (OSError, UnicodeError):
        error = JsonFileError("Cannot write JSON file.")
    finally:
        if temporary is not None:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                if error is None:
                    raise JsonFileError("Cannot clean up temporary JSON file.") from None
                error.add_note("Temporary JSON file cleanup failed.")
    if error is not None:
        raise error from None
