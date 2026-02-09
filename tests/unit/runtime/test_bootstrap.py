"""Tests for runtime bootstrap functions.

Covers:
- T028: Version pin warning (F-Pin-001, 1A-16)
"""

from __future__ import annotations

import warnings
from pathlib import Path

import pytest

from specify_cli.runtime.bootstrap import check_version_pin


# ---------------------------------------------------------------------------
# T028 -- Version pin warning (F-Pin-001)
# ---------------------------------------------------------------------------


class TestCheckVersionPin:
    """Tests for check_version_pin() -- acceptance criterion 1A-16."""

    def test_pin_version_emits_warning(self, tmp_path: Path) -> None:
        """F-Pin-001: runtime.pin_version emits warning, uses latest global."""
        project = tmp_path / "project"
        config = project / ".kittify" / "config.yaml"
        config.parent.mkdir(parents=True)
        config.write_text("runtime:\n  pin_version: '1.0.0'\n")

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            check_version_pin(project)

        assert any(
            "pinning is not yet supported" in str(warning.message) for warning in w
        )

    def test_pin_version_warning_contains_pin_value(self, tmp_path: Path) -> None:
        """Warning message includes the actual pinned version."""
        project = tmp_path / "project"
        config = project / ".kittify" / "config.yaml"
        config.parent.mkdir(parents=True)
        config.write_text("runtime:\n  pin_version: '2.5.3'\n")

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            check_version_pin(project)

        user_warnings = [x for x in w if issubclass(x.category, UserWarning)]
        assert len(user_warnings) == 1
        assert "2.5.3" in str(user_warnings[0].message)

    def test_pin_version_warning_says_not_silently_honored(
        self, tmp_path: Path
    ) -> None:
        """Warning explicitly says the pin will NOT be silently honored."""
        project = tmp_path / "project"
        config = project / ".kittify" / "config.yaml"
        config.parent.mkdir(parents=True)
        config.write_text("runtime:\n  pin_version: '1.0.0'\n")

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            check_version_pin(project)

        user_warnings = [x for x in w if issubclass(x.category, UserWarning)]
        assert len(user_warnings) == 1
        assert "NOT be silently honored" in str(user_warnings[0].message)

    def test_no_warning_without_pin_version(self, tmp_path: Path) -> None:
        """No warning emitted when runtime.pin_version is absent."""
        project = tmp_path / "project"
        config = project / ".kittify" / "config.yaml"
        config.parent.mkdir(parents=True)
        config.write_text("runtime:\n  some_other_key: value\n")

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            check_version_pin(project)

        user_warnings = [x for x in w if issubclass(x.category, UserWarning)]
        assert len(user_warnings) == 0

    def test_no_warning_without_runtime_section(self, tmp_path: Path) -> None:
        """No warning when config has no runtime section."""
        project = tmp_path / "project"
        config = project / ".kittify" / "config.yaml"
        config.parent.mkdir(parents=True)
        config.write_text("agents:\n  available:\n    - claude\n")

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            check_version_pin(project)

        user_warnings = [x for x in w if issubclass(x.category, UserWarning)]
        assert len(user_warnings) == 0

    def test_no_warning_without_config_file(self, tmp_path: Path) -> None:
        """No warning when .kittify/config.yaml doesn't exist."""
        project = tmp_path / "project"
        (project / ".kittify").mkdir(parents=True)

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            check_version_pin(project)

        user_warnings = [x for x in w if issubclass(x.category, UserWarning)]
        assert len(user_warnings) == 0

    def test_no_warning_without_kittify_dir(self, tmp_path: Path) -> None:
        """No warning when .kittify directory doesn't exist at all."""
        project = tmp_path / "project"
        project.mkdir(parents=True)

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            check_version_pin(project)

        user_warnings = [x for x in w if issubclass(x.category, UserWarning)]
        assert len(user_warnings) == 0

    def test_empty_config_file(self, tmp_path: Path) -> None:
        """Empty config file doesn't cause errors."""
        project = tmp_path / "project"
        config = project / ".kittify" / "config.yaml"
        config.parent.mkdir(parents=True)
        config.write_text("")

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            check_version_pin(project)

        user_warnings = [x for x in w if issubclass(x.category, UserWarning)]
        assert len(user_warnings) == 0

    def test_malformed_yaml_does_not_crash(self, tmp_path: Path) -> None:
        """Malformed YAML doesn't crash -- config errors handled elsewhere."""
        project = tmp_path / "project"
        config = project / ".kittify" / "config.yaml"
        config.parent.mkdir(parents=True)
        config.write_text(": : : bad yaml [[[")

        # Should not raise
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            check_version_pin(project)

        user_warnings = [x for x in w if issubclass(x.category, UserWarning)]
        assert len(user_warnings) == 0

    def test_runtime_not_a_dict(self, tmp_path: Path) -> None:
        """If runtime is a string or other non-dict, no crash."""
        project = tmp_path / "project"
        config = project / ".kittify" / "config.yaml"
        config.parent.mkdir(parents=True)
        config.write_text("runtime: 'just a string'\n")

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            check_version_pin(project)

        user_warnings = [x for x in w if issubclass(x.category, UserWarning)]
        assert len(user_warnings) == 0

    def test_pin_version_numeric(self, tmp_path: Path) -> None:
        """Pin version specified as a number (not string) still warns."""
        project = tmp_path / "project"
        config = project / ".kittify" / "config.yaml"
        config.parent.mkdir(parents=True)
        config.write_text("runtime:\n  pin_version: 1.0\n")

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            check_version_pin(project)

        user_warnings = [x for x in w if issubclass(x.category, UserWarning)]
        assert len(user_warnings) == 1
        assert "1.0" in str(user_warnings[0].message)
