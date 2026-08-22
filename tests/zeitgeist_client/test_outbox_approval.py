"""Z8-C: ``outbox_approval.py`` — the bundled outside-model approval surface
for locally queued Zeitgeist prose (program-graph handle Z8-C, parent Z8
"Human-gated prose outbox").

Covers the storage/state-machine half: content-addressed pending items,
idempotent resubmission, TTL-bounded expiry (default-deny — an expired item
is never approvable), the pending -> {approved, rejected, expired} ->
{revoked} transition set, and content-addressed, idempotent-on-retry
receipts. The human-gesture / fail-closed-trust half lives in
``test_outbox_approval_human_gesture.py`` (a separate file per node
criterion 1's two distinct concerns: "bundle inspect/approve/reject" here,
"outside model-callable ... actor/context/attestation binding" there).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from kernel.clock import parse_iso, timedelta
from specify_cli.zeitgeist_client import outbox_approval

pytestmark = pytest.mark.fast


@pytest.fixture()
def state_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / "spec-kitty-home"))
    return tmp_path / "spec-kitty-home"


class FakeTTY:
    """A scripted stand-in for the controlling terminal. Records every
    write() call (so tests can assert on exact disclosure) and answers
    readline() with a pre-scripted response line."""

    def __init__(self, response: str) -> None:
        self.response = response
        self.written: list[str] = []
        self.closed = False

    def write(self, text: str) -> int:
        self.written.append(text)
        return len(text)

    def flush(self) -> None:
        pass

    def readline(self) -> str:
        return self.response + "\n"

    def close(self) -> None:
        self.closed = True

    @property
    def transcript(self) -> str:
        return "".join(self.written)


def _approve_with_correct_challenge(monkeypatch: pytest.MonkeyPatch, item: outbox_approval.PendingItem, *, actor: str = "robert") -> outbox_approval.Receipt:
    tty = FakeTTY(item.item_id[:8])
    monkeypatch.setattr(outbox_approval, "_controlling_tty", lambda: tty)
    return outbox_approval.approve(item.item_id, actor=actor)


# --- submit(): content-addressed, idempotent, TTL-bounded -------------------


def test_submit_creates_a_pending_item_with_a_content_addressed_id(state_root: Path) -> None:
    item = outbox_approval.submit(repo="spec-kitty", audience="team-a", content="hello team")
    assert item.status == "pending"
    assert item.repo == "spec-kitty"
    assert item.audience == "team-a"
    assert item.content == "hello team"
    assert len(item.item_id) == 64  # sha256 hex
    expected_id = outbox_approval._content_hash(repo="spec-kitty", audience="team-a", content="hello team", context={})
    assert item.item_id == expected_id


def test_submit_is_idempotent_for_identical_content(state_root: Path) -> None:
    first = outbox_approval.submit(repo="spec-kitty", audience="team-a", content="same prose")
    second = outbox_approval.submit(repo="spec-kitty", audience="team-a", content="same prose")
    assert first.item_id == second.item_id
    assert len(outbox_approval.list_pending()) == 1


def test_submit_with_different_context_yields_a_different_id(state_root: Path) -> None:
    a = outbox_approval.submit(repo="spec-kitty", audience="team-a", content="same prose", context={"reason": "x"})
    b = outbox_approval.submit(repo="spec-kitty", audience="team-a", content="same prose", context={"reason": "y"})
    assert a.item_id != b.item_id


def test_submit_clamps_ttl_to_the_max_ceiling(state_root: Path) -> None:
    item = outbox_approval.submit(repo="spec-kitty", audience="team-a", content="x", ttl_s=outbox_approval.MAX_TTL_S * 100)
    created = parse_iso(item.created_at)
    expires = parse_iso(item.expires_at)
    assert (expires - created).total_seconds() == pytest.approx(outbox_approval.MAX_TTL_S, rel=0.01)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"repo": "", "audience": "a", "content": "c"},
        {"repo": "r", "audience": "", "content": "c"},
        {"repo": "r", "audience": "a", "content": ""},
        {"repo": "r", "audience": "a", "content": "c", "ttl_s": 0},
        {"repo": "r", "audience": "a", "content": "c", "ttl_s": -1},
    ],
)
def test_submit_rejects_empty_or_invalid_fields(state_root: Path, kwargs: dict[str, object]) -> None:
    with pytest.raises(ValueError):
        outbox_approval.submit(**kwargs)  # type: ignore[arg-type]


# --- inspect: list_pending()/show() ------------------------------------------


def test_list_pending_only_returns_items_still_awaiting_disposition(state_root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    pending_item = outbox_approval.submit(repo="spec-kitty", audience="team-a", content="still waiting")
    decided_item = outbox_approval.submit(repo="spec-kitty", audience="team-a", content="already decided")
    _approve_with_correct_challenge(monkeypatch, decided_item)

    ids = {i.item_id for i in outbox_approval.list_pending()}
    assert ids == {pending_item.item_id}


def test_list_pending_filters_by_repo(state_root: Path) -> None:
    outbox_approval.submit(repo="spec-kitty", audience="team-a", content="one")
    outbox_approval.submit(repo="zeitgeist", audience="team-a", content="two")
    only_spec_kitty = outbox_approval.list_pending(repo="spec-kitty")
    assert {i.repo for i in only_spec_kitty} == {"spec-kitty"}


def test_show_discloses_the_exact_full_content(state_root: Path) -> None:
    verbatim = "Ship the release notes to #team-a exactly as written, no paraphrase."
    item = outbox_approval.submit(repo="spec-kitty", audience="team-a", content=verbatim)
    shown = outbox_approval.show(item.item_id)
    assert shown.content == verbatim


def test_show_raises_not_found_for_an_unknown_id(state_root: Path) -> None:
    with pytest.raises(outbox_approval.NotFound):
        outbox_approval.show("0" * 64)


def test_redacted_preview_never_equals_long_raw_content(state_root: Path) -> None:
    long_content = "x" * 500
    preview = outbox_approval.redacted_preview(long_content)
    assert preview != long_content
    assert len(preview) < len(long_content)


def test_redacted_preview_returns_short_content_unchanged(state_root: Path) -> None:
    assert outbox_approval.redacted_preview("short") == "short"


# --- TTL / expiry: default-deny, never auto-published -----------------------


def test_pending_item_expires_after_its_ttl_and_is_swept_out_of_list_pending(state_root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    item = outbox_approval.submit(repo="spec-kitty", audience="team-a", content="stale by the time anyone looks", ttl_s=1.0)
    future = parse_iso(item.expires_at) + timedelta(seconds=1)
    monkeypatch.setattr(outbox_approval, "_now", lambda: future)

    assert outbox_approval.list_pending() == []
    assert outbox_approval.show(item.item_id).status == "expired"


def test_approve_on_an_expired_item_fails_closed_and_never_transitions_it(state_root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    item = outbox_approval.submit(repo="spec-kitty", audience="team-a", content="stale", ttl_s=1.0)
    future = parse_iso(item.expires_at) + timedelta(seconds=1)
    monkeypatch.setattr(outbox_approval, "_now", lambda: future)

    with pytest.raises(outbox_approval.Expired):
        outbox_approval.approve(item.item_id, actor="robert")
    assert outbox_approval.show(item.item_id).status == "expired"


# --- decide(): approve/reject/revoke transitions -----------------------------


def test_approve_transitions_pending_to_approved_and_records_a_receipt(state_root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    item = outbox_approval.submit(repo="spec-kitty", audience="team-a", content="go ahead")
    receipt = _approve_with_correct_challenge(monkeypatch, item, actor="robert")

    assert receipt.item_id == item.item_id
    assert receipt.decision == "approved"
    assert receipt.actor == "robert"
    assert outbox_approval.show(item.item_id).status == "approved"


def test_reject_transitions_pending_to_rejected(state_root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    item = outbox_approval.submit(repo="spec-kitty", audience="team-a", content="do not send")
    tty = FakeTTY(item.item_id[:8])
    monkeypatch.setattr(outbox_approval, "_controlling_tty", lambda: tty)

    receipt = outbox_approval.reject(item.item_id, actor="robert")
    assert receipt.decision == "rejected"
    assert outbox_approval.show(item.item_id).status == "rejected"


def test_reject_after_approve_raises_conflicting_decision(state_root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    item = outbox_approval.submit(repo="spec-kitty", audience="team-a", content="go ahead")
    _approve_with_correct_challenge(monkeypatch, item)

    tty = FakeTTY(item.item_id[:8])
    monkeypatch.setattr(outbox_approval, "_controlling_tty", lambda: tty)
    with pytest.raises(outbox_approval.ConflictingDecision):
        outbox_approval.reject(item.item_id, actor="robert")
    assert outbox_approval.show(item.item_id).status == "approved"  # unchanged


def test_approve_after_reject_raises_conflicting_decision(state_root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    item = outbox_approval.submit(repo="spec-kitty", audience="team-a", content="do not send")
    tty = FakeTTY(item.item_id[:8])
    monkeypatch.setattr(outbox_approval, "_controlling_tty", lambda: tty)
    outbox_approval.reject(item.item_id, actor="robert")

    tty2 = FakeTTY(item.item_id[:8])
    monkeypatch.setattr(outbox_approval, "_controlling_tty", lambda: tty2)
    with pytest.raises(outbox_approval.ConflictingDecision):
        outbox_approval.approve(item.item_id, actor="robert")


def test_revoke_on_a_still_pending_item_raises_invalid_transition(state_root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    item = outbox_approval.submit(repo="spec-kitty", audience="team-a", content="not decided yet")
    tty = FakeTTY(item.item_id[:8])
    monkeypatch.setattr(outbox_approval, "_controlling_tty", lambda: tty)
    with pytest.raises(outbox_approval.InvalidTransition):
        outbox_approval.revoke(item.item_id, actor="robert")


def test_revoke_after_approve_transitions_to_revoked_with_its_own_receipt(state_root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    item = outbox_approval.submit(repo="spec-kitty", audience="team-a", content="go ahead, for now")
    approve_receipt = _approve_with_correct_challenge(monkeypatch, item)

    tty = FakeTTY(item.item_id[:8])
    monkeypatch.setattr(outbox_approval, "_controlling_tty", lambda: tty)
    revoke_receipt = outbox_approval.revoke(item.item_id, actor="robert")

    assert revoke_receipt.decision == "revoked"
    assert revoke_receipt.receipt_id != approve_receipt.receipt_id
    assert outbox_approval.show(item.item_id).status == "revoked"


# --- receipts: content-addressed, idempotent on retry ------------------------


def test_receipt_id_is_content_addressed_over_the_decision(state_root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    item = outbox_approval.submit(repo="spec-kitty", audience="team-a", content="go ahead")
    receipt = _approve_with_correct_challenge(monkeypatch, item, actor="robert")

    expected = outbox_approval._receipt_hash(
        item_id=item.item_id, decision="approved", actor="robert", decided_at=receipt.decided_at
    )
    assert receipt.receipt_id == expected


def test_approving_an_already_approved_item_again_returns_the_same_receipt_without_a_new_gesture(
    state_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    item = outbox_approval.submit(repo="spec-kitty", audience="team-a", content="go ahead")
    first_receipt = _approve_with_correct_challenge(monkeypatch, item)

    def _boom() -> None:
        raise AssertionError("a retry of an already-decided item must not require a second human gesture")

    monkeypatch.setattr(outbox_approval, "_controlling_tty", _boom)
    second_receipt = outbox_approval.approve(item.item_id, actor="robert")
    assert second_receipt.receipt_id == first_receipt.receipt_id


# --- O1-C: status_counts() — counts only, never content ----------------------


def test_status_counts_on_an_empty_store_is_all_zero(state_root: Path) -> None:
    counts = outbox_approval.status_counts()
    assert counts == {"pending": 0, "approved": 0, "rejected": 0, "expired": 0, "revoked": 0}


def test_status_counts_reflects_every_terminal_state(state_root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    pending = outbox_approval.submit(repo="spec-kitty", audience="team-a", content="still pending")
    approved = outbox_approval.submit(repo="spec-kitty", audience="team-a", content="approve me")
    _approve_with_correct_challenge(monkeypatch, approved)
    rejected = outbox_approval.submit(repo="spec-kitty", audience="team-a", content="reject me")
    tty = FakeTTY(rejected.item_id[:8])
    monkeypatch.setattr(outbox_approval, "_controlling_tty", lambda: tty)
    outbox_approval.reject(rejected.item_id, actor="robert")
    revoked = outbox_approval.submit(repo="spec-kitty", audience="team-a", content="revoke me")
    _approve_with_correct_challenge(monkeypatch, revoked)
    tty2 = FakeTTY(revoked.item_id[:8])
    monkeypatch.setattr(outbox_approval, "_controlling_tty", lambda: tty2)
    outbox_approval.revoke(revoked.item_id, actor="robert")

    counts = outbox_approval.status_counts()
    assert counts["pending"] == 1
    assert counts["approved"] == 1
    assert counts["rejected"] == 1
    assert counts["revoked"] == 1
    assert pending.status == "pending"  # sanity: fixture item unchanged


def test_status_counts_sweeps_expired_items_first(state_root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    item = outbox_approval.submit(repo="spec-kitty", audience="team-a", content="will expire", ttl_s=1.0)
    future = parse_iso(item.expires_at) + timedelta(seconds=1)
    monkeypatch.setattr(outbox_approval, "_now", lambda: future)
    counts = outbox_approval.status_counts()
    assert counts["expired"] == 1
    assert counts["pending"] == 0


def test_status_counts_filters_by_repo_and_never_exposes_content(state_root: Path) -> None:
    outbox_approval.submit(repo="repo-a", audience="team-a", content="repo-a item")
    outbox_approval.submit(repo="repo-b", audience="team-a", content="repo-b item")
    counts_a = outbox_approval.status_counts(repo="repo-a")
    assert counts_a["pending"] == 1
    counts_b = outbox_approval.status_counts(repo="repo-b")
    assert counts_b["pending"] == 1
    # only ints — no way for content to leak through this surface
    assert all(isinstance(v, int) for v in counts_a.values())
