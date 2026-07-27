"""Acceptance pins for the top-level CLI-command read-side placement migration (WP04)."""

from __future__ import annotations

import ast
import json
import subprocess
from pathlib import Path

import pytest

from mission_runtime import MissionArtifactKind, placement_seam
from specify_cli.cli.commands import mission_type, next_cmd, verify
from specify_cli.cli.commands import retrospect
from specify_cli.cli.commands.charter import _widen
from specify_cli.coordination.surface_resolver import CoordinationBranchDeleted

pytestmark = [pytest.mark.fast, pytest.mark.git_repo]

MISSION_ID = "01KWZ46VTY9CVJ8G10ERTMPVRH"
MID8 = MISSION_ID[:8]
MISSION_SLUG = "read-seam-cli"
MISSION_DIR_NAME = f"{MISSION_SLUG}-{MID8}"
COORD_BRANCH = f"kitty/mission-{MISSION_DIR_NAME}"

_BYPASS_NAMES = {
    "candidate_feature_dir_for_mission",
    "resolve_planning_read_dir",
}

# Files WP04 owns that had real bypass call sites (ledger § WP04).
_MIGRATION_MODULES = {
    "archive.py",
    "_coordination_doctor.py",
    "merge.py",
    "mission_type.py",
    "next_cmd.py",
    "reconcile.py",
    "research.py",
    "retrospect.py",
    "validate_tasks.py",
    "verify.py",
}

# Ledger-approved stay-lenient residuals (file, enclosing function, symbol).
_EXPECTED_LENIENT_SITES = {
    ("archive.py", "create", "candidate_feature_dir_for_mission"),
    (
        "_coordination_doctor.py",
        "_finding_for_reconcile_marker",
        "resolve_planning_read_dir",
    ),
    ("_coordination_doctor.py", "_heal_one_strand", "resolve_planning_read_dir"),
    ("reconcile.py", "reconcile_mission_dossier", "candidate_feature_dir_for_mission"),
    ("retrospect.py", "_canonical_events_path", "candidate_feature_dir_for_mission"),
    ("retrospect.py", "summary_cmd", "candidate_feature_dir_for_mission"),
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
    (mission_dir / "meta.json").write_text(
        json.dumps(
            {
                "mission_id": MISSION_ID,
                "mission_slug": MISSION_DIR_NAME,
                "mid8": MID8,
                **({"coordination_branch": COORD_BRANCH} if deleted_coord else {}),
            }
        ),
        encoding="utf-8",
    )
    (mission_dir / "research.md").write_text("# research\n", encoding="utf-8")
    (mission_dir / "plan.md").write_text("# plan\n", encoding="utf-8")
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

        def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
            previous = self.function
            self.function = node.name
            self.generic_visit(node)
            self.function = previous

        def visit_Call(self, node: ast.Call) -> None:
            name = (
                node.func.id
                if isinstance(node.func, ast.Name)
                else getattr(node.func, "attr", None)
            )
            if name in _BYPASS_NAMES:
                descriptors.add((path.name, self.function, name))
            self.generic_visit(node)

    _Visitor().visit(tree)
    return descriptors


def test_cli_command_cluster_retains_only_ledger_approved_lenient_sites() -> None:
    """WP04 migrate-fail-loud calls leave only the ledger's stay-lenient residuals."""
    commands_dir = Path(verify.__file__).resolve().parent
    descriptors: set[tuple[str, str, str]] = set()
    for path in commands_dir.glob("*.py"):
        if path.name in _MIGRATION_MODULES:
            descriptors.update(_bypass_descriptors(path))
    widen_path = Path(_widen.__file__).resolve()
    descriptors.update(_bypass_descriptors(widen_path))

    assert descriptors == _EXPECTED_LENIENT_SITES


def test_primary_metadata_handle_resolution_preserves_canonical_slug(tmp_path: Path) -> None:
    """Migrated PRIMARY_METADATA slug-canon sites return the on-disk directory name."""
    mission_dir = _seed_repo(tmp_path, deleted_coord=False)

    assert mission_type._resolve_mission_slug(tmp_path, MID8) == mission_dir.name
    assert next_cmd._resolve_mission_slug(MID8, tmp_path) == mission_dir.name
    assert _widen._get_mission_id(tmp_path, MID8) == MISSION_ID
    assert verify._existing_feature_dir(tmp_path, MID8) == mission_dir


def test_migrated_primary_kinds_resolve_identically_to_primary_home(tmp_path: Path) -> None:
    """Healthy PRIMARY-partition reads converge on the primary mission directory."""
    mission_dir = _seed_repo(tmp_path, deleted_coord=False)

    for kind in (
        MissionArtifactKind.PRIMARY_METADATA,
        MissionArtifactKind.RESEARCH,
        MissionArtifactKind.FINALIZED_EXECUTION_PLAN,
        MissionArtifactKind.WORK_PACKAGE_TASK,
    ):
        resolved = placement_seam(tmp_path, MISSION_DIR_NAME).read_dir(kind)
        assert resolved.resolve() == mission_dir.resolve()


def test_migrated_primary_kinds_stay_silent_when_coord_branch_was_deleted(
    tmp_path: Path,
) -> None:
    """PRIMARY-partition migrate sites must NOT raise on a deleted coord branch.

    WP04's migrate-fail-loud kinds are all PRIMARY-partition; fail-loud for
    deleted COORD applies only to COORD-partition kinds. Preserving silence here
    is the healthy-case / NFR-002 behaviour pin for this cluster.
    """
    mission_dir = _seed_repo(tmp_path, deleted_coord=True)

    assert mission_type._resolve_mission_slug(tmp_path, MID8) == mission_dir.name
    assert next_cmd._resolve_mission_slug(MID8, tmp_path) == mission_dir.name
    assert verify._existing_feature_dir(tmp_path, MID8) == mission_dir
    assert (
        placement_seam(tmp_path, MISSION_DIR_NAME)
        .read_dir(MissionArtifactKind.WORK_PACKAGE_TASK)
        .resolve()
        == mission_dir.resolve()
    )


def test_stay_lenient_retrospect_fallback_tolerates_missing_status_surface(
    tmp_path: Path,
) -> None:
    """Ledger stay-lenient ``_canonical_events_path`` fallback must keep working.

    The fallback fires when ``resolve_status_surface`` raises ``FileNotFoundError``
    / ``ValueError`` (e.g. meta.json absent for a legacy mission) — not on
    ``CoordinationBranchDeleted``, which propagates from the status surface.
    """
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.email", "read-seam@example.test")
    _git(tmp_path, "config", "user.name", "Read Seam Test")
    _git(tmp_path, "commit", "--allow-empty", "-qm", "init")
    mission_dir = tmp_path / "kitty-specs" / MISSION_DIR_NAME
    mission_dir.mkdir(parents=True)
    # No meta.json → resolve_status_surface cannot classify; fallback engages.

    events_path = retrospect._canonical_events_path(tmp_path, MISSION_DIR_NAME)
    assert events_path == mission_dir / "status.events.jsonl"


def test_coord_partition_kind_still_fails_loud_via_seam(tmp_path: Path) -> None:
    """Sanity: the seam itself still raises for COORD kinds when the branch is gone."""
    _seed_repo(tmp_path, deleted_coord=True)

    with pytest.raises(CoordinationBranchDeleted) as exc_info:
        placement_seam(tmp_path, MISSION_DIR_NAME).read_dir(MissionArtifactKind.STATUS_STATE)

    assert exc_info.value.error_code == "COORDINATION_BRANCH_DELETED"
