"""Mission handle resolver: maps user-supplied handles to canonical mission identity.

Resolution priority (most-specific → least-specific):

1. **Full mission_id** (26-char ULID): exact match on ``meta.json.mission_id``
2. **mid8 prefix** (8 chars): match on ``mission_id[:8]``
3. **Full slug with numeric prefix** (e.g. ``"083-foo-bar"``): directory name match
4. **Human slug without prefix** (e.g. ``"foo-bar"``): stripped slug match
5. **Numeric prefix alone** (e.g. ``"083"``): directory prefix match

If a handle unambiguously identifies one mission at any priority level, it is
returned immediately.  If it matches multiple missions, ``AmbiguousHandleError``
is raised with the full candidate list.  If it matches zero missions at any
level, the resolver falls through to the next level; if all levels are
exhausted without a match, ``MissionNotFoundError`` is raised.

Missions whose ``meta.json`` lacks a ``mission_id`` are silently skipped during
index construction (they cannot be resolved by identity).  To fix such missions,
run ``spec-kitty migrate backfill-identity``.

Implementation note: ``kitty-specs/`` is walked once per ``resolve_mission``
call.  The resulting in-memory index is not cached across calls because the
resolver is used in short-lived CLI commands; caching can be added later if
profiling shows it is needed.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from specify_cli.lanes.branch_naming import strip_numeric_prefix

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_ULID_RE = re.compile(r"^[0-9A-Z]{26}$")
_MID8_RE = re.compile(r"^[0-9A-Z]{8}$")
_PREFIX_RE = re.compile(r"^(\d{3})-")

# ---------------------------------------------------------------------------
# Public data types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ResolvedMission:
    """Canonical resolved identity for a single mission.

    Attributes:
        mission_id: Full 26-character ULID string from ``meta.json``.
        mission_slug: Directory name in ``kitty-specs/`` (e.g. ``"083-foo-bar"``).
        feature_dir: Absolute path to the mission directory.
        mid8: First 8 characters of ``mission_id`` (short disambiguator).
    """

    mission_id: str
    mission_slug: str
    feature_dir: Path
    mid8: str


class AmbiguousHandleError(Exception):
    """Raised when a handle matches more than one mission.

    Attributes:
        handle: The user-supplied handle that was ambiguous.
        candidates: All missions matched by the handle.
    """

    def __init__(self, handle: str, candidates: list[ResolvedMission]) -> None:
        self.handle = handle
        self.candidates = candidates
        super().__init__(str(self))

    def __str__(self) -> str:
        lines = [
            f'Error: mission handle "{self.handle}" matches multiple missions.',
            "",
            "Candidates:",
        ]
        for c in self.candidates:
            lines.append(f"  {c.mission_slug} (mission_id {c.mission_id}, mid8 {c.mid8})")
        lines.append("")
        lines.append("Re-run with a more specific handle:")
        for c in self.candidates:
            lines.append(f"  spec-kitty <command> --mission {c.mid8}")
            lines.append(f"  spec-kitty <command> --mission {c.mission_slug}")
        lines.append("")
        lines.append("For JSON output of all candidates:")
        lines.append(f'  spec-kitty doctor identity --mission {self.handle} --json')
        return "\n".join(lines)

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-serialisable error payload for ``--json`` callers."""
        return {
            "error": "ambiguous_mission_handle",
            "handle": self.handle,
            "candidates": [
                {
                    "mission_id": c.mission_id,
                    "mid8": c.mid8,
                    "slug": c.mission_slug,
                    "feature_dir": str(c.feature_dir),
                }
                for c in self.candidates
            ],
        }


class MissionNotFoundError(Exception):
    """Raised when no mission matches the supplied handle.

    Attributes:
        handle: The user-supplied handle that matched nothing.
    """

    def __init__(self, handle: str) -> None:
        self.handle = handle
        super().__init__(f'No mission found for handle "{handle}".')


# ---------------------------------------------------------------------------
# Internal: index construction
# ---------------------------------------------------------------------------


def _build_index(repo_root: Path) -> list[ResolvedMission]:
    """Walk ``kitty-specs/`` and return a list of indexable missions.

    Missions whose ``meta.json`` lacks a ``mission_id`` are silently skipped.
    Non-directory entries (e.g. ``README.md``) are also skipped.
    """
    specs_dir = repo_root / "kitty-specs"
    if not specs_dir.exists():
        return []

    missions: list[ResolvedMission] = []
    for entry in sorted(specs_dir.iterdir()):
        if not entry.is_dir():
            continue
        meta_path = entry / "meta.json"
        if not meta_path.exists():
            continue
        try:
            data = json.loads(meta_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        mission_id: str | None = data.get("mission_id") or None
        if not mission_id:
            # Legacy mission without mission_id — cannot be resolved by identity.
            # Operator must run `spec-kitty migrate backfill-identity`.
            continue
        missions.append(
            ResolvedMission(
                mission_id=mission_id,
                mission_slug=entry.name,
                feature_dir=entry,
                mid8=mission_id[:8],
            )
        )
    return missions


# ---------------------------------------------------------------------------
# Internal: form classifiers
# ---------------------------------------------------------------------------


def _is_full_ulid(handle: str) -> bool:
    """Return True if the handle looks like a full 26-char ULID."""
    return bool(_ULID_RE.match(handle))


def _is_mid8(handle: str) -> bool:
    """Return True if the handle looks like a mid8 (8 uppercase alphanumeric chars)."""
    return bool(_MID8_RE.match(handle))


def _is_numeric_prefix(handle: str) -> bool:
    """Return True if the handle is a pure digit string (e.g. '083')."""
    return handle.isdigit()


# ---------------------------------------------------------------------------
# Public resolver
# ---------------------------------------------------------------------------


def resolve_mission(handle: str, repo_root: Path) -> ResolvedMission:
    """Resolve a user-supplied handle to a canonical mission.

    Resolution priority (see module docstring):
    1. Full mission_id (26-char ULID)
    2. mid8 prefix (8 chars of upper alphanumeric)
    3. Full slug with numeric prefix (directory name)
    4. Human slug without prefix
    5. Numeric prefix alone (all-digits handle)

    Args:
        handle: A mission handle in any supported form.
        repo_root: Absolute path to the repository root.

    Returns:
        The uniquely resolved :class:`ResolvedMission`.

    Raises:
        AmbiguousHandleError: The handle matches more than one mission.
        MissionNotFoundError: The handle matches no mission.
    """
    missions = _build_index(repo_root)

    # ------------------------------------------------------------------
    # Priority 1: Full mission_id (exact 26-char ULID)
    # ------------------------------------------------------------------
    if _is_full_ulid(handle):
        matches = [m for m in missions if m.mission_id == handle]
        return _resolve_or_raise(handle, matches)

    # ------------------------------------------------------------------
    # Priority 2: mid8 prefix (8 uppercase alphanum chars)
    # Note: also catches shorter unique prefixes (partial mid8) via startswith.
    # ------------------------------------------------------------------
    if _is_mid8(handle):
        matches = [m for m in missions if m.mission_id.startswith(handle)]
        return _resolve_or_raise(handle, matches)

    # ------------------------------------------------------------------
    # Priority 3: Full slug with numeric prefix (e.g. "083-foo-bar")
    # ------------------------------------------------------------------
    matches = [m for m in missions if m.mission_slug == handle]
    if matches:
        return _resolve_or_raise(handle, matches)

    # ------------------------------------------------------------------
    # Priority 4: Human slug without numeric prefix (e.g. "foo-bar")
    # ------------------------------------------------------------------
    if not _is_numeric_prefix(handle):
        human_matches = [
            m for m in missions if strip_numeric_prefix(m.mission_slug) == handle
        ]
        if human_matches:
            return _resolve_or_raise(handle, human_matches)

    # ------------------------------------------------------------------
    # Priority 5: Numeric prefix (all-digits string, e.g. "083")
    # ------------------------------------------------------------------
    if _is_numeric_prefix(handle):
        prefix_matches = [
            m for m in missions if _PREFIX_RE.match(m.mission_slug) and
            _PREFIX_RE.match(m.mission_slug).group(1) == handle  # type: ignore[union-attr]
        ]
        return _resolve_or_raise(handle, prefix_matches)

    raise MissionNotFoundError(handle)


# ---------------------------------------------------------------------------
# Internal: resolve-or-raise helper
# ---------------------------------------------------------------------------


def _resolve_or_raise(handle: str, matches: list[ResolvedMission]) -> ResolvedMission:
    """Return the single match, raise on zero or multiple matches."""
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        raise AmbiguousHandleError(handle, matches)
    raise MissionNotFoundError(handle)
