"""Unit tests for specify_cli.decisions.verify.

Covers all three VerifyFinding kinds, clean-state paths, plan.md scanning,
missing-file handling, location string format, and regex edge cases.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

from specify_cli.decisions.models import (
    DecisionIndex,
    DecisionStatus,
    IndexEntry,
    OriginFlow,
)
from specify_cli.decisions.store import save_index
from specify_cli.decisions.verify import (
    SENTINEL_RE,
    scan_markers,
    verify,
)

# ---------------------------------------------------------------------------
# Shared test data
# ---------------------------------------------------------------------------

ULID_A = "01AAAAAAAAAAAAAAAAAAAAAAAA"
ULID_B = "01BBBBBBBBBBBBBBBBBBBBBBBB"
ULID_C = "01CCCCCCCCCCCCCCCCCCCCCCCC"
ULID_UNKNOWN = "01ZZZZZZZZZZZZZZZZZZZZZZZZ"

MISSION_ID = "test-mission-id-001"
MISSION_SLUG = "test-mission"

T0 = datetime(2026, 4, 23, 10, 0, 0, tzinfo=UTC)
T1 = T0 + timedelta(seconds=60)
T2 = T0 + timedelta(seconds=120)


def _entry(
    decision_id: str = ULID_A,
    status: DecisionStatus = DecisionStatus.DEFERRED,
    created_at: datetime = T0,
) -> IndexEntry:
    return IndexEntry(
        decision_id=decision_id,
        origin_flow=OriginFlow.SPECIFY,
        step_id="step1",
        input_key="auth_strategy",
        question="Which auth strategy?",
        status=status,
        created_at=created_at,
        mission_id=MISSION_ID,
        mission_slug=MISSION_SLUG,
    )


def _write_index(mission_dir: Path, *entries: IndexEntry) -> None:
    """Save a DecisionIndex with the given entries."""
    idx = DecisionIndex(mission_id=MISSION_ID, entries=tuple(entries))
    save_index(mission_dir, idx)


def _write_spec(mission_dir: Path, content: str) -> None:
    (mission_dir / "spec.md").write_text(content, encoding="utf-8")


def _write_plan(mission_dir: Path, content: str) -> None:
    (mission_dir / "plan.md").write_text(content, encoding="utf-8")


def _sentinel(ulid: str, text: str = "need clarification") -> str:
    return f"[NEEDS CLARIFICATION: {text}] <!-- decision_id: {ulid} -->"


# ---------------------------------------------------------------------------
# T019-a  Clean case
# ---------------------------------------------------------------------------


def test_clean_case(tmp_path: Path) -> None:
    """Two deferred decisions with matching markers in spec.md → clean."""
    _write_index(tmp_path, _entry(ULID_A), _entry(ULID_B, created_at=T1))
    _write_spec(
        tmp_path,
        f"# Spec\n\n{_sentinel(ULID_A)}\n\n{_sentinel(ULID_B)}\n",
    )

    result = verify(tmp_path, MISSION_SLUG)

    assert result.status == "clean"
    assert result.findings == ()
    assert result.deferred_count == 2
    assert result.marker_count == 2


# ---------------------------------------------------------------------------
# T019-a (single)  Clean case — one deferred, one marker
# ---------------------------------------------------------------------------


def test_clean_case_single(tmp_path: Path) -> None:
    """One deferred decision with one matching marker → status=clean."""
    _write_index(tmp_path, _entry(ULID_A))
    _write_spec(tmp_path, f"{_sentinel(ULID_A)}\n")

    result = verify(tmp_path, MISSION_SLUG)

    assert result.status == "clean"
    assert result.findings == ()
    assert result.deferred_count == 1
    assert result.marker_count == 1


# ---------------------------------------------------------------------------
# T019-b  DEFERRED_WITHOUT_MARKER
# ---------------------------------------------------------------------------


def test_deferred_without_marker(tmp_path: Path) -> None:
    """Deferred decision with no marker in any doc → DEFERRED_WITHOUT_MARKER."""
    _write_index(tmp_path, _entry(ULID_A))
    _write_spec(tmp_path, "# Spec — no markers here\n")

    result = verify(tmp_path, MISSION_SLUG)

    assert result.status == "drift"
    assert len(result.findings) == 1
    f = result.findings[0]
    assert f.kind == "DEFERRED_WITHOUT_MARKER"
    assert f.decision_id_or_ref == ULID_A
    assert f.location is None


# ---------------------------------------------------------------------------
# T019-c  MARKER_WITHOUT_DECISION
# ---------------------------------------------------------------------------


def test_marker_without_decision(tmp_path: Path) -> None:
    """Marker references unknown decision_id → MARKER_WITHOUT_DECISION."""
    _write_index(tmp_path, _entry(ULID_A))
    _write_spec(tmp_path, f"{_sentinel(ULID_UNKNOWN)}\n")

    result = verify(tmp_path, MISSION_SLUG)

    assert result.status == "drift"
    kinds = {f.kind for f in result.findings}
    assert "MARKER_WITHOUT_DECISION" in kinds
    mwd = next(f for f in result.findings if f.kind == "MARKER_WITHOUT_DECISION")
    assert mwd.decision_id_or_ref == ULID_UNKNOWN
    assert mwd.location is not None


# ---------------------------------------------------------------------------
# T019-d  STALE_MARKER
# ---------------------------------------------------------------------------


def test_stale_marker(tmp_path: Path) -> None:
    """Marker references resolved decision → STALE_MARKER with status detail."""
    resolved = _entry(ULID_A, status=DecisionStatus.RESOLVED)
    _write_index(tmp_path, resolved)
    _write_spec(tmp_path, f"{_sentinel(ULID_A)}\n")

    result = verify(tmp_path, MISSION_SLUG)

    assert result.status == "drift"
    assert len(result.findings) == 1
    f = result.findings[0]
    assert f.kind == "STALE_MARKER"
    assert f.decision_id_or_ref == ULID_A
    assert "resolved" in (f.detail or "")


# ---------------------------------------------------------------------------
# T019-e  Mixed scenario
# ---------------------------------------------------------------------------


def test_mixed_findings(tmp_path: Path) -> None:
    """Two deferred (one has marker, one does not) plus one stale → 2 findings."""
    deferred_with = _entry(ULID_A)
    deferred_without = _entry(ULID_B, created_at=T1)
    resolved = _entry(ULID_C, status=DecisionStatus.RESOLVED, created_at=T2)
    _write_index(tmp_path, deferred_with, deferred_without, resolved)
    # spec.md: marker for ULID_A (clean) and ULID_C (stale)
    _write_spec(tmp_path, f"{_sentinel(ULID_A)}\n{_sentinel(ULID_C)}\n")

    result = verify(tmp_path, MISSION_SLUG)

    assert result.status == "drift"
    assert len(result.findings) == 2
    kinds = {f.kind for f in result.findings}
    assert "DEFERRED_WITHOUT_MARKER" in kinds
    assert "STALE_MARKER" in kinds

    dwm = next(f for f in result.findings if f.kind == "DEFERRED_WITHOUT_MARKER")
    assert dwm.decision_id_or_ref == ULID_B


# ---------------------------------------------------------------------------
# T019-f  Marker in plan.md
# ---------------------------------------------------------------------------


def test_marker_in_plan_md(tmp_path: Path) -> None:
    """Marker lives only in plan.md — still found and matched correctly."""
    _write_index(tmp_path, _entry(ULID_A))
    # No spec.md; marker only in plan.md
    _write_plan(tmp_path, f"{_sentinel(ULID_A)}\n")

    result = verify(tmp_path, MISSION_SLUG)

    assert result.status == "clean"
    assert result.findings == ()
    assert result.marker_count == 1


# ---------------------------------------------------------------------------
# T019-g  Missing files — deferred decision with no docs
# ---------------------------------------------------------------------------


def test_missing_files_with_deferred(tmp_path: Path) -> None:
    """No spec.md, no plan.md, one deferred → DEFERRED_WITHOUT_MARKER; no crash."""
    _write_index(tmp_path, _entry(ULID_A))

    result = verify(tmp_path, MISSION_SLUG)

    assert result.status == "drift"
    assert len(result.findings) == 1
    assert result.findings[0].kind == "DEFERRED_WITHOUT_MARKER"
    assert result.marker_count == 0


def test_empty_mission(tmp_path: Path) -> None:
    """Empty index, no docs → clean."""
    # Do not write index or docs at all
    result = verify(tmp_path, MISSION_SLUG)

    assert result.status == "clean"
    assert result.findings == ()
    assert result.deferred_count == 0
    assert result.marker_count == 0


# ---------------------------------------------------------------------------
# T019-h  Location format
# ---------------------------------------------------------------------------


def test_location_format(tmp_path: Path) -> None:
    """STALE_MARKER location is 'spec.md:L<N>' with the correct line number."""
    resolved = _entry(ULID_A, status=DecisionStatus.RESOLVED)
    _write_index(tmp_path, resolved)
    # Marker on line 3
    _write_spec(tmp_path, "line one\nline two\n" + _sentinel(ULID_A) + "\n")

    result = verify(tmp_path, MISSION_SLUG)

    assert result.status == "drift"
    stale = next(f for f in result.findings if f.kind == "STALE_MARKER")
    assert stale.location == "spec.md:L3"


# ---------------------------------------------------------------------------
# Regex edge cases
# ---------------------------------------------------------------------------


def test_sentinel_re_rejects_malformed_ulid() -> None:
    """A ULID shorter than 26 chars must NOT be matched by SENTINEL_RE."""
    short_id = "TOOSHORT"
    text = f"[NEEDS CLARIFICATION: foo] <!-- decision_id: {short_id} -->"
    assert SENTINEL_RE.search(text) is None


def test_sentinel_re_rejects_bare_marker() -> None:
    """A bare [NEEDS CLARIFICATION: ...] without the anchor comment must NOT match."""
    text = "[NEEDS CLARIFICATION: something unclear]"
    assert SENTINEL_RE.search(text) is None


def test_sentinel_re_matches_valid_ulid() -> None:
    """A well-formed 26-char Crockford ULID must be matched."""
    text = f"[NEEDS CLARIFICATION: foo] <!-- decision_id: {ULID_A} -->"
    m = SENTINEL_RE.search(text)
    assert m is not None
    assert m.group("did") == ULID_A


def test_marker_malformed_ulid_not_matched(tmp_path: Path) -> None:
    """A marker with a malformed (non-26-char) id does not appear in scan results."""
    _write_index(tmp_path)
    _write_spec(tmp_path, "[NEEDS CLARIFICATION: foo] <!-- decision_id: BADID -->\n")

    result = verify(tmp_path, MISSION_SLUG)

    assert result.marker_count == 0
    assert result.status == "clean"


# ---------------------------------------------------------------------------
# scan_markers helper
# ---------------------------------------------------------------------------


def test_scan_markers_returns_empty_for_missing_file(tmp_path: Path) -> None:
    result = scan_markers(tmp_path / "nonexistent.md")
    assert result == []


def test_scan_markers_line_numbers(tmp_path: Path) -> None:
    doc = tmp_path / "spec.md"
    doc.write_text(
        f"# Header\n\n{_sentinel(ULID_A)}\n{_sentinel(ULID_B)}\n",
        encoding="utf-8",
    )
    pairs = scan_markers(doc)
    assert pairs[0] == (ULID_A, "spec.md:L3")
    assert pairs[1] == (ULID_B, "spec.md:L4")
