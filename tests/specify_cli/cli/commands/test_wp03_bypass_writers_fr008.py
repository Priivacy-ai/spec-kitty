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


# ---------------------------------------------------------------------------
# WP07 / #2058 / FR-006 — the three tasks.py planning-commit tails
# (move-task / mark-status / map-requirements) route their commit through the
# ONE canonical ``commit_for_mission`` router, and the protected-primary refusal
# message + exit code stay byte-identical to the pre-refactor pre-check.
# ---------------------------------------------------------------------------


def _expected_protected_message(command: str, branch: str = "main") -> str:
    """The EXACT protected-branch refusal message the tails surfaced pre-WP07.

    Reconstructs ``_protected_branch_status_commit_error``'s string verbatim so a
    drift in either the production message or this test fails loudly (C-003
    byte-identity).
    """
    return (
        f"Refusing to run `{command}` with auto-commit on protected branch "
        f"'{branch}' before mutating status files. Run status commit "
        "operations from an allowed coordination/lane branch, or rerun with "
        "--no-auto-commit when you intentionally want to handle the status "
        "artifact commit manually."
    )


class TestTasksTailsRouteThroughCommitForMission:
    """T031: each tail commits ONLY via ``commit_for_mission`` (no direct git path)."""

    def test_tasks_module_has_no_direct_safe_commit_symbol(self) -> None:
        """tasks.py imports the router, not ``safe_commit`` — git goes via the router.

        After WP07 the three tails no longer reference ``safe_commit`` directly;
        the only commit surface is the imported ``commit_for_mission`` router. A
        regrown direct ``safe_commit`` import/attribute would reintroduce a parallel
        commit path (FR-006 / C-002).
        """
        from specify_cli.cli.commands.agent import tasks as tasks_mod

        assert hasattr(tasks_mod, "commit_for_mission"), (
            "tasks.py must import the canonical commit_for_mission router (FR-006)"
        )
        assert not hasattr(tasks_mod, "safe_commit"), (
            "tasks.py must NOT carry a direct safe_commit symbol after WP07 — the "
            "commit goes through commit_for_mission only (FR-006 / C-002)"
        )

    def test_tasks_py_has_no_direct_safe_commit_call(self) -> None:
        """AST guard: zero ``safe_commit(...)`` call sites remain in tasks.py."""
        import ast

        src = Path(
            "src/specify_cli/cli/commands/agent/tasks.py"
        ).read_text(encoding="utf-8")
        tree = ast.parse(src)
        safe_commit_calls = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and (
                (isinstance(node.func, ast.Name) and node.func.id == "safe_commit")
                or (
                    isinstance(node.func, ast.Attribute)
                    and node.func.attr == "safe_commit"
                )
            )
        ]
        assert safe_commit_calls == [], (
            "tasks.py still has direct safe_commit call sites; all three tails must "
            "route through commit_for_mission (FR-006)"
        )


class TestTasksTailsProtectedPrimaryByteIdentical:
    """T031: protected-primary refusal is byte-identical (message + exit code)."""

    @pytest.fixture
    def _protected_main(self, monkeypatch: pytest.MonkeyPatch) -> object:
        """Patch the shared resolvers so each command reaches its auto-commit
        pre-check on a PROTECTED ``main`` primary, then stops (exit 1).
        """
        from specify_cli.cli.commands.agent import tasks as tasks_mod

        monkeypatch.setattr(tasks_mod, "locate_project_root", lambda: Path("/repo"))
        monkeypatch.setattr(
            tasks_mod, "_find_mission_slug", lambda **_kwargs: _SLUG
        )
        monkeypatch.setattr(
            tasks_mod,
            "_ensure_target_branch_checked_out",
            lambda *_args, **_kwargs: (Path("/repo"), "main"),
        )
        monkeypatch.setattr(
            tasks_mod, "_emit_sparse_session_warning", lambda *_args, **_kwargs: None
        )
        monkeypatch.setattr(
            tasks_mod, "get_auto_commit_default", lambda *_args, **_kwargs: True
        )

        class _AlwaysProtected:
            def is_protected(self, _ref: str) -> bool:
                return True

        monkeypatch.setattr(
            "specify_cli.cli.commands.agent.tasks.ProtectionPolicy.resolve",
            classmethod(lambda _cls, _root: _AlwaysProtected()),
        )
        # move-task must NOT take the coord-skip arm (that is a separate, preserved
        # behaviour); force coord topology inactive so it hits the refusal pre-check.
        monkeypatch.setattr(
            tasks_mod, "_coord_topology_active", lambda *_args, **_kwargs: False
        )
        # map-requirements resolves its placement (filesystem) BEFORE the pre-check;
        # stub it to a primary "main" target so the refusal arm fires deterministically
        # without a real repo. tasks.py imports ``_resolve_planning_placement`` via a
        # function-local import from ``commit_router`` (the canonical source), so patch
        # it THERE — patching the inert ``mission`` re-export leaves the real resolver
        # live and it crashes on the fake ``/repo`` (post-#2056 reconciliation).
        from mission_runtime import CommitTarget

        monkeypatch.setattr(
            "specify_cli.coordination.commit_router._resolve_planning_placement",
            lambda *_args, **_kwargs: CommitTarget(ref="main"),
        )
        # If the router were ever reached (it must NOT be — the pre-check refuses
        # first), fail loudly: a reached router means the pre-check regressed.
        def _router_must_not_be_reached(*_args: object, **_kwargs: object) -> object:
            raise AssertionError(
                "commit_for_mission was reached on a protected primary; the "
                "pre-check refusal must short-circuit before any commit (C-003)"
            )

        monkeypatch.setattr(
            tasks_mod, "commit_for_mission", _router_must_not_be_reached
        )
        return monkeypatch

    def _assert_json_error_byte_identical(
        self, output: str, command: str
    ) -> None:
        """The ``--json`` error envelope carries the message verbatim (no Rich reflow)."""
        import json

        payload = json.loads(output.strip().splitlines()[-1])
        assert payload["error"] == _expected_protected_message(command), (
            f"protected-primary message drifted for {command!r}; got:\n"
            f"{payload['error']!r}"
        )

    def test_mark_status_protected_primary_message_byte_identical(
        self, _protected_main: object
    ) -> None:
        from typer.testing import CliRunner

        from specify_cli.cli.commands.agent.tasks import app

        result = CliRunner().invoke(
            app,
            ["mark-status", "T001", "--status", "done", "--mission", _SLUG, "--auto-commit", "--json"],
        )
        assert result.exit_code == 1, result.output
        self._assert_json_error_byte_identical(
            result.output, "spec-kitty agent tasks mark-status"
        )

    def test_map_requirements_protected_primary_message_byte_identical(
        self, _protected_main: object
    ) -> None:
        from typer.testing import CliRunner

        from specify_cli.cli.commands.agent.tasks import app

        result = CliRunner().invoke(
            app,
            ["map-requirements", "--wp", "WP01", "--refs", "FR-001", "--mission", _SLUG, "--auto-commit", "--json"],
        )
        assert result.exit_code == 1, result.output
        self._assert_json_error_byte_identical(
            result.output, "spec-kitty agent tasks map-requirements"
        )

    def test_move_task_protected_primary_message_byte_identical(
        self, _protected_main: object
    ) -> None:
        from typer.testing import CliRunner

        from specify_cli.cli.commands.agent.tasks import app

        result = CliRunner().invoke(
            app,
            ["move-task", "WP01", "--to", "for_review", "--mission", _SLUG, "--auto-commit", "--json"],
        )
        assert result.exit_code == 1, result.output
        self._assert_json_error_byte_identical(
            result.output, "spec-kitty agent tasks move-task"
        )
