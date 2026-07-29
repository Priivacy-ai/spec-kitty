"""Project identity: the ProjectIdentity re-export shim plus the canonical
event-identity resolution chain (#3030 T011).

The canonical home for ProjectIdentity is specify_cli.identity.project; this
module re-exports all public names for backward compatibility.

It is also the **single definition site** for resolving a project identity out of
an event envelope. Three consumers need the *identical* chain and NFR-001 demands
they agree: FR-004's pre-POST refusal (in ``delivery/``), FR-009's backfill, and
FR-013's consent writer (in ``sync/``). The original implementation was private to
``sync/queue.py``, which ``delivery/dispatcher.py`` may not import, and
``event_journal`` may not import ``delivery`` — with no named home each work
package would copy the chain and they would silently diverge. This module is that
home; ``delivery/targets.py`` already precedents importing from
``specify_cli.sync.*``.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from specify_cli.identity.project import (  # noqa: F401
    ProjectIdentity,
    atomic_write_config,
    derive_project_slug,
    ensure_identity,
    generate_build_id,
    generate_node_id,
    generate_project_uuid,
    is_writable,
    load_identity,
)

# ``ensure_identity`` remains importable for explicit legacy callers of this shim,
# but is intentionally omitted from ``__all__`` so wildcard imports do not promote
# a write-boundary helper as part of the trimmed public surface.
__all__ = [
    "IdentityBackfillResult",
    "NIL_PROJECT_UUID",
    "PROJECT_SLUG_RESOLUTION_CHAIN",
    "PROJECT_UUID_RESOLUTION_CHAIN",
    "ProjectIdentity",
    "atomic_write_config",
    "derive_project_slug",
    "generate_build_id",
    "generate_node_id",
    "generate_project_uuid",
    "is_writable",
    "load_identity",
    "backfill_journal_identity",
    "count_unresolved_identity",
    "resolve_event_project_slug",
    "resolve_event_project_uuid",
]


# --- canonical event-identity resolution (#3030 T011) ---------------------

#: Substituted for a missing uuid at ``sync/emitter.py:2150``. It is a
#: placeholder, never a real project, so it normalizes to ``None`` at both write
#: and backfill — otherwise it would become a groupable, consentable value that
#: silently pools unrelated projects under one key.
NIL_PROJECT_UUID = "00000000-0000-0000-0000-000000000000"

#: Ordered dotted paths tried in turn, each resolved against the event envelope
#: **then** its payload. Those two lookups per path are what make three entries
#: cover the four known writer sites:
#:
#: 1. ``namespace.project_uuid`` — the namespace block
#: 2. ``project_uuid`` on the envelope — ``emitter.py:2037``
#: 3. ``project_uuid`` on the payload — same path, payload fallback
#: 4. ``subject.project_uuid`` — ``_enrich_proof_subject`` (``emitter.py:1689``),
#:    which the pre-#3030 chain never inspected
#:
#: Order is load-bearing: ``envelope_fields`` can overwrite the top-level value
#: (``emitter.py:2048-2049``), so the namespace block is consulted first.
PROJECT_UUID_RESOLUTION_CHAIN: tuple[str, ...] = (
    "namespace.project_uuid",
    "project_uuid",
    "subject.project_uuid",
)

#: The slug counterpart. Slug is a convenience projection for reporting only —
#: never an authorization key, since slugs are derived and can collide.
PROJECT_SLUG_RESOLUTION_CHAIN: tuple[str, ...] = (
    "namespace.project_slug",
    "project_slug",
    "subject.project_slug",
)


def _resolve_dotted_path(source: Any, path: str) -> Any:
    """Walk a dotted *path* through nested mappings, or return ``None``."""
    current = source
    for part in path.split("."):
        if not isinstance(current, dict):
            return None
        current = current.get(part)
        if current is None:
            return None
    return current


def _normalize(value: Any) -> str | None:
    """Coerce a resolved value to a usable identity string, or ``None``.

    Empty strings and the nil sentinel are *absence*, not values.
    """
    if value is None:
        return None
    text = str(value).strip()
    if not text or text == NIL_PROJECT_UUID:
        return None
    return text


def _resolve_chain(
    event: dict[str, Any] | None,
    payload: dict[str, Any] | None,
    chain: tuple[str, ...],
) -> str | None:
    """Try each path in *chain* against the envelope, then the payload."""
    envelope = event if isinstance(event, dict) else {}
    body = payload if isinstance(payload, dict) else envelope.get("payload")
    body = body if isinstance(body, dict) else {}

    for path in chain:
        for source in (envelope, body):
            normalized = _normalize(_resolve_dotted_path(source, path))
            if normalized is not None:
                return normalized
    return None


def resolve_event_project_uuid(
    event: dict[str, Any] | None,
    payload: dict[str, Any] | None = None,
) -> str | None:
    """Return the event's ``project_uuid``, or ``None`` if unresolvable.

    ``None`` means *not consentable*: the caller must treat it as denied, never
    as a wildcard. ``payload`` defaults to ``event["payload"]``.
    """
    return _resolve_chain(event, payload, PROJECT_UUID_RESOLUTION_CHAIN)


def resolve_event_project_slug(
    event: dict[str, Any] | None,
    payload: dict[str, Any] | None = None,
) -> str | None:
    """Return the event's ``project_slug``, or ``None``. Reporting only."""
    return _resolve_chain(event, payload, PROJECT_SLUG_RESOLUTION_CHAIN)


# --- journal identity backfill (#3030 T012/T013) --------------------------


@dataclass(frozen=True)
class IdentityBackfillResult:
    """Outcome of one backfill pass over a journal."""

    #: Rows whose identity columns were filled in by this run.
    updated: int
    #: Rows still carrying no resolvable identity after this run. They stay in
    #: the journal (C-002) and are permanently unselectable, so FR-011 requires
    #: them counted rather than silently dropped.
    unresolved: int


def backfill_journal_identity(journal: Any) -> IdentityBackfillResult:
    """Project stored payload identity into the journal's identity columns.

    Lives in ``sync`` rather than ``event_journal`` on purpose: the journal is
    storage and must stay ignorant of consent policy (C-003), while the
    resolution chain is identity policy. ``sync`` already imports
    ``event_journal``, so this direction adds no new coupling — the reverse would
    have needed a charter note.

    Idempotent and lossless (NFR-004/SC-007): only rows with a NULL
    ``project_uuid`` are considered, the write never overwrites an existing
    value, and nothing outside the two columns is touched. Interruption is safe —
    unwritten rows stay NULL, which reads as *unselectable*, never as consented.

    An unparseable payload resolves to ``None`` rather than raising: a single
    corrupt row must not strand the whole history.
    """
    import json

    pending = journal.iter_rows_missing_identity()
    entries: list[tuple[str, str | None, str | None]] = []
    unresolved = 0

    for event_id, raw_payload in pending:
        envelope: dict[str, Any] | None = None
        try:
            decoded = json.loads(raw_payload) if raw_payload else None
        except (TypeError, ValueError):
            decoded = None
        if isinstance(decoded, dict):
            envelope = decoded

        project_uuid = resolve_event_project_uuid(envelope)
        if project_uuid is None:
            unresolved += 1
            continue
        entries.append((event_id, project_uuid, resolve_event_project_slug(envelope)))

    updated = journal.set_project_identity(entries)
    return IdentityBackfillResult(updated=updated, unresolved=unresolved)


def count_unresolved_identity(journal: Any) -> int:
    """Count journal rows with no stored project identity (FR-011/T013)."""
    return int(journal.count_missing_identity())
