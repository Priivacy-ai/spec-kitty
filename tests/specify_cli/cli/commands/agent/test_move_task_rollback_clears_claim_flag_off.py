"""#2512 (flag-OFF): ``move-task --to planned`` clears the FRONTMATTER claim.

Flag-OFF companion to ``test_move_task_rollback_clears_claim.py`` (flag ON).

Under the #2684 eviction the rollback claim release is emitted as an
``InnerStateChanged`` annotation (event-only). At **flag ON** that is the whole
story — the WP file is byte-stable and readers source the release from the
snapshot. But at **flag OFF (default / pre-cutover)** the legacy frontmatter is
still authoritative and is what flag-OFF ``stale_detection`` reads, so a
rollback MUST also strip the frontmatter ``agent``/``shell_pid`` claim markers
(the #2512 behaviour WP06 deleted with the god-write and WP10 restored on the
flag-OFF dual-write path only).

This test drives the real ``move-task`` entry point with ``status_phase``
unset (flag OFF), seeds a stale ``agent``/``shell_pid`` claim into the WP
frontmatter, rolls the WP back to ``planned``, and asserts the frontmatter
claim markers are gone (must NOT block the next allocator on a stale pid).
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
from click.testing import Result
from typer.testing import CliRunner

from specify_cli.cli.commands.agent import tasks as tasks_module
from specify_cli.cli.commands.agent.tasks import app as tasks_app
from specify_cli.status import Lane
from specify_cli.status.models import StatusEvent
from specify_cli.status.store import append_event
from specify_cli.task_utils import extract_scalar, split_frontmatter
from tests.lane_test_utils import write_single_lane_manifest

pytestmark = [pytest.mark.integration, pytest.mark.git_repo]

_MISSION_SLUG = "001-rollback-clears-claim-flag-off"
_STALE_PID = 41417
_STALE_AGENT = "claude-code"


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)


def _seed_claim_to_in_review(feature_dir: Path) -> None:
    """genesis -> planned -> claimed(claim triple) -> in_progress -> for_review
    -> in_review, so the event-log lane is ``in_review`` before the rollback."""
    hops = [
        (Lane.GENESIS, Lane.PLANNED, None),
        (Lane.PLANNED, Lane.CLAIMED, {"shell_pid": _STALE_PID, "agent": _STALE_AGENT}),
        (Lane.CLAIMED, Lane.IN_PROGRESS, None),
        (Lane.IN_PROGRESS, Lane.FOR_REVIEW, None),
        (Lane.FOR_REVIEW, Lane.IN_REVIEW, None),
    ]
    for idx, (frm, to, policy_metadata) in enumerate(hops, start=1):
        append_event(
            feature_dir,
            StatusEvent(
                event_id=f"seed-{idx}",
                mission_slug=_MISSION_SLUG,
                wp_id="WP01",
                from_lane=frm,
                to_lane=to,
                at=f"2026-01-01T00:00:0{idx}+00:00",
                actor="fixture",
                force=True,
                execution_mode="worktree",
                policy_metadata=policy_metadata,
            ),
        )


def _build_flag_off_mission(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> tuple[Path, Path]:
    """Materialise a **flag-OFF** (``status_phase`` unset) lanes mission with
    WP01 seeded to ``in_review`` and a stale claim in the WP **frontmatter**.
    Returns ``(repo, feature_dir)``.
    """
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-b", "main")
    _git(repo, "config", "user.email", "wp10@example.invalid")
    _git(repo, "config", "user.name", "WP10 Rollback Claim FlagOff")
    _git(repo, "config", "commit.gpgsign", "false")
    (repo / ".kittify").mkdir()
    (repo / ".kittify" / "config.yaml").write_text("auto_commit: false\n", encoding="utf-8")

    feature_dir = repo / "kitty-specs" / _MISSION_SLUG
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir(parents=True)
    write_single_lane_manifest(feature_dir, wp_ids=("WP01",))

    # flag OFF: status_phase left unset -> _phase1_snapshot_authority_active False,
    # so the legacy frontmatter god-write path (dual-write) runs.
    meta_path = feature_dir / "meta.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    meta.pop("status_phase", None)
    meta_path.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")

    (feature_dir / "tasks.md").write_text(
        "# Tasks\n\n## WP01 - Core\n\n(no subtasks)\n", encoding="utf-8"
    )
    # A LIVE claim in the frontmatter (the #2512 stale-marker repro): rolling
    # back to planned must strip ``agent``/``shell_pid`` on the flag-OFF path.
    (tasks_dir / "WP01-core.md").write_text(
        "---\n"
        "work_package_id: WP01\n"
        "title: Core\n"
        "agent: reviewer\n"
        f"shell_pid: {_STALE_PID}\n"
        "subtasks: []\n"
        "tracker_refs: []\n"
        "dependencies: []\n"
        "---\n\n# WP01\n\n## Activity Log\n",
        encoding="utf-8",
    )

    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "seed flag-off rollback-clears-claim fixture")
    _seed_claim_to_in_review(feature_dir)

    monkeypatch.chdir(repo)
    monkeypatch.setattr(tasks_module, "locate_project_root", lambda: repo)
    monkeypatch.setattr(
        tasks_module, "_validate_ready_for_review", lambda *_a, **_k: (True, [])
    )
    monkeypatch.setattr(tasks_module, "get_mission_type", lambda *_a, **_k: "software-dev")
    return repo, feature_dir


def _front(wp_file: Path) -> str:
    front, _body, _pad = split_frontmatter(wp_file.read_text(encoding="utf-8-sig"))
    return front


def _move(args: list[str]) -> Result:
    return CliRunner().invoke(tasks_app, ["move-task", *args])


def test_flag_off_rollback_to_planned_clears_frontmatter_claim(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """At flag OFF, a rollback to planned strips the frontmatter
    ``agent``/``shell_pid`` claim markers (the #2512 stale-pid release that
    flag-OFF ``stale_detection`` relies on)."""
    repo, feature_dir = _build_flag_off_mission(tmp_path, monkeypatch)
    wp_file = feature_dir / "tasks" / "WP01-core.md"
    feedback = repo / "feedback.md"
    feedback.write_text("**Issue**: rework requested.\n", encoding="utf-8")

    # Positive control: the claim markers are present BEFORE the rollback.
    front_before = _front(wp_file)
    assert extract_scalar(front_before, "agent") == "reviewer"
    assert extract_scalar(front_before, "shell_pid") == str(_STALE_PID)

    result = _move(
        [
            "WP01", "--to", "planned", "--mission", _MISSION_SLUG,
            "--review-feedback-file", str(feedback), "--no-auto-commit", "--json",
        ]
    )
    assert result.exit_code == 0, result.output

    front_after = _front(wp_file)
    assert not extract_scalar(front_after, "agent"), (
        f"agent marker not cleared on flag-OFF rollback: "
        f"{extract_scalar(front_after, 'agent')!r}"
    )
    assert not extract_scalar(front_after, "shell_pid"), (
        f"shell_pid marker not cleared on flag-OFF rollback: "
        f"{extract_scalar(front_after, 'shell_pid')!r}"
    )
