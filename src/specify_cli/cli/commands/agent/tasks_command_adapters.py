"""Coord-router port adapters relocated out of ``tasks.py`` (WP03, #2058/#2305).

Mission ``tasks-py-degod-wave2-01KWH9EQ`` FR-004: the three coord WRITE router
adapters — ``_MoveTaskCoordRouter``, ``_MapReqCoordRouter``,
``_MarkStatusCoordRouter`` — live here, moved VERBATIM from ``tasks.py``.

**Why this module exists** (import-cycle break): the adapters subclass
:class:`RealCoordCommitRouter` from ``specify_cli.agent_tasks_ports`` — the
top-level ports module, which imports downward only. Housing the subclasses in
``tasks.py`` meant any future ports↔commands edge risked a cycle once the
family relocation WPs (WP05–WP08) started importing adapter homes. This module
imports only the ports module, stdlib, and core modules at module scope — and
NEVER ``tasks`` itself (cycle-safe by construction).

**One adapter per port capability** (C-004): these adapters remain the ONLY
implementations of their coord WRITE capabilities. Do not add new adapter
variants here — extend via the port bundle factories in ``tasks.py``.

**Seam bridge** (research.md D1): the method bodies reach the patched seam
symbols (``emit_status_transition_transactional``, ``commit_for_mission``)
through a lazy in-function import of the ``tasks`` module
(``from specify_cli.cli.commands.agent import tasks as _tasks``) and call
``_tasks.<attr>(...)``, so every historical
``@patch("...agent.tasks.<symbol>")`` keeps INTERCEPTING after the move.
``tasks.py`` re-imports the three classes in the explicit ``as`` re-export
form, so ``tasks.<Router>`` stays a module attribute and the
``_default_*_ports`` factories keep constructing via patchable bindings.

Per-symbol routing/interception evidence:
``kitty-specs/tasks-py-degod-wave2-01KWH9EQ/seam-checklist.md`` (Layer 4 of
the parity contract).
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from mission_runtime import MissionArtifactKind
from specify_cli.agent_tasks_ports import (
    CommitArtifactResult,
    CommitStatusResult,
    MissionHandle,
    RealCoordCommitRouter,
)
from specify_cli.core.commit_guard import GuardCapability
from specify_cli.git.protection_policy import ProtectionPolicy
from specify_cli.status import TransitionRequest


class _MoveTaskCoordRouter(RealCoordCommitRouter):
    """Coord WRITE router bound to the ``tasks`` module's patchable symbols.

    Behaviour-identical to :class:`RealCoordCommitRouter`, but re-resolves
    ``emit_status_transition_transactional`` / ``commit_for_mission`` through the
    ``tasks`` module namespace so the established
    ``@patch("...agent.tasks.<symbol>")`` seams the move_task test-suite relies on
    keep intercepting after the WP06 port rewire (the Real adapter binds the
    ``agent_tasks_ports`` copies, which those module-scoped patches do not reach).
    """

    def commit_status(
        self, request: TransitionRequest, *, capability: GuardCapability
    ) -> CommitStatusResult:
        from specify_cli.cli.commands.agent import tasks as _tasks

        event = _tasks.emit_status_transition_transactional(request, capability=capability)
        return CommitStatusResult(event=event, skipped=False)

    def commit_artifact(
        self,
        mission: MissionHandle,
        paths: Sequence[Path],
        message: str,
        *,
        kind: MissionArtifactKind,
        policy: ProtectionPolicy,
    ) -> CommitArtifactResult:
        from specify_cli.cli.commands.agent import tasks as _tasks

        result = _tasks.commit_for_mission(
            mission.repo_root,
            mission.mission_slug,
            tuple(paths),
            message,
            policy,
            kind=kind,
        )
        return CommitArtifactResult(
            status=result.status,
            placement_ref=result.placement_ref,
            commit_hash=result.commit_hash,
            diagnostic=result.diagnostic,
        )


class _MapReqCoordRouter(RealCoordCommitRouter):
    """Coord WRITE router for ``map_requirements``, bound to the ``tasks`` module.

    Behaviour-identical to :class:`RealCoordCommitRouter.commit_artifact`, but (a)
    re-resolves ``commit_for_mission`` through the ``tasks`` module namespace so the
    established ``@patch("...agent.tasks.commit_for_mission")`` seam keeps
    intercepting after the WP07 port rewire, and (b) threads the resolved
    ``target_branch`` so the post-commit ff-advance still fires for a coord write
    (parity with the pre-rewire inline call at the original tasks.py:3257).
    """

    def __init__(self, target_branch: str | None) -> None:
        self._target_branch = target_branch

    def commit_artifact(
        self,
        mission: MissionHandle,
        paths: Sequence[Path],
        message: str,
        *,
        kind: MissionArtifactKind,
        policy: ProtectionPolicy,
    ) -> CommitArtifactResult:
        from specify_cli.cli.commands.agent import tasks as _tasks

        result = _tasks.commit_for_mission(
            mission.repo_root,
            mission.mission_slug,
            tuple(paths),
            message,
            policy,
            kind=kind,
            target_branch=self._target_branch,
        )
        return CommitArtifactResult(
            status=result.status,
            placement_ref=result.placement_ref,
            commit_hash=result.commit_hash,
            diagnostic=result.diagnostic,
        )


class _MarkStatusCoordRouter(RealCoordCommitRouter):
    """Coord WRITE router for ``mark_status``, bound to the ``tasks`` module.

    Behaviour-identical to :meth:`RealCoordCommitRouter.commit_artifact`, but
    re-resolves ``commit_for_mission`` through the ``tasks`` module namespace so the
    established ``@patch("...agent.tasks.commit_for_mission")`` seam keeps
    intercepting after the WP08 port rewire. ``mark_status`` commits the
    ``TASKS_INDEX`` artifact WITHOUT a threaded ``target_branch`` (byte-parity with
    the pre-rewire inline ``commit_for_mission`` call), so this override — unlike
    ``_MapReqCoordRouter`` — does NOT thread one.
    """

    def commit_artifact(
        self,
        mission: MissionHandle,
        paths: Sequence[Path],
        message: str,
        *,
        kind: MissionArtifactKind,
        policy: ProtectionPolicy,
    ) -> CommitArtifactResult:
        from specify_cli.cli.commands.agent import tasks as _tasks

        result = _tasks.commit_for_mission(
            mission.repo_root,
            mission.mission_slug,
            tuple(paths),
            message,
            policy,
            kind=kind,
        )
        return CommitArtifactResult(
            status=result.status,
            placement_ref=result.placement_ref,
            commit_hash=result.commit_hash,
            diagnostic=result.diagnostic,
        )
