"""Unit tests for specify_cli.intake_sources."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from specify_cli.intake_sources import HARNESS_PLAN_SOURCES, scan_for_plans


class TestHarnessPlanSources:
    def test_list_is_defined(self):
        assert isinstance(HARNESS_PLAN_SOURCES, list)

    def test_all_entries_have_correct_shape(self):
        for entry in HARNESS_PLAN_SOURCES:
            harness_key, source_agent_value, candidate_paths = entry
            assert isinstance(harness_key, str) and harness_key
            assert source_agent_value is None or isinstance(source_agent_value, str)
            assert isinstance(candidate_paths, list) and candidate_paths

    def test_no_overlapping_candidate_paths(self):
        seen: set[str] = set()
        for _, _, paths in HARNESS_PLAN_SOURCES:
            for p in paths:
                assert p not in seen, f"Duplicate path {p!r}"
                seen.add(p)


class TestScanForPlans:
    def test_empty_dir_returns_empty(self, tmp_path: Path):
        assert scan_for_plans(tmp_path) == []

    def test_nonexistent_dir_returns_empty(self):
        assert scan_for_plans(Path("/nonexistent/path/does/not/exist/xyz")) == []

    def test_empty_directory_at_candidate_path_returns_empty(self, tmp_path: Path):
        if not HARNESS_PLAN_SOURCES:
            pytest.skip("No active entries")
        _, _, candidate_paths = HARNESS_PLAN_SOURCES[0]
        target = tmp_path / candidate_paths[0]
        target.mkdir(parents=True, exist_ok=True)  # empty dir → no .md children
        assert scan_for_plans(tmp_path) == []

    def test_directory_at_candidate_path_expands_md_children(self, tmp_path: Path):
        """A directory at a candidate path yields its .md files as results."""
        mock_sources = [("opencode", "opencode", [".opencode/plans"])]
        plans_dir = tmp_path / ".opencode" / "plans"
        plans_dir.mkdir(parents=True)
        plan_file = plans_dir / "2026-04-20-my-plan.md"
        plan_file.write_text("# My Plan", encoding="utf-8")

        with patch("specify_cli.intake_sources.HARNESS_PLAN_SOURCES", mock_sources):
            results = scan_for_plans(tmp_path)

        assert len(results) == 1
        assert results[0][0] == plan_file
        assert results[0][1] == "opencode"
        assert results[0][2] == "opencode"

    def test_non_md_files_in_directory_are_excluded(self, tmp_path: Path):
        """Only .md files are included when expanding a directory candidate."""
        mock_sources = [("opencode", "opencode", [".opencode/plans"])]
        plans_dir = tmp_path / ".opencode" / "plans"
        plans_dir.mkdir(parents=True)
        (plans_dir / "plan.md").write_text("# Plan", encoding="utf-8")
        (plans_dir / "plan.json").write_text("{}", encoding="utf-8")
        (plans_dir / ".hidden").write_text("hidden", encoding="utf-8")

        with patch("specify_cli.intake_sources.HARNESS_PLAN_SOURCES", mock_sources):
            results = scan_for_plans(tmp_path)

        assert len(results) == 1
        assert results[0][0].name == "plan.md"

    def test_returns_multiple_matches_in_order(self, tmp_path: Path):
        mock_sources = [
            ("harness-a", "agent-a", ["plan-a.md"]),
            ("harness-b", "agent-b", ["plan-b.md"]),
        ]
        (tmp_path / "plan-a.md").write_text("A", encoding="utf-8")
        (tmp_path / "plan-b.md").write_text("B", encoding="utf-8")
        with patch("specify_cli.intake_sources.HARNESS_PLAN_SOURCES", mock_sources):
            results = scan_for_plans(tmp_path)
        assert len(results) == 2
        assert results[0][1] == "harness-a"
        assert results[1][1] == "harness-b"

    def test_finds_file_at_nested_path(self, tmp_path: Path):
        mock_sources = [("cursor", "cursor", [".cursor/plans/plan.md"])]
        target = tmp_path / ".cursor" / "plans" / "plan.md"
        target.parent.mkdir(parents=True)
        target.write_text("# Plan", encoding="utf-8")
        with patch("specify_cli.intake_sources.HARNESS_PLAN_SOURCES", mock_sources):
            results = scan_for_plans(tmp_path)
        assert len(results) == 1
        assert results[0][0] == target

    def test_no_exception_on_permission_error(self, tmp_path: Path):
        mock_sources = [("harness-x", "agent-x", ["secret.md"])]
        with patch("specify_cli.intake_sources.HARNESS_PLAN_SOURCES", mock_sources), \
             patch("pathlib.Path.is_file", side_effect=PermissionError("denied")):
            results = scan_for_plans(tmp_path)
        assert results == []
