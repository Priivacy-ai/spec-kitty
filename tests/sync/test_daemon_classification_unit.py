"""Unit tests for the sync-daemon cleanup classification engine.

Covers every row (1–9) of the normative decision table in
``data-model.md``, plus the three invariants called out in the WP:

* FR-008 — same scope, older ``package_version`` → ``safe_auto``
* D-01   — in-scope but ``health=None`` (or not responded) → ``operator_required/unresponsive``
* FR-003 — ``owner_present=True`` with no scope marker still → ``operator_required/pre_marker``
           (owner record does not rescue a pre-marker daemon)

All tests are pure (no subprocesses, no sockets, no filesystem).
"""

from __future__ import annotations

import pytest

from specify_cli.sync.classification import (
    CandidateProbe,
    CleanupClass,
    DaemonIdentityRecord,
    ForegroundScope,
    HealthProbe,
    IdentitySource,
    SingletonRef,
    SkipReason,
    classify_candidate,
)

# Module-level marker so the CI gate-coverage selector picks these pure unit
# tests up (every test file must declare a module-level ``pytestmark``).
pytestmark = [pytest.mark.unit, pytest.mark.fast]

# ---------------------------------------------------------------------------
# Test fixtures / builders
# ---------------------------------------------------------------------------

_SCOPE = "/Users/alice/.spec-kitty"
_OTHER_SCOPE = "/Users/bob/.spec-kitty"
_SINGLETON_PID = 9000
_SINGLETON_PORT = 9400
_ORPHAN_PID = 9001
_ORPHAN_PORT = 9401


def _foreground(
    scope_id: str = _SCOPE,
    singleton_pid: int | None = _SINGLETON_PID,
    singleton_port: int | None = _SINGLETON_PORT,
) -> ForegroundScope:
    return ForegroundScope(
        scope_id=scope_id,
        executable_scope="/usr/bin/python3",
        singleton=SingletonRef(pid=singleton_pid, port=singleton_port),
    )


def _health(
    *,
    responded: bool = True,
    owner_pid: int | None = _ORPHAN_PID,
    owner_port: int | None = _ORPHAN_PORT,
    package_version: str | None = "3.2.4",
    protocol_version: int | None = 1,
    daemon_family: str | None = "sync",
) -> HealthProbe:
    return HealthProbe(
        responded=responded,
        status="ok" if responded else None,
        protocol_version=protocol_version,
        package_version=package_version,
        daemon_family=daemon_family,
        owner_pid=owner_pid,
        owner_port=owner_port,
        queue_db_path="/Users/alice/.spec-kitty/queues/queue-aaaa.db",
        auth_scope="https://api.example.com|alice@example.com|t-private",
        server_url="https://api.example.com",
    )


def _probe(
    *,
    port: int = _ORPHAN_PORT,
    listener_pid: int | None = _ORPHAN_PID,
    health: HealthProbe | None = None,
    singleton_scope_id: str | None = _SCOPE,
    spawn_shape_ok: bool = True,
    executable_summary: str | None = "/usr/bin/python3",
    owner_present: bool = False,
) -> CandidateProbe:
    return CandidateProbe(
        port=port,
        listener_pid=listener_pid,
        health=health,
        singleton_scope_id=singleton_scope_id,
        spawn_shape_ok=spawn_shape_ok,
        executable_summary=executable_summary,
        owner_present=owner_present,
    )


# ---------------------------------------------------------------------------
# Row 1 — port out of range → never_touch / out_of_range
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_row1_out_of_range_below() -> None:
    """Port below 9400 → never_touch / out_of_range."""
    result = classify_candidate(_probe(port=9399), _foreground())
    assert result.cleanup_class == CleanupClass.NEVER_TOUCH
    assert result.skip_reason == SkipReason.out_of_range
    assert result.port == 9399


@pytest.mark.unit
def test_row1_out_of_range_above() -> None:
    """Port 9450 (= start + 50, exclusive) → never_touch / out_of_range."""
    result = classify_candidate(_probe(port=9450), _foreground())
    assert result.cleanup_class == CleanupClass.NEVER_TOUCH
    assert result.skip_reason == SkipReason.out_of_range


@pytest.mark.unit
def test_row1_out_of_range_way_above() -> None:
    """Arbitrary high port → never_touch / out_of_range."""
    result = classify_candidate(_probe(port=9999), _foreground())
    assert result.cleanup_class == CleanupClass.NEVER_TOUCH
    assert result.skip_reason == SkipReason.out_of_range


# ---------------------------------------------------------------------------
# Row 2 — not identifiable as SK sync → never_touch
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_row2_not_spec_kitty_no_response() -> None:
    """No spawn-shape and listener did not respond → never_touch / not_spec_kitty."""
    p = _probe(
        spawn_shape_ok=False,
        health=None,
        singleton_scope_id=None,
    )
    result = classify_candidate(p, _foreground())
    assert result.cleanup_class == CleanupClass.NEVER_TOUCH
    assert result.skip_reason == SkipReason.not_spec_kitty


@pytest.mark.unit
def test_row2_third_party_foreign_health() -> None:
    """No spawn-shape but a foreign (non-SK) health response → never_touch / third_party."""
    foreign_health = HealthProbe(
        responded=True,
        status="ok",
        protocol_version=None,  # missing SK protocol_version
        package_version=None,
        daemon_family=None,
        owner_pid=None,
        owner_port=None,
        queue_db_path=None,
        auth_scope=None,
        server_url=None,
    )
    p = _probe(
        spawn_shape_ok=False,
        health=foreign_health,
        singleton_scope_id=None,
    )
    result = classify_candidate(p, _foreground())
    assert result.cleanup_class == CleanupClass.NEVER_TOUCH
    assert result.skip_reason == SkipReason.third_party


@pytest.mark.unit
def test_row2b_health_and_marker_without_spawn_shape_never_touch() -> None:
    """Health-shaped response plus scope marker is not signalable without spawn shape."""
    p = _probe(
        spawn_shape_ok=False,
        singleton_scope_id=_SCOPE,
        health=_health(owner_pid=_ORPHAN_PID, owner_port=_ORPHAN_PORT),
    )
    result = classify_candidate(p, _foreground())
    assert result.cleanup_class == CleanupClass.NEVER_TOUCH
    assert result.skip_reason == SkipReason.third_party


# ---------------------------------------------------------------------------
# Row 3 — is the recorded singleton → excluded from cleanup
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_row3_is_recorded_singleton() -> None:
    """Candidate PID/port matches the singleton state-file entry → excluded."""
    # Probe with the singleton's PID/port; the foreground singleton matches.
    p = _probe(
        port=_SINGLETON_PORT,
        listener_pid=_SINGLETON_PID,
        health=_health(owner_pid=_SINGLETON_PID, owner_port=_SINGLETON_PORT),
        singleton_scope_id=_SCOPE,
    )
    result = classify_candidate(p, _foreground())
    assert result.cleanup_class == CleanupClass.NEVER_TOUCH
    assert result.skip_reason == SkipReason.is_recorded_singleton
    assert result.is_recorded_singleton is True


@pytest.mark.unit
def test_row3_highest_port_singleton() -> None:
    """Singleton on port 9449 (last in range) is never cleaned."""
    foreground = _foreground(singleton_pid=7777, singleton_port=9449)
    p = _probe(
        port=9449,
        listener_pid=7777,
        health=_health(owner_pid=7777, owner_port=9449),
        singleton_scope_id=_SCOPE,
    )
    result = classify_candidate(p, foreground)
    assert result.skip_reason == SkipReason.is_recorded_singleton


# ---------------------------------------------------------------------------
# Row 4 — cannot determine PID → operator_required / missing_pid
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_row4_missing_pid() -> None:
    """``listener_pid=None`` → operator_required / missing_pid."""
    p = _probe(listener_pid=None, singleton_scope_id=_SCOPE)
    result = classify_candidate(p, _foreground())
    assert result.cleanup_class == CleanupClass.OPERATOR_REQUIRED
    assert result.skip_reason == SkipReason.missing_pid
    assert result.pid is None


# ---------------------------------------------------------------------------
# Row 5 — no daemon-root marker → operator_required / pre_marker
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_row5_pre_marker_no_scope() -> None:
    """``singleton_scope_id=None`` → operator_required / pre_marker."""
    p = _probe(singleton_scope_id=None, health=_health())
    result = classify_candidate(p, _foreground())
    assert result.cleanup_class == CleanupClass.OPERATOR_REQUIRED
    assert result.skip_reason == SkipReason.pre_marker


# FR-003 invariant: owner_present does not rescue a pre-marker daemon.
@pytest.mark.unit
def test_fr003_owner_present_does_not_rescue_pre_marker() -> None:
    """owner_present=True with no scope marker → still operator_required/pre_marker."""
    p = _probe(
        singleton_scope_id=None,
        owner_present=True,  # owner.json exists — must NOT influence the verdict
        health=_health(),
    )
    result = classify_candidate(p, _foreground())
    assert result.cleanup_class == CleanupClass.OPERATOR_REQUIRED
    assert result.skip_reason == SkipReason.pre_marker
    # owner_present is carried through to the record for reporting
    assert result.owner_present is True


# ---------------------------------------------------------------------------
# Row 6 — scope marker present but wrong root → operator_required / cross_root
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_row6_cross_root() -> None:
    """Scope marker identifies a different runtime root → operator_required / cross_root."""
    p = _probe(singleton_scope_id=_OTHER_SCOPE, health=_health())
    result = classify_candidate(p, _foreground())
    assert result.cleanup_class == CleanupClass.OPERATOR_REQUIRED
    assert result.skip_reason == SkipReason.cross_root


# ---------------------------------------------------------------------------
# Row 7 — wedged / no live health self-report → operator_required / unresponsive
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_row7_health_none_unresponsive() -> None:
    """``health=None`` (caller could not probe) → operator_required / unresponsive (D-01)."""
    p = _probe(health=None, singleton_scope_id=_SCOPE)
    result = classify_candidate(p, _foreground())
    assert result.cleanup_class == CleanupClass.OPERATOR_REQUIRED
    assert result.skip_reason == SkipReason.unresponsive


@pytest.mark.unit
def test_row7_health_not_responded() -> None:
    """``health.responded=False`` (timed-out probe) → operator_required / unresponsive (D-01)."""
    silent = HealthProbe(
        responded=False,
        status=None,
        protocol_version=None,
        package_version=None,
        daemon_family=None,
        owner_pid=None,
        owner_port=None,
        queue_db_path=None,
        auth_scope=None,
        server_url=None,
    )
    p = _probe(health=silent, singleton_scope_id=_SCOPE)
    result = classify_candidate(p, _foreground())
    assert result.cleanup_class == CleanupClass.OPERATOR_REQUIRED
    assert result.skip_reason == SkipReason.unresponsive


# D-01 alias: must be unit-tagged with the explicit invariant name.
@pytest.mark.unit
def test_d01_wedged_listener_is_operator_required() -> None:
    """D-01: in-scope but wedged listener is never safe_auto."""
    p = _probe(
        port=9402,
        listener_pid=9002,
        health=None,
        singleton_scope_id=_SCOPE,
        spawn_shape_ok=True,
    )
    result = classify_candidate(p, _foreground())
    assert result.cleanup_class == CleanupClass.OPERATOR_REQUIRED
    assert result.skip_reason == SkipReason.unresponsive


# ---------------------------------------------------------------------------
# Row 8 — health pid/port ≠ listener → operator_required / pid_port_mismatch
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_row8_pid_port_mismatch_pid() -> None:
    """Health reports a different PID than the actual listener → operator_required."""
    mismatched = _health(owner_pid=99999, owner_port=_ORPHAN_PORT)
    p = _probe(health=mismatched, singleton_scope_id=_SCOPE)
    result = classify_candidate(p, _foreground())
    assert result.cleanup_class == CleanupClass.OPERATOR_REQUIRED
    assert result.skip_reason == SkipReason.pid_port_mismatch
    assert result.self_report_matches_listener is False


@pytest.mark.unit
def test_row8_pid_port_mismatch_port() -> None:
    """Health reports a different port than the actual listener → operator_required."""
    mismatched = _health(owner_pid=_ORPHAN_PID, owner_port=9402)
    p = _probe(health=mismatched, singleton_scope_id=_SCOPE)
    result = classify_candidate(p, _foreground())
    assert result.cleanup_class == CleanupClass.OPERATOR_REQUIRED
    assert result.skip_reason == SkipReason.pid_port_mismatch


# ---------------------------------------------------------------------------
# Row 9 — all guards passed → safe_auto
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_row9_safe_auto_happy_path() -> None:
    """All decision-table guards pass → safe_auto (no skip_reason)."""
    p = _probe(
        port=_ORPHAN_PORT,
        listener_pid=_ORPHAN_PID,
        health=_health(owner_pid=_ORPHAN_PID, owner_port=_ORPHAN_PORT),
        singleton_scope_id=_SCOPE,
        spawn_shape_ok=True,
    )
    result = classify_candidate(p, _foreground())
    assert result.cleanup_class == CleanupClass.SAFE_AUTO
    assert result.skip_reason is None
    assert result.self_report_matches_listener is True
    assert result.identity_source == IdentitySource.health_self_report


@pytest.mark.unit
def test_row9_safe_auto_port_9449() -> None:
    """Highest valid port (9449) passes through to safe_auto."""
    pid = 9049
    p = _probe(
        port=9449,
        listener_pid=pid,
        health=_health(owner_pid=pid, owner_port=9449),
        singleton_scope_id=_SCOPE,
    )
    result = classify_candidate(p, _foreground())
    assert result.cleanup_class == CleanupClass.SAFE_AUTO
    assert result.skip_reason is None


# FR-008 — version mismatch allowed once scope is proven.
@pytest.mark.unit
def test_fr008_older_version_still_safe_auto() -> None:
    """FR-008: older package_version with same scope → safe_auto (not skipped)."""
    older_version_health = _health(
        owner_pid=_ORPHAN_PID,
        owner_port=_ORPHAN_PORT,
        package_version="3.2.2",  # older than current "3.2.4"
    )
    p = _probe(
        port=_ORPHAN_PORT,
        listener_pid=_ORPHAN_PID,
        health=older_version_health,
        singleton_scope_id=_SCOPE,
        spawn_shape_ok=True,
    )
    result = classify_candidate(p, _foreground())
    assert result.cleanup_class == CleanupClass.SAFE_AUTO
    assert result.skip_reason is None
    assert result.package_version == "3.2.2"


@pytest.mark.unit
def test_fr008_different_executable_still_safe_auto() -> None:
    """FR-008: different executable_summary with same scope → safe_auto."""
    p = _probe(
        port=_ORPHAN_PORT,
        listener_pid=_ORPHAN_PID,
        health=_health(owner_pid=_ORPHAN_PID, owner_port=_ORPHAN_PORT),
        singleton_scope_id=_SCOPE,
        spawn_shape_ok=True,
        executable_summary="/usr/local/bin/python3.11",  # different from foreground
    )
    result = classify_candidate(p, _foreground())
    assert result.cleanup_class == CleanupClass.SAFE_AUTO
    assert result.skip_reason is None


# ---------------------------------------------------------------------------
# Invariant checks
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_invariant_skip_reason_none_iff_safe_auto() -> None:
    """skip_reason is None ⟺ cleanup_class == safe_auto for the full decision table."""
    fg = _foreground()

    # safe_auto → skip_reason must be None
    p_safe = _probe(
        health=_health(owner_pid=_ORPHAN_PID, owner_port=_ORPHAN_PORT),
        singleton_scope_id=_SCOPE,
    )
    r_safe = classify_candidate(p_safe, fg)
    assert r_safe.cleanup_class == CleanupClass.SAFE_AUTO
    assert r_safe.skip_reason is None

    # non-safe_auto → skip_reason must be set
    p_bad = _probe(singleton_scope_id=None)
    r_bad = classify_candidate(p_bad, fg)
    assert r_bad.cleanup_class != CleanupClass.SAFE_AUTO
    assert r_bad.skip_reason is not None


@pytest.mark.unit
def test_invariant_daemon_family_default() -> None:
    """daemon_family defaults to 'sync' when health response omits the field."""
    health_without_family = HealthProbe(
        responded=True,
        status="ok",
        protocol_version=1,
        package_version="3.2.4",
        daemon_family=None,  # WP04 not yet deployed
        owner_pid=_ORPHAN_PID,
        owner_port=_ORPHAN_PORT,
        queue_db_path=None,
        auth_scope=None,
        server_url=None,
    )
    p = _probe(
        health=health_without_family,
        singleton_scope_id=_SCOPE,
    )
    result = classify_candidate(p, _foreground())
    assert result.cleanup_class == CleanupClass.SAFE_AUTO
    assert result.daemon_family == "sync"


@pytest.mark.unit
def test_to_dict_keys_match_contract() -> None:
    """to_dict() returns all expected snake_case keys for WP05 JSON surface."""
    p = _probe(
        health=_health(owner_pid=_ORPHAN_PID, owner_port=_ORPHAN_PORT),
        singleton_scope_id=_SCOPE,
        owner_present=True,
    )
    result = classify_candidate(p, _foreground())
    d = result.to_dict()

    expected_keys = {
        "daemon_family",
        "pid",
        "port",
        "protocol_version",
        "package_version",
        "singleton_scope_id",
        "daemon_root",
        "queue_db_path",
        "auth_scope",
        "server_url",
        "owner_present",
        "identity_source",
        "executable_summary",
        "spawn_shape_ok",
        "self_report_matches_listener",
        "is_recorded_singleton",
        "cleanup_class",
        "skip_reason",
    }
    assert set(d.keys()) == expected_keys
    # Enum values must be serialised as strings, not enum objects.
    assert isinstance(d["cleanup_class"], str)
    assert isinstance(d["identity_source"], str)
    assert d["skip_reason"] is None  # safe_auto has no skip_reason
    assert d["owner_present"] is True


@pytest.mark.unit
def test_to_dict_skip_reason_serialised() -> None:
    """to_dict() serialises skip_reason as a string, not None, for non-safe records."""
    p = _probe(singleton_scope_id=None)
    result = classify_candidate(p, _foreground())
    assert result.cleanup_class == CleanupClass.OPERATOR_REQUIRED
    d = result.to_dict()
    assert isinstance(d["skip_reason"], str)
    assert d["skip_reason"] == "pre_marker"


@pytest.mark.unit
def test_record_is_frozen() -> None:
    """DaemonIdentityRecord instances are immutable (frozen=True)."""
    p = _probe(
        health=_health(owner_pid=_ORPHAN_PID, owner_port=_ORPHAN_PORT),
        singleton_scope_id=_SCOPE,
    )
    result = classify_candidate(p, _foreground())
    assert isinstance(result, DaemonIdentityRecord)
    with pytest.raises((AttributeError, TypeError)):
        result.cleanup_class = CleanupClass.NEVER_TOUCH  # type: ignore[misc]  # frozen dataclass: deliberate mutation asserts FrozenInstanceError at runtime
