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
from pathlib import Path

from specify_cli.event_journal import (
    DRAIN_BLOCKED_DAEMON_LOCK,
    DRAIN_BLOCKED_MISSING_AUTH,
    DRAIN_BLOCKED_MISSING_TEAM,
    DRAIN_BLOCKED_NETWORK,
    DRAIN_BLOCKED_PRIVATE_TEAMSPACE,
    DRAIN_BLOCKED_SAAS_DISABLED,
    EventIdentityRow,
)

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

    return consented_project_uuids(list(candidates), checkout_roots=_drain_checkout_roots())


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


def selectable_event_ids(
    rows: Iterable[EventIdentityRow],
    *,
    consent_predicate: ConsentPredicate | None = None,
) -> list[str]:
    """Return the ids of rows eligible to ship, in the order given.

    Order is preserved so drains stay reproducible. Consent is resolved once for
    the whole candidate set rather than per row, so a 100k-row journal across 20
    projects costs 20 consent lookups, not 100k (NFR-003).
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
    """Count rows with no resolvable identity (FR-011; WP07 surfaces it)."""
    return sum(1 for row in rows if not row.project_uuid)


# ``selectable_event_ids`` is the module's only name with a real ``src/`` consumer
# (``delivery/dispatcher.py``); everything else here is used only within this module
# or by tests. The symbol-level dead-code gate is a shrink-only ratchet, so the
# advertised surface shrinks to match rather than the allowlist growing to excuse it.
# All the trimmed names remain importable — notably ``unselectable_identity_count``,
# which FR-011's report is expected to consume once WP07's surface lands.
__all__ = [
    "selectable_event_ids",
]
