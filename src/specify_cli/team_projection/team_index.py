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
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


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
