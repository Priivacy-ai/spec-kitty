"""Integration tests for WP06: dep-graph / frontmatter readers routed to seam.

Per-site RED-first tests (FR-004/FR-006/FR-009) proving the coord-topology routing
invariant for each of the three sites routed in WP06:

- **Site 1 — T026**: ``_check_dependent_warnings`` (``tasks_dependency_graph.py:118``)
  builds the dependency graph from PRIMARY (tasks/ lives there) while the STATUS leg
  (``compute_incomplete_dependents``) reads events from the coord-aware ``feature_dir``.

- **Site 2 — T027**: ``_validate_ready_for_review`` (``tasks_parsing_validation.py:935``)
  reads research artifacts from PRIMARY via ``resolve_planning_read_dir(kind=RESEARCH)``.

- **Site 3 — T028**: ``validate_tasks`` command (``validate_tasks.py:113``) passes
  the WORK_PACKAGE_TASK-partition PRIMARY dir to ``scan_all_tasks_for_mismatches``
  (single-leg PRIMARY — WP-frontmatter vs lane-subdir, no STATUS leg).

All sites are **gate-blind** (the tasks/ join is inside helper functions, not at the
resolver call site), so no ratchet pins were added for these sites.  The tests here are
the regression proof.

Fixture layout (from ``coord_topology_fixture``):

* ``primary_feature_dir/``   — meta.json, tasks/WP01.md, lanes.json, DECOY events
* ``coord_feature_dir/``     — status.events.jsonl ONLY (coord marker)
* ``status_events_path``     — coord husk authoritative events file
* ``decoy_events_path``      — primary DECOY events file (distinct content)
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from tests.integration.coord_topology_fixture import (
    CoordTopologyContext,
    FlatTopologyContext,
    coord_topology_mission,
    flat_topology_mission,
)

# Re-export fixtures so pytest discovers them.
__all__ = ["coord_topology_mission", "flat_topology_mission"]

pytestmark = [pytest.mark.integration, pytest.mark.git_repo]


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _make_wp_task_content(wp_id: str, *, dependencies: list[str] | None = None) -> str:
    """Return minimal WP task file content with optional dependency frontmatter."""
    dep_lines = ""
    if dependencies:
        dep_lines = "dependencies:\n" + "".join(f"- {d}\n" for d in dependencies)
    return (
        f"---\nwork_package_id: {wp_id}\ntitle: {wp_id} test task\n"
        f"{dep_lines}---\n# {wp_id}\n"
    )


def _mock_workspace(branch_name: str | None = None) -> MagicMock:
    """Return a MagicMock workspace with the given branch_name."""
    ws = MagicMock()
    ws.branch_name = branch_name
    return ws


# ---------------------------------------------------------------------------
# Site 1 — _check_dependent_warnings (T026)
# ---------------------------------------------------------------------------


class TestCheckDependentWarningsRoutesToPrimary:
    """T026: build_dependency_graph caller uses PRIMARY dir (tasks/); STATUS stays coord.

    C-001 per-leg split: the dep-graph builder reads tasks/WP*.md files from PRIMARY;
    compute_incomplete_dependents reads status events from the coord-aware feature_dir.
    """

    def test_red_proof_coord_husk_has_no_tasks_dir(
        self, coord_topology_mission: CoordTopologyContext
    ) -> None:
        """Gate-blind RED proof: pre-fix, coord-aware resolver returns husk with no tasks/.

        Before WP06, ``_check_dependent_warnings`` called
        ``resolve_feature_dir_for_mission(main_repo_root, slug)`` for the graph build.
        For a coord-topology mission that function returns the STATUS-only coord husk.
        The husk carries no ``tasks/`` directory (fixture invariant).
        ``build_dependency_graph(coord_husk)`` would therefore return ``{}`` — an empty
        graph with no dependents — silently suppressing the dependency warning even when
        WP02 declared a dependency on WP01.

        This test documents the RED state: the coord husk lacks tasks/.
        """
        from specify_cli.missions._read_path_resolver import (
            candidate_feature_dir_for_mission,
        )

        ctx = coord_topology_mission

        # The coord-aware resolver returns the husk (status-only).
        pre_fix_path = candidate_feature_dir_for_mission(ctx.repo, ctx.slug)
        assert pre_fix_path == ctx.coord_feature_dir, (
            "RED anchor: coord-aware resolver must return the coord husk"
        )
        # The husk has no tasks/ — build_dependency_graph(husk) returns {}.
        assert not (pre_fix_path / "tasks").exists(), (
            "RED anchor: tasks/ must be absent from coord husk; "
            "build_dependency_graph(husk) would return {} → no warning even with WP02 dep"
        )

    def test_dependency_warning_reads_graph_from_primary(
        self, coord_topology_mission: CoordTopologyContext
    ) -> None:
        """GREEN: _check_dependent_warnings prints WP02 warning when dep found on PRIMARY.

        Setup: WP02.md with ``dependencies: [WP01]`` is added to PRIMARY tasks/.
        After WP06, ``build_dependency_graph`` is called with the PRIMARY dir
        (``resolve_planning_read_dir(kind=WORK_PACKAGE_TASK)``) so it finds WP02.

        The STATUS leg (``compute_incomplete_dependents``) reads events from the
        coord-aware ``feature_dir`` (patched to coord husk).  No parseable events
        exist for WP02 → lane defaults to PLANNED → WP02 is incomplete → warning printed.

        The console.print call containing "WP02" proves the graph was built from
        PRIMARY (coord husk has no tasks/ → empty graph → no warning without the fix).
        """
        from specify_cli.cli.commands.agent.tasks_dependency_graph import (
            _check_dependent_warnings,
        )

        ctx = coord_topology_mission

        # Add WP02 with dependency on WP01 to PRIMARY tasks/.
        tasks_dir = ctx.primary_feature_dir / "tasks"
        (tasks_dir / "WP02.md").write_text(
            _make_wp_task_content("WP02", dependencies=["WP01"]),
            encoding="utf-8",
        )

        mock_ws = _mock_workspace(branch_name=None)
        printed_args: list[str] = []

        module = "specify_cli.cli.commands.agent.tasks_dependency_graph"
        # read-surface-ssot-closeout WP08 / FR-001: the STATUS leg now routes
        # through the kind-aware ``mission_runtime.placement_seam(...)
        # .read_dir(STATUS_STATE)`` seam (late-imported inside the function,
        # mirroring the ``_resolve_workflow_placement`` lazy-import convention
        # — tests/specify_cli/cli/commands/agent/test_workflow_placement_routing
        # .py). Stub the seam itself rather than the retired
        # ``resolve_feature_dir_for_mission`` name.
        mock_seam = MagicMock()
        mock_seam.read_dir.return_value = ctx.coord_feature_dir
        with (
            patch(
                "mission_runtime.placement_seam",
                return_value=mock_seam,
            ),
            patch(
                f"{module}.resolve_workspace_for_wp",
                return_value=mock_ws,
            ),
            patch(
                f"{module}.console",
            ) as mock_console,
        ):
            mock_console.print.side_effect = lambda *a, **kw: printed_args.append(
                " ".join(str(x) for x in a)
            )
            _check_dependent_warnings(
                ctx.repo, ctx.slug, "WP01", "for_review", json_mode=False
            )

        # The dependency warning must mention WP02 — proves graph was built from PRIMARY.
        assert any("WP02" in msg for msg in printed_args), (
            f"Expected WP02 dependency warning to be printed (graph built from PRIMARY).\n"
            f"Printed messages: {printed_args}\n"
            "If this is empty, build_dependency_graph ran on the coord husk (no tasks/) "
            "and returned {} — the pre-WP06 bug."
        )
        from mission_runtime import MissionArtifactKind

        mock_seam.read_dir.assert_called_once_with(MissionArtifactKind.STATUS_STATE)

    def test_neutrality_flat_topology(
        self, flat_topology_mission: FlatTopologyContext
    ) -> None:
        """Flat topology: _check_dependent_warnings returns silently when no dependents."""
        from specify_cli.cli.commands.agent.tasks_dependency_graph import (
            _check_dependent_warnings,
        )

        ctx = flat_topology_mission

        module = "specify_cli.cli.commands.agent.tasks_dependency_graph"
        # See the routed-STATUS-leg note above: stub the seam, not the
        # retired ``resolve_feature_dir_for_mission`` name.
        mock_seam = MagicMock()
        mock_seam.read_dir.return_value = ctx.primary_feature_dir
        with (
            patch("mission_runtime.placement_seam", return_value=mock_seam),
            patch(f"{module}.resolve_workspace_for_wp", return_value=_mock_workspace()),
            patch(f"{module}.console") as mock_console,
        ):
            _check_dependent_warnings(
                ctx.repo, ctx.slug, "WP01", "for_review", json_mode=False
            )
            # No dependents declared → no print calls about dependents.
            dep_prints = [
                " ".join(str(a) for a in call.args)
                for call in mock_console.print.call_args_list
                if "depend on" in " ".join(str(a) for a in call.args)
            ]
            assert not dep_prints, (
                f"Unexpected dependency warning on flat topology: {dep_prints}"
            )


# ---------------------------------------------------------------------------
# Site 2 — _validate_ready_for_review (T027)
# ---------------------------------------------------------------------------


class TestValidateReadyForReviewRoutesToPrimary:
    """T027: _validate_ready_for_review routes research-artifact read to PRIMARY.

    FR-006: research.md / meta.json / spec.md live on PRIMARY (not the coord husk).
    The coord husk is STATUS-only — ``git status --porcelain <husk>`` from the main
    repo returns EMPTY (linked worktrees are not tracked by the main repo's git status).
    """

    def test_red_proof_husk_invisible_to_main_repo_git_status(
        self, coord_topology_mission: CoordTopologyContext
    ) -> None:
        """Gate-blind RED proof: pre-fix, dirty primary research.md bypasses the gate.

        Before WP06, ``feature_dir = resolve_feature_dir_for_mission(...)`` returned
        the coord husk. ``_validate_research_artifacts`` ran
        ``git status --porcelain <husk_dir>`` from the main repo — the husk is a LINKED
        WORKTREE, so main-repo git status returns EMPTY for its paths.  The gate passed
        unconditionally (``True, []``) even when an uncommitted research.md existed on
        the PRIMARY checkout.  The dirty file was invisible from the husk path.

        This test documents the RED state: the husk has no meta.json and is not
        tracked by the primary repo's git status.
        """
        import subprocess

        ctx = coord_topology_mission

        # Coord husk carries no meta.json (planning artifacts are on PRIMARY only).
        assert not (ctx.coord_feature_dir / "meta.json").exists(), (
            "RED anchor: meta.json must be absent from coord husk"
        )

        # Write a dirty research.md to PRIMARY (not committed → dirty).
        research_file = ctx.primary_feature_dir / "research.md"
        research_file.write_text("# Research notes (uncommitted)\n", encoding="utf-8")

        # git status --porcelain <coord_husk_dir> from the main repo returns EMPTY:
        # the coord husk is a linked worktree; its files are invisible to main-repo git.
        result = subprocess.run(
            ["git", "status", "--porcelain", str(ctx.coord_feature_dir)],
            cwd=ctx.repo,
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.stdout.strip() == "", (
            "RED anchor: git status on coord husk dir from main repo must return empty "
            "(linked worktree files are not tracked by main-repo git status). "
            f"Got: {result.stdout.strip()!r}"
        )

        # Cleanup — leave primary dirty for the GREEN test.
        research_file.unlink()

    def test_research_artifact_check_blocks_on_dirty_primary(
        self, coord_topology_mission: CoordTopologyContext
    ) -> None:
        """GREEN: _validate_ready_for_review detects dirty research.md on PRIMARY.

        After WP06, ``feature_dir = resolve_planning_read_dir(kind=RESEARCH)`` →
        ``ctx.primary_feature_dir``.  ``_validate_research_artifacts`` runs
        ``git status --porcelain str(primary_feature_dir)`` from the main repo and
        FINDS the uncommitted research.md → classifies it as blocking → returns
        ``(False, guidance)`` correctly.

        Contrast with the pre-fix behaviour (T027 RED proof above): the coord husk
        was invisible to main-repo git status, so the gate always passed when it
        should have blocked.
        """
        from specify_cli.cli.commands.agent.tasks_parsing_validation import (
            _validate_ready_for_review,
        )
        from specify_cli.core.constants import MISSION_TYPE_RESEARCH

        ctx = coord_topology_mission

        # Write a dirty (uncommitted) research.md to PRIMARY.
        research_file = ctx.primary_feature_dir / "research.md"
        research_file.write_text("# Uncommitted research notes\n", encoding="utf-8")

        class _SilentConsole:
            def print(self, *args: object, **kwargs: object) -> None:
                pass

        try:
            is_valid, guidance = _validate_ready_for_review(
                ctx.repo,
                ctx.slug,
                "WP01",
                force=False,
                target_lane="for_review",
                get_main_repo_root=lambda _: ctx.repo,
                get_mission_type=lambda _: MISSION_TYPE_RESEARCH,
                # Remaining injected collaborators are not called for research type
                # (worktree check is gated on MISSION_TYPE_SOFTWARE_DEV).
                get_feature_target_branch=lambda *_a: "main",
                resolve_workspace_for_wp=lambda *_a: _mock_workspace(),
                review_currency_check_branch=lambda *_a: "main",
                behind_commits_touch_only_planning_artifacts=lambda *_a: True,
                filter_runtime_state_paths=lambda s: s,
                list_wp_branch_specs_changes_for_guard=lambda *_a: [],
                console=_SilentConsole(),
            )
        finally:
            # Clean up the dirty file regardless of test outcome.
            if research_file.exists():
                research_file.unlink()

        assert not is_valid, (
            "After WP06, _validate_ready_for_review must detect the dirty research.md "
            "on PRIMARY and return is_valid=False."
        )
        assert guidance, (
            "Expected non-empty guidance list when blocking dirty files are found on PRIMARY."
        )
        # At least one guidance line should mention the file or advise git commit.
        guidance_text = "\n".join(guidance)
        assert "kitty-specs" in guidance_text or "research.md" in guidance_text or "uncommitted" in guidance_text.lower(), (
            f"Guidance text should reference the research artifacts.\nGot: {guidance_text}"
        )

    def test_research_gate_passes_when_primary_is_clean(
        self, coord_topology_mission: CoordTopologyContext
    ) -> None:
        """GREEN neutrality: gate passes when no dirty files exist on PRIMARY."""
        from specify_cli.cli.commands.agent.tasks_parsing_validation import (
            _validate_ready_for_review,
        )
        from specify_cli.core.constants import MISSION_TYPE_RESEARCH

        ctx = coord_topology_mission

        class _SilentConsole:
            def print(self, *args: object, **kwargs: object) -> None:
                pass

        # No dirty files — gate must pass.
        is_valid, guidance = _validate_ready_for_review(
            ctx.repo,
            ctx.slug,
            "WP01",
            force=False,
            target_lane="for_review",
            get_main_repo_root=lambda _: ctx.repo,
            get_mission_type=lambda _: MISSION_TYPE_RESEARCH,
            get_feature_target_branch=lambda *_a: "main",
            resolve_workspace_for_wp=lambda *_a: _mock_workspace(),
            review_currency_check_branch=lambda *_a: "main",
            behind_commits_touch_only_planning_artifacts=lambda *_a: True,
            filter_runtime_state_paths=lambda s: s,
            list_wp_branch_specs_changes_for_guard=lambda *_a: [],
            console=_SilentConsole(),
        )

        assert is_valid, (
            f"Gate must pass when PRIMARY is clean.\nguidance: {guidance}"
        )
        assert guidance == [], (
            f"No blocking guidance expected when PRIMARY is clean.\nguidance: {guidance}"
        )

    def test_neutrality_flat_topology_clean_primary(
        self, flat_topology_mission: FlatTopologyContext
    ) -> None:
        """Flat topology: gate passes when primary is clean (no regression)."""
        from specify_cli.cli.commands.agent.tasks_parsing_validation import (
            _validate_ready_for_review,
        )
        from specify_cli.core.constants import MISSION_TYPE_RESEARCH

        ctx = flat_topology_mission

        class _SilentConsole:
            def print(self, *args: object, **kwargs: object) -> None:
                pass

        is_valid, guidance = _validate_ready_for_review(
            ctx.repo,
            ctx.slug,
            "WP01",
            force=False,
            target_lane="for_review",
            get_main_repo_root=lambda _: ctx.repo,
            get_mission_type=lambda _: MISSION_TYPE_RESEARCH,
            get_feature_target_branch=lambda *_a: "main",
            resolve_workspace_for_wp=lambda *_a: _mock_workspace(),
            review_currency_check_branch=lambda *_a: "main",
            behind_commits_touch_only_planning_artifacts=lambda *_a: True,
            filter_runtime_state_paths=lambda s: s,
            list_wp_branch_specs_changes_for_guard=lambda *_a: [],
            console=_SilentConsole(),
        )

        assert is_valid, (
            f"Flat topology gate must pass when primary is clean.\nguidance: {guidance}"
        )


# ---------------------------------------------------------------------------
# Site 3 — validate_tasks command (T028)
# ---------------------------------------------------------------------------


class TestValidateTasksRoutesToPrimary:
    """T028: validate_tasks command passes PRIMARY dir to scan_all_tasks_for_mismatches.

    FR-009 / single-leg PRIMARY: the WORK_PACKAGE_TASK-partition primary dir is
    passed to ``scan_all_tasks_for_mismatches`` (which reads WP-frontmatter via
    tasks/planned|doing|… lane subdirs). The frontmatter-vs-subdir comparison is a
    single-leg read entirely on the planning surface — there is no STATUS leg.
    """

    def test_red_proof_coord_husk_has_no_legacy_tasks_subdirs(
        self, coord_topology_mission: CoordTopologyContext
    ) -> None:
        """Gate-blind RED proof: pre-fix, scan_all_tasks_for_mismatches on coord husk returns {}.

        Before WP06, ``feature_dir = resolve_feature_dir_for_slug(repo_root, slug)``
        returned the coord husk (STATUS-only).  The husk carries no ``tasks/`` directory,
        so ``scan_all_tasks_for_mismatches(husk)`` returns ``{}`` — zero mismatches —
        even when legacy WP files on PRIMARY have lane frontmatter mismatches.

        This test documents the RED state: coord husk has no tasks/.
        """
        from specify_cli.task_metadata_validation import scan_all_tasks_for_mismatches

        ctx = coord_topology_mission

        # Coord husk has no tasks/ → scan returns {} silently (pre-fix bug).
        assert not (ctx.coord_feature_dir / "tasks").exists(), (
            "RED anchor: coord husk must have no tasks/ directory"
        )
        result = scan_all_tasks_for_mismatches(ctx.coord_feature_dir)
        assert result == {}, (
            f"RED anchor: scan on coord husk must return empty dict (no tasks/ subdir).\n"
            f"Got: {result}"
        )

    def test_validate_tasks_detects_mismatch_on_primary(
        self, coord_topology_mission: CoordTopologyContext
    ) -> None:
        """GREEN: validate_tasks --mission finds legacy frontmatter mismatch on PRIMARY.

        A legacy WP99.md is placed in ``tasks/planned/`` on PRIMARY with
        ``lane: for_review`` (frontmatter mismatch — file is in planned/ but lane says
        for_review).  After WP06, ``scan_all_tasks_for_mismatches`` receives the PRIMARY
        dir → finds WP99.md → reports 1 mismatch → command exits 1.

        Before WP06, the coord husk (no tasks/) was scanned → 0 mismatches → exit 0,
        silently missing the mismatch.
        """
        import typer
        from typer.testing import CliRunner

        from specify_cli.cli.commands.validate_tasks import validate_tasks

        ctx = coord_topology_mission

        # Seed a legacy mismatch on PRIMARY: WP99.md in tasks/planned/ but lane says for_review.
        planned_dir = ctx.primary_feature_dir / "tasks" / "planned"
        planned_dir.mkdir(parents=True, exist_ok=True)
        (planned_dir / "WP99.md").write_text(
            "---\nwork_package_id: WP99\nlane: for_review\ntitle: Legacy WP\n---\n# WP99\n",
            encoding="utf-8",
        )

        app = typer.Typer()
        app.command()(validate_tasks)
        runner = CliRunner()

        with (
            patch(
                "specify_cli.cli.commands.validate_tasks.find_repo_root",
                return_value=ctx.repo,
            ),
            patch(
                "specify_cli.cli.commands.validate_tasks.get_project_root_or_exit",
                return_value=ctx.repo,
            ),
        ):
            result = runner.invoke(app, ["--mission", ctx.slug])

        assert result.exit_code == 1, (
            f"validate_tasks must exit 1 when mismatch found on PRIMARY.\n"
            f"Output: {result.output}\n"
            f"Exception: {result.exception}"
        )
        output = result.output
        assert "mismatch" in output.lower() or "WP99" in output or "Needs Fix" in output, (
            f"Output must mention the mismatch or WP99.\nFull output: {output}"
        )

    def test_validate_tasks_reads_frontmatter_from_primary(
        self, coord_topology_mission: CoordTopologyContext
    ) -> None:
        """GREEN: validate_tasks only scans the PRIMARY planning surface, not the coord husk.

        A legacy WP file with a lane frontmatter mismatch is seeded into the COORD
        HUSK's tasks/planned/ directory (artificially).  PRIMARY has no mismatch files.
        The command must exit 0 — proving that scan_all_tasks_for_mismatches receives
        the PRIMARY dir (single-leg PRIMARY read) and the husk's tasks/ is invisible.

        RED-first proof: if the code were broken and passed the coord husk instead of
        PRIMARY, scan_all_tasks_for_mismatches would find WP98.md and exit 1.
        """
        import typer
        from typer.testing import CliRunner

        from specify_cli.cli.commands.validate_tasks import validate_tasks

        ctx = coord_topology_mission

        # Seed a legacy lane mismatch in the coord husk's tasks/planned/ (artificial).
        # scan_all_tasks_for_mismatches on PRIMARY must NOT see this file.
        husk_planned = ctx.coord_feature_dir / "tasks" / "planned"
        husk_planned.mkdir(parents=True, exist_ok=True)
        (husk_planned / "WP98.md").write_text(
            "---\nwork_package_id: WP98\nlane: for_review\ntitle: Husk Mismatch\n---\n# WP98\n",
            encoding="utf-8",
        )
        # PRIMARY has no tasks/planned/ → no legacy mismatches → expect exit 0.

        app = typer.Typer()
        app.command()(validate_tasks)
        runner = CliRunner()

        with (
            patch(
                "specify_cli.cli.commands.validate_tasks.find_repo_root",
                return_value=ctx.repo,
            ),
            patch(
                "specify_cli.cli.commands.validate_tasks.get_project_root_or_exit",
                return_value=ctx.repo,
            ),
        ):
            result = runner.invoke(app, ["--mission", ctx.slug])

        assert result.exit_code == 0, (
            f"validate_tasks must exit 0: PRIMARY is clean; coord-husk mismatch is invisible.\n"
            f"Output: {result.output}\n"
            f"Exception: {result.exception}"
        )
        assert "consistent" in result.output.lower() or "0" in result.output, (
            f"Expected 0-mismatch output.\nFull output: {result.output}"
        )

    def test_neutrality_flat_topology(
        self, flat_topology_mission: FlatTopologyContext
    ) -> None:
        """Flat topology: validate_tasks exits 0 when no legacy mismatches on primary."""
        import typer
        from typer.testing import CliRunner

        from specify_cli.cli.commands.validate_tasks import validate_tasks

        ctx = flat_topology_mission

        app = typer.Typer()
        app.command()(validate_tasks)
        runner = CliRunner()

        with (
            patch(
                "specify_cli.cli.commands.validate_tasks.find_repo_root",
                return_value=ctx.repo,
            ),
            patch(
                "specify_cli.cli.commands.validate_tasks.get_project_root_or_exit",
                return_value=ctx.repo,
            ),
        ):
            result = runner.invoke(app, ["--mission", ctx.slug])

        assert result.exit_code == 0, (
            f"Flat topology: must exit 0 when no legacy mismatches.\n"
            f"Output: {result.output}\n"
            f"Exception: {result.exception}"
        )
