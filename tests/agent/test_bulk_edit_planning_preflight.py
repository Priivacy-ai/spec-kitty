"""Tests for identifying bulk-edit planning WPs."""

from __future__ import annotations

from pathlib import Path

import pytest

from specify_cli.bulk_edit.inference import (
    is_bulk_edit_planning_owned_file,
    wp_authors_bulk_edit_planning_artifact,
)

pytestmark = pytest.mark.fast


def _write_wp(tmp_path: Path, owned_files: list[str]) -> Path:
    wp_file = tmp_path / "WP01-plan.md"
    owned_lines = "\n".join(f"  - {path}" for path in owned_files)
    wp_file.write_text(
        "---\n"
        "work_package_id: WP01\n"
        "title: Plan bulk edit\n"
        "dependencies: []\n"
        "execution_mode: code_change\n"
        "owned_files:\n"
        f"{owned_lines}\n"
        "authoritative_surface: occurrence_map.yaml\n"
        "---\n"
        "# WP01\n",
        encoding="utf-8",
    )
    return wp_file


@pytest.mark.parametrize(
    "owned_file",
    [
        "occurrence_map.yaml",
        "./occurrence_map.yaml",
        "kitty-specs/demo-mission/occurrence_map.yaml",
        "kitty-specs/demo-mission/tasks.md",
    ],
)
def test_planning_owned_files_are_detected(owned_file: str) -> None:
    assert is_bulk_edit_planning_owned_file(owned_file, "demo-mission") is True


def test_unrelated_owned_file_is_not_planning() -> None:
    assert is_bulk_edit_planning_owned_file("src/specify_cli/runtime.py", "demo-mission") is False


def test_wp_authors_bulk_edit_planning_artifact(tmp_path: Path) -> None:
    wp_file = _write_wp(tmp_path, ["src/runtime.py", "occurrence_map.yaml"])

    assert wp_authors_bulk_edit_planning_artifact(wp_file, "demo-mission") is True


def test_wp_without_planning_artifact_is_not_exempt(tmp_path: Path) -> None:
    wp_file = _write_wp(tmp_path, ["src/runtime.py"])

    assert wp_authors_bulk_edit_planning_artifact(wp_file, "demo-mission") is False
