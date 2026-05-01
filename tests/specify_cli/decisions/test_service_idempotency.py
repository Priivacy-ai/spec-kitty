"""T017 — Unit tests for service.open_decision() idempotency semantics.

Tests verify that open_decision correctly implements the idempotency
semantics from research.md R-3 and spec.md FR-004, FR-005.

The service API uses (repo_root, mission_slug) to derive the mission_dir
as ``repo_root / "kitty-specs" / mission_slug``, and reads mission_id from
``meta.json`` in that directory.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from specify_cli.decisions.models import DecisionErrorCode, DecisionStatus, OriginFlow
from specify_cli.decisions.service import DecisionError, open_decision
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


def _open(
    repo_root: Path,
    *,
    step_id: str | None = "step-1",
    slot_key: str | None = None,
    input_key: str = "team_size",
    actor: str = "alice",
    dry_run: bool = False,
):
    _setup_meta(repo_root)
    return open_decision(
        repo_root,
        MISSION_SLUG,
        origin_flow=OriginFlow.CHARTER,
        step_id=step_id,
        slot_key=slot_key,
        input_key=input_key,
        question="How large is the team?",
        options=("1-5", "6-20", "20+"),
        actor=actor,
        dry_run=dry_run,
    )


# ---------------------------------------------------------------------------
# T017a — First call returns idempotent=False and creates index + artifact
# ---------------------------------------------------------------------------


def test_first_open_returns_not_idempotent(tmp_path: Path) -> None:
    with patch("specify_cli.decisions.emit.emit_decision_opened", return_value=1):
        resp = _open(tmp_path)

    assert resp.idempotent is False
    assert resp.decision_id != "DRY_RUN"
    assert len(resp.decision_id) == 26  # ULID

    mission_dir = _mission_dir(tmp_path)
    # Index and artifact should exist
    index = _store.load_index(mission_dir)
    assert len(index.entries) == 1
    artifact = _store.artifact_path(mission_dir, resp.decision_id)
    assert artifact.exists()


# ---------------------------------------------------------------------------
# T017b — Second call with same logical key returns idempotent=True + same id
# ---------------------------------------------------------------------------


def test_second_open_same_logical_key_is_idempotent(tmp_path: Path) -> None:
    with patch("specify_cli.decisions.emit.emit_decision_opened", return_value=1):
        resp1 = _open(tmp_path)
        resp2 = _open(tmp_path)

    assert resp2.idempotent is True
    assert resp2.decision_id == resp1.decision_id

    # No extra index entries
    index = _store.load_index(_mission_dir(tmp_path))
    assert len(index.entries) == 1


def test_second_open_no_new_event_emitted(tmp_path: Path) -> None:
    _setup_meta(tmp_path)
    with patch("specify_cli.decisions.emit.emit_decision_opened", return_value=1) as mock_emit:
        open_decision(
            tmp_path,
            MISSION_SLUG,
            origin_flow=OriginFlow.CHARTER,
            step_id="step-1",
            input_key="team_size",
            question="How large?",
            options=("1-5",),
            actor="alice",
        )
        open_decision(
            tmp_path,
            MISSION_SLUG,
            origin_flow=OriginFlow.CHARTER,
            step_id="step-1",
            input_key="team_size",
            question="How large?",
            options=("1-5",),
            actor="alice",
        )
    assert mock_emit.call_count == 1


# ---------------------------------------------------------------------------
# T017c — Open on terminal entry raises ALREADY_CLOSED
# ---------------------------------------------------------------------------


def test_open_after_terminal_raises_already_closed(tmp_path: Path) -> None:
    with patch("specify_cli.decisions.emit.emit_decision_opened", return_value=1):
        resp = _open(tmp_path)

    # Manually transition to terminal
    _store.update_entry(_mission_dir(tmp_path), resp.decision_id, status=DecisionStatus.RESOLVED)

    with pytest.raises(DecisionError) as exc_info, patch("specify_cli.decisions.emit.emit_decision_opened", return_value=1):
        _open(tmp_path)

    err = exc_info.value
    assert err.code == DecisionErrorCode.ALREADY_CLOSED
    assert err.details["decision_id"] == resp.decision_id


# ---------------------------------------------------------------------------
# T017d — Different input_keys on same step_id produce separate entries
# ---------------------------------------------------------------------------


def test_different_input_keys_produce_separate_entries(tmp_path: Path) -> None:
    _setup_meta(tmp_path)
    with patch("specify_cli.decisions.emit.emit_decision_opened", return_value=1):
        resp1 = open_decision(
            tmp_path,
            MISSION_SLUG,
            origin_flow=OriginFlow.CHARTER,
            step_id="step-1",
            input_key="team_size",
            question="How large?",
            actor="alice",
        )
        resp2 = open_decision(
            tmp_path,
            MISSION_SLUG,
            origin_flow=OriginFlow.CHARTER,
            step_id="step-1",
            input_key="budget",
            question="What budget?",
            actor="alice",
        )

    assert resp1.decision_id != resp2.decision_id
    index = _store.load_index(_mission_dir(tmp_path))
    assert len(index.entries) == 2


# ---------------------------------------------------------------------------
# T017e — dry_run returns DRY_RUN id with no filesystem side effects
# ---------------------------------------------------------------------------


def test_dry_run_returns_dry_run_id(tmp_path: Path) -> None:
    resp = _open(tmp_path, dry_run=True)
    assert resp.decision_id == "DRY_RUN"
    assert resp.idempotent is False


def test_dry_run_creates_no_index(tmp_path: Path) -> None:
    _open(tmp_path, dry_run=True)
    index_file = _store.index_path(_mission_dir(tmp_path))
    assert not index_file.exists()


def test_dry_run_emits_no_event(tmp_path: Path) -> None:
    with patch("specify_cli.decisions.emit.emit_decision_opened", return_value=1) as mock_emit:
        _open(tmp_path, dry_run=True)
    mock_emit.assert_not_called()


# ---------------------------------------------------------------------------
# T017f — Missing step_id and slot_key raises MISSING_STEP_OR_SLOT
# ---------------------------------------------------------------------------


def test_missing_step_and_slot_raises_error(tmp_path: Path) -> None:
    _setup_meta(tmp_path)
    with pytest.raises(DecisionError) as exc_info:
        open_decision(
            tmp_path,
            MISSION_SLUG,
            origin_flow=OriginFlow.CHARTER,
            step_id=None,
            slot_key=None,
            input_key="team_size",
            question="Q?",
            actor="alice",
        )

    assert exc_info.value.code == DecisionErrorCode.MISSING_STEP_OR_SLOT


# ---------------------------------------------------------------------------
# Bonus: slot_key works as an alternative identifier
# ---------------------------------------------------------------------------


def test_slot_key_opens_successfully(tmp_path: Path) -> None:
    with patch("specify_cli.decisions.emit.emit_decision_opened", return_value=1):
        resp = _open(tmp_path, step_id=None, slot_key="slot-abc")
    assert resp.decision_id != "DRY_RUN"
    assert not resp.idempotent


def test_slot_key_idempotent_on_retry(tmp_path: Path) -> None:
    with patch("specify_cli.decisions.emit.emit_decision_opened", return_value=1):
        resp1 = _open(tmp_path, step_id=None, slot_key="slot-abc")
        resp2 = _open(tmp_path, step_id=None, slot_key="slot-abc")
    assert resp2.idempotent is True
    assert resp2.decision_id == resp1.decision_id
