"""The canonical per-WP team-field allowlist seam (ex-D1 §2.1/§3.3).

The D1 projection pipeline (``team-index.json``, per-mission
``team-snapshot.json``, public variants, attestation manifest) was deleted with
the ``spec-kitty team-projection publish`` command: consumers read the tracked
repo directly instead of a published gitignored projection. What survives here
is the one piece another surface ports and must not re-derive by hand:
:data:`TEAM_WP_ALLOWED_FIELDS`, the closed allowlist of per-WP state fields a
team-facing consumer may see.

Team Kitty applies this allowlist on read when rendering WP detail from
committed ``status.json``/``tasks`` frontmatter; this module is its source of
truth.
"""

from __future__ import annotations

from typing import Any

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
        # allowlist would make the team view raise/drop on ordinary reviewed
        # WPs, not just on the future-hazard case §4 N8 exists to catch. It
        # carries a review verdict (approve/reject + reason), the same
        # disclosure class as the already-allowed ``review`` field — not
        # orchestration-state.
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


def _filter_wp_state(wp_state: dict[str, Any]) -> dict[str, Any]:
    unknown = set(wp_state.keys()) - _ALL_RECOGNIZED_WP_FIELDS
    if unknown:
        raise UnknownWPStateFieldError(
            "WP state dict carries field(s) outside TEAM_WP_ALLOWED_FIELDS: "
            f"{sorted(unknown)}"
        )
    return {key: wp_state[key] for key in TEAM_WP_ALLOWED_FIELDS if key in wp_state}
