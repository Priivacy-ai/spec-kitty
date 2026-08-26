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

Org-awareness (FR-003, mission cascade-org-inert-01M07E9P, WP01)
------------------------------------------------------------------

Until this WP, ``Indexer`` was constructed with no ``repo_root``
(``Indexer(ManifestRegistry())``), so a configured org pack's
``expected-artifacts.yaml`` override never reached ``rebaseline`` — unlike
every other caller of ``Indexer`` (``reconcile.py``, ``sync/dossier_pipeline.py``,
both already thread ``repo_root``).

**T001 worktree investigation (outcome (a) — worktrees never carry dossier
snapshots). Historical evidence trail, recorded before the sync transport was
deleted (issue #5): every ``sync/dossier_pipeline.py`` site it names is gone,
the conclusion (worktrees never carry snapshots) still describes this module's
guarantee.** Evidence trail. ``Indexer.__init__``'s docstring frames
``repo_root`` as the value threaded into
``manifest_registry.load_manifest(mission_type, repo_root=...)``
(``indexer.py:89-102``); the sole write site for a recorded snapshot is
``save_snapshot`` (``dossier/snapshot.py:154``), called from exactly one
production function, the private helper ``_emit_snapshot``
(``sync/dossier_pipeline.py:117``, ``save_snapshot`` call at line 140).
``_emit_snapshot`` has exactly one caller, ``sync_feature_dossier``
(``sync/dossier_pipeline.py:264``, calls ``_emit_snapshot`` at line 355),
itself only ever invoked via ``trigger_feature_dossier_sync_if_enabled``
(``sync/dossier_pipeline.py:413``). Reaching that function is possible two
ways — DIRECT calls, and one INDIRECT fan-out registered at import time —
both traced below.

*(A) Direct calls.* Nine production call sites call
``trigger_feature_dossier_sync_if_enabled`` (or a same-named thin wrapper
around it) directly:
``cli/commands/agent/tasks_mark_status.py``, ``workflow_executor.py`` (the
``implement``/claim path), ``mission_finalize.py``,
``mission_setup_plan.py``, ``mission_record_analysis.py``, ``research.py``,
``merge/executor.py:1300`` (``_phase_dossier_and_stale``, the
``spec-kitty merge`` post-merge phase — passes ``run.main_repo``, a field
explicitly named/typed as the main checkout), and two migration flows —
``migration/backfill_identity.py:265-277`` (``_rehash_modified_missions``,
the ``migrate backfill-identity`` flow) and
``migration/normalize_mission_lifecycle.py:108-111``
(``_apply_identity_normalization``, the ``migrate
normalize-mission-lifecycle`` flow). All nine resolve their own
``repo_root`` via ``locate_project_root()`` (``core/paths.py:182`` —
docstring: "Locate the MAIN spec-kitty project root directory, **even from
within worktrees**" / "returns Path to MAIN project root (not worktree)"),
the equivalent ``find_repo_root()`` (``task_utils/support.py:45``, itself
delegating to the same primitive), or ``get_main_repo_root()``
(``core/paths.py:451`` — "Get the main repository root, even if called from
a worktree" — reached transitively via ``workflow.py:791``,
``main_repo_root = get_main_repo_root(repo_root)``, which
``workflow_executor.py`` then takes as given per its own docstring at
``workflow_executor.py:513-515``); the two ``migrate_cmd.py`` flows call
``locate_project_root()`` directly (``cli/commands/migrate_cmd.py:265`` for
``backfill-identity``, and the equivalent pattern at the sibling
``normalize-mission-lifecycle`` command). ``migrate rebaseline`` itself
(``cli/commands/migrate_cmd.py``, ``rebaseline_dossier_hashes``) resolves
its own ``repo_root`` the same way.

*(B) Indirect fan-out — the previously-unexamined pathway.*
``sync/__init__.py``'s ``_dossier_sync_handler`` (``sync/__init__.py:198``,
registered at import time via ``register_default_handlers()`` at
``sync/__init__.py:455-456``, gated only by the test-only
``SPEC_KITTY_SYNC_MINIMAL_IMPORT`` env var) forwards straight into
``trigger_feature_dossier_sync_if_enabled``. It is invoked via
``fire_dossier_sync`` (``status/adapters.py:219``) from
``status/emit.py:806`` (inside ``emit_status_transition``) and
``status/emit.py:966`` (inside ``emit_status_transition_batch``) — this
repo's canonical entry point for every WP lane transition. Both call sites
pass ``repo_root`` **as given by the caller**, not re-derived internally:
``emit_status_transition``/``emit_status_transition_batch`` take
``repo_root: Path | None`` as a plain parameter and only fire the sync when
it is not ``None`` (``status/emit.py:805``, ``:963-966``). The transactional
wrapper most production callers actually use,
``emit_status_transition_transactional``
(``coordination/status_transition.py:1295``), routes dossier sync through
``_defer_dossier_sync`` (``status_transition.py:945``, invoked at
``status_transition.py:1384`` and, from the batch variant, ``:1642``) with
``repo_root=request.repo_root`` — the RAW ``TransitionRequest.repo_root``
field (``status/models.py:839``, default ``None``), not the internally
re-resolved ``identity.repo_root`` the same function uses for its own
``BookkeepingTransaction`` locking. So the question this WP must answer is
empirical: what value does every production ``TransitionRequest`` that
reaches this fan-out actually carry in ``repo_root``? Traced every
production constructor that sets it explicitly:

- ``cli/commands/implement.py:1441`` — ``repo_root=find_repo_root()``
  (``implement.py:1132``/``:1763``), the same worktree-aware primitive as
  (A).
- ``cli/commands/agent/workflow_executor.py:783`` (``start_implementation_
  status``, the claim path) and ``:1685`` (``start_review_status``, the
  review-claim path) — both ``repo_root=main_repo_root``, sourced from
  ``workflow.py:791``'s ``get_main_repo_root(repo_root)`` per (A) above.
- ``cli/commands/agent/tasks_move_task.py:2086`` (``_mt_emit_transitions``,
  the ``spec-kitty agent tasks move-task`` command — an emit call site not
  covered by the original enumeration) — ``repo_root=st.main_repo_root``,
  set in ``_mt_resolve_targets`` via ``tasks_shared.py:184``'s
  ``_ensure_target_branch_checked_out`` → ``get_main_repo_root(repo_root)``
  (explicit in-code comment there: "keep main-repo-root resolution so
  canonical serialization pins to the primary checkout regardless of where
  the operator stands").
- ``cli/commands/agent/status.py:331`` (``MissionStatus.transition()``, via
  ``status/aggregate.py:605``, the single production caller of that
  aggregate method) — ``repo_root=main_repo_root``, resolved at
  ``status.py:149`` via ``get_main_repo_root(repo_root)``.
- ``merge/done_bookkeeping.py:228`` and ``:382`` — ``repo_root=repo_root``
  (param), threaded from ``merge/executor.py``'s ``run.main_repo`` per (A).
- ``orchestrator_api/commands.py:1435`` — ``repo_root=main_repo_root``, via
  ``_get_main_repo_root()`` → ``get_main_repo_root(cwd)``
  (``orchestrator_api/commands.py:245-253``).
- ``lanes/recovery.py:813`` (crash recovery, ``execution_mode="worktree"``)
  — ``repo_root=repo_root`` (param), threaded from ``implement.py``'s
  ``find_repo_root()``-rooted flow.
- ``status/work_package_lifecycle.py`` (``start_implementation_status``/
  ``start_review_status``, called from the ``workflow_executor.py`` and
  ``orchestrator_api/commands.py`` sites above) — passes through the same
  already-resolved ``repo_root`` its callers supply.

Every one of these resolves through ``get_main_repo_root()``,
``find_repo_root()``, or ``locate_project_root()`` before it ever reaches
``TransitionRequest.repo_root`` — so, empirically, no production
``fire_dossier_sync`` call observed today carries a worktree-scoped
``repo_root``. One asymmetric gap surfaced during this trace (noted, not a
worktree-exposure risk, and out of this WP's scope to fix):
``status/bootstrap.py:163`` constructs a ``TransitionRequest`` for the
``finalize-tasks`` genesis→planned bootstrap seed with no ``repo_root=`` at
all, so — per the ``is not None`` guard above — dossier sync is silently
*skipped* there rather than mis-scoped.

``.kittify/dossiers/`` is also gitignored (``.gitignore:66,82,86,87``), so a
worktree checkout cannot inherit a stray recorded snapshot via git either.

Net: every real write path for a recorded snapshot funnels through the
PRIMARY/main checkout, never a ``.worktrees/<slug>-<mid8>-lane-<id>/`` path
— but this holds only because every current constructor of a
dossier-sync-carrying request happens to thread a main-checkout-resolved
value; ``repo_root`` is not re-derived or worktree-corrected at the
``fire_dossier_sync``/``_defer_dossier_sync`` boundary itself. A future
caller that constructs a ``TransitionRequest`` with an unresolved cwd-based
``repo_root`` (e.g. plain ``Path(".")`` from inside a worktree, mirroring
the example in this module's own sibling docstring at
``status/aggregate.py:9``, which is safe today only because its one real
caller — ``status.py:152``/``:193`` — overrides it with
``get_main_repo_root``) would silently defeat this invariant with no gate
to catch it; a regression here would not fail loudly, it would just read
the wrong project's org config. Derivation (B) — deriving ``repo_root``
per-snapshot from ``feature_dir.parent.parent`` inside
``rebaseline_snapshot_file`` — is therefore correct as specced today, with
**no** worktree-aware correction needed in ``rebaseline.py`` itself.

**Fail-safe, not forced.** The derivation still only holds because every
production writer's PRIMARY-partition resolution is literally
``<repo_root>/KITTY_SPECS_DIR/<mission_slug>`` — a structural invariant, not
merely an assumption. ``_derive_repo_root`` below checks that invariant
(``feature_dir.parent.name == KITTY_SPECS_DIR``) before deriving anything,
and returns ``None`` (today's org-blind behavior) when it does not hold —
e.g. a hand-placed or legacy-layout snapshot not nested under
``kitty-specs/``. A wrong ``repo_root`` is worse than none: it would silently
read a *different* project's org config.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

from specify_cli.core.constants import KITTY_SPECS_DIR
from specify_cli.dossier.indexer import Indexer
from specify_cli.dossier.manifest import ManifestRegistry
from specify_cli.dossier.snapshot import compute_snapshot

logger = logging.getLogger(__name__)

#: Filename of the recorded per-mission snapshot cache.
SNAPSHOT_FILENAME = "snapshot-latest.json"

#: Prefix that marks the canonical dossier snapshot hash (WP01/WP02, FR-003).
_CANONICAL_PREFIX = "sha256:"

#: Fallback mission type when a mission's ``meta.json`` is typeless/absent —
#: the same default the deleted sync dossier pipeline used.
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


def _derive_repo_root(feature_dir: Path) -> Path | None:
    """Derive the owning project's ``repo_root`` from a mission ``feature_dir``
    (FR-003, derivation (B)).

    Every production writer of a recorded dossier snapshot resolves
    ``feature_dir`` to ``<repo_root>/KITTY_SPECS_DIR/<mission_slug>`` (see this
    module's docstring, "Org-awareness" section, for the full T001 evidence
    trail) — so ``repo_root = feature_dir.parent.parent`` is correct whenever
    ``feature_dir``'s immediate parent is actually named ``KITTY_SPECS_DIR``.
    That check is the one structural invariant the whole derivation depends
    on, and it is verified here rather than assumed.

    Fails SAFE — returns ``None`` (today's org-blind behavior, identical to
    before this WP) — when the invariant does not hold, e.g. a hand-placed or
    legacy-layout snapshot not nested under ``kitty-specs/``. A wrong
    ``repo_root`` is worse than none: it would silently read a *different*
    project's org config.
    """
    if feature_dir.parent.name != KITTY_SPECS_DIR:
        return None
    return feature_dir.parent.parent


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
        repo_root = _derive_repo_root(feature_dir)
        dossier = Indexer(ManifestRegistry(), repo_root=repo_root).index_feature(feature_dir, mission_type)
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
