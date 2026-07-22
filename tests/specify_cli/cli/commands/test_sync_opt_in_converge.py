"""#2665 — `sync opt-in` auto-converges legacy queue residue on enable.

These unit tests pin the reporting branches of
``_auto_converge_legacy_on_enable`` with the runtime open and the convergence
engine mocked, so the CLI wiring is covered without a live runtime.
"""
from __future__ import annotations

import pytest

from specify_cli.cli.commands import sync as sync_cmd
from specify_cli.sync.migrate_journal import (
    CleanupOutcome,
    CleanupResult,
    ConvergeResult,
    MigrationConflict,
    MigrationResult,
)

pytestmark = pytest.mark.fast


class _FakeRuntime:
    journal = object()
    target = None

    def close(self) -> None:  # pragma: no cover - trivial
        return None


def test_auto_converge_reports_converged_rows(monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    monkeypatch.setattr(sync_cmd, "_open_event_sync_runtime", lambda *a, **k: _FakeRuntime())

    def _fake_converge(*_a, **_k):
        return ConvergeResult(
            migration=MigrationResult(),
            cleanup=CleanupResult(
                ran=True,
                outcomes=[CleanupOutcome(digest="legacy", is_legacy=True, deleted=7)],
            ),
        )

    monkeypatch.setattr("specify_cli.sync.migrate_journal.converge_legacy_runtime", _fake_converge)

    sync_cmd._auto_converge_legacy_on_enable()

    out = capsys.readouterr().out
    assert "Converged 7 legacy queue row" in out


def test_auto_converge_surfaces_conflicts(monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    monkeypatch.setattr(sync_cmd, "_open_event_sync_runtime", lambda *a, **k: _FakeRuntime())
    conflict = MigrationConflict(
        event_id="dup", source_digest="legacy", existing_sha="a", incoming_sha="b"
    )

    def _fake_converge(*_a, **_k):
        return ConvergeResult(migration=MigrationResult(conflicts=[conflict]), cleanup=None)

    monkeypatch.setattr("specify_cli.sync.migrate_journal.converge_legacy_runtime", _fake_converge)

    sync_cmd._auto_converge_legacy_on_enable()

    out = capsys.readouterr().out
    assert "resolve-conflicts keep-journal" in out


def test_auto_converge_swallows_runtime_open_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    def _boom(*_a, **_k):
        raise RuntimeError("runtime unavailable")

    monkeypatch.setattr(sync_cmd, "_open_event_sync_runtime", _boom)
    # Must not raise — the coherence gate downstream reports the incoherence.
    sync_cmd._auto_converge_legacy_on_enable()


def test_auto_converge_swallows_converge_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    """A failure INSIDE converge (not just opening the runtime) is swallowed too,
    so opt-in defers to the coherence gate instead of aborting with a traceback.
    """
    monkeypatch.setattr(sync_cmd, "_open_event_sync_runtime", lambda *a, **k: _FakeRuntime())

    def _boom(*_a, **_k):
        raise RuntimeError("journal API contract error mid-converge")

    monkeypatch.setattr("specify_cli.sync.migrate_journal.converge_legacy_runtime", _boom)
    # Must not raise — the runtime is still closed and control returns cleanly.
    sync_cmd._auto_converge_legacy_on_enable()
