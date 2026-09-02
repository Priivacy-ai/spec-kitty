"""FR-004 fail-closed regression for ``orchestrator_api/commands.py``.

Guards ``_resolve_history_commit_args`` (the WP prompt-file history-commit
placement resolver): an ``ActionContextError`` from the canonical placement
seam (``resolve_placement_only``) must raise the structured
``PlacementResolutionRequired`` (D11 fail-closed surface, C-005) and never
silently degrade to ``CommitTarget(ref=<current checked-out branch>)`` — a
shadow write path that commits the WP prompt-file history entry to whatever
branch the operator happens to have checked out.

Pre-fix, this went RED: a forced ``ActionContextError`` fell through to the
``git branch --show-current`` fallback and returned a ``CommitTarget``
pointing at it instead of raising.

WP08 (runtime-state-eviction, FR-007 / T031) note: ``append-history`` no
longer calls ``_resolve_history_commit_args`` at all (it emits a ``note``
``InnerStateChanged`` annotation instead of committing a WP-file edit), so the
resolver's own fail-closed contract (the first two tests below) is pinned as a
standalone unit guarantee for any future WP-prompt-file commit caller. The
former end-to-end ``append-history`` regression test is replaced with the
command's *current* structured-envelope contract: a failed emit still returns
``_fail(...)``'s JSON error, never a bare traceback (see the last test below).
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from mission_runtime import ActionContextError
from specify_cli.core.errors import PlacementResolutionRequired
from specify_cli.orchestrator_api import commands as orch
from specify_cli.orchestrator_api.commands import app

pytestmark = [pytest.mark.fast]

runner = CliRunner()

_MISSION_ID = "01KV8NPCQ9ZX3R7W2M5T8H4FBD"
_MID8 = _MISSION_ID[:8]
_HUMAN_SLUG = "fail-closed-history-commit"
_MISSION_SLUG = f"{_HUMAN_SLUG}-{_MID8}"


def _seed_mission(tmp_path: Path) -> tuple[Path, Path]:
    """A minimal, realistic primary mission dir carrying one WP prompt file."""
    repo_root = tmp_path / "repo"
    primary = repo_root / "kitty-specs" / _MISSION_SLUG
    tasks_dir = primary / "tasks"
    tasks_dir.mkdir(parents=True)
    meta = {
        "mission_id": _MISSION_ID,
        "mission_slug": _MISSION_SLUG,
        "slug": _MISSION_SLUG,
        "mission_number": None,
        "mission_type": "software-dev",
        "status_phase": 2,
    }
    (primary / "meta.json").write_text(
        json.dumps(meta, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (tasks_dir / "WP01.md").write_text(
        "---\nwork_package_id: WP01\ntitle: Example\ndependencies: []\n---\n\n"
        "## Activity Log\n\n- seed\n",
        encoding="utf-8",
    )
    return repo_root, primary


def test_resolve_history_commit_args_raises_structured_error_on_action_context_error(
    tmp_path: Path,
) -> None:
    """Direct unit proof (C-005 red-first target): the resolver must raise
    ``PlacementResolutionRequired``, never build a ``current_branch`` fallback
    ``CommitTarget``.
    """
    repo_root, _primary = _seed_mission(tmp_path)

    with (
        patch(
            "mission_runtime.resolve_placement_only",
            side_effect=ActionContextError("PLACEMENT_UNRESOLVED", "boom"),
        ),
        pytest.raises(PlacementResolutionRequired),
    ):
        orch._resolve_history_commit_args(repo_root, _MISSION_SLUG)


def test_resolve_history_commit_args_error_never_carries_current_branch_ref(
    tmp_path: Path,
) -> None:
    """Belt-and-braces: even if some future refactor changes the exception
    type, the resolver must never return a ``CommitTarget`` whose ``ref`` is
    the plain checked-out branch name obtained via ``git branch
    --show-current`` -- that shadow write path is exactly what FR-004 closes.
    """
    repo_root, _primary = _seed_mission(tmp_path)

    with patch(
        "mission_runtime.resolve_placement_only",
        side_effect=ActionContextError("PLACEMENT_UNRESOLVED", "boom"),
    ):
        try:
            orch._resolve_history_commit_args(repo_root, _MISSION_SLUG)
        except PlacementResolutionRequired:
            pass
        else:
            pytest.fail(
                "expected PlacementResolutionRequired; a fallback CommitTarget "
                "was returned instead (FR-004 regression)"
            )


def test_append_history_surfaces_structured_error_code_on_emit_failure(
    tmp_path: Path,
) -> None:
    """End-to-end (WP08 / T031): a failed ``InnerStateChanged`` emit still
    surfaces the orchestrator-api's own structured ``HISTORY_COMMIT_FAILED``
    envelope -- never a bare traceback -- even though ``append-history`` no
    longer routes through ``_resolve_history_commit_args``/
    ``resolve_placement_only`` at all (that WP-file-commit placement seam is
    unreachable from this command post-WP08; see the module docstring).
    """
    repo_root, _primary = _seed_mission(tmp_path)

    with (
        patch.object(orch, "_get_main_repo_root", return_value=repo_root),
        patch(
            # WP02 (verdict-seam-boundary-hardening-01KZG179, T006): the
            # command now resolves this via ``from specify_cli.status import
            # emit_inner_state_changed`` (the facade symbol), not the
            # ``status.emit`` submodule object, so the mock target moves to
            # the facade's own already-bound attribute.
            "specify_cli.status.emit_inner_state_changed",
            side_effect=ValueError("boom"),
        ),
    ):
        result = runner.invoke(
            app,
            [
                "append-history",
                "--mission",
                _MISSION_SLUG,
                "--wp",
                "WP01",
                "--actor",
                "test-actor",
                "--note",
                "attempted history append",
            ],
            catch_exceptions=False,
        )

    envelope = json.loads(result.output.strip().split("\n")[0])
    assert envelope["success"] is False
    assert envelope["error_code"] == "HISTORY_COMMIT_FAILED"


# ---------------------------------------------------------------------------
# WP03 (design-phase-orchestrator-api-01M1HE6M / T013): specify/plan/tasks
# fail-closed policy gates. Pure in-process CliRunner invocations -- the
# --policy check runs BEFORE any mission resolution in all three verbs, so
# no mission fixture / _get_main_repo_root patch is needed (consistent with
# this file's ``fast`` marker: no subprocess, no real git I/O).
# ---------------------------------------------------------------------------


def test_specify_missing_policy_is_structured_not_bare() -> None:
    result = runner.invoke(
        app,
        ["specify", "--mission", "wp03-missing-policy", "--mission-type", "software-dev"],
        catch_exceptions=False,
    )

    envelope = json.loads(result.output.strip().split("\n")[0])
    assert envelope["success"] is False
    assert envelope["error_code"] == "POLICY_METADATA_REQUIRED"


def test_plan_missing_policy_is_structured_not_bare() -> None:
    result = runner.invoke(
        app,
        ["plan", "--mission", "wp03-missing-policy"],
        catch_exceptions=False,
    )

    envelope = json.loads(result.output.strip().split("\n")[0])
    assert envelope["success"] is False
    assert envelope["error_code"] == "POLICY_METADATA_REQUIRED"


def test_tasks_missing_policy_is_structured_not_bare() -> None:
    result = runner.invoke(
        app,
        ["tasks", "--mission", "wp03-missing-policy"],
        catch_exceptions=False,
    )

    envelope = json.loads(result.output.strip().split("\n")[0])
    assert envelope["success"] is False
    assert envelope["error_code"] == "POLICY_METADATA_REQUIRED"


def test_specify_invalid_policy_is_structured_not_bare() -> None:
    result = runner.invoke(
        app,
        [
            "specify",
            "--mission",
            "wp03-invalid-policy",
            "--mission-type",
            "software-dev",
            "--policy",
            "{}",
        ],
        catch_exceptions=False,
    )

    envelope = json.loads(result.output.strip().split("\n")[0])
    assert envelope["success"] is False
    assert envelope["error_code"] == "POLICY_VALIDATION_FAILED"


def test_plan_invalid_policy_is_structured_not_bare() -> None:
    result = runner.invoke(
        app,
        ["plan", "--mission", "wp03-invalid-policy", "--policy", "{}"],
        catch_exceptions=False,
    )

    envelope = json.loads(result.output.strip().split("\n")[0])
    assert envelope["success"] is False
    assert envelope["error_code"] == "POLICY_VALIDATION_FAILED"


def test_tasks_invalid_policy_is_structured_not_bare() -> None:
    result = runner.invoke(
        app,
        ["tasks", "--mission", "wp03-invalid-policy", "--policy", "{}"],
        catch_exceptions=False,
    )

    envelope = json.loads(result.output.strip().split("\n")[0])
    assert envelope["success"] is False
    assert envelope["error_code"] == "POLICY_VALIDATION_FAILED"
