"""Focused unit tests for the pure store-report compute core (WP07 / T014).

These pin the compute half extracted from the three shared render helpers
(``_render_per_project_store`` / ``_render_consent_readability`` /
``_render_tracker_egress``). Each function is ``Console``-free and derives rows /
issue strings from a ``PerProjectStoreReport``-shaped input, so it is exercised
directly here (Sonar new-code coverage) rather than only through the golden.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from specify_cli.delivery.status_report import UnresolvedIdentityCandidate
from specify_cli.sync.sync_store_report_core import (
    ConsentFaultView,
    _empty_selection_cause,
    _per_project_store_issues,
    _unresolved_origin_clause,
    channel1_state_wording,
    consent_fault_view,
    tracker_egress_row_issue,
)

from specify_cli.core.saas_sync_config import sync_active
pytestmark = [
    pytest.mark.fast,
    pytest.mark.skipif(
        not sync_active(),
        reason="sync deactivated by default (#3799); set SPEC_KITTY_ENABLE_SAAS_SYNC=1 to run",
    ),
]


def _row(
    *,
    consent_granted: bool = True,
    is_unresolved_identity: bool = False,
    repo_slug: str | None = None,
    project_slug: str | None = None,
    project_uuid: str | None = None,
    unresolved_candidates: tuple[UnresolvedIdentityCandidate, ...] = (),
) -> Any:
    return SimpleNamespace(
        consent_granted=consent_granted,
        is_unresolved_identity=is_unresolved_identity,
        repo_slug=repo_slug,
        project_slug=project_slug,
        project_uuid=project_uuid,
        unresolved_candidates=unresolved_candidates,
    )


def _report(
    *,
    rows: tuple[Any, ...] = (),
    counted_event_total: int = 0,
    retained_event_count: int = 0,
    unresolved_identity_count: int = 0,
    reconciles: bool = True,
    named_non_consenting_rows: tuple[Any, ...] = (),
) -> Any:
    return SimpleNamespace(
        rows=rows,
        counted_event_total=counted_event_total,
        retained_event_count=retained_event_count,
        unresolved_identity_count=unresolved_identity_count,
        reconciles=reconciles,
        named_non_consenting_rows=named_non_consenting_rows,
    )


# --- channel1_state_wording --------------------------------------------------
def test_channel1_state_wording_known_state() -> None:
    from specify_cli.tracker.egress_verdict import CHANNEL1_GRANTED

    assert channel1_state_wording(CHANNEL1_GRANTED) == "hosted-sync consent is granted for this project"


def test_channel1_state_wording_unknown_state_falls_back_to_the_token() -> None:
    assert channel1_state_wording("some-future-state") == "some-future-state"


# --- tracker_egress_row_issue ------------------------------------------------
def test_tracker_egress_row_issue_refused_and_bound_yields_issue() -> None:
    issue = tracker_egress_row_issue(
        destination_value="hosted-service",
        state_wording="a refusal is recorded for this project",
        safe_message="denied by policy",
        refused=True,
        binding_present=True,
    )
    assert issue == (
        "tracker egress to hosted-service is refused "
        "(Channel 1: a refusal is recorded for this project): denied by policy"
    )


def test_tracker_egress_row_issue_refused_but_unbound_yields_none() -> None:
    assert (
        tracker_egress_row_issue(
            destination_value="hosted-service",
            state_wording="undetermined",
            safe_message="msg",
            refused=True,
            binding_present=False,
        )
        is None
    )


def test_tracker_egress_row_issue_permitted_yields_none() -> None:
    assert (
        tracker_egress_row_issue(
            destination_value="local-subprocess",
            state_wording="granted",
            safe_message="msg",
            refused=False,
            binding_present=True,
        )
        is None
    )


# --- consent_fault_view ------------------------------------------------------
def test_consent_fault_view_known_kind_maps_action_and_builds_issue() -> None:
    fault = SimpleNamespace(kind="unparseable", detail="line 3: bad token")
    view = consent_fault_view(scope="this checkout's project config", fault=fault, consequence="Nothing delivered.")
    assert isinstance(view, ConsentFaultView)
    assert view.kind == "unparseable"
    assert view.status == "UNPARSEABLE"
    assert view.action == "REPAIR THE FILE'S SYNTAX"
    assert view.detail == "line 3: bad token"
    # The issue string binds scope, kind, action, detail, consequence and the
    # not-absence tail — the render half appends this verbatim.
    assert view.issue.startswith("this checkout's project config (unparseable): REPAIR THE FILE'S SYNTAX. line 3: bad token Nothing delivered.")
    assert view.issue.endswith("nothing is delivered until the file itself is repaired.")


def test_consent_fault_view_unknown_kind_uses_fallback_action() -> None:
    fault = SimpleNamespace(kind="brand-new-kind", detail="")
    view = consent_fault_view(scope="machine-global consent index", fault=fault, consequence="X.")
    assert view.status == "UNREADABLE"
    assert view.action == "REPAIR THE FILE NAMED IN THE DETAIL"
    # An absent detail degrades to the recorded-nothing placeholder.
    assert view.detail == "no detail recorded"


def test_consent_fault_view_missing_kind_attr_degrades_to_unknown() -> None:
    view = consent_fault_view(scope="s", fault=SimpleNamespace(), consequence="c")
    assert view.kind == "unknown"


# --- _empty_selection_cause --------------------------------------------------
def test_empty_selection_cause_empty_journal() -> None:
    cause = _empty_selection_cause(_report(rows=()))
    assert cause.startswith("The event journal is empty")


def test_empty_selection_cause_all_unresolved() -> None:
    row = _row(is_unresolved_identity=True, consent_granted=False)
    cause = _empty_selection_cause(_report(rows=(row,), counted_event_total=5, unresolved_identity_count=5))
    assert "All 5 retained event(s) have no stored project identity" in cause
    assert "spec-kitty sync migrate" in cause


def test_empty_selection_cause_no_consent_names_the_projects() -> None:
    denied = _row(consent_granted=False, repo_slug="acme/widgets")
    report = _report(
        rows=(denied,),
        counted_event_total=3,
        unresolved_identity_count=0,
        named_non_consenting_rows=(denied,),
    )
    cause = _empty_selection_cause(report)
    assert "No project in the event journal has consented to hosted sync: acme/widgets." in cause
    assert "3 retained event(s)" in cause


def test_empty_selection_cause_delivered_or_blocked() -> None:
    granted = _row(consent_granted=True)
    cause = _empty_selection_cause(_report(rows=(granted,), counted_event_total=2))
    assert cause.startswith("Every consented project's retained events have already been delivered")


# --- _unresolved_origin_clause -----------------------------------------------
def test_unresolved_origin_clause_empty_when_no_candidates() -> None:
    assert _unresolved_origin_clause(_report(rows=())) == ""


def test_unresolved_origin_clause_names_candidates_with_counts() -> None:
    cand = UnresolvedIdentityCandidate(repo_slug="acme/widgets", project_slug=None, event_count=7, oldest_created_at=None)
    row = _row(is_unresolved_identity=True, unresolved_candidates=(cand,))
    clause = _unresolved_origin_clause(_report(rows=(row,)))
    assert "They appear to come from: acme/widgets (7)." in clause


def test_unresolved_origin_clause_uses_placeholder_for_unnamed_candidate() -> None:
    cand = UnresolvedIdentityCandidate(repo_slug=None, project_slug=None, event_count=1, oldest_created_at=None)
    row = _row(is_unresolved_identity=True, unresolved_candidates=(cand,))
    clause = _unresolved_origin_clause(_report(rows=(row,)))
    assert "<no name recorded> (1)" in clause


# --- _per_project_store_issues -----------------------------------------------
def test_per_project_store_issues_healthy_report_has_no_issues() -> None:
    assert _per_project_store_issues(_report(rows=(_row(),), counted_event_total=1, retained_event_count=1)) == []


def test_per_project_store_issues_flags_non_reconciling_report() -> None:
    issues = _per_project_store_issues(_report(reconciles=False, counted_event_total=4, retained_event_count=9))
    assert len(issues) == 1
    assert "do not reconcile" in issues[0]
    assert "(4)" in issues[0] and "(9)" in issues[0]


def test_per_project_store_issues_unresolved_identity_includes_origin_clause() -> None:
    cand = UnresolvedIdentityCandidate(repo_slug="acme/widgets", project_slug=None, event_count=2, oldest_created_at=None)
    row = _row(is_unresolved_identity=True, unresolved_candidates=(cand,))
    issues = _per_project_store_issues(_report(rows=(row,), unresolved_identity_count=2))
    assert len(issues) == 1
    assert "2 journal event(s) have no stored project identity" in issues[0]
    # The origin clause is folded onto the same issue string, not a separate entry.
    assert "They appear to come from: acme/widgets (2)." in issues[0]


def test_per_project_store_issues_names_non_consenting_projects() -> None:
    denied = _row(consent_granted=False, project_slug="beta")
    issues = _per_project_store_issues(_report(rows=(denied,), named_non_consenting_rows=(denied,)))
    assert len(issues) == 1
    assert "1 project(s) in the journal have not consented to hosted sync: beta." in issues[0]
    assert "spec-kitty sync purge --project <slug>" in issues[0]
