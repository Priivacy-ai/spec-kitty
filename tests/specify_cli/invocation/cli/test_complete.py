"""Integration tests for ``spec-kitty profile-invocation complete`` (WP03 T012/T014).

Covers FR-003/FR-012:
- closed_by="agent" is recorded on every CLI close (no --closed-by flag exists).
- --outcome is required and validated at the CLI boundary (never silently "done").
- Each outcome value is written verbatim.
- Double close exits 1 with the structured already-closed error (rich + --json).
- Evidence refused for advisory mode before any write; accepted for task_execution.
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from specify_cli import app as cli_app
from specify_cli.invocation.executor import ProfileInvocationExecutor
from specify_cli.invocation.modes import ModeOfWork
from specify_cli.invocation.writer import EVENTS_DIR

# Marked for mutmut sandbox skip — subprocess CLI invocation.
pytestmark = pytest.mark.non_sandbox


class ArgvCliRunner(CliRunner):
    def invoke(self, app, args=None, **kwargs):  # type: ignore[no-untyped-def]
        argv = ["spec-kitty", *(list(args) if args is not None and not isinstance(args, str) else [])]
        with patch.object(sys, "argv", argv):
            return super().invoke(app, args, **kwargs)


runner = ArgvCliRunner()

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "profiles"

_COMPACT_CTX = MagicMock()
_COMPACT_CTX.mode = "compact"
_COMPACT_CTX.text = "compact governance context"


def _setup_project(tmp_path: Path) -> Path:
    """Create minimal project structure with fixture profiles."""
    profiles_dir = tmp_path / ".kittify" / "profiles"
    profiles_dir.mkdir(parents=True)
    for yaml_file in FIXTURES_DIR.glob("*.agent.yaml"):
        shutil.copy(yaml_file, profiles_dir / yaml_file.name)
    (tmp_path / EVENTS_DIR).mkdir(parents=True, exist_ok=True)
    return tmp_path


def _open_invocation(project: Path, mode: ModeOfWork = ModeOfWork.TASK_EXECUTION) -> str:
    """Open an Op directly through the executor; return its invocation_id."""
    with patch(
        "specify_cli.invocation.executor.build_charter_context",
        return_value=_COMPACT_CTX,
    ):
        executor = ProfileInvocationExecutor(project)
        payload = executor.invoke(
            "implement the feature",
            profile_hint="implementer-fixture",
            mode_of_work=mode,
        )
    return payload.invocation_id


def _run_complete(project: Path, *args: str):  # type: ignore[no-untyped-def]
    with patch(
        "specify_cli.cli.commands.advise.find_repo_root", return_value=project
    ), patch(
        "specify_cli.invocation.executor.build_charter_context",
        return_value=_COMPACT_CTX,
    ):
        return runner.invoke(cli_app, ["profile-invocation", "complete", *args])


def _read_events(project: Path, invocation_id: str) -> list[dict[str, object]]:
    text = (project / EVENTS_DIR / f"{invocation_id}.jsonl").read_text(encoding="utf-8")
    return [json.loads(line) for line in text.splitlines() if line.strip()]


# ---------------------------------------------------------------------------
# closed_by="agent" on CLI closes; outcomes verbatim
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("outcome", ["done", "failed", "abandoned"])
def test_cli_close_records_outcome_verbatim_and_closed_by_agent(
    tmp_path: Path, outcome: str
) -> None:
    project = _setup_project(tmp_path)
    inv_id = _open_invocation(project)

    result = _run_complete(project, "--invocation-id", inv_id, "--outcome", outcome)

    assert result.exit_code == 0, result.output
    events = _read_events(project, inv_id)
    completed = events[1]
    assert completed["event"] == "completed"
    assert completed["outcome"] == outcome
    assert completed["closed_by"] == "agent"


def test_cli_does_not_expose_closed_by_flag(tmp_path: Path) -> None:
    """The sweep is the only other closer and calls the executor directly (FR-003)."""
    project = _setup_project(tmp_path)
    inv_id = _open_invocation(project)

    result = _run_complete(
        project,
        "--invocation-id", inv_id,
        "--outcome", "done",
        "--closed-by", "doctor_sweep",
    )
    assert result.exit_code != 0
    # The Op stays open: the unknown option is rejected before any write.
    events = _read_events(project, inv_id)
    assert [e["event"] for e in events] == ["started"]


# ---------------------------------------------------------------------------
# Explicit-outcome guard: missing/invalid outcome is a usage error
# ---------------------------------------------------------------------------


def test_cli_missing_outcome_is_usage_error(tmp_path: Path) -> None:
    project = _setup_project(tmp_path)
    inv_id = _open_invocation(project)

    result = _run_complete(project, "--invocation-id", inv_id)

    assert result.exit_code == 2, result.output
    # Nothing written — the Op is still open.
    events = _read_events(project, inv_id)
    assert [e["event"] for e in events] == ["started"]


def test_cli_invalid_outcome_is_usage_error(tmp_path: Path) -> None:
    project = _setup_project(tmp_path)
    inv_id = _open_invocation(project)

    result = _run_complete(project, "--invocation-id", inv_id, "--outcome", "finished")

    assert result.exit_code == 2, result.output
    events = _read_events(project, inv_id)
    assert [e["event"] for e in events] == ["started"]


# ---------------------------------------------------------------------------
# Double close: structured already-closed error, exit 1, rich + JSON
# ---------------------------------------------------------------------------


def test_double_close_exits_1_rich(tmp_path: Path) -> None:
    project = _setup_project(tmp_path)
    inv_id = _open_invocation(project)

    first = _run_complete(project, "--invocation-id", inv_id, "--outcome", "done")
    assert first.exit_code == 0, first.output

    second = _run_complete(project, "--invocation-id", inv_id, "--outcome", "done")
    assert second.exit_code == 1
    assert "already closed" in second.output

    # Idempotent: still exactly one completed event.
    events = _read_events(project, inv_id)
    assert [e["event"] for e in events].count("completed") == 1


def test_double_close_exits_1_json(tmp_path: Path) -> None:
    project = _setup_project(tmp_path)
    inv_id = _open_invocation(project)

    first = _run_complete(
        project, "--invocation-id", inv_id, "--outcome", "done", "--json"
    )
    assert first.exit_code == 0, first.output

    second = _run_complete(
        project, "--invocation-id", inv_id, "--outcome", "done", "--json"
    )
    assert second.exit_code == 1
    error_obj = json.loads(second.output.strip().splitlines()[-1])
    assert error_obj == {"error": "already_closed", "invocation_id": inv_id}


# ---------------------------------------------------------------------------
# Evidence mode gate through the CLI (FR-009): refused before any write
# ---------------------------------------------------------------------------


def test_cli_evidence_refused_for_advisory_before_any_write(tmp_path: Path) -> None:
    project = _setup_project(tmp_path)
    inv_id = _open_invocation(project, mode=ModeOfWork.ADVISORY)
    evidence = tmp_path / "evidence.md"
    evidence.write_text("# evidence", encoding="utf-8")

    result = _run_complete(
        project,
        "--invocation-id", inv_id,
        "--outcome", "done",
        "--evidence", str(evidence),
    )

    assert result.exit_code == 2
    # Pre-write rejection: started is still the only event; Op stays open.
    events = _read_events(project, inv_id)
    assert [e["event"] for e in events] == ["started"]
    assert not (project / ".kittify" / "evidence" / inv_id).exists()


def test_cli_evidence_accepted_for_task_execution(tmp_path: Path) -> None:
    project = _setup_project(tmp_path)
    inv_id = _open_invocation(project, mode=ModeOfWork.TASK_EXECUTION)
    evidence = tmp_path / "evidence.md"
    evidence.write_text("# evidence", encoding="utf-8")

    result = _run_complete(
        project,
        "--invocation-id", inv_id,
        "--outcome", "done",
        "--evidence", str(evidence),
    )

    assert result.exit_code == 0, result.output
    events = _read_events(project, inv_id)
    completed = events[1]
    assert completed["event"] == "completed"
    assert completed["closed_by"] == "agent"
    assert (project / ".kittify" / "evidence" / inv_id / "evidence.md").exists()


# ---------------------------------------------------------------------------
# Correlation links still appended after the completed event (FR-007)
# ---------------------------------------------------------------------------


def test_cli_close_appends_artifact_and_commit_links_after_completed(
    tmp_path: Path,
) -> None:
    project = _setup_project(tmp_path)
    inv_id = _open_invocation(project)

    result = _run_complete(
        project,
        "--invocation-id", inv_id,
        "--outcome", "done",
        "--artifact", "src/foo.py",
        "--artifact", "src/bar.py",
        "--commit", "deadbeef1234",
    )

    assert result.exit_code == 0, result.output
    events = [e["event"] for e in _read_events(project, inv_id)]
    assert events == [
        "started",
        "completed",
        "artifact_link",
        "artifact_link",
        "commit_link",
    ]
