"""Store + backfill a mission's :class:`MissionTopology` in ``meta.json`` (#2069).

The topology of a mission (the orthogonal coordination × lanes grid cell) used to
be re-inferred from disk/git at every resolve. FR-002/FR-003 make it a **stored,
authoritative** value:

- :func:`read_topology` — the PURE reader (#1814): returns the stored ``topology``
  when present, otherwise derives the shape ONCE via WP01's
  :func:`classify_topology` (the single authority for the 2×2 grid) and returns it
  **without writing**. The read/validate/accept SEAM paths use this so a read never
  mutates ``meta.json``.
- :class:`TopologyBackfillResult` / :func:`backfill_mission_topology` /
  :func:`backfill_topology_repo` — mirror the ``backfill_identity`` precedent: an
  idempotent, canonical-JSON, never-overwrite-an-existing-value migration that the
  ``spec-kitty migrate backfill-topology`` command drives.

``flattened`` is a separate boolean provenance flag (history mark), NOT a topology
value: a mission that lost its ``coordination_branch`` is SINGLE_BRANCH/LANES *and*
``flattened: true``. ``"FLATTENED"`` is never stored as a ``topology``.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from mission_runtime import MissionTopology, classify_topology, routes_through_coordination

from specify_cli.lanes import CorruptLanesError, read_lanes_json
from specify_cli.mission_metadata import load_meta

logger = logging.getLogger(__name__)

# Canonical meta.json keys (hoisted per Sonar S1192 — used in >=3 sites).
_TOPOLOGY_KEY = "topology"
_FLATTENED_KEY = "flattened"
_COORDINATION_BRANCH_KEY = "coordination_branch"

# Valid stored topology string values (the enum's stable .value forms).
_VALID_TOPOLOGY_VALUES = frozenset(member.value for member in MissionTopology)


def _has_lanes(feature_dir: Path) -> bool:
    """Return whether the mission has a ``lanes.json`` (corrupt ⇒ treated absent)."""
    try:
        return read_lanes_json(feature_dir) is not None
    except CorruptLanesError:
        # A corrupt lanes.json is not a usable lanes signal; classify as no-lanes
        # rather than crashing the migration. The corruption surfaces elsewhere.
        logger.warning("Corrupt lanes.json in %s — treating as no lanes", feature_dir.name)
        return False


def _derive_topology(meta: dict[str, Any], feature_dir: Path) -> MissionTopology:
    """Derive the topology from current signals via WP01's single authority."""
    coordination_branch = meta.get(_COORDINATION_BRANCH_KEY) or None
    return classify_topology(coordination_branch, _has_lanes(feature_dir))


def _write_meta_canonical(meta_path: Path, meta: dict[str, Any]) -> None:
    """Persist ``meta`` in the canonical sorted-key form (matches ``backfill_identity``)."""
    content = json.dumps(meta, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    meta_path.write_text(content, encoding="utf-8")


def read_topology(feature_dir: Path) -> MissionTopology:
    """PURE read of a mission's :class:`MissionTopology` — never persists (#1814).

    The read-path counterpart of :func:`backfill_mission_topology`. Returns the
    stored ``topology`` when ``meta.json`` carries a valid value; otherwise derives
    the shape ONCE via WP01's :func:`classify_topology` (from ``coordination_branch``
    + lanes presence) and returns it **without writing**. A read/validate/accept
    path therefore never mutates ``meta.json`` — the read-only-contract that a
    persisting read would violate when wired into the SEAM read paths (the finalize
    ``--validate-only`` / accept-readiness / transactional-read regression, #1814).

    Persisting the back-filled value is the explicit job of
    :func:`backfill_mission_topology` and the ``spec-kitty migrate backfill-topology``
    command — NEVER an incidental side effect of a read.

    Args:
        feature_dir: Absolute path to a mission directory containing ``meta.json``.

    Returns:
        The :class:`MissionTopology` for the mission.

    Raises:
        FileNotFoundError: If ``meta.json`` does not exist.
        ValueError: If ``meta.json`` is not a JSON object.
    """
    # post-#2091 canonical reader: allow_missing=False raises FileNotFoundError
    # on a missing meta.json, on_malformed="raise" (default) raises ValueError
    # on malformed/non-object content -- matching this function's documented
    # Raises: contract byte-for-byte.
    meta: dict[str, Any] = load_meta(feature_dir, allow_missing=False) or {}

    stored = meta.get(_TOPOLOGY_KEY)
    if isinstance(stored, str) and stored in _VALID_TOPOLOGY_VALUES:
        return MissionTopology(stored)

    # Un-backfilled legacy mission: derive the shape ONCE from current signals and
    # return it WITHOUT persisting (the read-only contract — #1814). The explicit
    # backfill command / mint path is the only writer.
    return _derive_topology(meta, feature_dir)


# ---------------------------------------------------------------------------
# Backfill (mirrors backfill_identity.py)
# ---------------------------------------------------------------------------

TopologyBackfillAction = Literal["wrote", "skip", "error"]


@dataclass
class TopologyBackfillResult:
    """Per-mission result from :func:`backfill_mission_topology`.

    Attributes:
        feature_dir: Absolute path to the mission directory.
        slug: Directory name used as the mission slug.
        action: ``"wrote"`` — topology derived and persisted; ``"skip"`` — a valid
            ``topology`` was already present (or no ``meta.json``); ``"error"`` —
            unreadable / corrupt ``meta.json``.
        topology: The stored or newly-derived topology ``.value`` string, or
            ``None`` on error / missing meta.
        reason: Human-readable explanation (populated on ``"skip"``/``"error"``).
    """

    feature_dir: Path
    slug: str
    action: TopologyBackfillAction
    topology: str | None = None
    reason: str | None = None


def backfill_mission_topology(
    feature_dir: Path, *, dry_run: bool = False
) -> TopologyBackfillResult:
    """Idempotently persist ``topology`` into ``<feature_dir>/meta.json``.

    A mission whose ``meta.json`` already carries a valid ``topology`` is a no-op
    (``action="skip"``); an existing value is **never** overwritten. A mission
    lacking the field has its topology derived once via WP01's
    :func:`classify_topology` and written in the canonical sorted-key form, with a
    default ``flattened: false`` provenance flag.

    Args:
        feature_dir: Absolute path to a single mission directory.
        dry_run: When ``True``, report the would-write without touching disk.

    Returns:
        A :class:`TopologyBackfillResult` describing what happened.
    """
    slug = feature_dir.name
    meta_path = feature_dir / "meta.json"

    if not meta_path.exists():
        return TopologyBackfillResult(
            feature_dir=feature_dir,
            slug=slug,
            action="skip",
            reason="meta.json not found",
        )

    try:
        meta: dict[str, Any] = load_meta(feature_dir, allow_missing=False) or {}
    except (FileNotFoundError, ValueError) as exc:
        logger.warning("Corrupt meta.json in %s: %s", slug, exc)
        return TopologyBackfillResult(
            feature_dir=feature_dir,
            slug=slug,
            action="error",
            reason=f"corrupt json: {exc}",
        )

    stored = meta.get(_TOPOLOGY_KEY)
    if isinstance(stored, str) and stored in _VALID_TOPOLOGY_VALUES:
        return TopologyBackfillResult(
            feature_dir=feature_dir,
            slug=slug,
            action="skip",
            topology=stored,
            reason="topology already present",
        )

    topology = _derive_topology(meta, feature_dir)

    # T007 (#2250 / FR-002): a declared ``coordination_branch`` that was never
    # created in git must NOT be backfilled as healthy coord. The probe lives at
    # the WRITE path ONLY — ``read_topology`` / ``_derive_topology`` /
    # ``classify_topology`` stay byte-for-byte pure (C-001: no I/O added there).
    # Reuse the canonical ``_coord_branch_exists`` seam (lazy import — avoids the
    # coordination ↔ migration layer cycle; same pattern as
    # ``_read_path_resolver.py:315``). The seam already fails closed: a non-git
    # directory or an unreadable git state returns ``True`` (branch treated as
    # present), so the normal write path is taken in tests without a git repo and
    # in degraded environments — no false-skip on git unavailability. #2219 cites
    # the analogous repo-global probe precedent.
    if routes_through_coordination(topology):
        coord_branch: str | None = meta.get(_COORDINATION_BRANCH_KEY) or None
        if coord_branch is not None:
            from specify_cli.coordination.surface_resolver import _coord_branch_exists

            _repo_root = feature_dir.parent.parent  # kitty-specs/<slug> → repo root
            if not _coord_branch_exists(_repo_root, coord_branch):
                logger.warning(
                    "Skipping topology backfill for %s: coordination_branch %r is "
                    "absent from git (never created or deleted). Flatten the mission "
                    "(remove coordination_branch from meta.json) or create the branch "
                    "before backfilling. #2250",
                    slug,
                    coord_branch,
                )
                return TopologyBackfillResult(
                    feature_dir=feature_dir,
                    slug=slug,
                    action="skip",
                    reason="coordination_branch absent from git",
                )

    if not dry_run:
        meta[_TOPOLOGY_KEY] = topology.value
        meta.setdefault(_FLATTENED_KEY, False)
        _write_meta_canonical(meta_path, meta)

    return TopologyBackfillResult(
        feature_dir=feature_dir,
        slug=slug,
        action="wrote",
        topology=topology.value,
    )


def backfill_topology_repo(
    repo_root: Path,
    *,
    dry_run: bool = False,
    mission_slug: str | None = None,
) -> list[TopologyBackfillResult]:
    """Walk ``kitty-specs/`` and idempotently backfill every mission's topology.

    Args:
        repo_root: Absolute path to the repository root.
        dry_run: When ``True``, compute results without writing any files.
        mission_slug: When provided, scope the walk to a single mission directory.

    Returns:
        List of :class:`TopologyBackfillResult`, one per mission directory visited.
    """
    kitty_specs = repo_root / "kitty-specs"
    results: list[TopologyBackfillResult] = []

    if not kitty_specs.is_dir():
        logger.warning("kitty-specs/ not found at %s", repo_root)
        return results

    if mission_slug is not None:
        candidates = [
            entry
            for entry in kitty_specs.iterdir()
            if entry.is_dir() and entry.name == mission_slug
        ]
        if not candidates:
            logger.warning("No mission directory found for slug %r", mission_slug)
            return results
    else:
        candidates = sorted(
            entry for entry in kitty_specs.iterdir() if entry.is_dir()
        )

    for feature_dir in candidates:
        results.append(backfill_mission_topology(feature_dir, dry_run=dry_run))

    return results


__all__ = [
    "backfill_topology_repo",
    "read_topology",
]
