"""Regression tests for ``next --json`` claimability parity (issue #988).

Before this fix, ``spec-kitty next --json`` could emit
``mission_state: implement`` with ``wp_id: null`` even though the explicit
``spec-kitty agent action implement`` would auto-claim a concrete WP.
After the fix, the JSON payload exposes the same WP that the explicit
action would claim, or a structured ``selection_reason`` token when no
claim is possible.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from specify_cli.next.decision import DecisionKind
from specify_cli.next.discovery import ClaimablePreview, preview_claimable_wp
from specify_cli.status.models import Lane, StatusEvent
from specify_cli.status.store import append_event
from tests.lane_test_utils import write_single_lane_manifest

pytestmark = pytest.mark.git_repo


def _init_repo(repo: Path) -> None:
    subprocess.run(["git", "init", "-b", "main"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo, check=True, capture_output=True)


def _scaffold(repo: Path, wps: dict[str, Lane]) -> tuple[Path, str]:
    _init_repo(repo)
    (repo / ".kittify").mkdir()
    mission_slug = "claimable-payload-mission-01KRKTT5"
    feature_dir = repo / "kitty-specs" / mission_slug
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir(parents=True)
    (feature_dir / "meta.json").write_text(
        json.dumps(
            {"mission_type": "software-dev", "mission_id": "01KRKTT58XC5KR0HF523333R9S"}
        ),
        encoding="utf-8",
    )
    (feature_dir / "spec.md").write_text("# Spec\n", encoding="utf-8")
    (feature_dir / "plan.md").write_text("# Plan\n", encoding="utf-8")
    (feature_dir / "tasks.md").write_text("# Tasks\n", encoding="utf-8")
    write_single_lane_manifest(feature_dir, wp_ids=tuple(wps.keys()))
    for wp_id, lane in wps.items():
        (tasks_dir / f"{wp_id}.md").write_text(
            f"---\nwork_package_id: {wp_id}\ndependencies: []\ntitle: {wp_id}\n---\n# {wp_id}\n",
            encoding="utf-8",
        )
        append_event(
            feature_dir,
            StatusEvent(
                event_id=f"seed-{wp_id}-{lane}",
                mission_slug=mission_slug,
                wp_id=wp_id,
                from_lane=Lane.PLANNED,
                to_lane=lane,
                at="2026-05-14T12:00:00+00:00",
                actor="fixture",
                force=True,
                execution_mode="worktree",
            ),
        )
    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "seed claimable payload mission"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    return feature_dir, mission_slug


def test_preview_claimable_wp_returns_first_planned_wp(tmp_path: Path) -> None:
    """The discovery helper mirrors ``_find_first_planned_wp`` candidate selection."""
    repo = tmp_path / "repo"
    repo.mkdir()
    feature_dir, _ = _scaffold(repo, {"WP01": Lane.PLANNED, "WP02": Lane.PLANNED})

    preview = preview_claimable_wp(feature_dir)

    assert isinstance(preview, ClaimablePreview)
    assert preview.wp_id == "WP01"
    assert preview.selection_reason is None
    assert preview.candidates == ("WP01", "WP02")


def test_preview_claimable_wp_returns_selection_reason_when_all_in_progress(
    tmp_path: Path,
) -> None:
    """When no WP is planned, the helper emits ``all_wps_in_progress``."""
    repo = tmp_path / "repo"
    repo.mkdir()
    feature_dir, _ = _scaffold(repo, {"WP01": Lane.IN_PROGRESS})

    preview = preview_claimable_wp(feature_dir)

    assert preview.wp_id is None
    assert preview.selection_reason == "all_wps_in_progress"
    assert preview.candidates == ("WP01",)


def test_preview_claimable_wp_handles_missing_tasks_dir(tmp_path: Path) -> None:
    """A feature_dir with no tasks/ returns ``no_tasks_dir`` without raising."""
    feature_dir = tmp_path / "no-tasks-dir"
    feature_dir.mkdir()

    preview = preview_claimable_wp(feature_dir)

    assert preview.wp_id is None
    assert preview.selection_reason == "no_tasks_dir"
    assert preview.candidates == ()


def test_preview_claimable_wp_distinguishes_terminal_from_active(
    tmp_path: Path,
) -> None:
    """All-done missions return ``no_planned_wps``, not ``all_wps_in_progress``.

    Spec correctness: the latter token implies "wait for the active WP to
    finish"; the former implies "this mission is essentially complete from
    the implement-loop's perspective". Conflating the two would mislead
    operators.
    """
    repo = tmp_path / "repo"
    repo.mkdir()
    feature_dir, _ = _scaffold(repo, {"WP01": Lane.DONE, "WP02": Lane.APPROVED})

    preview = preview_claimable_wp(feature_dir)

    assert preview.wp_id is None
    assert preview.selection_reason == "no_planned_wps"
    assert preview.candidates == ("WP01", "WP02")


def test_preview_claimable_wp_uses_frontmatter_id_not_filename(
    tmp_path: Path,
) -> None:
    """WP id source is YAML ``work_package_id``, matching ``_find_first_planned_wp`` (FR-003)."""
    repo = tmp_path / "repo"
    repo.mkdir()
    feature_dir, _ = _scaffold(repo, {"WP01": Lane.PLANNED})

    # Rename the file to a slug-suffixed form (``WP01-foo.md``) and bake a
    # mismatched filename stem to prove the helper reads frontmatter, not filename.
    tasks_dir = feature_dir / "tasks"
    original = tasks_dir / "WP01.md"
    renamed = tasks_dir / "WP01-some-slug.md"
    original.rename(renamed)

    preview = preview_claimable_wp(feature_dir)

    # Discovery must still pick WP01 because the frontmatter says
    # ``work_package_id: WP01``, regardless of the slug-suffixed filename.
    assert preview.wp_id == "WP01"
    assert preview.selection_reason is None
    assert preview.candidates == ("WP01",)


def test_next_json_payload_serializes_claimable_wp_id(tmp_path: Path) -> None:
    """``next --json`` mission_state=implement now serializes the claimable wp_id.

    This is the canonical regression for issue #988: before the fix, this same
    mission state would return ``wp_id: null``; after the fix it returns the
    concrete WP that ``agent action implement`` would auto-claim.
    """
    repo = tmp_path / "repo"
    repo.mkdir()
    _, mission_slug = _scaffold(repo, {"WP01": Lane.PLANNED})

    from specify_cli.next.runtime_bridge import query_current_state

    decision = query_current_state("codex", mission_slug, repo)

    assert decision.kind == DecisionKind.query
    assert decision.mission_state == "implement"
    assert decision.preview_step == "implement"
    assert decision.wp_id == "WP01"

    payload = decision.to_dict()
    assert payload["wp_id"] == "WP01"
    assert payload["mission_state"] == "implement"
    assert payload["preview_step"] == "implement"


def test_next_json_payload_surfaces_selection_reason_when_no_planned_wp(
    tmp_path: Path,
) -> None:
    """When no WP is claimable, the payload's ``reason`` exposes the structured token."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _, mission_slug = _scaffold(repo, {"WP01": Lane.IN_PROGRESS})

    from specify_cli.next.runtime_bridge import query_current_state

    decision = query_current_state("codex", mission_slug, repo)

    assert decision.kind == DecisionKind.query
    assert decision.mission_state == "implement"
    assert decision.preview_step == "implement"
    # No planned WP → wp_id remains None and reason carries the stable token.
    assert decision.wp_id is None
    assert decision.reason == "all_wps_in_progress"


def test_next_json_payload_wire_shape_unchanged_for_non_implement_state(
    tmp_path: Path,
) -> None:
    """Spec C-001: non-implement states keep their existing payload shape (wp_id null)."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _, mission_slug = _scaffold(repo, {"WP01": Lane.FOR_REVIEW})

    from specify_cli.next.runtime_bridge import query_current_state

    decision = query_current_state("codex", mission_slug, repo)

    assert decision.kind == DecisionKind.query
    assert decision.mission_state == "review"
    assert decision.preview_step == "review"
    # For the review state we did NOT introduce wp_id serialization; the
    # existing wire shape (wp_id=None) is preserved.
    assert decision.wp_id is None
