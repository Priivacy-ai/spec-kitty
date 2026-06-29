"""Status-report assembly for ``sync status --check --json`` (WP11, IC-08).

This module is the *logic half* of plan concern IC-08: it assembles the seven
**additive** JSON sections mandated by contract §6 (Status And Compatibility) so
the WP12 CLI wiring stays thin. It is a pure, side-effect-free reader: it only
consumes the already-resolved domain surfaces it is handed —

* WP01 :class:`~specify_cli.sync.target_authority.ResolvedSyncTarget` →
  ``target_authority`` (env/config disagreement made observable, contract §1);
* WP03 :class:`~specify_cli.event_journal.EventJournal` → ``event_journal``
  (retained/archived counts, oldest retained timestamp, journal size — the
  bounded-growth surface for NFR-004);
* WP05 :class:`~specify_cli.delivery.ledger.SqliteDeliveryLedger` +
  :class:`~specify_cli.delivery.targets.SqliteDeliveryTargetRegistry` →
  ``delivery_targets`` / ``delivery_ledger`` / ``terminal_failures`` (per-status
  counts, current-vs-previous delivery, inspectable permanent failures);
* WP10 :class:`~specify_cli.sync.migrate_journal.MigrationAudit` →
  ``migration_conflicts`` (unresolved divergent duplicates that block cleanup);
* the existing ``sync/queue.py`` body-upload surface →
  ``body_upload_compatibility``.

**C-006 / NFR-006 separation invariant (do not break):** the
``body_upload_queue`` / ``body_upload_failure_log`` counts live ONLY in the
``body_upload_compatibility`` section. No ``event_journal`` / ``delivery_ledger``
field is ever sourced from the body-upload tables; nothing here may imply a
body-upload row is an event-journal row. Existing top-level fields (passed in via
``base``) are preserved verbatim — this module *adds* sections, never renames or
removes one (SC-010).

Per **C-001** this is a read-only consumer: it never opens SQLite directly to
resolve a target and never mutates the journal, ledger, registry, or audit store.
Destructive payload operations live in :mod:`specify_cli.delivery.retention`.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from specify_cli.delivery.ledger import (
    LEDGER_TABLE,
    STATUS_DUPLICATE,
    STATUS_FAILED_TRANSIENT,
    STATUS_PENDING,
    STATUS_REJECTED,
    STATUS_SUCCESS,
    STATUS_TERMINAL_FAILED,
    TERMINAL_SUCCESS_STATUSES,
)
from specify_cli.delivery.targets import (
    InvalidTargetUrlError,
    canonicalize_url,
    compute_url_hash,
)

if TYPE_CHECKING:
    from specify_cli.delivery.ledger import SqliteDeliveryLedger
    from specify_cli.delivery.targets import SqliteDeliveryTargetRegistry
    from specify_cli.event_journal import EventJournal
    from specify_cli.sync.migrate_journal import MigrationAudit
    from specify_cli.sync.target_authority import ResolvedSyncTarget

# -- additive section keys (contract §6; exported so tests pin the exact set) ---
TARGET_AUTHORITY_KEY = "target_authority"
EVENT_JOURNAL_KEY = "event_journal"
DELIVERY_TARGETS_KEY = "delivery_targets"
DELIVERY_LEDGER_KEY = "delivery_ledger"
MIGRATION_CONFLICTS_KEY = "migration_conflicts"
TERMINAL_FAILURES_KEY = "terminal_failures"
BODY_UPLOAD_COMPAT_KEY = "body_upload_compatibility"


def default_status_sections() -> dict[str, Any]:
    """Return all seven additive sections in their empty/default shape.

    This is the canonical, side-effect-free *zero state* of the additive
    status surface (contract §6): every section key is present with a fully
    populated empty value (no missing keys, no ``None`` sections), so the WP12
    CLI can seed a status payload — or fall back when a domain surface is
    unavailable — without ever emitting a partial section. The same shape is
    what :func:`build_status_report` converges to when handed empty journal /
    ledger / registry inputs (e.g. zero retained events, zero ledger rows).

    The key set is **single-sourced** here: :data:`ADDITIVE_SECTION_KEYS` is
    derived from this dict (``tuple(default_status_sections())``) so
    :func:`build_status_report` and this helper cannot drift to different key
    sets — adding or removing a section in one place updates the exported key
    tuple automatically.
    """
    return {
        TARGET_AUTHORITY_KEY: {},
        EVENT_JOURNAL_KEY: {
            "retained_event_count": 0,
            "archived_event_count": 0,
            "oldest_retained_event_at": None,
            "journal_size_bytes": 0,
            "gc_suggested": False,
            "gc_suggestion": None,
        },
        DELIVERY_TARGETS_KEY: {"current": None, "previous": []},
        DELIVERY_LEDGER_KEY: {
            "delivered_current_target": 0,
            "delivered_previous_target": 0,
            "pending": 0,
            "rejected": 0,
            "transient": 0,
        },
        MIGRATION_CONFLICTS_KEY: {"count": 0, "cleanup_blocked": False, "conflicts": []},
        TERMINAL_FAILURES_KEY: {"count": 0, "events": []},
        BODY_UPLOAD_COMPAT_KEY: {
            "body_upload_queue_count": 0,
            "body_upload_failure_log_count": 0,
        },
    }


# The exported key tuple is derived from the default-section factory so the two
# surfaces share one source of truth and cannot diverge (S1192-safe: the keys
# are the named ``*_KEY`` constants above, referenced once each).
ADDITIVE_SECTION_KEYS: tuple[str, ...] = tuple(default_status_sections())

# "Large journal" threshold for the GC *suggestion* (NFR-004). A single named
# constant (Sonar S1192); callers may pass ``large_threshold_bytes`` to override
# it (production uses this default, tests inject a tiny value). The suggestion is
# gated on this; the journal *size* itself is surfaced unconditionally.
GC_LARGE_JOURNAL_THRESHOLD_BYTES = 50 * 1024 * 1024  # 50 MiB

_GC_SUGGESTION_REASON = (
    "Retained payloads are large and fully delivered to all known targets; "
    "an explicit `sync gc` would reclaim space while preserving delivery history."
)

# -- ledger status reads via the public diagnostic connection (contract §6) ----
# The ledger exposes ``connection`` precisely for these status/diagnostic joins.
# Every identifier below is a static module constant (``LEDGER_TABLE`` + the
# status vocabulary); row *values* always travel via ``?`` placeholders, so there
# is no dynamic SQL and no injection surface (the S608 rationale mirrors the
# sibling ``event_journal/models.py``).
_STATUS_COUNTS_SQL = f"SELECT target_id, status, COUNT(*) AS n FROM {LEDGER_TABLE} GROUP BY target_id, status"  # noqa: S608 — static identifiers; no values interpolated
_TERMINAL_FAILED_SQL = f"SELECT event_id, target_id, last_error FROM {LEDGER_TABLE} WHERE status = ?"  # noqa: S608 — static identifiers; value via ?
_DELIVERED_IDS_SQL = f"SELECT target_id, event_id FROM {LEDGER_TABLE} WHERE status IN (?, ?)"  # noqa: S608 — static identifiers; values via ?


# ---------------------------------------------------------------------------
# Current/previous target resolution (read-only; no second resolver — C-002)
# ---------------------------------------------------------------------------


def _resolve_current_target(resolved_target: ResolvedSyncTarget, registry: SqliteDeliveryTargetRegistry) -> Any:
    """Return the registered :class:`DeliveryTarget` for the resolved active URL.

    Derives the C-002 identity from ``resolved_server_url`` + scope using the
    public canonicalize/hash helpers (never a second resolver) and looks it up
    read-only. ``None`` when the current target is not yet registered (no ledger
    rows can be keyed to it, so its delivered count is 0).
    """
    try:
        canonical = canonicalize_url(resolved_target.resolved_server_url)
    except InvalidTargetUrlError:
        return None
    url_hash = compute_url_hash(canonical)
    return registry.get(url_hash, resolved_target.team_slug, resolved_target.user_id)


def _target_identity_dict(target: Any) -> dict[str, Any]:
    """Identity view (URL + scope) of a registered target."""
    return {
        "target_id": target.target_id,
        "canonical_url": target.canonical_url,
        "team_slug": target.team_slug,
        "user_email": target.user_email,
    }


def _resolved_identity_dict(resolved_target: ResolvedSyncTarget) -> dict[str, Any]:
    """Identity view derived from the resolved target when it is unregistered."""
    try:
        canonical = canonicalize_url(resolved_target.resolved_server_url)
    except InvalidTargetUrlError:
        canonical = resolved_target.resolved_server_url
    return {
        "target_id": None,
        "canonical_url": canonical,
        "team_slug": resolved_target.team_slug or "",
        "user_email": resolved_target.user_id or "",
    }


# ---------------------------------------------------------------------------
# Section builders (one small, independently-testable builder per section)
# ---------------------------------------------------------------------------


def _ledger_status_rows(ledger: SqliteDeliveryLedger) -> list[Any]:
    """Fetch ``(target_id, status, count)`` triples once for the count sections."""
    return list(ledger.connection.execute(_STATUS_COUNTS_SQL).fetchall())


def _delivered_counts_by_target(status_rows: list[Any]) -> dict[str, int]:
    """Per-target terminal-success delivered counts, from the grouped rows."""
    counts: dict[str, int] = {}
    for target_id, status, count in status_rows:
        if status in TERMINAL_SUCCESS_STATUSES:
            counts[str(target_id)] = counts.get(str(target_id), 0) + int(count)
    return counts


def _delivery_ledger_section(status_rows: list[Any], current_target_id: str | None) -> dict[str, Any]:
    """Per-status ledger counts; delivered split into current vs previous target.

    "Current" is the resolved active target's id; every other target with a
    terminal-success row is "previous" (US4 current-vs-previous). Terminal-failed
    is reported in its own ``terminal_failures`` section, never here.
    """
    delivered_current = 0
    delivered_previous = 0
    pending = 0
    rejected = 0
    transient = 0
    for target_id, status, count in status_rows:
        number = int(count)
        if status in TERMINAL_SUCCESS_STATUSES:
            if current_target_id is not None and str(target_id) == current_target_id:
                delivered_current += number
            else:
                delivered_previous += number
        elif status == STATUS_PENDING:
            pending += number
        elif status == STATUS_REJECTED:
            rejected += number
        elif status == STATUS_FAILED_TRANSIENT:
            transient += number
    return {
        "delivered_current_target": delivered_current,
        "delivered_previous_target": delivered_previous,
        "pending": pending,
        "rejected": rejected,
        "transient": transient,
    }


def _delivery_targets_section(
    resolved_target: ResolvedSyncTarget,
    registry: SqliteDeliveryTargetRegistry,
    status_rows: list[Any],
) -> tuple[dict[str, Any], str | None]:
    """Build ``delivery_targets`` and return ``(section, current_target_id)``.

    ``previous`` lists every known target other than the current one that has
    actually received deliveries, with its own delivered count (US4).
    """
    current_target = _resolve_current_target(resolved_target, registry)
    current_target_id = current_target.target_id if current_target is not None else None
    delivered_by_target = _delivered_counts_by_target(status_rows)
    previous: list[dict[str, Any]] = []
    for target in registry.list_targets():
        if current_target_id is not None and target.target_id == current_target_id:
            continue
        delivered = delivered_by_target.get(target.target_id, 0)
        if delivered <= 0:
            continue
        entry = _target_identity_dict(target)
        entry["delivered_count"] = delivered
        previous.append(entry)
    current = _target_identity_dict(current_target) if current_target is not None else _resolved_identity_dict(resolved_target)
    return {"current": current, "previous": previous}, current_target_id


def _delivered_success_ids_by_target(ledger: SqliteDeliveryLedger) -> dict[str, set[str]]:
    """Per-target set of event ids with a terminal-success delivery."""
    rows = ledger.connection.execute(_DELIVERED_IDS_SQL, (STATUS_SUCCESS, STATUS_DUPLICATE)).fetchall()
    by_target: dict[str, set[str]] = {}
    for target_id, event_id in rows:
        by_target.setdefault(str(target_id), set()).add(str(event_id))
    return by_target


def _all_delivered_to_all_known(ledger: SqliteDeliveryLedger, retained_event_ids: tuple[str, ...], known_target_ids: tuple[str, ...]) -> bool:
    """Whether every retained event is delivered (success) to every known target."""
    if not retained_event_ids:
        return True
    retained = set(retained_event_ids)
    delivered = _delivered_success_ids_by_target(ledger)
    return all(retained.issubset(delivered.get(target_id, set())) for target_id in known_target_ids)


def evaluate_gc_suggestion(
    *,
    retained_event_ids: tuple[str, ...],
    journal_size_bytes: int,
    ledger: SqliteDeliveryLedger,
    known_target_ids: tuple[str, ...],
    large_threshold_bytes: int | None = None,
) -> tuple[bool, dict[str, Any] | None]:
    """Gate the GC suggestion (NFR-004): large AND fully delivered to all known.

    Returns ``(gc_suggested, suggestion_or_None)``. With zero known targets the
    "delivered to all known targets" predicate is not meaningful, so no
    suggestion is produced. The journal *size* is surfaced unconditionally by the
    caller — only this *suggestion* is gated.
    """
    threshold = GC_LARGE_JOURNAL_THRESHOLD_BYTES if large_threshold_bytes is None else large_threshold_bytes
    if journal_size_bytes < threshold or not known_target_ids:
        return False, None
    if not _all_delivered_to_all_known(ledger, retained_event_ids, known_target_ids):
        return False, None
    suggestion = {
        "reason": _GC_SUGGESTION_REASON,
        "retained_event_count": len(retained_event_ids),
        "journal_size_bytes": journal_size_bytes,
    }
    return True, suggestion


def _event_journal_section(
    journal: EventJournal,
    ledger: SqliteDeliveryLedger,
    known_target_ids: tuple[str, ...],
    large_threshold_bytes: int | None,
) -> dict[str, Any]:
    """Retained/archived counts, oldest retained timestamp, size, GC suggestion.

    ``journal_size_bytes`` is the retained (live, non-archived) payload volume —
    the bounded-growth signal that is *always* surfaced (NFR-004). Archived rows
    leave the retained surface but are counted separately.
    """
    events = journal.read_all()
    retained = [event for event in events if event.archived_at is None]
    retained_ids = tuple(event.event_id for event in retained)
    size_bytes = sum(len(event.payload) for event in retained)
    oldest = min((event.created_at for event in retained), default=None)
    gc_suggested, gc_suggestion = evaluate_gc_suggestion(
        retained_event_ids=retained_ids,
        journal_size_bytes=size_bytes,
        ledger=ledger,
        known_target_ids=known_target_ids,
        large_threshold_bytes=large_threshold_bytes,
    )
    return {
        "retained_event_count": len(retained),
        "archived_event_count": len(events) - len(retained),
        "oldest_retained_event_at": oldest,
        "journal_size_bytes": size_bytes,
        "gc_suggested": gc_suggested,
        "gc_suggestion": gc_suggestion,
    }


def _terminal_failures_section(ledger: SqliteDeliveryLedger) -> dict[str, Any]:
    """Selector-excluded permanent failures (FR-015) — inspectable, never deleted."""
    rows = ledger.connection.execute(_TERMINAL_FAILED_SQL, (STATUS_TERMINAL_FAILED,)).fetchall()
    events = [
        {
            "event_id": str(row[0]),
            "target_id": str(row[1]),
            "last_error": None if row[2] is None else str(row[2]),
        }
        for row in rows
    ]
    return {"count": len(events), "events": events}


def _conflict_dict(conflict: Any) -> dict[str, Any]:
    return {
        "event_id": conflict.event_id,
        "source_digest": conflict.source_digest,
        "existing_sha": conflict.existing_sha,
        "incoming_sha": conflict.incoming_sha,
        "detail": conflict.detail,
    }


def _migration_conflicts_section(migration_audit: MigrationAudit | None) -> dict[str, Any]:
    """Unresolved divergent-duplicate conflicts (WP10); cleanup-blocked flag."""
    if migration_audit is None:
        return {"count": 0, "cleanup_blocked": False, "conflicts": []}
    conflicts = migration_audit.conflicts()
    return {
        "count": len(conflicts),
        "cleanup_blocked": migration_audit.has_conflicts(),
        "conflicts": [_conflict_dict(conflict) for conflict in conflicts],
    }


def _body_upload_compatibility_section(body_upload_queue: Any) -> dict[str, Any]:
    """Body-upload counts, labeled to keep them distinct from journal/ledger rows.

    C-006: these are the ``sync/queue.py``-owned ``body_upload_queue`` /
    ``body_upload_failure_log`` counts. They are reported here and ONLY here; no
    other section is sourced from the body-upload tables.
    """
    if body_upload_queue is None:
        return {"body_upload_queue_count": 0, "body_upload_failure_log_count": 0}
    return {
        "body_upload_queue_count": int(body_upload_queue.size()),
        "body_upload_failure_log_count": int(body_upload_queue.failure_count()),
    }


# ---------------------------------------------------------------------------
# Public entry point (consumed by the thin WP12 CLI wiring)
# ---------------------------------------------------------------------------


def build_status_report(
    *,
    resolved_target: ResolvedSyncTarget,
    journal: EventJournal,
    ledger: SqliteDeliveryLedger,
    target_registry: SqliteDeliveryTargetRegistry,
    migration_audit: MigrationAudit | None = None,
    body_upload_queue: Any = None,
    base: dict[str, Any] | None = None,
    large_threshold_bytes: int | None = None,
) -> dict[str, Any]:
    """Assemble the seven additive status sections (contract §6, FR-019, SC-010).

    Returns a JSON-serializable dict. When *base* (an existing
    ``sync status --check --json`` payload) is supplied, the seven sections are
    merged in **additively** — every pre-existing top-level field is preserved
    unchanged (the additive section keys never collide with the legacy keys), so
    old consumers keep working (SC-010, contract §6 compatibility rules).

    All inputs are already-resolved domain surfaces; this function opens no
    network connection, mutates nothing, and never reads raw SQLite to resolve a
    target (C-001 / C-002).
    """
    status_rows = _ledger_status_rows(ledger)
    targets_section, current_target_id = _delivery_targets_section(resolved_target, target_registry, status_rows)
    known_target_ids = tuple(target.target_id for target in target_registry.list_targets())
    sections: dict[str, Any] = {
        TARGET_AUTHORITY_KEY: resolved_target.to_diagnostics_dict(),
        EVENT_JOURNAL_KEY: _event_journal_section(journal, ledger, known_target_ids, large_threshold_bytes),
        DELIVERY_TARGETS_KEY: targets_section,
        DELIVERY_LEDGER_KEY: _delivery_ledger_section(status_rows, current_target_id),
        MIGRATION_CONFLICTS_KEY: _migration_conflicts_section(migration_audit),
        TERMINAL_FAILURES_KEY: _terminal_failures_section(ledger),
        BODY_UPLOAD_COMPAT_KEY: _body_upload_compatibility_section(body_upload_queue),
    }
    report: dict[str, Any] = dict(base) if base else {}
    report.update(sections)
    return report


__all__ = [
    "ADDITIVE_SECTION_KEYS",
    "BODY_UPLOAD_COMPAT_KEY",
    "DELIVERY_LEDGER_KEY",
    "DELIVERY_TARGETS_KEY",
    "EVENT_JOURNAL_KEY",
    "GC_LARGE_JOURNAL_THRESHOLD_BYTES",
    "MIGRATION_CONFLICTS_KEY",
    "TARGET_AUTHORITY_KEY",
    "TERMINAL_FAILURES_KEY",
    "build_status_report",
    "default_status_sections",
    "evaluate_gc_suggestion",
]
