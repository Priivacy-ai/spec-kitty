"""Rollout gating and readiness evaluation shared across tracker and sync surfaces.

This package exposes the canonical rollout API at the package root so callers
can write ``from specify_cli.saas import is_saas_sync_enabled`` directly.

Readiness (``evaluate_readiness``, ``ReadinessState``) lives in the sibling
module ``specify_cli.saas.readiness`` and is imported via that module path once
WP02 lands.  It is intentionally absent here to keep WP01 ownership clean.
"""

from __future__ import annotations

from specify_cli.saas.rollout import (
    SAAS_SYNC_ENV_VAR,
    is_saas_sync_enabled,
    saas_sync_disabled_message,
)

__all__ = [
    "SAAS_SYNC_ENV_VAR",
    "is_saas_sync_enabled",
    "saas_sync_disabled_message",
]
