"""Exact-commit provenance envelope for the team/public projection package.

Every artifact D1 writes embeds one :class:`ExactCommitProvenance` envelope.
It is a pure function of ``(git HEAD, scoped git status)`` — deliberately
carrying no wall-clock field, so two runs against the same commit produce a
byte-identical envelope (§3.3/§6.4 of the D1 contract draft).

Clean-tree detection follows the reviewed shape at
``charter_runtime/preflight/runner.py:_detect_dirty_artifacts``: one scoped
``git status --porcelain`` subprocess call, an explicit timeout, and
fail-closed degradation (``FileNotFoundError``/timeout/non-zero-exit all
report ``tree_clean=False`` — never raise on *detection* failure, never
silently report clean).
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from specify_cli.version_utils import get_version

#: Directories D1's clean-tree check scopes to — the tracked planning/status
#: surfaces this package reads bodies from (mirrors the scope
#: ``charter_runtime/preflight/runner.py`` uses for its own dirty-artifact
#: detection). ``.kittify/derived`` is explicitly EXCLUDED via git pathspec
#: magic: it is where THIS package's own output lands (``write.py``,
#: ``state/contract.py``'s ``derived_mission_views`` family, ``IGNORED``/
#: gitignored by design), so a `publish` run's own writes must never
#: retroactively dirty the very clean-tree check subsequent calls in the same
#: run rely on — self-write-dirties-own-check would make every artifact after
#: the first in a single ``write_team_projection`` invocation spuriously fail
#: `require_clean=True`, even on a project whose `.gitignore` has not yet
#: (re)learned the `.kittify/derived/` entry.
_DIRTY_SCOPE_PATHS: tuple[str, ...] = (
    "kitty-specs",
    ".kittify",
    ":(exclude).kittify/derived",
)

_GIT_STATUS_TIMEOUT_SECS = 5.0
_GIT_REV_PARSE_TIMEOUT_SECS = 5.0


class DirtyTreeError(Exception):
    """Raised when ``require_clean=True`` and the scoped working tree is not clean.

    Also raised when clean-tree detection itself fails (git missing, timeout,
    non-zero exit) — an *undetermined* tree is treated identically to a dirty
    one under ``require_clean=True`` (fail-closed).
    """

    def __init__(self, dirty_paths: tuple[str, ...], error_reason: str | None) -> None:
        self.dirty_paths = dirty_paths
        self.error_reason = error_reason
        detail = error_reason or f"dirty paths: {', '.join(dirty_paths) or '(unknown)'}"
        super().__init__(f"working tree is not clean for attestation: {detail}")


class ExactCommitProvenance(BaseModel):
    """The closed envelope every D1 artifact embeds."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_: Literal["exact_commit_provenance/v1"] = Field(alias="schema")
    repo: Literal["spec-kitty"]
    commit_sha: str = Field(pattern=r"^[0-9a-f]{40}$")
    tree_clean: bool
    generator: Literal["spec-kitty"]
    generator_version: str
    # Deliberately NO generated_at/timestamp field (§6.4): the envelope must
    # be a pure function of (event log, git HEAD, config) or two runs against
    # the same commit would not be byte-identical.


def _run_git(
    args: tuple[str, ...], *, cwd: Path, timeout: float
) -> subprocess.CompletedProcess[str] | None:
    """Run a scoped git subprocess; return ``None`` on any detection failure."""
    try:
        return subprocess.run(
            ["git", *args],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None


def _detect_tree_clean(repo_root: Path) -> tuple[bool, tuple[str, ...], str | None]:
    """Return ``(tree_clean, dirty_paths, error_reason)`` for the scoped tree.

    Mirrors ``charter_runtime/preflight/runner.py:_detect_dirty_artifacts``:
    a single scoped ``git status --porcelain`` call; git-missing/timeout/
    non-zero-exit all degrade to ``tree_clean=False`` with a named
    ``error_reason``, never a raised exception.
    """
    result = _run_git(
        ("status", "--porcelain", "--", *_DIRTY_SCOPE_PATHS),
        cwd=repo_root,
        timeout=_GIT_STATUS_TIMEOUT_SECS,
    )
    if result is None:
        return False, (), "git CLI not available or timed out; cannot determine worktree cleanliness"

    if result.returncode != 0:
        stderr_first = ""
        if result.stderr:
            lines = result.stderr.splitlines()
            stderr_first = lines[0] if lines else ""
        return (
            False,
            (),
            f"git status failed (exit {result.returncode}): {stderr_first}".rstrip(": "),
        )

    if not result.stdout.strip():
        return True, (), None

    dirty_paths = tuple(
        line[3:].strip() for line in result.stdout.splitlines() if line.strip()
    )
    return False, dirty_paths, None


def _resolve_head_sha(repo_root: Path) -> str | None:
    result = _run_git(
        ("rev-parse", "HEAD"), cwd=repo_root, timeout=_GIT_REV_PARSE_TIMEOUT_SECS
    )
    if result is None or result.returncode != 0:
        return None
    sha = result.stdout.strip()
    if len(sha) != 40:
        return None
    return sha


def capture_provenance(
    repo_root: Path,
    *,
    require_clean: bool,
) -> ExactCommitProvenance:
    """Capture the exact-commit provenance envelope for ``repo_root``.

    ``commit_sha`` is ``git rev-parse HEAD`` of ``repo_root`` — the same
    repository whose working tree the caller reads its body from. This is
    "the commit the working tree currently sits on, truthfully labeled," not
    an arbitrary requested commit (§3.4).

    If ``require_clean`` and the scoped tree is not clean (or clean-tree
    detection itself failed), raises :class:`DirtyTreeError` — no fields are
    ever returned for a refused capture.
    """
    tree_clean, dirty_paths, error_reason = _detect_tree_clean(repo_root)

    if require_clean and (not tree_clean or error_reason is not None):
        raise DirtyTreeError(dirty_paths, error_reason)

    commit_sha = _resolve_head_sha(repo_root)
    if commit_sha is None:
        # Unresolvable HEAD is a hard failure in local mode too — there is no
        # meaningful envelope without a commit_sha, and no field for D1 to
        # populate on failure (unlike tree_clean, which has a truthful False).
        if require_clean:
            raise DirtyTreeError(dirty_paths, "git rev-parse HEAD failed or is unavailable")
        raise DirtyTreeError((), "git rev-parse HEAD failed or is unavailable")

    return ExactCommitProvenance(
        schema="exact_commit_provenance/v1",
        repo="spec-kitty",
        commit_sha=commit_sha,
        tree_clean=tree_clean,
        generator="spec-kitty",
        generator_version=get_version(),
    )
