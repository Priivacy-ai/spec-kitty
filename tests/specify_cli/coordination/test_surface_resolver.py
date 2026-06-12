"""Tests for specify_cli.coordination.surface_resolver."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

import inspect

from specify_cli.coordination import surface_resolver
from specify_cli.coordination.surface_resolver import resolve_status_surface
from specify_cli.missions._read_path_resolver import StatusReadPathNotFound

pytestmark = pytest.mark.fast


def _write_meta(feature_dir: Path, **fields: object) -> None:
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "meta.json").write_text(json.dumps(fields), encoding="utf-8")


def test_resolve_primary_checkout_when_no_coord_branch(tmp_path: Path) -> None:
    _write_meta(tmp_path / "kitty-specs" / "my-mission", mission_id="01KTDVHZKGCHCW6HQ4V577PNES")
    result = resolve_status_surface(tmp_path, "my-mission")
    assert result == tmp_path / "kitty-specs" / "my-mission" / "status.events.jsonl"


def test_resolve_coordination_worktree_when_coord_branch_set(tmp_path: Path) -> None:
    _write_meta(
        tmp_path / "kitty-specs" / "my-mission",
        mission_id="01KTDVHZKGCHCW6HQ4V577PNES",
        coordination_branch="kitty/mission-my-mission-01KTDVHZ",
    )
    result = resolve_status_surface(tmp_path, "my-mission")
    expected = (
        tmp_path
        / ".worktrees"
        / "my-mission-01KTDVHZ-coord"
        / "kitty-specs"
        / "my-mission-01KTDVHZ"
        / "status.events.jsonl"
    )
    assert result == expected


def test_raises_when_meta_missing(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        resolve_status_surface(tmp_path, "no-such-mission")


def test_mid8_is_first_8_chars_of_mission_id(tmp_path: Path) -> None:
    _write_meta(
        tmp_path / "kitty-specs" / "my-mission",
        mission_id="01KTDVHZKGCHCW6HQ4V577PNES",
        coordination_branch="kitty/mission-my-mission-01KTDVHZ",
    )
    result = resolve_status_surface(tmp_path, "my-mission")
    assert "my-mission-01KTDVHZ-coord" in str(result)


def test_resolve_uses_explicit_mid8_field_when_present(tmp_path: Path) -> None:
    _write_meta(
        tmp_path / "kitty-specs" / "my-mission",
        mission_id="01KTDVHZKGCHCW6HQ4V577PNES",
        mid8="ABCD1234",
        coordination_branch="kitty/mission-my-mission-ABCD1234",
    )
    result = resolve_status_surface(tmp_path, "my-mission")
    assert "my-mission-ABCD1234-coord" in str(result)


def test_slug_with_mid8_already_embedded_is_not_doubled(tmp_path: Path) -> None:
    _write_meta(
        tmp_path / "kitty-specs" / "my-mission-01KTDVHZ",
        mission_id="01KTDVHZKGCHCW6HQ4V577PNES",
        coordination_branch="kitty/mission-my-mission-01KTDVHZ",
    )
    result = resolve_status_surface(tmp_path, "my-mission-01KTDVHZ")
    assert "my-mission-01KTDVHZ-coord" in str(result)
    assert "my-mission-01KTDVHZ-01KTDVHZ" not in str(result)


def test_materialized_coord_worktree_resolves_exactly_once(tmp_path: Path) -> None:
    """FR-036 (#1772): a coord-topology mission resolves the status surface
    exactly once — no nested ``.worktrees/<m>-coord/.worktrees/<m>-coord/…``.

    Before the single-pass fix, ``resolve_status_surface`` first called the
    coord-aware ``candidate_feature_dir_for_mission`` (which already returns the
    materialized coord feature dir), then *re-derived* a coord root and resolved
    a **second** time. When a nested ``.worktrees/<m>-coord`` directory exists
    *inside* the coord worktree, that second coord-aware resolution picked it,
    producing a path with ``.worktrees`` twice. This regression plants exactly
    that nested trap and proves the single-pass resolver ignores it: the result
    contains ``.worktrees`` exactly once and points at the real coord feature
    dir.
    """
    slug = "my-mission-01KTDVHZ"  # slug already embeds mid8 → coord-aware on 1st pass
    mid8 = "01KTDVHZ"
    coord_root = tmp_path / ".worktrees" / f"{slug}-coord"
    coord_feature_dir = coord_root / "kitty-specs" / slug
    _write_meta(
        coord_feature_dir,
        mission_id="01KTDVHZKGCHCW6HQ4V577PNES",
        mid8=mid8,
        coordination_branch=f"kitty/mission-{slug}",
    )

    # Plant the nested-coord trap that the old double-resolution would follow.
    nested_trap = coord_root / ".worktrees" / f"{slug}-coord" / "kitty-specs" / slug
    _write_meta(
        nested_trap,
        mission_id="01KTDVHZKGCHCW6HQ4V577PNES",
        mid8=mid8,
        coordination_branch=f"kitty/mission-{slug}",
    )

    result = resolve_status_surface(tmp_path, slug)

    assert str(result).count(".worktrees") == 1, (
        f"FR-036 regression: status surface double-resolved into a nested "
        f"path: {result}"
    )
    assert result == coord_feature_dir / "status.events.jsonl"


def test_unresolvable_mid8_fails_closed_instead_of_fabricating(tmp_path: Path) -> None:
    """C-cluster fix (FR-005 / F-001): when a coord-topology mission declares a
    coordination branch but no declared source carries the mid8 (no ``mid8``
    field, no >=8-char ``mission_id``, and the slug embeds no mid8), the resolver
    must fail closed with :class:`StatusReadPathNotFound` rather than fabricate a
    wrong-but-plausible ``(slug+"00000000")[:8]`` coord path.
    """
    _write_meta(
        tmp_path / "kitty-specs" / "my-mission",
        coordination_branch="kitty/mission-my-mission",
    )
    with pytest.raises(StatusReadPathNotFound):
        resolve_status_surface(tmp_path, "my-mission")


def test_fabricated_mid8_idiom_is_gone_from_source() -> None:
    """The forbidden fabrication idiom ``(... + "00000000")[:8]`` must have zero
    occurrences in the resolver source — fabricating a mid8 violates the 3.x
    invariant that unresolvable context raises rather than falling back."""
    source = inspect.getsource(surface_resolver)
    assert "00000000" not in source
