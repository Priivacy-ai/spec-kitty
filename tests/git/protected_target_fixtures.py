"""Reusable real-git-repo fixtures for the commit-guard protection suite.

Mission ``tooling-stability-guard-coherence-01KTRC04`` (WP01, ATDD-first).
Updated WP01 of ``specify-protected-primary-coherence-01KVMBD6`` (T005 self-check).

These fixtures build **real** git repositories under ``tmp_path`` — no mocks,
following 01KTPKST's mutation-tested precedent. Two things matter for the
commit guard to actually engage (debugger-debby RISK-5):

1. The repo must look like a spec-kitty project — ``_is_spec_kitty_project``
   returns ``True`` only when a ``.kittify/`` directory exists. Without it
   ``assert_not_protected_branch`` short-circuits and the guard is *skipped
   entirely*. The :class:`ProtectedTargetRepo` fixture asserts this precondition
   on itself so a future refactor cannot silently neuter the suite.
2. The target branch must be in the guard's protected set. With no remote
   configured, the resolved set is ``{"main", "master"}`` (NFR-004), so a
   repo whose HEAD is ``main`` is protected hermetically (no network).

T005 verification (WP01 / NFR-004)
-----------------------------------
``assert_target_is_protected`` calls ``commit_helpers.protected_branches()``
which is now a public delegate of
``ProtectionPolicy.resolve(repo_path).protected_branches`` (T002).  The
delegate is intentionally kept public so this fixture and the FR-010 allowlist
continue to work unchanged.  A repo with no ``protection:`` config block yields
``{main, master}`` — byte-identical to the pre-WP01 behaviour (NFR-004).

The :class:`ProtectedTargetRepo` dataclass is exported for WP05's SC-6 e2e
(``specify -> plan -> tasks -> finalize-tasks`` on a protected target). It is
deterministic and tmp-scoped — it leaks no ``test-feature-*`` mission state.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

import pytest

import specify_cli.git.commit_helpers as commit_helpers

# The branch name the fixture's repo is created on. ``main`` is in the guard's
# default protected set, so no remote is required to make it protected.
PROTECTED_TARGET_BRANCH = "main"


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    """Run a git command in ``repo`` and fail loudly on a non-zero exit."""
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )


@dataclass(frozen=True)
class ProtectedTargetRepo:
    """A freshly-built spec-kitty project whose target branch is protected.

    Attributes:
        repo_root: The repository / worktree top-level (they are the same here).
        target_branch: The protected branch HEAD is on (``main``).
    """

    repo_root: Path
    target_branch: str

    def assert_is_spec_kitty_project(self) -> None:
        """Self-check the ``.kittify/`` precondition the guard depends on.

        If this assertion fails, every protection test built on this fixture is
        vacuous — the guard would short-circuit at ``_is_spec_kitty_project``.
        """
        assert (self.repo_root / ".kittify").is_dir(), (
            "fixture precondition violated: .kittify/ missing, so the commit "
            "guard would be skipped entirely (debugger-debby RISK-5)"
        )
        assert commit_helpers._is_spec_kitty_project(self.repo_root), (
            "fixture precondition violated: commit_helpers does not recognize "
            "the repo as a spec-kitty project"
        )

    def assert_target_is_protected(self) -> None:
        """Self-check that the target branch is in the guard's protected set."""
        assert self.target_branch in commit_helpers.protected_branches(self.repo_root), (
            f"fixture precondition violated: {self.target_branch!r} is not in "
            f"the guard's protected set {commit_helpers.protected_branches(self.repo_root)}"
        )

    def write(self, relative_path: str, content: str) -> Path:
        """Create/overwrite a file in the repo and return its absolute path."""
        target = self.repo_root / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return target


def build_protected_target_repo(base_dir: Path) -> ProtectedTargetRepo:
    """Build a real spec-kitty git repo on a protected ``main`` under ``base_dir``.

    Deterministic and hermetic: no remote, no network, fixed identity. The repo
    has a ``.kittify/`` directory (so the guard engages) and an initial commit on
    ``main``. Exported for WP05's SC-6 e2e as well as WP01's own suite.
    """
    repo = base_dir / "protected_target_repo"
    repo.mkdir(parents=True, exist_ok=True)

    _git(repo, "init", "--initial-branch", PROTECTED_TARGET_BRANCH)
    _git(repo, "config", "user.email", "guard-suite@example.com")
    _git(repo, "config", "user.name", "Guard Suite")
    _git(repo, "config", "commit.gpgsign", "false")

    # The .kittify/ marker is what makes _is_spec_kitty_project True. Without it
    # the guard short-circuits — this is the RISK-5 precondition.
    kittify = repo / ".kittify"
    kittify.mkdir()
    (kittify / "config.yaml").write_text("project: guard-suite\n", encoding="utf-8")

    (repo / "README.md").write_text("# Guard suite fixture\n", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-m", "chore: initial commit")

    fixture = ProtectedTargetRepo(repo_root=repo.resolve(), target_branch=PROTECTED_TARGET_BRANCH)
    # Fail loudly here, at construction time, if either precondition is unmet.
    fixture.assert_is_spec_kitty_project()
    fixture.assert_target_is_protected()
    return fixture


@pytest.fixture
def protected_target_repo(tmp_path: Path) -> ProtectedTargetRepo:
    """Fixture wrapper around :func:`build_protected_target_repo` (tmp-scoped)."""
    return build_protected_target_repo(tmp_path)
