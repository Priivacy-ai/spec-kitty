"""Typed transition context for lane guard evaluation.

Replaces the implicit 8-argument kwargs bag previously threaded
through ``_run_guard()`` with a frozen value object.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from specify_cli.status.models import DoneEvidence, ReviewResult


@dataclass(frozen=True)
class TransitionContext:
    """All inputs needed for guard evaluation during a lane transition."""

    actor: str
    workspace_context: str | None = None  # "worktree" | "direct" | None
    subtasks_complete: bool = False
    evidence: DoneEvidence | None = None  # Required for -> done
    review_ref: str | None = None  # Required for rejection feedback (legacy compat)
    review_result: ReviewResult | None = None  # Required for all in_review -> * transitions
    reason: str | None = None  # Required for -> blocked/canceled
    force: bool = False  # Bypass terminal guard?
    implementation_evidence_present: bool = False  # For -> for_review guard
    current_actor: str | None = None  # Who currently holds the WP (conflict detection)
