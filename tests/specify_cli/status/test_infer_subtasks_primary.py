"""Regression test — WP02/T013 (FR-002/FR-003/FR-004).

Proves, through the PRODUCTION ``agent status emit`` -> ``MissionStatus.transition``
-> ``_resolve_review_gate_inputs`` route (``status/aggregate.py:717``, threaded by
T010) -- NOT a direct call to the standalone ``_infer_subtasks_complete`` -- that a
native ``in_progress -> for_review`` transition (no ``--subtasks-complete``, no
``--force``) on a coord-topology mission correctly:

* BLOCKS when the PRIMARY ``tasks.md``'s WP section has unchecked ``T###`` rows
  (proves T008's row-semantics fix and the T010 primary-surface threading -- the
  coord-branch husk this mission also carries has no ``tasks.md`` at all, so a
  pre-WP02 read of ``self.read_dir`` would have resolved the coord husk).
* ALLOWS when every row in the WP section is checked.
* BLOCKS when the PRIMARY ``tasks.md`` is genuinely absent (proves T009's
  fail-open removal -- an unprovable completeness state must block, never pass).
* ALLOWS when the WP section exists but has zero ``T###`` rows (the spec's
  zero-rows edge case -- T008 must not over-correct into always-blocking).
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from specify_cli.cli.commands.agent.status import app

pytestmark = [pytest.mark.integration, pytest.mark.git_repo]

runner = CliRunner()


@pytest.fixture(autouse=True)
def _disable_emit_side_effects(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep these tests focused on the local transition + completeness gate."""
    import specify_cli.status.emit as status_emit

    monkeypatch.setattr(status_emit, "_saas_fan_out", lambda *args, **kwargs: None)
    monkeypatch.setattr(status_emit, "fire_dossier_sync", lambda *args, **kwargs: None)


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _make_git_repo(root: Path) -> Path:
    repo = root / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-b", "main"], cwd=repo, check=True, capture_output=True, text=True)
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test User")
    (repo / ".kittify").mkdir()
    (repo / "README.md").write_text("test repo\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "init")
    return repo


def _status_event(slug: str, wp_id: str, from_lane: str, to_lane: str, event_id: str) -> dict:
    return {
        "event_id": event_id,
        "mission_slug": slug,
        "wp_id": wp_id,
        "from_lane": from_lane,
        "to_lane": to_lane,
        "at": "2026-06-01T12:00:00+00:00",
        "actor": "codex",
        "force": False,
        "execution_mode": "worktree",
        "evidence": None,
        "reason": None,
        "review_ref": None,
        "feature_slug": slug,
    }


def _write_events(feature_dir: Path, events: list[dict]) -> None:
    feature_dir.mkdir(parents=True, exist_ok=True)
    feature_dir.joinpath("status.events.jsonl").write_text(
        "\n".join(json.dumps(event) for event in events) + "\n",
        encoding="utf-8",
    )


def _build_coord_mission(tmp_path: Path, slug: str, *, tasks_md_body: str | None) -> Path:
    """Build a coord-topology mission with a primary ``tasks.md`` and a coord
    branch whose event log already has WP01 sitting in ``in_progress`` --
    the only lane from which ``in_progress -> for_review`` is even a legal edge.

    ``tasks_md_body=None`` omits ``tasks.md`` entirely (the T009 absent-primary
    case). The coord-branch dir intentionally never gets a ``tasks.md`` of its
    own -- ``tasks.md`` is a PRIMARY-partition artifact (``TASKS_INDEX``); a
    pre-WP02 read through the coord husk (``self.read_dir``) would find nothing
    there regardless of what the primary copy says, which is exactly the bug
    this WP closes.
    """
    mission_id = "01ABCDEF1234567890123456"
    mid8 = mission_id[:8]
    coord_branch = f"kitty/mission-{slug}-{mid8}"
    repo = _make_git_repo(tmp_path)

    primary_dir = repo / "kitty-specs" / slug
    primary_dir.mkdir(parents=True)
    (primary_dir / "meta.json").write_text(
        json.dumps(
            {
                "mission_id": mission_id,
                "coordination_branch": coord_branch,
                "mission_slug": slug,
            }
        ),
        encoding="utf-8",
    )
    if tasks_md_body is not None:
        (primary_dir / "tasks.md").write_text(tasks_md_body, encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "primary planning artifacts")

    _git(repo, "checkout", "-b", coord_branch)
    coord_branch_dir = repo / "kitty-specs" / f"{slug}-{mid8}"
    _write_events(
        coord_branch_dir,
        [
            _status_event(slug, "WP01", "planned", "claimed", "01HXYZ0123456789ABCDEFGH40"),
            _status_event(slug, "WP01", "claimed", "in_progress", "01HXYZ0123456789ABCDEFGH41"),
        ],
    )
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "coord in_progress")
    _git(repo, "checkout", "main")

    # Materialize the coord worktree the SAME way production does
    # (``CoordinationWorkspace.resolve``), so ``self.read_dir`` genuinely
    # resolves to an existing coord-husk directory instead of falling back to
    # primary via the create-window gate (aggregate's unmaterialised-coord
    # check: ``is_under_worktrees_segment(dir) and not dir.exists()``). This
    # is what makes the test exercise the REAL bug: the materialized coord
    # worktree DOES mirror the primary ``kitty-specs/<slug>/tasks.md`` sibling
    # (same git tree, checked out at the coord branch's commit) but the
    # coord-husk dir itself (``kitty-specs/<slug>-<mid8>/``) never has a
    # ``tasks.md`` of its own -- exactly the surface a pre-WP02 read of
    # ``self.read_dir`` would have consulted.
    from specify_cli.coordination.workspace import CoordinationWorkspace

    CoordinationWorkspace.resolve(repo, slug, mid8)

    return repo


def _emit_for_review(repo: Path, slug: str, *, implementation_evidence_present: bool = False):
    """Drive the native ``agent status emit ... --to for_review`` transition.

    ``--subtasks-complete`` and ``--force`` are deliberately never passed --
    this is the WP's headline assertion: completeness is INFERRED through the
    production route (T010's ``aggregate.py:717`` threading), not supplied by
    the caller. ``implementation_evidence_present`` is a separate, unrelated
    guard (out of this WP's scope -- WP02 only threads the primary surface for
    the subtasks-completeness inference); the "allowed" test cases pass it
    explicitly so the subtasks-completeness gate under test is isolated from
    it, while the "blocked" cases never reach the implementation-evidence
    guard at all (the subtasks guard short-circuits first).
    """
    args = [
        "emit",
        "WP01",
        "--to",
        "for_review",
        "--actor",
        "codex",
        "--mission",
        slug,
        "--json",
    ]
    if implementation_evidence_present:
        args.append("--implementation-evidence-present")
    with patch(
        "specify_cli.cli.commands.agent.status.locate_project_root",
        return_value=repo,
    ):
        return runner.invoke(app, args)


def test_blocks_on_unchecked_primary_subtask_rows(tmp_path: Path) -> None:
    """Unchecked T### row in the PRIMARY tasks.md -> blocked, no --force."""
    slug = "coord-blocked"
    tasks_md = "# Tasks\n\n## WP01\n- [ ] T001 implement thing\n"
    repo = _build_coord_mission(tmp_path, slug, tasks_md_body=tasks_md)

    result = _emit_for_review(repo, slug)

    assert result.exit_code != 0, result.stdout
    assert "completed subtasks" in result.stdout


def test_allowed_when_all_primary_rows_checked(tmp_path: Path) -> None:
    """All T### rows checked in the PRIMARY tasks.md -> transition allowed."""
    slug = "coord-allowed"
    tasks_md = "# Tasks\n\n## WP01\n- [x] T001 implement thing\n"
    repo = _build_coord_mission(tmp_path, slug, tasks_md_body=tasks_md)

    result = _emit_for_review(repo, slug, implementation_evidence_present=True)

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["from_lane"] == "in_progress"
    assert payload["to_lane"] == "for_review"


def test_blocks_when_primary_tasks_md_absent(tmp_path: Path) -> None:
    """T009: a genuinely-absent PRIMARY tasks.md is unprovable -> blocked, never fail-open."""
    slug = "coord-absent"
    repo = _build_coord_mission(tmp_path, slug, tasks_md_body=None)

    result = _emit_for_review(repo, slug)

    assert result.exit_code != 0, result.stdout
    assert "completed subtasks" in result.stdout


def test_allowed_when_wp_section_has_zero_rows(tmp_path: Path) -> None:
    """Spec zero-rows edge case: a WP section with no T### rows -> allowed."""
    slug = "coord-zero-rows"
    tasks_md = "# Tasks\n\n## WP01\nNo subtask rows in this section.\n"
    repo = _build_coord_mission(tmp_path, slug, tasks_md_body=tasks_md)

    result = _emit_for_review(repo, slug, implementation_evidence_present=True)

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["from_lane"] == "in_progress"
    assert payload["to_lane"] == "for_review"
