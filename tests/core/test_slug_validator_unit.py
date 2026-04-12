"""Unit tests for slug validator in mission_creation.py (FR-017, FR-018, FR-019)."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from ulid import ULID

from specify_cli.core.mission_creation import KEBAB_CASE_PATTERN, MissionCreationError


class TestKebabCasePattern:
    """Test the KEBAB_CASE_PATTERN regex directly."""

    @pytest.mark.parametrize("slug", [
        "user-auth",                        # letter-prefix (existing, must keep working)
        "fix-bug-123",                      # letter-prefix with numbers
        "new-dashboard",                    # multi-word
        "068-feature-name",                 # digit-prefix (the fix)
        "001-foo",                          # digit-prefix short
        "069-planning-pipeline-integrity",  # real spec-kitty slug
        "123",                              # bare digit (intentionally permissive)
        "a",                                # single letter
        "1",                                # single digit
    ])
    def test_valid_slugs(self, slug: str) -> None:
        assert KEBAB_CASE_PATTERN.match(slug) is not None, f"Expected {slug!r} to match"

    @pytest.mark.parametrize("slug", [
        "",                     # empty (FR-019)
        "User-Auth",            # uppercase (FR-018)
        "user_auth",            # underscore (FR-018)
        "user auth",            # space (FR-018)
        "-starts-with-hyphen",  # leading hyphen
        "ends-with-",           # trailing hyphen
        "double--hyphen",       # double hyphen
        "UPPER",                # all uppercase
    ])
    def test_invalid_slugs(self, slug: str) -> None:
        assert KEBAB_CASE_PATTERN.match(slug) is None, f"Expected {slug!r} to NOT match"


class TestCreateMissionCoreSlugValidation:
    """Integration-level test through create_mission_core() entry point."""

    def test_digit_prefix_slug_accepted(self, tmp_path: Path) -> None:
        """FR-017: digit-prefixed slug does not raise MissionCreationError for slug validation."""
        from specify_cli.core.mission_creation import create_mission_core

        # We only need to verify that slug validation passes; subsequent steps
        # can raise freely. We patch the context guards to isolate slug validation.
        with patch("specify_cli.core.mission_creation.is_worktree_context", return_value=False), \
             patch("specify_cli.core.mission_creation.locate_project_root", return_value=tmp_path), \
             patch("specify_cli.core.mission_creation.is_git_repo", return_value=True), \
             patch("specify_cli.core.mission_creation.get_current_branch", return_value="main"), \
             patch("specify_cli.core.mission_creation.ULID", return_value=ULID.from_str("01KNXQS9ATWWFXS3K5ZJ9E5008")), \
             patch("specify_cli.core.mission_creation._commit_feature_file"):
            # Create the kitty-specs dir so mkdir doesn't fail
            (tmp_path / "kitty-specs").mkdir()
            result = create_mission_core(repo_root=tmp_path, mission_slug="070-new-feature")
            assert result is not None
            assert result.mission_slug.startswith("new-feature-")

    def test_uppercase_slug_still_rejected(self, tmp_path: Path) -> None:
        """FR-018: uppercase slugs are still rejected by slug validation."""
        from specify_cli.core.mission_creation import create_mission_core

        with pytest.raises(MissionCreationError, match="Invalid feature slug"):
            create_mission_core(repo_root=tmp_path, mission_slug="User-Auth")

    def test_underscore_slug_still_rejected(self, tmp_path: Path) -> None:
        """FR-018: slugs with underscores are still rejected."""
        from specify_cli.core.mission_creation import create_mission_core

        with pytest.raises(MissionCreationError, match="Invalid feature slug"):
            create_mission_core(repo_root=tmp_path, mission_slug="user_auth")

    def test_error_message_contains_digit_prefix_example(self, tmp_path: Path) -> None:
        """T036: error message includes a digit-prefix valid example."""
        from specify_cli.core.mission_creation import create_mission_core

        with pytest.raises(MissionCreationError) as exc_info:
            create_mission_core(repo_root=tmp_path, mission_slug="User-Auth")

        error_text = str(exc_info.value)
        assert "068-feature-name" in error_text, "Error message should include digit-prefix example"
        assert "starts with number" not in error_text, "Error message should not mention 'starts with number'"
