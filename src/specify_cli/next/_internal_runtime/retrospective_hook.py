"""Thin caller into retrospective.gate from next runtime.

This module is the only ``next/``-located module owned by WP05.  It wraps
``specify_cli.retrospective.gate.is_completion_allowed`` in a typed exception
so callers in ``next/`` can catch ``MissionCompletionBlocked`` without importing
from the retrospective package directly.

WP06 wires the actual call from the existing ``next/`` control flow.
"""

from __future__ import annotations

from pathlib import Path

from specify_cli.retrospective.gate import (
    GateDecision,
    is_completion_allowed,
)


class MissionCompletionBlocked(Exception):
    """Raised when the gate refuses mission completion.

    Callers should inspect ``.decision`` for structured information about why
    completion was blocked, and surface ``decision.reason.code`` and
    ``decision.reason.detail`` to the operator.
    """

    def __init__(self, decision: GateDecision) -> None:
        self.decision = decision
        super().__init__(
            f"Mission completion blocked: {decision.reason.code}: {decision.reason.detail}"
        )


def before_mark_done(
    mission_id: str,
    *,
    feature_dir: Path,
    repo_root: Path,
) -> None:
    """Refuse to mark the mission done if the gate says no.

    This is the canonical hook that the ``next`` control loop calls before
    transitioning a mission to ``done``.  If the gate allows completion,
    this function returns normally.  If the gate blocks completion,
    :exc:`MissionCompletionBlocked` is raised.

    Args:
        mission_id: Canonical ULID mission identity.
        feature_dir: Path to ``kitty-specs/<slug>/``.
        repo_root: Repository root.

    Raises:
        MissionCompletionBlocked: if the gate returns ``allow_completion=False``.
        specify_cli.retrospective.gate.MissionIdentityMissing: if
            ``mission_id`` is empty.
        specify_cli.retrospective.gate.EventLogUnreadable: if the event log
            cannot be parsed.
        specify_cli.retrospective.mode.ModeResolutionError: if mode
            resolution fails.
    """
    decision = is_completion_allowed(
        mission_id=mission_id,
        feature_dir=feature_dir,
        repo_root=repo_root,
    )
    if not decision.allow_completion:
        raise MissionCompletionBlocked(decision)
