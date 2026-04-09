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


from specify_cli.auth.session import StoredSession, Team


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
            Team(id="team-1", name="Primary", role="owner"),
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
        storage_backend="keychain",
        last_used_at=now,
        auth_method="authorization_code",
    )


def test_session_has_email_field_not_username():
    session = _make_session(refresh_token_expires_at=None)
    assert session.email == "jane@example.com"
    assert not hasattr(session, "username")


def test_session_roundtrip_dict_with_refresh_expiry():
    future = _now() + timedelta(days=30)
    s = _make_session(refresh_token_expires_at=future)
    restored = StoredSession.from_dict(s.to_dict())
    assert restored == s
    assert restored.refresh_token_expires_at == future


def test_session_roundtrip_dict_without_refresh_expiry():
    s = _make_session(refresh_token_expires_at=None)
    d = s.to_dict()
    assert d["refresh_token_expires_at"] is None
    restored = StoredSession.from_dict(d)
    assert restored == s
    assert restored.refresh_token_expires_at is None


def test_session_roundtrip_json_with_refresh_expiry():
    future = _now() + timedelta(hours=5)
    s = _make_session(refresh_token_expires_at=future)
    restored = StoredSession.from_json(s.to_json())
    assert restored == s


def test_session_roundtrip_json_without_refresh_expiry():
    s = _make_session(refresh_token_expires_at=None)
    restored = StoredSession.from_json(s.to_json())
    assert restored == s
    assert restored.refresh_token_expires_at is None


def test_access_token_expired_no_buffer():
    past = _now() - timedelta(seconds=1)
    s = _make_session(refresh_token_expires_at=None, access_exp=past)
    assert s.is_access_token_expired() is True


def test_access_token_not_expired_when_in_future():
    future = _now() + timedelta(hours=1)
    s = _make_session(refresh_token_expires_at=None, access_exp=future)
    assert s.is_access_token_expired() is False
    assert s.is_access_token_expired(buffer_seconds=60) is False


def test_access_token_expired_with_buffer_catches_near_expiry():
    near = _now() + timedelta(seconds=5)
    s = _make_session(refresh_token_expires_at=None, access_exp=near)
    # With a 10-second buffer, a token expiring in 5s counts as expired.
    assert s.is_access_token_expired(buffer_seconds=10) is True


def test_is_refresh_token_expired_returns_false_when_none():
    """D-9: when the server does not communicate TTL, the client treats
    the refresh token as still valid; expiry is learned from 400 invalid_grant."""
    s = _make_session(refresh_token_expires_at=None)
    assert s.is_refresh_token_expired() is False


def test_is_refresh_token_expired_returns_true_when_past():
    past = _now() - timedelta(minutes=1)
    s = _make_session(refresh_token_expires_at=past)
    assert s.is_refresh_token_expired() is True


def test_is_refresh_token_expired_returns_false_when_future():
    future = _now() + timedelta(days=5)
    s = _make_session(refresh_token_expires_at=future)
    assert s.is_refresh_token_expired() is False


def test_touch_updates_last_used_at():
    s = _make_session(refresh_token_expires_at=None)
    old = s.last_used_at
    # Ensure the clock moves forward
    s.last_used_at = old - timedelta(hours=1)
    s.touch()
    assert s.last_used_at > old - timedelta(hours=1)


def test_team_roundtrip():
    t = Team(id="team-x", name="Team X", role="admin")
    assert Team.from_dict(t.to_dict()) == t


def test_no_hardcoded_90_days_in_session_module():
    """Guard against decision-D-9 regressions: no hardcoded refresh TTL."""
    module_path = Path(__file__).resolve().parents[2] / "src" / "specify_cli" / "auth" / "session.py"
    text = module_path.read_text(encoding="utf-8")
    assert "days=90" not in text
    assert "90 days" not in text
    assert "timedelta(days=90)" not in text


def test_session_with_empty_teams_list():
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
