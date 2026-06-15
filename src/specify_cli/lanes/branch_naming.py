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
from typing import Any, NamedTuple

from specify_cli.core.errors import StructuredError

# Public surface for the fail-closed branch-identity seam introduced by FR-006
# (WP04). Scoped to the NEW symbols this slice adds (C-007 convention); the
# module's long-standing helpers retain their existing implicit public surface.
__all__ = [
    "BranchIdentityUnresolved",
    "mission_branch_name_required",
    "resolve_transaction_mid8",
]

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
        raise ValueError(
            f"mission_id must be at least 8 characters to derive mid8, got {len(mission_id)!r}: {mission_id!r}"
        )
    return mission_id[:8]


def mid8_from_slug(slug: str) -> str:
    """Extract the mid8 suffix from a mission slug, or return empty string.

    Recognises the 8-character Crockford base32 tail appended to mission slugs
    by the mission-identity system (e.g. ``my-feature-01KT3YBD`` → ``01KT3YBD``).

    The check is ``tail == tail.upper()`` rather than ``tail.isupper()`` so that
    all-digit tails (valid in ULID base32) are accepted correctly — ``str.isupper()``
    returns ``False`` for strings that contain no cased characters.
    """
    if "-" not in slug:
        return ""
    tail = slug.rsplit("-", 1)[-1]
    if _MID8_RE.match(tail):
        return tail
    return ""


def _human_slug_for_mid8_branch(mission_slug: str, mission_id: str) -> str:
    """Strip the embedded mid8 only when it matches mission_id's mid8; mismatched mid8 is not stripped."""
    human_slug = strip_numeric_prefix(mission_slug)
    suffix = f"-{mid8(mission_id)}"
    if human_slug.endswith(suffix):
        return human_slug[: -len(suffix)]
    return human_slug


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
        human_slug = _human_slug_for_mid8_branch(mission_slug, mission_id)
        return f"{_MISSION_PREFIX}{human_slug}-{mid8(mission_id)}"
    # Legacy form: no mission_id supplied (pre-WP02 callers, must still work)
    return f"{_MISSION_PREFIX}{mission_slug}"


class BranchIdentityUnresolved(StructuredError):
    """Raised when a mission branch cannot be composed without inventing identity.

    Fail-closed signal for seam 2 (FR-006): a *modern* mission whose ``mission_id``
    is absent AND whose slug carries neither a legacy ``NNN-`` prefix nor a mid8
    tail has no recoverable disambiguator. Emitting ``kitty/mission-<slug>`` here
    would name a branch that does not exist on disk (the #1860 class). The error
    carries the offending ``mission_handle`` and an actionable ``next_step`` so
    callers surface a typed, recoverable failure rather than a silent wrong-compose.

    Dual-era contract: legacy ``\\d{3}-`` slugs and mid8-era slugs both RESOLVE;
    only the genuinely-unresolvable modern case raises.
    """

    error_code: str = "BRANCH_IDENTITY_UNRESOLVED"

    def __init__(self, mission_handle: str, *, next_step: str | None = None) -> None:
        self.mission_handle = mission_handle
        self.next_step = next_step or (
            f"mission {mission_handle!r} has no mission_id and its slug carries no "
            "mid8 disambiguator; pass mission_id from meta.json, or run "
            "`spec-kitty migrate backfill-identity` to mint a mission_id for a "
            "legacy mission missing one."
        )
        super().__init__(
            f"cannot compose a canonical mission branch for {mission_handle!r}: "
            f"mission_id is absent and the slug carries no mid8 disambiguator. "
            f"{self.next_step}"
        )

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = super().to_dict()
        payload["mission_handle"] = self.mission_handle
        payload["next_step"] = self.next_step
        return payload


def mission_branch_name_required(mission_slug: str, mission_id: str | None) -> str:
    """Compose the canonical mission integration branch, fail-closed.

    Thin wrapper over :func:`mission_branch_name` that refuses to emit a
    wrong-but-plausible legacy ``kitty/mission-<slug>`` for a *modern* mission
    whose identity is lost. Dual-era rule (research-authority-seams.md §2.3):

    - ``mission_id`` present → mid8-era branch (``<human-slug>-<mid8>``).
    - ``mission_id`` absent, slug is legacy ``NNN-`` → legacy branch (correct;
      pre-083 missions never had a mid8).
    - ``mission_id`` absent, slug already carries a mid8 tail → legacy compose
      preserves the embedded disambiguator (resolvable).
    - ``mission_id`` absent, slug is modern (no ``NNN-`` prefix, no mid8 tail)
      → :class:`BranchIdentityUnresolved` (the only genuinely-wrong case).

    Args:
        mission_slug: Feature slug (e.g. ``"083-my-feature"`` or
            ``"my-feature-01KNXQS9"``).
        mission_id: Optional ULID read from ``meta.json``.

    Returns:
        The canonical mission branch name.

    Raises:
        BranchIdentityUnresolved: For an unresolvable modern identity.
    """
    if mission_id is not None:
        return mission_branch_name(mission_slug, mission_id=mission_id)
    # No mission_id: legacy form is only correct when the slug itself carries
    # identity — an NNN- numeric prefix (pre-083 mission) or an embedded mid8
    # tail. Otherwise the disambiguator is genuinely lost: fail closed.
    if _NUMERIC_PREFIX_RE.match(mission_slug) or mid8_from_slug(mission_slug):
        return mission_branch_name(mission_slug, mission_id=None)
    raise BranchIdentityUnresolved(mission_slug)


def resolve_transaction_mid8(
    mission_slug: str,
    *,
    mission_id: str | None,
    mid8: str | None,
    coordination_branch: str | None = None,
) -> str:
    """Resolve the mid8 that names a mission's on-disk transaction dir, or fail.

    The fail-closed authority for FR-007: the two transaction-identity sites
    (``coordination/status_transition.py`` and ``cli/commands/implement.py``)
    historically fabricated a zero-padded mid8 from the slug when no declared
    mid8 was available. That idiom invented a wrong-but-plausible on-disk
    transaction-dir name, mis-routing the lock/transaction target — the
    claim-time "Failed to resolve coordination worktree" defect.

    Cascade of declared sources (post-083 ``meta.json`` is authoritative):
    ``meta.mid8`` → ``mission_id[:8]`` → the mid8 embedded in the canonical
    ``<slug>-<mid8>`` slug tail.

    Dual-era + topology contract (research-authority-seams.md §2.3 / §3): both
    eras *resolve*; the fail-closed raise is reserved for the one case where a
    fabricated mid8 would actively mis-route a **coordination-topology** write:

    - explicit ``mid8`` → that mid8;
    - ``mission_id`` (>= 8 chars) → ``mission_id[:8]`` (single-derivation);
    - slug carrying a mid8 tail → the tail;
    - cascade exhausted AND a legacy ``\\d{3}-`` slug → ``""`` (the bare-slug
      surface). A pre-083 legacy mission never had a mid8; it is RESOLVABLE
      under the dual-era rule exactly as ``mission_branch_name_required``
      composes its legacy branch. It routes to the primary checkout / legacy
      bridge — there is no real mid8 to name a coord worktree, so the legacy
      carve-out applies even when a ``coordination_branch`` is declared;
    - cascade exhausted AND no ``coordination_branch`` (flattened / meta-less
      mission — no coord topology in play) → ``""`` (the bare-slug surface).
      This preserves the pre-fix routing for these missions, which fell through
      to the primary checkout / legacy bridge regardless of the fabricated mid8
      — there is no coord target to mis-route;
    - cascade exhausted AND a *modern* slug (no ``\\d{3}-`` prefix, no mid8 tail)
      AND a ``coordination_branch`` IS declared → :class:`BranchIdentityUnresolved`.
      This is the genuinely-wrong case: coordination topology requires a real
      mid8 to name its worktree/branch, and fabricating one would route the
      write to a coord surface that never existed. Run
      ``spec-kitty migrate backfill-identity``.

    The empty-string return is deliberate and load-bearing: it preserves the
    pre-fix behaviour for missions with no coordination topology (legacy,
    flattened, or orphaned-event post-merge recording) WITHOUT inventing a
    wrong-but-plausible coord dir name.

    Args:
        mission_slug: Feature slug (e.g. ``"my-feature-01KT3YBD"``).
        mission_id: Optional ULID read from ``meta.json``.
        mid8: Optional explicit ``mid8`` read from ``meta.json``.
        coordination_branch: The declared ``coordination_branch`` from
            ``meta.json`` (``None`` for legacy/flattened/meta-less missions).
            Gates the fail-closed: only a coord-topology mission with a lost
            mid8 raises.

    Returns:
        The resolved 8-character mid8 disambiguator, or ``""`` when no
        coordination topology is in play and the cascade is exhausted.

    Raises:
        BranchIdentityUnresolved: when a *modern* coordination-topology
            mission's mid8 cascade is exhausted (no ``\\d{3}-`` prefix, no mid8
            tail, no declared mid8/mission_id). Legacy ``\\d{3}-`` slugs resolve.
    """
    if mid8:
        return mid8
    if mission_id is not None and len(mission_id) >= 8:
        return mission_id[:8]
    slug_mid8 = mid8_from_slug(mission_slug)
    if slug_mid8:
        return slug_mid8
    # Cascade of declared/embedded mid8 sources is exhausted. A legacy ``NNN-``
    # slug is still RESOLVABLE (dual-era rule, FR-006): pre-083 missions never
    # had a mid8, and the sibling ``mission_branch_name_required`` composes a
    # valid legacy ``kitty/mission-<NNN-slug>`` branch for the same handle. It
    # routes to the bare-slug surface (empty mid8) — there is no real mid8 to
    # name a coord worktree, and the legacy mission falls through to the primary
    # checkout / legacy bridge exactly as it did pre-fix. This carve-out must
    # precede the coord-branch raise so a legacy coord-topology mission resolves
    # rather than wedging its status transition (#1898 F-1).
    if _NUMERIC_PREFIX_RE.match(mission_slug):
        return ""
    # Only a genuinely-unresolvable MODERN mission (no NNN- prefix, no mid8 tail)
    # with coordination topology declared fails closed — fabricating a mid8 would
    # mis-route its coord write (NFR-003: no new silent fallback for modern
    # slugs). Without coord topology there is no target to mis-route, so route to
    # the bare-slug surface (empty mid8) as the pre-fix code did.
    if coordination_branch:
        raise BranchIdentityUnresolved(mission_slug)
    return ""


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
        human_slug = _human_slug_for_mid8_branch(mission_slug, mission_id)
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
    body = branch_name[len(_MISSION_PREFIX):]
    return bool(body)


def is_lane_branch(branch_name: str) -> bool:
    """Return True if branch matches a lane branch pattern (legacy or new)."""
    return (
        _LEGACY_LANE_RE.match(branch_name) is not None
        or _NEW_LANE_RE.match(branch_name) is not None
    )


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
