"""Pure compute core for the ``spec-kitty sync`` store-report family (WP07).

The Wave-4 ``sync.py`` de-god (mission ``sync-cli-degod-wave4-01M0B0MX``) splits
the three shared render+``issues`` helpers — ``_render_per_project_store`` (used
by **both** ``status`` and ``doctor``), ``_render_consent_readability`` and
``_render_tracker_egress`` — into a **pure compute half** (this module) and a
**render half** (the Console-emit, left on the host / in :mod:`sync_render`).

Every function here derives rows / issue strings and returns them; **none prints
or holds a ``Console``** (reviewer co-gate for this seam). That is the decoupling
(pedro finding Pd-2): the WP09 ``status`` core and the WP10 ``doctor`` core both
import the SAME compute from here, so neither command depends on the other. The
issue-derivation was previously a helper shared through the ``sync`` host module,
which coupled the two monsters via a status→doctor / doctor→status edge; that edge
is retired by giving the derivation a home that is neither command's module.

``_event_sync_report`` opens the WP10 migration-audit store and the project unit of
work read-only. "Pure" here means **no Console/print**, not "no I/O": it returns
the additive status-report sections as plain data for the CLI to serialise. Its two
host-owned dependencies (``_read_migration_conflicts_readonly`` on the host,
``_open_active_body_queue`` in :mod:`sync_runtime`) are reached the WP03 way — the
former late-bound off the host module object so a monkeypatch still intercepts, the
latter imported from its seam home — so this relocation changes no behaviour (INV-1
/ INV-4). The WP02 golden and the ~60 patch-tests are the guard.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Final

from specify_cli.tracker.egress_verdict import (
    CHANNEL1_GRANTED,
    CHANNEL1_NOT_CONSENTABLE,
    CHANNEL1_NO_RECORD,
    CHANNEL1_RECORDED_REFUSAL,
    CHANNEL1_UNCLASSIFIED,
    CHANNEL1_UNDETERMINED,
)

if TYPE_CHECKING:
    from specify_cli.delivery.status_report import (
        PerProjectStoreReport,
        UnresolvedIdentityCandidate,
    )
    from specify_cli.sync.sync_runtime import _EventSyncRuntime


#: Printed for the ``<no name recorded>`` placeholder when an unresolved-identity
#: candidate carries no recorded name. Shared by :func:`unresolved_origin_clause`
#: here and by ``_per_project_store_table`` on the host, so the two cannot disagree.
_NO_RECORDED_NAME = "<no name recorded>"


def _event_sync_report(base: dict[str, Any], runtime: _EventSyncRuntime) -> dict[str, Any]:
    """Merge the seven WP11 additive sections onto *base* (CLI serialises only).

    Opens the WP10 migration-audit store (read-only, best-effort) so the
    ``migration_conflicts`` section surfaces real divergent-duplicate conflicts
    that block cleanup (SC-011) rather than always reporting an empty set.
    """
    import specify_cli.cli.commands.sync as sync_module

    from specify_cli.delivery.status_report import build_status_report

    from specify_cli.delivery.ledger import SqliteDeliveryLedger
    from specify_cli.event_journal.journal import EventJournal
    from specify_cli.sync.queue import get_max_queue_size
    from specify_cli.sync.sync_runtime import _open_active_body_queue

    if runtime.target is None:
        raise RuntimeError("status target diagnostics were not requested")

    # Both reads can stat/open files.  Resolve them before the project UoW owns
    # BEGIN IMMEDIATE so local diagnostics never hold SQLite across filesystem
    # or a second read-only SQLite boundary.
    max_queue_size = get_max_queue_size()
    # Reached off the host module object (not an early-bound import) so a
    # ``monkeypatch.setattr("...sync._read_migration_conflicts_readonly", ...)``
    # still intercepts (INV-4); the host is Any-typed, so the value is absorbed
    # into a typed local rather than returned late-bound (mypy-strict guardrail).
    migration_conflicts: tuple[Any, ...] = sync_module._read_migration_conflicts_readonly()
    with runtime.store.unit_of_work() as unit:
        report: dict[str, Any] = build_status_report(
            resolved_target=runtime.target,
            journal=EventJournal(unit, runtime.store.layout_generation()),
            ledger=SqliteDeliveryLedger(unit, runtime.store.layout_generation()),
            context=runtime.store.create_context_from_unit(unit),
            body_upload_queue=_open_active_body_queue(
                runtime,
                unit,
                max_queue_size=max_queue_size,
            ),
            migration_conflicts=migration_conflicts,
            base=base,
        )
    return report


def _empty_selection_cause(report: PerProjectStoreReport) -> str:
    """Explain WHY a drain selected nothing, using only what the report can prove.

    FR-005 asks the drain to "report the real cause". Before this, `sync now` printed
    an all-zero counts line ending ``(selected 0)`` and stopped, which collapses four
    situations that need four different actions:

    * the journal is empty — nothing to do, and emphatically not a consent problem;
    * no project has consented — the operator's data will never ship until they act,
      which is the incident's own shape and the only one that is urgent;
    * every row's identity is unresolved — recoverable, and H4 wired the remedy;
    * a consented project's rows exist but none is selectable right now.

    That last branch is deliberately the weakest claim. Distinguishing "already
    delivered" from "terminally drain-blocked" needs ledger state the report does not
    carry, so it names both possibilities instead of asserting one. Guessing here
    would recreate exactly the wrong-and-actionable diagnosis the no-Private-Teamspace
    message was: an operator told the wrong cause acts on the wrong thing.

    Sourced entirely from :func:`build_per_project_store_report` — the same grouping
    that backs `doctor`, `status` and `migrate`, so the four surfaces cannot disagree
    about who is in the store (C-003). No second classifier.
    """
    if not report.rows:
        return "The event journal is empty — no events have been captured for this producer scope yet, so there is nothing to send."

    total = report.counted_event_total
    if report.unresolved_identity_count >= total > 0:
        return (
            f"All {total} retained event(s) have no stored project identity, so none "
            "of them can be selected for delivery. Run `spec-kitty sync migrate` to "
            "recover the identity of any whose stored payload still carries it."
        )

    if not any(row.consent_granted for row in report.rows):
        named = ", ".join((row.repo_slug or row.project_slug or row.project_uuid or "<unnamed>") for row in report.named_non_consenting_rows)
        detail = f": {named}" if named else ""
        return (
            f"No project in the event journal has consented to hosted sync{detail}. "
            f"Its {total} retained event(s) stay on this machine and will never be "
            "delivered until consent is recorded — run `spec-kitty sync opt-in` in "
            "the project that should ship, or `spec-kitty sync doctor` for the full "
            "per-project breakdown."
        )

    return (
        "Every consented project's retained events have already been delivered to "
        "this target, or are terminally drain-blocked. Nothing is being withheld "
        "for lack of consent; `spec-kitty sync doctor` shows the per-project state."
    )


def _unresolved_origin_clause(report: PerProjectStoreReport) -> str:
    """Name the repos the unresolved rows appear to come from, with counts (SC-004).

    Without this an operator is told a number and nothing else, and has to open
    SQLite to learn which repos are involved — even though the slugs are already on
    the rows and in the identity projection. Worded as *appear to come from*: with
    no uuid these rows' consent cannot be resolved, so this is provenance, never a
    statement about what any of those projects decided.
    """
    candidates: tuple[UnresolvedIdentityCandidate, ...] = tuple(
        candidate for row in report.rows if row.is_unresolved_identity for candidate in row.unresolved_candidates
    )
    if not candidates:
        return ""
    from specify_cli.delivery.status_report import unresolved_candidate_name

    named = ", ".join(f"{unresolved_candidate_name(candidate) or _NO_RECORDED_NAME} ({candidate.event_count})" for candidate in candidates)
    return (
        f" They appear to come from: {named}. Consent for these rows cannot be "
        "resolved without a project identity, so this is where they were captured, "
        "not what those projects decided."
    )


def _per_project_store_issues(report: PerProjectStoreReport) -> list[str]:
    """The operator-actionable warnings a per-project breakdown implies.

    Kept separate from the rendering so ``doctor``'s "Issues found" list and
    ``status``'s warnings cannot say different things about the same report. Living
    here — in neither command's module — is what keeps ``status`` and ``doctor``
    decoupled (Pd-2): both import this one derivation instead of one reaching into
    the other.
    """
    issues: list[str] = []
    # Reconciliation is the load-bearing check: a table that omits rows is the
    # incident's false-green with a nicer layout.
    if not report.reconciles:
        issues.append(
            f"Per-project totals ({report.counted_event_total}) do not reconcile "
            f"against the journal's retained count ({report.retained_event_count}). "
            "The report is incomplete — do not trust it."
        )
    if report.unresolved_identity_count:
        # Deliberately not "permanently undeliverable", and no longer pointing at
        # `purge` as the only remedy. Since #3030 H4 wired the identity backfill
        # into `sync migrate`, rows whose stored envelope carries a resolvable uuid
        # ARE recoverable, and for the operator's own consenting project that is the
        # difference between their history shipping and being stranded forever.
        # Sending them to `purge` would destroy recoverable data. What is permanent
        # is only that a NULL row cannot be SELECTED (FR-011, fail-closed).
        issues.append(
            f"{report.unresolved_identity_count} journal event(s) have no stored "
            "project identity, so they cannot be selected for delivery. Run "
            "`spec-kitty sync migrate` to recover the identity of any whose stored "
            "payload still carries it; whatever remains is retained locally and "
            "removable only with `spec-kitty sync purge`." + _unresolved_origin_clause(report)
        )
    # NAMED refusals only. The unresolved-identity bucket is also
    # `consent_granted=False`, but its consent could not be resolved at all — see
    # `named_non_consenting_rows`. Naming one of its member repos here told the
    # operator that repo had refused and should be purged; purging it leaves the
    # bucket's other repos on disk while the report reads clean.
    non_consenting = report.named_non_consenting_rows
    if non_consenting:
        named = ", ".join((r.repo_slug or r.project_slug or r.project_uuid or "<unnamed>") for r in non_consenting)
        issues.append(
            f"{len(non_consenting)} project(s) in the journal have not consented to "
            f"hosted sync: {named}. Their events are retained locally and never "
            "delivered; `spec-kitty sync purge --project <slug>` removes them."
        )
    return issues


#: Wording for every reachable :attr:`TrackerEgressVerdict.channel1_state` value
#: (#3108 FR-014). Rendered from the *field*, never parsed out of ``message`` --
#: at ``HOSTED_SERVICE`` all three refusal states share one message (FR-016's
#: byte-identity carve-out, ``decisions/DM-FR016-hosted-byte-identity.md``), and
#: this dict is the only place that distinction still reaches an operator.
#: Deliberately exhaustive over the closed six-member state set so a state this
#: build fails to recognise renders its own name rather than nothing (the
#: ``.get(..., state)`` fallback in :func:`channel1_state_wording`).
_CHANNEL1_STATE_WORDING: Final[dict[str, str]] = {
    CHANNEL1_GRANTED: "hosted-sync consent is granted for this project",
    CHANNEL1_NO_RECORD: "no record of hosted-sync consent exists for this project",
    CHANNEL1_RECORDED_REFUSAL: "a refusal is recorded for this project",
    CHANNEL1_NOT_CONSENTABLE: "not consentable, no project identity resolved",
    CHANNEL1_UNCLASSIFIED: "refuses, but the specific reason could not be classified",
    CHANNEL1_UNDETERMINED: "undetermined -- this directory is not inside a checkout",
}


def channel1_state_wording(state: str) -> str:
    """Map a Channel-1 state token to its operator wording (fallback: the token).

    The closed six-member state set is spelled out in :data:`_CHANNEL1_STATE_WORDING`;
    an unrecognised token renders its own name so a future state addition is never an
    invisible blank rather than a visible ``state``.
    """
    return _CHANNEL1_STATE_WORDING.get(state, state)


def tracker_egress_row_issue(
    *,
    destination_value: str,
    state_wording: str,
    safe_message: str,
    refused: bool,
    binding_present: bool,
) -> str | None:
    """The ``issues`` entry a single tracker-egress row contributes, or ``None``.

    ``binding_present`` gates the entry **only** — never what a row prints. A
    checkout with **no tracker bound at all** has no tracker-egress problem to
    remediate: absence of both channels refuses a transmission nothing is
    attempting. So a refused row on an unbound checkout contributes no issue.

    Both ``state_wording`` and ``safe_message`` are supplied already-rendered by the
    caller (the markup escape of ``verdict.message`` is a render concern and must be
    byte-identical to the printed line, HIGH-1 / C-020); this function only decides
    whether an issue is owed and assembles it from those strings.
    """
    if refused and binding_present:
        return f"tracker egress to {destination_value} is refused (Channel 1: {state_wording}): {safe_message}"
    return None


#: Every ``ConfigReadFault.kind`` mapped to **the operator action that resolves it**,
#: never to a restatement of the kind. That is the whole requirement: the defect
#: FR-020 exists to remove is an operator being told "no consent record for this
#: project" when the truth is "your index is unreadable", which sends them to record
#: consent they already recorded — and on the machine index that write *destroys the
#: other projects' records* (see :data:`_CONSENT_FAULT_NOT_ABSENCE`).
#:
#: Four kinds. FR-027 added ``unusable`` — a present-but-uninterpretable value —
#: alongside the file-level kinds, and it is the one most easily mistaken for absence
#: because the file looks perfectly fine.
#:
#: **The wording narrows because the vocabulary was unified.** Until 2026-07-30 the two
#: file-level tokens did not mean the same thing to both producers: ``sync/config.py``
#: called a TOML *syntax* error ``unparseable`` and an ``OSError`` ``unreadable``, while
#: ``sync/consent.py`` called an open-*or*-parse failure ``unreadable`` and a non-mapping
#: top level ``unparseable``. One kind-keyed string therefore had to span both readings
#: — "either its syntax does not parse, or its top level is not a mapping" — which meant
#: telling every reader one true thing and one false one. ``sync/consent.py`` now splits
#: cannot-open from cannot-parse and mints ``wrong_shape`` for a non-mapping top level
#: (see ``sync.config.CONFIG_FAULT_KINDS``), so each entry below names one state and one
#: remedy. Pinned by ``test_the_action_is_true_for_both_producers_of_the_same_kind``,
#: which now asserts the two producers agree rather than that the advice hedges.
#:
#: The first element of each triple is the status word printed beside the scope, so a
#: field-level fault is no longer announced as an unreadable file.
_CONSENT_FAULT_ACTIONS: dict[str, tuple[str, str, str]] = {
    "unreadable": (
        "UNREADABLE",
        "MAKE THE FILE READABLE",
        "It could not be opened at all — a permission or ownership problem. Fix the file's mode or its owner; the error in brackets says which applies.",
    ),
    "unparseable": (
        "UNPARSEABLE",
        "REPAIR THE FILE'S SYNTAX",
        "The file was opened and its syntax does not parse. Repair the error quoted in the detail — it names the line the parser stopped on.",
    ),
    "wrong_shape": (
        "WRONG SHAPE",
        "MAKE THE DOCUMENT A MAPPING",
        "The file parsed cleanly; its top level is simply not a set of keys. A list, a "
        "bare scalar or a leftover merge-conflict marker does this. Do not go looking "
        "for a syntax error — there is none.",
    ),
    "unusable": (
        "UNUSABLE VALUE",
        "CORRECT THE FIELD VALUE NAMED IN THE DETAIL",
        "The file parsed and its shape is fine, but a field holds a value that cannot "
        "be understood as that field. Only a real boolean records a consent decision, so "
        '`sync.enabled: "false"` is a quoted string that records nothing, and `enabled: no` '
        'is the string "no" (ruamel is YAML 1.2). A `project.uuid` that is not a uuid '
        "names no project.",
    ),
}

#: The fallback for a kind this build does not recognise. Not defensive padding: this
#: mission added a kind once already, and a kind-keyed table that renders nothing for
#: an unrecognised key would turn the next addition into an invisible fault — the
#: exact defect shape this section exists to close.
_CONSENT_FAULT_UNKNOWN_ACTION = (
    "UNREADABLE",
    "REPAIR THE FILE NAMED IN THE DETAIL",
    "This build has no specific advice for that fault kind; the detail below is the whole of what is known about it.",
)

#: Printed for every fault, on both surfaces. The second half is measured, not
#: reasoned — and it was **rewritten on 2026-07-30 because the hazard it described was
#: fixed**, which is the only honest reason to change operator advice. It used to read
#: "a write rewrites the file from an empty document when it cannot be read, discarding
#: every other project's record", and that was true: every `SyncConfig` setter was a
#: whole-file read-modify-write over `_load()`, which answers `{}` for an unreadable
#: file. Seven of the eight destroyed a bystander project's grant, and the same
#: destruction was reachable from a plain *read* via `consent._reconcile_index`.
#:
#: A write over an unreadable config is now refused
#: (`sync.config.ConfigNotReadableError`), so the records survive. Leaving the old
#: sentence standing would have been the same defect this section exists to remove, one
#: turn later: advice that was true when written and is false when read.
#: ``tests/cli/commands/test_sync_doctor_consent_health_3030.py`` pins both halves.
_CONSENT_FAULT_NOT_ABSENCE = (
    "This is NOT a missing consent record. Recording consent again will not clear it: "
    "a write over a config that cannot be read is refused, so your other projects' "
    "records are safe, but nothing is delivered until the file itself is repaired."
)


@dataclass(frozen=True)
class ConsentFaultView:
    """The rendered fields + ``issues`` entry a single consent fault contributes.

    Both the printed block and the ``issues`` string are built from the same
    derivation, so doctor's summary and the readability section cannot say different
    things about one fault. The render half reads ``status``/``action``/``remedy``/
    ``detail``/``consequence`` off this view and appends :attr:`issue` verbatim.
    """

    kind: str
    status: str
    action: str
    remedy: str
    detail: str
    consequence: str
    issue: str


def consent_fault_view(*, scope: str, fault: Any, consequence: str) -> ConsentFaultView:
    """Derive the printable fields + ``issues`` entry for one consent fault.

    ``fault`` is any object exposing ``kind`` / ``detail`` (a ``ConfigReadFault``);
    it is read defensively (``getattr``) exactly as the inline renderer did, so an
    absent field degrades to the same ``unknown`` / ``no detail recorded`` text
    rather than raising.
    """
    kind = str(getattr(fault, "kind", "") or "unknown")
    status, action, remedy = _CONSENT_FAULT_ACTIONS.get(kind, _CONSENT_FAULT_UNKNOWN_ACTION)
    detail = str(getattr(fault, "detail", "") or "no detail recorded")
    issue = f"{scope} ({kind}): {action}. {detail} {consequence} {_CONSENT_FAULT_NOT_ABSENCE}"
    return ConsentFaultView(
        kind=kind,
        status=status,
        action=action,
        remedy=remedy,
        detail=detail,
        consequence=consequence,
        issue=issue,
    )
