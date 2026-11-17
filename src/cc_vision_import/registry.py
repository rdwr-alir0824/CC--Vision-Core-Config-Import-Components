from collections.abc import Callable
from dataclasses import dataclass

from .artifacts import validate_artifact
from .contracts import ValidationResult
from .profiles import validate_destination_profile, validate_source_profile
from .plans import validate_plan
from .validation import validate_synthetic


@dataclass(frozen=True)
class ModuleDefinition:
    name: str
    description: str
    validate: Callable[[object], ValidationResult]


MODULES: tuple[ModuleDefinition, ...] = (
    ModuleDefinition(
        name="synthetic",
        description="Offline synthetic fixture validation; no product API compatibility.",
        validate=validate_synthetic,
    ),
    ModuleDefinition(
        name="source-profile",
        description="Offline source profile contract; no connection or compatibility check.",
        validate=validate_source_profile,
    ),
    ModuleDefinition(
        name="destination-profile",
        description="Offline destination profile contract; no connection or compatibility check.",
        validate=validate_destination_profile,
    ),
    ModuleDefinition(
        name="artifact",
        description="Offline versioned artifact contract; no product schema or migration execution.",
        validate=validate_artifact,
    ),
    ModuleDefinition(
        name="plan",
        description="Offline candidate plan integrity and blocking diagnostics; no preflight or execution.",
        validate=validate_plan,
    ),
)


def get_module(name: str) -> ModuleDefinition | None:
    return next((module for module in MODULES if module.name == name), None)
