"""Tests for tasks_support module, particularly git worktree handling."""

from pathlib import Path
import pytest
from specify_cli.tasks_support import find_repo_root, activity_entries, TaskCliError


def test_find_repo_root_normal_repo(tmp_path):
    """Test find_repo_root in a normal git repository."""
    # Create a normal repo structure
    git_dir = tmp_path / ".git"
    git_dir.mkdir()

    # Should find the repo root
    result = find_repo_root(tmp_path)
    assert result == tmp_path


def test_find_repo_root_with_kittify(tmp_path):
    """Test find_repo_root with .kittify directory."""
    # Create .kittify directory
    kittify_dir = tmp_path / ".kittify"
    kittify_dir.mkdir()

    # Should find the repo root via .kittify
    result = find_repo_root(tmp_path)
    assert result == tmp_path


def test_find_repo_root_worktree(tmp_path):
    """Test find_repo_root follows worktree .git file to main repo.

    find_repo_root detects when .git is a file (worktree pointer) and follows
    the gitdir pointer back to the main repository. This prevents nested
    worktree creation bugs.
    """
    # Set up main repo
    main_repo = tmp_path / "main-repo"
    main_repo.mkdir()
    git_dir = main_repo / ".git"
    git_dir.mkdir()
    worktrees_dir = git_dir / "worktrees"
    worktrees_dir.mkdir()

    # Create worktree structure
    worktree_git_dir = worktrees_dir / "feature-branch"
    worktree_git_dir.mkdir()

    worktree = tmp_path / "worktrees" / "feature-branch"
    worktree.mkdir(parents=True)

    # Create .git file in worktree (points to main repo)
    git_file = worktree / ".git"
    git_file.write_text(f"gitdir: {worktree_git_dir}\n")

    # Create .kittify in worktree (copied/symlinked from main)
    kittify_worktree = worktree / ".kittify"
    kittify_worktree.mkdir()

    # find_repo_root follows the .git file pointer back to main repo
    # This is critical for preventing nested worktree creation
    result = find_repo_root(worktree)
    assert result == main_repo, (
        f"Expected main repo {main_repo}, got {result}. "
        "find_repo_root should follow worktree .git pointer to main repo."
    )


def test_find_repo_root_worktree_with_subdirs(tmp_path):
    """Test find_repo_root walks up from subdirectories and follows to main repo."""
    # Set up main repo
    main_repo = tmp_path / "main-repo"
    main_repo.mkdir()
    git_dir = main_repo / ".git"
    git_dir.mkdir()
    worktrees_dir = git_dir / "worktrees"
    worktrees_dir.mkdir()

    # Create worktree structure
    worktree_git_dir = worktrees_dir / "feature-branch"
    worktree_git_dir.mkdir()

    worktree = tmp_path / "worktrees" / "feature-branch"
    worktree.mkdir(parents=True)

    # Create .git file in worktree
    git_file = worktree / ".git"
    git_file.write_text(f"gitdir: {worktree_git_dir}\n")

    # Create subdirectory in worktree
    subdir = worktree / "src" / "deep" / "path"
    subdir.mkdir(parents=True)

    # find_repo_root walks up, finds worktree .git file, follows to main repo
    result = find_repo_root(subdir)
    assert result == main_repo


def test_find_repo_root_no_git(tmp_path):
    """Test find_repo_root raises error when no .git or .kittify found."""
    # Empty directory with no git
    with pytest.raises(TaskCliError, match="Unable to locate repository root"):
        find_repo_root(tmp_path)


def test_find_repo_root_malformed_worktree_git_file(tmp_path):
    """Test find_repo_root continues searching when .git file is malformed.

    find_repo_root now tries to parse .git files to follow worktree pointers.
    If the .git file is malformed, it continues searching upward for a valid
    repo marker (.git directory or .kittify directory).
    """
    # Create worktree with malformed .git file
    worktree = tmp_path / "worktree"
    worktree.mkdir()

    git_file = worktree / ".git"
    git_file.write_text("invalid content\n")

    # find_repo_root tries to parse .git file, fails, continues searching
    # Since there's no valid repo marker above, it should raise TaskCliError
    with pytest.raises(TaskCliError, match="Unable to locate repository root"):
        find_repo_root(worktree)


def test_find_repo_root_walks_upward(tmp_path):
    """Test find_repo_root walks upward through parent directories."""
    # Create repo at root
    git_dir = tmp_path / ".git"
    git_dir.mkdir()

    # Create deep subdirectory
    deep_dir = tmp_path / "a" / "b" / "c" / "d"
    deep_dir.mkdir(parents=True)

    # Should find repo root from deep subdirectory
    result = find_repo_root(deep_dir)
    assert result == tmp_path


class TestActivityEntries:
    """Tests for activity_entries() parser."""

    def test_parse_simple_agent_name(self):
        """Test parsing activity log with simple agent name (no hyphens)."""
        body = """
## Activity Log

- 2026-01-26T15:00:00Z – cursor – shell_pid=12345 – lane=done – All work complete
"""
        entries = activity_entries(body)
        
        assert len(entries) == 1
        assert entries[0]['timestamp'] == '2026-01-26T15:00:00Z'
        assert entries[0]['agent'] == 'cursor'
        assert entries[0]['shell_pid'] == '12345'
        assert entries[0]['lane'] == 'done'
        assert entries[0]['note'] == 'All work complete'

    def test_parse_hyphenated_agent_name(self):
        """Test parsing activity log with hyphenated agent name.
        
        This is the primary bug fix - agent names like 'cursor-agent',
        'claude-reviewer' should be parsed correctly.
        """
        body = """
## Activity Log

- 2026-01-26T13:50:55Z – claude-reviewer – shell_pid=58988 – lane=done – Review complete
- 2026-01-26T14:00:00Z – cursor-agent – shell_pid=12345 – lane=doing – Started work
"""
        entries = activity_entries(body)
        
        assert len(entries) == 2
        
        # First entry with hyphenated agent name
        assert entries[0]['agent'] == 'claude-reviewer'
        assert entries[0]['shell_pid'] == '58988'
        assert entries[0]['lane'] == 'done'
        
        # Second entry with hyphenated agent name
        assert entries[1]['agent'] == 'cursor-agent'
        assert entries[1]['shell_pid'] == '12345'
        assert entries[1]['lane'] == 'doing'

    def test_parse_multiple_hyphens_in_agent_name(self):
        """Test parsing agent names with multiple hyphens."""
        body = """
- 2026-01-26T10:00:00Z – my-custom-ai-agent – shell_pid=99999 – lane=planned – Starting task
"""
        entries = activity_entries(body)
        
        assert len(entries) == 1
        assert entries[0]['agent'] == 'my-custom-ai-agent'

    def test_parse_without_shell_pid(self):
        """Test parsing activity log without shell_pid (optional field)."""
        body = """
- 2026-01-26T12:00:00Z – system – lane=planned – Auto-generated task
"""
        entries = activity_entries(body)
        
        assert len(entries) == 1
        assert entries[0]['agent'] == 'system'
        assert entries[0]['shell_pid'] == ''
        assert entries[0]['lane'] == 'planned'

    def test_parse_mixed_agent_names(self):
        """Test parsing with mix of simple and hyphenated agent names."""
        body = """
## Activity Log

- 2026-01-25T10:00:00Z – system – lane=planned – Task created
- 2026-01-25T11:00:00Z – cursor-agent – shell_pid=11111 – lane=doing – Started implementation
- 2026-01-25T12:00:00Z – cursor – shell_pid=22222 – lane=for_review – Ready for review
- 2026-01-25T13:00:00Z – claude-reviewer – shell_pid=33333 – lane=done – Approved
"""
        entries = activity_entries(body)
        
        assert len(entries) == 4
        assert entries[0]['agent'] == 'system'
        assert entries[1]['agent'] == 'cursor-agent'
        assert entries[2]['agent'] == 'cursor'
        assert entries[3]['agent'] == 'claude-reviewer'

    def test_parse_with_hyphen_separator(self):
        """Test parsing with regular hyphen separator (not en-dash)."""
        body = """
- 2026-01-26T14:00:00Z - cursor-agent - shell_pid=12345 - lane=doing - Started work
"""
        entries = activity_entries(body)
        
        assert len(entries) == 1
        assert entries[0]['agent'] == 'cursor-agent'
        assert entries[0]['lane'] == 'doing'

    def test_parse_with_en_dash_separator(self):
        """Test parsing with en-dash separator (–, U+2013)."""
        body = """
- 2026-01-26T14:00:00Z – cursor-agent – shell_pid=12345 – lane=doing – Started work
"""
        entries = activity_entries(body)
        
        assert len(entries) == 1
        assert entries[0]['agent'] == 'cursor-agent'
        assert entries[0]['lane'] == 'doing'

    def test_parse_multiline_note(self):
        """Test that note field captures everything to end of line."""
        body = """
- 2026-01-26T14:00:00Z – cursor-agent – shell_pid=12345 – lane=done – Complex note with - hyphens and – dashes
"""
        entries = activity_entries(body)
        
        assert len(entries) == 1
        assert entries[0]['note'] == 'Complex note with - hyphens and – dashes'

    def test_parse_empty_body(self):
        """Test parsing empty body returns empty list."""
        entries = activity_entries("")
        assert entries == []

    def test_parse_no_activity_log_section(self):
        """Test parsing body without Activity Log section returns empty list."""
        body = """
## Some Other Section

This is not an activity log.
"""
        entries = activity_entries(body)
        assert entries == []

    def test_parse_all_lanes(self):
        """Test parsing entries with all possible lane values."""
        body = """
- 2026-01-26T10:00:00Z – agent – shell_pid=1 – lane=planned – Planned
- 2026-01-26T11:00:00Z – agent – shell_pid=2 – lane=doing – Doing
- 2026-01-26T12:00:00Z – agent – shell_pid=3 – lane=for_review – Review
- 2026-01-26T13:00:00Z – agent – shell_pid=4 – lane=done – Done
"""
        entries = activity_entries(body)
        
        assert len(entries) == 4
        assert entries[0]['lane'] == 'planned'
        assert entries[1]['lane'] == 'doing'
        assert entries[2]['lane'] == 'for_review'
        assert entries[3]['lane'] == 'done'
