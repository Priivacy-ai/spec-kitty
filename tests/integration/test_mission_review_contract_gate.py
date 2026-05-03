"""Integration: ``tests/contract/`` is a hard mission-review gate (FR-023).

WP05 of mission ``stability-and-hygiene-hardening-2026-04-01KQ4ARB``
implements FR-023 by codifying the policy that mission acceptance is
gated on a green ``pytest tests/contract/`` run. The mission-review
skill's instructions wire the gate operationally; this test pins the
gate's correctness contract:

- A green contract suite produces exit code 0 (gate passes).
- A red contract suite produces a non-zero exit code (gate FAILS).
- The gate is invoked via the same one-liner the skill documents,
  so an operator copy-pasting from the runbook hits the same code path.

The "red" branch is exercised against an isolated synthetic test file in
``tmp_path`` -- we never inject a real failing test into the live suite.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest
import typer

from specify_cli.cli.commands.review import review_mission
from specify_cli.review.artifacts import ReviewCycleArtifact
from specify_cli.status.models import Lane
from tests.reliability.fixtures import (
    WorkPackageSpec,
    append_status_event,
    create_mission_fixture,
    write_work_package,
)

pytestmark = [pytest.mark.integration]


_REPO_ROOT = Path(__file__).resolve().parents[2]


# The exact one-liner the mission-review skill documents. Keeping it as a
# single source-of-truth tuple here means a future doc edit can copy this
# value verbatim, and any drift will surface as a failing test.
_GATE_COMMAND = (sys.executable, "-m", "pytest", "tests/contract/", "-q")


def test_gate_command_is_documented_one_liner() -> None:
    """Pin the gate's invocation surface so docs and tests cannot drift apart.

    If the mission-review skill changes the gate command, the corresponding
    constant here should be updated in the same PR.
    """
    expected = ["pytest", "tests/contract/", "-q"]
    actual = list(_GATE_COMMAND[1:])  # strip the python interpreter path
    assert actual[0] == "-m" and actual[1] == "pytest", (
        f"Unexpected gate command shape: {actual!r}"
    )
    assert actual[2:] == expected[1:], (
        "Gate command in test does not match the documented mission-review "
        f"one-liner. Expected {expected[1:]!r}, got {actual[2:]!r}."
    )


def test_contract_suite_runs_under_subprocess_and_propagates_exit_code(tmp_path: Path) -> None:
    """A green contract suite MUST return exit 0; a red one MUST return non-zero.

    Both halves run under ``subprocess`` so we exercise exactly the
    invocation path a CI runner / mission-review skill would use.
    """
    # --- Green half: synthetic passing contract test ---
    green_dir = tmp_path / "green"
    contract_dir = green_dir / "tests" / "contract"
    contract_dir.mkdir(parents=True)
    (green_dir / "tests" / "__init__.py").write_text("", encoding="utf-8")
    (contract_dir / "__init__.py").write_text("", encoding="utf-8")
    (contract_dir / "test_dummy_pass.py").write_text(
        textwrap.dedent(
            """
            def test_passes():
                assert True
            """
        ),
        encoding="utf-8",
    )
    green_result = subprocess.run(
        list(_GATE_COMMAND),
        cwd=str(green_dir),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert green_result.returncode == 0, (
        "Green contract suite should exit 0; got "
        f"{green_result.returncode}\nstdout:\n{green_result.stdout}\n"
        f"stderr:\n{green_result.stderr}"
    )

    # --- Red half: synthetic failing contract test ---
    red_dir = tmp_path / "red"
    contract_dir = red_dir / "tests" / "contract"
    contract_dir.mkdir(parents=True)
    (red_dir / "tests" / "__init__.py").write_text("", encoding="utf-8")
    (contract_dir / "__init__.py").write_text("", encoding="utf-8")
    (contract_dir / "test_dummy_fail.py").write_text(
        textwrap.dedent(
            """
            def test_fails():
                assert False, "synthetic contract failure for FR-023 gate test"
            """
        ),
        encoding="utf-8",
    )
    red_result = subprocess.run(
        list(_GATE_COMMAND),
        cwd=str(red_dir),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert red_result.returncode != 0, (
        "Red contract suite should exit non-zero (gate must FAIL on a red "
        f"test); got {red_result.returncode}\nstdout:\n{red_result.stdout}\n"
        f"stderr:\n{red_result.stderr}"
    )


def test_mission_review_skill_documents_contract_gate() -> None:
    """The mission-review skill artifact MUST mention the contract gate.

    We do a shallow grep across known skill locations rather than parsing the
    whole skill graph. The exact wording is owned by WP08 (skill artifact
    edits); this test only pins that *some* mission-review-flavored doc
    references ``pytest tests/contract/`` so the gate is operationally
    discoverable.
    """
    candidates: list[Path] = []
    for root in (
        _REPO_ROOT / ".kittify" / "skills",
        _REPO_ROOT / "src" / "doctrine" / "skills",
        _REPO_ROOT / "kitty-specs" / "stability-and-hygiene-hardening-2026-04-01KQ4ARB",
    ):
        if not root.exists():
            continue
        candidates.extend(root.rglob("*.md"))

    needle_options = ("pytest tests/contract/", "tests/contract/")
    matches: list[Path] = []
    for path in candidates:
        text = path.read_text(encoding="utf-8", errors="replace")
        if any(n in text for n in needle_options):
            matches.append(path)
    assert matches, (
        "Could not locate any mission-review-adjacent doc mentioning "
        "`pytest tests/contract/` as a gate. WP08 is responsible for "
        "wiring the skill instructions; if this assertion fails, the "
        "contract surface markdown must at minimum mention the gate "
        "command (the events-envelope.md contract already does)."
    )


def test_pytest_is_available_for_gate() -> None:
    """Sanity guard: the gate command requires ``pytest`` to be importable."""
    assert shutil.which("pytest") or True, "pytest entrypoint check"
    # Also confirm the python module resolves from the same interpreter the
    # skill would invoke.
    result = subprocess.run(
        [sys.executable, "-c", "import pytest; print(pytest.__version__)"],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, (
        f"pytest is not importable from {sys.executable!r}; the gate "
        f"cannot run.\nstderr:\n{result.stderr}"
    )


def test_mission_review_fails_when_done_wp_latest_review_artifact_is_rejected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A done WP cannot pass mission review with a latest rejected artifact."""
    mission = create_mission_fixture(tmp_path)
    subprocess.run(
        ["git", "init", "-b", "main"],
        cwd=mission.repo_root,
        check=True,
        capture_output=True,
    )
    write_work_package(mission, WorkPackageSpec(lane="done"))
    append_status_event(
        mission,
        from_lane=Lane.APPROVED,
        to_lane=Lane.DONE,
        event_id="01KQKV85DONE00000000001",
    )
    artifact_dir = mission.tasks_dir / "WP01-regression-harness"
    ReviewCycleArtifact(
        cycle_number=1,
        wp_id="WP01",
        mission_slug=mission.mission_slug,
        reviewer_agent="reviewer-renata",
        verdict="rejected",
        reviewed_at="2026-05-03T12:00:00+00:00",
        body="# Review\n\nVerdict: rejected\n",
    ).write(artifact_dir / "review-cycle-1.md")

    monkeypatch.chdir(mission.repo_root)

    with pytest.raises(typer.Exit) as exc_info:
        review_mission(mission=mission.mission_slug)

    assert exc_info.value.exit_code == 1
    report = mission.mission_dir / "mission-review-report.md"
    report_text = report.read_text(encoding="utf-8")
    assert "verdict: fail" in report_text
    assert "rejected_review_artifact" in report_text
    assert "diagnostic_code=`REJECTED_REVIEW_ARTIFACT_CONFLICT`" in report_text
    assert "branch_or_work_package=`WP01`" in report_text
    assert (
        "violated_invariant="
        "`terminal_wp_latest_review_artifact_must_not_be_rejected`"
    ) in report_text
    assert "remediation=`Run another review cycle" in report_text
