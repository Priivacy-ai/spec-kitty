"""Status-report assembly for ``sync status --check --json`` (WP11, IC-08).

This module is the *logic half* of plan concern IC-08: it assembles the
**additive** JSON sections mandated by contract §6 (Status And Compatibility) —
the seven from WP11 plus #3030 FR-015's ``per_project_store`` — so the WP12 CLI
wiring stays thin. It is a pure, side-effect-free reader: it only consumes the
already-resolved domain surfaces it is handed —

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
  ``body_upload_compatibility``;
* #3030 WP07 :func:`build_per_project_store_report` → ``per_project_store``
  (whose data is in the journal, each project's consent state, and whether the
  breakdown accounts for every retained row — FR-011 / FR-015 / SC-004).

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

from collections.abc import Collection
from dataclasses import dataclass

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
from specify_cli.delivery.selection import unselectable_identity_count
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
#: #3030 FR-015: `sync status` is one of the three surfaces that must answer
#: "whose data is in the journal?". Added after the seven WP11 sections, so the
#: additive-only compatibility rule (SC-010) still holds — no existing key moves.
PER_PROJECT_STORE_KEY = "per_project_store"


def default_status_sections() -> dict[str, Any]:
    """Return every additive section in their empty/default shape.

    This is the canonical, side-effect-free *zero state* of the additive
    status surface (contract §6): every section key is present with a fully
    populated empty value (no missing keys, no ``None`` sections), so the WP12
    CLI can seed a status payload — or fall back when a domain surface is
    unavailable — without ever emitting a partial section. The same shape is
    what :func:`build_status_report` converges to when handed empty journal /
    ledger / registry inputs (e.g. zero retained events, zero ledger rows) —
    with one deliberate exception, ``per_project_store["reconciles"]``, whose
    comment below explains why the zero state must not claim ``true``.

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
        PER_PROJECT_STORE_KEY: {
            # ``None``, not ``True``. This zero state is also the CLI's fallback
            # when the runtime could NOT be opened, and a section that claims
            # "reconciles: true" about a store it never read is the incident's
            # false-green in JSON. ``null`` means unanswered, so a consumer
            # checking truthiness alarms instead of relaxing. It is the one
            # section whose default therefore does NOT equal what a real,
            # empty-journal ``build_status_report`` converges to (that reports
            # ``true``) — deliberately.
            "reconciles": None,
            "retained_event_count": 0,
            "counted_event_total": 0,
            "unresolved_identity_count": 0,
            "non_consenting_project_count": 0,
            "projects": [],
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


def _per_project_store_section(journal: EventJournal) -> dict[str, Any]:
    """Who has data in the journal, with consent state (#3030 FR-015, SC-004).

    FR-015 names three surfaces — ``sync doctor``, ``sync status`` and ``sync
    migrate`` — and this is ``status``'s. Sourced from
    :func:`build_per_project_store_report` rather than re-grouping here, so the
    machine-readable section and the two rendered ones cannot disagree about the
    same invariant (C-003).

    ``reconciles`` is the field a monitor should key on: ``false`` means the
    per-project rows do not account for every retained event, i.e. the breakdown
    is incomplete and must not be trusted.
    """
    report = build_per_project_store_report(journal)
    return {
        "reconciles": report.reconciles,
        "retained_event_count": report.retained_event_count,
        "counted_event_total": report.counted_event_total,
        "unresolved_identity_count": report.unresolved_identity_count,
        # Counts projects KNOWN to have withheld consent. The unresolved-identity
        # bucket is excluded on purpose — see ``named_non_consenting_rows`` — so a
        # monitor keying on this never reports a refusal that cannot be known.
        "non_consenting_project_count": len(report.named_non_consenting_rows),
        "projects": [
            {
                "project_uuid": row.project_uuid,
                "project_slug": row.project_slug,
                "repo_slug": row.repo_slug,
                "event_count": row.event_count,
                "oldest_created_at": row.oldest_created_at,
                "consent_granted": row.consent_granted,
                "consent_level": row.consent_level,
                "consent_reason": row.consent_reason,
                "unresolved_identity": row.is_unresolved_identity,
                # Where the bucket's rows appear to have come from, per repo. Empty
                # for a resolved project. Never an attribution of consent.
                "unresolved_candidates": [
                    {
                        "repo_slug": candidate.repo_slug,
                        "project_slug": candidate.project_slug,
                        # The name the CLI renders, resolved here so a machine
                        # consumer does not re-implement the fallback chain — two
                        # copies of it is exactly how N1-a happened. ``null`` means
                        # nothing was recorded in either column.
                        "name": unresolved_candidate_name(candidate),
                        "event_count": candidate.event_count,
                        "oldest_created_at": candidate.oldest_created_at,
                    }
                    for candidate in row.unresolved_candidates
                ],
            }
            for row in report.rows
        ],
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
    """Assemble the additive status sections (contract §6, FR-019, SC-010).

    Returns a JSON-serializable dict. When *base* (an existing
    ``sync status --check --json`` payload) is supplied, the sections are
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
        PER_PROJECT_STORE_KEY: _per_project_store_section(journal),
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
    # PER_PROJECT_STORE_KEY is deliberately NOT exported. Its seven siblings are,
    # but each of those sits in the dead-symbol gate's allowlist because no src/
    # file imports them; exporting an eighth would mean widening that allowlist to
    # accommodate a name nothing consumes. The constant stays importable, and the
    # key set consumers actually read is single-sourced through
    # ADDITIVE_SECTION_KEYS above.
    "PerProjectStoreReport",
    "ProjectStoreRow",
    "TARGET_AUTHORITY_KEY",
    "UnresolvedIdentityCandidate",
    "TERMINAL_FAILURES_KEY",
    "build_per_project_store_report",
    "build_status_report",
    "default_status_sections",
    "evaluate_gc_suggestion",
    "unresolved_candidate_name",
]


# --- per-project store composition (#3030 WP07 / T021, FR-011 + FR-015) -----
#
# `doctor` read healthy throughout the 2026-07-27 incident. Its queue-health block
# reads `OfflineQueue().get_queue_stats()`, which is EMPTY after `sync migrate` —
# so the operator was shown "Queue size 0" while 9,133 events sat in the journal,
# 1,322 of them belonging to projects that had never opted in. Any per-project
# report rendered from that store reproduces the same false-green, which is why
# FR-015 reconciles against the journal's retained count instead.


@dataclass(frozen=True)
class UnresolvedIdentityCandidate:
    """One repo's share of the unresolved-identity bucket (#3030 N1, FR-011/SC-004).

    The bucket groups every row whose ``project_uuid`` is NULL, and those rows can
    come from DIFFERENT repos — ``emitter.py`` resolves ``project_uuid`` and
    ``repo_slug`` independently, and gates capture on ``checkout_enabled`` rather
    than on uuid resolvability, so a consenting checkout whose uuid resolution fails
    writes one. The bucket therefore has no single identity to report, but the slugs
    ARE on the rows, so declining to report them would force an operator back to
    hand-written SQLite to answer "whose data is in here?" — the exact gap SC-004
    closes.

    A *candidate*, not an attribution: without a uuid, consent cannot be resolved
    for these rows, so this names where they appear to have come from and never
    claims what that project decided.
    """

    repo_slug: str | None
    project_slug: str | None
    event_count: int
    oldest_created_at: str | None


def unresolved_candidate_name(candidate: UnresolvedIdentityCandidate) -> str | None:
    """The recorded name to show for *candidate*, or ``None`` if it recorded none.

    Lives here rather than in the CLI because both operator surfaces (the table
    sub-row and the FR-011 warning) render it, and two copies of a fallback chain is
    how N1-a happened: the named-refusal path already fell back
    ``repo_slug -> project_slug -> uuid``, while the candidate path stopped at
    ``repo_slug`` and reported a named project as nameless.

    ``repo_slug`` leads because ``sync purge --project`` and the consent records are
    keyed on it, so it is the name an operator can act on. ``project_slug`` is the
    fallback. There is no uuid in the chain — for this bucket it is NULL by
    definition, which is why the rows are in it.

    ``None`` means *nothing was recorded*, which callers must render as such rather
    than inventing a substitute.
    """
    return candidate.repo_slug or candidate.project_slug or None


@dataclass(frozen=True)
class ProjectStoreRow:
    """One project's presence in the journal, with its consent state."""

    project_uuid: str | None
    project_slug: str | None
    repo_slug: str | None
    event_count: int
    oldest_created_at: str | None
    consent_granted: bool
    consent_level: str
    consent_reason: str
    #: Populated for the unresolved-identity bucket ONLY, where the row spans
    #: several repos and ``project_slug``/``repo_slug`` are therefore both None.
    #: Empty for a resolved project, which has exactly one identity.
    unresolved_candidates: tuple[UnresolvedIdentityCandidate, ...] = ()

    @property
    def is_unresolved_identity(self) -> bool:
        """Rows the predicate can never select (FR-011).

        Falsy, not ``is None``, so a ``project_uuid`` of ``''`` answers ``True``
        here. That is the same vocabulary the modules that decide selectability
        already use: ``read_identity_projection`` drops falsy uuids from its ``IN``
        list, ``selection.unselectable_identity_count`` counts them via ``not
        row.project_uuid``, and ``retention._journal_census`` files them under
        ``IDENTITY_LESS_KEY``. Keying on ``is None`` made this the one dissenting
        module and let one row carry two diagnoses.

        A whitespace-only uuid is deliberately **not** unresolved: the projection
        returns it, so it is selectable. See the grouping in
        :func:`build_per_project_store_report` for the measurement behind the line.
        """
        return not self.project_uuid


@dataclass(frozen=True)
class PerProjectStoreReport:
    """The full per-project breakdown plus its reconciliation against the journal."""

    rows: tuple[ProjectStoreRow, ...]
    retained_event_count: int
    unresolved_identity_count: int

    @property
    def counted_event_total(self) -> int:
        return sum(row.event_count for row in self.rows)

    @property
    def reconciles(self) -> bool:
        """Whether the per-project totals account for every retained row.

        FR-015's load-bearing property. If this is False the report is lying by
        omission — the shape of the incident's false-green — so callers must
        surface the discrepancy rather than print the table alone.

        The two operands MUST come from independent sources or this check is a
        mathematical identity that no input can falsify. The first implementation
        derived ``retained_event_count`` from the same projection read that
        produced ``rows``, so it was exactly that: always True, including over an
        empty or wrong journal. ``retained_event_count`` now comes from the
        journal's own ``count()`` (a separate ``COUNT(*)``), which is what makes
        the disagreement the check exists to catch actually reachable.
        """
        return self.counted_event_total == self.retained_event_count

    @property
    def named_non_consenting_rows(self) -> tuple[ProjectStoreRow, ...]:
        """Projects that are KNOWN to have withheld consent — safe to name.

        Excludes the unresolved-identity bucket, deliberately and load-bearingly.
        That bucket is also ``consent_granted=False`` (it must never read as
        consented), but for a different reason: its consent could not be resolved at
        all. Including it here made the CLI tell an operator that one arbitrarily
        chosen repo had refused consent and should be purged — a false fact whose
        remedy closes an incident early, leaving the bucket's other repos on disk
        and unnamed. The bucket speaks through ``unresolved_identity_count`` and its
        own FR-011 warning instead, so no row is reported twice under two diagnoses.
        """
        return tuple(
            row
            for row in self.rows
            if not row.consent_granted and not row.is_unresolved_identity
        )


def _unresolved_identity_candidates(
    group: list[Any],
) -> tuple[UnresolvedIdentityCandidate, ...]:
    """Break the unresolved bucket down by the RECORDED IDENTITY of its rows (N1).

    Keyed on the ``(repo_slug, project_slug)`` PAIR, not on ``repo_slug`` alone.
    Keying on the repo slug alone reproduced, one level down, the very defect the
    candidate breakdown was introduced to fix:

    * rows whose ``repo_slug`` was never recorded but whose ``project_slug`` was
      all collapsed into one anonymous candidate and rendered "no repo recorded",
      with the name sitting unread in the adjacent column (N1-a); and
    * that candidate then took the first-found ``project_slug``, so a group
      spanning ``acme-app`` and ``beta-svc`` published one of them as its name
      (N1-b) — the same heterogeneous-group attribution this module forbids for a
      resolved group a few lines below ("a disagreement among them is not a licence
      to invent a third value").

    The three columns are resolved independently at capture — ``project_slug``
    walks a chain over the envelope and the payload, ``repo_slug`` is a single
    top-level lookup, and a nil-sentinel uuid normalises to ``None`` — so
    "``repo_slug`` is null" carries no implication that the row is nameless.

    Two rows therefore share a candidate only when they agree on BOTH columns. Rows
    that recorded neither are still one candidate of their own: they are genuinely
    unattributable (every legacy ``sync migrate`` import is one), and that label has
    to keep meaning what it says or it cannot be trusted when it is the truth.

    Note the count sum-check below is NOT this invariant: merging two distinct names
    keeps the totals perfectly reconciled. It constrains counts; only the pair key
    constrains names.
    """
    by_identity: dict[tuple[str | None, str | None], list[Any]] = {}
    for row in group:
        identity = (row.repo_slug or None, row.project_slug or None)
        by_identity.setdefault(identity, []).append(row)

    candidates = [
        UnresolvedIdentityCandidate(
            repo_slug=repo_slug,
            project_slug=project_slug,
            event_count=len(rows),
            oldest_created_at=min(r.created_at for r in rows),
        )
        for (repo_slug, project_slug), rows in by_identity.items()
    ]
    # Largest first, with the genuinely unnameable candidate last so it never heads
    # the list. Ties break on the rendered name so the order is deterministic.
    candidates.sort(
        key=lambda c: (
            unresolved_candidate_name(c) is None,
            -c.event_count,
            unresolved_candidate_name(c) or "",
        )
    )
    return tuple(candidates)


def build_per_project_store_report(
    journal: Any,
    *,
    event_ids: Collection[str] | None = None,
) -> PerProjectStoreReport:
    """Group the journal by project and resolve each project's consent state.

    Reads the identity projection, so no payload is decoded (NFR-003) and the cost
    is one pass plus one consent lookup per distinct project — not per event.

    Identity-less rows are grouped under a single ``project_uuid=None`` row rather
    than dropped: they are unselectable for as long as the column is NULL, and
    FR-011 exists so that denial is observable instead of silent data loss.

    ``event_ids`` restricts the universe to a named set of rows, which is what
    ``sync migrate`` needs: its claim is about the composition of what IT moved,
    not of the whole journal it moved them into. Restricting rather than adding a
    second grouping implementation keeps FR-015's one invariant expressed once
    (C-003), and the reconciliation stays falsifiable because the requested-id
    count comes from the CALLER while the rows come from the journal's own read —
    a migration that reports an import the journal cannot show fails to reconcile.

    Read-only, deliberately: ``resolve_project_consent`` is called WITHOUT
    ``repo_root``/``checkout_roots``, so its level-1 branch (the only one that
    writes, via ``_reconcile_index``) is unreachable from here. A diagnostic must
    not mutate the consent index it is reporting on (C-001).
    """
    from specify_cli.sync.consent import resolve_project_consent

    # The REPORTING read, not the drain's filtered one. `read_identity_projection`
    # requires a uuid filter so the drain cannot scan (NFR-003); this report has the
    # inverse requirement and must see rows whose project is not known to consent —
    # including NULL-identity rows, which are the whole of FR-011.
    rows = journal.read_identity_projection_for_report()
    if event_ids is not None:
        wanted = frozenset(event_ids)
        rows = [row for row in rows if row.event_id in wanted]

    # **Decision recorded 2026-07-31: a PYTHON-FALSY ``project_uuid`` is
    # identity-less; a whitespace-only one is not.** The line is drawn where the
    # store draws it, measured rather than reasoned:
    #
    # * ``''`` — ``read_identity_projection`` drops it from the ``IN`` list
    #   (``[uuid for uuid in project_uuids if uuid]``), so no drain can ever select
    #   it; ``unselectable_identity_count`` (the counter this report returns, below)
    #   counts it via ``not row.project_uuid``; and ``retention._journal_census``
    #   files it under ``IDENTITY_LESS_KEY``. Identity-less in three modules.
    # * ``'   '`` — the projection *does* return it and ``_journal_census`` keys it
    #   as its own project. It is selectable, so calling it identity-less here would
    #   be a fourth opinion, and would put the bucket (3) back at odds with the
    #   counter (2) — the same double-count in mirror image.
    #
    # Grouping on the raw value made a ``''`` row a NAMED project while the counter
    # ALSO counted it as unresolved — one row, two diagnoses, which
    # ``named_non_consenting_rows`` exists to forbid. The named half was the harmful
    # one: it entered the list whose remedy is ``sync purge --project <slug>``, and
    # ``purge_project_events`` blanks a falsy selector to "select nothing" while
    # ``iter_rows_missing_identity`` matches ``IS NULL`` only — so the operator was
    # sent to a command that provably cannot touch that row.
    #
    # Latent from production writes (``sync/project_identity._normalize`` yields
    # ``None`` for a blank on both the capture and the backfill path), so this is
    # fixed as an agreement between modules rather than as a live leak: ``retention``
    # and ``test_purge_all_events_3030`` already treat the population as real enough
    # to special-case, and one mission must not hold two definitions of it.
    #
    # ``'   '`` remains reported as a named project that no purge selector can reach
    # (``retention.purge_all_events`` documents it as population 2). That is a single
    # diagnosis, which is all this grouping owes it; making it *removable* is a
    # retention concern, not a reporting one.
    grouped: dict[str | None, list[Any]] = {}
    for row in rows:
        grouped.setdefault(row.project_uuid or None, []).append(row)

    report_rows: list[ProjectStoreRow] = []
    for project_uuid, group in grouped.items():
        candidates: tuple[UnresolvedIdentityCandidate, ...] = ()
        if project_uuid is None:
            # NO first-found slug here. The bucket spans repos, so adopting one
            # member's slug reports a project identity the bucket does not have —
            # and, via the consent warning, a refusal that cannot be known. The
            # slugs are surfaced as candidates instead (SC-004 without the lie).
            project_slug = None
            repo_slug = None
            candidates = _unresolved_identity_candidates(group)
            decision_granted = False
            level = "unresolved_identity"
            reason = (
                "no stored project identity; unselectable while the column is "
                "NULL or blank, and counted here rather than dropped (FR-011)"
            )
        else:
            # Safe for a resolved project: every row in this group shares one
            # ``project_uuid``, so the slugs describe one identity. A disagreement
            # among them is not a licence to invent a third value.
            project_slug = next((r.project_slug for r in group if r.project_slug), None)
            repo_slug = next((r.repo_slug for r in group if r.repo_slug), None)
            # `project_uuid` ONLY. The `repo_slug=` argument this used to pass was
            # removed when #3030 reverted repo-slug-keyed consent: a repo slug is a
            # mutable git remote, so keying a grant on it lets a fresh clone, a renamed
            # remote or a re-`git init`ed repo inherit a decision nobody made (FR-019).
            # The slug is still READ above and rendered — naming which repo a row came
            # from is the report's job — but it never influences the decision.
            decision = resolve_project_consent(project_uuid)
            decision_granted = decision.granted
            level = str(decision.level)
            reason = decision.reason

        report_rows.append(
            ProjectStoreRow(
                project_uuid=project_uuid,
                project_slug=project_slug,
                repo_slug=repo_slug,
                event_count=len(group),
                oldest_created_at=min(r.created_at for r in group) if group else None,
                consent_granted=decision_granted,
                consent_level=level,
                consent_reason=reason,
                unresolved_candidates=candidates,
            )
        )

    # Deterministic: consenting first, then by count descending, with the
    # unresolved-identity bucket last so it never hides at the top.
    report_rows.sort(
        key=lambda r: (
            r.is_unresolved_identity,
            not r.consent_granted,
            -r.event_count,
            r.project_uuid or "",
        )
    )

    # INDEPENDENT of the projection above, deliberately. Using len(rows) here
    # would make `reconciles` a tautology — see its docstring. A journal that
    # cannot answer count() reports -1, which never equals a non-negative total,
    # so an unanswerable count surfaces as "does not reconcile" rather than as
    # silent agreement.
    #
    # For a restricted report the independent operand is the caller's own tally of
    # the ids it asked about; journal.count() counts the whole table and could
    # never match a subset, so reusing it there would turn `reconciles` into a
    # permanent False — an alarm that always fires is as useless as one that never
    # does.
    if event_ids is not None:
        retained = len(frozenset(event_ids))
    else:
        try:
            retained = int(journal.count())
        except Exception:
            retained = -1

    return PerProjectStoreReport(
        rows=tuple(report_rows),
        retained_event_count=retained,
        # WP06's counter, not a second one: `selection.unselectable_identity_count`
        # already defines "rows the predicate can never select" and its docstring
        # names WP07 as the surface. Re-deriving it here would be two
        # representations of one invariant (C-003) that could drift.
        unresolved_identity_count=unselectable_identity_count(rows),
    )
