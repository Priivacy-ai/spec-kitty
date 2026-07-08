"""T027/T028: empty-``mid8`` composition guard at the ``CoordinationWorkspace``
seam (#2091, invariant M-1).

Pre-fix: an empty ``mid8`` silently composes a malformed branch/dir name
(``kitty/mission-<slug>-`` / ``<slug>--coord``, note the trailing/doubled
hyphen from the dropped disambiguator) at the ``CoordinationWorkspace``
composition seam (``worktree_path`` / ``branch_name`` / ``resolve``). Because
the branch was never created, ``resolve()``'s ``git worktree add`` fails far
from the actual defect with an opaque ``subprocess.CalledProcessError`` /
exit-128 — the caller sees a low-level git failure, not an actionable
"mid8 is required" message.

Post-fix: ``CoordinationWorkspace`` fails LOUDLY and immediately with
:class:`CoordinationWorkspaceIdentityUnresolved` (stable ``error_code``)
before any git subprocess is invoked, for all three public composition
entry points.

The ``runtime_bridge.py`` guard (``coord_routing_topology and not _mid8``) is
belt-and-suspenders for ONE call path; this seam-level guard protects EVERY
caller of ``CoordinationWorkspace`` (``commit_router``, ``transaction``,
``surface_resolver``, ``status_transition``, ``_read_path_resolver``, CLI
commands, ``mission_runtime.resolution`` — see the composition-seam callers
audited for WP06), which is the point of guarding at the single canonical
composition authority (C-001) rather than re-deriving the check per caller.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from specify_cli.coordination.workspace import (
    CoordinationWorkspace,
    CoordinationWorkspaceIdentityUnresolved,
)

pytestmark = [pytest.mark.unit, pytest.mark.git_repo]

MISSION_SLUG = "demo-feature"


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)


@pytest.fixture
def bare_repo(tmp_path: Path) -> Path:
    """A minimal git repo — no coordination branch (composition must fail
    before any branch lookup, so none is needed)."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "config", "user.email", "t@example.com")
    _git(repo, "config", "user.name", "Test")
    _git(repo, "config", "commit.gpgsign", "false")
    (repo / "seed.txt").write_text("seed\n")
    _git(repo, "add", "seed.txt")
    _git(repo, "commit", "-q", "-m", "initial")
    return repo


# ---------------------------------------------------------------------------
# Pure entry points — no filesystem/git touch required to observe the guard.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("mid8", ["", None])
def test_worktree_path_rejects_empty_mid8(tmp_path: Path, mid8: str | None) -> None:
    with pytest.raises(CoordinationWorkspaceIdentityUnresolved) as exc_info:
        CoordinationWorkspace.worktree_path(tmp_path, MISSION_SLUG, mid8)  # type: ignore[arg-type]
    assert exc_info.value.error_code == "COORDINATION_WORKSPACE_MID8_REQUIRED"
    assert exc_info.value.mission_slug == MISSION_SLUG


@pytest.mark.parametrize("mid8", ["", None])
def test_branch_name_rejects_empty_mid8(mid8: str | None) -> None:
    with pytest.raises(CoordinationWorkspaceIdentityUnresolved) as exc_info:
        CoordinationWorkspace.branch_name(MISSION_SLUG, mid8)  # type: ignore[arg-type]
    assert exc_info.value.error_code == "COORDINATION_WORKSPACE_MID8_REQUIRED"


# ---------------------------------------------------------------------------
# The composition-seam regression (#2091): resolve() must fail loud BEFORE
# reaching ``git worktree add`` — never the opaque exit-128.
# ---------------------------------------------------------------------------


def test_resolve_rejects_empty_mid8_before_git_worktree_add(bare_repo: Path) -> None:
    """RED-FIRST (T027): pre-fix this raised ``subprocess.CalledProcessError``
    (exit-128) from a malformed ``git worktree add ... kitty/mission-demo-feature-``
    — reproduced directly against pre-fix code:

        subprocess.CalledProcessError: Command '['git', '-C', <repo>, 'worktree',
        'add', <repo>/.worktrees/demo-feature--coord',
        'kitty/mission-demo-feature-']' returned non-zero exit status 128.

    Post-fix: the guard fires before any subprocess call, so no worktree
    directory or git process is ever created for the malformed identity.
    """
    with pytest.raises(CoordinationWorkspaceIdentityUnresolved) as exc_info:
        CoordinationWorkspace.resolve(bare_repo, MISSION_SLUG, "")

    assert exc_info.value.error_code == "COORDINATION_WORKSPACE_MID8_REQUIRED"
    # No malformed worktree directory was created on disk.
    assert not (bare_repo / ".worktrees").exists()


def test_is_present_rejects_empty_mid8(tmp_path: Path) -> None:
    with pytest.raises(CoordinationWorkspaceIdentityUnresolved):
        CoordinationWorkspace.is_present(tmp_path, MISSION_SLUG, "")


def test_teardown_rejects_empty_mid8(tmp_path: Path) -> None:
    with pytest.raises(CoordinationWorkspaceIdentityUnresolved):
        CoordinationWorkspace.teardown(tmp_path, MISSION_SLUG, "")
