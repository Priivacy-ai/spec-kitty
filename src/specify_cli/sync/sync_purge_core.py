"""Pure census differentials + verdict logic for ``spec-kitty sync purge`` (WP06).

`sync purge` — the operator's remediation path (#3030 WP08 / T022).
FR-016 / FR-017 / NFR-006 / C-002. ``sync gc`` only reclaims payloads already
delivered to every known target, so it cannot clear the retained rows the
2026-07-27 incident left on disk. The ``purge`` command is the only path that can,
and it composes the four stores' purge primitives rather than re-deriving any of
them: ``delivery/retention.py`` owns the journal, the delivery ledger and the
body-upload queue; ``sync/local_commit.py`` owns the per-checkout
``pending_local_commits`` queue. Selection and deletion stay there (C-003).

The Wave-4 ``sync.py`` de-god (mission ``sync-cli-degod-wave4-01M0B0MX``, WP06)
splits the purge subsystem's operator surface into two cohesive seam modules:

* **this module** — the **pure** half: the raw-census data shape, the store
  outcome shape, and every differential / verdict function. It is provably
  **I/O-free** (no ``Console``, no ``print``, no filesystem, no SQLite): every
  function takes already-read censuses and returns a value or a dataclass, so the
  arithmetic that decides whether NFR-006 held can be unit-tested directly (plan
  IC-04). The census **readers** and store **executors** that touch the
  journal / ledger / body queue live in the sibling
  :mod:`specify_cli.sync.sync_purge_exec`, which imports the shared shapes and
  constants **from here**.

This is a **pure move** (INV-1): every function body is byte-identical to the
inline form it replaced in ``cli/commands/sync.py``. The WP02 golden and the
``tests/cli/commands/test_sync_purge_3030.py`` suite are the guard; the
new-code coverage is in ``tests/sync/test_sync_purge_core.py``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from uuid import UUID



#: Census key for a ``NULL`` project identity. Deliberately distinct from ``""``:
#: a NULL row and a non-NULL blank row are different populations reachable by
#: different selectors, and a census that folded them together is exactly what
#: made an NFR-006 differential vacuous earlier in this mission (a population
#: counted in no bucket has a differential of zero by construction).
_PURGE_NULL_KEY = "<null>"

_PURGE_JOURNAL = "event_journal"
_PURGE_LEDGER = "delivery_ledger"
_PURGE_BODY = "body_upload_queue"
_PURGE_FRAMES = "local_commit_frames"

_PURGE_STORE_LABELS = {
    _PURGE_JOURNAL: "event journal",
    _PURGE_LEDGER: "delivery ledger",
    _PURGE_BODY: "body-upload queue",
    # The scope is part of the name because it is not the same as the other three.
    _PURGE_FRAMES: "local-commit frames (this checkout only)",
}

#: Where a checkout keeps its queued ``LocalCommit`` frames. Duplicated from
#: ``sync/local_commit.py``'s private ``_sync_state_path`` on the same reasoning
#: ``delivery/retention.py`` records for ``_DELIVERY_SUBDIR``: this module needs the
#: path to *report* it and to read it independently, and reaching into another
#: module's private helper is the worse coupling. ``tests/cli/commands/
#: test_sync_purge_3030.py`` asserts the two agree, so a relocation is a red rather
#: than a purge report pointed at a file nobody writes.
_PURGE_SYNC_STATE_RELPATH = Path(".kittify") / "sync-state.json"

#: How `--all` is described, in one place, because the wording is an authority
#: decision rather than a flourish. Project-owned payloads live in the active
#: checkout's routed ``ProjectSyncStore``; ``pending_local_commits`` is likewise
#: per-checkout ``LOCAL_RUNTIME`` state. The command must never imply that it scans
#: or erases another project's physical store.
_PURGE_ALL_SCOPE_NOTE = (
    "Scope of --all: the active project's event journal, delivery ledger and "
    "body-upload queue, plus THIS CHECKOUT's queued local-commit frames "
    "({frames_path}). No other project store or checkout is opened or scanned. "
    "Re-run this command from each checkout whose active project you need cleared."
)

#: Printed on every destructive run. Journal, ledger and body changes share one
#: project-store transaction. The checkout-local frame file is a separate durable
#: boundary, so interruption can still require a convergent re-run.
_PURGE_NON_ATOMIC_NOTE = (
    "The active project's journal, ledger and body queue are deleted in one local "
    "database transaction. Checkout-local frames are a separate file boundary; if "
    "a run is interrupted, re-run the same command — it converges."
)


@dataclass(frozen=True)
class _RawCensus:
    """One store's row counts, grouped by the raw identity value it stores.

    Taken by the CLI itself and **not** through the domain censuses the purge
    primitives report from (NFR-006). Two properties matter:

    * **Total-preserving by construction.** Every row lands in exactly one bucket
      and ``NULL`` / ``""`` / ``"   "`` are three distinct buckets, so no population
      can be missing from both the before and after picture — the shape that let a
      purge move rows and still report "0% of any other project's" truthfully by its
      own arithmetic.
    * **Independent of the purge's own reads.** The differential below is measured
      from two of these snapshots, so it can disagree with what the primitive claims
      to have deleted. A check whose operands both come from the thing under test
      was already rejected on this mission, having produced zero failures over 200
      randomized cases.
    """

    total: int = 0
    by_key: dict[str, int] = field(default_factory=dict)
    unreadable: bool = False

    def count(self, keys: frozenset[str]) -> int:
        return sum(self.by_key.get(key, 0) for key in keys)

    @property
    def unbucketed(self) -> int:
        """Rows the grouping could not account for. Must be ``0``; reported if not."""
        return self.total - sum(self.by_key.values())


@dataclass
class _PurgeStoreOutcome:
    """What one store contributed to the purge, as measured rather than as claimed."""

    store: str
    location: str
    in_scope: int = 0
    removed_observed: int = 0
    removed_reported: int | None = None
    others_delta_observed: int = 0
    total_after: int = 0
    left_behind: dict[str, int] = field(default_factory=dict)
    states: dict[str, int] = field(default_factory=dict)
    never_attempted: int = 0
    unreadable: bool = False
    note: str = ""

    def as_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "location": self.location,
            "in_scope": self.in_scope,
            "removed_observed": self.removed_observed,
            "removed_reported": self.removed_reported,
            "others_delta_observed": self.others_delta_observed,
            "total_after": self.total_after,
            "left_behind": dict(self.left_behind),
            "unreadable": self.unreadable,
        }
        if self.store == _PURGE_LEDGER:
            data["states"] = dict(self.states)
            data["never_attempted"] = self.never_attempted
        if self.note:
            data["note"] = self.note
        return data



def _purge_unattributable_keys(census: _RawCensus) -> frozenset[str]:
    """Census keys that name no project: ``NULL``, ``""``, and whitespace-only."""
    return frozenset(key for key in census.by_key if key == _PURGE_NULL_KEY or not key.strip())


def _purge_left_behind(census: _RawCensus) -> dict[str, int]:
    """The unattributable residue of one store, as two named counts."""
    null_rows = census.by_key.get(_PURGE_NULL_KEY, 0)
    blank_rows = sum(count for key, count in census.by_key.items() if key != _PURGE_NULL_KEY and not key.strip())
    residue: dict[str, int] = {}
    if null_rows:
        residue["identity_null"] = null_rows
    if blank_rows:
        residue["identity_blank"] = blank_rows
    return residue


def _purge_differential(before: _RawCensus, after: _RawCensus, scope: frozenset[str]) -> tuple[int, int]:
    """``(rows removed inside scope, absolute change outside it)``, both measured.

    Absolute and over the union of both censuses, so a key that *appeared* counts as
    a change too: a purge must neither remove nor create another project's rows, and
    a concurrent writer is exactly as much of a finding as an over-reaching selector.
    """
    removed = before.count(scope) - after.count(scope)
    keys = (set(before.by_key) | set(after.by_key)) - scope
    others = sum(abs(after.by_key.get(key, 0) - before.by_key.get(key, 0)) for key in keys)
    return removed, others


def _purge_ledger_differential(before: _RawCensus, after: _RawCensus) -> tuple[int, int]:
    """The ledger's ``(removed, changed outside the selection)``, derived not grouped.

    The ledger is keyed ``(event_id, target_id)`` and carries no project column, so
    "another project's ledger rows" cannot be grouped for. It *is* exactly derivable:
    total change minus the change the selection accounts for. Both operands come from
    the CLI's own two reads, so the answer can disagree with what the purge reported —
    which is the whole point of measuring it here (NFR-006).
    """
    removed = before.by_key.get(_PURGE_LEDGER, 0) - after.by_key.get(_PURGE_LEDGER, 0)
    return removed, abs((before.total - after.total) - removed)


def _purge_stored_spelling_conflicts(selector: str, censuses: list[_RawCensus]) -> list[str]:
    """Stored keys that mean the same project as *selector* but are spelled differently.

    A real cross-store hazard rather than pedantry: the journal matches a
    ``project_uuid`` by exact string equality, while the frame purge compares
    case-insensitively. So an upper-cased or dash-less selector would clear a
    checkout's frames while leaving every journal row in place, and report "0 journal
    rows in scope" — indistinguishable from a project that was already clean.
    """
    try:
        wanted: UUID | None = UUID(selector)
    except (ValueError, AttributeError, TypeError):
        wanted = None
    conflicts: set[str] = set()
    for census in censuses:
        for key in census.by_key:
            if key in (selector, _PURGE_NULL_KEY) or not key.strip():
                continue
            same = key.strip().casefold() == selector.strip().casefold()
            if not same and wanted is not None:
                try:
                    same = UUID(key.strip()) == wanted
                except (ValueError, AttributeError, TypeError):
                    same = False
            if same:
                conflicts.add(key)
    return sorted(conflicts)



def _purge_ledger_view(census: _RawCensus, *, all_events: bool) -> _RawCensus:
    """The ledger census as the selector sees it.

    ``--all`` covers the ledger's own rows — including the ghosts whose journal row
    ``sync gc`` already removed, which no journal-derived id list can name — so the
    selected count is the whole table.
    """
    if not all_events:
        return census
    return _RawCensus(
        total=census.total,
        by_key={_PURGE_LEDGER: census.total},
        unreadable=census.unreadable,
    )



def _purge_frames_scope(census: _RawCensus, frames_result: Any | None, *, all_events: bool, selector_uuid: str) -> frozenset[str]:
    """The frame-census keys this run claims, as the primitive itself scoped them."""
    if all_events:
        return frozenset(census.by_key)
    if frames_result is None:
        return frozenset()
    if frames_result.unattributed_in_scope:
        # This checkout declares the target as its own project, so its unattributable
        # frames are its own content and are in scope — the pre-fix population the
        # incident actually produced, which carries no `project_uuid` at all.
        return frozenset({selector_uuid}) | _purge_unattributable_keys(census)
    return frozenset({selector_uuid})


def _purge_selector_line(*, project: str | None, identity_less: bool, selector_uuid: str, matched_slug: str | None) -> str:
    if project is not None:
        matched = f' (matched slug "{matched_slug}")' if matched_slug else ""
        return f"Selector: project [bold]{selector_uuid}[/bold]{matched}"
    if identity_less:
        return "Selector: journal rows with no project identity (NULL)"
    return "Selector: [bold]every event[/bold] in the stores named below"



def _purge_outcomes(
    *,
    before: dict[str, _RawCensus],
    after: dict[str, _RawCensus],
    scopes: dict[str, frozenset[str]],
    locations: dict[str, str],
    reported: dict[str, int | None],
    result: Any | None,
    ghosts_before: int,
    identity_less: bool,
    in_checkout: bool,
    frames_census_reported: int,
) -> dict[str, _PurgeStoreOutcome]:
    """Assemble the per-store outcome from the two independent censuses.

    ``removed_reported`` is carried alongside ``removed_observed`` rather than instead
    of it: the report shows what the purge said *and* what the stores show, so a
    disagreement is visible instead of averaged away.
    """
    outcomes: dict[str, _PurgeStoreOutcome] = {}
    for store in (_PURGE_JOURNAL, _PURGE_LEDGER, _PURGE_BODY, _PURGE_FRAMES):
        if store == _PURGE_LEDGER:
            removed, others = _purge_ledger_differential(before[store], after[store])
        else:
            removed, others = _purge_differential(before[store], after[store], scopes[store])
        outcomes[store] = _PurgeStoreOutcome(
            store=store,
            location=locations[store],
            in_scope=before[store].count(scopes[store]),
            removed_observed=removed,
            removed_reported=reported[store],
            others_delta_observed=others,
            total_after=after[store].total,
            left_behind=_purge_left_behind(after[store]),
            unreadable=before[store].unreadable or after[store].unreadable,
        )

    ledger = outcomes[_PURGE_LEDGER]
    ledger.left_behind = {"without_journal_row": ghosts_before} if ghosts_before else {}
    if result is not None:
        ledger.states = {str(name): int(count) for name, count in result.ledger_status_before.items()}
        ledger.never_attempted = result.never_attempted

    if identity_less:
        note = "not spanned by --identity-less: unattributable rows here cannot be attributed to any project, and only --all reaches them"
        outcomes[_PURGE_BODY].note = note
        outcomes[_PURGE_FRAMES].note = note
    if not in_checkout:
        outcomes[_PURGE_FRAMES].note = "no checkout resolved from the current directory, so no local-commit queue was inspected — re-run from inside the checkout"
    elif before[_PURGE_FRAMES].unreadable:
        outcomes[_PURGE_FRAMES].note = (
            f"the purge's own census reads {frames_census_reported} queued frame(s) from "
            "a file this command could not parse, so that number is not evidence of "
            "what the file holds — repair or remove the file and re-run"
        )
    return outcomes


def _purge_not_reached(
    *,
    after: dict[str, _RawCensus],
    journal_scope: frozenset[str],
    frames_scope: frozenset[str],
    body_scope: frozenset[str],
    ghosts_before: int,
    all_events: bool,
) -> list[dict[str, Any]]:
    """Name every population this run leaves behind, with its count and its selector.

    A residue nobody names is the same defect as a report that overstates. All five
    are real rather than hypothetical: the NULL-identity rows the backfill must not
    delete (C-002), the non-NULL blank and whitespace-only uuids that are visible in
    the census and reachable by no targeted selector, the ledger rows whose journal row
    ``sync gc`` already removed (so every machine that has run it holds some), the
    body-upload rows no *project* selector reaches, and the pre-fix frames of a
    checkout that vouches for nothing.

    Every population is filtered against the scope this run actually claimed, so a
    row the current selector already covers is not also listed as left behind.
    """
    rows: list[dict[str, Any]] = []

    def add(population: str, description: str, count: int | None, reachable_by: str, text: str) -> None:
        rows.append(
            {
                "population": population,
                "description": description,
                "count": count,
                "reachable_by": reachable_by,
                "reachable_by_text": text,
            }
        )

    journal = after[_PURGE_JOURNAL]
    null_left = journal.by_key.get(_PURGE_NULL_KEY, 0)
    if null_left and _PURGE_NULL_KEY not in journal_scope:
        add(
            "journal_identity_null",
            "journal rows with a NULL project identity",
            null_left,
            "--identity-less",
            "permanently undeliverable and matchable by no project; run `sync purge --identity-less`",
        )
    blank_left = sum(count for key, count in journal.by_key.items() if key != _PURGE_NULL_KEY and not key.strip() and key not in journal_scope)
    if blank_left:
        add(
            "journal_identity_blank",
            "journal rows whose project_uuid is blank or whitespace-only",
            blank_left,
            "--all",
            "visible in the census and selectable by nothing else: a project purge "
            "blanks a falsy selector and the identity-less selector is NULL-only, so "
            "only `sync purge --all` reaches them",
        )
    if ghosts_before:
        add(
            "ledger_without_journal_row",
            "delivery-ledger rows whose journal row is already gone",
            ghosts_before,
            "--all",
            "every targeted selection collects its ids from the journal, and `sync gc` removes journal rows while preserving ledger history by design",
        )
    body_blank = sum(count for key, count in after[_PURGE_BODY].by_key.items() if (not key or key != key.strip()) and key not in body_scope)
    if body_blank:
        add(
            "body_uploads_identity_blank",
            "queued document bodies whose project_uuid is blank or padded",
            body_blank,
            "--all",
            "the queue's per-project removal strips its argument and refuses a falsy "
            "one, so no --project value reaches these rows; `sync purge --all` clears "
            "the store outright and is the only selector that does",
        )
    frames_unattributed = sum(
        count for key, count in after[_PURGE_FRAMES].by_key.items() if (key == _PURGE_NULL_KEY or not key.strip()) and key not in frames_scope
    )
    if frames_unattributed:
        add(
            "local_commit_frames_unattributed",
            "queued local-commit frames carrying no project_uuid",
            frames_unattributed,
            "--all",
            "this checkout does not declare the purged project as its own, so it vouches for nothing; `sync purge --all` run from the owning checkout reaches them",
        )
    if all_events:
        add(
            "local_commit_frames_other_checkouts",
            "other checkouts' queued local-commit frames",
            None,
            "run this command from each checkout",
            "per-checkout state with no registry to enumerate it — deliberately not "
            "counted, because a count that cannot be proven complete would be worse "
            "than none",
        )
    return rows


def _purge_faults(
    *,
    outcomes: dict[str, _PurgeStoreOutcome],
    before: dict[str, _RawCensus],
    after: dict[str, _RawCensus],
    apply: bool,
    others_total: int,
    frames_census_reported: int,
    frames_census_disagrees: bool,
) -> list[str]:
    """Everything the measurements say went wrong. Empty means NFR-006 held.

    Each entry is a disagreement between two independently obtained numbers, never a
    restatement of one of them: the stores' own before/after against what the purge
    reported, and the purge's census of the frame file against the file itself.
    """
    faults: list[str] = []
    if frames_census_disagrees:
        faults.append(
            f"{_PURGE_STORE_LABELS[_PURGE_FRAMES]}: the purge's census reads "
            f"{frames_census_reported} queued frame(s) where the file holds "
            f"{before[_PURGE_FRAMES].total} — the purge is not acting on the file's "
            "actual contents."
        )
    if apply:
        faults.extend(
            f"{_PURGE_STORE_LABELS[store]}: unreadable, so a destructive run cannot claim to have cleared it."
            for store, outcome in outcomes.items()
            if outcome.unreadable
        )
    if others_total:
        faults.append(
            f"{others_total} row(s) outside the selection changed. Either the purge "
            "over-reached or another writer (a running sync daemon, a concurrent "
            "capture) touched a store during the run — stop the daemon and re-measure "
            "before trusting this report."
        )
    for store, outcome in outcomes.items():
        expected = outcome.in_scope if apply else 0
        if outcome.removed_observed != expected:
            faults.append(f"{_PURGE_STORE_LABELS[store]}: expected {expected} row(s) to go, measured {outcome.removed_observed}.")
        # The journal's reported count is not comparable under `--all`: that selection
        # deliberately includes ledger-only ids that were never journal rows.
        if apply and store != _PURGE_JOURNAL and outcome.removed_reported is not None and outcome.removed_reported != outcome.removed_observed:
            faults.append(f"{_PURGE_STORE_LABELS[store]}: the purge reported {outcome.removed_reported} removed, the store shows {outcome.removed_observed}.")
        # The ledger census is deliberately partial — one synthetic bucket for the
        # selection, because the store has no project column to group by — so its
        # totality is enforced by `_purge_ledger_differential`'s derivation instead.
        if store != _PURGE_LEDGER and (before[store].unbucketed or after[store].unbucketed):
            faults.append(
                f"{_PURGE_STORE_LABELS[store]}: rows exist that the per-project census cannot account for, so this store's differential is not trustworthy."
            )
    return faults
