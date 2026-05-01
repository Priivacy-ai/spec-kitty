"""Integration test for allocation-failure status handling.

Asserts that the implement runtime no longer records implementation start before
workspace allocation succeeds. If allocation fails, the WP is moved directly to
``blocked`` with ``reason=worktree_alloc_failed`` so there is no stranded
``claimed`` state.

The test mocks ``create_lane_workspace`` to raise an OSError on first
call and inspects ``status.events.jsonl`` to verify the event order.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import typer

from specify_cli.cli.commands.implement import implement
from specify_cli.lanes.models import ExecutionLane, LanesManifest
from specify_cli.lanes.persistence import write_lanes_json

pytestmark = pytest.mark.integration


@pytest.fixture(autouse=True)
def _disable_status_side_effects(monkeypatch: pytest.MonkeyPatch) -> None:
    import specify_cli.status.emit as status_emit

    monkeypatch.setattr(status_emit, "_saas_fan_out", lambda *args, **kwargs: None)
    monkeypatch.setattr(status_emit, "fire_dossier_sync", lambda *args, **kwargs: None)


def _create_meta(feature_dir: Path) -> Path:
    feature_dir.mkdir(parents=True, exist_ok=True)
    meta_path = feature_dir / "meta.json"
    meta_path.write_text(
        json.dumps(
            {
                "feature_number": feature_dir.name.split("-")[0],
                "mission_slug": feature_dir.name,
                "created_at": "2026-04-26T00:00:00Z",
                "friendly_name": feature_dir.name,
                "mission": "software-dev",
                "slug": feature_dir.name,
                "target_branch": "main",
                "vcs": "git",
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return meta_path


def _create_lanes(feature_dir: Path) -> None:
    write_lanes_json(
        feature_dir,
        LanesManifest(
            version=1,
            mission_slug=feature_dir.name,
            mission_id=f"mission-{feature_dir.name}",
            mission_branch=f"kitty/mission-{feature_dir.name}",
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
            computed_at="2026-04-26T10:00:00Z",
            computed_from="test",
        ),
    )


def _write_wp_file(feature_dir: Path) -> Path:
    wp_file = feature_dir / "tasks" / "WP01-fixture.md"
    wp_file.parent.mkdir(parents=True, exist_ok=True)
    wp_file.write_text(
        "---\n"
        "work_package_id: WP01\n"
        "dependencies: []\n"
        "execution_mode: code_change\n"
        "owned_files:\n  - src/wp01/**\n"
        "authoritative_surface: src/wp01/\n"
        "---\n# WP01\n",
        encoding="utf-8",
    )
    return wp_file


def test_implement_blocks_without_claiming_when_alloc_fails(
    tmp_path: Path,
) -> None:
    feature_slug = "010-alloc-failure-fixture"
    feature_dir = tmp_path / "kitty-specs" / feature_slug
    _create_meta(feature_dir)
    _create_lanes(feature_dir)
    _write_wp_file(feature_dir)

    events_log = feature_dir / "status.events.jsonl"
    assert not events_log.exists()

    with (
        patch(
            "specify_cli.cli.commands.implement.find_repo_root",
            return_value=tmp_path,
        ),
        patch(
            "specify_cli.cli.commands.implement.detect_feature_context",
            return_value=("010", feature_slug),
        ),
        patch(
            "specify_cli.cli.commands.implement.resolve_feature_target_branch",
            return_value="main",
        ),
        patch(
            "specify_cli.cli.commands.implement._ensure_planning_artifacts_committed_git",
        ),
        patch(
            "specify_cli.cli.commands.implement._ensure_vcs_in_meta",
        ) as mock_ensure_vcs,
        patch(
            "specify_cli.cli.commands.implement.create_lane_workspace",
            side_effect=OSError("simulated worktree allocation failure"),
        ) as mock_alloc,
    ):
        mock_ensure_vcs.return_value = MagicMock(value="git")

        with pytest.raises(typer.Exit):
            implement("WP01", feature=feature_slug, recover=False)

        # Confirm the allocator was actually invoked.
        assert mock_alloc.called

    assert events_log.exists(), "status.events.jsonl must exist after alloc failure status emit"

    events = [
        json.loads(line)
        for line in events_log.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    transitions = [(e["from_lane"], e["to_lane"]) for e in events]

    # Allocation failure should not leave an implementation claim behind.
    assert transitions == [("planned", "blocked")]

    blocked_event = events[0]
    assert blocked_event["reason"] == "worktree_alloc_failed"
    # Evidence may live under policy_metadata; either a plain "evidence"
    # string or a structured map containing one is acceptable.
    policy_meta = blocked_event.get("policy_metadata") or {}
    raw_evidence = policy_meta.get("evidence")
    assert raw_evidence and "simulated worktree allocation failure" in str(raw_evidence)
