"""WP10 unit tests for the pure ``sync doctor`` decision core.

The behaviour-lock for ``doctor``'s *rendered* output is the WP02 golden
(``test_sync_cli_safe.py::test_doctor_render_frozen_unhealthy`` + the healthy and
exit-4 arms), which WP10 only *verifies* green pre/post-restructure (Rn-1). These
tests are the focused, branch-level coverage the restructure adds: they drive
:func:`build_doctor_report` — the pure core that folds WP07's store/consent/tracker
compute halves into the ordered ``issues`` list — over every issue-source branch,
the healthy/unhealthy verdict, and the ``auth_missing`` recovery predicate, with no
I/O and no ``Console`` in sight.

``doctor`` takes no arguments and has no ``--json`` (Pd-3); nothing here invents one.
"""

from __future__ import annotations

import dataclasses
from datetime import timedelta
from types import SimpleNamespace
from typing import Any

from kernel.clock import now_utc

from specify_cli.sync.sync_doctor_core import (
    DoctorFacts,
    DoctorReport,
    build_doctor_report,
    doctor_token_flags,
)


def _healthy_facts(**overrides: Any) -> DoctorFacts:
    """A fully-healthy :class:`DoctorFacts` baseline; override one field per branch."""
    session = SimpleNamespace(
        access_token_expires_at=now_utc() + timedelta(days=30),
        refresh_token_expires_at=now_utc() + timedelta(days=30),
        email="user@example.com",
        name="User",
        teams=[],
        default_team_id=None,
    )
    base = DoctorFacts(
        queue_error=None,
        queue_stats=SimpleNamespace(total_queued=0, max_queue_size=1000, oldest_event_age=None, top_event_types=[]),
        body_diagnostics={"total_tasks": 0, "recorded_failure_count": 0, "recent_failures": []},
        queue_db="/tmp/queue.db",
        session=session,
        session_present=True,
        access_token_ok=True,
        refresh_token_ok=True,
        server_url="https://sync.example.com",
        connection_status="[green]Connected[/green]",
        connection_note="",
        connection_is_healthy=True,
        connection_is_auth_owned=False,
        singleton_report=SimpleNamespace(orphan_count=0, orphan_processes=[]),
        singleton_scan_diagnostic=None,
        per_project_report=None,
        per_project_open_error=None,
        per_project_group_error=None,
        consent_index_health=SimpleNamespace(fault=None),
        consent_index_error=None,
        consent_local_fault=None,
        consent_local_error=None,
        consent_repo_root_present=True,
        tracker_local_verdict=_tracker_verdict("local_subprocess", refused=False),
        tracker_hosted_verdict=_tracker_verdict("hosted_service", refused=False),
        tracker_binding_present=True,
        orphan_records=[],
        orphan_record_count=0,
        owner_record_path="/tmp/owner.json",
    )
    return dataclasses.replace(base, **overrides)


def _tracker_verdict(destination: str, *, refused: bool) -> SimpleNamespace:
    return SimpleNamespace(
        destination=SimpleNamespace(value=destination),
        channel1_state="granted",
        message="egress message",
        refused=refused,
    )


def _report(**overrides: Any) -> DoctorReport:
    return build_doctor_report(_healthy_facts(**overrides))


# ---------------------------------------------------------------------------
# Healthy verdict
# ---------------------------------------------------------------------------


def test_healthy_facts_yield_no_issues() -> None:
    report = _report()
    assert report.issues == []
    assert report.healthy is True
    assert report.auth_missing is False


# ---------------------------------------------------------------------------
# Queue-health branch
# ---------------------------------------------------------------------------


def test_queue_unavailable_surfaces_migrate_issue() -> None:
    report = _report(queue_error="disk gone", queue_stats=None, body_diagnostics=None)
    assert any("Project queue authority is unavailable" in i for i in report.issues)
    assert report.healthy is False


def test_queue_full_surfaces_eviction_issue() -> None:
    report = _report(
        queue_stats=SimpleNamespace(total_queued=1000, max_queue_size=1000, oldest_event_age=None, top_event_types=[])
    )
    assert any("Queue is FULL" in i for i in report.issues)


def test_queue_near_full_surfaces_percentage_issue() -> None:
    report = _report(
        queue_stats=SimpleNamespace(total_queued=850, max_queue_size=1000, oldest_event_age=None, top_event_types=[])
    )
    assert any("Queue is 85% full" in i for i in report.issues)


def test_recorded_body_failures_surface_issue() -> None:
    report = _report(body_diagnostics={"total_tasks": 3, "recorded_failure_count": 2, "recent_failures": []})
    assert any("Body upload failures were recorded" in i for i in report.issues)


# ---------------------------------------------------------------------------
# Auth branch
# ---------------------------------------------------------------------------


def test_no_session_is_not_authenticated_and_auth_missing() -> None:
    report = _report(session=None, session_present=False, access_token_ok=False, refresh_token_ok=False)
    assert any("Not authenticated" in i for i in report.issues)
    assert report.auth_missing is True


def test_both_tokens_expired_surfaces_issue_and_auth_missing() -> None:
    report = _report(access_token_ok=False, refresh_token_ok=False)
    assert any("Both access and refresh tokens are expired" in i for i in report.issues)
    assert report.auth_missing is True  # the issue text contains "expired"


def test_access_expired_refresh_valid_surfaces_autorefresh_issue() -> None:
    report = _report(access_token_ok=False, refresh_token_ok=True)
    assert any("auto-refresh on next sync attempt" in i for i in report.issues)


# ---------------------------------------------------------------------------
# Server-reachability branch
# ---------------------------------------------------------------------------


def test_unhealthy_server_surfaces_connection_note() -> None:
    report = _report(
        connection_status="[red]Error[/red]",
        connection_note="server said 503",
        connection_is_healthy=False,
        connection_is_auth_owned=False,
    )
    assert "server said 503" in report.issues


def test_unhealthy_server_without_note_falls_back_to_default_text() -> None:
    report = _report(
        connection_status="[red]Error[/red]",
        connection_note="",
        connection_is_healthy=False,
        connection_is_auth_owned=False,
    )
    assert any("is not reachable" in i for i in report.issues)


def test_auth_owned_connection_is_not_double_reported() -> None:
    report = _report(
        connection_status="[red]Not authenticated[/red]",
        connection_is_healthy=False,
        connection_is_auth_owned=True,
    )
    assert not any("is not reachable" in i for i in report.issues)


# ---------------------------------------------------------------------------
# Daemon-singleton branch
# ---------------------------------------------------------------------------


def test_singleton_scan_failure_surfaces_diagnostic_issue() -> None:
    report = _report(singleton_report=None, singleton_scan_diagnostic="live daemon scan failed: boom")
    assert any("live daemon scan failed: boom" in i and "Retry the scan" in i for i in report.issues)


def test_orphan_daemons_surface_singleton_issue() -> None:
    report = _report(singleton_report=SimpleNamespace(orphan_count=2, orphan_processes=[]))
    assert any("are not the registered singleton" in i for i in report.issues)


# ---------------------------------------------------------------------------
# Per-project store branch (WP07 compute half + open/group errors)
# ---------------------------------------------------------------------------


def test_per_project_open_error_surfaces_mirrored_message() -> None:
    report = _report(per_project_open_error="permission denied")
    assert any("could not be opened" in i and "permission denied" in i for i in report.issues)


def test_per_project_group_error_surfaces_mirrored_message() -> None:
    report = _report(per_project_group_error="db malformed")
    assert any("could not be grouped" in i and "db malformed" in i for i in report.issues)


def test_per_project_report_routes_through_compute_half() -> None:
    report_obj = SimpleNamespace(
        reconciles=True,
        counted_event_total=0,
        retained_event_count=0,
        unresolved_identity_count=0,
        named_non_consenting_rows=[SimpleNamespace(repo_slug="proj-a", project_slug=None, project_uuid=None)],
    )
    report = _report(per_project_report=report_obj)
    # `_per_project_store_issues` produces the non-consenting-project warning.
    assert any("have not consented to hosted sync" in i and "proj-a" in i for i in report.issues)


# ---------------------------------------------------------------------------
# Consent-readability branch (WP07 compute half + read errors)
# ---------------------------------------------------------------------------


def test_consent_index_fault_routes_through_consent_fault_view() -> None:
    fault = SimpleNamespace(kind="unreadable", detail="permission denied")
    report = _report(consent_index_health=SimpleNamespace(fault=fault))
    assert any("machine-global consent index (unreadable)" in i for i in report.issues)


def test_consent_index_read_error_surfaces_mirrored_message() -> None:
    report = _report(consent_index_health=None, consent_index_error="io boom")
    assert any("machine-global consent index is readable could not be" in i and "io boom" in i for i in report.issues)


def test_consent_local_fault_routes_through_consent_fault_view() -> None:
    fault = SimpleNamespace(kind="wrong_shape", detail="top level is a list")
    report = _report(consent_local_fault=fault)
    assert any("this checkout's project config (wrong_shape)" in i for i in report.issues)


def test_consent_local_read_error_surfaces_mirrored_message() -> None:
    report = _report(consent_local_error="stat failed")
    assert any("this checkout's own consent record is readable could not be determined" in i for i in report.issues)


def test_consent_local_fault_ignored_when_no_repo_root() -> None:
    fault = SimpleNamespace(kind="wrong_shape", detail="x")
    report = _report(consent_repo_root_present=False, consent_local_fault=fault)
    assert not any("this checkout's project config" in i for i in report.issues)


# ---------------------------------------------------------------------------
# Tracker-egress branch (WP07 compute half)
# ---------------------------------------------------------------------------


def test_refused_bound_tracker_row_surfaces_issue() -> None:
    report = _report(tracker_local_verdict=_tracker_verdict("local_subprocess", refused=True))
    assert any("tracker egress to local_subprocess is refused" in i for i in report.issues)


def test_refused_unbound_tracker_row_contributes_no_issue() -> None:
    report = _report(
        tracker_binding_present=False,
        tracker_local_verdict=_tracker_verdict("local_subprocess", refused=True),
        tracker_hosted_verdict=_tracker_verdict("hosted_service", refused=True),
    )
    assert not any("tracker egress" in i for i in report.issues)


# ---------------------------------------------------------------------------
# Orphan owner-record branch
# ---------------------------------------------------------------------------


def test_orphan_owner_records_surface_retirement_issue() -> None:
    report = _report(orphan_records=[object(), object()], orphan_record_count=2, owner_record_path="/tmp/o.json")
    assert any("2 orphan daemon owner record(s) on disk" in i and "/tmp/o.json" in i for i in report.issues)


# ---------------------------------------------------------------------------
# Issue ordering (byte-stable vs the pre-restructure interleave)
# ---------------------------------------------------------------------------


def test_issue_order_is_queue_auth_server_singleton_perproject_consent_tracker_orphan() -> None:
    per_project = SimpleNamespace(
        reconciles=True,
        counted_event_total=0,
        retained_event_count=0,
        unresolved_identity_count=0,
        named_non_consenting_rows=[SimpleNamespace(repo_slug="proj-a", project_slug=None, project_uuid=None)],
    )
    report = _report(
        queue_error="q",
        queue_stats=None,
        body_diagnostics=None,
        session=None,
        session_present=False,
        access_token_ok=False,
        refresh_token_ok=False,
        connection_status="[red]Error[/red]",
        connection_note="srv",
        connection_is_healthy=False,
        connection_is_auth_owned=False,
        singleton_report=SimpleNamespace(orphan_count=1, orphan_processes=[]),
        per_project_report=per_project,
        consent_index_health=SimpleNamespace(fault=SimpleNamespace(kind="unreadable", detail="d")),
        tracker_local_verdict=_tracker_verdict("local_subprocess", refused=True),
        orphan_records=[object()],
        orphan_record_count=1,
    )
    markers = [
        "Project queue authority is unavailable",  # queue
        "Not authenticated",  # auth
        "srv",  # server
        "are not the registered singleton",  # singleton
        "have not consented to hosted sync",  # per-project
        "machine-global consent index (unreadable)",  # consent
        "tracker egress to local_subprocess is refused",  # tracker
        "orphan daemon owner record(s) on disk",  # orphan records
    ]
    positions = [next(idx for idx, issue in enumerate(report.issues) if marker in issue) for marker in markers]
    assert positions == sorted(positions), report.issues


# ---------------------------------------------------------------------------
# doctor_token_flags helper
# ---------------------------------------------------------------------------


def test_doctor_token_flags_valid_when_both_future() -> None:
    now = now_utc()
    session = SimpleNamespace(
        access_token_expires_at=now + timedelta(days=1),
        refresh_token_expires_at=now + timedelta(days=1),
    )
    assert doctor_token_flags(session, now) == (True, True)


def test_doctor_token_flags_access_expired_refresh_missing_expiry_is_valid() -> None:
    now = now_utc()
    session = SimpleNamespace(
        access_token_expires_at=now - timedelta(days=1),
        refresh_token_expires_at=None,
    )
    assert doctor_token_flags(session, now) == (False, True)
