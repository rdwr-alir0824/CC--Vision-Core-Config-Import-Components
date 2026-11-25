from __future__ import annotations

import json
from typing import NoReturn


def _json_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON member.")
        result[key] = value
    return result


def _reject_constant(_value: str) -> NoReturn:
    raise ValueError("Nonstandard JSON numeric constant.")


def load_json(text: str) -> object:
    return json.loads(text, object_pairs_hook=_json_object, parse_constant=_reject_constant)
