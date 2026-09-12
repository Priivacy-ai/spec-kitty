"""Runtime compatibility checks for outbound payloads."""

from __future__ import annotations

import json
from dataclasses import dataclass
from importlib.resources import files
from typing import Any, cast


Payload = dict[str, Any]
ContractNode = dict[str, Any]

_CONTRACT_CACHE: ContractNode | None = None


@dataclass(slots=True)
class ContractViolationError(Exception):
    """Raised when an outbound payload violates the vendored contract."""

    field: str
    context: str
    reason: str

    def __str__(self) -> str:
        return f"ContractViolationError: {self.context}: {self.reason} (field={self.field})"


def _load_contract() -> ContractNode:
    global _CONTRACT_CACHE

    if _CONTRACT_CACHE is None:
        contract_path = files("specify_cli.core").joinpath("upstream_contract.json")
        _CONTRACT_CACHE = cast(ContractNode, json.loads(contract_path.read_text(encoding="utf-8")))

    return _CONTRACT_CACHE


def _raise_violation(context: str, field: str, reason: str) -> None:
    raise ContractViolationError(field=field, context=context, reason=reason)


def _require_fields(payload: Payload, context: str, field_names: list[str]) -> None:
    for field_name in field_names:
        if field_name not in payload:
            _raise_violation(context, field_name, f"required field '{field_name}' missing in {context} payload")


def _forbid_fields(payload: Payload, context: str, field_names: list[str]) -> None:
    for field_name in field_names:
        if field_name in payload:
            _raise_violation(context, field_name, f"forbidden field '{field_name}' present in {context} payload")


def _validate_constraint(payload: Payload, context: str, field_name: str, constraint: ContractNode) -> None:
    if field_name not in payload:
        return

    value = payload[field_name]

    allowed = constraint.get("allowed")
    if isinstance(allowed, list) and value not in allowed:
        _raise_violation(context, field_name, f"field '{field_name}' must be one of {allowed!r}, got {value!r}")

    forbidden = constraint.get("forbidden")
    if isinstance(forbidden, list) and value in forbidden:
        _raise_violation(context, field_name, f"field '{field_name}' value {value!r} is forbidden in {context}")

    expected_value = constraint.get("value")
    if expected_value is not None and value != expected_value:
        _raise_violation(context, field_name, f"field '{field_name}' must equal {expected_value!r}, got {value!r}")


def _validate_section(payload: Payload, context: str, section: ContractNode) -> None:
    for key, value in section.items():
        if key == "required_fields" and isinstance(value, list):
            _require_fields(payload, context, cast(list[str], value))
            continue

        if key == "forbidden_fields" and isinstance(value, list):
            _forbid_fields(payload, context, cast(list[str], value))
            continue

        if key.startswith("required_") and key.endswith("_fields") and isinstance(value, list):
            _require_fields(payload, context, cast(list[str], value))
            continue

        if key.startswith("forbidden_") and key.endswith("_fields") and isinstance(value, list):
            _forbid_fields(payload, context, cast(list[str], value))
            continue

        if key.startswith("allowed_") and isinstance(value, list):
            field_name = key.removeprefix("allowed_")
            _validate_constraint(payload, context, field_name, {"allowed": value})
            continue

        if key.startswith("forbidden_") and isinstance(value, list):
            field_name = key.removeprefix("forbidden_")
            _validate_constraint(payload, context, field_name, {"forbidden": value})
            continue

        if isinstance(value, dict):
            # Nested sub-section (e.g., payload.mission_scoped) —
            # recursively validate its rules against the same payload.
            if "required_fields" in value or "forbidden_fields" in value:
                _validate_section(payload, f"{context}.{key}", value)
            else:
                _validate_constraint(payload, context, key, value)


def validate_outbound_payload(payload: Payload, context: str) -> None:
    """Validate an outbound payload against the vendored upstream contract."""

    section = _load_contract().get(context)
    if not isinstance(section, dict):
        return

    _validate_section(payload, context, cast(ContractNode, section))


def is_allowed_error_code(context: str, error_code: str) -> bool:
    """True if *error_code* is in *context*'s ``allowed_error_codes`` list.

    PR-CONTRACT-002: unlike :func:`validate_outbound_payload` (which checks
    STATIC field shape at emission time), this is a runtime membership check
    against the SAME vendored allow-list, for callers that propagate a
    dynamically-typed exception's error code (e.g. ``exc.code.value`` from a
    ``DecisionError``) rather than a literal string -- the one shape
    ``tests/contract/test_orchestrator_api.py::TestAllowedErrorCodes``'s
    static-regex check over literal ``_fail(...)`` call sites cannot see.
    Absent/malformed ``allowed_error_codes`` fails closed (``False``) --
    never silently trusts an error code because the contract section was
    missing.
    """
    section = _load_contract().get(context)
    if not isinstance(section, dict):
        return False
    allowed = section.get("allowed_error_codes")
    if not isinstance(allowed, list):
        return False
    return error_code in allowed
