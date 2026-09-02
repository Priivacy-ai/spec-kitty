"""WP04 (design-phase-orchestrator-api-01M1HE6M) -- ``check-prerequisites``/
``record-analysis`` orchestrator-api verbs (FR-004/FR-005, NFR-004/SK-93,
SK-06/#3133).

Acceptance scenarios (see
``kitty-specs/design-phase-orchestrator-api-01M1HE6M/tasks/WP04-check-prerequisites-record-analysis.md``):

1. ``check-prerequisites --mission <slug> --include-tasks`` returns the SAME
   validated-structure fields the host CLI's own ``check_prerequisites``
   Typer command (``mission_check_prerequisites.py:498``) returns for
   ``--json --include-tasks`` -- verified here by calling BOTH the
   orchestrator-api verb and the host function directly and diffing their
   payloads, not by re-deriving the shape independently (a real field-parity
   proof, not an assertion against a hand-copied fixture).
2. ``record-analysis`` (NFR-004 / SK-93): the artifact-verification mechanism
   is the SOLE success signal -- three genuinely distinct SC-005 scenarios:
   (a) swallowed-exception-but-written -> ``success: true`` (the SK-93
       regression guard: a raised exception after a real write must NOT be
       reported as failure).
   (b) hang-but-written -> the command returns within its enforced timeout
       bound regardless of the underlying write path blocking forever (a real
       wall-clock assertion, not "eventually returned").
   (c) stale-but-coincidentally-matching-verdict -> ``success: false`` (the
       SPEC-VERIFY-001 regression guard: a verdict-string match alone is
       never sufficient -- the re-read ``generated_at`` must also be strictly
       later than the call-start timestamp).
3. SK-06 / #3133: an ``unknown`` verdict (a report with no valid
   ``analysis-findings/v1`` carrier) is NEVER reported as ``success: true``,
   even when the underlying write genuinely succeeds with a fresh timestamp.

This is the RED-then-GREEN ATDD anchor (charter C-011): pre-implementation,
neither ``check-prerequisites`` nor ``record-analysis`` exist as
``@app.command``s on ``orchestrator_api.commands.app``, so every scenario
below fails at the Typer "no such command" / non-zero-exit level.

Real mission scaffolding (real files under ``kitty-specs/<slug>/``, real git
commits via the ``specify``/``plan``/``tasks`` verbs -- WP03) plus real
``analysis-report.md`` disk I/O -- hence ``integration``/``git_repo`` (NOT
``fast``), mirroring ``test_specify_plan_tasks_verbs.py``'s /
``test_transition_subtask_gate.py``'s precedent.
"""

from __future__ import annotations

import json
import subprocess
import threading
import time
from pathlib import Path
from typing import Any, cast

import pytest
from click.testing import Result
from typer.testing import CliRunner

from specify_cli.orchestrator_api.commands import app
from tests._factories import provision_test_charter

pytestmark = [pytest.mark.integration, pytest.mark.git_repo]

runner = CliRunner()

_POLICY = json.dumps(
    {
        "orchestrator_id": "test-orch",
        "orchestrator_version": "0.0.1",
        "agent_family": "claude",
        "approval_mode": "full_auto",
        "sandbox_mode": "workspace_write",
        "network_mode": "none",
        "dangerous_flags": [],
    }
)

_SUBSTANTIVE_SPEC = """# Spec — WP04 verbs

## Functional Requirements

| ID | Title | Description | Priority | Status |
|----|-------|-------------|----------|--------|
| FR-001 | Do the thing | Users can do the thing end to end. | High | Open |

## User Scenarios
A user does the thing via the orchestrator-api.
"""

_CARRIER_READY = (
    "---\n"
    "schema: analysis-findings/v1\n"
    "findings: []\n"
    "counts: {critical: 0, high: 0, medium: 0, low: 0, info: 0}\n"
    "---\n\n"
    "# Specification Analysis Report\n\nNo blocking findings.\n"
)

_LEGACY_NO_CARRIER_BODY = "# Specification Analysis Report\n\nNo carrier at all -- a legacy report.\n"


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
    )


def _init_repo(tmp_path: Path) -> Path:
    """A real, non-protected-branch git repo with an activated mission type."""
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(
        ["git", "init", "-b", "wp04-work"], cwd=repo, check=True, capture_output=True
    )
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test User")
    (repo / ".kittify").mkdir()
    (repo / "README.md").write_text("test repo\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "init")
    provision_test_charter(repo)
    return repo


def _run(repo: Path, args: list[str]) -> Result:
    """Invoke the real orchestrator-api ``app`` with cwd pinned at ``repo``."""
    import os

    prev_cwd = Path.cwd()
    os.chdir(repo)
    try:
        return runner.invoke(app, args, catch_exceptions=False)
    finally:
        os.chdir(prev_cwd)


def _envelope(result: Result) -> dict[str, Any]:
    return cast("dict[str, Any]", json.loads(result.output.strip().split("\n")[0]))


def _specify(repo: Path, mission_slug: str, *, mission_type: str = "software-dev") -> dict[str, Any]:
    result = _run(
        repo,
        [
            "specify",
            "--mission",
            mission_slug,
            "--mission-type",
            mission_type,
            "--topology",
            "single_branch",
            "--policy",
            _POLICY,
        ],
    )
    return _envelope(result)


def _build_mission(repo: Path, slug: str) -> tuple[str, Path]:
    """Specify + plan + tasks a real mission, matching WP03's proven flow.

    Returns ``(mission_slug, feature_dir)``. The mission carries real,
    committed spec.md/plan.md/tasks.md -- the exact set
    ``write_analysis_report``'s required-artifact check demands.
    """
    created = _specify(repo, slug)
    assert created["success"] is True, created
    mission_slug = created["data"]["mission_slug"]
    feature_dir = Path(created["data"]["feature_dir"])

    spec_file = Path(created["data"]["spec_file"])
    spec_file.write_text(_SUBSTANTIVE_SPEC, encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-m", "substantive spec")

    plan_result = _run(repo, ["plan", "--mission", mission_slug, "--policy", _POLICY])
    plan_envelope = _envelope(plan_result)
    assert plan_envelope["success"] is True, plan_envelope

    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir(exist_ok=True)
    (tasks_dir / "WP01-task.md").write_text(
        "---\n"
        "work_package_id: WP01\n"
        "title: Test WP01\n"
        "dependencies: []\n"
        "requirement_refs: [FR-001]\n"
        "subtasks: []\n"
        "owned_files:\n"
        "  - src/module_wp01/**\n"
        "authoritative_surface: src/module_wp01/\n"
        "execution_mode: code_change\n"
        "---\n\n# WP01\n\n## Activity Log\n",
        encoding="utf-8",
    )
    (feature_dir / "tasks.md").write_text(
        "# Tasks\n\n## Work Package WP01\n\n**Dependencies**: None\n",
        encoding="utf-8",
    )
    _git(repo, "add", "-A")
    _git(repo, "commit", "-m", "seed tasks")

    tasks_result = _run(repo, ["tasks", "--mission", mission_slug, "--policy", _POLICY])
    tasks_envelope = _envelope(tasks_result)
    assert tasks_envelope["success"] is True, tasks_envelope

    # Every phase transition leaves the tree clean before the next one starts
    # (matching a real orchestrator's own commit-between-phases workflow) --
    # `tasks` leaves its own bookkeeping residue (e.g. `.kittify/sync-state.json`)
    # uncommitted, which is unrelated to record-analysis's OWN dirty-tree guard
    # (SK-114) and must not be mistaken for it.
    status = _git(repo, "status", "--porcelain").stdout
    if status.strip():
        _git(repo, "add", "-A")
        _git(repo, "commit", "-m", "post-tasks bookkeeping")

    return mission_slug, feature_dir


def _record_analysis(
    repo: Path, mission_slug: str, body: str, *, tmp_path: Path, agent: str = "test-agent"
) -> dict[str, Any]:
    input_file = tmp_path / "report-body.md"
    input_file.write_text(body, encoding="utf-8")
    result = _run(
        repo,
        [
            "record-analysis",
            "--mission",
            mission_slug,
            "--input-file",
            str(input_file),
            "--agent",
            agent,
            "--policy",
            _POLICY,
        ],
    )
    return _envelope(result)


# ---------------------------------------------------------------------------
# Acceptance Scenario 1 -- check-prerequisites: field-parity with the host CLI
# ---------------------------------------------------------------------------


def test_check_prerequisites_field_parity_with_host_cli(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    mission_slug, _feature_dir = _build_mission(repo, "wp04-scenario1")

    import contextlib
    import io
    import os

    prev_cwd = Path.cwd()
    os.chdir(repo)
    try:
        from specify_cli.cli.commands.agent.mission_check_prerequisites import (
            check_prerequisites as host_check_prerequisites,
        )

        capture = io.StringIO()
        with contextlib.redirect_stdout(capture):
            host_check_prerequisites(feature=mission_slug, json_output=True, include_tasks=True)
        host_payload = json.loads(capture.getvalue().strip().split("\n")[0])
    finally:
        os.chdir(prev_cwd)

    result = _run(
        repo,
        ["check-prerequisites", "--mission", mission_slug, "--include-tasks"],
    )
    envelope = _envelope(result)

    assert envelope["success"] is True, envelope
    assert envelope["error_code"] is None
    data = envelope["data"]

    # Field-parity: every field the host CLI's own check_prerequisites Typer
    # command emits must be present with an identical value on the
    # orchestrator-api verb's payload (C-002: context only, no re-derivation).
    for key, value in host_payload.items():
        assert key in data, f"missing field {key!r} from orchestrator-api check-prerequisites payload"
        assert data[key] == value, f"field {key!r} diverges: host={value!r} orch={data[key]!r}"

    # Transport-contract identity field.
    assert data["mission_slug"] == mission_slug
    assert data["valid"] is True


def test_check_prerequisites_missing_mission_fails_closed(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)

    result = _run(
        repo,
        ["check-prerequisites", "--mission", "999-does-not-exist"],
    )
    envelope = _envelope(result)

    assert envelope["success"] is False
    assert envelope["error_code"] == "MISSION_NOT_FOUND"


# ---------------------------------------------------------------------------
# Acceptance Scenario 2 -- record-analysis: ordinary success path
# ---------------------------------------------------------------------------


def test_record_analysis_persists_and_verifies_via_reread(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    mission_slug, feature_dir = _build_mission(repo, "wp04-scenario2")

    envelope = _record_analysis(repo, mission_slug, _CARRIER_READY, tmp_path=tmp_path)

    assert envelope["success"] is True, envelope
    assert envelope["error_code"] is None
    data = envelope["data"]
    assert data["mission_slug"] == mission_slug
    assert data["verdict"] == "ready"
    report_path = feature_dir / "analysis-report.md"
    assert report_path.exists()
    assert Path(data["path"]) == report_path


# ---------------------------------------------------------------------------
# SK-06 / #3133 -- an unknown verdict is never reported as success
# ---------------------------------------------------------------------------


def test_record_analysis_never_reports_unknown_verdict_as_success(tmp_path: Path) -> None:
    """A legacy report (no analysis-findings/v1 carrier) writes real
    ``verdict: unknown`` content to disk (a genuinely successful WRITE) --
    but the orchestrator-api verb must still report ``success: false``,
    because an unrecorded/unknown verdict is never a trustworthy signal
    (the exact SK-06/#3133 near-miss: a malformed carrier producing
    ``verdict: unknown`` with exit 0 and no warning).
    """
    repo = _init_repo(tmp_path)
    mission_slug, feature_dir = _build_mission(repo, "wp04-scenario-sk06")

    envelope = _record_analysis(repo, mission_slug, _LEGACY_NO_CARRIER_BODY, tmp_path=tmp_path)

    assert envelope["success"] is False, envelope
    assert envelope["error_code"] == "RECORD_ANALYSIS_VERDICT_UNRELIABLE"
    # The write DID genuinely happen (unlike SC-005a/c) -- disk carries the
    # real unknown-verdict artifact; the API just refuses to call it success.
    report_path = feature_dir / "analysis-report.md"
    assert report_path.exists()
    assert "verdict: unknown" in report_path.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# SC-005(a) -- swallowed-exception-but-written (the SK-93 regression guard)
# ---------------------------------------------------------------------------


def test_record_analysis_sc005a_swallowed_exception_but_written_reports_success(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _init_repo(tmp_path)
    mission_slug, feature_dir = _build_mission(repo, "wp04-scenario-sc005a")

    import specify_cli.analysis_report as analysis_report_module

    real_write = analysis_report_module.write_analysis_report

    def _raises_after_real_write(**kwargs: Any) -> Any:
        real_write(**kwargs)
        raise RuntimeError("simulated SK-93 swallowed-exception-but-written failure")

    monkeypatch.setattr(analysis_report_module, "write_analysis_report", _raises_after_real_write)

    envelope = _record_analysis(repo, mission_slug, _CARRIER_READY, tmp_path=tmp_path)

    assert envelope["success"] is True, envelope
    assert envelope["error_code"] is None
    data = envelope["data"]
    assert data["verdict"] == "ready"
    report_path = feature_dir / "analysis-report.md"
    assert report_path.exists()


# ---------------------------------------------------------------------------
# SC-005(b) -- hang-but-written (the majority documented SK-93 failure shape)
# ---------------------------------------------------------------------------


def test_record_analysis_sc005b_hang_returns_within_enforced_timeout(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _init_repo(tmp_path)
    mission_slug, feature_dir = _build_mission(repo, "wp04-scenario-sc005b")

    import specify_cli.orchestrator_api.commands as orch_commands

    # Small bound so the test proves the mechanism quickly (the mocked write
    # NEVER returns/sets the event -- a real, unbounded hang).
    monkeypatch.setattr(orch_commands, "_RECORD_ANALYSIS_TIMEOUT_SECONDS", 0.3)

    never_set = threading.Event()

    def _hangs_forever(**_kwargs: Any) -> Any:
        never_set.wait()  # never set -> blocks forever
        raise AssertionError("unreachable")

    monkeypatch.setattr("specify_cli.analysis_report.write_analysis_report", _hangs_forever)

    started = time.monotonic()
    envelope = _record_analysis(repo, mission_slug, _CARRIER_READY, tmp_path=tmp_path)
    elapsed = time.monotonic() - started

    # A REAL enforced bound: comfortably under any sane CI-slowness margin,
    # nowhere near "the mocked call eventually returned" (it never does).
    assert elapsed < 5.0, f"record-analysis did not return within its enforced bound (took {elapsed}s)"
    assert envelope["success"] is False, envelope
    assert envelope["error_code"] == "RECORD_ANALYSIS_WRITE_NOT_CONFIRMED"
    # Nothing was written -- success is determined by the re-read, never by
    # whether the mocked call "returned".
    assert not (feature_dir / "analysis-report.md").exists()


# ---------------------------------------------------------------------------
# SC-005(c) -- stale-but-coincidentally-matching-verdict (SPEC-VERIFY-001)
# ---------------------------------------------------------------------------


def test_record_analysis_sc005c_stale_matching_verdict_reports_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _init_repo(tmp_path)
    mission_slug, feature_dir = _build_mission(repo, "wp04-scenario-sc005c")

    # Pre-seed a STALE analysis-report.md whose verdict happens to equal what
    # THIS call will submit ("ready"), but whose generated_at is ancient --
    # long before this test's call-start.
    stale_content = (
        "---\n"
        "schema_version: 1\n"
        "artifact_type: spec-kitty.analysis-report\n"
        "command: /spec-kitty.analyze\n"
        f"mission_slug: {mission_slug}\n"
        "mission_id: null\n"
        "generated_at: '2001-01-01T00:00:00+00:00'\n"
        "analyzer_agent: unknown\n"
        "input_artifacts: {}\n"
        "verdict: ready\n"
        "issue_counts: {critical: 0, high: 0, medium: 0, low: 0, info: 0}\n"
        "findings: []\n"
        "---\n\n"
        "# Stale pre-existing report\n"
    )
    (feature_dir / "analysis-report.md").write_text(stale_content, encoding="utf-8")
    # Commit the pre-seeded stale artifact so the ONLY thing exercised here is
    # the re-read/correlate logic -- not an incidental dirty-tree refusal.
    _git(repo, "add", "-A")
    _git(repo, "commit", "-m", "pre-seed stale analysis report")

    def _fails_before_writing(**_kwargs: Any) -> Any:
        raise RuntimeError("simulated early-exit failure before write_analysis_report")

    monkeypatch.setattr("specify_cli.analysis_report.write_analysis_report", _fails_before_writing)

    envelope = _record_analysis(repo, mission_slug, _CARRIER_READY, tmp_path=tmp_path)

    assert envelope["success"] is False, envelope
    assert envelope["error_code"] == "RECORD_ANALYSIS_WRITE_NOT_CONFIRMED"
    # The stale file is untouched -- verdict-string equality alone (both are
    # "ready") must NOT have been treated as sufficient evidence.
    on_disk = (feature_dir / "analysis-report.md").read_text(encoding="utf-8")
    assert "2001-01-01T00:00:00+00:00" in on_disk
