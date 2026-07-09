"""WP04 — byte-parity proof that the direct + scope-review mid8 sites route through
``resolve_mid8`` without changing their observable output (FR-001, NFR-001), and the
FR-002 guarantee that no ``MissionExecutionContext``-held identity is re-derived.

Golden values are **literals captured from HEAD before any edit** (anti-gaming): a
26-char ULID-style ``mission_id`` truncates to its first 8 chars; the decline paths
(absent / short / non-str ``mission_id``) yield ``""``/``None`` exactly as the
pre-route guards did.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from specify_cli.lanes.branch_naming import resolve_mid8

pytestmark = [pytest.mark.unit, pytest.mark.fast]

# Golden literals captured from HEAD (``mission_id[:8]`` before routing).
_FULL_MISSION_ID = "01KV7SFD0123456789ABCDEFGH"  # 26-char ULID-style
_GOLDEN_MID8 = "01KV7SFD"


# ---------------------------------------------------------------------------
# resolve_mid8 parity — the contract every routed site relies on.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "mission_slug",
    [
        "my-feature",  # no embedded tail
        "",  # the empty-slug form the direct sites pass
        f"my-feature-{_GOLDEN_MID8}",  # slug embeds the matching tail
        "my-feature-ZZZZZZZZ",  # slug embeds a divergent/stale tail (declared wins)
    ],
)
def test_resolve_mid8_matches_full_id_truncation(mission_slug: str) -> None:
    """A guaranteed-full ``mission_id`` always truncates to ``mission_id[:8]``."""
    assert resolve_mid8(mission_slug, mission_id=_FULL_MISSION_ID) == _GOLDEN_MID8


@pytest.mark.parametrize("mission_id", [None, "", "abc", "01KV7SF"])  # absent / short
def test_resolve_mid8_declines_without_full_id(mission_id: str | None) -> None:
    """Absent or <8-char ``mission_id`` declines to ``""`` (the guard's else-branch)."""
    assert resolve_mid8("my-feature", mission_id=mission_id) == ""


# ---------------------------------------------------------------------------
# resolution.py — _mid8_from_primary_meta (core read-path producer, M1).
# Decline/empty behavior must be preserved.
# ---------------------------------------------------------------------------


def _write_meta(repo_root: Path, slug: str, meta: dict[str, object]) -> Path:
    feature_dir = repo_root / "kitty-specs" / slug
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
    return feature_dir


def test_resolution_primary_meta_uses_mission_id_truncation(tmp_path: Path) -> None:
    """``mission_id`` (no explicit ``mid8``) → ``mission_id[:8]`` (M1 golden)."""
    from mission_runtime.resolution import _mid8_from_primary_meta

    slug = "rider-mission"
    _write_meta(tmp_path, slug, {"mission_id": _FULL_MISSION_ID, "mission_slug": slug})
    assert _mid8_from_primary_meta(tmp_path, slug) == _GOLDEN_MID8


def test_resolution_primary_meta_prefers_explicit_mid8(tmp_path: Path) -> None:
    """Explicit ``mid8`` field is returned verbatim (unchanged by routing)."""
    from mission_runtime.resolution import _mid8_from_primary_meta

    slug = "rider-mission"
    _write_meta(tmp_path, slug, {"mid8": "EXPLICIT8", "mission_id": _FULL_MISSION_ID})
    assert _mid8_from_primary_meta(tmp_path, slug) == "EXPLICIT8"


def test_resolution_primary_meta_declines_when_no_identity(tmp_path: Path) -> None:
    """No ``mid8``/``mission_id`` (or short id) → ``""`` (decline preserved)."""
    from mission_runtime.resolution import _mid8_from_primary_meta

    slug = "rider-mission"
    _write_meta(tmp_path, slug, {"mission_slug": slug})
    assert _mid8_from_primary_meta(tmp_path, slug) == ""

    short = "short-mission"
    _write_meta(tmp_path, short, {"mission_id": "01KV7SF"})  # 7 chars < 8
    assert _mid8_from_primary_meta(tmp_path, short) == ""


def test_resolution_primary_meta_declines_when_missing_dir(tmp_path: Path) -> None:
    """No feature dir at all → ``""`` (the ValueError/empty branch)."""
    from mission_runtime.resolution import _mid8_from_primary_meta

    assert _mid8_from_primary_meta(tmp_path, "does-not-exist") == ""


# ---------------------------------------------------------------------------
# mission_type.py — _read_mission_mid8 (contract-sensitive ``… else ""``, M2).
# ---------------------------------------------------------------------------


def test_mission_type_read_mid8_truncates_then_declines(tmp_path: Path) -> None:
    from specify_cli.cli.commands.mission_type import _read_mission_mid8

    # ``_read_mission_mid8`` reads ``meta.json`` from the *directory* of the
    # given path (``load_meta(meta_path.parent)``), so each case gets its own
    # dir with a ``meta.json`` — matching how production calls it
    # (``feature_dir / "meta.json"``). Earlier this wrote uniquely-named json
    # files into one shared dir with no ``meta.json``, so the loader found
    # nothing and returned ``""`` — a stale-test artifact, not a product drift.
    def _read_meta(name: str, meta: dict[str, object]) -> str:
        case_dir = tmp_path / name
        case_dir.mkdir()
        meta_path = case_dir / "meta.json"
        meta_path.write_text(json.dumps(meta), encoding="utf-8")
        result: str = _read_mission_mid8(meta_path)
        return result

    assert _read_meta("full", {"mission_id": _FULL_MISSION_ID}) == _GOLDEN_MID8
    assert _read_meta("explicit", {"mid8": "EXPLICIT8"}) == "EXPLICIT8"
    # contract: empty string, never None
    assert _read_meta("bare", {"mission_slug": "x"}) == ""


# ---------------------------------------------------------------------------
# workflow.py — _load_coord_branch_meta (``mid[:8] … else None``, M3).
# ---------------------------------------------------------------------------


def test_workflow_coord_meta_mid8_truncation_and_none(tmp_path: Path) -> None:
    from specify_cli.cli.commands.agent.workflow import _load_coord_branch_meta

    full = tmp_path / "full"
    full.mkdir()
    (full / "meta.json").write_text(
        json.dumps({"mission_id": _FULL_MISSION_ID, "coordination_branch": "kitty/coord"}),
        encoding="utf-8",
    )
    coord, mid, mid8 = _load_coord_branch_meta(full)
    assert coord == "kitty/coord"
    assert mid == _FULL_MISSION_ID
    assert mid8 == _GOLDEN_MID8

    # Short / missing mission_id → mid8 None (the else-None guard preserved).
    short = tmp_path / "short"
    short.mkdir()
    (short / "meta.json").write_text(json.dumps({"mission_id": "01KV7SF"}), encoding="utf-8")
    _, _, mid8_short = _load_coord_branch_meta(short)
    assert mid8_short is None


# ---------------------------------------------------------------------------
# generator.py — _find_mission_dir (M5, SELECTOR comparison, semantics preserved).
# ---------------------------------------------------------------------------


def _seed_mission(repo_root: Path, slug: str, mission_id: str) -> Path:
    feature_dir = repo_root / "kitty-specs" / slug
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "meta.json").write_text(
        json.dumps({"mission_id": mission_id, "mission_slug": slug}), encoding="utf-8"
    )
    return feature_dir


def test_generator_find_mission_dir_matches_by_mid8(tmp_path: Path) -> None:
    """A mid8 handle resolves to the mission whose ``mission_id`` truncates to it."""
    from specify_cli.retrospective.generator import _resolve_mission_dir

    feature_dir = _seed_mission(tmp_path, "rider-mission", _FULL_MISSION_ID)
    assert _resolve_mission_dir(_GOLDEN_MID8, tmp_path) == feature_dir


def test_generator_find_mission_dir_matches_by_full_id_and_slug(tmp_path: Path) -> None:
    from specify_cli.retrospective.generator import _resolve_mission_dir

    feature_dir = _seed_mission(tmp_path, "rider-mission", _FULL_MISSION_ID)
    assert _resolve_mission_dir(_FULL_MISSION_ID, tmp_path) == feature_dir
    assert _resolve_mission_dir("rider-mission", tmp_path) == feature_dir


def test_generator_find_mission_dir_no_false_match_on_empty_id(tmp_path: Path) -> None:
    """A meta with no ``mission_id`` must not match a non-empty handle (selector)."""
    from specify_cli.retrospective.generator import _resolve_mission_dir

    feature_dir = tmp_path / "kitty-specs" / "legacy"
    feature_dir.mkdir(parents=True)
    (feature_dir / "meta.json").write_text(json.dumps({"mission_slug": "legacy"}), encoding="utf-8")
    assert _resolve_mission_dir(_GOLDEN_MID8, tmp_path) is None


# ---------------------------------------------------------------------------
# FR-002 — no MissionExecutionContext-held identity re-derivation (T013).
# Construct a REAL MissionExecutionContext + IdentityFragment and assert the carried
# mid8 is consumed as-is (single-derivation invariant), never recomputed.
# ---------------------------------------------------------------------------


def test_execution_context_carries_single_derived_mid8() -> None:
    """A real MissionExecutionContext holds ``identity.mid8`` derived once; consumers read it."""
    from mission_runtime.context import IdentityFragment, MissionExecutionContext

    identity = IdentityFragment.derive(
        mission_id=_FULL_MISSION_ID, mission_slug="rider-mission-01KV7SFD"
    )
    ctx = MissionExecutionContext(
        action="implement",
        mission_slug="rider-mission-01KV7SFD",
        feature_dir="kitty-specs/rider-mission-01KV7SFD",
        target_branch="feat/naming-rider-3-2-1",
        detection_method="explicit",
        identity=identity,
    )

    # The fragment carries the canonical mid8; reading it must equal the golden,
    # and re-deriving via resolve_mid8 from the SAME declared identity must agree
    # — i.e. there is one derivation point and consumers do not diverge from it.
    assert ctx.identity is not None
    assert ctx.identity.mid8 == _GOLDEN_MID8
    assert resolve_mid8(ctx.mission_slug, mission_id=ctx.identity.mission_id) == ctx.identity.mid8


def test_identity_fragment_rejects_inconsistent_mid8() -> None:
    """The single-derivation invariant rejects a mid8 that is not ``mission_id[:8]``."""
    from mission_runtime.context import IdentityFragment

    with pytest.raises(ValueError, match="single-derived"):
        IdentityFragment(mission_id=_FULL_MISSION_ID, mid8="WRONG888", mission_slug="x")
