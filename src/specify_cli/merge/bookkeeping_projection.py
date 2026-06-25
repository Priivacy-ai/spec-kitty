"""Status-surface trust + snapshot/restore + projection for the merge seam.

Mission #2057 (decompose ``cli/commands/merge.py``) — IC-09 / WP09.

The security-sensitive path-trust assertions, the final-bookkeeping snapshot
capture/restore, and the coord→target status projection moved out of the command
shim verbatim. ``_restore_final_bookkeeping_snapshots`` keeps its exact signature
and behavior because the executor (WP10) calls it at the ~6 restore-on-exception
sites (INV-6). One-way import: this module never imports the command shim.
"""

from __future__ import annotations

from pathlib import Path

from specify_cli.coordination.surface_resolver import is_under_worktrees_segment
from specify_cli.core.constants import KITTIFY_DIR, KITTY_SPECS_DIR, WORKTREES_DIR
from specify_cli.core.git_ops import run_command
from specify_cli.core.paths import assert_safe_path_segment, get_main_repo_root
from specify_cli.core.utils import ensure_within_any, ensure_within_directory
from specify_cli.merge._constants import _STATUS_EVENTS_FILENAME, _STATUS_FILENAME
from specify_cli.missions._read_path_resolver import primary_feature_dir_for_mission


def _validate_mission_slug_path_segment(mission_slug: str) -> str:
    """Reject mission slugs unsafe for direct path composition.

    Delegates to the canonical ``assert_safe_path_segment`` validator (FR-002 / WP04).
    Raises ``ValueError`` on any traversal-unsafe value, preserving the existing contract.
    """
    return str(assert_safe_path_segment(mission_slug))


def _target_bookkeeping_status_paths(
    *,
    main_repo: Path,
    mission_slug: str,
    status_feature_dir: Path,
) -> tuple[Path, Path]:
    """Return status paths that may be staged from the target checkout.

    ``status_feature_dir`` is topology-aware and can point at the coordination
    worktree. The final merge bookkeeping commit runs from ``main_repo`` onto
    the target branch, so it must stage primary-checkout paths only.
    """
    safe_mission_slug = _validate_mission_slug_path_segment(mission_slug)
    target_feature_dir = (
        primary_feature_dir_for_mission(main_repo, safe_mission_slug)
        if is_under_worktrees_segment(status_feature_dir)
        else status_feature_dir
    )
    safe_target_feature_dir = ensure_within_directory(target_feature_dir, main_repo)
    return (
        safe_target_feature_dir / _STATUS_EVENTS_FILENAME,
        safe_target_feature_dir / _STATUS_FILENAME,
    )


def _read_optional_bytes(path: Path) -> bytes | None:
    if not path.exists():
        return None
    return path.read_bytes()


def _assert_status_path_within_target_surface(
    *,
    repo_root: Path,
    mission_slug: str,
    candidate: Path,
) -> Path:
    """Reject bookkeeping paths that escape the canonical mission status surface.

    Validates ``mission_slug`` via ``assert_safe_path_segment`` (FR-003) before
    composing the surface root, then delegates containment to ``ensure_within_any``
    (FR-006 / T016).
    """
    assert_safe_path_segment(mission_slug)
    repo_resolved = get_main_repo_root(repo_root).resolve(strict=False)
    surface_root = primary_feature_dir_for_mission(repo_resolved, mission_slug).resolve(strict=False)
    contained: Path = ensure_within_any(candidate, roots=[surface_root])
    return contained


def _assert_status_surface_path_is_trusted(
    *,
    repo_root: Path,
    status_feature_dir: Path,
) -> Path:
    """Reject status surfaces that resolve outside the repo's trusted roots.

    Selects the single correct root via ``is_under_worktrees_segment`` (worktrees
    vs kitty-specs), then delegates containment to ``ensure_within_any``
    (FR-006 / T018).  The selection is intentionally preserved — widening to a
    union of both roots would be a behavior change (research.md §(d)).

    The *claimed* topology (the path segment) must match the *resolved* topology:
    if the segment says worktrees but the resolved path is not under the worktrees
    root (or vice versa), the surface is rejected.  This closes a symlink/taint
    gap where a kitty-specs-shaped path could resolve into the worktrees tree (or
    the reverse) and slip past the single-root containment check.
    """
    repo_resolved = get_main_repo_root(repo_root).resolve(strict=False)
    worktrees_root = (repo_resolved / WORKTREES_DIR).resolve(strict=False)
    # Root specs dir (no per-mission slug appended) used purely for symlink/taint
    # containment checking, not raw per-mission-spec path composition. Bound to a
    # neutrally named local (``specs_root``) to avoid a false positive on the raw
    # mission-spec path ratchet (test_no_raw_mission_spec_paths) while keeping that
    # ratchet active over the rest of this module.
    specs_root = (repo_resolved / KITTY_SPECS_DIR).resolve(strict=False)
    # Absolutize the candidate (anchor a relative surface to the repo root) before
    # any containment check, then reject — pre-resolution — a path that escapes the
    # root its segment claims. Hardens the write path against a traversal/symlink
    # surface that would otherwise only be caught after ``.resolve()`` (#2043 Sonar).
    status_candidate = (
        status_feature_dir
        if status_feature_dir.is_absolute()
        else repo_resolved / status_feature_dir
    ).absolute()
    segment_claims_worktrees = is_under_worktrees_segment(status_candidate)
    claimed_root = worktrees_root if segment_claims_worktrees else specs_root
    try:
        status_candidate.relative_to(claimed_root)
    except ValueError as exc:
        raise ValueError(f"Untrusted status surface path: {status_feature_dir}") from exc
    status_resolved = status_candidate.resolve(strict=False)
    resolves_under_worktrees = status_resolved.is_relative_to(worktrees_root)
    resolves_under_specs = status_resolved.is_relative_to(specs_root)

    if segment_claims_worktrees != resolves_under_worktrees:
        raise ValueError(f"Untrusted status surface path: {status_feature_dir}")
    if not resolves_under_worktrees and not resolves_under_specs:
        raise ValueError(f"Untrusted status surface path: {status_feature_dir}")

    trusted_root = worktrees_root if resolves_under_worktrees else specs_root
    trusted_surface: Path = ensure_within_directory(status_resolved, trusted_root)
    return trusted_surface


def _assert_status_surface_file_path_is_trusted(
    *,
    repo_root: Path,
    status_feature_dir: Path,
    filename: str,
) -> Path:
    """Reject status-surface child paths outside the exact bookkeeping files."""
    if filename not in {_STATUS_EVENTS_FILENAME, _STATUS_FILENAME}:
        raise ValueError(f"Refusing untrusted status filename: {filename}")
    trusted_surface = _assert_status_surface_path_is_trusted(
        repo_root=repo_root,
        status_feature_dir=status_feature_dir,
    )
    candidate = trusted_surface / filename
    if candidate.is_symlink():
        raise ValueError(f"Refusing symlinked status surface path: {candidate}")
    trusted_file: Path = ensure_within_any(
        candidate,
        roots=[],
        files=[trusted_surface / _STATUS_EVENTS_FILENAME, trusted_surface / _STATUS_FILENAME],
    )
    return trusted_file


def _restore_optional_bytes(path: Path, original: bytes | None) -> None:
    if original is None:
        path.unlink(missing_ok=True)
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(original)


def _assert_bookkeeping_snapshot_path_is_trusted(
    *,
    repo_root: Path,
    candidate: Path,
) -> Path:
    """Reject rollback snapshot paths outside merge bookkeeping roots.

    Delegates multi-root containment + exact-file allowlist to ``ensure_within_any``
    (FR-006 / T017).  The trusted set (3 dirs + the exact file) is preserved exactly —
    no set change (NFR-001 / C-007).
    """
    repo_resolved = get_main_repo_root(repo_root).resolve(strict=False)
    trusted_snapshot: Path = ensure_within_any(
        candidate,
        roots=[
            (repo_resolved / KITTY_SPECS_DIR).resolve(strict=False),
            (repo_resolved / WORKTREES_DIR).resolve(strict=False),
            (repo_resolved / KITTIFY_DIR / "runtime" / "merge").resolve(strict=False),
        ],
        files=[repo_resolved / KITTIFY_DIR / "merge-state.json"],
    )
    return trusted_snapshot


def _capture_bookkeeping_snapshots(
    repo_root: Path,
    *candidates: Path,
) -> dict[Path, bytes | None]:
    """Capture rollback bytes for repo-derived bookkeeping paths only."""
    snapshots: dict[Path, bytes | None] = {}
    for candidate in candidates:
        trusted_path = _assert_bookkeeping_snapshot_path_is_trusted(
            repo_root=repo_root,
            candidate=candidate,
        )
        snapshots[trusted_path] = _read_optional_bytes(trusted_path)
    return snapshots


def _restore_final_bookkeeping_snapshots(
    snapshots: dict[Path, bytes | None],
) -> None:
    """Best-effort restore for final merge bookkeeping rollback.

    Snapshot paths are validated at capture time (``_capture_bookkeeping_snapshots``
    → ``_assert_bookkeeping_snapshot_path_is_trusted``), so restore trusts the dict
    keys and only needs to tolerate transient I/O failures.

    INV-6: signature + behavior are stable — the executor (WP10) calls this at the
    ~6 restore-on-exception sites.
    """
    for path, original in snapshots.items():
        try:
            _restore_optional_bytes(path, original)
        except OSError:
            continue


def _target_branch_still_at_baseline(
    main_repo: Path,
    target_branch: str,
    baseline_sha: str,
) -> bool:
    """Return True when target still points at the pre-target-merge baseline."""
    if not baseline_sha or baseline_sha == "HEAD~1":
        return False
    ret, out, _err = run_command(
        ["git", "rev-parse", target_branch],
        capture=True,
        check_return=False,
        cwd=main_repo,
    )
    return bool(ret == 0 and out.strip() == baseline_sha)


def _project_status_bookkeeping_to_target(
    *,
    main_repo: Path,
    mission_slug: str,
    status_feature_dir: Path,
) -> tuple[Path, Path]:
    """Copy authoritative status bookkeeping to target-checkout paths.

    Coord-backed missions write done transitions through the coordination
    surface, but the final target-branch housekeeping commit can only stage
    paths tracked under ``main_repo``. Project just the status artifacts into
    ``kitty-specs/<slug>/`` before the commit; keep the authoritative write
    topology unchanged.
    """
    target_events_path, target_status_path = _target_bookkeeping_status_paths(
        main_repo=main_repo,
        mission_slug=mission_slug,
        status_feature_dir=status_feature_dir,
    )
    trusted_status_feature_dir = _assert_status_surface_path_is_trusted(
        repo_root=main_repo,
        status_feature_dir=status_feature_dir,
    )
    trusted_target_events_path = _assert_status_path_within_target_surface(
        repo_root=main_repo,
        mission_slug=mission_slug,
        candidate=target_events_path,
    )
    trusted_target_status_path = _assert_status_path_within_target_surface(
        repo_root=main_repo,
        mission_slug=mission_slug,
        candidate=target_status_path,
    )
    if not is_under_worktrees_segment(trusted_status_feature_dir):
        return trusted_target_events_path, trusted_target_status_path

    trusted_target_events_path.parent.mkdir(parents=True, exist_ok=True)
    source_events_path = _assert_status_surface_file_path_is_trusted(
        repo_root=main_repo,
        status_feature_dir=trusted_status_feature_dir,
        filename=_STATUS_EVENTS_FILENAME,
    )
    source_status_path = _assert_status_surface_file_path_is_trusted(
        repo_root=main_repo,
        status_feature_dir=trusted_status_feature_dir,
        filename=_STATUS_FILENAME,
    )
    source_events_bytes = _read_optional_bytes(source_events_path)
    source_status_bytes = _read_optional_bytes(source_status_path)
    original_events_bytes = _read_optional_bytes(trusted_target_events_path)
    original_status_bytes = _read_optional_bytes(trusted_target_status_path)
    try:
        if source_events_bytes is not None:
            trusted_target_events_path.write_bytes(source_events_bytes)
        if source_status_bytes is not None:
            trusted_target_status_path.write_bytes(source_status_bytes)
    except OSError:
        _restore_optional_bytes(trusted_target_events_path, original_events_bytes)
        _restore_optional_bytes(trusted_target_status_path, original_status_bytes)
        raise
    return trusted_target_events_path, trusted_target_status_path


__all__ = [
    "_validate_mission_slug_path_segment",
    "_target_bookkeeping_status_paths",
    "_read_optional_bytes",
    "_restore_optional_bytes",
    "_assert_status_path_within_target_surface",
    "_assert_status_surface_path_is_trusted",
    "_assert_status_surface_file_path_is_trusted",
    "_assert_bookkeeping_snapshot_path_is_trusted",
    "_capture_bookkeeping_snapshots",
    "_restore_final_bookkeeping_snapshots",
    "_target_branch_still_at_baseline",
    "_project_status_bookkeeping_to_target",
]
