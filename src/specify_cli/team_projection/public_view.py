"""Explicit-opt-in public projection (§3.3 of the D1 contract draft).

Public output is absent unless explicitly opted in via the tracked
``.kittify/config.yaml`` ``public_projection.enabled`` key — never an
environment variable, and never a reuse of the SaaS-sync opt-in axis (§2.3,
§6.3): a config key under a ``TRACKED``/``AUTHORITATIVE`` file means the
opt-in decision is itself commit-provenanced.

Every field allowed on a public artifact MUST also be allowed on its team
counterpart (§3.3's normative closed-schema relation, enforced statically by
``tests/team_projection/test_public_view.py``'s N9 rows) — public is always a
narrowing projection of team, never a sibling vocabulary.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field
from ruamel.yaml import YAML

from .mission_view import TEAM_WP_ALLOWED_FIELDS, TeamMissionSnapshot
from .provenance import ExactCommitProvenance
from .team_index import TeamIndex

#: Deliberately narrower than TEAM_WP_ALLOWED_FIELDS: no actor/agent/role/
#: model/provider/review/assignee/tracker_refs/subtasks/review_result on the
#: public variant (§3.3 decision 7 — smallest defensible surface; a public
#: viewer needs mission progress, not which human or agent worked which WP).
PUBLIC_WP_ALLOWED_FIELDS: frozenset[str] = frozenset({"lane", "last_transition_at"})

#: Top-level mission-identity fields carried onto the public mission
#: snapshot. Narrower than the team snapshot's full ``mission`` dict (which
#: additionally carries event_count/last_event_id/work_packages/summary at
#: the top level) -- those non-identity fields are handled separately below
#: (``work_packages``/``summary`` are always carried, filtered; the rest are
#: dropped as not criterion-named for public consumption).
PUBLIC_MISSION_ALLOWED_FIELDS: frozenset[str] = frozenset(
    {"mission_slug", "mission_number", "mission_type"}
)

#: Public index row fields. "mid8" and "content_sha256" are excluded from the
#: public index; "content_sha256" still appears inside PublicMissionSnapshot
#: itself (§3.3).
PUBLIC_INDEX_ALLOWED_FIELDS: frozenset[str] = frozenset(
    {"mission_id", "mission_slug", "display_number", "summary"}
)

assert PUBLIC_WP_ALLOWED_FIELDS <= TEAM_WP_ALLOWED_FIELDS


class PublicMissionSnapshot(BaseModel):
    """The public-scoped, closed per-mission snapshot artifact."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_: Literal["public_mission_snapshot/v1"] = Field(alias="schema")
    provenance: ExactCommitProvenance
    content_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    mission: dict[str, Any]


class PublicIndex(BaseModel):
    """The public-scoped, closed cross-mission index artifact."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_: Literal["public_index/v1"] = Field(alias="schema")
    provenance: ExactCommitProvenance
    content_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    missions: tuple[dict[str, Any], ...]


def is_public_projection_enabled(project_dir: Path) -> bool:
    """Read ``.kittify/config.yaml``'s ``public_projection.enabled`` key.

    Fail-closed (§4 N4/N5): a missing file, a missing key, a non-bool value,
    or malformed YAML all return ``False``. Never reads an environment
    variable (§6.3) — an env var would let two machines building the same
    commit disagree on whether public output exists, undermining the
    "provenance" story by making the opt-in state itself non-reproducible
    from the commit alone.
    """
    config_path = project_dir / ".kittify" / "config.yaml"
    if not config_path.exists():
        return False

    try:
        yaml = YAML(typ="safe")
        with config_path.open(encoding="utf-8") as fh:
            data = yaml.load(fh)
    except Exception:
        return False

    if not isinstance(data, dict):
        return False

    section = data.get("public_projection")
    if not isinstance(section, dict):
        return False

    enabled = section.get("enabled")
    if not isinstance(enabled, bool):
        return False

    return enabled


def _content_sha256(body: Any) -> str:
    import hashlib
    import json

    canonical = json.dumps(body, sort_keys=True, separators=(",", ":"))
    # noqa justification: content-integrity digest for an attestation
    # manifest artifact (§3.3), not a charter-hashed doctrine artifact.
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()  # noqa: TID251


def project_public_mission_snapshot(
    team: TeamMissionSnapshot,
) -> PublicMissionSnapshot:
    """Pure allowlist projection of ``team`` onto the public field sets.

    This is the ONLY code path permitted to narrow a team artifact to a
    public one (§3.3) — no writer constructs a ``Public*`` model any other
    way. Callers are responsible for checking
    :func:`is_public_projection_enabled` first (the write path, ``write.py``,
    is the only production caller and always checks first) — this function
    itself performs no opt-in check, so it stays a pure, trivially-testable
    projection.
    """
    mission = team.mission
    projected_mission: dict[str, Any] = {
        key: mission[key] for key in PUBLIC_MISSION_ALLOWED_FIELDS if key in mission
    }
    work_packages = mission.get("work_packages") or {}
    projected_mission["work_packages"] = {
        wp_id: {k: v for k, v in wp_state.items() if k in PUBLIC_WP_ALLOWED_FIELDS}
        for wp_id, wp_state in work_packages.items()
    }
    if "summary" in mission:
        projected_mission["summary"] = mission["summary"]

    return PublicMissionSnapshot(
        schema="public_mission_snapshot/v1",
        provenance=team.provenance,
        content_sha256=_content_sha256(projected_mission),
        mission=projected_mission,
    )


def project_public_index(team: TeamIndex) -> PublicIndex:
    """Pure allowlist projection of a :class:`TeamIndex` onto the public
    index shape: each row filtered to :data:`PUBLIC_INDEX_ALLOWED_FIELDS`,
    same order as the team index (§3.3)."""
    missions = tuple(
        {
            key: value
            for key, value in entry.model_dump(mode="json").items()
            if key in PUBLIC_INDEX_ALLOWED_FIELDS
        }
        for entry in team.missions
    )
    return PublicIndex(
        schema="public_index/v1",
        provenance=team.provenance,
        content_sha256=_content_sha256(list(missions)),
        missions=missions,
    )
