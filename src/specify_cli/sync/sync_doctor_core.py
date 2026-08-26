"""Pure decision core for ``spec-kitty sync doctor`` (WP10).

The Wave-4 ``sync.py`` de-god (mission ``sync-cli-degod-wave4-01M0B0MX``)
restructures the cc-73 ``doctor`` command — the second ``# noqa: C901`` monster —
from an *interleaved* gather-render (network + daemon + store I/O run **between**
issue-accumulating render calls) into a three-phase
``gather-all-I/O -> pure core -> render`` shell (architect finding A-1). This
module is the **pure core**: it receives the already-gathered facts
(:class:`DoctorFacts`) and *decides* the ordered ``issues`` list plus the
healthy/unhealthy verdict and the teamspace-recovery flag. It is **I/O-free** —
no ``Console``, no ``print``, no network, no filesystem, no SQLite. The reviewer
co-gate greps this module for ``Console`` / ``print``; any hit is a reject.

The three shared store-report helpers were split by WP07 into a *compute* half
(here-consumed) and a *render* half (still on the host). :func:`build_doctor_report`
**calls those compute halves** — :func:`_per_project_store_issues`,
:func:`consent_fault_view`, :func:`tracker_egress_row_issue` — and folds their
findings into the ordered report (Pd-2 / DIRECTIVE_044: it neither prints nor
re-derives the store/consent/tracker logic). The host's render shell re-invokes
the render halves for their **printed** sections; the authoritative summary and
verdict come from this core.

The byte-stable observable contract is guarded by the WP02 goldens
(``test_doctor_render_frozen_unhealthy`` + the healthy and exit-4 arms) and the
~60 ``test_sync_doctor*`` patch-tests.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from kernel.clock import datetime
from typing import Any

from rich.markup import escape as _escape_markup

from specify_cli.auth.verdict import auth_verdict_from_flags
from specify_cli.sync.sync_store_report_core import (
    _per_project_store_issues,
    channel1_state_wording,
    consent_fault_view,
    tracker_egress_row_issue,
)

# ---------------------------------------------------------------------------
# Issue-text constants.
#
# The queue / auth / server / singleton / orphan-record messages *relocate* here
# from the pre-restructure ``doctor`` body — this module is now their only home.
# The per-project and consent messages below deliberately MIRROR the wording the
# host render halves (``_render_per_project_store`` in ``sync_render.py`` — not a
# WP10-owned file — and ``_render_consent_readability`` in ``sync.py``) still emit
# while printing their sections. Keeping the summary/verdict decision pure means
# reproducing the exact operator wording here; the ~60 ``test_sync_doctor*`` and
# ``test_sync_doctor_{per_project,consent_health}_*`` tests assert on this text
# end-to-end, so any drift from the render halves fails immediately.
# ---------------------------------------------------------------------------
_QUEUE_UNAVAILABLE_ISSUE = (
    "Project queue authority is unavailable. Run `spec-kitty sync project-store-migrate` "
    "from an identified checkout; no empty-queue claim was made."
)
_QUEUE_FULL_ISSUE = (
    "Queue is FULL -- oldest events are being evicted to make room for new ones. "
    "Run `spec-kitty sync now` after fixing auth/connectivity."
)
_BODY_FAILURE_ISSUE = (
    "Body upload failures were recorded. Review the recent body upload failures below "
    "and fix the underlying artifact or contract mismatch."
)
_NOT_AUTHENTICATED_ISSUE = "Not authenticated. Run `spec-kitty auth login`."
_BOTH_TOKENS_EXPIRED_ISSUE = (
    "Both access and refresh tokens are expired. Run `spec-kitty auth login` to re-authenticate."
)
_ACCESS_EXPIRED_ISSUE = (
    "Access token expired but refresh token is still valid. "
    "Token will auto-refresh on next sync attempt."
)
_SINGLETON_SCAN_SUFFIX = ". Retry the scan or stop sync before trusting queue health."

#: Per-project journal open/group failures — mirror of ``_render_per_project_store``
#: (``sync_render.py``); guarded by ``test_doctor_names_the_journal_it_could_not_{open,group}``.
_PER_PROJECT_OPEN_ISSUE = (
    "The event journal could not be opened, so this run cannot say which "
    "projects have data in it: {exc}. Until this is resolved, treat a "
    "clean queue-health block as unproven — it reads a different store."
)
_PER_PROJECT_GROUP_ISSUE = (
    "The event journal opened but its rows could not be grouped by "
    "project: {exc}. Whose data is in the journal is currently UNKNOWN; "
    "the queue-health block above does not answer it."
)

#: Consent-readability scope / consequence / read-error strings — mirror of
#: ``_render_consent_readability`` (``sync.py``); guarded by the
#: ``test_sync_doctor_consent_health_3030`` suite.
_CONSENT_INDEX_SCOPE = "machine-global consent index"
_CONSENT_INDEX_CONSEQUENCE = (
    "Every project on this machine resolves as UNDETERMINED while this stands, "
    "so nothing is delivered."
)
_CONSENT_INDEX_READ_ERROR = (
    "Whether the machine-global consent index is readable could not be "
    "determined: {exc}. Until it is, treat every consent state reported above "
    "as unproven."
)
_CONSENT_LOCAL_SCOPE = "this checkout's project config"
_CONSENT_LOCAL_READ_ERROR = (
    "Whether this checkout's own consent record is readable could not be determined: {exc}."
)
#: The ``consequence`` string for a project-local consent fault. Verbatim mirror of
#: ``sync._CONSENT_FAULT_REACH``.
_CONSENT_LOCAL_CONSEQUENCE = (
    "A read fault cannot be attributed to a project — an unreadable file does not "
    "disclose which project it declares — so while it stands it denies for every "
    "project resolved through this checkout, not only this one. Its reach is narrower "
    "than that sounds: every production caller offers exactly one checkout root, the "
    "current directory's, so the broken file is this checkout's own and no sibling "
    "checkout can have caused it."
)


@dataclass(frozen=True)
class DoctorFacts:
    """Every fact the shell's up-front I/O phase gathers for ``doctor``.

    Host-owned duck-typed objects (``queue_stats``, ``session``,
    ``singleton_report``, ``per_project_report``, ``consent_*``, ``tracker_*``)
    are typed ``Any``; every value read off them is absorbed into a
    correctly-typed local before it leaves this core, per the mypy-strict
    quarantine guardrail. The two token-expiry timestamps are folded into
    ``access_token_ok`` / ``refresh_token_ok`` by the gather phase so this core
    performs no clock reads.
    """

    # --- queue health ---
    queue_error: str | None
    queue_stats: Any | None
    body_diagnostics: dict[str, Any] | None
    queue_db: str | None
    # --- auth ---
    session: Any | None
    session_present: bool
    access_token_ok: bool
    refresh_token_ok: bool
    # --- server reachability ---
    server_url: str
    connection_status: str
    connection_note: str
    connection_is_healthy: bool
    connection_is_auth_owned: bool
    # --- daemon singleton ---
    singleton_report: Any | None
    singleton_scan_diagnostic: str | None
    # --- per-project journal composition ---
    per_project_report: Any | None
    per_project_open_error: str | None
    per_project_group_error: str | None
    # --- consent-record readability ---
    consent_index_health: Any | None
    consent_index_error: str | None
    consent_local_fault: Any | None
    consent_local_error: str | None
    consent_repo_root_present: bool
    # --- tracker egress ---
    tracker_local_verdict: Any
    tracker_hosted_verdict: Any
    tracker_binding_present: bool
    # --- orphan daemon owner records ---
    orphan_records: list[Any]
    orphan_record_count: int
    owner_record_path: str


@dataclass(frozen=True)
class DoctorReport:
    """The decided ``doctor`` outcome: the ordered issues + derived verdicts.

    ``issues`` is empty iff the sync surface is healthy. ``auth_missing`` mirrors
    the pre-restructure teamspace-recovery predicate (session absent, or any issue
    mentioning ``auth login`` / ``expired``) and gates the exit-4 recovery arm.
    """

    issues: list[str] = field(default_factory=list)
    auth_missing: bool = False

    @property
    def healthy(self) -> bool:
        """``True`` when no issue was surfaced (the "Sync is healthy" arm)."""
        return not self.issues


def _queue_issues(facts: DoctorFacts) -> list[str]:
    """Queue-depth + body-upload warnings (or the store-unavailable issue)."""
    if facts.queue_error is not None:
        return [_QUEUE_UNAVAILABLE_ISSUE]
    issues: list[str] = []
    stats = facts.queue_stats
    body = facts.body_diagnostics
    if stats is not None:
        max_size = int(stats.max_queue_size)
        queue_size = int(stats.total_queued)
        pct = (queue_size / max_size * 100) if max_size > 0 else 0
        if pct >= 100:
            issues.append(_QUEUE_FULL_ISSUE)
        elif pct >= 80:
            issues.append(f"Queue is {pct:.0f}% full. Consider syncing soon with `spec-kitty sync now`.")
    if body is not None and int(body["recorded_failure_count"]) > 0:
        issues.append(_BODY_FAILURE_ISSUE)
    return issues


def _auth_issues(facts: DoctorFacts) -> list[str]:
    """Token-expiry warnings, derived from the shared honest auth verdict.

    The tri-state decision is owned by ``auth.verdict`` (#3723; sync -> auth is
    the legal direction). This core is I/O-free, so it feeds the pre-gathered
    ``(access_ok, refresh_ok)`` flags to :func:`auth_verdict_from_flags` and maps
    the resulting *state* onto its byte-stable issue vocabulary: ``ok`` -> no
    issue; ``unknown`` (access expired, refresh unproven offline) ->
    ``_ACCESS_EXPIRED_ISSUE``; ``fail`` -> the missing / both-expired issue.
    """
    verdict = auth_verdict_from_flags(
        session_present=facts.session_present,
        access_ok=facts.access_token_ok,
        refresh_ok=facts.refresh_token_ok,
    )
    if verdict.state == "ok":
        return []
    if not facts.session_present:
        return [_NOT_AUTHENTICATED_ISSUE]
    if not facts.refresh_token_ok:
        return [_BOTH_TOKENS_EXPIRED_ISSUE]
    return [_ACCESS_EXPIRED_ISSUE]


def _server_issues(facts: DoctorFacts) -> list[str]:
    """The non-healthy, non-auth-owned server-reachability issue (FR-002, #3406)."""
    if facts.connection_is_healthy or facts.connection_is_auth_owned:
        return []
    return [
        facts.connection_note
        or f"Sync server at {facts.server_url} is not reachable. Events will continue to queue locally."
    ]


def _singleton_issues(facts: DoctorFacts) -> list[str]:
    """Daemon-singleton warnings (spec-kitty#1071) or the scan-failure issue."""
    if facts.singleton_scan_diagnostic is not None:
        return [facts.singleton_scan_diagnostic + _SINGLETON_SCAN_SUFFIX]
    report = facts.singleton_report
    if report is not None and int(report.orphan_count) > 0:
        orphan_count = int(report.orphan_count)
        return [
            f"{orphan_count} live `run_sync_daemon` process(es) "
            "are not the registered singleton. Multiple daemons make queue state "
            "ambiguous (spec-kitty#1071). Kill the orphans manually or run "
            "`spec-kitty sync stop` and a clean `spec-kitty sync now`."
        ]
    return []


def _per_project_issues(facts: DoctorFacts) -> list[str]:
    """Per-project journal-composition warnings.

    Calls WP07's :func:`_per_project_store_issues` compute half on the gathered
    report; on an open/group I/O failure the gather phase captured the exception
    text and the mirrored message is surfaced instead.
    """
    if facts.per_project_open_error is not None:
        return [_PER_PROJECT_OPEN_ISSUE.format(exc=facts.per_project_open_error)]
    if facts.per_project_group_error is not None:
        return [_PER_PROJECT_GROUP_ISSUE.format(exc=facts.per_project_group_error)]
    if facts.per_project_report is not None:
        return list(_per_project_store_issues(facts.per_project_report))
    return []


def _consent_issues(facts: DoctorFacts) -> list[str]:
    """Consent-record readability warnings (SC-004, FR-020/FR-027).

    Faults route through WP07's :func:`consent_fault_view` compute half; a read
    that could not even be attempted surfaces the mirrored read-error message.
    """
    issues: list[str] = []
    if facts.consent_index_error is not None:
        issues.append(_CONSENT_INDEX_READ_ERROR.format(exc=facts.consent_index_error))
    elif facts.consent_index_health is not None and facts.consent_index_health.fault is not None:
        issues.append(
            consent_fault_view(
                scope=_CONSENT_INDEX_SCOPE,
                fault=facts.consent_index_health.fault,
                consequence=_CONSENT_INDEX_CONSEQUENCE,
            ).issue
        )
    if facts.consent_local_error is not None:
        issues.append(_CONSENT_LOCAL_READ_ERROR.format(exc=facts.consent_local_error))
    elif facts.consent_repo_root_present and facts.consent_local_fault is not None:
        issues.append(
            consent_fault_view(
                scope=_CONSENT_LOCAL_SCOPE,
                fault=facts.consent_local_fault,
                consequence=_CONSENT_LOCAL_CONSEQUENCE,
            ).issue
        )
    return issues


def _tracker_row_issue(verdict: Any, *, binding_present: bool) -> str | None:
    """One tracker-egress row's issue via WP07's :func:`tracker_egress_row_issue`."""
    state_wording: str = channel1_state_wording(verdict.channel1_state)
    safe_message: str = _escape_markup(verdict.message)
    destination_value: str = verdict.destination.value
    row_issue: str | None = tracker_egress_row_issue(
        destination_value=destination_value,
        state_wording=state_wording,
        safe_message=safe_message,
        refused=bool(verdict.refused),
        binding_present=binding_present,
    )
    return row_issue


def _tracker_issues(facts: DoctorFacts) -> list[str]:
    """Tracker-egress refusal issues, one per :class:`EgressDestination` (FR-014)."""
    issues: list[str] = []
    for verdict in (facts.tracker_local_verdict, facts.tracker_hosted_verdict):
        row_issue = _tracker_row_issue(verdict, binding_present=facts.tracker_binding_present)
        if row_issue is not None:
            issues.append(row_issue)
    return issues


def _orphan_record_issues(facts: DoctorFacts) -> list[str]:
    """Orphan daemon owner-record retirement issue (WP03 / FR-010)."""
    if facts.orphan_record_count > 0:
        return [
            f"{facts.orphan_record_count} orphan daemon owner record(s) on disk; "
            f"retire via `rm {facts.owner_record_path}`."
        ]
    return []


def _auth_missing(session_present: bool, issues: list[str]) -> bool:
    """Whether the teamspace-aware recovery arm (issue #829) should be offered.

    Mirrors the pre-restructure predicate exactly: the session is absent, or some
    surfaced issue mentions ``auth login`` or ``expired``.
    """
    return not session_present or any("auth login" in issue or "expired" in issue for issue in issues)


def build_doctor_report(facts: DoctorFacts) -> DoctorReport:
    """Decide ``doctor``'s ordered ``issues`` list + verdicts from gathered facts.

    Issue order is byte-stable against the pre-restructure interleave: queue,
    auth, server, daemon-singleton, per-project store, consent readability,
    tracker egress, orphan owner records. The store/consent/tracker findings come
    from WP07's compute halves (Pd-2); nothing here prints or performs I/O.
    """
    issues: list[str] = []
    issues.extend(_queue_issues(facts))
    issues.extend(_auth_issues(facts))
    issues.extend(_server_issues(facts))
    issues.extend(_singleton_issues(facts))
    issues.extend(_per_project_issues(facts))
    issues.extend(_consent_issues(facts))
    issues.extend(_tracker_issues(facts))
    issues.extend(_orphan_record_issues(facts))
    return DoctorReport(issues=issues, auth_missing=_auth_missing(facts.session_present, issues))


def doctor_token_flags(session: Any, now: datetime) -> tuple[bool, bool]:
    """Derive ``(access_ok, refresh_ok)`` from a session and the gathered clock.

    Shared by the gather phase (to fill :class:`DoctorFacts`) and the render shell
    (to colour the token rows) so the table and the summary cannot disagree on
    validity. A ``None`` refresh expiry is treated as valid (no stored expiry).
    """
    access_exp = session.access_token_expires_at
    refresh_exp = session.refresh_token_expires_at
    access_ok = access_exp is not None and access_exp > now
    refresh_ok = refresh_exp is None or refresh_exp > now
    return access_ok, refresh_ok


__all__ = [
    "DoctorFacts",
    "DoctorReport",
    "build_doctor_report",
    "doctor_token_flags",
]
