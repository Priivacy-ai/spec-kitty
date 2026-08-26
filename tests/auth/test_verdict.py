"""Unit tests for the honest auth :class:`HealthVerdict` authority (#3723).

Covers the type-level invariants (evidence-required, headline-derived) and the
full decision ladder of both producers (``evaluate_auth_verdict`` /
``auth_verdict_from_flags``), including the load-bearing #3723 case: an expired
access token whose refresh chain is unproven offline is ``unknown``, never
``ok``.
"""

from __future__ import annotations

from dataclasses import replace

from kernel.clock import now_utc, timedelta

import pytest

from specify_cli.auth.session import StoredSession, Team
from specify_cli.auth.verdict import (
    HealthVerdict,
    auth_verdict_from_flags,
    evaluate_auth_verdict,
)

pytestmark = [pytest.mark.fast]


def _session(*, access_delta: timedelta, refresh_delta: timedelta | None) -> StoredSession:
    now = now_utc()
    return StoredSession(
        user_id="u",
        email="rob@example.com",
        name="Rob",
        teams=[Team(id="t1", name="Personal", role="owner", is_private_teamspace=True)],
        default_team_id="t1",
        access_token="at",
        refresh_token="rt",
        session_id="sid",
        issued_at=now,
        access_token_expires_at=now + access_delta,
        refresh_token_expires_at=None if refresh_delta is None else now + refresh_delta,
        scope="openid",
        storage_backend="file",
        last_used_at=now,
        auth_method="authorization_code",
    )


class _Probe:
    def __init__(self, *, active: bool, error: str | None = None) -> None:
        self.active = active
        self.error = error


# ---------------------------------------------------------------------------
# Type-level invariants
# ---------------------------------------------------------------------------


def test_headline_is_derived_from_state_not_settable() -> None:
    assert HealthVerdict(state="ok", evidence="x").headline == "Authenticated"
    assert HealthVerdict(state="unknown", evidence="").headline == "Cannot verify"
    assert HealthVerdict(state="fail", evidence="x").headline == "Not authenticated"
    # ``headline`` is a read-only computed property (no settable banner field).
    assert "headline" not in HealthVerdict(state="ok", evidence="x").__dict__


def test_evidence_required_for_definite_states() -> None:
    for state in ("ok", "fail"):
        with pytest.raises(ValueError):
            HealthVerdict(state=state, evidence="   ")  # type: ignore[arg-type]


def test_unknown_is_the_only_state_allowed_empty_evidence() -> None:
    # unknown is permitted to say "I could not check".
    assert HealthVerdict(state="unknown", evidence="").state == "unknown"


# ---------------------------------------------------------------------------
# evaluate_auth_verdict — decision ladder
# ---------------------------------------------------------------------------


def test_no_session_is_fail() -> None:
    v = evaluate_auth_verdict(None, now_utc())
    assert v.state == "fail"
    assert v.evidence
    assert v.remediation == "spec-kitty auth login"


def test_healthy_access_is_ok_and_names_both_windows() -> None:
    v = evaluate_auth_verdict(
        _session(access_delta=timedelta(minutes=15), refresh_delta=timedelta(days=30)),
        now_utc(),
    )
    assert v.state == "ok"
    assert "access valid" in v.evidence
    assert "refresh valid" in v.evidence


def test_refresh_expired_is_fail() -> None:
    v = evaluate_auth_verdict(
        _session(access_delta=timedelta(minutes=-1), refresh_delta=timedelta(days=-1)),
        now_utc(),
    )
    assert v.state == "fail"
    assert "refresh token expired" in v.evidence


def test_expired_access_valid_refresh_offline_is_unknown() -> None:
    """The #3723 fix: unproven refresh chain -> unknown, never ok."""
    v = evaluate_auth_verdict(
        _session(access_delta=timedelta(minutes=-1), refresh_delta=timedelta(days=30)),
        now_utc(),
    )
    assert v.state == "unknown"
    assert "expired" in v.evidence
    assert v.headline == "Cannot verify"


def test_expired_access_probe_live_is_ok() -> None:
    v = evaluate_auth_verdict(
        _session(access_delta=timedelta(minutes=-1), refresh_delta=timedelta(days=30)),
        now_utc(),
        server_probe=_Probe(active=True),
    )
    assert v.state == "ok"


def test_expired_access_probe_failed_is_fail() -> None:
    v = evaluate_auth_verdict(
        _session(access_delta=timedelta(minutes=-1), refresh_delta=timedelta(days=30)),
        now_utc(),
        server_probe=_Probe(active=False, error="Could not obtain access token."),
    )
    assert v.state == "fail"
    assert "Could not obtain access token." in v.evidence


def test_legacy_refresh_none_is_ok_when_access_valid() -> None:
    v = evaluate_auth_verdict(
        _session(access_delta=timedelta(minutes=15), refresh_delta=None),
        now_utc(),
    )
    assert v.state == "ok"
    assert "server-managed" in v.evidence


# ---------------------------------------------------------------------------
# auth_verdict_from_flags — I/O-free twin
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("session_present", "access_ok", "refresh_ok", "expected"),
    [
        (False, False, False, "fail"),
        (True, True, True, "ok"),
        (True, False, False, "fail"),
        (True, False, True, "unknown"),
    ],
)
def test_flags_ladder(session_present: bool, access_ok: bool, refresh_ok: bool, expected: str) -> None:
    v = auth_verdict_from_flags(
        session_present=session_present, access_ok=access_ok, refresh_ok=refresh_ok
    )
    assert v.state == expected


def test_flags_expired_access_with_live_probe_is_ok() -> None:
    v = auth_verdict_from_flags(
        session_present=True,
        access_ok=False,
        refresh_ok=True,
        server_probe=_Probe(active=True),
    )
    assert v.state == "ok"


def test_replace_preserves_headline_derivation() -> None:
    v = replace(HealthVerdict(state="ok", evidence="x"), state="unknown", evidence="")
    assert v.headline == "Cannot verify"
