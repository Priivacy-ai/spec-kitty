"""Unit tests for wps_manifest module."""
from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from specify_cli.core.wps_manifest import (
    WorkPackageEntry,
    WpsManifest,
    dependencies_are_explicit,
    generate_tasks_md_from_manifest,
    load_wps_manifest,
)


class TestLoadWpsManifest:
    def test_load_valid_manifest(self, tmp_path: Path) -> None:
        wps = tmp_path / "wps.yaml"
        wps.write_text(
            "work_packages:\n"
            "  - id: WP01\n"
            "    title: 'First WP'\n"
            "    dependencies: []\n",
            encoding="utf-8",
        )
        manifest = load_wps_manifest(tmp_path)
        assert manifest is not None
        assert len(manifest.work_packages) == 1
        assert manifest.work_packages[0].id == "WP01"
        assert manifest.work_packages[0].title == "First WP"

    def test_absent_returns_none(self, tmp_path: Path) -> None:
        result = load_wps_manifest(tmp_path)
        assert result is None

    def test_malformed_raises_validation_error_with_field_name(self, tmp_path: Path) -> None:
        wps = tmp_path / "wps.yaml"
        wps.write_text(
            "work_packages:\n  - id: INVALID_ID\n    title: 'test'\n",
            encoding="utf-8",
        )
        with pytest.raises(ValidationError) as exc_info:
            load_wps_manifest(tmp_path)
        error_str = str(exc_info.value)
        assert "id" in error_str or "WP" in error_str  # field name appears in error

    def test_missing_required_title_raises(self, tmp_path: Path) -> None:
        wps = tmp_path / "wps.yaml"
        wps.write_text(
            "work_packages:\n  - id: WP01\n",  # missing title
            encoding="utf-8",
        )
        with pytest.raises(ValidationError):
            load_wps_manifest(tmp_path)

    def test_load_multiple_work_packages(self, tmp_path: Path) -> None:
        wps = tmp_path / "wps.yaml"
        wps.write_text(
            "work_packages:\n"
            "  - id: WP01\n"
            "    title: 'First'\n"
            "  - id: WP02\n"
            "    title: 'Second'\n"
            "    dependencies: [WP01]\n",
            encoding="utf-8",
        )
        manifest = load_wps_manifest(tmp_path)
        assert manifest is not None
        assert len(manifest.work_packages) == 2
        assert manifest.work_packages[1].dependencies == ["WP01"]

    def test_invalid_dependency_raises(self, tmp_path: Path) -> None:
        wps = tmp_path / "wps.yaml"
        wps.write_text(
            "work_packages:\n"
            "  - id: WP01\n"
            "    title: 'T'\n"
            "    dependencies: [NOTAWP]\n",
            encoding="utf-8",
        )
        with pytest.raises(ValidationError):
            load_wps_manifest(tmp_path)

    def test_optional_fields_default(self, tmp_path: Path) -> None:
        wps = tmp_path / "wps.yaml"
        wps.write_text(
            "work_packages:\n  - id: WP01\n    title: 'Minimal'\n",
            encoding="utf-8",
        )
        manifest = load_wps_manifest(tmp_path)
        assert manifest is not None
        entry = manifest.work_packages[0]
        assert entry.dependencies == []
        assert entry.owned_files == []
        assert entry.requirement_refs == []
        assert entry.subtasks == []
        assert entry.prompt_file is None


class TestDependenciesAreExplicit:
    def test_present_empty_list_is_explicit(self, tmp_path: Path) -> None:
        """dependencies: [] in YAML → explicit."""
        wps = tmp_path / "wps.yaml"
        wps.write_text(
            "work_packages:\n  - id: WP01\n    title: 'T'\n    dependencies: []\n",
            encoding="utf-8",
        )
        manifest = load_wps_manifest(tmp_path)
        assert manifest is not None
        assert dependencies_are_explicit(manifest.work_packages[0]) is True

    def test_absent_key_is_not_explicit(self, tmp_path: Path) -> None:
        """No 'dependencies' key in YAML → not explicit."""
        wps = tmp_path / "wps.yaml"
        wps.write_text(
            "work_packages:\n  - id: WP01\n    title: 'T'\n",
            encoding="utf-8",
        )
        manifest = load_wps_manifest(tmp_path)
        assert manifest is not None
        assert dependencies_are_explicit(manifest.work_packages[0]) is False

    def test_present_nonempty_list_is_explicit(self, tmp_path: Path) -> None:
        wps = tmp_path / "wps.yaml"
        wps.write_text(
            "work_packages:\n  - id: WP02\n    title: 'T'\n    dependencies: [WP01]\n",
            encoding="utf-8",
        )
        manifest = load_wps_manifest(tmp_path)
        assert manifest is not None
        assert dependencies_are_explicit(manifest.work_packages[0]) is True

    def test_multiple_wps_track_independently(self, tmp_path: Path) -> None:
        wps = tmp_path / "wps.yaml"
        wps.write_text(
            "work_packages:\n"
            "  - id: WP01\n"
            "    title: 'With deps key'\n"
            "    dependencies: []\n"
            "  - id: WP02\n"
            "    title: 'Without deps key'\n",
            encoding="utf-8",
        )
        manifest = load_wps_manifest(tmp_path)
        assert manifest is not None
        assert dependencies_are_explicit(manifest.work_packages[0]) is True
        assert dependencies_are_explicit(manifest.work_packages[1]) is False


class TestGenerateTasksMd:
    def _make_manifest(self) -> WpsManifest:
        return WpsManifest(
            work_packages=[
                WorkPackageEntry(
                    id="WP01",
                    title="First",
                    dependencies=[],
                    subtasks=["T001", "T002"],
                    requirement_refs=["FR-001"],
                ),
                WorkPackageEntry(
                    id="WP02",
                    title="Second",
                    dependencies=["WP01"],
                ),
            ]
        )

    def test_contains_all_wp_titles(self) -> None:
        md = generate_tasks_md_from_manifest(self._make_manifest(), "Test Feature")
        assert "First" in md
        assert "Second" in md

    def test_contains_dependency_lines(self) -> None:
        md = generate_tasks_md_from_manifest(self._make_manifest(), "Test Feature")
        assert "WP01" in md  # WP02 depends on WP01

    def test_empty_deps_shows_none(self) -> None:
        md = generate_tasks_md_from_manifest(self._make_manifest(), "Test Feature")
        assert "None" in md  # WP01 has no deps

    def test_subtask_ids_present(self) -> None:
        md = generate_tasks_md_from_manifest(self._make_manifest(), "Test Feature")
        assert "T001" in md
        assert "T002" in md

    def test_has_generated_header_note(self) -> None:
        md = generate_tasks_md_from_manifest(self._make_manifest(), "Test Feature")
        assert "Generated by finalize-tasks" in md

    def test_feature_name_in_heading(self) -> None:
        md = generate_tasks_md_from_manifest(self._make_manifest(), "Test Feature")
        assert "Test Feature" in md

    def test_requirement_refs_present(self) -> None:
        md = generate_tasks_md_from_manifest(self._make_manifest(), "Test Feature")
        assert "FR-001" in md

    def test_wp_headings_present(self) -> None:
        md = generate_tasks_md_from_manifest(self._make_manifest(), "Test Feature")
        assert "## Work Package WP01" in md
        assert "## Work Package WP02" in md

    def test_prompt_file_shown_when_set(self) -> None:
        manifest = WpsManifest(
            work_packages=[
                WorkPackageEntry(
                    id="WP01",
                    title="With Prompt",
                    prompt_file="tasks/WP01-with-prompt.md",
                )
            ]
        )
        md = generate_tasks_md_from_manifest(manifest, "Feature")
        assert "tasks/WP01-with-prompt.md" in md
