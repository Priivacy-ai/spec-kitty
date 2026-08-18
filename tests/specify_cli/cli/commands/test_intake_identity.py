"""Fail-closed checkout-identity guard for ``spec-kitty intake`` (FR-002, #3540).

Mission ``worktree-root-resolution-01M0B59R`` WP02.

``intake`` resolves its brief slot through ``find_repo_root`` (``task_utils``),
which deliberately re-anchors a linked worktree to the **primary** checkout.
That re-anchoring means an ``intake`` invoked from a lane worktree would write
the *primary's* shared, untracked ``.kittify/mission-brief.md`` slot — a silent
cross-checkout clobber (spec C-003 / #3128). The remediation is a fail-closed
**refusal** routed through the single WP01 ``FailClosedRefusal`` seam, never a
checkout-local redirect.

These tests use real ``git worktree`` topology so the guard resolves ownership
from decidable local git state exactly as production does.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
import typer
from typer.testing import CliRunner

from specify_cli.cli.commands.intake import IntakeCheckoutRefusedError, intake
from specify_cli.core.checkout_identity import FailClosedRefusal
from specify_cli.mission_brief import BRIEF_SOURCE_FILENAME, MISSION_BRIEF_FILENAME

pytestmark = [pytest.mark.non_sandbox, pytest.mark.regression]

runner = CliRunner()

_PRIMARY_BRIEF_CONTENT = "# Primary brief — DO NOT CLOBBER\n"


@pytest.fixture()
def intake_app() -> typer.Typer:
    """A minimal Typer app exposing only the ``intake`` command."""
    app = typer.Typer()
    app.command()(intake)
    return app


def _git(args: list[str], cwd: Path) -> None:
    subprocess.run(["git", *args], cwd=str(cwd), check=True, capture_output=True)


def _init_primary(root: Path) -> None:
    """Initialise a real git repository with one commit at ``root``."""
    root.mkdir(parents=True, exist_ok=True)
    _git(["init", "-q"], root)
    _git(["config", "user.email", "test@example.com"], root)
    _git(["config", "user.name", "Test"], root)
    (root / "README.md").write_text("seed\n", encoding="utf-8")
    _git(["add", "-A"], root)
    _git(["commit", "-qm", "seed"], root)


def _add_worktree(primary: Path, lane: Path) -> None:
    """Attach a real linked worktree at ``lane``."""
    _git(["worktree", "add", "-q", str(lane)], primary)


def _brief_slot(root: Path) -> Path:
    return root / ".kittify" / MISSION_BRIEF_FILENAME


def _source_slot(root: Path) -> Path:
    return root / ".kittify" / BRIEF_SOURCE_FILENAME


def _write_existing_primary_brief(primary: Path) -> bytes:
    """Populate the primary's shared brief slot; return its exact bytes."""
    kittify = primary / ".kittify"
    kittify.mkdir(parents=True, exist_ok=True)
    _brief_slot(primary).write_text(_PRIMARY_BRIEF_CONTENT, encoding="utf-8")
    _source_slot(primary).write_text("source_file: primary\n", encoding="utf-8")
    return _brief_slot(primary).read_bytes()


def _make_plan(tmp_path: Path) -> Path:
    plan = tmp_path / "incoming-plan.md"
    plan.write_text("# Lane plan\n", encoding="utf-8")
    return plan


def test_intake_from_lane_refuses_and_does_not_write_primary_slot(
    intake_app: typer.Typer, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A lane-worktree intake must refuse rather than clobber the primary slot.

    RED on base: ``find_repo_root`` re-anchors to the primary, so ``intake``
    writes the primary's ``.kittify/mission-brief.md`` — the assertions below
    (refusal raised; primary slot still absent; no lane slot) all fail.

    GREEN after: the guard fails closed via the WP01 ``FailClosedRefusal`` seam:
      (a) an ``IntakeCheckoutRefusedError`` carrying a ``FailClosedRefusal`` is
          raised;
      (b) its message names the target checkout path verbatim;
      (c) the primary slot is unchanged (here: still absent);
      (d) no brief slot was written in the lane worktree either — foreclosing
          the C-003/#3128-forbidden "redirect into the lane" fake.
    """
    primary = tmp_path / "primary"
    lane = tmp_path / "lane"
    _init_primary(primary)
    _add_worktree(primary, lane)
    plan = _make_plan(tmp_path)

    monkeypatch.chdir(lane)
    with pytest.raises(IntakeCheckoutRefusedError) as excinfo:
        runner.invoke(
            intake_app, [str(plan)], catch_exceptions=False
        )

    # (a) a FailClosedRefusal is raised (wrapped in the CLI refusal error).
    assert isinstance(excinfo.value.refusal, FailClosedRefusal)
    # (b) the message names the canonical target checkout path verbatim.
    assert str(primary.resolve()) in str(excinfo.value)
    # (c) primary slot unchanged — never created by the foreign write.
    assert not _brief_slot(primary).exists()
    # (d) no redirect: the lane never received a brief slot either.
    assert not _brief_slot(lane).exists()


def test_intake_force_from_lane_refuses_and_preserves_primary_slot(
    intake_app: typer.Typer, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``--force`` must not bypass the identity check (T009).

    A foreign-owned slot is refused even with ``--force``; the primary's
    existing brief stays byte-identical and the lane gets nothing.
    """
    primary = tmp_path / "primary"
    lane = tmp_path / "lane"
    _init_primary(primary)
    before = _write_existing_primary_brief(primary)
    _add_worktree(primary, lane)
    plan = _make_plan(tmp_path)

    monkeypatch.chdir(lane)
    with pytest.raises(IntakeCheckoutRefusedError) as excinfo:
        runner.invoke(
            intake_app, [str(plan), "--force"], catch_exceptions=False
        )

    assert isinstance(excinfo.value.refusal, FailClosedRefusal)
    assert str(primary.resolve()) in str(excinfo.value)
    # Primary slot byte-identical — --force did not overwrite it.
    assert _brief_slot(primary).read_bytes() == before
    # No redirect into the lane.
    assert not _brief_slot(lane).exists()


def test_intake_from_owner_checkout_writes_normally(
    intake_app: typer.Typer, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The owner checkout is unaffected: intake writes its own slot as before."""
    primary = tmp_path / "primary"
    _init_primary(primary)
    plan = _make_plan(tmp_path)

    monkeypatch.chdir(primary)
    result = runner.invoke(intake_app, [str(plan)], catch_exceptions=False)

    assert result.exit_code == 0, f"output: {result.output}"
    assert _brief_slot(primary).exists()
    assert _source_slot(primary).exists()
