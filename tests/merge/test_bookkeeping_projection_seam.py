"""Seam test for ``specify_cli.merge.bookkeeping_projection`` (mission #2057, WP09).

Covers the security-sensitive path-trust assertions (trusted AND rejected
branches) and the surviving coord→target projection helpers. The
final-bookkeeping snapshot/restore compensator that used to live in this module
was RETIRED by the lifecycle-gate-execution-context mission (WP09 / T048 / TAO-3):
the merge executor now enrols its bytes with the SINGLE owner compensator in
``coordination.atomic_write``, so the compensator round-trip / trust tests below
re-point onto that owner surface (same byte-identical semantics). The
re-export-identity and one-way-import guards live in the consolidated
``tests/merge/test_merge_compat_surface.py``.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from specify_cli.coordination import atomic_write as aw
from specify_cli.core.constants import KITTY_SPECS_DIR
from specify_cli.merge import bookkeeping_projection as bp

pytestmark = pytest.mark.fast


def test_restore_generated_artifact_snapshots_signature_stable() -> None:
    """TAO-3: the ONE owner compensator restores from a single dict positional arg."""
    import inspect

    sig = inspect.signature(aw.restore_generated_artifact_snapshots)
    params = list(sig.parameters)
    assert params[0] == "snapshots"


# --- _validate_mission_slug_path_segment ------------------------------------


def test_validate_mission_slug_accepts_safe_segment() -> None:
    assert bp._validate_mission_slug_path_segment("my-mission-01ABC") == "my-mission-01ABC"


def test_validate_mission_slug_rejects_traversal() -> None:
    with pytest.raises(ValueError):
        bp._validate_mission_slug_path_segment("../escape")


# --- snapshot capture / restore round-trip ----------------------------------


def _repo_with_spec(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    (repo / KITTY_SPECS_DIR / "m").mkdir(parents=True)
    return repo


def test_capture_and_restore_round_trip(tmp_path: Path) -> None:
    repo = _repo_with_spec(tmp_path)
    events = repo / KITTY_SPECS_DIR / "m" / "status.events.jsonl"
    events.write_text("ORIGINAL\n", encoding="utf-8")

    roots = [repo / KITTY_SPECS_DIR]
    snapshots = aw.capture_generated_artifact_snapshots(events, trusted_roots=roots)
    # Mutate, then restore through the single owner compensator.
    events.write_text("MUTATED\n", encoding="utf-8")
    aw.restore_generated_artifact_snapshots(snapshots)
    assert events.read_text(encoding="utf-8") == "ORIGINAL\n"


def test_capture_restore_recreates_deleted_file(tmp_path: Path) -> None:
    repo = _repo_with_spec(tmp_path)
    events = repo / KITTY_SPECS_DIR / "m" / "status.events.jsonl"
    # Absent at capture time -> snapshot is None -> restore must remove it.
    roots = [repo / KITTY_SPECS_DIR]
    snapshots = aw.capture_generated_artifact_snapshots(events, trusted_roots=roots)
    events.write_text("CREATED-AFTER-CAPTURE\n", encoding="utf-8")
    aw.restore_generated_artifact_snapshots(snapshots)
    assert not events.exists()


# --- path-trust: trusted + rejected branches (owner containment) -------------


def test_snapshot_trust_accepts_kitty_specs(tmp_path: Path) -> None:
    repo = _repo_with_spec(tmp_path)
    candidate = repo / KITTY_SPECS_DIR / "m" / "status.json"
    snapshots = aw.capture_generated_artifact_snapshots(
        candidate, trusted_roots=[repo / KITTY_SPECS_DIR]
    )
    assert candidate.resolve(strict=False) in snapshots


def test_snapshot_trust_rejects_outside_path(tmp_path: Path) -> None:
    repo = _repo_with_spec(tmp_path)
    outside = tmp_path / "elsewhere" / "evil.json"
    with pytest.raises(ValueError):
        aw.capture_generated_artifact_snapshots(
            outside, trusted_roots=[repo / KITTY_SPECS_DIR]
        )


def test_status_surface_trust_accepts_kitty_specs(tmp_path: Path) -> None:
    repo = _repo_with_spec(tmp_path)
    surface = repo / KITTY_SPECS_DIR / "m"
    with patch.object(bp, "get_main_repo_root", lambda _r: repo):
        trusted = bp._assert_status_surface_path_is_trusted(repo_root=repo, status_feature_dir=surface)
    assert trusted == surface.resolve()


def test_status_surface_trust_rejects_topology_mismatch(tmp_path: Path) -> None:
    """A worktrees-shaped segment that resolves outside the worktrees root is rejected."""
    repo = _repo_with_spec(tmp_path)
    # A path under kitty-specs but named like a worktrees path is a mismatch.
    bogus = repo / "not-real-root" / "x"
    with (
        patch.object(bp, "get_main_repo_root", lambda _r: repo),
        pytest.raises(ValueError, match="Untrusted status surface path"),
    ):
        bp._assert_status_surface_path_is_trusted(repo_root=repo, status_feature_dir=bogus)


def test_status_surface_file_trust_rejects_bad_filename(tmp_path: Path) -> None:
    repo = _repo_with_spec(tmp_path)
    surface = repo / KITTY_SPECS_DIR / "m"
    with (
        patch.object(bp, "get_main_repo_root", lambda _r: repo),
        pytest.raises(ValueError, match="Refusing untrusted status filename"),
    ):
        bp._assert_status_surface_file_path_is_trusted(
            repo_root=repo, status_feature_dir=surface, filename="evil.txt"
        )


# --- _target_branch_still_at_baseline ---------------------------------------


def test_target_branch_still_at_baseline(tmp_path: Path) -> None:
    assert bp._target_branch_still_at_baseline(tmp_path, "main", "") is False
    assert bp._target_branch_still_at_baseline(tmp_path, "main", "HEAD~1") is False
    with patch.object(bp, "run_command", return_value=(0, "abc123", "")):
        assert bp._target_branch_still_at_baseline(tmp_path, "main", "abc123") is True
        assert bp._target_branch_still_at_baseline(tmp_path, "main", "deadbeef") is False
    with patch.object(bp, "run_command", return_value=(1, "", "err")):
        assert bp._target_branch_still_at_baseline(tmp_path, "main", "abc123") is False


# --- _project_status_bookkeeping_to_target (non-worktree fast path) ----------


def test_project_returns_target_paths_when_not_worktree(tmp_path: Path) -> None:
    repo = _repo_with_spec(tmp_path)
    surface = repo / KITTY_SPECS_DIR / "m"
    with patch.object(bp, "get_main_repo_root", lambda _r: repo):
        events, status = bp._project_status_bookkeeping_to_target(
            main_repo=repo, mission_slug="m", status_feature_dir=surface
        )
    assert events.name == "status.events.jsonl"
    assert status.name == "status.json"
