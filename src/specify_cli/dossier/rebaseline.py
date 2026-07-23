"""One-time re-baseline of recorded snapshot hashes (FR-009, NFR-003, WP05).

WP02 migrated the CLI emit path onto the canonical dossier snapshot hash
(``sha256:``-prefixed, computed over the normalized WP static projection —
see :func:`specify_cli.dossier.hasher.compute_dossier_snapshot_hash`). Snapshot
hashes recorded *before* that cutover were persisted under the retired
concat-of-hashes / bare-hex formula and over the old raw-byte per-artifact
basis, so they are non-comparable with a freshly computed canonical hash. Left
alone they would read as divergent even when nothing changed.

This module provides the one-time re-baseline that recomputes recorded snapshot
hashes under the canonical definition, so unchanged content reconciles as
PARITY after the cutover (FR-009) with zero false-divergence across the local
backlog (NFR-003). It is acceptable to recompute historical hashes because
there are no live hosted customers (spec Assumption A-003).

Design guarantees:

- **Canonical, not re-implemented (C-001).** The hash is produced by re-running
  the live pipeline — :class:`specify_cli.dossier.indexer.Indexer` →
  :func:`specify_cli.dossier.snapshot.compute_snapshot` — the SAME path the
  drift/reconcile surface uses. It does not transform recorded component hashes
  (those carry the retired raw-byte WP basis and would not match a reconcile).
- **Read-only over source artifacts (#2263).** Indexing only reads the mission
  source tree; the re-baseline writes solely to the recorded
  ``.kittify/dossiers/<slug>/snapshot-latest.json`` cache file, never to a
  source artifact.
- **Idempotent.** A snapshot already in the canonical (``sha256:``-prefixed)
  form is left byte-for-byte untouched, so re-running is a no-op.
- **Full re-snapshot, NOT a pure hash reformat (#2883 item 7).** A non-canonical
  recorded hash is replaced by recomputing over *current* source, so any source
  change made since the last emit is absorbed into the new baseline. In other
  words re-baseline silently advances the recorded hash to current source and
  thereby masks any pre-cutover drift. This is intentional for the one-time
  cutover and bounded by A-003 (no live hosted customers); a later reader must
  not mistake it for reformatting the stored value in place.

See: kitty-specs/dossier-parity-reconciler-01KXYXVP/spec.md (FR-009, NFR-003,
A-003) and tasks/WP05-rebaseline-migration.md (T019-T021).
"""

from __future__ import annotations

import json
import logging
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

from specify_cli.dossier.indexer import Indexer
from specify_cli.dossier.manifest import ManifestRegistry
from specify_cli.dossier.snapshot import compute_snapshot

logger = logging.getLogger(__name__)

#: Filename of the recorded per-mission snapshot cache.
SNAPSHOT_FILENAME = "snapshot-latest.json"

#: Prefix that marks the canonical dossier snapshot hash (WP01/WP02, FR-003).
_CANONICAL_PREFIX = "sha256:"

#: Fallback mission type when a mission's ``meta.json`` is typeless/absent —
#: matches :func:`specify_cli.sync.dossier_pipeline.sync_feature_dossier`.
_DEFAULT_MISSION_TYPE = "software-dev"


@dataclass(frozen=True)
class RebaselineOutcome:
    """Result of re-baselining a single recorded snapshot.

    Attributes:
        snapshot_path: The recorded ``snapshot-latest.json`` that was inspected.
        mission_slug: The mission slug (recorded snapshot's ``mission_slug`` or,
            failing that, the dossier directory name).
        old_hash: The recorded hash before re-baseline.
        new_hash: The recorded hash after re-baseline (canonical when changed;
            equal to ``old_hash`` on a no-op or error).
        changed: True when the recorded hash was rewritten (or, under
            ``dry_run``, *would* be rewritten).
        error: A short reason string when the snapshot could not be re-baselined
            (left untouched); ``None`` on success.
    """

    snapshot_path: Path
    mission_slug: str
    old_hash: str
    new_hash: str
    changed: bool
    error: str | None = None


def is_canonical_snapshot_hash(value: str | None) -> bool:
    """True if *value* is already in the canonical ``sha256:``-prefixed form."""
    return value is not None and value.startswith(_CANONICAL_PREFIX)


def iter_recorded_snapshot_files(root: Path) -> Iterator[Path]:
    """Yield every recorded ``snapshot-latest.json`` under *root*, sorted.

    Discovers the ``.kittify/dossiers/<slug>/snapshot-latest.json`` cache files
    written by the live dossier sync, whether *root* is a single mission tree,
    a repository root, or a directory of many missions (the local backlog).

    Args:
        root: Directory to search recursively.

    Yields:
        Paths to recorded snapshot files, in sorted (deterministic) order.
    """
    yield from sorted(root.glob(f"**/.kittify/dossiers/*/{SNAPSHOT_FILENAME}"))


def _resolve_feature_dir(snapshot_path: Path) -> Path:
    """Resolve the mission source directory for a recorded snapshot file.

    Layout: ``<feature_dir>/.kittify/dossiers/<slug>/snapshot-latest.json`` —
    the feature directory is three levels above the enclosing ``<slug>`` dir.
    """
    return snapshot_path.parents[3]


def rebaseline_snapshot_file(snapshot_path: Path, *, dry_run: bool = False) -> RebaselineOutcome:
    """Re-baseline one recorded snapshot to the canonical hash (FR-009).

    Reads the recorded snapshot; if its hash is already canonical it is a no-op
    (idempotent). Otherwise the mission source tree is re-indexed and a fresh
    canonical snapshot is computed via the live pipeline, and the recorded file
    is rewritten in place with the canonical values (unless ``dry_run``).

    The mission source tree is only *read*; the sole write target is the
    recorded snapshot cache file itself (#2263).

    Args:
        snapshot_path: Path to a recorded ``snapshot-latest.json``.
        dry_run: When True, compute the canonical hash and report whether it
            would change, but do not write.

    Returns:
        A :class:`RebaselineOutcome` describing the (potential) change.
    """
    mission_slug = snapshot_path.parent.name
    try:
        data = json.loads(snapshot_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        logger.warning("Cannot read recorded snapshot %s: %s", snapshot_path, exc)
        return RebaselineOutcome(snapshot_path, mission_slug, "", "", changed=False, error="unreadable_snapshot")

    old_hash = str(data.get("parity_hash_sha256", ""))
    mission_slug = str(data.get("mission_slug") or mission_slug)

    # Idempotent: an already-canonical snapshot is left byte-for-byte untouched.
    if is_canonical_snapshot_hash(old_hash):
        return RebaselineOutcome(snapshot_path, mission_slug, old_hash, old_hash, changed=False)

    feature_dir = _resolve_feature_dir(snapshot_path)
    if not feature_dir.is_dir():
        logger.warning("Source dir missing for recorded snapshot %s", snapshot_path)
        return RebaselineOutcome(snapshot_path, mission_slug, old_hash, old_hash, changed=False, error="source_missing")

    # Recompute under the canonical definition by RE-RUNNING the live pipeline
    # over source (never transforming the retired recorded component hashes).
    try:
        from specify_cli.mission import get_mission_type

        mission_type = get_mission_type(feature_dir) or _DEFAULT_MISSION_TYPE
        dossier = Indexer(ManifestRegistry()).index_feature(feature_dir, mission_type)
        snapshot = compute_snapshot(dossier)
    except Exception as exc:  # noqa: BLE001 - one bad mission must not abort the backlog sweep
        logger.warning("Re-index failed for %s: %s", feature_dir, exc)
        return RebaselineOutcome(snapshot_path, mission_slug, old_hash, old_hash, changed=False, error=f"reindex_failed: {exc}")

    new_hash = snapshot.parity_hash_sha256

    if not dry_run:
        # Rewrite the recorded snapshot IN PLACE (same file), so a snapshot
        # whose dossier-dir slug differs from the indexed slug is still updated
        # where it lives. Serialization mirrors snapshot.save_snapshot.
        payload = snapshot.model_dump()
        snapshot_path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")

    return RebaselineOutcome(snapshot_path, mission_slug, old_hash, new_hash, changed=True)


def rebaseline_recorded_snapshots(root: Path, *, dry_run: bool = False) -> list[RebaselineOutcome]:
    """Re-baseline every recorded snapshot under *root* (NFR-003 backlog sweep).

    Discovers all recorded ``snapshot-latest.json`` files and re-baselines each.
    A failure on one mission is captured in its :class:`RebaselineOutcome`
    (``error`` set, ``changed=False``) and never aborts the sweep.

    Args:
        root: Directory to search recursively (repo root or backlog directory).
        dry_run: When True, report changes without writing.

    Returns:
        One :class:`RebaselineOutcome` per discovered recorded snapshot.
    """
    return [rebaseline_snapshot_file(path, dry_run=dry_run) for path in iter_recorded_snapshot_files(root)]
