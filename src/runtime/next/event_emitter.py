"""Runtime mission-event emission seam for the ``next`` bridge.

The former ``SyncRuntimeEventEmitter`` forwarded every runtime callback
(mission run started, next step issued, decision requested/answered, …) into
the deleted sync ``EventEmitter``, whose journal/outbox died with the sync
transport (issue #5). What remains is the seam itself: a no-op emitter with
the same call surface, so the bridge's instrumentation points survive intact
and E3 can register a real handler (the zeitgeist moment fan-out) at this seam
without reshaping the bridge.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from specify_cli.mission_metadata import resolve_mission_identity

logger = logging.getLogger(__name__)


class RuntimeEventEmitter:
    """No-op sink for runtime mission-event callbacks.

    Every ``emit_*`` callback accepts the same payloads the bridge already
    constructs and deliberately drops them. Nothing here may raise: emission is
    fire-and-forget instrumentation, never control flow.
    """

    def __init__(
        self,
        *,
        mission_slug: str,
        mission_type: str,
        mission_id: str | None,
    ) -> None:
        self._mission_slug = mission_slug
        self._mission_type = mission_type
        self._mission_id = mission_id

    @classmethod
    def for_feature(
        cls,
        *,
        feature_dir: Path,
        mission_slug: str,
        mission_type: str,
    ) -> RuntimeEventEmitter:
        try:
            mission_id = resolve_mission_identity(feature_dir).mission_id
        except Exception:
            mission_id = None
        return cls(
            mission_slug=mission_slug,
            mission_type=mission_type,
            mission_id=mission_id,
        )

    def seed_from_snapshot(self, snapshot: Any) -> None:
        """No-op: retained so the bridge's seed call site survives unchanged."""

    # The unused ``payload`` arguments are the point: they keep the bridge's
    # call contract byte-identical for the E3 handler that will register here.
    def emit_mission_run_started(self, payload: Any) -> None:  # noqa: ARG002 - no-op sink keeps the E3 handler's parameter contract visible
        del payload
        logger.debug("Mission run started (emission retired): %s", self._mission_slug)

    def emit_next_step_issued(self, payload: Any) -> None:  # noqa: ARG002 - see class comment
        pass

    def emit_next_step_auto_completed(self, payload: Any) -> None:  # noqa: ARG002 - see class comment
        pass

    def emit_decision_input_requested(self, payload: Any) -> None:  # noqa: ARG002 - see class comment
        pass

    def emit_decision_input_answered(self, payload: Any) -> None:  # noqa: ARG002 - see class comment
        pass

    def emit_mission_run_completed(self, payload: Any) -> None:  # noqa: ARG002 - see class comment
        pass

    def emit_significance_evaluated(self, payload: Any) -> None:  # noqa: ARG002 - see class comment
        pass

    def emit_decision_timeout_expired(self, payload: Any) -> None:  # noqa: ARG002 - see class comment
        pass
