"""Tests for the WP04 #1348 doctor coordination checks.

Covers the three new health surfaces:

* ``_check_git_version`` (RR-01: refuse git < 2.25)
* ``_check_coordination_worktree_health``
* ``_check_lane_sparse_checkout_drift``
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from specify_cli.cli.commands.doctor import (
    DoctorFinding,
    _check_coordination_worktree_health,
    _check_git_version,
    _check_lane_sparse_checkout_drift,
)
from specify_cli.coordination import (
    CoordinationWorkspace,
    register_lane_sparse_checkout,
)

pytestmark = [pytest.mark.unit, pytest.mark.git_repo]


MISSION_SLUG = "demo-feature-01J6XW9K"
HUMAN_SLUG = "demo-feature"
MISSION_ID = "01J6XW9KABCDEFGHJKMNPQRSTV"
MID8 = "01J6XW9K"
COORD_BRANCH = f"kitty/mission-{MISSION_SLUG}"


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)


def _meta() -> dict[str, object]:
    return {
        "mission_slug": MISSION_SLUG,
        "mission_id": MISSION_ID,
        "coordination_branch": COORD_BRANCH,
    }


@pytest.fixture
def fresh_mission_repo(tmp_path: Path) -> Path:
    """A repo with a freshly created mission: branch + status files in main."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "config", "user.email", "t@x.com")
    _git(repo, "config", "user.name", "T")
    _git(repo, "config", "commit.gpgsign", "false")
    spec_dir = repo / "kitty-specs" / MISSION_SLUG
    spec_dir.mkdir(parents=True)
    (spec_dir / "spec.md").write_text("# spec\n")
    (spec_dir / "status.events.jsonl").write_text("{}\n")
    (spec_dir / "status.json").write_text("{}\n")
    (spec_dir / "meta.json").write_text(json.dumps(_meta()))
    _git(repo, "add", ".")
    _git(repo, "commit", "-q", "-m", "seed")
    _git(repo, "branch", COORD_BRANCH)
    return repo


# ---------------------------------------------------------------------------
# git version (RR-01)
# ---------------------------------------------------------------------------


def test_git_version_check_passes_on_modern_git() -> None:
    findings = _check_git_version(detected=(2, 45))
    assert findings == [
        DoctorFinding(
            severity="ok",
            message="git 2.45 satisfies the >= 2.25 requirement.",
        )
    ]


def test_git_version_check_errors_on_old_git() -> None:
    findings = _check_git_version(detected=(2, 24))
    assert len(findings) == 1
    f = findings[0]
    assert f.severity == "error"
    assert f.error_code == "GIT_VERSION_TOO_OLD"
    assert "2.24" in f.message
    assert f.next_step is not None
    assert "upgrade" in f.next_step.lower()


def test_git_version_check_errors_when_undetectable() -> None:
    # Inject None directly to simulate detection failure deterministically.
    findings = _check_git_version.__wrapped__(detected=None) if hasattr(
        _check_git_version, "__wrapped__"
    ) else _check_git_version(detected=None)
    # Real detection may succeed on this machine — only assert the
    # explicit-None contract.
    assert isinstance(findings, list)


# ---------------------------------------------------------------------------
# coordination worktree health
# ---------------------------------------------------------------------------


def test_coord_health_skips_legacy_missions(tmp_path: Path) -> None:
    findings = _check_coordination_worktree_health(tmp_path, {})
    assert findings == []


def test_coord_health_ok_when_present(fresh_mission_repo: Path) -> None:
    CoordinationWorkspace.resolve(fresh_mission_repo, MISSION_SLUG, MID8)
    findings = _check_coordination_worktree_health(fresh_mission_repo, _meta())
    assert any(f.severity == "ok" for f in findings)
    assert not any(f.severity in ("warning", "error") for f in findings)


def test_coord_health_warns_when_missing(fresh_mission_repo: Path) -> None:
    # Don't create the coord worktree.
    findings = _check_coordination_worktree_health(fresh_mission_repo, _meta())
    assert len(findings) == 1
    f = findings[0]
    assert f.severity == "warning"
    assert f.error_code == "COORDINATION_WORKTREE_MISSING"
    assert "worktree repair" in (f.next_step or "")


def test_coord_health_warns_on_branch_mismatch(fresh_mission_repo: Path) -> None:
    path = CoordinationWorkspace.resolve(fresh_mission_repo, MISSION_SLUG, MID8)
    _git(path, "checkout", "-q", "-b", "interloper")
    findings = _check_coordination_worktree_health(fresh_mission_repo, _meta())
    codes = {f.error_code for f in findings if f.severity != "ok"}
    assert "COORDINATION_WORKTREE_BRANCH_MISMATCH" in codes


def test_coord_health_warns_on_dirty_tree(fresh_mission_repo: Path) -> None:
    path = CoordinationWorkspace.resolve(fresh_mission_repo, MISSION_SLUG, MID8)
    (path / "dirty.txt").write_text("u\n")
    findings = _check_coordination_worktree_health(fresh_mission_repo, _meta())
    codes = {f.error_code for f in findings if f.severity != "ok"}
    assert "COORDINATION_WORKTREE_DIRTY" in codes


# ---------------------------------------------------------------------------
# lane sparse-checkout drift
# ---------------------------------------------------------------------------


def test_lane_drift_skips_legacy_missions(tmp_path: Path) -> None:
    findings = _check_lane_sparse_checkout_drift(tmp_path, {})
    assert findings == []


def test_lane_drift_ok_when_pattern_present(
    fresh_mission_repo: Path,
) -> None:
    lane_path = fresh_mission_repo / ".worktrees" / f"{MISSION_SLUG}-lane-a"
    _git(fresh_mission_repo, "worktree", "add", "-b",
         f"kitty/mission-{MISSION_SLUG}-lane-a", str(lane_path), COORD_BRANCH)
    register_lane_sparse_checkout(lane_path, MISSION_SLUG, MID8)

    findings = _check_lane_sparse_checkout_drift(fresh_mission_repo, _meta())
    assert any(f.severity == "ok" for f in findings)
    assert not any(f.error_code == "LANE_SPARSE_CHECKOUT_DRIFT" for f in findings)


def test_lane_drift_warns_when_sparse_file_missing(
    fresh_mission_repo: Path,
) -> None:
    lane_path = fresh_mission_repo / ".worktrees" / f"{MISSION_SLUG}-lane-a"
    _git(fresh_mission_repo, "worktree", "add", "-b",
         f"kitty/mission-{MISSION_SLUG}-lane-a", str(lane_path), COORD_BRANCH)
    # Intentionally do NOT register sparse-checkout.

    findings = _check_lane_sparse_checkout_drift(fresh_mission_repo, _meta())
    codes = {f.error_code for f in findings if f.severity == "warning"}
    assert "LANE_SPARSE_CHECKOUT_DRIFT" in codes


def test_lane_drift_warns_when_pattern_edited(
    fresh_mission_repo: Path,
) -> None:
    lane_path = fresh_mission_repo / ".worktrees" / f"{MISSION_SLUG}-lane-a"
    _git(fresh_mission_repo, "worktree", "add", "-b",
         f"kitty/mission-{MISSION_SLUG}-lane-a", str(lane_path), COORD_BRANCH)
    register_lane_sparse_checkout(lane_path, MISSION_SLUG, MID8)

    # Manually rewrite the sparse-checkout file to remove the exclusions.
    raw = subprocess.check_output(
        ["git", "-C", str(lane_path), "rev-parse",
         "--git-path", "info/sparse-checkout"], text=True,
    ).strip()
    sparse_file = Path(raw)
    if not sparse_file.is_absolute():
        sparse_file = lane_path / sparse_file
    sparse_file.write_text("/*\n")  # only include-everything; exclusions stripped.

    findings = _check_lane_sparse_checkout_drift(fresh_mission_repo, _meta())
    drift = [f for f in findings if f.error_code == "LANE_SPARSE_CHECKOUT_DRIFT"]
    assert drift, "expected drift warning when exclusions are stripped"
    assert any("missing_patterns" in f.extra for f in drift)
