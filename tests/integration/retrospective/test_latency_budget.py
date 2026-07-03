"""WP04 T023 integration — latency budget (NFR-005).

Runs the default facilitator callback against a 4-WP / 30-event mission
and asserts the callback completes in under 2.0 seconds wall-clock.

NFR-005: default-flow callback completion < 2.0s.
NFR-001: aggregate test suite for retrospective under 60s (enforced externally).
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

pytestmark = [pytest.mark.integration]

import ulid as _ulid_mod


def _scaffold_four_wp_mission(tmp_path: Path, mission_slug: str) -> tuple[Path, str]:
    """Create a 4-WP mission with 30 status events for realistic load."""
    mission_id = str(_ulid_mod.ULID())
    feature_dir = tmp_path / "kitty-specs" / mission_slug
    feature_dir.mkdir(parents=True)

    (feature_dir / "meta.json").write_text(
        json.dumps({
            "mission_id": mission_id,
            "mission_slug": mission_slug,
            "mission_type": "software-dev",
            "friendly_name": "Latency Test Mission",
            "mission_number": None,
        }),
        encoding="utf-8",
    )
    (feature_dir / "spec.md").write_text(
        "# Spec\n\n## Functional Requirements\n\n"
        "| ID | Requirement | Acceptance Criteria | Status |\n"
        "| --- | --- | --- | --- |\n"
        + "".join(
            f"| FR-{i:03d} | Requirement {i} | Covered by WP0{(i % 4) + 1}. | proposed |\n"
            for i in range(1, 9)
        ),
        encoding="utf-8",
    )
    (feature_dir / "plan.md").write_text("# Plan\n", encoding="utf-8")
    (feature_dir / "tasks.md").write_text("# Tasks\n", encoding="utf-8")

    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir()
    for i in range(1, 5):
        wp_id = f"WP0{i}"
        refs = ", ".join(f"FR-{j:03d}" for j in range((i - 1) * 2 + 1, (i - 1) * 2 + 3))
        (tasks_dir / f"{wp_id}.md").write_text(
            f"---\nwork_package_id: {wp_id}\nlane: done\ndependencies: []\n"
            f"requirement_refs: [{refs}]\ntitle: {wp_id} Latency Test\n---\n# {wp_id}\n",
            encoding="utf-8",
        )

    # Write 30 status events (simulate a real mission lifecycle).
    events: list[dict] = []
    lanes = ["planned", "claimed", "in_progress", "for_review", "in_review", "approved", "done"]
    for wp_i in range(1, 5):
        wp_id = f"WP0{wp_i}"
        for lane_i in range(len(lanes) - 1):
            events.append({
                "actor": "test-agent",
                "at": f"2026-0{wp_i}-{lane_i + 1:02d}T00:00:00+00:00",
                "event_id": str(_ulid_mod.ULID()),
                "evidence": None,
                "execution_mode": "worktree",
                "feature_slug": mission_slug,
                "force": False,
                "from_lane": lanes[lane_i],
                "reason": None,
                "review_ref": None,
                "to_lane": lanes[lane_i + 1],
                "wp_id": wp_id,
            })
    # Pad to 30 events with extra comment-style events.
    while len(events) < 30:
        events.append({
            "actor": "test-agent",
            "at": "2026-05-01T00:00:00+00:00",
            "event_id": str(_ulid_mod.ULID()),
            "evidence": None,
            "execution_mode": "worktree",
            "feature_slug": mission_slug,
            "force": True,
            "from_lane": "done",
            "reason": "backfill",
            "review_ref": None,
            "to_lane": "done",
            "wp_id": "WP01",
        })

    events_path = feature_dir / "status.events.jsonl"
    events_path.write_text(
        "\n".join(json.dumps(e) for e in events) + "\n",
        encoding="utf-8",
    )
    return feature_dir, mission_id


@pytest.mark.integration
def test_latency_budget_default_flow_under_2s(tmp_path: Path) -> None:
    """Default flow on a 4-WP / 30-event mission completes in < 2.0s.

    NFR-005 assertion. Median of 3 runs used for resilience against
    transient OS scheduler delays.
    """
    from runtime.next.runtime_bridge import _build_retrospective_facilitator_callback

    mission_slug = "latency-budget-01KQ"

    timings: list[float] = []
    for i in range(3):
        # Each run gets a completely isolated directory so records don't collide.
        run_root = tmp_path / f"run-{i}"
        run_root.mkdir()
        run_feature_dir, run_mission_id = _scaffold_four_wp_mission(run_root, mission_slug)
        run_callback = _build_retrospective_facilitator_callback(
            mission_slug=mission_slug,
            repo_root=run_root,
            provenance_kind="runtime_post_completion",
        )
        t0 = time.perf_counter()
        run_callback(
            mission_id=run_mission_id,
            feature_dir=run_feature_dir,
            repo_root=run_root,
        )
        timings.append(time.perf_counter() - t0)

    median_time = sorted(timings)[1]
    assert median_time < 2.0, (
        f"NFR-005 violated: default-flow facilitator callback took {median_time:.3f}s "
        f"(median of 3 runs: {[f'{t:.3f}' for t in timings]}). "
        "Must complete in under 2.0s."
    )
