"""Concurrency tests for ensure_runtime() — file locking under parallel access.

Covers:
- T011: N parallel ensure_runtime() calls do not corrupt ~/.kittify/ (G5, 1A-06)
"""

from __future__ import annotations

import multiprocessing
import os
import shutil
import tempfile
from pathlib import Path

import pytest


def _setup_fake_assets(asset_dir: str) -> None:
    """Create a minimal package asset tree for testing."""
    missions = Path(asset_dir) / "missions"
    (missions / "software-dev").mkdir(parents=True, exist_ok=True)
    (missions / "software-dev" / "mission.yaml").write_text("test-mission-sw")
    (missions / "research").mkdir(parents=True, exist_ok=True)
    (missions / "research" / "mission.yaml").write_text("test-mission-res")
    (missions / "documentation").mkdir(parents=True, exist_ok=True)
    (missions / "documentation" / "mission.yaml").write_text("test-mission-doc")

    scripts = Path(asset_dir) / "scripts"
    scripts.mkdir(parents=True, exist_ok=True)
    (scripts / "validate.py").write_text("# validate script")


def _run_ensure(args: tuple[str, str]) -> bool:
    """Worker function: run ensure_runtime() and return success.

    Must be a top-level function for multiprocessing to pickle it.

    Args:
        args: Tuple of (home_path, asset_dir) for env vars.
    """
    home_path, asset_dir = args
    os.environ["SPEC_KITTY_HOME"] = home_path
    os.environ["SPEC_KITTY_TEMPLATE_ROOT"] = str(Path(asset_dir) / "missions")
    try:
        from specify_cli.runtime.bootstrap import ensure_runtime

        ensure_runtime()
        return True
    except Exception as exc:
        import traceback

        traceback.print_exc()
        return False


class TestConcurrentEnsureRuntime:
    """N parallel CLI starts do not corrupt ~/.kittify/ (G5, 1A-06)."""

    @pytest.mark.slow
    def test_concurrent_no_corruption_8_workers(self, tmp_path: Path) -> None:
        """8 parallel ensure_runtime() calls produce a valid ~/.kittify/."""
        home = tmp_path / "kittify"
        asset_dir = tmp_path / "assets"
        asset_dir.mkdir()
        _setup_fake_assets(str(asset_dir))

        n_workers = 8
        args_list = [(str(home), str(asset_dir))] * n_workers

        ctx = multiprocessing.get_context("spawn")
        with ctx.Pool(n_workers) as pool:
            results = pool.map(_run_ensure, args_list)

        assert all(results), f"Some workers failed: {results}"

        # Verify version.lock is correct
        version_file = home / "cache" / "version.lock"
        assert version_file.exists(), "version.lock missing after concurrent runs"
        stored_version = version_file.read_text().strip()
        assert len(stored_version) > 0, "version.lock is empty"

        # Verify no corruption (managed dirs present)
        assert (home / "missions" / "software-dev").is_dir()
        assert (home / "missions" / "software-dev" / "mission.yaml").exists()
        assert (home / "missions" / "research").is_dir()

    @pytest.mark.slow
    def test_concurrent_no_corruption_4_workers(self, tmp_path: Path) -> None:
        """4 parallel ensure_runtime() calls produce a valid ~/.kittify/."""
        home = tmp_path / "kittify"
        asset_dir = tmp_path / "assets"
        asset_dir.mkdir()
        _setup_fake_assets(str(asset_dir))

        n_workers = 4
        args_list = [(str(home), str(asset_dir))] * n_workers

        ctx = multiprocessing.get_context("spawn")
        with ctx.Pool(n_workers) as pool:
            results = pool.map(_run_ensure, args_list)

        assert all(results), f"Some workers failed: {results}"

        version_file = home / "cache" / "version.lock"
        assert version_file.exists()
        assert (home / "missions" / "software-dev").is_dir()

    @pytest.mark.slow
    def test_concurrent_no_corruption_16_workers(self, tmp_path: Path) -> None:
        """16 parallel ensure_runtime() calls produce a valid ~/.kittify/."""
        home = tmp_path / "kittify"
        asset_dir = tmp_path / "assets"
        asset_dir.mkdir()
        _setup_fake_assets(str(asset_dir))

        n_workers = 16
        args_list = [(str(home), str(asset_dir))] * n_workers

        ctx = multiprocessing.get_context("spawn")
        with ctx.Pool(n_workers) as pool:
            results = pool.map(_run_ensure, args_list)

        assert all(results), f"Some workers failed: {results}"

        # Verify version.lock is correct
        version_file = home / "cache" / "version.lock"
        assert version_file.exists(), "version.lock missing after concurrent runs"
        stored_version = version_file.read_text().strip()
        assert len(stored_version) > 0, "version.lock is empty"

        # Verify no corruption (managed dirs present)
        assert (home / "missions" / "software-dev").is_dir()
        assert (home / "missions" / "software-dev" / "mission.yaml").exists()
        assert (home / "missions" / "research").is_dir()
        assert (home / "missions" / "documentation").is_dir()

        # No orphaned temp directories
        update_dirs = list(tmp_path.glob(".kittify_update_*"))
        assert len(update_dirs) == 0, f"Orphaned temp dirs: {update_dirs}"

    @pytest.mark.slow
    def test_concurrent_no_temp_dirs_left_behind(self, tmp_path: Path) -> None:
        """After concurrent runs, no .kittify_update_* temp dirs remain."""
        home = tmp_path / "kittify"
        asset_dir = tmp_path / "assets"
        asset_dir.mkdir()
        _setup_fake_assets(str(asset_dir))

        n_workers = 4
        args_list = [(str(home), str(asset_dir))] * n_workers

        ctx = multiprocessing.get_context("spawn")
        with ctx.Pool(n_workers) as pool:
            results = pool.map(_run_ensure, args_list)

        assert all(results)

        # No orphaned temp directories
        update_dirs = list(tmp_path.glob(".kittify_update_*"))
        assert len(update_dirs) == 0, f"Orphaned temp dirs: {update_dirs}"

    @pytest.mark.slow
    def test_concurrent_version_lock_consistent(self, tmp_path: Path) -> None:
        """All workers converge on the same version.lock value."""
        home = tmp_path / "kittify"
        asset_dir = tmp_path / "assets"
        asset_dir.mkdir()
        _setup_fake_assets(str(asset_dir))

        n_workers = 8
        args_list = [(str(home), str(asset_dir))] * n_workers

        ctx = multiprocessing.get_context("spawn")
        with ctx.Pool(n_workers) as pool:
            results = pool.map(_run_ensure, args_list)

        assert all(results)

        version_file = home / "cache" / "version.lock"
        stored = version_file.read_text().strip()
        # All workers should write the same version; verify it's non-empty
        # and looks like a valid version string
        assert len(stored) > 0
        assert "." in stored or "dev" in stored, f"Unexpected version format: {stored}"
