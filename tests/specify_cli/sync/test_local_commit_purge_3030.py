"""T022: the operator can purge ``pending_local_commits`` (#3030 WP08).

WP12 gated local-commit frames on per-project consent and left the frames it
withholds **on disk**, recording that "WP08 owns the operator's purge path". WP08's
surface was ``delivery/`` only when that was written, so no such path existed: an
operator could run the purge, be told the project was erased, and still have pre-fix
mission slugs sitting in ``.kittify/sync-state.json``. Those slugs are client
engagement names for the 2026-07-27 incident's population — they *are* the
confidentiality content, not metadata about it.

Two properties shape every test here.

**The measurement is independent of the code under test.** ``_counts_on_disk``
re-reads ``sync-state.json`` with ``json.loads`` and counts frames itself. NFR-006 is
a differential ("100% of the target's entries, 0% of any other project's"), and a
check whose before *and* after both come from the purge's own census proves only that
the purge is arithmetically self-consistent — the shape a prior finding on this
mission was rejected for. Every assertion below therefore compares an independently
measured before against an independently measured after; the result object's own
censuses are asserted *against* those numbers rather than trusted as them.

**Pre-fix frames carry no ``project_uuid`` key at all** (WP12 added the field
additively), so ``_frame(project_uuid=_ABSENT)`` models the incident's actual
population — an absent key, not ``None`` and not ``""``. Their purgeability is the
whole point of this file, and it rests on store locality: ``sync-state.json`` lives
inside the checkout whose commits wrote it (``_sync_state_path``), and
``emit_local_commit`` is called by ``safe_commit`` with that same checkout's root, so
an unattributable frame in project X's file is X's by construction. The tests pin
that the vouching is *checked* rather than assumed: a checkout that declares another
project, or declares nothing, does not vouch.
"""

from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any

import pytest

from specify_cli.sync.local_commit import (
    IDENTITY_LESS_FRAME_KEY,
    SyncState,
    census_pending_local_commits,
    purge_all_pending_local_commits,
    purge_pending_local_commits,
    save_sync_state,
)

from specify_cli.core.saas_sync_config import sync_active
pytestmark = [
    pytest.mark.unit, pytest.mark.fast,
    pytest.mark.skipif(
        not sync_active(),
        reason="sync deactivated by default (#3799); set SPEC_KITTY_ENABLE_SAAS_SYNC=1 to run",
    ),
]

UUID_A = "aaaaaaaa-0000-0000-0000-00000000000a"
UUID_B = "bbbbbbbb-0000-0000-0000-00000000000b"
UUID_C = "cccccccc-0000-0000-0000-00000000000c"

#: Sentinel for "this frame has no ``project_uuid`` key" — the pre-fix shape.
_ABSENT = object()

_MISSION_ID = "acme-holdings-carve-out-01KYKWQS"


def _frame(
    *,
    project_uuid: Any,
    git_hash: str = "0" * 40,
    mission_id: str = _MISSION_ID,
) -> dict[str, Any]:
    """A stored ``LocalCommit`` frame; ``_ABSENT`` omits the identity key entirely."""
    frame: dict[str, Any] = {
        "type": "LocalCommit",
        "git_hash": git_hash,
        "mission_id": mission_id,
        "build_id": "01HT1BBBBBBBBBBBBBBBBBBBBB1",
        "changed_files": [f"kitty-specs/{mission_id}/spec.md"],
        "committed_at": "2026-07-30T07:00:00+00:00",
    }
    if project_uuid is not _ABSENT:
        frame["project_uuid"] = project_uuid
    return frame


def _checkout(tmp_path: Path, name: str, *, uuid: str | None) -> Path:
    """A checkout whose ``.kittify/config.yaml`` declares (or omits) project identity.

    ``uuid=None`` writes a config with no project uuid — the case where the store's
    location cannot vouch for its own unattributable frames.
    """
    root = tmp_path / name
    (root / ".kittify").mkdir(parents=True, exist_ok=True)
    lines = ["project:", f"  slug: {name}", "  node_id: 0123456789ab"]
    if uuid is not None:
        lines.insert(1, f"  uuid: {uuid}")
    (root / ".kittify" / "config.yaml").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return root


def _seed(root: Path, frames: list[dict[str, Any]], *, confirmed: str | None = None) -> None:
    save_sync_state(root, SyncState(last_saas_confirmed_hash=confirmed, pending_local_commits=frames))


def _state_path(root: Path) -> Path:
    return root / ".kittify" / "sync-state.json"


def _counts_on_disk(root: Path) -> dict[str, int]:
    """Frames per project, counted by re-reading the file — the independent instrument.

    Never calls ``census_pending_local_commits``: both operands of an NFR-006
    differential must not come from the code under test.
    """
    path = _state_path(root)
    if not path.exists():
        return {}
    frames = json.loads(path.read_text(encoding="utf-8"))["pending_local_commits"]
    counts: dict[str, int] = {}
    for frame in frames:
        raw = frame.get("project_uuid")
        key = "" if raw is None else str(raw).strip()
        counts[key] = counts.get(key, 0) + 1
    return counts


# ---------------------------------------------------------------------------
# Census
# ---------------------------------------------------------------------------


def test_census_groups_unattributable_frames_under_the_identity_less_key(tmp_path: Path) -> None:
    """The census reports the pre-fix population as such instead of hiding it.

    An operator cannot ask for the erasure of frames they cannot see, and folding
    them into a project's count would misreport that project's exposure.
    """
    root = _checkout(tmp_path, "alpha", uuid=UUID_A)
    _seed(
        root,
        [
            _frame(project_uuid=UUID_A),
            _frame(project_uuid=UUID_B),
            _frame(project_uuid=_ABSENT),
            _frame(project_uuid=None),
            _frame(project_uuid="   "),
        ],
    )

    census = census_pending_local_commits(root)

    assert census == {UUID_A: 1, UUID_B: 1, IDENTITY_LESS_FRAME_KEY: 3}
    assert sum(census.values()) == 5, (
        "the census must be total-preserving: a frame counted in no bucket has a "
        "differential of zero by construction and could be moved unnoticed"
    )
    assert census == _counts_on_disk(root)


def test_census_of_a_checkout_with_no_state_file_is_empty(tmp_path: Path) -> None:
    assert census_pending_local_commits(_checkout(tmp_path, "alpha", uuid=UUID_A)) == {}


# ---------------------------------------------------------------------------
# Dry run is the default
# ---------------------------------------------------------------------------


def test_dry_run_is_the_default_and_writes_nothing(tmp_path: Path) -> None:
    """Called with no ``dry_run`` argument, the purge must not delete (WP08 DoD)."""
    root = _checkout(tmp_path, "alpha", uuid=UUID_A)
    _seed(root, [_frame(project_uuid=UUID_A), _frame(project_uuid=_ABSENT), _frame(project_uuid=UUID_B)])
    raw_before = _state_path(root).read_text(encoding="utf-8")
    before = _counts_on_disk(root)

    result = purge_pending_local_commits(root, UUID_A)

    assert result.dry_run is True
    assert _state_path(root).read_text(encoding="utf-8") == raw_before
    assert _counts_on_disk(root) == before
    assert result.removed == 0
    assert result.selected == 2, "a dry run must still report what a real run would remove"
    assert result.is_exact


def test_dry_run_reported_count_equals_what_the_real_run_deletes(tmp_path: Path) -> None:
    """The preview is the contract: what it says is what the confirmed run removes.

    Both sides are also checked against the independently measured differential, so
    the equality cannot be satisfied by two consistent-but-wrong numbers.
    """
    root = _checkout(tmp_path, "alpha", uuid=UUID_A)
    _seed(
        root,
        [
            _frame(project_uuid=UUID_A, git_hash="1" * 40),
            _frame(project_uuid=UUID_A, git_hash="2" * 40),
            _frame(project_uuid=_ABSENT, git_hash="3" * 40),
            _frame(project_uuid=UUID_B, git_hash="4" * 40),
            _frame(project_uuid=UUID_C, git_hash="5" * 40),
        ],
    )

    preview = purge_pending_local_commits(root, UUID_A)
    before = _counts_on_disk(root)
    real = purge_pending_local_commits(root, UUID_A, dry_run=False)
    after = _counts_on_disk(root)

    measured = sum(before.values()) - sum(after.values())
    assert preview.selected == real.removed == measured == 3


# ---------------------------------------------------------------------------
# NFR-006: 100% of the target, 0% of anyone else
# ---------------------------------------------------------------------------


def test_purge_removes_the_targets_frames_and_no_others(tmp_path: Path) -> None:
    root = _checkout(tmp_path, "alpha", uuid=UUID_A)
    _seed(
        root,
        [
            _frame(project_uuid=UUID_A, git_hash="1" * 40),
            _frame(project_uuid=UUID_A, git_hash="2" * 40),
            _frame(project_uuid=UUID_B, git_hash="3" * 40),
            _frame(project_uuid=UUID_B, git_hash="4" * 40),
            _frame(project_uuid=UUID_C, git_hash="5" * 40),
        ],
    )
    before = _counts_on_disk(root)
    assert before == {UUID_A: 2, UUID_B: 2, UUID_C: 1}

    result = purge_pending_local_commits(root, UUID_A, dry_run=False)

    after = _counts_on_disk(root)
    assert after == {UUID_B: 2, UUID_C: 1}
    assert result.before == before
    assert result.after == after
    assert result.removed == 2
    assert result.other_project_differential == 0
    assert result.is_exact


def test_the_pre_fix_population_is_purged_with_the_project_that_owns_the_store(
    tmp_path: Path,
) -> None:
    """The incident's own frames — no ``project_uuid`` key — must be reachable.

    They are attributed by store locality: the file lives in the checkout whose
    commits wrote it, so an unattributable frame there is that checkout's project's.
    Leaving them behind is the failure mode this slice exists to remove, and it is
    exactly what a uuid-only match produces.
    """
    root = _checkout(tmp_path, "alpha", uuid=UUID_A)
    _seed(
        root,
        [
            _frame(project_uuid=_ABSENT, git_hash="1" * 40),
            _frame(project_uuid=None, git_hash="2" * 40),
            _frame(project_uuid="  ", git_hash="3" * 40),
            _frame(project_uuid=UUID_A, git_hash="4" * 40),
            _frame(project_uuid=UUID_B, git_hash="5" * 40),
        ],
    )

    result = purge_pending_local_commits(root, UUID_A, dry_run=False)

    assert _counts_on_disk(root) == {UUID_B: 1}
    assert result.removed == 4
    assert result.unattributed_in_scope is True
    assert result.is_exact


def test_frames_of_another_project_survive_that_projects_selector(tmp_path: Path) -> None:
    """Purging B from A's checkout takes B's frames only.

    The unattributable frames are **not** taken: A's checkout cannot vouch for them
    on B's behalf, and deleting unattributable confidential text under another
    project's purge is the silent overreach the body-queue purge also refuses.
    """
    root = _checkout(tmp_path, "alpha", uuid=UUID_A)
    _seed(
        root,
        [
            _frame(project_uuid=UUID_A, git_hash="1" * 40),
            _frame(project_uuid=_ABSENT, git_hash="2" * 40),
            _frame(project_uuid=UUID_B, git_hash="3" * 40),
        ],
    )

    result = purge_pending_local_commits(root, UUID_B, dry_run=False)

    assert _counts_on_disk(root) == {UUID_A: 1, IDENTITY_LESS_FRAME_KEY: 1}
    assert result.removed == 1
    assert result.unattributed_in_scope is False
    assert result.other_project_differential == 0
    assert result.is_exact


def test_a_checkout_that_declares_no_identity_vouches_for_nothing(tmp_path: Path) -> None:
    """No declared uuid means no locality attribution — the frames stay for ``--all``.

    Fails closed rather than guessing: an unreadable identity is absence, and absence
    must not authorise deletion any more than it authorises egress.
    """
    root = _checkout(tmp_path, "alpha", uuid=None)
    _seed(root, [_frame(project_uuid=_ABSENT), _frame(project_uuid=UUID_A)])

    result = purge_pending_local_commits(root, UUID_A, dry_run=False)

    assert _counts_on_disk(root) == {IDENTITY_LESS_FRAME_KEY: 1}
    assert result.unattributed_in_scope is False
    assert result.is_exact


def test_a_blank_selector_removes_nothing_including_the_identity_less_bucket(
    tmp_path: Path,
) -> None:
    """A blank target must never degrade into "match every frame".

    Sharper here than in the journal purge: ``IDENTITY_LESS_FRAME_KEY`` *is* the
    empty string, so a selector that reached the matcher unstripped would silently
    select the unattributable population by key equality.
    """
    root = _checkout(tmp_path, "alpha", uuid=UUID_A)
    _seed(root, [_frame(project_uuid=_ABSENT), _frame(project_uuid=UUID_A)])
    before = _counts_on_disk(root)

    for selector in ("", "   "):
        result = purge_pending_local_commits(root, selector, dry_run=False)
        assert result.removed == 0
        assert result.selected == 0
        assert _counts_on_disk(root) == before


def test_purge_of_a_project_with_no_frames_creates_no_state_file(tmp_path: Path) -> None:
    """Reporting zero must not materialise the queue file as a side effect."""
    root = _checkout(tmp_path, "alpha", uuid=UUID_A)

    result = purge_pending_local_commits(root, UUID_A, dry_run=False)

    assert result.removed == 0
    assert result.before == {} and result.after == {}
    assert not _state_path(root).exists()


def test_purge_leaves_the_ack_watermark_untouched(tmp_path: Path) -> None:
    """``last_saas_confirmed_hash`` is out of scope, deliberately.

    It is the ack watermark, not a census key: dropping it would make already
    acknowledged frames eligible to send again. It carries a git hash of the
    operator's own checkout and no mission slug, so retaining it removes nothing
    from FR-016's claim.
    """
    root = _checkout(tmp_path, "alpha", uuid=UUID_A)
    _seed(root, [_frame(project_uuid=UUID_A)], confirmed="f" * 40)

    purge_pending_local_commits(root, UUID_A, dry_run=False)

    stored = json.loads(_state_path(root).read_text(encoding="utf-8"))
    assert stored["last_saas_confirmed_hash"] == "f" * 40
    assert stored["pending_local_commits"] == []


def test_differential_holds_over_randomised_populations(tmp_path: Path) -> None:
    """NFR-006 over many shapes, measured independently on both sides.

    Seeded rather than free-running: a randomised gate whose failures cannot be
    reproduced is a gate that reports green about a case nobody can look at.
    """
    rng = random.Random(30303)
    for case in range(60):
        root = _checkout(tmp_path / f"case{case}", "alpha", uuid=UUID_A)
        population = [UUID_A, UUID_B, UUID_C, _ABSENT]
        frames = [
            _frame(project_uuid=rng.choice(population), git_hash=f"{index:040d}")
            for index in range(rng.randint(0, 12))
        ]
        _seed(root, frames)
        target = rng.choice([UUID_A, UUID_B, UUID_C])

        before = _counts_on_disk(root)
        result = purge_pending_local_commits(root, target, dry_run=False)
        after = _counts_on_disk(root)

        in_scope = {target} | ({IDENTITY_LESS_FRAME_KEY} if target == UUID_A else set())
        expected = {key: count for key, count in before.items() if key not in in_scope}
        assert after == expected, f"case {case}: target={target} before={before} after={after}"
        assert result.removed == sum(before.values()) - sum(after.values())
        assert result.is_exact


# ---------------------------------------------------------------------------
# FR-017: every frame in this checkout's queue
# ---------------------------------------------------------------------------


def test_purge_all_clears_every_frame_including_unidentifiable_ones(tmp_path: Path) -> None:
    root = _checkout(tmp_path, "alpha", uuid=None)
    _seed(
        root,
        [
            _frame(project_uuid=UUID_A, git_hash="1" * 40),
            _frame(project_uuid=_ABSENT, git_hash="2" * 40),
            _frame(project_uuid=UUID_B, git_hash="3" * 40),
        ],
    )

    preview = purge_all_pending_local_commits(root)
    assert preview.dry_run is True, "dry run is the default for the total purge too"
    assert preview.selected == 3
    assert _counts_on_disk(root) == {UUID_A: 1, IDENTITY_LESS_FRAME_KEY: 1, UUID_B: 1}

    result = purge_all_pending_local_commits(root, dry_run=False)

    assert _counts_on_disk(root) == {}
    assert result.removed == preview.selected == 3
    assert result.all_frames is True
    assert result.is_exact


# ---------------------------------------------------------------------------
# C-002: deletion is only ever the operator's explicit act
# ---------------------------------------------------------------------------


def test_the_flush_does_not_delete_the_frames_it_withholds(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An unattended path must never reach the purge.

    WP12's residual state is retained-and-ignored; the flush runs on every WebSocket
    connect, so a purge wired into it would delete confidential history with no
    operator in the loop. Asserted behaviourally at the egress seam and on disk,
    because "no call site today" is a fact about the current file and not a property.
    """
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / "home"))
    (tmp_path / "home").mkdir(parents=True, exist_ok=True)
    monkeypatch.delenv("SPEC_KITTY_ENABLE_SAAS_SYNC", raising=False)

    from specify_cli.sync.local_commit import flush_pending_local_commits

    root = _checkout(tmp_path, "alpha", uuid=UUID_A)
    _seed(root, [_frame(project_uuid=UUID_A), _frame(project_uuid=_ABSENT)])
    before = _counts_on_disk(root)

    class _RecordingClient:
        def __init__(self) -> None:
            self.connected = True
            self.sent: list[dict[str, Any]] = []

        async def send_event(self, frame: dict[str, Any]) -> None:
            self.sent.append(frame)

    client = _RecordingClient()
    flush_pending_local_commits(root, client)

    assert client.sent == [], "no consent record anywhere is not consent"
    assert _counts_on_disk(root) == before, "withheld frames are retained, never purged"
