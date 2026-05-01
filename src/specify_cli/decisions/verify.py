"""Decision Moment verifier — marker ↔ decision cross-check.

Scans ``spec.md`` and ``plan.md`` for inline sentinel markers of the form::

    [NEEDS CLARIFICATION: <text>] <!-- decision_id: <ulid> -->

and cross-checks them against deferred entries in the decisions index.

Notes:
    - Both target doc files are optional; missing files are silently skipped.
    - The entire file is read into memory; this is appropriate for spec.md /
      plan.md files up to a few hundred KB.
    - The verifier is check-only: it never modifies any file.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from specify_cli.decisions.models import DecisionStatus, IndexEntry
from specify_cli.decisions.store import load_index


__all__ = [
    "SENTINEL_RE",
    "VerifyFinding",
    "VerifyResponse",
    "scan_markers",
    "verify",
]

# ---------------------------------------------------------------------------
# Sentinel regex
# ---------------------------------------------------------------------------

SENTINEL_RE = re.compile(r"\[NEEDS CLARIFICATION: [^\]]*\]\s*<!--\s*decision_id:\s*(?P<did>[0-9A-HJKMNP-TV-Z]{26})\s*-->")

# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------

FindingKind = Literal["DEFERRED_WITHOUT_MARKER", "MARKER_WITHOUT_DECISION", "STALE_MARKER"]


@dataclass(frozen=True)
class VerifyFinding:
    """A single drift finding produced by the verifier."""

    kind: FindingKind
    decision_id_or_ref: str
    location: str | None = None
    detail: str | None = None


@dataclass(frozen=True)
class VerifyResponse:
    """Structured result of a ``verify`` call."""

    status: Literal["clean", "drift"]
    deferred_count: int
    marker_count: int
    findings: tuple[VerifyFinding, ...]


# ---------------------------------------------------------------------------
# Marker scanner
# ---------------------------------------------------------------------------


def scan_markers(doc_path: Path) -> list[tuple[str, str]]:
    """Return ``(decision_id, location_str)`` pairs found in *doc_path*.

    *location_str* is ``"<filename>:L<line_number>"``.  Returns an empty list
    when the file does not exist or cannot be read.

    Only tokens that match the 26-character Crockford Base32 ULID alphabet are
    accepted; malformed ids are silently ignored (the regex rejects them).
    """
    if not doc_path.exists():
        return []

    results: list[tuple[str, str]] = []
    text = doc_path.read_text(encoding="utf-8")
    filename = doc_path.name

    for lineno, line in enumerate(text.splitlines(), start=1):
        for match in SENTINEL_RE.finditer(line):
            did = match.group("did")
            results.append((did, f"{filename}:L{lineno}"))

    return results


# ---------------------------------------------------------------------------
# Verifier
# ---------------------------------------------------------------------------


def verify(mission_dir: Path, mission_slug: str) -> VerifyResponse:  # noqa: ARG001 — reserved for future path customisation
    """Cross-check deferred decisions against inline sentinel markers.

    Loads the decisions index from *mission_dir*, scans ``spec.md`` and
    ``plan.md`` for ``[NEEDS CLARIFICATION: ...]`` sentinels, then applies
    three drift rules:

    - **DEFERRED_WITHOUT_MARKER** — a deferred decision has no inline marker.
    - **MARKER_WITHOUT_DECISION** — a marker references an unknown decision_id.
    - **STALE_MARKER** — a marker references a decision that is no longer
      deferred (e.g. resolved or canceled).

    Args:
        mission_dir: Directory that contains ``decisions/index.json`` and
            optionally ``spec.md`` / ``plan.md``.
        mission_slug: Human-readable mission slug (currently unused; reserved
            for future path customisation).

    Returns:
        A :class:`VerifyResponse` with ``status="clean"`` when no findings
        are produced, or ``status="drift"`` otherwise.
    """
    # 1. Load index
    index = load_index(mission_dir)

    # 2. Partition entries
    deferred_entries = [e for e in index.entries if e.status == DecisionStatus.DEFERRED]
    deferred_ids: set[str] = {e.decision_id for e in deferred_entries}
    known_ids: dict[str, IndexEntry] = {e.decision_id: e for e in index.entries}

    # 3. Scan target docs
    all_markers: list[tuple[str, str]] = []
    for doc_name in ("spec.md", "plan.md"):
        all_markers.extend(scan_markers(mission_dir / doc_name))

    # Build a deduplicated marker_ids map (first occurrence wins for location)
    marker_ids: dict[str, str] = {}
    for did, loc in all_markers:
        if did not in marker_ids:
            marker_ids[did] = loc

    # 4. Apply three-rule cross-check
    findings: list[VerifyFinding] = []

    # Rule 1 — DEFERRED_WITHOUT_MARKER
    for did in sorted(deferred_ids):
        if did not in marker_ids:
            findings.append(
                VerifyFinding(
                    kind="DEFERRED_WITHOUT_MARKER",
                    decision_id_or_ref=did,
                    location=None,
                    detail="No inline marker found in spec.md or plan.md",
                )
            )

    # Rule 2 — MARKER_WITHOUT_DECISION
    for marker_did, loc in sorted(marker_ids.items()):
        if marker_did not in known_ids:
            findings.append(
                VerifyFinding(
                    kind="MARKER_WITHOUT_DECISION",
                    decision_id_or_ref=marker_did,
                    location=loc,
                    detail="Marker references unknown decision_id",
                )
            )

    # Rule 3 — STALE_MARKER
    for marker_did, loc in sorted(marker_ids.items()):
        if marker_did in known_ids and marker_did not in deferred_ids:
            entry = known_ids[marker_did]
            findings.append(
                VerifyFinding(
                    kind="STALE_MARKER",
                    decision_id_or_ref=marker_did,
                    location=loc,
                    detail=f"Decision is in status '{entry.status.value}', not 'deferred'",
                )
            )

    return VerifyResponse(
        status="clean" if not findings else "drift",
        deferred_count=len(deferred_entries),
        marker_count=len(all_markers),
        findings=tuple(findings),
    )
