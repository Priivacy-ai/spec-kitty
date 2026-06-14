"""Templated git-repo fixture (WP06 / A3 / PP-03).

The test suite runs a real ``git init`` + initial commit in ~233 files for the
common "needs a baseline git repo" case. That is the single most repeated
per-test subprocess cost in the fast-sync / charter / agent-cli / dashboard
shards.

This package replaces that pattern with a **build-once, clone-per-test**
strategy:

* :func:`_template_repo` builds **one** bare repo (with a single initial commit)
  per process, lazily, into a temp dir. It is cached for the lifetime of the
  process. Because every ``xdist`` worker is a *separate process*, the cache is
  per-worker and therefore parallel-safe by construction — no cross-worker
  shared mutable state, no lock needed (WP04 isolates ``HOME`` separately).
* :func:`clone_template` does a **local filesystem clone** of that bare template
  into a destination working tree. ``git clone --local`` hardlinks the object
  store and replays the already-present initial commit, which is materially
  cheaper than ``git init`` followed by staging + committing fresh content.
* The :func:`templated_repo` fixture (function-scoped) clones the template into
  the test's ``tmp_path`` and yields a ready-to-use working repo.

Scope (binding, per the WP06 contract):

* The template is a **plain bare repo with one commit** — it deliberately has
  **no** worktrees, **no** detached/unborn HEAD, and is **not** a ``--bare``
  working surface for the consumer. Tests that need those bespoke states keep
  their own explicit ``git init`` setup; this template is only for the common
  baseline case.
* The clone is a normal (non-bare) working tree with ``user.name`` /
  ``user.email`` configured so consumers can commit immediately.
"""

from __future__ import annotations

import subprocess
import tempfile
from collections.abc import Iterator
from functools import lru_cache
from pathlib import Path

import pytest

# Identity baked into the template's initial commit and re-applied to every
# clone so that ``git commit`` works without further configuration. Hoisted to
# module constants (Sonar S1192) because they appear in both the template build
# and the per-clone config step.
_GIT_USER_NAME = "Spec Kitty"
_GIT_USER_EMAIL = "spec@example.com"

# Default branch for the template. ``-b main`` keeps the clone on a predictable
# branch name regardless of the host git's ``init.defaultBranch`` setting.
_DEFAULT_BRANCH = "main"


def _git(*args: str, cwd: Path) -> None:
    """Run a git command in *cwd*, raising on failure with captured output."""
    subprocess.run(
        ["git", *args],
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
    )


def _build_bare_template(into: Path) -> Path:
    """Build the bare template repo under *into* and return its path.

    Builds a normal repo with a single initial commit, then produces a bare
    clone of it. The bare clone is what callers clone *from* (cloning from a
    bare repo avoids ``git clone`` warning about cloning a checked-out branch
    and keeps the source immutable).
    """
    seed = into / "seed"
    seed.mkdir(parents=True, exist_ok=True)
    _git("init", "-b", _DEFAULT_BRANCH, cwd=seed)
    _git("config", "user.name", _GIT_USER_NAME, cwd=seed)
    _git("config", "user.email", _GIT_USER_EMAIL, cwd=seed)
    # A minimal, generic initial commit. Consumers that need their own files add
    # them on top; the point is only that the repo has a committed HEAD so
    # repo-root resolution and "clean tree" checks behave like a real project.
    (seed / "README.md").write_text("# template\n", encoding="utf-8")
    _git("add", "README.md", cwd=seed)
    _git("commit", "-m", "Initial commit", cwd=seed)

    bare = into / "template.git"
    _git("clone", "--bare", str(seed), str(bare), cwd=into)
    return bare


@lru_cache(maxsize=1)
def _template_repo() -> Path:
    """Return the path to the process-cached bare template repo, building once.

    Cached per process via ``lru_cache``; each ``xdist`` worker is its own
    process so the build happens at most once per worker. The template lives
    under a dedicated ``tempfile.mkdtemp`` directory that persists for the
    process lifetime (intentionally not cleaned up — it is a read-only source
    reused across the whole session).
    """
    base = Path(tempfile.mkdtemp(prefix="spec-kitty-git-template-"))
    return _build_bare_template(base)


def clone_template(dest: Path) -> Path:
    """Clone the bare template into *dest* as a working repo and return *dest*.

    A local filesystem clone (``git clone --local``) is far cheaper than
    ``git init`` + initial commit: it hardlinks the template's object store and
    checks out the already-present initial commit. The clone is configured with
    a commit identity so callers can ``git commit`` straight away.

    *dest* must not already exist (git refuses to clone into a non-empty
    directory); callers typically pass a fresh ``tmp_path`` subdirectory.
    """
    template = _template_repo()
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    _git(
        "clone",
        "--local",
        "-b",
        _DEFAULT_BRANCH,
        str(template),
        str(dest),
        cwd=dest.parent,
    )
    _git("config", "user.name", _GIT_USER_NAME, cwd=dest)
    _git("config", "user.email", _GIT_USER_EMAIL, cwd=dest)
    return dest


@pytest.fixture
def templated_repo(tmp_path: Path) -> Iterator[Path]:
    """Function-scoped clone of the bare template into ``tmp_path/repo``.

    Drop-in baseline replacement for the common ``temp_repo``-style fixtures
    that do ``git init`` + ``git config`` + (often) an initial commit. The
    yielded path is a normal working repo with one commit on ``main`` and a
    configured commit identity.

    VCS-detection caches (``is_git_available`` / ``get_git_version``) are
    cleared around the fixture so that detection never observes stale state
    from a prior test — preserving the ``cache_clear()`` semantics the
    repo-root resolver and existing git fixtures rely on.
    """
    from specify_cli.core.vcs.detection import _clear_detection_cache

    _clear_detection_cache()
    repo = clone_template(tmp_path / "repo")
    try:
        yield repo
    finally:
        _clear_detection_cache()
