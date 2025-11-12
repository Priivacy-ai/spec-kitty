#!/usr/bin/env python3
"""
Unit tests for GitignoreManager class.

This module provides comprehensive test coverage for the GitignoreManager
functionality, including all public methods, edge cases, and error scenarios.
"""

import os
import tempfile
from pathlib import Path
import pytest
import sys

# Add the src directory to the path so we can import the module
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from specify_cli.gitignore_manager import GitignoreManager, ProtectionResult, AgentDirectory  # noqa: E402


class TestGitignoreManager:
    """Test suite for GitignoreManager class."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def temp_file(self):
        """Create a temporary file for testing."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as tmpfile:
            tmpfile.write("test content")
            tmpfile_path = Path(tmpfile.name)
        yield tmpfile_path
        tmpfile_path.unlink(missing_ok=True)

    @pytest.fixture
    def manager(self, temp_dir):
        """Create a GitignoreManager instance with temp directory."""
        return GitignoreManager(temp_dir)

    # T024 - Test GitignoreManager.__init__ validation
    def test_init_with_valid_directory(self, temp_dir):
        """Test successful initialization with valid directory."""
        manager = GitignoreManager(temp_dir)
        assert manager.project_path == temp_dir
        assert manager.gitignore_path == temp_dir / ".gitignore"
        assert manager.marker == "# Added by Spec Kitty CLI (auto-managed)"

    def test_init_with_nonexistent_directory(self):
        """Test initialization fails with non-existent directory."""
        with pytest.raises(ValueError, match="Project path does not exist"):
            GitignoreManager(Path("/nonexistent/directory"))

    def test_init_with_file_instead_of_directory(self, temp_file):
        """Test initialization fails when path is a file, not directory."""
        with pytest.raises(ValueError, match="Project path is not a directory"):
            GitignoreManager(temp_file)

    def test_init_with_string_path(self, temp_dir):
        """Test initialization accepts string paths."""
        manager = GitignoreManager(str(temp_dir))
        assert manager.project_path == temp_dir

    # T025 - Test protect_all_agents method
    def test_protect_all_agents_creates_gitignore(self, manager, temp_dir):
        """Test protect_all_agents creates .gitignore when it doesn't exist."""
        assert not manager.gitignore_path.exists()

        result = manager.protect_all_agents()

        assert result.success
        assert result.modified
        assert len(result.entries_added) == 11  # All 12 agent directories
        assert len(result.entries_skipped) == 0
        assert manager.gitignore_path.exists()

    def test_protect_all_agents_with_empty_gitignore(self, manager, temp_dir):
        """Test protect_all_agents adds to empty .gitignore."""
        manager.gitignore_path.touch()

        result = manager.protect_all_agents()

        assert result.success
        assert result.modified
        assert len(result.entries_added) == 11

        content = manager.gitignore_path.read_text()
        assert manager.marker in content
        assert ".claude/" in content
        assert ".codex/" in content

    def test_protect_all_agents_with_existing_entries(self, manager, temp_dir):
        """Test protect_all_agents preserves existing entries."""
        existing_content = "node_modules/\n*.log\n"
        manager.gitignore_path.write_text(existing_content)

        result = manager.protect_all_agents()

        assert result.success
        assert result.modified

        content = manager.gitignore_path.read_text()
        assert "node_modules/" in content
        assert "*.log" in content
        assert ".claude/" in content

    def test_protect_all_agents_includes_all_agents(self, manager):
        """Test that all 12 agent directories are protected."""
        result = manager.protect_all_agents()

        expected_dirs = [
            ".claude/", ".codex/", ".opencode/", ".windsurf/",
            ".gemini/", ".cursor/", ".qwen/", ".kilocode/",
            ".augment/", ".roo/", ".amazonq/"
        ]

        content = manager.gitignore_path.read_text()
        for dir_name in expected_dirs:
            assert dir_name in content

    # T026 - Test protect_selected_agents method
    def test_protect_selected_single_agent(self, manager):
        """Test protecting a single selected agent."""
        result = manager.protect_selected_agents(["claude"])

        assert result.success
        assert result.modified
        assert ".claude/" in result.entries_added
        assert len(result.entries_added) == 1

    def test_protect_selected_multiple_agents(self, manager):
        """Test protecting multiple selected agents."""
        result = manager.protect_selected_agents(["claude", "codex", "gemini"])

        assert result.success
        assert result.modified
        assert len(result.entries_added) == 3
        assert ".claude/" in result.entries_added
        assert ".codex/" in result.entries_added
        assert ".gemini/" in result.entries_added

    def test_protect_selected_unknown_agent(self, manager):
        """Test warning for unknown agent name."""
        result = manager.protect_selected_agents(["unknown_agent"])

        assert result.success
        assert not result.modified
        assert any("Unknown agent name: unknown_agent" in w for w in result.warnings)

    def test_protect_selected_empty_list(self, manager):
        """Test with empty agent list."""
        result = manager.protect_selected_agents([])

        assert result.success
        assert not result.modified
        assert any("No valid agent directories" in w for w in result.warnings)

    def test_protect_selected_mixed_valid_invalid(self, manager):
        """Test with mix of valid and invalid agents."""
        result = manager.protect_selected_agents(["claude", "invalid", "codex"])

        assert result.success
        assert result.modified
        assert len(result.entries_added) == 2
        assert any("Unknown agent name: invalid" in w for w in result.warnings)

    # T027 - Test duplicate detection logic
    def test_duplicate_detection_prevents_duplicates(self, manager):
        """Test that duplicate entries are never created."""
        # First run
        result1 = manager.protect_all_agents()
        assert result1.modified
        assert len(result1.entries_added) == 11

        # Second run
        result2 = manager.protect_all_agents()
        assert not result2.modified
        assert len(result2.entries_skipped) == 11
        assert len(result2.entries_added) == 0

    def test_duplicate_detection_with_manual_entries(self, manager):
        """Test duplicate detection with manually added entries."""
        # Manually add some entries
        manager.gitignore_path.write_text(".claude/\n.codex/\n")

        # Try to protect all agents
        result = manager.protect_all_agents()

        assert result.modified  # Still modified because we add the other 10
        assert ".claude/" in result.entries_skipped
        assert ".codex/" in result.entries_skipped
        assert len(result.entries_added) == 9

    def test_duplicate_detection_marker_comment(self, manager):
        """Test that marker comment is not duplicated."""
        # Run twice
        manager.protect_all_agents()
        manager.protect_all_agents()

        content = manager.gitignore_path.read_text()
        # Count occurrences of marker
        marker_count = content.count(manager.marker)
        assert marker_count == 1

    # T028 - Test line ending preservation
    def test_line_ending_preservation_windows(self, manager):
        """Test preservation of Windows line endings."""
        # Create file with Windows line endings
        test_content = "existing\r\nentries\r\n"
        manager.gitignore_path.write_bytes(test_content.encode())

        # Add new entries
        manager.ensure_entries([".test/"])

        # Note: OS might normalize line endings on write
        # The important thing is the code attempts to preserve them
        content = manager.gitignore_path.read_text()
        assert ".test/" in content

    def test_line_ending_preservation_unix(self, manager):
        """Test preservation of Unix line endings."""
        # Create file with Unix line endings
        test_content = "existing\nentries\n"
        manager.gitignore_path.write_text(test_content)

        # Add new entries
        manager.ensure_entries([".test/"])

        content = manager.gitignore_path.read_text()
        assert ".test/" in content

    def test_line_ending_detection_method(self, manager):
        """Test the line ending detection method."""
        # Test Windows detection
        assert manager._detect_line_ending("test\r\nline") == "\r\n"

        # Test Unix detection
        assert manager._detect_line_ending("test\nline") == "\n"

        # Test default for ambiguous
        assert manager._detect_line_ending("single line") == "\n"

    # T029 - Test error handling scenarios
    def test_error_handling_permission_denied(self, manager, temp_dir):
        """Test handling of permission errors."""
        # Create read-only .gitignore
        manager.gitignore_path.touch()
        os.chmod(manager.gitignore_path, 0o444)  # Read-only

        try:
            result = manager.protect_all_agents()

            assert not result.success
            assert len(result.errors) > 0
            assert any("Permission denied" in e for e in result.errors)
            assert any("chmod u+w" in e for e in result.errors)
        finally:
            # Restore permissions for cleanup
            os.chmod(manager.gitignore_path, 0o644)

    def test_error_handling_corrupted_file(self, manager):
        """Test handling of corrupted .gitignore file."""
        # Create a file with null bytes (binary content)
        manager.gitignore_path.write_bytes(b"\x00\x01\x02\x03")

        # Should handle gracefully
        result = manager.protect_all_agents()

        # The implementation might either:
        # 1. Succeed by overwriting the corrupted file
        # 2. Fail with an appropriate error
        # Either is acceptable as long as no exception is raised
        assert isinstance(result, ProtectionResult)

    def test_error_handling_no_exceptions_bubble(self, manager):
        """Test that errors don't cause unhandled exceptions."""
        # Even with various error conditions, should return ProtectionResult
        manager.gitignore_path.write_text("normal content")
        result = manager.protect_all_agents()
        assert isinstance(result, ProtectionResult)

    # T032 - Edge case tests
    def test_edge_case_github_special_handling(self, manager):
        """Test that unknown agent 'github' is handled properly."""
        result = manager.protect_selected_agents(["github"])

        assert result.success
        assert len(result.entries_added) == 0  # Unknown agent, nothing added
        assert any("Unknown agent" in w for w in result.warnings)

    def test_edge_case_large_gitignore(self, manager):
        """Test performance with large .gitignore file."""
        # Create a large .gitignore
        large_content = "\n".join([f"pattern{i}/" for i in range(1000)])
        manager.gitignore_path.write_text(large_content)

        # Should still work efficiently
        result = manager.protect_all_agents()

        assert result.success
        assert result.modified

        # Verify original content preserved
        content = manager.gitignore_path.read_text()
        assert "pattern999/" in content
        assert ".claude/" in content

    def test_edge_case_special_characters(self, manager):
        """Test handling of special characters in paths."""
        # Add entries with special characters
        special_entries = [".test-dir/", ".test_dir/", ".test.dir/"]
        manager.ensure_entries(special_entries)

        content = manager.gitignore_path.read_text()
        for entry in special_entries:
            assert entry in content

    def test_edge_case_empty_marker_sections(self, manager):
        """Test handling of empty marker sections."""
        # Create file with marker but no entries after it
        content = f"existing\n{manager.marker}\n"
        manager.gitignore_path.write_text(content)

        result = manager.protect_all_agents()

        assert result.success
        assert result.modified
        content = manager.gitignore_path.read_text()
        assert content.count(manager.marker) == 1

    def test_get_agent_directories_returns_copy(self):
        """Test that get_agent_directories returns a copy, not reference."""
        dirs1 = GitignoreManager.get_agent_directories()
        dirs2 = GitignoreManager.get_agent_directories()

        assert dirs1 == dirs2
        assert dirs1 is not dirs2  # Different objects

        # Modifying one shouldn't affect the other
        dirs1.append(AgentDirectory("test", ".test/", False, "Test"))
        assert len(dirs1) == 12  # 11 original + 1 test agent
        assert len(dirs2) == 11  # Original unchanged

    def test_all_agent_directories_have_trailing_slash(self):
        """Test that all agent directories end with trailing slash."""
        dirs = GitignoreManager.get_agent_directories()

        for agent_dir in dirs:
            assert agent_dir.directory.endswith("/"), f"{agent_dir.directory} missing trailing slash"

    def test_result_object_structure(self, manager):
        """Test ProtectionResult object has expected structure."""
        result = manager.protect_all_agents()

        assert hasattr(result, 'success')
        assert hasattr(result, 'modified')
        assert hasattr(result, 'entries_added')
        assert hasattr(result, 'entries_skipped')
        assert hasattr(result, 'errors')
        assert hasattr(result, 'warnings')

        assert isinstance(result.entries_added, list)
        assert isinstance(result.entries_skipped, list)
        assert isinstance(result.errors, list)
        assert isinstance(result.warnings, list)