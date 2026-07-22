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
import re
import subprocess
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any, NamedTuple, Protocol, runtime_checkable

from mission_runtime import (
    ActionContextError,
    CommitTarget,
    is_coordination_artifact_residue_path,
    resolve_action_context,
    resolve_topology,
    routes_through_coordination,
)
from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

from specify_cli.core.errors import PlacementResolutionRequired
from specify_cli.frontmatter import WP_RUNTIME_FIELDS
from specify_cli.status import COORD_OWNED_STATUS_FILES
from specify_cli.task_utils.support import split_frontmatter

# vcs-lock fields written by ``mission_metadata.set_vcs_lock`` (the canonical
# writer). #2222 / C-003: this lock is one-time VCS-TYPE state, NOT the
# concurrency mutex, so a dependency-free back-to-back claim must not be
# blocked by the prior claim's own uncommitted lock self-write.
_VCS_LOCK_META_FIELDS: frozenset[str] = frozenset({"vcs", "vcs_locked_at"})
_META_JSON_FILENAME = "meta.json"
_MISSING_META_VALUE = object()

# tasks/WP##[-slug].md filenames (#2570.1) -- e.g. "WP01.md" or the canonical
# "WP01-allocator-runtime-frontmatter.md" shape ``find_wp_file`` resolves
# (see its ``wp_name_re``). The runtime-frontmatter exclusion below is scoped
# to exactly this shape, never a generic "*.md" match.
_WP_FILENAME_PATTERN = re.compile(r"^WP\d{2}(?:[-_.].+)?\.md$", re.IGNORECASE)


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


def _commit_target_ref_for(planning_branch: str | None) -> str:
    """The ONE cli-local expression the read side and the write side both
    derive the PRIMARY-partition ref from (FR-005, ref half; #2650 / WP04).

    Pre-unification, the read side (:func:`resolve_precondition_ref`) hard-
    coded the git-rev shorthand ``"HEAD"`` inline and the write side
    (``implement.py::_commit_planning_artifacts_transaction``'s PRIMARY-group
    destination) hard-coded the mission's ``planning_branch`` name inline --
    two independently-written literals that happened to agree only because
    every real claim runs from a checkout whose ``HEAD`` IS ``planning_branch``.
    A detached-HEAD or off-target-branch checkout could silently break that
    coincidence. Routing both sides through this single function removes the
    two-literal duplication (NFR-004): a future edit to "what counts as the
    PRIMARY ref" can only be made here, once.

    ``planning_branch`` is ``None`` at the read-side call sites in this module
    (``resolve_precondition_ref`` resolves a ref PER PATH, not per branch --
    no branch name is in scope there) and always a real branch name at the
    write-side call sites in ``implement.py`` (the mission's actual commit
    destination is already resolved by the time the commit runs).

    ``planning_branch or "HEAD"`` is NOT the C-009-forbidden default-BRANCH
    fallback: an absent/empty ``planning_branch`` resolves to the LOCAL
    CHECKOUT (``"HEAD"``, the read side's original constant), never a
    hardcoded branch name such as ``main``. Pure: no filesystem/git side
    effects.
    """
    return planning_branch or "HEAD"


def resolve_precondition_ref(repo_rel_path: str, coord_branch_for_filter: str | None) -> str:
    """Resolve the SINGLE ref *repo_rel_path* must be compared against for the
    implement-claim precondition (contracts/resolve-precondition-ref.md,
    corrected post-tasks-squad; FR-001/FR-002/BLOCKER-2).

    Per-path, not per-staging-call: on a coordination mission
    ``coord_branch_for_filter`` is one non-``None`` branch for every
    candidate, so only the PATH distinguishes a PRIMARY ``spec.md`` (compares
    against the primary/target branch -- ``HEAD`` in the local checkout) from
    a COORD ``status.events.jsonl`` (compares against the coordination ref).

    Uses :func:`~mission_runtime.is_coordination_artifact_residue_path`
    (None-safe over an unrecognized kind) -- NOT
    ``is_primary_artifact_kind(kind_for_mission_file(path))``:
    ``kind_for_mission_file("meta.json")`` returns ``None``, so that form is
    both a ``mypy --strict`` error and would misroute ``meta.json`` to coord,
    reintroducing #2533 (BLOCKER-2).

    Defaults toward primary (fail-safe direction, NFR-004): everything not
    explicitly coord-residue -- PRIMARY kinds, ``meta.json`` (kind ``None``),
    and unrecognized paths -- resolves to the shared :func:`_commit_target_ref_for`
    expression (``"HEAD"`` here; FR-005 ref half). A PRIMARY artifact is
    never compared against the coordination branch. Pure: no filesystem/git
    side effects.
    """
    if coord_branch_for_filter and is_coordination_artifact_residue_path(repo_rel_path):
        return coord_branch_for_filter
    return _commit_target_ref_for(None)


def _committed_meta_mapping(repo_root: Path, repo_rel: str, ref: str | None, *, git: GitPort = DEFAULT_GIT_PORT) -> dict[str, Any] | None:
    """The committed meta.json mapping at the path-resolved precondition ref
    (:func:`resolve_precondition_ref` -- ``HEAD`` for meta.json, which is
    always a PRIMARY kind), or ``None`` when the path is absent there or
    unparseable."""
    blob = git.show_blob(repo_root, resolve_precondition_ref(repo_rel, ref), repo_rel)
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


def _is_wp_filename(repo_rel: str) -> bool:
    """Is *repo_rel* a ``tasks/WP##.md``-shaped path (the runtime-frontmatter
    exclusion is scoped strictly to this filename shape, never any markdown)?"""
    return bool(_WP_FILENAME_PATTERN.match(Path(repo_rel).name))


def _parse_wp_frontmatter(text: str) -> tuple[Mapping[str, Any] | None, str, str]:
    """Split WP-markdown *text* into ``(frontmatter mapping, body, padding)``.

    Returns ``(None, body, padding)`` when *text* has no frontmatter block or
    the block does not parse to a YAML mapping -- defensive: a malformed or
    frontmatter-less WP file can never be treated as a runtime-only diff.
    """
    front_text, body, padding = split_frontmatter(text)
    if not front_text:
        return None, body, padding
    try:
        parsed = YAML(typ="safe").load(front_text)
    except YAMLError:
        return None, body, padding
    return (parsed if isinstance(parsed, dict) else None), body, padding


def _is_runtime_frontmatter_only_wp_diff(
    committed_front: Mapping[str, Any] | None,
    working_front: Mapping[str, Any] | None,
    committed_tail: str,
    working_tail: str,
) -> bool:
    """Pure decision: is the WP##.md change ONLY runtime claim/workspace
    frontmatter (T001's :data:`~specify_cli.frontmatter.WP_RUNTIME_FIELDS`)?

    Structural analogue of :func:`_is_vcs_lock_only_meta_diff` for WP markdown
    files. Returns ``True`` iff (1) both the committed and working frontmatter
    parsed to a mapping, (2) the markdown body -- everything after the
    frontmatter block, byte-compared as ``padding + body`` -- is unchanged,
    AND (3) every frontmatter key whose value differs is a member of
    :data:`~specify_cli.frontmatter.WP_RUNTIME_FIELDS` (K-1/NFR-005: the body
    check alone is not enough -- a non-runtime frontmatter key change must
    also still block).
    """
    if committed_front is None or working_front is None:
        return False
    if committed_tail != working_tail:
        return False
    changed_keys = {
        key
        for key in set(committed_front) | set(working_front)
        if committed_front.get(key, _MISSING_META_VALUE) != working_front.get(key, _MISSING_META_VALUE)
    }
    return bool(changed_keys) and changed_keys <= WP_RUNTIME_FIELDS


def _drop_runtime_frontmatter_only_wp(
    repo_root: Path,
    paths: list[str],
    ref: str | None,
    *,
    auto_commit: bool,
    git: GitPort = DEFAULT_GIT_PORT,
) -> list[str]:
    """Drop a WP##.md change from the dirty-tree claim guard when its only
    diff vs the placement ref is runtime claim/workspace frontmatter (#2570.1).

    ``spec-kitty implement`` writes ``shell_pid``/``shell_pid_created_at`` at
    claim time and ``base_branch``/``base_commit``/``planning_base_branch`` at
    workspace-creation time into ``tasks/WP##.md``. Under
    ``auto_commit=False`` that self-write is left uncommitted, so the NEXT
    lane's dependency-free claim wrongly sees it as a dirty planning artifact
    and refuses. Structural analogue of :func:`_drop_vcs_lock_only_meta`,
    scoped to WP##.md paths and gated by
    :func:`_is_runtime_frontmatter_only_wp_diff` (body byte-identical AND
    every differing key in
    :data:`~specify_cli.frontmatter.WP_RUNTIME_FIELDS`, the T001 canonical
    source both this helper and WP07's ``move-task`` guard reuse).

    Byte-identical no-op on the default ``auto_commit=True`` path (NFR-001,
    mirrors :func:`_drop_vcs_lock_only_meta`).
    """
    if auto_commit:
        return paths
    kept: list[str] = []
    for repo_rel in paths:
        if not _is_wp_filename(repo_rel):
            kept.append(repo_rel)
            continue
        source = (repo_root / Path(repo_rel)).resolve()
        if not source.exists():
            kept.append(repo_rel)
            continue
        committed_blob = git.show_blob(repo_root, resolve_precondition_ref(repo_rel, ref), repo_rel)
        if committed_blob is None:
            kept.append(repo_rel)
            continue
        working_front, working_body, working_padding = _parse_wp_frontmatter(source.read_text(encoding="utf-8-sig"))
        committed_front, committed_body, committed_padding = _parse_wp_frontmatter(
            committed_blob.decode("utf-8", errors="replace")
        )
        if _is_runtime_frontmatter_only_wp_diff(
            committed_front,
            working_front,
            committed_padding + committed_body,
            working_padding + working_body,
        ):
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


def _files_changed_vs_precondition_ref(
    repo_root: Path,
    files: list[str],
    coord_branch_for_filter: str | None,
    *,
    verbatim_ref: str | None = None,
    git: GitPort = DEFAULT_GIT_PORT,
) -> list[str]:
    """Per-path idempotency filter (T003, contracts/resolve-precondition-ref.md
    "Preferred design"): partition *files* by :func:`resolve_precondition_ref`
    into a PRIMARY group (diffed against ``HEAD``) and a COORD-residue group
    (diffed against *coord_branch_for_filter*), calling
    :func:`_files_changed_vs_ref` once per group so ITS OWN
    ``(repo_root, files, ref)`` signature stays untouched (its direct unit
    tests keep passing). Preserves the original relative order of *files* in
    the result -- callers print ``files_to_commit`` verbatim in the "not
    committed" instructions.

    ``verbatim_ref`` (PR #2662 squad fix): when the caller commits the WHOLE
    batch to ONE ref (the healthy ``placement_ref is not None`` verbatim path in
    ``_commit_planning_artifacts_transaction``, which the C-004/#2160 deferral
    leaves un-partitioned), the idempotency comparison MUST use that same single
    write target for EVERY file -- not the PRIMARY-vs-``HEAD`` split. Otherwise a
    PRIMARY artifact already-identical on the coord write ref but differing from
    ``HEAD`` is compared vs ``HEAD`` (still "changed"), re-committed verbatim to
    coord, produces an empty commit, and ``safe_commit`` hard-fails the claim
    (confirmed on coordination missions; the read=HEAD / write=coord divergence
    is a concrete instance of the overloaded "primary ref", #2653). Proper fix
    (partition the verbatim write so PRIMARY lands on the primary branch) is
    deferred to #2160.
    """
    if verbatim_ref is not None:
        changed_verbatim = set(_files_changed_vs_ref(repo_root, files, verbatim_ref, git=git))
        return [repo_rel for repo_rel in files if repo_rel in changed_verbatim]
    primary_ref = _commit_target_ref_for(None)
    primary_files: list[str] = []
    coord_files: list[str] = []
    for repo_rel in files:
        if resolve_precondition_ref(repo_rel, coord_branch_for_filter) == primary_ref:
            primary_files.append(repo_rel)
        else:
            coord_files.append(repo_rel)
    changed = set(_files_changed_vs_ref(repo_root, primary_files, primary_ref, git=git))
    changed |= set(_files_changed_vs_ref(repo_root, coord_files, coord_branch_for_filter, git=git))
    return [repo_rel for repo_rel in files if repo_rel in changed]


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
    verbatim_ref: str | None = None,
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

    ``verbatim_ref`` (PR #2662 squad fix) is the single ref the whole batch will
    be committed to on the healthy ``placement_ref is not None`` verbatim path;
    when set, the idempotency filter compares EVERY file against it so a
    PRIMARY artifact already-identical on the (coord) write ref is dropped
    instead of re-committed into an empty commit that hard-fails the claim. See
    :func:`_files_changed_vs_precondition_ref`.
    """
    entries = _feature_dir_status_entries(repo_root, artifact_source_dir, git=git)
    structural = _structural_entries(entries)
    if structural:
        return PlanningArtifactStagingPlan(structural=structural, files_to_commit=[], status_paths_to_commit=[])

    status_paths = _status_paths_for_commit(entries, coord_branch_for_filter)
    status_paths = _drop_vcs_lock_only_meta(repo_root, status_paths, coord_branch_for_filter, auto_commit=auto_commit, git=git)
    status_paths = _drop_runtime_frontmatter_only_wp(repo_root, status_paths, coord_branch_for_filter, auto_commit=auto_commit, git=git)
    files_to_commit = list(status_paths)
    if coord_branch_for_filter:
        files_to_commit.extend(_exclude_coord_owned(extra_file_paths, coord_branch_for_filter))
    files_to_commit = list(dict.fromkeys(files_to_commit))
    files_to_commit = _drop_vcs_lock_only_meta(repo_root, files_to_commit, coord_branch_for_filter, auto_commit=auto_commit, git=git)
    files_to_commit = _drop_runtime_frontmatter_only_wp(repo_root, files_to_commit, coord_branch_for_filter, auto_commit=auto_commit, git=git)
    if not files_to_commit:
        return PlanningArtifactStagingPlan(structural=[], files_to_commit=[], status_paths_to_commit=[])

    # Idempotency guard: skip files already identical on THEIR OWN partition ref
    # (PRIMARY kinds -> HEAD, COORD-residue kinds -> the coordination branch;
    # see ``resolve_precondition_ref``) so a re-discovered (but
    # already-committed) edit does not produce an empty commit that
    # ``safe_commit`` rejects. See ``_files_changed_vs_precondition_ref``.
    files_to_commit = _files_changed_vs_precondition_ref(repo_root, files_to_commit, coord_branch_for_filter, verbatim_ref=verbatim_ref, git=git)
    if not files_to_commit:
        return PlanningArtifactStagingPlan(structural=[], files_to_commit=[], status_paths_to_commit=[])

    status_paths_to_commit = _files_changed_vs_precondition_ref(repo_root, status_paths, coord_branch_for_filter, verbatim_ref=verbatim_ref, git=git)
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
