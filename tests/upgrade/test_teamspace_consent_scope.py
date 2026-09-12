"""Seam unit tests for the scoped mission-state consent gate (C3, D-9,
FR-005/006/014, NFR-003).

Load-bearing distinction (post-tasks squad, HIGH): the gate has THREE
pre-consent early returns (`not blocked`, `audit_error`, `dry_run`) that all
yield ``pending=True`` — a fixture that never reaches the consent decision at
all would make "repair not called" prove nothing (green-for-wrong-reason).
The non-fakeable proof is ``RepairOutcome.declined is True``, which is set
ONLY on the post-consent-decision deny path. Every test below that claims to
exercise the consent decision uses a fixture that is genuinely
``blocked=True`` with ``blocker_count > 0`` and ``audit_error is None`` and
``dry_run=False``.
"""

from __future__ import annotations

import types
from pathlib import Path
from unittest.mock import MagicMock

import pytest
import typer
from rich.console import Console

from specify_cli.cli.commands import _teamspace_mission_state_gate as gate
from specify_cli.cli.commands._teamspace_mission_state_gate import (
    RepairOutcome,
    TeamspaceMissionStateReadiness,
    offer_teamspace_mission_state_migration,
)

pytestmark = [pytest.mark.unit, pytest.mark.fast]


class _FakeStdin:
    """Stand-in for ``sys.stdin`` with a controllable ``isatty()``."""

    def __init__(self, *, is_tty: bool) -> None:
        self._is_tty = is_tty

    def isatty(self) -> bool:
        return self._is_tty


def _genuinely_blocked_readiness(repo_root: Path) -> TeamspaceMissionStateReadiness:
    """A fixture with ``blocker_count > 0``, ``audit_error is None`` — the
    ONLY readiness shape that actually reaches the consent decision at all."""
    return TeamspaceMissionStateReadiness(
        repo_root=repo_root,
        total_missions=1,
        blocker_count=2,
        missions_with_blockers=1,
        blocker_codes=("teamspace-blocker",),
        audit_error=None,
    )


def _patch_readiness(monkeypatch: pytest.MonkeyPatch, repo_root: Path) -> None:
    monkeypatch.setattr(
        gate,
        "check_teamspace_mission_state_readiness",
        lambda _repo_root: _genuinely_blocked_readiness(repo_root),
    )


def _spy_repair_repo(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    """Patch ``repair_repo`` AT ITS SOURCE MODULE — the gate imports it
    locally (``from specify_cli.migration.mission_state import repair_repo``)
    inside the function body, so patching the source attribute is what the
    fresh import actually picks up."""
    spy = MagicMock(name="repair_repo")
    monkeypatch.setattr("specify_cli.migration.mission_state.repair_repo", spy)
    return spy


# ---------------------------------------------------------------------------
# NFR-003 non-fakeable proof + FR-006/SC-003 default-deny
# ---------------------------------------------------------------------------


def test_interactive_default_deny_reaches_consent_and_declines(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Interactive session, no explicit opt-in, user declines the prompt:
    the consent decision at the gate's core IS reached (proven by
    ``declined is True``, not merely ``pending``), and ``repair_repo`` is
    never called."""
    _patch_readiness(monkeypatch, tmp_path)
    spy = _spy_repair_repo(monkeypatch)
    monkeypatch.setattr(gate, "sys", types.SimpleNamespace(stdin=_FakeStdin(is_tty=True)))
    monkeypatch.setattr(typer, "confirm", lambda *_a, **_kw: False)

    outcome = offer_teamspace_mission_state_migration(
        tmp_path,
        console=Console(),
        dry_run=False,
        repair_opt_in=False,
    )

    spy.assert_not_called()
    assert isinstance(outcome, RepairOutcome)
    assert outcome.declined is True
    assert outcome.pending is False
    assert outcome.ran is False


def test_interactive_prompt_defaults_to_no(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """FR-006/SC-003(a): the interactive prompt's own default is ``no`` —
    verified by asserting the ``default`` kwarg passed to ``typer.confirm``."""
    _patch_readiness(monkeypatch, tmp_path)
    _spy_repair_repo(monkeypatch)
    monkeypatch.setattr(gate, "sys", types.SimpleNamespace(stdin=_FakeStdin(is_tty=True)))

    captured: dict[str, object] = {}

    def _fake_confirm(*_args: object, **kwargs: object) -> bool:
        captured.update(kwargs)
        return False

    monkeypatch.setattr(typer, "confirm", _fake_confirm)

    offer_teamspace_mission_state_migration(
        tmp_path,
        console=Console(),
        dry_run=False,
        repair_opt_in=False,
    )

    assert captured["default"] is False


def test_non_interactive_no_opt_in_denies_without_abort(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """FR-006/SC-003(b): a non-interactive session (no TTY) with no explicit
    opt-in denies WITHOUT aborting the run — guards against ``typer.confirm``
    raising ``Abort`` when there is no TTY."""
    _patch_readiness(monkeypatch, tmp_path)
    spy = _spy_repair_repo(monkeypatch)
    monkeypatch.setattr(gate, "sys", types.SimpleNamespace(stdin=_FakeStdin(is_tty=False)))

    def _confirm_must_not_be_called(*_a: object, **_kw: object) -> bool:
        raise AssertionError("typer.confirm must not be invoked without a TTY")

    monkeypatch.setattr(typer, "confirm", _confirm_must_not_be_called)

    outcome = offer_teamspace_mission_state_migration(
        tmp_path,
        console=Console(),
        dry_run=False,
        repair_opt_in=False,
    )

    spy.assert_not_called()
    assert outcome.declined is True
    assert outcome.pending is False


def test_explicit_repair_opt_in_bypasses_the_prompt_and_runs_repair(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """An explicit opt-in short-circuits the prompt entirely and runs the
    repair (positive control for the spy — proves the spy would fire if the
    decision allowed it)."""
    _patch_readiness(monkeypatch, tmp_path)
    spy = _spy_repair_repo(monkeypatch)
    fake_report = MagicMock()
    fake_report.to_dict.return_value = {"summary": {"missions_updated": 1, "missions_unchanged": 0, "missions_error": 0}}
    fake_report.manifest_path = tmp_path / "manifest.json"
    spy.return_value = fake_report

    def _confirm_must_not_be_called(*_a: object, **_kw: object) -> bool:
        raise AssertionError("typer.confirm must not run when repair_opt_in is explicit")

    monkeypatch.setattr(typer, "confirm", _confirm_must_not_be_called)

    readiness_calls = {"count": 0}

    def _readiness_then_cleared(_repo_root: Path) -> TeamspaceMissionStateReadiness:
        readiness_calls["count"] += 1
        if readiness_calls["count"] == 1:
            return _genuinely_blocked_readiness(tmp_path)
        # Post-repair re-check (gate's success path): blockers cleared.
        return TeamspaceMissionStateReadiness(repo_root=tmp_path)

    monkeypatch.setattr(gate, "check_teamspace_mission_state_readiness", _readiness_then_cleared)

    outcome = offer_teamspace_mission_state_migration(
        tmp_path,
        console=Console(),
        dry_run=False,
        repair_opt_in=True,
    )

    spy.assert_called_once_with(tmp_path)
    assert outcome.ran is True
    assert outcome.declined is False
    assert outcome.failed is False


# ---------------------------------------------------------------------------
# Green-for-wrong-reason guard: the pre-consent early returns are pending,
# never declined
# ---------------------------------------------------------------------------


def test_not_blocked_is_pending_not_declined(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        gate,
        "check_teamspace_mission_state_readiness",
        lambda _repo_root: TeamspaceMissionStateReadiness(repo_root=tmp_path),
    )
    spy = _spy_repair_repo(monkeypatch)

    outcome = offer_teamspace_mission_state_migration(tmp_path, console=Console(), dry_run=False, repair_opt_in=False)

    spy.assert_not_called()
    assert outcome.pending is True
    assert outcome.declined is False


def test_audit_error_is_pending_not_declined(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        gate,
        "check_teamspace_mission_state_readiness",
        lambda _repo_root: TeamspaceMissionStateReadiness(repo_root=tmp_path, audit_error="boom"),
    )
    spy = _spy_repair_repo(monkeypatch)

    outcome = offer_teamspace_mission_state_migration(tmp_path, console=Console(), dry_run=False, repair_opt_in=False)

    spy.assert_not_called()
    assert outcome.pending is True
    assert outcome.declined is False


def test_dry_run_is_pending_not_declined(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_readiness(monkeypatch, tmp_path)
    spy = _spy_repair_repo(monkeypatch)

    outcome = offer_teamspace_mission_state_migration(tmp_path, console=Console(), dry_run=True, repair_opt_in=False)

    spy.assert_not_called()
    assert outcome.pending is True
    assert outcome.declined is False


# ---------------------------------------------------------------------------
# Static + behavioral guard: the repair CONSENT DECISION never reads
# ``assume_yes`` (NFR-003). ``offer_teamspace_mission_state_migration`` keeps
# accepting ``assume_yes`` only so the existing ``upgrade.py`` call sites
# (which pass it positionally-by-keyword and are out of this WP's scope)
# keep working — but it is never threaded into the decision helper.
# ---------------------------------------------------------------------------


def test_should_run_repair_never_references_assume_yes() -> None:
    """Arch guard: the actual consent-decision helper must not reference
    ``assume_yes`` anywhere in its source — not merely "not used", but
    structurally incapable of reading it (it isn't even a parameter)."""
    import inspect

    params = inspect.signature(gate._should_run_repair).parameters
    assert "assume_yes" not in params
    assert "assume_yes" not in inspect.getsource(gate._should_run_repair)


def test_offer_signature_has_own_repair_opt_in_parameter() -> None:
    import inspect

    params = inspect.signature(offer_teamspace_mission_state_migration).parameters
    assert "repair_opt_in" in params


def test_assume_yes_true_does_not_bypass_repair_consent(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Behavioral proof of NFR-003: even when the caller holds full
    migration-apply consent (``assume_yes=True``), a non-interactive session
    with no explicit ``repair_opt_in`` still declines the repair — ``assume_yes``
    must never leak into this decision."""
    _patch_readiness(monkeypatch, tmp_path)
    spy = _spy_repair_repo(monkeypatch)
    monkeypatch.setattr(gate, "sys", types.SimpleNamespace(stdin=_FakeStdin(is_tty=False)))

    outcome = offer_teamspace_mission_state_migration(
        tmp_path,
        console=Console(),
        dry_run=False,
        assume_yes=True,
        repair_opt_in=False,
    )

    spy.assert_not_called()
    assert outcome.declined is True


def test_offer_never_raises_typer_exit(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """D-9/C3: none of the gate's return paths raise ``typer.Exit`` anymore."""
    _patch_readiness(monkeypatch, tmp_path)
    _spy_repair_repo(monkeypatch)
    monkeypatch.setattr(gate, "sys", types.SimpleNamespace(stdin=_FakeStdin(is_tty=True)))
    monkeypatch.setattr(typer, "confirm", lambda *_a, **_kw: False)

    try:
        offer_teamspace_mission_state_migration(tmp_path, console=Console(), dry_run=False, repair_opt_in=False)
    except typer.Exit:
        pytest.fail("offer_teamspace_mission_state_migration must never raise typer.Exit")
