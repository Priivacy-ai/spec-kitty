"""Physical hosted-effect boundary for ``agent mission setup-plan``.

Local setup-plan verification deliberately lives in :mod:`mission_setup_plan`.
This module is the sole production owner of that command's hosted sink imports
and calls.  Lifecycle SaaS fan-out is a genuine hosted egress effect and is
dominated by the decision's affirmative verdict before its sink is ever
selected.  Dossier capture is project-isolated LOCAL capture per
:func:`trigger_feature_dossier_sync_if_enabled`'s own contract — the machine
SaaS flag and project egress decision are enforced later by the canonical
dispatcher and therefore cannot suppress it — so it runs unconditionally here,
matching every sibling command that captures a mission dossier.
"""

from __future__ import annotations

import contextlib
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Protocol

from specify_cli.cli.commands.agent.setup_plan_hosted import HostedSyncDecision
from specify_cli.status.lifecycle_events import fanout_lifecycle_event_hosted
from specify_cli.sync.dossier_pipeline import (
    trigger_feature_dossier_sync_if_enabled,
)


class _LifecycleEventIntent(Protocol):
    """Inert local lifecycle data accepted by the hosted boundary."""

    @property
    def envelope(self) -> Mapping[str, object]: ...

    @property
    def log_path(self) -> Path: ...


class _DossierSyncIntent(Protocol):
    """Inert dossier coordinates accepted by the hosted boundary."""

    @property
    def feature_dir(self) -> Path: ...

    @property
    def mission_slug(self) -> str: ...

    @property
    def repo_root(self) -> Path: ...


def _fanout_lifecycle_events(
    decision: HostedSyncDecision,
    lifecycle_intents: Iterable[_LifecycleEventIntent],
) -> None:
    """Adapt inert lifecycle envelopes to the hosted SaaS fan-out sink.

    The terminal guard is intentionally adjacent to the physical-effect region:
    no sink is reachable unless :func:`decide_hosted_sync` affirmed this
    decision.
    """
    if not decision.allow_effects:
        return
    for intent in lifecycle_intents:
        fanout_lifecycle_event_hosted(intent.envelope, log_path=intent.log_path)


def _trigger_dossier_sync(intent: _DossierSyncIntent) -> None:
    """Trigger local-only dossier capture; never suppressed by hosted refusal."""
    with contextlib.suppress(Exception):
        trigger_feature_dossier_sync_if_enabled(
            intent.feature_dir,
            intent.mission_slug,
            intent.repo_root,
        )


def execute_setup_plan_hosted_effects(
    decision: HostedSyncDecision,
    *,
    lifecycle_intents: Iterable[_LifecycleEventIntent],
    dossier_intent: _DossierSyncIntent | None,
) -> None:
    """Execute setup-plan's hosted-adjacent effects.

    Lifecycle fan-out is gated on the exact issued decision; dossier capture
    is unconditional local capture and is never suppressed by it.
    """
    _fanout_lifecycle_events(decision, lifecycle_intents)
    if dossier_intent is not None:
        _trigger_dossier_sync(dossier_intent)
