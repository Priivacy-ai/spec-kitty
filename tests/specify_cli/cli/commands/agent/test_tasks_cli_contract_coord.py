"""Subprocess / real-git coord half of the ``agent tasks`` golden harness.

This is the subprocess / real-git coord-topology + branch-coverage-ratchet half
of the golden harness, split out of ``test_tasks_cli_contract.py`` so the pure
in-process contract tests can stay in the ``fast`` lane (marker-correctness
Rules 1 & 2).

This module adds the coord-topology + protected-branch fixture and the
mutating-command characterization the #2114 command-surface harness explicitly
punted. Everything here drives the LIVE ``app`` via ``CliRunner`` against REAL
on-disk git + coord-worktree state (no topology/resolver stub) so a later body
extraction (WP03+) can be proven byte-identical:

* **T003** -- a *real on-disk* coord-topology + protected-primary fixture
  (``_build_coord_protected_tree``) built on the canonical
  ``tests.integration.coord_topology_fixture`` un-stubbed topology builder plus
  the real ``CoordinationWorkspace`` git worktree. No resolver / topology stub.
* **T004** -- the ``move_task`` **coord skip-exit-0 arm** frozen with the
  DISTINGUISHING evidence the spec demands: primary-branch HEAD **unchanged** AND
  a coord event emitted AND the conditional ``--json`` keys
  (``wp_file_update`` / ``status_events_path``) -- never exit-0 + key-presence
  alone (a non-skip success also exits 0).
* **T005** -- the ``mark_status`` / ``map_requirements`` **refuse-exit-1** arms on
  the same tree; the skip-vs-refuse divergence is *deliberately preserved*
  (deferred #2300 -- do NOT reconcile it here; NFR-001 pure parity).
* **T006** -- EVERY other named ``move_task`` decision branch WP03 extracts
  (arbiter-override, rejected-verdict + its ``--skip-review-artifact-check``
  override, the FR-008a planning-artifact-WP ``done`` arm + its code-change
  contrast, review-currency refusal, and the for_review->in_progress force path)
  frozen as explicit driven cases.
* **T007** -- the no-stdout side-effect set (coord-vs-primary emission, WP-file
  writes, tracker-ref frontmatter, review-artifact override) PLUS a *from-harness*
  branch-coverage ratchet on ``move_task`` / ``status`` / ``map_requirements`` so
  no decision branch is left unfrozen before WP03.

NFR-001 (pure parity): this harness encodes NO intended behaviour change. It must
be green on the current base and pass identically before/after every later WP.
"""

from __future__ import annotations

import ast
import json
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Any

import pytest
from typer.testing import CliRunner

from specify_cli.cli.commands.agent import tasks_map_requirements as tasks_map_requirements_module
from specify_cli.cli.commands.agent import tasks_mapping_core as tasks_mapping_core_module
from specify_cli.cli.commands.agent import tasks_move_task as tasks_move_task_module
from specify_cli.cli.commands.agent import tasks_status_cmd as tasks_status_cmd_module
from specify_cli.cli.commands.agent import tasks_status_view as tasks_status_view_module
from specify_cli.cli.commands.agent import tasks_transition_core as tasks_transition_core_module
from specify_cli.cli.commands.agent.tasks import (
    _coord_topology_active,
    _skip_target_branch_commit,
    app,
)
from specify_cli.status.models import Lane, StatusEvent
from specify_cli.status.store import append_event
from tests.integration.coord_topology_fixture import (
    CoordTopologyContext,
    _build_coord_topology,
)
from tests.mocked_env import setup_mocked_env

# This golden harness spawns the CLI via ``subprocess`` (incl. ``git``) — it is
# an integration-lane test, not a sub-second pure-logic ``fast`` test, and must
# carry ``git_repo`` (marker-correctness Rules 1 & 2).
pytestmark = [pytest.mark.integration, pytest.mark.git_repo]

runner = CliRunner()


# ===========================================================================
# WP01 (tasks-py-degod / FR-001 / C-004 / NFR-001): mutating-command freeze
# ===========================================================================
#
# The sections below add the coord-topology + protected-branch fixture and the
# mutating-command characterization the #2114 harness above explicitly punted.
# Everything here drives the LIVE ``app`` via ``CliRunner`` against REAL on-disk
# git + coord-worktree state (no topology/resolver stub) so a later body
# extraction (WP03+) can be proven byte-identical.

# A fixed, realistic 26-char Crockford-base32 ULID prefix already embedded in the
# coord fixture slug (``<human>-01KW2E7A``) — reused for seeded event ids so the
# test data is production-shaped, never a toy placeholder.
_MID8 = "01KW2E7A"


# ---------------------------------------------------------------------------
# T003 -- coord-topology + protected-branch fixture (REAL on-disk state)
# ---------------------------------------------------------------------------


def _status_event_dict(slug: str, event_id: str, from_lane: str, to_lane: str, at: str) -> dict[str, Any]:
    """One parseable (``evidence=None``) status-event JSONL record.

    The canonical coord fixture's own seed events use a *string* ``evidence``
    marker (a resolver-smoke sentinel) which is intentionally UNPARSEABLE by the
    real reducer. The mutating commands round-trip events through the reducer AND
    ``locate_work_package`` reads the primary event log per WP file, so both legs
    must be parseable here. We therefore overwrite the fixture's coord + decoy
    event files with valid records (distinct lanes keep the primary decoy a
    wrong-leg detector — see ``_build_coord_protected_tree``).
    """
    return {
        "actor": "coord-fixture",
        "at": at,
        "event_id": event_id,
        "evidence": None,
        "execution_mode": "code_change",
        "feature_slug": slug,
        "force": False,
        "from_lane": from_lane,
        "reason": None,
        "review_ref": None,
        "to_lane": to_lane,
        "wp_id": "WP01",
    }


def _write_events(path: Path, events: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for event in events:
            handle.write(json.dumps(event) + "\n")


def _build_coord_protected_tree(root: Path) -> CoordTopologyContext:
    """Materialise a REAL coord-topology + protected-primary mission tree.

    Vehicle for T004-T007. Built on the canonical un-stubbed topology builder
    (``tests.integration.coord_topology_fixture._build_coord_topology``) which
    creates a real git repo, a real coordination branch, and a real
    ``CoordinationWorkspace`` git worktree (the STATUS husk). The primary
    ``target_branch`` defaults to ``main`` — which the default
    ``ProtectionPolicy`` treats as PROTECTED — so ``_skip_target_branch_commit``
    is genuinely ``True`` (coord worktree present AND primary protected). Nothing
    about the topology is stubbed.

    Adjustments over the base fixture (both are on-disk data, not stubs):

    * The coord husk event log is rewritten so WP01 is at ``in_progress`` via
      valid, reducer-parseable events (the base fixture's string-``evidence``
      seed is a resolver-smoke sentinel the reducer rejects).
    * The primary DECOY event log is rewritten to valid-but-DISTINCT-lane
      (``planned``) events so it stays a loud wrong-leg detector while remaining
      parseable for ``locate_work_package``'s per-file lane read.
    """
    ctx = _build_coord_topology(root, write_husk_meta=False)
    _write_events(
        ctx.status_events_path,
        [
            _status_event_dict(ctx.slug, f"{_MID8}FC0000000000000001", "planned", "claimed", "2026-06-26T00:00:00+00:00"),
            _status_event_dict(ctx.slug, f"{_MID8}FC0000000000000002", "claimed", "in_progress", "2026-06-26T01:00:00+00:00"),
        ],
    )
    _write_events(
        ctx.decoy_events_path,
        [_status_event_dict(ctx.slug, "01KW2E7BFC0000000000000009", "planned", "planned", "2026-06-26T00:00:00+00:00")],
    )
    (ctx.primary_feature_dir / "tasks.md").write_text("# Work Packages\n\n## WP01 - fixture\n", encoding="utf-8")
    (ctx.primary_feature_dir / "spec.md").write_text("# Spec\n\nFR-001 do a thing.\nFR-002 do another.\n", encoding="utf-8")
    return ctx


def test_coord_protected_tree_is_real_on_disk_state(tmp_path: Path) -> None:
    """T003: the fixture builds REAL coord state — no topology/resolver stub.

    Asserts every load-bearing invariant of the vehicle so T004-T007 cannot be
    silently defanged by a stubbed topology (the exact failure mode the WP guards
    against): the coord worktree exists on disk, the coord branch exists in git,
    ``_coord_topology_active`` is ``True`` (probed via the real git registry), and
    ``_skip_target_branch_commit`` is ``True`` for the protected primary but
    ``False`` for a non-protected branch (the determinant of the skip arm).
    """
    ctx = _build_coord_protected_tree(tmp_path)

    # Real coord worktree directory (created via CoordinationWorkspace, not mocked).
    coord_worktree_root = ctx.coord_feature_dir.parents[1]
    assert coord_worktree_root.is_dir()
    assert (coord_worktree_root / ".git").exists(), "coord worktree must be a real linked git worktree"

    # Real coordination branch in the repo.
    branches = subprocess.run(
        ["git", "-C", str(ctx.repo), "branch", "--list", ctx.coord_branch],
        capture_output=True, text=True, check=True,
    ).stdout
    assert ctx.coord_branch in branches, "coordination branch must exist in git"

    # Topology probe uses the real git worktree registry (unstubbed).
    assert _coord_topology_active(ctx.repo, ctx.slug) is True

    # The skip determinant: True for the protected primary, False otherwise.
    assert _skip_target_branch_commit(ctx.repo, ctx.slug, "main") is True
    assert _skip_target_branch_commit(ctx.repo, ctx.slug, "feature/not-protected") is False


# ---------------------------------------------------------------------------
# Shared drive helpers for the simple (non-coord) move_task guard branches.
# ---------------------------------------------------------------------------
#
# Several move_task decision branches are topology-independent; freezing them on
# a lightweight non-coord mission keeps each case deterministic. The recipe
# mirrors the sibling ``test_tasks.py`` (``_build_wp_file`` + ``_seed_wp_event``
# + ``setup_mocked_env`` with the review-gate seams patched) — the codebase's own
# way of driving these guards.

_REVIEW_GATE_BYPASS: dict[str, Any] = {"_validate_ready_for_review": (True, []), "_check_unchecked_subtasks": []}


def _simple_mission(root: Path, slug: str, *, execution_mode: str = "code_change") -> Path:
    """Create a minimal, real-on-disk WP mission under *root*; return feature_dir."""
    feature_dir = root / "kitty-specs" / slug
    (feature_dir / "tasks").mkdir(parents=True)
    (root / ".kittify").mkdir(exist_ok=True)
    (feature_dir / "tasks" / "WP01-fixture.md").write_text(
        "---\n"
        "work_package_id: WP01\n"
        "title: Fixture WP01\n"
        f"execution_mode: {execution_mode}\n"
        "agent: testbot\n"
        "---\n\n# WP01\n\n## Activity Log\n",
        encoding="utf-8",
    )
    (feature_dir / "tasks.md").write_text("# Work Packages\n\n## WP01 - fixture\n- [ ] T001 do a thing\n", encoding="utf-8")
    (feature_dir / "spec.md").write_text("# Spec\n\nFR-001 do a thing.\nFR-002 do another.\n", encoding="utf-8")
    return feature_dir


def _seed_event(
    feature_dir: Path, from_lane: str, to_lane: str, ordinal: int, *, review_ref: str | None = None
) -> None:
    """Append one real StatusEvent (production-shaped ULID event id)."""
    append_event(
        feature_dir,
        StatusEvent(
            event_id=f"{_MID8}FC00000000000000{ordinal:04d}",
            mission_slug=feature_dir.name,
            wp_id="WP01",
            from_lane=Lane(from_lane),
            to_lane=Lane(to_lane),
            at=f"2026-01-01T00:00:{ordinal:02d}+00:00",
            actor="test",
            force=True,
            execution_mode="worktree",
            review_ref=review_ref,
        ),
    )


def _seed_chain(feature_dir: Path, lanes: list[tuple[str, str]]) -> None:
    for ordinal, (from_lane, to_lane) in enumerate(lanes, start=1):
        _seed_event(feature_dir, from_lane, to_lane, ordinal)


def _write_review_cycle(feature_dir: Path, cycle: int, verdict: str) -> Path:
    """Write a ``review-cycle-N.md`` artifact next to the WP file (``tasks/WP01-fixture``)."""
    wp_dir = feature_dir / "tasks" / "WP01-fixture"
    wp_dir.mkdir(parents=True, exist_ok=True)
    artifact = wp_dir / f"review-cycle-{cycle}.md"
    artifact.write_text(
        f"---\n"
        f"cycle_number: {cycle}\n"
        f"mission_slug: {feature_dir.name}\n"
        f"reviewed_at: '2026-04-30T12:00:00Z'\n"
        f"reviewer_agent: reviewer-renata\n"
        f"verdict: {verdict}\n"
        f"wp_id: WP01\n"
        f"---\n\nReview body.\n",
        encoding="utf-8",
    )
    return artifact


# ---------------------------------------------------------------------------
# Scenario runner: ONE driver, replayed for assertions (module fixture) and,
# under a fresh coverage tracer, for the T007 branch-coverage ratchet.
# ---------------------------------------------------------------------------


@dataclass
class Scenario:
    """Captured observable outcome of one driven CLI invocation."""

    exit_code: int
    output: str
    payload: dict[str, Any] | None = None
    evidence: dict[str, Any] = field(default_factory=dict)


def _invoke(argv: list[str]) -> tuple[int, str, dict[str, Any] | None]:
    result = runner.invoke(app, argv)
    payload: dict[str, Any] | None = None
    stdout = result.stdout or ""
    if "--json" in argv and stdout.strip().startswith("{"):
        try:
            payload = json.loads(stdout)
        except json.JSONDecodeError:
            payload = None
    return result.exit_code, stdout, payload


def _git_head(repo: Path) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD"], capture_output=True, text=True, check=True
    ).stdout.strip()


def _run_all_scenarios(mkdir: Any) -> dict[str, Scenario]:
    """Drive every mutating-command characterization scenario once.

    *mkdir* is a zero-arg callable returning a fresh empty directory (each
    scenario needs an isolated repo/tmp root). Returns a dict keyed by scenario
    name -> :class:`Scenario`. Used by the ``scenarios`` module fixture (for the
    assertion tests) and re-run under a coverage tracer by the T007 ratchet.
    """
    out: dict[str, Scenario] = {}

    # --- T004: coord skip-exit-0 arm (distinguishing evidence) ---
    ctx = _build_coord_protected_tree(mkdir())
    head_before = _git_head(ctx.repo)
    coord_events_before = ctx.status_events_path.read_text(encoding="utf-8").count("\n")
    with setup_mocked_env(ctx.repo, mission_slug=ctx.slug, workspace_resolution=None, auto_commit_default=True):
        code, text, payload = _invoke(["move-task", "WP01", "--to", "for_review", "--mission", ctx.slug, "--force", "--json"])
    out["skip_arm"] = Scenario(
        code, text, payload,
        {
            "head_before": head_before,
            "head_after": _git_head(ctx.repo),
            "coord_events_before": coord_events_before,
            "coord_events_after": ctx.status_events_path.read_text(encoding="utf-8").count("\n"),
            "coord_events_path_str": str(ctx.status_events_path),
            "coord_worktree_segment": ".worktrees",
        },
    )

    # --- T005: refuse-exit-1 arms on the SAME coord+protected tree ---
    ctx_ms = _build_coord_protected_tree(mkdir())
    (ctx_ms.primary_feature_dir / "tasks.md").write_text(
        "# Work Packages\n\n## WP01 - fixture\n- [ ] T001 do a thing\n", encoding="utf-8"
    )
    with setup_mocked_env(ctx_ms.repo, mission_slug=ctx_ms.slug, workspace_resolution=None, auto_commit_default=True):
        code, text, _ = _invoke(["mark-status", "T001", "--status", "done", "--mission", ctx_ms.slug, "--json"])
    out["refuse_mark_status"] = Scenario(code, text)

    ctx_mr = _build_coord_protected_tree(mkdir())
    with setup_mocked_env(ctx_mr.repo, mission_slug=ctx_mr.slug, workspace_resolution=None, auto_commit_default=True):
        code, text, _ = _invoke(["map-requirements", "--wp", "WP01", "--refs", "FR-001", "--mission", ctx_mr.slug, "--json"])
    out["refuse_map_requirements"] = Scenario(code, text)

    fd = _simple_mission(mkdir(), f"protectedself-{_MID8}")
    with setup_mocked_env(fd.parent.parent, mission_slug=fd.name, auto_commit_default=True):
        code, text, payload = _invoke([
            "move-task", "WP01", "--to", "for_review", "--mission", fd.name,
            "--self-review-fallback", "--intended-reviewer", "reviewer-renata",
            "--reviewer-failure-reason", "unavailable", "--json",
        ])
    out["protected_self_review_precedence"] = Scenario(code, text, payload)

    # --- T006: every other named move_task decision branch ---

    # arbiter-override: --force forward from planned after a for_review->planned rejection.
    fd = _simple_mission(mkdir(), f"arbiter-{_MID8}")
    _seed_chain(fd, [("planned", "claimed"), ("claimed", "in_progress"), ("in_progress", "for_review")])
    _seed_event(fd, "for_review", "planned", 4, review_ref="feedback://arbiter/WP01/review-cycle-1.md")
    with setup_mocked_env(fd.parent.parent, mission_slug=fd.name, extra_patches=_REVIEW_GATE_BYPASS):
        code, text, _ = _invoke([
            "move-task", "WP01", "--to", "for_review", "--mission", fd.name, "--force",
            "--note", "correctness: override the stale rejection", "--no-auto-commit",
        ])
    out["arbiter_override"] = Scenario(
        code, text, evidence={"arbiter_artifacts": [str(p.relative_to(fd)) for p in fd.rglob("arbiter-override-*.json")]}
    )

    # rejected-verdict guard: force-approve blocked by a rejected review artifact.
    fd = _simple_mission(mkdir(), f"rejected-{_MID8}")
    _seed_chain(fd, [("planned", "claimed"), ("claimed", "in_progress"), ("in_progress", "for_review")])
    _write_review_cycle(fd, 1, "rejected")
    with setup_mocked_env(fd.parent.parent, mission_slug=fd.name, extra_patches=_REVIEW_GATE_BYPASS):
        code, text, _ = _invoke(["move-task", "WP01", "--to", "approved", "--mission", fd.name, "--force", "--no-auto-commit"])
    out["rejected_verdict_block"] = Scenario(code, text)

    # rejected-verdict OVERRIDE: --skip-review-artifact-check --note re-opens the path.
    fd = _simple_mission(mkdir(), f"override-{_MID8}")
    _seed_chain(fd, [("planned", "claimed"), ("claimed", "in_progress"), ("in_progress", "for_review")])
    artifact = _write_review_cycle(fd, 1, "rejected")
    with setup_mocked_env(fd.parent.parent, mission_slug=fd.name, extra_patches=_REVIEW_GATE_BYPASS):
        code, text, _ = _invoke([
            "move-task", "WP01", "--to", "approved", "--mission", fd.name, "--force",
            "--skip-review-artifact-check", "--note", "arbiter release: rejection superseded",
            "--no-auto-commit",
        ])
    out["rejected_verdict_override"] = Scenario(
        code, text, evidence={"artifact_text": artifact.read_text(encoding="utf-8")}
    )

    # planning-artifact-WP done (FR-008a): ancestry check SKIPPED for a non-code_change WP.
    fd = _simple_mission(mkdir(), f"planart-{_MID8}", execution_mode="planning_artifact")
    _seed_chain(fd, [("planned", "claimed"), ("claimed", "in_progress"), ("in_progress", "for_review"), ("for_review", "approved")])
    ws_plan = SimpleNamespace(execution_mode="planning_artifact", worktree_path=str(fd.parent.parent), branch_name="none", resolution_kind="lane_workspace")
    with setup_mocked_env(fd.parent.parent, mission_slug=fd.name, workspace_resolution=ws_plan, extra_patches=_REVIEW_GATE_BYPASS):
        code, text, _ = _invoke(["move-task", "WP01", "--to", "done", "--mission", fd.name, "--force", "--no-auto-commit"])
    out["planning_artifact_done"] = Scenario(code, text)

    # code-change contrast: the SAME move with a code_change WP DEMANDS ancestry/override.
    fd = _simple_mission(mkdir(), f"codechange-{_MID8}", execution_mode="code_change")
    _seed_chain(fd, [("planned", "claimed"), ("claimed", "in_progress"), ("in_progress", "for_review"), ("for_review", "approved")])
    ws_code = SimpleNamespace(execution_mode="code_change", worktree_path=str(fd.parent.parent), branch_name="kitty/none", resolution_kind="lane_workspace")
    with setup_mocked_env(fd.parent.parent, mission_slug=fd.name, workspace_resolution=ws_code, extra_patches=_REVIEW_GATE_BYPASS):
        code, text, _ = _invoke(["move-task", "WP01", "--to", "done", "--mission", fd.name, "--force", "--no-auto-commit"])
    out["code_change_done_blocked"] = Scenario(code, text)
    # ... and proceeds once an override reason is supplied.
    with setup_mocked_env(fd.parent.parent, mission_slug=fd.name, workspace_resolution=ws_code, extra_patches=_REVIEW_GATE_BYPASS):
        code, text, _ = _invoke([
            "move-task", "WP01", "--to", "done", "--mission", fd.name, "--force",
            "--done-override-reason", "branch deleted after hotfix merge", "--no-auto-commit",
        ])
    out["code_change_done_override"] = Scenario(code, text)

    # review-currency refusal: _validate_ready_for_review returns not-ready.
    fd = _simple_mission(mkdir(), f"currency-{_MID8}")
    _seed_chain(fd, [("planned", "claimed"), ("claimed", "in_progress")])
    _not_ready = {
        "_validate_ready_for_review": (False, ["Review branch is stale relative to base"]),
        "_check_unchecked_subtasks": [],
    }
    with setup_mocked_env(fd.parent.parent, mission_slug=fd.name, extra_patches=_not_ready):
        code, text, _ = _invoke(["move-task", "WP01", "--to", "for_review", "--mission", fd.name, "--no-auto-commit"])
    out["review_currency_refuse"] = Scenario(code, text)

    # for_review -> in_progress force (backward rewind sets review_ref=force-override).
    fd = _simple_mission(mkdir(), f"rewind-{_MID8}")
    _seed_chain(fd, [("planned", "claimed"), ("claimed", "in_progress"), ("in_progress", "for_review")])
    with setup_mocked_env(fd.parent.parent, mission_slug=fd.name, extra_patches=_REVIEW_GATE_BYPASS):
        code, text, payload = _invoke(["move-task", "WP01", "--to", "doing", "--mission", fd.name, "--force", "--no-auto-commit", "--json"])
    out["for_review_to_in_progress_force"] = Scenario(code, text, payload)

    # --- T007: no-stdout side effects ---

    # WP-file activity-log write on a plain forward move.
    fd = _simple_mission(mkdir(), f"wpwrite-{_MID8}")
    _seed_chain(fd, [("planned", "claimed"), ("claimed", "in_progress")])
    wp_file = fd / "tasks" / "WP01-fixture.md"
    with setup_mocked_env(fd.parent.parent, mission_slug=fd.name, extra_patches=_REVIEW_GATE_BYPASS):
        code, text, _ = _invoke(["move-task", "WP01", "--to", "for_review", "--mission", fd.name, "--no-auto-commit"])
    out["wp_file_write"] = Scenario(code, text, evidence={"wp_body": wp_file.read_text(encoding="utf-8")})

    # tracker-ref frontmatter persistence.
    fd = _simple_mission(mkdir(), f"tracker-{_MID8}")
    _seed_chain(fd, [("planned", "claimed"), ("claimed", "in_progress")])
    wp_file = fd / "tasks" / "WP01-fixture.md"
    with setup_mocked_env(fd.parent.parent, mission_slug=fd.name, extra_patches=_REVIEW_GATE_BYPASS):
        code, text, _ = _invoke([
            "move-task", "WP01", "--to", "for_review", "--mission", fd.name,
            "--tracker-ref", "#1298", "--tracker-ref", "JIRA-7", "--no-auto-commit", "--json",
        ])
    out["tracker_ref"] = Scenario(code, text, evidence={"wp_body": wp_file.read_text(encoding="utf-8")})

    # --- extra move_task arms (coverage breadth for the T007 ratchet) ---
    # self-review fallback approval.
    fd = _simple_mission(mkdir(), f"selfreview-{_MID8}")
    _seed_chain(fd, [("planned", "claimed"), ("claimed", "in_progress"), ("in_progress", "for_review")])
    with setup_mocked_env(fd.parent.parent, mission_slug=fd.name, extra_patches=_REVIEW_GATE_BYPASS):
        _invoke([
            "move-task", "WP01", "--to", "approved", "--mission", fd.name, "--force",
            "--self-review-fallback", "--intended-reviewer", "reviewer-renata",
            "--reviewer-failure-reason", "reviewer offline", "--reviewer", "operator",
            "--approval-ref", "PR#42", "--no-auto-commit",
        ])
    # self-review-fallback option error (enabled without intended reviewer, not force).
    fd = _simple_mission(mkdir(), f"selfreviewerr-{_MID8}")
    _seed_chain(fd, [("planned", "claimed"), ("claimed", "in_progress"), ("in_progress", "for_review")])
    with setup_mocked_env(fd.parent.parent, mission_slug=fd.name, extra_patches=_REVIEW_GATE_BYPASS):
        _invoke(["move-task", "WP01", "--to", "approved", "--mission", fd.name, "--self-review-fallback", "--no-auto-commit"])
    # malformed review artifact (no parseable verdict) blocks approval.
    fd = _simple_mission(mkdir(), f"malformed-{_MID8}")
    _seed_chain(fd, [("planned", "claimed"), ("claimed", "in_progress"), ("in_progress", "for_review")])
    mal_dir = fd / "tasks" / "WP01-fixture"
    mal_dir.mkdir(parents=True, exist_ok=True)
    (mal_dir / "review-cycle-1.md").write_text("no frontmatter here\n", encoding="utf-8")
    with setup_mocked_env(fd.parent.parent, mission_slug=fd.name, extra_patches=_REVIEW_GATE_BYPASS):
        _invoke(["move-task", "WP01", "--to", "approved", "--mission", fd.name, "--force", "--no-auto-commit"])
    # backward auto-promote (approved -> doing without --force).
    fd = _simple_mission(mkdir(), f"backward-{_MID8}")
    _seed_chain(fd, [("planned", "claimed"), ("claimed", "in_progress"), ("in_progress", "for_review"), ("for_review", "approved")])
    with setup_mocked_env(fd.parent.parent, mission_slug=fd.name, extra_patches=_REVIEW_GATE_BYPASS):
        _invoke(["move-task", "WP01", "--to", "doing", "--mission", fd.name, "--no-auto-commit", "--json"])
    # planned rollback: missing feedback file, empty feedback file, then a valid rollback.
    fd = _simple_mission(mkdir(), f"rollback-{_MID8}")
    _seed_chain(fd, [("planned", "claimed"), ("claimed", "in_progress"), ("in_progress", "for_review"), ("for_review", "in_review")])
    root = fd.parent.parent
    with setup_mocked_env(root, mission_slug=fd.name, extra_patches=_REVIEW_GATE_BYPASS):
        _invoke(["move-task", "WP01", "--to", "planned", "--mission", fd.name, "--review-feedback-file", str(root / "missing.md"), "--no-auto-commit"])
    empty_fb = root / "empty.md"
    empty_fb.write_text("   \n", encoding="utf-8")
    with setup_mocked_env(root, mission_slug=fd.name, extra_patches=_REVIEW_GATE_BYPASS):
        _invoke(["move-task", "WP01", "--to", "planned", "--mission", fd.name, "--review-feedback-file", str(empty_fb), "--no-auto-commit"])
    good_fb = root / "feedback.md"
    good_fb.write_text("**Issue**: needs rework.\n", encoding="utf-8")
    with setup_mocked_env(root, mission_slug=fd.name, extra_patches=_REVIEW_GATE_BYPASS):
        _invoke(["move-task", "WP01", "--to", "planned", "--mission", fd.name, "--review-feedback-file", str(good_fb), "--no-auto-commit"])
    # agent-mismatch warning + invalid lane usage error.
    fd = _simple_mission(mkdir(), f"misc-{_MID8}")
    _seed_chain(fd, [("planned", "claimed"), ("claimed", "in_progress")])
    with setup_mocked_env(fd.parent.parent, mission_slug=fd.name, extra_patches=_REVIEW_GATE_BYPASS):
        _invoke(["move-task", "WP01", "--to", "for_review", "--mission", fd.name, "--agent", "other-agent", "--no-auto-commit"])
    _invoke(["move-task", "WP01", "--to", "bogus-lane", "--mission", fd.name])

    # --- mark_status + map_requirements success/error breadth ---
    fd = _simple_mission(mkdir(), f"markstatus-{_MID8}")
    _seed_event(fd, "planned", "claimed", 1)
    with setup_mocked_env(fd.parent.parent, mission_slug=fd.name, extra_patches=_REVIEW_GATE_BYPASS):
        _invoke(["mark-status", "T001", "--status", "done", "--mission", fd.name, "--no-auto-commit", "--json"])
        _invoke(["mark-status", "T001", "--status", "pending", "--mission", fd.name, "--no-auto-commit"])
        _invoke(["mark-status", "--status", "done", "--mission", fd.name])
        _invoke(["mark-status", "T001", "--status", "not-a-status", "--mission", fd.name])

    fd = _simple_mission(mkdir(), f"maprequirements-{_MID8}")
    _seed_event(fd, "planned", "claimed", 1)
    with setup_mocked_env(fd.parent.parent, mission_slug=fd.name, extra_patches=_REVIEW_GATE_BYPASS):
        _invoke(["map-requirements", "--wp", "WP01", "--refs", "FR-001", "--mission", fd.name, "--no-auto-commit", "--json"])
        _invoke([
            "map-requirements", "--wp", "WP01", "--refs", "FR-001,FR-002", "--replace",
            "--tracker-ref", "#77", "--mission", fd.name, "--no-auto-commit", "--json",
        ])
        _invoke(["map-requirements", "--batch", '{"WP01": ["FR-002"]}', "--mission", fd.name, "--no-auto-commit", "--json"])
        _invoke(["map-requirements", "--wp", "WP01", "--refs", "FR-001", "--batch", "{}", "--mission", fd.name])
        _invoke(["map-requirements", "--batch", "not valid json", "--mission", fd.name])
        _invoke(["map-requirements", "--batch", "[1, 2]", "--mission", fd.name])
        _invoke(["map-requirements", "--wp", "WP01", "--mission", fd.name])

    # --- status success/error breadth ---
    fd = _simple_mission(mkdir(), f"status-{_MID8}")
    _seed_chain(fd, [("planned", "claimed"), ("claimed", "in_progress")])
    with setup_mocked_env(fd.parent.parent, mission_slug=fd.name, workspace_resolution=FileNotFoundError):
        _invoke(["status", "--mission", fd.name, "--json"])
        _invoke(["status", "--mission", fd.name])
        _invoke(["status", "--mission", fd.name, "--stale-threshold", "5", "--json"])
    _invoke(["status", "--mission", "definitely-nonexistent-mission", "--json"])

    return out


@pytest.fixture(scope="module")
def scenarios(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Scenario]:
    """Drive every mutating-command scenario ONCE for the whole module."""
    counter = {"n": 0}

    def mkdir() -> Path:
        counter["n"] += 1
        return tmp_path_factory.mktemp(f"tasks_cli_wp01_{counter['n']}")

    return _run_all_scenarios(mkdir)


# ---------------------------------------------------------------------------
# T004 -- coord skip-exit-0 arm (DISTINGUISHING evidence)
# ---------------------------------------------------------------------------


def test_move_task_coord_skip_arm_distinguishing_evidence(scenarios: dict[str, Scenario]) -> None:
    """T004: the skip-exit-0 arm is frozen by evidence that a NON-skip lacks.

    Exit-0 + ``--json`` key presence alone does NOT distinguish the skip arm (a
    normal success also exits 0). The DISTINGUISHING evidence, per FR-001, is:

    * primary-branch HEAD is UNCHANGED (the WP-file commit to the protected
      primary was skipped — a non-skip success WOULD have committed and moved
      HEAD), AND
    * a coord event was emitted (the transition is authoritative on the coord
      branch), AND
    * the conditional ``--json`` keys (``wp_file_update`` / ``status_events_path``)
      appear, with ``status_events_path`` pointing under the coord worktree.
    """
    sc = scenarios["skip_arm"]
    assert sc.exit_code == 0, sc.output
    assert sc.payload is not None

    # Distinguishing evidence 1: primary HEAD unchanged (no primary commit).
    assert sc.evidence["head_before"] == sc.evidence["head_after"], (
        "skip arm must NOT commit the WP file to the protected primary — HEAD moved"
    )
    # Distinguishing evidence 2: a coord event was emitted.
    assert sc.evidence["coord_events_after"] == sc.evidence["coord_events_before"] + 1, (
        "skip arm must still emit the transition to the coordination branch"
    )
    # Distinguishing evidence 3: the conditional skip-arm --json keys.
    assert sc.payload["wp_file_update"] == "skipped"
    assert "wp_file_update_reason" in sc.payload
    assert sc.evidence["coord_worktree_segment"] in sc.payload["status_events_path"], (
        "status_events_path must resolve under the coord worktree in the skip arm"
    )
    assert sc.payload["new_lane"] == "for_review"
    assert sc.payload["old_lane"] == "in_progress"


# ---------------------------------------------------------------------------
# T005 -- refuse-exit-1 arms (skip-vs-refuse divergence deliberately preserved)
# ---------------------------------------------------------------------------
#
# NFR-001 / deferred #2300: on the SAME coord + protected-primary tree where
# move_task SKIPS (exit 0), mark_status and map_requirements REFUSE (exit 1)
# because ``_protected_branch_status_commit_error`` fires unconditionally under
# ``auto_commit`` — it does NOT consult ``_skip_target_branch_commit``. This
# inconsistency is a real divergence but a behaviour change to reconcile; this
# mission PRESERVES it. Do NOT "fix" the divergence in a later WP under the guise
# of a refactor — that is a behaviour change, out of scope here.


def test_mark_status_refuses_exit_1_on_coord_protected_tree(scenarios: dict[str, Scenario]) -> None:
    """T005: mark_status refuses (exit 1) where move_task skips (exit 0)."""
    sc = scenarios["refuse_mark_status"]
    assert sc.exit_code == 1, sc.output
    assert "protected branch" in sc.output and "auto-commit" in sc.output


def test_map_requirements_refuses_exit_1_on_coord_protected_tree(scenarios: dict[str, Scenario]) -> None:
    """T005: map_requirements refuses (exit 1) where move_task skips (exit 0)."""
    sc = scenarios["refuse_map_requirements"]
    assert sc.exit_code == 1, sc.output
    assert "protected branch" in sc.output and "auto-commit" in sc.output


# ---------------------------------------------------------------------------
# T006 -- every OTHER named move_task decision branch, frozen as driven cases
# ---------------------------------------------------------------------------


class TestMoveTaskDecisionBranchesFrozen:
    """Freeze each named move_task guard branch WP03 extracts (FR-004)."""

    def test_arbiter_override_persists_decision(self, scenarios: dict[str, Scenario]) -> None:
        """--force forward from planned after a rejection records an arbiter override."""
        sc = scenarios["arbiter_override"]
        assert sc.exit_code == 0, sc.output
        assert "Arbiter override recorded" in sc.output
        assert sc.evidence["arbiter_artifacts"] == ["tasks/WP01/arbiter-override-1.json"], (
            "arbiter override must persist a standalone decision artifact"
        )

    def test_rejected_verdict_blocks_approval(self, scenarios: dict[str, Scenario]) -> None:
        """A rejected latest review artifact fails-closed on approve (no override flag)."""
        sc = scenarios["rejected_verdict_block"]
        assert sc.exit_code == 1, sc.output
        assert "rejected" in sc.output
        assert "--skip-review-artifact-check" in sc.output

    def test_rejected_verdict_override_reopens_path(self, scenarios: dict[str, Scenario]) -> None:
        """--skip-review-artifact-check + --note durably overrides the rejection."""
        sc = scenarios["rejected_verdict_override"]
        assert sc.exit_code == 0, sc.output
        assert "review_artifact_override_reason" in sc.evidence["artifact_text"], (
            "override evidence must be stamped durably into the review artifact"
        )

    def test_planning_artifact_done_skips_ancestry(self, scenarios: dict[str, Scenario]) -> None:
        """FR-008a: a planning-artifact WP reaches done WITHOUT merge ancestry."""
        sc = scenarios["planning_artifact_done"]
        assert sc.exit_code == 0, sc.output
        assert "done" in sc.output.lower()

    def test_code_change_done_requires_ancestry_contrast(self, scenarios: dict[str, Scenario]) -> None:
        """Contrast: a code_change WP demands ancestry (blocks) then an override (proceeds).

        This is the load-bearing contrast — it proves the planning-artifact arm's
        exit-0 is the FR-008a SKIP, not merely that ``done`` always succeeds.
        """
        blocked = scenarios["code_change_done_blocked"]
        assert blocked.exit_code == 1, blocked.output
        assert "ancestry" in blocked.output.lower()
        proceeded = scenarios["code_change_done_override"]
        assert proceeded.exit_code == 0, proceeded.output

    def test_review_currency_refusal(self, scenarios: dict[str, Scenario]) -> None:
        """A not-ready review-currency verdict refuses the for_review move (exit 1)."""
        sc = scenarios["review_currency_refuse"]
        assert sc.exit_code == 1, sc.output
        assert "stale" in sc.output

    def test_self_review_guard_precedes_protected_branch(self, scenarios: dict[str, Scenario]) -> None:
        """Protected auto-commit keeps the pure guard order's first refusal."""
        sc = scenarios["protected_self_review_precedence"]
        assert sc.exit_code == 1, sc.output
        assert sc.payload is not None
        assert sc.payload["error"] == "--self-review-fallback is only valid when approving or marking done."

    def test_for_review_to_in_progress_force(self, scenarios: dict[str, Scenario]) -> None:
        """for_review -> in_progress with --force rewinds (exit 0, lane flips back)."""
        sc = scenarios["for_review_to_in_progress_force"]
        assert sc.exit_code == 0, sc.output
        assert sc.payload is not None
        assert sc.payload["old_lane"] == "for_review"
        assert sc.payload["new_lane"] == "in_progress"


# ---------------------------------------------------------------------------
# T007 -- no-stdout side effects + from-harness branch-coverage ratchet
# ---------------------------------------------------------------------------


class TestMoveTaskSideEffects:
    """Freeze the side effects that leave no stdout signature."""

    def test_coord_vs_primary_event_emission(self, scenarios: dict[str, Scenario]) -> None:
        """Skip arm emits to the COORD event log while the PRIMARY HEAD is untouched."""
        sc = scenarios["skip_arm"]
        assert sc.evidence["coord_events_after"] == sc.evidence["coord_events_before"] + 1
        assert sc.evidence["head_before"] == sc.evidence["head_after"]

    def test_wp_file_activity_log_written(self, scenarios: dict[str, Scenario]) -> None:
        """A forward move appends a real activity-log line to the WP file body."""
        sc = scenarios["wp_file_write"]
        assert sc.exit_code == 0, sc.output
        body = sc.evidence["wp_body"]
        activity_lines = [line for line in body.splitlines() if line.startswith("- ")]
        assert activity_lines, "move_task must append an activity-log entry to the WP file"

    def test_tracker_ref_frontmatter_persisted(self, scenarios: dict[str, Scenario]) -> None:
        """--tracker-ref values land in the WP frontmatter tracker_refs."""
        sc = scenarios["tracker_ref"]
        assert sc.exit_code == 0, sc.output
        body = sc.evidence["wp_body"]
        assert "#1298" in body and "JIRA-7" in body, "tracker refs must persist to WP frontmatter"


# Per-function branch-coverage floors, MEASURED from this harness's drives on the
# current base (see the mission's WP01 handoff): move_task 67.8% (118/174),
# map_requirements 51.9% (54/104), status 49.0% (50/102). The thresholds sit a
# few points BELOW the measured values to absorb non-deterministic side arms
# (sync-daemon timing, dict ordering) while still ratcheting: WP03+ must NOT drop
# a mutating command below its floor without the drop being visible here. The
# uncovered arms are predominantly defensive IO / exception handlers and the
# real-git auto-commit SUCCESS path (not reachable in-process without a full lane
# repo); every NAMED decision branch WP03 extracts is ADDITIONALLY pinned by an
# explicit T006 case above, which is the primary anti-unguarded-extraction guard.
_BRANCH_COVERAGE_FLOORS = {
    "move_task": 65.0,
    "map_requirements": 48.0,
    "status": 46.0,
}

# WP05 (tasks-py-degod-wave2-01KWH9EQ / FR-012): the coverage plumbing resolves
# each floored command from the module(s) its body ACTUALLY lives in. The
# single-file form (``tasks_module.__file__`` + ``include=[tasks.py]``, keyed on
# the command ``FunctionDef`` name) went vacuous the moment wave-1 thinned the
# wrappers: a thin wrapper has zero branch arcs and the old
# ``… if total else 100.0`` fallback reported 100.0 — every floor "passed" while
# measuring NOTHING.
#
# Each command maps to its ENTRY home plus the PURE-CORE home(s) wave-1
# extracted from the calibrated single body — the floors (WP01 handoff:
# move_task 118/174, map_requirements 54/104, status 50/102) were measured over
# those single bodies, so the calibration-faithful basis is the entry's
# same-module helper closure PLUS the extracted decision core (the
# map_requirements re-point reproduces the calibrated arc universe almost
# exactly: 106 measured possible arcs vs 104 calibrated). This map is the one
# place a family-relocation WP re-points; WP06/WP07 re-point the ENTRY home
# here when ``status``/``map_requirements`` move (the core homes stay). The
# floor VALUES above are frozen — re-pointing is expressly NOT floor-adjustment
# (parity-contract Layer 3).
_FLOORED_FUNCTION_HOMES: dict[str, tuple[tuple[ModuleType, str], ...]] = {
    "move_task": (
        (tasks_move_task_module, "_do_move_task"),
        (tasks_transition_core_module, "decide_transition"),
        (tasks_transition_core_module, "build_transition_plan"),
    ),
    # WP06 (tasks-py-degod-wave2-01KWH9EQ): ENTRY home re-pointed to
    # ``tasks_map_requirements`` (family relocation); the wave-1 pure-core home
    # (``plan_mapping``) stays — multi-home semantics per the WP05 map above.
    "map_requirements": (
        (tasks_map_requirements_module, "_do_map_requirements"),
        (tasks_mapping_core_module, "plan_mapping"),
    ),
    # WP07 (tasks-py-degod-wave2-01KWH9EQ): ENTRY home re-pointed to
    # ``tasks_status_cmd`` (family relocation); the wave-1 pure-core homes
    # (``build_status_view`` / ``build_stale_fallback_results``) stay —
    # multi-home semantics per the WP05 map above.
    "status": (
        (tasks_status_cmd_module, "_do_status"),
        (tasks_status_view_module, "build_status_view"),
        (tasks_status_view_module, "build_stale_fallback_results"),
    ),
}


def _module_source_path(module: ModuleType) -> str:
    """Resolved source path of *module* (asserting it is file-backed)."""
    module_file = module.__file__
    assert module_file is not None
    return str(Path(module_file).resolve())


def _same_module_closure(
    funcs: dict[str, ast.FunctionDef], entry: str
) -> list[ast.FunctionDef]:
    """Module-level ``FunctionDef``s reachable from *entry* by bare-``Name`` reference.

    The floors were calibrated on the SINGLE-BODY commands (wave-1 WP01); the
    wave-1 phase split moved the measured branches into same-module ``_mt_*`` /
    ``_mr_*`` / ``_st_*`` helpers the entry calls by bare name, so the honest
    measurement is the entry PLUS that closure — never the entry alone (a linear
    phase-call orchestrator has ~zero branch arcs of its own). Cross-module seam
    calls go through the ``_tasks.<attr>`` bridge (attribute access, not a bare
    ``Name``), so the closure stays within the entry's module by construction.
    """
    seen: set[str] = set()
    stack = [entry]
    while stack:
        fn_name = stack.pop()
        if fn_name in seen or fn_name not in funcs:
            continue
        seen.add(fn_name)
        stack.extend(
            n.id
            for n in ast.walk(funcs[fn_name])
            if isinstance(n, ast.Name) and n.id in funcs and n.id not in seen
        )
    return [funcs[fn_name] for fn_name in seen]


def _mutating_function_line_ranges() -> dict[str, list[tuple[str, tuple[int, int]]]]:
    """Return ``{floored_name: [(source_path, (start_line, end_line)), …]}``.

    Each command's AST is resolved from the module file(s) its
    ``_FLOORED_FUNCTION_HOMES`` entries name, so a relocated body keeps being
    measured where it actually lives; the measured span per home is the entry
    function plus its same-module helper closure (see ``_same_module_closure``).
    A missing entry qualname is a hard failure — a silent drop would un-gate
    that command's branches.
    """
    ranges: dict[str, list[tuple[str, tuple[int, int]]]] = {}
    for name, homes in _FLOORED_FUNCTION_HOMES.items():
        spans: list[tuple[str, tuple[int, int]]] = []
        for module, qualname in homes:
            source_path = _module_source_path(module)
            tree = ast.parse(Path(source_path).read_text(encoding="utf-8"))
            funcs = {
                node.name: node
                for node in tree.body
                if isinstance(node, ast.FunctionDef)
            }
            if qualname not in funcs:
                pytest.fail(
                    f"{name}: floored function {qualname!r} not found in "
                    f"{source_path} — the ratchet re-point is broken"
                )
            for node in _same_module_closure(funcs, qualname):
                assert node.end_lineno is not None
                spans.append((source_path, (node.lineno, node.end_lineno)))
        ranges[name] = sorted(spans)
    return ranges


def _analyze_branch_arcs(
    cov: Any, source_path: str
) -> tuple[list[tuple[int, int]], set[tuple[int, int]], set[int]]:
    """Arc-analyze ONE source file: (possible, executed, branch_sources).

    A *branch arc* is a possible ``(source_line, target)`` transition whose source
    line has more than one possible target (a real fork). Uses coverage's stable
    arc-analysis surface via ``Any`` so the private ``_analyze`` accessor stays
    out of the type checker's way.
    """
    analysis = cov._analyze(source_path)
    possible = list(analysis.arc_possibilities)
    executed = set(analysis.arcs_executed)
    targets_by_source: dict[int, set[int]] = {}
    for src, dst in possible:
        targets_by_source.setdefault(src, set()).add(dst)
    branch_sources = {src for src, dsts in targets_by_source.items() if src > 0 and len(dsts) > 1}
    return possible, executed, branch_sources


def _branch_coverage_by_function(
    cov: Any, ranges: dict[str, list[tuple[str, tuple[int, int]]]]
) -> dict[str, float]:
    """Compute per-command branch-coverage % from a stopped coverage session.

    Multi-file (WP05 / FR-012): each floored command is analyzed against the
    module file(s) its body lives in (``cov._analyze`` per file, results merged
    per command over the entry-plus-closure spans). Coverage % is the fraction
    of the command's branch arcs that were executed.

    ZERO measured arcs on a floored command is a HARD FAILURE, never 100.0: a
    mutating command body has decision branches by construction, so an empty
    measurement means the plumbing points at the wrong file/function (the exact
    vacuous-green trap the old single-file ``… if total else 100.0`` arm hid).
    """
    analyses: dict[str, tuple[list[tuple[int, int]], set[tuple[int, int]], set[int]]] = {}
    result: dict[str, float] = {}
    for name, spans in ranges.items():
        total = covered = 0
        for source_path, (lo, hi) in spans:
            if source_path not in analyses:
                analyses[source_path] = _analyze_branch_arcs(cov, source_path)
            possible, executed, branch_sources = analyses[source_path]
            for src, dst in possible:
                if src in branch_sources and lo <= src <= hi:
                    total += 1
                    if (src, dst) in executed:
                        covered += 1
        if not total:
            pytest.fail(
                f"{name}: 0 branch arcs measured — the ratchet re-point is "
                f"vacuous (nothing of the mapped spans {spans} was analyzed)"
            )
        result[name] = covered / total * 100.0
    return result


def test_from_harness_branch_coverage_ratchet(tmp_path_factory: pytest.TempPathFactory) -> None:
    """T007: measure per-function branch coverage FROM this harness and gate it.

    Re-runs every mutating-command scenario under a fresh ``coverage`` tracer and
    asserts the branch coverage of ``move_task`` / ``status`` / ``map_requirements``
    stays at or above the measured floor. This is the ratchet that ensures no
    decision branch is silently left unfrozen before WP03's extraction.

    When the whole suite already runs under a coverage tracer (CI's ``--cov``
    pass), a nested tracer cannot measure, so the gate skips there and runs in the
    standard ``pytest -q`` pass (the CLAUDE.md dual-run model).
    """
    if sys.gettrace() is not None:
        pytest.skip("a tracer is already active (suite under --cov); ratchet runs in the no-cov pass")

    import coverage

    ranges = _mutating_function_line_ranges()
    include_paths = sorted(
        {source_path for spans in ranges.values() for source_path, _ in spans}
    )

    cov = coverage.Coverage(branch=True, include=include_paths)
    counter = {"n": 0}

    def mkdir() -> Path:
        counter["n"] += 1
        return tmp_path_factory.mktemp(f"tasks_cli_wp01_cov_{counter['n']}")

    cov.start()
    try:
        _run_all_scenarios(mkdir)
    finally:
        cov.stop()

    measured = _branch_coverage_by_function(cov, ranges)
    shortfalls = {
        name: (round(measured[name], 1), floor)
        for name, floor in _BRANCH_COVERAGE_FLOORS.items()
        if measured[name] + 1e-6 < floor
    }
    assert not shortfalls, (
        "from-harness branch coverage dropped below the frozen floor "
        f"(measured%, floor%): {shortfalls}. A decision branch is now unfrozen — "
        "add a driven case before extracting it."
    )
