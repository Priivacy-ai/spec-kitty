"""Hidden git merge-driver entrypoints for Spec Kitty repositories.

Six custom drivers keep mission bookkeeping semantic under
``git merge --squash -X theirs`` (the squash mission→target integration in
``lanes/merge.py::_merge_branch_into``). A custom driver overrides ``-X theirs``
on the paths it is registered for, so target-newer canonical state is reconciled
rather than clobbered (#2709 / FR-003 / FR-004 / FR-008):

- ``merge-driver-event-log``         — ``status.events.jsonl`` union (append-only log).
- ``merge-driver-meta``              — ``meta.json`` field merge: acceptance/VCS keys
  target-authoritative (the accepted-newer ``ours`` side), ``acceptance_history``
  unioned, all other (planning) keys mission-authoritative (``theirs``; preserves
  the #1732 ``-X theirs`` planning-artifact authority).
- ``merge-driver-traces``            — ``traces/*.md`` markdown union: order-preserving
  line-level dedup so both sides' sections survive without duplication.
- ``merge-driver-acceptance-matrix`` — ``acceptance-matrix.json`` row-aware,
  base-aware (3-way) merge over ``criteria``/``negative_invariants``, keyed by
  ``criterion_id``/``invariant_id`` (FR-008 / see ``contracts/merge-driver-
  algorithm.md``).
- ``merge-driver-issue-matrix``      — ``issue-matrix.json`` row-aware,
  base-aware (3-way) merge over ``rows``, keyed by canonicalized ``issue_ref``.
- ``merge-driver-review-cycle``      — ``tasks/<wp>/review-cycle-*.md`` refuse-
  fail-closed on a genuine two-verdict collision (review-cycle-verdict-seam-
  rebuild-01KZ2W7W WP18/T077); see that driver's own docstring for why this is
  the ONE driver in this module that never reconciles by unioning/field-
  merging — a review verdict document must never be blended.

Git invokes a driver with ``%O %A %B`` = base / ours / theirs and expects the
merged result written to the ``ours`` (``%A``) path with exit 0. Under the squash
integration ``ours`` is the target checkout (e.g. ``main``) and ``theirs`` is the
mission branch.

**#2970 path-injection hardening (S2083).** Every driver's ``%O``/``%A``/``%B``
argv is externally-supplied (git-computed, but syntactically untrusted input to
this process). Per gitattributes(5) and confirmed empirically, git ALWAYS
materializes the three placeholders as sibling temp files in ONE directory (the
top of the working tree) for a real merge; every driver-unit test in this
codebase constructs them as siblings under one ``tmp_path`` for the same reason.
:func:`_resolve_merge_driver_paths` enforces exactly that invariant — the three
resolved paths must share a parent directory — before any read/write. An
absolute path or a ``..`` escape routing one placeholder outside that shared
directory (the concrete shape of the 5 S2083 BLOCKER findings) is refused
red-first, without narrowing any reconciliation rule below.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

import typer

from specify_cli.acceptance import (
    ACCEPTANCE_HISTORY_FIELD,
    ACCEPTANCE_PROVENANCE_FIELDS,
)
from specify_cli.acceptance.matrix import AcceptanceMatrix
from specify_cli.status import EventLogMergeError, merge_event_log_files
from specify_cli.tasks.issue_matrix import ISSUE_MATRIX_SCHEMA_VERSION

# meta.json serialization identical to ``mission_metadata.write_meta`` so the
# reconciled blob is byte-consistent with the canonical writer (no diff churn).
_META_JSON_KWARGS: dict[str, Any] = {
    "indent": 2,
    "ensure_ascii": False,
    "sort_keys": True,
}

# Target-authoritative ``meta.json`` keys the squash driver takes from the
# accepted-newer target side. Acceptance/VCS provenance (the canonical
# ``ACCEPTANCE_PROVENANCE_FIELDS`` shapes) plus the target-assigned lifecycle /
# merge canonical fields (``mission_number``, ``status``, ``baseline_merge_commit``,
# the ``merged_*`` block): every one is minted on the target at accept/merge time,
# so a squash of the older mission branch must reconcile — not revert — them.
# Every OTHER key (mission planning identity: slug, mission_id, target_branch,
# purpose_*, friendly_name, created_at, coordination_branch, …) stays
# mission-authoritative to preserve the #1732 ``-X theirs`` intent (C-002).
_TARGET_AUTHORITATIVE_META_FIELDS: tuple[str, ...] = (
    *ACCEPTANCE_PROVENANCE_FIELDS,
    "mission_number",
    "status",
    "baseline_merge_commit",
    "merged_at",
    "merged_by",
    "merged_into",
    "merged_strategy",
    "merged_push",
    "merged_commit",
)


# ---------------------------------------------------------------------------
# #2970 (E1) — path-injection hardening shared by every driver entrypoint
# ---------------------------------------------------------------------------


class MergeDriverPathError(Exception):
    """Raised when a driver's ``%O``/``%A``/``%B`` argv escapes git's own
    same-directory temp-file contract (#2970 / Sonar S2083)."""


def _resolve_merge_driver_paths(
    base_path: str, ours_path: str, theirs_path: str
) -> tuple[Path, Path, Path]:
    """Resolve the three driver placeholders, refusing a path-injection escape.

    Git materializes ``%O``/``%A``/``%B`` as three sibling temp files in ONE
    directory for every real invocation (verified empirically against git's
    merge-driver machinery); every driver-unit test in this codebase builds
    them the same way (three files under one ``tmp_path``). Requiring the
    three *resolved* paths to share a parent directory is therefore a
    zero-cost invariant for every legitimate caller, while an absolute path
    (e.g. ``/etc/...``) or a ``..`` traversal aimed at a DIFFERENT directory —
    the concrete shape of the 5 S2083 BLOCKER findings — fails it and is
    refused before any read/write happens.
    """
    resolved = (
        Path(base_path).resolve(),
        Path(ours_path).resolve(),
        Path(theirs_path).resolve(),
    )
    if len({path.parent for path in resolved}) > 1:
        raise MergeDriverPathError(
            "refusing merge-driver invocation: %O/%A/%B do not share a parent "
            f"directory ({[str(path) for path in resolved]!r}) — refused as a "
            "possible path-injection attempt (#2970)"
        )
    return resolved


def _resolve_merge_driver_paths_or_exit(
    base_path: str, ours_path: str, theirs_path: str
) -> tuple[Path, Path, Path]:
    """:func:`_resolve_merge_driver_paths`, translating a refusal to ``Exit(1)``.

    Every driver entrypoint calls this FIRST, before any file is opened — the
    single choke point that closes all 5 S2083 findings in this module.
    """
    try:
        return _resolve_merge_driver_paths(base_path, ours_path, theirs_path)
    except MergeDriverPathError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1) from exc


def merge_driver_event_log(
    base_path: str = typer.Argument(..., metavar="BASE"),
    ours_path: str = typer.Argument(..., metavar="OURS"),
    theirs_path: str = typer.Argument(..., metavar="THEIRS"),
) -> None:
    """Merge ``status.events.jsonl`` conflict inputs using event-log semantics."""
    base, ours, theirs = _resolve_merge_driver_paths_or_exit(base_path, ours_path, theirs_path)
    try:
        merge_event_log_files(
            base_path=base,
            ours_path=ours,
            theirs_path=theirs,
        )
    except EventLogMergeError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1) from exc


# ---------------------------------------------------------------------------
# meta.json field merge (FR-004)
# ---------------------------------------------------------------------------


def _load_json_object(path: Path) -> dict[str, Any]:
    """Load a JSON object from *path*; empty/missing yields ``{}``.

    The missing and blank tolerances are pinned behaviour and are UNCHANGED
    (``tests/merge/test_merge_driver_wrappers_2709.py``). A JSON *syntax* error
    is translated to :class:`EventLogMergeError` naming ``meta.json`` and the
    path, in the same style as the non-object message below, rather than
    letting a bare :class:`json.JSONDecodeError` escape (FR-005). Exit-code
    behaviour is unchanged either way: ``merge_driver_meta``'s handler catches
    BOTH ``json.JSONDecodeError`` and ``EventLogMergeError``, echoes
    ``str(exc)`` to stderr and raises ``typer.Exit(1)``.
    """
    if not path.exists():
        return {}
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return {}
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise EventLogMergeError(
            f"{path}: meta.json could not be decoded ({exc})"
        ) from exc
    if not isinstance(data, dict):
        raise EventLogMergeError(f"{path}: meta.json is not a JSON object")
    return data


def _union_acceptance_history(
    theirs_history: list[dict[str, Any]] | None,
    ours_history: list[dict[str, Any]] | None,
) -> list[dict[str, Any]]:
    """Union two ``acceptance_history`` lists, dedup by content, sort by time.

    Entries have no stable id, so dedup is by canonical-JSON equality. Order is
    deterministic (``accepted_at`` then ``accepted_by``) so the union is idempotent
    under repeat merges (NFR-001 spirit).
    """
    combined: list[dict[str, Any]] = []
    seen: set[str] = set()
    for history in (theirs_history or [], ours_history or []):
        for entry in history:
            key = json.dumps(entry, sort_keys=True)
            if key in seen:
                continue
            seen.add(key)
            combined.append(entry)
    combined.sort(
        key=lambda entry: (
            str(entry.get("accepted_at", "")),
            str(entry.get("accepted_by", "")),
        )
    )
    return combined


def reconcile_meta_payloads(
    ours: dict[str, Any],
    theirs: dict[str, Any],
) -> dict[str, Any]:
    """Field-merge two ``meta.json`` payloads for the squash driver (FR-004).

    ``ours`` is the target checkout (accepted-newer authority for acceptance/VCS
    provenance); ``theirs`` is the mission branch (planning-key authority — the
    #1732 ``-X theirs`` intent). Acceptance/VCS scalar keys are taken from ``ours``
    when present; ``acceptance_history`` is unioned; every other key falls back to
    ``theirs`` so mission-authoritative planning state is preserved.
    """
    result = dict(theirs)  # mission-authoritative baseline (C-002 / #1732).
    for key in _TARGET_AUTHORITATIVE_META_FIELDS:
        if key in ours:
            result[key] = ours[key]
    unioned_history = _union_acceptance_history(
        theirs.get(ACCEPTANCE_HISTORY_FIELD),
        ours.get(ACCEPTANCE_HISTORY_FIELD),
    )
    if unioned_history:
        result[ACCEPTANCE_HISTORY_FIELD] = unioned_history
    return result


def merge_driver_meta(
    base_path: str = typer.Argument(..., metavar="BASE"),
    ours_path: str = typer.Argument(..., metavar="OURS"),
    theirs_path: str = typer.Argument(..., metavar="THEIRS"),
) -> None:
    """Field-merge conflicting ``meta.json`` blobs; write result to ``ours``."""
    base, ours, theirs = _resolve_merge_driver_paths_or_exit(base_path, ours_path, theirs_path)
    _ = base  # %O ancestor: git always passes it, but the field merge is 2-way.
    try:
        merged = reconcile_meta_payloads(
            _load_json_object(ours),
            _load_json_object(theirs),
        )
    except (json.JSONDecodeError, EventLogMergeError) as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1) from exc
    ours.write_text(json.dumps(merged, **_META_JSON_KWARGS) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# traces/*.md markdown union (FR-003)
# ---------------------------------------------------------------------------


def union_trace_texts(ours_text: str, theirs_text: str) -> str:
    """Union two append-only trace documents (FR-003).

    Concrete contract: concatenate ``ours`` then ``theirs`` at line granularity,
    dropping any **non-empty** line already emitted (line-level dedup). Empty
    lines are preserved verbatim so section spacing survives. A section present on
    both sides collapses to one copy; the ``<!-- section:... -->`` delimiter lines
    are ordinary non-empty lines, so distinct delimiters both survive and a naive
    ``cat`` concat (which duplicates shared lines) fails this contract.
    """
    seen: set[str] = set()
    merged: list[str] = []
    for text in (ours_text, theirs_text):
        for line in text.splitlines():
            if line.strip() == "":
                merged.append(line)
                continue
            if line in seen:
                continue
            seen.add(line)
            merged.append(line)
    return "\n".join(merged) + "\n" if merged else ""


def merge_driver_traces(
    base_path: str = typer.Argument(..., metavar="BASE"),
    ours_path: str = typer.Argument(..., metavar="OURS"),
    theirs_path: str = typer.Argument(..., metavar="THEIRS"),
) -> None:
    """Union conflicting ``traces/*.md`` documents; write result to ``ours``."""
    base, ours, theirs = _resolve_merge_driver_paths_or_exit(base_path, ours_path, theirs_path)
    _ = base  # %O ancestor: git always passes it, but the union is 2-way.
    ours_text = ours.read_text(encoding="utf-8") if ours.exists() else ""
    theirs_text = theirs.read_text(encoding="utf-8") if theirs.exists() else ""
    ours.write_text(union_trace_texts(ours_text, theirs_text), encoding="utf-8")


# ---------------------------------------------------------------------------
# Row-aware, base-aware (3-way) matrix merge (FR-008)
# ---------------------------------------------------------------------------
#
# ``acceptance-matrix.json`` and ``issue-matrix.json`` are COORD-partition
# artifacts that both sides of a squash mission→target merge can genuinely
# diverge on (#2482 / #2804): the target fills evidence at accept time, a
# mission branch may independently gain its own rows. A whole-file
# "more-filled-side" pick (the retired #2804 heuristic) clobbers whichever
# side loses the fill-score comparison even when the two sides wrote
# DISJOINT rows — the exact #2482 loss this rewrite closes. These drivers
# instead reconcile PER ROW, 3-way (``%O``/``%A``/``%B``): see
# ``contracts/merge-driver-algorithm.md`` for the full contract this
# implements (row-key canonicalization, per-row reconciliation, delete-vs-
# stale disambiguation, byte-determinism, never re-authoring a computed
# field).


class RowMatrixMergeError(Exception):
    """Raised when a matrix document cannot be parsed/reconciled row-aware.

    Covers malformed JSON documents and the intra-side duplicate-key guard
    (two distinct raw rows on ONE side normalizing to the same canonical
    key) — both are refused rather than silently resolved, per the
    algorithm contract's "never silent drop" rule.
    """


def _parse_json_document(path: Path) -> dict[str, Any]:
    """Load a JSON *object* document from *path*; a missing file yields ``{}``."""
    if not path.exists():
        return {}
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return {}
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise RowMatrixMergeError(f"{path}: not valid JSON ({exc})") from exc
    if not isinstance(data, dict):
        raise RowMatrixMergeError(f"{path}: matrix document is not a JSON object")
    return data


# A field-level conflict never silently picks a side (contract: "never silent
# pick"). It is embedded as a git-style conflict marker string — the merged
# document stays valid JSON (the field's value is just a string), so the
# merge never aborts (2026-07-23-2 / no consolidation abort) while remaining
# visibly, unambiguously flagged for a human to resolve.
_CONFLICT_MARKER_OURS = "<<<<<<< ours"
_CONFLICT_MARKER_SEP = "======="
_CONFLICT_MARKER_THEIRS = ">>>>>>> theirs"


def _field_conflict_marker(ours_value: Any, theirs_value: Any) -> str:
    return "\n".join(
        (
            _CONFLICT_MARKER_OURS,
            json.dumps(ours_value),
            _CONFLICT_MARKER_SEP,
            json.dumps(theirs_value),
            _CONFLICT_MARKER_THEIRS,
        )
    )


def _merge_field(base_v: Any, ours_v: Any, theirs_v: Any) -> Any:
    """3-way merge of one field value (contract: per-row reconciliation).

    ``ours_v``/``theirs_v`` equal → take it (whether or not it changed from
    base). Changed on exactly one side (relative to *base_v*) → take the
    changed side (this also covers a field one side dropped entirely — a
    dict ``.get`` miss and ``base_v`` both read as ``None``, so "removed" and
    "changed to None" are treated identically, which is the correct 3-way
    reading). Changed on both sides to different values → a structured
    conflict marker, never a silent pick.
    """
    if ours_v == theirs_v:
        return ours_v
    if ours_v == base_v:
        return theirs_v
    if theirs_v == base_v:
        return ours_v
    return _field_conflict_marker(ours_v, theirs_v)


def _merge_row_fields(
    base_row: Mapping[str, Any] | None,
    ours_row: Mapping[str, Any],
    theirs_row: Mapping[str, Any],
) -> dict[str, Any]:
    """Per-field 3-way merge of one row that exists (with differing content)
    on at least two of the three sides. ``base_row`` may be ``None`` (the row
    was added independently on both ``ours``/``theirs`` — every field then
    merges against an absent/``None`` base, which correctly always resolves
    to "changed on the side that has it")."""
    base = base_row or {}
    field_names = dict.fromkeys((*base, *ours_row, *theirs_row))
    return {
        name: _merge_field(base.get(name), ours_row.get(name), theirs_row.get(name))
        for name in field_names
    }


def _reconcile_added_row(
    ours_row: Mapping[str, Any] | None,
    theirs_row: Mapping[str, Any] | None,
) -> dict[str, Any] | None:
    """A key absent from *base*: added on one side, or independently on both
    (contract rule 1/2 — never a delete, since there is no base entry to
    delete)."""
    if ours_row is None:
        return None if theirs_row is None else dict(theirs_row)  # added on B only
    if theirs_row is None:
        return dict(ours_row)  # added on A only
    if ours_row == theirs_row:
        return dict(ours_row)
    return _merge_row_fields(None, ours_row, theirs_row)


def _reconcile_existing_row(
    base_row: Mapping[str, Any],
    ours_row: Mapping[str, Any] | None,
    theirs_row: Mapping[str, Any] | None,
) -> dict[str, Any] | None:
    """A key present in *base*: delete-vs-stale disambiguation (contract) +
    3-way field merge when both sides still carry (differing) content."""
    if ours_row is None:
        # ours deleted; theirs still carries the base entry (maybe changed).
        return None if theirs_row is None or theirs_row == base_row else dict(theirs_row)
    if theirs_row is None:
        # theirs deleted; ours still carries the base entry (maybe changed).
        return None if ours_row == base_row else dict(ours_row)
    if ours_row == theirs_row:
        return dict(ours_row)
    return _merge_row_fields(base_row, ours_row, theirs_row)


def _reconcile_row(
    *,
    base_row: Mapping[str, Any] | None,
    ours_row: Mapping[str, Any] | None,
    theirs_row: Mapping[str, Any] | None,
) -> dict[str, Any] | None:
    """One row's 3-way reconciliation (contract: per-row reconciliation +
    delete-vs-stale disambiguation). Returns the merged row, or ``None`` when
    the row is dropped (both sides deleted it, or one side deleted it while
    the other left it genuinely unchanged from *base_row*)."""
    if base_row is None:
        return _reconcile_added_row(ours_row, theirs_row)
    return _reconcile_existing_row(base_row, ours_row, theirs_row)


def _canonicalize_keyed_rows(
    rows: Any,
    *,
    key_of: Callable[[Any, Mapping[str, Any]], str],
    is_row: Callable[[Any], bool] = lambda row: isinstance(row, Mapping),
) -> dict[str, dict[str, Any]]:
    """Canonicalize a side's raw row collection to ``{canonical_key: row}``.

    *rows* may be a ``list`` (acceptance-matrix ``criteria``/``negative_
    invariants``) or a ``dict`` keyed by raw issue-ref (issue-matrix
    ``rows``) — *key_of* extracts the canonical key from each. The intra-
    side collision guard (contract) fires here: two DISTINCT raw rows on
    this ONE side normalizing to the same canonical key raise
    :class:`RowMatrixMergeError` rather than silently collapsing (identical
    duplicates are harmlessly deduped).
    """
    items = rows.items() if isinstance(rows, Mapping) else enumerate(rows or [])
    canonical: dict[str, dict[str, Any]] = {}
    for raw_key, row in items:
        if not is_row(row):
            continue
        key = key_of(raw_key, row)
        row_dict = dict(row)
        if key in canonical and canonical[key] != row_dict:
            raise RowMatrixMergeError(
                f"intra-side duplicate row key {key!r}: two distinct rows on "
                "one side normalize to the same canonical key — refusing to "
                "silently collapse either (#2970-adjacent row-merge guard)"
            )
        canonical[key] = row_dict
    return canonical


def _reconcile_keyed_rows(
    base_rows: Any,
    ours_rows: Any,
    theirs_rows: Any,
    *,
    key_of: Callable[[Any, Mapping[str, Any]], str],
) -> dict[str, dict[str, Any]]:
    """3-way reconcile one row collection, keyed by canonicalized identity.

    Returns ``{canonical_key: merged_row}`` in sorted-key order — the stable
    canonical order the contract requires for byte-determinism.
    """
    base = _canonicalize_keyed_rows(base_rows, key_of=key_of)
    ours = _canonicalize_keyed_rows(ours_rows, key_of=key_of)
    theirs = _canonicalize_keyed_rows(theirs_rows, key_of=key_of)

    merged: dict[str, dict[str, Any]] = {}
    for key in sorted({*base, *ours, *theirs}):
        row = _reconcile_row(
            base_row=base.get(key), ours_row=ours.get(key), theirs_row=theirs.get(key)
        )
        if row is not None:
            merged[key] = row
    return merged  # already inserted in sorted-key order


# ---------------------------------------------------------------------------
# issue-matrix.json (FR-008): rows keyed by canonicalized issue_ref
# ---------------------------------------------------------------------------

# Matches a trailing run of 1+ digits, optionally preceded by ``#``/``GH-``/
# ``gh#`` — the shapes ``#1726`` / ``GH-1726`` / ``1726`` all normalize to.
_ISSUE_REF_DIGITS = re.compile(r"(\d+)\s*$")


def _canonicalize_issue_ref(raw_ref: str) -> str:
    """Normalize ``#1726`` / ``GH-1726`` / ``1726`` to the one canonical form.

    A ref with no trailing digits (a non-numeric key) is returned stripped,
    unchanged — it is already its own canonical form.
    """
    match = _ISSUE_REF_DIGITS.search(raw_ref.strip())
    return f"#{match.group(1)}" if match else raw_ref.strip()


def _issue_row_key(raw_ref: Any, _row: Mapping[str, Any]) -> str:
    return _canonicalize_issue_ref(str(raw_ref))


def reconcile_issue_matrix_documents(
    base_doc: Mapping[str, Any],
    ours_doc: Mapping[str, Any],
    theirs_doc: Mapping[str, Any],
) -> dict[str, Any]:
    """3-way, row-aware reconciliation of an ``issue-matrix.json`` document."""
    merged_rows = _reconcile_keyed_rows(
        base_doc.get("rows", {}),
        ours_doc.get("rows", {}),
        theirs_doc.get("rows", {}),
        key_of=_issue_row_key,
    )
    return {"schema_version": ISSUE_MATRIX_SCHEMA_VERSION, "rows": merged_rows}


def merge_driver_issue_matrix(
    base_path: str = typer.Argument(..., metavar="BASE"),
    ours_path: str = typer.Argument(..., metavar="OURS"),
    theirs_path: str = typer.Argument(..., metavar="THEIRS"),
) -> None:
    """Row-aware, 3-way merge of ``issue-matrix.json``; write result to ``ours`` (FR-008)."""
    base, ours, theirs = _resolve_merge_driver_paths_or_exit(base_path, ours_path, theirs_path)
    try:
        merged = reconcile_issue_matrix_documents(
            _parse_json_document(base),
            _parse_json_document(ours),
            _parse_json_document(theirs),
        )
    except RowMatrixMergeError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1) from exc
    ours.write_text(json.dumps(merged, indent=2, sort_keys=True) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# acceptance-matrix.json (FR-008): criteria keyed by criterion_id,
# negative_invariants keyed by invariant_id
# ---------------------------------------------------------------------------

_ACCEPTANCE_IDENTITY_FIELDS: tuple[str, ...] = ("mission_slug", "mission_number", "mission_type")


def _row_key_field(field_name: str) -> Callable[[Any, Mapping[str, Any]], str]:
    """A ``key_of`` extractor reading a row's own id *field_name* (list-shaped
    collections have no meaningful raw key of their own — the id lives
    inside the row)."""

    def _key_of(_raw_key: Any, row: Mapping[str, Any]) -> str:
        return str(row.get(field_name, ""))

    return _key_of


def _reconcile_identity_fields(
    base_doc: Mapping[str, Any],
    ours_doc: Mapping[str, Any],
    theirs_doc: Mapping[str, Any],
) -> dict[str, Any]:
    """Prefer ``ours`` (target-authoritative, mirroring the #1732/#2804 tie
    convention) for the acceptance-matrix's scalar identity fields, falling
    back to ``theirs`` then *base_doc* so ``mission_slug`` — required by
    :meth:`AcceptanceMatrix.from_dict` — is never missing from a real
    document."""
    result: dict[str, Any] = {}
    for name in _ACCEPTANCE_IDENTITY_FIELDS:
        ours_value = ours_doc.get(name)
        result[name] = ours_value if ours_value not in (None, "") else theirs_doc.get(name)
    if result.get("mission_slug") in (None, ""):
        result["mission_slug"] = base_doc.get("mission_slug", "")
    return result


def reconcile_acceptance_matrix_documents(
    base_doc: Mapping[str, Any],
    ours_doc: Mapping[str, Any],
    theirs_doc: Mapping[str, Any],
) -> dict[str, Any]:
    """3-way, row-aware reconciliation of an ``acceptance-matrix.json`` document.

    ``overall_verdict`` is a COMPUTED property (never a stored/merged field,
    per the contract) — it is recomputed by :class:`AcceptanceMatrix` from the
    reconciled ``criteria``/``negative_invariants``, never taken from either
    side's stored (possibly stale) value.
    """
    merged_criteria = _reconcile_keyed_rows(
        base_doc.get("criteria", []),
        ours_doc.get("criteria", []),
        theirs_doc.get("criteria", []),
        key_of=_row_key_field("criterion_id"),
    )
    merged_invariants = _reconcile_keyed_rows(
        base_doc.get("negative_invariants", []),
        ours_doc.get("negative_invariants", []),
        theirs_doc.get("negative_invariants", []),
        key_of=_row_key_field("invariant_id"),
    )
    merged_document = {
        **_reconcile_identity_fields(base_doc, ours_doc, theirs_doc),
        "criteria": list(merged_criteria.values()),
        "negative_invariants": list(merged_invariants.values()),
    }
    return AcceptanceMatrix.from_dict(merged_document).to_dict()


def merge_driver_acceptance_matrix(
    base_path: str = typer.Argument(..., metavar="BASE"),
    ours_path: str = typer.Argument(..., metavar="OURS"),
    theirs_path: str = typer.Argument(..., metavar="THEIRS"),
) -> None:
    """Row-aware, 3-way merge of ``acceptance-matrix.json``; write result to ``ours`` (FR-008)."""
    base, ours, theirs = _resolve_merge_driver_paths_or_exit(base_path, ours_path, theirs_path)
    try:
        merged = reconcile_acceptance_matrix_documents(
            _parse_json_document(base),
            _parse_json_document(ours),
            _parse_json_document(theirs),
        )
    except RowMatrixMergeError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1) from exc
    ours.write_text(json.dumps(merged, indent=2) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# review-cycle-*.md (review-cycle-verdict-seam-rebuild-01KZ2W7W WP18/T077):
# a two-verdict collision must REFUSE, never blend
# ---------------------------------------------------------------------------
#
# T017's discharge (see WP04's ruling, tests/architectural/census/
# verdict_seam_IC04.yaml, and tests/architectural/test_merge_reconciliation_
# class_guard.py::test_review_cycle_tasks_hazard_is_ruled_and_tracked): the
# create-window split (ADR 2026-08-03-1) means a coord mission's review
# cycles land on TWO different physical surfaces during the migration window
# (cycle 1 on PRIMARY at ``tasks/<wp>/``, a later cycle mis-numbered "1" again
# on COORD because ``ReviewCycleArtifact.next_cycle_number`` globs only the
# worktree it is called from) -- so a genuine, DIFFERENT-content collision
# under the SAME ``review-cycle-N.md`` filename is reachable, not
# hypothetical.
#
# THE DESIGN DECISION (T077, weighed against FR-006 / C-002(b)):
#
#   (a) REFUSE fail-closed -- embed both raw verdict documents, verbatim and
#       clearly demarcated (never interleaved/blended), and exit non-zero so
#       ``git merge --squash -X theirs`` reports the path as an unresolved
#       conflict (``_merge_branch_into`` then ``git merge --abort``s and
#       raises -- the target ref is never advanced. See
#       ``test_review_cycle_merge_driver.py``'s red-first ``_merge_branch_into``
#       proof).
#
#   (b) RENUMBER -- silently reassign the incoming ("theirs") record the next
#       free cycle number in the reconciled directory and write it out as a
#       SECOND file, leaving ``ours`` untouched.
#
# This driver implements (a), not (b). Reasoning:
#
# * A ``review-cycle-N.md`` is a *verdict record* -- FR-001/US2's entire point
#   is that a reader can trust the recorded verdict is the one a reviewer
#   actually wrote, unmodified. Renumbering only touches the FILENAME/
#   ``cycle_number`` field, never the verdict body -- but that field IS part
#   of the record a reviewer signed off on (it is what
#   ``latest_review_artifact_verdict`` / ``ReviewCycleArtifact.latest`` use to
#   decide WHICH record is authoritative-latest). Silently reassigning it
#   during an unattended squash merge changes which record downstream
#   consumers treat as "the latest verdict" without any human present to
#   confirm the reordering is chronologically correct -- this is the
#   "inventing" failure mode C-002(b)/FR-006 warn about, just at the
#   metadata layer instead of the body.
# * The renumbering computation itself would have to trust a directory
#   listing (``next_cycle_number``-shaped: glob + count/max) at merge time --
#   but an unreliable directory listing THAT SPANS TWO PARTITIONS is the
#   ROOT CAUSE of this exact hazard (create-window split). Re-deriving "next
#   free" via the same class of mechanism that caused the collision, this
#   time unattended inside a squash-merge subprocess with no operator able to
#   sanity-check chronology across the split, is not clearly safer than
#   refusing -- it just moves the same fragile assumption one layer down and
#   removes the human check.
# * Refusing loses NOTHING: both verdict documents survive byte-for-byte
#   (embedded verbatim in the conflict-marked ``ours`` path, AND the
#   incoming/mission side is untouched on its own branch since the whole
#   squash aborts) -- satisfying FR-006's "never overwrites" literally, not
#   just in spirit. A human resolves the actual chronology, which is exactly
#   the judgment call an automated merge driver should not make silently.
#
# Identical content on both sides is NOT this collision -- it is the
# trivial, common case (the same verdict was independently recorded/copied
# onto both partitions) and resolves cleanly with no conflict at all.


def merge_driver_review_cycle(
    base_path: str = typer.Argument(..., metavar="BASE"),
    ours_path: str = typer.Argument(..., metavar="OURS"),
    theirs_path: str = typer.Argument(..., metavar="THEIRS"),
) -> None:
    """Resolve a ``review-cycle-N.md`` collision without fabricating a verdict.

    Two distinct verdict documents colliding under the same filename are
    NEVER unioned/field-merged/interleaved into one document -- see the
    module-level design-decision comment immediately above this function for
    the full reasoning (refuse fail-closed, not renumber).

    Identical content on both sides (byte-for-byte) is the trivial fast path:
    resolves cleanly, exit 0, never reported as a conflict. Otherwise, both
    raw documents are embedded verbatim inside standard git-style conflict
    markers (never blended field-by-field -- a whole-document refusal, since
    a review verdict has no safely mergeable sub-fields the way a JSON matrix
    row does) and the driver exits non-zero so git reports the path as an
    unresolved conflict for a human to reconcile.
    """
    base, ours, theirs = _resolve_merge_driver_paths_or_exit(base_path, ours_path, theirs_path)
    _ = base  # %O ancestor: unused -- an add/add collision has no common base,
    # and the refuse-vs-fast-path decision is a pure 2-way (ours vs theirs)
    # content comparison regardless of whether a base exists.
    ours_text = ours.read_text(encoding="utf-8") if ours.exists() else ""
    theirs_text = theirs.read_text(encoding="utf-8") if theirs.exists() else ""

    if ours_text == theirs_text:
        # Trivial fast path (T077 validation checklist): the same verdict
        # landed on both partitions -- not a conflict, nothing to reconcile.
        ours.write_text(ours_text, encoding="utf-8")
        return

    conflict_document = "\n".join(
        (
            _CONFLICT_MARKER_OURS,
            ours_text,
            _CONFLICT_MARKER_SEP,
            theirs_text,
            _CONFLICT_MARKER_THEIRS,
        )
    )
    ours.write_text(conflict_document, encoding="utf-8")
    typer.echo(
        f"refusing to auto-resolve review-cycle verdict collision at {ours.name}: "
        "two distinct verdict records collided under one filename (T017/T077 "
        "create-window hazard); conflict markers written, resolve manually -- "
        "never fabricating a merged verdict",
        err=True,
    )
    raise typer.Exit(1)
