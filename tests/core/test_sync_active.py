"""FR-002 / INV-3 — the ``sync_active()`` arming predicate truth table.

``sync_active()`` is the single canonical machine-level arming predicate for the
legacy sync surface (contract: ``contracts/sync-active-seam.md``). It is a pure
function of three environment toggles:

- ``E`` = ``SPEC_KITTY_ENABLE_SAAS_SYNC`` (the opt-in enable flag)
- ``D`` = ``SPEC_KITTY_SYNC_DISABLE`` (a sync-disable toggle)
- ``M`` = ``SPEC_KITTY_SYNC_MINIMAL_IMPORT`` (a sync-disable toggle)

The contract is ``sync_active = E AND NOT (D OR M)`` — disable/minimal-import
wins over enable. This module exercises **all 8 combinations** (INV-3) from
``data-model.md``. INV-4 (single definition) is enforced separately by the
arch census; here we only pin the boolean truth table.
"""

from __future__ import annotations

import pytest

from specify_cli.core.saas_sync_config import sync_active

_ENABLE = "SPEC_KITTY_ENABLE_SAAS_SYNC"
_DISABLE = "SPEC_KITTY_SYNC_DISABLE"
_MINIMAL = "SPEC_KITTY_SYNC_MINIMAL_IMPORT"


# (E, D, M, expected) — the 8-row truth table from data-model.md.
_TRUTH_TABLE = [
    (False, False, False, False),
    (True, False, False, True),
    (True, True, False, False),
    (True, False, True, False),
    (True, True, True, False),
    (False, True, False, False),
    (False, False, True, False),
    (False, True, True, False),
]



pytestmark = [pytest.mark.fast]

@pytest.mark.parametrize(("enable", "disable", "minimal", "expected"), _TRUTH_TABLE)
def test_sync_active_truth_table(
    monkeypatch: pytest.MonkeyPatch,
    enable: bool,
    disable: bool,
    minimal: bool,
    expected: bool,
) -> None:
    """sync_active == E AND NOT (D OR M) for every toggle combination (INV-3)."""
    for name, present in ((_ENABLE, enable), (_DISABLE, disable), (_MINIMAL, minimal)):
        if present:
            monkeypatch.setenv(name, "1")
        else:
            monkeypatch.delenv(name, raising=False)

    assert sync_active() is expected


def test_sync_active_disable_wins_over_enable(monkeypatch: pytest.MonkeyPatch) -> None:
    """Disable beats enable — arming is refused even with the enable flag on."""
    monkeypatch.setenv(_ENABLE, "1")
    monkeypatch.setenv(_DISABLE, "1")
    monkeypatch.delenv(_MINIMAL, raising=False)
    assert sync_active() is False


def test_sync_active_returns_bool(monkeypatch: pytest.MonkeyPatch) -> None:
    """The predicate returns a real ``bool``, never a truthy string/None."""
    monkeypatch.setenv(_ENABLE, "1")
    monkeypatch.delenv(_DISABLE, raising=False)
    monkeypatch.delenv(_MINIMAL, raising=False)
    result = sync_active()
    assert isinstance(result, bool)
    assert result is True
