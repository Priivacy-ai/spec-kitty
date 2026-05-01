"""Shared direct-ingress team-id resolver. NEVER fall back to a shared team.

This module is sync because the consumers (batch.py, queue.py, emitter.py) are sync;
the websocket call site (client.py) is inside an async function but invokes this
helper synchronously, no event-loop bridging needed.

See kitty-specs/private-teamspace-ingress-safeguards-01KQH03Y/contracts/api.md §4.
"""

from __future__ import annotations

import logging
from typing import Final, cast

from specify_cli.auth.session import require_private_team_id
from specify_cli.auth.token_manager import TokenManager

_LOG = logging.getLogger(__name__)

CATEGORY_MISSING_PRIVATE_TEAM: Final[str] = "direct_ingress_missing_private_team"


def resolve_private_team_id_for_ingress(
    token_manager: TokenManager,
    *,
    endpoint: str,
) -> str | None:
    """Return the Private Teamspace id for a direct-ingress request, else None. SYNC.

    Performs at most one /api/v1/me rehydrate per CLI process for shared-only sessions
    (single-flight + negative-cache enforced inside TokenManager). On a None return,
    emits a structured warning and the caller MUST NOT send the ingress request.

    Parameters
    ----------
    token_manager:
        The shared TokenManager instance.
    endpoint:
        The direct-ingress endpoint that triggered the resolution attempt.
        Recorded in the structured warning. Use exactly the path-only string
        (e.g. "/api/v1/events/batch/" or "/api/v1/ws-token").

    Returns
    -------
    str | None
        A Private Teamspace id when one is available, otherwise None.
    """
    session = token_manager.get_current_session()
    team_id: str | None = (
        cast("str | None", require_private_team_id(session))
        if session is not None
        else None
    )
    if team_id is not None:
        return team_id

    rehydrate_attempted = session is not None
    if rehydrate_attempted:
        token_manager.rehydrate_membership_if_needed()  # SYNC, no await
        session = token_manager.get_current_session()
        team_id = (
            cast("str | None", require_private_team_id(session))
            if session is not None
            else None
        )
        if team_id is not None:
            return team_id

    payload = {
        "category": CATEGORY_MISSING_PRIVATE_TEAM,
        "rehydrate_attempted": rehydrate_attempted,
        "ingress_sent": False,
        "endpoint": endpoint,
    }
    _LOG.warning("direct ingress skipped: %s", payload, extra=payload)
    return None
