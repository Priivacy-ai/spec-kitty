"""Shared low-level git existence-check plumbing for the lanes pipeline.

Consolidates the ``git rev-parse --verify`` branch/ref existence idiom that
was reimplemented across :mod:`specify_cli.coordination.status_transition`,
:mod:`specify_cli.missions._create`,
:mod:`specify_cli.lanes.worktree_allocator`, and
:mod:`specify_cli.lanes.merge` (issue #1904).

Scope is deliberately narrow: this is the existence-CHECK idiom only. Branch
*name* composition stays in :mod:`specify_cli.lanes.branch_naming` (topology
ratchet, mission #132) and is orthogonal to these helpers.

Behavior is byte-identical to the strictest pre-consolidation call site:
``git -C <repo> rev-parse --verify --quiet <refspec>`` with output captured and
``check=False`` (truthy iff returncode == 0). ``-C <repo>`` is equivalent to the
``cwd=<repo>`` form the lanes sites used. ``--quiet`` only suppresses stderr,
which was already swallowed by ``capture_output=True`` at every site, so adding
it changes no observable behavior. ``env`` is parameterized so the merge
pipeline's ``_make_merge_env()`` composes through rather than forking the
helper.
"""

from __future__ import annotations

import subprocess
from pathlib import Path


def _verify(repo_root: Path, refspec: str, *, env: dict[str, str] | None = None) -> bool:
    result = subprocess.run(
        ["git", "-C", str(repo_root), "rev-parse", "--verify", "--quiet", refspec],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    return result.returncode == 0


def branch_exists(repo_root: Path, branch: str, *, env: dict[str, str] | None = None) -> bool:
    """Return True iff a local branch ``branch`` exists in ``repo_root``.

    Resolves ``refs/heads/<branch>`` so only local branch refs (never tags,
    remotes, or arbitrary revspecs) count as existing.
    """
    return _verify(repo_root, f"refs/heads/{branch}", env=env)


def ref_exists(repo_root: Path, ref: str, *, env: dict[str, str] | None = None) -> bool:
    """Return True iff ``ref`` resolves to a commit object in ``repo_root``.

    Distinct from :func:`branch_exists` — this accepts any revspec
    (``main``, ``origin/main``, ``HEAD``, ``2.x``…) and only confirms that git
    can resolve it to a real commit (via the ``<ref>^{commit}`` peel form).
    """
    return _verify(repo_root, f"{ref}^{{commit}}", env=env)
