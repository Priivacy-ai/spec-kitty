"""Mission runtime event emission interface and persistence.

Uses canonical event constants and payload models from spec-kitty-events v2.3.1.
"""

# Internalized from spec-kitty-runtime 0.4.3 as part of
# `shared-package-boundary-cutover-01KQ22DS` (mission). See
# `runtime-standalone-package-retirement-01KQ20Z8` for the upstream
# public-API inventory.
from __future__ import annotations

import json
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
from specify_cli.next._internal_runtime.significance import (
    SignificanceEvaluatedPayload,
    TimeoutExpiredPayload,
)

# Explicit re-exports so `from specify_cli.next._internal_runtime.events import X`
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
    "SignificanceEvaluatedPayload",
    "TimeoutExpiredPayload",
    "RuntimeEventEmitter",
    "NullEmitter",
    "JsonlEventLog",
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


# ---------------------------------------------------------------------------
# NullEmitter (no-op default)
# ---------------------------------------------------------------------------

class NullEmitter:
    """No-op emitter — default when no concrete emitter is provided."""

    def __init__(self, correlation_id: str = "") -> None:
        self.correlation_id = correlation_id

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
        with open(self._path, "r", encoding="utf-8") as handle:
            for line in handle:
                stripped = line.strip()
                if stripped:
                    records.append(json.loads(stripped))
        return records
