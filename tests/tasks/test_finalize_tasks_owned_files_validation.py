"""Regression tests for finalize-tasks owned_files validation."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from specify_cli.cli.commands.agent.mission import (
    INVALID_WP_OWNED_FILES_KITTY_SPECS,
    app,
)

pytestmark = pytest.mark.fast

runner = CliRunner()


def _build_feature(tmp_path: Path, *, owned_file: str) -> Path:
    mission_slug = "077-invalid-owned-files"
    feature_dir = tmp_path / "kitty-specs" / mission_slug
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir(parents=True)
    (feature_dir / "meta.json").write_text('{"target_branch": "main"}\n', encoding="utf-8")
    (feature_dir / "spec.md").write_text(
        "# Spec\n"
        "## Functional Requirements\n"
        "| ID | Requirement | Acceptance Criteria | Status |\n"
        "| --- | --- | --- | --- |\n"
        "| FR-001 | Test requirement | Covered by WP01. | proposed |\n",
        encoding="utf-8",
    )
    (feature_dir / "tasks.md").write_text(
        "## WP01\n"
        "**Requirement Refs**: FR-001\n",
        encoding="utf-8",
    )
    (tasks_dir / "WP01-invalid.md").write_text(
        "---\n"
        "work_package_id: WP01\n"
        "title: Invalid ownership\n"
        "dependencies: []\n"
        "requirement_refs: [FR-001]\n"
        "execution_mode: code_change\n"
        "owned_files:\n"
        f"  - {owned_file}\n"
        "authoritative_surface: src/example/\n"
        "---\n"
        "# WP01\n",
        encoding="utf-8",
    )
    return feature_dir


def _add_create_intent(feature_dir: Path, path: str) -> None:
    wp_file = feature_dir / "tasks" / "WP01-invalid.md"
    content = wp_file.read_text(encoding="utf-8")
    content = content.replace(
        "authoritative_surface: src/example/\n",
        f"authoritative_surface: src/example/\ncreate_intent:\n  - {path}\n",
    )
    wp_file.write_text(content, encoding="utf-8")


def _run_command(cmd: list[str], **_kwargs: object) -> tuple[int, str, str]:
    if "status" in cmd and "--porcelain" in cmd:
        return (0, "M tasks.md", "")
    if "rev-parse" in cmd and "HEAD" in cmd:
        return (0, "c" * 40, "")
    return (0, "", "")


def _invoke_finalize(tmp_path: Path, feature_dir: Path, extra_args: list[str] | None = None):
    args = ["finalize-tasks", "--mission", feature_dir.name, "--json"]
    if extra_args:
        args.extend(extra_args)
    # WP05 (T014): the ``mission.safe_commit`` re-export shim is gone; the canonical
    # commit boundary is ``commit_router.commit_for_mission``. The spy is attached to
    # THAT seam so the "rejected before any commit" contract is asserted at the real
    # commit boundary, not a retired alias.
    commit_patcher = patch(
        "specify_cli.coordination.commit_router.commit_for_mission",
        return_value=True,
    )
    with (
        patch("specify_cli.cli.commands.agent.mission.locate_project_root", return_value=tmp_path),
        patch("specify_cli.cli.commands.agent.mission._find_feature_directory", return_value=feature_dir),
        patch("specify_cli.cli.commands.agent.mission._show_branch_context", return_value=(tmp_path, "main")),
        patch("specify_cli.cli.commands.agent.mission.run_command", side_effect=_run_command),
        patch("specify_cli.cli.commands.agent.mission.get_emitter"),
        commit_patcher as commit_for_mission,
    ):
        return runner.invoke(app, args), commit_for_mission


def _json_payload(stdout: str) -> dict[str, object]:
    lines = [line for line in stdout.splitlines() if line.strip().startswith("{")]
    assert lines, stdout
    return json.loads(lines[-1])


def _strict_json_payload(stdout: str) -> dict[str, object]:
    return json.loads(stdout)


def test_validate_only_rejects_kitty_specs_owned_files(tmp_path: Path) -> None:
    feature_dir = _build_feature(
        tmp_path,
        owned_file="kitty-specs/077-invalid-owned-files/occurrence_map.yaml",
    )

    result, commit_for_mission = _invoke_finalize(tmp_path, feature_dir, ["--validate-only"])

    assert result.exit_code == 1
    commit_for_mission.assert_not_called()
    payload = _json_payload(result.stdout)
    assert payload["error_code"] == INVALID_WP_OWNED_FILES_KITTY_SPECS
    assert payload["invalid_owned_files"] == [
        {
            "wp_id": "WP01",
            "path": "kitty-specs/077-invalid-owned-files/occurrence_map.yaml",
        }
    ]


def test_full_finalize_rejects_before_commit(tmp_path: Path) -> None:
    feature_dir = _build_feature(
        tmp_path,
        owned_file="./kitty-specs/077-invalid-owned-files/plan.md",
    )

    result, commit_for_mission = _invoke_finalize(tmp_path, feature_dir)

    assert result.exit_code == 1
    commit_for_mission.assert_not_called()
    payload = _json_payload(result.stdout)
    assert payload["error_code"] == INVALID_WP_OWNED_FILES_KITTY_SPECS
    assert payload["invalid_owned_files"] == [
        {
            "wp_id": "WP01",
            "path": "./kitty-specs/077-invalid-owned-files/plan.md",
        }
    ]


def test_validate_only_json_suppresses_create_intent_info_note(tmp_path: Path) -> None:
    feature_dir = _build_feature(tmp_path, owned_file="src/example/new_module.py")
    _add_create_intent(feature_dir, "src/example/new_module.py")

    result, _commit_for_mission = _invoke_finalize(tmp_path, feature_dir, ["--validate-only"])

    assert result.exit_code == 0
    payload = _strict_json_payload(result.stdout)
    assert payload["result"] == "validation_passed"
    assert "create_intent" not in result.stdout
    assert "create_intent" not in result.stderr


def test_validate_only_json_suppresses_ownership_stderr_on_error(tmp_path: Path) -> None:
    feature_dir = _build_feature(tmp_path, owned_file="src/example/missing_module.py")

    result, commit_for_mission = _invoke_finalize(tmp_path, feature_dir, ["--validate-only"])

    assert result.exit_code == 1
    commit_for_mission.assert_not_called()
    payload = _strict_json_payload(result.stdout)
    assert payload["error"] == (
        "Ownership validation failed: literal-path owned_files entries match zero files. "
        "Fix the paths or add them to 'create_intent'."
    )
    assert payload["ownership_literal_path_errors"]
    assert result.stderr == ""
