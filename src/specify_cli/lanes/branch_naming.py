"""Branch naming conventions for mission and lane branches.

Branch name grammar (two forms, both accepted by parse_mission_slug_from_branch):

  Legacy form (pre-WP02):
    kitty/mission-<NNN>-<slug>[-lane-<id>]
    where <NNN> is a 3-digit zero-padded numeric prefix

  New form (WP02+, FR-032, FR-033):
    kitty/mission-<human-slug>-<mid8>[-lane-<id>]
    where <human-slug> is the mission slug with any leading NNN- prefix stripped,
    and <mid8> is the first 8 characters of the mission's ULID.

Example for this mission:
  083-mission-id-canonical-identity-migration with ULID 01KNXQS9ATWWFXS3K5ZJ9E5008
  -> human-slug: mission-id-canonical-identity-migration
  -> mid8: 01KNXQS9
  -> branch: kitty/mission-mission-id-canonical-identity-migration-01KNXQS9-lane-a

Rationale: pre-merge branches must not carry dead numbering semantics, because
there is no mission_number until merge time (FR-044). The mid8 token ensures
two concurrent missions with identical human slugs produce distinct branch names
(FR-032), eliminating the partition-unsafe collision that led to the 080-* triple.

Both forms are accepted at read time so existing worktrees keep working (FR-052).
"""

from __future__ import annotations

import re
from typing import NamedTuple

_MISSION_PREFIX = "kitty/mission-"

# Legacy regex: NNN-slug (3 digits + hyphen prefix)
_LEGACY_MISSION_RE = re.compile(r"^kitty/mission-(\d{3}-.+)$")
_LEGACY_LANE_RE = re.compile(r"^kitty/mission-(\d{3}-.+)-(lane-[a-z])$")
_PLAIN_LEGACY_MISSION_RE = re.compile(r"^kitty/mission-(.+)$")
_PLAIN_LEGACY_LANE_RE = re.compile(r"^kitty/mission-(.+)-(lane-[a-z])$")

# New regex: <human-slug>-<mid8>[-lane-<id>]
# Mid8 = exactly 8 uppercase alphanumeric characters (ULID character set)
_MID8_RE = re.compile(r"^[0-9A-HJKMNP-TV-Z]{8}$")  # Crockford base32, exactly 8 chars
_NEW_LANE_RE = re.compile(r"^kitty/mission-(.+)-([0-9A-HJKMNP-TV-Z]{8})-(lane-[a-z])$")
_NEW_MISSION_RE = re.compile(r"^kitty/mission-(.+)-([0-9A-HJKMNP-TV-Z]{8})$")

# Numeric prefix pattern: exactly 3 digits + hyphen
_NUMERIC_PREFIX_RE = re.compile(r"^\d{3}-(.+)$")


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------


def strip_numeric_prefix(slug: str) -> str:
    """Strip a leading NNN- numeric prefix from a mission slug.

    Strips exactly 3 digits followed by a hyphen from the start of the slug.
    If the slug has no such prefix, it is returned unchanged. The remainder
    after stripping must be non-empty; if it would be empty, the original slug
    is returned unchanged.

    Rule: strip exactly ``r"^\\d{3}-"``. Do not strip 2-digit, 4-digit, or
    longer prefixes. This matches the allocator's historical output format.

    Examples:
        "083-foo"       -> "foo"
        "001-bar-baz"   -> "bar-baz"
        "foo"           -> "foo"      (no prefix)
        "08-foo"        -> "08-foo"   (only 2 digits, not stripped)
        "1234-foo"      -> "1234-foo" (4 digits, not stripped)
        "083-"          -> "083-"     (empty remainder, not stripped)
    """
    if not slug:
        return slug
    match = _NUMERIC_PREFIX_RE.match(slug)
    if match:
        remainder = match.group(1)
        if remainder:  # only strip if remainder is non-empty
            return remainder
    return slug


def mid8(mission_id: str) -> str:
    """Return the first 8 characters of a ULID (the ``mid8`` alias).

    Args:
        mission_id: A ULID string (26 characters, Crockford base32).

    Returns:
        The first 8 characters.

    Raises:
        ValueError: If ``mission_id`` is shorter than 8 characters — this is a
            programming error (mission_id from meta.json is always a full ULID).
    """
    if len(mission_id) < 8:
        raise ValueError(f"mission_id must be at least 8 characters to derive mid8, got {len(mission_id)!r}: {mission_id!r}")
    return mission_id[:8]


# ---------------------------------------------------------------------------
# Branch name constructors
# ---------------------------------------------------------------------------


def mission_branch_name(mission_slug: str, *, mission_id: str | None = None) -> str:
    """Return the mission integration branch name.

    When ``mission_id`` is provided, uses the new ``<human-slug>-<mid8>`` format
    (FR-032).  When ``mission_id`` is ``None``, falls back to the legacy format
    for backward compatibility with pre-WP02 callers.

    New form:  ``kitty/mission-<human-slug>-<mid8>``
    Legacy:    ``kitty/mission-<slug>``

    Examples:
        mission_branch_name("083-my-feature", mission_id="01KNXQS9ATWWFXS3K5ZJ9E5008")
          -> "kitty/mission-my-feature-01KNXQS9"
        mission_branch_name("057-my-feature")  # legacy, no mission_id
          -> "kitty/mission-057-my-feature"
    """
    if mission_id is not None:
        human_slug = strip_numeric_prefix(mission_slug)
        return f"{_MISSION_PREFIX}{human_slug}-{mid8(mission_id)}"
    # Legacy form: no mission_id supplied (pre-WP02 callers, must still work)
    return f"{_MISSION_PREFIX}{mission_slug}"


def lane_branch_name(
    mission_slug: str,
    lane_id: str,
    planning_base_branch: str | None = None,
    *,
    mission_id: str | None = None,
) -> str:
    """Return a lane branch name.

    For the canonical ``lane-planning`` lane, returns the planning base branch
    rather than a ``kitty/mission-…`` branch name, because planning-artifact WPs
    live in the main repository checkout on the target branch (typically ``main``).

    When ``mission_id`` is provided, uses the new ``<human-slug>-<mid8>`` format
    (FR-032).  When ``mission_id`` is ``None``, falls back to the legacy format.

    Args:
        mission_slug: Feature slug (e.g. ``"083-my-feature"``).
        lane_id: Lane identifier (e.g. ``"lane-a"`` or ``"lane-planning"``).
        planning_base_branch: The branch that planning-artifact work targets
            (typically the value of ``target_branch`` from ``meta.json``).
            Defaults to ``"main"`` when ``lane_id == "lane-planning"`` and this
            argument is omitted.  Ignored for all other lane IDs.
        mission_id: Optional ULID. When present, the new ``<human-slug>-<mid8>``
            naming format is used. When ``None``, the legacy format is preserved.

    Examples:
        lane_branch_name("083-my-feature", "lane-a", mission_id="01KNXQS9ATWWFXS3K5ZJ9E5008")
          -> "kitty/mission-my-feature-01KNXQS9-lane-a"
        lane_branch_name("057-my-feature", "lane-a")  # legacy
          -> "kitty/mission-057-my-feature-lane-a"
        lane_branch_name("083-my-feature", "lane-planning")
          -> "main"
        lane_branch_name("083-my-feature", "lane-planning", planning_base_branch="release/3.x")
          -> "release/3.x"
    """
    if lane_id == "lane-planning":
        return planning_base_branch if planning_base_branch is not None else "main"
    if mission_id is not None:
        human_slug = strip_numeric_prefix(mission_slug)
        return f"{_MISSION_PREFIX}{human_slug}-{mid8(mission_id)}-{lane_id}"
    # Legacy form
    return f"{_MISSION_PREFIX}{mission_slug}-{lane_id}"


# ---------------------------------------------------------------------------
# Predicates
# ---------------------------------------------------------------------------


def is_mission_branch(branch_name: str) -> bool:
    """Return True if branch matches either mission branch pattern (legacy or new).

    A mission branch matches ``kitty/mission-<body>`` but NOT a lane branch
    (which ends in ``-lane-<id>``).
    """
    if not branch_name.startswith(_MISSION_PREFIX):
        return False
    # Must not be a lane branch
    if is_lane_branch(branch_name):
        return False
    body = branch_name[len(_MISSION_PREFIX) :]
    return bool(body)


def is_lane_branch(branch_name: str) -> bool:
    """Return True if branch matches a lane branch pattern (legacy or new)."""
    return _LEGACY_LANE_RE.match(branch_name) is not None or _NEW_LANE_RE.match(branch_name) is not None


def is_legacy_branch(branch_name: str) -> bool:
    """Return True if branch uses the legacy NNN-slug naming form.

    Legacy form: ``kitty/mission-NNN-slug[-lane-X]``
    New form:    ``kitty/mission-<human-slug>-<mid8>[-lane-X]``

    Returns False for non-mission branches.
    """
    if not branch_name.startswith(_MISSION_PREFIX):
        return False
    parsed = parse_mission_slug_from_branch(branch_name)
    return parsed is not None and parsed.mid8_token is None


# ---------------------------------------------------------------------------
# Parse result type
# ---------------------------------------------------------------------------


class BranchParseResult(NamedTuple):
    """Structured result from ``parse_mission_slug_from_branch``.

    Attributes:
        slug: The human slug extracted from the branch name.
            - Legacy: the full ``NNN-slug`` portion.
            - New: just the ``<human-slug>`` (NNN prefix already stripped).
        mid8_token: The 8-character ULID prefix for new-form branches;
            ``None`` for legacy branches.
        lane_id: The lane identifier (e.g. ``"lane-a"``) when present;
            ``None`` for mission branches without a lane.
    """

    slug: str
    mid8_token: str | None
    lane_id: str | None


# ---------------------------------------------------------------------------
# Branch parser
# ---------------------------------------------------------------------------


def parse_mission_slug_from_branch(branch_name: str) -> BranchParseResult | None:
    """Extract mission identity tokens from a mission or lane branch name.

    Accepts both legacy (``NNN-slug``) and new (``<human-slug>-<mid8>``) forms,
    for backward compatibility with worktrees created before WP02 (FR-052).

    Grammar (in priority order):
      1. New lane:     ``kitty/mission-<human-slug>-<mid8>-lane-<id>``
      2. New mission:  ``kitty/mission-<human-slug>-<mid8>``
      3. Legacy lane:  ``kitty/mission-NNN-slug-lane-<id>``
      4. Legacy miss.: ``kitty/mission-NNN-slug``

    The parser distinguishes new from legacy by checking whether the penultimate
    token (before the optional lane suffix) is an 8-char ULID-alphabet token.
    Parsing is anchored from the *right* so slugs with embedded hyphens are
    handled correctly.

    Returns:
        A :class:`BranchParseResult` triple ``(slug, mid8_token, lane_id)`` or
        ``None`` if the branch doesn't match any known mission pattern.
    """
    if not branch_name.startswith(_MISSION_PREFIX):
        return None

    # Try new lane form first (most specific)
    m = _NEW_LANE_RE.match(branch_name)
    if m:
        return BranchParseResult(slug=m.group(1), mid8_token=m.group(2), lane_id=m.group(3))

    # Try new mission form (no lane suffix)
    m = _NEW_MISSION_RE.match(branch_name)
    if m:
        return BranchParseResult(slug=m.group(1), mid8_token=m.group(2), lane_id=None)

    # Try legacy lane form
    m = _LEGACY_LANE_RE.match(branch_name)
    if m:
        return BranchParseResult(slug=m.group(1), mid8_token=None, lane_id=m.group(2))

    # Try legacy mission form
    m = _LEGACY_MISSION_RE.match(branch_name)
    if m:
        return BranchParseResult(slug=m.group(1), mid8_token=None, lane_id=None)

    # Try compatibility legacy lane form without numeric prefix.
    m = _PLAIN_LEGACY_LANE_RE.match(branch_name)
    if m:
        return BranchParseResult(slug=m.group(1), mid8_token=None, lane_id=m.group(2))

    # Try compatibility legacy mission form without numeric prefix.
    m = _PLAIN_LEGACY_MISSION_RE.match(branch_name)
    if m:
        return BranchParseResult(slug=m.group(1), mid8_token=None, lane_id=None)

    return None


def parse_lane_id_from_branch(branch_name: str) -> str | None:
    """Extract lane_id from a lane branch name.

    Returns None if the branch is not a lane branch.
    """
    # New form
    m = _NEW_LANE_RE.match(branch_name)
    if m:
        return m.group(3)
    # Legacy form
    m = _LEGACY_LANE_RE.match(branch_name)
    if m:
        return m.group(2)
    # Compatibility legacy form without numeric prefix
    m = _PLAIN_LEGACY_LANE_RE.match(branch_name)
    if m:
        return m.group(2)
    return None
