"""Seam test for ``specify_cli.merge.resolve`` (mission #2057, WP04).

Covers slug extraction, merge-state key-candidate ordering, state load/clear/
cleanup, and target-branch resolution. Proves the command shim re-exports the
test-imported resolvers and enforces one-way imports (FR-006, C-002, INV-2).
The state-key candidate ORDER (modern ULID before legacy slug) is locked.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from specify_cli.cli.commands import merge as shim
from specify_cli.merge import resolve
from specify_cli.merge.state import MergeState

pytestmark = pytest.mark.fast


# --- Re-export / one-way-import contract ------------------------------------

SHIM_REEXPORTED = [
    "_resolve_mission_slug",
    "_resolve_target_branch",
    "_load_merge_state_for_mission",
    "_load_merge_state_entry_for_mission",
    "_load_or_create_merge_state",
    "_clear_merge_state_for_mission",
    "_cleanup_merge_workspaces_for_state",
]


@pytest.mark.parametrize("name", SHIM_REEXPORTED)
def test_shim_re_exports_the_same_object(name: str) -> None:
    assert getattr(shim, name) is getattr(resolve, name)


def test_resolve_does_not_import_the_command_shim() -> None:
    import ast
    import inspect

    tree = ast.parse(inspect.getsource(resolve))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
        elif isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
    assert not any(
        m.startswith("specify_cli.cli.commands.merge") for m in modules
    ), sorted(modules)


# --- _extract_mission_slug --------------------------------------------------


def test_extract_mission_slug_legacy_nnn_and_lane() -> None:
    assert resolve._extract_mission_slug("017-smarter-feature-merge") == "017-smarter-feature-merge"
    assert resolve._extract_mission_slug("017-smarter-feature-merge-lane-a") == "017-smarter-feature-merge"
    assert resolve._extract_mission_slug("totally-unparseable!!") is None


# --- _merge_state_key_candidates (ORDER is locked) --------------------------


def test_key_candidates_empty_for_no_slug() -> None:
    assert resolve._merge_state_key_candidates(Path("/r"), None) == []


def test_key_candidates_ulid_before_slug(tmp_path: Path) -> None:
    """Modern ULID key precedes the legacy slug key; duplicates collapsed."""
    feature_dir = tmp_path / "kitty-specs" / "my-mission"
    feature_dir.mkdir(parents=True)

    class _Identity:
        mission_id = "01ABCDEF000000000000000000"

    with (
        patch.object(resolve, "candidate_feature_dir_for_mission", return_value=feature_dir),
        patch.object(resolve, "get_main_repo_root", return_value=tmp_path),
        patch.object(resolve, "resolve_mission_identity", return_value=_Identity()),
    ):
        keys = resolve._merge_state_key_candidates(tmp_path, "my-mission")
    assert keys == ["01ABCDEF000000000000000000", "my-mission"]


def test_key_candidates_slug_only_when_no_identity(tmp_path: Path) -> None:
    with (
        patch.object(resolve, "candidate_feature_dir_for_mission", side_effect=RuntimeError("boom")),
        patch.object(resolve, "get_main_repo_root", return_value=tmp_path),
    ):
        keys = resolve._merge_state_key_candidates(tmp_path, "my-mission")
    assert keys == ["my-mission"]


# --- _load_merge_state_entry_for_mission ------------------------------------


def _state(slug: str = "m", mid: str = "01ID") -> MergeState:
    return MergeState(mission_id=mid, mission_slug=slug, target_branch="main", wp_order=["WP01"])


def test_load_entry_no_slug_uses_default_state() -> None:
    st = _state()
    with patch.object(resolve, "load_state", return_value=st):
        assert resolve._load_merge_state_entry_for_mission(Path("/r"), None) == (None, st)
    with patch.object(resolve, "load_state", return_value=None):
        assert resolve._load_merge_state_entry_for_mission(Path("/r"), None) is None


def test_load_entry_returns_first_matching_key(tmp_path: Path) -> None:
    st = _state(mid="01ULID")
    with (
        patch.object(resolve, "_merge_state_key_candidates", return_value=["01ULID", "m"]),
        patch.object(resolve, "load_state", side_effect=lambda _r, k=None: st if k == "01ULID" else None),
    ):
        key, state = resolve._load_merge_state_entry_for_mission(tmp_path, "m")
    assert key == "01ULID"
    assert state is st


def test_load_state_for_mission_unwraps_entry() -> None:
    st = _state()
    with patch.object(resolve, "_load_merge_state_entry_for_mission", return_value=("k", st)):
        assert resolve._load_merge_state_for_mission(Path("/r"), "m") is st
    with patch.object(resolve, "_load_merge_state_entry_for_mission", return_value=None):
        assert resolve._load_merge_state_for_mission(Path("/r"), "m") is None


# --- _load_or_create_merge_state --------------------------------------------


def test_load_or_create_returns_existing_canonical() -> None:
    st = _state(mid="01CANON")
    with patch.object(resolve, "load_state", return_value=st):
        result, existed = resolve._load_or_create_merge_state(
            main_repo=Path("/r"), mission_slug="m", canonical_id="01CANON",
            target_branch="main", wp_order=["WP01"], push_requested=False,
        )
    assert result is st and existed is True


def test_load_or_create_creates_new_when_absent() -> None:
    saved: list[MergeState] = []
    with (
        patch.object(resolve, "load_state", return_value=None),
        patch.object(resolve, "_load_merge_state_entry_for_mission", return_value=None),
        patch.object(resolve, "save_state", side_effect=lambda s, _r: saved.append(s)),
    ):
        result, existed = resolve._load_or_create_merge_state(
            main_repo=Path("/r"), mission_slug="m", canonical_id="01NEW",
            target_branch="main", wp_order=["WP01"], push_requested=True,
        )
    assert existed is False
    assert result.mission_id == "01NEW"
    assert result.push_requested is True
    assert saved == [result]


def test_load_or_create_migrates_legacy_state() -> None:
    legacy = _state(mid="01LEGACY")
    cleared: list[str] = []
    with (
        patch.object(resolve, "load_state", return_value=None),
        patch.object(resolve, "_load_merge_state_entry_for_mission", return_value=("01LEGACY", legacy)),
        patch.object(resolve, "save_state", lambda *a, **k: None),
        patch.object(resolve, "clear_state", side_effect=lambda _r, k: cleared.append(k)),
    ):
        result, existed = resolve._load_or_create_merge_state(
            main_repo=Path("/r"), mission_slug="m", canonical_id="01CANON",
            target_branch="main", wp_order=["WP01"], push_requested=False,
        )
    assert existed is True
    assert result.mission_id == "01CANON"
    assert cleared == ["01LEGACY"]


# --- _clear_merge_state_for_mission -----------------------------------------


def test_clear_state_no_slug_clears_default() -> None:
    with patch.object(resolve, "clear_state", return_value=True) as m:
        assert resolve._clear_merge_state_for_mission(Path("/r"), None) is True
    m.assert_called_once_with(Path("/r"))


def test_clear_state_clears_all_candidate_keys(tmp_path: Path) -> None:
    cleared: list[str] = []

    def _clear(_r: Path, k: str) -> bool:
        cleared.append(k)
        return True

    with (
        patch.object(resolve, "_merge_state_key_candidates", return_value=["01ULID", "m"]),
        patch.object(resolve, "_iter_merge_states_for_slug", return_value=[]),
        patch.object(resolve, "clear_state", side_effect=_clear),
    ):
        result = resolve._clear_merge_state_for_mission(tmp_path, "m")
    assert result is True
    assert cleared == ["01ULID", "m"]


# --- _cleanup_merge_workspaces_for_state ------------------------------------


def test_cleanup_workspaces_dedups_keys(tmp_path: Path) -> None:
    cleaned: list[str] = []
    st = _state(slug="m", mid="01ULID")

    def _record(k: str, _r: Path) -> None:
        cleaned.append(k)

    with (
        patch.object(resolve, "_merge_state_key_candidates", return_value=["01ULID", "m"]),
        patch.object(resolve, "cleanup_merge_workspace", side_effect=_record),
    ):
        resolve._cleanup_merge_workspaces_for_state(
            tmp_path, mission_slug="m", state_entry=("01ULID", st)
        )
    # Deduped, falsy keys dropped, order preserved.
    assert cleaned == ["01ULID", "m"]


# --- _resolve_target_branch -------------------------------------------------


def test_resolve_target_branch_delegates() -> None:
    with patch(
        "specify_cli.core.paths.resolve_merge_target_branch",
        return_value=("prog/2057-merge", "meta"),
    ):
        assert resolve._resolve_target_branch(Path("/r"), "m", None) == ("prog/2057-merge", "meta")
