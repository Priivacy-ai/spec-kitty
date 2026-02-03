"""Batch sync for offline queue replay via REST endpoint"""
import gzip
import json
from pathlib import Path
from typing import Optional
import requests

from .queue import OfflineQueue


class BatchSyncResult:
    """Result of a batch sync operation"""

    def __init__(self):
        self.total_events = 0
        self.synced_count = 0
        self.duplicate_count = 0
        self.error_count = 0
        self.error_messages: list[str] = []
        self.synced_ids: list[str] = []
        self.failed_ids: list[str] = []

    @property
    def success_count(self) -> int:
        """Events successfully processed (synced or duplicate)"""
        return self.synced_count + self.duplicate_count


def batch_sync(
    queue: OfflineQueue,
    auth_token: str,
    server_url: str,
    limit: int = 1000,
    show_progress: bool = True
) -> BatchSyncResult:
    """
    Sync offline queue to server via batch endpoint.

    Drains the offline queue and uploads events in a single batch request
    with gzip compression. Successfully synced events are removed from the queue.

    Args:
        queue: OfflineQueue instance containing events to sync
        auth_token: JWT access token for authentication
        server_url: Server base URL (e.g., https://spec-kitty-dev.fly.dev)
        limit: Maximum number of events to sync (default 1000)
        show_progress: Whether to print progress messages (default True)

    Returns:
        BatchSyncResult with sync statistics and status

    Example:
        >>> queue = OfflineQueue()
        >>> result = batch_sync(queue, token, 'https://spec-kitty-dev.fly.dev')
        >>> print(f"Synced {result.synced_count} events")
    """
    result = BatchSyncResult()

    events = queue.drain_queue(limit=limit)
    result.total_events = len(events)

    if not events:
        if show_progress:
            print("No events to sync")
        return result

    if show_progress:
        print(f"Syncing {len(events)} events... (0/{len(events)})")

    # Compress payload with gzip
    payload = json.dumps({'events': events}).encode('utf-8')
    compressed = gzip.compress(payload)

    # POST to batch endpoint
    headers = {
        'Authorization': f'Bearer {auth_token}',
        'Content-Encoding': 'gzip',
        'Content-Type': 'application/json'
    }

    try:
        response = requests.post(
            f"{server_url.rstrip('/')}/api/v1/events/batch/",
            data=compressed,
            headers=headers,
            timeout=60  # 60s timeout for batch processing
        )

        if response.status_code == 200:
            response_data = response.json()
            results = response_data.get('results', [])

            # Parse per-event status
            for event_result in results:
                event_id = event_result.get('event_id')
                status = event_result.get('status')

                if status == 'success':
                    result.synced_count += 1
                    result.synced_ids.append(event_id)
                elif status == 'duplicate':
                    result.duplicate_count += 1
                    result.synced_ids.append(event_id)
                else:
                    result.error_count += 1
                    result.failed_ids.append(event_id)
                    error_msg = event_result.get('error_message', 'Unknown error')
                    result.error_messages.append(f"{event_id}: {error_msg}")

            # Delete synced events from queue
            if result.synced_ids:
                queue.mark_synced(result.synced_ids)

            # Increment retry count for failed events
            if result.failed_ids:
                queue.increment_retry(result.failed_ids)

            if show_progress:
                print(f"Syncing {len(events)} events... ({result.success_count}/{len(events)} complete)")
                if result.error_count > 0:
                    print(f"  {result.synced_count} synced, {result.duplicate_count} duplicates, {result.error_count} errors")
                else:
                    print(f"Synced {result.synced_count}/{len(events)} events")
                    if result.duplicate_count > 0:
                        print(f"  ({result.duplicate_count} duplicates skipped)")

        elif response.status_code == 401:
            if show_progress:
                print("Batch sync failed: Authentication failed (401)")
            result.error_messages.append("Authentication failed")
            result.error_count = len(events)
            result.failed_ids = [e.get('event_id') for e in events]
            queue.increment_retry(result.failed_ids)

        elif response.status_code == 400:
            error_detail = response.json().get('error', 'Bad request')
            if show_progress:
                print(f"Batch sync failed: {error_detail}")
            result.error_messages.append(error_detail)
            result.error_count = len(events)
            result.failed_ids = [e.get('event_id') for e in events]
            queue.increment_retry(result.failed_ids)

        else:
            if show_progress:
                print(f"Batch sync failed: HTTP {response.status_code}")
            result.error_messages.append(f"HTTP {response.status_code}")
            result.error_count = len(events)
            result.failed_ids = [e.get('event_id') for e in events]
            queue.increment_retry(result.failed_ids)

    except requests.exceptions.Timeout:
        if show_progress:
            print("Batch sync failed: Request timeout")
        result.error_messages.append("Request timeout")
        result.error_count = len(events)
        result.failed_ids = [e.get('event_id') for e in events]
        queue.increment_retry(result.failed_ids)

    except requests.exceptions.ConnectionError as e:
        if show_progress:
            print(f"Batch sync failed: Connection error - {e}")
        result.error_messages.append(f"Connection error: {e}")
        result.error_count = len(events)
        result.failed_ids = [e.get('event_id') for e in events]
        queue.increment_retry(result.failed_ids)

    except Exception as e:
        if show_progress:
            print(f"Batch sync failed: {e}")
        result.error_messages.append(str(e))
        result.error_count = len(events)
        result.failed_ids = [e.get('event_id') for e in events]
        queue.increment_retry(result.failed_ids)

    return result


def sync_all_queued_events(
    queue: OfflineQueue,
    auth_token: str,
    server_url: str,
    batch_size: int = 1000,
    show_progress: bool = True
) -> BatchSyncResult:
    """
    Sync all events from the queue in batches.

    Continues syncing in batches until queue is empty or all remaining events
    have exceeded retry limit.

    Args:
        queue: OfflineQueue instance
        auth_token: JWT access token
        server_url: Server base URL
        batch_size: Events per batch (default 1000)
        show_progress: Whether to print progress

    Returns:
        Aggregated BatchSyncResult across all batches
    """
    total_result = BatchSyncResult()
    batch_num = 0

    while queue.size() > 0:
        batch_num += 1
        if show_progress:
            print(f"\n--- Batch {batch_num} ---")

        result = batch_sync(
            queue=queue,
            auth_token=auth_token,
            server_url=server_url,
            limit=batch_size,
            show_progress=show_progress
        )

        total_result.total_events += result.total_events
        total_result.synced_count += result.synced_count
        total_result.duplicate_count += result.duplicate_count
        total_result.error_count += result.error_count
        total_result.synced_ids.extend(result.synced_ids)
        total_result.failed_ids.extend(result.failed_ids)
        total_result.error_messages.extend(result.error_messages)

        # Stop if no progress made (all errors)
        if result.success_count == 0 and result.error_count > 0:
            if show_progress:
                print("Stopping: No events successfully synced in this batch")
            break

    if show_progress:
        print(f"\n=== Sync Complete ===")
        print(f"Total: {total_result.synced_count} synced, {total_result.duplicate_count} duplicates, {total_result.error_count} errors")
        if queue.size() > 0:
            print(f"Remaining in queue: {queue.size()} events")

    return total_result
