"""`sync doctor` calls the R2-T1 legacy daemon retirement step (R2.md §3.2.2).

This is the wiring half of R2-T1's WP(a): ``specify_cli.sync.retirement
.retire_legacy_sync_daemon`` needs at least one genuine ``src/`` caller (the
repo's own ``test_no_dead_modules.py`` gate refuses a "library written but
never wired" module), and R2.md §3.2.2 names "a dedicated ``spec-kitty
doctor`` check" as one of the two acceptable call sites. This pins
``_render_legacy_daemon_retirement`` -- the small, directly-testable renderer
``doctor`` calls -- against the ``retirement.RetirementOutcome`` states,
without paying for ``doctor``'s full runtime fixture (queue store, token
manager, tracker config, ...), mirroring how ``_render_tracker_egress_row``
(WP06/#3108) is a separately-callable unit inside the same file.

State -> behaviour:
    no_daemon               -> prints nothing, no issue appended (the
                                overwhelmingly common post-R2 case must stay
                                silent, matching §6 D3's "physically absent
                                for code" posture -- this is not a health
                                fault).
    stopped / cleared_stale
    / already_stopped       -> prints a green resolution line, no issue
                                (resolved automatically -- nothing for the
                                operator to act on).
    unverifiable_owner_record
    / unverified_ownership  -> prints a line and appends to ``issues`` (the
                                two states the daemon-retirement step is
                                required, by §3.2's own contract, to
                                refuse to act on by itself).
"""

from __future__ import annotations

import io

import pytest
from rich.console import Console

from specify_cli.cli.commands.sync import _render_legacy_daemon_retirement
from specify_cli.sync.retirement import RetirementOutcome, RetirementStatus

pytestmark = pytest.mark.fast


def _capture() -> tuple[Console, io.StringIO]:
    buf = io.StringIO()
    return Console(file=buf, width=200, record=True), buf


def _run(monkeypatch: pytest.MonkeyPatch, outcome: RetirementOutcome) -> tuple[str, list[str]]:
    def _fake_retire() -> RetirementOutcome:
        return outcome

    monkeypatch.setattr(
        "specify_cli.sync.retirement.retire_legacy_sync_daemon", _fake_retire
    )
    console, buf = _capture()
    issues: list[str] = []
    _render_legacy_daemon_retirement(console, issues)
    return buf.getvalue(), issues


@pytest.mark.parametrize(
    "status",
    ["stopped", "cleared_stale", "already_stopped"],
)
def test_resolved_states_print_and_raise_no_issue(
    monkeypatch: pytest.MonkeyPatch, status: RetirementStatus
) -> None:
    outcome = RetirementOutcome(status=status, detail="fixture detail text")
    output, issues = _run(monkeypatch, outcome)

    assert "fixture detail text" in output
    assert issues == []


@pytest.mark.parametrize(
    "status",
    ["unverifiable_owner_record", "unverified_ownership"],
)
def test_unresolved_states_print_and_raise_an_issue(
    monkeypatch: pytest.MonkeyPatch, status: RetirementStatus
) -> None:
    outcome = RetirementOutcome(status=status, detail="fixture fault text")
    output, issues = _run(monkeypatch, outcome)

    assert "fixture fault text" in output
    assert len(issues) == 1
    assert "fixture fault text" in issues[0]


def test_no_daemon_is_silent(monkeypatch: pytest.MonkeyPatch) -> None:
    outcome = RetirementOutcome(status="no_daemon", detail="nothing to retire")
    output, issues = _run(monkeypatch, outcome)

    assert output == ""
    assert issues == []


def test_wired_into_doctor_command_source() -> None:
    """Structural pin: ``doctor`` itself must call the renderer.

    A regression here (the renderer existing but ``doctor`` no longer
    calling it) would silently reopen the "library written but never wired"
    gap this wiring exists to close, without any of the behavioural tests
    above going red (they call the renderer directly).
    """
    import inspect

    from specify_cli.cli.commands import sync as sync_module

    source = inspect.getsource(sync_module.doctor)
    assert "_render_legacy_daemon_retirement(" in source
