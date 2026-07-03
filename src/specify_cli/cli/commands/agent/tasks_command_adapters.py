"""Seam-routed coord-router construction for the ``agent tasks`` families.

Mission ``tasks-py-degod-wave2-01KWH9EQ`` FR-004 originally relocated three
``RealCoordCommitRouter`` **subclasses** (``_MoveTaskCoordRouter``,
``_MapReqCoordRouter``, ``_MarkStatusCoordRouter``) out of ``tasks.py``. The
degod-follow-ups pre-merge squad flagged those subclasses as near-triplicated
bodies that bent the one-adapter-per-port rule (C-004) — they existed ONLY to
re-resolve the two WRITE seams through the ``tasks`` namespace (and, for
``map_requirements``, to thread ``target_branch``). This module replaces them
with **constructor DI**: a single production adapter class
(:class:`RealCoordCommitRouter`) plus the two seam-wrapper functions and the
:func:`seam_coord_router` factory below. There is now ZERO per-family
duplication and exactly one production coord adapter class.

**Why this module still exists** (import-cycle break): the seam wrappers and the
factory reference :class:`RealCoordCommitRouter` from
``specify_cli.agent_tasks_ports`` — the top-level ports module, which imports
downward only. Keeping the seam construction here (never in ``tasks.py``) means
this module imports only the ports module, stdlib, and core modules at module
scope, and NEVER ``tasks`` itself at import time (cycle-safe by construction).
The tasks-namespace resolution happens LAZILY, inside the seam wrappers, at call
time.

**Seam bridge / late binding** (research.md D1): the two wrappers
:func:`_seam_commit_for_mission` / :func:`_seam_emit_status_transition_transactional`
do a lazy in-function import of the ``tasks`` module
(``from specify_cli.cli.commands.agent import tasks as _tasks``) and call
``_tasks.<attr>(...)``, so a ``@patch("...agent.tasks.<symbol>")`` applied AFTER
router construction still INTERCEPTS. ``tasks.py`` re-exports
:func:`seam_coord_router` (explicit ``as`` re-export) so the ``_default_*_ports``
factories construct through a patchable ``tasks.seam_coord_router`` binding.

Per-symbol routing/interception evidence:
``kitty-specs/tasks-py-degod-wave2-01KWH9EQ/seam-checklist.md`` (Layer 4 of
the parity contract).
"""

from __future__ import annotations

from specify_cli.agent_tasks_ports import (
    RealCoordCommitRouter,
    _CommitForMissionFn,
    _EmitTransactionalFn,
)
from specify_cli.coordination.commit_router import CommitRouterResult
from specify_cli.status import StatusEvent


def _seam_commit_for_mission(*args: object, **kwargs: object) -> CommitRouterResult:
    """Route ``commit_for_mission`` through the ``tasks`` module at CALL time.

    The lazy import + ``_tasks.<attr>`` indirection is the seam bridge: a
    ``@patch("...agent.tasks.commit_for_mission")`` applied after the router is
    constructed still intercepts, because the symbol is resolved here on every
    call rather than bound once at construction (research.md D1).
    """
    from specify_cli.cli.commands.agent import tasks as _tasks

    # The router already decided the exact positional/keyword shape (C-001
    # byte-parity branches in ``RealCoordCommitRouter.commit_artifact``); this
    # wrapper is a transparent passthrough. Pin the lazily-resolved namespace
    # symbol to the declared seam-injection contract (``_CommitForMissionFn`` =
    # ``Callable[..., CommitRouterResult]``) so whole-tree mypy checks the return
    # precisely while honouring the open forwarded arg-list the seam requires.
    routed: _CommitForMissionFn = _tasks.commit_for_mission
    result: CommitRouterResult = routed(*args, **kwargs)
    return result


def _seam_emit_status_transition_transactional(
    *args: object, **kwargs: object
) -> StatusEvent:
    """Route ``emit_status_transition_transactional`` through ``tasks`` at CALL time.

    Same late-binding contract as :func:`_seam_commit_for_mission`: keeps the
    ``@patch("...agent.tasks.emit_status_transition_transactional")`` seam live
    for the ``move_task`` family (the only family whose coord router routes the
    transactional emitter through the ``tasks`` namespace).
    """
    from specify_cli.cli.commands.agent import tasks as _tasks

    # Same transparent-passthrough contract as ``_seam_commit_for_mission``: the
    # router keys the exact call shape, this wrapper only re-routes the symbol
    # through the ``tasks`` namespace. Pin to ``_EmitTransactionalFn`` =
    # ``Callable[..., StatusEvent]`` for a precise return under whole-tree mypy.
    routed: _EmitTransactionalFn = _tasks.emit_status_transition_transactional
    event: StatusEvent = routed(*args, **kwargs)
    return event


def seam_coord_router(
    *,
    thread_target_branch: bool = False,
    target_branch: str | None = None,
    route_emit: bool = False,
) -> RealCoordCommitRouter:
    """Build the production coord router with its WRITE seams routed via ``tasks``.

    Single construction helper for all three coord families (C-004, one adapter
    per port). ``commit_artifact`` always routes ``commit_for_mission`` through
    the ``tasks`` namespace (every family relies on that seam). The two knobs
    reproduce the exact pre-collapse per-family divergence (C-001):

    * ``route_emit`` — route ``emit_status_transition_transactional`` through the
      ``tasks`` namespace too. ONLY ``move_task`` set this (it was the only
      subclass to override ``commit_status``); ``map_requirements`` /
      ``mark_status`` inherited the base emitter binding, so they leave it
      ``False``.
    * ``thread_target_branch`` / ``target_branch`` — thread the resolved primary
      branch into ``commit_for_mission`` for the post-commit ff-advance. ONLY
      ``map_requirements`` set this; ``move_task`` / ``mark_status`` committed
      target-branch-less (byte-parity with the pre-rewire inline calls).
    """
    return RealCoordCommitRouter(
        target_branch=target_branch,
        thread_target_branch=thread_target_branch,
        commit_fn=_seam_commit_for_mission,
        emit_fn=(
            _seam_emit_status_transition_transactional if route_emit else None
        ),
    )
