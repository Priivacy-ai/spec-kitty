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

This module closes that hole with one sanctioned helper pair, plus the
ownership window that records what an operation appended:

* :func:`owned_emission_window` -- the ownership record's frame. A context
  manager that holds the per-mission ``feature_status_lock`` across an
  operation's whole snapshot -> emit window and captures the tail's event
  ids at exit, still inside the same hold.
* :func:`capture_events_tail_ids` -- the expectation read. Called on the
  log's tail while the lock is held (the window calls it; the coord fallback
  arm reads its own ``EventStream`` instead).
* :func:`rollback_events_log_tail` -- the log-only rollback. It acquires the
  same per-mission ``feature_status_lock`` the write pipeline uses (re-entrant for
  a caller that already holds it) BEFORE looking at the log, re-reads the tail,
  verifies it still contains EXACTLY the expected rows, and only then truncates
  through the store's raw durability primitive :func:`specify_cli.status.store.truncate_events_log`.
* :func:`rollback_status_artifacts` -- BOTH artifacts in ONE lock hold. The
  operator acceptance follow-up (spec-kitty #4087, 2026-09-08) demonstrated a
  schedule where the log half verified and truncated under the lock, the lock
  released, a second writer appended/materialized/Git-committed both artifacts,
  and the derived ``status.json`` restore then ran UNLOCKED and clobbered the
  acknowledged newer snapshot. The rollback decision, the truncation (or its
  refusal/no-op), and the derived-snapshot restore therefore share ONE
  ``feature_status_lock`` hold here -- there is no seam between "the log half
  verified" and "the snapshot bytes are restored" for another writer to enter.

Fail-safe direction: a tail that does not verify (foreign rows landed, a torn
row, or the log shrank below the pre-emit size) is NEVER cut. The helper logs
loudly and returns ``False`` -- stranding one already-emitted row is the
recoverable outcome; destroying another writer's durable events is not.

Ownership is recorded under the lock, never inferred from a later arbitrary
tail (spec-kitty #4072 operator acceptance, 2026-09-08): an expected-ids
capture taken OUTSIDE the lock-held window that spans the emit can adopt a
concurrent writer's just-committed rows as "expected" and a later rollback
would cut them. Every workflow commit path therefore wraps its pre-emit
snapshot and its emits in :func:`owned_emission_window` and threads the
captured ids into its commit; the coord fallback arm holds the same L1 across
emit, capture, commit and rollback and reads its capture from its own
``EventStream`` inside that hold. Between the window's release and a later
rollback anything may land -- the multiset verification catches it and
refuses.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

from .locking import BOUNDED_STATUS_LOCK_TIMEOUT_SECONDS, FeatureStatusLockTimeoutError, feature_status_lock
from .reducer import SNAPSHOT_FILENAME
from .store import EVENTS_FILENAME, truncate_events_log

__all__ = [
    "OwnedEmission",
    "capture_events_tail_ids",
    "owned_emission_window",
    "rollback_events_log_tail",
    "rollback_status_artifacts",
]

logger = logging.getLogger(__name__)


def _tail_rows(
    events_path: Path,
    pre_emit_event_size: int,
    *,
    missing_as_empty: bool = True,
) -> list[dict[str, object]] | None:
    """Parse the log's ``[pre_emit_event_size:]`` region as whole JSONL rows.

    ``None`` means the region is not a sequence of complete JSON objects (a
    torn write, binary garbage, a parse error -- or, when *missing_as_empty*
    is False, the log vanishing between an earlier ``stat()`` and this read):
    the caller treats that as "cannot verify", never as "verified empty".
    Blank lines are skipped: the atomic append primitive normalizes a missing
    trailing newline by inserting one, which can leave a leading blank line
    in the region.

    A missing log is ``[]`` for the capture path (nothing this operation
    appended can be in a log that does not exist) but "cannot verify" for the
    rollback path (#4087): the rollback already observed the log exist, so a
    vanished log means an unsanctioned delete/rewrite landed in the window,
    and truncating would zero-extend/recreate the file (``"ab"``) rather than
    restore anything.
    """
    try:
        data = events_path.read_bytes()
    except FileNotFoundError:
        return [] if missing_as_empty else None
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
    """The ``event_id`` of every row, in file order, stringified.

    No ordering happens here: the rollback-time comparison sorts both sides
    at the call site, so this stays the raw file-order record.
    """
    return [str(row.get("event_id", "")) for row in rows]


def capture_events_tail_ids(events_path: Path, pre_emit_event_size: int) -> list[str] | None:
    """Read the event ids a just-finished emit left in the log's tail.

    The expectation record for :func:`rollback_events_log_tail`. Returns the
    ids in file order, or ``None`` when the tail cannot be parsed as whole
    rows (the rollback then refuses any nonempty tail). Only
    meaningful while the mission status lock is held -- see
    :func:`owned_emission_window`.
    """
    rows = _tail_rows(events_path, pre_emit_event_size)
    return None if rows is None else _row_event_ids(rows)


@dataclass
class OwnedEmission:
    """One operation's pre-emit snapshot plus its captured ownership record.

    ``pre_emit_event_size`` / ``pre_emit_status_bytes`` are captured at
    :func:`owned_emission_window` entry (under the lock, before any emit);
    ``expected_event_ids`` is captured at the window's exit (still under the
    same hold, after the operation's emits) -- so it names exactly the rows
    this operation appended, never a concurrent writer's.
    """

    pre_emit_event_size: int
    pre_emit_status_bytes: bytes | None
    expected_event_ids: list[str] | None = None


@contextmanager
def owned_emission_window(
    feature_dir: Path,
    *,
    repo_root: Path | None,
    timeout: float = BOUNDED_STATUS_LOCK_TIMEOUT_SECONDS,
) -> Iterator[OwnedEmission]:
    """Hold the mission status lock across one operation's snapshot -> emit window.

    The ownership seam for the workflow commit paths (spec-kitty #4072
    operator acceptance): the pre-emit event-log size and ``status.json``
    bytes are captured at entry and the tail's event ids at exit, both inside
    ONE ``feature_status_lock`` hold (the same lock, lock-root resolution and
    lock key the write pipeline uses; re-entrant for the emit helpers that
    take it themselves). A concurrent lock-honoring writer therefore cannot
    append between this operation's snapshot and its capture -- the capture
    records only this operation's rows, which is exactly what a later
    :func:`rollback_events_log_tail` verifies before cutting.

    Ownership must never be inferred from a later arbitrary tail read outside
    this hold: a capture taken after the lock was released can adopt a
    concurrent writer's just-committed rows as "expected", and the rollback
    would then destroy them. Anything that lands AFTER the window's capture
    is caught by the rollback's multiset verification and refused.

    The take is bounded (the window spans the emit helpers' own git-registry
    consultation, so a stalled sibling holder surfaces as
    :class:`FeatureStatusLockTimeoutError` rather than wedging every status
    writer for the mission). If the body raises, no capture happens:
    ``expected_event_ids`` stays ``None`` and the rollback (which the callers
    only run on a COMMIT failure, never an emit failure) refuses a nonempty
    tail without ownership.
    """
    from specify_cli.workspace.root_resolver import resolve_status_lock_root  # noqa: PLC0415 -- cycle-safe lazy import, same seam status.emit uses

    lock_root = resolve_status_lock_root(feature_dir, repo_root)
    events_path = feature_dir / EVENTS_FILENAME
    status_path = feature_dir / SNAPSHOT_FILENAME
    with feature_status_lock(lock_root, feature_dir.name, timeout=timeout):
        emission = OwnedEmission(
            pre_emit_event_size=events_path.stat().st_size if events_path.exists() else 0,
            pre_emit_status_bytes=status_path.read_bytes() if status_path.exists() else None,
        )
        yield emission
        emission.expected_event_ids = capture_events_tail_ids(events_path, emission.pre_emit_event_size)


def _rollback_events_log_locked(
    feature_dir: Path,
    *,
    pre_emit_event_size: int,
    expected_event_ids: Sequence[str] | None,
) -> bool:
    """The in-lock rollback core: verify the tail, cut only what this operation appended.

    Must be called while the mission status lock is HELD (either entry point
    below takes it; a caller that already holds it re-enters). Returns ``True``
    when the log is (or already was) at/below the pre-emit size; ``False`` on
    every refusal (the log is left untouched).
    """
    events_path = feature_dir / EVENTS_FILENAME
    try:
        size = events_path.stat().st_size
    except FileNotFoundError:
        if pre_emit_event_size == 0:
            return True  # nothing was ever appended; the pre-emit state already holds
        # The log existed at the caller's pre-emit snapshot (its size is the
        # pre-emit size) but has vanished: an unsanctioned delete/rewrite
        # landed in the window. Claiming the pre-emit state "holds" would let
        # the caller restore the pre-emit derived snapshot over a missing
        # authority -- refuse instead (#4087).
        logger.warning(
            "Refused rollback truncate of %s: the log vanished after the pre-emit snapshot (pre-emit size %d); log left absent",
            events_path,
            pre_emit_event_size,
        )
        return False
    if size < pre_emit_event_size:
        # The log SHRANK below the pre-emit size: a whole-log rewrite (merge
        # driver, migration) landed in the window. Truncating to a larger size
        # would zero-extend the file; cutting anything would judge a log this
        # operation did not leave in that state. Refuse.
        logger.warning(
            "Refused rollback truncate of %s: log size %d is below the pre-emit size %d (the log was rewritten in the window); log left intact",
            events_path,
            size,
            pre_emit_event_size,
        )
        return False
    if size == pre_emit_event_size:
        return True  # idempotent no-op: the log is already at the pre-emit size
    if expected_event_ids is None:
        logger.warning(
            "Refused rollback truncate of %s: no captured event ownership for a nonempty tail; log left intact",
            events_path,
        )
        return False
    # ``missing_as_empty=False`` (#4087): the ``stat()`` above observed the
    # log exist (or returned via one of the guards), so a missing log inside
    # the lock is an unsanctioned delete in the window -- never a "verified
    # empty" tail (truncating would recreate the file NUL-filled to the
    # pre-emit size via the store's ``"ab"`` open).
    rows = _tail_rows(events_path, pre_emit_event_size, missing_as_empty=False)
    if rows is None:
        logger.warning(
            "Refused rollback truncate of %s: tail beyond %d bytes is not whole JSONL rows (torn write or foreign content); log left intact",
            events_path,
            pre_emit_event_size,
        )
        return False
    if sorted(_row_event_ids(rows)) != sorted(expected_event_ids):
        logger.warning(
            "Refused rollback truncate of %s: tail holds %r, expected %r (a concurrent writer's rows would be destroyed); log left intact",
            events_path,
            _row_event_ids(rows),
            list(expected_event_ids),
        )
        return False
    truncate_events_log(feature_dir, pre_emit_event_size=pre_emit_event_size)
    return True


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
    re-entrant for a caller already holding it) BEFORE the first ``stat()``,
    then verifies the log's tail beyond *pre_emit_event_size* before cutting
    it:

    * structurally -- every non-blank line in the cut region must be a whole
      JSON object (never a torn row);
    * ownership -- a nonempty tail requires *expected_event_ids*, and its
      event ids must be exactly that multiset (never a concurrent writer's rows).

    *expected_event_ids* must come from an in-lock capture
    (:func:`owned_emission_window`, or the coord fallback arm's own
    in-hold ``EventStream`` read) -- never from a tail read taken outside the
    lock-held window that spans the emit.

    Callers that also restore the derived ``status.json`` must use
    :func:`rollback_status_artifacts` instead: restoring the snapshot after
    THIS function returns runs outside the lock, which is exactly the
    successful-truncation/snapshot-restore race #4087 demonstrated.

    Returns ``True`` when the log was (or already was) at/below the pre-emit
    size -- the rollback outcome every caller wants. Returns ``False`` when
    verification refused the cut (foreign rows, torn row, shrunken log, a
    log that vanished after the caller observed it exist, or the lock could
    not be acquired): the log is left untouched and the refusal is logged
    loudly. Refusal strands one already-emitted row; it never destroys
    another writer's durable events.
    """
    from specify_cli.workspace.root_resolver import resolve_status_lock_root  # noqa: PLC0415 -- cycle-safe lazy import, same seam status.emit uses

    lock_root = resolve_status_lock_root(feature_dir, repo_root)
    try:
        with feature_status_lock(lock_root, feature_dir.name, timeout=timeout):
            return _rollback_events_log_locked(
                feature_dir,
                pre_emit_event_size=pre_emit_event_size,
                expected_event_ids=expected_event_ids,
            )
    except FeatureStatusLockTimeoutError as exc:
        logger.warning(
            "Refused rollback truncate of %s: could not acquire the mission status lock within %ss (%s); log left intact",
            feature_dir / EVENTS_FILENAME,
            timeout,
            exc,
        )
        return False


def rollback_status_artifacts(
    feature_dir: Path,
    *,
    repo_root: Path | None,
    pre_emit_event_size: int,
    pre_emit_status_bytes: bytes | None,
    expected_event_ids: Sequence[str] | None = None,
    timeout: float = BOUNDED_STATUS_LOCK_TIMEOUT_SECONDS,
) -> bool:
    """Tail-verified rollback of BOTH status artifacts under ONE lock hold.

    The #4087 operator acceptance seam: the rollback decision, the event-log
    truncation (or its refusal/no-op), and the derived ``status.json``
    restore all run inside ONE ``feature_status_lock`` hold -- the same lock,
    lock-root resolution and lock key the write pipeline uses, re-entrant for
    a caller that already holds it (the coord fallback arm's L1, the review
    shell). Without that single hold, a second writer could append a valid
    event, canonically materialize the snapshot and Git-commit both artifacts
    between a SUCCESSFUL log truncation and this operation's snapshot
    restore; the restore would then clobber the acknowledged newer snapshot
    with obsolete pre-emit bytes, leaving the working derived state
    incoherent with both the committed snapshot and canonical replay.

    Fail-safe direction, shared by both halves: when the log half refuses --
    foreign rows in the tail, a torn row, a shrunken or vanished log, an
    un-acquirable lock -- the derived snapshot is left at its newer coherent
    state too (restoring the pre-emit bytes over a log that still holds the
    surviving rows would leave the surface incoherent) and ``False`` is
    returned as the explicit recoverable diagnostic. Only a verified (or
    genuinely no-op) log rollback also restores the snapshot bytes:
    *pre_emit_status_bytes* writes them back, ``None`` unlinks the snapshot
    (the pre-emit state had none).

    Returns ``True`` when both artifacts were restored (or the log was
    already at its pre-emit size and the snapshot bytes were restored /
    unlinked), ``False`` on any refusal -- the log is never cut and the
    snapshot is never rewritten on a refusal.
    """
    from specify_cli.workspace.root_resolver import resolve_status_lock_root  # noqa: PLC0415 -- cycle-safe lazy import, same seam status.emit uses

    lock_root = resolve_status_lock_root(feature_dir, repo_root)
    status_path = feature_dir / SNAPSHOT_FILENAME
    try:
        with feature_status_lock(lock_root, feature_dir.name, timeout=timeout):
            rolled_back = _rollback_events_log_locked(
                feature_dir,
                pre_emit_event_size=pre_emit_event_size,
                expected_event_ids=expected_event_ids,
            )
            if not rolled_back:
                return False
            try:
                if pre_emit_status_bytes is None:
                    status_path.unlink(missing_ok=True)
                else:
                    status_path.parent.mkdir(parents=True, exist_ok=True)
                    status_path.write_bytes(pre_emit_status_bytes)
            except OSError:
                # The LOG half verified and was restored; a failed snapshot
                # write is logged, not fatal -- the log remains the sole
                # authority and `agent status materialize` regenerates the
                # derived snapshot from it.
                logger.exception("Could not restore %s on rollback; regenerate with 'spec-kitty agent status materialize'", status_path)
            return True
    except FeatureStatusLockTimeoutError as exc:
        logger.warning(
            "Refused rollback restore of %s (and %s): could not acquire the mission status lock within %ss (%s); both artifacts are left intact",
            feature_dir / EVENTS_FILENAME,
            status_path,
            timeout,
            exc,
        )
        return False
    except OSError as exc:
        logger.warning(
            "Refused rollback restore of %s (and %s): %s; both artifacts are left intact",
            feature_dir / EVENTS_FILENAME,
            status_path,
            exc,
        )
        return False
