"""Sync failure fakes that keep local command output assertions isolated."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class SyncDiagnostic:
    """Structured non-fatal final-sync diagnostic."""

    severity: str
    diagnostic_code: str
    message: str
    fatal: bool
    sync_phase: str

    def normalized_key(self) -> tuple[str, str, str]:
        return (
            self.diagnostic_code,
            self.sync_phase,
            " ".join(self.message.lower().split()),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "severity": self.severity,
            "diagnostic_code": self.diagnostic_code,
            "message": self.message,
            "fatal": self.fatal,
            "sync_phase": self.sync_phase,
        }


class ControlledSyncFailure(Exception):
    """Raised by fake sync clients to model deterministic final-sync failures."""

    def __init__(self, diagnostic: SyncDiagnostic) -> None:
        super().__init__(diagnostic.message)
        self.diagnostic = diagnostic


@dataclass(frozen=True)
class CommandOutput:
    """Captured command surfaces for stdout/stderr parseability checks."""

    stdout: str
    stderr: str
    exit_code: int = 0


class FakeSyncClient:
    """A fake final-sync client with controlled lock/shutdown/transport failures."""

    def __init__(self, diagnostics: list[SyncDiagnostic] | None = None) -> None:
        self._diagnostics = diagnostics or []
        self.sent_payloads: list[dict[str, Any]] = []

    @classmethod
    def with_lock_shutdown_and_transport_failures(cls) -> FakeSyncClient:
        return cls(
            [
                SyncDiagnostic(
                    severity="warning",
                    diagnostic_code="SYNC_LOCK_HELD",
                    message="Sync lock is already held",
                    fatal=False,
                    sync_phase="finalize",
                ),
                SyncDiagnostic(
                    severity="warning",
                    diagnostic_code="SYNC_INTERPRETER_SHUTDOWN",
                    message="Interpreter shutdown interrupted sync cleanup",
                    fatal=False,
                    sync_phase="cleanup",
                ),
                SyncDiagnostic(
                    severity="warning",
                    diagnostic_code="SYNC_TRANSPORT_ERROR",
                    message="Transport unavailable after local success",
                    fatal=False,
                    sync_phase="upload",
                ),
            ]
        )

    def emit(self, payload: dict[str, Any]) -> None:
        self.sent_payloads.append(payload)
        if self._diagnostics:
            raise ControlledSyncFailure(self._diagnostics[0])

    def diagnostics(self) -> list[SyncDiagnostic]:
        """Return diagnostics deduped per invocation by contract key."""

        seen: set[tuple[str, str, str]] = set()
        deduped: list[SyncDiagnostic] = []
        for diagnostic in self._diagnostics:
            key = diagnostic.normalized_key()
            if key in seen:
                continue
            seen.add(key)
            deduped.append(diagnostic)
        return deduped

    def render_stderr(self) -> str:
        return "\n".join(json.dumps(item.to_dict(), sort_keys=True) for item in self.diagnostics())


def assert_json_stdout_parseable(output: CommandOutput) -> dict[str, Any]:
    """Assert stdout is pure JSON and return its decoded object."""

    parsed = json.loads(output.stdout)
    assert isinstance(parsed, dict)
    return parsed


def assert_stderr_contains_diagnostic_codes(output: CommandOutput, *codes: str) -> None:
    """Assert diagnostics are carried on stderr, separately from stdout JSON."""

    for code in codes:
        assert code in output.stderr
    assert output.exit_code == 0
