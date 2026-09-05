"""Validation helpers for auth session payloads returned by SaaS."""

from __future__ import annotations

from typing import Any

from ..errors import AuthenticationError
from ..session import Team


def parse_me_payload(payload: Any) -> dict[str, Any]:
    """Validate that ``/api/v1/me`` returned an object payload."""
    if not isinstance(payload, dict):
        raise AuthenticationError("User info response must be a JSON object.")
    return payload


def require_me_field(me: dict[str, Any], field: str) -> Any:
    """Return a required ``/api/v1/me`` field or raise the auth error contract."""
    try:
        return me[field]
    except KeyError as exc:
        raise AuthenticationError(
            f"User info response missing required field '{field}'."
        ) from exc


def parse_me_teams(me: dict[str, Any]) -> list[Team]:
    """Parse required team fields from ``/api/v1/me`` without leaking KeyError."""
    raw_teams = me.get("teams", [])
    if not isinstance(raw_teams, list):
        raise AuthenticationError("User info response field 'teams' must be a list.")

    teams: list[Team] = []
    for raw_team in raw_teams:
        if not isinstance(raw_team, dict):
            raise AuthenticationError("User info response team entry must be an object.")
        try:
            teams.append(
                Team(
                    id=raw_team["id"],
                    name=raw_team["name"],
                    role=raw_team["role"],
                    is_private_teamspace=bool(
                        raw_team.get("is_private_teamspace", False)
                    ),
                )
            )
        except KeyError as exc:
            raise AuthenticationError(
                f"User info response missing required team field '{exc.args[0]}'."
            ) from exc
    return teams
