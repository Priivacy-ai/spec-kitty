"""Branch naming conventions for mission and lane branches.

Mission branch: kitty/mission-{mission_slug}
Lane branch:    kitty/mission-{mission_slug}-{lane_id}

Both use the kitty/ namespace prefix for visual grouping in git.
Branch names use mission_slug (human-readable) rather than mission_id
(ULID) because branches are a human-facing surface.
"""

from __future__ import annotations

import re

_MISSION_PREFIX = "kitty/mission-"
_MISSION_RE = re.compile(r"^kitty/mission-(.+)$")
_LANE_RE = re.compile(r"^kitty/mission-(.+)-(lane-[a-z])$")


def mission_branch_name(mission_slug: str) -> str:
    """Return the mission integration branch name.

    Example: mission_branch_name("057-my-feature") -> "kitty/mission-057-my-feature"
    """
    return f"{_MISSION_PREFIX}{mission_slug}"


def lane_branch_name(mission_slug: str, lane_id: str) -> str:
    """Return a lane branch name.

    Example: lane_branch_name("057-my-feature", "lane-a") -> "kitty/mission-057-my-feature-lane-a"
    """
    return f"{_MISSION_PREFIX}{mission_slug}-{lane_id}"


def is_mission_branch(branch_name: str) -> bool:
    """Return True if branch matches the mission branch pattern.

    A mission branch matches kitty/mission-{slug} but NOT
    kitty/mission-{slug}-lane-{x} (which is a lane branch).
    """
    if not branch_name.startswith(_MISSION_PREFIX):
        return False
    # Must match mission pattern but NOT lane pattern
    return _MISSION_RE.match(branch_name) is not None and _LANE_RE.match(branch_name) is None


def is_lane_branch(branch_name: str) -> bool:
    """Return True if branch matches a lane branch pattern."""
    return _LANE_RE.match(branch_name) is not None


def parse_mission_slug_from_branch(branch_name: str) -> str | None:
    """Extract mission_slug from a mission or lane branch name.

    Returns None if the branch doesn't match either pattern.
    """
    lane_match = _LANE_RE.match(branch_name)
    if lane_match:
        return lane_match.group(1)
    mission_match = _MISSION_RE.match(branch_name)
    if mission_match:
        return mission_match.group(1)
    return None


def parse_lane_id_from_branch(branch_name: str) -> str | None:
    """Extract lane_id from a lane branch name.

    Returns None if the branch is not a lane branch.
    """
    lane_match = _LANE_RE.match(branch_name)
    if lane_match:
        return lane_match.group(2)
    return None
