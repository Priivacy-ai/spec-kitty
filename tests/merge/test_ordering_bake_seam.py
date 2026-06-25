"""Seam test for the relocated mission-number bake cluster (mission #2057, WP07).

Covers the bake orchestrator's short-circuits (already-baked, non-git-repo,
no-op-on-target, dry-run) and the helper predicates, and proves the shim
re-exports ``_bake_mission_number_into_mission_branch`` and that the bake
cluster keeps its lazy imports lazy (C-007) without reaching back into the shim
(INV-2).
"""

from __future__ import annotations

from pathlib import Path
from subprocess import CompletedProcess
from unittest.mock import patch

import pytest

from specify_cli.cli.commands import merge as shim
from specify_cli.merge import ordering
from specify_cli.merge.state import MergeState

pytestmark = pytest.mark.fast


def _state(baked: bool = False) -> MergeState:
    s = MergeState(mission_id="01ID", mission_slug="m", target_branch="main", wp_order=["WP01"])
    s.mission_number_baked = baked
    return s


def test_shim_re_exports_bake_entrypoint() -> None:
    assert shim._bake_mission_number_into_mission_branch is ordering._bake_mission_number_into_mission_branch


def test_ordering_does_not_import_command_shim() -> None:
    import ast
    import inspect

    tree = ast.parse(inspect.getsource(ordering))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
        elif isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
    assert not any(
        m.startswith("specify_cli.cli.commands.merge") for m in modules
    ), sorted(modules)


def test_lazy_imports_stay_lazy() -> None:
    """C-007/INV-7: heavy / cycle-prone deps are imported inside functions, not at module top."""
    import ast
    import inspect

    tree = ast.parse(inspect.getsource(ordering))
    top_level_modules = {
        node.module
        for node in tree.body
        if isinstance(node, ast.ImportFrom) and node.module
    }
    # These must NOT be hoisted to module top (would risk import cycles).
    assert "specify_cli.missions._read_path_resolver" not in top_level_modules
    assert not any(m.startswith("specify_cli.lanes") for m in top_level_modules)


# --- _already_baked ---------------------------------------------------------


def test_already_baked() -> None:
    assert ordering._already_baked(_state(baked=True)) is True
    assert ordering._already_baked(_state(baked=False)) is False
    assert ordering._already_baked(None) is False


# --- _is_assigned_mission_number --------------------------------------------


@pytest.mark.parametrize(
    ("value", "expected"),
    [(5, True), (0, True), (True, False), (False, False), (None, False), ("3", False)],
)
def test_is_assigned_mission_number(value: object, expected: bool) -> None:
    assert ordering._is_assigned_mission_number(value) is expected


# --- _mark_mission_number_baked ---------------------------------------------


def test_mark_mission_number_baked_persists(tmp_path: Path) -> None:
    saved: list[MergeState] = []
    state = _state(baked=False)
    with patch("specify_cli.merge.state.save_state", side_effect=lambda s, _r: saved.append(s)):
        ordering._mark_mission_number_baked(state, tmp_path)
    assert state.mission_number_baked is True
    assert saved == [state]


def test_mark_mission_number_baked_noop_for_none(tmp_path: Path) -> None:
    # Should not raise / not attempt to save when state is None.
    ordering._mark_mission_number_baked(None, tmp_path)


# --- _bake_mission_number_into_mission_branch short-circuits ----------------


def test_bake_short_circuits_when_already_baked(tmp_path: Path) -> None:
    result = ordering._bake_mission_number_into_mission_branch(
        tmp_path, "m", "kitty/mission-m", "main", merge_state=_state(baked=True)
    )
    assert result is None


def test_bake_short_circuits_when_not_git_repo(tmp_path: Path) -> None:
    with patch.object(ordering, "_is_git_repo", return_value=False):
        result = ordering._bake_mission_number_into_mission_branch(
            tmp_path, "m", "kitty/mission-m", "main", merge_state=_state()
        )
    assert result is None


def test_bake_returns_none_when_target_already_assigned(tmp_path: Path) -> None:
    with (
        patch.object(ordering, "_is_git_repo", return_value=True),
        patch.object(ordering, "_compute_next_mission_number_or_none", return_value=None),
    ):
        result = ordering._bake_mission_number_into_mission_branch(
            tmp_path, "m", "kitty/mission-m", "main", merge_state=_state()
        )
    assert result is None


def test_bake_dry_run_logs_without_write(tmp_path: Path) -> None:
    with (
        patch.object(ordering, "_is_git_repo", return_value=True),
        patch.object(ordering, "_compute_next_mission_number_or_none", return_value=7),
        patch.object(ordering, "_write_mission_number_to_branch") as write_mock,
    ):
        result = ordering._bake_mission_number_into_mission_branch(
            tmp_path, "m", "kitty/mission-m", "main", dry_run=True, merge_state=_state()
        )
    assert result is None
    write_mock.assert_not_called()


def test_bake_writes_and_marks_baked_on_success(tmp_path: Path) -> None:
    marked: list[bool] = []
    state = _state()
    with (
        patch.object(ordering, "_is_git_repo", return_value=True),
        patch.object(ordering, "_compute_next_mission_number_or_none", return_value=9),
        patch.object(ordering, "_write_mission_number_to_branch", return_value=True),
        patch.object(ordering, "_mark_mission_number_baked", side_effect=lambda *_a: marked.append(True)),
    ):
        result = ordering._bake_mission_number_into_mission_branch(
            tmp_path, "m", "kitty/mission-m", "main", merge_state=state
        )
    assert result == 9
    assert marked == [True]


def test_bake_returns_none_when_write_skipped(tmp_path: Path) -> None:
    with (
        patch.object(ordering, "_is_git_repo", return_value=True),
        patch.object(ordering, "_compute_next_mission_number_or_none", return_value=9),
        patch.object(ordering, "_write_mission_number_to_branch", return_value=False),
    ):
        result = ordering._bake_mission_number_into_mission_branch(
            tmp_path, "m", "kitty/mission-m", "main", merge_state=_state()
        )
    assert result is None


# --- _write_mission_number_to_branch: missing-branch early return -----------


def test_write_skips_when_branch_missing(tmp_path: Path) -> None:
    with patch.object(ordering, "_has_branch_ref", return_value=False):
        assert ordering._write_mission_number_to_branch(
            tmp_path, "kitty/mission-m", "m", 3, _state()
        ) is False


# --- _assign_planning_only_mission_number_if_needed -------------------------


def test_planning_only_assignment_noop_when_not_needed(tmp_path: Path) -> None:
    with patch("specify_cli.merge.state.needs_number_assignment", return_value=False):
        assert ordering._assign_planning_only_mission_number_if_needed(tmp_path, tmp_path) is None


def test_planning_only_assignment_writes_meta(tmp_path: Path) -> None:
    feature_dir = tmp_path / "kitty-specs" / "m"
    feature_dir.mkdir(parents=True)
    written: list[dict[str, object]] = []
    with (
        patch("specify_cli.merge.state.needs_number_assignment", return_value=True),
        patch.object(ordering, "assign_next_mission_number", return_value=4),
        patch.object(ordering, "load_meta", return_value={"mission_slug": "m"}),
        patch.object(ordering, "write_meta", side_effect=lambda _d, meta, **_k: written.append(meta)),
    ):
        result = ordering._assign_planning_only_mission_number_if_needed(tmp_path, feature_dir)
    assert result == feature_dir / "meta.json"
    assert written[0]["mission_number"] == 4


def test_planning_only_assignment_writes_meta_when_load_returns_none(tmp_path: Path) -> None:
    """load_meta returning None must still produce a fresh meta dict (the ``or {}``)."""
    feature_dir = tmp_path / "kitty-specs" / "m"
    feature_dir.mkdir(parents=True)
    written: list[dict[str, object]] = []
    with (
        patch("specify_cli.merge.state.needs_number_assignment", return_value=True),
        patch.object(ordering, "assign_next_mission_number", return_value=2),
        patch.object(ordering, "load_meta", return_value=None),
        patch.object(ordering, "write_meta", side_effect=lambda _d, meta, **_k: written.append(meta)),
    ):
        result = ordering._assign_planning_only_mission_number_if_needed(tmp_path, feature_dir)
    assert result == feature_dir / "meta.json"
    assert written[0] == {"mission_number": 2}


# --- has_dependency_info ----------------------------------------------------


def test_has_dependency_info() -> None:
    assert ordering.has_dependency_info({"WP01": ["WP02"], "WP02": []}) is True
    assert ordering.has_dependency_info({"WP01": [], "WP02": []}) is False
    assert ordering.has_dependency_info({}) is False


# --- get_merge_order --------------------------------------------------------


def _ws(wp_id: str) -> tuple[Path, str, str]:
    return (Path(f"/wt/{wp_id}"), wp_id, f"kitty/{wp_id}")


def test_get_merge_order_empty_returns_empty(tmp_path: Path) -> None:
    assert ordering.get_merge_order([], tmp_path) == []


def test_get_merge_order_no_deps_falls_back_to_numeric(tmp_path: Path) -> None:
    workspaces = [_ws("WP02"), _ws("WP01")]
    with patch.object(ordering, "build_dependency_graph", return_value={"WP01": [], "WP02": []}):
        result = ordering.get_merge_order(workspaces, tmp_path)
    assert [wp for _, wp, _ in result] == ["WP01", "WP02"]


def test_get_merge_order_topo_sorts_dependencies_first(tmp_path: Path) -> None:
    workspaces = [_ws("WP02"), _ws("WP01")]
    # WP02 depends on WP01 -> WP01 must come first.
    with patch.object(ordering, "build_dependency_graph", return_value={"WP01": [], "WP02": ["WP01"]}):
        result = ordering.get_merge_order(workspaces, tmp_path)
    assert [wp for _, wp, _ in result] == ["WP01", "WP02"]


def test_get_merge_order_raises_on_cycle(tmp_path: Path) -> None:
    workspaces = [_ws("WP01"), _ws("WP02")]
    with (
        patch.object(ordering, "build_dependency_graph", return_value={"WP01": ["WP02"], "WP02": ["WP01"]}),
        pytest.raises(ordering.MergeOrderError, match="Circular dependency"),
    ):
        ordering.get_merge_order(workspaces, tmp_path)


def test_get_merge_order_wraps_topological_value_error(tmp_path: Path) -> None:
    workspaces = [_ws("WP01")]
    with (
        patch.object(ordering, "build_dependency_graph", return_value={"WP01": ["WP02"]}),
        patch.object(ordering, "detect_cycles", return_value=[]),
        patch.object(ordering, "topological_sort", side_effect=ValueError("bad graph")),
        pytest.raises(ordering.MergeOrderError, match="bad graph"),
    ):
        ordering.get_merge_order(workspaces, tmp_path)


# --- display_merge_order ----------------------------------------------------


def test_display_merge_order_empty_is_noop() -> None:
    printed: list[str] = []
    fake_console = type("C", (), {"print": lambda self, *a: printed.append(" ".join(map(str, a)))})()
    ordering.display_merge_order([], fake_console)
    assert printed == []


def test_display_merge_order_lists_workspaces() -> None:
    printed: list[str] = []
    fake_console = type("C", (), {"print": lambda self, *a: printed.append(" ".join(map(str, a)))})()
    ordering.display_merge_order([_ws("WP01"), _ws("WP02")], fake_console)
    joined = "\n".join(printed)
    assert "WP01" in joined and "WP02" in joined


# --- _compute_next_mission_number_or_none -----------------------------------


def test_compute_next_falls_back_when_worktree_add_fails(tmp_path: Path) -> None:
    """git worktree add failure -> fall back to scanning main_repo (lines 286-292)."""
    def _fake_run(args: list[str], **kwargs: object) -> CompletedProcess[str]:
        if args[:3] == ["git", "worktree", "add"]:
            return CompletedProcess(args, 1, stdout="", stderr="cannot add worktree")
        return CompletedProcess(args, 0, stdout="", stderr="")

    with (
        patch("subprocess.run", side_effect=_fake_run),
        patch.object(ordering, "assign_next_mission_number", return_value=11) as assign_mock,
    ):
        result = ordering._compute_next_mission_number_or_none(tmp_path, "m", "main")
    assert result == 11
    # Fallback scanned main_repo, not a tmp worktree.
    assert assign_mock.call_args.args[0] == tmp_path


def test_compute_next_returns_none_when_target_already_assigned(tmp_path: Path) -> None:
    """meta.json on target already carries an integer -> no-op None (lines 299-308)."""
    import json as _json

    def _fake_run(args: list[str], **kwargs: object) -> CompletedProcess[str]:
        if args[:3] == ["git", "worktree", "add"]:
            # Materialise the scan worktree's target meta.json.
            scan_root = Path(args[4])
            specs = scan_root / "kitty-specs" / "m"
            specs.mkdir(parents=True, exist_ok=True)
            (specs / "meta.json").write_text(_json.dumps({"mission_number": 5}), encoding="utf-8")
            return CompletedProcess(args, 0, stdout="", stderr="")
        return CompletedProcess(args, 0, stdout="", stderr="")

    with patch("subprocess.run", side_effect=_fake_run):
        result = ordering._compute_next_mission_number_or_none(tmp_path, "m", "main")
    assert result is None


# --- _write_mission_number_to_branch: error/cleanup branches ----------------


def test_write_skips_when_worktree_add_fails(tmp_path: Path) -> None:
    """git worktree add failure on the write path -> False (lines 357-363)."""
    def _fake_run(args: list[str], **kwargs: object) -> CompletedProcess[str]:
        if args[:3] == ["git", "worktree", "add"]:
            return CompletedProcess(args, 1, stdout="", stderr="add failed")
        return CompletedProcess(args, 0, stdout="", stderr="")

    with (
        patch.object(ordering, "_has_branch_ref", return_value=True),
        patch("subprocess.run", side_effect=_fake_run),
    ):
        assert ordering._write_mission_number_to_branch(
            tmp_path, "kitty/mission-m", "m", 3, _state()
        ) is False


def test_write_skips_when_meta_missing(tmp_path: Path) -> None:
    """meta.json absent on the mission branch worktree -> False (lines 385-391)."""
    def _fake_run(args: list[str], **kwargs: object) -> CompletedProcess[str]:
        return CompletedProcess(args, 0, stdout="", stderr="")

    with (
        patch.object(ordering, "_has_branch_ref", return_value=True),
        patch.object(ordering, "path_is_under_worktrees", return_value=False),
        patch("subprocess.run", side_effect=_fake_run),
    ):
        # The composed meta path under the tmp scan worktree never exists.
        assert ordering._write_mission_number_to_branch(
            tmp_path, "kitty/mission-m", "m", 3, _state()
        ) is False


def test_write_refuses_when_meta_path_under_worktrees(tmp_path: Path) -> None:
    """Resolved meta path under .worktrees/ -> refuse to bake (lines 377-384)."""
    def _fake_run(args: list[str], **kwargs: object) -> CompletedProcess[str]:
        return CompletedProcess(args, 0, stdout="", stderr="")

    with (
        patch.object(ordering, "_has_branch_ref", return_value=True),
        patch.object(ordering, "path_is_under_worktrees", return_value=True),
        patch("subprocess.run", side_effect=_fake_run),
        patch(
            "specify_cli.missions._read_path_resolver.compose_meta_json_path",
            side_effect=lambda wt, slug: wt / ".worktrees" / "m-coord" / "meta.json",
        ),
    ):
        assert ordering._write_mission_number_to_branch(
            tmp_path, "kitty/mission-m", "m", 3, _state()
        ) is False


def test_write_refuses_when_meta_not_a_dict(tmp_path: Path) -> None:
    """meta.json is a JSON list, not an object -> refuse (lines 395-399)."""
    import json as _json

    def _fake_run(args: list[str], **kwargs: object) -> CompletedProcess[str]:
        if args[:3] == ["git", "worktree", "add"]:
            scan_root = Path(args[4])
            specs = scan_root / "kitty-specs" / "m"
            specs.mkdir(parents=True, exist_ok=True)
            (specs / "meta.json").write_text(_json.dumps(["not", "a", "dict"]), encoding="utf-8")
            return CompletedProcess(args, 0, stdout="", stderr="")
        return CompletedProcess(args, 0, stdout="", stderr="")

    with (
        patch.object(ordering, "_has_branch_ref", return_value=True),
        patch.object(ordering, "path_is_under_worktrees", return_value=False),
        patch("subprocess.run", side_effect=_fake_run),
        patch(
            "specify_cli.missions._read_path_resolver.compose_meta_json_path",
            side_effect=lambda wt, slug: wt / "kitty-specs" / slug / "meta.json",
        ),
    ):
        assert ordering._write_mission_number_to_branch(
            tmp_path, "kitty/mission-m", "m", 3, _state()
        ) is False


def test_write_idempotency_hit_marks_baked_returns_false(tmp_path: Path) -> None:
    """meta already has the exact number -> idempotency skip + mark baked (lines 402-414)."""
    import json as _json

    def _fake_run(args: list[str], **kwargs: object) -> CompletedProcess[str]:
        if args[:3] == ["git", "worktree", "add"]:
            scan_root = Path(args[4])
            specs = scan_root / "kitty-specs" / "m"
            specs.mkdir(parents=True, exist_ok=True)
            (specs / "meta.json").write_text(_json.dumps({"mission_number": 9}), encoding="utf-8")
            return CompletedProcess(args, 0, stdout="", stderr="")
        return CompletedProcess(args, 0, stdout="", stderr="")

    marked: list[bool] = []
    with (
        patch.object(ordering, "_has_branch_ref", return_value=True),
        patch.object(ordering, "path_is_under_worktrees", return_value=False),
        patch("subprocess.run", side_effect=_fake_run),
        patch.object(ordering, "_mark_mission_number_baked", side_effect=lambda *_a: marked.append(True)),
        patch(
            "specify_cli.missions._read_path_resolver.compose_meta_json_path",
            side_effect=lambda wt, slug: wt / "kitty-specs" / slug / "meta.json",
        ),
    ):
        result = ordering._write_mission_number_to_branch(
            tmp_path, "kitty/mission-m", "m", 9, _state()
        )
    assert result is False
    assert marked == [True]
