"""WP09 unit coverage for the pure ``sync status`` decision core.

The behaviour-lock for ``status``'s full human render is the WP02 golden
(``test_sync_cli_safe.py::test_status_full_human_render_frozen`` + the
``status --check`` arms) — per the binding Rn-1 correction this file does NOT
re-freeze that snapshot. These tests instead exercise the extracted pure core
(``specify_cli.sync.sync_status_core``) branch-by-branch: ``build_status_rows``
and ``evaluate_boundary_coherence`` (the two load-bearing extractions) plus the
supporting ``build_boundary_sections`` / ``build_orphan_detail_lines`` /
``derive_auth_recovery_pending`` helpers, satisfying the Sonar new-code-coverage
expectation that every new branch is executed directly.
"""

from __future__ import annotations

import pytest

from types import SimpleNamespace
from typing import Any

from specify_cli.auth.verdict import HealthVerdict
from specify_cli.sync.sync_status_core import (
    StatusFacts,
    build_boundary_sections,
    build_orphan_detail_lines,
    build_status_rows,
    build_status_view,
    derive_auth_recovery_pending,
    evaluate_boundary_coherence,
)

_OK_VERDICT = HealthVerdict(state="ok", evidence="access valid 15m; refresh valid 30d")


def _daemon(**overrides: Any) -> SimpleNamespace:
    base = {
        "healthy": False,
        "url": None,
        "pid": None,
        "port": None,
        "sync_running": False,
        "websocket_status": "Disconnected",
        "last_sync": None,
        "consecutive_failures": 0,
    }
    return SimpleNamespace(**{**base, **overrides})


def _foreground(**overrides: Any) -> SimpleNamespace:
    base = {
        "package_version": "1.2.3",
        "executable_path": "/usr/bin/python",
        "source_path": "/src",
        "server_url": None,
        "team_or_user": None,
        "queue_db_path": "/q.db",
    }
    return SimpleNamespace(**{**base, **overrides})


def _failure_set(**overrides: Any) -> SimpleNamespace:
    base = {
        "foreground": _foreground(),
        "daemon_status": "absent",
        "legacy_event_rows": 0,
        "legacy_body_upload_rows": 0,
        "legacy_rows_for_scope": 0,
        "mismatches": [],
    }
    return SimpleNamespace(**{**base, **overrides})


def _facts(**overrides: Any) -> StatusFacts:
    base: dict[str, Any] = {
        "check_connection": False,
        "saas_enabled": True,
        "server_url": "https://s",
        "config_file": "/cfg.toml",
        "queue_size": 0,
        "body_queue_count": 0,
        "auth_verdict": _OK_VERDICT,
        "daemon_status": _daemon(),
        "connection_status": None,
        "connection_note": None,
        "orphan_report": None,
        "orphan_scan_diagnostic": None,
        "failure_set": _failure_set(),
        "daemon_record": None,
        "daemon_team_or_user": None,
        "daemon_mismatched": [],
        "orphan_record_count": 0,
        "legacy_db_path": "/legacy.db",
        "stranded_tag": None,
        "auth_recovery_pending": False,
    }
    return StatusFacts(**{**base, **overrides})


def _rowmap(rows: list[Any]) -> dict[str, str]:
    """Collapse ``StatusRow`` list to ``{label: value}`` (labels here are unique)."""
    return {r.label: r.value for r in rows}


# ---------------------------------------------------------------------------
# build_status_rows — main table
# ---------------------------------------------------------------------------

pytestmark = [pytest.mark.fast]


def test_status_rows_queue_empty_and_saas_enabled() -> None:
    rows = _rowmap(build_status_rows(_facts(queue_size=0, saas_enabled=True)))
    assert rows["Queue"] == "[green]0 event(s)[/green]"
    assert rows["SaaS Sync"] == "[green]Enabled[/green]"
    # SaaS enabled + ok verdict -> green Authenticated row that NAMES its evidence
    # (#3723 rule 1): the row can never claim green without the token window.
    assert rows["Auth"] == "[green]Authenticated[/green] (access valid 15m; refresh valid 30d)"
    assert rows["Server URL"] == "https://s"
    assert rows["Config File"] == "/cfg.toml"


def test_status_rows_queue_nonzero_is_yellow() -> None:
    rows = _rowmap(build_status_rows(_facts(queue_size=3)))
    assert rows["Queue"] == "[yellow]3 event(s)[/yellow]"


def test_status_rows_saas_disabled_and_auth_flag_off() -> None:
    rows = _rowmap(build_status_rows(_facts(saas_enabled=False, auth_verdict=_OK_VERDICT)))
    assert "Disabled" in rows["SaaS Sync"]
    # When the feature flag is off, the verdict is ignored and the row is the flag note.
    assert rows["Auth"] == "[dim]Disabled by feature flag[/dim]"


def test_status_rows_saas_enabled_but_unauthenticated() -> None:
    fail_verdict = HealthVerdict(state="fail", evidence="no active session")
    rows = _rowmap(build_status_rows(_facts(saas_enabled=True, auth_verdict=fail_verdict)))
    assert rows["Auth"] == "[red]Not authenticated[/red] (no active session)"


def test_status_rows_auth_unknown_is_yellow_and_never_green() -> None:
    """#3723: an expired-access session whose refresh chain is unproven offline
    renders ``unknown`` — a yellow, evidence-bearing row — never a green claim."""
    unknown = HealthVerdict(
        state="unknown",
        evidence="access token expired; refresh chain not verified offline",
    )
    rows = _rowmap(build_status_rows(_facts(saas_enabled=True, auth_verdict=unknown)))
    assert rows["Auth"] == (
        "[yellow]Cannot verify[/yellow] "
        "(access token expired; refresh chain not verified offline)"
    )
    assert "green" not in rows["Auth"]


def test_status_rows_auth_states_map_to_three_distinct_texts() -> None:
    ok_text = _rowmap(build_status_rows(_facts(auth_verdict=_OK_VERDICT)))["Auth"]
    unknown_text = _rowmap(
        build_status_rows(
            _facts(auth_verdict=HealthVerdict(state="unknown", evidence="unproven"))
        )
    )["Auth"]
    fail_text = _rowmap(
        build_status_rows(
            _facts(auth_verdict=HealthVerdict(state="fail", evidence="no active session"))
        )
    )["Auth"]
    # The three states must each render a distinct row (pairwise distinct, not a
    # golden-count on the collection size).
    assert ok_text != unknown_text
    assert unknown_text != fail_text
    assert ok_text != fail_text


def test_status_rows_daemon_running_with_endpoints() -> None:
    daemon = _daemon(
        healthy=True,
        url="http://127.0.0.1:9000",
        pid=4242,
        port=9000,
        sync_running=True,
        websocket_status="Connected",
    )
    rows = _rowmap(build_status_rows(_facts(daemon_status=daemon)))
    assert rows["Daemon"] == "[green]Running[/green]"
    assert rows["Daemon URL"] == "http://127.0.0.1:9000"
    assert rows["Daemon PID"] == "4242"
    assert rows["Daemon Port"] == "9000"
    assert rows["Sync Mode"] == "[green]Global daemon[/green]"
    assert rows["WebSocket"] == "[green]Connected[/green]"


def test_status_rows_daemon_stopped_omits_endpoints() -> None:
    labels = [r.label for r in build_status_rows(_facts(daemon_status=_daemon()))]
    assert "Daemon" in labels
    assert "Daemon URL" not in labels
    assert "Daemon PID" not in labels
    assert "Daemon Port" not in labels


def test_status_rows_last_sync_valid_iso_is_formatted() -> None:
    daemon = _daemon(last_sync="2026-01-02T03:04:05+00:00")
    rows = _rowmap(build_status_rows(_facts(daemon_status=daemon)))
    assert rows["Last Sync"] == "2026-01-02 03:04:05 UTC"


def test_status_rows_last_sync_unparseable_falls_back_to_raw() -> None:
    daemon = _daemon(last_sync="not-a-timestamp")
    rows = _rowmap(build_status_rows(_facts(daemon_status=daemon)))
    assert rows["Last Sync"] == "not-a-timestamp"


def test_status_rows_last_sync_never() -> None:
    rows = _rowmap(build_status_rows(_facts()))
    assert rows["Last Sync"] == "[dim]Never[/dim]"


def test_status_rows_consecutive_failures_row() -> None:
    daemon = _daemon(consecutive_failures=2)
    rows = _rowmap(build_status_rows(_facts(daemon_status=daemon)))
    assert rows["Failures"] == "[yellow]2 consecutive[/yellow]"


# ---------------------------------------------------------------------------
# build_status_rows — connection (--check) arm
# ---------------------------------------------------------------------------


def test_connection_rows_absent_without_check() -> None:
    labels = [r.label for r in build_status_rows(_facts(check_connection=False))]
    assert "Ping" not in labels
    assert "Singleton" not in labels


def test_connection_rows_ping_and_singleton_ok() -> None:
    facts = _facts(
        check_connection=True,
        connection_status="[green]Connected[/green]",
        connection_note="",
        orphan_report=SimpleNamespace(orphan_count=0, orphan_processes=[]),
    )
    rows = _rowmap(build_status_rows(facts))
    assert rows["Ping"] == "[green]Connected[/green]"
    assert rows["Singleton"] == "[green]OK[/green] (no orphan daemons detected)"


def test_connection_rows_note_and_orphans_detected() -> None:
    facts = _facts(
        check_connection=True,
        connection_status="[yellow]Not authenticated[/yellow]",
        connection_note="token expired",
        orphan_report=SimpleNamespace(orphan_count=2, orphan_processes=[]),
    )
    rows = build_status_rows(facts)
    rowmap = _rowmap(rows)
    # The unlabeled note row carries the dim detail.
    assert any(r.label == "" and r.value == "[dim]token expired[/dim]" for r in rows)
    assert rowmap["Singleton"] == "[yellow]2 orphan daemon(s) detected[/yellow]"


def test_connection_rows_scan_failure_surfaces_unavailable() -> None:
    facts = _facts(
        check_connection=True,
        connection_status="[green]Connected[/green]",
        orphan_report=None,
        orphan_scan_diagnostic="live daemon scan failed: boom",
    )
    rows = _rowmap(build_status_rows(facts))
    assert rows["Singleton"] == "[red]Unavailable[/red] (live daemon scan failed: boom)"


# ---------------------------------------------------------------------------
# build_orphan_detail_lines
# ---------------------------------------------------------------------------


def test_orphan_detail_lines_empty_when_no_report() -> None:
    assert build_orphan_detail_lines(None) == []


def test_orphan_detail_lines_empty_when_zero_count() -> None:
    report = SimpleNamespace(orphan_count=0, orphan_processes=[])
    assert build_orphan_detail_lines(report) == []


def test_orphan_detail_lines_render_pid_and_cmdline() -> None:
    report = SimpleNamespace(
        orphan_count=1,
        orphan_processes=[SimpleNamespace(pid=7, cmdline=["python", "run_sync_daemon"])],
    )
    assert build_orphan_detail_lines(report) == ["  PID 7: python run_sync_daemon"]


# ---------------------------------------------------------------------------
# derive_auth_recovery_pending
# ---------------------------------------------------------------------------


def test_auth_recovery_none_and_empty_are_false() -> None:
    assert derive_auth_recovery_pending(None) is False
    assert derive_auth_recovery_pending("") is False
    assert derive_auth_recovery_pending("[green]Connected[/green]") is False


def test_auth_recovery_true_for_each_marker() -> None:
    assert derive_auth_recovery_pending("Not authenticated") is True
    assert derive_auth_recovery_pending("Session expired") is True
    assert derive_auth_recovery_pending("Authentication failed") is True


# ---------------------------------------------------------------------------
# build_boundary_sections
# ---------------------------------------------------------------------------


def test_boundary_sections_daemon_absent() -> None:
    sections = build_boundary_sections(_facts(daemon_record=None))
    daemon_map = dict(sections.daemon_rows)
    assert daemon_map["Status"] == "absent"
    assert daemon_map["PID"] == "<absent>"
    assert daemon_map["Queue DB path"] == "<absent>"
    # No mismatches -> no detail rows, and the top-level scalar reads green none.
    assert sections.mismatch_rows == []
    top = dict(sections.top_level_rows)
    assert top["Mismatched fields"] == "[green]none[/green]"
    assert top["Mismatches"] == "[green]0[/green]"


def test_boundary_sections_daemon_present_and_mismatches() -> None:
    record = SimpleNamespace(
        pid=11,
        port=22,
        package_version="9.9",
        executable_path="/d/exe",
        source_checkout_path="/d/src",
        server_url="https://d",
        queue_db_path="/d/q.db",
    )
    mismatch = SimpleNamespace(field="server_url", foreground_value="https://s", daemon_value="https://d")
    facts = _facts(
        failure_set=_failure_set(daemon_status="running", mismatches=[mismatch]),
        daemon_record=record,
        daemon_team_or_user="alice/acme",
    )
    sections = build_boundary_sections(facts)
    daemon_map = dict(sections.daemon_rows)
    assert daemon_map["Status"] == "running"
    assert daemon_map["PID"] == "11"
    assert daemon_map["Team/User"] == "alice/acme"
    assert sections.mismatch_rows == [("server_url", "https://s", "https://d")]
    top = dict(sections.top_level_rows)
    assert top["Mismatched fields"] == "[red]server_url[/red]"
    assert top["Mismatches"] == "[red]1[/red]"


def test_boundary_sections_daemon_mismatched_fallback() -> None:
    # No structured mismatches, but the daemon/foreground field diff list is set.
    facts = _facts(daemon_mismatched=["source_path"])
    top = dict(build_boundary_sections(facts).top_level_rows)
    assert top["Mismatched fields"] == "[red]source_path[/red]"


def test_boundary_sections_stranded_tag_appends_rows_and_suffix() -> None:
    facts = _facts(stranded_tag="my-mission")
    sections = build_boundary_sections(facts)
    legacy_map = dict(sections.legacy_queue_rows)
    assert legacy_map["Stranded mission"] == "setup-plan stranded mission slug my-mission"
    top = dict(sections.top_level_rows)
    assert top["Legacy queue rows"].endswith("— setup-plan stranded mission slug my-mission")


def test_boundary_sections_orphan_record_count_is_yellow() -> None:
    top = dict(build_boundary_sections(_facts(orphan_record_count=4)).top_level_rows)
    assert top["Orphan records"] == "[yellow]4[/yellow]"
    assert top["Orphan daemon records"] == "[yellow]4[/yellow]"


# ---------------------------------------------------------------------------
# build_status_view — composition
# ---------------------------------------------------------------------------


def test_build_status_view_composes_all_parts() -> None:
    view = build_status_view(_facts())
    assert [r.label for r in view.main_rows][0] == "Queue"
    assert view.orphan_detail_lines == []
    assert view.boundary.foreground_rows  # non-empty


# ---------------------------------------------------------------------------
# evaluate_boundary_coherence — the --check gate
# ---------------------------------------------------------------------------


def test_boundary_coherent_exit_0() -> None:
    verdict = evaluate_boundary_coherence(
        base_failures=[],
        auth_present=True,
        auth_required=True,
        orphan_count=0,
        orphan_scan_diagnostic=None,
    )
    assert verdict.failures == []
    assert verdict.exit_code == 0


def test_boundary_auth_required_but_absent_exit_2() -> None:
    verdict = evaluate_boundary_coherence(
        base_failures=[],
        auth_present=False,
        auth_required=True,
        orphan_count=0,
        orphan_scan_diagnostic=None,
    )
    assert verdict.exit_code == 2
    assert any("no authenticated identity is available" in line for line in verdict.failures)


def test_boundary_auth_not_required_when_flag_off() -> None:
    verdict = evaluate_boundary_coherence(
        base_failures=[],
        auth_present=False,
        auth_required=False,
        orphan_count=0,
        orphan_scan_diagnostic=None,
    )
    assert verdict.failures == []
    assert verdict.exit_code == 0


def test_boundary_live_orphans_and_diagnostic_ordering() -> None:
    verdict = evaluate_boundary_coherence(
        base_failures=["legacy queue DB has rows pending migration"],
        auth_present=True,
        auth_required=True,
        orphan_count=3,
        orphan_scan_diagnostic="live daemon scan failed: boom",
    )
    assert verdict.exit_code == 2
    # Base failures come first, then the orphan line, then the scan diagnostic.
    assert verdict.failures[0].startswith("legacy queue DB")
    assert "3 live `run_sync_daemon` process(es) detected" in verdict.failures[1]
    assert verdict.failures[2].startswith("live daemon scan failed: boom — retry the scan")


def test_boundary_base_failures_alone_trip_exit_2() -> None:
    verdict = evaluate_boundary_coherence(
        base_failures=["foreground/daemon disagree on D-3 field(s): server_url"],
        auth_present=True,
        auth_required=True,
        orphan_count=0,
        orphan_scan_diagnostic=None,
    )
    assert verdict.exit_code == 2
    assert verdict.failures == ["foreground/daemon disagree on D-3 field(s): server_url"]
