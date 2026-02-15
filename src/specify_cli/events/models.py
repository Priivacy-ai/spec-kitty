"""Event queue storage models with replay metadata."""

from dataclasses import dataclass
from datetime import datetime
from typing import Literal
import json
from spec_kitty_events.models import Event


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

    def to_jsonl_line(self) -> str:
        """
        Serialize to JSONL line (single line JSON).

        Includes both canonical event fields and replay metadata.
        """
        # Serialize Event to dict (implementation depends on Event model from 006)
        event_dict = self.event.model_dump(mode='json') if hasattr(self.event, 'model_dump') else self.event.__dict__

        # Add replay metadata with _ prefix (CLI-specific, not in canonical envelope)
        full_dict = {
            **event_dict,
            "_replay_status": self.replay_status,
            "_retry_count": self.retry_count,
            "_last_retry_at": self.last_retry_at.isoformat() if self.last_retry_at else None,
        }

        return json.dumps(full_dict, separators=(',', ':'))  # Compact JSON

    @classmethod
    def from_jsonl_line(cls, line: str) -> "EventQueueEntry":
        """
        Deserialize from JSONL line.

        Raises:
            ValueError: If line is malformed or missing required fields
        """
        data = json.loads(line)

        # Extract replay metadata
        replay_status = data.pop("_replay_status", "pending")
        retry_count = data.pop("_retry_count", 0)
        last_retry_str = data.pop("_last_retry_at", None)
        last_retry_at = datetime.fromisoformat(last_retry_str) if last_retry_str else None

        # Reconstruct Event (implementation depends on Event model from 006)
        event = Event(**data) if hasattr(Event, '__init__') else Event.model_validate(data)

        return cls(
            event=event,
            replay_status=replay_status,
            retry_count=retry_count,
            last_retry_at=last_retry_at,
        )
