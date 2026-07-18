"""Hidden git merge-driver entrypoints for Spec Kitty repositories.

Three custom drivers keep mission bookkeeping semantic under
``git merge --squash -X theirs`` (the squash mission→target integration in
``lanes/merge.py::_merge_branch_into``). A custom driver overrides ``-X theirs``
on the paths it is registered for, so target-newer canonical state is reconciled
rather than clobbered (#2709 / FR-003 / FR-004):

- ``merge-driver-event-log`` — ``status.events.jsonl`` union (append-only log).
- ``merge-driver-meta``      — ``meta.json`` field merge: acceptance/VCS keys
  target-authoritative (the accepted-newer ``ours`` side), ``acceptance_history``
  unioned, all other (planning) keys mission-authoritative (``theirs``; preserves
  the #1732 ``-X theirs`` planning-artifact authority).
- ``merge-driver-traces``    — ``traces/*.md`` markdown union: order-preserving
  line-level dedup so both sides' sections survive without duplication.

Git invokes a driver with ``%O %A %B`` = base / ours / theirs and expects the
merged result written to the ``ours`` (``%A``) path with exit 0. Under the squash
integration ``ours`` is the target checkout (e.g. ``main``) and ``theirs`` is the
mission branch.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import typer

from specify_cli.acceptance import (
    ACCEPTANCE_HISTORY_FIELD,
    ACCEPTANCE_PROVENANCE_FIELDS,
)
from specify_cli.status import EventLogMergeError, merge_event_log_files

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


def merge_driver_event_log(
    base_path: str = typer.Argument(..., metavar="BASE"),
    ours_path: str = typer.Argument(..., metavar="OURS"),
    theirs_path: str = typer.Argument(..., metavar="THEIRS"),
) -> None:
    """Merge ``status.events.jsonl`` conflict inputs using event-log semantics."""
    try:
        merge_event_log_files(
            base_path=Path(base_path),
            ours_path=Path(ours_path),
            theirs_path=Path(theirs_path),
        )
    except EventLogMergeError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1) from exc


# ---------------------------------------------------------------------------
# meta.json field merge (FR-004)
# ---------------------------------------------------------------------------


def _load_json_object(path: Path) -> dict[str, Any]:
    """Load a JSON object from *path*; empty/missing yields ``{}``."""
    if not path.exists():
        return {}
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return {}
    data = json.loads(text)
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
    _ = base_path  # %O ancestor: git always passes it, but the field merge is 2-way.
    ours = Path(ours_path)
    try:
        merged = reconcile_meta_payloads(
            _load_json_object(ours),
            _load_json_object(Path(theirs_path)),
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
    _ = base_path  # %O ancestor: git always passes it, but the union is 2-way.
    ours = Path(ours_path)
    ours_text = ours.read_text(encoding="utf-8") if ours.exists() else ""
    theirs = Path(theirs_path)
    theirs_text = theirs.read_text(encoding="utf-8") if theirs.exists() else ""
    ours.write_text(union_trace_texts(ours_text, theirs_text), encoding="utf-8")
