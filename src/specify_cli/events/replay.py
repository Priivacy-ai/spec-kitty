"""Batch event replay to SaaS API with retry logic."""

import httpx
import time
import json
from typing import Dict
from datetime import datetime

from specify_cli.events.store import read_pending_events, get_queue_path
from specify_cli.events.models import EventQueueEntry


def replay_pending_events(
    mission_id: str,
    saas_api_url: str,
    session_token: str,
    max_batch_size: int = 100,
    max_retries: int = 3,
) -> Dict[str, list[str]]:
    """
    Replay pending events to SaaS in batches.

    Args:
        mission_id: Mission identifier
        saas_api_url: SaaS API base URL
        session_token: Session token for authentication
        max_batch_size: Maximum events per batch (default 100)
        max_retries: Maximum retry attempts per batch (default 3)

    Returns:
        Dictionary with "accepted" and "rejected" event_ids
    """
    pending = read_pending_events(mission_id)

    if not pending:
        return {"accepted": [], "rejected": []}

    # Batch events
    batches = [pending[i:i + max_batch_size] for i in range(0, len(pending), max_batch_size)]

    accepted_ids = []
    rejected_ids = []

    for batch in batches:
        result = _send_batch(batch, saas_api_url, session_token, max_retries)
        accepted_ids.extend(result["accepted"])
        rejected_ids.extend(result["rejected"])

    # Update queue: Mark accepted as "delivered", rejected as "failed"
    _update_queue_status(mission_id, accepted_ids, rejected_ids)

    return {"accepted": accepted_ids, "rejected": rejected_ids}


def _send_batch(
    batch: list[EventQueueEntry],
    saas_api_url: str,
    session_token: str,
    max_retries: int,
) -> Dict[str, list[str]]:
    """Send batch to SaaS with retry logic."""
    endpoint = f"{saas_api_url}/api/v1/events/batch/"
    headers = {
        "Authorization": f"Bearer {session_token}",
        "Content-Type": "application/json",
    }

    # Serialize events to dicts (use mode="json" to handle datetime serialization)
    payload = {"events": [entry.event.model_dump(mode="json") for entry in batch]}

    for attempt in range(max_retries):
        try:
            response = httpx.post(endpoint, json=payload, headers=headers, timeout=10.0)
            response.raise_for_status()
            return response.json()  # {"accepted": [...], "rejected": [...]}
        except (httpx.HTTPError, httpx.TimeoutException) as e:
            if attempt == max_retries - 1:
                # Final retry failed: Return all as rejected
                return {
                    "accepted": [],
                    "rejected": [entry.event.event_id for entry in batch],
                }

            # Exponential backoff: 1s, 2s, 4s
            time.sleep(2 ** attempt)

    return {"accepted": [], "rejected": []}


def _update_queue_status(mission_id: str, accepted_ids: list[str], rejected_ids: list[str]) -> None:
    """Update replay_status for events in queue."""
    queue_path = get_queue_path(mission_id)

    if not queue_path.exists():
        return

    # Read all events
    all_events = []
    with open(queue_path, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = EventQueueEntry.from_record(json.loads(line))
                all_events.append(entry)
            except (json.JSONDecodeError, ValueError):
                continue

    # Update status
    for entry in all_events:
        if entry.event.event_id in accepted_ids:
            entry.replay_status = "delivered"
        elif entry.event.event_id in rejected_ids:
            entry.replay_status = "failed"
            entry.retry_count += 1
            entry.last_retry_at = datetime.now()

    # Rewrite entire queue (atomic)
    temp_path = queue_path.with_suffix(".tmp")
    with open(temp_path, "w") as f:
        for entry in all_events:
            f.write(json.dumps(entry.to_record(), separators=(',', ':')) + "\n")

    temp_path.replace(queue_path)
