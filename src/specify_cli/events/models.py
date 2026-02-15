"""Event queue storage models with replay metadata."""

from dataclasses import dataclass
from datetime import datetime
from typing import Literal
import json
from specify_cli.spec_kitty_events.models import Event


@dataclass
class EventQueueEntry:
    """
    Event queue entry with replay metadata.

    The event field contains the canonical Event from spec-kitty-events library.
    Metadata fields (replay_status, retry_count, last_retry_at) are CLI-specific
    and not part of the canonical envelope.
    """
    event: Event
    replay_status: Literal["pending", "delivered", "failed"]
    retry_count: int = 0
    last_retry_at: datetime | None = None

    def to_record(self) -> dict[str, object]:
        """
        Serialize to a queue record payload.

        Includes both canonical event fields and replay metadata.
        """
        # Serialize Event to dict (implementation depends on Event model from 006)
        event_dict = self.event.model_dump(mode='json') if hasattr(self.event, 'model_dump') else self.event.__dict__

        # Add replay metadata with _ prefix (CLI-specific, not in canonical envelope)
        full_dict: dict[str, object] = {
            **event_dict,
            "_replay_status": self.replay_status,
            "_retry_count": self.retry_count,
            "_last_retry_at": self.last_retry_at.isoformat() if self.last_retry_at else None,
        }

        return full_dict

    @classmethod
    def from_record(cls, data: dict[str, object]) -> "EventQueueEntry":
        """
        Deserialize from queue record payload.

        Raises:
            ValueError: If line is malformed or missing required fields
        """
        from typing import cast

        # Extract replay metadata (make a copy to avoid mutating input)
        data_copy = dict(data)
        replay_status_val = data_copy.pop("_replay_status", "pending")

        # Validate and cast replay_status
        if not isinstance(replay_status_val, str) or replay_status_val not in ("pending", "delivered", "failed"):
            replay_status: Literal["pending", "delivered", "failed"] = "pending"
        else:
            replay_status = cast(Literal["pending", "delivered", "failed"], replay_status_val)

        # Cast retry_count
        retry_count_val = data_copy.pop("_retry_count", 0)
        retry_count = int(retry_count_val) if isinstance(retry_count_val, (int, str)) else 0

        # Cast last_retry_at
        last_retry_str = data_copy.pop("_last_retry_at", None)
        last_retry_at = datetime.fromisoformat(str(last_retry_str)) if last_retry_str else None

        # Reconstruct Event (implementation depends on Event model from 006)
        event = Event(**data_copy) if hasattr(Event, '__init__') else Event.model_validate(data_copy)

        return cls(
            event=event,
            replay_status=replay_status,
            retry_count=retry_count,
            last_retry_at=last_retry_at,
        )
