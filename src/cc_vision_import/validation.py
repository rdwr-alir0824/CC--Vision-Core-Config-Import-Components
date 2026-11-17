from .contracts import ValidationIssue, ValidationResult


def validate_synthetic(payload: object) -> ValidationResult:
    """Validate a synthetic fixture, not a Vision or Cyber Controller artifact."""
    issues: list[ValidationIssue] = []
    if not isinstance(payload, dict):
        return ValidationResult(
            module="synthetic",
            status="invalid",
            issues=(
                ValidationIssue("invalid_type", "$", "Expected a JSON object."),
            ),
        )

    if payload.keys() - {"schema_version", "module", "objects"}:
        issues.append(
            ValidationIssue(
                "unknown_fields", "$", "Only schema_version, module, and objects are allowed."
            )
        )
    version = payload.get("schema_version")
    if type(version) is not int or version != 1:
        issues.append(
            ValidationIssue(
                "unsupported_schema", "$.schema_version", "Expected integer schema version 1."
            )
        )
    if payload.get("module") != "synthetic":
        issues.append(
            ValidationIssue(
                "module_mismatch", "$.module", "Expected the synthetic module."
            )
        )

    objects = payload.get("objects")
    if not isinstance(objects, list):
        issues.append(
            ValidationIssue("invalid_type", "$.objects", "Expected an array of objects.")
        )
        return ValidationResult("synthetic", "invalid", issues=tuple(issues))

    seen_ids: set[str] = set()
    for index, item in enumerate(objects):
        path = f"$.objects[{index}]"
        if not isinstance(item, dict):
            issues.append(
                ValidationIssue("invalid_type", path, "Expected an object with id and name.")
            )
            continue
        if item.keys() - {"id", "name"}:
            issues.append(
                ValidationIssue(
                    "unknown_fields", path, "Only id and name are allowed."
                )
            )
        for field in ("id", "name"):
            value = item.get(field)
            if not isinstance(value, str) or not value.strip() or value != value.strip():
                issues.append(
                    ValidationIssue(
                        "invalid_value",
                        f"{path}.{field}",
                        "Expected a nonempty string without surrounding whitespace.",
                    )
                )
            elif field == "id":
                if value in seen_ids:
                    issues.append(
                        ValidationIssue(
                            "duplicate_id", f"{path}.id", "Object IDs must be unique."
                        )
                    )
                seen_ids.add(value)

    return ValidationResult(
        module="synthetic",
        status="invalid" if issues else "valid",
        object_count=len(objects),
        issues=tuple(issues),
    )
