"""Tests for human-slug + mid8 branch naming (WP02 / T012).

Covers:
- strip_numeric_prefix correctness (table-driven)
- mid8 extraction
- New branch constructor round-trip
- Collision: two missions with same human slug but different ULIDs -> distinct branches
- Legacy parse: NNN-slug forms still parse correctly
- parse_mission_slug_from_branch for both legacy and new forms
- is_legacy_branch helper
"""

from __future__ import annotations

import pytest

from specify_cli.lanes.branch_naming import (
    _mid8,
    is_legacy_branch,
    lane_branch_name,
    mission_branch_name,
    parse_mission_slug_from_branch,
    strip_numeric_prefix,
)


# ---------------------------------------------------------------------------
# strip_numeric_prefix — table-driven
# ---------------------------------------------------------------------------


pytestmark = [pytest.mark.unit, pytest.mark.fast]
@pytest.mark.parametrize(
    ("slug", "expected"),
    [
        ("083-foo", "foo"),
        ("001-bar-baz", "bar-baz"),
        ("999-x", "x"),
        ("foo", "foo"),  # no prefix — unchanged
        ("foo-bar", "foo-bar"),  # no prefix — unchanged
        ("08-foo", "08-foo"),  # only 2 digits — not stripped
        ("1234-foo", "1234-foo"),  # 4 digits — not stripped
        ("", ""),  # empty string — unchanged
        ("083-", "083-"),  # prefix but empty human slug after — unchanged (edge: strip only when non-empty remainder)
    ],
)
def test_strip_numeric_prefix(slug: str, expected: str) -> None:
    assert strip_numeric_prefix(slug) == expected


# ---------------------------------------------------------------------------
# mid8
# ---------------------------------------------------------------------------


def test_mid8_returns_first_8_chars() -> None:
    ulid = "01KNXQS9ATWWFXS3K5ZJ9E5008"
    assert _mid8(ulid) == "01KNXQS9"


def test_mid8_on_minimum_length() -> None:
    # ULID is 26 chars; mid8 needs at least 8
    assert _mid8("01234567ABCDEFGHIJKLMNOPQ") == "01234567"


def test_mid8_raises_on_too_short() -> None:
    with pytest.raises(ValueError, match="mission_id must be at least 8 characters"):
        _mid8("short")


# ---------------------------------------------------------------------------
# New branch name constructor
# ---------------------------------------------------------------------------


def test_mission_branch_name_new_format() -> None:
    slug = "083-mission-id-canonical-identity-migration"
    ulid = "01KNXQS9ATWWFXS3K5ZJ9E5008"
    result = mission_branch_name(slug, mission_id=ulid)
    assert result == "kitty/mission-mission-id-canonical-identity-migration-01KNXQS9"


def test_mission_branch_name_does_not_double_existing_mid8_suffix() -> None:
    slug = "agent-profile-projection-plugin-production-01KV3NGS"
    ulid = "01KV3NGSDCJ272573TF6T6NWDW"
    result = mission_branch_name(slug, mission_id=ulid)
    assert result == "kitty/mission-agent-profile-projection-plugin-production-01KV3NGS"


def test_lane_branch_name_new_format() -> None:
    slug = "083-mission-id-canonical-identity-migration"
    ulid = "01KNXQS9ATWWFXS3K5ZJ9E5008"
    result = lane_branch_name(slug, "lane-a", mission_id=ulid)
    assert result == "kitty/mission-mission-id-canonical-identity-migration-01KNXQS9-lane-a"


def test_lane_branch_name_does_not_double_existing_mid8_suffix() -> None:
    slug = "agent-profile-projection-plugin-production-01KV3NGS"
    ulid = "01KV3NGSDCJ272573TF6T6NWDW"
    result = lane_branch_name(slug, "lane-a", mission_id=ulid)
    assert result == "kitty/mission-agent-profile-projection-plugin-production-01KV3NGS-lane-a"


def test_lane_branch_name_without_numeric_prefix() -> None:
    # Slug with no numeric prefix — strip_numeric_prefix returns it unchanged
    slug = "my-feature"
    ulid = "01KNXQS9ATWWFXS3K5ZJ9E5008"
    result = lane_branch_name(slug, "lane-b", mission_id=ulid)
    assert result == "kitty/mission-my-feature-01KNXQS9-lane-b"


def test_lane_branch_name_planning_lane_ignores_mission_id() -> None:
    # lane-planning returns the planning base branch, no change
    result = lane_branch_name("083-foo", "lane-planning", mission_id="01KNXQS9ATWWFXS3K5ZJ9E5008")
    assert result == "main"


def test_lane_branch_name_planning_with_explicit_base() -> None:
    result = lane_branch_name(
        "083-foo", "lane-planning",
        planning_base_branch="release/3.x",
        mission_id="01KNXQS9ATWWFXS3K5ZJ9E5008",
    )
    assert result == "release/3.x"


# ---------------------------------------------------------------------------
# Collision: same human slug, different ULIDs -> distinct branch names
# ---------------------------------------------------------------------------


def test_collision_different_ulids_produce_distinct_branches() -> None:
    slug = "083-foo-bar"
    # Two ULIDs with DIFFERENT mid8 prefixes so they produce distinct branch names.
    ulid_a = "01KNXQS9ATWWFXS3K5ZJ9E5008"  # mid8 = 01KNXQS9
    ulid_b = "01KNXQSAATWWFXS3K5ZJ9E5009"  # mid8 = 01KNXQSA  (differs at char 8)

    branch_a = lane_branch_name(slug, "lane-a", mission_id=ulid_a)
    branch_b = lane_branch_name(slug, "lane-a", mission_id=ulid_b)

    assert branch_a != branch_b
    assert _mid8(ulid_a) in branch_a
    assert _mid8(ulid_b) in branch_b
    # The mid8 tokens must differ
    assert _mid8(ulid_a) != _mid8(ulid_b)


# ---------------------------------------------------------------------------
# parse_mission_slug_from_branch — legacy forms
# ---------------------------------------------------------------------------


# Real branch names from the 080-* triple on main, paired with expected lane_id.
# Note: "080-wpstate-lane-consumer-strangler-fig-phase-2" embeds "lane-consumer" in the
# slug itself — the parser correctly classifies it as a non-lane mission branch (lane_id=None)
# because the suffix "phase-2" does not match the lane pattern "lane-[a-z]".
LEGACY_BRANCHES: list[tuple[str, str | None]] = [
    ("kitty/mission-080-browser-mediated-oauth-cli-auth", None),
    ("kitty/mission-080-ci-hardening-and-lint-cleanup", None),
    ("kitty/mission-feature-without-number", None),
    # "lane-consumer" is part of the slug, NOT a lane suffix — lane_id must be None
    ("kitty/mission-080-wpstate-lane-consumer-strangler-fig-phase-2", None),
    # These end with a real lane suffix
    ("kitty/mission-080-browser-mediated-oauth-cli-auth-lane-a", "lane-a"),
    ("kitty/mission-082-stealth-gated-saas-sync-hardening-lane-b", "lane-b"),
    ("kitty/mission-feature-without-number-lane-a", "lane-a"),
]


@pytest.mark.parametrize("branch,expected_lane_id", LEGACY_BRANCHES)
def test_parse_legacy_branch(branch: str, expected_lane_id: str | None) -> None:
    result = parse_mission_slug_from_branch(branch)
    assert result is not None, f"Failed to parse legacy branch: {branch}"
    slug, mid8_val, lane_id = result
    assert slug  # non-empty
    assert mid8_val is None  # legacy: no mid8
    assert lane_id == expected_lane_id, (
        f"Expected lane_id={expected_lane_id!r} for {branch!r}, got {lane_id!r}"
    )


# ---------------------------------------------------------------------------
# parse_mission_slug_from_branch — new forms
# ---------------------------------------------------------------------------


def test_parse_new_branch_without_lane() -> None:
    branch = "kitty/mission-mission-id-canonical-identity-migration-01KNXQS9"
    result = parse_mission_slug_from_branch(branch)
    assert result is not None
    slug, mid8_val, lane_id = result
    assert slug == "mission-id-canonical-identity-migration"
    assert mid8_val == "01KNXQS9"
    assert lane_id is None


def test_parse_new_branch_with_lane() -> None:
    branch = "kitty/mission-mission-id-canonical-identity-migration-01KNXQS9-lane-a"
    result = parse_mission_slug_from_branch(branch)
    assert result is not None
    slug, mid8_val, lane_id = result
    assert slug == "mission-id-canonical-identity-migration"
    assert mid8_val == "01KNXQS9"
    assert lane_id == "lane-a"


def test_parse_new_branch_slug_with_hyphens() -> None:
    # Multi-part slug
    branch = "kitty/mission-foo-bar-baz-01KNXQS9-lane-b"
    result = parse_mission_slug_from_branch(branch)
    assert result is not None
    slug, mid8_val, lane_id = result
    assert slug == "foo-bar-baz"
    assert mid8_val == "01KNXQS9"
    assert lane_id == "lane-b"


def test_parse_unknown_branch_returns_none() -> None:
    result = parse_mission_slug_from_branch("feature/some-other-branch")
    assert result is None


def test_parse_non_kitty_prefix_returns_none() -> None:
    result = parse_mission_slug_from_branch("main")
    assert result is None


# ---------------------------------------------------------------------------
# is_legacy_branch
# ---------------------------------------------------------------------------


def test_is_legacy_branch_with_numeric_prefix() -> None:
    assert is_legacy_branch("kitty/mission-080-browser-mediated-oauth-cli-auth") is True
    assert is_legacy_branch("kitty/mission-080-foo-lane-a") is True
    assert is_legacy_branch("kitty/mission-feature-without-number") is True
    assert is_legacy_branch("kitty/mission-feature-without-number-lane-a") is True


def test_is_legacy_branch_new_form() -> None:
    assert is_legacy_branch("kitty/mission-foo-bar-01KNXQS9") is False
    assert is_legacy_branch("kitty/mission-foo-bar-01KNXQS9-lane-a") is False


def test_is_legacy_branch_non_kitty() -> None:
    assert is_legacy_branch("main") is False
    assert is_legacy_branch("feature/something") is False


# ---------------------------------------------------------------------------
# Round-trip: construct then parse
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("slug", "ulid", "lane"),
    [
        ("083-foo-bar", "01KNXQS9ATWWFXS3K5ZJ9E5008", "lane-a"),
        ("001-simple", "01KNXQS0ATWWFXS3K5ZJ9E5001", "lane-b"),
        ("my-feature", "01KNXQS1ATWWFXS3K5ZJ9E5002", "lane-c"),
    ],
)
def test_round_trip_construct_then_parse(slug: str, ulid: str, lane: str) -> None:
    branch = lane_branch_name(slug, lane, mission_id=ulid)
    result = parse_mission_slug_from_branch(branch)
    assert result is not None
    parsed_slug, parsed_mid8, parsed_lane = result
    assert parsed_mid8 == ulid[:8]
    assert parsed_lane == lane
    # The human slug should be strip_numeric_prefix(slug)
    assert parsed_slug == strip_numeric_prefix(slug)


# ---------------------------------------------------------------------------
# Pathological case: slug already ends with a *different* mid8-shaped token
# ---------------------------------------------------------------------------


def test_mission_branch_name_does_not_strip_different_mid8_suffix() -> None:
    """Slug ending with a mid8-shaped token that differs from the mission's own mid8.

    When the slug already contains a different mid8-shaped suffix (e.g. an
    earlier mission's mid8 embedded in the human slug), ``_human_slug_for_mid8_branch``
    must NOT strip it — the deduplication guard only removes the suffix when it
    matches the *current* mission_id's mid8.  The result is a branch name with
    both the embedded token and the own mid8, i.e. a double-append.  This is the
    documented behavior, not a bug.
    """
    slug = "my-feature-AAAA1111"
    ulid = "01KV3NGSDCJ272573TF6T6NWDW"  # mid8 = 01KV3NGS
    result = mission_branch_name(slug, mission_id=ulid)
    # "AAAA1111" != "01KV3NGS" so it is NOT stripped; own mid8 is appended normally.
    assert result == "kitty/mission-my-feature-AAAA1111-01KV3NGS"


def test_lane_branch_name_pathological_mid8_mismatch() -> None:
    """Parallel pathological test for lane_branch_name with a mismatched mid8.

    When the slug's embedded mid8-shaped suffix differs from the mission_id's
    mid8, the guard does NOT strip the slug's token — documented behavior.
    The result contains both the slug's embedded token and the own mid8,
    followed by the lane suffix.
    """
    slug = "my-feature-AAAA1111"
    mission_id = "01KV3NGSDCJ272573TF6T6NWDW"  # mid8 = "01KV3NGS"
    result = lane_branch_name(slug, "lane-a", mission_id=mission_id)
    # slug's "AAAA1111" treated as part of human name; "01KV3NGS" appended
    assert result == "kitty/mission-my-feature-AAAA1111-01KV3NGS-lane-a"
