"""WP08 (#2116) — coreless orchestrator side-effects + the #2300 boundary gate.

The WP08 rewire thins the two **coreless** command bodies — ``mark_status`` and
``finalize_tasks`` — into thin orchestrators (``_do_mark_status`` /
``_do_finalize_tasks``) over the existing seams and the WP02 capability ports,
carrying **NO** transition decision core. This module has two jobs:

T033/T034/T035 — inject the WP02 **Fake** ports (``ports=`` on the extracted
    ``_do_<cmd>`` orchestrators — the C-005 injection seam that never touches the
    Typer surface) and assert the executed side-effects match the pre-rewire
    behaviour:

    ``mark_status``
        * the TASKS_INDEX write surface (#2154) is resolved through the
          ``FsReader.planning_read_dir`` port keyed ``TASKS_INDEX``;
        * an auto-commit run routes the tasks.md commit through the coord
          ``commit_artifact`` capability keyed ``TASKS_INDEX``, while a
          ``--no-auto-commit`` run leaves that seam untouched;
        * the production mark_status coord router (``seam_coord_router()``)
          re-resolves ``commit_for_mission`` through THIS module (so the ``@patch``
          seam keeps intercepting) and — unlike ``move_task``/``map_requirements``
          — does NOT thread a ``target_branch`` (byte-parity with the pre-rewire
          inline call);
        * the refuse-exit-1-on-protected divergence (T005 / deferred #2300) holds.

    ``finalize_tasks``
        * FR-010 fold: the pre30-guard read is resolved through the
          ``FsReader.planning_read_dir`` port keyed ``WORK_PACKAGE_TASK`` (migrated
          off the kind-blind coord-husk resolver), byte-identically per WP02 T013.

T036 — a **structural** non-import AST gate proving ``tasks_transition_core`` is
    NOT reachable from the ``mark_status`` / ``finalize_tasks`` code paths. Behaviour
    parity (golden) does NOT catch an illicit import — an implementer could route
    through the transition core then special-case the exit code back to 1 — so this
    gate guards the deferred-unification boundary (#2300) *structurally*. It is made
    non-tautological by a positive control: the SAME gate proves ``move_task``'s path
    DOES reach the core, so a vacuous "found nothing" pass is impossible.

NFR-004 pure parity: no behaviour change is encoded here.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path
from types import ModuleType
from unittest.mock import patch

import pytest
import typer

from mission_runtime import MissionArtifactKind

import specify_cli.cli.commands.agent.tasks as tasks_mod
from specify_cli.cli.commands.agent.tasks import (
    _do_finalize_tasks,
    _do_mark_status,
    seam_coord_router,
)
from specify_cli.agent_tasks_ports import MissionHandle, TasksPorts
from specify_cli.git.protection_policy import ProtectionPolicy
from specify_cli.status import BootstrapResult
from tests.mocked_env import setup_mocked_env
from tests.specify_cli.cli.commands.agent.test_tasks_ports import (
    FakeCoordCommitRouter,
    FakeFsReader,
    FakeGitOps,
    FakeRender,
)

pytestmark = pytest.mark.fast

_MISSION = "coreless-orchestration-01KWF08S"


# ===========================================================================
# Fixtures + Fake-port bundles
# ===========================================================================


def _fake_ports(planning_dir: Path, kind: MissionArtifactKind) -> tuple[
    TasksPorts, FakeFsReader, FakeCoordCommitRouter
]:
    """A WP02 Fake bundle whose FsReader resolves *kind* to the REAL on-disk dir.

    The orchestrator's tasks.md read/guard must land on the fixture dir, so the
    Fake ``planning_read_dir`` returns it for the pinned kind; the coord
    ``commit_artifact`` capability records its calls on a separate log.
    """
    fs = FakeFsReader(planning_dirs={kind: planning_dir}, default_planning_dir=planning_dir)
    coord = FakeCoordCommitRouter()
    return TasksPorts(fs=fs, coord=coord, git=FakeGitOps(), render=FakeRender()), fs, coord


def _build_mark_fixture(tmp_path: Path, mission_slug: str) -> Path:
    """Primary planning surface: meta.json + a tasks.md with a resolvable checkbox."""
    (tmp_path / ".kittify").mkdir(exist_ok=True)
    feature_dir = tmp_path / "kitty-specs" / mission_slug
    (feature_dir / "tasks").mkdir(parents=True, exist_ok=True)
    (feature_dir / "meta.json").write_text(
        json.dumps({"mission_slug": mission_slug, "mission_type": "software-dev"}),
        encoding="utf-8",
    )
    (feature_dir / "tasks.md").write_text(
        "# Tasks\n\n## WP01\n\n- [ ] T001 Do the thing\n",
        encoding="utf-8",
    )
    return feature_dir


def _build_finalize_fixture(tmp_path: Path, mission_slug: str) -> Path:
    """Primary planning surface: meta.json + tasks.md + one WP frontmatter file."""
    (tmp_path / ".kittify").mkdir(exist_ok=True)
    feature_dir = tmp_path / "kitty-specs" / mission_slug
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "meta.json").write_text(
        json.dumps({"mission_slug": mission_slug, "mission_type": "software-dev"}),
        encoding="utf-8",
    )
    (feature_dir / "tasks.md").write_text(
        "# Tasks\n\n## WP01\n\nNo explicit dependencies.\n",
        encoding="utf-8",
    )
    (tasks_dir / "WP01-test.md").write_text(
        "---\nwork_package_id: WP01\ntitle: Test WP01\nexecution_mode: code_change\n---\n# WP01\n",
        encoding="utf-8",
    )
    return feature_dir


# ===========================================================================
# T033 — mark_status: TASKS_INDEX read + commit routing, coreless
# ===========================================================================


def test_mark_status_read_dir_routes_through_fs_port_tasks_index(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """T033: the tasks.md write surface resolves via ``FsReader.planning_read_dir``
    keyed ``TASKS_INDEX`` (#2154), and a ``--no-auto-commit`` run never touches the
    coord ``commit_artifact`` seam."""
    feature_dir = _build_mark_fixture(tmp_path, _MISSION)
    ports, fs, coord = _fake_ports(feature_dir, MissionArtifactKind.TASKS_INDEX)

    with setup_mocked_env(tmp_path, mission_slug=_MISSION, target_branch="wip-lane"), patch(
        "specify_cli.cli.commands.agent.tasks.emit_history_added"
    ):
        _do_mark_status(
            task_ids=["T001"],
            status="done",
            mission=_MISSION,
            auto_commit=False,
            json_output=True,
            ports=ports,
        )

    # The write surface resolved through the kind-aware FsReader port (#2154).
    assert ("planning_read_dir", MissionArtifactKind.TASKS_INDEX) in fs.calls
    # No auto-commit => the coord WRITE capability is untouched.
    assert coord.artifact_calls == []
    # The checkbox row was durably flipped on disk.
    assert "- [x] T001" in (feature_dir / "tasks.md").read_text(encoding="utf-8")

    payload = json.loads(capsys.readouterr().out)
    assert payload["summary"]["updated"] == 1


def test_mark_status_auto_commit_routes_via_commit_artifact_tasks_index(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """T033: an auto-commit run routes the tasks.md commit through the coord
    ``commit_artifact`` capability, keyed ``TASKS_INDEX`` with the tasks.md file."""
    feature_dir = _build_mark_fixture(tmp_path, _MISSION)
    ports, _fs, coord = _fake_ports(feature_dir, MissionArtifactKind.TASKS_INDEX)

    with setup_mocked_env(
        tmp_path,
        mission_slug=_MISSION,
        target_branch="wip-lane",
        auto_commit_default=True,
        # The protected-primary guard is orthogonal to the commit ROUTING under test.
        extra_patches={"_protected_branch_status_commit_error": None},
    ), patch("specify_cli.cli.commands.agent.tasks.emit_history_added"):
        _do_mark_status(
            task_ids=["T001"],
            status="done",
            mission=_MISSION,
            auto_commit=True,
            json_output=True,
            ports=ports,
        )

    assert len(coord.artifact_calls) == 1
    slug, paths, message, kind = coord.artifact_calls[0]
    assert slug == _MISSION
    assert kind == MissionArtifactKind.TASKS_INDEX
    assert (feature_dir / "tasks.md").resolve() in paths
    assert message.startswith("chore: Mark T001 as done")
    capsys.readouterr()


def test_mark_status_coord_router_binds_module_commit_without_target_branch() -> None:
    """T033: the production mark_status coord router re-resolves ``commit_for_mission``
    through THIS module (so the ``@patch`` seam intercepts) and does NOT thread a
    ``target_branch`` — byte-parity with the pre-rewire inline mark_status call.

    (constructor-DI collapse: built via ``seam_coord_router()`` rather than the
    deleted ``_MarkStatusCoordRouter`` subclass.)"""
    router = seam_coord_router()
    handle = MissionHandle(repo_root=Path("/repo"), mission_slug=_MISSION)

    with patch("specify_cli.cli.commands.agent.tasks.commit_for_mission") as mock_commit:
        mock_commit.return_value.status = "committed"
        mock_commit.return_value.placement_ref = "primary"
        mock_commit.return_value.commit_hash = "0" * 40
        mock_commit.return_value.diagnostic = None
        result = router.commit_artifact(
            handle,
            [Path("kitty-specs/m/tasks.md")],
            "chore: Mark T001 as done on spec 001",
            kind=MissionArtifactKind.TASKS_INDEX,
            policy=ProtectionPolicy(protected_branches=frozenset(), operator_hatch_active=False),
        )

    assert result.status == "committed"
    assert mock_commit.call_args.kwargs["kind"] == MissionArtifactKind.TASKS_INDEX
    # The mark_status commit leg is target-branch-less (parity with the old inline call).
    assert "target_branch" not in mock_commit.call_args.kwargs


def test_mark_status_refuses_exit_1_on_protected_auto_commit(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """T033 / T005 (deferred #2300): under auto-commit on a protected target,
    mark_status REFUSES (exit 1) — the divergence from move_task's skip is preserved
    by the coreless orchestrator, not reconciled."""
    feature_dir = _build_mark_fixture(tmp_path, _MISSION)
    ports, _fs, coord = _fake_ports(feature_dir, MissionArtifactKind.TASKS_INDEX)

    protected_msg = "Cannot auto-commit status change: 'main' is a protected branch"
    with setup_mocked_env(
        tmp_path,
        mission_slug=_MISSION,
        target_branch="main",
        auto_commit_default=True,
        extra_patches={"_protected_branch_status_commit_error": protected_msg},
    ), pytest.raises(typer.Exit) as exc:
        _do_mark_status(
            task_ids=["T001"],
            status="done",
            mission=_MISSION,
            auto_commit=True,
            json_output=False,
            ports=ports,
        )

    assert exc.value.exit_code == 1
    assert "protected branch" in capsys.readouterr().out
    # Refused BEFORE any mutation: neither the tasks.md write nor the commit fired.
    assert "- [x] T001" not in (feature_dir / "tasks.md").read_text(encoding="utf-8")
    assert coord.artifact_calls == []


# ===========================================================================
# T034 / T035 — finalize_tasks: WORK_PACKAGE_TASK guard fold, coreless
# ===========================================================================


def test_finalize_tasks_guard_read_routes_through_fs_port_work_package_task(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """T034/T035 (FR-010): the pre30-guard read resolves through the
    ``FsReader.planning_read_dir`` port keyed ``WORK_PACKAGE_TASK`` — migrated off the
    kind-blind coord-husk resolver, byte-identically per the WP02 T013 proof."""
    feature_dir = _build_finalize_fixture(tmp_path, _MISSION)
    ports, fs, _coord = _fake_ports(feature_dir, MissionArtifactKind.WORK_PACKAGE_TASK)

    fake_bootstrap = BootstrapResult(
        total_wps=1, already_initialized=0, newly_seeded=1, skipped=0, wp_details=[]
    )
    with setup_mocked_env(tmp_path, mission_slug=_MISSION, target_branch="wip-lane"), patch(
        "specify_cli.cli.commands.agent.tasks.bootstrap_canonical_state",
        return_value=fake_bootstrap,
    ):
        _do_finalize_tasks(
            mission=_MISSION,
            json_output=True,
            validate_only=True,
            ports=ports,
        )

    # The FR-010 fold: the guard/parse read routed through the kind-aware port.
    assert ("planning_read_dir", MissionArtifactKind.WORK_PACKAGE_TASK) in fs.calls
    # The kind-blind coord-husk resolver is NOT used for the guard leg anymore.
    assert ("planning_read_dir", MissionArtifactKind.STATUS_STATE) not in fs.calls

    payload = json.loads(capsys.readouterr().out)
    assert payload["result"] == "validation_passed"


def test_finalize_tasks_validate_only_skips_frontmatter_write(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """T034: ``--validate-only`` computes the plan but writes no WP frontmatter
    (the write is gated on ``validate_only``, coreless — no decision core)."""
    feature_dir = _build_finalize_fixture(tmp_path, _MISSION)
    ports, _fs, _coord = _fake_ports(feature_dir, MissionArtifactKind.WORK_PACKAGE_TASK)
    wp_file = feature_dir / "tasks" / "WP01-test.md"
    before = wp_file.read_text(encoding="utf-8")

    fake_bootstrap = BootstrapResult(
        total_wps=1, already_initialized=1, newly_seeded=0, skipped=0, wp_details=[]
    )
    with setup_mocked_env(tmp_path, mission_slug=_MISSION, target_branch="wip-lane"), patch(
        "specify_cli.cli.commands.agent.tasks.bootstrap_canonical_state",
        return_value=fake_bootstrap,
    ):
        _do_finalize_tasks(
            mission=_MISSION, json_output=True, validate_only=True, ports=ports
        )

    assert wp_file.read_text(encoding="utf-8") == before
    capsys.readouterr()


# ===========================================================================
# T036 — structural non-import AST gate (guards the #2300 boundary)
# ===========================================================================


def _module_tree(module: ModuleType = tasks_mod) -> ast.Module:
    module_file = module.__file__
    assert isinstance(module_file, str)
    return ast.parse(Path(module_file).read_text(encoding="utf-8"))


def _transition_core_symbols(tree: ast.Module) -> set[str]:
    """Every name imported from ``tasks_transition_core`` (derived live from source)."""
    syms: set[str] = set()
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.ImportFrom)
            and node.module
            and node.module.endswith("tasks_transition_core")
        ):
            for alias in node.names:
                syms.add(alias.asname or alias.name)
    return syms


def _module_functions(tree: ast.Module) -> dict[str, ast.FunctionDef]:
    return {n.name: n for n in tree.body if isinstance(n, ast.FunctionDef)}


def _referenced_names(fn: ast.FunctionDef) -> set[str]:
    return {n.id for n in ast.walk(fn) if isinstance(n, ast.Name)}


def _reachable_closure(
    funcs: dict[str, ast.FunctionDef], entry_names: list[str]
) -> set[str]:
    """Transitive closure of module-level FunctionDefs reachable from *entry_names*.

    An edge ``f -> g`` exists when ``f`` references a module-level function name ``g``
    (bare-``Name`` reference). This over-approximates reachability (safe direction:
    it would only find MORE core references, never fewer), keeping the "coreless"
    assertion strict.
    """
    seen: set[str] = set()
    stack = list(entry_names)
    while stack:
        name = stack.pop()
        if name in seen or name not in funcs:
            continue
        seen.add(name)
        for ref in _referenced_names(funcs[name]):
            if ref in funcs and ref not in seen:
                stack.append(ref)
    return seen


def _has_local_core_import(fn: ast.FunctionDef) -> bool:
    """True when *fn* contains a function-local ``from ...tasks_transition_core import``."""
    return any(
        isinstance(node, ast.ImportFrom)
        and node.module is not None
        and node.module.endswith("tasks_transition_core")
        for node in ast.walk(fn)
    )


def _path_reaches_core(
    entry_names: list[str], module: ModuleType = tasks_mod
) -> tuple[set[str], bool]:
    """Return ``(leaked_symbols, has_local_import)`` for a command's code path."""
    tree = _module_tree(module)
    funcs = _module_functions(tree)
    core_syms = _transition_core_symbols(tree)
    assert core_syms, "the tasks_transition_core import must exist (gate would be vacuous)"
    closure = _reachable_closure(funcs, entry_names)
    refs: set[str] = set()
    local_import = False
    for name in closure:
        refs |= _referenced_names(funcs[name])
        local_import = local_import or _has_local_core_import(funcs[name])
    return refs & core_syms, local_import


def test_mark_status_path_does_not_reach_transition_core() -> None:
    """T036: no ``tasks_transition_core`` symbol is reachable from ``mark_status``.

    Guards the deferred #2300 boundary STRUCTURALLY: an implementer cannot route
    ``mark_status`` through ``move_task``'s ``decide_transition`` core (then special-
    case the exit code back to 1) to hit ≤150 LOC — behaviour parity alone would miss
    that; this AST reachability check makes it CI-red.
    """
    leaked, local_import = _path_reaches_core(["mark_status", "_do_mark_status"])
    assert leaked == set(), f"mark_status reaches the transition core: {sorted(leaked)}"
    assert not local_import, "mark_status path smuggles a function-local core import"


def test_finalize_tasks_path_does_not_reach_transition_core() -> None:
    """T036: no ``tasks_transition_core`` symbol is reachable from ``finalize_tasks``."""
    leaked, local_import = _path_reaches_core(["finalize_tasks", "_do_finalize_tasks"])
    assert leaked == set(), f"finalize_tasks reaches the transition core: {sorted(leaked)}"
    assert not local_import, "finalize_tasks path smuggles a function-local core import"


def test_ast_gate_is_not_vacuous_move_task_control() -> None:
    """T036 (non-tautological control): the SAME gate proves ``move_task``'s path DOES
    reach the transition core.

    Without this control, a broken scanner that never resolves edges would pass the
    two coreless assertions vacuously. ``move_task`` is core-BACKED (WP03), so its
    closure MUST reference a ``tasks_transition_core`` symbol (e.g. ``decide_transition``).

    WP05 re-pin (tasks-py-degod-wave2-01KWH9EQ): the core-backed path
    (``_do_move_task`` + the ``_mt_*`` phase helpers) relocated VERBATIM to
    ``tasks_move_task.py``, so the closure is resolved over THAT module — the
    ``tasks.py`` wrapper is a thin delegate whose callee is a re-import (not a
    module-level ``FunctionDef``), invisible to this scanner by design. The
    relocated ``_mt_run_decision`` reaches the core via the ``_tasks.<attr>``
    seam bridge, so ``decide_transition`` shows up as a routed reference on the
    ``tasks`` namespace; the module's own ``tasks_transition_core`` imports
    (``MoveTaskRequest``, ``RefuseExit1``, ``build_transition_plan``, …) keep
    the leak detectable.
    """
    from specify_cli.cli.commands.agent import tasks_move_task as tasks_move_task_mod

    leaked, _local = _path_reaches_core(
        ["_do_move_task"], module=tasks_move_task_mod
    )
    assert leaked, (
        "gate is vacuous — it cannot detect the real transition-core reference in "
        "move_task's core-backed path; the coreless assertions would pass falsely"
    )
