"""Regression (#2646 / FR-003): verify #2646 closes via WP01's writer alone.

GitHub issue #2646 reports that an approved WP can still display a stale
``rejected`` warning in ``agent tasks status`` for ``lanes_with_coord``
missions. A post-plan adversarial squad found live evidence that #2646
reproduces today only because WP01's durable, provenance-guarded
review-cycle writer (``create_rejected_review_cycle`` with the ``verdict``
parameter, the coord/primary write-home fix, and the relaxed
``_guard_rejected_verdict`` guard that lets an ordinary approval persist a
real ``verdict: approved`` artifact) did not exist yet — NOT because of a
live coord/primary read-authority split (that split appears already closed
by an earlier, separately-merged placement-seam-unification mission).

This module is a **verify-first** regression test (WP02 of
review-verdict-write-integrity-01KZ1CGF): it drives the REAL shipped writer
(no stub, no monkeypatched artifact write) through reject -> approve for a
``lanes_with_coord`` mission fixture and asserts ``show_kanban_status`` (the
function backing ``agent tasks status --json``) reports the WP approved with
NO stale-verdict warning, with ZERO changes to
``src/specify_cli/agent_utils/status.py``.

The originally-planned fix (routing ``agent_utils/status.py`` through
``resolve_snapshot_review``/``latest_review_artifact_verdict``) was RETRACTED
during this mission: ``ReviewOverride`` carries no ``verdict`` field, so that
design is type-shape broken. This module's job is to prove empirically
whether any fix is needed at all, not to implement the retracted design.

T009 result: PASS -- ``show_kanban_status`` reports WP01 approved with
``stale_verdicts == []`` for the coord-topology fixture, using WP01's real
writer end-to-end (write -> commit -> reduce -> read). ``_get_wp_review_verdict``
reads ``review-cycle-N.md`` straight from the PRIMARY ``tasks/<wp>/`` dir
(``show_kanban_status``'s ``tasks_dir`` always resolves to the PRIMARY
partition via the ``WORK_PACKAGE_TASK`` kind, for BOTH coord and flat
topologies) -- there is no coord-husk read leg for this scan at all, so the
originally-suspected coord/primary split was never reachable from this code
path. ``src/specify_cli/agent_utils/status.py`` has ZERO changes in this WP
(see ``git log --oneline -- src/specify_cli/agent_utils/status.py`` on this
WP's commits). T010 does NOT activate.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from specify_cli.agent_tasks_ports import RealCoordCommitRouter
from specify_cli.agent_utils.status import show_kanban_status
from specify_cli.review.cycle import create_rejected_review_cycle
from specify_cli.status.models import Lane, StatusEvent
from specify_cli.status.store import append_event

from tests.integration.coord_topology_fixture import (
    CoordTopologyContext,
    FlatTopologyContext,
)

# ``coord_topology_mission`` / ``flat_topology_mission`` are consumed as pytest
# fixtures (parameter name injection) via ``tests/regression/conftest.py``'s
# re-export -- importing the fixture functions directly into this module too
# would shadow the same-named test parameters (ruff F811), the same reason
# ``tests/acceptance/conftest.py`` exists.

pytestmark = [pytest.mark.regression, pytest.mark.integration, pytest.mark.git_repo]

# ``coord_topology_fixture`` writes the WP01 task file as ``tasks/WP01.md``
# (no per-WP kebab suffix), so its stem -- and therefore the
# ``artifact_dir``/``wp_slug`` that both the writer and the reader key off of
# -- is the bare WP id.
_WP_ID = "WP01"
_WP_SLUG = "WP01"


# ---------------------------------------------------------------------------
# Shared drive helpers
# ---------------------------------------------------------------------------


def _unprotect_main(repo: Path) -> None:
    """Disable branch protection so WP01's real commit step actually lands.

    Mirrors ``tests/review/test_cycle.py::_unprotect_main`` /
    ``tests/coordination/test_analysis_report_rehome.py``'s
    ``_disable_branch_protection`` idiom: the fixture repo carries no
    ``.kittify/config.yaml``, so ``ProtectionPolicy.resolve`` defaults to
    protecting ``{main, master}`` -- writing an explicit empty
    ``protected_branches: []`` list opts this test repo out.
    """
    kittify_dir = repo / ".kittify"
    kittify_dir.mkdir(parents=True, exist_ok=True)
    (kittify_dir / "config.yaml").write_text(
        "protection:\n  protected_branches: []\n", encoding="utf-8"
    )
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "test: unprotect main"],
        cwd=repo,
        check=True,
        capture_output=True,
    )


def _drive_reject_then_approve(repo: Path, mission_slug: str, tmp_path: Path) -> None:
    """Drive WP01's REAL writer once rejected, once approved (T008).

    Uses ``create_rejected_review_cycle`` directly (per the WP prompt: this
    mirrors this mission's own earlier live reproduction more closely than
    fabricating a full ``planned -> ... -> in_review`` lane-transition history
    to drive the CLI ``move-task`` path) with a REAL ``RealCoordCommitRouter``
    so both cycle artifacts are actually git-committed (WP01's own acceptance
    criteria), not merely written to disk.
    """
    _unprotect_main(repo)

    rejection_feedback = tmp_path / "rejection-feedback.md"
    rejection_feedback.write_text(
        "**Issue**: Missing regression coverage for the stale-verdict path.\n",
        encoding="utf-8",
    )
    rejected = create_rejected_review_cycle(
        main_repo_root=repo,
        mission_slug=mission_slug,
        wp_id=_WP_ID,
        wp_slug=_WP_SLUG,
        feedback_source=rejection_feedback,
        reviewer_agent="reviewer-renata",
        commit_router=RealCoordCommitRouter(),
    )
    assert rejected.artifact.verdict == "rejected"

    approval_feedback = tmp_path / "approval-feedback.md"
    approval_feedback.write_text(
        "Approved by reviewer-renata: the missing coverage was added.\n",
        encoding="utf-8",
    )
    approved = create_rejected_review_cycle(
        main_repo_root=repo,
        mission_slug=mission_slug,
        wp_id=_WP_ID,
        wp_slug=_WP_SLUG,
        feedback_source=approval_feedback,
        reviewer_agent="reviewer-renata",
        verdict="approved",
        commit_router=RealCoordCommitRouter(),
    )
    assert approved.artifact.verdict == "approved"
    assert approved.artifact.cycle_number == 2

    # T008 step 3: confirm review-cycle-2.md exists, carries verdict: approved,
    # and is actually committed (not merely written).
    assert approved.artifact_path.exists()
    assert approved.artifact_path.name == "review-cycle-2.md"
    assert "verdict: approved" in approved.artifact_path.read_text(encoding="utf-8")

    status = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )
    rel = str(approved.artifact_path.relative_to(repo))
    assert rel not in status.stdout, (
        "review-cycle-2.md is NOT committed -- git status still shows it:\n"
        f"{status.stdout}"
    )


def _append_status_event(feature_dir: Path, mission_slug: str, mission_id: str, *, event_id: str) -> None:
    """Append a ``for_review -> approved`` transition event for WP01.

    ``reduce()`` replays events without validating transition legality (it is
    a pure fold, not a state-machine gate), so a single terminal-lane event is
    sufficient to bring the WP into the ``approved`` lane for this scan --
    matching how ``tests/regression/test_2684_review_override_recognition.py``
    seeds its own terminal-lane fixture.
    """
    event = StatusEvent(
        event_id=event_id,
        mission_slug=mission_slug,
        mission_id=mission_id,
        wp_id=_WP_ID,
        from_lane=Lane.FOR_REVIEW,
        to_lane=Lane.APPROVED,
        at="2026-08-02T12:00:00+00:00",
        actor="reviewer-renata",
        force=False,
        execution_mode="worktree",
        reason="approved after reject->approve review cycle",
    )
    append_event(feature_dir, event)


# ---------------------------------------------------------------------------
# T009: the load-bearing verification -- coord topology (#2646's exact shape)
# ---------------------------------------------------------------------------


def test_2646_coord_topology_approved_wp_has_no_stale_verdict_warning(
    coord_topology_mission: CoordTopologyContext,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """#2646's exact reported scenario: lanes_with_coord, reject -> approve.

    Drives WP01's real shipped writer (no stub) through reject then approve,
    brings the WP to the ``approved`` lane via a real status event on the
    AUTHORITATIVE coord-husk event log, then asserts
    ``show_kanban_status`` -- the function backing ``agent tasks status
    --json`` -- reports the WP approved with NO stale-verdict warning.
    """
    ctx = coord_topology_mission

    _drive_reject_then_approve(ctx.repo, ctx.slug, tmp_path)
    _append_status_event(
        ctx.coord_feature_dir,
        ctx.slug,
        ctx.mission_id,
        event_id="01KW2E7A0FR001APPROVEEVT01",
    )

    monkeypatch.chdir(ctx.repo)
    monkeypatch.setattr(
        "specify_cli.agent_utils.status.locate_project_root", lambda cwd: ctx.repo
    )
    monkeypatch.setattr(
        "specify_cli.agent_utils.status.get_main_repo_root", lambda repo_root: ctx.repo
    )
    monkeypatch.setattr(
        "specify_cli.agent_utils.status.get_status_read_root", lambda: ctx.repo
    )

    result = show_kanban_status(ctx.slug)

    assert "error" not in result, result
    wp01 = next(wp for wp in result["work_packages"] if wp["id"] == _WP_ID)
    assert wp01["lane"] == Lane.APPROVED
    assert not wp01.get("_stale_verdict"), (
        "T009 FAIL: WP01 still carries a stale-verdict marker after reject->"
        f"approve via WP01's real writer. work_package entry: {wp01!r}"
    )
    assert result["stale_verdicts"] == [], (
        "T009 FAIL: show_kanban_status reported a stale verdict for an "
        f"approved WP after WP01's writer ran: {result['stale_verdicts']!r}"
    )


# ---------------------------------------------------------------------------
# Flat/single-branch neutrality control (spec.md User Story 3, Scenario 3)
# ---------------------------------------------------------------------------


def test_2646_flat_topology_approved_wp_has_no_stale_verdict_warning(
    flat_topology_mission: FlatTopologyContext,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Neutrality control: the flat/single-branch case behaves identically.

    This WP investigates only the coord-topology leg of #2646, but the fix
    (or, here, the confirmed absence of one) must not regress the pre-mission
    flat-topology baseline (spec.md User Story 3, Acceptance Scenario 3).
    """
    ctx = flat_topology_mission

    _drive_reject_then_approve(ctx.repo, ctx.slug, tmp_path)
    _append_status_event(
        ctx.primary_feature_dir,
        ctx.slug,
        ctx.mission_id,
        event_id="01KW2E7B0FR001APPROVEEVT01",
    )

    monkeypatch.chdir(ctx.repo)
    monkeypatch.setattr(
        "specify_cli.agent_utils.status.locate_project_root", lambda cwd: ctx.repo
    )
    monkeypatch.setattr(
        "specify_cli.agent_utils.status.get_main_repo_root", lambda repo_root: ctx.repo
    )
    monkeypatch.setattr(
        "specify_cli.agent_utils.status.get_status_read_root", lambda: ctx.repo
    )

    result = show_kanban_status(ctx.slug)

    assert "error" not in result, result
    wp01 = next(wp for wp in result["work_packages"] if wp["id"] == _WP_ID)
    assert wp01["lane"] == Lane.APPROVED
    assert not wp01.get("_stale_verdict")
    assert result["stale_verdicts"] == []
