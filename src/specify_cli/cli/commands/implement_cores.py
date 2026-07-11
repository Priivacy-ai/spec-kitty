"""Pure decision cores + a minimal git port for ``implement.py`` (WP03 / #2173).

This module extracts the git-porcelain/diff family and the placement-resolution
family that used to live inline in ``cli/commands/implement.py`` into small,
independently testable functions. Any function that needs live git data takes
an injected :class:`GitPort` (T015 "git injected as a port" requirement) so
the decision/parsing logic itself can be exercised in unit tests without a
real repository and without mocking ``subprocess``.

:class:`_SubprocessGitPort` is the ONE git-subprocess I/O boundary in this
module -- a thin adapter, not decision logic. Every port-consuming function
below defaults its ``git`` parameter to :data:`DEFAULT_GIT_PORT` (an instance
of that adapter), so every existing call site in ``implement.py`` -- and every
external test that imports these names directly with their historical,
git-param-free signatures -- keeps working unchanged against real git.

``implement.py`` re-exports the public names from here via a bare import (not
added to its own ``__all__``); see the module docstring there for the shim
contract (T019 / FR-009).
"""

from __future__ import annotations

import json
import subprocess
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import TYPE_CHECKING, Any, NamedTuple, Protocol, runtime_checkable

from mission_runtime import (
    ActionContextError,
    CommitTarget,
    resolve_action_context,
    resolve_topology,
    routes_through_coordination,
)

from specify_cli.core.errors import PlacementResolutionRequired
from specify_cli.status import COORD_OWNED_STATUS_FILES

if TYPE_CHECKING:
    pass

# vcs-lock fields written by ``mission_metadata.set_vcs_lock`` (the canonical
# writer). #2222 / C-003: this lock is one-time VCS-TYPE state, NOT the
# concurrency mutex, so a dependency-free back-to-back claim must not be
# blocked by the prior claim's own uncommitted lock self-write.
_VCS_LOCK_META_FIELDS: frozenset[str] = frozenset({"vcs", "vcs_locked_at"})
_META_JSON_FILENAME = "meta.json"
_MISSING_META_VALUE = object()


# ---------------------------------------------------------------------------
# Git port (T015): the sole I/O boundary in this module.
# ---------------------------------------------------------------------------


@runtime_checkable
class GitPort(Protocol):
    """Minimal git read surface the staging/diff decision cores depend on."""

    def status_porcelain(self, repo_root: Path, target: Path) -> str:
        """Raw ``git status --porcelain --untracked-files=all <target>``
        stdout (empty string on any non-zero exit)."""
        ...

    def show_blob(self, repo_root: Path, ref: str, repo_rel_path: str) -> bytes | None:
        """Bytes of *repo_rel_path* at *ref*, or ``None`` when absent there."""
        ...


class _SubprocessGitPort:
    """Concrete :class:`GitPort` adapter -- real ``git`` subprocess calls.

    This is the ONLY place in the module that shells out. Every core function
    below defaults to :data:`DEFAULT_GIT_PORT` (an instance of this class), so
    unpatched callers see the exact prior behavior while tests can inject a
    fake port to exercise the pure decision logic.
    """

    def status_porcelain(self, repo_root: Path, target: Path) -> str:
        # NOTE: callers must NOT further ``.strip()`` this: porcelain v1 emits
        # "XY<space>PATH" (a fixed 3-char prefix). For a tracked file that is
        # modified-but-not-staged, X is a space (" M path"); stripping the raw
        # stdout would remove the leading space of the *first* line, shifting
        # its columns so ``line[3:]`` truncates the first path character.
        result = subprocess.run(
            ["git", "status", "--porcelain", "--untracked-files=all", str(target)],
            cwd=repo_root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        if result.returncode != 0:
            return ""
        return result.stdout

    def show_blob(self, repo_root: Path, ref: str, repo_rel_path: str) -> bytes | None:
        result = subprocess.run(
            ["git", "show", f"{ref}:{repo_rel_path}"],
            cwd=repo_root,
            capture_output=True,
            check=False,
        )
        if result.returncode != 0:
            return None
        return result.stdout


DEFAULT_GIT_PORT: GitPort = _SubprocessGitPort()


# ---------------------------------------------------------------------------
# git-porcelain/diff family (T015)
# ---------------------------------------------------------------------------


class _PorcelainEntry(NamedTuple):
    """A single ``git status --porcelain`` record for a feature-dir path.

    ``xy`` is the 2-char status code, ``path`` the current/new repo-relative
    path. ``is_structural`` marks deletions and renames/copies -- changes that
    ``BookkeepingTransaction.write_artifact`` (a write-only API) cannot apply,
    so they must be committed to the coordination branch out-of-band or the
    claim must fail closed rather than silently leave the branch incoherent.
    """

    xy: str
    path: str
    is_structural: bool


def _parse_porcelain_entries(raw_stdout: str) -> list[_PorcelainEntry]:
    """Pure parse of raw (unstripped) ``git status --porcelain`` stdout.

    Parses column 3 of each *unstripped* line so a leading-space status code
    on the first line never truncates its path (see
    :meth:`_SubprocessGitPort.status_porcelain`). Deletions and renames/copies
    are classified as structural.
    """
    entries: list[_PorcelainEntry] = []
    for line in raw_stdout.splitlines():
        if len(line) <= 3:
            continue
        xy = line[:2]
        rest = line[3:]
        if " -> " in rest:
            # Rename/copy: "old -> new". The old path must be removed on
            # coord -- a write-only transaction cannot do that, so this is
            # structural.
            new_path = rest.split(" -> ", 1)[1].strip()
            entries.append(_PorcelainEntry(xy=xy, path=new_path, is_structural=True))
            continue
        # Deletions (D in either index or worktree column) are structural too.
        is_structural = "D" in xy
        entries.append(_PorcelainEntry(xy=xy, path=rest.strip(), is_structural=is_structural))
    return entries


def _feature_dir_status_entries(repo_root: Path, feature_dir: Path, *, git: GitPort = DEFAULT_GIT_PORT) -> list[_PorcelainEntry]:
    raw = git.status_porcelain(repo_root, feature_dir)
    return _parse_porcelain_entries(raw)


def _structural_entries(entries: list[_PorcelainEntry]) -> list[_PorcelainEntry]:
    """Deletions/renames/copies -- changes that cannot be auto-committed to the
    coordination branch and must fail closed (#1598)."""
    return [e for e in entries if e.is_structural]


def detect_structural_planning_changes(repo_root: Path, artifact_source_dir: Path, *, git: GitPort = DEFAULT_GIT_PORT) -> list[_PorcelainEntry]:
    """Structural planning-artifact changes from git porcelain alone.

    Independent of coord/topology resolution, so the git-executor can fire the
    #1598 fail-closed guard BEFORE resolving the coordination-branch filter
    (which can raise on a broken topology). Restores the pre-degod ordering
    (#2464 squad-B1) where a structural change is reported to the operator even
    when topology resolution would fault.
    """
    return _structural_entries(_feature_dir_status_entries(repo_root, artifact_source_dir, git=git))


def _exclude_coord_owned(paths: Iterable[str], coord_branch_for_filter: str | None) -> list[str]:
    """Drop the canonical status log/snapshot (``COORD_OWNED_STATUS_FILES``) from
    *paths* on coordination-topology missions only.

    On a coordination mission those files are owned by the transactional emitter on
    the coord branch, and the primary checkout's copies are stale -- committing them
    would clobber the seeded lane state (#1589). On a non-coordination (flat/legacy)
    mission there is no coord authority, so the primary checkout's status files ARE
    canonical and must be committed; excluding them there silently drops a status
    edit (review M3). Single predicate for both commit-path sources (review F-03).
    """
    if coord_branch_for_filter:
        return [p for p in paths if Path(p).name not in COORD_OWNED_STATUS_FILES]
    return list(paths)


def _status_paths_for_commit(entries: list[_PorcelainEntry], coord_branch_for_filter: str | None) -> list[str]:
    """The feature-dir paths to commit from ``git status`` entries -- see
    :func:`_exclude_coord_owned`."""
    return _exclude_coord_owned((e.path for e in entries), coord_branch_for_filter)


def _is_vcs_lock_only_meta_diff(committed: Mapping[str, Any] | None, working: Mapping[str, Any]) -> bool:
    """Pure decision: is the meta.json change ONLY the one-time vcs-lock fields?

    Returns ``True`` iff every key whose value differs between the *committed*
    baseline and the *working*-tree meta.json is a member of
    :data:`_VCS_LOCK_META_FIELDS` (#2222 / C-003). The comparison is on parsed
    JSON, so it is robust to byte-level reformatting by ``write_meta``.

    An empty diff returns ``False`` (nothing to exclude); any non-lock key in
    the diff returns ``False`` so a genuinely dirty meta.json still blocks the
    claim (the required negative guard -- the exclusion is lock-field-only,
    never a blanket meta.json bypass).
    """
    base: Mapping[str, Any] = committed or {}
    changed_keys = {key for key in set(base) | set(working) if base.get(key, _MISSING_META_VALUE) != working.get(key, _MISSING_META_VALUE)}
    return bool(changed_keys) and changed_keys <= _VCS_LOCK_META_FIELDS


def _parse_meta_mapping(raw: bytes) -> dict[str, Any] | None:
    """Parse meta.json *raw* bytes to a dict, or ``None`` when it is not a JSON
    object (defensive: a non-object/corrupt meta is never treated as lock-only)."""
    try:
        parsed = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None
    return parsed if isinstance(parsed, dict) else None


def _committed_meta_mapping(repo_root: Path, repo_rel: str, ref: str | None, *, git: GitPort = DEFAULT_GIT_PORT) -> dict[str, Any] | None:
    """The committed meta.json mapping at *ref* (or ``HEAD`` for flat/legacy
    missions), or ``None`` when the path is absent there or unparseable."""
    blob = git.show_blob(repo_root, ref or "HEAD", repo_rel)
    if blob is None:
        return None
    return _parse_meta_mapping(blob)


def _drop_vcs_lock_only_meta(
    repo_root: Path,
    paths: list[str],
    ref: str | None,
    *,
    auto_commit: bool,
    git: GitPort = DEFAULT_GIT_PORT,
) -> list[str]:
    """Drop a vcs-lock-only meta.json change from the dirty-tree claim guard.

    #2222 / C-003: ``mission_metadata.set_vcs_lock`` writes a one-time VCS-TYPE
    lock to meta.json -- never the concurrency mutex. Under ``auto_commit=False``
    the prior dependency-free claim leaves that self-write uncommitted; without
    this exclusion the next claim's dirty-tree guard wrongly aborts. Excluding a
    lock-only diff is stop-gating (the lock stays uncommitted), NOT
    auto-committing it, and opens no race.

    Byte-identical no-op on the default ``auto_commit=True`` path (NFR-001): the
    exclusion is gated here so the guard's commit set is untouched when
    auto-commit is on. The exclusion is scoped strictly to the lock-field-only
    diff (see :func:`_is_vcs_lock_only_meta_diff`); any non-lock meta.json edit
    is kept and still blocks the claim.
    """
    if auto_commit:
        return paths
    kept: list[str] = []
    for repo_rel in paths:
        if Path(repo_rel).name != _META_JSON_FILENAME:
            kept.append(repo_rel)
            continue
        source = (repo_root / Path(repo_rel)).resolve()
        if not source.exists():
            kept.append(repo_rel)
            continue
        working = _parse_meta_mapping(source.read_bytes())
        committed = _committed_meta_mapping(repo_root, repo_rel, ref, git=git)
        if working is not None and _is_vcs_lock_only_meta_diff(committed, working):
            continue
        kept.append(repo_rel)
    return kept


def _files_changed_vs_ref(repo_root: Path, files: list[str], ref: str | None, *, git: GitPort = DEFAULT_GIT_PORT) -> list[str]:
    """Drop files whose working-tree content already matches *ref*.

    The coordination model commits claim-time planning-artifact edits to the
    coordination branch but leaves them uncommitted in the main checkout. The
    next claim re-discovers those edits as "uncommitted" even though their
    content is already on the coordination branch. Committing them again would
    produce an empty commit, which ``safe_commit`` rejects ("git commit failed")
    -- silently blocking every claim after the first. Filtering to genuinely
    changed files makes the planning-artifact commit idempotent.
    """
    if not ref:
        return files
    changed: list[str] = []
    for repo_rel in files:
        source = (repo_root / Path(repo_rel)).resolve()
        if not source.exists():
            # Defensive: callers pass only writable (non-structural) paths, which
            # exist on disk. Structural deletions/renames are rejected upstream
            # (fail-closed) before reaching here, so a missing path here is
            # unexpected -- skip it rather than crash the claim.
            continue
        if git.show_blob(repo_root, ref, repo_rel) != source.read_bytes():
            changed.append(repo_rel)
    return changed


# ---------------------------------------------------------------------------
# T016: pure staging-decision core for _ensure_planning_artifacts_committed_git
# ---------------------------------------------------------------------------


class PlanningArtifactStagingPlan(NamedTuple):
    """Result of :func:`resolve_planning_artifact_staging`.

    ``structural`` non-empty means the claim must fail closed (the caller
    prints the offending entries and exits); every other field is meaningless
    in that case. Otherwise ``files_to_commit`` is the final (deduped,
    idempotency-filtered) set to stage, and ``status_paths_to_commit`` is the
    subset that came from live ``git status`` entries (used by the caller to
    decide whether to print the "not committed" instructions).
    """

    structural: list[_PorcelainEntry]
    files_to_commit: list[str]
    status_paths_to_commit: list[str]


def resolve_planning_artifact_staging(
    repo_root: Path,
    artifact_source_dir: Path,
    coord_branch_for_filter: str | None,
    extra_file_paths: list[str],
    *,
    auto_commit: bool,
    git: GitPort = DEFAULT_GIT_PORT,
) -> PlanningArtifactStagingPlan:
    """Pure staging decision for planning-artifact commits (T016).

    Mirrors the pre-extraction body of
    ``_ensure_planning_artifacts_committed_git`` (#1598 fail-closed structural
    guard, #2222 vcs-lock exclusion, idempotency filtering) with zero
    console/typer side effects -- the git-executor caller in ``implement.py``
    turns a non-empty ``structural`` into the fail-closed print+exit, and an
    empty ``files_to_commit`` into a silent no-op return.

    ``extra_file_paths`` is the caller-supplied ``_feature_dir_file_paths``
    listing (a plain filesystem walk, not part of this git-porcelain core);
    passing it in keeps this function's git surface limited to ``git status``
    and ``git show`` via the injected port.
    """
    entries = _feature_dir_status_entries(repo_root, artifact_source_dir, git=git)
    structural = _structural_entries(entries)
    if structural:
        return PlanningArtifactStagingPlan(structural=structural, files_to_commit=[], status_paths_to_commit=[])

    status_paths = _status_paths_for_commit(entries, coord_branch_for_filter)
    status_paths = _drop_vcs_lock_only_meta(repo_root, status_paths, coord_branch_for_filter, auto_commit=auto_commit, git=git)
    files_to_commit = list(status_paths)
    if coord_branch_for_filter:
        files_to_commit.extend(_exclude_coord_owned(extra_file_paths, coord_branch_for_filter))
    files_to_commit = list(dict.fromkeys(files_to_commit))
    files_to_commit = _drop_vcs_lock_only_meta(repo_root, files_to_commit, coord_branch_for_filter, auto_commit=auto_commit, git=git)
    if not files_to_commit:
        return PlanningArtifactStagingPlan(structural=[], files_to_commit=[], status_paths_to_commit=[])

    # Idempotency guard: skip files already identical on the coordination branch
    # so a re-discovered (but already-committed) edit does not produce an empty
    # commit that ``safe_commit`` rejects. See ``_files_changed_vs_ref``.
    files_to_commit = _files_changed_vs_ref(repo_root, files_to_commit, coord_branch_for_filter, git=git)
    if not files_to_commit:
        return PlanningArtifactStagingPlan(structural=[], files_to_commit=[], status_paths_to_commit=[])

    status_paths_to_commit = _files_changed_vs_ref(repo_root, status_paths, coord_branch_for_filter, git=git)
    return PlanningArtifactStagingPlan(
        structural=[],
        files_to_commit=files_to_commit,
        status_paths_to_commit=status_paths_to_commit,
    )


# ---------------------------------------------------------------------------
# placement family (T015)
# ---------------------------------------------------------------------------


def _resolve_placement_ref(repo_root: Path, *, mission_slug: str, wp_id: str) -> CommitTarget | None:
    """Resolve the context's artifact-placement ref (C-PLACE-1 / IC-05).

    Routes through the single canonical resolver (``resolve_action_context``,
    C-CTX-1) and returns ``context.artifact_placement.placement_ref`` -- the ONE
    :class:`CommitTarget` that planning artifacts AND status events resolve to.
    On any resolution failure it returns ``None`` so the caller keeps the legacy
    meta-derived placement path (C-004 strangler: never break the implement
    lifecycle on a context-resolution edge case).
    """
    try:
        context = resolve_action_context(
            repo_root,
            action="implement",
            feature=mission_slug,
            wp_id=wp_id,
        )
    except ActionContextError:
        return None
    placement = context.artifact_placement
    return placement.placement_ref if placement is not None else None


def _resolve_claim_commit_target(placement_ref: CommitTarget | None) -> CommitTarget:
    """Resolve the WP status claim-commit target (T012 / D11 fail-closed).

    A small, pure extraction (Sonar-testable) over the single seam-resolved
    ``placement_ref`` (the SAME :class:`CommitTarget` planning artifacts AND
    status events resolve to, C-PLACE-1). Replaces the forbidden
    ``_get_current_branch(repo_root) or planning_branch`` grammar: when
    ``placement_ref`` failed to resolve, this FAILS CLOSED with
    :class:`PlacementResolutionRequired` instead of silently committing the
    WP claim to whatever branch happens to be checked out.
    """
    if placement_ref is None:
        raise PlacementResolutionRequired(
            "Cannot resolve the canonical write placement for this mission's "
            "WP status claim commit -- refusing to commit to the currently "
            "checked-out branch (D11 fail-closed). This usually means the "
            "mission's stored topology could not be resolved (e.g. a "
            "coordination branch declared in meta.json is missing/torn down "
            "in git). Run `spec-kitty doctor workspaces --fix`, or flatten "
            "the mission by removing `coordination_branch` from meta.json if "
            "the coordination topology was never used, then retry."
        )
    return placement_ref


def _placement_coord_filter(repo_root: Path, mission_slug: str, placement_ref: CommitTarget | None) -> str | None:
    """Return the coord-owned-exclusion ref implied by the mission's topology.

    The coord/flattened/primary decision reads the STORED topology via the ONE
    canonical :func:`routes_through_coordination` predicate -- never a per-ref
    ``.kind`` (the retired arm) and not independent meta.json/git logic
    (C-005). Only a genuine *coordination* topology owns the status files on a
    separate branch and therefore excludes them from the primary-checkout
    commit; a flattened/primary topology has no primary/coord split, so the
    primary status files are NOT filtered out. The excluded ref is the
    context's single ``placement_ref.ref`` (the SAME CommitTarget status
    events resolve to). Returns ``None`` for flattened/primary topologies.
    """
    if placement_ref is None:
        return None
    if routes_through_coordination(resolve_topology(repo_root, mission_slug)):
        return placement_ref.ref
    return None
