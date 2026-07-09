"""Migrate hash-scoped SQLite queues into the append-only event journal (WP10).

This is plan concern **IC-07**: lift the events that are still *currently queued*
in the legacy ``queue.db`` and every scoped ``queues/queue-<digest>.db`` into the
WP03 :class:`~specify_cli.event_journal.EventJournal`, recording per-source
provenance and quarantining divergent-duplicate collisions — without ever
fabricating identity, rewriting an ``event_id``, or touching a source DB.

The unrecoverable-identity reality (contract §5; spec edge case "Hash-only scoped
DB paths"): the queue digest is a **one-way** SHA-256 of ``server|user|team``
(``sync/queue.py::build_queue_scope`` + ``scope_db_path``). The original URL/team
cannot be derived from the filename, so:

* a source whose digest matches the WP01 resolved target's derived queue path is
  attached **best-effort** to that *known* target handle, and
* any unmatched digest (and the legacy ``queue.db``) is attached to an explicit
  **``unknown``** provenance marker — never a guessed URL/team.

Guarantees pinned by ``tests/sync/test_migrate_journal.py``:

* **FR-013 / SC-006** — *all* scoped DBs + legacy ``queue.db`` are discovered and
  every currently-queued payload is preserved across one run; delivered-and-deleted
  history is unrecoverable (only queued payloads survive).
* **NFR-005** — import is idempotent on re-run (journal ``INSERT OR IGNORE`` on
  ``event_id`` + provenance keyed on ``(event_id, source_digest)``); one bad/locked
  source is reported without aborting the others.
* **C-005** — ``event_id`` is carried through verbatim, never rewritten.
* **FR-018 / SC-011** — same ``event_id`` + *divergent* canonical payload writes a
  migration-conflict/audit row, leaves the existing journal payload and the source
  DB untouched, blocks cleanup, and exits non-zero/blocked.

Per **C-001** this module writes only through the WP03 journal public API and its
own migration-audit store (provenance/conflicts are migration metadata that have
no home on a delivery-state ledger row); it never re-implements those tables.
Source DBs are opened **read-only** so they are structurally untouched.
"""
from __future__ import annotations

import contextlib
import hashlib
import json
import re
import sqlite3
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from specify_cli.core.time_utils import now_utc_iso
from specify_cli.event_journal import Event, EventJournal, JournalTransaction

if TYPE_CHECKING:  # pragma: no cover - typing-only (avoid the queue<->authority cycle)
    from specify_cli.sync.target_authority import ResolvedSyncTarget

# --- naming / identifier safety -------------------------------------------

QUEUES_SUBDIR = "queues"
LEGACY_QUEUE_NAME = "queue.db"
LEGACY_DIGEST = "legacy"
AUDIT_DB_NAME = "migration_audit.db"

UNKNOWN_PREFIX = "unknown:"
KNOWN_PREFIX = "known:"

# Only currently-queued payloads survive (FR-013 / contract §5 rules 3 & 7).
MIGRATION_NOTE = (
    "Migrated only currently-queued payloads from discovered queue DBs into the "
    "event journal; delivered-and-deleted history is unrecoverable and was not "
    "reconstructed."
)

# ``queue-<digest>.db`` where ``<digest>`` is the SHA-256-truncated hex from
# ``scope_db_path``. ``re.ASCII`` keeps the match ASCII-only so a non-ASCII
# filename can never masquerade as a digest (charter Identifier Safety).
_QUEUE_DIGEST_RE = re.compile(r"^queue-([0-9a-f]+)\.db$", re.ASCII)

# Explicit ASCII allowlist for any human-readable migration-target token; every
# other code point (including accented Latin) folds to ``_`` so the produced
# identifier is always ``.isascii()`` (charter Identifier Safety).
_NON_IDENTIFIER_CHARS = re.compile(r"[^A-Za-z0-9_]", re.ASCII)


def migration_target_token(raw: str) -> str:
    """Sanitize *raw* to an ASCII-only deterministic migration-target token.

    Uses the ``[A-Za-z0-9_]`` allowlist compiled with ``re.ASCII`` so accented
    input never leaks through the default Unicode ``\\w`` semantics. The result
    is always ``.isascii()`` and stable for a given input.
    """
    return _NON_IDENTIFIER_CHARS.sub("_", raw)


# --- discovered source records (T056) -------------------------------------


@dataclass(frozen=True)
class SourceDb:
    """One discovered migration source: a scoped queue DB or the legacy queue.db.

    ``digest`` is the parsed ``queue-<digest>.db`` hex for scoped DBs, or the
    sentinel :data:`LEGACY_DIGEST` for the legacy ``queue.db`` (which carries no
    digest). ``provenance`` is filled in during import (best-effort known target
    or explicit ``unknown``); the resolved scope is *not* reverse-engineered.
    """

    path: Path
    digest: str
    is_legacy: bool


def _parse_digest(name: str) -> str | None:
    """Return the hex digest of a ``queue-<digest>.db`` filename, else ``None``."""
    match = _QUEUE_DIGEST_RE.match(name)
    return match.group(1) if match else None


def discover_source_dbs(spec_kitty_dir: Path) -> list[SourceDb]:
    """Discover every migration source under *spec_kitty_dir* (T056, FR-013).

    Globs ``queues/queue-*.db`` (parsing the digest; a filename that does not
    match the hex-digest shape is skipped, not misparsed) and includes the legacy
    ``queue.db`` when present. Returns a stable, sorted list so re-runs and tests
    are reproducible. An empty/absent queue dir yields ``[]`` (no error).
    """
    sources: list[SourceDb] = []
    queues_dir = spec_kitty_dir / QUEUES_SUBDIR
    if queues_dir.is_dir():
        for candidate in queues_dir.glob("queue-*.db"):
            digest = _parse_digest(candidate.name)
            if digest is None:
                continue  # malformed filename — not a recoverable scoped DB
            sources.append(SourceDb(path=candidate, digest=digest, is_legacy=False))
    legacy = spec_kitty_dir / LEGACY_QUEUE_NAME
    if legacy.is_file():
        sources.append(SourceDb(path=legacy, digest=LEGACY_DIGEST, is_legacy=True))
    return sorted(sources, key=lambda s: (not s.is_legacy, s.digest))


# --- migration-audit store (provenance + conflicts) -----------------------

_PROVENANCE_SCHEMA = """
CREATE TABLE IF NOT EXISTS migration_provenance (
    event_id      TEXT NOT NULL,
    source_digest TEXT NOT NULL,
    target_id     TEXT NOT NULL,
    payload_sha   TEXT NOT NULL,
    recorded_at   TEXT NOT NULL,
    PRIMARY KEY (event_id, source_digest)
);
CREATE TABLE IF NOT EXISTS migration_conflicts (
    event_id      TEXT NOT NULL,
    source_digest TEXT NOT NULL,
    existing_sha  TEXT NOT NULL,
    incoming_sha  TEXT NOT NULL,
    detail        TEXT,
    recorded_at   TEXT NOT NULL,
    PRIMARY KEY (event_id, source_digest)
);
"""


@dataclass(frozen=True)
class MigrationConflict:
    """A same-``event_id``/divergent-payload collision parked for an operator.

    Records enough for an operator to inspect both sides (the two canonical
    payload digests + the conflicting source digest) without mutating either the
    journal payload or the source DB (FR-018, contract §5 rule 6).
    """

    event_id: str
    source_digest: str
    existing_sha: str
    incoming_sha: str
    detail: str | None = None


class MigrationAudit:
    """SQLite-backed provenance + conflict store for the queue→journal migration.

    Provenance answers "which source DB(s) did this migrated event come from, and
    to which (best-effort/unknown) target was it attached?"; conflicts record the
    divergent-duplicate quarantine. Both writers are idempotent (``INSERT OR
    IGNORE`` on the natural key) so a re-run never duplicates rows (NFR-005).
    """

    def __init__(self, db_path: Path | str = ":memory:") -> None:
        self._db_path = db_path
        is_memory = db_path == ":memory:"
        if not is_memory:
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(db_path))
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(_PROVENANCE_SCHEMA)
        self._conn.commit()

    @property
    def connection(self) -> sqlite3.Connection:
        return self._conn

    def close(self) -> None:
        self._conn.close()

    def record_provenance(
        self, *, event_id: str, source_digest: str, target_id: str, payload_sha: str
    ) -> None:
        """Idempotently record one ``(event_id, source_digest)`` provenance row."""
        self._conn.execute(
            "INSERT OR IGNORE INTO migration_provenance "
            "(event_id, source_digest, target_id, payload_sha, recorded_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (event_id, source_digest, target_id, payload_sha, now_utc_iso()),
        )

    def record_conflict(self, conflict: MigrationConflict) -> None:
        """Idempotently record a divergent-duplicate migration-conflict row."""
        self._conn.execute(
            "INSERT OR IGNORE INTO migration_conflicts "
            "(event_id, source_digest, existing_sha, incoming_sha, detail, recorded_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                conflict.event_id,
                conflict.source_digest,
                conflict.existing_sha,
                conflict.incoming_sha,
                conflict.detail,
                now_utc_iso(),
            ),
        )

    def commit(self) -> None:
        self._conn.commit()

    def rollback(self) -> None:
        self._conn.rollback()

    def provenance_for(self, event_id: str) -> list[str]:
        """Return the sorted distinct source digests recorded for *event_id*."""
        rows = self._conn.execute(
            "SELECT DISTINCT source_digest FROM migration_provenance "
            "WHERE event_id = ? ORDER BY source_digest",
            (event_id,),
        ).fetchall()
        return [str(row["source_digest"]) for row in rows]

    def target_for(self, event_id: str) -> str | None:
        """Return the attached target handle for *event_id*, or ``None``."""
        row = self._conn.execute(
            "SELECT target_id FROM migration_provenance WHERE event_id = ? LIMIT 1",
            (event_id,),
        ).fetchone()
        return None if row is None else str(row["target_id"])

    def conflicts(self) -> list[MigrationConflict]:
        """Return every recorded migration conflict (ordered for reproducibility)."""
        rows = self._conn.execute(
            "SELECT event_id, source_digest, existing_sha, incoming_sha, detail "
            "FROM migration_conflicts ORDER BY event_id, source_digest"
        ).fetchall()
        return [
            MigrationConflict(
                event_id=str(row["event_id"]),
                source_digest=str(row["source_digest"]),
                existing_sha=str(row["existing_sha"]),
                incoming_sha=str(row["incoming_sha"]),
                detail=None if row["detail"] is None else str(row["detail"]),
            )
            for row in rows
        ]

    def has_conflicts(self) -> bool:
        row = self._conn.execute("SELECT 1 FROM migration_conflicts LIMIT 1").fetchone()
        return row is not None


# --- per-source outcomes + overall result ---------------------------------


@dataclass
class SourceOutcome:
    """Per-source migration status so a re-run can report 'nothing to do'."""

    digest: str
    is_legacy: bool
    imported: int = 0
    deduped: int = 0
    conflicts: int = 0
    error: str | None = None


@dataclass
class MigrationResult:
    """Observable outcome of one migration run (NFR-001 assertions key off this).

    ``exit_code``/``blocked`` are non-zero/True iff any divergent-duplicate
    conflict exists or any source DB could not be read/imported. Cleanup is
    blocked until an operator resolves the conflict or source error.
    """

    imported_event_ids: list[str] = field(default_factory=list)
    deduped: list[str] = field(default_factory=list)
    unknown_event_ids: list[str] = field(default_factory=list)
    conflicts: list[MigrationConflict] = field(default_factory=list)
    sources: list[SourceOutcome] = field(default_factory=list)
    note: str = MIGRATION_NOTE

    @property
    def cleanup_blocked(self) -> bool:
        return bool(self.conflicts) or any(source.error for source in self.sources)

    @property
    def blocked(self) -> bool:
        return self.cleanup_blocked

    @property
    def exit_code(self) -> int:
        return 1 if self.cleanup_blocked else 0


# --- canonical payload + source row reading -------------------------------


@dataclass(frozen=True)
class _QueuedRow:
    event_id: str
    event_type: str
    data: str
    timestamp: int | None
    coalesce_key: str | None


def _canonical_payload(data: str) -> bytes:
    """Canonicalize a queued ``data`` blob deterministically for dedupe/compare.

    Stable JSON serialization (sorted keys, compact separators) so two byte-level
    encodings of the *same* event do not count as divergence (contract §5 rule 5).
    Non-JSON data falls back to its raw UTF-8 bytes.
    """
    try:
        parsed = json.loads(data)
    except (TypeError, ValueError):
        return data.encode("utf-8")
    return json.dumps(parsed, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _payload_sha(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()  # noqa: TID251 - migration payload digest, not the charter freshness hash


def _table_exists(conn: sqlite3.Connection, table: str) -> bool:
    cur = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name = ?", (table,)
    )
    return cur.fetchone() is not None


def _read_queued_rows(path: Path) -> list[_QueuedRow]:
    """Read currently-queued rows from a source DB **read-only** (T058 safety).

    Opening with ``mode=ro`` guarantees the source is structurally untouched. A
    source lacking the ``queue`` table (e.g. a body-upload-only legacy DB) yields
    no events rather than an error.
    """
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        if not _table_exists(conn, "queue"):
            return []
        columns = {str(row[1]) for row in conn.execute("PRAGMA table_info(queue)")}
        has_coalesce = "coalesce_key" in columns
        projection = "event_id, event_type, data, timestamp" + (
            ", coalesce_key" if has_coalesce else ""
        )
        rows = conn.execute(
            f"SELECT {projection} FROM queue ORDER BY timestamp ASC, id ASC"  # noqa: S608  # nosec B608 - projection is built from a fixed allowlist, not user input
        ).fetchall()
    finally:
        conn.close()
    return [_row_to_queued(row, has_coalesce) for row in rows]


def _row_to_queued(row: tuple[Any, ...], has_coalesce: bool) -> _QueuedRow:
    timestamp = row[3]
    return _QueuedRow(
        event_id=str(row[0]),
        event_type=str(row[1]),
        data=str(row[2]),
        timestamp=int(timestamp) if timestamp is not None else None,
        coalesce_key=str(row[4]) if has_coalesce and row[4] is not None else None,
    )


def _build_event(row: _QueuedRow, payload: bytes) -> Event:
    """Build a journal :class:`Event`, carrying ``event_id`` verbatim (C-005)."""
    when = (
        datetime.fromtimestamp(row.timestamp, tz=UTC).isoformat()
        if row.timestamp is not None
        else now_utc_iso()
    )
    return Event(
        event_id=row.event_id,
        event_type=row.event_type,
        payload=payload,
        occurred_at=when,
        created_at=when,
        coalesce_key=row.coalesce_key,
    )


# --- target attachment (T057) ---------------------------------------------


def _resolved_digest(resolved_target: ResolvedSyncTarget | None) -> str | None:
    """Return the digest carried by the resolved target's derived queue path."""
    if resolved_target is None:
        return None
    return _parse_digest(resolved_target.queue_db_path.name)


def _target_for_source(source: SourceDb, resolved_digest: str | None) -> tuple[str, bool]:
    """Resolve the (target_handle, is_known) pair for *source* (T057).

    A digest matching the resolved target's derived queue path attaches
    best-effort to that known target handle; every other digest (and the legacy
    ``queue.db``) attaches to an explicit ``unknown`` handle keyed by the source
    digest — **never** a fabricated URL/team identity from a one-way hash.
    """
    if resolved_digest is not None and not source.is_legacy and source.digest == resolved_digest:
        return f"{KNOWN_PREFIX}{migration_target_token(source.digest)}", True
    return f"{UNKNOWN_PREFIX}{migration_target_token(source.digest)}", False


# --- the import (T058–T061) -----------------------------------------------


@dataclass
class _RowImport:
    """The classified outcome of importing one queued row."""

    action: str  # "imported" | "deduped" | "conflict"
    event_id: str
    conflict: MigrationConflict | None = None


@dataclass
class _SourceStaging:
    """In-memory result deltas for one source, merged only after a clean commit.

    The journal batch + provenance are committed all-or-nothing per source, so
    the observable :class:`MigrationResult`/`SourceOutcome` counters must follow
    the same fate: they are accumulated here during the source loop and folded
    into the shared result *only* once both stores have committed. On any
    rollback they are simply discarded, so a half-applied source never leaks
    imported/deduped/conflict counts for rows whose journal+provenance writes
    were rolled back.
    """

    imported: list[str] = field(default_factory=list)
    deduped: list[str] = field(default_factory=list)
    unknown: list[str] = field(default_factory=list)
    conflicts: list[MigrationConflict] = field(default_factory=list)

    def merge_into(self, result: MigrationResult, outcome: SourceOutcome) -> None:
        result.imported_event_ids.extend(self.imported)
        result.deduped.extend(self.deduped)
        result.unknown_event_ids.extend(self.unknown)
        result.conflicts.extend(self.conflicts)
        outcome.imported += len(self.imported)
        outcome.deduped += len(self.deduped)
        outcome.conflicts += len(self.conflicts)


def _classify_and_apply(
    row: _QueuedRow, txn: JournalTransaction, source_digest: str
) -> _RowImport:
    """Append/dedupe/quarantine one row against the staged journal batch.

    * unseen ``event_id`` → stage the canonical payload (``imported``);
    * identical canonical payload → no second row (``deduped``);
    * divergent canonical payload → never overwrite; emit a conflict so the
      existing journal payload stays immutable (FR-018, C-005).

    The append is *staged* on *txn* (not committed); the source loop commits the
    whole batch alongside provenance, so a later provenance failure rolls the
    staged row back rather than orphaning it (atomicity).
    """
    payload = _canonical_payload(row.data)
    existing = txn.read_by_id(row.event_id)
    if existing is None:
        txn.append(_build_event(row, payload))
        return _RowImport(action="imported", event_id=row.event_id)
    if existing.payload == payload:
        return _RowImport(action="deduped", event_id=row.event_id)
    conflict = MigrationConflict(
        event_id=row.event_id,
        source_digest=source_digest,
        existing_sha=_payload_sha(existing.payload),
        incoming_sha=_payload_sha(payload),
        detail="divergent canonical payload for an existing event_id",
    )
    return _RowImport(action="conflict", event_id=row.event_id, conflict=conflict)


def _import_source(
    source: SourceDb,
    *,
    journal: EventJournal,
    audit: MigrationAudit,
    target_id: str,
    result: MigrationResult,
    is_known: bool,
) -> SourceOutcome:
    """Migrate one source DB **atomically** (T058); collect per-row outcomes.

    The journal rows and their provenance are written as one all-or-nothing unit
    per source: every append is *staged* on a deferred journal transaction and
    every provenance/conflict row is staged on the audit store, then **both** are
    committed only after the whole source loop succeeds. On any
    :class:`sqlite3.Error` (e.g. a provenance write failing) **both** are rolled
    back — the staged journal batch is dropped and ``audit.rollback()`` discards
    the provenance — so a provenance failure can never leave an orphan committed
    journal row with no matching provenance (atomicity guarantee).

    Provenance is committed *before* the journal batch so that a committed
    journal row always implies its provenance is already durable. Both writes are
    idempotent (journal ``INSERT OR IGNORE`` on ``event_id``; audit keyed on
    ``(event_id, source_digest)``), so an interrupted source re-runs cleanly with
    no duplication (NFR-005). The source DB is opened read-only and is untouched.
    """
    outcome = SourceOutcome(digest=source.digest, is_legacy=source.is_legacy)
    try:
        rows = _read_queued_rows(source.path)
    except sqlite3.Error as exc:  # locked/corrupt source — report, do not abort run
        outcome.error = str(exc)
        return outcome
    staging = _SourceStaging()
    with journal.transaction() as txn:
        try:
            for row in rows:
                _apply_row(row, source, txn, audit, target_id, staging, is_known)
            audit.commit()  # provenance durable first …
            txn.commit()  # … then the journal batch (no orphan journal row)
        except sqlite3.Error as exc:  # roll BOTH back: drop staged journal + provenance
            txn.rollback()
            audit.rollback()
            outcome.error = str(exc)
            return outcome  # discard staging — nothing was committed for this source
    staging.merge_into(result, outcome)
    return outcome


def _apply_row(
    row: _QueuedRow,
    source: SourceDb,
    txn: JournalTransaction,
    audit: MigrationAudit,
    target_id: str,
    staging: _SourceStaging,
    is_known: bool,
) -> None:
    """Stage one classified row onto the journal batch/audit + buffer result deltas.

    Result deltas are buffered in *staging* (not the shared result) so they are
    only published once the source's journal+provenance commit succeeds.
    """
    imported = _classify_and_apply(row, txn, source.digest)
    if imported.conflict is not None:
        audit.record_conflict(imported.conflict)
        staging.conflicts.append(imported.conflict)
        return
    audit.record_provenance(
        event_id=imported.event_id,
        source_digest=source.digest,
        target_id=target_id,
        payload_sha=_payload_sha(_canonical_payload(row.data)),
    )
    if imported.action == "imported":
        staging.imported.append(imported.event_id)
    else:  # deduped
        staging.deduped.append(imported.event_id)
    if not is_known:
        staging.unknown.append(imported.event_id)


def migrate_queues_to_journal(
    spec_kitty_dir: Path,
    *,
    journal: EventJournal,
    audit: MigrationAudit | None = None,
    resolved_target: ResolvedSyncTarget | None = None,
) -> MigrationResult:
    """Migrate all discovered queue DBs into *journal* (IC-07; contract §5).

    Discovers every scoped ``queue-<digest>.db`` plus the legacy ``queue.db``,
    attaches each source's events to a best-effort *known* target (digest match
    against *resolved_target*) or an explicit ``unknown`` provenance, dedupes
    identical duplicates while accumulating all source provenance, and quarantines
    divergent duplicates into migration-conflict rows. Source DBs are read-only,
    so they are never modified; only currently-queued payloads survive.

    Returns a :class:`MigrationResult` whose ``exit_code``/``blocked`` are
    non-zero/True while any conflict is unresolved (cleanup is blocked).
    """
    owns_audit = audit is None
    store = audit or MigrationAudit(spec_kitty_dir / AUDIT_DB_NAME)
    result = MigrationResult()
    try:
        resolved_digest = _resolved_digest(resolved_target)
        for source in discover_source_dbs(spec_kitty_dir):
            target_id, is_known = _target_for_source(source, resolved_digest)
            outcome = _import_source(
                source,
                journal=journal,
                audit=store,
                target_id=target_id,
                result=result,
                is_known=is_known,
            )
            result.sources.append(outcome)
    finally:
        if owns_audit:
            with contextlib.suppress(sqlite3.Error):
                store.close()
    return result


__all__ = [
    "AUDIT_DB_NAME",
    "KNOWN_PREFIX",
    "LEGACY_DIGEST",
    "MIGRATION_NOTE",
    "MigrationAudit",
    "MigrationConflict",
    "MigrationResult",
    "SourceDb",
    "SourceOutcome",
    "UNKNOWN_PREFIX",
    "discover_source_dbs",
    "migrate_queues_to_journal",
    "migration_target_token",
]
