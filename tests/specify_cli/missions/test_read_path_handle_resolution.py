"""WP04 / IC-03 regression coverage for the read-path handle resolution.

These tests reproduce the e2e findings this mission drains:

* **F-001 / F-003 / F-004** — a bare ``mid8`` handle (e.g. ``01KTPKST``) must
  resolve to the *same* mission directory as the full ``<slug>-<mid8>`` form. The
  pre-fix resolver joined the mid8 to ``kitty-specs/<mid8>`` literally and
  returned a wrong-but-plausible (non-existent) directory.
* **C-CTX-4 / C-009** — an ambiguous handle (matching more than one mission)
  raises a *structured* :class:`MissionSelectorAmbiguous`
  (``MISSION_AMBIGUOUS_SELECTOR``), never a silent fallback to one of the
  candidates.

The single read primitive is ``resolve_mission_read_path``; the consolidated
``candidate_feature_dir_for_mission`` re-export must inherit the same behaviour
(C-005: one resolver), so it is exercised here too.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from specify_cli.missions._read_path_resolver import (
    MISSION_AMBIGUOUS_SELECTOR_CODE,
    MissionSelectorAmbiguous,
    candidate_feature_dir_for_mission,
    _resolve_mission_read_path as resolve_mission_read_path,
)

pytestmark = [pytest.mark.fast]


def _seed_mission(
    tmp_path: Path, *, slug: str, mission_id: str
) -> Path:
    """Create ``kitty-specs/<slug>/meta.json`` carrying a ``mission_id``.

    The mission directory is the canonical ``<slug>`` name (which already embeds
    the mid8 for post-WP03 missions); the resolver derives mid8 from the slug.
    """
    mission_dir = tmp_path / "kitty-specs" / slug
    mission_dir.mkdir(parents=True)
    (mission_dir / "meta.json").write_text(
        json.dumps({"mission_id": mission_id, "mission_slug": slug}),
        encoding="utf-8",
    )
    return mission_dir


def test_mid8_handle_resolves_same_dir_as_full_slug(tmp_path: Path) -> None:
    """F-001: ``--mission <mid8>`` resolves identically to ``--mission <slug>``.

    Reproduces ``decision open --mission 01KTPKST`` failing because the mid8 was
    treated as a literal slug (``kitty-specs/01KTPKST`` not found).
    """
    mission_id = "01KTPKSTABCDEFGHJKMNPQRSTV"  # 26-char ULID-shaped
    mid8 = mission_id[:8]  # "01KTPKST"
    slug = f"my-feature-{mid8}"
    expected = _seed_mission(tmp_path, slug=slug, mission_id=mission_id)

    via_full_slug = resolve_mission_read_path(tmp_path, slug, mid8)
    via_mid8 = resolve_mission_read_path(tmp_path, mid8, "")

    assert via_full_slug == expected
    assert via_mid8 == expected, (
        "a bare mid8 handle must resolve to the same feature_dir as the full "
        "slug (F-001/F-003/F-004); the read path must not join the mid8 to "
        "kitty-specs/<mid8> literally"
    )


def test_candidate_helper_inherits_mid8_resolution(tmp_path: Path) -> None:
    """C-005: the consolidated ``candidate_feature_dir_for_mission`` (the ONE
    read primitive) inherits mid8 resolution, so all 30+ callers benefit."""
    mission_id = "01KTPKSTABCDEFGHJKMNPQRSTV"
    mid8 = mission_id[:8]
    slug = f"my-feature-{mid8}"
    expected = _seed_mission(tmp_path, slug=slug, mission_id=mission_id)

    assert candidate_feature_dir_for_mission(tmp_path, mid8) == expected
    assert candidate_feature_dir_for_mission(tmp_path, slug) == expected


def test_ambiguous_handle_raises_structured_error(tmp_path: Path) -> None:
    """C-CTX-4 / C-009: an ambiguous numeric-prefix handle raises a structured
    MissionSelectorAmbiguous — never a silent pick of one candidate."""
    _seed_mission(
        tmp_path, slug="083-alpha", mission_id="01AAAAAAAAAAAAAAAAAAAAAAAA"
    )
    _seed_mission(
        tmp_path, slug="083-beta", mission_id="01BBBBBBBBBBBBBBBBBBBBBBBB"
    )

    with pytest.raises(MissionSelectorAmbiguous) as excinfo:
        # "083" matches two missions by numeric prefix → ambiguous.
        resolve_mission_read_path(tmp_path, "083", "")

    assert excinfo.value.error_code == MISSION_AMBIGUOUS_SELECTOR_CODE
    assert set(excinfo.value.candidates) == {"083-alpha", "083-beta"}


def test_unknown_handle_does_not_fabricate_dir(tmp_path: Path) -> None:
    """C-CTX-4: an unresolvable handle with ``require_exists`` raises rather than
    returning a wrong-but-plausible path."""
    _seed_mission(
        tmp_path, slug="my-feature-01KTPKST", mission_id="01KTPKSTABCDEFGHJKMNPQRSTV"
    )
    from specify_cli.missions._read_path_resolver import StatusReadPathNotFound

    with pytest.raises(StatusReadPathNotFound):
        resolve_mission_read_path(
            tmp_path, "does-not-exist", "", require_exists=True
        )
