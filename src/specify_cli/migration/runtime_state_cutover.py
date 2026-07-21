"""Cutover orchestration: seed runtime state, fail-closed verify, atomic flip.

The **single** invocable spine step (research D-01): one shared
:func:`cutover_mission` helper implements ``backfill -> fail-closed verify ->
atomic per-mission ``status_phase`` flip`` so the load-bearing atomicity lives in
exactly one place. Both the operator CLI (``spec-kitty migrate
backfill-runtime-state``) and — in a later WP — the upgrade migration reuse this
helper; neither re-implements verify-then-flip.

Fail-closed contract (FR-003 / NFR-001 / INV-1):

* :func:`cutover_mission` is the **sole production writer** of ``meta.json``
  ``status_phase``.
* It flips to the snapshot-authority value **only** after an ``ok`` verify. The
  flip phase (:func:`_flip_phase`) is structurally unreachable on a non-``ok``
  verify, a :class:`MigrationOrderingError`, or a per-mission backfill error — so
  a divergent-state mission is *never* flipped (zero silent data loss).
* The write target resolves via :func:`canonicalize_feature_dir` — never
  ``Path.cwd()`` and never a raw worktree/root alias — so no ``status_phase`` (or
  event) write ever lands at the repo root (INV-5 / C-003 / #2815). This helper
  adds **no** event-write path of its own: all seed events go through the backfill
  library, which already canonicalizes.

Idempotency (NFR-002 / INV-4): the backfill mints byte-identical deterministic
seed ids (a re-run seeds nothing) and :func:`_flip_phase` short-circuits when the
phase is already snapshot-authority, so a second run seeds nothing and re-flips
nothing (byte-stable).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from specify_cli.core.paths import assert_safe_path_segment
from specify_cli.core.utils import ensure_within_any
from specify_cli.mission_metadata import load_meta, write_meta
from specify_cli.workspace import canonicalize_feature_dir

from .backfill_runtime_state import (
    BackfillResult,
    MigrationOrderingError,
    VerifyResult,
    backfill_runtime_state,
    verify_backfill,
)

logger = logging.getLogger(__name__)

#: The ``meta.json`` key this helper is the sole production writer of.
_STATUS_PHASE_KEY = "status_phase"

#: The snapshot-authority ``status_phase`` value written by the flip (contract
#: step 5). Stored as a string; ``status.emit._read_status_phase`` parses it via
#: ``int("1")`` unchanged. Any parsed phase ``>= 1`` counts as already-flipped.
_SNAPSHOT_AUTHORITY_PHASE = "1"


@dataclass
class CutoverResult:
    """Per-mission outcome of :func:`cutover_mission`.

    Attributes:
        slug: The mission slug (directory name).
        flipped: True iff this run wrote the snapshot-authority ``status_phase``.
        would_flip: Dry-run signal — True iff verify passed against the
            current (already-seeded) state, with nothing written. A mission
            that still needs seeding fails verify first (a dry-run writes no
            seeds), so ``would_flip`` never fires for it; the dry-run signal
            for that case is the operator-facing ``would_seed`` (derived from
            ``seeded_count > 0`` in the CLI layer).
        seeded_count: NEW seed events appended this run (0 on an idempotent
            re-run or a dry-run over an already-seeded corpus).
        verify: The fail-closed :class:`VerifyResult`, or ``None`` when the run
            aborted before verify (ordering error / backfill error).
        error: Human-readable abort reason (ordering error / backfill error), or
            ``None`` on a clean run.
    """

    slug: str
    flipped: bool
    would_flip: bool = False
    seeded_count: int = 0
    verify: VerifyResult | None = None
    error: str | None = None


def _seed_phase(feature_dir: Path, *, dry_run: bool) -> BackfillResult:
    """Phase 1 — idempotently seed the mission's legacy runtime state as events.

    Thin wrapper over :func:`backfill_runtime_state`; extracted so the seed step
    is independently unit-testable and :func:`cutover_mission` stays trivial.
    """
    return backfill_runtime_state(feature_dir, dry_run=dry_run)


def _verify_phase(feature_dir: Path) -> VerifyResult:
    """Phase 2 — fail-closed count+value parity of the snapshot vs the OLD reader.

    Thin wrapper over :func:`verify_backfill`; a non-``ok`` result makes the flip
    phase unreachable in :func:`cutover_mission`.
    """
    return verify_backfill(feature_dir)


def _flip_phase(feature_dir: Path) -> None:
    """Phase 3 — the SOLE ``status_phase`` writer; only reached on an ``ok`` verify.

    Resolves the write target via :func:`canonicalize_feature_dir` (never
    ``Path.cwd()`` / a raw alias — INV-5 / C-003) and writes the snapshot-authority
    value with a tolerant ``validate=False`` write: this mutates exactly one key on
    a possibly-legacy ``meta.json`` that may lack unrelated required identity
    fields, so it must not fail the whole flip on an unrelated schema gap (the
    documented ``doc_state`` tolerant-write precedent).

    Idempotent: short-circuits when the phase is already snapshot-authority, so a
    re-run writes zero bytes (INV-4).
    """
    target = canonicalize_feature_dir(feature_dir)
    meta = load_meta(target, allow_missing=True, on_malformed="raise") or {}
    if _is_snapshot_authority(meta):
        return
    meta[_STATUS_PHASE_KEY] = _SNAPSHOT_AUTHORITY_PHASE
    write_meta(target, meta, validate=False)
    logger.info("Flipped status_phase -> %s for %s", _SNAPSHOT_AUTHORITY_PHASE, target.name)


def _is_snapshot_authority(meta: dict[str, object]) -> bool:
    """Return True iff *meta* already declares a snapshot-authority phase (>= 1)."""
    try:
        return int(str(meta.get(_STATUS_PHASE_KEY)).strip()) >= 1
    except (TypeError, ValueError):
        return False


def cutover_mission(feature_dir: Path, *, dry_run: bool = False) -> CutoverResult:
    """Seed -> fail-closed verify -> atomic ``status_phase`` flip for one mission.

    Orchestrates the three phases per the IC-01 contract, **branching on
    ``verify.ok`` without raising** so every path returns a :class:`CutoverResult`:

    1. seed (:func:`_seed_phase`); a :class:`MigrationOrderingError` (strip ran
       before verify) or a per-mission backfill error aborts with ``flipped=False``
       and ``error`` set — never a partial flip;
    2. verify (:func:`_verify_phase`); ``not verify.ok`` returns ``flipped=False``
       (the flip is unreachable — NFR-001 / INV-1);
    3. ``dry_run`` returns ``would_flip=verify.ok`` writing nothing;
    4. otherwise flip (:func:`_flip_phase`) and return ``flipped=True``.

    Args:
        feature_dir: kitty-specs mission directory (canonicalized downstream).
        dry_run: When True, seed nothing / flip nothing; report would-seed counts.

    Returns:
        A :class:`CutoverResult` describing the outcome.
    """
    slug = feature_dir.name
    try:
        seed = _seed_phase(feature_dir, dry_run=dry_run)
    except MigrationOrderingError as exc:
        return CutoverResult(slug=slug, flipped=False, error=str(exc))

    slug = seed.slug
    if seed.action == "error":
        return CutoverResult(slug=slug, flipped=False, seeded_count=seed.seeded_count, error=seed.reason)

    try:
        verify = _verify_phase(feature_dir)
    except MigrationOrderingError as exc:
        return CutoverResult(slug=slug, flipped=False, seeded_count=seed.seeded_count, error=str(exc))

    if not verify.ok:
        return CutoverResult(slug=slug, flipped=False, seeded_count=seed.seeded_count, verify=verify)

    if dry_run:
        return CutoverResult(slug=slug, flipped=False, would_flip=True, seeded_count=seed.seeded_count, verify=verify)

    _flip_phase(feature_dir)
    return CutoverResult(slug=slug, flipped=True, seeded_count=seed.seeded_count, verify=verify)


def cutover_repo(
    repo_root: Path,
    *,
    dry_run: bool = False,
    mission_slug: str | None = None,
) -> list[CutoverResult]:
    """Walk ``kitty-specs/`` (or a single ``--mission`` dir) and cutover each mission.

    Mirrors :func:`~specify_cli.migration.backfill_runtime_state.backfill_runtime_state_repo`:
    the write target is always resolved from each mission directory (never
    ``Path.cwd()`` — C-003), and each mission is processed independently
    (per-mission best-effort — research D-03). Keeping the walk here (not in the
    CLI body) keeps the command thin and the walk unit-testable.

    Args:
        repo_root: Absolute path to the repository root.
        dry_run: When True, seed/flip nothing; report would-seed counts.
        mission_slug: When provided, scope the walk to a single mission directory.

    Returns:
        One :class:`CutoverResult` per mission directory visited (empty when there
        is no ``kitty-specs/`` or the named mission does not exist).
    """
    kitty_specs = repo_root / "kitty-specs"
    if not kitty_specs.is_dir():
        logger.warning("kitty-specs/ not found at %s", repo_root)
        return []

    if mission_slug is not None:
        assert_safe_path_segment(mission_slug)
        candidate = kitty_specs / mission_slug
        if not candidate.is_dir():
            logger.warning("No mission directory found for slug %r", mission_slug)
            return []
        try:
            candidates = [ensure_within_any(candidate, roots=[kitty_specs])]
        except ValueError as exc:
            raise ValueError(
                f"Mission directory resolves outside kitty-specs: {candidate}"
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

    return [cutover_mission(feature_dir, dry_run=dry_run) for feature_dir in candidates]


__all__ = [
    "CutoverResult",
    "cutover_mission",
    "cutover_repo",
]
