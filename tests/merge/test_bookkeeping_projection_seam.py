"""Seam test for ``specify_cli.merge.bookkeeping_projection`` (mission #2057, WP09).

Covers the security-sensitive path-trust assertions (trusted AND rejected
branches), the snapshot capture/restore round-trip (byte-identical), and the
``_restore_final_bookkeeping_snapshots`` signature the executor depends on
(INV-6). Proves the shim re-exports the trust/snapshot/projection symbols and
enforces one-way imports (FR-003, FR-006, INV-2).
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from specify_cli.cli.commands import merge as shim
from specify_cli.core.constants import KITTY_SPECS_DIR
from specify_cli.merge import bookkeeping_projection as bp

pytestmark = pytest.mark.fast


SHIM_REEXPORTED = [
    "_validate_mission_slug_path_segment",
    "_target_bookkeeping_status_paths",
    "_assert_status_path_within_target_surface",
    "_assert_status_surface_path_is_trusted",
    "_assert_bookkeeping_snapshot_path_is_trusted",
    "_capture_bookkeeping_snapshots",
    "_restore_final_bookkeeping_snapshots",
    "_target_branch_still_at_baseline",
    "_project_status_bookkeeping_to_target",
]


@pytest.mark.parametrize("name", SHIM_REEXPORTED)
def test_shim_re_exports_the_same_object(name: str) -> None:
    assert getattr(shim, name) is getattr(bp, name)


def test_projection_does_not_import_command_shim() -> None:
    import ast
    import inspect

    tree = ast.parse(inspect.getsource(bp))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
        elif isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
    assert not any(
        m.startswith("specify_cli.cli.commands.merge") for m in modules
    ), sorted(modules)


def test_restore_final_bookkeeping_snapshots_signature_stable() -> None:
    """INV-6: the executor (WP10) calls this with a single dict positional arg."""
    import inspect

    sig = inspect.signature(bp._restore_final_bookkeeping_snapshots)
    params = list(sig.parameters)
    assert params == ["snapshots"]


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

    with patch.object(bp, "get_main_repo_root", lambda _r: repo):
        snapshots = bp._capture_bookkeeping_snapshots(repo, events)
        # Mutate, then restore.
        events.write_text("MUTATED\n", encoding="utf-8")
        bp._restore_final_bookkeeping_snapshots(snapshots)
    assert events.read_text(encoding="utf-8") == "ORIGINAL\n"


def test_capture_restore_recreates_deleted_file(tmp_path: Path) -> None:
    repo = _repo_with_spec(tmp_path)
    events = repo / KITTY_SPECS_DIR / "m" / "status.events.jsonl"
    # Absent at capture time -> snapshot is None -> restore must remove it.
    with patch.object(bp, "get_main_repo_root", lambda _r: repo):
        snapshots = bp._capture_bookkeeping_snapshots(repo, events)
        events.write_text("CREATED-AFTER-CAPTURE\n", encoding="utf-8")
        bp._restore_final_bookkeeping_snapshots(snapshots)
    assert not events.exists()


# --- path-trust: trusted + rejected branches --------------------------------


def test_snapshot_trust_accepts_kitty_specs(tmp_path: Path) -> None:
    repo = _repo_with_spec(tmp_path)
    candidate = repo / KITTY_SPECS_DIR / "m" / "status.json"
    with patch.object(bp, "get_main_repo_root", lambda _r: repo):
        trusted = bp._assert_bookkeeping_snapshot_path_is_trusted(repo_root=repo, candidate=candidate)
    assert trusted == candidate.resolve()


def test_snapshot_trust_rejects_outside_path(tmp_path: Path) -> None:
    repo = _repo_with_spec(tmp_path)
    outside = tmp_path / "elsewhere" / "evil.json"
    with (
        patch.object(bp, "get_main_repo_root", lambda _r: repo),
        pytest.raises(ValueError),
    ):
        bp._assert_bookkeeping_snapshot_path_is_trusted(repo_root=repo, candidate=outside)


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
