"""Policy audit log — separate from the lane-transition event stream.

Policy overrides (risk, commit guard, merge gate) are feature-level or
merge-level actions that do not map to WP lane transitions. They are
stored in a dedicated append-only JSONL file at:

    kitty-specs/{feature_slug}/policy-audit.jsonl

This log is read-only evidence for governance. It does not drive state.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import ulid as _ulid_mod

AUDIT_FILENAME = "policy-audit.jsonl"


def _generate_ulid() -> str:
    if hasattr(_ulid_mod, "new"):
        return _ulid_mod.new().str  # type: ignore[attr-defined]
    return str(_ulid_mod.ULID())


@dataclass(frozen=True)
class PolicyAuditEvent:
    """A single policy audit event."""

    event_id: str
    event_type: str  # "risk_override" | "commit_guard_override" | "merge_gate_override"
    feature_slug: str
    actor: str
    reason: str
    details: dict[str, Any]
    at: str  # ISO 8601

    def to_json_line(self) -> str:
        return json.dumps(asdict(self), sort_keys=True)

    @classmethod
    def from_json_line(cls, line: str) -> PolicyAuditEvent:
        data = json.loads(line)
        return cls(**data)


def create_audit_event(
    event_type: str,
    feature_slug: str,
    actor: str,
    reason: str,
    details: dict[str, Any] | None = None,
) -> PolicyAuditEvent:
    """Create a new PolicyAuditEvent with generated ID and timestamp."""
    return PolicyAuditEvent(
        event_id=_generate_ulid(),
        event_type=event_type,
        feature_slug=feature_slug,
        actor=actor,
        reason=reason,
        details=details or {},
        at=datetime.now(timezone.utc).isoformat(),
    )


def append_audit_event(feature_dir: Path, event: PolicyAuditEvent) -> None:
    """Append a policy audit event to the feature's audit log."""
    audit_path = feature_dir / AUDIT_FILENAME
    with open(audit_path, "a", encoding="utf-8") as f:
        f.write(event.to_json_line() + "\n")


def read_audit_events(feature_dir: Path) -> list[PolicyAuditEvent]:
    """Read all policy audit events for a feature."""
    audit_path = feature_dir / AUDIT_FILENAME
    if not audit_path.exists():
        return []
    events: list[PolicyAuditEvent] = []
    for line in audit_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            events.append(PolicyAuditEvent.from_json_line(line))
    return events
