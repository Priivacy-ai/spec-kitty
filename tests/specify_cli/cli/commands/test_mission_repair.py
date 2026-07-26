"""``agent mission repair`` (WP08, coord-write-placement-closure-01KYCF83, FR-005/NFR-005).

RED-first (DIRECTIVE_041) through the REAL command entry point
(:func:`specify_cli.cli.commands.agent.mission_repair.run_mission_repair`, and the
registered ``agent mission repair`` CLI surface): a pre-existing cross-partition
content split-brain either forwards under strict-ancestor + clean worktree (zero
data loss), or is refused with a mission-scoped unified diff and mutates NOTHING
on genuine (non-ancestor) divergence.

Mirrors the real-git fixture-construction pattern from
``tests/coordination/test_coord_staleness.py`` (single repo, ``main`` + ``coord``
branches, real ``git worktree add``) rather than mocking git — the WP's own FF
machinery (``_coordination_doctor._is_ff_candidate``/``_fast_forward_finding``) is
exercised for real, not stubbed.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
import typer
from typer.testing import CliRunner

from specify_cli.cli.commands.agent import mission_repair as mr
from tests._support.ansi import strip_ansi

pytestmark = [pytest.mark.integration, pytest.mark.git_repo]

_MISSION_ID = "01KYCF8300000000000000REPR"
_COORD_BRANCH = "coord"
_TARGET_BRANCH = "main"


# ---------------------------------------------------------------------------
# Real-git fixture construction (mirrors tests/coordination/test_coord_staleness.py)
# ---------------------------------------------------------------------------


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repo), *args], check=True, capture_output=True, text=True,
    )


def _init_repo(repo: Path) -> None:
    repo.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["git", "init", "-qb", _TARGET_BRANCH, str(repo)], check=True, capture_output=True,
    )
    _git(repo, "config", "user.email", "test@test.com")
    _git(repo, "config", "user.name", "Test")
    _git(repo, "config", "commit.gpgsign", "false")
    (repo / "README.md").write_text("init\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "init")


def _seed_mission(repo: Path, mission_slug: str, *, coordination_branch: str | None = _COORD_BRANCH) -> Path:
    """Write ``kitty-specs/<slug>/meta.json`` + a baseline ``status.events.jsonl`` and commit.

    Omitting ``coordination_branch`` (pass ``None``) yields the legacy/non-
    coordinated shape used by the "nothing to repair" test.
    """
    feature_dir = repo / "kitty-specs" / mission_slug
    feature_dir.mkdir(parents=True, exist_ok=True)
    meta: dict[str, object] = {
        "mission_slug": mission_slug,
        "mission_id": _MISSION_ID,
        "target_branch": _TARGET_BRANCH,
    }
    if coordination_branch is not None:
        meta["coordination_branch"] = coordination_branch
    (feature_dir / "meta.json").write_text(json.dumps(meta, sort_keys=True), encoding="utf-8")
    (feature_dir / "status.events.jsonl").write_text("baseline-event\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "seed mission")
    return feature_dir


def _make_clean_repo(repo: Path, mission_slug: str) -> Path:
    """coord and main point at the SAME tip -- nothing to repair."""
    _init_repo(repo)
    feature_dir = _seed_mission(repo, mission_slug)
    _git(repo, "branch", _COORD_BRANCH)
    return feature_dir


def _make_coord_behind_repo(repo: Path, mission_slug: str) -> Path:
    """coord (behind) is a STRICT ancestor of main/target (ahead)."""
    _init_repo(repo)
    feature_dir = _seed_mission(repo, mission_slug)
    _git(repo, "branch", _COORD_BRANCH)
    (feature_dir / "status.events.jsonl").write_text("target-advanced-event\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "advance target only")
    return feature_dir


def _make_target_behind_repo(repo: Path, mission_slug: str) -> Path:
    """main/target (behind) is a STRICT ancestor of coord (ahead) -- the reverse direction."""
    _init_repo(repo)
    feature_dir = _seed_mission(repo, mission_slug)
    _git(repo, "branch", _COORD_BRANCH)
    _git(repo, "checkout", "-q", _COORD_BRANCH)
    (feature_dir / "status.events.jsonl").write_text("coord-advanced-event\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "advance coord only")
    _git(repo, "checkout", "-q", _TARGET_BRANCH)
    return feature_dir


def _make_diverged_repo(repo: Path, mission_slug: str) -> Path:
    """coord and main each carry a mission-content commit the other lacks -- diverged."""
    _init_repo(repo)
    feature_dir = _seed_mission(repo, mission_slug)
    _git(repo, "branch", _COORD_BRANCH)
    _git(repo, "checkout", "-q", _COORD_BRANCH)
    (feature_dir / "status.events.jsonl").write_text("coord-only-diverged-event\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "coord diverges")
    _git(repo, "checkout", "-q", _TARGET_BRANCH)
    (feature_dir / "status.events.jsonl").write_text("target-only-diverged-event\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "target diverges")
    return feature_dir


def _add_worktree(repo: Path, tmp_path: Path, branch: str, name: str) -> Path:
    worktree = tmp_path / name
    _git(repo, "worktree", "add", str(worktree), branch)
    return worktree


def _patch_root(monkeypatch: pytest.MonkeyPatch, repo: Path) -> None:
    monkeypatch.setattr(mr, "locate_project_root", lambda: repo)


# ---------------------------------------------------------------------------
# T038 (a): strict-ancestor + clean worktree -> zero-loss fast-forward.
# ---------------------------------------------------------------------------


@pytest.mark.non_sandbox
def test_ff_candidate_coord_behind_forwards_with_zero_data_loss(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    mission_slug = "coord-behind-mission"
    feature_dir = _make_coord_behind_repo(repo, mission_slug)
    coord_worktree = _add_worktree(repo, tmp_path, _COORD_BRANCH, "coord-wt")
    _patch_root(monkeypatch, repo)

    target_sha = _git(repo, "rev-parse", _TARGET_BRANCH).stdout.strip()
    coord_sha_before = _git(repo, "rev-parse", _COORD_BRANCH).stdout.strip()
    assert coord_sha_before != target_sha, "fixture precondition: coord must start behind target"

    mr.run_mission_repair(mission_slug)  # must NOT raise -- successful forward exits 0

    assert _git(repo, "rev-parse", _COORD_BRANCH).stdout.strip() == target_sha
    assert _git(coord_worktree, "rev-parse", "HEAD").stdout.strip() == target_sha
    # Zero data loss: the forwarded content is present in the coord worktree.
    assert (
        coord_worktree / "kitty-specs" / mission_slug / "status.events.jsonl"
    ).read_text(encoding="utf-8") == "target-advanced-event\n"
    # And the source content is untouched.
    assert (feature_dir / "status.events.jsonl").read_text(encoding="utf-8") == "target-advanced-event\n"


@pytest.mark.non_sandbox
def test_ff_candidate_target_behind_forwards_reverse_direction(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    """The reverse direction: primary/target is the stale partition, not coord.

    Gap-1's ``doctor coordination --fix`` only ever forwards coord -> target;
    this is the genuinely NEW bidirectional behaviour Gap-2 adds (T039).
    """
    repo = tmp_path / "repo"
    mission_slug = "target-behind-mission"
    _make_target_behind_repo(repo, mission_slug)
    _patch_root(monkeypatch, repo)

    coord_sha = _git(repo, "rev-parse", _COORD_BRANCH).stdout.strip()
    target_sha_before = _git(repo, "rev-parse", _TARGET_BRANCH).stdout.strip()
    assert target_sha_before != coord_sha, "fixture precondition: target must start behind coord"

    mr.run_mission_repair(mission_slug)

    assert _git(repo, "rev-parse", _TARGET_BRANCH).stdout.strip() == coord_sha
    feature_dir = repo / "kitty-specs" / mission_slug
    assert (feature_dir / "status.events.jsonl").read_text(encoding="utf-8") == "coord-advanced-event\n"


# ---------------------------------------------------------------------------
# T038 (b) / T041: non-ancestor divergence -> refuse + diff + non-zero exit +
# ZERO mutation.
# ---------------------------------------------------------------------------


@pytest.mark.non_sandbox
def test_divergent_refuses_with_diff_and_mutates_nothing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    repo = tmp_path / "repo"
    mission_slug = "diverged-mission"
    _make_diverged_repo(repo, mission_slug)
    _patch_root(monkeypatch, repo)

    coord_sha_before = _git(repo, "rev-parse", _COORD_BRANCH).stdout.strip()
    target_sha_before = _git(repo, "rev-parse", _TARGET_BRANCH).stdout.strip()
    feature_dir = repo / "kitty-specs" / mission_slug
    content_before = (feature_dir / "status.events.jsonl").read_text(encoding="utf-8")

    with pytest.raises(typer.Exit) as exc:
        mr.run_mission_repair(mission_slug)
    assert exc.value.exit_code == 1

    out = capsys.readouterr().out
    assert "Refusing to repair" in out
    assert "diverged" in out
    assert "diff --git" in out  # a real unified diff was printed
    assert "coord-only-diverged-event" in out or "target-only-diverged-event" in out

    # NFR-005: byte-identical before/after -- zero mutation.
    assert _git(repo, "rev-parse", _COORD_BRANCH).stdout.strip() == coord_sha_before
    assert _git(repo, "rev-parse", _TARGET_BRANCH).stdout.strip() == target_sha_before
    assert (feature_dir / "status.events.jsonl").read_text(encoding="utf-8") == content_before


@pytest.mark.non_sandbox
def test_divergent_diff_is_scoped_to_the_mission_directory(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    """The diff names THIS mission's diverged content, not repo-wide noise."""
    repo = tmp_path / "repo"
    mission_slug = "diverged-mission-scoped"
    _make_diverged_repo(repo, mission_slug)
    _patch_root(monkeypatch, repo)

    with pytest.raises(typer.Exit):
        mr.run_mission_repair(mission_slug)

    out = capsys.readouterr().out
    assert f"kitty-specs/{mission_slug}/status.events.jsonl" in out


# ---------------------------------------------------------------------------
# T039: clean state -> no-op.
# ---------------------------------------------------------------------------


@pytest.mark.non_sandbox
def test_clean_mission_is_a_noop(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    mission_slug = "clean-mission"
    _make_clean_repo(repo, mission_slug)
    _patch_root(monkeypatch, repo)

    coord_sha_before = _git(repo, "rev-parse", _COORD_BRANCH).stdout.strip()
    target_sha_before = _git(repo, "rev-parse", _TARGET_BRANCH).stdout.strip()

    mr.run_mission_repair(mission_slug)  # must NOT raise

    assert _git(repo, "rev-parse", _COORD_BRANCH).stdout.strip() == coord_sha_before
    assert _git(repo, "rev-parse", _TARGET_BRANCH).stdout.strip() == target_sha_before


def test_legacy_mission_without_coordination_branch_is_a_noop(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    """No ``coordination_branch`` -> nothing to reconcile; must not raise."""
    repo = tmp_path / "repo"
    mission_slug = "legacy-mission"
    _init_repo(repo)
    _seed_mission(repo, mission_slug, coordination_branch=None)
    _patch_root(monkeypatch, repo)

    mr.run_mission_repair(mission_slug)  # must NOT raise


def test_unknown_mission_exits_1(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _init_repo(repo)
    _patch_root(monkeypatch, repo)

    with pytest.raises(typer.Exit) as exc:
        mr.run_mission_repair("no-such-mission")
    assert exc.value.exit_code == 1


# ---------------------------------------------------------------------------
# T041: an unsafe FF precondition (dirty worktree) also refuses + mutates nothing,
# even though the branches ARE a strict-ancestor pair.
# ---------------------------------------------------------------------------


@pytest.mark.non_sandbox
def test_ff_candidate_with_dirty_worktree_refuses_and_mutates_nothing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    repo = tmp_path / "repo"
    mission_slug = "dirty-coord-mission"
    _make_coord_behind_repo(repo, mission_slug)
    coord_worktree = _add_worktree(repo, tmp_path, _COORD_BRANCH, "coord-wt")
    (coord_worktree / "dirty.txt").write_text("uncommitted\n", encoding="utf-8")
    _patch_root(monkeypatch, repo)

    coord_sha_before = _git(repo, "rev-parse", _COORD_BRANCH).stdout.strip()

    with pytest.raises(typer.Exit) as exc:
        mr.run_mission_repair(mission_slug)
    assert exc.value.exit_code == 1

    out = capsys.readouterr().out
    assert "Refusing to repair" in out

    assert _git(repo, "rev-parse", _COORD_BRANCH).stdout.strip() == coord_sha_before
    assert (coord_worktree / "dirty.txt").exists()


# ---------------------------------------------------------------------------
# T040: the command is REGISTERED + reachable via the real ``agent mission`` app.
# ---------------------------------------------------------------------------

_RUNNER = CliRunner()


def test_repair_command_registered_on_mission_app() -> None:
    from specify_cli.cli.commands.agent.mission import app as mission_app

    result = _RUNNER.invoke(mission_app, ["repair", "--help"])
    assert result.exit_code == 0
    assert "--mission" in strip_ansi(result.stdout)


@pytest.mark.non_sandbox
def test_repair_reachable_end_to_end_via_cli(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    """The registered CLI command actually drives the real repair logic, not a stub."""
    from specify_cli.cli.commands.agent.mission import app as mission_app

    repo = tmp_path / "repo"
    mission_slug = "cli-clean-mission"
    _make_clean_repo(repo, mission_slug)
    _patch_root(monkeypatch, repo)

    result = _RUNNER.invoke(mission_app, ["repair", "--mission", mission_slug])

    assert result.exit_code == 0
    plain = strip_ansi(result.stdout)
    assert "Clean" in plain or "Nothing to repair" in plain
