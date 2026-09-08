"""Status-owned, lock-held, tail-verified rollback truncate (spec-kitty #3960).

Why this module exists
----------------------
Mission ``fsm-write-path-integrity-01M1TZV6`` moved every status write behind
a status-owned, lock-held pipeline, but left its two *rollback* truncates
outside it (mission-review DRIFT-2): the coord fallback arm in
``coordination/status_transition.py`` and its twin in
``cli/commands/agent/workflow.py`` both truncated ``status.events.jsonl``
back to a pre-emit byte size without verifying that the rows they were about
to cut were the rows their own operation had just appended. A concurrent
writer that appended between the snapshot and the rollback lost its events to
the blind truncate.

This module closes that hole with one sanctioned helper pair:

* :func:`capture_events_tail_ids` -- the expectation record. Called while the
  operation's own writes are complete (post-emit, pre-commit), it reads the
  event ids now sitting in the log's tail.
* :func:`rollback_events_log_tail` -- the rollback. It re-acquires the same
  per-mission ``feature_status_lock`` the write pipeline uses (re-entrant for
  a caller that already holds it), re-reads the tail, verifies it still
  contains EXACTLY the expected rows, and only then truncates through the
  store's raw durability primitive :func:`specify_cli.status.store.truncate_events_log`.

Fail-safe direction: a tail that does not verify (foreign rows landed, a torn
row, or the log shrank below the pre-emit size) is NEVER cut. The helper logs
loudly and returns ``False`` -- stranding one already-emitted row is the
recoverable outcome; destroying another writer's durable events is not.

Residual window, stated plainly: between the emit's lock release and the
expectation capture there is no lock held on the workflow commit paths
(the capture runs at ``commit_workflow_change`` entry, immediately after the
emit returns in the same call stack). The verification compares the rollback-
time tail against the capture-time tail, so anything that lands *after* the
capture is caught and refused; only the microseconds between emit and capture
are trusted. The coord fallback arm has no such window at all -- its capture
runs inside the L1 hold that spans emit, commit and rollback.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Sequence
from pathlib import Path

from .locking import BOUNDED_STATUS_LOCK_TIMEOUT_SECONDS, FeatureStatusLockTimeoutError, feature_status_lock
from .store import EVENTS_FILENAME, truncate_events_log

__all__ = [
    "capture_events_tail_ids",
    "rollback_events_log_tail",
]

logger = logging.getLogger(__name__)


def _tail_rows(events_path: Path, pre_emit_event_size: int) -> list[dict[str, object]] | None:
    """Parse the log's ``[pre_emit_event_size:]`` region as whole JSONL rows.

    ``None`` means the region is not a sequence of complete JSON objects (a
    torn write, binary garbage, or a parse error) -- the caller treats that as
    "cannot verify", never as "verified empty". Blank lines are skipped: the
    atomic append primitive normalizes a missing trailing newline by inserting
    one, which can leave a leading blank line in the region.
    """
    try:
        data = events_path.read_bytes()
    except FileNotFoundError:
        return []
    except OSError as exc:
        logger.warning("Could not read %s for tail verification: %s", events_path, exc)
        return None
    if len(data) < pre_emit_event_size:
        return None
    tail = data[pre_emit_event_size:].decode("utf-8", errors="replace")
    rows: list[dict[str, object]] = []
    for line in tail.splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except ValueError:
            return None
        if not isinstance(row, dict):
            return None
        rows.append(row)
    return rows


def _row_event_ids(rows: Sequence[dict[str, object]]) -> list[str]:
    """The ``event_id`` of every row, in file order; non-string ids sort last."""
    return [str(row.get("event_id", "")) for row in rows]


def capture_events_tail_ids(events_path: Path, pre_emit_event_size: int) -> list[str] | None:
    """Read the event ids a just-finished emit left in the log's tail.

    The expectation record for :func:`rollback_events_log_tail`. Returns the
    ids in file order, or ``None`` when the tail cannot be parsed as whole
    rows (the rollback then degrades to structural verification only).
    """
    rows = _tail_rows(events_path, pre_emit_event_size)
    return None if rows is None else _row_event_ids(rows)


def rollback_events_log_tail(
    feature_dir: Path,
    *,
    repo_root: Path | None,
    pre_emit_event_size: int,
    expected_event_ids: Sequence[str] | None = None,
    timeout: float = BOUNDED_STATUS_LOCK_TIMEOUT_SECONDS,
) -> bool:
    """Tail-verified, lock-held rollback truncate of a mission's event log.

    Acquires the same per-mission status lock the write pipeline uses (same
    lock-root resolution as ``status.emit``, same ``feature_dir.name`` key;
    re-entrant for a caller already holding it), then verifies the log's tail
    beyond *pre_emit_event_size* before cutting it:

    * structurally -- every non-blank line in the cut region must be a whole
      JSON object (never a torn row);
    * when *expected_event_ids* is provided -- the tail's event ids must be
      exactly that multiset (never a concurrent writer's rows).

    Returns ``True`` when the log was (or already was) at/below the pre-emit
    size -- the rollback outcome every caller wants. Returns ``False`` when
    verification refused the cut (foreign rows, torn row, shrunken log) or the
    lock could not be acquired: the log is left untouched and the refusal is
    logged loudly. Refusal strands one already-emitted row; it never destroys
    another writer's durable events.
    """
    from specify_cli.workspace.root_resolver import resolve_status_lock_root  # noqa: PLC0415 -- cycle-safe lazy import, same seam status.emit uses

    lock_root = resolve_status_lock_root(feature_dir, repo_root)
    events_path = feature_dir / EVENTS_FILENAME
    try:
        size = events_path.stat().st_size
    except FileNotFoundError:
        return True  # nothing was ever appended; the pre-emit state already holds
    if size < pre_emit_event_size:
        # The log SHRANK below the pre-emit size: a whole-log rewrite (merge
        # driver, migration) landed in the window. Truncating to a larger size
        # would zero-extend the file; cutting anything would judge a log this
        # operation did not leave in that state. Refuse.
        logger.warning(
            "Refused rollback truncate of %s: log size %d is below the pre-emit "
            "size %d (the log was rewritten in the window); log left intact",
            events_path,
            size,
            pre_emit_event_size,
        )
        return False
    if size == pre_emit_event_size:
        return True  # idempotent no-op: the log is already at the pre-emit size
    try:
        with feature_status_lock(lock_root, feature_dir.name, timeout=timeout):
            rows = _tail_rows(events_path, pre_emit_event_size)
            if rows is None:
                logger.warning(
                    "Refused rollback truncate of %s: tail beyond %d bytes is not "
                    "whole JSONL rows (torn write or foreign content); log left intact",
                    events_path,
                    pre_emit_event_size,
                )
                return False
            if expected_event_ids is not None and sorted(_row_event_ids(rows)) != sorted(expected_event_ids):
                logger.warning(
                    "Refused rollback truncate of %s: tail holds %r, expected %r "
                    "(a concurrent writer's rows would be destroyed); log left intact",
                    events_path,
                    _row_event_ids(rows),
                    list(expected_event_ids),
                )
                return False
            truncate_events_log(feature_dir, pre_emit_event_size=pre_emit_event_size)
            return True
    except FeatureStatusLockTimeoutError as exc:
        logger.warning(
            "Refused rollback truncate of %s: could not acquire the mission status "
            "lock within %ss (%s); log left intact",
            events_path,
            timeout,
            exc,
        )
        return False
