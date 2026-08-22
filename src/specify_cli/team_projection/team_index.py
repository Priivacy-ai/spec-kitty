"""Cross-mission team index (§3.3 of the D1 contract draft).

A table of contents, not a bundle (§6.6): each entry carries a
``content_sha256`` pointer to that mission's own
:class:`~specify_cli.team_projection.mission_view.TeamMissionSnapshot`
rather than duplicating the mission body inline.

Ordering is ALWAYS ``dashboard.scanner.sort_missions_for_display`` output,
never raw registry-dict iteration (§2.1 gap, §4 N2) — ``Path.iterdir()``
order underneath ``gather_feature_paths`` is filesystem-dependent and not
guaranteed identical across two machines reading the same commit.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from specify_cli.core.paths import assert_safe_path_segment
from specify_cli.dashboard import scanner

from .mission_view import build_team_mission_snapshot
from .provenance import ExactCommitProvenance, capture_provenance


class TeamIndexEntry(BaseModel):
    """One table-of-contents row for a single mission."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    mission_id: str
    mission_slug: str
    display_number: int | None
    mid8: str | None
    summary: dict[str, int]
    content_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")


class TeamIndex(BaseModel):
    """The team-scoped, closed cross-mission index."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_: Literal["team_index/v1"] = Field(alias="schema")
    provenance: ExactCommitProvenance
    content_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    missions: tuple[TeamIndexEntry, ...]


def _content_sha256_of_entries(entries: tuple[dict[str, Any], ...]) -> str:
    import hashlib
    import json

    canonical = json.dumps(list(entries), sort_keys=True, separators=(",", ":"))
    # noqa justification: content-integrity digest for an attestation
    # manifest artifact (§3.3), not a charter-hashed doctrine artifact.
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()  # noqa: TID251


def resolve_feature_dir_for_mission_slug(project_dir: Path, mission_slug: str) -> Path:
    """Resolve the on-disk mission directory for a registry ``mission_slug``.

    Shared by ``attestation.py``/``write.py`` (which both need to re-resolve
    a mission's ``feature_dir`` from a :class:`TeamIndexEntry`, not just the
    registry key iterated here). Falls back to the conventional
    ``kitty-specs/<slug>`` layout for pseudo-keyed (legacy/orphan) missions
    whose registry key differs from the on-disk directory name — the
    directory name IS the ``mission_slug`` in every case
    (``build_mission_registry`` always sets it from ``feature_dir.name``,
    §2.1), so this fallback is exact, not a guess.

    This is the single chokepoint every caller in this package uses before
    joining ``mission_slug`` into any filesystem path (§3.1's declared
    ``specify_cli.core.paths.assert_safe_path_segment`` import surface,
    Renata D1-T1 review MEDIUM finding) — ``write.py``'s own
    ``derived_dir / entry.mission_slug / ...`` joins always run after this
    function has already validated the same ``entry.mission_slug`` value for
    that mission in the same publish run, so guarding here transitively
    guards those too. Raises ``ValueError`` (hard fail, never a silent
    downgrade) because a mission directory reaching this far has already
    been treated as a legitimate mission by the scanner; a hostile name at
    this point is a defense-in-depth backstop, not an expected input to
    degrade gracefully around.
    """
    assert_safe_path_segment(mission_slug)
    feature_paths: dict[str, Path] = scanner.gather_feature_paths(project_dir)
    resolved: Path | None = feature_paths.get(mission_slug)
    if resolved is not None:
        return resolved
    return project_dir / "kitty-specs" / mission_slug


def build_team_index(project_dir: Path, *, require_clean: bool = False) -> TeamIndex:
    """Build the closed, ordered cross-mission team index.

    ``require_clean=False`` (default) is local/dashboard mode; ``True`` is
    attestation-manifest mode (§3.4) — both modes share the one
    :func:`~specify_cli.team_projection.provenance.capture_provenance` call
    for ``project_dir`` used to stamp the shared envelope, and every
    per-mission snapshot build below uses the SAME ``require_clean`` value so
    a dirty tree fails the whole index build atomically, never partially.
    """
    registry = scanner.build_mission_registry(project_dir)
    ordered_keys = scanner.sort_missions_for_display(registry)

    entries: list[TeamIndexEntry] = []
    for key in ordered_keys:
        record = registry[key]
        feature_dir = Path(record["feature_dir"])
        snapshot = build_team_mission_snapshot(
            feature_dir, project_dir, require_clean=require_clean
        )
        entries.append(
            TeamIndexEntry(
                mission_id=record["mission_id"],
                mission_slug=record["mission_slug"],
                display_number=record["display_number"],
                mid8=record["mid8"],
                summary=dict(snapshot.mission.get("summary") or {}),
                content_sha256=snapshot.content_sha256,
            )
        )

    provenance = capture_provenance(project_dir, require_clean=require_clean)
    entry_dicts = tuple(entry.model_dump(mode="json") for entry in entries)

    return TeamIndex(
        schema="team_index/v1",
        provenance=provenance,
        content_sha256=_content_sha256_of_entries(entry_dicts),
        missions=tuple(entries),
    )
