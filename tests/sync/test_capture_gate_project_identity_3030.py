"""M1: the capture gate must answer for the *event's* project, not for cwd.

``EventEmitter._capture_gate_state`` resolved ``checkout_enabled`` by calling
``is_sync_enabled_for_checkout()`` with **no argument** — i.e. against
``Path.cwd()`` — while the row it gates is stamped with the identity from
``_get_identity()``, which caches for the emitter's lifetime. In a short-lived CLI
process the two agree and nothing is observable. In the long-lived ``SyncRuntime``
emitter singleton an ``os.chdir`` decouples them, and the gate then answers project
B's question about project A's event.

The leaking direction is closed downstream: the drain's predicate keys on the
row's stored ``project_uuid``, so a row stamped A cannot ship on B's grant. The
damage runs the other way — **silent capture loss**:

* cwd in a *refusing* project while emitting for a *consenting* one drops the row
  entirely (capture-first refuses the write, #3030 T006), so the consenting
  operator's own event is gone with no diagnostic beyond a debug log; and
* even where the row survives, a cwd-derived gate stamps ``drain_blocked_reason``
  from cwd's answer. ``saas_disabled`` is **terminal** in
  ``delivery/selection.py``, so the row lands permanently unselectable — retained
  on disk, never deliverable, counted nowhere.

This is the same cwd-vs-identity defect T025 names for body uploads and T027 for
local-commit frames. Both of those were closed; the capture path was unowned.

Both directions are pinned below, so neither a cwd-derived implementation nor a
blanket-deny one can pass. Assertions are made against the **journal** — the
durable row is the artefact that decides deliverability — not against a predicate's
return value.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import pytest

from specify_cli.event_journal import DRAIN_BLOCKED_SAAS_DISABLED
from specify_cli.event_journal.journal import get_journal, reset_journal_cache

pytestmark = [pytest.mark.unit, pytest.mark.fast]

UUID_A = "aaaaaaaa-0000-0000-0000-00000000000a"
UUID_B = "bbbbbbbb-0000-0000-0000-00000000000b"


@pytest.fixture(autouse=True)
def _isolated_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Per-test consent index and journal home; the arming env var deleted.

    ``SPEC_KITTY_ENABLE_SAAS_SYNC`` is machine-global arming and never a grant
    (``consent.py`` level 3), so a developer's own export must not decide anything
    here. ``is_saas_sync_enabled`` is patched True instead, because a machine with
    SaaS sync off would stamp every row ``saas_disabled`` and the per-project
    question would never be reached.
    """
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / "home"))
    (tmp_path / "home").mkdir(parents=True, exist_ok=True)
    monkeypatch.delenv("SPEC_KITTY_ENABLE_SAAS_SYNC", raising=False)
    monkeypatch.setattr("specify_cli.sync.emitter.is_saas_sync_enabled", lambda: True)
    reset_journal_cache()
    yield
    reset_journal_cache()


def _checkout(tmp_path: Path, name: str, *, uuid: str, consents: bool | None) -> Path:
    """A checkout whose ``.kittify/config.yaml`` declares identity and consent.

    ``consents=None`` writes no ``sync`` section — the 2026-07-27 incident's actual
    state, and the one FR-002 requires to deny.
    """
    root = tmp_path / name
    (root / ".kittify").mkdir(parents=True, exist_ok=True)
    lines = ["project:", f"  uuid: {uuid}", f"  slug: {name}", "  node_id: 0123456789ab"]
    if consents is not None:
        lines += ["sync:", f"  enabled: {str(consents).lower()}"]
    (root / ".kittify" / "config.yaml").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return root


def _envelope(event_id: str, project_uuid: str | None) -> dict[str, Any]:
    """A wire envelope shaped like the one ``EventEmitter._emit`` assembles."""
    return {
        "event_id": event_id,
        "event_type": "WPStatusChanged",
        "aggregate_id": "wp-01",
        "aggregate_type": "WorkPackage",
        "schema_version": "3.0.0",
        "payload": {"status": "done"},
        "timestamp": "2026-07-30T07:00:00+00:00",
        "team_slug": None,
        "project_uuid": project_uuid,
        "project_slug": "some-slug",
    }


def _capture(envelope: dict[str, Any]) -> None:
    """Drive the real capture path for *envelope* from the current cwd."""
    from specify_cli.sync.emitter import EventEmitter

    EventEmitter()._capture_to_journal(
        event_id=str(envelope["event_id"]),
        event_type=str(envelope["event_type"]),
        event=envelope,
        occurred_at=str(envelope["timestamp"]),
        team_slug=None,
    )


def _captured_rows() -> dict[str, Any]:
    return {event.event_id: event for event in get_journal(team_slug=None).read_all()}


# --------------------------------------------------------------------------- #
# The red: cwd consents, the event's own project does not                       #
# --------------------------------------------------------------------------- #


def test_capture_refuses_an_event_whose_project_denies_while_cwd_consents(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Standing in a consenting project must not authorize another's capture.

    Project B consents in its own committed config; project A has no record
    anywhere. The emitter is standing in B and emitting for A. A cwd-derived gate
    reads B's ``sync.enabled: true`` and captures the row.
    """
    consenting_b = _checkout(tmp_path, "project-b", uuid=UUID_B, consents=True)
    monkeypatch.chdir(consenting_b)

    envelope = _envelope("evt-a-in-b", UUID_A)
    _capture(envelope)

    assert "evt-a-in-b" not in _captured_rows(), (
        "the capture gate answered cwd's question (project B consents) and wrote a "
        "row for project A, which has no consent record anywhere. The gate must be "
        "resolved from the event's own project_uuid — the identity the row is "
        "stamped with — not from the directory the process happens to be in"
    )


def test_the_stamped_reason_comes_from_the_events_project_not_cwds(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The audit column must not be poisoned by cwd either.

    A consenting project A emitted from within a *refusing* project B. If the gate
    is cwd-derived the row is stamped ``saas_disabled``, which
    ``delivery/selection.py`` classifies **terminal** — so the row is retained on
    disk and permanently unselectable. A stranded row is not a leak, and that is
    exactly why nothing else in the suite notices it.
    """
    from specify_cli.sync.consent import set_project_consent

    set_project_consent(UUID_A, True)
    refusing_b = _checkout(tmp_path, "project-b", uuid=UUID_B, consents=False)
    monkeypatch.chdir(refusing_b)

    envelope = _envelope("evt-a-from-refusing-b", UUID_A)
    _capture(envelope)

    rows = _captured_rows()
    assert "evt-a-from-refusing-b" in rows, (
        "project A consents, so its event must be captured no matter which "
        "directory the emitter is standing in"
    )
    assert rows["evt-a-from-refusing-b"].drain_blocked_reason != DRAIN_BLOCKED_SAAS_DISABLED, (
        "the row was stamped with cwd's refusal. saas_disabled is terminal in "
        "delivery/selection.py, so this row would be retained and never "
        "deliverable — silent capture loss, not a leak"
    )
    assert rows["evt-a-from-refusing-b"].project_uuid == UUID_A


# --------------------------------------------------------------------------- #
# The converse: a blanket-deny implementation must not pass either              #
# --------------------------------------------------------------------------- #


def test_capture_accepts_an_event_whose_own_project_consents_via_the_index(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The uuid-keyed index must still be able to grant, from outside any checkout.

    The daemon's usual case: no readable checkout for the project at all. Consent
    then comes from the machine-global index, which is the level that exists
    precisely because the drain sees only a ``project_uuid``.
    """
    from specify_cli.sync.consent import set_project_consent

    set_project_consent(UUID_A, True)
    outside = tmp_path / "not-a-project"
    outside.mkdir()
    monkeypatch.chdir(outside)
    monkeypatch.delenv("SPECIFY_REPO_ROOT", raising=False)

    _capture(_envelope("evt-a-outside", UUID_A))

    assert "evt-a-outside" in _captured_rows(), (
        "a project that consents in the uuid-keyed index must be capturable with no "
        "checkout available; a blanket deny would pass the refusal tests above "
        "while breaking every honest daemon capture"
    )


def test_the_projects_own_committed_refusal_still_outranks_the_index(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """FR-013: a refusal in the project's own config beats a stale index grant.

    Resolving the gate per project must go down ``sync/consent.py``'s one chain, not
    take a shortcut to the index. Standing in A's own checkout is what makes level 1
    reachable at all.
    """
    from specify_cli.sync.consent import set_project_consent

    set_project_consent(UUID_A, True)
    refusing_a = _checkout(tmp_path, "project-a", uuid=UUID_A, consents=False)
    monkeypatch.chdir(refusing_a)

    _capture(_envelope("evt-a-refused-locally", UUID_A))

    assert "evt-a-refused-locally" not in _captured_rows(), (
        "project A's own .kittify/config.yaml says sync.enabled: false; a refusal "
        "outranks the index grant (FR-013), so nothing may be captured"
    )


def test_an_event_with_no_resolvable_project_is_never_captured(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """NFR-001: not identifiable is not consentable, so it must not be stored.

    Such a row would land with ``project_uuid`` NULL, which the drain's SQL
    predicate can never match — retained forever, deliverable never. Refusing the
    write keeps an unconsentable payload out of the machine-global journal, which is
    the whole thesis of NFR-005 as amended.
    """
    consenting_b = _checkout(tmp_path, "project-b", uuid=UUID_B, consents=True)
    monkeypatch.chdir(consenting_b)

    _capture(_envelope("evt-no-identity", None))

    assert "evt-no-identity" not in _captured_rows(), (
        "an event carrying no resolvable project_uuid cannot be shown to belong to "
        "a consenting project, so it must not be written — not written and then "
        "stranded as an unmatched NULL row"
    )


# --------------------------------------------------------------------------- #
# The scenario the defect actually needs: one long-lived emitter, two projects  #
# --------------------------------------------------------------------------- #


def test_one_long_lived_emitter_gates_each_event_on_its_own_project(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The ``SyncRuntime`` singleton's shape: one emitter, cwd moved underneath it.

    ``_get_identity`` caches for the emitter's lifetime, so in a short-lived CLI
    process cwd and the stamped identity always agree and the defect is invisible.
    This is the process where they diverge.
    """
    from specify_cli.sync.consent import set_project_consent
    from specify_cli.sync.emitter import EventEmitter

    set_project_consent(UUID_A, True)  # A consents
    consenting_a = _checkout(tmp_path, "project-a", uuid=UUID_A, consents=True)
    refusing_b = _checkout(tmp_path, "project-b", uuid=UUID_B, consents=False)

    emitter = EventEmitter()
    original = Path(os.getcwd())
    try:
        for cwd in (consenting_a, refusing_b):
            os.chdir(cwd)
            for uuid, tag in ((UUID_A, "a"), (UUID_B, "b")):
                envelope = _envelope(f"evt-{tag}-from-{cwd.name}", uuid)
                emitter._capture_to_journal(
                    event_id=str(envelope["event_id"]),
                    event_type=str(envelope["event_type"]),
                    event=envelope,
                    occurred_at=str(envelope["timestamp"]),
                    team_slug=None,
                )
    finally:
        os.chdir(original)

    captured = set(_captured_rows())
    assert captured == {"evt-a-from-project-a", "evt-a-from-project-b"}, (
        "exactly the two project-A events must be captured, from either working "
        f"directory, and neither project-B event from either: {sorted(captured)}"
    )


def test_a_gate_read_failure_denies_rather_than_capturing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """FR-003's rule: inability to determine consent is not consent.

    This module's house style swallows gate errors and carries on, which is right
    for a git hook and wrong for a confidentiality boundary — there it converts an
    unanswerable question into a stored payload.
    """
    consenting_b = _checkout(tmp_path, "project-b", uuid=UUID_B, consents=True)
    monkeypatch.chdir(consenting_b)

    def _explode(*_args: object, **_kwargs: object) -> frozenset[str]:
        raise RuntimeError("consent index unreadable")

    monkeypatch.setattr(
        "specify_cli.sync.consent.consented_project_uuids", _explode
    )

    _capture(_envelope("evt-unanswerable", UUID_A))

    assert "evt-unanswerable" not in _captured_rows(), (
        "a consent read that raises must deny, not fall back to cwd or to a grant"
    )


def test_capture_writes_the_envelope_json_verbatim_for_a_consenting_project(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Guard the positive path's substance, not only the row's existence.

    The dispatcher decodes this BLOB verbatim and the receiver POSTs it, so a gate
    change that quietly altered what is stored would be a delivery bug the refusal
    tests above cannot see.
    """
    from specify_cli.sync.consent import set_project_consent

    set_project_consent(UUID_A, True)
    consenting_a = _checkout(tmp_path, "project-a", uuid=UUID_A, consents=True)
    monkeypatch.chdir(consenting_a)

    envelope = _envelope("evt-verbatim", UUID_A)
    _capture(envelope)

    row = _captured_rows()["evt-verbatim"]
    assert json.loads(row.payload.decode()) == envelope
    assert row.project_uuid == UUID_A
