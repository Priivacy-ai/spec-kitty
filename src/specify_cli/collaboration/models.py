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
    - mission_run_id: Mission run correlation ULID (SaaS-assigned)
    - participant_id: SaaS-minted ULID (26 chars, bound to auth principal)
    - role: Join role label (validated by SaaS)
    - joined_at: ISO timestamp when joined (immutable)
    - last_activity_at: ISO timestamp of last command (updated on events)
    - drive_intent: Active execution intent (active|inactive)
    - focus: Current focus target (none, wp:<id>, step:<id>)
    """
    mission_id: str
    mission_run_id: str
    participant_id: str  # ULID, 26 chars
    role: str
    joined_at: datetime
    last_activity_at: datetime
    drive_intent: Literal["active", "inactive"] = "inactive"
    focus: str | None = None  # none, wp:<id>, step:<id>
    session_token: str = ""  # SaaS API token from join response
    saas_api_url: str = ""  # SaaS API base URL

    def to_dict(self) -> dict[str, object]:
        """Serialize to JSON-compatible dict."""
        return {
            "mission_id": self.mission_id,
            "mission_run_id": self.mission_run_id,
            "participant_id": self.participant_id,
            "role": self.role,
            "joined_at": self.joined_at.isoformat(),
            "last_activity_at": self.last_activity_at.isoformat(),
            "drive_intent": self.drive_intent,
            "focus": self.focus,
            "session_token": self.session_token,
            "saas_api_url": self.saas_api_url,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "SessionState":
        """Deserialize from JSON dict."""
        return cls(
            mission_id=str(data["mission_id"]),
            mission_run_id=str(data["mission_run_id"]),
            participant_id=str(data["participant_id"]),
            role=str(data["role"]),
            joined_at=datetime.fromisoformat(str(data["joined_at"])),
            last_activity_at=datetime.fromisoformat(str(data["last_activity_at"])),
            drive_intent=str(data.get("drive_intent", "inactive")),  # type: ignore[arg-type]
            focus=str(data["focus"]) if data.get("focus") else None,
            session_token=str(data.get("session_token", "")),
            saas_api_url=str(data.get("saas_api_url", "")),
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

    def to_dict(self) -> dict[str, object]:
        """Serialize to JSON-compatible dict."""
        return {
            "active_mission_id": self.active_mission_id,
            "last_switched_at": self.last_switched_at.isoformat() if self.last_switched_at else None,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "ActiveMissionPointer":
        """Deserialize from JSON dict."""
        last_switched_str = data.get("last_switched_at")
        return cls(
            active_mission_id=str(data["active_mission_id"]) if data.get("active_mission_id") else None,
            last_switched_at=datetime.fromisoformat(str(last_switched_str)) if last_switched_str else None,
        )
