import argparse
import json
from collections.abc import Sequence
from dataclasses import asdict
from pathlib import Path
from ._json import load_json
from .contracts import ContractValidationError, ExitStatus, ValidationIssue, ValidationResult
from .controller_workflow import _status_fields, plan_offline_request
from .offline_inputs import local_path
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
    plan = commands.add_parser("plan", help="Plan an offline controller migration; never execute changes.")
    plan.add_argument("--request", required=True, help="Versioned local controller workflow manifest.")
    plan.add_argument("--record", help="New protected local record file; never overwritten. May contain configuration.")
    plan.add_argument("--verify", help="Retained protected record to verify against current inputs.")
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

    if args.command == "plan":
        result = plan_offline_request(args.request, verify_record=args.verify)
        report = result.report
        status = result.exit_status
        if args.record is not None and result.record is not None:
            code = None
            created_path = None
            written = False
            cleanup_failed = False
            original_output_failure = None
            try:
                serialized = result.record_json()
                path = local_path(args.record, Path.cwd())
                with path.open("x", encoding="utf-8") as output:
                    created_path = path
                    output.write(serialized)
                written = True
            except ContractValidationError as error:
                codes = {issue.code for issue in error.result.issues}
                if "secret_value_not_allowed" in codes:
                    code, status = "secret_value_not_allowed", ExitStatus.CONTRACT_ERROR
                elif codes & {"integrity_mismatch", "record_unavailable"}:
                    code, status = "integrity_mismatch", ExitStatus.INTEGRITY_ERROR
                else:
                    code, status = "nonlocal_output", ExitStatus.INPUT_ERROR
            except FileExistsError:
                code, status = "output_exists", ExitStatus.INPUT_ERROR
            except (OSError, ValueError, UnicodeError):
                code, status = "output_unwritable", ExitStatus.INPUT_ERROR
            except Exception:
                code, status = "internal_error", ExitStatus.INTERNAL_ERROR
            finally:
                if created_path is not None and not written:
                    try:
                        created_path.unlink(missing_ok=True)
                    except OSError:
                        cleanup_failed = True
                    except Exception:
                        original_output_failure = code
                        code, status = "internal_error", ExitStatus.INTERNAL_ERROR
                        cleanup_failed = True
            if code is not None:
                report = {
                    **report, "workflow_result": "failed",
                    **_status_fields(status), "record_available": False,
                    "output_failure": code,
                    "validation_failures": [
                        *report["validation_failures"],
                        {"stage": "record_output", "code": code},
                    ],
                }
                if cleanup_failed:
                    report["output_cleanup_failure"] = "output_cleanup_failed"
                if original_output_failure is not None:
                    report["original_output_failure"] = original_output_failure
        print(json.dumps(report, allow_nan=False))
        return status

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
