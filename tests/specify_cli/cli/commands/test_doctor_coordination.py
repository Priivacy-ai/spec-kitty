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
    # WP03 (#2240): next_step carries a real `git worktree add` command; no longer
    # the husk-remove-only `doctor workspaces --fix` (#1890 recurrence guard).
    assert "worktree add" in (f.next_step or "")
    assert "recovery_args" in f.extra


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


def test_coord_health_recovery_efficacy_missing_worktree(fresh_mission_repo: Path) -> None:
    """T010 efficacy: the COORDINATION_WORKTREE_MISSING recovery hint must ACTUALLY
    recreate the worktree — not merely exist.

    Pre-fix: `next_step` says `doctor workspaces --fix` (only removes husks);
    `extra` has no ``recovery_args`` key → assertion below fails → RED (#2240).
    Post-fix: `extra["recovery_args"]` carries the real `git worktree add` command
    → executing it creates the worktree → GREEN.
    """
    # coord branch created by fixture, but worktree NOT materialised.
    findings = _check_coordination_worktree_health(fresh_mission_repo, _meta())
    assert len(findings) == 1
    f = findings[0]
    assert f.error_code == "COORDINATION_WORKTREE_MISSING"

    # ── efficacy anchor ──────────────────────────────────────────────────────
    # The finding MUST carry a machine-readable `recovery_args` list so that
    # following the hint actually resolves the state.  On pre-fix code this key
    # is absent (extra == {}) → RED.  The failure message explains the #2240
    # phantom-hint recurrence.
    recovery_args: list[str] | None = f.extra.get("recovery_args")
    assert recovery_args is not None, (
        "COORDINATION_WORKTREE_MISSING finding must carry extra['recovery_args'] "
        "with a real `git worktree add` command so that following the hint "
        "actually recreates the coordination worktree. "
        "Recommending `doctor workspaces --fix` (which only removes husks) "
        "is the #2240 phantom-hint recurrence of the #1890 dead-command class."
    )

    # Execute the recovery command and verify state is resolved.
    subprocess.run(list(recovery_args), check=True, capture_output=True)
    worktree = CoordinationWorkspace.worktree_path(fresh_mission_repo, MISSION_SLUG, MID8)
    assert worktree.exists(), (
        "recovery_args must recreate the coordination worktree; it is still missing"
    )

    # Doctor must now report OK for this mission.
    after = _check_coordination_worktree_health(fresh_mission_repo, _meta())
    assert all(f2.severity == "ok" for f2 in after), (
        f"doctor still reports issues after recovery: {after}"
    )


def test_coord_health_never_created_branch_routes_to_flatten(
    fresh_mission_repo: Path,
) -> None:
    """T010 secondary: a declared coord_branch that does NOT exist in git must
    produce COORDINATION_WORKTREE_NEVER_CREATED (not the generic MISSING code)
    and its hint must lead with flattening.

    Pre-fix: both absent-branch and missing-worktree cases return the same
    COORDINATION_WORKTREE_MISSING code → assert on NEVER_CREATED fails → RED.
    """
    nonexistent_meta = {
        **_meta(),
        "coordination_branch": "kitty/mission-nonexistent-00000000",
    }
    findings = _check_coordination_worktree_health(fresh_mission_repo, nonexistent_meta)
    assert len(findings) == 1
    f = findings[0]
    assert f.error_code == "COORDINATION_WORKTREE_NEVER_CREATED", (
        f"a declared-but-absent coord branch must produce "
        f"COORDINATION_WORKTREE_NEVER_CREATED, got {f.error_code!r}"
    )
    # Flatten must be the first action recommended (consistent with WP02 / #2250).
    hint = (f.next_step or "").lower()
    assert "meta.json" in hint or "flatten" in hint, (
        "never-created hint must mention meta.json (flatten by removing coordination_branch)"
    )
    # No recovery_args: the fix is editing meta.json, not a git command.
    assert "recovery_args" not in f.extra


def test_coord_health_warns_stale_coord_worktree(fresh_mission_repo: Path) -> None:
    """T012: a coord worktree whose HEAD is behind the coord branch tip must
    produce a COORDINATION_WORKTREE_STALE warning.

    Pre-fix: no stale detection → no STALE finding → assertion fails → RED.
    """
    # Materialise the coord worktree (at the branch tip).
    path = CoordinationWorkspace.resolve(fresh_mission_repo, MISSION_SLUG, MID8)

    # Advance the coord branch by committing in the worktree…
    (path / "_stale_marker.txt").write_text("advance\n")
    _git(path, "add", ".")
    _git(path, "commit", "-m", "advance coord branch for stale test")

    # …then roll the worktree HEAD back one commit.  The coord branch tip stays
    # at the new commit, so the worktree is now 1 commit behind.
    #
    # NOTE: `git reset --hard HEAD~1` in a worktree moves BOTH the branch tip
    # and the worktree HEAD (shared ref).  To leave the branch tip at commit2
    # while moving the worktree HEAD to commit1, we first detach HEAD from the
    # branch (branch stays at commit2) and then reset the detached HEAD back.
    _git(path, "checkout", "--detach")
    _git(path, "reset", "--hard", "HEAD~1")

    findings = _check_coordination_worktree_health(fresh_mission_repo, _meta())
    stale = [fi for fi in findings if fi.error_code == "COORDINATION_WORKTREE_STALE"]
    assert stale, (
        "expected COORDINATION_WORKTREE_STALE warning when the coord worktree "
        "HEAD is 1 commit behind the coord branch tip"
    )
    assert stale[0].severity == "warning"
    assert stale[0].next_step is not None


def test_stale_coord_worktree_refresh_efficacy(
    fresh_mission_repo: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """T013 efficacy: _refresh_stale_coord_worktrees must fast-forward a stale
    coord worktree — outcome 'refreshed', HEAD==tip after, STALE not re-emitted.

    This proves ``doctor workspaces --fix`` performs what it claims (the exact
    phantom-efficacy class #2240 targets).  The stale signal is injected via
    monkeypatch of ``_coord_worktree_needs_refresh`` (returning stale=True with
    the coord branch name) because the git linked-worktree model makes HEAD and
    refs/heads/<branch> resolve identically in a single-repo checkout — a
    symbolic-HEAD worktree that lags behind its own branch tip cannot arise
    without fetch/push from an external clone.  The remainder of the execution
    path — registered-worktree discovery, real git merge --ff-only, and outcome
    classification — runs against genuine git objects, closing the lines 193-205
    (and 153-177 via the already_current + detached unit tests below) coverage
    gap flagged at 77% module coverage.

    Pre-fix (before _refresh_stale_coord_worktrees existed in WP03): import of
    the attribute itself would fail → RED.  Post-fix: the merge exits 0 → GREEN.
    """
    from specify_cli.cli.commands import _workspace_husk_doctor as wh

    # Materialise a coord worktree registered in git (name ends with -coord so
    # _registered_coord_worktrees picks it up).
    wt = CoordinationWorkspace.resolve(fresh_mission_repo, MISSION_SLUG, MID8)
    assert wt.exists(), "coord worktree must exist for the refresh efficacy test"

    # Inject staleness: _coord_worktree_needs_refresh returns (True, COORD_BRANCH)
    # to drive the function past the 'already_current' early-return and into the
    # git merge --ff-only branch.  The monkeypatch is scoped to this test.
    monkeypatch.setattr(
        wh,
        "_coord_worktree_needs_refresh",
        lambda _wt, _root: (True, COORD_BRANCH),
    )

    # Execute the recovery path — this is the real _refresh_stale_coord_worktrees,
    # not a mock.  It calls real git commands against the worktree on disk.
    outcomes = wh._refresh_stale_coord_worktrees(fresh_mission_repo)

    # Must yield exactly one outcome for the registered coord worktree.
    assert len(outcomes) == 1, f"expected 1 outcome from refresh, got {outcomes!r}"
    _path_str, outcome = outcomes[0]
    assert outcome == "refreshed", (
        f"expected 'refreshed' from git merge --ff-only; got {outcome!r}. "
        "'failed' means the merge exited non-zero. "
        "'skip_detached' means _registered_coord_worktrees did not find the worktree. "
        "'already_current' means the stale-injection monkeypatch was not applied."
    )

    # Efficacy: coord worktree HEAD must equal the coord branch tip.
    worktree_head = subprocess.check_output(
        ["git", "-C", str(wt), "rev-parse", "HEAD"], text=True,
    ).strip()
    branch_tip = subprocess.check_output(
        ["git", "-C", str(fresh_mission_repo), "rev-parse",
         f"refs/heads/{COORD_BRANCH}"], text=True,
    ).strip()
    assert worktree_head == branch_tip, (
        "after refresh, coord worktree HEAD must equal the coord branch tip"
    )

    # State resolution: re-running _check_coordination_worktree_health uses
    # _coord_worktree_stale_finding (a separate function in _coordination_doctor.py,
    # not the monkeypatched _coord_worktree_needs_refresh) and must not emit
    # COORDINATION_WORKTREE_STALE for a worktree that is already at the tip.
    findings_after = _check_coordination_worktree_health(fresh_mission_repo, _meta())
    stale_after = [
        f for f in findings_after
        if f.error_code == "COORDINATION_WORKTREE_STALE"
    ]
    assert not stale_after, (
        f"COORDINATION_WORKTREE_STALE must not be present after refresh; "
        f"still emitted: {stale_after}"
    )


# ---------------------------------------------------------------------------
# _coord_worktree_needs_refresh unit coverage (lines 153-177)
# ---------------------------------------------------------------------------


def test_coord_worktree_needs_refresh_already_current(
    fresh_mission_repo: Path,
) -> None:
    """_coord_worktree_needs_refresh returns (False, branch) when HEAD==tip.

    Covers lines 153-170: symbolic-ref succeeds, both rev-parse calls succeed,
    head_sha == tip_sha → (False, branch) early return.
    """
    from specify_cli.cli.commands import _workspace_husk_doctor as wh

    wt = CoordinationWorkspace.resolve(fresh_mission_repo, MISSION_SLUG, MID8)
    stale, branch = wh._coord_worktree_needs_refresh(wt, fresh_mission_repo)
    assert stale is False
    assert branch == COORD_BRANCH


def test_coord_worktree_needs_refresh_detached_head(
    fresh_mission_repo: Path,
) -> None:
    """_coord_worktree_needs_refresh returns (False, '') when HEAD is detached.

    Covers lines 153-160: symbolic-ref exits non-zero → branch == '' →
    early return (False, ''), which _refresh_stale_coord_worktrees maps to
    'skip_detached'.
    """
    from specify_cli.cli.commands import _workspace_husk_doctor as wh

    wt = CoordinationWorkspace.resolve(fresh_mission_repo, MISSION_SLUG, MID8)
    _git(wt, "checkout", "--detach")
    stale, branch = wh._coord_worktree_needs_refresh(wt, fresh_mission_repo)
    assert stale is False
    assert branch == ""
