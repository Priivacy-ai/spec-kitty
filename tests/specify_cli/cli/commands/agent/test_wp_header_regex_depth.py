"""WP02 / FR-004: Regression tests for WP header regex depth across all 5 sites.

Each site must accept ``##``, ``###``, ``####`` headings and reject ``#####``+.

Sites under test:
1. ``_parse_wp_sections_from_tasks_md()`` in mission.py
2-3. ``_infer_subtasks_complete()`` in emit.py (section start + section end)
4-5. ``_check_unchecked_subtasks()`` in tasks.py (section start + section end)
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Site 1: mission.py — _parse_wp_sections_from_tasks_md()
# ---------------------------------------------------------------------------


pytestmark = [pytest.mark.unit]

class TestParseWpSectionsHeaderDepth:
    """_parse_wp_sections_from_tasks_md must detect WP sections at h2/h3/h4."""

    @pytest.mark.parametrize(
        "depth,expected",
        [
            ("##", True),
            ("###", True),
            ("####", True),
            ("#####", False),
        ],
        ids=["h2", "h3", "h4", "h5-boundary"],
    )
    def test_wp_header_depth(self, depth: str, expected: bool) -> None:
        from specify_cli.cli.commands.agent.mission import _parse_wp_sections_from_tasks_md

        content = f"{depth} WP01: Setup\n\nSome body content\n"
        result = _parse_wp_sections_from_tasks_md(content)
        assert ("WP01" in result) == expected, f"Header '{depth} WP01' should {'be' if expected else 'NOT be'} detected"

    @pytest.mark.parametrize(
        "depth",
        ["##", "###", "####"],
        ids=["h2", "h3", "h4"],
    )
    def test_wp_header_with_work_package_prefix(self, depth: str) -> None:
        """'Work Package' prefix variant must also work at supported depths."""
        from specify_cli.cli.commands.agent.mission import _parse_wp_sections_from_tasks_md

        content = f"{depth} Work Package WP01: Setup\n\nBody\n"
        result = _parse_wp_sections_from_tasks_md(content)
        assert "WP01" in result

    def test_multiple_sections_mixed_depth(self) -> None:
        """Parser must handle mixed heading depths within a single tasks.md."""
        from specify_cli.cli.commands.agent.mission import _parse_wp_sections_from_tasks_md

        content = "## WP01: Setup\n\nWP01 body\n\n### WP02: Core\n\nWP02 body\n\n#### WP03: Tests\n\nWP03 body\n"
        result = _parse_wp_sections_from_tasks_md(content)
        assert set(result.keys()) == {"WP01", "WP02", "WP03"}


# ---------------------------------------------------------------------------
# Sites 2-3: emit.py — _infer_subtasks_complete()
# ---------------------------------------------------------------------------


class TestInferSubtasksCompleteHeaderDepth:
    """_infer_subtasks_complete must detect WP sections at h2/h3/h4."""

    @pytest.mark.parametrize(
        "depth,expected_found",
        [
            ("##", True),
            ("###", True),
            ("####", True),
            ("#####", False),
        ],
        ids=["h2", "h3", "h4", "h5-boundary"],
    )
    def test_wp_section_detection(
        self,
        depth: str,
        expected_found: bool,
        tmp_path: Path,
    ) -> None:
        """WP section start regex must match at h2-h4 depth only."""
        from specify_cli.status.emit import _infer_subtasks_complete

        feature_dir = tmp_path / "kitty-specs" / "test-feature"
        feature_dir.mkdir(parents=True)
        tasks_md = feature_dir / "tasks.md"
        # Build tasks.md with one WP section containing an unchecked subtask
        tasks_md.write_text(
            f"{depth} WP01: Setup\n\n- [ ] T001 Do something\n",
            encoding="utf-8",
        )

        result = _infer_subtasks_complete(feature_dir, "WP01")
        if expected_found:
            # Section found → unchecked task → should return False
            assert result is False, f"Header '{depth} WP01' should be detected, finding unchecked subtask"
        else:
            # Section NOT found → returns True (no section = assumed complete)
            assert result is True, f"Header '{depth} WP01' should NOT be detected (h5 boundary)"

    def test_section_end_boundary(self, tmp_path: Path) -> None:
        """Section-end regex must stop scanning at the next WP heading."""
        from specify_cli.status.emit import _infer_subtasks_complete

        feature_dir = tmp_path / "kitty-specs" / "test-feature"
        feature_dir.mkdir(parents=True)
        tasks_md = feature_dir / "tasks.md"
        # WP01 has all checked; WP02 has unchecked — must NOT bleed.
        tasks_md.write_text(
            "### WP01: Setup\n\n- [x] T001 Done\n\n### WP02: Core\n\n- [ ] T002 Not done\n",
            encoding="utf-8",
        )

        result = _infer_subtasks_complete(feature_dir, "WP01")
        assert result is True, "WP01 section should be complete (unchecked is in WP02)"

    def test_section_end_boundary_h4(self, tmp_path: Path) -> None:
        """Section-end regex must work with #### headings too."""
        from specify_cli.status.emit import _infer_subtasks_complete

        feature_dir = tmp_path / "kitty-specs" / "test-feature"
        feature_dir.mkdir(parents=True)
        tasks_md = feature_dir / "tasks.md"
        tasks_md.write_text(
            "#### WP01: Setup\n\n- [x] T001 Done\n\n#### WP02: Core\n\n- [ ] T002 Not done\n",
            encoding="utf-8",
        )

        result = _infer_subtasks_complete(feature_dir, "WP01")
        assert result is True, "WP01 section should end at #### WP02 boundary"


# ---------------------------------------------------------------------------
# Sites 4-5: tasks.py — _check_unchecked_subtasks()
# ---------------------------------------------------------------------------


class TestCheckUncheckedSubtasksHeaderDepth:
    """_check_unchecked_subtasks must detect WP sections at h2/h3/h4."""

    def _setup_feature(
        self,
        tmp_path: Path,
        tasks_content: str,
        feature_slug: str = "060-test",
    ) -> Path:
        """Create minimal feature directory with tasks.md."""
        feature_dir = tmp_path / "kitty-specs" / feature_slug
        feature_dir.mkdir(parents=True)
        (feature_dir / "tasks.md").write_text(tasks_content, encoding="utf-8")
        return tmp_path  # repo_root

    @pytest.mark.parametrize(
        "depth,expected_found",
        [
            ("##", True),
            ("###", True),
            ("####", True),
            ("#####", False),
        ],
        ids=["h2", "h3", "h4", "h5-boundary"],
    )
    @patch("specify_cli.cli.commands.agent.tasks.get_main_repo_root")
    def test_wp_section_detection(
        self,
        mock_main_root: MagicMock,
        depth: str,
        expected_found: bool,
        tmp_path: Path,
    ) -> None:
        """WP section start regex must match at h2-h4 depth only."""
        from specify_cli.cli.commands.agent.tasks import _check_unchecked_subtasks

        content = f"{depth} WP01: Setup\n\n- [ ] T001 Do something\n"
        repo_root = self._setup_feature(tmp_path, content)
        mock_main_root.return_value = repo_root

        result = _check_unchecked_subtasks(repo_root, "060-test", "WP01", _force=False)
        if expected_found:
            assert len(result) > 0, f"Header '{depth} WP01' should be detected, finding unchecked subtask"
        else:
            assert len(result) == 0, f"Header '{depth} WP01' should NOT be detected (h5 boundary)"

    @patch("specify_cli.cli.commands.agent.tasks.get_main_repo_root")
    def test_section_end_boundary(self, mock_main_root: MagicMock, tmp_path: Path) -> None:
        """Section-end regex must stop scanning at the next WP heading."""
        from specify_cli.cli.commands.agent.tasks import _check_unchecked_subtasks

        content = "### WP01: Setup\n\n- [x] T001 Done\n\n### WP02: Core\n\n- [ ] T002 Not done\n"
        repo_root = self._setup_feature(tmp_path, content)
        mock_main_root.return_value = repo_root

        result = _check_unchecked_subtasks(repo_root, "060-test", "WP01", _force=False)
        assert len(result) == 0, "WP01 section should have no unchecked (unchecked is in WP02)"

    @patch("specify_cli.cli.commands.agent.tasks.get_main_repo_root")
    def test_section_end_boundary_h4(self, mock_main_root: MagicMock, tmp_path: Path) -> None:
        """Section-end regex must work with #### headings too."""
        from specify_cli.cli.commands.agent.tasks import _check_unchecked_subtasks

        content = "#### WP01: Setup\n\n- [x] T001 Done\n\n#### WP02: Core\n\n- [ ] T002 Not done\n"
        repo_root = self._setup_feature(tmp_path, content)
        mock_main_root.return_value = repo_root

        result = _check_unchecked_subtasks(repo_root, "060-test", "WP01", _force=False)
        assert len(result) == 0, "WP01 section should end at #### WP02 boundary"


# ---------------------------------------------------------------------------
# Finding 2: only canonical ``- [ ] T###`` rows block a lane transition.
# Validation/command rows, prose, and fenced code blocks must NOT count.
# ---------------------------------------------------------------------------


class TestCheckUncheckedSubtasksCanonicalOnly:
    """_check_unchecked_subtasks must only block on canonical T### subtasks."""

    def _setup_feature(
        self,
        tmp_path: Path,
        tasks_content: str,
        feature_slug: str = "060-test",
    ) -> Path:
        feature_dir = tmp_path / "kitty-specs" / feature_slug
        feature_dir.mkdir(parents=True)
        (feature_dir / "tasks.md").write_text(tasks_content, encoding="utf-8")
        return tmp_path  # repo_root

    @patch("specify_cli.cli.commands.agent.tasks.get_main_repo_root")
    def test_real_unchecked_tasks_still_block(self, mock_main_root: MagicMock, tmp_path: Path) -> None:
        """Genuine ``- [ ] T###`` rows must still block movement (regression guard)."""
        from specify_cli.cli.commands.agent.tasks import _check_unchecked_subtasks

        content = (
            "## WP01: Setup\n\n"
            "### Included Subtasks\n"
            "- [ ] T001 Create the module\n"
            "- [x] T002 Already done\n"
            "- [ ] T003 Wire it up\n"
        )
        repo_root = self._setup_feature(tmp_path, content)
        mock_main_root.return_value = repo_root

        result = _check_unchecked_subtasks(repo_root, "060-test", "WP01", _force=False)
        assert result == ["T001", "T003"], "Only unchecked canonical T### rows should be reported"

    @patch("specify_cli.cli.commands.agent.tasks.get_main_repo_root")
    def test_validation_command_rows_do_not_block(self, mock_main_root: MagicMock, tmp_path: Path) -> None:
        """Validation/checklist command rows like ``- [ ] swift test`` must NOT block."""
        from specify_cli.cli.commands.agent.tasks import _check_unchecked_subtasks

        content = (
            "## WP01: Setup\n\n"
            "### Included Subtasks\n"
            "- [x] T001 Implement feature\n\n"
            "### Validation\n"
            "- [ ] swift test\n"
            "- [ ] git status --short\n"
            "- [ ] npm run lint\n"
            "- [ ] Review the diff before merging\n"
        )
        repo_root = self._setup_feature(tmp_path, content)
        mock_main_root.return_value = repo_root

        result = _check_unchecked_subtasks(repo_root, "060-test", "WP01", _force=False)
        assert result == [], "Validation/command/prose rows must not be treated as blocking subtasks"

    @patch("specify_cli.cli.commands.agent.tasks.get_main_repo_root")
    def test_fenced_code_task_like_lines_do_not_block(self, mock_main_root: MagicMock, tmp_path: Path) -> None:
        """Task-like lines inside fenced code blocks must NOT block."""
        from specify_cli.cli.commands.agent.tasks import _check_unchecked_subtasks

        content = (
            "## WP01: Setup\n\n"
            "### Included Subtasks\n"
            "- [x] T001 Implement feature\n\n"
            "### Implementation Notes\n"
            "Example task list to mimic in the README:\n"
            "```markdown\n"
            "- [ ] T999 This is documentation, not a real subtask\n"
            "- [ ] T998 Neither is this\n"
            "```\n"
        )
        repo_root = self._setup_feature(tmp_path, content)
        mock_main_root.return_value = repo_root

        result = _check_unchecked_subtasks(repo_root, "060-test", "WP01", _force=False)
        assert result == [], "T### rows inside fenced code blocks must not block"

    @patch("specify_cli.cli.commands.agent.tasks.get_main_repo_root")
    def test_mixed_real_and_noise(self, mock_main_root: MagicMock, tmp_path: Path) -> None:
        """Real unchecked T### blocks even when surrounded by command/code noise."""
        from specify_cli.cli.commands.agent.tasks import _check_unchecked_subtasks

        content = (
            "## WP01: Setup\n\n"
            "### Included Subtasks\n"
            "- [ ] T001 Real unchecked subtask\n"
            "- [ ] swift test\n"
            "```sh\n"
            "- [ ] T500 fenced noise\n"
            "```\n"
            "- [ ] git status --short\n"
        )
        repo_root = self._setup_feature(tmp_path, content)
        mock_main_root.return_value = repo_root

        result = _check_unchecked_subtasks(repo_root, "060-test", "WP01", _force=False)
        assert result == ["T001"], "Only the canonical unchecked T### should be reported"
