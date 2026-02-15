"""Session state and participation models."""

from dataclasses import dataclass
from datetime import datetime
from typing import Literal


@dataclass
class SessionState:
    """
    Per-mission CLI session state (local cache of participant identity).

    Stored in: ~/.spec-kitty/missions/<mission_id>/session.json
    File permissions: 0600 (owner read/write only)

    Fields:
    - mission_id: Mission identifier (SaaS-assigned)
    - participant_id: SaaS-minted ULID (26 chars, bound to auth principal)
    - role: Join role (developer, reviewer, observer, stakeholder)
    - joined_at: ISO timestamp when joined (immutable)
    - last_activity_at: ISO timestamp of last command (updated on events)
    - drive_intent: Active execution intent (active|inactive)
    - focus: Current focus target (none, wp:<id>, step:<id>)
    """
    mission_id: str
    participant_id: str  # ULID, 26 chars
    role: Literal["developer", "reviewer", "observer", "stakeholder"]
    joined_at: datetime
    last_activity_at: datetime
    drive_intent: Literal["active", "inactive"] = "inactive"
    focus: str | None = None  # none, wp:<id>, step:<id>

    def get_capabilities(self) -> dict[str, bool]:
        """
        Derive capabilities from role (capability matrix, S1/M1 fixed).

        Returns:
            Dictionary with 6 capabilities:
            - can_focus, can_drive, can_execute, can_ack_warning, can_comment, can_decide
        """
        # Capability matrix (see data-model.md)
        matrix = {
            "developer": {
                "can_focus": True,
                "can_drive": True,
                "can_execute": True,
                "can_ack_warning": True,
                "can_comment": True,
                "can_decide": True,
            },
            "reviewer": {
                "can_focus": True,
                "can_drive": True,
                "can_execute": True,
                "can_ack_warning": True,
                "can_comment": True,
                "can_decide": True,
            },
            "observer": {
                "can_focus": True,
                "can_drive": False,
                "can_execute": False,
                "can_ack_warning": False,
                "can_comment": True,
                "can_decide": False,
            },
            "stakeholder": {
                "can_focus": False,
                "can_drive": False,
                "can_execute": False,
                "can_ack_warning": False,
                "can_comment": True,
                "can_decide": True,
            },
        }
        return matrix[self.role]

    def to_dict(self) -> dict:
        """Serialize to JSON-compatible dict."""
        return {
            "mission_id": self.mission_id,
            "participant_id": self.participant_id,
            "role": self.role,
            "joined_at": self.joined_at.isoformat(),
            "last_activity_at": self.last_activity_at.isoformat(),
            "drive_intent": self.drive_intent,
            "focus": self.focus,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SessionState":
        """Deserialize from JSON dict."""
        return cls(
            mission_id=data["mission_id"],
            participant_id=data["participant_id"],
            role=data["role"],
            joined_at=datetime.fromisoformat(data["joined_at"]),
            last_activity_at=datetime.fromisoformat(data["last_activity_at"]),
            drive_intent=data.get("drive_intent", "inactive"),
            focus=data.get("focus"),
        )


@dataclass
class ActiveMissionPointer:
    """
    CLI active mission pointer (fast lookup for commands omitting --mission flag).

    Stored in: ~/.spec-kitty/session.json

    S1/M1 Scope: Single active mission at a time.
    """
    active_mission_id: str | None = None
    last_switched_at: datetime | None = None

    def to_dict(self) -> dict:
        """Serialize to JSON-compatible dict."""
        return {
            "active_mission_id": self.active_mission_id,
            "last_switched_at": self.last_switched_at.isoformat() if self.last_switched_at else None,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ActiveMissionPointer":
        """Deserialize from JSON dict."""
        last_switched_str = data.get("last_switched_at")
        return cls(
            active_mission_id=data.get("active_mission_id"),
            last_switched_at=datetime.fromisoformat(last_switched_str) if last_switched_str else None,
        )
