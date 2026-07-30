"""Real-git committed-tree proof for the ``tracer-append`` command (WP10 / T038, FR-006).

Split out of ``test_tracer_writer.py`` (which stays pure-logic/``fast``) because
this file drives a REAL ``git`` repo via ``subprocess`` -- ``git worktree add``
for a real lane worktree, the production ``CoordinationWorkspace``/
``commit_for_mission`` machinery (no stubbed ``safe_commit``), and ``git show`` /
``git rev-parse`` on the resulting commits. Per the marker-correctness
architectural gate (``tests/architectural/test_pytest_marker_correctness.py``),
a subprocess-driven git test file MUST carry ``git_repo`` and MUST NOT carry
``fast`` -- CI selects it with ``-m git_repo``.

Proves, on committed git trees (not config/mock assertions):

1. A ``tracer-append`` invoked from a LANE worktree lands its commit on the
   COORDINATION branch (I-T1 / FR-006) -- ``git show <coord_branch>:...``
   succeeds and carries the entry.
2. The LANE branch receives **zero** new commits (its HEAD sha is byte-for-byte
   unchanged before/after) -- the literal #2980/#2549 barrier this WP closes.
3. The lane worktree's working tree stays clean (``git status --porcelain``
   empty) after the append -- the direct mechanism that previously blocked a
   subsequent ``move-task`` (a dirty lane checkout); re-driving the full
   ``move-task`` state machine is out of this WP's owned surface
   (``retrospective/`` + ``cli/commands/agent/tracer_append.py`` only).
4. Re-appending byte-identical content is a no-op: the coord branch gets no
   SECOND commit and the persisted file carries the entry line exactly once
   (I-T3 / FR-012 idempotency).
5. A blank ``--actor`` is guarded -- no commit lands anywhere (#2960).
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
import typer
from click.testing import Result
from typer.testing import CliRunner
from unittest.mock import patch

from specify_cli.cli.commands.agent.tracer_append import tracer_append
from tests.integration.coord_topology_fixture import _build_coord_topology

pytestmark = [pytest.mark.integration, pytest.mark.git_repo]

RUNNER = CliRunner()

_APP = typer.Typer()
_APP.command()(tracer_append)

_TRACER_MODULE = "specify_cli.cli.commands.agent.tracer_append"


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _git_probe(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        check=False,
        capture_output=True,
        text=True,
    )


def _create_lane_worktree(repo: Path, slug: str, *, lane_id: str = "lane-a") -> tuple[Path, str]:
    """Create a real lane branch + worktree off ``main`` (post-finalize shape)."""
    lane_branch = f"kitty/mission-{slug}-{lane_id}"
    lane_path = repo / ".worktrees" / f"{slug}-{lane_id}"
    lane_path.parent.mkdir(parents=True, exist_ok=True)
    _git(repo, "worktree", "add", "-b", lane_branch, str(lane_path), "main")
    return lane_path, lane_branch


def _invoke_from_lane(lane_path: Path, *args: str) -> Result:
    with patch(f"{_TRACER_MODULE}.locate_project_root", return_value=lane_path):
        return RUNNER.invoke(_APP, list(args))


# ---------------------------------------------------------------------------
# 1-3: lane-origin append lands on coord, zero lane commit, clean lane tree
# ---------------------------------------------------------------------------


def test_lane_origin_append_lands_on_coord_with_zero_lane_commit(tmp_path: Path) -> None:
    ctx = _build_coord_topology(tmp_path, write_husk_meta=False)
    lane_path, lane_branch = _create_lane_worktree(ctx.repo, ctx.slug)
    lane_sha_before = _git(ctx.repo, "rev-parse", lane_branch)

    result = _invoke_from_lane(
        lane_path,
        "--mission", ctx.slug,
        "--category", "tooling-friction",
        "--entry", "The daemon hung mid-decode on a 3MB payload.",
        "--actor", "claude",
        "--json",
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["ok"] is True
    assert payload["kind"] == "TRACER_FILE"
    assert payload["destination_surface"] == "coord"
    assert payload["row_or_entry_ref"]
    assert payload["status"] == "committed"

    # (1) Committed-tree proof: the entry lands on the COORD ref.
    rel = f"kitty-specs/{ctx.slug}/traces/tooling-friction.md"
    coord_show = _git_probe(ctx.repo, "show", f"{ctx.coord_branch}:{rel}")
    assert coord_show.returncode == 0, (
        f"tracer entry not found on coord ref {ctx.coord_branch!r}: {coord_show.stderr}"
    )
    assert "claude" in coord_show.stdout
    assert "The daemon hung mid-decode on a 3MB payload." in coord_show.stdout

    # (2) Zero new commits on the LANE branch -- the #2980/#2549 barrier.
    lane_sha_after = _git(ctx.repo, "rev-parse", lane_branch)
    assert lane_sha_after == lane_sha_before, (
        "tracer-append must not add any commit to the lane branch; "
        f"before={lane_sha_before} after={lane_sha_after}"
    )

    # (3) The lane worktree's own working tree stays clean (the direct
    # mechanism that previously blocked a subsequent move-task).
    lane_status = _git(lane_path, "status", "--porcelain")
    assert lane_status == "", f"lane worktree must stay clean; git status:\n{lane_status}"

    # Residue cleanup: the local staging copy on the PRIMARY checkout does not
    # linger as an untracked file, and the primary checkout itself stays clean.
    staged_local = ctx.repo / "kitty-specs" / ctx.slug / "traces" / "tooling-friction.md"
    assert not staged_local.exists(), "residue cleanup must remove the staged local copy"
    primary_status = _git(ctx.repo, "status", "--porcelain", "--", "kitty-specs")
    assert primary_status == "", (
        f"primary checkout's kitty-specs/ must stay clean; git status:\n{primary_status}"
    )


# ---------------------------------------------------------------------------
# 4: idempotent re-append (I-T3 / FR-012)
# ---------------------------------------------------------------------------


def test_identical_reappend_is_a_no_op_no_duplicate(tmp_path: Path) -> None:
    ctx = _build_coord_topology(tmp_path, write_husk_meta=False)
    lane_path, _lane_branch = _create_lane_worktree(ctx.repo, ctx.slug)

    args = (
        "--mission", ctx.slug,
        "--category", "approach",
        "--entry", "Adopted the seam over a bespoke commit path.",
        "--actor", "architect-alphonso",
        "--json",
    )

    first = _invoke_from_lane(lane_path, *args)
    assert first.exit_code == 0, first.output
    first_payload = json.loads(first.output)
    assert first_payload["status"] == "committed"

    coord_sha_after_first = _git(ctx.repo, "rev-parse", ctx.coord_branch)

    second = _invoke_from_lane(lane_path, *args)
    assert second.exit_code == 0, second.output
    second_payload = json.loads(second.output)
    assert second_payload["status"] == "unchanged"
    assert second_payload["row_or_entry_ref"] == first_payload["row_or_entry_ref"]

    coord_sha_after_second = _git(ctx.repo, "rev-parse", ctx.coord_branch)
    assert coord_sha_after_second == coord_sha_after_first, (
        "an identical re-append must not create a second commit on the coord branch"
    )

    rel = f"kitty-specs/{ctx.slug}/traces/approach.md"
    content = _git(ctx.repo, "show", f"{ctx.coord_branch}:{rel}")
    assert content.count("Adopted the seam over a bespoke commit path.") == 1, (
        "the entry must appear exactly once -- a re-append must not duplicate it"
    )


# ---------------------------------------------------------------------------
# 5: blank --actor is guarded, never a blanked commit (#2960)
# ---------------------------------------------------------------------------


def test_blank_actor_guarded_no_commit_lands_anywhere(tmp_path: Path) -> None:
    ctx = _build_coord_topology(tmp_path, write_husk_meta=False)
    lane_path, lane_branch = _create_lane_worktree(ctx.repo, ctx.slug)
    lane_sha_before = _git(ctx.repo, "rev-parse", lane_branch)

    result = _invoke_from_lane(
        lane_path,
        "--mission", ctx.slug,
        "--category", "tooling-friction",
        "--entry", "should never be persisted",
        "--actor", "   ",
        "--json",
    )

    assert result.exit_code != 0
    payload = json.loads(result.output)
    assert payload["ok"] is False
    assert "actor" in payload["error"].lower() or "attribution" in payload["error"].lower()

    # No commit landed anywhere: the coord branch never even got a tracer file.
    rel = f"kitty-specs/{ctx.slug}/traces/tooling-friction.md"
    coord_show = _git_probe(ctx.repo, "show", f"{ctx.coord_branch}:{rel}")
    assert coord_show.returncode != 0, (
        "a blank actor must never produce a committed (blank-attributed) entry"
    )
    lane_sha_after = _git(ctx.repo, "rev-parse", lane_branch)
    assert lane_sha_after == lane_sha_before
