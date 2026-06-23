"""Regression (#2088): finalize-tasks must NOT reject same-lane sequential WPs
that share owned_files.

This is a genuine red-first capture through the STABLE entry point
(``finalize-tasks --validate-only``), not a test of the fix's new API. On the
pre-fix code the ownership validator's all-pairs overlap check rejects two WPs
that share ``owned_files`` even when one transitively depends on the other (a
linearized refactor chain the lane allocator collapses into one lane). This test
builds exactly such a sequential-overlap pair and asserts validation PASSES — it
FAILS ("Ownership validation failed: Overlap …") on the dependency-blind code and
PASSES once the validator is dependency-aware.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from specify_cli.cli.commands.agent.mission import app

pytestmark = pytest.mark.fast

runner = CliRunner()

_SLUG = "single-authority-topology-cleanup-01KVRJ6P"
_SHARED = "src/specify_cli/coordination/surface_resolver.py"


def _wp(wp_id: str, deps: list[str]) -> str:
    dep_block = "[]" if not deps else "[" + ", ".join(deps) + "]"
    return (
        "---\n"
        f"work_package_id: {wp_id}\n"
        f"title: {wp_id} sequential-overlap\n"
        f"dependencies: {dep_block}\n"
        "requirement_refs: [FR-001]\n"
        "execution_mode: code_change\n"
        "owned_files:\n"
        f"  - {_SHARED}\n"
        "authoritative_surface: src/specify_cli/coordination/\n"
        "---\n"
        f"# {wp_id}\n"
    )


def _build_sequential_overlap_feature(tmp_path: Path) -> Path:
    # The shared owned_file must exist so the literal-path-zero-match gate passes
    # and the OVERLAP check (the behaviour under test) decides the outcome.
    shared = tmp_path / _SHARED
    shared.parent.mkdir(parents=True, exist_ok=True)
    shared.write_text("# stub surface\n", encoding="utf-8")

    feature_dir = tmp_path / "kitty-specs" / _SLUG
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir(parents=True)
    (feature_dir / "meta.json").write_text('{"target_branch": "main"}\n', encoding="utf-8")
    (feature_dir / "spec.md").write_text(
        "# Spec\n"
        "## Functional Requirements\n"
        "| ID | Requirement | Acceptance Criteria | Status |\n"
        "| --- | --- | --- | --- |\n"
        "| FR-001 | Linearized refactor of one surface | Covered by WP01/WP02. | proposed |\n",
        encoding="utf-8",
    )
    (feature_dir / "tasks.md").write_text(
        "## WP01\n**Requirement Refs**: FR-001\n## WP02\n**Requirement Refs**: FR-001\n",
        encoding="utf-8",
    )
    # WP02 depends on WP01 → strictly sequential → sharing the same file is legitimate.
    (tasks_dir / "WP01-first.md").write_text(_wp("WP01", []), encoding="utf-8")
    (tasks_dir / "WP02-second.md").write_text(_wp("WP02", ["WP01"]), encoding="utf-8")
    return feature_dir


def _run_command(cmd: list[str], **_kwargs: object) -> tuple[int, str, str]:
    if "status" in cmd and "--porcelain" in cmd:
        return (0, "M tasks.md", "")
    if "rev-parse" in cmd and "HEAD" in cmd:
        return (0, "c" * 40, "")
    return (0, "", "")


def _json_payload(stdout: str) -> dict[str, object]:
    lines = [line for line in stdout.splitlines() if line.strip().startswith("{")]
    assert lines, stdout
    return json.loads(lines[-1])


def test_sequential_overlap_passes_finalize_validation(tmp_path: Path) -> None:
    feature_dir = _build_sequential_overlap_feature(tmp_path)

    with (
        patch("specify_cli.cli.commands.agent.mission.locate_project_root", return_value=tmp_path),
        patch(
            "specify_cli.cli.commands.agent.mission._find_feature_directory",
            return_value=feature_dir,
        ),
        patch(
            "specify_cli.cli.commands.agent.mission._show_branch_context",
            return_value=(tmp_path, "main"),
        ),
        patch("specify_cli.cli.commands.agent.mission.run_command", side_effect=_run_command),
        patch("specify_cli.cli.commands.agent.mission.get_emitter"),
        # The mission's commit tail routes through commit_for_mission, which is the
        # module that imports and calls safe_commit (the old mission.py re-export was
        # removed by the single-authority topology cleanup, #2070). Patch it at the
        # canonical use site.
        patch("specify_cli.coordination.commit_router.safe_commit", return_value=True),
    ):
        result = runner.invoke(
            app,
            ["finalize-tasks", "--mission", _SLUG, "--json", "--validate-only"],
        )

    payload = _json_payload(result.stdout)
    # Pre-fix: exit 1, error "Ownership validation failed", ownership_errors lists
    # the WP01/WP02 overlap. Post-fix (dependency-aware): validation passes.
    assert result.exit_code == 0, payload
    assert payload.get("result") == "validation_passed", payload
    assert "ownership_errors" not in payload or not payload["ownership_errors"]
