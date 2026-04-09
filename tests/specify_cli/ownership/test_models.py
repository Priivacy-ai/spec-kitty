"""Tests for ownership.models — ExecutionMode and OwnershipManifest."""

from __future__ import annotations

from typing import Any

import pytest

from specify_cli.ownership.models import ExecutionMode, OwnershipManifest
from specify_cli.status.wp_metadata import WPMetadata


# ---------------------------------------------------------------------------
# ExecutionMode
# ---------------------------------------------------------------------------


class TestExecutionMode:
    def test_exactly_two_values(self) -> None:
        values = [m.value for m in ExecutionMode]
        assert sorted(values) == ["code_change", "planning_artifact"]

    def test_is_str_enum(self) -> None:
        assert isinstance(ExecutionMode.CODE_CHANGE, str)
        assert str(ExecutionMode.CODE_CHANGE) == "code_change"
        assert str(ExecutionMode.PLANNING_ARTIFACT) == "planning_artifact"

    def test_construction_from_string(self) -> None:
        assert ExecutionMode("code_change") is ExecutionMode.CODE_CHANGE
        assert ExecutionMode("planning_artifact") is ExecutionMode.PLANNING_ARTIFACT

    def test_invalid_value_raises(self) -> None:
        with pytest.raises(ValueError):
            ExecutionMode("unknown_mode")


# ---------------------------------------------------------------------------
# OwnershipManifest
# ---------------------------------------------------------------------------


class TestOwnershipManifest:
    def _make(self, **kwargs: Any) -> OwnershipManifest:
        defaults: dict[str, Any] = {
            "execution_mode": ExecutionMode.CODE_CHANGE,
            "owned_files": ("src/specify_cli/ownership/**",),
            "authoritative_surface": "src/specify_cli/ownership/",
        }
        defaults.update(kwargs)
        return OwnershipManifest(**defaults)

    def test_basic_creation(self) -> None:
        m = self._make()
        assert m.execution_mode == ExecutionMode.CODE_CHANGE
        assert "src/specify_cli/ownership/**" in m.owned_files
        assert m.authoritative_surface == "src/specify_cli/ownership/"

    def test_frozen(self) -> None:
        m = self._make()
        with pytest.raises((AttributeError, TypeError)):
            m.execution_mode = ExecutionMode.PLANNING_ARTIFACT  # type: ignore[misc]

    def test_owned_files_is_tuple(self) -> None:
        m = self._make(owned_files=("a/**", "b/**"))
        assert isinstance(m.owned_files, tuple)

    # from_frontmatter ---

    def test_from_frontmatter_roundtrip(self) -> None:
        data = {
            "execution_mode": "code_change",
            "owned_files": ["src/foo/**", "tests/foo/**"],
            "authoritative_surface": "src/foo/",
        }
        m = OwnershipManifest.from_frontmatter(data)
        assert m.execution_mode == ExecutionMode.CODE_CHANGE
        assert m.owned_files == ("src/foo/**", "tests/foo/**")
        assert m.authoritative_surface == "src/foo/"

    def test_from_frontmatter_planning_artifact(self) -> None:
        data = {
            "execution_mode": "planning_artifact",
            "owned_files": ["kitty-specs/001-feature/**"],
            "authoritative_surface": "kitty-specs/001-feature/",
        }
        m = OwnershipManifest.from_frontmatter(data)
        assert m.execution_mode == ExecutionMode.PLANNING_ARTIFACT

    def test_from_frontmatter_missing_owned_files_defaults_to_empty(self) -> None:
        data = {
            "execution_mode": "code_change",
            "authoritative_surface": "src/",
        }
        m = OwnershipManifest.from_frontmatter(data)
        assert m.owned_files == ()

    def test_from_frontmatter_invalid_mode_raises(self) -> None:
        with pytest.raises(ValueError):
            OwnershipManifest.from_frontmatter({"execution_mode": "bad_value", "owned_files": [], "authoritative_surface": ""})

    # to_frontmatter ---

    def test_to_frontmatter(self) -> None:
        m = self._make(
            owned_files=("src/foo/**",),
            authoritative_surface="src/foo/",
        )
        result = m.to_frontmatter()
        assert result["execution_mode"] == "code_change"
        assert result["owned_files"] == ["src/foo/**"]
        assert result["authoritative_surface"] == "src/foo/"

    def test_roundtrip_via_frontmatter(self) -> None:
        m = self._make(
            execution_mode=ExecutionMode.PLANNING_ARTIFACT,
            owned_files=("kitty-specs/001/**", "docs/001/**"),
            authoritative_surface="kitty-specs/001/",
        )
        data = m.to_frontmatter()
        restored = OwnershipManifest.from_frontmatter(data)
        assert restored == m


class TestOwnershipManifestFromWPMetadata:
    """from_frontmatter() accepts WPMetadata in addition to raw dicts."""

    def test_accepts_wp_metadata(self) -> None:
        meta = WPMetadata(
            work_package_id="WP01",
            title="T",
            execution_mode="code_change",
            owned_files=["src/foo/**"],
            authoritative_surface="src/foo/",
        )
        m = OwnershipManifest.from_frontmatter(meta)
        assert m.execution_mode == ExecutionMode.CODE_CHANGE
        assert m.owned_files == ("src/foo/**",)
        assert m.authoritative_surface == "src/foo/"

    def test_wp_metadata_missing_owned_files_defaults_empty(self) -> None:
        meta = WPMetadata(
            work_package_id="WP01",
            title="T",
            execution_mode="code_change",
            authoritative_surface="src/",
        )
        m = OwnershipManifest.from_frontmatter(meta)
        assert m.owned_files == ()

    def test_wp_metadata_missing_execution_mode_raises(self) -> None:
        meta = WPMetadata(
            work_package_id="WP01",
            title="T",
        )
        with pytest.raises(KeyError, match="execution_mode"):
            OwnershipManifest.from_frontmatter(meta)

    def test_wp_metadata_planning_artifact(self) -> None:
        meta = WPMetadata(
            work_package_id="WP01",
            title="T",
            execution_mode="planning_artifact",
            owned_files=["kitty-specs/001/**"],
            authoritative_surface="kitty-specs/001/",
        )
        m = OwnershipManifest.from_frontmatter(meta)
        assert m.execution_mode == ExecutionMode.PLANNING_ARTIFACT

    def test_wp_metadata_same_result_as_dict(self) -> None:
        """WPMetadata path produces identical result to equivalent dict."""
        data: dict[str, Any] = {
            "execution_mode": "code_change",
            "owned_files": ["src/bar/**"],
            "authoritative_surface": "src/bar/",
        }
        meta = WPMetadata(
            work_package_id="WP01",
            title="T",
            execution_mode="code_change",
            owned_files=["src/bar/**"],
            authoritative_surface="src/bar/",
        )
        from_dict = OwnershipManifest.from_frontmatter(data)
        from_meta = OwnershipManifest.from_frontmatter(meta)
        assert from_dict == from_meta
