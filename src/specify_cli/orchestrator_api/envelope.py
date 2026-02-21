"""Canonical JSON response envelope and policy metadata for orchestrator-api.

Responsibilities:
- Build a consistent envelope for all orchestrator-api command outputs.
- Parse and validate the --policy JSON required on run-affecting commands.
- Define banned flag constants used by the CI guardrail scan.
"""

from __future__ import annotations

import dataclasses
import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

CONTRACT_VERSION = "1.0.0"
MIN_PROVIDER_VERSION = "0.1.0"

# Banned flags: defined here as validation constants (NOT invoked anywhere).
# The CI scan excludes this file from the banned-flag grep.
BANNED_FLAGS: frozenset[str] = frozenset(
    [
        "--full-auto",
        "--yolo",
        "--dangerously-bypass-approvals-and-sandbox",
        "--dangerously-skip-permissions",
    ]
)

SECRET_PATTERN = re.compile(r"(token|secret|key|password|credential)", re.IGNORECASE)

_REQUIRED_POLICY_FIELDS = (
    "orchestrator_id",
    "orchestrator_version",
    "agent_family",
    "approval_mode",
    "sandbox_mode",
    "network_mode",
    "dangerous_flags",
)


def _new_correlation_id() -> str:
    return "corr-" + uuid.uuid4().hex


def make_envelope(
    command: str,
    success: bool,
    data: dict[str, Any],
    error_code: str | None = None,
) -> dict[str, Any]:
    """Build a canonical JSON response envelope.

    Args:
        command: Short command name (e.g. "contract-version").
        success: Whether the operation succeeded.
        data: Payload data dict (may be empty on failure).
        error_code: Machine-readable error code string (None on success).

    Returns:
        Envelope dict with 7 required keys.
    """
    return {
        "contract_version": CONTRACT_VERSION,
        "command": f"orchestrator-api.{command}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "correlation_id": _new_correlation_id(),
        "success": success,
        "error_code": error_code,
        "data": data,
    }


@dataclass
class PolicyMetadata:
    """Parsed and validated orchestrator policy metadata."""

    orchestrator_id: str
    orchestrator_version: str
    agent_family: str
    approval_mode: str
    sandbox_mode: str
    network_mode: str
    dangerous_flags: list[str]
    tool_restrictions: str | None = None


def parse_and_validate_policy(raw_json: str) -> PolicyMetadata:
    """Parse --policy JSON, validate structure, reject secret-like values.

    Args:
        raw_json: JSON string from the --policy CLI option.

    Returns:
        Validated PolicyMetadata dataclass.

    Raises:
        ValueError: If required fields are missing, types are wrong,
                    or secret-like values are detected.
    """
    import json

    try:
        data = json.loads(raw_json)
    except json.JSONDecodeError as exc:
        raise ValueError(f"--policy is not valid JSON: {exc}") from exc

    if not isinstance(data, dict):
        raise ValueError("--policy must be a JSON object")

    # Validate required fields are present
    for field_name in _REQUIRED_POLICY_FIELDS:
        if field_name not in data:
            raise ValueError(f"--policy missing required field: '{field_name}'")

    # Validate dangerous_flags is a list
    if not isinstance(data["dangerous_flags"], list):
        raise ValueError("--policy.dangerous_flags must be a JSON array")

    # Validate all values: reject secret-like strings
    for field_name, value in data.items():
        if isinstance(value, str) and SECRET_PATTERN.search(value):
            raise ValueError(
                f"--policy field '{field_name}' appears to contain a secret "
                f"(matched pattern: token|secret|key|password|credential). "
                f"Do not pass secrets via --policy."
            )

    return PolicyMetadata(
        orchestrator_id=str(data["orchestrator_id"]),
        orchestrator_version=str(data["orchestrator_version"]),
        agent_family=str(data["agent_family"]),
        approval_mode=str(data["approval_mode"]),
        sandbox_mode=str(data["sandbox_mode"]),
        network_mode=str(data["network_mode"]),
        dangerous_flags=list(data["dangerous_flags"]),
        tool_restrictions=data.get("tool_restrictions"),
    )


def policy_to_dict(policy: PolicyMetadata) -> dict[str, Any]:
    """Convert PolicyMetadata to a plain dict for storage in events."""
    return dataclasses.asdict(policy)


__all__ = [
    "CONTRACT_VERSION",
    "MIN_PROVIDER_VERSION",
    "BANNED_FLAGS",
    "make_envelope",
    "PolicyMetadata",
    "parse_and_validate_policy",
    "policy_to_dict",
]
