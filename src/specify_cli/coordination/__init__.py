"""Coordination workspace package.

Manages per-mission coordination worktrees and lane sparse-checkout policy.

Public surface:

- :class:`CoordinationWorkspace` — resolve / teardown coordination worktree
- :class:`CoordinationWorkspaceBranchMismatch` — structured error
  (``error_code = "COORDINATION_WORKTREE_BRANCH_MISMATCH"``)
- :func:`lane_sparse_checkout_patterns` — pure helper returning the pattern
  lines that lane worktrees use
- :func:`register_lane_sparse_checkout` — apply the sparse-checkout policy
  to a newly created lane worktree

The coordination worktree is the single writer of ``status.events.jsonl`` /
``status.json``. Lane worktrees use git ``sparse-checkout`` (non-cone mode)
to make those two files invisible inside the lane, eliminating any chance
that a lane process accidentally writes them.

See ``contracts/coordination_workspace.md`` and FR-024 / FR-025 / FR-029.
"""

from __future__ import annotations

from specify_cli.coordination.workspace import (
    CoordinationWorkspace,
    CoordinationWorkspaceBranchMismatch,
    lane_sparse_checkout_patterns,
    register_lane_sparse_checkout,
)

__all__ = [
    "CoordinationWorkspace",
    "CoordinationWorkspaceBranchMismatch",
    "lane_sparse_checkout_patterns",
    "register_lane_sparse_checkout",
]
