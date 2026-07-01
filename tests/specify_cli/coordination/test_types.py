"""Unit tests for ``specify_cli.coordination.types`` (WP05 T020 / T025).

Covers:

* :class:`GitChangeSet` is frozen.
* :class:`Refused` is frozen and ``to_dict`` round-trips the public fields.
* :class:`Allowed` / :class:`Refused` discriminate cleanly via isinstance.
* :class:`PendingEventHandle` and :class:`CommitReceipt` are frozen and
  carry the contract-required fields.
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import UTC, datetime
from pathlib import Path

import pytest

from specify_cli.coordination.types import (
    Allowed,
    CommitReceipt,
    GitChangeSet,
    PendingEventHandle,
    PolicyVerdict,
    Refused,
)

pytestmark = [pytest.mark.unit, pytest.mark.fast]


def _change_set() -> GitChangeSet:
    return GitChangeSet(
        destination_ref="kitty/mission-foo-01ABCDEF",
        repo_root=Path("/repo"),
        worktree_root=Path("/repo/.worktrees/foo-01ABCDEF-coord"),
        paths=(Path("kitty-specs/foo-01ABCDEF/status.events.jsonl"),),
        message="status: WP01",
        operation="emit_status_transition",
    )


def test_git_change_set_is_frozen() -> None:
    cs = _change_set()
    with pytest.raises(FrozenInstanceError):
        cs.destination_ref = "other"  # type: ignore[misc]


def test_git_change_set_carries_paths_tuple() -> None:
    cs = _change_set()
    # ``paths`` is a tuple → hashable + immutable.
    assert isinstance(cs.paths, tuple)
    assert cs.paths[0].name == "status.events.jsonl"


def test_refused_to_dict_round_trips() -> None:
    refused = Refused(
        error_code="PROTECTED_BRANCH_REFUSED",
        message="refusing main",
        destination_ref="main",
        next_step="use coord branch",
    )
    payload = refused.to_dict()
    assert payload == {
        "error_code": "PROTECTED_BRANCH_REFUSED",
        "message": "refusing main",
        "destination_ref": "main",
        "next_step": "use coord branch",
    }


def test_refused_is_frozen() -> None:
    refused = Refused(
        error_code="X",
        message="m",
        destination_ref="b",
        next_step="n",
    )
    with pytest.raises(FrozenInstanceError):
        refused.error_code = "Y"  # type: ignore[misc]


def test_allowed_and_refused_discriminate_via_isinstance() -> None:
    a: PolicyVerdict = Allowed()
    r: PolicyVerdict = Refused(
        error_code="X", message="m", destination_ref="b", next_step="n",
    )
    assert isinstance(a, Allowed)
    assert not isinstance(a, Refused)
    assert isinstance(r, Refused)
    assert not isinstance(r, Allowed)


def test_pending_event_handle_is_frozen() -> None:
    handle = PendingEventHandle(event_id="01HXYZ")
    assert handle.event_id == "01HXYZ"
    with pytest.raises(FrozenInstanceError):
        handle.event_id = "other"  # type: ignore[misc]


def test_commit_receipt_carries_contract_fields() -> None:
    now = datetime.now(UTC)
    receipt = CommitReceipt(
        commit_sha="abc123",
        committed_at=now,
        destination_ref="kitty/mission-foo-01ABCDEF",
        worktree_root=Path("/repo/.worktrees/foo-coord"),
        event_ids=("01EID",),
    )
    assert receipt.commit_sha == "abc123"
    assert receipt.committed_at == now
    assert receipt.event_ids == ("01EID",)
    with pytest.raises(FrozenInstanceError):
        receipt.commit_sha = "deadbeef"  # type: ignore[misc]
