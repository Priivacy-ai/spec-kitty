"""Mission runtime event emission interface and persistence.

Uses canonical event constants and payload models from spec-kitty-events v2.3.1.
"""

# Internalized from spec-kitty-runtime 0.4.3 as part of
# `shared-package-boundary-cutover-01KQ22DS` (mission). See
# `runtime-standalone-package-retirement-01KQ20Z8` for the upstream
# public-API inventory.
from __future__ import annotations

import json
import logging
import os
from collections.abc import Callable
from pathlib import Path
from typing import Any, Protocol

from spec_kitty_events.mission_next import (
    DECISION_INPUT_ANSWERED,
    DECISION_INPUT_REQUESTED,
    MISSION_RUN_COMPLETED,
    MISSION_RUN_STARTED,
    NEXT_STEP_AUTO_COMPLETED,
    NEXT_STEP_ISSUED,
    DecisionInputAnsweredPayload,
    DecisionInputRequestedPayload,
    MissionRunCompletedPayload,
    MissionRunStartedPayload,
    NextStepAutoCompletedPayload,
    NextStepIssuedPayload,
)
# WP04 (org-doctrine-profile-integrity-closeout, T014): these two payloads
# are imported for use as annotations on the emitter Protocol/impl below
# (``emit_significance_evaluated`` / ``emit_decision_timeout_expired``).
# They are intentionally NOT re-exported in ``__all__`` — consumers resolve
# the canonical payloads from ``significance.py`` directly. Keeping these
# imports (annotation-only) while dropping them from ``__all__`` clears the
# dead-symbol gate without breaking any annotation.
from runtime.next._internal_runtime.significance import (
    SignificanceEvaluatedPayload,
    TimeoutExpiredPayload,
)
# Layer note (dead-port-disposition-01M1VRA2, research R-5): ``runtime`` may import
# ``specify_cli.*`` except ``specify_cli.cli`` / ``specify_cli.next``; both ``core``
# and ``mission_metadata`` are already on the runtime outbound ledger
# (``tests/architectural/test_layer_rules.py``), so these add no ledger entry.
from specify_cli.core.env import is_truthy
from specify_cli.mission_metadata import resolve_mission_identity

# Explicit re-exports so `from runtime.next._internal_runtime.events import X`
# resolves under `mypy --strict` (otherwise `attr-defined` flags the indirected names).
__all__ = [
    "DECISION_INPUT_ANSWERED",
    "DECISION_INPUT_REQUESTED",
    "MISSION_RUN_COMPLETED",
    "MISSION_RUN_STARTED",
    "NEXT_STEP_AUTO_COMPLETED",
    "NEXT_STEP_ISSUED",
    "DecisionInputAnsweredPayload",
    "DecisionInputRequestedPayload",
    "MissionRunCompletedPayload",
    "MissionRunStartedPayload",
    "NextStepAutoCompletedPayload",
    "NextStepIssuedPayload",
    "RuntimeEventEmitter",
    "NullEmitter",
    "JsonlEventLog",
    "seed_runtime_emitter",
    "runtime_emitter_for_mission",
    "register_runtime_emitter_factory",
    "reset_runtime_emitter_factory",
]


# ---------------------------------------------------------------------------
# RuntimeEventEmitter protocol
# ---------------------------------------------------------------------------

class RuntimeEventEmitter(Protocol):
    """Interface for mission runtime event emission.

    All emit methods accept a single canonical payload model from
    spec-kitty-events.mission_next.
    """

    def emit_mission_run_started(self, payload: MissionRunStartedPayload) -> None: ...

    def emit_next_step_issued(self, payload: NextStepIssuedPayload) -> None: ...

    def emit_next_step_auto_completed(self, payload: NextStepAutoCompletedPayload) -> None: ...

    def emit_decision_input_requested(self, payload: DecisionInputRequestedPayload) -> None: ...

    def emit_decision_input_answered(self, payload: DecisionInputAnsweredPayload) -> None: ...

    def emit_mission_run_completed(self, payload: MissionRunCompletedPayload) -> None: ...

    def emit_significance_evaluated(self, payload: SignificanceEvaluatedPayload) -> None: ...

    def emit_decision_timeout_expired(self, payload: TimeoutExpiredPayload) -> None: ...


def seed_runtime_emitter(emitter: RuntimeEventEmitter, snapshot: Any) -> None:
    """Seed optional producer state without affecting mission control flow.

    Protocol-only products need no hook. Lookup and invocation failures are
    logged and ignored, including when a decision-log wrapper delegates inward.
    """
    try:
        seed = getattr(emitter, "seed_from_snapshot", None)
        if seed is not None:
            seed(snapshot)
    except Exception as exc:  # noqa: BLE001 — optional instrumentation must not alter mission state
        logging.getLogger(__name__).warning("Failed to seed runtime emitter from snapshot: %s", exc)


# ---------------------------------------------------------------------------
# NullEmitter (no-op default)
# ---------------------------------------------------------------------------

class NullEmitter:
    """No-op emitter — default when no concrete emitter is provided.

    Also the null object the runtime emitter seam returns (see
    :func:`runtime_emitter_for_mission`). Nothing here may raise: emission is
    fire-and-forget instrumentation, never control flow.
    """

    def __init__(
        self,
        correlation_id: str = "",
        *,
        mission_slug: str = "",
        mission_type: str = "",
        mission_id: str | None = None,
    ) -> None:
        self.correlation_id = correlation_id
        self.mission_slug = mission_slug
        self.mission_type = mission_type
        self.mission_id = mission_id

    @classmethod
    def for_mission(
        cls,
        *,
        feature_dir: Path,
        mission_slug: str,
        mission_type: str,
    ) -> NullEmitter:
        """Build the null seam for one mission, resolving its ULID when possible."""
        try:
            mission_id: str | None = resolve_mission_identity(feature_dir).mission_id
        except Exception:  # noqa: BLE001 — identity is informational; the seam must never raise
            mission_id = None
        return cls(mission_slug=mission_slug, mission_type=mission_type, mission_id=mission_id)

    def seed_from_snapshot(self, snapshot: Any) -> None:
        """No-op: the null seam carries no phase state to seed."""
        del snapshot

    def emit_mission_run_started(self, payload: MissionRunStartedPayload) -> None:
        pass

    def emit_next_step_issued(self, payload: NextStepIssuedPayload) -> None:
        pass

    def emit_next_step_auto_completed(self, payload: NextStepAutoCompletedPayload) -> None:
        pass

    def emit_decision_input_requested(self, payload: DecisionInputRequestedPayload) -> None:
        pass

    def emit_decision_input_answered(self, payload: DecisionInputAnsweredPayload) -> None:
        pass

    def emit_mission_run_completed(self, payload: MissionRunCompletedPayload) -> None:
        pass

    def emit_significance_evaluated(self, payload: SignificanceEvaluatedPayload) -> None:
        pass

    def emit_decision_timeout_expired(self, payload: TimeoutExpiredPayload) -> None:
        pass


# ---------------------------------------------------------------------------
# Runtime emitter seam (factory + registry)
# ---------------------------------------------------------------------------
#
# This is the reserved E3 *producer* seam for the six ``mission_next`` runtime
# moments (mission run started/completed, next step issued/auto-completed,
# decision input requested/answered). Nothing registers here today; the seam
# returns :class:`NullEmitter` so the bridge's instrumentation points survive
# intact.
#
# A future producer registers once at its import tail via
# :func:`register_runtime_emitter_factory`, under the
# ``SPEC_KITTY_SYNC_MINIMAL_IMPORT`` gate, mirroring
# ``specify_cli.status.adapters.ensure_zeitgeist_moment_handlers``::
#
#     if not is_truthy(os.environ.get("SPEC_KITTY_SYNC_MINIMAL_IMPORT")):
#         register_runtime_emitter_factory(MyProducer.for_mission)
#
# The zeitgeist *moment fan-out* is a separate, already-live seam in
# ``specify_cli/status/adapters.py`` (``WPStatusChanged`` and lifecycle events);
# it is NOT what registers here. This seam carries only the runtime-loop
# moments listed above.
#
# Governing ADR: ``docs/adr/3.x/2026-09-06-2-runtime-event-emitter-disposition.md``.

RuntimeEmitterFactory = Callable[..., RuntimeEventEmitter]
_registered_factory: RuntimeEmitterFactory | None = None


def register_runtime_emitter_factory(factory: RuntimeEmitterFactory) -> None:
    """Register the producer factory a future E3 adapter installs at import tail.

    The callable must accept ``feature_dir``, ``mission_slug`` and
    ``mission_type`` as keywords and return an object satisfying
    :class:`RuntimeEventEmitter`. Registering replaces any prior factory.
    """
    global _registered_factory
    _registered_factory = factory


def reset_runtime_emitter_factory() -> None:
    """Restore the default (null) seam; test-only utility, mirrors ``reset_handlers()``."""
    global _registered_factory
    _registered_factory = None


def runtime_emitter_for_mission(
    *,
    feature_dir: Path,
    mission_slug: str,
    mission_type: str,
) -> RuntimeEventEmitter:
    """Return the mission's runtime emitter seam.

    Under ``SPEC_KITTY_SYNC_MINIMAL_IMPORT`` the null seam is returned
    unconditionally and the registered factory is not called (S2). Otherwise
    the registered factory wins (S3); with none registered the null seam is
    returned (S1). The env gate is read at call time so tests can toggle it
    without reloading this module.
    """
    if is_truthy(os.environ.get("SPEC_KITTY_SYNC_MINIMAL_IMPORT")):
        return NullEmitter.for_mission(
            feature_dir=feature_dir, mission_slug=mission_slug, mission_type=mission_type
        )
    if _registered_factory is not None:
        return _registered_factory(
            feature_dir=feature_dir, mission_slug=mission_slug, mission_type=mission_type
        )
    return NullEmitter.for_mission(
        feature_dir=feature_dir, mission_slug=mission_slug, mission_type=mission_type
    )


# ---------------------------------------------------------------------------
# JsonlEventLog (append-only JSONL persistence)
# ---------------------------------------------------------------------------

class JsonlEventLog:
    """Append-only JSONL log. Writes dicts with sort_keys for determinism.

    Runtime-local debug/audit log. Payload dicts match canonical payload
    model shapes but do not use the full Event envelope (event_id,
    lamport_clock, etc.) — that is a cross-repo concern for a later version.
    """

    def __init__(self, path: Path) -> None:
        self._path = path

    @property
    def path(self) -> Path:
        return self._path

    def append(self, record: dict[str, Any]) -> None:
        """Append a single record as a JSON line."""
        line = json.dumps(record, sort_keys=True, separators=(",", ":"), default=str)
        with open(self._path, "a", encoding="utf-8") as handle:
            handle.write(line + "\n")

    def read_all(self) -> list[dict[str, Any]]:
        """Read all records from the log file."""
        if not self._path.exists():
            return []
        records: list[dict[str, Any]] = []
        with open(self._path, encoding="utf-8") as handle:
            for line in handle:
                stripped = line.strip()
                if stripped:
                    records.append(json.loads(stripped))
        return records
