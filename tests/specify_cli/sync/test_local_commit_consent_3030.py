"""T027: LocalCommit frames are gated on per-project consent (#3030 WP12).

The third uncovered egress path, found by the post-WP06 adversarial review rather
than by any earlier mission artefact. Before this file,
``grep -c "consent" src/specify_cli/sync/local_commit.py`` was **0**: every
``safe_commit`` touching ``kitty-specs/`` wrote a frame carrying the mission slug
(a client engagement name for the 2026-07-27 incident's population), and the next
WebSocket connect from that working directory flushed it.

Two invariants are pinned here, and the second is the one that makes the fix real:

1. **Emission and flush both deny by default** (FR-002). No consent record
   anywhere is not consent, so a never-opted-in checkout writes no frame at all
   and any frame already on disk for a non-consenting project is never sent.
2. **The decision comes from the frame's own identity, never from the working
   directory.** ``flush_pending_local_commits`` is called with
   ``WebSocketClient._repo_root``, which defaults to ``Path.cwd()``
   (``client.py:104``) because ``runtime.py`` constructs the client without it.
   A cwd-derived check therefore answers the question for whichever project the
   operator happens to be standing in — the identical defect T025 names for body
   uploads and M1 names for the capture path. ``test_flush_refuses_frame_whose_own
   _project_denies_even_when_cwd_consents`` fails for a cwd-derived implementation,
   and ``test_flush_sends_frame_whose_own_project_consents_even_when_cwd_denies``
   fails for a blanket-deny one. Neither passes by accident.

Every assertion here is against a recording client at the **egress seam**
(``client.send_event`` is the only call ``local_commit`` makes on its way to the
socket), not against a predicate's return value — SC-003's pattern. A gate that
returns ``False`` while something else still posts the frame is the failure mode
this mission exists to close.
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

pytestmark = [pytest.mark.unit, pytest.mark.fast]

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

    ``send_event`` is the only outbound call ``local_commit`` makes, so an empty
    ``sent`` list is evidence that *no request was issued* — stronger than
    asserting a consent predicate returned ``False``.
    """

    def __init__(self) -> None:
        self.connected = True
        self.sent: list[dict[str, Any]] = []

    async def send_event(self, frame: dict[str, Any]) -> None:
        self.sent.append(frame)


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
    return root


def _index(**entries: bool) -> None:
    """Seed the machine-global uuid-keyed consent index through its public writer."""
    from specify_cli.sync.consent import set_project_consent

    for uuid, enabled in entries.items():
        set_project_consent(uuid, enabled)


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


def test_never_opted_in_checkout_writes_no_frame_and_sends_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The incident's machine state: authenticated, armed, no consent record.

    Both halves matter. No frame on disk means the connect-time flush has nothing
    to replay; no send means the immediate-send attempt is gated too, whether or
    not a production writer for ``token_manager._ws_client`` ever appears.
    """
    project = _checkout(tmp_path, "acme", uuid=UUID_A, consents=None)
    monkeypatch.setenv("SPEC_KITTY_ENABLE_SAAS_SYNC", "1")
    client = _RecordingClient()
    monkeypatch.setattr(
        "specify_cli.sync.local_commit._get_saas_client", lambda: client
    )

    emit_local_commit(project, _HASH_A, _MISSION_ID, _BUILD_ID, _FILES, _AT)

    assert client.sent == [], "a never-opted-in project must issue no LocalCommit request"
    assert load_sync_state(project).pending_local_commits == [], (
        "the frame must not be staged either: the connect-time flush replays "
        "whatever is on disk"
    )
    state_file = project / ".kittify" / "sync-state.json"
    if state_file.exists():
        assert _MISSION_ID not in state_file.read_text(encoding="utf-8"), (
            "the mission slug is the leaked datum; it must not reach disk"
        )


def test_explicitly_opted_out_checkout_writes_no_frame(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A recorded refusal denies as firmly as an absent record."""
    project = _checkout(tmp_path, "acme", uuid=UUID_A, consents=False)
    client = _RecordingClient()
    monkeypatch.setattr(
        "specify_cli.sync.local_commit._get_saas_client", lambda: client
    )

    emit_local_commit(project, _HASH_A, _MISSION_ID, _BUILD_ID, _FILES, _AT)

    assert client.sent == []
    assert load_sync_state(project).pending_local_commits == []


def test_consenting_checkout_stages_frame_carrying_its_project_uuid(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The gate must not break the feature — and the frame must become self-describing.

    ``build_id`` is a one-way uuid5 of ``(project_uuid, node_id)`` and falls back to
    a random uuid4 when identity is incomplete, and ``mission_id`` is a repo-local
    slug. Neither can be resolved back to a project, so the frame carries
    ``project_uuid`` explicitly: without it the flush has no identity of its own to
    consult and is forced back onto cwd.
    """
    project = _checkout(tmp_path, "acme", uuid=UUID_A, consents=True)
    monkeypatch.setattr(
        "specify_cli.sync.local_commit._get_saas_client", lambda: None
    )

    emit_local_commit(project, _HASH_A, _MISSION_ID, _BUILD_ID, _FILES, _AT)

    pending = load_sync_state(project).pending_local_commits
    assert len(pending) == 1
    assert pending[0]["project_uuid"] == UUID_A


# ---------------------------------------------------------------------------
# Flush — the live path
# ---------------------------------------------------------------------------


def test_flush_refuses_frame_for_non_consenting_project(tmp_path: Path) -> None:
    """A frame already on disk for a non-consenting project is never replayed."""
    project = _checkout(tmp_path, "acme", uuid=UUID_A, consents=None)
    save_sync_state(project, SyncState(pending_local_commits=[_frame(project_uuid=UUID_A)]))
    client = _RecordingClient()

    flush_pending_local_commits(project, client)

    assert client.sent == []


def test_flush_refuses_frame_after_consent_is_revoked(tmp_path: Path) -> None:
    """Consent is re-resolved per flush, not baked in when the frame was staged.

    A project that consented, emitted, then opted out must not have its backlog
    shipped by the next connect. This is why the flush re-checks rather than
    trusting that a staged frame was once authorized.
    """
    project = _checkout(tmp_path, "acme", uuid=UUID_A, consents=True)
    save_sync_state(project, SyncState(pending_local_commits=[_frame(project_uuid=UUID_A)]))
    _checkout(tmp_path, "acme", uuid=UUID_A, consents=False)
    client = _RecordingClient()

    flush_pending_local_commits(project, client)

    assert client.sent == []
    assert len(load_sync_state(project).pending_local_commits) == 1, (
        "retained-and-ignored: a revoked project's backlog stays as evidence"
    )


def test_flush_refuses_frame_whose_own_project_denies_even_when_cwd_consents(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """**The test that makes the fix real.**

    ``flush_pending_local_commits`` runs against ``Path.cwd()``. A frame belonging
    to non-consenting project A is staged in the state file the flush reads while
    the operator stands in consenting project B. An implementation that resolves
    consent from cwd sees B's grant and posts A's mission slug; one that resolves
    from the frame's own ``project_uuid`` refuses.
    """
    project_a = _checkout(tmp_path, "acme", uuid=UUID_A, consents=None)
    project_b = _checkout(tmp_path, "public-oss", uuid=UUID_B, consents=True)
    # A's frame, staged in the state file the flush will actually read.
    save_sync_state(project_b, SyncState(pending_local_commits=[_frame(project_uuid=UUID_A)]))
    assert project_a.exists()  # A exists and denies; it is simply not where cwd is

    monkeypatch.chdir(project_b)
    client = _RecordingClient()

    flush_pending_local_commits(Path.cwd(), client)

    assert client.sent == [], (
        "consent was resolved from the working directory, not from the frame's "
        "own project: project A's mission slug was posted under project B's grant"
    )


def test_flush_sends_frame_whose_own_project_consents_even_when_cwd_denies(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The converse, so blanket-deny cannot pass for a fix.

    Project A consents (recorded in the uuid-keyed index, since A's own checkout is
    not the one cwd offers); the operator stands in opted-out project B. A's frame
    must still ship: the decision belongs to the frame's project in both
    directions, and a gate that only ever refuses would silently retire the
    feature instead of securing it.
    """
    _checkout(tmp_path, "public-oss", uuid=UUID_B, consents=False)
    project_b = tmp_path / "public-oss"
    _index(**{UUID_A: True})
    save_sync_state(project_b, SyncState(pending_local_commits=[_frame(project_uuid=UUID_A)]))

    monkeypatch.chdir(project_b)
    client = _RecordingClient()

    flush_pending_local_commits(Path.cwd(), client)

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

    assert [f["git_hash"] for f in client.sent] == [_HASH_B], (
        "an unidentifiable frame is not consentable even from a consenting checkout"
    )
    on_disk = json.loads(
        (project / ".kittify" / "sync-state.json").read_text(encoding="utf-8")
    )
    assert len(on_disk["pending_local_commits"]) == 2, (
        "retained, not purged: WP08 owns the operator's purge path"
    )


def test_flush_of_blank_project_uuid_is_refused(tmp_path: Path) -> None:
    """A blank uuid is absence, not a groupable key (NFR-001's ``None ∉ delivered``)."""
    project = _checkout(tmp_path, "acme", uuid=UUID_A, consents=True)
    save_sync_state(project, SyncState(pending_local_commits=[_frame(project_uuid="   ")]))
    client = _RecordingClient()

    flush_pending_local_commits(project, client)

    assert client.sent == []
