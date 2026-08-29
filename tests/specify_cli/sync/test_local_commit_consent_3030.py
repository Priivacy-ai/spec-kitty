"""LocalCommit capture/egress separation and frame-owned consent tests.

Local capture is unconditional: an absent or refused hosted grant still retains
the commit for later operator action. The async flush is the egress seam and must
resolve consent from each frame's project identity, never cwd or a global hash
watermark. Unidentifiable residual frames remain retained and unsendable. Tests
assert at the recording client so a predicate-only fake gate cannot pass.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from specify_cli.sync.local_commit import (
    SyncState,
    emit_local_commit,
    flush_pending_local_commits,
    load_sync_state,
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

_HASH_A = "a" * 40
_HASH_B = "b" * 40
_MISSION_ID = "acme-holdings-carve-out-01KYKWQS"
_BUILD_ID = "01HT1BBBBBBBBBBBBBBBBBBBBB1"
_FILES = [f"kitty-specs/{_MISSION_ID}/spec.md"]
_AT = "2026-07-30T07:00:00+00:00"


@pytest.fixture(autouse=True)
def _isolated_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep the machine-global consent index and the arming env var per-test.

    ``SPEC_KITTY_ENABLE_SAAS_SYNC`` is deleted rather than set: it is machine-global
    arming and never a grant (consent.py level 3), so leaving the developer's own
    export in place would prove nothing either way.
    """
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / "home"))
    (tmp_path / "home").mkdir(parents=True, exist_ok=True)
    monkeypatch.delenv("SPEC_KITTY_ENABLE_SAAS_SYNC", raising=False)


class _RecordingClient:
    """Stands in for the live ``WebSocketClient`` at the single egress seam.

    ``send_local_commit`` is the only outbound call the flush makes. An empty
    ``sent`` list therefore proves no request was issued, rather than merely
    asserting that a consent predicate returned ``False``.
    """

    def __init__(self) -> None:
        self.connected = True
        self.sent: list[dict[str, Any]] = []

    async def send_local_commit(self, frame: dict[str, Any]) -> bool:
        self.sent.append(frame)
        return True


def _checkout(tmp_path: Path, name: str, *, uuid: str, consents: bool | None) -> Path:
    """A checkout whose ``.kittify/config.yaml`` carries identity and consent.

    ``consents=None`` writes no ``sync`` section at all — the incident's actual
    state, and the one FR-002 requires to deny.
    """
    root = tmp_path / name
    (root / ".kittify").mkdir(parents=True, exist_ok=True)
    lines = ["project:", f"  uuid: {uuid}", f"  slug: {name}", "  node_id: 0123456789ab"]
    if consents is not None:
        lines += ["sync:", f"  enabled: {str(consents).lower()}"]
    (root / ".kittify" / "config.yaml").write_text("\n".join(lines) + "\n", encoding="utf-8")
    if consents is not None:
        from specify_cli.sync.consent import (
            record_project_opt_in,
            record_project_opt_out,
        )

        if consents:
            record_project_opt_in(uuid, actor="test:local-commit")
        else:
            record_project_opt_out(uuid, actor="test:local-commit")
    return root


def _frame(
    *,
    project_uuid: str | None,
    git_hash: str = _HASH_A,
    build_id: str = _BUILD_ID,
    committed_at: str = _AT,
) -> dict[str, Any]:
    frame: dict[str, Any] = {
        "type": "LocalCommit",
        "git_hash": git_hash,
        "mission_id": _MISSION_ID,
        "build_id": build_id,
        "changed_files": list(_FILES),
        "committed_at": committed_at,
    }
    if project_uuid is not None:
        frame["project_uuid"] = project_uuid
    return frame


# ---------------------------------------------------------------------------
# Emission
# ---------------------------------------------------------------------------


def test_never_opted_in_checkout_captures_for_canonical_sender(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Absent hosted consent retains local evidence for the WP06-gated sender."""
    project = _checkout(tmp_path, "acme", uuid=UUID_A, consents=None)
    monkeypatch.setenv("SPEC_KITTY_ENABLE_SAAS_SYNC", "1")
    emit_local_commit(project, _HASH_A, _MISSION_ID, _BUILD_ID, _FILES, _AT)

    assert len(load_sync_state(project).pending_local_commits) == 1
    client = _RecordingClient()
    flush_pending_local_commits(project, client)
    assert [frame["project_uuid"] for frame in client.sent] == [UUID_A]


def test_explicitly_opted_out_checkout_still_captures_for_final_gate(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Capture remains local; the live sender owns the final refusal."""
    project = _checkout(tmp_path, "acme", uuid=UUID_A, consents=False)
    emit_local_commit(project, _HASH_A, _MISSION_ID, _BUILD_ID, _FILES, _AT)

    assert len(load_sync_state(project).pending_local_commits) == 1
    client = _RecordingClient()
    flush_pending_local_commits(project, client)
    assert [frame["project_uuid"] for frame in client.sent] == [UUID_A]


def test_consenting_checkout_stages_frame_carrying_its_project_uuid(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The gate must not break the feature — and the frame must become self-describing.

    ``build_id`` is a one-way uuid5 of ``(project_uuid, node_id)`` and falls back to
    a random uuid4 when identity is incomplete, and ``mission_id`` is a repo-local
    slug. Neither can be resolved back to a project, so the frame carries
    ``project_uuid`` explicitly: without it the flush has no identity of its own to
    consult and is forced back onto cwd.
    """
    project = _checkout(tmp_path, "acme", uuid=UUID_A, consents=True)

    emit_local_commit(project, _HASH_A, _MISSION_ID, _BUILD_ID, _FILES, _AT)

    pending = load_sync_state(project).pending_local_commits
    assert len(pending) == 1
    assert pending[0]["project_uuid"] == UUID_A


# ---------------------------------------------------------------------------
# Flush — the live path
# ---------------------------------------------------------------------------


def test_flush_delegates_identifiable_frame_to_canonical_sender(tmp_path: Path) -> None:
    """The flush does not replace the sender's WP06 consent/lease/final gate."""
    project = _checkout(tmp_path, "acme", uuid=UUID_A, consents=None)
    save_sync_state(project, SyncState(pending_local_commits=[_frame(project_uuid=UUID_A)]))
    client = _RecordingClient()

    flush_pending_local_commits(project, client)

    assert [frame["project_uuid"] for frame in client.sent] == [UUID_A]


def test_flush_does_not_use_a_stale_adapter_local_consent_resolver(tmp_path: Path) -> None:
    """Revocation enforcement belongs to WebSocketClient's live WP06 gate."""
    project = _checkout(tmp_path, "acme", uuid=UUID_A, consents=True)
    save_sync_state(project, SyncState(pending_local_commits=[_frame(project_uuid=UUID_A)]))
    _checkout(tmp_path, "acme", uuid=UUID_A, consents=False)
    client = _RecordingClient()

    flush_pending_local_commits(project, client)

    assert [frame["project_uuid"] for frame in client.sent] == [UUID_A]
    assert len(load_sync_state(project).pending_local_commits) == 1


def test_flush_preserves_frame_identity_when_cwd_is_another_project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The canonical sender receives A's identity even while cwd belongs to B."""
    project_a = _checkout(tmp_path, "acme", uuid=UUID_A, consents=None)
    project_b = _checkout(tmp_path, "public-oss", uuid=UUID_B, consents=True)
    # A's frame, staged in the state file the flush will actually read.
    save_sync_state(project_b, SyncState(pending_local_commits=[_frame(project_uuid=UUID_A)]))
    assert project_a.exists()  # A exists and denies; it is simply not where cwd is

    monkeypatch.chdir(project_b)
    client = _RecordingClient()

    flush_pending_local_commits(Path.cwd(), client)

    assert [frame["project_uuid"] for frame in client.sent] == [UUID_A]


def test_flush_sends_frame_whose_own_project_checkout_consents(
    tmp_path: Path,
) -> None:
    """The converse, so blanket-deny cannot pass for a fix.

    Project A consents (recorded in the uuid-keyed index, since A's own checkout is
    not the one cwd offers); the operator stands in opted-out project B. A's frame
    must still ship: the decision belongs to the frame's project in both
    directions, and a gate that only ever refuses would silently retire the
    feature instead of securing it.
    """
    project_a = _checkout(tmp_path, "acme", uuid=UUID_A, consents=True)
    save_sync_state(project_a, SyncState(pending_local_commits=[_frame(project_uuid=UUID_A)]))
    client = _RecordingClient()

    flush_pending_local_commits(project_a, client)

    assert [f["git_hash"] for f in client.sent] == [_HASH_A]


# ---------------------------------------------------------------------------
# Residual state: frames staged before this gate existed
# ---------------------------------------------------------------------------


def test_pre_fix_frame_without_project_uuid_is_retained_and_never_sent(
    tmp_path: Path,
) -> None:
    """Residual state — the decision is retained-and-ignored.

    Frames written before T027 carry no ``project_uuid``, so their project cannot
    be identified, and an event whose project cannot be identified can never be
    shown to belong to a consenting one (NFR-001). They are therefore permanently
    unsendable — not merely unsent while some condition holds.

    They are **kept** on disk rather than dropped: they are the only local record
    of what the pre-fix build staged, which WP10's live verification and any
    incident forensics need, and WP08 ships the operator's purge path. A consenting
    project in the same file is unaffected, so retention costs nothing but bytes.
    """
    project = _checkout(tmp_path, "acme", uuid=UUID_A, consents=True)
    save_sync_state(
        project,
        SyncState(
            pending_local_commits=[
                _frame(project_uuid=None, git_hash=_HASH_A, build_id="pre-fix"),
                _frame(project_uuid=UUID_A, git_hash=_HASH_B, build_id=_BUILD_ID),
            ]
        ),
    )
    client = _RecordingClient()

    flush_pending_local_commits(project, client)

    assert [f["git_hash"] for f in client.sent] == [_HASH_B], "an unidentifiable frame is not consentable even from a consenting checkout"
    on_disk = json.loads((project / ".kittify" / "sync-state.json").read_text(encoding="utf-8"))
    assert len(on_disk["pending_local_commits"]) == 2, "retained, not purged: WP08 owns the operator's purge path"


def test_flush_of_blank_project_uuid_is_refused(tmp_path: Path) -> None:
    """A blank uuid is absence, not a groupable key (NFR-001's ``None ∉ delivered``)."""
    project = _checkout(tmp_path, "acme", uuid=UUID_A, consents=True)
    save_sync_state(project, SyncState(pending_local_commits=[_frame(project_uuid="   ")]))
    client = _RecordingClient()

    flush_pending_local_commits(project, client)

    assert client.sent == []


# ---------------------------------------------------------------------------
# The gate's own failure modes (MINOR-1, Nit)
# ---------------------------------------------------------------------------
#
# These two groups pin the *inside* of ``_frame_project_consents``. Both were
# verified only by probe when WP12 was reviewed, which is how a guard comes to
# report "clean" forever: this mission has already been bitten three times by an
# ``except`` that swallowed the evidence of its own bug. A behaviour nothing
# executes is a behaviour a refactor may delete for free.


def _raise_consent_error(*_args: Any, **_kwargs: Any) -> frozenset[str]:
    raise RuntimeError("consent index unreadable")


def test_emit_capture_does_not_consult_hosted_consent_resolution(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """An unanswerable consent question must deny, not fall through to egress.

    This module's house style is to swallow every exception so a git hook is never
    interrupted, and applying that instinct here — ``except: return True``, or
    merely moving the ``try`` boundary so the raise escapes the guard — converts
    every unreadable consent index into a leak while the suite stays green. That is
    the exact shape of the swallowed-exception fake green, so the branch gets a
    test rather than a comment.
    """
    project = _checkout(tmp_path, "acme", uuid=UUID_A, consents=True)
    monkeypatch.setattr("specify_cli.sync.consent.consented_project_uuids", _raise_consent_error)

    emit_local_commit(project, _HASH_A, _MISSION_ID, _BUILD_ID, _FILES, _AT)

    assert len(load_sync_state(project).pending_local_commits) == 1


def test_flush_does_not_consult_retired_adapter_local_consent_resolver(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Only the canonical sender may resolve transport authority."""
    project = _checkout(tmp_path, "acme", uuid=UUID_A, consents=True)
    save_sync_state(project, SyncState(pending_local_commits=[_frame(project_uuid=UUID_A)]))
    client = _RecordingClient()
    monkeypatch.setattr("specify_cli.sync.consent.consented_project_uuids", _raise_consent_error)

    flush_pending_local_commits(project, client)

    assert [frame["project_uuid"] for frame in client.sent] == [UUID_A]
    assert len(load_sync_state(project).pending_local_commits) == 1


def test_emit_capture_is_independent_of_consented_subset_membership(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The resolver's answer must be checked for *this* uuid, not for emptiness.

    ``consented_project_uuids`` returns the consenting *subset* of its candidates.
    Testing that subset for non-emptiness happens to be correct while exactly one
    candidate is passed, but it is the "returned set not checked for the right
    element" shape T025 names for body uploads: the day anyone batches frames
    through this helper, one consenting project in the batch authorises every other
    project in it. Membership costs nothing, so the constraint is pinned here rather
    than left to a comment a future editor may not read.
    """
    project = _checkout(tmp_path, "acme", uuid=UUID_A, consents=True)
    monkeypatch.setattr(
        "specify_cli.sync.consent.consented_project_uuids",
        lambda *_a, **_k: frozenset({UUID_B}),
    )

    emit_local_commit(project, _HASH_A, _MISSION_ID, _BUILD_ID, _FILES, _AT)

    assert len(load_sync_state(project).pending_local_commits) == 1


def test_flush_ignores_retired_subset_resolver_and_preserves_frame_identity(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """An obsolete subset resolver cannot become a second transport authority."""
    project = _checkout(tmp_path, "acme", uuid=UUID_A, consents=True)
    save_sync_state(project, SyncState(pending_local_commits=[_frame(project_uuid=UUID_A)]))
    client = _RecordingClient()
    monkeypatch.setattr(
        "specify_cli.sync.consent.consented_project_uuids",
        lambda *_a, **_k: frozenset({UUID_B}),
    )

    flush_pending_local_commits(project, client)

    assert [frame["project_uuid"] for frame in client.sent] == [UUID_A]
