import argparse
import json
from collections.abc import Sequence
from dataclasses import asdict
from pathlib import Path
from ._json import load_json
from .contracts import ExitStatus, ValidationIssue, ValidationResult
from .registry import MODULES, get_module


def _input_error(module: str, code: str, message: str) -> ExitStatus:
    result = ValidationResult(
        module=module,
        status="error",
        issues=(ValidationIssue(code, "$", message),),
    )
    print(json.dumps(asdict(result)))
    return ExitStatus.INPUT_ERROR


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m cc_vision_import",
        description="Offline application foundation. No live export or import operations.",
    )
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("modules", help="List registered modules and available operations.")
    validate = commands.add_parser("validate", help="Validate a local synthetic fixture, profile, artifact, or plan.")
    validate.add_argument("--module", choices=[module.name for module in MODULES], required=True)
    validate.add_argument("--input", required=True, help="Local UTF-8 JSON file; not a URL or UNC path.")
    args = parser.parse_args(argv)

    if args.command == "modules":
        print(
            json.dumps(
                {
                    "modules": [
                        {
                            "name": module.name,
                            "description": module.description,
                            "operations": ["validate"],
                        }
                        for module in MODULES
                    ]
                }
            )
        )
        return ExitStatus.SUCCESS

    module = get_module(args.module)
    if module is None:
        parser.error("The selected module is not registered.")

    input_path: str = args.input
    if input_path.startswith(("\\\\", "//")) or "://" in input_path:
        return _input_error(
            module.name, "nonlocal_input", "Use a local file, not a URL or UNC path."
        )
    try:
        text = Path(input_path).read_text(encoding="utf-8")
    except UnicodeError:
        return _input_error(module.name, "invalid_encoding", "Input must be UTF-8 text.")
    except (OSError, ValueError):
        return _input_error(
            module.name, "input_unreadable", "Cannot read the input file; check its path and permissions."
        )
    try:
        payload = load_json(text)
    except (ValueError, RecursionError):
        return _input_error(
            module.name, "invalid_json", "Input must be valid JSON with unique member names."
        )

    result = module.validate(payload)
    print(json.dumps(asdict(result)))
    return ExitStatus.SUCCESS if result.status == "valid" else ExitStatus.VALIDATION_FAILED
