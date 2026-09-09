"""Guard-aligned tests for the #4032 absent-authority provisioning fix.

Mission: upgrade-no-migrations-provisioning-fix-01M20NK8, WP02 (T009).

The headline bug: ``spec-kitty upgrade`` used to fail (``failed`` outcome,
``"Managed skill provisioning requires an existing authority"``) on any
project whose ``.kittify/config.yaml`` authority is absent at assessment
time (the legacy, config-absent project shape -- see
``tests/upgrade/_fixtures.py::build_config_absent_project``). WP02's fix
decides the deferral once at the assessment/compiler layer
(``upgrade/assessment.py``), nulling ``PreparedUpgradeRepairs.provisioning``
so the finalizer's raw ``.apply()`` performs no create (C-001), and surfaces
a non-error ``deferred_provisioning`` diagnostic
(``contracts/deferred-provisioning-diagnostic.md``).

This module owns the FAITHFUL config-absent guard test (P4/FR-007 --
headline bug coverage that a naive re-pin of the pre-existing tests would
have skipped) plus the guard's own non-vacuity and degenerate-input
regression locks (T008/DIRECTIVE_043, C-006).
"""

from __future__ import annotations

import dataclasses
import json
import os
from pathlib import Path
from typing import cast

import pytest
import typer
from click.testing import Result
from typer.testing import CliRunner

from charter.activation.compiler import prepare_mission_type_activations
from specify_cli.cli.commands.upgrade import upgrade
from specify_cli.skills.installer import _prepare_skill_provisioning

from tests.upgrade._fixtures import build_config_absent_project, build_initialized_project

pytestmark = [pytest.mark.integration, pytest.mark.git_repo]

_test_app = typer.Typer(add_completion=False)
_test_app.command()(upgrade)
_runner = CliRunner()


def _run_upgrade(args: list[str], cwd: Path) -> Result:
    old_cwd = os.getcwd()
    try:
        os.chdir(cwd)
        return _runner.invoke(_test_app, args, catch_exceptions=False)
    finally:
        os.chdir(old_cwd)


def _last_json_line(output: str) -> dict[str, object]:
    lines = [line for line in output.strip().splitlines() if line.strip()]
    return cast("dict[str, object]", json.loads(lines[-1]))


# ---------------------------------------------------------------------------
# T009 -- the headline config-absent scenario, through the real upgrade()
# ---------------------------------------------------------------------------


def test_config_absent_upgrade_defers_provisioning_non_fatally(tmp_path: Path) -> None:
    """FR-001..FR-004/FR-007/NFR-001/INV-1/INV-2: config-absent project.

    Exit 0, ``up_to_date``, the ``deferred_provisioning`` signal carries real
    content (not merely a present key -- RT5), neither ``errors`` nor
    ``warnings`` gained an entry (the dedicated non-error channel), and the
    ``.kittify/config.yaml`` authority is NOT created by the run (C-001).
    This is the adopted T005 RED-first witness's own scenario (same fixture
    shape as ``test_upgrade_idempotency.py::
    test_no_migrations_no_op_repeat_is_clean_exit_zero``, which this fix also
    flips green -- see the WP02 Activity Log for both captured tracebacks).
    """
    project = tmp_path / "proj"
    build_config_absent_project(project)

    result = _run_upgrade(
        ["--target", "1.0.0a1", "--yes", "--no-worktrees", "--json"],
        cwd=project,
    )

    assert result.exit_code == 0, result.output
    payload = _last_json_line(result.output)
    assert payload["status"] == "up_to_date"
    assert payload["success"] is True
    assert payload["errors"] == []
    assert payload["warnings"] == []

    deferred = payload["deferred_provisioning"]
    assert deferred is not None, "deferred_provisioning must carry the non-error signal, not be absent/null"
    assert deferred == {"deferred": True, "reason": "no_config_authority"}, deferred

    # INV-1/C-001: the finalizer's raw `.apply()` must not create the
    # authority it was told to defer on.
    assert not (project / ".kittify" / "config.yaml").exists()


def test_config_absent_upgrade_human_mode_prints_deferred_note(tmp_path: Path) -> None:
    """Human-mode contract half: a `Note:` line reports the deferral.

    Exercises the SAME generic seam (WP01's ``_print_non_error_diagnostics``)
    from the non-JSON branch, so the deferral is observable in both output
    modes per ``contracts/deferred-provisioning-diagnostic.md``.
    """
    project = tmp_path / "proj"
    build_config_absent_project(project)

    result = _run_upgrade(["--target", "1.0.0a1", "--yes", "--no-worktrees"], cwd=project)

    assert result.exit_code == 0, result.output
    assert "Note:" in result.output
    assert "config authority" in result.output
    assert "deferred" in result.output


# ---------------------------------------------------------------------------
# T008 -- guard non-vacuity (DIRECTIVE_043) + C-006 degenerate-input lock
# ---------------------------------------------------------------------------


def test_prepare_skill_provisioning_raises_on_present_authority_non_canonical_descriptor(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Non-vacuity (RT2/DIRECTIVE_043): the guard still raises on a genuinely
    malformed/non-canonical descriptor -- proving the reduction to a "pure
    integrity validator" did not gut the raise arm to a no-op.

    Drives a PRESENT-authority (real, `spec-kitty init`-ed project -- NOT the
    now-benign absent-authority shape) descriptor whose
    ``mission_type_activations`` field has been tampered with, so it no
    longer equals a freshly recomputed
    ``prepare_mission_type_activations(root)``. Asserts the EXACT integrity
    ``ValueError`` raised FROM ``_prepare_skill_provisioning`` itself, not
    merely that some exception occurs.
    """
    project = build_initialized_project(tmp_path / "proj", monkeypatch)

    descriptor = prepare_mission_type_activations(project)
    assert descriptor.write.before_bytes is not None, "sanity: this must be a present-authority descriptor"

    tampered = dataclasses.replace(
        descriptor,
        mission_type_activations=(*descriptor.mission_type_activations, "not-a-canonical-mission-type"),
    )

    with pytest.raises(ValueError, match=r"^Managed skill provisioning differs from the canonical compiler$"):
        _prepare_skill_provisioning(project, tampered)


def test_prepare_skill_provisioning_present_but_empty_authority_does_not_hard_error(tmp_path: Path) -> None:
    """C-006 regression lock: a present-but-degenerate authority (empty
    ``.kittify/config.yaml``, ``before_bytes == b""``) must NOT hard-error
    through the reduced guard.

    Distinct from the mission's headline ABSENT-authority scenario (no file
    at all) -- this is a PRESENT, zero-byte file. Healing/validating its
    content is out of scope (C-006, scoped out to a follow-up); the guard
    reshape here must simply not regress the pre-existing non-fatal behavior
    for it.
    """
    project = tmp_path / "proj"
    kittify = project / ".kittify"
    kittify.mkdir(parents=True)
    (kittify / "config.yaml").write_bytes(b"")

    descriptor = prepare_mission_type_activations(project)
    assert descriptor.write.before_bytes == b""

    result = _prepare_skill_provisioning(project, descriptor)

    assert result is descriptor


# ---------------------------------------------------------------------------
# T010 -- smoke-exercise the real-init-ed builder (anti-dead-code)
# ---------------------------------------------------------------------------


def test_build_initialized_project_smoke(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """T010: the real-init-ed builder produces a project with a present
    config authority -- its only WP02 consumer besides the non-vacuity test
    above, so it is not dead-on-arrival for WP03 (its sole downstream
    consumer, per ``tests/upgrade/_fixtures.py``'s module docstring)."""
    project = build_initialized_project(tmp_path / "proj", monkeypatch)

    config_path = project / ".kittify" / "config.yaml"
    assert config_path.is_file()
    assert config_path.read_bytes() != b""

    descriptor = prepare_mission_type_activations(project)
    assert descriptor.write.before_bytes is not None
    assert not descriptor.write.absent_parents
