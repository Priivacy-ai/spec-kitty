"""Per-mission team snapshot: a closed, allowlist-filtered projection of the
existing ``StatusSnapshot`` machinery (§3.3 of the D1 contract draft).

Reuses ``status.reducer.materialize_snapshot`` (never reimplements event
reduction, §4 C1) and filters every per-WP state dict through a closed
allowlist so orchestration-only runtime slots (``shell_pid``,
``shell_pid_created_at``) and unbounded free-form prose (``notes``) can never
reach a team or public consumer (§4 N7/N8).
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from specify_cli.status.reducer import materialize_snapshot

from .provenance import ExactCommitProvenance, capture_provenance

#: Closed allowlist of per-WP state fields carried onto the TEAM projection.
#: Deliberately excludes ``shell_pid``/``shell_pid_created_at`` (host PID +
#: local spawn time — pure orchestration/runtime state with zero content
#: value outside the machine that spawned them) and ``notes`` (unbounded
#: free-form operator prose, unreviewed — same hazard class as F3's
#: forbidden-key set / Z8's human-gated review).
TEAM_WP_ALLOWED_FIELDS: frozenset[str] = frozenset(
    {
        "lane",
        "actor",
        "last_transition_at",
        "last_event_id",
        "force_count",
        "agent",
        "assignee",
        "role",
        "agent_profile",
        "agent_profile_version",
        "model",
        "provider",
        "review",
        "tracker_refs",
        "subtasks",
        # NOTE: a deliberate, evidence-grounded addition beyond the D1
        # contract draft's literal §3.3 listing. ``status/reducer.py``'s
        # ``_wp_state_from_event`` (T025/T026, WP07) writes ``review_result``
        # directly on the WP state dict — it is NOT a member of
        # ``_RUNTIME_SLOTS`` (so it is not carried by the same mechanism as
        # ``shell_pid``/``notes``) and is real, already-landed production
        # state, not a hypothetical future addition. Any mission WP that has
        # exited ``in_review`` carries this field; omitting it from the team
        # allowlist would make ``build_team_mission_snapshot`` raise
        # ``UnknownWPStateFieldError`` on ordinary reviewed WPs, not just on
        # the future-hazard case §4 N8 exists to catch. It carries a review
        # verdict (approve/reject + reason), the same disclosure class as the
        # already-allowed ``review`` field — not orchestration-state.
        "review_result",
    }
)

#: Fields ``status/reducer.py``'s ``_wp_state_from_event``/``_RUNTIME_SLOTS``
#: is known to write today that are DELIBERATELY excluded from
#: :data:`TEAM_WP_ALLOWED_FIELDS` (§2.1/§3.3: orchestration-only runtime
#: identifiers and unbounded free prose). These are silently dropped, never
#: raised on — they are the exact hazard the allowlist exists to filter, not
#: an unrecognized/unaccounted-for field. Anything OUTSIDE the union of this
#: set and :data:`TEAM_WP_ALLOWED_FIELDS` is genuinely unknown to this
#: module's model of the reducer's output shape (e.g. a future
#: ``_RUNTIME_SLOTS`` addition that has not yet been triaged into either
#: bucket) and MUST raise (§4 N8) rather than pass through open.
_KNOWN_BUT_EXCLUDED_WP_FIELDS: frozenset[str] = frozenset(
    {"shell_pid", "shell_pid_created_at", "notes"}
)

_ALL_RECOGNIZED_WP_FIELDS: frozenset[str] = TEAM_WP_ALLOWED_FIELDS | _KNOWN_BUT_EXCLUDED_WP_FIELDS


class UnknownWPStateFieldError(ValueError):
    """Raised when a WP state dict carries a key outside :data:`TEAM_WP_ALLOWED_FIELDS`.

    The allowlist is CLOSED, not an open denylist (§4 N8): a future
    ``_RUNTIME_SLOTS`` addition landing before this allowlist is updated must
    be caught here, not silently passed through to a team/public consumer.
    """


class TeamMissionSnapshot(BaseModel):
    """The team-scoped, closed per-mission snapshot artifact."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_: Literal["team_mission_snapshot/v1"] = Field(alias="schema")
    provenance: ExactCommitProvenance
    content_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    mission: dict[str, Any]


def _filter_wp_state(wp_state: dict[str, Any]) -> dict[str, Any]:
    unknown = set(wp_state.keys()) - _ALL_RECOGNIZED_WP_FIELDS
    if unknown:
        raise UnknownWPStateFieldError(
            "WP state dict carries field(s) outside TEAM_WP_ALLOWED_FIELDS: "
            f"{sorted(unknown)}"
        )
    return {key: wp_state[key] for key in TEAM_WP_ALLOWED_FIELDS if key in wp_state}


def _content_sha256(mission_body: dict[str, Any]) -> str:
    canonical = json.dumps(mission_body, sort_keys=True, separators=(",", ":"))
    # noqa justification: content-integrity digest for an attestation
    # manifest artifact (§3.3), not a charter-hashed doctrine artifact —
    # charter.hasher.hash_content() is the wrong tool here.
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()  # noqa: TID251


def build_team_mission_snapshot(
    feature_dir: Path,
    repo_root: Path,
    *,
    require_clean: bool = False,
) -> TeamMissionSnapshot:
    """Build the closed team-scoped snapshot for one mission.

    ``require_clean=False`` (the default) is the local/dashboard mode: always
    succeeds, ``provenance.tree_clean`` faithfully reports the scoped git
    status. ``require_clean=True`` is attestation-manifest mode: raises
    :class:`~specify_cli.team_projection.provenance.DirtyTreeError` and
    builds nothing when the scoped tree is not clean (§3.4).
    """
    snapshot = materialize_snapshot(feature_dir)
    mission_body = snapshot.to_dict()

    work_packages = mission_body.get("work_packages") or {}
    mission_body["work_packages"] = {
        wp_id: _filter_wp_state(wp_state) for wp_id, wp_state in work_packages.items()
    }

    provenance = capture_provenance(repo_root, require_clean=require_clean)

    return TeamMissionSnapshot(
        schema="team_mission_snapshot/v1",
        provenance=provenance,
        content_sha256=_content_sha256(mission_body),
        mission=mission_body,
    )
