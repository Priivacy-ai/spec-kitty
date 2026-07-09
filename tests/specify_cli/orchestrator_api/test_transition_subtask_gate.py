"""#2510: the orchestrator-api transition derives subtasks_complete server-side.

Field repro: an orchestrator-driven coordination mission moved four WPs
``in_progress -> for_review`` with ``force=false`` while every ``- [ ] T###``
row in ``tasks.md`` was unchecked. The orchestrator passes no
``--subtasks-complete``; the API forwarded ``None``; emit-time inference read
``tasks.md`` off the STATUS feature dir (the coord worktree husk — where the
PRIMARY-partition ``tasks.md`` never exists) and FAILED OPEN.

The API now mirrors the commit-gate precedent: when the caller does not
assert the flag (and is not forcing), it derives the value from the PRIMARY
planning surface before building the TransitionRequest.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from specify_cli.orchestrator_api.commands import app

pytestmark = [pytest.mark.fast]

runner = CliRunner()

_MISSION_ID = "01KV8NPCQ9ZX3R7W2M5T8H4FBD"
_MID8 = _MISSION_ID[:8]
_MISSION_SLUG = f"subtask-gate-repro-{_MID8}"

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


def _seed_mission(tmp_path: Path, *, tasks_md: str) -> Path:
    repo_root = tmp_path / "repo"
    primary = repo_root / "kitty-specs" / _MISSION_SLUG
    tasks_dir = primary / "tasks"
    tasks_dir.mkdir(parents=True)
    (primary / "meta.json").write_text(
        json.dumps(
            {
                "mission_id": _MISSION_ID,
                "mission_slug": _MISSION_SLUG,
                "slug": _MISSION_SLUG,
                "mission_number": None,
                "mission_type": "software-dev",
                "status_phase": 2,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (primary / "tasks.md").write_text(tasks_md, encoding="utf-8")
    (tasks_dir / "WP01.md").write_text(
        "---\nwork_package_id: WP01\ntitle: Example\ndependencies: []\n---\n\nbody\n",
        encoding="utf-8",
    )
    return repo_root


def _run_transition(repo_root: Path, extra_args: list[str] | None = None) -> object | None:
    """Invoke ``transition WP01 -> for_review`` capturing the TransitionRequest."""
    captured: list[object] = []

    def _capture(request, **_kwargs):  # noqa: ANN001 — mirrors the real signature
        captured.append(request)

        class _Event:
            from_lane = "in_progress"
            to_lane = "for_review"

        return _Event()

    with (
        patch(
            "specify_cli.orchestrator_api.commands._get_main_repo_root",
            return_value=repo_root,
        ),
        patch(
            "specify_cli.orchestrator_api.commands._enforce_for_review_commit_gate",
            return_value=None,
        ),
        patch(
            "specify_cli.coordination.status_transition.emit_status_transition_transactional",
            side_effect=_capture,
        ),
    ):
        result = runner.invoke(
            app,
            [
                "transition",
                "--mission",
                _MISSION_SLUG,
                "--wp",
                "WP01",
                "--to",
                "for_review",
                "--actor",
                "test-orch",
                "--policy",
                _POLICY,
                *(extra_args or []),
            ],
        )
    assert result.exit_code == 0, result.output
    return captured[0] if captured else None


_UNCHECKED_TASKS_MD = (
    "# Tasks\n\n## WP01 — Repro\n- [ ] T001 First (WP01)\n- [ ] T002 Second (WP01)\n"
)
_CHECKED_TASKS_MD = (
    "# Tasks\n\n## WP01 — Repro\n- [x] T001 First (WP01)\n- [x] T002 Second (WP01)\n"
)


def test_unasserted_flag_is_derived_false_from_primary_tasks_md(tmp_path: Path) -> None:
    """The field repro: no --subtasks-complete + unchecked PRIMARY rows must
    reach the guard as False — never None (which fails open off the husk)."""
    repo_root = _seed_mission(tmp_path, tasks_md=_UNCHECKED_TASKS_MD)
    request = _run_transition(repo_root)
    assert request is not None
    assert request.subtasks_complete is False


def test_unasserted_flag_is_derived_true_when_all_checked(tmp_path: Path) -> None:
    repo_root = _seed_mission(tmp_path, tasks_md=_CHECKED_TASKS_MD)
    request = _run_transition(repo_root)
    assert request is not None
    assert request.subtasks_complete is True


def test_explicit_caller_assertion_is_respected(tmp_path: Path) -> None:
    """Contract compatibility: an explicit --subtasks-complete is not overridden."""
    repo_root = _seed_mission(tmp_path, tasks_md=_UNCHECKED_TASKS_MD)
    request = _run_transition(repo_root, ["--subtasks-complete"])
    assert request is not None
    assert request.subtasks_complete is True


def test_force_skips_derivation(tmp_path: Path) -> None:
    repo_root = _seed_mission(tmp_path, tasks_md=_UNCHECKED_TASKS_MD)
    request = _run_transition(repo_root, ["--force"])
    assert request is not None
    assert request.subtasks_complete is None
