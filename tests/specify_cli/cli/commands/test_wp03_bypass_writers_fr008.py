"""WP03 (write-surface-coherence-01KVTVZS) — bypass-writer convergence + FR-008.

Covers the three converged write authorities and the FR-008 message rewrite
(DECISION 5):

* T012 — ``safe-commit``'s ``_resolve_mission_aware_target`` consults the
  kind-aware authority so a planning artifact under coordination topology resolves
  to the primary ``target_branch`` (not coord).
* ``kind_for_mission_file`` — the single public file→kind classifier (NFR-004).
* T015 — BOTH FR-008 refusal messages name the feature-branch remedy and do NOT
  advise the coordination worktree: the router refusal (a returned
  ``no_op_wrong_surface`` diagnostic) AND ``ProtectedBranchRefused`` (a raised
  exception message).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from mission_runtime import MissionArtifactKind, kind_for_mission_file
from specify_cli.git.commit_helpers import ProtectedBranchRefused

pytestmark = [pytest.mark.unit, pytest.mark.git_repo]

# Realistic identity (NFR-005 / test-data policy): real ULID + mid8 + slug.
_SLUG = "write-surface-coherence-01KVTVZS"


# ---------------------------------------------------------------------------
# kind_for_mission_file — the ONE public file→kind classifier (NFR-004)
# ---------------------------------------------------------------------------


class TestKindForMissionFile:
    @pytest.mark.parametrize(
        ("rel_path", "expected"),
        [
            (f"kitty-specs/{_SLUG}/spec.md", MissionArtifactKind.SPEC),
            (f"kitty-specs/{_SLUG}/plan.md", MissionArtifactKind.FINALIZED_EXECUTION_PLAN),
            (f"kitty-specs/{_SLUG}/tasks.md", MissionArtifactKind.TASKS_INDEX),
            (f"kitty-specs/{_SLUG}/tasks/WP03-foo.md", MissionArtifactKind.WORK_PACKAGE_TASK),
            (f"kitty-specs/{_SLUG}/data-model.md", MissionArtifactKind.DATA_MODEL),
            (f"kitty-specs/{_SLUG}/research.md", MissionArtifactKind.RESEARCH),
            (f"kitty-specs/{_SLUG}/status.events.jsonl", MissionArtifactKind.STATUS_STATE),
            (f"kitty-specs/{_SLUG}/analysis-report.md", MissionArtifactKind.ANALYSIS_REPORT),
        ],
    )
    def test_known_paths_classify(
        self, rel_path: str, expected: MissionArtifactKind
    ) -> None:
        assert kind_for_mission_file(rel_path, mission_slug=_SLUG) == expected

    def test_unknown_path_is_none(self) -> None:
        assert kind_for_mission_file("src/specify_cli/foo.py") is None
        assert (
            kind_for_mission_file(f"kitty-specs/{_SLUG}/notes.txt", mission_slug=_SLUG)
            is None
        )

    def test_other_mission_path_is_none(self) -> None:
        # A different mission's artifact is not classified for THIS mission_slug.
        assert (
            kind_for_mission_file("kitty-specs/other-mission/spec.md", mission_slug=_SLUG)
            is None
        )

    def test_planning_kinds_are_primary_partition(self) -> None:
        """A planning artifact classifies to a PRIMARY-partition kind (lands primary)."""
        from mission_runtime import is_primary_artifact_kind

        for rel in (f"kitty-specs/{_SLUG}/spec.md", f"kitty-specs/{_SLUG}/tasks/WP01.md"):
            kind = kind_for_mission_file(rel, mission_slug=_SLUG)
            assert kind is not None
            assert is_primary_artifact_kind(kind)

    def test_status_kind_is_not_primary_partition(self) -> None:
        """A status bookkeeping file is NOT a primary kind (keeps coord route)."""
        from mission_runtime import is_primary_artifact_kind

        kind = kind_for_mission_file(
            f"kitty-specs/{_SLUG}/status.events.jsonl", mission_slug=_SLUG
        )
        assert kind is not None
        assert not is_primary_artifact_kind(kind)


# ---------------------------------------------------------------------------
# T012 — safe-commit's mission-aware target is kind-aware (planning → primary)
# ---------------------------------------------------------------------------


class TestSafeCommitMissionAwareTargetIsKindAware:
    def test_resolve_mission_aware_target_threads_kind(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """``_resolve_mission_aware_target`` passes the kind into the placement seam.

        Red-first: pre-WP03 this helper called ``resolve_placement_only`` WITHOUT
        a kind. After T012 it threads the kind so a planning artifact resolves to
        the primary partition. We assert the kind reaches the seam.
        """
        import specify_cli.cli.commands.safe_commit_cmd as cmd

        seen: dict[str, object] = {}

        def _fake_resolve(repo_root: Path, mission_slug: str, *, kind: object) -> object:
            seen["kind"] = kind
            from mission_runtime import CommitTarget

            return CommitTarget(ref="feat/some-target")

        monkeypatch.setattr(
            "mission_runtime.resolve_placement_only", _fake_resolve
        )
        target = cmd._resolve_mission_aware_target(
            Path("/repo"), _SLUG, MissionArtifactKind.SPEC
        )
        assert seen["kind"] is MissionArtifactKind.SPEC
        assert target is not None
        assert target.ref == "feat/some-target"

    def test_mission_file_kind_classifies_first_kitty_specs_arg(self) -> None:
        """``_mission_file_kind`` derives the kind from the file path via the classifier."""
        import specify_cli.cli.commands.safe_commit_cmd as cmd

        repo_root = Path("/repo")
        spec = repo_root / "kitty-specs" / _SLUG / "spec.md"
        kind = cmd._mission_file_kind(repo_root, [spec], _SLUG)
        assert kind is MissionArtifactKind.SPEC


# ---------------------------------------------------------------------------
# T015 — FR-008 message rewrite (DECISION 5): both messages name a feature branch
# ---------------------------------------------------------------------------


class TestFR008MessagesNameFeatureBranch:
    def test_protected_branch_refused_message_remedy(self) -> None:
        """``ProtectedBranchRefused`` (raised) names a feature branch, not coord."""
        exc = ProtectedBranchRefused(
            destination_ref="main",
            worktree_root=Path("/repo"),
            commit_message="spec: planning commit",
        )
        message = str(exc).lower()
        assert "feature branch" in message, (
            f"FR-008 message must name the feature-branch remedy; got: {exc!s}"
        )
        assert "coordination worktree" not in message, (
            f"FR-008 message must NOT advise the coordination worktree; got: {exc!s}"
        )

    def test_router_refusal_diagnostic_remedy(
        self, tmp_path: Path
    ) -> None:
        """The router refusal (returned ``no_op_wrong_surface``) names a feature branch.

        Drives the REAL ``commit_for_mission`` on a flattened/primary protected
        ref so the protected-primary refusal arm fires, then asserts the returned
        diagnostic carries the feature-branch remedy and NOT the coord worktree.
        """
        from mission_runtime import CommitTarget
        from specify_cli.coordination import commit_router as router

        class _AlwaysProtected:
            def is_protected(self, _ref: str) -> bool:
                return True

        # Force a primary placement on a protected ref (flattened: no coord route),
        # exercising the protected-primary refusal arm without a full git repo.
        monkeypatch_targets = {
            "resolve_placement_only": lambda _r, _s, *, kind: CommitTarget(ref="main"),
            "resolve_topology": lambda _r, _s: None,
            "routes_through_coordination": lambda _t: False,
            "_resolve_primary_target_branch": lambda _r, _s: "main",
        }
        import pytest as _pytest

        with _pytest.MonkeyPatch.context() as mp:
            for name, fn in monkeypatch_targets.items():
                mp.setattr(f"specify_cli.coordination.commit_router.{name}", fn)
            spec = tmp_path / "spec.md"
            spec.write_text("# Spec\n", encoding="utf-8")
            result = router.commit_for_mission(
                repo_root=tmp_path,
                mission_slug=_SLUG,
                files=(spec,),
                message="spec: planning commit",
                policy=_AlwaysProtected(),
                kind=MissionArtifactKind.SPEC,
            )

        assert result.status == "no_op_wrong_surface", (
            f"expected the protected-primary refusal, got {result.status!r}"
        )
        diagnostic = (result.diagnostic or "").lower()
        assert "feature branch" in diagnostic, (
            f"router refusal must name the feature-branch remedy; got: {result.diagnostic!r}"
        )
        assert "coordination worktree" not in diagnostic, (
            "router refusal must NOT advise the coordination worktree; got: "
            f"{result.diagnostic!r}"
        )
