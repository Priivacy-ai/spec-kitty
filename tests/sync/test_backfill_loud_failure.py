"""WP04 loud-failure acceptance tests for ``migrate backfill-runtime-state`` (#3476).

Pins the #3476 shape and its false-positive boundary at the *command* boundary via
``typer.testing.CliRunner`` over isolated temp roots (``build_mission`` +
``locate_project_root`` patched — never the live ``~/.spec-kitty``):

* T018 — a cutover/backfill write that **cannot land** (a legacy layout refuses the
  journal append with ``ProjectLayoutRequiredError``, ``journal.py:117-119``) must
  surface at the boundary: exit non-zero, an actionable message naming the mission
  and the recovery, and **no bare traceback** (``result.exception is None``). The
  exact #3476 shape pinned: *"seed write refused on a legacy layout is swallowed and
  the command reports success while backfilling nothing."*
* T019 — the false-positive fence: a legitimate already-migrated no-op and a
  ``--dry-run`` preview stay quiet and exit ``0`` with no loud-failure signal.
* T031 — the FR-010 boundary consumer: a recorded (WP05) unrecoverable capture
  failure is surfaced at the epilogue (report + non-zero) without crashing the
  command; a clean run stays silent.

The refusal is fault-injected at the exact verified-append seam the real legacy-layout
guard propagates through, so the behavioural pin (exit code + surfaced detail) holds
regardless of which WP finally wires the guard into the store append.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import Result
from typer.testing import CliRunner

from specify_cli.cli.commands.migrate_cmd import app as migrate_app
from specify_cli.event_journal.journal import ProjectLayoutRequiredError
from specify_cli.status.store import StoreError
from specify_cli.sync.emitter import CapturedFailure
from tests.unit.migration._backfill_fixture import build_mission

from specify_cli.core.saas_sync_config import sync_active
pytestmark = [
    pytest.mark.fast,
    pytest.mark.skipif(
        not sync_active(),
        reason="sync deactivated by default (#3799); set SPEC_KITTY_ENABLE_SAAS_SYNC=1 to run",
    ),
]

runner = CliRunner()

_LOCATE = "specify_cli.cli.commands.migrate_cmd.locate_project_root"
_APPEND_EVENTS = "specify_cli.migration.backfill_runtime_state.append_events_atomic_verified"
_APPEND_ANNOTATIONS = "specify_cli.migration.backfill_runtime_state.append_annotations_atomic_verified"
_SEED_BACKFILL = "specify_cli.migration.runtime_state_cutover.backfill_runtime_state"
_CAPTURED_FAILURES = "specify_cli.sync.emitter.captured_failures"

_REFUSAL_MESSAGE = "live payload writes require the project_only layout; legacy state is migration input only"


def _invoke(repo_root: Path, args: list[str]) -> Result:
    with patch(_LOCATE, return_value=repo_root):
        return runner.invoke(migrate_app, ["backfill-runtime-state", *args])


def _assert_no_leaked_exception(result: Result) -> None:
    """The command surfaced its outcome — it did not crash with a bare traceback.

    A clean ``typer.Exit`` rides out of ``CliRunner`` as ``SystemExit`` (only an
    exit-0 run yields ``None``); a *leaked domain exception* (e.g. the raw
    ``ProjectLayoutRequiredError``) is anything else. This pins "surfaced, not a
    bare traceback" without coupling to the exit code.
    """
    assert result.exception is None or isinstance(result.exception, SystemExit), (
        f"command leaked {result.exception!r} instead of surfacing it"
    )


def _refuse_write(*_args: object, **_kwargs: object) -> None:
    """Stand in for the legacy-layout journal refusal at the verified-append seam."""
    raise ProjectLayoutRequiredError(_REFUSAL_MESSAGE)


def _refuse_write_wrapped(*_args: object, **_kwargs: object) -> None:
    """The refusal in the store's wrapped ``StoreError`` form (cause chain preserved).

    Mirrors ``append_events_atomic_verified`` re-raising the underlying refusal as a
    ``StoreError`` subclass ``from`` the original ``ProjectLayoutRequiredError`` — the
    layout signal survives on ``__cause__`` for the boundary to recover.
    """
    raise StoreError(f"append failed: {_REFUSAL_MESSAGE}") from ProjectLayoutRequiredError(
        _REFUSAL_MESSAGE
    )


# --- T018: write-cannot-land surfaces as a failure ---------------------------


def test_write_cannot_land_surfaces_actionable_failure(tmp_path: Path) -> None:
    """#3476: a seed write refused on a legacy layout must be loud, not swallowed.

    Pre-fix, the refusal either crashes with a bare traceback or is swallowed and
    the command reports success while backfilling nothing. This asserts the
    boundary contract: exit non-zero, no leaked exception, and an actionable
    message naming the mission and the recovery.
    """
    build_mission(tmp_path, slug="legacy-refuser")

    with patch(_APPEND_EVENTS, _refuse_write), patch(_APPEND_ANNOTATIONS, _refuse_write):
        result = _invoke(tmp_path, ["--json"])

    assert result.exit_code != 0, result.output
    # Not a bare traceback: the failure is surfaced, not leaked.
    _assert_no_leaked_exception(result)
    payload = json.loads(result.output)
    assert payload["summary"]["failed"] == 1
    assert payload["summary"]["flipped"] == 0
    row = payload["results"][0]
    assert row["slug"] == "legacy-refuser"
    assert row["error"] is not None
    # Actionable: names what cannot happen and the recovery (layout cutover first).
    assert "could not land" in row["error"].lower()
    assert "layout" in row["error"].lower()
    # status_phase never flipped for a mission whose seed could not land.
    assert "status_phase" not in json.loads(
        (tmp_path / "kitty-specs" / "legacy-refuser" / "meta.json").read_text()
    )


def test_write_cannot_land_surfaces_in_human_summary(tmp_path: Path) -> None:
    """The rich (non-JSON) summary names the failing mission + the actionable reason."""
    build_mission(tmp_path, slug="legacy-refuser")

    with patch(_APPEND_EVENTS, _refuse_write), patch(_APPEND_ANNOTATIONS, _refuse_write):
        result = _invoke(tmp_path, [])

    assert result.exit_code != 0
    _assert_no_leaked_exception(result)
    assert "legacy-refuser" in result.output
    assert "could not land" in result.output.lower()


def test_write_cannot_land_wrapped_form_also_surfaces(tmp_path: Path) -> None:
    """The refusal in its store-wrapped ``EventPersistenceError`` form is caught too."""
    build_mission(tmp_path, slug="legacy-refuser")

    with patch(_APPEND_EVENTS, _refuse_write_wrapped), patch(
        _APPEND_ANNOTATIONS, _refuse_write_wrapped
    ):
        result = _invoke(tmp_path, ["--json"])

    assert result.exit_code != 0
    _assert_no_leaked_exception(result)
    payload = json.loads(result.output)
    assert payload["summary"]["failed"] == 1
    assert "could not land" in payload["results"][0]["error"].lower()


def test_seed_phase_direct_refusal_surfaces_via_cutover_mission(tmp_path: Path) -> None:
    """A ``ProjectLayoutRequiredError`` escaping the seed phase (not the append) is
    caught by ``cutover_mission`` itself and surfaced — the belt-and-suspenders
    branch for a refusal raised outside the backfill append seam.
    """
    build_mission(tmp_path, slug="legacy-refuser")

    with patch(_SEED_BACKFILL, side_effect=ProjectLayoutRequiredError(_REFUSAL_MESSAGE)):
        result = _invoke(tmp_path, ["--json"])

    assert result.exit_code != 0
    _assert_no_leaked_exception(result)
    payload = json.loads(result.output)
    assert payload["summary"]["failed"] == 1
    assert "could not land" in payload["results"][0]["error"].lower()


# --- T019: a legitimate no-op is NOT flagged ---------------------------------


def test_already_migrated_rerun_is_quiet(tmp_path: Path) -> None:
    """An already-migrated re-run seeds nothing, flips nothing, exits 0, no failure."""
    build_mission(tmp_path, slug="042-demo")
    first = _invoke(tmp_path, [])
    assert first.exit_code == 0

    result = _invoke(tmp_path, ["--json"])

    assert result.exit_code == 0, result.output
    _assert_no_leaked_exception(result)
    payload = json.loads(result.output)
    assert payload["summary"]["failed"] == 0
    assert payload["summary"]["seeded"] == 0
    assert all(r["failed"] is False for r in payload["results"])
    assert all(r["error"] is None for r in payload["results"])
    assert "could not land" not in result.output.lower()


def test_dry_run_preview_is_quiet(tmp_path: Path) -> None:
    """A --dry-run preview over a healthy legacy corpus is not a failure (exit 0)."""
    build_mission(tmp_path, slug="042-demo")

    result = _invoke(tmp_path, ["--dry-run", "--json"])

    assert result.exit_code == 0, result.output
    _assert_no_leaked_exception(result)
    payload = json.loads(result.output)
    assert payload["summary"]["failed"] == 0
    assert all(r["failed"] is False for r in payload["results"])
    assert "could not land" not in result.output.lower()
    assert "Failed (status_phase left untouched)" not in result.output


# --- T031: FR-010 boundary consumer of WP05's capture-failure flag -----------


def test_epilogue_surfaces_recorded_capture_failure(tmp_path: Path) -> None:
    """A recorded unrecoverable capture failure is surfaced at the epilogue (non-zero).

    Simulates WP05's emitter recording a swallowed capture failure during the run;
    the cutover itself is clean. The command must surface the failure (report +
    non-zero) WITHOUT crashing (``result.exception is None``).
    """
    build_mission(tmp_path, slug="042-demo")
    failure = CapturedFailure(site="emit_status_transition", summary="OSError('disk gone')")

    with patch(_CAPTURED_FAILURES, return_value=(failure,)):
        result = _invoke(tmp_path, [])

    assert result.exit_code != 0, result.output
    _assert_no_leaked_exception(result)
    assert "emit_status_transition" in result.output
    assert "capture" in result.output.lower()


def test_clean_run_stays_silent_on_capture_flag(tmp_path: Path) -> None:
    """No recorded capture failure -> no capture report, cutover success exits 0."""
    build_mission(tmp_path, slug="042-demo")

    result = _invoke(tmp_path, ["--json"])

    assert result.exit_code == 0, result.output
    _assert_no_leaked_exception(result)
    assert "capture failure" not in result.output.lower()
