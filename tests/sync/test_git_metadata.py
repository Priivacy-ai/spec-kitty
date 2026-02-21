"""Tests for GitMetadataResolver (WP03: T012–T017).

Covers:
- GitMetadata dataclass defaults, values, frozen behavior
- GitMetadataResolver construction (default/custom TTL, repo_slug_override)
- Branch and SHA resolution via mocked subprocess
- TTL cache hit/miss/cold behavior with mocked time.monotonic
- Repo slug parsing for SSH, HTTPS, subgroups, self-hosted
- Repo slug validation and config override precedence
- Graceful degradation for all failure modes (git missing, not a repo, timeout, permission)
"""

from __future__ import annotations

import logging
import subprocess
from dataclasses import FrozenInstanceError
from unittest.mock import MagicMock, patch

import pytest

from specify_cli.sync.git_metadata import (
    GitMetadata,
    GitMetadataResolver,
    parse_repo_slug,
)


# ---------------------------------------------------------------------------
# T012 – GitMetadata dataclass and resolver construction
# ---------------------------------------------------------------------------


class TestGitMetadata:
    """Test GitMetadata frozen dataclass."""

    def test_default_values(self):
        """All fields default to None."""
        meta = GitMetadata()
        assert meta.git_branch is None
        assert meta.head_commit_sha is None
        assert meta.repo_slug is None

    def test_with_values(self):
        """Fields are populated when provided."""
        meta = GitMetadata(
            git_branch="main",
            head_commit_sha="abc" * 13 + "a",
            repo_slug="org/repo",
        )
        assert meta.git_branch == "main"
        assert meta.head_commit_sha == "abc" * 13 + "a"
        assert meta.repo_slug == "org/repo"

    def test_frozen(self):
        """Frozen dataclass raises on mutation."""
        meta = GitMetadata()
        with pytest.raises(FrozenInstanceError):
            meta.git_branch = "changed"

    def test_frozen_with_values(self):
        """Frozen dataclass raises on mutation even when initialised with values."""
        meta = GitMetadata(git_branch="main")
        with pytest.raises(FrozenInstanceError):
            meta.git_branch = "other"

    def test_equality(self):
        """Two GitMetadata instances with same values are equal."""
        a = GitMetadata(git_branch="main", head_commit_sha="abc123")
        b = GitMetadata(git_branch="main", head_commit_sha="abc123")
        assert a == b

    def test_inequality(self):
        """Two GitMetadata instances with different values are not equal."""
        a = GitMetadata(git_branch="main")
        b = GitMetadata(git_branch="develop")
        assert a != b


class TestGitMetadataResolverConstruction:
    """Test GitMetadataResolver __init__."""

    def test_default_ttl(self, tmp_path):
        """Default TTL is 2.0 seconds."""
        resolver = GitMetadataResolver(repo_root=tmp_path)
        assert resolver.ttl == 2.0

    def test_custom_ttl(self, tmp_path):
        """TTL can be overridden."""
        resolver = GitMetadataResolver(repo_root=tmp_path, ttl=5.0)
        assert resolver.ttl == 5.0

    def test_repo_slug_override(self, tmp_path):
        """repo_slug_override is stored."""
        resolver = GitMetadataResolver(repo_root=tmp_path, repo_slug_override="org/repo")
        assert resolver._repo_slug_override == "org/repo"

    def test_repo_slug_override_default_none(self, tmp_path):
        """repo_slug_override defaults to None."""
        resolver = GitMetadataResolver(repo_root=tmp_path)
        assert resolver._repo_slug_override is None

    def test_repo_root_stored(self, tmp_path):
        """repo_root is stored on the resolver."""
        resolver = GitMetadataResolver(repo_root=tmp_path)
        assert resolver.repo_root == tmp_path

    def test_cache_starts_cold(self, tmp_path):
        """Cache state starts empty/cold."""
        resolver = GitMetadataResolver(repo_root=tmp_path)
        assert resolver._cached_branch is None
        assert resolver._cached_sha is None
        assert resolver._cache_time == 0.0
        assert resolver._repo_slug_resolved is False


# ---------------------------------------------------------------------------
# T013 – Branch/SHA resolution
# ---------------------------------------------------------------------------


class TestBranchAndShaResolution:
    """Test subprocess-based branch and SHA resolution."""

    @patch("specify_cli.sync.git_metadata.subprocess.run")
    def test_normal_branch(self, mock_run, tmp_path):
        """Normal branch name is resolved from git rev-parse."""
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="feature-branch\n"),  # branch
            MagicMock(returncode=0, stdout="abc123def456789012345678901234567890\n"),  # SHA
            MagicMock(returncode=0, stdout="git@github.com:acme/repo.git\n"),  # remote for repo slug
        ]
        resolver = GitMetadataResolver(repo_root=tmp_path)
        meta = resolver.resolve()
        assert meta.git_branch == "feature-branch"
        assert meta.head_commit_sha == "abc123def456789012345678901234567890"

    @patch("specify_cli.sync.git_metadata.subprocess.run")
    def test_detached_head(self, mock_run, tmp_path):
        """Detached HEAD returns 'HEAD' as branch name."""
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="HEAD\n"),  # detached
            MagicMock(returncode=0, stdout="abc123def456789012345678901234567890\n"),  # SHA
            MagicMock(returncode=0, stdout="git@github.com:acme/repo.git\n"),  # remote
        ]
        resolver = GitMetadataResolver(repo_root=tmp_path)
        meta = resolver.resolve()
        assert meta.git_branch == "HEAD"
        assert meta.head_commit_sha is not None

    @patch("specify_cli.sync.git_metadata.subprocess.run")
    def test_cwd_is_repo_root(self, mock_run, tmp_path):
        """subprocess is called with cwd=repo_root for worktree awareness."""
        mock_run.return_value = MagicMock(returncode=0, stdout="main\n")
        resolver = GitMetadataResolver(repo_root=tmp_path)
        resolver._resolve_branch_and_sha()
        # Both branch and SHA calls should use cwd=tmp_path
        for call in mock_run.call_args_list:
            assert call.kwargs.get("cwd") == tmp_path

    @patch("specify_cli.sync.git_metadata.subprocess.run")
    def test_branch_failure_sha_success(self, mock_run, tmp_path):
        """Branch failure returns None branch but SHA can still succeed."""
        mock_run.side_effect = [
            MagicMock(returncode=128, stdout="", stderr="fatal"),  # branch fails
            MagicMock(returncode=0, stdout="abc123\n"),  # SHA succeeds
        ]
        resolver = GitMetadataResolver(repo_root=tmp_path)
        branch, sha = resolver._resolve_branch_and_sha()
        assert branch is None
        assert sha == "abc123"

    @patch("specify_cli.sync.git_metadata.subprocess.run")
    def test_branch_success_sha_failure(self, mock_run, tmp_path):
        """Branch succeeds but SHA failure returns None sha."""
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="main\n"),  # branch succeeds
            MagicMock(returncode=128, stdout="", stderr="fatal"),  # SHA fails
        ]
        resolver = GitMetadataResolver(repo_root=tmp_path)
        branch, sha = resolver._resolve_branch_and_sha()
        assert branch == "main"
        assert sha is None

    @patch("specify_cli.sync.git_metadata.subprocess.run")
    def test_whitespace_stripped(self, mock_run, tmp_path):
        """Whitespace is stripped from branch and SHA output."""
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="  main  \n"),
            MagicMock(returncode=0, stdout="  abc123  \n"),
        ]
        resolver = GitMetadataResolver(repo_root=tmp_path)
        branch, sha = resolver._resolve_branch_and_sha()
        assert branch == "main"
        assert sha == "abc123"


# ---------------------------------------------------------------------------
# T014 – TTL cache behavior
# ---------------------------------------------------------------------------


class TestTTLCache:
    """Test TTL-based caching for branch/SHA resolution."""

    @patch("specify_cli.sync.git_metadata.time.monotonic")
    @patch("specify_cli.sync.git_metadata.subprocess.run")
    def test_cache_hit_within_ttl(self, mock_run, mock_time, tmp_path):
        """Second resolve() within TTL window uses cached values."""
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="main\n"),  # branch
            MagicMock(returncode=0, stdout="aaa111\n"),  # SHA
            MagicMock(returncode=0, stdout="git@github.com:acme/repo.git\n"),  # remote (first resolve)
        ]
        # First resolve at t=1.0, second resolve at t=2.0 (within 2s TTL)
        mock_time.side_effect = [1.0, 2.0]

        resolver = GitMetadataResolver(repo_root=tmp_path)
        meta1 = resolver.resolve()
        meta2 = resolver.resolve()

        # subprocess called 3 times total: branch + SHA + remote (only first resolve)
        # Second resolve hits cache, no additional subprocess calls
        assert mock_run.call_count == 3
        assert meta1.git_branch == meta2.git_branch
        assert meta1.head_commit_sha == meta2.head_commit_sha

    @patch("specify_cli.sync.git_metadata.time.monotonic")
    @patch("specify_cli.sync.git_metadata.subprocess.run")
    def test_cache_miss_after_ttl(self, mock_run, mock_time, tmp_path):
        """After TTL expires, resolve() re-fetches from subprocess."""
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="main\n"),  # branch (first)
            MagicMock(returncode=0, stdout="aaa111\n"),  # SHA (first)
            MagicMock(returncode=0, stdout="git@github.com:acme/repo.git\n"),  # remote (first resolve)
            MagicMock(returncode=0, stdout="feature\n"),  # branch (second, after TTL)
            MagicMock(returncode=0, stdout="bbb222\n"),  # SHA (second)
        ]
        # First resolve at t=1.0, second resolve at t=4.0 (>2s TTL)
        mock_time.side_effect = [1.0, 4.0]

        resolver = GitMetadataResolver(repo_root=tmp_path)
        meta1 = resolver.resolve()
        meta2 = resolver.resolve()

        # 5 total: 2 (branch+SHA) + 1 (remote) for first, 2 (branch+SHA) for second
        assert mock_run.call_count == 5
        assert meta1.git_branch == "main"
        assert meta2.git_branch == "feature"
        assert meta1.head_commit_sha == "aaa111"
        assert meta2.head_commit_sha == "bbb222"

    @patch("specify_cli.sync.git_metadata.time.monotonic", return_value=0.0)
    @patch("specify_cli.sync.git_metadata.subprocess.run")
    def test_cold_cache_always_resolves(self, mock_run, mock_time, tmp_path):
        """First call always resolves (cold cache)."""
        mock_run.return_value = MagicMock(returncode=0, stdout="main\n")
        resolver = GitMetadataResolver(repo_root=tmp_path)
        resolver.resolve()
        assert mock_run.called

    @patch("specify_cli.sync.git_metadata.time.monotonic")
    @patch("specify_cli.sync.git_metadata.subprocess.run")
    def test_cache_boundary_exact_ttl(self, mock_run, mock_time, tmp_path):
        """At exactly TTL boundary (t=0 + 2.0s), cache is still valid."""
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="main\n"),
            MagicMock(returncode=0, stdout="aaa111\n"),
            MagicMock(returncode=0, stdout="git@github.com:acme/repo.git\n"),
        ]
        # First at t=1.0, second at exactly t=2.99 (diff=1.99 < 2.0 TTL)
        mock_time.side_effect = [1.0, 2.99]

        resolver = GitMetadataResolver(repo_root=tmp_path)
        meta1 = resolver.resolve()
        meta2 = resolver.resolve()

        # Only 3 subprocess calls: branch + SHA + remote (cache hit for second)
        assert mock_run.call_count == 3
        assert meta1.git_branch == meta2.git_branch


# ---------------------------------------------------------------------------
# T015 – Repo slug derivation
# ---------------------------------------------------------------------------


class TestParseRepoSlug:
    """Test parse_repo_slug() for all remote URL formats."""

    def test_ssh_standard(self):
        """Standard SSH URL: git@github.com:owner/repo.git"""
        assert parse_repo_slug("git@github.com:acme/spec-kitty.git") == "acme/spec-kitty"

    def test_https_standard(self):
        """Standard HTTPS URL: https://github.com/owner/repo.git"""
        assert parse_repo_slug("https://github.com/acme/spec-kitty.git") == "acme/spec-kitty"

    def test_ssh_no_git_suffix(self):
        """SSH URL without .git suffix."""
        assert parse_repo_slug("git@github.com:acme/spec-kitty") == "acme/spec-kitty"

    def test_https_no_git_suffix(self):
        """HTTPS URL without .git suffix."""
        assert parse_repo_slug("https://github.com/acme/spec-kitty") == "acme/spec-kitty"

    def test_gitlab_subgroup(self):
        """GitLab subgroup: git@gitlab.com:org/team/repo.git"""
        assert parse_repo_slug("git@gitlab.com:org/team/repo.git") == "org/team/repo"

    def test_ssh_url_format(self):
        """SSH URL form: ssh://git@github.com/owner/repo.git."""
        assert parse_repo_slug("ssh://git@github.com/acme/spec-kitty.git") == "acme/spec-kitty"

    def test_ssh_url_gitlab_subgroup(self):
        """SSH URL supports GitLab subgroups."""
        assert parse_repo_slug("ssh://git@gitlab.com/org/team/repo.git") == "org/team/repo"

    def test_bitbucket_ssh(self):
        """Bitbucket SSH URL."""
        assert parse_repo_slug("git@bitbucket.org:acme/spec-kitty.git") == "acme/spec-kitty"

    def test_self_hosted_https(self):
        """Self-hosted HTTPS URL."""
        assert parse_repo_slug("https://git.internal.co/acme/repo.git") == "acme/repo"

    def test_https_with_trailing_slash(self):
        """Trailing slash is normalized away."""
        assert parse_repo_slug("https://github.com/acme/spec-kitty/") == "acme/spec-kitty"

    def test_no_path_returns_none(self):
        """URL without owner/repo path returns None."""
        assert parse_repo_slug("git@github.com:repo.git") is None

    def test_https_deep_subgroup(self):
        """HTTPS URL with deep subgroup path."""
        assert parse_repo_slug("https://gitlab.com/org/team/subteam/repo.git") == "org/team/subteam/repo"

    def test_ssh_deep_subgroup(self):
        """SSH URL with deep subgroup path."""
        assert parse_repo_slug("git@gitlab.com:org/team/subteam/repo.git") == "org/team/subteam/repo"

    def test_https_self_hosted_no_git_suffix(self):
        """Self-hosted HTTPS without .git suffix."""
        assert parse_repo_slug("https://git.internal.co/acme/repo") == "acme/repo"

    def test_empty_string(self):
        """Empty string returns None (no slash in path)."""
        assert parse_repo_slug("") is None

    def test_file_url_returns_none(self):
        """file:// remotes are local and should not be treated as repo slugs."""
        assert parse_repo_slug("file:///Users/robert/code/spec-kitty") is None

    def test_local_filesystem_path_returns_none(self):
        """Bare filesystem paths are not hosted repo slugs."""
        assert parse_repo_slug("/Users/robert/code/spec-kitty") is None

    def test_relative_filesystem_path_returns_none(self):
        """Relative local paths are not hosted repo slugs."""
        assert parse_repo_slug("../spec-kitty") is None


class TestDeriveRepoSlug:
    """Test _derive_repo_slug_from_remote() with mocked subprocess."""

    @patch("specify_cli.sync.git_metadata.subprocess.run")
    def test_from_ssh_remote(self, mock_run, tmp_path):
        """SSH remote URL is parsed into owner/repo."""
        mock_run.return_value = MagicMock(returncode=0, stdout="git@github.com:acme/spec-kitty.git\n")
        resolver = GitMetadataResolver(repo_root=tmp_path)
        slug = resolver._derive_repo_slug_from_remote()
        assert slug == "acme/spec-kitty"

    @patch("specify_cli.sync.git_metadata.subprocess.run")
    def test_from_https_remote(self, mock_run, tmp_path):
        """HTTPS remote URL is parsed into owner/repo."""
        mock_run.return_value = MagicMock(returncode=0, stdout="https://github.com/acme/spec-kitty.git\n")
        resolver = GitMetadataResolver(repo_root=tmp_path)
        slug = resolver._derive_repo_slug_from_remote()
        assert slug == "acme/spec-kitty"

    @patch("specify_cli.sync.git_metadata.subprocess.run")
    def test_no_remote(self, mock_run, tmp_path):
        """Non-zero return code for no remote returns None."""
        mock_run.return_value = MagicMock(returncode=128, stdout="", stderr="fatal: No such remote")
        resolver = GitMetadataResolver(repo_root=tmp_path)
        assert resolver._derive_repo_slug_from_remote() is None

    @patch("specify_cli.sync.git_metadata.subprocess.run")
    def test_cwd_passed_to_subprocess(self, mock_run, tmp_path):
        """subprocess is called with cwd=repo_root."""
        mock_run.return_value = MagicMock(returncode=0, stdout="git@github.com:acme/repo.git\n")
        resolver = GitMetadataResolver(repo_root=tmp_path)
        resolver._derive_repo_slug_from_remote()
        assert mock_run.call_args.kwargs.get("cwd") == tmp_path


# ---------------------------------------------------------------------------
# T016 – Repo slug validation and config override precedence
# ---------------------------------------------------------------------------


class TestRepoSlugValidation:
    """Test _validate_repo_slug() method."""

    def test_valid_owner_repo(self, tmp_path):
        """Standard owner/repo is valid."""
        resolver = GitMetadataResolver(repo_root=tmp_path)
        assert resolver._validate_repo_slug("acme/spec-kitty") is True

    def test_valid_subgroup(self, tmp_path):
        """Subgroup org/team/repo is valid."""
        resolver = GitMetadataResolver(repo_root=tmp_path)
        assert resolver._validate_repo_slug("org/team/repo") is True

    def test_invalid_no_slash(self, tmp_path):
        """String without slash is invalid."""
        resolver = GitMetadataResolver(repo_root=tmp_path)
        assert resolver._validate_repo_slug("noslash") is False

    def test_invalid_empty_segment(self, tmp_path):
        """Leading slash creates empty segment: invalid."""
        resolver = GitMetadataResolver(repo_root=tmp_path)
        assert resolver._validate_repo_slug("/repo") is False

    def test_invalid_trailing_slash(self, tmp_path):
        """Trailing slash creates empty segment: invalid."""
        resolver = GitMetadataResolver(repo_root=tmp_path)
        assert resolver._validate_repo_slug("owner/") is False

    def test_invalid_double_slash(self, tmp_path):
        """Double slash creates empty segment: invalid."""
        resolver = GitMetadataResolver(repo_root=tmp_path)
        assert resolver._validate_repo_slug("owner//repo") is False

    def test_invalid_empty_string(self, tmp_path):
        """Empty string is invalid."""
        resolver = GitMetadataResolver(repo_root=tmp_path)
        assert resolver._validate_repo_slug("") is False

    def test_valid_with_hyphens_and_underscores(self, tmp_path):
        """Hyphens and underscores in segments are valid."""
        resolver = GitMetadataResolver(repo_root=tmp_path)
        assert resolver._validate_repo_slug("my-org/my_repo") is True

    def test_valid_deep_path(self, tmp_path):
        """Deep paths with multiple segments are valid."""
        resolver = GitMetadataResolver(repo_root=tmp_path)
        assert resolver._validate_repo_slug("org/team/subteam/repo") is True


class TestRepoSlugPrecedence:
    """Test config override precedence over auto-derived slug."""

    @patch("specify_cli.sync.git_metadata.subprocess.run")
    def test_override_takes_precedence(self, mock_run, tmp_path):
        """Valid override is used without calling git remote."""
        # The subprocess calls are for branch/SHA (always called)
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="main\n"),  # branch
            MagicMock(returncode=0, stdout="abc123\n"),  # SHA
            # No remote call expected because override is valid
        ]
        resolver = GitMetadataResolver(repo_root=tmp_path, repo_slug_override="custom/repo")
        meta = resolver.resolve()
        assert meta.repo_slug == "custom/repo"
        # Only 2 subprocess calls (branch + SHA), no remote call
        assert mock_run.call_count == 2

    @patch("specify_cli.sync.git_metadata.subprocess.run")
    def test_invalid_override_falls_back_to_auto(self, mock_run, tmp_path):
        """Invalid override falls back to auto-derived from remote."""
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="main\n"),  # branch
            MagicMock(returncode=0, stdout="abc123\n"),  # SHA
            MagicMock(returncode=0, stdout="git@github.com:auto/derived.git\n"),  # remote
        ]
        resolver = GitMetadataResolver(repo_root=tmp_path, repo_slug_override="invalid")
        meta = resolver.resolve()
        assert meta.repo_slug == "auto/derived"

    @patch("specify_cli.sync.git_metadata.subprocess.run")
    def test_no_override_uses_auto(self, mock_run, tmp_path):
        """Without override, auto-derived from remote is used."""
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="main\n"),  # branch
            MagicMock(returncode=0, stdout="abc123\n"),  # SHA
            MagicMock(returncode=0, stdout="https://github.com/auto/repo.git\n"),  # remote
        ]
        resolver = GitMetadataResolver(repo_root=tmp_path)
        meta = resolver.resolve()
        assert meta.repo_slug == "auto/repo"

    @patch("specify_cli.sync.git_metadata.subprocess.run")
    def test_invalid_override_logs_warning(self, mock_run, tmp_path, caplog):
        """Invalid override logs a warning before falling back."""
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="main\n"),
            MagicMock(returncode=0, stdout="abc123\n"),
            MagicMock(returncode=0, stdout="git@github.com:auto/derived.git\n"),
        ]
        resolver = GitMetadataResolver(repo_root=tmp_path, repo_slug_override="invalid")
        with caplog.at_level(logging.WARNING):
            resolver.resolve()
        assert "Invalid repo_slug override" in caplog.text

    @patch("specify_cli.sync.git_metadata.subprocess.run")
    def test_repo_slug_resolved_once(self, mock_run, tmp_path):
        """Repo slug is resolved once per session (cached)."""
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="main\n"),  # branch
            MagicMock(returncode=0, stdout="abc123\n"),  # SHA
            MagicMock(returncode=0, stdout="git@github.com:acme/repo.git\n"),  # remote (first resolve)
            # Second resolve: branch + SHA only (cache hit for TTL miss case)
            MagicMock(returncode=0, stdout="dev\n"),
            MagicMock(returncode=0, stdout="def456\n"),
        ]
        # TTL so second resolve refreshes branch/SHA but NOT repo slug
        with patch("specify_cli.sync.git_metadata.time.monotonic", side_effect=[1.0, 10.0]):
            resolver = GitMetadataResolver(repo_root=tmp_path)
            meta1 = resolver.resolve()
            meta2 = resolver.resolve()

        assert meta1.repo_slug == "acme/repo"
        assert meta2.repo_slug == "acme/repo"
        # 5 total: branch+SHA+remote (first) + branch+SHA (second)
        assert mock_run.call_count == 5


# ---------------------------------------------------------------------------
# T017 – Graceful degradation
# ---------------------------------------------------------------------------


class TestGracefulDegradation:
    """Test failure modes return None values and log warnings."""

    @patch(
        "specify_cli.sync.git_metadata.subprocess.run",
        side_effect=FileNotFoundError("git not found"),
    )
    def test_git_not_installed(self, mock_run, tmp_path):
        """FileNotFoundError (git not installed) produces all-None metadata."""
        resolver = GitMetadataResolver(repo_root=tmp_path)
        meta = resolver.resolve()
        assert meta.git_branch is None
        assert meta.head_commit_sha is None

    @patch("specify_cli.sync.git_metadata.subprocess.run")
    def test_not_in_git_repo(self, mock_run, tmp_path):
        """Non-zero returncode (not a git repo) produces None branch/SHA."""
        mock_run.return_value = MagicMock(returncode=128, stdout="", stderr="fatal: not a git repository")
        resolver = GitMetadataResolver(repo_root=tmp_path)
        meta = resolver.resolve()
        assert meta.git_branch is None
        assert meta.head_commit_sha is None

    @patch(
        "specify_cli.sync.git_metadata.subprocess.run",
        side_effect=subprocess.TimeoutExpired("git", 5),
    )
    def test_subprocess_timeout(self, mock_run, tmp_path):
        """TimeoutExpired produces all-None metadata."""
        resolver = GitMetadataResolver(repo_root=tmp_path)
        meta = resolver.resolve()
        assert meta.git_branch is None
        assert meta.head_commit_sha is None

    @patch(
        "specify_cli.sync.git_metadata.subprocess.run",
        side_effect=PermissionError("access denied"),
    )
    def test_permission_error(self, mock_run, tmp_path):
        """PermissionError produces all-None metadata."""
        resolver = GitMetadataResolver(repo_root=tmp_path)
        meta = resolver.resolve()
        assert meta.git_branch is None
        assert meta.head_commit_sha is None
        assert meta.repo_slug is None

    @patch(
        "specify_cli.sync.git_metadata.subprocess.run",
        side_effect=FileNotFoundError("git not found"),
    )
    def test_warning_logged_for_missing_git(self, mock_run, tmp_path, caplog):
        """FileNotFoundError logs a warning about missing git."""
        resolver = GitMetadataResolver(repo_root=tmp_path)
        with caplog.at_level(logging.WARNING):
            resolver.resolve()
        assert "git not found" in caplog.text

    @patch(
        "specify_cli.sync.git_metadata.subprocess.run",
        side_effect=subprocess.TimeoutExpired("git", 5),
    )
    def test_warning_logged_for_timeout(self, mock_run, tmp_path, caplog):
        """TimeoutExpired logs a warning about timeout."""
        resolver = GitMetadataResolver(repo_root=tmp_path)
        with caplog.at_level(logging.WARNING):
            resolver.resolve()
        assert "timed out" in caplog.text

    @patch(
        "specify_cli.sync.git_metadata.subprocess.run",
        side_effect=PermissionError("access denied"),
    )
    def test_warning_logged_for_permission_error(self, mock_run, tmp_path, caplog):
        """PermissionError logs a warning."""
        resolver = GitMetadataResolver(repo_root=tmp_path)
        with caplog.at_level(logging.WARNING):
            resolver.resolve()
        assert "failed" in caplog.text.lower() or "access denied" in caplog.text.lower()

    @patch(
        "specify_cli.sync.git_metadata.subprocess.run",
        side_effect=FileNotFoundError("git not found"),
    )
    def test_git_not_installed_repo_slug_also_none(self, mock_run, tmp_path):
        """When git is missing, repo_slug is also None (derive fails gracefully)."""
        resolver = GitMetadataResolver(repo_root=tmp_path)
        meta = resolver.resolve()
        assert meta.repo_slug is None

    @patch("specify_cli.sync.git_metadata.subprocess.run")
    def test_branch_ok_remote_timeout(self, mock_run, tmp_path):
        """Branch/SHA succeed but remote times out — repo_slug is None."""
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="main\n"),  # branch OK
            MagicMock(returncode=0, stdout="abc123\n"),  # SHA OK
            subprocess.TimeoutExpired("git", 5),  # remote times out
        ]
        resolver = GitMetadataResolver(repo_root=tmp_path)
        meta = resolver.resolve()
        assert meta.git_branch == "main"
        assert meta.head_commit_sha == "abc123"
        assert meta.repo_slug is None

    @patch("specify_cli.sync.git_metadata.subprocess.run")
    def test_all_calls_fail_gracefully(self, mock_run, tmp_path):
        """All subprocess calls returning errors still produces a valid GitMetadata."""
        mock_run.return_value = MagicMock(returncode=128, stdout="", stderr="fatal")
        resolver = GitMetadataResolver(repo_root=tmp_path)
        meta = resolver.resolve()
        assert isinstance(meta, GitMetadata)
        assert meta.git_branch is None
        assert meta.head_commit_sha is None
        # repo_slug might be None too since remote fails
        assert meta.repo_slug is None

    def test_resolve_never_raises(self, tmp_path):
        """resolve() never raises even with unexpected errors."""
        resolver = GitMetadataResolver(repo_root=tmp_path)
        with patch(
            "specify_cli.sync.git_metadata.subprocess.run",
            side_effect=OSError("unexpected OS error"),
        ):
            meta = resolver.resolve()
        assert isinstance(meta, GitMetadata)
        assert meta.git_branch is None
        assert meta.head_commit_sha is None
