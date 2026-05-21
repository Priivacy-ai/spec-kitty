"""Architectural guard for newly authored WP owned_files."""

from __future__ import annotations

from pathlib import Path

import pytest

from specify_cli.cli.commands.agent.mission import _invalid_kitty_specs_owned_files
from specify_cli.status.wp_metadata import WPMetadata, read_wp_frontmatter

pytestmark = pytest.mark.fast

MISSION_UNDER_TEST = "autonomous-runtime-safety-followups-01KS52BD"


def test_current_mission_wp_owned_files_do_not_target_kitty_specs() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    tasks_dir = repo_root / "kitty-specs" / MISSION_UNDER_TEST / "tasks"
    frontmatter_by_wp: dict[str, WPMetadata] = {}

    for wp_file in sorted(tasks_dir.glob("WP*.md")):
        metadata, _body = read_wp_frontmatter(wp_file)
        frontmatter_by_wp[metadata.work_package_id] = metadata

    assert _invalid_kitty_specs_owned_files(frontmatter_by_wp) == []
