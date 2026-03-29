"""AXL validator — validate Packet instances against their domain schemas.

Zero external dependencies. Uses only stdlib + axl.models + axl.schemas.
"""

from __future__ import annotations

from axl.models import Operation, Packet, ValidationResult, ValidationWarning, V3Packet
from axl.schemas import (
    SCHEMAS,
    VALID_ACTIONS,
    VALID_CURRENCIES,
    VALID_DIRECTIONS,
    VALID_INTENTS,
    domain_field_count,
)


def validate_field(value: str, field_type: str, field_name: str) -> tuple[bool, str | None]:
    """Validate a single field value against its expected type.

    Returns (is_valid, error_message_or_none).
    """
    # Null values are always valid
    if value in ("_", "∅", ""):
        return True, None

    if field_type == "str":
        # Any non-empty string is valid
        return True, None

    if field_type == "num":
        # Must parse as float; strip R, <=, >= prefixes first
        cleaned = value
        for prefix in ("R<=", "R>=", "R", "<=", ">="):
            if cleaned.startswith(prefix):
                cleaned = cleaned[len(prefix):]
                break
        # Strip trailing units (e.g. "4500ms", "500ms")
        stripped = cleaned.rstrip("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ%")
        if not stripped:
            return False, f"Field '{field_name}': cannot parse '{value}' as num"
        try:
            float(stripped)
            return True, None
        except ValueError:
            return False, f"Field '{field_name}': cannot parse '{value}' as num"

    if field_type == "pct":
        try:
            v = float(value)
        except ValueError:
            return False, f"Field '{field_name}': '{value}' is not a valid pct (must be float 0-1)"
        if not (0.0 <= v <= 1.0):
            return False, f"Field '{field_name}': pct {v} out of range 0-1"
        return True, None

    if field_type == "dir":
        if value not in VALID_DIRECTIONS:
            return False, f"Field '{field_name}': '{value}' is not a valid direction"
        return True, None

    if field_type == "action":
        if value not in VALID_ACTIONS:
            return False, f"Field '{field_name}': '{value}' is not a valid action"
        return True, None

    if field_type == "intent":
        if value not in VALID_INTENTS:
            return False, f"Field '{field_name}': '{value}' is not a valid intent"
        return True, None

    if field_type == "currency":
        if value not in VALID_CURRENCIES:
            return False, f"Field '{field_name}': '{value}' is not a valid currency"
        return True, None

    # Unknown field type — accept it
    return True, None


def validate(packet: Packet) -> ValidationResult:
    """Validate a Packet against its domain schema.

    Returns a ValidationResult with errors and warnings.
    """
    errors: list[ValidationWarning] = []
    warnings: list[ValidationWarning] = []

    domain = packet.body.domain

    # Check domain exists
    if domain not in SCHEMAS:
        errors.append(ValidationWarning(
            field_name="domain",
            message=f"Unknown domain: '{domain}'",
            severity="error",
        ))
        return ValidationResult(valid=False, warnings=warnings, errors=errors)

    # Check tier range
    tier = packet.body.tier
    if not (1 <= tier <= 5):
        errors.append(ValidationWarning(
            field_name="tier",
            message=f"Tier {tier} out of range 1-5",
            severity="error",
        ))

    schema = SCHEMAS[domain]
    expected_count = domain_field_count(domain)
    actual_count = len(packet.body.fields)

    # Field count check — warn, don't error
    if actual_count != expected_count:
        warnings.append(ValidationWarning(
            field_name="field_count",
            message=f"Expected {expected_count} fields for {domain}, got {actual_count}",
            severity="warning",
        ))

    # Validate each field against its schema type
    for i, field_val in enumerate(packet.body.fields):
        if i >= len(schema):
            # Extra field beyond schema — just warn
            warnings.append(ValidationWarning(
                field_name=f"field_{i}",
                message=f"Extra field at position {i}: '{field_val}'",
                severity="warning",
            ))
            continue

        field_def = schema[i]
        ok, msg = validate_field(field_val, field_def.field_type, field_def.name)
        if not ok:
            errors.append(ValidationWarning(
                field_name=field_def.name,
                message=msg or f"Invalid value for {field_def.name}",
                severity="error",
            ))

    valid = len(errors) == 0
    return ValidationResult(valid=valid, warnings=warnings, errors=errors)


# ─── v3 validator ──────────────────────────────────────────

_REQUIRES_RE = frozenset({Operation.CON, Operation.MRG, Operation.SEK, Operation.YLD})


def validate_v3(packet: V3Packet) -> list[str]:
    """Validate a V3Packet. Returns a list of error strings (empty = valid)."""
    errors: list[str] = []

    # CC range
    if not (0 <= packet.confidence <= 99):
        errors.append(f"Confidence {packet.confidence} out of range 0-99")

    # Operations that require RE: in ARG1 or ARG2
    if packet.operation in _REQUIRES_RE:
        has_re = False
        for field in (packet.arg1, packet.arg2):
            if field and (field.startswith("RE:") or "RE:" in field):
                has_re = True
                break
        if not has_re:
            if packet.operation == Operation.SEK:
                # SEK can also use <- evidence
                if not packet.arg1 or not packet.arg1.startswith("<-"):
                    errors.append(
                        f"{packet.operation.value} requires ARG1 with RE:target "
                        f"(got: {packet.arg1!r})"
                    )
            else:
                errors.append(
                    f"{packet.operation.value} requires RE:target in ARG1 or ARG2 "
                    f"(got arg1={packet.arg1!r}, arg2={packet.arg2!r})"
                )

    # YLD must state from:->to:
    if packet.operation == Operation.YLD:
        has_transition = False
        for field in (packet.arg1, packet.arg2):
            if field and "from:" in field and "->" in field:
                has_transition = True
                break
        # Also accept the top-level pattern: from:X->Y as arg1 or arg2
        if not has_transition:
            # Check if it's in the format from:old->new anywhere in the packet
            for field in (packet.arg1, packet.arg2):
                if field and "->" in field:
                    has_transition = True
                    break
        if not has_transition:
            errors.append("YLD must state from:old_belief->new_belief")

    # PRD should have evidence
    if packet.operation == Operation.PRD:
        has_evidence = False
        for field in (packet.arg1, packet.arg2):
            if field and (field.startswith("<-") or field.startswith("RE:")):
                has_evidence = True
                break
        if not has_evidence:
            errors.append("PRD should cite evidence via <- in ARG1 or ARG2")

    # Temporal must be valid
    valid_temporals = {"NOW", "1H", "4H", "1D", "1W", "1M", "HIST"}
    if packet.temporal not in valid_temporals:
        errors.append(f"Unknown temporal: {packet.temporal!r}")

    return errors
