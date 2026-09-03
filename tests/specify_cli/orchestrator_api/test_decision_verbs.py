"""WP05 (design-phase-orchestrator-api-01M1HE6M) -- ``open-decision``/
``resolve-decision``/``defer-decision``/``cancel-decision`` orchestrator-api
verbs (FR-006/007/008/009, FR-012, NFR-001/002/005, C-001/003).

Acceptance scenarios (see
``kitty-specs/design-phase-orchestrator-api-01M1HE6M/tasks/WP05-decision-ledger-verbs.md``,
spec User Story 3):

1. ``open-decision --mission --origin specify <question payload> --policy``
   -> ``success: true``, ``data.decision_id``, ledger ``status: open`` on disk.
2. ``resolve-decision --mission --decision-id <id> <answer payload> --policy``
   -> ``success: true``, ``data.status: resolved``, ledger updated on disk.
3. ``defer-decision``/``cancel-decision`` -> the corresponding
   ``decisions/service.py`` function is invoked, ledger reflects the new
   status on disk.
4. An ``--origin`` value outside ``{charter, specify, plan}`` ->
   ``INVALID_ORIGIN_FLOW`` structured error, rejected BEFORE the service
   layer is ever called (no ledger entry created).
5. Terminal-transition rejection: ``resolve-decision`` on an
   already-resolved decision (with a DIFFERENT final answer) -> structured
   error, never a silent no-op success.

Mechanism A only (spec Clarification 3): these verbs wrap
``decisions/service.py``'s ``origin``-keyed ledger (``OriginFlow.CHARTER/
SPECIFY/PLAN``) 1:1, matching the existing host-CLI ``spec-kitty agent
decision open|resolve|defer|cancel`` subcommands -- unrelated to WP08's
``answer-decision`` (run-snapshot ``pending_decisions``, no ``OriginFlow``
concept).

This is the RED-then-GREEN ATDD anchor (charter C-011): pre-implementation,
none of ``open-decision``/``resolve-decision``/``defer-decision``/
``cancel-decision`` exist as ``@app.command``s on
``orchestrator_api.commands.app``, so every scenario below fails at the
Typer "no such command" / non-zero-exit level.

Real mission scaffolding (real files under ``kitty-specs/<slug>/`` via the
``specify`` verb -- WP03 -- plus real ``decisions/index.json`` ledger disk
I/O) -- hence ``integration``/``git_repo`` (NOT ``fast``, per this repo's own
``pytest.ini`` definition reserving ``fast`` for no-subprocess/no-git tests):
``fast``-marked would be invisible to ``integration-tests-core-misc``'s
collection filter, mirroring ``test_check_prerequisites_record_analysis.py``'s
precedent.
"""

from __future__ import annotations

import json
import subprocess
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
        ["git", "init", "-b", "wp05-work"], cwd=repo, check=True, capture_output=True
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
    """``specify`` a real mission (real, committed ``meta.json`` with a real
    ``mission_id``) -- the decisions ledger needs only ``meta.json``, not the
    full spec/plan/tasks scaffold WP04's fixture needed.

    Returns ``(mission_slug, feature_dir)``.
    """
    created = _specify(repo, slug)
    assert created["success"] is True, created
    mission_slug = created["data"]["mission_slug"]
    feature_dir = Path(created["data"]["feature_dir"])
    return mission_slug, feature_dir


def _open_decision(
    repo: Path,
    mission_slug: str,
    *,
    origin: str = "specify",
    input_key: str = "team_size",
    question: str = "How many engineers?",
    step_id: str | None = "step-1",
    slot_key: str | None = None,
    actor: str = "test-agent",
) -> dict[str, Any]:
    args = [
        "open-decision",
        "--mission",
        mission_slug,
        "--origin",
        origin,
        "--input-key",
        input_key,
        "--question",
        question,
        "--actor",
        actor,
        "--policy",
        _POLICY,
    ]
    if step_id is not None:
        args += ["--step-id", step_id]
    if slot_key is not None:
        args += ["--slot-key", slot_key]
    return _envelope(_run(repo, args))


def _read_index(feature_dir: Path) -> dict[str, Any]:
    index_path = feature_dir / "decisions" / "index.json"
    return cast("dict[str, Any]", json.loads(index_path.read_text(encoding="utf-8")))


def _entry_for(index: dict[str, Any], decision_id: str) -> dict[str, Any]:
    for entry in index["entries"]:
        if entry["decision_id"] == decision_id:
            return cast("dict[str, Any]", entry)
    raise AssertionError(f"decision_id {decision_id!r} not found in index: {index}")


# ---------------------------------------------------------------------------
# Acceptance Scenario 1 -- open-decision: creates an open ledger entry
# ---------------------------------------------------------------------------


def test_open_decision_creates_open_ledger_entry(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    mission_slug, feature_dir = _build_mission(repo, "wp05-scenario1")

    envelope = _open_decision(repo, mission_slug)

    assert envelope["success"] is True, envelope
    data = envelope["data"]
    assert data["mission_slug"] == mission_slug
    assert isinstance(data["decision_id"], str) and data["decision_id"]
    assert data["status"] == "open"
    assert data["idempotent"] is False

    index = _read_index(feature_dir)
    entry = _entry_for(index, data["decision_id"])
    assert entry["status"] == "open"
    assert entry["origin_flow"] == "specify"
    assert entry["input_key"] == "team_size"


def test_open_decision_is_idempotent_for_the_same_logical_key(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    mission_slug, _feature_dir = _build_mission(repo, "wp05-scenario1b")

    first = _open_decision(repo, mission_slug)
    second = _open_decision(repo, mission_slug)

    assert first["success"] is True, first
    assert second["success"] is True, second
    assert second["data"]["decision_id"] == first["data"]["decision_id"]
    assert second["data"]["idempotent"] is True


# ---------------------------------------------------------------------------
# Acceptance Scenario 2 -- resolve-decision: resolves and persists
# ---------------------------------------------------------------------------


def test_resolve_decision_marks_resolved_and_persists(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    mission_slug, feature_dir = _build_mission(repo, "wp05-scenario2")
    opened = _open_decision(repo, mission_slug)
    decision_id = opened["data"]["decision_id"]

    result = _run(
        repo,
        [
            "resolve-decision",
            "--mission",
            mission_slug,
            "--decision-id",
            decision_id,
            "--final-answer",
            "5",
            "--actor",
            "test-agent",
            "--policy",
            _POLICY,
        ],
    )
    envelope = _envelope(result)

    assert envelope["success"] is True, envelope
    data = envelope["data"]
    assert data["decision_id"] == decision_id
    assert data["status"] == "resolved"
    assert data["idempotent"] is False

    index = _read_index(feature_dir)
    entry = _entry_for(index, decision_id)
    assert entry["status"] == "resolved"
    assert entry["final_answer"] == "5"


# ---------------------------------------------------------------------------
# Acceptance Scenario 3 -- defer-decision / cancel-decision
# ---------------------------------------------------------------------------


def test_defer_decision_marks_deferred_and_persists(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    mission_slug, feature_dir = _build_mission(repo, "wp05-scenario3a")
    opened = _open_decision(repo, mission_slug)
    decision_id = opened["data"]["decision_id"]

    result = _run(
        repo,
        [
            "defer-decision",
            "--mission",
            mission_slug,
            "--decision-id",
            decision_id,
            "--rationale",
            "need more info before deciding",
            "--actor",
            "test-agent",
            "--policy",
            _POLICY,
        ],
    )
    envelope = _envelope(result)

    assert envelope["success"] is True, envelope
    assert envelope["data"]["status"] == "deferred"

    index = _read_index(feature_dir)
    entry = _entry_for(index, decision_id)
    assert entry["status"] == "deferred"
    assert entry["rationale"] == "need more info before deciding"


def test_cancel_decision_marks_canceled_and_persists(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    mission_slug, feature_dir = _build_mission(repo, "wp05-scenario3b")
    opened = _open_decision(repo, mission_slug)
    decision_id = opened["data"]["decision_id"]

    result = _run(
        repo,
        [
            "cancel-decision",
            "--mission",
            mission_slug,
            "--decision-id",
            decision_id,
            "--rationale",
            "no longer relevant",
            "--actor",
            "test-agent",
            "--policy",
            _POLICY,
        ],
    )
    envelope = _envelope(result)

    assert envelope["success"] is True, envelope
    assert envelope["data"]["status"] == "canceled"

    index = _read_index(feature_dir)
    entry = _entry_for(index, decision_id)
    assert entry["status"] == "canceled"
    assert entry["rationale"] == "no longer relevant"


# ---------------------------------------------------------------------------
# WP05-001 (review finding, severity 3) -- defer-decision/cancel-decision
# reject an empty/whitespace-only --rationale BEFORE the service layer is
# ever called, mirroring the host CLI's own cmd_defer/cmd_cancel guard
# (decision.py:341-348/391-398) verbatim. Pre-fix this silently succeeded
# and persisted the empty rationale to the ledger -- these negative-path
# tests assert BOTH the structured rejection AND that no ledger mutation
# occurs (the decision stays "open", never advances to a terminal status).
# ---------------------------------------------------------------------------


def test_defer_decision_empty_rationale_rejected_no_ledger_mutation(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    mission_slug, feature_dir = _build_mission(repo, "wp05-001-defer-empty")
    opened = _open_decision(repo, mission_slug)
    decision_id = opened["data"]["decision_id"]

    result = _run(
        repo,
        [
            "defer-decision",
            "--mission",
            mission_slug,
            "--decision-id",
            decision_id,
            "--rationale",
            "",
            "--actor",
            "test-agent",
            "--policy",
            _POLICY,
        ],
    )
    envelope = _envelope(result)

    assert envelope["success"] is False, envelope
    assert envelope["error_code"] == "DECISION_MISSING_STEP_OR_SLOT"

    index = _read_index(feature_dir)
    entry = _entry_for(index, decision_id)
    assert entry["status"] == "open"
    assert entry["rationale"] is None


def test_defer_decision_whitespace_only_rationale_rejected_no_ledger_mutation(
    tmp_path: Path,
) -> None:
    repo = _init_repo(tmp_path)
    mission_slug, feature_dir = _build_mission(repo, "wp05-001-defer-ws")
    opened = _open_decision(repo, mission_slug)
    decision_id = opened["data"]["decision_id"]

    result = _run(
        repo,
        [
            "defer-decision",
            "--mission",
            mission_slug,
            "--decision-id",
            decision_id,
            "--rationale",
            "   ",
            "--actor",
            "test-agent",
            "--policy",
            _POLICY,
        ],
    )
    envelope = _envelope(result)

    assert envelope["success"] is False, envelope
    assert envelope["error_code"] == "DECISION_MISSING_STEP_OR_SLOT"

    index = _read_index(feature_dir)
    entry = _entry_for(index, decision_id)
    assert entry["status"] == "open"
    assert entry["rationale"] is None


def test_cancel_decision_empty_rationale_rejected_no_ledger_mutation(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    mission_slug, feature_dir = _build_mission(repo, "wp05-001-cancel-empty")
    opened = _open_decision(repo, mission_slug)
    decision_id = opened["data"]["decision_id"]

    result = _run(
        repo,
        [
            "cancel-decision",
            "--mission",
            mission_slug,
            "--decision-id",
            decision_id,
            "--rationale",
            "",
            "--actor",
            "test-agent",
            "--policy",
            _POLICY,
        ],
    )
    envelope = _envelope(result)

    assert envelope["success"] is False, envelope
    assert envelope["error_code"] == "DECISION_MISSING_STEP_OR_SLOT"

    index = _read_index(feature_dir)
    entry = _entry_for(index, decision_id)
    assert entry["status"] == "open"
    assert entry["rationale"] is None


def test_cancel_decision_whitespace_only_rationale_rejected_no_ledger_mutation(
    tmp_path: Path,
) -> None:
    repo = _init_repo(tmp_path)
    mission_slug, feature_dir = _build_mission(repo, "wp05-001-cancel-ws")
    opened = _open_decision(repo, mission_slug)
    decision_id = opened["data"]["decision_id"]

    result = _run(
        repo,
        [
            "cancel-decision",
            "--mission",
            mission_slug,
            "--decision-id",
            decision_id,
            "--rationale",
            "\t\n  ",
            "--actor",
            "test-agent",
            "--policy",
            _POLICY,
        ],
    )
    envelope = _envelope(result)

    assert envelope["success"] is False, envelope
    assert envelope["error_code"] == "DECISION_MISSING_STEP_OR_SLOT"

    index = _read_index(feature_dir)
    entry = _entry_for(index, decision_id)
    assert entry["status"] == "open"
    assert entry["rationale"] is None


# ---------------------------------------------------------------------------
# WP05-002 (review finding, severity 1) -- DECISION_NOT_FOUND coverage for
# defer-decision/cancel-decision (previously exercised only via
# resolve-decision, though the wiring is identical -- documents parity in
# the test suite rather than relying on code-reading to infer it).
# ---------------------------------------------------------------------------


def test_defer_decision_nonexistent_decision_id_is_structured_not_bare(
    tmp_path: Path,
) -> None:
    repo = _init_repo(tmp_path)
    mission_slug, _feature_dir = _build_mission(repo, "wp05-002-defer-not-found")

    result = _run(
        repo,
        [
            "defer-decision",
            "--mission",
            mission_slug,
            "--decision-id",
            "01ARZ3NDEKTSV4RRFFQ69G5FAV",
            "--rationale",
            "need more info",
            "--actor",
            "test-agent",
            "--policy",
            _POLICY,
        ],
    )
    envelope = _envelope(result)

    assert envelope["success"] is False, envelope
    assert envelope["error_code"] == "DECISION_NOT_FOUND"


def test_cancel_decision_nonexistent_decision_id_is_structured_not_bare(
    tmp_path: Path,
) -> None:
    repo = _init_repo(tmp_path)
    mission_slug, _feature_dir = _build_mission(repo, "wp05-002-cancel-not-found")

    result = _run(
        repo,
        [
            "cancel-decision",
            "--mission",
            mission_slug,
            "--decision-id",
            "01ARZ3NDEKTSV4RRFFQ69G5FAV",
            "--rationale",
            "no longer relevant",
            "--actor",
            "test-agent",
            "--policy",
            _POLICY,
        ],
    )
    envelope = _envelope(result)

    assert envelope["success"] is False, envelope
    assert envelope["error_code"] == "DECISION_NOT_FOUND"


# ---------------------------------------------------------------------------
# Acceptance Scenario 4 -- FR-012: OriginFlow scope guard
# ---------------------------------------------------------------------------


def test_open_decision_invalid_origin_rejected(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    mission_slug, feature_dir = _build_mission(repo, "wp05-scenario4")

    envelope = _open_decision(repo, mission_slug, origin="analyze")

    assert envelope["success"] is False, envelope
    assert envelope["error_code"] == "INVALID_ORIGIN_FLOW"
    # Rejected BEFORE the service layer -- no ledger entry created.
    assert not (feature_dir / "decisions" / "index.json").exists()


def test_open_decision_invalid_origin_tasks_value_rejected(tmp_path: Path) -> None:
    """FR-012: OriginFlow has exactly three members -- ``tasks`` is NOT one
    of them (only charter/specify/plan), even though it is a real CLI-flow
    name elsewhere in this codebase.
    """
    repo = _init_repo(tmp_path)
    mission_slug, _feature_dir = _build_mission(repo, "wp05-scenario4b")

    envelope = _open_decision(repo, mission_slug, origin="tasks")

    assert envelope["success"] is False, envelope
    assert envelope["error_code"] == "INVALID_ORIGIN_FLOW"


# ---------------------------------------------------------------------------
# Acceptance Scenario 5 -- terminal-transition rejection
# ---------------------------------------------------------------------------


def test_resolve_decision_on_already_resolved_with_different_answer_rejected(
    tmp_path: Path,
) -> None:
    """Re-resolving an already-``resolved`` decision with a DIFFERENT answer
    must fail closed with a structured error -- never a silent no-op
    success that overwrites the recorded answer.
    """
    repo = _init_repo(tmp_path)
    mission_slug, feature_dir = _build_mission(repo, "wp05-scenario5")
    opened = _open_decision(repo, mission_slug)
    decision_id = opened["data"]["decision_id"]

    first_resolve = _run(
        repo,
        [
            "resolve-decision",
            "--mission",
            mission_slug,
            "--decision-id",
            decision_id,
            "--final-answer",
            "5",
            "--actor",
            "test-agent",
            "--policy",
            _POLICY,
        ],
    )
    assert _envelope(first_resolve)["success"] is True

    second_resolve = _run(
        repo,
        [
            "resolve-decision",
            "--mission",
            mission_slug,
            "--decision-id",
            decision_id,
            "--final-answer",
            "7",
            "--actor",
            "test-agent",
            "--policy",
            _POLICY,
        ],
    )
    envelope = _envelope(second_resolve)

    assert envelope["success"] is False, envelope
    assert envelope["error_code"] == "DECISION_TERMINAL_CONFLICT"

    # The ledger keeps the FIRST recorded answer -- never silently overwritten.
    index = _read_index(feature_dir)
    entry = _entry_for(index, decision_id)
    assert entry["final_answer"] == "5"
