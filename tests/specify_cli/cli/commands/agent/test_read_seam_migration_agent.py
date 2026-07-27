"""Acceptance pins for the agent-command read-side placement migration."""

from __future__ import annotations

import ast
import json
import subprocess
from pathlib import Path

import pytest

from specify_cli.cli.commands.agent import status, workflow
from specify_cli.coordination.surface_resolver import CoordinationBranchDeleted

pytestmark = [pytest.mark.integration, pytest.mark.git_repo]

MISSION_ID = "01KWZ46VTY9CVJ8G10ERTMPVRH"
MID8 = MISSION_ID[:8]
MISSION_SLUG = "read-seam-agent"
MISSION_DIR_NAME = f"{MISSION_SLUG}-{MID8}"
COORD_BRANCH = f"kitty/mission-{MISSION_DIR_NAME}"
_BYPASS_NAMES = {
    "candidate_feature_dir_for_mission",
    "resolve_planning_read_dir",
}
_MIGRATION_MODULES = {
    "status.py",
    "tasks.py",
    "tasks_dependency_graph.py",
    "tasks_map_requirements.py",
    "tasks_materialization.py",
    "tasks_parsing_validation.py",
    "tasks_shared.py",
    "tasks_status_cmd.py",
    "workflow.py",
    "workflow_executor.py",
}
_EXPECTED_LENIENT_SITES = {
    ("tasks_move_task.py", "_coord_status_events_path", "candidate_feature_dir_for_mission"),
    ("tasks_status_cmd.py", "_st_resolve_dirs", "candidate_feature_dir_for_mission"),
}


def _git(repo_root: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-C", str(repo_root), *args],
        check=True,
        capture_output=True,
        text=True,
    )


def _seed_repo(tmp_path: Path, *, deleted_coord: bool) -> Path:
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.email", "read-seam@example.test")
    _git(tmp_path, "config", "user.name", "Read Seam Test")
    _git(tmp_path, "commit", "--allow-empty", "-qm", "init")

    mission_dir = tmp_path / "kitty-specs" / MISSION_DIR_NAME
    (mission_dir / "tasks").mkdir(parents=True)
    metadata: dict[str, str] = {
        "mission_id": MISSION_ID,
        "mission_slug": MISSION_DIR_NAME,
    }
    if deleted_coord:
        metadata["coordination_branch"] = COORD_BRANCH
    (mission_dir / "meta.json").write_text(json.dumps(metadata), encoding="utf-8")
    return mission_dir


def _bypass_descriptors(path: Path) -> set[tuple[str, str, str]]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    descriptors: set[tuple[str, str, str]] = set()

    class _Visitor(ast.NodeVisitor):
        def __init__(self) -> None:
            self.function = "<module>"

        def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
            previous = self.function
            self.function = node.name
            self.generic_visit(node)
            self.function = previous

        visit_AsyncFunctionDef = visit_FunctionDef

        def visit_Call(self, node: ast.Call) -> None:
            name = node.func.id if isinstance(node.func, ast.Name) else getattr(node.func, "attr", None)
            if name in _BYPASS_NAMES:
                descriptors.add((path.name, self.function, name))
            self.generic_visit(node)

    _Visitor().visit(tree)
    return descriptors


def test_agent_command_cluster_retains_only_ledger_approved_lenient_sites() -> None:
    """All WP03 migrate-fail-loud calls leave only the two approved fallbacks."""
    agent_dir = Path(status.__file__).resolve().parent
    descriptors: set[tuple[str, str, str]] = set()
    for path in agent_dir.glob("*.py"):
        if path.name in _MIGRATION_MODULES or path.name == "tasks_move_task.py":
            descriptors.update(_bypass_descriptors(path))

    assert descriptors == _EXPECTED_LENIENT_SITES


def test_primary_metadata_handle_resolution_preserves_the_canonical_slug(tmp_path: Path) -> None:
    """The migrated PRIMARY_METADATA read returns the same canonical directory name."""
    mission_dir = _seed_repo(tmp_path, deleted_coord=False)

    assert status._find_mission_slug(MID8, repo_root=tmp_path) == mission_dir.name


def test_preview_claimable_wp_fails_loudly_when_coord_branch_was_deleted(tmp_path: Path) -> None:
    """The stable workflow preview entry point exposes deleted COORD authority."""
    _seed_repo(tmp_path, deleted_coord=True)

    with pytest.raises(CoordinationBranchDeleted) as exc_info:
        workflow._preview_claimable_wp_for_mission(tmp_path, MISSION_DIR_NAME)

    assert exc_info.value.error_code == "COORDINATION_BRANCH_DELETED"
