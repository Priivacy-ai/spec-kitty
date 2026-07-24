"""Two-partition consolidation-readiness preview (WP07, FR-006 / SC-002 / #2885).

The review-artifact consistency gate needs two facts that live in two different
partitions of a coord-topology mission:

* a WP's **lane state** — ``STATUS_STATE``, authoritative on the coordination
  husk's ``status.events.jsonl``; and
* its **review-cycle artifacts** — ``WORK_PACKAGE_TASK``, PRIMARY-partition,
  tracked under ``kitty-specs/<slug>/tasks/<wp>/`` on the primary checkout.

Before the fix, ``find_rejected_review_artifact_conflicts`` judged BOTH off a
single caller-supplied directory. Whichever surface it was handed was correct
for at most one fact and empty (or a stale stray) for the other — so the dry-run
preview (handed the PRIMARY dir) read an empty status log, every WP looked
stateless, and it passed a rejected review by default, while the real
consolidation (handed the coord husk) refused. Preview and consolidation
disagreed (#2885). The gate now resolves each fact from its own declared home,
so both callers resolve the same two surfaces and AGREE (SC-002).

Test harvest & attribution (mission constraint C-007)
-----------------------------------------------------
The two coord-topology scenarios below — a genuine terminal-WP rejection that
MUST be caught, and a stale stray review-cycle file on the coordination husk that
MUST NOT shadow the real tracked artifact on PRIMARY — are harvested from the
kept-for-reference pull request **#2834** by **@rayjohnson** (Ray Johnson),
"fix(merge): split lane-state and review-cycle reads to their real partitions".
They are reproduced here rather than rewritten from scratch, and adapted to this
mission's signature-preserving API (the gate re-resolves both partitions from the
mission identity internally, so a caller may hand it EITHER surface). The SC-002
agreement assertion — that the preview leg and the real-consolidation leg return
the identical verdict — is added on top of @rayjohnson's originals.
"""

from __future__ import annotations

import pytest

from tests.integration.coord_topology_fixture import (  # noqa: F401
    CoordTopologyContext,
    coord_topology_mission,
)

# Re-export the fixture so pytest discovers it in this module.
__all__ = ["coord_topology_mission"]

# New git-shelling integration file (C-006): the coord fixture drives real git.
pytestmark = [pytest.mark.integration, pytest.mark.git_repo]


def _seed_terminal_wp01(ctx: CoordTopologyContext, *, event_id: str) -> None:
    """Drive WP01 to a terminal (approved) lane on the REAL coord-husk status log.

    The fixture pre-seeds a raw-text marker line (a wrong-leg probe) that is not a
    schema-valid ``StatusEvent`` and is never meant to survive ``materialize`` — so
    replace it with a real, well-formed terminal transition and exercise production
    materialization end to end. (Idiom harvested from @rayjohnson's PR #2834.)
    """
    from specify_cli.status.models import Lane, StatusEvent
    from specify_cli.status.store import append_event

    ctx.status_events_path.write_text("", encoding="utf-8")
    append_event(
        ctx.coord_feature_dir,
        StatusEvent(
            event_id=event_id,
            mission_slug=ctx.slug,
            mission_id=ctx.mission_id,
            wp_id="WP01",
            from_lane=Lane.FOR_REVIEW,
            to_lane=Lane.APPROVED,
            at="2026-06-26T01:00:00+00:00",
            actor="reviewer-renata",
            force=False,
            execution_mode="worktree",
            reason="approved for merge",
        ),
    )


def _write_review_cycle(
    ctx: CoordTopologyContext,
    *,
    base_dir,
    verdict: str,
    reviewed_at: str,
    body: str,
) -> None:
    """Write a review-cycle-1 artifact for WP01 under ``base_dir/tasks/WP01-fixture``."""
    from specify_cli.review.artifacts import ReviewCycleArtifact

    ReviewCycleArtifact(
        cycle_number=1,
        wp_id="WP01",
        mission_slug=ctx.slug,
        reviewer_agent="reviewer-renata",
        verdict=verdict,
        reviewed_at=reviewed_at,
        body=body,
    ).write(base_dir / "tasks" / "WP01-fixture" / "review-cycle-1.md")


def test_review_artifact_gate_catches_genuine_rejection_on_coord_topology(
    coord_topology_mission: CoordTopologyContext,
) -> None:
    """A genuinely-rejected review-cycle artifact on a terminal WP is caught (US2.1).

    Harvested from @rayjohnson's PR #2834. Requires BOTH partitions to resolve
    correctly at once: the WP's lane (terminal) must come from the coord husk's real
    status log (``STATUS_STATE``), and the review-cycle verdict from the PRIMARY
    checkout (``WORK_PACKAGE_TASK``). Reading lane state from PRIMARY (no
    authoritative status log there for a coord mission) never reaches a terminal
    lane; reading the review-cycle from the coord husk finds no ``tasks/`` dir at all
    — either wrong leg makes this silently find nothing.
    """
    from specify_cli.post_merge.review_artifact_consistency import (
        find_rejected_review_artifact_conflicts,
    )

    ctx = coord_topology_mission
    _seed_terminal_wp01(ctx, event_id="01KW2E7A0TERMINAL00000001")
    _write_review_cycle(
        ctx,
        base_dir=ctx.primary_feature_dir,
        verdict="rejected",
        reviewed_at="2026-06-26T00:30:00+00:00",
        body="# Review\n\nVerdict: rejected.\n",
    )

    findings = find_rejected_review_artifact_conflicts(ctx.primary_feature_dir, ["WP01"])

    assert len(findings) == 1, (
        "Expected the genuine rejection to be caught. An empty result means either "
        "the lane read missed the coord husk's terminal status, or the review-cycle "
        f"read missed the PRIMARY checkout's tracked artifact. Got: {findings}"
    )
    assert findings[0].wp_id == "WP01"
    assert findings[0].verdict == "rejected"


def test_review_artifact_gate_ignores_stray_artifact_on_coord_husk(
    coord_topology_mission: CoordTopologyContext,
) -> None:
    """A stray husk review-cycle must not shadow PRIMARY's real content (US2.2).

    Harvested from @rayjohnson's PR #2834 (field-report regression). The
    coordination worktree carries a STALE rejected review-cycle artifact, as if
    left over from an earlier cycle never forwarded there; the PRIMARY checkout
    carries the real, correct APPROVED artifact. WP01's lane (approved) is read from
    the coord husk's real status log. Before the fix, review-cycle content was ALSO
    read from the husk, so the stale rejected artifact falsely blocked an
    already-approved WP. After the fix, review-cycle content resolves to PRIMARY
    (``WORK_PACKAGE_TASK``) — the husk's stray copy is never opened — so a stale
    leftover review file does NOT cause a false not-ready (SC-002 / US2.2).
    """
    from specify_cli.post_merge.review_artifact_consistency import (
        find_rejected_review_artifact_conflicts,
    )

    ctx = coord_topology_mission
    _seed_terminal_wp01(ctx, event_id="01KW2E7A0TERMINAL00000002")
    # The real, correct artifact on PRIMARY: approved.
    _write_review_cycle(
        ctx,
        base_dir=ctx.primary_feature_dir,
        verdict="approved",
        reviewed_at="2026-06-26T00:30:00+00:00",
        body="# Review\n\nVerdict: approved.\n",
    )
    # A stale, stray artifact on the COORD HUSK: rejected. Must never be read.
    _write_review_cycle(
        ctx,
        base_dir=ctx.coord_feature_dir,
        verdict="rejected",
        reviewed_at="2026-06-25T00:00:00+00:00",
        body="# Review\n\nVerdict: rejected (stale, never forwarded).\n",
    )

    findings = find_rejected_review_artifact_conflicts(ctx.primary_feature_dir, ["WP01"])

    assert findings == [], (
        "The coord husk's stray rejected artifact must not shadow PRIMARY's real "
        f"approved one — a stale leftover must not cause a false not-ready. Got: {findings}"
    )


def test_preview_and_consolidation_agree_on_rejected_review_case(
    coord_topology_mission: CoordTopologyContext,
) -> None:
    """SC-002: preview and real consolidation AGREE on the case that once disagreed.

    This is the #2885 reproduction turned into a regression. The dry-run preview
    hands the gate the PRIMARY mission dir (see ``forecast.py`` —
    ``feature_dir_for_preview`` is the ``WORK_PACKAGE_TASK`` surface); the real
    consolidation hands it the coordination husk (see ``executor.py`` — the STATUS
    leg's ``feature_dir``). Before the split those two inputs produced DIFFERENT
    verdicts on a genuinely-rejected terminal WP: preview said ready, consolidation
    refused. After the split, each input re-resolves both partitions from the
    mission identity, so the two legs return the IDENTICAL finding.
    """
    from specify_cli.post_merge.review_artifact_consistency import (
        find_rejected_review_artifact_conflicts,
    )

    ctx = coord_topology_mission
    _seed_terminal_wp01(ctx, event_id="01KW2E7A0TERMINAL00000003")
    _write_review_cycle(
        ctx,
        base_dir=ctx.primary_feature_dir,
        verdict="rejected",
        reviewed_at="2026-06-26T00:30:00+00:00",
        body="# Review\n\nVerdict: rejected.\n",
    )

    # The preview leg (forecast): resolved through the PRIMARY WORK_PACKAGE_TASK dir.
    preview_findings = find_rejected_review_artifact_conflicts(
        ctx.primary_feature_dir, ["WP01"]
    )
    # The real-consolidation leg (executor): the coord-husk STATUS surface.
    consolidation_findings = find_rejected_review_artifact_conflicts(
        ctx.coord_feature_dir, ["WP01"]
    )

    assert preview_findings == consolidation_findings, (
        "SC-002: the preview and the real consolidation must return the identical "
        "verdict on the rejected-review case. They disagreed under #2885 because the "
        "preview read lane state from PRIMARY (empty) while consolidation read the "
        f"coord husk. preview={preview_findings} consolidation={consolidation_findings}"
    )
    # Non-vacuity: both legs actually caught the rejection (not both-empty agreement).
    assert len(preview_findings) == 1
    assert preview_findings[0].wp_id == "WP01"
    assert preview_findings[0].verdict == "rejected"
