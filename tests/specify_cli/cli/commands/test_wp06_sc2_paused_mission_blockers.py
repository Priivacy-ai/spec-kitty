"""WP06 / T022 — SC-2 reproduction: the paused 01KTNWFC blockers do not reproduce.

The doctrine-glossary-architecture-consolidation mission (01KTNWFC) was paused by
two structural deadlocks (``work/MISSION_01KTNWFC_PAUSED.md``):

* **#1814** — ``record-analysis`` deadlocked on *coord residue*: the primary
  checkout of a coordination-topology mission legitimately carries stale copies
  of the coord-owned status log/snapshot, and the dirty-tree preflight counted
  that residue as an unsafe dirty working tree, so ``record-analysis`` could
  never run from the primary checkout.
* **#1816** — implement-claim blocked on a *planning-artifact branch-split*: the
  placement decision was derived independently from meta.json, so a flattened
  mission was mis-treated as a primary↔coord split.

WP06 resolves both by routing the placement decision through the context's
single :class:`CommitTarget` (the ``ArtifactPlacementFragment.placement_ref`` ==
``BranchRefFragment.destination_ref``, C-PLACE-1). These tests reproduce the two
blockers at the precise sites that deadlocked and assert they no longer do — the
checks are genuine (real ``git status`` residue / real porcelain entries), not
mocked away.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
import typer

from mission_runtime import CommitTarget, CommitTargetKind
from specify_cli.status import COORD_OWNED_STATUS_FILES

pytestmark = [pytest.mark.unit, pytest.mark.git_repo]


# ---------------------------------------------------------------------------
# #1814 — record-analysis must not deadlock on coord residue
# ---------------------------------------------------------------------------
class TestRecordAnalysisCoordResidueNoDeadlock:
    """The dirty-tree preflight is context-aware (C-PLACE-1): under coordination
    topology the coord-owned status residue in the primary checkout is NOT a
    blocking dirty working tree."""

    def _repo_with_coord_residue(self, tmp_path: Path) -> Path:
        repo = tmp_path / "repo"
        repo.mkdir()

        def git(*args: str) -> None:
            subprocess.run(
                ["git", *args], cwd=repo, check=True, capture_output=True, text=True
            )

        git("init", "-b", "kitty/mission-residue-lane-a")
        git("config", "user.email", "t@example.com")
        git("config", "user.name", "Test")
        mission_dir = repo / "kitty-specs" / "residue-01ABCDEF"
        mission_dir.mkdir(parents=True)
        # Seed + commit the coord-owned status files so they are *tracked*; a
        # later edit makes them show up as worktree-modified residue.
        for name in sorted(COORD_OWNED_STATUS_FILES):
            (mission_dir / name).write_text("{}\n", encoding="utf-8")
        git("add", "-A")
        git("commit", "-m", "seed status files")
        # The coord branch is now the canonical owner of these files; the primary
        # checkout edit below is exactly the "coord residue" that deadlocked #1814.
        for name in sorted(COORD_OWNED_STATUS_FILES):
            (mission_dir / name).write_text('{"stale": true}\n', encoding="utf-8")
        return repo

    def test_coord_residue_does_not_block_record_analysis(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from specify_cli.cli.commands.agent.mission import (
            _enforce_analysis_report_write_preflight,
        )

        repo = self._repo_with_coord_residue(tmp_path)
        monkeypatch.chdir(repo)

        coord_placement = CommitTarget(
            ref="kitty/mission-residue-01ABCDEF",
            kind=CommitTargetKind.COORDINATION,
        )

        # WP06 fix: coord-owned residue is filtered out — no DIRTY_WORKTREE deadlock.
        _enforce_analysis_report_write_preflight(
            repo, json_output=True, placement_ref=coord_placement
        )

    def test_regression_guard_without_context_still_blocks(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Without the context placement ref (legacy call), the coord residue is
        still treated as dirty — proving the test exercises a *real* dirty tree
        and the fix is the context-awareness, not a weakened check."""
        from specify_cli.cli.commands.agent.mission import (
            _enforce_analysis_report_write_preflight,
        )

        repo = self._repo_with_coord_residue(tmp_path)
        monkeypatch.chdir(repo)

        with pytest.raises(typer.Exit):
            _enforce_analysis_report_write_preflight(repo, json_output=True)

    def test_genuine_uncommitted_edit_still_blocks_under_coord(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A *genuine* uncommitted non-status edit must still block even under
        coordination topology — the fix only ignores coord-owned residue, never
        real planning-artifact churn (no over-broad escape hatch)."""
        from specify_cli.cli.commands.agent.mission import (
            _enforce_analysis_report_write_preflight,
        )

        repo = self._repo_with_coord_residue(tmp_path)
        (repo / "kitty-specs" / "residue-01ABCDEF" / "spec.md").write_text(
            "dirty spec edit\n", encoding="utf-8"
        )
        monkeypatch.chdir(repo)

        coord_placement = CommitTarget(
            ref="kitty/mission-residue-01ABCDEF",
            kind=CommitTargetKind.COORDINATION,
        )
        with pytest.raises(typer.Exit):
            _enforce_analysis_report_write_preflight(
                repo, json_output=True, placement_ref=coord_placement
            )


# ---------------------------------------------------------------------------
# #1816 — implement-claim must not block on a planning-artifact branch-split
# ---------------------------------------------------------------------------
class TestImplementClaimNoPlanningArtifactSplit:
    """The planning-artifact placement decision comes from the context's single
    :class:`CommitTarget` (C-PLACE-1), so a flattened mission is never mis-routed
    as a primary↔coord split."""

    def _entries(self) -> list[object]:
        from specify_cli.cli.commands.implement import _PorcelainEntry

        return [
            _PorcelainEntry(
                xy=" M", path="kitty-specs/m/status.events.jsonl", is_structural=False
            ),
            _PorcelainEntry(
                xy=" M", path="kitty-specs/m/status.json", is_structural=False
            ),
            _PorcelainEntry(xy=" M", path="kitty-specs/m/tasks.md", is_structural=False),
        ]

    def test_flattened_placement_has_no_coord_split(self) -> None:
        from specify_cli.cli.commands.implement import (
            _placement_coord_filter,
            _status_paths_for_commit,
        )

        flattened = CommitTarget(
            ref="fixups/code-engine-stabilization", kind=CommitTargetKind.FLATTENED
        )
        # Flattened topology → no coord branch to reconcile (C-PLACE-1).
        assert _placement_coord_filter(flattened) is None

        # Consequently the status files are committed on the single flattened ref
        # (not excluded as coord-owned) — there is no primary↔coord split.
        paths = _status_paths_for_commit(
            self._entries(), _placement_coord_filter(flattened)
        )
        assert "kitty-specs/m/status.events.jsonl" in paths
        assert "kitty-specs/m/status.json" in paths
        assert "kitty-specs/m/tasks.md" in paths

    def test_coordination_placement_routes_to_coord_ref(self) -> None:
        from specify_cli.cli.commands.implement import (
            _placement_coord_filter,
            _status_paths_for_commit,
        )

        coord = CommitTarget(
            ref="kitty/mission-m-01ABCDEF", kind=CommitTargetKind.COORDINATION
        )
        # Coordination topology → the coord ref owns the status files; the primary
        # checkout's copies are excluded so they don't clobber the seeded state.
        assert _placement_coord_filter(coord) == "kitty/mission-m-01ABCDEF"
        paths = _status_paths_for_commit(self._entries(), _placement_coord_filter(coord))
        assert "kitty-specs/m/status.events.jsonl" not in paths
        assert "kitty-specs/m/status.json" not in paths
        assert "kitty-specs/m/tasks.md" in paths

    def test_primary_placement_commits_status_files(self) -> None:
        from specify_cli.cli.commands.implement import (
            _placement_coord_filter,
            _status_paths_for_commit,
        )

        primary = CommitTarget(ref="main", kind=CommitTargetKind.PRIMARY)
        # Primary/legacy topology → no coord owner; the primary status files are
        # canonical and must be committed.
        assert _placement_coord_filter(primary) is None
        paths = _status_paths_for_commit(
            self._entries(), _placement_coord_filter(primary)
        )
        assert "kitty-specs/m/status.events.jsonl" in paths
        assert "kitty-specs/m/status.json" in paths
