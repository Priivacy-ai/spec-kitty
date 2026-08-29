"""#2801 clean-cut — the pre-review regression gate reads only its OWN env.

Contract: ``contracts/pre-review-gate-env.md`` (INV-1..INV-4), FR-009, C-004,
SC-002, FR-016.

Before this cut, ``_mt_pre_review_gate_env_disable_reason`` honored the sync
disable vocabulary (``SPEC_KITTY_SYNC_DISABLE`` / ``SPEC_KITTY_SYNC_MINIMAL_IMPORT``)
via ``core.env.first_set_sync_disable_env``. That coupling (#2801) meant a
machine that had disabled sync also silently disabled the review gate.

After the cut the gate is governed SOLELY by ``SPEC_KITTY_PRE_REVIEW_GATE_DISABLE``
— a gate flag, not a sync flag. The sync toggles are inert against the gate.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from specify_cli.cli.commands.agent import tasks_move_task

_GATE_DISABLE = "SPEC_KITTY_PRE_REVIEW_GATE_DISABLE"
_SYNC_DISABLE = "SPEC_KITTY_SYNC_DISABLE"
_SYNC_MINIMAL = "SPEC_KITTY_SYNC_MINIMAL_IMPORT"
_SAAS_ENABLE = "SPEC_KITTY_ENABLE_SAAS_SYNC"

_ALL_ENV = (_GATE_DISABLE, _SYNC_DISABLE, _SYNC_MINIMAL, _SAAS_ENABLE)



pytestmark = [pytest.mark.fast]

def _clear(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in _ALL_ENV:
        monkeypatch.delenv(name, raising=False)


def test_gate_runs_when_no_env_set(monkeypatch: pytest.MonkeyPatch) -> None:
    """INV-1: with nothing set (bare install), the gate is NOT disabled by env."""
    _clear(monkeypatch)
    assert tasks_move_task._mt_pre_review_gate_env_disable_reason() is None


def test_gate_disabled_only_by_its_own_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    """INV-2: SPEC_KITTY_PRE_REVIEW_GATE_DISABLE=1 => gate skipped."""
    _clear(monkeypatch)
    monkeypatch.setenv(_GATE_DISABLE, "1")
    reason = tasks_move_task._mt_pre_review_gate_env_disable_reason()
    assert reason is not None
    assert _GATE_DISABLE in reason


@pytest.mark.parametrize("sync_var", [_SYNC_DISABLE, _SYNC_MINIMAL])
def test_sync_disable_toggles_do_not_disable_gate(
    monkeypatch: pytest.MonkeyPatch, sync_var: str
) -> None:
    """INV-3 (load-bearing #2801): sync-disable toggles are inert on the gate."""
    _clear(monkeypatch)
    monkeypatch.setenv(sync_var, "1")
    assert tasks_move_task._mt_pre_review_gate_env_disable_reason() is None


def test_saas_enable_does_not_affect_gate(monkeypatch: pytest.MonkeyPatch) -> None:
    """INV-3: the SaaS enable flag is inert on the gate too."""
    _clear(monkeypatch)
    monkeypatch.setenv(_SAAS_ENABLE, "1")
    assert tasks_move_task._mt_pre_review_gate_env_disable_reason() is None


def test_gate_flag_wins_regardless_of_sync_toggles(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """INV-2 + INV-3: only the gate flag governs, whatever the sync toggles do."""
    _clear(monkeypatch)
    monkeypatch.setenv(_GATE_DISABLE, "1")
    monkeypatch.setenv(_SYNC_DISABLE, "1")
    monkeypatch.setenv(_SYNC_MINIMAL, "1")
    monkeypatch.setenv(_SAAS_ENABLE, "1")
    reason = tasks_move_task._mt_pre_review_gate_env_disable_reason()
    assert reason is not None
    assert _GATE_DISABLE in reason


def test_skip_reason_flag_precedes_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """--skip-pre-review-gate flag is honored first (explicit per-invocation)."""
    _clear(monkeypatch)
    st = SimpleNamespace(skip_pre_review_gate=True)
    reason = tasks_move_task._mt_pre_review_gate_skip_reason(st)
    assert reason == "--skip-pre-review-gate flag"


def test_skip_reason_env_when_no_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    """Without the flag, the gate-disable env drives the skip reason."""
    _clear(monkeypatch)
    monkeypatch.setenv(_GATE_DISABLE, "1")
    st = SimpleNamespace(skip_pre_review_gate=False)
    reason = tasks_move_task._mt_pre_review_gate_skip_reason(st)
    assert reason is not None
    assert _GATE_DISABLE in reason


def test_skip_reason_none_runs_gate(monkeypatch: pytest.MonkeyPatch) -> None:
    """Neither flag nor env set => the gate runs (skip reason is None)."""
    _clear(monkeypatch)
    monkeypatch.setenv(_SYNC_DISABLE, "1")  # sync toggle must NOT skip the gate
    st = SimpleNamespace(skip_pre_review_gate=False)
    assert tasks_move_task._mt_pre_review_gate_skip_reason(st) is None
