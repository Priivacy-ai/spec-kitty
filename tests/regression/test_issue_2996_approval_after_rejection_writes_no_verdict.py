"""RED-FIRST P0 reproduction of #2996(a) per ADR 2026-07-17-1
(docs/adr/3.x/2026-07-17-1-red-main-is-honest-ci-is-release-authority.md).
Intentionally FAILS until the product bug is fixed — a red mainline is the
honest signal of this release-blocking P0. Do NOT xfail/skip/quarantine to
green; fix the product. Tracking issue: #2996.

Extracted (landing fold: make ``@pytest.mark.regression`` mean exactly one
thing) from ``tests/integration/test_review_cycle_rejection_only.py``, which
carries only this one regression-marked test alongside several unrelated,
passing WP04 (#676) counter-advancement tests. Those tests, and the
``for_review_repo`` fixture / helpers they share with this reproduction,
stay in the original file untouched; this module carries its own copies so
this file has no import dependency back onto a file that may itself keep
evolving for unrelated reasons.

Symptom: once a WP has EVER been rejected, no normal ``move-task --to
approved`` invocation can ever record an approval verdict artifact — even
after the WP has been fully reworked and resubmitted through
claimed -> in_progress -> for_review -> in_review. Expected red until #2996
closes.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
from typer.testing import CliRunner

from specify_cli.frontmatter import write_frontmatter
from specify_cli.lanes.models import ExecutionLane, LanesManifest
from specify_cli.lanes.persistence import write_lanes_json
from specify_cli.status.models import Lane, StatusEvent
from specify_cli.status.store import append_event

pytestmark = [pytest.mark.regression, pytest.mark.integration, pytest.mark.git_repo]

MISSION_SLUG = "001-rejection-only-feature"
WP_SLUG = "WP01-test-task"


def _make_event(
    *,
    event_id: str,
    wp_id: str = "WP01",
    from_lane: Lane = Lane.PLANNED,
    to_lane: Lane = Lane.CLAIMED,
    review_ref: str | None = None,
    mission_slug: str = MISSION_SLUG,
) -> StatusEvent:
    return StatusEvent(
        event_id=event_id,
        mission_slug=mission_slug,
        wp_id=wp_id,
        from_lane=from_lane,
        to_lane=to_lane,
        at="2026-04-28T12:00:00Z",
        actor="claude",
        force=False,
        execution_mode="worktree",
        review_ref=review_ref,
    )


def _write_cli_wp(wp_path: Path) -> None:
    write_frontmatter(
        wp_path,
        {
            "work_package_id": "WP01",
            "subtasks": ["T001"],
            "title": "Test Task",
            "phase": "Phase 1",
            "lane": "planned",
            "dependencies": [],
            "assignee": "",
            "agent": "claude",
            "shell_pid": "",
            "review_status": "none",
            "review_feedback": "",
            "history": [],
        },
        "# WP01 Prompt\n",
    )


# ---------------------------------------------------------------------------
# Fixture: build a minimal mission + WP repo and put the WP into for_review.
# ---------------------------------------------------------------------------


@pytest.fixture()
def for_review_repo(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> tuple[Path, Path, Path]:
    """Initialise a git repo with one mission, one WP, currently in ``for_review``.

    Returns ``(repo_root, feature_dir, sub_artifact_dir)``.
    """
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-b", "main"], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.name", "Test User"], cwd=repo, check=True, capture_output=True
    )
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=repo,
        check=True,
        capture_output=True,
    )

    (repo / ".kittify").mkdir()

    feature_dir = repo / "kitty-specs" / MISSION_SLUG
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir(parents=True)
    (feature_dir / "meta.json").write_text(
        json.dumps(
            {
                "feature_number": "001",
                "mission_slug": MISSION_SLUG,
                "created_at": "2026-04-28T00:00:00Z",
                "friendly_name": MISSION_SLUG,
                "mission": "software-dev",
                "slug": MISSION_SLUG,
                "target_branch": "main",
                "vcs": "git",
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    write_lanes_json(
        feature_dir,
        LanesManifest(
            version=1,
            mission_slug=MISSION_SLUG,
            mission_id=f"mission-{MISSION_SLUG}",
            mission_branch=f"kitty/mission-{MISSION_SLUG}",
            target_branch="main",
            lanes=[
                ExecutionLane(
                    lane_id="lane-a",
                    wp_ids=("WP01",),
                    write_scope=("src/**",),
                    predicted_surfaces=("core",),
                    depends_on_lanes=(),
                    parallel_group=0,
                )
            ],
            computed_at="2026-04-28T10:00:00Z",
            computed_from="test",
        ),
    )
    (feature_dir / "tasks.md").write_text(
        "## WP01 Test\n\n- [x] T001 Placeholder task\n", encoding="utf-8"
    )
    _write_cli_wp(tasks_dir / f"{WP_SLUG}.md")

    # Drive event log: planned -> claimed -> in_progress -> for_review.
    append_event(
        feature_dir,
        _make_event(
            event_id="01TEST00000000000000000001",
            from_lane=Lane.PLANNED,
            to_lane=Lane.CLAIMED,
        ),
    )
    append_event(
        feature_dir,
        _make_event(
            event_id="01TEST00000000000000000002",
            from_lane=Lane.CLAIMED,
            to_lane=Lane.IN_PROGRESS,
        ),
    )
    append_event(
        feature_dir,
        _make_event(
            event_id="01TEST00000000000000000003",
            from_lane=Lane.IN_PROGRESS,
            to_lane=Lane.FOR_REVIEW,
        ),
    )

    workspace = repo / ".worktrees" / f"{MISSION_SLUG}-lane-a"
    workspace.mkdir(parents=True)

    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "seed for-review fixture"],
        cwd=repo,
        check=True,
        capture_output=True,
    )

    sub_artifact_dir = feature_dir / "tasks" / WP_SLUG

    monkeypatch.chdir(repo)
    return repo, feature_dir, sub_artifact_dir


def _trigger_rejection(repo: Path, body: str) -> Path:
    """Drive the canonical rejection handler exactly once.

    Mirrors what ``spec-kitty agent tasks move-task WP01 --to planned
    --review-feedback-file <path>`` does internally — calls
    ``_persist_review_feedback`` which writes ``review-cycle-N.md`` and
    returns the persisted path.
    """
    from specify_cli.cli.commands.agent.tasks import _persist_review_feedback

    feedback_file = repo / f"feedback_{abs(hash(body))}.md"
    feedback_file.write_text(body, encoding="utf-8")

    persisted: Path
    persisted, _pointer = _persist_review_feedback(
        main_repo_root=repo,
        mission_slug=MISSION_SLUG,
        task_id="WP01",
        feedback_source=feedback_file,
        reviewer_agent="claude",
    )
    return persisted


def test_approving_a_rejected_wp_writes_no_verdict_artifact(
    for_review_repo: tuple[Path, Path, Path],
) -> None:
    """Pin #2996(a): once a WP has EVER been rejected, no normal
    ``move-task --to approved`` invocation can ever record an approval
    verdict artifact -- even after the WP has been fully reworked and
    resubmitted through claimed -> in_progress -> for_review -> in_review.

    Root cause (traced against ``main`` @ upstream/main): the rejected-verdict
    guard (``_guard_rejected_verdict``,
    ``src/specify_cli/cli/commands/agent/tasks_transition_core.py:364-388``)
    reads the WP's *latest* ``review-cycle-N.md`` verdict regardless of how
    many times the WP has since re-entered ``for_review``/``in_review`` --
    there is no notion of "this rejection was already acted upon by a
    subsequent resubmission". Every approve attempt after any rejection ever
    recorded is refused unless the caller passes
    ``--skip-review-artifact-check --note ...``. The guard's OWN override arm
    is not the fix either: ``_authorize_review_override`` computes ``True``
    and is stamped onto ``Emit.authorize_review_override``
    (``tasks_transition_core.py:173,391-399,664``), but that field is never
    read anywhere in ``tasks_move_task.py`` -- contrast with sibling ``Emit``
    fields ``planned_rollback``/``arbiter_forward``/``done_override_note``/
    ``skip_primary``, which ARE consumed there. No code path -- override flags
    or not -- ever writes a new ``review-cycle-N.md`` with ``verdict:
    approved``. ``ReviewCycleArtifact.write()``
    (``src/specify_cli/review/artifacts.py:199``) has exactly one caller,
    ``create_rejected_review_cycle`` (``src/specify_cli/review/cycle.py:320``),
    which hardcodes ``verdict="rejected"``.

    This test drives the full, well-behaved lifecycle a reviewer would
    actually use -- reject once, then rework and resubmit for a SECOND
    genuine review -- and shows that a plain
    ``move-task WP01 --to approved --agent reviewer-renata --note ...
    --no-auto-commit`` (no ``--skip-review-artifact-check``, no ``--force``)
    is refused, and no fresh ``review-cycle-N.md`` is ever created to
    represent the eventual approval.

    Contract pinned here (per #2996 step 4 -- "a new review-cycle-(N+1).md
    is written with verdict: approved, a real reviewer_agent, and the actual
    affected files / repro command"): the caller *declares* its identity via
    ``--agent`` (a real, documented option -- see
    ``src/specify_cli/cli/commands/agent/tasks.py:610``), and the recorded
    artifact must echo that declared identity plus reviewer-authored body
    content. This is deliberately NOT ``reviewer_agent != "unknown"`` on an
    invocation that declares no reviewer -- that phrasing is satisfiable by
    *inferring* an identity from ambient state, which is the exact
    provenance-fabrication pathology #2996(b) pins against elsewhere (a
    ``review-cycle-2.md`` written with ``reviewer_agent: unknown`` and a body
    byte-identical to cycle 1's, authored by nobody). Requiring the artifact
    to echo a caller-declared identity, plus carry non-empty reviewer content,
    closes off the cheapest satisfying "fix" -- synthesizing an empty
    approval artifact with an inferred reviewer -- without licensing either
    half of #2996's pathology.

    Beware the false green this test replaces coverage for:
    ``tests/post_merge/test_review_artifact_consistency.py:214`` passes today
    because its fixture (``_write_review_artifact``) calls
    ``ReviewCycleArtifact(..., verdict="approved").write(...)`` directly,
    substituting for the exact production step (a real ``move-task --to
    approved`` writing an approved verdict artifact) that this defect
    removes. That test proves the POST-MERGE AUDIT gate exists; it does not
    prove any live path can produce the artifact the audit expects to find.
    """
    from specify_cli.cli.commands.agent import tasks as agent_tasks
    from specify_cli.review.artifacts import ReviewCycleArtifact

    repo, feature_dir, sub_artifact_dir = for_review_repo

    # WP starts at for_review (fixture). Move it into in_review for the FIRST
    # (real) review round.
    append_event(
        feature_dir,
        _make_event(
            event_id="01TEST00000000000000000004",
            from_lane=Lane.FOR_REVIEW,
            to_lane=Lane.IN_REVIEW,
        ),
    )

    # Reviewer rejects cycle 1.
    persisted = _trigger_rejection(repo, "## Cycle 1 issues\n\nFix the off-by-one.")
    assert persisted.name == "review-cycle-1.md"
    latest_after_rejection = ReviewCycleArtifact.latest(sub_artifact_dir)
    assert latest_after_rejection is not None
    assert latest_after_rejection.verdict == "rejected"

    # Drive the WP back through the FULL lifecycle after the rejection --
    # in_review -> planned (rejected) -> claimed -> in_progress -> for_review
    # -> in_review -- exactly as a real implementer reworking and
    # resubmitting the WP for a genuine second review round would.
    append_event(
        feature_dir,
        _make_event(
            event_id="01TEST00000000000000000005",
            from_lane=Lane.IN_REVIEW,
            to_lane=Lane.PLANNED,
        ),
    )
    append_event(
        feature_dir,
        _make_event(
            event_id="01TEST00000000000000000006",
            from_lane=Lane.PLANNED,
            to_lane=Lane.CLAIMED,
        ),
    )
    append_event(
        feature_dir,
        _make_event(
            event_id="01TEST00000000000000000007",
            from_lane=Lane.CLAIMED,
            to_lane=Lane.IN_PROGRESS,
        ),
    )
    append_event(
        feature_dir,
        _make_event(
            event_id="01TEST00000000000000000008",
            from_lane=Lane.IN_PROGRESS,
            to_lane=Lane.FOR_REVIEW,
        ),
    )
    append_event(
        feature_dir,
        _make_event(
            event_id="01TEST00000000000000000009",
            from_lane=Lane.FOR_REVIEW,
            to_lane=Lane.IN_REVIEW,
        ),
    )

    # The reviewer is now satisfied and approves -- a plain approve, with NO
    # override flags, and a caller-declared reviewer identity via --agent
    # (the real option the CLI already exposes -- see
    # src/specify_cli/cli/commands/agent/tasks.py:610).
    reviewer_identity = "reviewer-renata"
    runner = CliRunner()
    result = runner.invoke(
        agent_tasks.app,
        [
            "move-task",
            "WP01",
            "--to",
            "approved",
            "--mission",
            MISSION_SLUG,
            "--agent",
            reviewer_identity,
            "--note",
            "Approving after fixes were verified in the resubmitted review cycle.",
            "--no-auto-commit",
        ],
    )

    # Assert artifact FIRST (names the missing producer, not the guard).
    latest = ReviewCycleArtifact.latest(sub_artifact_dir)
    assert latest is not None, (
        "expected a fresh review-cycle-N.md verdict artifact to exist after "
        f"the approve attempt; none was created. CLI stdout:\n{result.stdout}"
    )
    # Number-agnostic per #2996: the highest-numbered artifact must be the
    # approval, not necessarily cycle 2 specifically -- next_cycle_number is
    # len(glob) + 1 (a known double-increment source; see
    # src/specify_cli/review/artifacts.py), so a correct fix could legitimately
    # land the approval at cycle 3. What matters is that a NEW cycle was
    # written rather than the stale rejected cycle 1 being reused.
    assert latest.cycle_number > 1, (
        f"expected a fresh cycle number above the rejected cycle 1, got "
        f"{latest.cycle_number} -- the stale rejected cycle 1 is still "
        f"'latest'. CLI stdout:\n{result.stdout}"
    )
    assert latest.verdict == "approved", (
        f"expected the latest review-cycle artifact's verdict to be "
        f"'approved', got {latest.verdict!r}. CLI stdout:\n{result.stdout}"
    )
    # The artifact must echo the identity the CALLER declared -- not an
    # identity inferred from ambient state. An invocation that declares no
    # reviewer cannot honestly satisfy this; requiring the declared identity
    # to be echoed keeps the contract satisfiable without inference.
    assert latest.reviewer_agent == reviewer_identity, (
        f"expected the approval artifact to echo the declared --agent "
        f"identity {reviewer_identity!r}, got {latest.reviewer_agent!r}. "
        f"CLI stdout:\n{result.stdout}"
    )
    # Reviewer-authored content, not a synthesized empty shell: a fix that
    # fabricates an approval artifact with an empty body would satisfy every
    # assertion above but must not satisfy this one.
    assert latest.body.strip(), (
        "expected the approval artifact to carry non-empty reviewer-authored "
        f"body content, got an empty body. CLI stdout:\n{result.stdout}"
    )

    assert result.exit_code == 0, (
        f"expected the well-behaved reworked-and-resubmitted approve to "
        f"succeed; got exit code {result.exit_code}. CLI stdout:\n{result.stdout}"
    )
