"""Git metadata resolution for per-event observability context.

Provides:
- GitMetadata frozen dataclass — per-event git state (branch, SHA, repo slug,
  remote host)
- GitMetadataResolver — resolves git metadata with TTL cache
- parse_repo_slug() — extracts owner/repo from SSH or HTTPS remote URLs
- parse_remote_host() — extracts the bare hostname from the same remote URL
"""

from __future__ import annotations

import logging
import re
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


_SCP_LIKE_REMOTE_RE = re.compile(r"^(?:[^@/]+@)?(?P<host>[^:/]+):(?P<path>.+)$")


@dataclass(frozen=True)
class GitMetadata:
    """Volatile git state resolved per-event. Not persisted."""

    git_branch: str | None = None
    head_commit_sha: str | None = None
    repo_slug: str | None = None
    remote_host: str | None = None


def parse_repo_slug(url: str) -> str | None:
    """Parse owner/repo-style slug from hosted git remote URL.

    Supports:
    - SSH: git@github.com:owner/repo.git
    - HTTPS: https://github.com/owner/repo.git
    - SSH URL: ssh://git@github.com/owner/repo.git
    - GitLab subgroups: git@gitlab.com:org/team/repo.git

    Args:
        url: Git remote URL

    Returns:
        owner/repo-style slug (supports subgroups), or None if unparseable
        or not a hosted remote URL.
    """
    cleaned_url = url.strip()
    if not cleaned_url:
        return None

    parsed = urlparse(cleaned_url)
    path: str | None

    # Explicitly reject local-file remotes and bare filesystem paths.
    if parsed.scheme == "file":
        return None
    if cleaned_url.startswith(("/", "./", "../")):
        return None

    # URL-form remotes (https://, ssh://, git://, etc.)
    if parsed.scheme and parsed.netloc:
        path = parsed.path
    else:
        # SCP-like SSH form (git@host:owner/repo.git)
        match = _SCP_LIKE_REMOTE_RE.match(cleaned_url)
        if not match:
            return None
        path = match.group("path")

    normalized_path = path.strip().lstrip("/").rstrip("/")
    if normalized_path.endswith(".git"):
        normalized_path = normalized_path[:-4]

    if not normalized_path:
        return None

    segments = [segment for segment in normalized_path.split("/") if segment]
    if len(segments) < 2:
        return None

    return "/".join(segments)


def parse_remote_host(url: str) -> str | None:
    """Parse the bare hostname from a hosted git remote URL.

    Supports the same remote URL forms as :func:`parse_repo_slug` (SSH,
    HTTPS, ``ssh://`` URLs, and SCP-like ``user@host:path`` remotes) and
    applies the same local/file-remote rejections, so a URL is either
    parseable by both functions or by neither. Returns the hostname with
    no user info and no port, or ``None`` if unparseable or not a hosted
    remote URL.

    Args:
        url: Git remote URL

    Returns:
        Bare hostname (e.g. ``github.com``), or None if unparseable or
        not a hosted remote URL.
    """
    cleaned_url = url.strip()
    if not cleaned_url:
        return None

    parsed = urlparse(cleaned_url)

    # Explicitly reject local-file remotes and bare filesystem paths.
    if parsed.scheme == "file":
        return None
    if cleaned_url.startswith(("/", "./", "../")):
        return None

    # URL-form remotes (https://, ssh://, git://, etc.)
    if parsed.scheme and parsed.netloc:
        return parsed.hostname

    # SCP-like SSH form (git@host:owner/repo.git)
    match = _SCP_LIKE_REMOTE_RE.match(cleaned_url)
    if not match:
        return None
    return match.group("host")


class GitMetadataResolver:
    """Resolves per-event git metadata with TTL cache.

    One instance per EventEmitter. Branch/SHA are cached with a TTL
    (default 2 seconds) since they change frequently. Repo slug is
    resolved once per session since the remote URL is stable.

    All failures produce None values — never raises exceptions.
    """

    DEFAULT_TTL: float = 2.0

    def __init__(
        self,
        repo_root: Path,
        ttl: float = DEFAULT_TTL,
        repo_slug_override: str | None = None,
    ) -> None:
        self.repo_root = repo_root
        self.ttl = ttl
        self._repo_slug_override = repo_slug_override
        # Cache state for branch/SHA (TTL-based)
        self._cached_branch: str | None = None
        self._cached_sha: str | None = None
        self._cache_time: float = 0.0
        # Repo slug (session-level, resolved once)
        self._cached_repo_slug: str | None = None
        self._repo_slug_resolved: bool = False
        # Remote host (session-level, resolved once; independent of the
        # repo_slug override, since an override carries no host information).
        # Shares the cached remote URL fetch below with repo-slug derivation
        # so a session issues at most one `git remote get-url origin` call.
        self._cached_remote_host: str | None = None
        self._remote_host_resolved: bool = False
        self._cached_remote_url: str | None = None
        self._remote_url_fetched: bool = False

    def resolve(self) -> GitMetadata:
        """Return current git state. Uses TTL cache for branch/SHA.

        Returns:
            GitMetadata with best-effort values (None for unavailable fields)
        """
        now = time.monotonic()

        # Check TTL for branch/SHA
        if now - self._cache_time < self.ttl and self._cache_time > 0:
            branch = self._cached_branch
            sha = self._cached_sha
        else:
            branch, sha = self._resolve_branch_and_sha()
            self._cached_branch = branch
            self._cached_sha = sha
            self._cache_time = now

        # Repo slug and remote host: resolved once per session (stable)
        repo_slug = self._resolve_repo_slug()
        remote_host = self._resolve_remote_host()

        return GitMetadata(
            git_branch=branch,
            head_commit_sha=sha,
            repo_slug=repo_slug,
            remote_host=remote_host,
        )

    def _resolve_branch_and_sha(self) -> tuple[str | None, str | None]:
        """Resolve current branch and HEAD SHA via git subprocess."""
        try:
            # Get branch name
            branch_result = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                cwd=self.repo_root,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=5,
            )
            branch = branch_result.stdout.strip() if branch_result.returncode == 0 else None

            # Get HEAD SHA
            sha_result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=self.repo_root,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=5,
            )
            sha = sha_result.stdout.strip() if sha_result.returncode == 0 else None

            return branch, sha
        except FileNotFoundError:
            logger.warning("git not found; git metadata unavailable")
            return None, None
        except subprocess.TimeoutExpired:
            logger.warning("git command timed out")
            return None, None
        except Exception as e:
            logger.warning("git metadata resolution failed: %s", e)
            return None, None

    def _resolve_repo_slug(self) -> str | None:
        """Resolve repo slug: config override > auto-derived > None."""
        if self._repo_slug_resolved:
            return self._cached_repo_slug

        self._repo_slug_resolved = True

        # Check config override first
        if self._repo_slug_override:
            if self._validate_repo_slug(self._repo_slug_override):
                self._cached_repo_slug = self._repo_slug_override
                return self._cached_repo_slug
            else:
                logger.warning(
                    "Invalid repo_slug override '%s' (expected owner/repo format); falling back to auto-derived",
                    self._repo_slug_override,
                )

        # Auto-derive from remote
        self._cached_repo_slug = self._derive_repo_slug_from_remote()
        return self._cached_repo_slug

    def _fetch_remote_url(self) -> str | None:
        """Fetch and cache the ``origin`` remote URL (resolved once per session).

        Shared by :meth:`_derive_repo_slug_from_remote` and
        :meth:`_resolve_remote_host` so a session issues at most one
        ``git remote get-url origin`` subprocess call even though both the
        slug and the host are derived from it.
        """
        if self._remote_url_fetched:
            return self._cached_remote_url

        self._remote_url_fetched = True
        try:
            result = subprocess.run(
                ["git", "remote", "get-url", "origin"],
                cwd=self.repo_root,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=5,
            )
            if result.returncode != 0:
                return None

            self._cached_remote_url = result.stdout.strip()
            return self._cached_remote_url
        except FileNotFoundError:
            logger.warning("git not found; cannot resolve remote URL")
            return None
        except subprocess.TimeoutExpired:
            logger.warning("git remote command timed out")
            return None
        except Exception as e:
            logger.warning("remote URL resolution failed: %s", e)
            return None

    def _derive_repo_slug_from_remote(self) -> str | None:
        """Extract owner/repo from git remote origin URL."""
        url = self._fetch_remote_url()
        return parse_repo_slug(url) if url else None

    def _resolve_remote_host(self) -> str | None:
        """Resolve remote host from git remote origin URL (resolved once per session).

        Independent of ``repo_slug_override``: an override supplies only a
        slug, never a host, so the host is always derived from the actual
        ``origin`` remote regardless of whether the slug was overridden.
        """
        if self._remote_host_resolved:
            return self._cached_remote_host

        self._remote_host_resolved = True
        url = self._fetch_remote_url()
        self._cached_remote_host = parse_remote_host(url) if url else None
        return self._cached_remote_host

    def _validate_repo_slug(self, slug: str) -> bool:
        """Validate repo slug has at least one / with non-empty segments.

        Args:
            slug: Candidate repo slug string

        Returns:
            True if slug is valid (e.g., 'owner/repo' or 'org/team/repo')
        """
        if "/" not in slug:
            return False
        parts = slug.split("/")
        return all(part.strip() for part in parts)
