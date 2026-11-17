from dataclasses import dataclass
from enum import IntEnum
from typing import Literal


type ProductName = Literal["vision", "cyber-controller"]
type JsonValue = None | bool | int | float | str | list[JsonValue] | dict[str, JsonValue]


class ExitStatus(IntEnum):
    SUCCESS = 0
    VALIDATION_FAILED = 1
    USAGE_ERROR = 2
    INPUT_ERROR = 3


@dataclass(frozen=True)
class ValidationIssue:
    code: str
    path: str
    message: str


@dataclass(frozen=True)
class ValidationResult:
    module: str
    status: Literal["valid", "invalid", "error"]
    object_count: int = 0
    issues: tuple[ValidationIssue, ...] = ()


class ContractValidationError(ValueError):
    def __init__(self, result: ValidationResult) -> None:
        super().__init__("Offline contract validation failed.")
        self.result = result
