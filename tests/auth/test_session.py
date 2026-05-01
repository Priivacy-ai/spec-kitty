"""Tests for ``specify_cli.auth.session`` (feature 080, WP01 T004).

Critical invariants covered:

- The identity field is ``email`` (sourced from ``/api/v1/me``) — NOT ``username``.
- ``refresh_token_expires_at`` is ``Optional[datetime]`` and round-trips both
  when set and when ``None``.
- ``is_refresh_token_expired()`` returns ``False`` when the expiry is ``None``
  (C-012 / D-9: the client never hardcodes a refresh TTL).
- No hardcoded "90 days" constants in this module.
"""

from __future__ import annotations

from datetime import datetime, timedelta, UTC
from pathlib import Path


from specify_cli.auth.session import (
    StoredSession,
    Team,
    get_private_team_id,
    pick_default_team_id,
    require_private_team_id,
)


def _now() -> datetime:
    return datetime.now(UTC)


def _make_session(
    *,
    refresh_token_expires_at: datetime | None,
    access_exp: datetime | None = None,
) -> StoredSession:
    now = _now()
    return StoredSession(
        user_id="user-abc",
        email="jane@example.com",
        name="Jane Doe",
        teams=[
            Team(id="team-1", name="Primary", role="owner", is_private_teamspace=True),
            Team(id="team-2", name="Secondary", role="member"),
        ],
        default_team_id="team-1",
        access_token="access-xyz",
        refresh_token="refresh-xyz",
        session_id="session-xyz",
        issued_at=now,
        access_token_expires_at=access_exp if access_exp is not None else now + timedelta(minutes=15),
        refresh_token_expires_at=refresh_token_expires_at,
        scope="openid profile email offline_access",
        storage_backend="file",
        last_used_at=now,
        auth_method="authorization_code",
    )


def test_session_has_email_field_not_username() -> None:
    session = _make_session(refresh_token_expires_at=None)
    assert session.email == "jane@example.com"
    assert not hasattr(session, "username")


def test_session_roundtrip_dict_with_refresh_expiry() -> None:
    future = _now() + timedelta(days=30)
    s = _make_session(refresh_token_expires_at=future)
    restored = StoredSession.from_dict(s.to_dict())
    assert restored == s
    assert restored.refresh_token_expires_at == future


def test_session_roundtrip_dict_without_refresh_expiry() -> None:
    s = _make_session(refresh_token_expires_at=None)
    d = s.to_dict()
    assert d["refresh_token_expires_at"] is None
    restored = StoredSession.from_dict(d)
    assert restored == s
    assert restored.refresh_token_expires_at is None


def test_session_roundtrip_json_with_refresh_expiry() -> None:
    future = _now() + timedelta(hours=5)
    s = _make_session(refresh_token_expires_at=future)
    restored = StoredSession.from_json(s.to_json())
    assert restored == s


def test_session_roundtrip_json_without_refresh_expiry() -> None:
    s = _make_session(refresh_token_expires_at=None)
    restored = StoredSession.from_json(s.to_json())
    assert restored == s
    assert restored.refresh_token_expires_at is None


def test_access_token_expired_no_buffer() -> None:
    past = _now() - timedelta(seconds=1)
    s = _make_session(refresh_token_expires_at=None, access_exp=past)
    assert s.is_access_token_expired() is True


def test_access_token_not_expired_when_in_future() -> None:
    future = _now() + timedelta(hours=1)
    s = _make_session(refresh_token_expires_at=None, access_exp=future)
    assert s.is_access_token_expired() is False
    assert s.is_access_token_expired(buffer_seconds=60) is False


def test_access_token_expired_with_buffer_catches_near_expiry() -> None:
    near = _now() + timedelta(seconds=5)
    s = _make_session(refresh_token_expires_at=None, access_exp=near)
    # With a 10-second buffer, a token expiring in 5s counts as expired.
    assert s.is_access_token_expired(buffer_seconds=10) is True


def test_is_refresh_token_expired_returns_false_when_none() -> None:
    """D-9: when the server does not communicate TTL, the client treats
    the refresh token as still valid; expiry is learned from 400 invalid_grant."""
    s = _make_session(refresh_token_expires_at=None)
    assert s.is_refresh_token_expired() is False


def test_is_refresh_token_expired_returns_true_when_past() -> None:
    past = _now() - timedelta(minutes=1)
    s = _make_session(refresh_token_expires_at=past)
    assert s.is_refresh_token_expired() is True


def test_is_refresh_token_expired_returns_false_when_future() -> None:
    future = _now() + timedelta(days=5)
    s = _make_session(refresh_token_expires_at=future)
    assert s.is_refresh_token_expired() is False


def test_touch_updates_last_used_at() -> None:
    s = _make_session(refresh_token_expires_at=None)
    old = s.last_used_at
    # Ensure the clock moves forward
    s.last_used_at = old - timedelta(hours=1)
    s.touch()
    assert s.last_used_at > old - timedelta(hours=1)


def test_team_roundtrip() -> None:
    t = Team(id="team-x", name="Team X", role="admin", is_private_teamspace=True)
    assert Team.from_dict(t.to_dict()) == t


def test_pick_default_team_id_prefers_private_teamspace() -> None:
    teams = [
        Team(id="team-1", name="Shared", role="member"),
        Team(id="team-2", name="Private", role="owner", is_private_teamspace=True),
    ]
    assert pick_default_team_id(teams) == "team-2"


def test_pick_default_team_id_falls_back_to_first_team() -> None:
    teams = [
        Team(id="team-1", name="Shared", role="member"),
        Team(id="team-2", name="Shared 2", role="owner"),
    ]
    assert pick_default_team_id(teams) == "team-1"


def test_get_private_team_id_returns_private_team_when_present() -> None:
    teams = [
        Team(id="team-1", name="Shared", role="member"),
        Team(id="team-2", name="Private", role="owner", is_private_teamspace=True),
    ]
    assert get_private_team_id(teams) == "team-2"


def test_get_private_team_id_returns_none_when_absent() -> None:
    teams = [
        Team(id="team-1", name="Shared", role="member"),
        Team(id="team-2", name="Shared 2", role="owner"),
    ]
    assert get_private_team_id(teams) is None


def test_no_hardcoded_90_days_in_session_module() -> None:
    """Guard against decision-D-9 regressions: no hardcoded refresh TTL."""
    module_path = Path(__file__).resolve().parents[2] / "src" / "specify_cli" / "auth" / "session.py"
    text = module_path.read_text(encoding="utf-8")
    assert "days=90" not in text
    assert "90 days" not in text
    assert "timedelta(days=90)" not in text


def test_from_dict_backward_compat_no_generation() -> None:
    """StoredSession.from_dict must not raise KeyError when 'generation' is absent (legacy sessions)."""
    d = _make_session(refresh_token_expires_at=None).to_dict()
    del d["generation"]
    session = StoredSession.from_dict(d)
    assert session.generation is None


def _make_session_with_teams(
    teams: list[Team], *, default_team_id: str | None = None
) -> StoredSession:
    """Build a StoredSession with a custom team list for require_private_team_id tests."""
    now = _now()
    return StoredSession(
        user_id="user-abc",
        email="jane@example.com",
        name="Jane Doe",
        teams=teams,
        default_team_id=default_team_id if default_team_id is not None else (teams[0].id if teams else ""),
        access_token="access-xyz",
        refresh_token="refresh-xyz",
        session_id="session-xyz",
        issued_at=now,
        access_token_expires_at=now + timedelta(minutes=15),
        refresh_token_expires_at=None,
        scope="openid profile email offline_access",
        storage_backend="file",
        last_used_at=now,
        auth_method="authorization_code",
    )


def test_require_private_team_id_returns_private_when_present() -> None:
    session = _make_session_with_teams(
        teams=[
            Team(id="t-shared-1", name="Shared 1", role="member", is_private_teamspace=False),
            Team(id="t-private", name="Private", role="owner", is_private_teamspace=True),
            Team(id="t-shared-2", name="Shared 2", role="member", is_private_teamspace=False),
        ],
    )
    assert require_private_team_id(session) == "t-private"


def test_require_private_team_id_returns_none_when_no_private_team() -> None:
    session = _make_session_with_teams(
        teams=[
            Team(id="t-shared-1", name="Shared 1", role="member", is_private_teamspace=False),
            Team(id="t-shared-2", name="Shared 2", role="member", is_private_teamspace=False),
        ],
    )
    assert require_private_team_id(session) is None


def test_require_private_team_id_ignores_default_team_id() -> None:
    """Even when default_team_id is set to a shared team, no private team in
    the list means we return None — never fall back to default_team_id."""
    session = _make_session_with_teams(
        default_team_id="t-shared-default",
        teams=[
            Team(id="t-shared-default", name="Shared Default", role="owner", is_private_teamspace=False),
            Team(id="t-shared-other", name="Shared Other", role="member", is_private_teamspace=False),
        ],
    )
    assert require_private_team_id(session) is None


def test_require_private_team_id_never_returns_first_team_fallback() -> None:
    """Even with teams[0] populated, no private team => None. No teams[0] fallback."""
    session = _make_session_with_teams(
        teams=[
            Team(id="t-first-shared", name="First Shared", role="owner", is_private_teamspace=False),
        ],
    )
    assert require_private_team_id(session) is None


def test_require_private_team_id_wins_over_drifting_default() -> None:
    """Regression for spec NFR-004: when default_team_id points at a shared team
    but the team list contains a Private Teamspace, return the private id."""
    session = _make_session_with_teams(
        default_team_id="t-shared-default",
        teams=[
            Team(id="t-shared-default", name="Shared Default", role="owner", is_private_teamspace=False),
            Team(id="t-private", name="Private", role="owner", is_private_teamspace=True),
        ],
    )
    assert require_private_team_id(session) == "t-private"


def test_session_with_empty_teams_list() -> None:
    """Sessions must handle the edge case where the user belongs to no team."""
    now = _now()
    s = StoredSession(
        user_id="u",
        email="x@example.com",
        name="X",
        teams=[],
        default_team_id="",
        access_token="a",
        refresh_token="r",
        session_id="s",
        issued_at=now,
        access_token_expires_at=now + timedelta(minutes=15),
        refresh_token_expires_at=None,
        scope="openid",
        storage_backend="file",
        last_used_at=now,
        auth_method="device_code",
    )
    restored = StoredSession.from_dict(s.to_dict())
    assert restored == s
    assert restored.teams == []
