"""Implement command - allocate the lane worktree for a work package."""

from __future__ import annotations

import functools
import json
import re
import subprocess
from collections.abc import Callable
from io import StringIO
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Any, NamedTuple

import typer
from pydantic import ValidationError
from specify_cli.cli.console import console
from rich.panel import Panel

from specify_cli.cli import StepTracker
from specify_cli.cli.selector_resolution import resolve_mission_handle
from specify_cli.core.context_validation import require_main_repo
from specify_cli.core.time_utils import now_utc_iso
from specify_cli.core.errors import PlacementResolutionRequired
from specify_cli.core.git_ops import get_current_branch
from specify_cli.core.vcs import VCSBackend
from specify_cli.mission_metadata import resolve_mission_identity, set_vcs_lock
from specify_cli.frontmatter import FrontmatterError
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
from specify_cli.coordination.coherence import is_coord_residue_churn, is_status_state_path
from specify_cli.lanes.implement_support import create_lane_workspace
from specify_cli.lanes.persistence import require_lanes_json
from specify_cli.coordination.status_transition import emit_status_transition_transactional
from specify_cli.status import TransitionError
from specify_cli.status import Lane, TransitionRequest
from specify_cli.status import (
    WorkPackageClaimConflict,
    WorkPackageStartRejected,
    start_implementation_status,
)
from specify_cli.task_utils import TaskCliError, find_repo_root
from specify_cli.workspace.context import resolve_workspace_for_wp

# WP03 / T019: re-export shim -- bare import (NOT added to __all__, see the
# bottom of this file). implement_cores.py houses the pure git-porcelain/diff
# and placement decision cores (git injected as a port); this module keeps
# them importable at their historical `specify_cli.cli.commands.implement.*`
# location for external callers/tests and is the "git executor" for the one
# staging-decision core (_ensure_planning_artifacts_committed_git, T016).
from specify_cli.cli.commands.implement_cores import (  # noqa: F401 -- shim re-export
    _committed_meta_mapping,
    _drop_if,
    _feature_dir_status_entries,
    detect_structural_planning_changes,
    _files_changed_vs_ref,
    _is_runtime_frontmatter_only_wp_diff,
    _is_self_write_only_diff,
    _is_vcs_lock_only_meta_diff,
    _parse_meta_mapping,
    _parse_wp_frontmatter,
    _placement_coord_filter,
    _PorcelainEntry,
    _commit_target_ref_for,
    _resolve_claim_commit_target,
    _resolve_placement_ref,
    _status_paths_for_commit,
    resolve_planning_artifact_staging,
)

if TYPE_CHECKING:
    # WP03 / T013: type-only -- ``_run_recover_mode`` and its extracted
    # helpers keep the real import lazy (inside the function body) to match
    # the module's existing deferred-import discipline; this gives mypy the
    # shapes without adding a runtime import edge to ``specify_cli.lanes``.
    from specify_cli.lanes.recovery import RecoveryReport, RecoveryState

_WP_ID_RE = re.compile(r"^WP\d{2}$", re.IGNORECASE)
# WP03 / S1192: the rich-markup error prefix, repeated across the
# planning-artifact commit helper this WP touches -- hoisted to one constant
# rather than restated at each ``console.print`` call site.
_RED_ERROR_PREFIX = "[red]Error:[/red] "
# WP02 / T008 / S1192: the workspace-ready banner's rich-markup open/close
# tags, repeated ~8x in ``_print_workspace_ready_banner`` -- hoisted to
# constants rather than restated at each call site. The distinct
# ``title="[bold yellow]...[/]"`` uses elsewhere in this module (bulk-edit
# inference banners) use a different close tag and are left as-is.
_BANNER_OPEN = "[bold yellow]"
_BANNER_CLOSE = "[/bold yellow]"


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


def _json_wrapper_resolve_wp_id(args: tuple[Any, ...], kwargs: dict[str, Any]) -> Any:
    """Resolve the ``wp_id`` used for JSON error payloads: the ``wp_id``
    kwarg first, else the first positional argument (the Typer commands
    wrapped by ``_json_safe_output`` all take ``wp_id`` as arg 0)."""
    wp_id = kwargs.get("wp_id")
    if wp_id is None and args:
        wp_id = args[0]
    return wp_id


def _json_wrapper_begin_capture(json_output: bool) -> tuple[bool, StringIO | None]:
    """Snapshot ``console.quiet`` and, in ``--json`` mode, redirect console
    output into an in-memory buffer so wrapped-function chatter never leaks
    onto stdout ahead of the machine-readable payload."""
    previous_quiet = console.quiet
    capture_buffer: StringIO | None = None
    if json_output:
        capture_buffer = StringIO()
        console.file = capture_buffer
        console.quiet = False
    return previous_quiet, capture_buffer


def _json_wrapper_summarize_capture(capture_buffer: StringIO | None) -> str:
    """Return the last 20 non-blank, rstripped lines captured from the
    console -- the JSON error-summary shape pinned by T010."""
    lines = [line.rstrip() for line in (capture_buffer.getvalue() if capture_buffer else "").splitlines() if line.strip()]
    return "\n".join(lines[-20:]).strip() if lines else "implement command failed"


def _json_wrapper_emit_error_payload(error: str, wp_id: Any) -> None:
    payload: dict[str, Any] = {"status": "error", "error": error}
    if wp_id:
        payload["wp_id"] = str(wp_id)
    print(json.dumps(payload))


def _json_wrapper_handle_typer_exit(exc: typer.Exit, json_output: bool, capture_buffer: StringIO | None, wp_id: Any) -> None:
    """Emit the JSON error payload for a ``typer.Exit`` failure -- unless
    ``exit_code`` is falsy (0), which is a success exit and never gets a
    payload. The caller re-raises ``exc`` verbatim afterwards; this helper
    never raises."""
    if json_output and getattr(exc, "exit_code", 1):
        summary = _json_wrapper_summarize_capture(capture_buffer)
        _json_wrapper_emit_error_payload(summary or "implement command failed", wp_id)


def _json_wrapper_end_capture(previous_quiet: bool) -> None:
    console.quiet = previous_quiet
    # Reset _file to None so the console uses sys.stdout dynamically.
    # Restoring previous_file can leave the console pointing at a closed
    # pytest capsys buffer when tests run in sequence.
    console._file = None


def _json_safe_output(func: Callable[..., Any]) -> Callable[..., Any]:
    """Ensure --json mode stays machine-readable on both success and failure."""

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        json_output = bool(kwargs.get("json_output", False))
        wp_id = _json_wrapper_resolve_wp_id(args, kwargs)
        previous_quiet, capture_buffer = _json_wrapper_begin_capture(json_output)

        try:
            return func(*args, **kwargs)
        except typer.Exit as exc:
            _json_wrapper_handle_typer_exit(exc, json_output, capture_buffer, wp_id)
            raise
        except Exception as exc:  # pragma: no cover - defensive
            if json_output:
                _json_wrapper_emit_error_payload(str(exc), wp_id)
            raise typer.Exit(1) from exc
        finally:
            _json_wrapper_end_capture(previous_quiet)

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


def _feature_dir_status_paths(repo_root: Path, feature_dir: Path) -> list[str]:
    """Repo-relative paths of *writable* (non-structural) feature-dir changes."""
    return [e.path for e in _feature_dir_status_entries(repo_root, feature_dir) if not e.is_structural]


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
        console.print(f"\n[red]Error:[/red] Planning artifacts must be committed on {planning_branch}.")
        console.print(f"Current branch: {current_branch}")
        raise typer.Exit(1)

    if auto_commit:
        return

    console.print("\n[yellow]Auto-commit disabled.[/yellow] Commit planning artifacts first:")
    console.print(f"  git add -f {feature_dir}")
    console.print(f'  git commit -m "chore: planning artifacts for {mission_slug}"')
    raise typer.Exit(1)


def _load_primary_anchored_mission_meta(
    repo_root: Path | None, mission_slug: str
) -> dict[str, Any] | None:
    """FR-003 cascade layer 1: read the PRIMARY-checkout ``meta.json``.

    ``coordination_branch`` / ``mission_id`` / ``mid8`` live ONLY in the
    PRIMARY-checkout meta.json; the coord worktree's mission dir has none.
    ``feature_dir`` (the caller's fallback, see
    :func:`_load_fallback_mission_meta`) is topology-aware and prefers the
    coord worktree once materialized — reading meta there returns empty, so
    every identifier silently fell back to the slug (``mid8`` ->
    ``<slug>0000``), which then names a non-existent coord branch/worktree at
    claim time ("Failed to resolve coordination worktree for
    <slug>-<slug-fallback>"). Anchor the config read on the canonical primary
    dir first (the caller threads the true main ``repo_root``), so config is
    read before topology is resolved.

    Returns ``None`` when *repo_root* is not supplied or the primary meta is
    missing/corrupt (legacy). Does NOT catch an ambiguous-handle raise from
    :func:`_canonicalize_primary_read_handle` — that must propagate (no
    silent pick, C-009).
    """
    if repo_root is None:
        return None

    from specify_cli.mission_metadata import load_meta as _load_meta
    from specify_cli.missions._read_path_resolver import (
        _canonicalize_primary_read_handle,
        primary_feature_dir_for_mission,
    )

    # FR-011 / T012: fold the handle to its canonical dir NAME first so a bare
    # mid8 / human slug resolves the durable ``<slug>-<mid8>`` home (ambiguous
    # handle RAISES — no silent pick).
    _canonical_handle = _canonicalize_primary_read_handle(repo_root, mission_slug)
    try:
        return _load_meta(primary_feature_dir_for_mission(repo_root, _canonical_handle))
    except Exception:  # noqa: BLE001 — meta missing/corrupt is legacy
        return None


def _load_fallback_mission_meta(feature_dir: Path) -> dict[str, Any] | None:
    """FR-003 cascade layer 2: read ``meta.json`` off the passed *feature_dir*.

    Only consulted when :func:`_load_primary_anchored_mission_meta` yields
    ``None`` (no ``repo_root``, or the primary meta is missing/corrupt).
    """
    from specify_cli.mission_metadata import load_meta as _load_meta

    try:
        return _load_meta(feature_dir)
    except Exception:  # noqa: BLE001 — meta missing/corrupt is legacy
        return None


def _extract_mission_identifiers_from_meta(
    mission_meta: dict[str, Any] | None, mission_slug: str
) -> tuple[str | None, str | None, str | None]:
    """Pull ``(coord_branch, mission_id, mid8)`` out of a resolved meta dict.

    mid8 precedence: the stored ``meta["mid8"]`` value wins; otherwise the
    fallback routes through the authoritative :func:`resolve_mid8` resolver
    (WP03 / FR-009). ``or None`` preserves the prior ``None`` contract
    (``resolve_mid8`` declines to ``""``).
    """
    if not isinstance(mission_meta, dict):
        return None, None, None

    coord_branch: str | None = mission_meta.get("coordination_branch") or None
    mission_id: str | None = mission_meta.get("mission_id") or None

    from specify_cli.lanes.branch_naming import resolve_mid8

    mid8: str | None = mission_meta.get("mid8") or (
        resolve_mid8(
            mission_slug,
            mission_id=mission_id if isinstance(mission_id, str) else None,
        )
        or None
    )
    return coord_branch, mission_id, mid8


def _compute_effective_bookkeeping_ids(
    mission_slug: str,
    mission_id: str | None,
    mid8: str | None,
    coord_branch: str | None,
) -> tuple[str, str]:
    """Derive ``(effective_mission_id, effective_mid8)`` from the resolved triple.

    ``effective_mission_id`` falls back to ``legacy-<slug>`` when no declared
    ``mission_id`` is available. ``effective_mid8`` routes through the
    canonical fail-closed authority (FR-007) rather than fabricating a
    zero-padded mid8 from the slug — that idiom named a non-existent coord
    branch/worktree at claim time.
    """
    effective_mission_id = str(mission_id) if mission_id else f"legacy-{mission_slug}"

    from specify_cli.lanes.branch_naming import resolve_transaction_mid8

    effective_mid8 = resolve_transaction_mid8(
        mission_slug,
        mission_id=str(mission_id) if mission_id else None,
        mid8=str(mid8) if mid8 else None,
        coordination_branch=coord_branch,
    )
    return effective_mission_id, effective_mid8


class _BookkeepingTransactionIdentifiers(NamedTuple):
    """The identifiers :func:`_resolve_bookkeeping_transaction_identifiers` returns.

    A ``NamedTuple`` (PR #2662 squad LOW-3 hardening): it IS a 5-tuple, so the
    frozen C-006 contract holds by construction — ``tasks_move_task.py`` reads
    ``[0]`` cross-lane and the in-module caller unpacks all five, both unchanged
    — while the fields are now named/structural instead of a bare positional
    pin. Arity and order MUST NOT change (C-006).
    """

    coord_branch: str | None
    mission_id: str | None
    mid8: str | None
    effective_mission_id: str
    effective_mid8: str


def _resolve_bookkeeping_transaction_identifiers(
    feature_dir: Path,
    mission_slug: str,
    repo_root: Path | None = None,
) -> _BookkeepingTransactionIdentifiers:
    """Resolve the ``(coord_branch, mission_id, mid8, effective_mission_id,
    effective_mid8)`` bookkeeping identifiers as a 5-field NamedTuple.

    C-006 (frozen contract, #2649): ``tasks_move_task.py`` imports this
    symbol and reads only element ``[0]`` cross-lane, while the in-module
    caller (``_ensure_planning_artifacts_committed_git``) unpacks all five —
    the 5-tuple arity and order MUST NOT change (a NamedTuple keeps both the
    positional and the new named access working).
    """
    mission_meta = _load_primary_anchored_mission_meta(repo_root, mission_slug)
    if mission_meta is None:
        mission_meta = _load_fallback_mission_meta(feature_dir)

    coord_branch, mission_id, mid8 = _extract_mission_identifiers_from_meta(
        mission_meta, mission_slug
    )
    effective_mission_id, effective_mid8 = _compute_effective_bookkeeping_ids(
        mission_slug, mission_id, mid8, coord_branch
    )
    return _BookkeepingTransactionIdentifiers(
        coord_branch, mission_id, mid8, effective_mission_id, effective_mid8
    )


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


def _print_structural_planning_refusal(structural: list[_PorcelainEntry]) -> None:
    """Print the #1598 fail-closed refusal for structural planning-artifact
    changes (deletions/renames/copies) that cannot be auto-committed to the
    coordination branch.

    ``BookkeepingTransaction.write_artifact`` is a write-only API that cannot
    remove an old path from the coordination branch, so silently committing only
    the additions would leave the branch incoherent (stale deleted/renamed-from
    artifacts). The claim must refuse; the operator commits the structural change
    to the coordination branch out-of-band, then re-runs the claim.
    """
    console.print(f"\n{_RED_ERROR_PREFIX}Uncommitted structural planning-artifact changes (deletions/renames) cannot be auto-committed to the coordination branch:")
    for entry in structural:
        console.print(f"  {entry.xy.strip() or entry.xy} {entry.path}")
    console.print("\nCommit these structural changes to the coordination branch yourself (e.g. `git rm`/`git mv` + commit), then re-run the claim.")


def _ensure_planning_artifacts_committed_git(
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
    artifact_source_dir = _planning_artifact_source_dir(repo_root, feature_dir, mission_slug)

    # Squad-B1 (#2464): fail closed on structural planning-artifact changes
    # BEFORE resolving the coordination-branch filter below (which can raise on
    # a broken topology). This restores the pre-degod ordering so a topology
    # fault never preempts the tailored structural-refusal message under a
    # double fault (structural change present AND topology resolution raising).
    structural = detect_structural_planning_changes(repo_root, artifact_source_dir)
    if structural:
        _print_structural_planning_refusal(structural)
        raise typer.Exit(1)

    # WP06 / T019 / C-PLACE-1: when the context supplies a placement ref, the
    # coord/flattened/primary decision comes from that single CommitTarget — no
    # independent meta-derived coord logic (C-005). Otherwise fall back to the
    # legacy meta-derived coord branch (C-004 strangler).
    if placement_ref is not None:
        coord_branch_for_filter = _placement_coord_filter(repo_root, mission_slug, placement_ref)
    else:
        coord_branch_for_filter = _resolve_bookkeeping_transaction_identifiers(feature_dir, mission_slug, repo_root)[0]

    # T016: the staging DECISION (structural fail-closed check, #2222
    # vcs-lock exclusion, dedup, idempotency filtering) is a pure core in
    # implement_cores.py; this function is the git EXECUTOR -- it turns a
    # non-empty ``plan.structural`` into the fail-closed print+exit below and
    # an empty ``plan.files_to_commit`` into a silent no-op return, then does
    # the actual BookkeepingTransaction I/O.
    extra_file_paths = _feature_dir_file_paths(repo_root, artifact_source_dir) if coord_branch_for_filter else []
    # PR #2662 squad fix: on the healthy ``placement_ref is not None`` path the
    # whole batch commits VERBATIM to ``placement_ref.ref`` (the un-partitioned
    # C-004/#2160 deferral). Compare every file against that same write target so
    # a PRIMARY artifact already-identical on the (coord) ref is not re-committed
    # into an empty commit that hard-fails the claim (read=HEAD / write=coord
    # divergence; #2653). ``None`` keeps the PRIMARY-vs-HEAD / COORD-vs-coord split.
    verbatim_ref = placement_ref.ref if placement_ref is not None else None
    plan = resolve_planning_artifact_staging(
        repo_root,
        artifact_source_dir,
        coord_branch_for_filter,
        extra_file_paths,
        auto_commit=auto_commit,
        verbatim_ref=verbatim_ref,
    )

    files_to_commit = plan.files_to_commit
    if not files_to_commit:
        return

    if plan.status_paths_to_commit:
        _print_uncommitted_planning_artifacts(files_to_commit)
        _print_planning_artifact_commit_instructions(
            current_branch,
            planning_branch,
            auto_commit,
            artifact_source_dir,
            mission_slug,
        )

    commit_msg = f"chore: planning artifacts for {mission_slug}\n\nAuto-committed by spec-kitty before creating the lane worktree for {wp_id}"

    _commit_planning_artifacts_transaction(
        repo_root=repo_root,
        feature_dir=feature_dir,
        mission_slug=mission_slug,
        planning_branch=planning_branch,
        files_to_commit=files_to_commit,
        commit_msg=commit_msg,
        placement_ref=placement_ref,
    )


def _partition_files_for_commit(files_to_commit: list[str]) -> tuple[list[str], list[str]]:
    """Split *files_to_commit* into PRIMARY and COORD-residue groups (T007).

    Mirrors ``commit_router._group_files_by_partition``: classifies each
    repo-relative path with the same
    :func:`~specify_cli.coordination.coherence.is_coord_residue_churn`
    predicate WP01 wired into the read-side ``resolve_precondition_ref`` --
    one authority (NFR-004), no new partition literal (WP12 retired the
    former ``mission_runtime`` predicate onto this owner leg). Everything NOT
    explicitly COORD-residue (PRIMARY kinds, ``meta.json``, unrecognized paths)
    defaults to the PRIMARY group -- the same fail-safe-toward-primary
    direction as the read side.
    """
    primary_files: list[str] = []
    coord_files: list[str] = []
    for path_str in files_to_commit:
        if is_coord_residue_churn(path_str):
            coord_files.append(path_str)
        else:
            primary_files.append(path_str)
    return primary_files, coord_files


def _run_planning_artifact_commit(
    *,
    repo_root: Path,
    mission_id: str,
    mission_slug: str,
    mid8: str,
    destination_ref: str,
    files: list[str],
    commit_msg: str,
) -> None:
    """Execute ONE ``BookkeepingTransaction`` commit of *files* to *destination_ref*.

    Extracted from :func:`_commit_planning_artifacts_transaction` (T007) so
    the partition-aware caller below can run this once per PRIMARY/COORD-
    residue group without duplicating the transaction I/O + exception
    handling. Preserves the pre-partition byte-for-byte behavior for a single
    group covering all of ``files_to_commit``.
    """
    from specify_cli.coordination.transaction import BookkeepingTransaction

    with BookkeepingTransaction.acquire(
        repo_root=repo_root,
        mission_id=mission_id,
        mission_slug=mission_slug,
        mid8=mid8,
        destination_ref=destination_ref,
        operation=f"planning artifacts for {mission_slug}",
    ) as txn:
        for path_str in files:
            repo_path = Path(path_str)
            source_path = (repo_root / repo_path).resolve()
            if not source_path.exists():
                continue
            txn.write_artifact(repo_path, source_path.read_bytes())
        try:
            txn.commit(commit_msg)
        except Exception as exc:  # noqa: BLE001 — surface as exit-1
            console.print(f"{_RED_ERROR_PREFIX}Failed to commit planning artifacts to {destination_ref}: {exc}")
            raise typer.Exit(1) from exc


def _commit_planning_artifacts_transaction(
    *,
    repo_root: Path,
    feature_dir: Path,
    mission_slug: str,
    planning_branch: str,
    files_to_commit: list[str],
    commit_msg: str,
    placement_ref: CommitTarget | None,
) -> None:
    """T016 git-executor tail: run the BookkeepingTransaction commit(s).

    Split out of :func:`_ensure_planning_artifacts_committed_git` so that
    function's own complexity stays scoped to the staging decision it drives;
    this helper owns only the transaction I/O (identifier resolution,
    destination-ref selection, ``BookkeepingTransaction`` write+commit,
    legacy-vs-coordination status prints).

    WP06 T026: route planning-artifact commits through BookkeepingTransaction
    so the commit lands on the mission's coordination branch (FR-005) and any
    write of status events is atomically reversible (FR-010). Legacy missions
    (created pre-WP03) have no ``coordination_branch`` in meta.json; the
    transaction's built-in legacy fallback (``_is_legacy_mission`` +
    ``_resolve_legacy_lane_destination`` in ``coordination/transaction.py``)
    overrides ``destination_ref`` with the actual checked-out lane branch, so
    the pre-flight policy gate, surgical rollback, and feature-status lock
    apply uniformly to coordination-branch and legacy missions alike (FR-027).

    WP03 / T011 / D11: no inline ``coord_branch if coord_branch else
    planning_branch`` grammar (the forbidden pattern named in
    contracts/seam-api.md's consumer table). When a ``placement_ref`` was
    threaded (modern, non-legacy missions), it is already the ONE
    seam-resolved :class:`CommitTarget` planning artifacts AND status events
    resolve to (C-PLACE-1) -- use its ``.ref`` directly instead of
    reconstructing the coord/primary choice a second time from
    ``coord_branch``. Genuinely-legacy missions (no ``placement_ref``) keep
    the existing meta-derived placeholder -- out of this WP's scope (#2453;
    the value is never persisted).

    WP02 / T007 / FR-003 / INV-1: pre-fix, the ``elif coord_branch:`` (meta-
    derived) branch below committed EVERY file in ``files_to_commit`` through
    ONE transaction to the coordination branch, so a genuinely-dirty PRIMARY
    artifact would land on coordination, never the primary/target branch.
    Post-fix, THAT branch partitions ``files_to_commit``
    (:func:`_partition_files_for_commit`) into a PRIMARY group (committed to
    ``planning_branch``, the mission's target branch) and a COORD-residue
    group (committed to the coordination branch) -- two transactions when
    both groups are non-empty, mirroring
    ``commit_router._group_files_by_partition``'s own two-group split.

    C-004 (mission scope): the ``if placement_ref is not None:`` branch is
    UNCHANGED by this WP -- it keeps committing the whole batch to
    ``placement_ref.ref`` verbatim (WP03 / T011 / D11's pinned "no
    re-derivation" contract, ``test_effective_destination_ref_is_placement_ref_verbatim``).
    C-004 explicitly defers retiring that seam path's "one ref for
    everything" model (and its now-false C-PLACE-1 docstring) to the
    separate #2160 placement-seam SSOT cluster -- out of scope here.

    #2648 (WP01) narrow-triple fail-close: this function has exactly FOUR
    ``placement_ref``/``coord_branch``/protection outcomes, and only ONE of
    them raises --

    - ``placement_ref is not None`` -- commit verbatim to ``placement_ref.ref``
      (C-004, unchanged by this WP).
    - ``placement_ref is None`` and ``not coord_branch`` -- flat/legacy
      mission, single transaction to ``planning_branch`` (C-004 strangler,
      unchanged).
    - ``placement_ref is None`` and ``coord_branch`` truthy and
      ``is_protected(planning_branch)`` -- the NARROW TRIPLE: raises
      :class:`PlacementResolutionRequired` with the SAME operator message as
      the status-commit half (``_resolve_claim_commit_target``,
      implement_cores.py). A real mission's ``planning_branch`` is never
      main/master (it is the mission's dedicated feature branch), so this
      only fires for a degenerate fixture/edge case or a torn-down topology;
      pre-fix, this arm silently diverted the WHOLE dirty-PRIMARY batch to
      the coordination branch instead of raising -- a genuinely-dirty
      PRIMARY artifact would never reach ``planning_branch`` and the operator
      would get no signal that the write placement is undecidable. Loud
      fail-close beats a silent wrong-branch commit here (D11).
    - ``placement_ref is None`` and ``coord_branch`` truthy and
      ``planning_branch`` is NOT protected -- meta-derived coordination
      mission, partition-aware split (unchanged: see ``T007`` below).

    Only the narrow triple raises; the other three outcomes still commit.
    """
    (
        coord_branch,
        mission_id,
        mid8,
        effective_mission_id,
        effective_mid8,
    ) = _resolve_bookkeeping_transaction_identifiers(feature_dir, mission_slug, repo_root)

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

    is_legacy = not (coord_branch and mission_id and mid8)
    if is_legacy:
        console.print(
            f"\n[cyan]Auto-committing planning artifacts to {planning_branch}...[/cyan] "
            f"[dim](legacy path -- mission has no coordination_branch; "
            f"routed through BookkeepingTransaction for FR-020/FR-027 atomicity)[/dim]"
        )

    if placement_ref is not None:
        # WP03 / T011 / D11 (unchanged, C-004): the seam-resolved value is
        # used VERBATIM for the whole batch -- no re-derivation, no per-file
        # partition override.
        _run_planning_artifact_commit(
            repo_root=repo_root,
            mission_id=effective_mission_id,
            mission_slug=mission_slug,
            mid8=effective_mid8,
            destination_ref=placement_ref.ref,
            files=files_to_commit,
            commit_msg=commit_msg,
        )
    elif not coord_branch:
        # Flattened/legacy mission: no coordination branch at all -- the
        # historical single transaction to ``planning_branch``, routed
        # through the shared ``_commit_target_ref_for`` expression (FR-005 ref
        # half) so this write-side destination and the read-side idempotency
        # compare cannot silently diverge (#2650 / WP04).
        _run_planning_artifact_commit(
            repo_root=repo_root,
            mission_id=effective_mission_id,
            mission_slug=mission_slug,
            mid8=effective_mid8,
            destination_ref=_commit_target_ref_for(planning_branch),
            files=files_to_commit,
            commit_msg=commit_msg,
        )
    elif ProtectionPolicy.resolve(repo_root).is_protected(planning_branch):
        # #2648 (WP01) narrow-triple fail-close: ``placement_ref is None`` AND
        # the meta-derived ``coord_branch`` is truthy AND
        # ``is_protected(planning_branch)`` -- EXACTLY the precondition where
        # the status-commit half (``_resolve_claim_commit_target``,
        # implement_cores.py) already raises ``PlacementResolutionRequired``.
        # Pre-fix, this arm silently diverted the WHOLE dirty-PRIMARY batch to
        # the coordination branch instead of the (protected) target branch --
        # a genuinely-dirty PRIMARY artifact would never reach
        # ``planning_branch``. Raising here (rather than falling back to a
        # coord-only commit) makes both halves of the claim agree: neither
        # commits partially or silently when the canonical write placement
        # cannot be resolved for a protected planning branch.
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
    else:
        # T007: meta-derived coordination mission -- partition-aware commit.
        # A genuinely-dirty PRIMARY artifact lands on ``planning_branch``
        # (never coordination); COORD-residue artifacts still land on the
        # coordination branch. Only the group(s) that are non-empty run.
        primary_files, coord_files = _partition_files_for_commit(files_to_commit)
        if primary_files:
            # FR-005 ref half (#2650 / WP04): the PRIMARY-group destination
            # is derived from the SAME ``_commit_target_ref_for`` expression the
            # read-side idempotency compare uses -- one source of the
            # cli-side PRIMARY ref, not two independently-written literals.
            _run_planning_artifact_commit(
                repo_root=repo_root,
                mission_id=effective_mission_id,
                mission_slug=mission_slug,
                mid8=effective_mid8,
                destination_ref=_commit_target_ref_for(planning_branch),
                files=primary_files,
                commit_msg=commit_msg,
            )
        if coord_files:
            _run_planning_artifact_commit(
                repo_root=repo_root,
                mission_id=effective_mission_id,
                mission_slug=mission_slug,
                mid8=effective_mid8,
                destination_ref=str(coord_branch),
                files=coord_files,
                commit_msg=commit_msg,
            )

    if is_legacy:
        console.print(f"[green]✓[/green] Planning artifacts committed to {planning_branch}")
    else:
        console.print(f"[green]✓[/green] Planning artifacts committed to coordination branch {coord_branch}")


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
        now_iso = now_utc_iso()
        set_vcs_lock(feature_dir, vcs_type="git", locked_at=now_iso)
        console.print("[cyan]→ VCS locked to git in meta.json[/cyan]")

    return VCSBackend.GIT


def _recover_resolve_context(mission: str | None, json_output: bool) -> tuple[Path, str]:
    """Resolve ``(repo_root, mission_slug)`` for recovery.

    On failure, emits the JSON error payload (when requested) and exits 1 --
    matching the pre-extraction behavior byte-for-byte (T011 branch 1)."""
    try:
        repo_root = find_repo_root()
        _mission_number, mission_slug = detect_feature_context(mission, repo_root=repo_root)
    except (TaskCliError, typer.Exit) as exc:
        if json_output:
            print(json.dumps({"status": "error", "error": str(exc)}))
        raise typer.Exit(1) from None
    return repo_root, mission_slug


def _recover_emit_no_action_result(json_output: bool) -> None:
    """Report that the scan found nothing to recover (T011 branch 2)."""
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


def _recover_print_scan_table(needs_recovery: list[RecoveryState]) -> None:
    """Console-only rendering of the pre-recovery scan results table."""
    from rich.table import Table

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


def _recover_emit_report(report: RecoveryReport, json_output: bool) -> None:
    """Emit the final recovery report -- json payload (no
    ``contexts_recreated``) vs the console summary (which includes it),
    plus the console-only errors block (T011 branches 3+4)."""
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
        return
    console.print("[bold green]Recovery complete[/bold green]")
    console.print(f"  WPs recovered: {', '.join(report.recovered_wps) or 'none'}")
    console.print(f"  Worktrees recreated: {report.worktrees_recreated}")
    console.print(f"  Contexts recreated: {report.contexts_recreated}")
    console.print(f"  Status transitions emitted: {report.transitions_emitted}")
    if report.errors:
        console.print("  [red]Errors:[/red]")
        for err in report.errors:
            console.print(f"    - {err}")


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
    from specify_cli.lanes.recovery import run_recovery, scan_recovery_state

    repo_root, mission_slug = _recover_resolve_context(mission, json_output)

    # First, show what we found
    states = scan_recovery_state(repo_root, mission_slug)
    needs_recovery = [s for s in states if s.recovery_action != "no_action"]

    if not needs_recovery:
        _recover_emit_no_action_result(json_output)
        return

    if not json_output:
        _recover_print_scan_table(needs_recovery)

    # Run recovery
    report = run_recovery(repo_root, mission_slug)
    _recover_emit_report(report, json_output)


# ---------------------------------------------------------------------------
# T017: implement() decomposition helpers -- each owns one leaf decision or
# side effect so the Typer-shell function itself stays a thin orchestration
# sequence (S3776 <=15). None of these change externally-observed behavior;
# see the WP03 tracer for the extraction rationale.
# ---------------------------------------------------------------------------


def _detect_wp_context(mission: str, wp_id: str, repo_root: Path, auto_commit: bool | None) -> tuple[bool | None, str, Path, Path, Any]:
    """Resolve ``(auto_commit, mission_slug, feature_dir, wp_file,
    declared_deps)`` for the ``detect`` step. Exceptions propagate to the
    caller's tracker-aware ``except`` clause unchanged."""
    from specify_cli.core.agent_config import get_auto_commit_default
    from specify_cli.core.dependency_graph import parse_wp_dependencies

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
    feature_dir = placement_seam(repo_root, mission_slug).read_dir(MissionArtifactKind.SPEC)
    wp_file = find_wp_file(repo_root, mission_slug, wp_id)
    declared_deps = parse_wp_dependencies(wp_file)
    return auto_commit, mission_slug, feature_dir, wp_file, declared_deps


def _raise_if_status_commit_protected(repo_root: Path, planning_branch: str, auto_commit: bool | None) -> None:
    """Raise ``ValueError`` when auto-commit is on and the pre-lane status
    commit would target a protected branch."""
    if not auto_commit:
        return
    status_destination = _status_commit_destination_branch(repo_root, fallback_branch=planning_branch)
    protected_error = _protected_branch_status_commit_error(status_destination, repo_root)
    if protected_error is not None:
        raise ValueError(protected_error)


def _execution_mode_for_workspace(resolved_workspace: Any) -> str:
    """``"direct_repo"`` for a repository-root planning workspace, else
    ``"worktree"``."""
    return "direct_repo" if resolved_workspace.resolution_kind == "repo_root" else "worktree"


def _ensure_wp_claim_preconditions(status_feature_dir: Path, wp_id: str, declared_deps: Any) -> None:
    """Raise if *wp_id* is unseeded (T012 / Contract 3) or a declared
    dependency is not yet ``approved``/``done``."""
    from specify_cli.core.dependency_graph import dependency_readiness_for_wp
    from specify_cli.status import reduce as _reduce_events
    from specify_cli.status import read_events as _read_events

    wp_lanes = {_wp_id: _state.get("lane", Lane.GENESIS) for _wp_id, _state in _reduce_events(_read_events(status_feature_dir)).work_packages.items()}
    # T012 / Contract 3: reject unseeded WPs BEFORE any workspace
    # allocation. A genesis WP has not been through finalize-tasks; the
    # user must run it first to seed the genesis→planned bootstrap event.
    current_wp_lane = wp_lanes.get(wp_id, Lane.GENESIS)
    if current_wp_lane == Lane.GENESIS:
        # FR-009: same rejection (and exception type) as the lifecycle layer,
        # so programmatic callers catching WorkPackageStartRejected see this
        # path too (review M5).
        raise WorkPackageStartRejected(f"WP {wp_id} is not finalized; run `spec-kitty agent mission finalize-tasks`")
    dependency_readiness = dependency_readiness_for_wp(wp_id, declared_deps, wp_lanes)
    if not dependency_readiness.satisfied:
        blocked = ", ".join(dependency_readiness.unsatisfied)
        raise ValueError(f"dependencies_not_satisfied: {wp_id} depends on {blocked}; all dependencies must be approved or done before implementation can start")


def _run_bulk_edit_gate_and_inference(feature_dir: Path, wp_file: Path, mission_slug: str, wp_id: str, acknowledge_not_bulk_edit: bool) -> None:
    """Bulk-edit occurrence-classification gate (FR-006) + inference warning
    (FR-009). Raises ``typer.Exit(1)`` on a gate failure or an un-acknowledged
    triggered inference; a silent return means the claim may proceed."""
    from specify_cli.bulk_edit.gate import ensure_occurrence_classification_ready, render_gate_failure

    gate_result = ensure_occurrence_classification_ready(feature_dir)
    if not gate_result.passed:
        render_gate_failure(gate_result, console)
        raise typer.Exit(1)

    if gate_result.change_mode is not None:
        return

    from specify_cli.bulk_edit.inference import (
        scan_spec_file,
        wp_authors_bulk_edit_planning_artifact,
    )

    inference = scan_spec_file(feature_dir)
    planning_wp = wp_authors_bulk_edit_planning_artifact(wp_file, mission_slug)
    if inference.triggered and planning_wp:
        matched = ", ".join(f"'{p}' ({w}pt)" for p, w in inference.matched_phrases)
        console.print(
            Panel(
                f"This mission's spec contains language suggesting a bulk edit "
                f"(score: {inference.score}/{inference.threshold}), but {wp_id} owns "
                f"the occurrence-map planning artifact.\n"
                f"  Matched: {matched}\n\n"
                f"Continuing without --acknowledge-not-bulk-edit for this planning WP.",
                title="[bold yellow]Bulk Edit Inference Informational[/]",
                border_style="yellow",
            )
        )
        return
    if inference.triggered and not acknowledge_not_bulk_edit:
        matched = ", ".join(f"'{p}' ({w}pt)" for p, w in inference.matched_phrases)
        console.print(
            Panel(
                f"This mission's spec contains language suggesting a bulk edit "
                f"(score: {inference.score}/{inference.threshold}):\n"
                f"  Matched: {matched}\n\n"
                f"If this IS a bulk edit, set change_mode to 'bulk_edit' in meta.json.\n"
                f"If it is NOT, re-run with --acknowledge-not-bulk-edit to suppress.",
                title="[bold yellow]Bulk Edit Inference Warning[/]",
                border_style="yellow",
            )
        )
        raise typer.Exit(1)


def _resolve_execution_lane(resolved_workspace: Any, lanes_feature_dir: Path, wp_id: str, tracker: StepTracker) -> tuple[Any, Any]:
    """Resolve ``(lanes_manifest, lane)`` for a lane workspace, or ``(None,
    None)`` for a repository-root planning workspace. Completes the
    ``validate`` tracker step either way."""
    from specify_cli.lanes.compute import is_planning_lane

    if is_planning_lane(resolved_workspace):
        tracker.complete("validate", "Execution: repository root planning workspace")
        return None, None
    lanes_manifest = require_lanes_json(lanes_feature_dir)
    lane = lanes_manifest.lane_for_wp(wp_id)
    if lane is None:
        raise ValueError(f"{wp_id} is not assigned to any lane in lanes.json")
    tracker.complete("validate", f"Lane: {lane.lane_id}")
    return lanes_manifest, lane


def _resolve_active_lanes_manifest(repo_root: Path, base: str | None, resolved_workspace: Any, lanes_manifest: Any) -> Any:
    """Apply ``--base`` (#1684): validate the ref and patch the manifest's
    ``mission_branch`` so the allocator branches from the explicit base
    instead of auto-detecting. ``--base`` selects only the ROOT the lane
    branches from; the allocator still merges approved ``depends_on_lanes``
    tips on top, so cross-lane code propagation is preserved regardless of
    the chosen root. Returns *lanes_manifest* unchanged when ``--base`` does
    not apply."""
    from specify_cli.lanes.compute import is_planning_lane

    if base is None:
        return lanes_manifest
    if is_planning_lane(resolved_workspace):
        console.print("[yellow]Warning:[/yellow] --base is ignored for repository-root planning work")
        return lanes_manifest
    _validate_base_ref(repo_root, base)
    # Shallow-patch the manifest's mission_branch so
    # allocate_lane_worktree branches from the explicit ref.
    from dataclasses import replace as _dc_replace

    console.print(f"[cyan]→ Using explicit base ref: {base}[/cyan]")
    return _dc_replace(lanes_manifest, mission_branch=base)


def _emit_blocked_on_alloc_failure(
    feature_dir: Path,
    mission_slug: str,
    wp_id: str,
    effective_actor: str,
    status_execution_mode: str,
    repo_root: Path,
    exc: Exception,
) -> None:
    """Best-effort BLOCKED transition after a workspace-allocation failure;
    a no-op when the WP's current lane cannot validly transition to
    BLOCKED."""
    current_lane = _get_wp_lane_from_event_log(feature_dir, wp_id)
    if current_lane not in {Lane.PLANNED, Lane.CLAIMED, Lane.IN_PROGRESS}:
        return
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
    except Exception as _blocked_exc:  # noqa: BLE001 -- best-effort, never mask the real alloc failure
        console.print(f"[yellow]Warning:[/yellow] Could not emit blocked transition after alloc failure: {_blocked_exc}")


def _commit_wp_claim_status(
    *,
    repo_root: Path,
    feature_dir: Path,
    mission_slug: str,
    wp_id: str,
    wp_file: Path,
    auto_commit: bool | None,
    placement_ref: CommitTarget | None,
    status_result: Any,
) -> None:
    """Auto-commit (or staged-only) side effect for a WP's claimed->'doing'
    transition. A no-op when *status_result* shows no lane change occurred.

    Split out of ``implement()`` so the outer try/except there keeps its
    exact ``SafeCommitPathPolicyError`` / ``PlacementResolutionRequired`` /
    soft-warning shape (D11 -- see
    ``test_implement_placement_routing.py::test_structured_error_is_not_swallowed_as_soft_warning``,
    which asserts on ``implement()``'s own source).
    """
    if status_result is None or not status_result.status_changed:
        return
    if not auto_commit:
        console.print(f"[cyan]→ {wp_id} moved to 'doing' (auto-commit disabled, changes staged only)[/cyan]")
        return

    from specify_cli.cli.commands.agent.tasks import _collect_status_artifacts

    commit_msg = f"chore: {wp_id} claimed for implementation"
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
    # canonical ``MissionArtifactKind.STATUS_STATE`` check (WP13 retired the
    # former ``COORD_OWNED_STATUS_FILES`` frozenset onto this single-source
    # kind classifier) drops those files on coord topology only; on a
    # flat/legacy mission they ARE canonical on PRIMARY and stay in the bundle.
    if routes_through_coordination(resolve_topology(repo_root, mission_slug)):
        status_paths = [
            path.resolve()
            for path in _collect_status_artifacts(feature_dir)
            if not is_status_state_path(path)
        ]
    else:
        status_paths = [path.resolve() for path in _collect_status_artifacts(feature_dir)]
    files_to_commit = [wp_file.resolve(), *status_paths]
    if meta_file.exists():
        files_to_commit.append(meta_file.resolve())
    if config_file.exists():
        files_to_commit.append(config_file.resolve())

    # WP03 / T011 / T012 / D11: the status claim commit routes through
    # the SAME seam-resolved ``placement_ref`` planning artifacts
    # resolve to (C-PLACE-1) instead of the forbidden
    # ``_get_current_branch(repo_root) or planning_branch``
    # checkout-derived grammar. A resolution failure now FAILS CLOSED
    # (see ``_resolve_claim_commit_target``) rather than silently
    # committing to whatever branch is checked out.
    claim_commit_target = _resolve_claim_commit_target(placement_ref)
    try:
        safe_commit(
            repo_root=repo_root,
            worktree_root=repo_root,
            target=claim_commit_target,
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
        console.print(f"[yellow]Warning:[/yellow] Could not auto-commit lane change: {_commit_exc}")


def _build_implement_json_payload(
    repo_root: Path,
    mission_slug: str,
    wp_id: str,
    workspace_path: Path,
    branch_name: str | None,
    result: Any,
    resolved_workspace: Any,
) -> dict[str, Any]:
    """Assemble the ``--json`` success payload (FR-004/FR-005 #2186 identity
    anchor + FR-006 lane-test-env passthrough)."""
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

    identity_dir = primary_feature_dir_for_mission(repo_root, _canonicalize_primary_read_handle(repo_root, mission_slug))
    identity = resolve_mission_identity(identity_dir)
    return {
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
        "lane_test_env": (result.lane_test_env if isinstance(getattr(result, "lane_test_env", None), dict) else {}),
    }


def _claim_policy_metadata(shell_pid: int, agent: str) -> dict[str, Any]:
    """Best-effort ``policy_metadata`` triple for the claim transition (WP07/T026).

    Mirrors ``cli.commands.agent.workflow_executor._claim_policy_metadata``
    (duplicated rather than imported to avoid a lower-layer -> agent-package
    dependency): routes ``(shell_pid, shell_pid_created_at, agent)`` onto the
    ``planned -> claimed`` transition's ``policy_metadata`` sidecar (FR-004)
    using WP01's exact reducer-fold key names, omitting
    ``shell_pid_created_at`` (never fabricating a value) when
    :func:`~specify_cli.core.process_liveness.capture_creation_time_baseline`
    cannot capture a baseline (C-007 best-effort, D3a legacy-claim semantics).
    """
    from specify_cli.core.process_liveness import capture_creation_time_baseline
    from specify_cli.status import build_claim_policy_metadata

    baseline = capture_creation_time_baseline(shell_pid)
    if baseline is None:
        return {"shell_pid": shell_pid, "agent": agent}
    return build_claim_policy_metadata(shell_pid=shell_pid, shell_pid_created_at=baseline, agent=agent)


def _start_wp_implementation_status(
    *,
    feature_dir: Path,
    mission_slug: str,
    wp_id: str,
    effective_actor: str,
    workspace_path: Path,
    status_execution_mode: str,
    repo_root: Path,
) -> Any:
    """Call ``start_implementation_status``, translating claim-conflict /
    transition failures into a printed error + ``typer.Exit(1)``."""
    import os as _os

    try:
        return start_implementation_status(
            feature_dir=feature_dir,
            mission_slug=mission_slug,
            wp_id=wp_id,
            actor=effective_actor,
            workspace_context=f"{status_execution_mode}:{workspace_path}",
            execution_mode=status_execution_mode,
            repo_root=repo_root,
            # WP07/T026 (FR-004/FR-014): the claim triple rides the
            # planned -> claimed transition's policy_metadata sidecar; the
            # frontmatter pre-write mirror was removed in the #2816 cutover.
            policy_metadata=_claim_policy_metadata(_os.getppid(), effective_actor),
        )
    except WorkPackageClaimConflict as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1) from exc
    except TransitionError as exc:
        console.print(f"[red]Error:[/red] Could not start implementation status: {exc}")
        raise typer.Exit(1) from exc


def _report_workspace_created(tracker: StepTracker, result: Any, workspace_path: Path, repo_root: Path) -> None:
    """Complete the ``create`` tracker step and print the workspace/branch
    summary lines shared by the repo-root and lane-worktree cases."""
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


def _print_workspace_ready_banner(result: Any, workspace_path: Path) -> None:
    """Human-readable "workspace ready" banner (repo-root planning vs lane
    worktree), plus the FR-006 lane-test-env export block."""
    if result.lane_id is None:
        console.print("\n[bold green]✓ Repository-root workspace ready[/bold green]")
        console.print()
        console.print(_BANNER_OPEN + "=" * 72 + _BANNER_CLOSE)
        console.print(_BANNER_OPEN + "Planning-artifact work for this WP happens in the repository root" + _BANNER_CLOSE)
        console.print(_BANNER_OPEN + "=" * 72 + _BANNER_CLOSE)
        console.print()
        console.print(f"  [bold]cd {workspace_path}[/bold]")
        console.print()
        console.print("[dim]This WP does not get a lane worktree or workspace context file.[/dim]")
        console.print("[dim]Make planning-artifact changes directly in the repository root.[/dim]")
        return

    console.print("\n[bold green]✓ Lane worktree ready[/bold green]")
    console.print()
    console.print(_BANNER_OPEN + "=" * 72 + _BANNER_CLOSE)
    console.print(_BANNER_OPEN + "CRITICAL: Change to the lane worktree before editing files" + _BANNER_CLOSE)
    console.print(_BANNER_OPEN + "=" * 72 + _BANNER_CLOSE)
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
        console.print("[dim]Two parallel SaaS / Django lanes will collide on a single shared test DB unless these are exported in the lane's test process.[/dim]")


@_json_safe_output
@require_main_repo
def implement(
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
        auto_commit, mission_slug, feature_dir, wp_file, declared_deps = _detect_wp_context(mission, wp_id, repo_root, auto_commit)
        tracker.complete("detect", f"Feature: {mission_slug}")
    except (TaskCliError, FileNotFoundError, FrontmatterError, ValidationError, typer.Exit) as exc:
        tracker.error("detect", str(exc))
        console.print(tracker.render())
        raise typer.Exit(1) from exc

    tracker.start("validate")
    try:
        planning_branch = resolve_feature_target_branch(mission_slug, repo_root)
        _raise_if_status_commit_protected(repo_root, planning_branch, auto_commit)

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

        # T012 / Contract 3 + dependency gate: reject unseeded WPs and
        # not-yet-ready dependencies BEFORE any workspace allocation.
        _ensure_wp_claim_preconditions(_status_feature_dir, wp_id, declared_deps)

        # WP06 / T019 / C-PLACE-1: resolve the single artifact-placement ref from
        # the canonical context so implement-claim never reconciles a
        # primary↔coord planning-artifact split (#1816). The placement ref is the
        # SAME CommitTarget status events resolve to. Resolution is best-effort:
        # on a context-resolution error we pass ``None`` and the helper keeps the
        # legacy meta-derived path (C-004 strangler — never break the lifecycle).
        _placement_ref = _resolve_placement_ref(repo_root, mission_slug=mission_slug, wp_id=wp_id)

        _ensure_planning_artifacts_committed_git(
            repo_root=repo_root,
            feature_dir=feature_dir,
            mission_slug=mission_slug,
            wp_id=wp_id,
            planning_branch=planning_branch,
            auto_commit=bool(auto_commit),
            placement_ref=_placement_ref,
        )

        # Bulk edit occurrence classification gate (FR-006) + inference
        # warning for potentially unmarked bulk edits (FR-009).
        _run_bulk_edit_gate_and_inference(feature_dir, wp_file, mission_slug, wp_id, acknowledge_not_bulk_edit)

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

        lanes_manifest, _lane = _resolve_execution_lane(resolved_workspace, _lanes_feature_dir, wp_id, tracker)
    except Exception as exc:
        # Catches (among others) CorruptLanesError, MissingLanesError,
        # WorkPackageStartRejected, ValueError, typer.Exit -- every failure
        # in this block maps to the same "report + exit 1" outcome, so one
        # generic handler (Exception is a strict superset) replaces the
        # former specific-tuple + generic-fallback pair without changing
        # behavior for any of them.
        tracker.error("validate", str(exc))
        console.print(tracker.render())
        raise typer.Exit(1) from exc

    tracker.start("create")
    effective_actor = actor or "implement-command"
    status_result = None
    status_execution_mode = _execution_mode_for_workspace(resolved_workspace)
    try:
        # WP04/T015 (FR-004/NFR-003/SC-004): the pre-write claim triple rides
        # the planned -> claimed transition's policy_metadata sidecar (see
        # _start_wp_implementation_status below). The former frontmatter
        # dual-write mirror was removed in the #2816 unconditional cutover, so
        # `spec-kitty implement` writes 0 runtime bytes to the WP file.
        vcs_backend = _ensure_vcs_in_meta(feature_dir, repo_root)

        # When --base is provided, validate the ref and build a patched
        # LanesManifest that uses it as the mission_branch so the worktree
        # allocator branches from the explicit base instead of auto-detecting.
        active_lanes_manifest = _resolve_active_lanes_manifest(repo_root, base, resolved_workspace, lanes_manifest)

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

        status_result = _start_wp_implementation_status(
            feature_dir=feature_dir,
            mission_slug=mission_slug,
            wp_id=wp_id,
            effective_actor=effective_actor,
            workspace_path=workspace_path,
            status_execution_mode=status_execution_mode,
            repo_root=repo_root,
        )

        _report_workspace_created(tracker, result, workspace_path, repo_root)
    except typer.Exit:
        console.print(tracker.render())
        raise
    except Exception as exc:
        tracker.error("create", f"workspace allocation failed: {exc}")
        console.print(tracker.render())
        console.print(f"\n[red]Error:[/red] Workspace allocation failed: {exc}")
        _emit_blocked_on_alloc_failure(feature_dir, mission_slug, wp_id, effective_actor, status_execution_mode, repo_root, exc)
        raise typer.Exit(1) from exc

    try:
        _commit_wp_claim_status(
            repo_root=repo_root,
            feature_dir=feature_dir,
            mission_slug=mission_slug,
            wp_id=wp_id,
            wp_file=wp_file,
            auto_commit=auto_commit,
            placement_ref=_placement_ref,
            status_result=status_result,
        )
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
        print(json.dumps(_build_implement_json_payload(repo_root, mission_slug, wp_id, workspace_path, branch_name, result, resolved_workspace)))
        return

    _print_workspace_ready_banner(result, workspace_path)


__all__ = ["_ensure_vcs_in_meta", "detect_feature_context", "find_wp_file", "implement"]
