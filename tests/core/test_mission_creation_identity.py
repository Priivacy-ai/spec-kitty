"""Regression tests for ULID mission_id minting at creation time (T019 / FR-201..FR-206)."""

from __future__ import annotations

import json
import subprocess
import threading
from pathlib import Path
from unittest.mock import patch

import pytest
from ulid import ULID

from specify_cli.core.mission_creation import create_mission_core

pytestmark = pytest.mark.fast

_CORE_MODULE = "specify_cli.core.mission_creation"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _init_git_repo(repo: Path) -> None:
    """Initialise a minimal git repo with .kittify and kitty-specs."""
    (repo / ".kittify").mkdir(exist_ok=True)
    (repo / "kitty-specs").mkdir(exist_ok=True)
    subprocess.run(["git", "init"], cwd=repo, capture_output=True, check=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=repo, capture_output=True, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, capture_output=True, check=True)
    subprocess.run(["git", "commit", "-m", "init", "--allow-empty"], cwd=repo, capture_output=True, check=True)


def _run_create(tmp_path: Path, slug: str, feature_number: int = 1) -> dict:
    """Helper: call create_mission_core with standard mocks, return meta dict."""
    with (
        patch(f"{_CORE_MODULE}.locate_project_root", return_value=tmp_path),
        patch(f"{_CORE_MODULE}.is_worktree_context", return_value=False),
        patch(f"{_CORE_MODULE}.is_git_repo", return_value=True),
        patch(f"{_CORE_MODULE}.get_current_branch", return_value="main"),
        patch(f"{_CORE_MODULE}.get_next_feature_number", return_value=feature_number),
        patch(f"{_CORE_MODULE}.emit_mission_created"),
        patch(f"{_CORE_MODULE}._commit_feature_file"),
    ):
        return create_mission_core(tmp_path, slug)


# ---------------------------------------------------------------------------
# T3.1 — mission_id minted at creation, ULID-shaped
# ---------------------------------------------------------------------------


def test_mission_id_minted_at_creation(tmp_path: Path) -> None:
    """create_mission_core writes a 26-char ULID mission_id to meta.json."""
    _init_git_repo(tmp_path)
    result = _run_create(tmp_path, "test-identity")

    meta_path = tmp_path / "kitty-specs" / "001-test-identity" / "meta.json"
    assert meta_path.exists()
    meta = json.loads(meta_path.read_text())

    assert "mission_id" in meta
    assert isinstance(meta["mission_id"], str)
    assert len(meta["mission_id"]) == 26, f"Expected 26-char ULID, got {meta['mission_id']!r}"
    # Parses without exception — proves it is a valid ULID
    ULID.from_str(meta["mission_id"])


def test_mission_id_present_in_result_meta(tmp_path: Path) -> None:
    """MissionCreationResult.meta contains mission_id."""
    _init_git_repo(tmp_path)
    result = _run_create(tmp_path, "test-meta-identity")

    assert "mission_id" in result.meta
    assert len(result.meta["mission_id"]) == 26
    ULID.from_str(result.meta["mission_id"])


# ---------------------------------------------------------------------------
# T3.2 — mission_id is NOT derived from prefix scan
# ---------------------------------------------------------------------------


def test_mission_id_is_not_derived_from_prefix_scan(tmp_path: Path) -> None:
    """Two missions with different numeric prefixes get different, independent ULIDs."""
    _init_git_repo(tmp_path)
    result_a = _run_create(tmp_path, "feature-alpha", feature_number=1)
    result_b = _run_create(tmp_path, "feature-beta", feature_number=2)

    id_a = result_a.meta["mission_id"]
    id_b = result_b.meta["mission_id"]

    assert id_a != id_b, "Two distinct missions must have different mission_ids"
    # Both must parse as valid ULIDs
    ULID.from_str(id_a)
    ULID.from_str(id_b)


# ---------------------------------------------------------------------------
# T3.3 — Concurrent creates do not collide
# ---------------------------------------------------------------------------


def test_concurrent_creates_no_collision(tmp_path: Path) -> None:
    """Spawning two threads each creating a different slug yields two distinct mission_ids."""
    _init_git_repo(tmp_path)
    results: list[dict] = []
    errors: list[Exception] = []

    counter = [0]
    counter_lock = threading.Lock()

    def create_and_capture(slug: str) -> None:
        with counter_lock:
            counter[0] += 1
            n = counter[0]
        try:
            result = _run_create(tmp_path, slug, feature_number=n)
            results.append(result.meta)
        except Exception as exc:
            errors.append(exc)

    t1 = threading.Thread(target=create_and_capture, args=("concurrent-alpha",))
    t2 = threading.Thread(target=create_and_capture, args=("concurrent-beta",))
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    assert not errors, f"Thread errors: {errors}"
    assert len(results) == 2
    id_0 = results[0]["mission_id"]
    id_1 = results[1]["mission_id"]
    assert id_0 != id_1, f"Collision detected: both missions got mission_id={id_0!r}"
    # Both must be valid ULIDs
    ULID.from_str(id_0)
    ULID.from_str(id_1)
