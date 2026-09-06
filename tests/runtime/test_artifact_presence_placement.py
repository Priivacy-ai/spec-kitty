"""#3910: guard facts respect PRIMARY planning and coord lifecycle authority."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from mission_runtime import MissionArtifactKind, placement_seam
from runtime.next import runtime_bridge as bridge
from runtime.next import runtime_bridge_composition as composition
from runtime.next.runtime_bridge_io import gather_artifact_presence
from specify_cli.missions._read_path_resolver import coord_feature_dir
from specify_cli.status.models import Lane, StatusEvent
from specify_cli.status.store import append_event

pytestmark = [pytest.mark.unit, pytest.mark.git_repo]

MISSION_ID = "01M1V6E1A1Z8H2Y360MJHVKX5B"
MISSION_SLUG = "guard-placement-01M1V6E1"
PRIMARY_BRANCH = "codex/planning"
COORD_BRANCH = "kitty/mission-guard-placement-01M1V6E1-coord"


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)


def _mission(tmp_path: Path, topology: str = "coord") -> tuple[Path, Path, Path]:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", PRIMARY_BRANCH)
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test")
    _git(repo, "config", "commit.gpgsign", "false")
    (repo / ".kittify").mkdir()
    (repo / ".kittify/config.yaml").write_text("agents:\n  available: [codex]\n", encoding="utf-8")
    primary = repo / "kitty-specs" / MISSION_SLUG
    primary.mkdir(parents=True)
    meta = {
        "mission_id": MISSION_ID,
        "mission_slug": MISSION_SLUG,
        "mission_type": "software-dev",
        "target_branch": PRIMARY_BRANCH,
        "topology": topology,
    }
    if topology in {"coord", "lanes_with_coord"}:
        meta["coordination_branch"] = COORD_BRANCH
    (primary / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
    _git(repo, "add", ".kittify", "kitty-specs")
    _git(repo, "commit", "-qm", "Seed mission identity")
    status = primary
    if "coordination_branch" in meta:
        status = coord_feature_dir(repo, MISSION_SLUG, MISSION_ID[:8])
        coord_root = status.parent.parent
        _git(repo, "worktree", "add", "-q", "-b", COORD_BRANCH, str(coord_root))
    seam = placement_seam(repo, MISSION_SLUG)
    assert seam.read_dir(MissionArtifactKind.SPEC) == primary
    assert seam.read_dir(MissionArtifactKind.STATUS_STATE) == status
    return repo, primary, status


@pytest.mark.parametrize("topology", ["coord", "lanes_with_coord"])
@pytest.mark.parametrize("artifact,step", [("spec.md", "specify"), ("plan.md", "plan")])
@pytest.mark.parametrize("authoritative", [True, False], ids=["primary-only", "coord-decoy"])
def test_split_artifact_guards(
    tmp_path: Path, topology: str, artifact: str, step: str, authoritative: bool
) -> None:
    repo, primary, status = _mission(tmp_path, topology)
    home = primary if authoritative else status
    (home / artifact).write_text("# Planning contract\n\nUse the declared artifact authority.\n", encoding="utf-8")
    _git(home, "add", artifact)
    _git(home, "commit", "-qm", "Record planning input")
    expected = [] if authoritative else [f"Required artifact missing: {artifact}"]

    cli_failures = bridge._check_cli_guards(step, status, mission_family="software-dev", repo_root=repo)
    composed_failures = composition._check_composed_action_guard(step, status, repo_root=repo)
    snapshot = gather_artifact_presence(status, mission_family="software-dev", step_id=step, repo_root=repo)
    assert (cli_failures, composed_failures) == (expected, expected)
    assert (artifact in snapshot.present_artifacts) is authoritative
    assert not ((status if authoritative else primary) / artifact).exists()


@pytest.mark.parametrize("topology", ["single_branch", "lanes"])
def test_non_coord_guard_control(tmp_path: Path, topology: str) -> None:
    repo, primary, status = _mission(tmp_path, topology)
    for artifact, step in [("spec.md", "specify"), ("plan.md", "plan")]:
        (primary / artifact).write_text("# Planning contract\n", encoding="utf-8")
        assert bridge._check_cli_guards(step, status, mission_family="software-dev", repo_root=repo) == []
        assert composition._check_composed_action_guard(step, status, repo_root=repo) == []


def test_planning_tasks_and_coord_lifecycle_facts(tmp_path: Path) -> None:
    repo, primary, status = _mission(tmp_path)
    tasks = primary / "tasks"
    tasks.mkdir()
    (tasks / "WP01-guard.md").write_text(
        "---\nwork_package_id: WP01\ndependencies: []\nrequirement_refs: []\n---\n# Guard\n",
        encoding="utf-8",
    )
    (primary / "spec.md").write_text("# Spec\n\n- **FR-001**: Resolve planning authority.\n", encoding="utf-8")
    append_event(status, StatusEvent(
        event_id="test-WP01-for-review", mission_slug=MISSION_SLUG, wp_id="WP01",
        from_lane=Lane.IN_PROGRESS, to_lane=Lane.FOR_REVIEW,
        at="2026-09-06T00:00:00+00:00", actor="test", force=True, execution_mode="worktree",
    ))
    (status / "mission-events.jsonl").write_text(
        '{"type":"source_documented"}\n{"type":"gate_passed","name":"publication_approved"}\n',
        encoding="utf-8",
    )
    snapshot = gather_artifact_presence(status, mission_family="software-dev", step_id="tasks_finalize", repo_root=repo)
    assert "tasks_wp_files" in snapshot.present_artifacts
    assert snapshot.status_facts["wp_lane_raw"] == {"WP01": Lane.FOR_REVIEW}
    assert snapshot.status_facts["wp_dependencies_present"] == {"WP01": True}
    assert snapshot.status_facts["requirement_mapping_failures"]
    assert snapshot.status_facts["source_documented_count"] == 1
    assert snapshot.status_facts["publication_approved"] is True
    assert not (primary / "status.events.jsonl").exists()
    assert not (status / "tasks").exists()


def test_unclassified_artifact_retains_local_authority(tmp_path: Path) -> None:
    repo, primary, status = _mission(tmp_path)
    # A built-in research filename with no canonical placement kind.
    (status / "report.md").write_text("# Report\n", encoding="utf-8")
    snapshot = gather_artifact_presence(status, mission_family="research", step_id="output", repo_root=repo)
    assert "report.md" in snapshot.present_artifacts
    assert not (primary / "report.md").exists()


def test_occurrence_guard_reads_primary_metadata(tmp_path: Path) -> None:
    repo, primary, status = _mission(tmp_path)
    meta_path = primary / "meta.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    meta["change_mode"] = "bulk_edit"
    meta_path.write_text(json.dumps(meta), encoding="utf-8")
    snapshot = gather_artifact_presence(status, mission_family="software-dev", step_id="tasks_finalize", repo_root=repo)
    assert snapshot.status_facts["occurrence_gate_failures"]
    assert str(primary / "occurrence_map.yaml") in snapshot.status_facts["occurrence_gate_failures"][0]
