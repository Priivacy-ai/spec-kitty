"""Physical hosted-effect boundary for ``agent mission setup-plan``.

Local setup-plan verification deliberately lives in :mod:`mission_setup_plan`.
This module is the sole production owner of that command's hosted sink imports
and calls.  A caller can supply only inert intent data; every physical sink is
dominated by an exact-identity check against the decision authority.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Protocol

from specify_cli.cli.commands.agent.setup_plan_hosted import (
    HostedSyncDecision,
    is_canonical_hosted_sync_decision,
)
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


def _trigger_dossier_sync(
    decision: HostedSyncDecision,
    intent: _DossierSyncIntent,
) -> None:
    """Adapt inert setup-plan coordinates to the established hosted sink."""
    if not is_canonical_hosted_sync_decision(decision):
        return

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
    """Execute setup-plan hosted effects only for the exact issued decision.

    The terminal guard is intentionally adjacent to the physical-effect region.
    It rejects value-equivalent reconstructions, copies, deserializations, and
    forged decisions before any hosted callable is selected or invoked.
    """
    if not is_canonical_hosted_sync_decision(decision):
        return

    for intent in lifecycle_intents:
        fanout_lifecycle_event_hosted(intent.envelope, log_path=intent.log_path)
    if dossier_intent is not None:
        _trigger_dossier_sync(decision, dossier_intent)
