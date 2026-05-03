from __future__ import annotations

import json
from pathlib import Path

from specify_cli.frontmatter import read_frontmatter
from specify_cli.status.models import Lane

from tests.reliability.fixtures import (
    BranchContext,
    CommandOutput,
    FakeSyncClient,
    ReviewArtifactSpec,
    SharedLaneContext,
    WorkPackageSpec,
    append_status_event,
    assert_json_stdout_parseable,
    assert_prompt_metadata_identity,
    assert_stderr_contains_diagnostic_codes,
    branch_divergence_state,
    concurrent_review_prompt_identities,
    create_mission_fixture,
    materialize_status,
    write_review_artifact,
    write_review_prompt,
    write_shared_lane_context,
    write_work_package,
)


def test_workflow_reliability_fixture_shapes_are_representable(tmp_path: Path) -> None:
    branch_context = BranchContext(
        mission_branch="kitty/mission-release-320-workflow-reliability-01KQKV85",
        lane_branch="kitty/mission-release-320-workflow-reliability-01KQKV85-lane-a",
        base_ref="kitty/mission-release-320-workflow-reliability-01KQKV85",
        lane_worktree=tmp_path / "repo" / ".worktrees" / "lane-a",
    )
    mission = create_mission_fixture(tmp_path, branch_context=branch_context)

    wp01_path = write_work_package(
        mission,
        WorkPackageSpec(
            work_package_id="WP01",
            owned_files=("tests/reliability/**",),
            requirement_refs=("FR-001", "NFR-001"),
            subtasks=("T001", "T002"),
        ),
    )
    wp02_path = write_work_package(
        mission,
        WorkPackageSpec(
            work_package_id="WP02",
            title="Status Transition Atomicity",
            dependencies=("WP01",),
            owned_files=("src/specify_cli/status/**", "tests/status/**"),
            requirement_refs=("FR-001", "FR-002"),
        ),
    )

    wp02_frontmatter, _body = read_frontmatter(wp02_path)
    assert wp02_frontmatter["work_package_id"] == "WP02"
    assert wp02_frontmatter["dependencies"] == ["WP01"]
    assert wp02_frontmatter["owned_files"] == ["src/specify_cli/status/**", "tests/status/**"]

    append_status_event(
        mission,
        work_package_id="WP01",
        from_lane=Lane.PLANNED,
        to_lane=Lane.IN_PROGRESS,
        event_id="01KQKV85STATUS00000000001",
    )
    snapshot = materialize_status(mission)
    assert mission.status_events_path.exists()
    assert mission.status_snapshot_path.exists()
    assert snapshot.work_packages["WP01"]["lane"] == "in_progress"

    review_spec = ReviewArtifactSpec(
        work_package_id="WP01",
        work_package_slug=wp01_path.stem,
        verdict="rejected",
    )
    review_artifact = write_review_artifact(mission, review_spec)
    review_frontmatter, _review_body = read_frontmatter(review_artifact)
    expected_review_path = mission.tasks_dir / "WP01-regression-harness" / "review-cycle-1.md"
    assert review_artifact == expected_review_path
    assert review_artifact.relative_to(mission.mission_dir) == Path(
        "tasks/WP01-regression-harness/review-cycle-1.md"
    )
    assert review_frontmatter["review_ref"] == (
        "review-cycle://release-320-workflow-reliability-01KQKV85/WP01-regression-harness/review-cycle-1.md"
    )
    assert review_frontmatter["verdict"] == "rejected"

    lane_context_path = write_shared_lane_context(
        mission,
        SharedLaneContext(
            lane_id="lane-a",
            active_work_package_id="WP02",
            lane_work_package_ids=("WP01", "WP02"),
            owned_files_by_work_package={
                "WP01": ("tests/reliability/**",),
                "WP02": ("src/specify_cli/status/**", "tests/status/**"),
            },
            lane_worktree=branch_context.lane_worktree,
        ),
    )
    lane_context = json.loads(lane_context_path.read_text(encoding="utf-8"))
    assert lane_context["active_work_package_id"] == "WP02"
    assert lane_context["owned_files_by_work_package"]["WP01"] != lane_context["owned_files_by_work_package"]["WP02"]

    prompt_a, prompt_b = concurrent_review_prompt_identities(tmp_path)
    path_a = write_review_prompt(prompt_a)
    path_b = write_review_prompt(prompt_b)
    assert path_a != path_b
    assert_prompt_metadata_identity(path_a, prompt_a)
    assert_prompt_metadata_identity(path_b, prompt_b)
    assert prompt_a.created_at == prompt_b.created_at
    assert prompt_a.invocation_id == prompt_b.invocation_id

    sync_client = FakeSyncClient.with_lock_shutdown_and_transport_failures()
    output = CommandOutput(
        stdout=json.dumps({"local_success": True, "work_package_id": "WP01"}),
        stderr=sync_client.render_stderr(),
        exit_code=0,
    )
    parsed_stdout = assert_json_stdout_parseable(output)
    assert parsed_stdout["local_success"] is True
    assert_stderr_contains_diagnostic_codes(
        output,
        "SYNC_LOCK_HELD",
        "SYNC_INTERPRETER_SHUTDOWN",
        "SYNC_TRANSPORT_ERROR",
    )

    divergence = branch_divergence_state(mission_owned_files=(str(wp01_path.relative_to(mission.repo_root)),))
    assert divergence.has_diverged
    assert divergence.remediation_branch == "release-320-workflow-reliability-focused-pr"
