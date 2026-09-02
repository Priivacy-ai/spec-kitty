"""Shared regression test for the FR-014 next-invocation lifecycle seam.

Mission ``design-phase-orchestrator-api-01M1HE6M``, WP02. Operator ruling
SPEC-FRESH2-001 (``kitty-specs/design-phase-orchestrator-api-01M1HE6M/reviews/
spec.ruling.md``) requires that the ``spec-kitty next --answer`` host-CLI path
and orchestrator-api's future ``answer-decision`` verb (WP08, strictly gated
on this WP) reach the SAME three side effects -- ``pair_previous_lifecycle_
record``, ``emit_mission_next_invoked``, ``write_issuance_lifecycle_record``
-- through one extracted, shared seam (``runtime.next.next_invocation_
lifecycle``) rather than two independently-maintained copies.

:func:`assert_lifecycle_seam_effects` is this WP's own deliverable (spec
SC-008): a caller-agnostic regression helper that fails if EITHER caller
stops writing the mission-events log or the issuance-lifecycle-record store.
WP08 imports and reuses this helper UNMODIFIED against its own
``answer-decision`` verb -- do not change its signature without coordinating
with WP08's author.

The module-level import below is this WP's ATDD RED signal: before T005
lands ``src/runtime/next/next_invocation_lifecycle.py``, this import raises
``ModuleNotFoundError`` at collection time -- a genuine RED (real,
not-yet-built behavior), not a vacuous assertion. A test that only drove the
EXISTING ``next_cmd --answer`` path (which already produces these side
effects via the pre-WP02 inline private functions) would NOT be RED
pre-WP02; the import failure is what makes this WP's ATDD test fail first.
"""

from __future__ import annotations

import json
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

# --- RED signal (T004): this module does not exist until T005 lands it. ---
from runtime.next.next_invocation_lifecycle import (
    emit_mission_next_invoked,
    pair_previous_lifecycle_record,
    write_issuance_lifecycle_record,
)

from specify_cli import app as cli_app
from specify_cli.invocation.lifecycle import read_lifecycle_records
from specify_cli.mission_v1.events import read_events

from tests._factories import provision_test_charter

pytestmark = [pytest.mark.integration, pytest.mark.git_repo]

runner = CliRunner()

# Referenced directly (not just imported) so a stale re-export or a renamed
# symbol fails loudly here too, not only via the CLI-path exercise below --
# and so ruff does not flag the RED-signal import as unused.
_SEAM_FUNCTIONS: tuple[Callable[..., Any], ...] = (
    pair_previous_lifecycle_record,
    emit_mission_next_invoked,
    write_issuance_lifecycle_record,
)

_MISSION_SLUG = "042-lifecycle-seam-feature"
_MISSION_TYPE = "lifecycle-seam-input-mission"


def assert_lifecycle_seam_effects(
    feature_dir: Path,
    repo_root: Path,
    mission_slug: str,
    run_action: Callable[[], None],
) -> None:
    """Assert ``run_action`` exercised all three lifecycle-seam side effects.

    ``run_action``: zero-arg callable performing the action under test.
    Agnostic to caller -- a ``next_cmd --answer`` invocation here, an
    orchestrator-api ``answer-decision`` call in WP08's extension.

    Snapshots the mission-events log and the issuance-lifecycle-record store
    before and after ``run_action()``, then asserts (via plain ``assert`` --
    this repo's pytest-native style, no bool return) that:

    1. A ``MissionNextInvoked`` entry was appended to ``mission-events.jsonl``
       (``emit_mission_next_invoked``).
    2. The count of paired (``completed``/``failed``) lifecycle records
       increased (``pair_previous_lifecycle_record`` paired an outstanding
       ``started`` record).
    3. The count of ``started`` lifecycle records increased
       (``write_issuance_lifecycle_record`` wrote a new issuance record).

    A failing assertion here points directly at which of the three seam
    functions regressed -- mission_slug is accepted for symmetry with a
    future caller that needs it to scope its own read, even though the CLI
    path here reads via ``repo_root``/``feature_dir`` alone.
    """
    del mission_slug  # accepted for shape-symmetry with WP08's extension

    events_before = read_events(feature_dir)
    records_before = read_lifecycle_records(repo_root)
    paired_before = sum(1 for r in records_before if r.phase != "started")
    started_before = sum(1 for r in records_before if r.phase == "started")

    run_action()

    events_after = read_events(feature_dir)
    records_after = read_lifecycle_records(repo_root)
    paired_after = sum(1 for r in records_after if r.phase != "started")
    started_after = sum(1 for r in records_after if r.phase == "started")

    new_events = events_after[len(events_before) :]
    assert any(e.get("type") == "MissionNextInvoked" for e in new_events), (
        "expected emit_mission_next_invoked to append a MissionNextInvoked "
        f"entry; new mission-events.jsonl entries: {new_events!r}"
    )
    assert paired_after > paired_before, (
        "expected pair_previous_lifecycle_record to pair an outstanding "
        f"`started` record (paired count {paired_before} -> {paired_after})"
    )
    assert started_after > started_before, (
        "expected write_issuance_lifecycle_record to write a new `started` "
        f"record (started count {started_before} -> {started_after})"
    )


# ---------------------------------------------------------------------------
# Fixture-mission builders.
#
# Verbatim-pattern reuse of ``tests/next/test_next_command_integration.py``'s
# proven, real (unmocked) fixture builders -- this repo's own established
# convention for this shape of fixture is to duplicate the helper into each
# consuming test file with an attribution comment (see
# ``tests/runtime/test_bridge_parity.py``'s ``_write_runtime_input_mission``,
# which cites the same origin) rather than import across test-suite
# boundaries. This WP's own mission needs a THREE-step chain (a plain first
# step, then an input-requiring step, then a plain last step) rather than
# the two-step ``tests/next`` fixture: see the ``run_action`` design note
# below for why.
# ---------------------------------------------------------------------------


def _init_git_repo(path: Path) -> None:
    subprocess.run(
        ["git", "init", "--initial-branch=main"], cwd=path, capture_output=True, check=True
    )
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"], cwd=path, capture_output=True, check=True
    )
    subprocess.run(["git", "config", "user.name", "Test"], cwd=path, capture_output=True, check=True)
    (path / "README.md").write_text("# test", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=path, capture_output=True, check=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=path, capture_output=True, check=True)


def _scaffold_project(tmp_path: Path, *, mission_slug: str, mission_type: str) -> Path:
    """Scaffold a minimal spec-kitty project with a mission carrying a real
    ``mission_id`` -- the lifecycle seam's PRIMARY-anchoring reads
    (``resolve_mission_identity(...).mission_id``) are a fail-closed no-op
    without one (FR-004/#2278), which would silently defeat this test.
    """
    repo_root = tmp_path / "project"
    repo_root.mkdir()
    _init_git_repo(repo_root)

    kittify = repo_root / ".kittify"
    kittify.mkdir()
    provision_test_charter(repo_root)

    from specify_cli.identity.project import ensure_identity

    ensure_identity(repo_root)

    feature_dir = repo_root / "kitty-specs" / mission_slug
    feature_dir.mkdir(parents=True)
    (feature_dir / "meta.json").write_text(
        json.dumps(
            {
                "mission_type": mission_type,
                "mission_id": "01HSEAMTESTMISSIONULID0001",
            }
        ),
        encoding="utf-8",
    )
    return repo_root


def _write_three_step_input_mission(repo_root: Path, mission_type: str) -> None:
    """A runtime-only mission: a plain first step, an input-requiring second
    step, then a plain third step.

    Deliberately three steps, not the two-step ``tests/next`` fixture shape:
    the runtime engine only registers a pending decision (and therefore only
    accepts ``--answer`` for it) once a PRIOR ``--result``-bearing call has
    revealed it, and that SAME revealing call unconditionally pairs whatever
    ``started`` record preceded it (``pair_previous_lifecycle_record`` runs
    on every ``--result`` call, before ``decide_next``, regardless of what
    ``decide_next`` returns). So for any acyclic linear mission, "pair an
    outstanding `started`" and "reveal input:<key> as pending" always land
    in the SAME call, and "answer input:<key>" and "write the next `started`"
    always land in a LATER, separate call -- an ``--answer`` call alone never
    produces both a pairing and a new `started` write in one shot. A third
    step (which needs no further input) lets the follow-up bare-result call
    made right after the ``--answer`` call both pair the ``--answer``-issued
    step AND issue the next one, so a single ``run_action`` closure of
    [``--answer`` call, follow-up call] genuinely exercises all three seam
    functions with real, observable deltas -- exactly what this test's
    RED-first discipline needs it to prove (T004 Definition of Done: "a
    behavioral assertion", not exercising a code path that happens to be a
    no-op for the fixture shape chosen).
    """
    mission_dir = repo_root / ".kittify" / "overrides" / "missions" / mission_type
    mission_dir.mkdir(parents=True, exist_ok=True)
    (mission_dir / "mission-runtime.yaml").write_text(
        (
            "mission:\n"
            f"  key: {mission_type}\n"
            f"  name: {mission_type}\n"
            "  version: '1.0.0'\n"
            "steps:\n"
            "  - id: step_one\n"
            "    title: Step One\n"
            "    description: Plain first step, no input required\n"
            "  - id: collect_input\n"
            "    title: Collect Input\n"
            "    description: Gather required answer\n"
            "    depends_on: [step_one]\n"
            "    requires_inputs: [approval]\n"
            "  - id: execute\n"
            "    title: Execute\n"
            "    depends_on: [collect_input]\n"
            "    description: Proceed with mission\n"
        ),
        encoding="utf-8",
    )
    template_dir = repo_root / ".kittify" / "overrides" / "command-templates"
    template_dir.mkdir(parents=True, exist_ok=True)
    for action in ("step_one", "collect_input", "execute"):
        (template_dir / f"{action}.md").write_text(
            f"# {action}\n\nRun the synthetic {action} step for the WP02 seam fixture.\n",
            encoding="utf-8",
        )


@pytest.fixture(autouse=True)
def _bypass_charter_preflight(monkeypatch: pytest.MonkeyPatch) -> None:
    """Bypass the charter preflight gate (verbatim pattern from
    ``tests/next/test_next_command_integration.py``): this fixture stages
    minimal mission state and does not run ``spec-kitty charter sync``, so
    the real preflight gate would otherwise block every advancing call this
    test makes before it ever reaches the seam code under test.
    """
    from specify_cli.charter_runtime.preflight.result import CharterPreflightResult

    result = CharterPreflightResult(passed=True, checks=[])
    monkeypatch.setattr(
        "specify_cli.charter_runtime.preflight.hook.run_preflight_or_abort",
        lambda *_args, **_kwargs: result,
    )
    monkeypatch.setattr(
        "specify_cli.charter_runtime.preflight.hook.run_preflight_for_dashboard",
        lambda *_args, **_kwargs: result,
    )


class TestNextAnswerLifecycleSeamEffects:
    """Drives the real ``spec-kitty next --answer`` CLI path (T004 step 3)."""

    def test_answer_path_pairs_and_issues_through_the_shared_seam(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        repo_root = _scaffold_project(
            tmp_path, mission_slug=_MISSION_SLUG, mission_type=_MISSION_TYPE
        )
        _write_three_step_input_mission(repo_root, mission_type=_MISSION_TYPE)
        monkeypatch.chdir(repo_root)
        feature_dir = repo_root / "kitty-specs" / _MISSION_SLUG
        agent = "wp02-seam-test"

        # --- setup: reach a real pending `decision_required`, outside the
        # measured window (see the fixture builder's docstring for why the
        # pairing of `step_one` is inseparable from revealing the decision).
        issue_step_one = runner.invoke(
            cli_app,
            ["next", "--agent", agent, "--mission", _MISSION_SLUG, "--result", "success", "--json"],
        )
        assert issue_step_one.exit_code == 0, issue_step_one.output
        assert json.loads(issue_step_one.stdout)["kind"] == "step"

        reveal_decision = runner.invoke(
            cli_app,
            ["next", "--agent", agent, "--mission", _MISSION_SLUG, "--result", "success", "--json"],
        )
        assert reveal_decision.exit_code == 0, reveal_decision.output
        decision_payload = json.loads(reveal_decision.stdout)
        assert decision_payload["kind"] == "decision_required"
        decision_id = decision_payload["decision_id"]
        assert decision_id == "input:approval"

        # --- run_action: the real `next --answer` invocation named by T004,
        # followed by the bare advancing call that (per the fixture design
        # note) is where the resulting `started` record actually gets paired
        # alongside the next step's own new `started` write.
        def run_action() -> None:
            answer_result = runner.invoke(
                cli_app,
                [
                    "next",
                    "--agent",
                    agent,
                    "--mission",
                    _MISSION_SLUG,
                    "--result",
                    "success",
                    "--answer",
                    "yes",
                    "--decision-id",
                    decision_id,
                    "--json",
                ],
            )
            assert answer_result.exit_code == 0, answer_result.output
            answered_payload = json.loads(answer_result.stdout)
            assert answered_payload["kind"] == "step"
            assert answered_payload["answered"] == decision_id

            advance_result = runner.invoke(
                cli_app,
                ["next", "--agent", agent, "--mission", _MISSION_SLUG, "--result", "success", "--json"],
            )
            assert advance_result.exit_code == 0, advance_result.output
            assert json.loads(advance_result.stdout)["kind"] == "step"

        assert_lifecycle_seam_effects(feature_dir, repo_root, _MISSION_SLUG, run_action)
