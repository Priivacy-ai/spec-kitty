"""T018 — Unit tests for service resolve/defer/cancel terminal command semantics.

Tests verify idempotency on exact re-call, conflict rejection on contradictory
re-call, and that each terminal outcome updates the index and artifact correctly.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from specify_cli.decisions.models import DecisionErrorCode, DecisionStatus, OriginFlow
from specify_cli.decisions.service import (
    DecisionError,
    cancel_decision,
    defer_decision,
    open_decision,
    resolve_decision,
)
from specify_cli.decisions import store as _store

MISSION_ID = "01KTEST_MISSION_ID_000001"
MISSION_SLUG = "test-mission"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mission_dir(repo_root: Path) -> Path:
    return repo_root / "kitty-specs" / MISSION_SLUG


def _setup_meta(repo_root: Path) -> None:
    """Create meta.json so open_decision can resolve mission_id."""
    mission_dir = _mission_dir(repo_root)
    mission_dir.mkdir(parents=True, exist_ok=True)
    meta = {"mission_id": MISSION_ID, "mission_slug": MISSION_SLUG}
    (mission_dir / "meta.json").write_text(json.dumps(meta), encoding="utf-8")


def _open_decision(repo_root: Path) -> str:
    """Open a fresh decision and return its decision_id."""
    _setup_meta(repo_root)
    with patch("specify_cli.decisions.emit.emit_decision_opened", return_value=1):
        resp = open_decision(
            repo_root,
            MISSION_SLUG,
            origin_flow=OriginFlow.CHARTER,
            step_id="step-1",
            input_key="team_size",
            question="How large is the team?",
            options=("1-5", "6-20", "20+"),
            actor="alice",
        )
    return resp.decision_id


def _resolve(
    repo_root: Path,
    decision_id: str,
    *,
    final_answer: str = "1-5",
    other_answer: bool = False,
    rationale: str | None = None,
    resolved_by: str | None = None,
    dry_run: bool = False,
):
    with patch("specify_cli.decisions.emit.emit_decision_resolved", return_value=2):
        return resolve_decision(
            repo_root,
            MISSION_SLUG,
            decision_id,
            final_answer=final_answer,
            other_answer=other_answer,
            rationale=rationale,
            resolved_by=resolved_by,
            actor="alice",
            dry_run=dry_run,
        )


def _defer(
    repo_root: Path,
    decision_id: str,
    *,
    rationale: str = "not sure yet",
    dry_run: bool = False,
):
    with patch("specify_cli.decisions.emit.emit_decision_resolved", return_value=2):
        return defer_decision(
            repo_root,
            MISSION_SLUG,
            decision_id,
            rationale=rationale,
            actor="alice",
            dry_run=dry_run,
        )


def _cancel(
    repo_root: Path,
    decision_id: str,
    *,
    rationale: str = "no longer needed",
    dry_run: bool = False,
):
    with patch("specify_cli.decisions.emit.emit_decision_resolved", return_value=2):
        return cancel_decision(
            repo_root,
            MISSION_SLUG,
            decision_id,
            rationale=rationale,
            actor="alice",
            dry_run=dry_run,
        )


# ---------------------------------------------------------------------------
# T018a — resolve transitions status to RESOLVED with final_answer
# ---------------------------------------------------------------------------


def test_resolve_transitions_to_resolved(tmp_path: Path) -> None:
    did = _open_decision(tmp_path)
    resp = _resolve(tmp_path, did)

    assert resp.status == DecisionStatus.RESOLVED
    assert resp.terminal_outcome == "resolved"
    assert not resp.idempotent

    # Check index
    entry = next(e for e in _store.load_index(_mission_dir(tmp_path)).entries if e.decision_id == did)
    assert entry.status == DecisionStatus.RESOLVED
    assert entry.final_answer == "1-5"


def test_resolve_writes_artifact(tmp_path: Path) -> None:
    did = _open_decision(tmp_path)
    _resolve(tmp_path, did)
    artifact = _store.artifact_path(_mission_dir(tmp_path), did)
    assert artifact.exists()
    content = artifact.read_text()
    assert "resolved" in content


# ---------------------------------------------------------------------------
# T018b — resolve twice with identical payload is idempotent
# ---------------------------------------------------------------------------


def test_resolve_twice_same_answer_is_idempotent(tmp_path: Path) -> None:
    did = _open_decision(tmp_path)
    _resolve(tmp_path, did, final_answer="1-5")
    resp2 = _resolve(tmp_path, did, final_answer="1-5")

    assert resp2.idempotent is True


def test_resolve_idempotent_emits_no_second_event(tmp_path: Path) -> None:
    _setup_meta(tmp_path)
    did = _open_decision(tmp_path)
    with patch("specify_cli.decisions.emit.emit_decision_resolved", return_value=2) as mock_emit:
        resolve_decision(
            tmp_path,
            MISSION_SLUG,
            did,
            final_answer="1-5",
            actor="alice",
        )
        resolve_decision(
            tmp_path,
            MISSION_SLUG,
            did,
            final_answer="1-5",
            actor="alice",
        )
    assert mock_emit.call_count == 1


# ---------------------------------------------------------------------------
# T018c — resolve after defer raises TERMINAL_CONFLICT
# ---------------------------------------------------------------------------


def test_resolve_after_defer_raises_terminal_conflict(tmp_path: Path) -> None:
    did = _open_decision(tmp_path)
    _defer(tmp_path, did)

    with pytest.raises(DecisionError) as exc_info:
        _resolve(tmp_path, did)

    err = exc_info.value
    assert err.code == DecisionErrorCode.TERMINAL_CONFLICT
    assert err.details["decision_id"] == did


# ---------------------------------------------------------------------------
# T018d — resolve twice with different final_answer raises TERMINAL_CONFLICT
# ---------------------------------------------------------------------------


def test_resolve_twice_different_answer_raises_conflict(tmp_path: Path) -> None:
    did = _open_decision(tmp_path)
    _resolve(tmp_path, did, final_answer="1-5")

    with pytest.raises(DecisionError) as exc_info:
        _resolve(tmp_path, did, final_answer="6-20")

    assert exc_info.value.code == DecisionErrorCode.TERMINAL_CONFLICT


# ---------------------------------------------------------------------------
# T018e — defer transitions status to DEFERRED with rationale
# ---------------------------------------------------------------------------


def test_defer_transitions_to_deferred(tmp_path: Path) -> None:
    did = _open_decision(tmp_path)
    resp = _defer(tmp_path, did, rationale="need more info")

    assert resp.status == DecisionStatus.DEFERRED
    assert resp.terminal_outcome == "deferred"
    assert not resp.idempotent

    entry = next(e for e in _store.load_index(_mission_dir(tmp_path)).entries if e.decision_id == did)
    assert entry.status == DecisionStatus.DEFERRED
    assert entry.rationale == "need more info"


# ---------------------------------------------------------------------------
# T018f — cancel transitions status to CANCELED with rationale
# ---------------------------------------------------------------------------


def test_cancel_transitions_to_canceled(tmp_path: Path) -> None:
    did = _open_decision(tmp_path)
    resp = _cancel(tmp_path, did, rationale="no longer applicable")

    assert resp.status == DecisionStatus.CANCELED
    assert resp.terminal_outcome == "canceled"
    assert not resp.idempotent

    entry = next(e for e in _store.load_index(_mission_dir(tmp_path)).entries if e.decision_id == did)
    assert entry.status == DecisionStatus.CANCELED
    assert entry.rationale == "no longer applicable"


# ---------------------------------------------------------------------------
# T018g — resolve with nonexistent decision_id raises NOT_FOUND
# ---------------------------------------------------------------------------


def test_resolve_nonexistent_raises_not_found(tmp_path: Path) -> None:
    _setup_meta(tmp_path)
    with pytest.raises(DecisionError) as exc_info:
        _resolve(tmp_path, "NONEXISTENT_DECISION_ID_XXXX")

    assert exc_info.value.code == DecisionErrorCode.NOT_FOUND


def test_defer_nonexistent_raises_not_found(tmp_path: Path) -> None:
    _setup_meta(tmp_path)
    with pytest.raises(DecisionError) as exc_info:
        _defer(tmp_path, "NONEXISTENT_DECISION_ID_XXXX")

    assert exc_info.value.code == DecisionErrorCode.NOT_FOUND


def test_cancel_nonexistent_raises_not_found(tmp_path: Path) -> None:
    _setup_meta(tmp_path)
    with pytest.raises(DecisionError) as exc_info:
        _cancel(tmp_path, "NONEXISTENT_DECISION_ID_XXXX")

    assert exc_info.value.code == DecisionErrorCode.NOT_FOUND


# ---------------------------------------------------------------------------
# T018h — dry_run returns mock response with no filesystem side effects
# ---------------------------------------------------------------------------


def test_resolve_dry_run_returns_response(tmp_path: Path) -> None:
    did = _open_decision(tmp_path)
    resp = _resolve(tmp_path, did, dry_run=True)

    assert resp.terminal_outcome == "resolved"
    assert resp.status == DecisionStatus.RESOLVED
    assert not resp.idempotent

    # Index entry should still be OPEN
    entry = next(e for e in _store.load_index(_mission_dir(tmp_path)).entries if e.decision_id == did)
    assert entry.status == DecisionStatus.OPEN


def test_defer_dry_run_no_side_effects(tmp_path: Path) -> None:
    did = _open_decision(tmp_path)
    _defer(tmp_path, did, dry_run=True)

    entry = next(e for e in _store.load_index(_mission_dir(tmp_path)).entries if e.decision_id == did)
    assert entry.status == DecisionStatus.OPEN


def test_cancel_dry_run_no_side_effects(tmp_path: Path) -> None:
    did = _open_decision(tmp_path)
    _cancel(tmp_path, did, dry_run=True)

    entry = next(e for e in _store.load_index(_mission_dir(tmp_path)).entries if e.decision_id == did)
    assert entry.status == DecisionStatus.OPEN


# ---------------------------------------------------------------------------
# T018i — resolve with other_answer=True records other_answer in index
# ---------------------------------------------------------------------------


def test_resolve_other_answer_recorded(tmp_path: Path) -> None:
    did = _open_decision(tmp_path)
    with patch("specify_cli.decisions.emit.emit_decision_resolved", return_value=2):
        resolve_decision(
            tmp_path,
            MISSION_SLUG,
            did,
            final_answer="something custom",
            other_answer=True,
            actor="alice",
        )

    entry = next(e for e in _store.load_index(_mission_dir(tmp_path)).entries if e.decision_id == did)
    assert entry.other_answer is True
    assert entry.final_answer == "something custom"


# ---------------------------------------------------------------------------
# defer + re-defer with same rationale is idempotent
# ---------------------------------------------------------------------------


def test_defer_twice_same_rationale_is_idempotent(tmp_path: Path) -> None:
    did = _open_decision(tmp_path)
    _defer(tmp_path, did, rationale="wait for input")
    resp2 = _defer(tmp_path, did, rationale="wait for input")
    assert resp2.idempotent is True


# ---------------------------------------------------------------------------
# cancel + re-cancel with same rationale is idempotent
# ---------------------------------------------------------------------------


def test_cancel_twice_same_rationale_is_idempotent(tmp_path: Path) -> None:
    did = _open_decision(tmp_path)
    _cancel(tmp_path, did, rationale="obsolete")
    resp2 = _cancel(tmp_path, did, rationale="obsolete")
    assert resp2.idempotent is True
