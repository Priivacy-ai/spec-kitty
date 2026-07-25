"""WP09 (coord-write-placement-closure-01KYCF83) — T042/T045/T046/T047: the
birth-time runtime cutover (IC-08 / FR-009 / NFR-003 / C-004).

Two families of coverage, per the WP's own red-first + crux-resolution
demands (see ``tracers/design-decisions.md`` for the full IC-08 analysis):

* **T042 / T047 — the real end-to-end anchor.** A coord-topology mission
  (and its flat/single-branch degenerate twin) created via the REAL
  ``create_mission_core`` entry point, a WP claimed and one subtask completed
  through the REAL event-sourced status-emit pipeline (never a ``tasks.md``
  checkbox edit / frontmatter ``shell_pid``/``agent`` write — the WP04/WP05
  dependency this WP inherits), then merged via the REAL
  ``_run_lane_based_merge``. Asserts the birth-cutover fires at the bake
  stage with NO manual backfill invocation: ``status_phase>=1`` +
  ``verify_backfill().ok`` + a non-empty snapshot, and the resolved-partition
  split (``status_phase`` lands PRIMARY-only; never written to the COORD
  worktree's own ``meta.json``).

* **T045 / T046 — crash-atomicity / idempotency, exercised directly against
  :func:`cutover_mission` with genuine legacy (pre-event-sourcing-style)
  frontmatter runtime so the seed phase is non-trivial.** These prove the
  two-write atomicity property and migration-coexistence idempotency at the
  function level, independent of the full merge pipeline.

Before this WP landed, ``cutover_mission`` was never invoked from the merge
executor at all (grep confirms no call site existed in ``executor.py`` /
``ordering.py``) — the anchor tests below are genuinely red-first: they fail
on the pre-WP09 tree because no mission is ever reconciled at merge time.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from mission_runtime import MissionTopology

pytestmark = [pytest.mark.git_repo, pytest.mark.non_sandbox]

# Reused, PROVEN git/CLI harness primitives (T009 —
# tests/specify_cli/test_specify_topology_flag.py). Cross-test-module reuse of
# private helpers is an established pattern in this suite (e.g.
# tests/merge/test_executor_coord_reconcile.py imports from
# tests/regression/test_issue_2367_bake_strand.py).
from tests.specify_cli.test_specify_topology_flag import (
    _claim_allocation_patched,
    _git,
    _init_project,
    _read_meta,
    _real_merge_external_mocks,
)


# ---------------------------------------------------------------------------
# T042 / T047 — real create -> claim -> subtask-complete -> merge
# ---------------------------------------------------------------------------


def _write_single_lane(
    feature_dir: Path, slug: str, mission_branch: str, *, wp_id: str = "WP01"
) -> None:
    from datetime import UTC, datetime

    from specify_cli.lanes.models import ExecutionLane, LanesManifest
    from specify_cli.lanes.persistence import write_lanes_json

    write_lanes_json(
        feature_dir,
        LanesManifest(
            version=1,
            mission_slug=slug,
            mission_id=slug,
            mission_branch=mission_branch,
            target_branch="main",
            lanes=[
                ExecutionLane(
                    lane_id="lane-a",
                    wp_ids=(wp_id,),
                    write_scope=("src/a/**",),
                    predicted_surfaces=("code",),
                    depends_on_lanes=(),
                    parallel_group=0,
                )
            ],
            computed_at=datetime.now(UTC).isoformat(),
            computed_from="test-fixture",
        ),
    )


def _write_wp01_with_subtask(feature_dir: Path) -> None:
    """A WP file with a real, still-supported ``subtasks`` list — no
    ``shell_pid`` / ``agent`` frontmatter (those authoring paths are fully
    event-sourced post-WP04/WP05; a value here would be legacy-shaped, not
    born-reconciled)."""
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir(parents=True, exist_ok=True)
    (tasks_dir / "WP01-root.md").write_text(
        "---\n"
        "work_package_id: WP01\n"
        "title: WP01 birth-cutover demo\n"
        "dependencies: []\n"
        "execution_mode: code_change\n"
        # ``agent`` is the RUNTIME CLAIM MIRROR field (historically dual-written
        # alongside the event-sourced claim; retired by WP04/WP05) -- NOT a
        # static assignment field. A born-reconciled WP carries it EMPTY (the
        # real claim lives solely in the event log); see
        # tests/regression/test_claim_event_source.py's ``_write_wp_file`` for
        # the same convention.
        'agent: ""\n'
        "owned_files:\n"
        "  - src/a/**\n"
        "authoritative_surface: src/a/\n"
        "subtasks:\n"
        "  - T001\n"
        "---\n"
        "# WP01\n",
        encoding="utf-8",
    )
    (feature_dir / "tasks.md").write_text(
        "## WP01 birth-cutover demo\n\n- [ ] T001 Placeholder task\n",
        encoding="utf-8",
    )


def _seed_planned(feature_dir: Path, slug: str, wp_id: str) -> None:
    from specify_cli.status.emit import emit_status_transition
    from specify_cli.status.models import TransitionRequest

    emit_status_transition(
        TransitionRequest(
            feature_dir=feature_dir,
            mission_slug=slug,
            wp_id=wp_id,
            to_lane="planned",
            actor="seed",
            force=True,
            reason="seed",
        )
    )


def _status_dir(repo: Path, slug: str) -> Path:
    """The topology-aware status-surface directory to emit against — the
    COORD worktree's ``kitty-specs/<slug>`` under coordination topology, the
    PRIMARY checkout otherwise. ``emit_status_transition`` uses the literal
    ``feature_dir`` a caller supplies (it does not re-derive it), so every
    real-entry-point emit in this harness resolves through this helper rather
    than hard-coding the PRIMARY checkout."""
    from specify_cli.coordination.surface_resolver import resolve_status_surface

    return resolve_status_surface(repo, slug).parent


def _claim_real(
    repo: Path, slug: str, wp_id: str, *, actor: str = "python-pedro"
) -> None:
    """Drive ``planned -> claimed`` through the REAL production status-emit
    pipeline — the genuine event-sourced claim (FR-008 / IC-07): no
    frontmatter ``shell_pid`` / ``agent`` write accompanies it."""
    from specify_cli.status.emit import emit_status_transition
    from specify_cli.status.models import TransitionRequest

    emit_status_transition(
        TransitionRequest(
            feature_dir=_status_dir(repo, slug),
            mission_slug=slug,
            wp_id=wp_id,
            to_lane="claimed",
            actor=actor,
        )
    )


def _mark_subtask_done(repo: Path, slug: str, *task_ids: str) -> None:
    """Complete subtask(s) through the REAL ``mark-status`` CLI entry point —
    an ``InnerStateChanged`` annotation only; ``tasks.md`` checkbox bytes are
    NOT persisted (FR-008 / IC-07)."""
    from typer.testing import CliRunner

    from specify_cli.cli.commands.agent import tasks as agent_tasks

    result = CliRunner().invoke(
        agent_tasks.app,
        ["mark-status", *task_ids, "--status", "done", "--mission", slug, "--no-auto-commit"],
    )
    assert result.exit_code == 0, result.output


def _drive_claimed_through_approved(repo: Path, slug: str, wp_id: str) -> None:
    """Advance an already-``claimed`` WP to ``approved`` via the REAL
    status-emit pipeline (mirrors T009's ``_seed_wp_approved`` but does NOT
    re-seed ``planned`` / re-claim — the caller already drove a genuine
    ``planned -> claimed`` transition)."""
    from specify_cli.status.emit import emit_status_transition
    from specify_cli.status.models import ReviewResult, TransitionRequest

    feature_dir = _status_dir(repo, slug)
    for to_lane in ("in_progress", "for_review", "in_review"):
        gating = to_lane == "for_review"
        emit_status_transition(
            TransitionRequest(
                feature_dir=feature_dir,
                mission_slug=slug,
                wp_id=wp_id,
                to_lane=to_lane,
                actor="seed",
                force=gating,
                reason="seed: manufacture reviewable state" if gating else None,
            )
        )
    emit_status_transition(
        TransitionRequest(
            feature_dir=feature_dir,
            mission_slug=slug,
            wp_id=wp_id,
            to_lane="approved",
            actor="seed",
            evidence={
                "review": {
                    "reviewer": "reviewer-renata",
                    "verdict": "approved",
                    "reference": f"review-{wp_id}",
                }
            },
            review_result=ReviewResult(
                reviewer="reviewer-renata", verdict="approved", reference=f"review-{wp_id}"
            ),
        )
    )


def _bootstrap_born_mission(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    topology: MissionTopology,
) -> tuple[Path, str, Path]:
    """Create + claim + complete-subtask + approve WP01 through the real
    production entry points, for the given create-time *topology*."""
    from specify_cli.core.mission_creation import create_mission_core

    repo = _init_project(tmp_path)
    monkeypatch.chdir(repo)
    monkeypatch.setenv("SPEC_KITTY_SUPPRESS_MISSION_TYPE_DEPRECATION", "1")

    # ``.worktrees/`` (a nested worktree has no submodule/gitlink registration
    # in this bare fixture, so an un-ignored ``git add -A`` would sweep its own
    # files in) and ``.kittify/sync-state.json`` (the offline-queue's local
    # fallback file, touched by every status-emit call in this sandboxed
    # fixture — no real Teamspace project_uuid is configured) are pure
    # test-harness churn, orthogonal to the birth-cutover behavior under test;
    # ignore both so neither trips the merge's dirty-tree guard.
    (repo / ".gitignore").write_text(".worktrees/\n.kittify/sync-state.json\n", encoding="utf-8")
    _git(repo, "add", ".gitignore")
    _git(repo, "commit", "-m", "chore: ignore worktrees + sync-state churn")

    result = create_mission_core(repo, "birth-cutover-demo", topology=topology)
    feature_dir = result.feature_dir
    slug = feature_dir.name

    if result.coordination_branch is not None:
        mission_branch = result.coordination_branch
    else:
        mission_branch = f"kitty/mission-{slug}"
        _git(repo, "branch", mission_branch, "main")

    _write_single_lane(feature_dir, slug, mission_branch)
    _write_wp01_with_subtask(feature_dir)
    _seed_planned(feature_dir, slug, "WP01")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-m", f"chore({slug}): finalize WP01")

    coord_worktree: Path | None = None
    if result.coordination_branch is not None:
        from specify_cli.coordination.workspace import CoordinationWorkspace
        from specify_cli.missions._create import ensure_coordination_branch

        # ``create_mission_core`` mints the coordination branch from the
        # PRE-planning-content tip (before ``kitty-specs/<slug>`` was
        # committed above), which would leave the coord worktree "coord-empty"
        # (no mission dir there at all) and make ``resolve_status_surface``
        # fall back to PRIMARY for every subsequent status write -- never
        # exercising the two-partition split at all. Re-fork it (the real,
        # documented operator escape hatch, ``force_recreate_coordination_branch``)
        # from the CURRENT "main" tip, which now includes the mission's
        # planning content, mirroring the production shape
        # test_issue_2367_bake_strand.py's fixture uses (content committed
        # BEFORE the coordination branch forks).
        ensure_coordination_branch(
            repo_root=repo,
            mission_slug=slug,
            mission_id=str(result.meta["mission_id"]),
            target_branch="main",
            force_recreate=True,
        )
        coord_worktree = CoordinationWorkspace.resolve(
            repo, slug, str(result.meta["mission_id"])[:8]
        )

    _claim_real(repo, slug, "WP01")
    _mark_subtask_done(repo, slug, "T001")
    _drive_claimed_through_approved(repo, slug, "WP01")

    if coord_worktree is not None:
        # The claim/subtask-completion/approval events above landed on the
        # COORD worktree for real (``resolve_status_surface`` now correctly
        # routes there — the coord branch carries the mission dir since the
        # re-fork above). Commit them there, as the production CLI wrapper
        # would (``mark-status --no-auto-commit`` mirrors only the skip, not
        # a permanent uncommitted state).
        _git(coord_worktree, "add", "-A")
        _git(coord_worktree, "commit", "-m", f"chore({slug}): WP01 runtime events")

    # Sweep any incidental main-repo residue. ``.worktrees/`` and
    # ``.kittify/sync-state.json`` are gitignored above, so a plain ``-A`` is
    # safe here (git already excludes both).
    import subprocess as _subprocess

    _git(repo, "add", "-A")
    diff_check = _subprocess.run(
        ["git", "-C", str(repo), "diff", "--cached", "--quiet"], capture_output=True
    )
    if diff_check.returncode != 0:
        _git(repo, "commit", "-m", f"chore({slug}): WP01 runtime bookkeeping residue")

    # Real code content on the lane branch so the merge integrates something.
    lane_branch = f"kitty/mission-{slug}-lane-a"
    _git(repo, "branch", lane_branch, mission_branch)
    _git(repo, "checkout", lane_branch)
    code_path = repo / "src" / "a" / "foo.py"
    code_path.parent.mkdir(parents=True, exist_ok=True)
    code_path.write_text("def foo():\n    return 'birth-cutover-ok'\n", encoding="utf-8")
    _git(repo, "add", "src")
    _git(repo, "commit", "-m", f"feat({slug}): WP01 adds src/a/foo.py")
    _git(repo, "checkout", "main")

    return repo, slug, feature_dir


def _run_real_merge(repo: Path, slug: str) -> None:
    from specify_cli.merge.config import MergeStrategy
    from specify_cli.cli.commands.merge import _run_lane_based_merge

    with _claim_allocation_patched(repo, repo / "kitty-specs" / slug), _real_merge_external_mocks(repo):
        _run_lane_based_merge(
            repo_root=repo,
            mission_slug=slug,
            push=False,
            delete_branch=False,
            remove_worktree=False,
            strategy=MergeStrategy.SQUASH,
            allow_sparse_checkout=True,
        )


@pytest.mark.parametrize(
    "topology",
    [MissionTopology.COORD, MissionTopology.SINGLE_BRANCH],
    ids=["coord", "flat"],
)
def test_birth_cutover_reconciles_at_merge_no_manual_backfill(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, topology: MissionTopology
) -> None:
    """T042 (RED-first anchor) / T047: create -> claim -> complete -> merge
    lands ``status_phase>=1`` + ``verify_backfill().ok`` + a non-empty
    snapshot, with NO manual backfill invocation anywhere in this test."""
    from specify_cli.migration.backfill_runtime_state import verify_backfill
    from specify_cli.status.reducer import reduce
    from specify_cli.status.store import read_events

    repo, slug, feature_dir = _bootstrap_born_mission(tmp_path, monkeypatch, topology=topology)

    _run_real_merge(repo, slug)

    # status_phase/meta.json is the PRIMARY leg (always).
    meta = _read_meta(feature_dir)
    status_phase = meta.get("status_phase")
    assert status_phase is not None and int(status_phase) >= 1, (
        "birth-cutover must stamp status_phase>=1 at merge time with NO manual "
        f"backfill; got meta.json status_phase={status_phase!r}"
    )

    # verify_backfill/the reduced snapshot are checked against the resolved
    # STATUS surface (the COORD leg under coordination topology -- where the
    # birth-cutover's seed+verify legs actually ran; collapses to
    # ``feature_dir`` under flat topology, T047's degenerate case).
    status_dir = _status_dir(repo, slug)
    verify = verify_backfill(status_dir)
    assert verify.ok, f"verify_backfill parity must hold post-cutover: {verify.mismatches}"

    snapshot = reduce(read_events(status_dir))
    assert snapshot.work_packages, "reduced snapshot must be non-empty after birth-cutover"
    assert snapshot.work_packages["WP01"]["lane"] == "done"


@pytest.mark.parametrize(
    "topology",
    [MissionTopology.COORD, MissionTopology.SINGLE_BRANCH],
    ids=["coord", "flat"],
)
def test_birth_cutover_status_phase_is_primary_only(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, topology: MissionTopology
) -> None:
    """T047 partition-surface split: ``status_phase`` lands on the resolved
    PRIMARY meta.json only. For coord topology the coordination worktree's
    OWN ``meta.json`` copy (if any) never carries the flip — the sole-writer
    contract (C-004) is PRIMARY-scoped, never COORD."""
    repo, slug, feature_dir = _bootstrap_born_mission(tmp_path, monkeypatch, topology=topology)

    _run_real_merge(repo, slug)

    primary_meta = _read_meta(feature_dir)
    assert primary_meta.get("status_phase") is not None

    if topology is MissionTopology.COORD:
        from specify_cli.coordination.workspace import CoordinationWorkspace

        coord_worktree = CoordinationWorkspace.worktree_path(
            repo, slug, str(primary_meta["mission_id"])[:8]
        )
        coord_meta_path = coord_worktree / "kitty-specs" / slug / "meta.json"
        if coord_meta_path.exists():
            coord_meta = json.loads(coord_meta_path.read_text(encoding="utf-8"))
            assert coord_meta.get("status_phase") is None, (
                "status_phase must NEVER be written to the COORD worktree's "
                "meta.json copy (sole-writer, PRIMARY-only leg — C-004): got "
                f"{coord_meta.get('status_phase')!r}"
            )


# ---------------------------------------------------------------------------
# T045 / T046 — crash-atomicity + migration-coexistence idempotency
# (direct cutover_mission calls, with genuine legacy frontmatter runtime so
# the seed phase is non-trivial)
# ---------------------------------------------------------------------------


def _write_legacy_mission(feature_dir: Path, *, wp_id: str = "WP01") -> None:
    """A mission shaped like the PRE-WP04/WP05 corpus: real ``shell_pid`` /
    ``agent`` / subtask-checkbox runtime living in frontmatter/``tasks.md`` —
    exactly what :func:`backfill_runtime_state` seeds from. Deliberately NOT
    the born-reconciled shape (T042 above) — this is the migration-coexistence
    population IC-08 must stay idempotent against."""
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "meta.json").write_text(
        json.dumps(
            {
                "mission_slug": feature_dir.name,
                # A real, distinct ULID (production-shaped) -- NOT equal to the
                # slug: backfill_runtime_state/verify_backfill collapse
                # ``mission_id == slug`` to ``None`` on the seeded StatusEvent
                # (the "no distinguishable id" convention), while a legacy
                # readback with a MISSING mission_id key defaults it back to the
                # slug -- an artificial mismatch that has nothing to do with
                # this WP's two-target/atomicity behavior, so use a genuine
                # ULID-shaped id here to sidestep it.
                "mission_id": "01JMLEGACYCUTOVERDEMO0001",
                "mid8": "LEGACY001",
                "mission_number": None,
                "mission_type": "software-dev",
                "target_branch": "main",
                "purpose_tldr": "legacy corpus fixture",
                "purpose_context": "a pre-WP04 mission with real frontmatter runtime",
                "created_at": "2026-01-01T00:00:00+00:00",
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    (tasks_dir / f"{wp_id}-work.md").write_text(
        "---\n"
        f"work_package_id: {wp_id}\n"
        f"title: {wp_id} legacy work\n"
        "agent: implementer-ivan\n"
        "shell_pid: \"4242\"\n"
        "shell_pid_created_at: \"1735689600.0\"\n"
        "---\n"
        f"# {wp_id}\n",
        encoding="utf-8",
    )
    (feature_dir / "tasks.md").write_text(
        f"## {wp_id} legacy work\n\n- [x] T001 Legacy completed task\n",
        encoding="utf-8",
    )


def test_crash_between_seed_and_flip_heals_on_resume(tmp_path: Path) -> None:
    """T045: a crash between the durable seed-event append and the
    ``status_phase`` flip must not half-birth a mission — resume (a bare
    re-invocation of ``cutover_mission``) heals to a consistent state with
    zero duplicate seeding."""
    from specify_cli.migration.backfill_runtime_state import verify_backfill
    from specify_cli.migration.runtime_state_cutover import _seed_phase, cutover_mission
    from specify_cli.status.store import read_event_stream

    feature_dir = tmp_path / "kitty-specs" / "legacy-crash-demo"
    _write_legacy_mission(feature_dir)

    # Simulate "the crash happened right after the durable seed append but
    # before verify/flip": call ONLY the seed phase directly.
    seed_result = _seed_phase(feature_dir, dry_run=False)
    assert seed_result.action == "wrote" and seed_result.seeded_count > 0, (
        "precondition: the legacy fixture must actually seed real events, or "
        "this test proves nothing about the crash window"
    )
    pre_resume_meta = json.loads((feature_dir / "meta.json").read_text(encoding="utf-8"))
    assert pre_resume_meta.get("status_phase") is None, (
        "precondition (half-born state): status_phase must be unset before the "
        f"flip; got {pre_resume_meta.get('status_phase')!r}"
    )
    events_after_seed = (feature_dir / "status.events.jsonl").read_text(encoding="utf-8")

    # "Resume": re-invoke the FULL cutover_mission — no special heal API.
    resumed = cutover_mission(feature_dir)

    assert resumed.seeded_count == 0, (
        "resume must not duplicate seeding — the deterministic seed ids were "
        f"already on disk; got seeded_count={resumed.seeded_count}"
    )
    assert resumed.verify is not None and resumed.verify.ok, resumed.verify
    assert resumed.flipped, "resume must complete the still-open flip leg"

    events_after_resume = (feature_dir / "status.events.jsonl").read_text(encoding="utf-8")
    assert events_after_resume == events_after_seed, (
        "the event log must be byte-identical across the resume (no duplicate "
        "or reordered seed rows)"
    )

    post_meta = json.loads((feature_dir / "meta.json").read_text(encoding="utf-8"))
    assert post_meta.get("status_phase") == "1"
    assert verify_backfill(feature_dir).ok

    # Idempotent re-run of the now-fully-healed mission: 0 seeds, meta.json
    # byte-stable (``_flip_phase`` short-circuits once already
    # snapshot-authority -- ``flipped`` stays True by contract, meaning "verify
    # passed and the mission has snapshot authority", not "a write occurred").
    stream_before_third = read_event_stream(feature_dir)
    meta_before_third = (feature_dir / "meta.json").read_text(encoding="utf-8")
    third = cutover_mission(feature_dir)
    assert third.seeded_count == 0
    stream_after_third = read_event_stream(feature_dir)
    assert len(stream_after_third.transitions) == len(stream_before_third.transitions)
    assert len(stream_after_third.annotations) == len(stream_before_third.annotations)
    assert (feature_dir / "meta.json").read_text(encoding="utf-8") == meta_before_third, (
        "a third run over an already-flipped mission must write zero bytes"
    )


def test_birth_then_migration_and_migration_then_birth_are_both_idempotent(
    tmp_path: Path,
) -> None:
    """T046: the birth-cutover and the one-time migration route through the
    exact same deterministic-seed spine — running either one first and then
    the other seeds 0 the second time and leaves the event log byte-identical."""
    from specify_cli.migration.runtime_state_cutover import cutover_mission

    birth_first_dir = tmp_path / "kitty-specs" / "legacy-birth-first"
    _write_legacy_mission(birth_first_dir, wp_id="WP01")
    first = cutover_mission(birth_first_dir)
    assert first.flipped and first.seeded_count > 0
    events_after_first = (birth_first_dir / "status.events.jsonl").read_text(encoding="utf-8")
    meta_after_first = (birth_first_dir / "meta.json").read_text(encoding="utf-8")

    second = cutover_mission(birth_first_dir)
    assert second.seeded_count == 0, "the second (migration-shaped) run must seed nothing new"
    events_after_second = (birth_first_dir / "status.events.jsonl").read_text(encoding="utf-8")
    assert events_after_second == events_after_first, (
        "birth-then-migration must be byte-identical on the second pass"
    )
    assert (birth_first_dir / "meta.json").read_text(encoding="utf-8") == meta_after_first, (
        "the second pass must write zero new bytes to meta.json (already flipped)"
    )

    migration_first_dir = tmp_path / "kitty-specs" / "legacy-migration-first"
    _write_legacy_mission(migration_first_dir, wp_id="WP01")
    m_first = cutover_mission(migration_first_dir)
    assert m_first.flipped and m_first.seeded_count > 0
    events_m_after_first = (migration_first_dir / "status.events.jsonl").read_text(
        encoding="utf-8"
    )
    meta_m_after_first = (migration_first_dir / "meta.json").read_text(encoding="utf-8")

    m_second = cutover_mission(migration_first_dir)
    assert m_second.seeded_count == 0
    assert (migration_first_dir / "meta.json").read_text(encoding="utf-8") == meta_m_after_first, (
        "the second pass must write zero new bytes to meta.json (already flipped)"
    )
    events_m_after_second = (migration_first_dir / "status.events.jsonl").read_text(
        encoding="utf-8"
    )
    assert events_m_after_second == events_m_after_first, (
        "migration-then-birth must be byte-identical on the second pass"
    )


# ---------------------------------------------------------------------------
# Two-target spine — direct unit coverage (T044)
# ---------------------------------------------------------------------------


def test_two_target_spine_seeds_status_dir_and_flips_feature_dir(tmp_path: Path) -> None:
    """The two-target form seeds/verifies against *status_feature_dir* and
    flips *feature_dir* — never conflating the two, and never seeding into
    the PRIMARY leg when they differ."""
    from specify_cli.migration.runtime_state_cutover import cutover_mission

    primary_dir = tmp_path / "primary" / "kitty-specs" / "split-demo"
    status_dir = tmp_path / "coord" / "kitty-specs" / "split-demo"
    status_dir.mkdir(parents=True)
    _write_legacy_mission(status_dir)
    # The PRIMARY leg carries ONLY meta.json (the write target); no tasks/ of
    # its own is needed since the read anchor for THIS split is the status dir
    # (documented residual scope in cutover_mission's docstring).
    primary_dir.mkdir(parents=True)
    (primary_dir / "meta.json").write_text(
        (status_dir / "meta.json").read_text(encoding="utf-8"), encoding="utf-8"
    )

    result = cutover_mission(primary_dir, status_feature_dir=status_dir)

    assert result.seeded_count > 0
    assert result.flipped

    primary_events = primary_dir / "status.events.jsonl"
    assert not primary_events.exists(), (
        "seed events must land on the COORD/status leg, never on the PRIMARY leg"
    )
    assert (status_dir / "status.events.jsonl").exists()

    primary_meta = json.loads((primary_dir / "meta.json").read_text(encoding="utf-8"))
    assert primary_meta.get("status_phase") == "1"
    status_meta = json.loads((status_dir / "meta.json").read_text(encoding="utf-8"))
    assert status_meta.get("status_phase") is None, (
        "the flip must never touch the status/COORD leg's meta.json"
    )


def test_two_target_spine_defaults_status_dir_to_feature_dir(tmp_path: Path) -> None:
    """Flat/single-branch degenerate case (T047): omitting status_feature_dir
    collapses both legs to *feature_dir*, matching the pre-WP09 single-target
    behavior byte-for-byte."""
    from specify_cli.migration.runtime_state_cutover import cutover_mission

    feature_dir = tmp_path / "kitty-specs" / "flat-demo"
    _write_legacy_mission(feature_dir)

    result = cutover_mission(feature_dir)

    assert result.seeded_count > 0
    assert result.flipped
    assert (feature_dir / "status.events.jsonl").exists()
    meta = json.loads((feature_dir / "meta.json").read_text(encoding="utf-8"))
    assert meta.get("status_phase") == "1"


# ---------------------------------------------------------------------------
# F1/F2/F3 (PR #2920 review) — the coord seed-events commit, driven against a
# REAL coord worktree + REAL safe_commit. Before the fold this path committed a
# COORD-partition artifact through the PRIMARY-only commit_merge_bookkeeping
# seam (-> SafeCommitHeadMismatch, unwrapped, aborting the merge) and gated on
# the per-run seeded_count (-> stranded on resume). No prior test drove it.
# ---------------------------------------------------------------------------

_SEED_EVENT_LINE = (
    '{"event_id":"01JSEEDBIRTHCUTOVER0000000","at":"2026-07-25T00:00:00+00:00",'
    '"wp_id":"WP01","from_lane":"planned","to_lane":"claimed","actor":"migration"}\n'
)


def _coord_seed_run(tmp_path: Path):
    """Build a real main repo + a real coord worktree on a coord branch, with an
    UNCOMMITTED status.events.jsonl seeded in the coord partition. Returns a
    duck-typed run carrying only the attributes ``_commit_coord_seed_events``
    reads (``main_repo``, ``mission_slug``, ``pre_target_coord_ref``,
    ``canonical_events_path``), plus the coord worktree + events path.
    """
    import types
    from typing import cast

    from specify_cli.merge.executor import _MergeRunState

    slug = "coord-seed-mission-01KYCF83TEST00000000000000"
    main_repo = tmp_path / "repo"
    main_repo.mkdir()
    _git(main_repo, "init", "-b", "main")
    _git(main_repo, "config", "user.email", "t@example.com")
    _git(main_repo, "config", "user.name", "T")
    (main_repo / "seed.txt").write_text("x\n", encoding="utf-8")
    _git(main_repo, "add", "-A")
    _git(main_repo, "commit", "-m", "init")
    coord_branch = f"kitty/mission-{slug}-coord"
    _git(main_repo, "branch", coord_branch)
    coord_worktree = main_repo / ".worktrees" / f"{slug}-coord"
    _git(main_repo, "worktree", "add", str(coord_worktree), coord_branch)

    status_feature_dir = coord_worktree / "kitty-specs" / slug
    status_feature_dir.mkdir(parents=True)
    events_path = status_feature_dir / "status.events.jsonl"
    events_path.write_text(_SEED_EVENT_LINE, encoding="utf-8")  # dirty, uncommitted

    run = cast(
        "_MergeRunState",
        types.SimpleNamespace(
            main_repo=main_repo,
            mission_slug=slug,
            pre_target_coord_ref=coord_branch,
            canonical_events_path=events_path,
        ),
    )
    return run, coord_worktree, status_feature_dir, coord_branch


def test_coord_seed_commit_targets_coord_branch_no_head_mismatch(tmp_path: Path) -> None:
    """F1: the seed events commit lands on the COORD branch via real safe_commit
    (no SafeCommitHeadMismatch), not the PRIMARY target branch."""
    from specify_cli.merge.executor import _commit_coord_seed_events

    run, coord_worktree, status_feature_dir, coord_branch = _coord_seed_run(tmp_path)

    _commit_coord_seed_events(run, status_feature_dir)

    # The seed events are now committed on the coord branch (clean tree) ...
    porcelain = _git(coord_worktree, "status", "--porcelain").stdout
    assert porcelain.strip() == "", f"seed events not committed: {porcelain!r}"
    # ... and the commit is on the coord branch with the reconcile subject.
    subject = _git(coord_worktree, "log", "-1", "--pretty=%s").stdout.strip()
    assert "birth-cutover seed events reconciled" in subject
    tracked = _git(coord_worktree, "show", "HEAD:kitty-specs/" + run.mission_slug + "/status.events.jsonl").stdout
    assert "01JSEEDBIRTHCUTOVER0000000" in tracked


def test_coord_seed_commit_is_resume_safe_noop_when_clean(tmp_path: Path) -> None:
    """F2: a second invocation (events already committed, tree clean) is a no-op
    — gated on dirty-state, not the per-run seeded_count, so resume heals without
    duplicating."""
    from specify_cli.merge.executor import _commit_coord_seed_events

    run, coord_worktree, status_feature_dir, _ = _coord_seed_run(tmp_path)
    _commit_coord_seed_events(run, status_feature_dir)
    head_after_first = _git(coord_worktree, "rev-parse", "HEAD").stdout.strip()

    _commit_coord_seed_events(run, status_feature_dir)  # resume: nothing dirty
    head_after_second = _git(coord_worktree, "rev-parse", "HEAD").stdout.strip()
    assert head_after_second == head_after_first  # no duplicate commit


def test_coord_seed_commit_best_effort_never_raises(tmp_path: Path) -> None:
    """F3: a resolution failure (no coord ref captured) is a silent no-op, never
    an exception that would abort the merge."""
    import types
    from typing import cast

    from specify_cli.merge.executor import _MergeRunState, _commit_coord_seed_events

    run, _coord_worktree, status_feature_dir, _ = _coord_seed_run(tmp_path)
    # Drop the coord ref -> the helper must no-op, not raise.
    broken = cast(
        "_MergeRunState",
        types.SimpleNamespace(
            main_repo=run.main_repo,
            mission_slug=run.mission_slug,
            pre_target_coord_ref=None,
            canonical_events_path=run.canonical_events_path,
        ),
    )
    _commit_coord_seed_events(broken, status_feature_dir)  # must not raise
