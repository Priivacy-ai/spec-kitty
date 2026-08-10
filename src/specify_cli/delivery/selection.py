"""Per-project selection: which journal rows are eligible to ship (#3030 WP06).

This is the seam the 2026-07-27 leak went through. ``_select_undelivered`` took its
universe from ``journal.read_all()`` — every row of every project on the machine —
and applied no project predicate at all. The consent gate did not exist in the
delivery context; ``GateKind`` covered SaaS-enabled, private-teamspace, auth and
endpoint, none of which is per-project.

Two independent filters live here, and keeping them independent matters:

**1. Consent (FR-007, T018).** The stored ``project_uuid`` column is the **sole
authority** for selection. Post-backfill it is never re-derived from the payload at
selection time: SQL ``IN`` never matches NULL, so a legacy or nil-sentinel row is
invisible to an indexed predicate while an in-memory chain would often resolve it —
the same event would be deliverable on one path and denied on the other. Pinned
rule: NULL rows are permanently unselectable and counted under FR-011, not lazily
re-resolved. The in-memory chain is used only by FR-004's refusal check and by the
backfill.

**2. Drain-blocked reason (T003).** ``drain_blocked_reason`` records why the capture
layer thought an event was not ready. It is **not** a consent representation — see
C-003's recorded decision — and the vocabulary is split rather than excluded
wholesale, because excluding every non-null value would permanently strand every
capture taken before login. The split is *policy vs readiness*:

- **terminal** — the operator's own policy did not permit shipping this event at
  capture time. Excluded from selection.
- **transient** — the operator consented, but the machine was not ready
  (unauthenticated, team unresolved, network down, daemon lock). Re-evaluated on
  every tick and still selectable, per ``emitter.py``'s stated contract that
  drain-blocked events are re-evaluated each drain.
"""
from __future__ import annotations

from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from specify_cli.delivery.consent_gate import ConsentAnswer, resolve_consent_answer
from specify_cli.event_journal import (
    DRAIN_BLOCKED_DAEMON_LOCK,
    DRAIN_BLOCKED_MISSING_AUTH,
    DRAIN_BLOCKED_MISSING_TEAM,
    DRAIN_BLOCKED_NETWORK,
    DRAIN_BLOCKED_PRIVATE_TEAMSPACE,
    DRAIN_BLOCKED_SAAS_DISABLED,
    EventIdentityRow,
)
from specify_cli.sync.project_context import ConsentState, ProjectSyncContext

#: Policy: the operator had hosted sync off for this capture, so shipping it now
#: would deliver something they had not agreed to ship. ``classify_drain_blocked_reason``
#: maps both ``not saas_enabled`` and ``not checkout_enabled`` onto this single
#: token, and the two are indistinguishable after the fact — the second is a
#: consent refusal, so the pair is treated fail-closed as terminal.
TERMINAL_DRAIN_BLOCKED_REASONS: frozenset[str] = frozenset(
    {DRAIN_BLOCKED_SAAS_DISABLED}
)

#: Readiness: the operator consented; the machine was not ready. These MUST stay
#: selectable or an honest user's pre-login backlog is stranded forever.
TRANSIENT_DRAIN_BLOCKED_REASONS: frozenset[str] = frozenset(
    {
        DRAIN_BLOCKED_MISSING_AUTH,
        DRAIN_BLOCKED_MISSING_TEAM,
        DRAIN_BLOCKED_PRIVATE_TEAMSPACE,
        DRAIN_BLOCKED_DAEMON_LOCK,
        DRAIN_BLOCKED_NETWORK,
    }
)

#: A consent predicate: given candidate uuids, return those that consent. Injected
#: so the dispatcher stays free of a hard dependency on the sync package's
#: resolution rules, mirroring how ``ReceiverGate`` is passed in as pure data.
#:
#: Deliberately takes uuids and nothing else. It used to also receive a
#: ``{uuid: repo_slug}`` map, which existed only to feed a repo-slug-keyed consent
#: level; that level was removed (FR-019 — a mutable git remote cannot speak for a
#: project), and the parameter went with it so the seam cannot re-acquire a second
#: authorization key by accident.
ConsentPredicate = Callable[[Sequence[str | None]], frozenset[str]]


def _default_consent_predicate(candidates: Sequence[str | None]) -> frozenset[str]:
    """Resolve consent through WP05's single resolver.

    Offers the checkout the drain is running in as a level-1 root, resolved **once
    per drain** rather than per row. Without it the project-local
    ``.kittify/config.yaml`` level is unreachable on every real drain — the resolver
    would fall straight through to the machine-global index, and a committed,
    reviewable in-repo refusal would silently not be honoured at delivery time.

    A root that declares a different ``project_uuid`` is ignored by the resolver, so
    passing the current checkout can only ever answer for its own project. When the
    drain runs outside any checkout (the daemon's usual case) there is no root to
    offer and the chain degrades to the index, then to deny — never to a grant.
    """
    from specify_cli.sync.consent import consented_project_uuids

    return frozenset(
        consented_project_uuids(
            list(candidates), checkout_roots=_drain_checkout_roots()
        )
    )


def _drain_checkout_roots() -> list[Path]:
    """The checkout the drain is running in, if it is running in one at all."""
    try:
        from specify_cli.core.paths import locate_project_root

        root = locate_project_root(Path.cwd().resolve())
    except Exception:  # noqa: BLE001 - an unreadable cwd is absence, not a decision
        return []
    return [root] if root is not None else []


def is_terminally_blocked(reason: str | None) -> bool:
    """Whether *reason* permanently excludes a row from selection (T003).

    An unrecognised non-null reason is treated as terminal. Fail-closed: a token
    this module has never seen cannot be shown to be a mere readiness problem, and
    the cost of wrongly excluding is a stranded event the operator can purge,
    while the cost of wrongly including is an unconsented delivery.
    """
    if reason is None:
        return False
    return reason not in TRANSIENT_DRAIN_BLOCKED_REASONS


def _drain_consent_memo(predicate: ConsentPredicate) -> ConsentPredicate:
    """Wrap *predicate* so each distinct uuid is resolved at most once per drain.

    :func:`select_consented` consults consent twice — once to build the
    SQL project filter, once as the row-level gate — and NFR-003 requires it be
    resolved *once per distinct project*. Memoising here satisfies both: the second
    pass's candidates are a subset of the first's, so it issues no new lookups.

    The memo is per-call, never module-level. A process-lifetime cache would make a
    revoked consent keep granting until restart, and the daemon is long-lived.
    """
    resolved: dict[str, bool] = {}

    def _resolve(candidates: Sequence[str | None]) -> frozenset[str]:
        unknown = [c for c in candidates if c and c not in resolved]
        if unknown:
            granted = predicate(unknown)
            for uuid in unknown:
                resolved[uuid] = uuid in granted
        return frozenset(c for c in candidates if c and resolved[c])

    return _resolve


@dataclass(frozen=True)
class ConsentedSelection:
    """A drain's selected ids **plus the answer that cleared them** (#3030 FR-028).

    The answer is carried, not recomputed. ``select_consented`` already resolves
    consent for every project present in the store in order to build the SQL
    predicate; the dispatcher needs the very same value to mint the
    :class:`~specify_cli.delivery.consent_gate.ConsentedBatch` it hands the
    receiver. Re-asking would be the second consent chain C-003 forbids — and
    worse than merely wasteful, since two resolutions of a revocable decision
    can disagree within one drain.
    """

    event_ids: list[str]
    answer: ConsentAnswer


def select_consented(
    journal: Any,
    *,
    context: ProjectSyncContext,
) -> ConsentedSelection:
    """Select from one explicit store using its coherent authority snapshot.

    Three steps, and the order of the first two is the whole point:

    1. Ask the journal which projects it holds — an index skip-scan costing one seek
       per distinct project, **not** a walk over the rows.
    2. Resolve consent over that small set, once per project.
    3. Read the identity projection **filtered to the consented uuids in SQL**, so
       the ``project_uuid`` index is what excludes the other projects' rows.

    What this replaces: an unfiltered ``ORDER BY created_at`` read of every row of
    every project, filtered in Python afterwards. That read was correct — no
    unconsented row ever shipped — but it made the project index dead weight and
    cost a full table scan plus a sort on every drain batch, which is the cost
    NFR-003 exists to bound.

    Still **no LIMIT** anywhere in this path. ``ledger.select_undelivered`` slices
    the universe this returns; a limit applied before it would let already-delivered
    terminal rows fill the window and be stripped afterwards, yielding an empty
    selection with consented undelivered rows behind it (NFR-002 starvation).
    """
    owner = str(context.project_uuid)
    if journal.project_uuid != owner:
        raise ValueError("selection context does not match the journal store owner")
    granted = context.consent_state is ConsentState.GRANTED and context.epoch_id is not None
    answer = resolve_consent_answer(
        [owner],
        consent_predicate=lambda candidates: (
            frozenset({owner}) if granted and owner in candidates else frozenset()
        ),
    )
    if not granted:
        return ConsentedSelection(event_ids=[], answer=answer)
    # The UUID predicate remains in the repository query even though the physical
    # database is already isolated. Both controls are independently load-bearing.
    rows = journal.read_identity_projection(project_uuids=[owner])
    return ConsentedSelection(
        event_ids=selectable_event_ids(
            rows,
            consent_predicate=lambda candidates: frozenset(
                candidate for candidate in candidates if candidate == owner
            ),
        ),
        answer=answer,
    )


def selectable_event_ids(
    rows: Iterable[EventIdentityRow],
    *,
    consent_predicate: ConsentPredicate | None = None,
) -> list[str]:
    """Return the ids of rows eligible to ship, in the order given.

    Order is preserved so drains stay reproducible. Consent is resolved once for
    the whole candidate set rather than per row, so a 100k-row journal across 20
    projects costs 20 consent lookups, not 100k (NFR-003).

    On the drain path this runs *after* the SQL project filter, over rows already
    restricted to consenting projects, and so is a second gate rather than the only
    one. Both are kept and both are pinned directly — the SQL gate by
    ``tests/delivery/test_nfr003_predicate_cost_3030.py``, this one by
    ``tests/sync/test_consent_resolver_3030.py``, which calls it with a single
    hand-built row and requires a refusal. It is also the gate for any caller
    holding rows it did not fetch through :func:`select_consented`.
    """
    materialised = list(rows)
    predicate = consent_predicate or _default_consent_predicate

    # Resolve consent over the distinct uuids present, preserving first-seen order
    # purely for deterministic behaviour under a stubbed predicate.
    candidates: list[str | None] = []
    seen: set[str] = set()
    for row in materialised:
        uuid = row.project_uuid
        if uuid and uuid not in seen:
            seen.add(uuid)
            candidates.append(uuid)

    consented = predicate(candidates) if candidates else frozenset()

    return [
        row.event_id
        for row in materialised
        if row.project_uuid  # NULL identity is never selectable (NFR-001)
        and row.project_uuid in consented
        and not is_terminally_blocked(row.drain_blocked_reason)
    ]


def unselectable_identity_count(rows: Iterable[EventIdentityRow]) -> int:
    """Count rows with no resolvable identity among *rows* (FR-011).

    Note what this can and cannot see since FR-008's read became project-filtered:
    ``project_uuid IS NULL`` rows are excluded by the SQL predicate, so rows fetched
    through :func:`select_consented` never contain one and this would
    always return 0 for them. FR-011's report must therefore take its count from
    ``EventJournal.count_missing_identity``, which asks the store directly. This
    helper remains correct for any caller that assembled its own row set.
    """
    return sum(1 for row in rows if not row.project_uuid)


# Only names with a real ``src/`` consumer are advertised; the symbol-level dead-code
# gate is a shrink-only ratchet, so the advertised surface shrinks to match rather
# than the allowlist growing to excuse it. Everything trimmed stays importable —
# notably ``selectable_event_ids``, which the consent-resolver pin enters through,
# plus ``is_terminally_blocked``, ``ConsentPredicate`` and the two drain-blocked
# vocabularies, which are consumed inside this module and express the T003 decision
# rather than a public API.
#
# Recomputed from the merged tree during the #3030 lane-f rebase rather than taken
# from either side. ``unselectable_identity_count`` is now advertised: the HEAD side's
# note said FR-011's report "is expected to consume [it] once WP07's surface lands",
# and it has — ``delivery/status_report.build_per_project_store_report`` imports it, so
# FR-011's count has one definition rather than two (C-003).
__all__ = [
    "select_consented",
    "unselectable_identity_count",
]
