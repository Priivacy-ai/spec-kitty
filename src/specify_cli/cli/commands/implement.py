"""Implement command - allocate the lane worktree for a work package."""

from __future__ import annotations

import functools
import json
import re
import subprocess
from collections.abc import Iterable, Mapping
from datetime import UTC, datetime
from io import StringIO
from pathlib import Path
from typing import Annotated, Any, NamedTuple

import typer
from pydantic import ValidationError
from rich.console import Console
from rich.panel import Panel

from specify_cli.cli import StepTracker
from specify_cli.cli.selector_resolution import resolve_mission_handle
from specify_cli.core.context_validation import require_main_repo
from specify_cli.core.errors import PlacementResolutionRequired
from specify_cli.core.git_ops import get_current_branch
from specify_cli.core.vcs import VCSBackend
from specify_cli.mission_metadata import resolve_mission_identity, set_vcs_lock
from specify_cli.frontmatter import FrontmatterError, update_fields
from specify_cli.git import safe_commit
from specify_cli.git.commit_helpers import (
    SafeCommitPathPolicyError,
)
from specify_cli.git.protection_policy import ProtectionPolicy
from specify_cli.core.constants import WORKTREES_DIR
from mission_runtime import (
    CommitTarget,
    MissionArtifactKind,
    placement_seam,
    resolve_topology,
    routes_through_coordination,
)
from specify_cli.lanes.implement_support import create_lane_workspace
from specify_cli.lanes.persistence import CorruptLanesError, MissingLanesError, require_lanes_json
from specify_cli.coordination.status_transition import emit_status_transition_transactional
from specify_cli.status import COORD_OWNED_STATUS_FILES
from specify_cli.status import TransitionError
from specify_cli.status import Lane, TransitionRequest
from specify_cli.status import (
    WorkPackageClaimConflict,
    WorkPackageStartRejected,
    start_implementation_status,
)
from specify_cli.task_utils import TaskCliError, find_repo_root
from specify_cli.workspace.context import resolve_workspace_for_wp

console = Console()
_WP_ID_RE = re.compile(r"^WP\d{2}$", re.IGNORECASE)
_META_JSON_FILENAME = "meta.json"
# vcs-lock fields written by ``mission_metadata.set_vcs_lock`` (the canonical
# writer). #2222 / C-003: this lock is one-time VCS-TYPE state, NOT the
# concurrency mutex, so a dependency-free back-to-back claim must not be blocked
# by the prior claim's own uncommitted lock self-write. Mirrored here as a named
# constant (S1192) rather than imported because ``mission_metadata`` exposes no
# field-name constant and this WP must not edit that module (upstream gap: a
# ``VCS_LOCK_FIELDS`` export there would let this be imported instead).
_VCS_LOCK_META_FIELDS: frozenset[str] = frozenset({"vcs", "vcs_locked_at"})
_MISSING_META_VALUE = object()
# WP03 / S1192: the rich-markup error prefix, repeated across the
# planning-artifact commit helper this WP touches -- hoisted to one constant
# rather than restated at each ``console.print`` call site.
_RED_ERROR_PREFIX = "[red]Error:[/red] "


def _protected_branch_status_commit_error(branch: str, repo_root: Path) -> str | None:
    # ProtectionPolicy.resolve is the sole I/O boundary (FR-007/NFR-003):
    # config+hatch reads happen once; is_protected() is I/O-free.
    if not ProtectionPolicy.resolve(repo_root).is_protected(branch):
        return None
    return (
        f"Refusing to start implementation status on protected branch '{branch}' "
        "before mutating status files. Run this status commit from an allowed "
        "coordination/lane branch, or rerun with --no-auto-commit when you "
        "intentionally want to handle the status artifact commit manually."
    )


def _status_commit_destination_branch(repo_root: Path, fallback_branch: str) -> str:
    """Return the branch that the pre-lane status commit would target."""
    return get_current_branch(repo_root) or fallback_branch


def _get_wp_lane_from_event_log(feature_dir: Path, wp_id: str) -> str:
    """Get the canonical WP lane, defaulting to genesis for unseeded WPs.

    An unseeded WP (no events, or no snapshot entry) defaults to
    ``Lane.GENESIS`` — matching the write-side ``_derive_from_lane``
    behaviour (Contract 3, FR-008).
    """
    try:
        from specify_cli.status import reduce
        from specify_cli.status import read_events

        events = read_events(feature_dir)
        if events:
            snapshot = reduce(events)
            state = snapshot.work_packages.get(wp_id)
            if state:
                return Lane(state.get("lane", Lane.GENESIS))
    except Exception:  # noqa: S110 — best-effort lane lookup, fallback is safe
        pass
    return Lane.GENESIS


def _json_safe_output(func):
    """Ensure --json mode stays machine-readable on both success and failure."""

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        json_output = bool(kwargs.get("json_output", False))
        previous_quiet = console.quiet
        capture_buffer: StringIO | None = None
        if json_output:
            capture_buffer = StringIO()
            console.file = capture_buffer
            console.quiet = False

        wp_id = kwargs.get("wp_id")
        if wp_id is None and args:
            wp_id = args[0]

        try:
            return func(*args, **kwargs)
        except typer.Exit as exc:
            if json_output and getattr(exc, "exit_code", 1):
                lines = [line.rstrip() for line in (capture_buffer.getvalue() if capture_buffer else "").splitlines() if line.strip()]
                summary = "\n".join(lines[-20:]).strip() if lines else "implement command failed"
                payload = {"status": "error", "error": summary or "implement command failed"}
                if wp_id:
                    payload["wp_id"] = str(wp_id)
                print(json.dumps(payload))
            raise
        except Exception as exc:  # pragma: no cover - defensive
            if json_output:
                payload = {"status": "error", "error": str(exc)}
                if wp_id:
                    payload["wp_id"] = str(wp_id)
                print(json.dumps(payload))
            raise typer.Exit(1) from exc
        finally:
            console.quiet = previous_quiet
            # Reset _file to None so the console uses sys.stdout dynamically.
            # Restoring previous_file can leave the console pointing at a closed
            # pytest capsys buffer when tests run in sequence.
            console._file = None

    return wrapper


def detect_feature_context(
    mission_flag: str | None = None,
    repo_root: Path | None = None,
) -> tuple[str | None, str]:
    """Require an explicit mission slug and return ``(mission_number, slug)``.

    Uses the canonical mission resolver (resolve_mission_handle) when
    repo_root is supplied, falling back to bare slug parsing otherwise.
    The repo_root is always available in the callers that matter.
    """
    import re as _re

    raw_handle = mission_flag
    if raw_handle is None:
        console.print("[red]Error:[/red] --mission <slug> is required")
        raise typer.Exit(1)

    if repo_root is not None:
        # Use canonical resolver — handles ambiguity, mid8, full ULID, etc.
        resolved = resolve_mission_handle(raw_handle, repo_root)
        slug = resolved.mission_slug
    else:
        # Bare-slug fallback for callers without a repo_root (e.g., unit tests).
        slug = raw_handle

    match = _re.match(r"^(\d{3})-", slug)
    return (match.group(1) if match else None), slug


def find_wp_file(repo_root: Path, mission_slug: str, wp_id: str) -> Path:
    """Find the markdown file for a work package.

    WP05 / FR-003 (coord-topology regression fix): WP prompt files under
    ``tasks/`` are authored on the PRIMARY checkout (``mission_creation`` writes
    the mission dir there and the ``tasks`` step appends beside it). On a
    coordination-topology mission finalize-tasks commits a COPY of those files
    onto the coordination branch, but a freshly-resolved ``find_wp_file`` runs
    before the lane worktree is allocated and must locate the authored prompt on
    the surface that always carries it. The topology-aware
    ``resolve_feature_dir_for_mission`` selects the coordination worktree once
    one exists, which need not carry every authored prompt — so anchor the
    WP-file read on the primary surface, consistent with finalize-tasks and
    ``mission_runtime.resolve_placement_only``.
    """
    from specify_cli.missions._read_path_resolver import (
        _canonicalize_primary_read_handle,
        primary_feature_dir_for_mission,
    )

    # FR-011 / T012: fold the handle to its canonical on-disk dir NAME before the
    # topology-blind primary compose, so a bare mid8 / human slug lands on the
    # durable ``<slug>-<mid8>`` home (ambiguous handle RAISES — no silent pick).
    _canonical_handle = _canonicalize_primary_read_handle(repo_root, mission_slug)
    tasks_dir = primary_feature_dir_for_mission(repo_root, _canonical_handle) / "tasks"
    if not tasks_dir.exists():
        raise FileNotFoundError(f"Tasks directory not found: {tasks_dir}")

    normalized_wp_id = wp_id.strip().upper()
    if not _WP_ID_RE.fullmatch(normalized_wp_id):
        raise FileNotFoundError(f"Invalid work package ID: {wp_id}. Expected format WP## (for example, WP01).")

    wp_name_re = re.compile(rf"^{re.escape(normalized_wp_id)}(?:[-_.].+)?\.md$", re.IGNORECASE)
    wp_files = sorted(path for path in tasks_dir.glob("WP*.md") if wp_name_re.match(path.name))
    if not wp_files:
        raise FileNotFoundError(f"WP file not found for {normalized_wp_id} in {tasks_dir}")
    return wp_files[0]


def resolve_feature_target_branch(mission_slug: str, repo_root: Path) -> str:
    """Resolve the feature's configured target branch from metadata."""
    from specify_cli.core.git_ops import resolve_target_branch

    resolution = resolve_target_branch(
        mission_slug=mission_slug,
        repo_path=repo_root,
        respect_current=True,
    )
    return resolution.target


def _validate_base_ref(repo_root: Path, base_ref: str) -> str:
    """Validate that a base ref resolves locally and return its full SHA.

    Raises typer.Exit(1) with a clear error message if the ref is unknown.
    """
    result = subprocess.run(
        ["git", "rev-parse", "--verify", "--end-of-options", base_ref],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if result.returncode != 0:
        console.print(f"[red]Error:[/red] Base ref '{base_ref}' does not resolve. Try 'git fetch' or 'git branch -a' to see available refs.")
        raise typer.Exit(1)
    return result.stdout.strip()


def _git_stdout(repo_root: Path, args: list[str]) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=repo_root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if result.returncode != 0:
        return ""
    return result.stdout.strip()


class _PorcelainEntry(NamedTuple):
    """A single ``git status --porcelain`` record for a feature-dir path.

    ``xy`` is the 2-char status code, ``path`` the current/new repo-relative
    path. ``is_structural`` marks deletions and renames/copies — changes that
    ``BookkeepingTransaction.write_artifact`` (a write-only API) cannot apply,
    so they must be committed to the coordination branch out-of-band or the
    claim must fail closed rather than silently leave the branch incoherent.
    """

    xy: str
    path: str
    is_structural: bool


def _feature_dir_status_entries(
    repo_root: Path, feature_dir: Path
) -> list[_PorcelainEntry]:
    # NOTE: must read raw stdout here, NOT via _git_stdout(): porcelain v1 emits
    # "XY<space>PATH" (a fixed 3-char prefix). For a tracked file that is
    # modified-but-not-staged, X is a space (" M path"); _git_stdout()'s outer
    # .strip() would remove the leading space of the *first* line, shifting its
    # columns so line[3:] truncated the first path character (KITTY_SPECS_DIR ->
    # "itty-specs"). Parse column 3 from each *unstripped* line so the path is
    # always intact, and classify deletions/renames as structural.
    result = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=all", str(feature_dir)],
        cwd=repo_root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if result.returncode != 0:
        return []
    entries: list[_PorcelainEntry] = []
    for line in result.stdout.splitlines():
        if len(line) <= 3:
            continue
        xy = line[:2]
        rest = line[3:]
        if " -> " in rest:
            # Rename/copy: "old -> new". The old path must be removed on coord —
            # a write-only transaction cannot do that, so this is structural.
            new_path = rest.split(" -> ", 1)[1].strip()
            entries.append(_PorcelainEntry(xy=xy, path=new_path, is_structural=True))
            continue
        # Deletions (D in either index or worktree column) are structural too.
        is_structural = "D" in xy
        entries.append(_PorcelainEntry(xy=xy, path=rest.strip(), is_structural=is_structural))
    return entries


def _feature_dir_status_paths(repo_root: Path, feature_dir: Path) -> list[str]:
    """Repo-relative paths of *writable* (non-structural) feature-dir changes."""
    return [
        e.path
        for e in _feature_dir_status_entries(repo_root, feature_dir)
        if not e.is_structural
    ]


def _resolve_lanes_dir(repo_root: Path, mission_slug: str) -> Path:
    """Return the directory containing ``lanes.json`` for *mission_slug*.

    Prefers the coordination-worktree surface (where ``finalize-tasks``
    commits ``lanes.json``) and falls back to the primary checkout for
    flat/legacy missions that carry no coordination worktree.  Pure path:
    no git subprocess calls beyond filesystem stats when the coord worktree
    is already materialised.

    Distinct from :func:`lanes.persistence.resolve_lanes_dir`, which is a
    path-join helper (``feature_dir / lanes.json``); this function resolves
    the *feature_dir* itself from topology.

    C-LANES-1 (#1991 / FR-008): ``lanes.json`` lives on the coordination
    branch (committed by ``finalize-tasks``; primary copy deleted after
    staging). This extraction makes the inline
    ``_lanes_feature_dir = _status_feature_dir`` guard unit-testable
    without infrastructure mocks (WP03 / #2052).
    """
    from specify_cli.coordination.surface_resolver import (
        resolve_status_surface_with_anchor as _resolve_surface,
    )

    return _resolve_surface(repo_root, mission_slug).read_dir


def _print_uncommitted_planning_artifacts(files_to_commit: list[str]) -> None:
    console.print("\n[cyan]Planning artifacts not committed:[/cyan]")
    for file_path in files_to_commit:
        console.print(f"  {file_path}")


def _print_planning_artifact_commit_instructions(
    current_branch: str,
    planning_branch: str,
    auto_commit: bool,
    feature_dir: Path,
    mission_slug: str,
) -> None:
    if current_branch != planning_branch:
        console.print(
            f"\n[red]Error:[/red] Planning artifacts must be committed on {planning_branch}."
        )
        console.print(f"Current branch: {current_branch}")
        raise typer.Exit(1)

    if auto_commit:
        return

    console.print(
        "\n[yellow]Auto-commit disabled.[/yellow] Commit planning artifacts first:"
    )
    console.print(f"  git add -f {feature_dir}")
    console.print(f'  git commit -m "chore: planning artifacts for {mission_slug}"')
    raise typer.Exit(1)


def _resolve_bookkeeping_transaction_identifiers(
    feature_dir: Path,
    mission_slug: str,
    repo_root: Path | None = None,
) -> tuple[str | None, str | None, str | None, str, str]:
    from specify_cli.mission_metadata import load_meta as _load_meta

    # FR-003 cascade layer 1: ``coordination_branch`` / ``mission_id`` / ``mid8``
    # live ONLY in the PRIMARY-checkout meta.json; the coord worktree's mission
    # dir has none. ``feature_dir`` is topology-aware and prefers the coord
    # worktree once materialized — reading meta there returns empty, so every
    # identifier silently fell back to the slug (``mid8`` -> ``<slug>0000``),
    # which then names a non-existent coord branch/worktree at claim time
    # ("Failed to resolve coordination worktree for <slug>-<slug-fallback>").
    # Anchor the config read on the canonical primary dir first (the caller
    # threads the true main ``repo_root``), before falling back to the passed
    # dir, so config is read before topology is resolved.
    mission_meta: dict[str, Any] | None = None
    if repo_root is not None:
        from specify_cli.missions._read_path_resolver import (
            _canonicalize_primary_read_handle,
            primary_feature_dir_for_mission,
        )

        # FR-011 / T012: fold the handle to its canonical dir NAME first so a bare
        # mid8 / human slug resolves the durable ``<slug>-<mid8>`` home (ambiguous
        # handle RAISES — no silent pick).
        _canonical_handle = _canonicalize_primary_read_handle(repo_root, mission_slug)
        try:
            mission_meta = _load_meta(
                primary_feature_dir_for_mission(repo_root, _canonical_handle)
            )
        except Exception:  # noqa: BLE001 — meta missing/corrupt is legacy
            mission_meta = None
    if mission_meta is None:
        try:
            mission_meta = _load_meta(feature_dir)
        except Exception:  # noqa: BLE001 — meta missing/corrupt is legacy
            mission_meta = None

    coord_branch: str | None = None
    mission_id: str | None = None
    mid8: str | None = None
    if isinstance(mission_meta, dict):
        coord_branch = mission_meta.get("coordination_branch") or None
        mission_id = mission_meta.get("mission_id") or None
        # Preserve the stored ``meta["mid8"]`` preference, then route the
        # fallback through the authoritative resolver (WP03 / FR-009).
        # ``or None`` preserves the prior ``None`` contract (resolve_mid8
        # declines to ``""``).
        from specify_cli.lanes.branch_naming import resolve_mid8

        mid8 = mission_meta.get("mid8") or (
            resolve_mid8(
                mission_slug,
                mission_id=mission_id if isinstance(mission_id, str) else None,
            )
            or None
        )

    effective_mission_id = (
        str(mission_id) if mission_id else f"legacy-{mission_slug}"
    )
    # FR-007: route the mid8 through the canonical fail-closed authority rather
    # than fabricating a zero-padded mid8 from the slug — that idiom named a
    # non-existent coord branch/worktree at claim time.
    from specify_cli.lanes.branch_naming import resolve_transaction_mid8

    effective_mid8 = resolve_transaction_mid8(
        mission_slug,
        mission_id=str(mission_id) if mission_id else None,
        mid8=str(mid8) if mid8 else None,
        coordination_branch=coord_branch,
    )
    return coord_branch, mission_id, mid8, effective_mission_id, effective_mid8


def _coord_branch_blob(repo_root: Path, ref: str, repo_rel_path: str) -> bytes | None:
    """Return the bytes of *repo_rel_path* at *ref*, or ``None`` if absent there."""
    result = subprocess.run(
        ["git", "show", f"{ref}:{repo_rel_path}"],
        cwd=repo_root,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        return None
    return result.stdout


def _files_changed_vs_ref(
    repo_root: Path, files: list[str], ref: str | None
) -> list[str]:
    """Drop files whose working-tree content already matches *ref*.

    The coordination model commits claim-time planning-artifact edits to the
    coordination branch but leaves them uncommitted in the main checkout. The
    next claim re-discovers those edits as "uncommitted" even though their
    content is already on the coordination branch. Committing them again would
    produce an empty commit, which ``safe_commit`` rejects ("git commit failed")
    — silently blocking every claim after the first. Filtering to genuinely
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
            # unexpected — skip it rather than crash the claim.
            continue
        if _coord_branch_blob(repo_root, ref, repo_rel) != source.read_bytes():
            changed.append(repo_rel)
    return changed


def _feature_dir_file_paths(repo_root: Path, feature_dir: Path) -> list[str]:
    # FR-005 / Issue #1887: reject calls where feature_dir resolves under
    # .worktrees/.  Relativizing a coord-worktree path against the primary repo
    # root produces paths like ".worktrees/<slug>/..." which safe_commit then
    # stages into the primary index, leaking coord internals into origin/main.
    # The caller must pass the correct coordination-branch-relative path instead.
    feature_dir_resolved = feature_dir.resolve()
    repo_root_resolved = repo_root.resolve()
    try:
        rel = feature_dir_resolved.relative_to(repo_root_resolved)
    except ValueError:
        rel = None
    if rel is not None and rel.parts and rel.parts[0] == WORKTREES_DIR:
        raise SafeCommitPathPolicyError(
            offending_path=rel.as_posix(),
            worktree_root=repo_root_resolved,
        )

    paths: list[str] = []
    for path in sorted(feature_dir.rglob("*")):
        if not path.is_file():
            continue
        try:
            rel_path = path.resolve().relative_to(repo_root_resolved).as_posix()
        except ValueError:
            continue
        # Secondary guard: individual files must not land under .worktrees/.
        if Path(rel_path).parts and Path(rel_path).parts[0] == WORKTREES_DIR:
            raise SafeCommitPathPolicyError(
                offending_path=rel_path,
                worktree_root=repo_root_resolved,
            )
        paths.append(rel_path)
    return paths


def _planning_artifact_source_dir(repo_root: Path, feature_dir: Path, mission_slug: str) -> Path:
    """Return the primary-checkout mission dir for planning-artifact discovery."""
    repo_root_resolved = repo_root.resolve()
    try:
        rel = feature_dir.resolve().relative_to(repo_root_resolved)
    except ValueError:
        return feature_dir
    if rel.parts and rel.parts[0] == WORKTREES_DIR:
        from specify_cli.missions._read_path_resolver import (
            _canonicalize_primary_read_handle,
            primary_feature_dir_for_mission,
        )

        # FR-011 / T012: fold the handle to its canonical dir NAME first so a bare
        # mid8 / human slug resolves the durable ``<slug>-<mid8>`` home (ambiguous
        # handle RAISES — no silent pick).
        _canonical_handle = _canonicalize_primary_read_handle(repo_root, mission_slug)
        primary_dir = primary_feature_dir_for_mission(repo_root, _canonical_handle)
        if primary_dir.exists():
            return primary_dir
    return feature_dir


def _exclude_coord_owned(paths: Iterable[str], coord_branch_for_filter: str | None) -> list[str]:
    """Drop the canonical status log/snapshot (``COORD_OWNED_STATUS_FILES``) from
    *paths* on coordination-topology missions only.

    On a coordination mission those files are owned by the transactional emitter on
    the coord branch, and the primary checkout's copies are stale — committing them
    would clobber the seeded lane state (#1589). On a non-coordination (flat/legacy)
    mission there is no coord authority, so the primary checkout's status files ARE
    canonical and must be committed; excluding them there silently drops a status
    edit (review M3). Single predicate for both commit-path sources (review F-03).
    """
    if coord_branch_for_filter:
        return [p for p in paths if Path(p).name not in COORD_OWNED_STATUS_FILES]
    return list(paths)


def _status_paths_for_commit(
    entries: list[_PorcelainEntry], coord_branch_for_filter: str | None
) -> list[str]:
    """The feature-dir paths to commit from ``git status`` entries — see
    :func:`_exclude_coord_owned`."""
    return _exclude_coord_owned((e.path for e in entries), coord_branch_for_filter)


def _is_vcs_lock_only_meta_diff(
    committed: Mapping[str, Any] | None, working: Mapping[str, Any]
) -> bool:
    """Pure decision: is the meta.json change ONLY the one-time vcs-lock fields?

    Returns ``True`` iff every key whose value differs between the *committed*
    baseline and the *working*-tree meta.json is a member of
    :data:`_VCS_LOCK_META_FIELDS` (#2222 / C-003). The comparison is on parsed
    JSON, so it is robust to byte-level reformatting by ``write_meta``.

    An empty diff returns ``False`` (nothing to exclude); any non-lock key in
    the diff returns ``False`` so a genuinely dirty meta.json still blocks the
    claim (the required negative guard — the exclusion is lock-field-only, never
    a blanket meta.json bypass).
    """
    base: Mapping[str, Any] = committed or {}
    changed_keys = {
        key
        for key in set(base) | set(working)
        if base.get(key, _MISSING_META_VALUE)
        != working.get(key, _MISSING_META_VALUE)
    }
    return bool(changed_keys) and changed_keys <= _VCS_LOCK_META_FIELDS


def _parse_meta_mapping(raw: bytes) -> dict[str, Any] | None:
    """Parse meta.json *raw* bytes to a dict, or ``None`` when it is not a JSON
    object (defensive: a non-object/corrupt meta is never treated as lock-only)."""
    try:
        parsed = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None
    return parsed if isinstance(parsed, dict) else None


def _committed_meta_mapping(
    repo_root: Path, repo_rel: str, ref: str | None
) -> dict[str, Any] | None:
    """The committed meta.json mapping at *ref* (or ``HEAD`` for flat/legacy
    missions), or ``None`` when the path is absent there or unparseable."""
    blob = _coord_branch_blob(repo_root, ref or "HEAD", repo_rel)
    if blob is None:
        return None
    return _parse_meta_mapping(blob)


def _drop_vcs_lock_only_meta(
    repo_root: Path, paths: list[str], ref: str | None, *, auto_commit: bool
) -> list[str]:
    """Drop a vcs-lock-only meta.json change from the dirty-tree claim guard.

    #2222 / C-003: ``mission_metadata.set_vcs_lock`` writes a one-time VCS-TYPE
    lock to meta.json — never the concurrency mutex. Under ``auto_commit=False``
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
        committed = _committed_meta_mapping(repo_root, repo_rel, ref)
        if working is not None and _is_vcs_lock_only_meta_diff(committed, working):
            continue
        kept.append(repo_rel)
    return kept


def _resolve_placement_ref(
    repo_root: Path, *, mission_slug: str, wp_id: str
) -> CommitTarget | None:
    """Resolve the context's artifact-placement ref (C-PLACE-1 / IC-05).

    Routes through the single canonical resolver (``resolve_action_context``,
    C-CTX-1) and returns ``context.artifact_placement.placement_ref`` — the ONE
    :class:`CommitTarget` that planning artifacts AND status events resolve to.
    On any resolution failure it returns ``None`` so the caller keeps the legacy
    meta-derived placement path (C-004 strangler: never break the implement
    lifecycle on a context-resolution edge case).
    """
    from mission_runtime import (
        ActionContextError,
        resolve_action_context,
    )

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


def _placement_coord_filter(
    repo_root: Path, mission_slug: str, placement_ref: CommitTarget | None
) -> str | None:
    """Return the coord-owned-exclusion ref implied by the mission's topology.

    WP06 / T019 / C-PLACE-1: the coord/flattened/primary decision reads the WP02
    STORED topology via the ONE canonical :func:`routes_through_coordination`
    predicate (FR-005 / FR-001b) — never a per-ref ``.kind`` (the retired arm) and
    not independent meta.json/git logic (C-005). Only a genuine *coordination*
    topology owns the status files on a separate branch and therefore excludes
    them from the primary-checkout commit; a flattened/primary topology has no
    primary↔coord split, so the primary status files are NOT filtered out —
    preserving the #1816 implement-claim fix. The excluded ref is the context's
    single ``placement_ref.ref`` (the SAME CommitTarget status events resolve to).
    Returns ``None`` for flattened/primary topologies.
    """
    if placement_ref is None:
        return None
    if routes_through_coordination(resolve_topology(repo_root, mission_slug)):
        return placement_ref.ref
    return None


def _ensure_planning_artifacts_committed_git(  # noqa: C901 -- legacy orchestration helper; unrelated to issue #1386
    repo_root: Path,
    feature_dir: Path,
    mission_slug: str,
    wp_id: str,
    planning_branch: str,
    *,
    auto_commit: bool,
    placement_ref: CommitTarget | None = None,
) -> None:
    """Ensure planning artifacts are committed on the feature planning branch.

    ``placement_ref`` (WP06 / T019) is the context's resolved
    :class:`CommitTarget` — the ONE ref planning artifacts AND status events
    resolve to (C-PLACE-1). When supplied it drives the coord/flattened/primary
    placement decision so implement-claim never reconciles a primary↔coord
    split (#1816). When ``None`` (callers not yet threading the context, C-004
    strangler) the legacy meta-derived path is used unchanged.
    """
    current_branch = _git_stdout(repo_root, ["rev-parse", "--abbrev-ref", "HEAD"])
    artifact_source_dir = _planning_artifact_source_dir(
        repo_root, feature_dir, mission_slug
    )
    entries = _feature_dir_status_entries(repo_root, artifact_source_dir)

    # Fail closed on structural changes (deletions, renames, copies). The
    # planning-artifact commit goes through ``BookkeepingTransaction.write_artifact``,
    # a write-only API that cannot remove an old path from the coordination
    # branch. Silently committing only the additions would leave the branch
    # incoherent (stale deleted/renamed-from artifacts), so the claim must
    # refuse rather than proceed — restoring the pre-idempotency fail-closed
    # contract (#1598 review). The operator commits the structural change to the
    # coordination branch out-of-band, then re-runs the claim.
    structural = [e for e in entries if e.is_structural]
    if structural:
        console.print(
            f"\n{_RED_ERROR_PREFIX}Uncommitted structural planning-artifact changes "
            "(deletions/renames) cannot be auto-committed to the coordination branch:"
        )
        for entry in structural:
            console.print(f"  {entry.xy.strip() or entry.xy} {entry.path}")
        console.print(
            "\nCommit these structural changes to the coordination branch yourself "
            "(e.g. `git rm`/`git mv` + commit), then re-run the claim."
        )
        raise typer.Exit(1)

    # WP06 / T019 / C-PLACE-1: when the context supplies a placement ref, the
    # coord/flattened/primary decision comes from that single CommitTarget — no
    # independent meta-derived coord logic (C-005). Otherwise fall back to the
    # legacy meta-derived coord branch (C-004 strangler).
    if placement_ref is not None:
        coord_branch_for_filter = _placement_coord_filter(
            repo_root, mission_slug, placement_ref
        )
    else:
        coord_branch_for_filter = _resolve_bookkeeping_transaction_identifiers(
            feature_dir, mission_slug, repo_root
        )[0]

    status_paths = _status_paths_for_commit(entries, coord_branch_for_filter)
    # #2222 / C-003: under auto_commit=False, ignore the mission's own one-time
    # vcs-lock self-write to meta.json so a back-to-back dependency-free claim is
    # not blocked by it (no-op when auto_commit=True — NFR-001). Helper-gated so
    # the guard gains no new branch (it keeps its existing C901 complexity waiver).
    status_paths = _drop_vcs_lock_only_meta(
        repo_root, status_paths, coord_branch_for_filter, auto_commit=auto_commit
    )
    files_to_commit = list(status_paths)
    if coord_branch_for_filter:
        files_to_commit.extend(
            _exclude_coord_owned(
                _feature_dir_file_paths(repo_root, artifact_source_dir),
                coord_branch_for_filter,
            )
        )
    files_to_commit = list(dict.fromkeys(files_to_commit))
    files_to_commit = _drop_vcs_lock_only_meta(
        repo_root, files_to_commit, coord_branch_for_filter, auto_commit=auto_commit
    )
    if not files_to_commit:
        return

    # Idempotency guard: skip files already identical on the coordination branch
    # so a re-discovered (but already-committed) edit does not produce an empty
    # commit that ``safe_commit`` rejects. See ``_files_changed_vs_ref``.
    files_to_commit = _files_changed_vs_ref(
        repo_root, files_to_commit, coord_branch_for_filter
    )
    if not files_to_commit:
        return

    status_paths_to_commit = set(_files_changed_vs_ref(repo_root, status_paths, coord_branch_for_filter))
    if status_paths_to_commit:
        _print_uncommitted_planning_artifacts(files_to_commit)
        _print_planning_artifact_commit_instructions(
            current_branch,
            planning_branch,
            auto_commit,
            artifact_source_dir,
            mission_slug,
        )

    commit_msg = (
        f"chore: planning artifacts for {mission_slug}\n\n"
        f"Auto-committed by spec-kitty before creating the lane worktree for {wp_id}"
    )

    # WP06 T026: route planning-artifact commits through
    # BookkeepingTransaction so the commit lands on the mission's
    # coordination branch (FR-005) and any write of status events is
    # atomically reversible (FR-010).
    #
    # Legacy missions (created pre-WP03) have no ``coordination_branch``
    # in meta.json. For those, fall back to the legacy raw-git path.
    # WP08 will replace this fallback with a proper legacy bridge.
    (
        coord_branch,
        mission_id,
        mid8,
        effective_mission_id,
        effective_mid8,
    ) = _resolve_bookkeeping_transaction_identifiers(
        feature_dir, mission_slug, repo_root
    )

    # WP06 / T019 / C-PLACE-1: the placement destination is the context's single
    # ``placement_ref`` when threaded — one ref for planning artifacts AND status
    # events. Under a flattened/primary topology there is no coord branch
    # (``CommitTarget`` is ref-only; the retired ``.kind``/FLATTENED arm is gone),
    # so ``coord_branch`` collapses to ``None`` and the commit lands on
    # ``planning_branch`` (== target == coordination); under coordination
    # topology it is the coord ref. Identity (``mission_id`` / ``mid8``) is
    # unaffected — only the placement decision moves to the context (C-005).
    if placement_ref is not None:
        coord_branch = _placement_coord_filter(repo_root, mission_slug, placement_ref)

    # Route ALL planning-artifact commits through BookkeepingTransaction.
    # The transaction has a built-in legacy fallback (see
    # ``_is_legacy_mission`` + ``_resolve_legacy_lane_destination`` in
    # ``coordination/transaction.py``) so the pre-flight policy gate,
    # surgical rollback, and feature-status lock apply uniformly to
    # coordination-branch and legacy missions alike (FR-027).
    #
    # Modern (post-WP03) missions have ``coordination_branch``,
    # ``mission_id``, and ``mid8`` in meta; the transaction routes the
    # commit to the coord branch.
    #
    # Legacy missions lack ``coordination_branch``; the transaction
    # detects this via ``_is_legacy_mission`` and overrides the caller-
    # supplied ``destination_ref`` with the actual checked-out lane
    # branch resolved from HEAD. We synthesize ``mission_id`` / ``mid8``
    # from the slug if meta lacks them (truly pre-WP03 missions).
    from specify_cli.coordination.transaction import BookkeepingTransaction

    # Synthesize identifiers for legacy missions that lack them in meta.
    # The legacy fallback in BookkeepingTransaction overrides
    # destination_ref from HEAD, so the placeholder coord_branch value
    # below is never persisted; the routing just needs *some* shape-valid
    # ref name to satisfy the pre-flight policy gate's normalisation.
    #
    # WP03 / T011 / D11: no inline ``coord_branch if coord_branch else
    # planning_branch`` grammar (the forbidden pattern named in
    # contracts/seam-api.md's consumer table). When a ``placement_ref`` was
    # threaded (modern, non-legacy missions), it is already the ONE
    # seam-resolved :class:`CommitTarget` planning artifacts AND status
    # events resolve to (C-PLACE-1) -- use its ``.ref`` directly instead of
    # reconstructing the coord/primary choice a second time from
    # ``coord_branch``. Genuinely-legacy missions (no ``placement_ref``) keep
    # the existing meta-derived placeholder -- out of this WP's scope
    # (#2453; the value is never persisted, see comment above).
    if placement_ref is not None:
        effective_destination_ref = placement_ref.ref
    elif coord_branch:
        effective_destination_ref = str(coord_branch)
    else:
        effective_destination_ref = planning_branch

    is_legacy = not (coord_branch and mission_id and mid8)
    if is_legacy:
        console.print(
            f"\n[cyan]Auto-committing planning artifacts to {planning_branch}...[/cyan] "
            f"[dim](legacy path -- mission has no coordination_branch; "
            f"routed through BookkeepingTransaction for FR-020/FR-027 atomicity)[/dim]"
        )

    with BookkeepingTransaction.acquire(
        repo_root=repo_root,
        mission_id=effective_mission_id,
        mission_slug=mission_slug,
        mid8=effective_mid8,
        destination_ref=effective_destination_ref,
        operation=f"planning artifacts for {mission_slug}",
    ) as txn:
        for path_str in files_to_commit:
            repo_path = Path(path_str)
            source_path = (repo_root / repo_path).resolve()
            if not source_path.exists():
                continue
            txn.write_artifact(repo_path, source_path.read_bytes())
        try:
            txn.commit(commit_msg)
        except Exception as exc:  # noqa: BLE001 — surface as exit-1
            target = coord_branch or planning_branch
            console.print(
                f"{_RED_ERROR_PREFIX}Failed to commit planning artifacts to {target}: {exc}"
            )
            raise typer.Exit(1) from exc

    if is_legacy:
        console.print(
            f"[green]✓[/green] Planning artifacts committed to {planning_branch}"
        )
    else:
        console.print(
            f"[green]✓[/green] Planning artifacts committed to coordination branch {coord_branch}"
        )


def _ensure_vcs_in_meta(feature_dir: Path, _repo_root: Path) -> VCSBackend:
    """Ensure VCS is selected and locked in meta.json."""
    # read-surface-ssot-closeout WP05 / FR-005: route the inline
    # ``json.loads`` read through the canonical ``load_meta`` authority. This
    # site HARD-FAILS on a missing or malformed meta.json (both branches below
    # raise ``typer.Exit(1)``) -- the post-#2091 contract for a hard-failing
    # site is ``allow_missing=False`` (never ``allow_missing=True``, which
    # would mask the guard by silently returning ``None`` instead of raising).
    from specify_cli.mission_metadata import load_meta

    try:
        meta = load_meta(feature_dir, allow_missing=False, on_malformed="raise")
    except FileNotFoundError:
        console.print(f"[red]Error:[/red] meta.json not found in {feature_dir}")
        console.print("Run /spec-kitty.specify first to create feature structure")
        raise typer.Exit(1) from None
    except ValueError as exc:
        console.print(f"[red]Error:[/red] Invalid JSON in meta.json: {exc}")
        raise typer.Exit(1) from exc
    # ``allow_missing=False`` + ``on_malformed="raise"`` never returns ``None``
    # (both ``None``-producing branches raise, above) -- ``or {}`` narrows the
    # ``dict[str, Any] | None`` signature for mypy without an assert
    # (matching ``load_meta_strict``'s own narrowing idiom).
    meta = meta or {}

    if "vcs" not in meta:
        now_iso = datetime.now(UTC).isoformat()
        set_vcs_lock(feature_dir, vcs_type="git", locked_at=now_iso)
        console.print("[cyan]→ VCS locked to git in meta.json[/cyan]")

    return VCSBackend.GIT


def _run_recover_mode(
    _wp_id: str,
    mission: str | None,
    json_output: bool,
) -> None:
    """Run crash recovery for the given mission.

    Orchestrates scan + worktree/context/status reconciliation + reporting.
    The _wp_id argument is accepted but ignored for recovery -- all WPs in
    the mission are scanned.
    """
    from rich.table import Table

    from specify_cli.lanes.recovery import run_recovery, scan_recovery_state

    try:
        repo_root = find_repo_root()
        _mission_number, mission_slug = detect_feature_context(mission, repo_root=repo_root)
    except (TaskCliError, typer.Exit) as exc:
        if json_output:
            print(json.dumps({"status": "error", "error": str(exc)}))
        raise typer.Exit(1) from None

    # First, show what we found
    states = scan_recovery_state(repo_root, mission_slug)
    needs_recovery = [s for s in states if s.recovery_action != "no_action"]

    if not needs_recovery:
        if json_output:
            print(
                json.dumps(
                    {
                        "status": "ok",
                        "message": "No crashed implementation sessions found.",
                        "recovered_wps": [],
                        "worktrees_recreated": 0,
                        "transitions_emitted": 0,
                        "errors": [],
                    }
                )
            )
        else:
            console.print("[green]No crashed implementation sessions found.[/green]")
        return

    if not json_output:
        table = Table(title="Recovery Scan Results")
        table.add_column("WP", style="cyan")
        table.add_column("Lane", style="blue")
        table.add_column("Branch", style="dim")
        table.add_column("Worktree", style="green")
        table.add_column("Context", style="green")
        table.add_column("Status", style="yellow")
        table.add_column("Action", style="bold")

        for s in needs_recovery:
            table.add_row(
                s.wp_id,
                s.lane_id,
                s.branch_name,
                "yes" if s.worktree_exists else "[red]NO[/red]",
                "yes" if s.context_exists else "[red]NO[/red]",
                s.status_lane,
                s.recovery_action,
            )
        console.print(table)
        console.print()

    # Run recovery
    report = run_recovery(repo_root, mission_slug)

    if json_output:
        print(
            json.dumps(
                {
                    "status": "ok",
                    "recovered_wps": report.recovered_wps,
                    "worktrees_recreated": report.worktrees_recreated,
                    "transitions_emitted": report.transitions_emitted,
                    "errors": report.errors,
                }
            )
        )
    else:
        console.print("[bold green]Recovery complete[/bold green]")
        console.print(f"  WPs recovered: {', '.join(report.recovered_wps) or 'none'}")
        console.print(f"  Worktrees recreated: {report.worktrees_recreated}")
        console.print(f"  Contexts recreated: {report.contexts_recreated}")
        console.print(f"  Status transitions emitted: {report.transitions_emitted}")
        if report.errors:
            console.print("  [red]Errors:[/red]")
            for err in report.errors:
                console.print(f"    - {err}")


@_json_safe_output
@require_main_repo
def implement(  # noqa: C901 — orchestration function, complexity inherent
    wp_id: str = typer.Argument(..., help="Work package ID (for example, WP01)"),
    mission: Annotated[str | None, typer.Option("--mission", help="Mission slug (for example, 001-my-feature)")] = None,
    auto_commit: Annotated[
        bool | None,
        typer.Option("--auto-commit/--no-auto-commit", help="Auto-commit status and planning changes (default: from project config)"),
    ] = None,
    json_output: bool = typer.Option(False, "--json", help="Output in JSON format"),
    recover: bool = typer.Option(False, "--recover", help="Recover from crashed implementation session"),
    base: Annotated[
        str | None,
        typer.Option(
            "--base",
            help=(
                "Explicit base ref for the lane workspace (default: auto-detect). "
                "Use this when upstream dependency branches have been merged-and-deleted "
                "and you want to start from the current target branch tip, e.g. --base main."
            ),
        ),
    ] = None,
    acknowledge_not_bulk_edit: Annotated[
        bool,
        typer.Option(
            "--acknowledge-not-bulk-edit",
            help="Suppress the bulk-edit inference warning when spec language resembles a bulk edit but the mission is not one.",
        ),
    ] = False,
    actor: Annotated[str | None, typer.Option("--actor", hidden=True, help="Actor identity for programmatic callers")] = None,
) -> None:
    """Internal — allocate or reuse the lane worktree for a work package.

    This command is internal infrastructure, used by ``spec-kitty agent action implement``
    for workspace creation. It is not the canonical user-facing implementation path for
    spec-kitty 3.1.1.

    Canonical user workflow::

      spec-kitty next --agent <name> --mission <slug>   (loop entry)
      spec-kitty agent action implement <WP> --agent <name>  (per-WP verb)

    This command remains available as a compatibility surface for direct callers.
    See FR-503 and D-4 in the 3.1.1 spec.
    """
    from specify_cli.core.agent_config import get_auto_commit_default
    from specify_cli.core.dependency_graph import dependency_readiness_for_wp, parse_wp_dependencies

    # SC-003 no-selector guard: exit 2 when --mission is omitted (mirrors
    # all other commands and aligns with the no-selector-error-contract).
    # Guard runs BEFORE --recover so that `implement --recover` with no
    # --mission also exits 2, not 1 via detect_feature_context.
    if mission is None:
        console.print("[red]Error:[/red] --mission <slug> is required")
        raise typer.Exit(2)

    if recover:
        _run_recover_mode(wp_id, mission, json_output)
        return

    tracker = StepTracker(f"Implement {wp_id}")
    tracker.add("detect", "Detect feature context")
    tracker.add("validate", "Validate planning state")
    tracker.add("create", "Resolve execution workspace")
    console.print()

    tracker.start("detect")
    try:
        repo_root = find_repo_root()
        # FR-006 caller contract (T024): charter preflight runs BEFORE
        # any worktree allocation or .kittify/ modification. On failure
        # we exit 1 with the blocked_reason — no state mutation.
        from specify_cli.charter_runtime.preflight.hook import run_preflight_or_abort

        run_preflight_or_abort(repo_root, consumer="implement")
        if auto_commit is None:
            auto_commit = get_auto_commit_default(repo_root)
        _mission_number, mission_slug = detect_feature_context(mission, repo_root=repo_root)
        # read-surface-ssot-closeout WP05 / FR-001 / NFR-001: route through the
        # kind-aware placement seam instead of the kind-blind
        # ``resolve_feature_dir_for_mission`` (which could return the
        # coordination worktree's mission dir once materialized -- the #2453
        # coord-husk-shadows-primary defect NFR-001 closes). ``SPEC`` is a
        # PRIMARY-partition kind (mission_runtime.artifacts), so ``read_dir``
        # resolves the topology-blind primary directory directly: the SAME
        # directory every downstream read in this function needs (meta.json,
        # spec.md, tasks.md, the occurrence-map gate). This collapses the
        # former three-step meta.json-existence cascade (resolve -> candidate
        # fallback -> primary fallback), which existed ONLY to paper over the
        # kind-blind resolver's coord-husk shadowing -- the kind-correct seam
        # never returns a meta-less coord husk in the first place.
        feature_dir = placement_seam(repo_root, mission_slug).read_dir(
            MissionArtifactKind.SPEC
        )
        wp_file = find_wp_file(repo_root, mission_slug, wp_id)
        declared_deps = parse_wp_dependencies(wp_file)
        tracker.complete("detect", f"Feature: {mission_slug}")
    except (TaskCliError, FileNotFoundError, FrontmatterError, ValidationError, typer.Exit) as exc:
        tracker.error("detect", str(exc))
        console.print(tracker.render())
        raise typer.Exit(1) from exc

    tracker.start("validate")
    try:
        planning_branch = resolve_feature_target_branch(mission_slug, repo_root)
        if auto_commit:
            status_destination = _status_commit_destination_branch(
                repo_root,
                fallback_branch=planning_branch,
            )
            protected_error = _protected_branch_status_commit_error(status_destination, repo_root)
            if protected_error is not None:
                raise ValueError(protected_error)

        from specify_cli.status import reduce as _reduce_events
        from specify_cli.status import read_events as _read_events
        from specify_cli.coordination.surface_resolver import (
            resolve_status_surface_with_anchor as _resolve_status_surface,
        )

        # FR-003 layer 4: read WP-lane status through the SAME canonical,
        # config-determined surface authority the status WRITE path
        # (coordination/status_transition) uses, never a second ad-hoc
        # resolution. resolve_mission_read_path derived its own coord
        # preference from a slug-derived mid8 (empty for bare slugs), so in the
        # planning→implement window the read landed on a different surface than
        # the write and saw genesis ("WP not finalized"). The anchor authority
        # derives mid8 from meta and carries the fail-closed coord semantics
        # (StatusReadPathNotFound) — one authority, C-STAT-1.
        _status_feature_dir = _resolve_status_surface(repo_root, mission_slug).read_dir
        # C-LANES-1 (#1991 / FR-008): lanes.json lives on the COORDINATION
        # branch (committed by finalize-tasks; primary copy deleted after
        # staging). Derive the lanes-dir from the same coord surface used for
        # status reads — never from ``feature_dir`` (the primary fallback dir),
        # which is the regression this assignment prevents.
        # WP03 / #2052: routed through the pure extraction seam so the topology
        # logic is unit-testable without infrastructure mocks.
        _lanes_feature_dir: Path = _resolve_lanes_dir(repo_root, mission_slug)

        _wp_lanes = {
            _wp_id: _state.get("lane", Lane.GENESIS)
            for _wp_id, _state in _reduce_events(_read_events(_status_feature_dir)).work_packages.items()
        }
        # T012 / Contract 3: reject unseeded WPs BEFORE any workspace
        # allocation.  A genesis WP has not been through finalize-tasks; the
        # user must run it first to seed the genesis→planned bootstrap event.
        _current_wp_lane = _wp_lanes.get(wp_id, Lane.GENESIS)
        if _current_wp_lane == Lane.GENESIS:
            # FR-009: same rejection (and exception type) as the lifecycle layer,
            # so programmatic callers catching WorkPackageStartRejected see this
            # path too (review M5).
            raise WorkPackageStartRejected(
                f"WP {wp_id} is not finalized; run `spec-kitty agent mission finalize-tasks`"
            )
        _dependency_readiness = dependency_readiness_for_wp(wp_id, declared_deps, _wp_lanes)
        if not _dependency_readiness.satisfied:
            blocked = ", ".join(_dependency_readiness.unsatisfied)
            raise ValueError(
                f"dependencies_not_satisfied: {wp_id} depends on {blocked}; "
                "all dependencies must be approved or done before implementation can start"
            )

        # WP06 / T019 / C-PLACE-1: resolve the single artifact-placement ref from
        # the canonical context so implement-claim never reconciles a
        # primary↔coord planning-artifact split (#1816). The placement ref is the
        # SAME CommitTarget status events resolve to. Resolution is best-effort:
        # on a context-resolution error we pass ``None`` and the helper keeps the
        # legacy meta-derived path (C-004 strangler — never break the lifecycle).
        _placement_ref = _resolve_placement_ref(
            repo_root, mission_slug=mission_slug, wp_id=wp_id
        )

        _ensure_planning_artifacts_committed_git(
            repo_root=repo_root,
            feature_dir=feature_dir,
            mission_slug=mission_slug,
            wp_id=wp_id,
            planning_branch=planning_branch,
            auto_commit=bool(auto_commit),
            placement_ref=_placement_ref,
        )

        # Bulk edit occurrence classification gate (FR-006)
        from specify_cli.bulk_edit.gate import ensure_occurrence_classification_ready, render_gate_failure

        gate_result = ensure_occurrence_classification_ready(feature_dir)
        if not gate_result.passed:
            render_gate_failure(gate_result, console)
            raise typer.Exit(1)

        # Inference warning for potentially unmarked bulk edits (FR-009)
        if gate_result.change_mode is None:
            from specify_cli.bulk_edit.inference import (
                scan_spec_file,
                wp_authors_bulk_edit_planning_artifact,
            )

            inference = scan_spec_file(feature_dir)
            planning_wp = wp_authors_bulk_edit_planning_artifact(wp_file, mission_slug)
            if inference.triggered and planning_wp:
                matched = ", ".join(f"'{p}' ({w}pt)" for p, w in inference.matched_phrases)
                console.print(Panel(
                    f"This mission's spec contains language suggesting a bulk edit "
                    f"(score: {inference.score}/{inference.threshold}), but {wp_id} owns "
                    f"the occurrence-map planning artifact.\n"
                    f"  Matched: {matched}\n\n"
                    f"Continuing without --acknowledge-not-bulk-edit for this planning WP.",
                    title="[bold yellow]Bulk Edit Inference Informational[/]",
                    border_style="yellow",
                ))
            elif inference.triggered and not acknowledge_not_bulk_edit:
                matched = ", ".join(f"'{p}' ({w}pt)" for p, w in inference.matched_phrases)
                console.print(Panel(
                    f"This mission's spec contains language suggesting a bulk edit "
                    f"(score: {inference.score}/{inference.threshold}):\n"
                    f"  Matched: {matched}\n\n"
                    f"If this IS a bulk edit, set change_mode to 'bulk_edit' in meta.json.\n"
                    f"If it is NOT, re-run with --acknowledge-not-bulk-edit to suppress.",
                    title="[bold yellow]Bulk Edit Inference Warning[/]",
                    border_style="yellow",
                ))
                raise typer.Exit(1)

        # FR-017 / NFR-004: build and validate the runtime OperationalContext
        # BEFORE any worktree allocation. The shared claim builder is read-only
        # (no worktree, no status event); calling its guards here means a
        # missing-context precondition failure aborts before create_lane_workspace
        # runs, so a failed claim leaves zero new worktree paths and zero new
        # status events.
        from runtime.next.runtime_bridge import build_operational_context_for_claim

        operational_context = build_operational_context_for_claim(
            repo_root=repo_root,
            feature_dir=feature_dir,
            mission_slug=mission_slug,
            wp_id=wp_id,
            actor=actor or "implement-command",
            active_model=actor,
            active_role=actor or "implement-command",
            current_activity="implement",
        )
        operational_context.require_active_role()

        resolved_workspace = resolve_workspace_for_wp(repo_root, mission_slug, wp_id)

        lanes_manifest = None
        lane = None
        from specify_cli.lanes.compute import is_planning_lane
        if not is_planning_lane(resolved_workspace):
            lanes_manifest = require_lanes_json(_lanes_feature_dir)
            lane = lanes_manifest.lane_for_wp(wp_id)
            if lane is None:
                raise ValueError(f"{wp_id} is not assigned to any lane in lanes.json")
            tracker.complete("validate", f"Lane: {lane.lane_id}")
        else:
            tracker.complete("validate", "Execution: repository root planning workspace")
    except (CorruptLanesError, MissingLanesError, WorkPackageStartRejected, ValueError, typer.Exit) as exc:
        tracker.error("validate", str(exc))
        console.print(tracker.render())
        raise typer.Exit(1) from exc
    except Exception as exc:
        tracker.error("validate", str(exc))
        console.print(tracker.render())
        raise typer.Exit(1) from exc

    tracker.start("create")
    effective_actor = actor or "implement-command"
    status_result = None
    status_execution_mode = "direct_repo" if resolved_workspace.resolution_kind == "repo_root" else "worktree"
    try:
        import os as _os

        update_fields(wp_file, {"shell_pid": str(_os.getppid())})
        vcs_backend = _ensure_vcs_in_meta(feature_dir, repo_root)

        # When --base is provided, validate the ref and build a patched
        # LanesManifest that uses it as the mission_branch so the worktree
        # allocator branches from the explicit base instead of auto-detecting.
        # #1684 composition: --base selects only the ROOT the lane branches from;
        # the allocator still merges approved depends_on_lanes tips on top, so
        # cross-lane code propagation is preserved regardless of the chosen root.
        active_lanes_manifest = lanes_manifest
        if base is not None and not is_planning_lane(resolved_workspace):
            _validate_base_ref(repo_root, base)
            # Shallow-patch the manifest's mission_branch so
            # allocate_lane_worktree branches from the explicit ref.
            from dataclasses import replace as _dc_replace

            active_lanes_manifest = _dc_replace(lanes_manifest, mission_branch=base)
            console.print(f"[cyan]→ Using explicit base ref: {base}[/cyan]")
        elif base is not None:
            console.print("[yellow]Warning:[/yellow] --base is ignored for repository-root planning work")

        result = create_lane_workspace(
            repo_root=repo_root,
            mission_slug=mission_slug,
            wp_id=wp_id,
            wp_file=wp_file,
            resolved_workspace=resolved_workspace,
            lanes_manifest=active_lanes_manifest,
            declared_deps=declared_deps,
            vcs_backend_value=vcs_backend.value,
        )
        workspace_path = result.workspace_path
        branch_name = result.branch_name

        try:
            status_result = start_implementation_status(
                feature_dir=feature_dir,
                mission_slug=mission_slug,
                wp_id=wp_id,
                actor=effective_actor,
                workspace_context=f"{status_execution_mode}:{workspace_path}",
                execution_mode=status_execution_mode,
                repo_root=repo_root,
            )
        except WorkPackageClaimConflict as exc:
            console.print(f"[red]Error:[/red] {exc}")
            raise typer.Exit(1) from exc
        except TransitionError as exc:
            console.print(f"[red]Error:[/red] Could not start implementation status: {exc}")
            raise typer.Exit(1) from exc

        if result.lane_id is None:
            tracker.complete("create", f"Repository root: {workspace_path.relative_to(repo_root)}")
        elif result.is_reuse:
            tracker.complete("create", f"Reused lane {result.lane_id}: {workspace_path.relative_to(repo_root)}")
        else:
            tracker.complete("create", f"Lane {result.lane_id}: {workspace_path.relative_to(repo_root)}")
        console.print(tracker.render())
        if result.mission_branch:
            console.print(f"[cyan]→ Mission branch: {result.mission_branch}[/cyan]")
        if result.branch_name:
            console.print(f"[cyan]→ Lane branch: {result.branch_name}[/cyan]")
        else:
            console.print("[cyan]→ Workspace contract: repository root planning workspace[/cyan]")
    except typer.Exit:
        console.print(tracker.render())
        raise
    except Exception as exc:
        tracker.error("create", f"workspace allocation failed: {exc}")
        console.print(tracker.render())
        console.print(f"\n[red]Error:[/red] Workspace allocation failed: {exc}")
        current_lane = _get_wp_lane_from_event_log(feature_dir, wp_id)
        if current_lane in {Lane.PLANNED, Lane.CLAIMED, Lane.IN_PROGRESS}:
            try:
                emit_status_transition_transactional(
                    TransitionRequest(
                        feature_dir=feature_dir,
                        mission_slug=mission_slug,
                        wp_id=wp_id,
                        to_lane=Lane.BLOCKED,
                        actor=effective_actor,
                        execution_mode=status_execution_mode,
                        reason="worktree_alloc_failed",
                        policy_metadata={"evidence": str(exc)},
                        repo_root=repo_root,
                    )
                )
            except Exception as _blocked_exc:
                console.print(
                    f"[yellow]Warning:[/yellow] Could not emit blocked transition after alloc failure: {_blocked_exc}"
                )
        raise typer.Exit(1) from exc

    try:
        if status_result is not None and status_result.status_changed:
            commit_msg = f"chore: {wp_id} claimed for implementation"
            if auto_commit:
                from specify_cli.cli.commands.agent.tasks import _collect_status_artifacts

                meta_file = feature_dir / "meta.json"
                config_file = repo_root / ".kittify" / "config.yaml"
                # #2155 (FR-002 / T011): bundle ONLY primary-surface artifacts into
                # the primary-root claim commit. The status transition was already
                # committed to the coordination branch by
                # ``start_implementation_status`` (the transactional emitter); under
                # coord topology the coord-owned status files (events.jsonl /
                # status.json) resolved by ``_collect_status_artifacts`` live UNDER
                # ``.worktrees/``, so staging them from the primary root trips the
                # #1887 ``SafeCommitPathPolicyError`` guard — which the former broad
                # ``except`` swallowed as an "Auto-commit skipped" warning, leaving
                # the feature branch dirty (the surviving #2155 residual). The
                # canonical ``COORD_OWNED_STATUS_FILES`` partition drops those files
                # on coord topology only; on a flat/legacy mission they ARE canonical
                # on PRIMARY and stay in the bundle.
                if routes_through_coordination(resolve_topology(repo_root, mission_slug)):
                    from specify_cli.status import COORD_OWNED_STATUS_FILES

                    status_paths = [
                        path.resolve()
                        for path in _collect_status_artifacts(feature_dir)
                        if path.name not in COORD_OWNED_STATUS_FILES
                    ]
                else:
                    status_paths = [path.resolve() for path in _collect_status_artifacts(feature_dir)]
                files_to_commit = [wp_file.resolve(), *status_paths]
                if meta_file.exists():
                    files_to_commit.append(meta_file.resolve())
                if config_file.exists():
                    files_to_commit.append(config_file.resolve())

                # WP03 / T011 / T012 / D11: the status claim commit routes
                # through the SAME seam-resolved ``_placement_ref`` planning
                # artifacts resolve to (C-PLACE-1) instead of the forbidden
                # ``_get_current_branch(repo_root) or planning_branch``
                # checkout-derived grammar. A resolution failure now FAILS
                # CLOSED (see ``_resolve_claim_commit_target``) rather than
                # silently committing to whatever branch is checked out.
                _claim_commit_target = _resolve_claim_commit_target(_placement_ref)
                try:
                    safe_commit(
                        repo_root=repo_root,
                        worktree_root=repo_root,
                        target=_claim_commit_target,
                        message=commit_msg,
                        paths=tuple(files_to_commit),
                    )
                    console.print(f"[cyan]→ {wp_id} moved to 'doing'[/cyan]")
                except SafeCommitPathPolicyError:
                    # #2155 (FR-002 / T011): a wrong-surface guard refusal is a real
                    # defect, not an "Auto-commit skipped" warning — re-raise so it
                    # surfaces instead of leaving the branch silently dirty. The
                    # partition above prevents this on a correct bundle; reaching here
                    # means a coord-owned path leaked into the primary commit and the
                    # C-006 guard MUST stay authoritative (never swallowed).
                    raise
                except Exception as _commit_exc:  # noqa: BLE001 — non-policy git failures stay soft
                    console.print(
                        f"[yellow]Warning:[/yellow] Could not auto-commit lane change: {_commit_exc}"
                    )
            else:
                console.print(f"[cyan]→ {wp_id} moved to 'doing' (auto-commit disabled, changes staged only)[/cyan]")
    except SafeCommitPathPolicyError:
        # #2155 (FR-002 / T011): a wrong-surface guard refusal must NOT be folded
        # into the soft "Could not update WP status" warning — let it propagate so
        # the defect surfaces (the inner handler already re-raised it on purpose).
        raise
    except PlacementResolutionRequired:
        # WP03 / D11: a fail-closed placement-resolution refusal must NOT be
        # folded into the soft "Could not update WP status" warning either —
        # that would silently resurrect the checkout-derived fallback this
        # error exists to forbid. Let it propagate so the operator sees and
        # acts on the structured, actionable message.
        raise
    except Exception as exc:
        console.print(f"[yellow]Warning:[/yellow] Could not update WP status: {exc}")

    if json_output:
        result_execution_mode = result.execution_mode if isinstance(result.execution_mode, str) else resolved_workspace.execution_mode
        workspace_rel = str(workspace_path.relative_to(repo_root))
        # FR-004/FR-005 (#2186): the JSON ``mission_slug``/``mission_number``/
        # ``mission_type`` come from meta.json, which lives ONLY on the PRIMARY
        # checkout. ``feature_dir`` above may have landed on the coord husk (the
        # topology-aware resolve→candidate cascade); give the identity read its OWN
        # PRIMARY anchor rather than relying on the conditional meta-fallback above
        # (C-EXCL-FALLBACK — so that fallback can be retired later). NFR-004: no
        # primary-dir stub — this resolves the durable PRIMARY home for real.
        from specify_cli.missions._read_path_resolver import (
            _canonicalize_primary_read_handle,
            primary_feature_dir_for_mission,
        )

        _identity_dir = primary_feature_dir_for_mission(
            repo_root, _canonicalize_primary_read_handle(repo_root, mission_slug)
        )
        identity = resolve_mission_identity(_identity_dir)
        print(
            json.dumps(
                {
                    "workspace": workspace_rel,
                    "workspace_path": workspace_rel,
                    "branch": branch_name,
                    "mission_slug": identity.mission_slug,
                    "mission_number": identity.mission_number,
                    "mission_type": identity.mission_type,
                    "wp_id": wp_id,
                    "lane_id": result.lane_id,
                    "execution_mode": result_execution_mode,
                    "status": "created",
                    # FR-006: surface the lane-suffixed test DB env so
                    # downstream agents / test runners can `os.environ.update`
                    # without re-deriving the helper. Empty dict for
                    # planning-artifact workspaces (lane_id is None) or
                    # when the result type doesn't carry a real dict
                    # (e.g. a MagicMock in unit tests).
                    "lane_test_env": (
                        result.lane_test_env
                        if isinstance(getattr(result, "lane_test_env", None), dict)
                        else {}
                    ),
                }
            )
        )
        return

    if result.lane_id is None:
        console.print("\n[bold green]✓ Repository-root workspace ready[/bold green]")
        console.print()
        console.print("[bold yellow]" + "=" * 72 + "[/bold yellow]")
        console.print("[bold yellow]Planning-artifact work for this WP happens in the repository root[/bold yellow]")
        console.print("[bold yellow]" + "=" * 72 + "[/bold yellow]")
        console.print()
        console.print(f"  [bold]cd {workspace_path}[/bold]")
        console.print()
        console.print("[dim]This WP does not get a lane worktree or workspace context file.[/dim]")
        console.print("[dim]Make planning-artifact changes directly in the repository root.[/dim]")
        return

    console.print("\n[bold green]✓ Lane worktree ready[/bold green]")
    console.print()
    console.print("[bold yellow]" + "=" * 72 + "[/bold yellow]")
    console.print("[bold yellow]CRITICAL: Change to the lane worktree before editing files[/bold yellow]")
    console.print("[bold yellow]" + "=" * 72 + "[/bold yellow]")
    console.print()
    console.print(f"  [bold]cd {workspace_path}[/bold]")
    console.print()
    console.print("[dim]All file edits, writes, and commits MUST happen in this directory.[/dim]")
    console.print("[dim]Writing to the main repository instead of the lane worktree is a critical error.[/dim]")

    # FR-006: surface the lane-suffixed test DB env so the agent can
    # export it before running the project's test suite. Persisted to
    # WorkspaceContext for resurrection by later commands; printed here
    # so a human operator can copy/paste in their shell.
    lane_env = getattr(result, "lane_test_env", None)
    if isinstance(lane_env, dict) and lane_env:
        console.print()
        console.print("[bold cyan]Lane-specific test environment (FR-006):[/bold cyan]")
        for key, value in sorted(lane_env.items()):
            console.print(f"  export {key}={value}")
        console.print(
            "[dim]Two parallel SaaS / Django lanes will collide on a single shared test DB"
            " unless these are exported in the lane's test process.[/dim]"
        )


__all__ = ["_ensure_vcs_in_meta", "detect_feature_context", "find_wp_file", "implement"]
