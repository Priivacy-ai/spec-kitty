"""Migration engine: backfill runtime state into the event log + fail-closed verify.

Realises **IC-03** (per-field backfill + fail-closed verify) and gates the reader
cutover for every downstream field vertical (WP05-WP09). The pinned migration
order this module implements the *first two steps* of is::

    backfill -> verify(pre-strip, FAIL-CLOSED) -> reader cutover -> writer cutover
             -> strip mutable fields -> delete fallbacks -> land hash guard

This WP owns **backfill + verify + the ``MUTABLE_FIELDS`` field-moves** only. It
does **not** perform reader/writer cutover (the field verticals do) and does
**not** delete the legacy fallbacks (WP10 does, gated on this backfill).

Backfill (:func:`backfill_runtime_state`)
    For every WP in the live corpus, reconstruct the frontmatter/checkbox runtime
    state that is about to be stripped into seed events:

    - the **claim** state (``shell_pid`` / ``shell_pid_created_at`` / ``agent``)
      rides a seed ``planned -> claimed`` :class:`StatusEvent` whose
      ``policy_metadata`` sidecar the WP01 reducer folds into the snapshot slots
      (FR-004 claim path);
    - ``assignee`` / ``tracker_refs`` / subtask completion / ``review`` ride seed
      :class:`InnerStateChanged` annotations with a typed :class:`WPInnerStateDelta`.

    Every seed ``event_id`` is a **deterministic namespaced ULID**
    (``mission_id + wp_id + field``), so a re-run mints byte-identical ids and the
    idempotency check (skip an id already on disk) makes a second run seed nothing
    (NFR-002). Subtask-completion marks **clamp** their ``at`` to the WP's
    ``claimed`` timestamp — the marks carry no real timestamp, so the clamp is
    deliberately fictional (see the honesty precondition below).

    NOTE on the emit seam: the public :func:`~specify_cli.status.emit.emit_inner_state_changed`
    mints a *random* ULID, which cannot satisfy the deterministic-idempotent seed
    contract. The backfill therefore reuses the exact internals that API is built
    on — the sanctioned ``wp_state.annotate()`` non-transition seam plus the
    durability-verified store append (:func:`append_annotations_atomic_verified`)
    — but supplies its own deterministic ``event_id``. The seeds are ordinary
    WP01 events: the reducer folds them into the snapshot with no special-casing.

Verify (:func:`verify_backfill`) — **fail-closed**
    Asserts every value produced by the OLD frontmatter/checkbox reader exists in
    its exact deterministic seed row, while allowing legitimate later events to
    win in the current snapshot. The proof reads the **un-stripped** frontmatter:
    :func:`strip_mutable_fields` MUST NOT run before verify. The verifier also
    checks WP/count integrity, rejects corrupt deterministic seed rows, and raises
    :class:`MigrationOrderingError`. Any mismatch, ordering violation, or corrupt
    seed **aborts before reader cutover** — never a warning.

Honesty bound (no-data-loss)
    "No data loss" is asserted against deterministic seed-row payload parity and
    WP/count integrity, **not** temporal fidelity or equality with the latest
    reduced value: backfilled subtask-completion timestamps are clamped
    (fictional), seed ULIDs are content-namespaced (not chronological), and a
    later legitimate annotation may supersede a seed in the current snapshot.
    The contract holds only because **no consumer reads subtask-completion time or
    relies on seed-ULID chronological order** — this is asserted as an explicit
    precondition in the test-suite.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from specify_cli.core.paths import assert_safe_path_segment
from specify_cli.core.subtask_rows import iter_wp_section_subtask_rows
from specify_cli.core.utils import ensure_within_any
from specify_cli.mission_metadata import load_meta
from specify_cli.status import (
    InnerStateChanged,
    Lane,
    ReviewOverride,
    Status,
    StatusEvent,
    WPInnerStateDelta,
)
from specify_cli.status import materialize_snapshot
from specify_cli.status import (
    EVENTS_FILENAME,
    StoreError,
    append_annotations_atomic_verified,
    append_events_atomic_verified,
    read_event_stream,
)
from specify_cli.status import annotate
from specify_cli.workspace import canonicalize_feature_dir

from .mission_state import deterministic_ulid

logger = logging.getLogger(__name__)

#: Actor recorded on seed events (migration provenance, not a live agent).
BACKFILL_ACTOR = "migration:backfill_runtime_state"

#: The concrete ``review_artifact_override_*`` frontmatter keys the write half
#: (``tasks_materialization._persist_review_artifact_override``) emits. Enumerated
#: — never glob-guessed — and consumed by both the legacy reader here and the
#: ``strip_frontmatter.MUTABLE_FIELDS`` extension.
_REVIEW_OVERRIDE_KEYS = (
    "review_artifact_override_at",
    "review_artifact_override_actor",
    "review_artifact_override_wp_id",
    "review_artifact_override_reason",
)

#: Snapshot runtime slots sourced from WP *frontmatter* (not from tasks.md
#: checkboxes). The ordering guard keys on these: a snapshot slot present here
#: whose frontmatter key has already been stripped proves a strip-before-verify.
_FRONTMATTER_SOURCED_SLOTS = ("shell_pid", "shell_pid_created_at", "agent", "assignee", "tracker_refs", "review")

BackfillAction = Literal["wrote", "skip", "error"]


class BackfillVerificationError(RuntimeError):
    """Fail-closed abort: the reduced snapshot did not match the OLD reader.

    Raised by :func:`run_backfill_and_verify` when :func:`verify_backfill`
    reports a count/value mismatch (including a fault-injected corrupt seed).
    This is terminal — the caller MUST NOT advance to reader cutover.
    """


class MigrationOrderingError(RuntimeError):
    """Fail-closed abort: verify was asked to run against stripped frontmatter.

    The pinned order is ``backfill -> verify(pre-strip) -> cutover -> strip``.
    If :func:`strip_mutable_fields` has already removed a frontmatter key whose
    value the snapshot still carries, the OLD reader would read empty and yield a
    vacuous false green. Detecting that is itself fail-closed.
    """


class LegacyRuntimeReadError(RuntimeError):
    """Fail-closed abort: a WP artifact cannot be parsed for migration."""


@dataclass(frozen=True)
class LegacyWPRuntime:
    """Pre-eviction runtime state reconstructed from ONE WP's legacy read path.

    This is the OLD frontmatter/checkbox reader's per-WP view — the ground truth
    :func:`verify_backfill` compares the reduced snapshot against.
    """

    wp_id: str
    shell_pid: int | None = None
    shell_pid_created_at: str | None = None
    agent: str | None = None
    assignee: str | None = None
    tracker_refs: tuple[str, ...] = ()
    #: subtask-id -> completion status (``Lane.DONE`` / ``Lane.PLANNED``).
    subtasks: dict[str, Status] = field(default_factory=dict)
    review: ReviewOverride | None = None
    #: Frontmatter keys actually present on disk (drives the ordering guard).
    frontmatter_keys: frozenset[str] = frozenset()

    def has_evictable_state(self) -> bool:
        """True when this WP carries any runtime state that must be seeded."""
        return bool(
            self.shell_pid is not None
            or self.shell_pid_created_at is not None
            or self.agent is not None
            or self.assignee is not None
            or self.tracker_refs
            or self.subtasks
            or (self.review is not None and self.review.complete)
        )

@dataclass
class BackfillResult:
    """Per-mission result from :func:`backfill_runtime_state`.

    Attributes:
        feature_dir: Absolute path to the mission directory.
        slug: Directory name used as the mission slug.
        action: ``"wrote"`` — one or more seeds appended; ``"skip"`` — nothing to
            seed or already fully seeded (idempotent no-op); ``"error"`` — an
            unrecoverable per-mission error.
        seeded_count: Number of NEW seed events appended this run (0 on a re-run).
        reason: Human-readable explanation (populated on ``"skip"``/``"error"``).
        warnings: Non-fatal per-WP warnings (e.g. a never-claimed WP skipped).
    """

    feature_dir: Path
    slug: str
    action: BackfillAction
    seeded_count: int = 0
    reason: str | None = None
    warnings: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class VerifyResult:
    """Fail-closed result of :func:`verify_backfill`.

    ``ok`` is True only when every legacy-derived deterministic seed is present
    with its exact payload and the WP/count integrity guards pass.
    ``mismatches`` carries a human-readable line per divergence for diagnostics;
    the runner treats any non-``ok`` result as a terminal abort (no reader
    cutover).
    """

    ok: bool
    wp_count: int
    mismatches: tuple[str, ...] = ()

    def raise_if_failed(self) -> None:
        """Raise :class:`BackfillVerificationError` unless verify passed."""
        if not self.ok:
            raise BackfillVerificationError(
                "backfill verify failed (fail-closed; no reader cutover): "
                + "; ".join(self.mismatches)
            )


# ---------------------------------------------------------------------------
# Deterministic seed identity
# ---------------------------------------------------------------------------


def _mission_id(feature_dir: Path) -> str:
    """Return the canonical ``mission_id`` (ULID) or fall back to the slug.

    The mission_id is the deterministic-ULID namespace root. A legacy mission
    without a minted ``mission_id`` degrades to its directory name — still stable
    per corpus, which is all the seed determinism requires.
    """
    meta = load_meta(feature_dir, allow_missing=True, on_malformed="none")
    if meta is not None:
        raw = meta.get("mission_id")
        if raw:
            return str(raw)
    return feature_dir.name


def _seed_id(mission_id: str, wp_id: str, field_name: str) -> str:
    """Return the deterministic namespaced seed ULID for one (wp, field).

    Namespaced on ``mission_id | wp_id | field`` (``|`` separator, matching the
    ``rebuild_state._deterministic_id`` precedent) so the same corpus mints
    byte-identical ids across runs (idempotency) and each field vertical gets a
    distinct, collision-free id.
    """
    return str(deterministic_ulid(f"{mission_id}|{wp_id}|{field_name}"))


# ---------------------------------------------------------------------------
# OLD reader (pre-eviction frontmatter + tasks.md checkboxes)
# ---------------------------------------------------------------------------


def _coerce_tracker_refs(raw: Any) -> tuple[str, ...]:
    """Normalise a frontmatter ``tracker_refs`` value to a tuple of strings."""
    if raw is None:
        return ()
    if isinstance(raw, str):
        return tuple(part.strip() for part in raw.split(",") if part.strip())
    if isinstance(raw, (list, tuple)):
        return tuple(str(item).strip() for item in raw if str(item).strip())
    return ()


def _review_from_frontmatter(frontmatter: dict[str, Any], wp_id: str) -> ReviewOverride | None:
    """Reconstruct a :class:`ReviewOverride` from the override quartet, if complete."""
    at = frontmatter.get("review_artifact_override_at")
    actor = frontmatter.get("review_artifact_override_actor")
    override_wp = frontmatter.get("review_artifact_override_wp_id") or wp_id
    reason = frontmatter.get("review_artifact_override_reason")
    if not (at and actor and reason):
        return None
    override = ReviewOverride(at=str(at), actor=str(actor), wp_id=str(override_wp), reason=str(reason))
    return override if override.complete else None


def _subtasks_from_tasks_md(tasks_md_text: str, wp_id: str) -> dict[str, Status]:
    """Read per-subtask completion for *wp_id* from a ``tasks.md`` body.

    Reuses the canonical fence-aware, first-``WPxx``-heading walker
    (``core.subtask_rows.iter_wp_section_subtask_rows``) — the same source the
    lane-transition guard and dashboard consume — so the backfill never forks the
    "what counts as a subtask" definition. A checked row folds to ``Lane.DONE``,
    an unchecked row to ``Lane.PLANNED`` (a not-done sentinel).
    """
    result: dict[str, Status] = {}
    for task_id, checked in iter_wp_section_subtask_rows(tasks_md_text, wp_id):
        result[task_id] = Lane.DONE if checked else Lane.PLANNED
    return result


def _wp_code(wp_file: Path) -> str:
    """Derive the ``WPxx`` code from a WP filename stem."""
    import re

    m = re.match(r"^(WP\d+)", wp_file.stem)
    return m.group(1) if m else wp_file.stem


def read_legacy_runtime(feature_dir: Path) -> dict[str, LegacyWPRuntime]:
    """Reconstruct every WP's pre-eviction runtime state (the OLD reader).

    Reads each ``tasks/WP*.md`` frontmatter (``shell_pid`` / ``shell_pid_created_at``
    / ``agent`` / ``assignee`` / ``tracker_refs`` / ``review_artifact_override_*``)
    and the per-WP ``tasks.md`` checkbox section (subtask completion). This is the
    ground truth :func:`verify_backfill` compares the reduced snapshot against and
    the source :func:`backfill_runtime_state` seeds from.

    Returns a mapping keyed by ``WPxx`` code; only WPs that carry some evictable
    runtime state are included.
    """
    from specify_cli.frontmatter import FrontmatterManager

    tasks_dir = feature_dir / "tasks"
    if not tasks_dir.is_dir():
        return {}

    tasks_md = feature_dir / "tasks.md"
    tasks_md_text = tasks_md.read_text(encoding="utf-8") if tasks_md.exists() else ""

    manager = FrontmatterManager()
    out: dict[str, LegacyWPRuntime] = {}

    for wp_file in sorted(tasks_dir.glob("WP*.md")):
        try:
            frontmatter, _body = manager.read(wp_file)
        except Exception as exc:  # noqa: BLE001 - translate parser failures to migration domain
            raise LegacyRuntimeReadError(
                f"cannot read {wp_file.name} for legacy runtime: {exc}"
            ) from exc

        wp_id = _wp_code(wp_file)
        shell_pid_raw = frontmatter.get("shell_pid")
        agent_raw = frontmatter.get("agent")
        runtime = LegacyWPRuntime(
            wp_id=wp_id,
            shell_pid=int(shell_pid_raw) if isinstance(shell_pid_raw, (int, str)) and str(shell_pid_raw).strip().isdigit() else None,
            shell_pid_created_at=(str(frontmatter["shell_pid_created_at"]) if frontmatter.get("shell_pid_created_at") else None),
            agent=(str(agent_raw) if isinstance(agent_raw, str) and agent_raw.strip() else None),
            assignee=(str(frontmatter["assignee"]) if frontmatter.get("assignee") else None),
            tracker_refs=_coerce_tracker_refs(frontmatter.get("tracker_refs")),
            subtasks=_subtasks_from_tasks_md(tasks_md_text, wp_id),
            review=_review_from_frontmatter(frontmatter, wp_id),
            frontmatter_keys=frozenset(frontmatter.keys()),
        )
        if runtime.has_evictable_state() or runtime.frontmatter_keys:
            out[wp_id] = runtime

    return out


# ---------------------------------------------------------------------------
# Claim anchor (from the existing event log)
# ---------------------------------------------------------------------------


def _claim_anchors(feature_dir: Path) -> dict[str, str]:
    """Return each WP's ``claimed`` timestamp anchor from the existing event log.

    The anchor is the ``at`` of the WP's first transition *into* ``claimed``; if
    the WP never entered ``claimed`` explicitly it falls back to the WP's earliest
    transition ``at``. A WP with no transitions at all (never seeded) has no
    anchor and is absent from the mapping — its subtask/claim seeds are skipped
    (a never-claimed WP cannot honestly carry completed subtasks).
    """
    stream = read_event_stream(feature_dir)
    earliest: dict[str, str] = {}
    claimed: dict[str, str] = {}
    for ev in stream.transitions:
        if ev.wp_id not in earliest or ev.at < earliest[ev.wp_id]:
            earliest[ev.wp_id] = ev.at
        if ev.to_lane == Lane.CLAIMED and (ev.wp_id not in claimed or ev.at < claimed[ev.wp_id]):
            claimed[ev.wp_id] = ev.at
    return {wp_id: claimed.get(wp_id, earliest[wp_id]) for wp_id in earliest}


# ---------------------------------------------------------------------------
# Backfill
# ---------------------------------------------------------------------------


def _build_seed_events(
    feature_dir: Path,
    legacy: dict[str, LegacyWPRuntime],
    anchors: dict[str, str],
    warnings: list[str],
) -> tuple[list[StatusEvent], list[InnerStateChanged]]:
    """Build (claim transitions, annotations) seed events for a corpus.

    Seed ``event_id``s are deterministic namespaced ULIDs. Subtask-completion
    ``at`` is clamped to the WP's ``claimed`` anchor (fictional time, documented).
    Every reconstructed annotation shares that anchor ``at`` so its fold ordering
    (post-transition, via the WP01 event-kind partition) is deterministic; the
    truthful ``review_artifact_override_at`` is preserved *inside* the delta's
    :class:`ReviewOverride`, not on the envelope.
    """
    slug = feature_dir.name
    mission_id = _mission_id(feature_dir)
    transitions: list[StatusEvent] = []
    annotations: list[InnerStateChanged] = []

    for wp_id, runtime in sorted(legacy.items()):
        anchor = anchors.get(wp_id)
        if anchor is None:
            if runtime.has_evictable_state():
                warnings.append(f"{wp_id}: no claim anchor (never-claimed WP) — runtime seed skipped")
            continue

        # Claim state rides a seed planned->claimed transition whose
        # policy_metadata sidecar the reducer folds into the snapshot slots.
        if runtime.shell_pid is not None or runtime.agent is not None or runtime.shell_pid_created_at is not None:
            policy_metadata: dict[str, Any] = {}
            if runtime.shell_pid is not None:
                policy_metadata["shell_pid"] = runtime.shell_pid
            if runtime.shell_pid_created_at is not None:
                policy_metadata["shell_pid_created_at"] = runtime.shell_pid_created_at
            if runtime.agent is not None:
                policy_metadata["agent"] = runtime.agent
            transitions.append(
                StatusEvent(
                    event_id=_seed_id(mission_id, wp_id, "claim"),
                    mission_slug=slug,
                    wp_id=wp_id,
                    from_lane=Lane.PLANNED,
                    to_lane=Lane.CLAIMED,
                    at=anchor,
                    actor=BACKFILL_ACTOR,
                    force=False,
                    execution_mode="worktree",
                    policy_metadata=policy_metadata,
                    mission_id=mission_id if mission_id != slug else None,
                )
            )

        # assignee / tracker_refs / subtasks / review ride annotations. Each is a
        # distinct namespaced seed so idempotency skips them independently.
        _append_annotation(annotations, mission_id, wp_id, anchor, "assignee", WPInnerStateDelta(assignee=runtime.assignee) if runtime.assignee else None)
        _append_annotation(
            annotations,
            mission_id,
            wp_id,
            anchor,
            "tracker_refs",
            WPInnerStateDelta(tracker_refs=list(runtime.tracker_refs)) if runtime.tracker_refs else None,
        )
        _append_annotation(
            annotations,
            mission_id,
            wp_id,
            anchor,
            "subtasks",
            WPInnerStateDelta(subtasks=dict(runtime.subtasks)) if runtime.subtasks else None,
        )
        _append_annotation(
            annotations,
            mission_id,
            wp_id,
            anchor,
            "review",
            WPInnerStateDelta(review=runtime.review) if (runtime.review is not None and runtime.review.complete) else None,
        )
    return transitions, annotations


def _append_annotation(
    annotations: list[InnerStateChanged],
    mission_id: str,
    wp_id: str,
    at: str,
    field_name: str,
    delta: WPInnerStateDelta | None,
) -> None:
    """Append a deterministic-id seed annotation for one field, if the delta is present."""
    if delta is None or delta.is_empty():
        return
    annotations.append(
        annotate(
            wp_id,
            delta,
            actor=BACKFILL_ACTOR,
            at=at,
            event_id=_seed_id(mission_id, wp_id, field_name),
        )
    )


def backfill_runtime_state(feature_dir: Path, *, dry_run: bool = False) -> BackfillResult:
    """Idempotently seed one mission's frontmatter/checkbox runtime state as events.

    Resolves the write target via :func:`canonicalize_feature_dir` (never
    ``Path.cwd()`` — C-003 / #2647), reconstructs each WP's pre-eviction runtime
    state, and appends the missing seed events through the durability-verified
    store seams. Determinism + idempotency: seed ids are content-namespaced ULIDs,
    and any seed whose id is already on disk is skipped, so a second run seeds
    nothing (NFR-002).

    Args:
        feature_dir: kitty-specs mission directory (canonicalized here).
        dry_run: When True, compute the would-seed count without writing.

    Returns:
        A :class:`BackfillResult` describing what happened.
    """
    feature_dir = canonicalize_feature_dir(feature_dir)
    slug = feature_dir.name

    if not (feature_dir / "tasks").is_dir():
        return BackfillResult(feature_dir=feature_dir, slug=slug, action="skip", reason="no tasks/ directory")

    warnings: list[str] = []
    try:
        legacy = read_legacy_runtime(feature_dir)
        anchors = _claim_anchors(feature_dir)
        transitions, annotations = _build_seed_events(feature_dir, legacy, anchors, warnings)
    except (StoreError, LegacyRuntimeReadError) as exc:
        return BackfillResult(feature_dir=feature_dir, slug=slug, action="error", reason=f"event log unreadable: {exc}", warnings=warnings)

    # Idempotency: drop any seed whose deterministic id is already on disk.
    existing_ids = _existing_event_ids(feature_dir)
    new_transitions = [e for e in transitions if e.event_id not in existing_ids]
    new_annotations = [a for a in annotations if a.event_id not in existing_ids]
    seeded_count = len(new_transitions) + len(new_annotations)

    if seeded_count == 0:
        return BackfillResult(feature_dir=feature_dir, slug=slug, action="skip", reason="nothing new to seed (idempotent)", warnings=warnings)

    if dry_run:
        return BackfillResult(feature_dir=feature_dir, slug=slug, action="wrote", seeded_count=seeded_count, reason="dry-run (no write)", warnings=warnings)

    if new_transitions:
        append_events_atomic_verified(feature_dir, new_transitions)
    if new_annotations:
        append_annotations_atomic_verified(feature_dir, new_annotations)

    logger.info("Backfilled %d runtime seed event(s) for %s", seeded_count, slug)
    return BackfillResult(feature_dir=feature_dir, slug=slug, action="wrote", seeded_count=seeded_count, warnings=warnings)


def _existing_event_ids(feature_dir: Path) -> set[str]:
    """Return the set of ``event_id``s already present in the event log.

    Reads the annotation-aware stream so both lane transitions and off-axis
    annotations are covered by the idempotency skip.
    """
    events_path = feature_dir / EVENTS_FILENAME
    if not events_path.exists():
        return set()
    stream = read_event_stream(feature_dir)
    ids = {e.event_id for e in stream.transitions}
    ids |= {a.event_id for a in stream.annotations}
    return ids


def backfill_runtime_state_repo(
    repo_root: Path,
    *,
    dry_run: bool = False,
    mission_slug: str | None = None,
) -> list[BackfillResult]:
    """Walk ``kitty-specs/`` and idempotently backfill every mission.

    Mirrors :func:`~specify_cli.migration.backfill_identity.backfill_repo`. The
    write target is always resolved from each mission directory, never
    ``Path.cwd()`` (C-003).

    Args:
        repo_root: Absolute path to the repository root.
        dry_run: When True, compute results without writing.
        mission_slug: When provided, scope the walk to a single mission directory.

    Returns:
        One :class:`BackfillResult` per mission directory visited.
    """
    kitty_specs = repo_root / "kitty-specs"
    results: list[BackfillResult] = []
    if not kitty_specs.is_dir():
        logger.warning("kitty-specs/ not found at %s", repo_root)
        return results

    if mission_slug is not None:
        assert_safe_path_segment(mission_slug)
        candidates = [kitty_specs / mission_slug] if (kitty_specs / mission_slug).is_dir() else []
        if not candidates:
            logger.warning("No mission directory found for slug %r", mission_slug)
            return results
        try:
            candidates = [ensure_within_any(candidates[0], roots=[kitty_specs])]
        except ValueError as exc:
            raise ValueError(
                f"Mission directory resolves outside kitty-specs: {candidates[0]}"
            ) from exc
    else:
        candidates = []
        for entry in sorted(kitty_specs.iterdir()):
            if not entry.is_dir():
                continue
            try:
                candidates.append(ensure_within_any(entry, roots=[kitty_specs]))
            except ValueError:
                logger.warning(
                    "Skipping mission directory that resolves outside kitty-specs: %s",
                    entry,
                )

    for feature_dir in candidates:
        results.append(backfill_runtime_state(feature_dir, dry_run=dry_run))
    return results


# ---------------------------------------------------------------------------
# Fail-closed verify
# ---------------------------------------------------------------------------


def _assert_unstripped(
    wp_id: str,
    runtime: LegacyWPRuntime,
    seeded_slots: set[str],
) -> None:
    """Raise :class:`MigrationOrderingError` if the frontmatter was stripped early.

    Non-vacuous ordering guard: if the reduced snapshot carries a
    frontmatter-sourced slot for this WP but the WP file no longer carries the
    corresponding frontmatter key, ``strip_mutable_fields`` ran before verify and
    the OLD reader would read empty -> vacuous false green. Fail closed.
    """
    for slot in sorted(seeded_slots):
        key = "review_artifact_override_at" if slot == "review" else slot
        if key not in runtime.frontmatter_keys:
            raise MigrationOrderingError(
                f"{wp_id}: deterministic seed carries {slot!r} but frontmatter key {key!r} is absent — "
                "strip_mutable_fields ran before verify (pinned order is backfill -> verify(pre-strip) -> cutover -> strip)"
            )


def _seeded_frontmatter_slots(
    feature_dir: Path,
    wp_ids: set[str],
) -> dict[str, set[str]]:
    """Return frontmatter slots proven to have deterministic migration seeds.

    The order guard must inspect migration provenance, not the latest snapshot:
    a legitimate runtime annotation may populate a slot that was never present
    in legacy frontmatter. Deterministic seed IDs let us distinguish those cases.
    """
    stream = read_event_stream(feature_dir)
    transitions = {event.event_id: event for event in stream.transitions}
    annotations = {event.event_id: event for event in stream.annotations}
    mission_id = _mission_id(feature_dir)
    slots_by_wp: dict[str, set[str]] = {}
    for wp_id in wp_ids:
        slots: set[str] = set()
        claim = transitions.get(_seed_id(mission_id, wp_id, "claim"))
        if claim is not None:
            policy_metadata = claim.policy_metadata or {}
            slots.update(
                slot
                for slot in ("shell_pid", "shell_pid_created_at", "agent")
                if slot in policy_metadata
            )
        for field_name, slot in (
            ("assignee", "assignee"),
            ("tracker_refs", "tracker_refs"),
            ("review", "review"),
        ):
            if _seed_id(mission_id, wp_id, field_name) in annotations:
                slots.add(slot)
        slots_by_wp[wp_id] = slots
    return slots_by_wp


def _verify_expected_seed_events(
    feature_dir: Path,
    legacy: dict[str, LegacyWPRuntime],
    anchors: dict[str, str],
) -> list[str]:
    """Verify every deterministic migration seed exists with its exact payload.

    The reduced snapshot is latest-wins runtime state, so a legitimate later
    reassignment can differ from the legacy value without losing history. The
    no-data-loss proof therefore pins the deterministic seed row itself: every
    seed that :func:`_build_seed_events` derives from the legacy source must be
    present byte-semantically (same typed ``to_dict`` payload). Later events may
    then replace the current snapshot value without making cutover verification
    falsely reject an already-active mission.
    """
    expected_transitions, expected_annotations = _build_seed_events(
        feature_dir,
        legacy,
        anchors,
        [],
    )
    stream = read_event_stream(feature_dir)
    actual_transitions = {event.event_id: event for event in stream.transitions}
    actual_annotations = {event.event_id: event for event in stream.annotations}
    mismatches: list[str] = []

    for expected_transition in expected_transitions:
        actual_transition = actual_transitions.get(expected_transition.event_id)
        if actual_transition is None:
            mismatches.append(
                f"{expected_transition.wp_id}: claim mismatch (deterministic seed missing)"
            )
        elif actual_transition.to_dict() != expected_transition.to_dict():
            mismatches.append(
                f"{expected_transition.wp_id}: claim mismatch (deterministic seed payload diverged)"
            )

    for expected_annotation in expected_annotations:
        actual_annotation = actual_annotations.get(expected_annotation.event_id)
        field_name = next(
            (
                name
                for name, value in expected_annotation.delta.to_dict().items()
                if value is not None
            ),
            "annotation",
        )
        if actual_annotation is None:
            mismatches.append(
                f"{expected_annotation.wp_id}: {field_name} mismatch "
                "(deterministic seed missing)"
            )
        elif actual_annotation.to_dict() != expected_annotation.to_dict():
            mismatches.append(
                f"{expected_annotation.wp_id}: {field_name} mismatch "
                "(deterministic seed payload diverged)"
            )

    return mismatches


def _has_snapshot_runtime(wp: dict[str, Any]) -> bool:
    """True iff a reduced-snapshot WP carries any runtime-slot value."""
    return any(
        wp.get(slot) not in (None, [], {})
        for slot in (
            "shell_pid",
            "shell_pid_created_at",
            "agent",
            "assignee",
            "tracker_refs",
            "subtasks",
            "review",
            "role",
            "agent_profile",
            "agent_profile_version",
            "model",
            "provider",
        )
    )


def verify_backfill(feature_dir: Path) -> VerifyResult:
    """Fail-closed proof that OLD-reader values survive in deterministic seeds.

    Rebuilds the expected deterministic rows from the OLD frontmatter/checkbox
    reader (:func:`read_legacy_runtime`) and compares each exact typed payload to
    the raw event stream. The current reduced snapshot may legitimately be newer
    because runtime slots are latest-wins.

    Fail-closed:
        - a corrupt/unreadable event log -> ``ok=False`` (terminal);
        - any seed-payload, conflict, or count mismatch -> ``ok=False`` (terminal);
        - a frontmatter already stripped at verify time -> :class:`MigrationOrderingError`.

    The strip is a *downstream* step, never a precondition of verify.

    Returns:
        A :class:`VerifyResult`; call :meth:`VerifyResult.raise_if_failed` (or use
        :func:`run_backfill_and_verify`) to turn a non-``ok`` result into an abort.

    Raises:
        MigrationOrderingError: if verify is run after ``strip_mutable_fields``.
    """
    feature_dir = canonicalize_feature_dir(feature_dir)
    try:
        legacy = read_legacy_runtime(feature_dir)
    except LegacyRuntimeReadError as exc:
        return VerifyResult(
            ok=False,
            wp_count=0,
            mismatches=(f"legacy runtime unreadable: {exc}",),
        )

    try:
        snapshot = materialize_snapshot(feature_dir)
    except StoreError as exc:
        return VerifyResult(ok=False, wp_count=0, mismatches=(f"event log unreadable: {exc}",))

    mismatches: list[str] = []
    # A WP is the backfill's responsibility to seed ONLY when it has a claim
    # anchor: a never-claimed WP (no transition events) is skipped by
    # _build_seed_events (warn, not fail), so verify mirrors that skip — an
    # anchor-less WP is never a count mismatch (Defect 1, spec Edge Case).
    anchors = _claim_anchors(feature_dir)
    seeded_wps = {
        wp_id
        for wp_id, runtime in legacy.items()
        if runtime.has_evictable_state() and wp_id in anchors
    }

    # Count parity, DATA-LOSS direction: a seeded WP whose snapshot carries no
    # runtime at all.
    snapshot_runtime_wps = {wp_id for wp_id, wp in snapshot.work_packages.items() if _has_snapshot_runtime(wp)}
    for wp_id in sorted(seeded_wps - snapshot_runtime_wps):
        mismatches.append(f"{wp_id}: legacy carries runtime state but snapshot has none (count mismatch)")

    # Reverse direction is tolerant of the already-migrated / mid-migration state
    # (Defect 3): a WP whose snapshot carries runtime the legacy FRONTMATTER lacks
    # is valid IFF it still has a legacy WP row (a real WP file, its runtime merely
    # event-sourced now — the actively-running mission does exactly this). A
    # snapshot WP with NO legacy row at all (no WP file) is a phantom / injected
    # entry and is still caught fail-closed.
    legacy_wp_ids = set(legacy.keys())
    for wp_id in sorted(snapshot_runtime_wps - legacy_wp_ids):
        mismatches.append(f"{wp_id}: snapshot carries runtime state but no legacy WP row exists (phantom / injected)")

    # The legacy-derived values must exist exactly in their deterministic seed
    # rows. Compare those raw rows rather than the latest-wins snapshot value:
    # an already-active mission can legitimately carry a later reassignment.
    mismatches.extend(_verify_expected_seed_events(feature_dir, legacy, anchors))

    # Preserve the strip-order guard using deterministic seed provenance. Current
    # snapshot values may be ahead of legacy (even at the same timestamp), so
    # snapshot presence alone is not evidence that frontmatter was stripped.
    seeded_slots = _seeded_frontmatter_slots(feature_dir, legacy_wp_ids)
    for wp_id in sorted(legacy_wp_ids):
        _assert_unstripped(wp_id, legacy[wp_id], seeded_slots[wp_id])

    return VerifyResult(ok=not mismatches, wp_count=len(seeded_wps), mismatches=tuple(mismatches))


def run_backfill_and_verify(feature_dir: Path, *, dry_run: bool = False) -> tuple[BackfillResult, VerifyResult]:
    """Run the pinned ``backfill -> verify(pre-strip, fail-closed)`` unit.

    This enforces the order by construction: it seeds, then verifies against the
    still-un-stripped frontmatter, and turns a non-``ok`` verify into a terminal
    :class:`BackfillVerificationError`. It never strips — the strip is a
    downstream step owned by the field verticals / WP10.

    Returns:
        ``(BackfillResult, VerifyResult)`` on success (verify ``ok``).

    Raises:
        BackfillVerificationError: on any count/value mismatch (fail-closed).
        MigrationOrderingError: if the frontmatter was stripped before verify.
    """
    backfill_result = backfill_runtime_state(feature_dir, dry_run=dry_run)
    if backfill_result.action == "error":
        raise BackfillVerificationError(
            backfill_result.reason or "backfill failed before verify"
        )
    verify_result = verify_backfill(feature_dir)
    verify_result.raise_if_failed()
    return backfill_result, verify_result


# ---------------------------------------------------------------------------
# T013: zero-reader verification for history[] / progress
# ---------------------------------------------------------------------------

#: Fields proven dead by the runtime-state eviction: no live reader anywhere
#: consumes them for a decision, so they are safe to delete (``history[]`` +
#: ``add_history_entry`` in WP07/T028; the ``progress`` field is already inert).
#: This module produces the *proof* (:func:`assert_zero_readers`); it performs no
#: deletion.
ZERO_READER_FIELDS = ("history", "progress")

#: Basenames carrying the ``history`` *writer* read-modify-write machinery
#: (``FrontmatterManager.add_history_entry`` + the ``WPMetadata`` merge
#: carry-forward). These touch ``history[]`` to *append*, never to consume it for
#: a decision, and are WP07/T028's to delete. They are excluded from the
#: zero-*reader* proof so the proof measures genuine consumers, not the doomed
#: writer. Once WP07/T028 removes them the exclusion becomes a no-op.
HISTORY_WRITER_SEAMS = frozenset({"frontmatter.py", "wp_metadata.py"})


def find_field_readers(
    src_root: Path,
    field_name: str,
    *,
    exclude_basenames: frozenset[str] = frozenset(),
) -> list[str]:
    """Return ``path:line`` sites that appear to *read* ``field_name`` from a mapping.

    A grep-style scan over ``*.py`` under ``src_root`` for frontmatter/metadata
    read patterns — ``["field"]`` / ``['field']`` / ``.get("field")`` / ``.field``
    attribute access. Write-only markers (``set_scalar``/``add_history_entry``/
    ``del``/``pop``) and the field-registry declarations
    (``MUTABLE_FIELDS``/``STATIC_FIELDS``/…) are NOT counted — this proves *no
    live reader*, not *no mention*. ``exclude_basenames`` drops whole files (e.g.
    the ``history`` writer seams WP07/T028 owns) from the audit.

    Used by :func:`assert_zero_readers` and the WP03 zero-reader tests to gate the
    eventual deletion (WP07/T028 for ``history[]``, WP10 for the fallbacks).
    """
    import re

    read_patterns = [
        re.compile(rf"""\[\s*["']{re.escape(field_name)}["']\s*\]"""),
        re.compile(rf"""\.get\(\s*["']{re.escape(field_name)}["']"""),
        re.compile(rf"""(?<![\w.])\.{re.escape(field_name)}\b"""),
    ]
    # Write seams / registry declarations that mention the field but do not read it.
    write_markers = (
        "set_scalar",
        "add_history_entry",
        "del ",
        ".pop(",
        "MUTABLE_FIELDS",
        "STATIC_FIELDS",
        "RETIRED_FIELDS",
        "ZERO_READER_FIELDS",
    )

    hits: list[str] = []
    self_path = Path(__file__).resolve()
    for py_file in sorted(src_root.rglob("*.py")):
        if py_file.resolve() == self_path or py_file.name in exclude_basenames:
            continue
        try:
            text = py_file.read_text(encoding="utf-8")
        except OSError:
            continue
        for lineno, line in enumerate(text.splitlines(), start=1):
            stripped = line.lstrip()
            # Module imports (``from .progress import …``) name a module, not a
            # frontmatter field read — never a live reader of the field.
            if stripped.startswith(("import ", "from ")):
                continue
            if any(marker in line for marker in write_markers):
                continue
            if any(pat.search(line) for pat in read_patterns):
                hits.append(f"{py_file}:{lineno}")
    return hits


def assert_zero_readers(
    src_root: Path,
    fields: tuple[str, ...] = ZERO_READER_FIELDS,
    *,
    exclude_basenames: frozenset[str] = HISTORY_WRITER_SEAMS,
) -> None:
    """Raise if any of *fields* still has a live *reader* under *src_root*.

    The proof that gates deletion of ``history[]`` (WP07/T028) and confirms
    ``progress`` is inert (FR-010). Non-vacuous: it fails loudly the moment a
    consumer is (re)introduced. By default the ``history`` writer seams
    (:data:`HISTORY_WRITER_SEAMS`) are excluded — they append, they do not consume
    — so the proof measures genuine readers. This function only *proves*; it
    deletes nothing.
    """
    offenders: dict[str, list[str]] = {}
    for field_name in fields:
        readers = find_field_readers(src_root, field_name, exclude_basenames=exclude_basenames)
        if readers:
            offenders[field_name] = readers
    if offenders:
        raise AssertionError(f"zero-reader verification failed; live readers found: {offenders}")


__all__ = [
    "BackfillResult",
    "MigrationOrderingError",
    "VerifyResult",
    "backfill_runtime_state",
    "read_legacy_runtime",
    "verify_backfill",
]
