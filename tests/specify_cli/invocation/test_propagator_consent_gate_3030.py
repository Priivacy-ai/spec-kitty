"""FR-025 (#3030) — the invocation propagator is a fourth egress path.

Measured leaking on 2026-07-30, with **no consent record anywhere** and through the
REAL sync-side registration (no stubbed resolver needed):

===========================================  ==============  ===================
case                                         envelopes sent  leaked
===========================================  ==============  ===================
``repo_root`` is not a project root          1               ``request_text``
consent chain raises (safe-degraded)         1               ``request_text``
project exists, never opted in               0               —
project consents                             1               (intended)
===========================================  ==============  ===================

``request_text`` is the verbatim agent prompt. The first two rows leaked because
``_propagate_one`` guarded with ``if sync_enabled is False: return`` while the seam
answered ``None`` for *both* "no resolver registered" and "the resolver raised" —
so "could not determine consent" was read as permission. It is FR-003's rule
("inability to determine consent is never read as consent") re-derived in a second
place, because FR-003 was fixed inside ``is_sync_enabled_for_checkout`` and this
path never called it.

Two properties every case here asserts, in this order:

1. **No envelope was transmitted** — the recording client's list is empty. A test
   asserting a boolean would pass on a gate that flipped a flag and sent anyway.
2. **The secret does not appear in anything transmitted** — searched over the
   serialised payload, not over one field, so a future envelope that carries the
   prompt under a different key still fails.

The consenting case is a **positive control** and must PASS: it is the only thing
that proves the harness can transmit at all. Without it, a broken fixture (an
unregistered client factory, a warnings-as-errors artifact inside ``_send_event``)
makes every refusal case pass while proving nothing.

Each case gets its own ``HOME`` with no machine-global sync config: the consent
resolver reconciles its index as a side effect, so a shared home lets one case's
grant answer another case's question.
"""

from __future__ import annotations

import json
import os
from collections.abc import Iterator
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

import pytest

from specify_cli.invocation.adapters import (
    register_saas_client_factory,
    reset_adapters,
)
from specify_cli.invocation.propagator import _propagate_one
from specify_cli.invocation.record import OpCompletedEvent, OpStartedEvent

pytestmark = [pytest.mark.unit, pytest.mark.fast]

#: Stands in for the confidential material the incident actually moved: the
#: envelope's ``request_text`` is the agent prompt, verbatim.
SECRET = "ACME Holdings carve-out: draft the disclosure schedule"


class _RecordingClient:
    """A connected SaaS client that records instead of transmitting.

    Registered through the real ``register_saas_client_factory`` seam rather than
    by patching ``propagator._get_saas_client``, so the only thing standing in for
    production is the transport itself — the decision point under test is
    untouched.
    """

    def __init__(self) -> None:
        self.sent: list[dict] = []

    async def send_event(self, event: dict) -> None:
        self.sent.append(event)

    @property
    def transmitted(self) -> str:
        """Everything that left, serialised — searched for the secret as a whole."""
        return json.dumps(self.sent, default=str)


@pytest.fixture()
def wiring(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[_RecordingClient]:
    """Production sync-side registration + a recording transport, on a fresh machine.

    ``register_default_handlers`` is called first and the recording factory second,
    so the client slot is overridden while the consent slot keeps the real resolver.
    """
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.delenv("SPEC_KITTY_HOME", raising=False)
    monkeypatch.delenv("SPECIFY_REPO_ROOT", raising=False)
    monkeypatch.delenv("SPEC_KITTY_ENABLE_SAAS_SYNC", raising=False)

    reset_adapters()
    os.environ["SPEC_KITTY_SYNC_MINIMAL_IMPORT"] = "1"
    try:
        from specify_cli.sync import register_default_handlers

        register_default_handlers()
        client = _RecordingClient()
        register_saas_client_factory(lambda _root: client)
        yield client
    finally:
        os.environ.pop("SPEC_KITTY_SYNC_MINIMAL_IMPORT", None)
        # Restore, do not merely clear. ``reset_adapters()`` alone leaves the
        # *process* with no consent resolver, and the registry is module-global —
        # so every later test file in the same session that expects the production
        # registration fails with "no hosted-sync consent resolver is registered".
        # That is a refusal, so the casualties are the positive controls of other
        # suites, which on a consent mission reads as a gate defect rather than as
        # fixture teardown order. Reproduced deterministically in alphabetical
        # order: this file runs before tests/specify_cli/saas_client/ and
        # tests/sync/tracker/, and took three of their transmit pins with it.
        reset_adapters()
        from specify_cli.sync import register_default_handlers as _restore_handlers

        _restore_handlers()


def _started_record() -> OpStartedEvent:
    """A task-execution ``started`` Op — the projection policy includes its body."""
    return OpStartedEvent(
        invocation_id="01HXYZABCDEFGH1JK2MN3PQRST",
        profile_id="implementer-ivan",
        action="implement",
        request_text=SECRET,
        actor="claude",
        mode_of_work="task_execution",
        governance_context_hash="abcdef0123456789",
        governance_context_available=True,
        started_at="2026-07-30T06:00:00Z",
    )


def _project(root: Path, *, sync_enabled: bool | None = None) -> tuple[Path, str]:
    """Write a complete project identity, optionally with an in-repo consent record.

    Returns the root and its ``project_uuid`` so a test can record consent against
    the uuid rather than against the path.
    """
    project_uuid = str(uuid4())
    config_dir = root / ".kittify"
    config_dir.mkdir(parents=True, exist_ok=True)
    lines = [
        "project:",
        f"  uuid: {project_uuid}",
        "  slug: engagement-assistant",
        "  node_id: node12345678",
        "  repo_slug: regnology-example/engagement-assistant",
        "  build_id: 8a4a7da6-a97c-4bb4-893a-b31664abfee4",
    ]
    if sync_enabled is not None:
        lines += ["sync:", f"  enabled: {str(sync_enabled).lower()}"]
    (config_dir / "config.yaml").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return root, project_uuid


# ---------------------------------------------------------------------------
# Positive control — must pass, or every refusal below proves nothing
# ---------------------------------------------------------------------------


def test_consenting_project_propagates_the_envelope(
    wiring: _RecordingClient, tmp_path: Path
) -> None:
    """POSITIVE CONTROL: an opted-in project's Op is transmitted, body included.

    Consent is recorded in the project's own ``.kittify/config.yaml`` — level 1 of
    the declared precedence chain. If this goes red, the harness cannot transmit
    and the refusal assertions in this module are vacuous.
    """
    root, _uuid = _project(tmp_path / "consenting")
    from specify_cli.sync.routing import enable_checkout_sync

    enable_checkout_sync(root, actor="propagator-positive-control")

    _propagate_one(_started_record(), root)

    # Cardinality is the contract, not a stand-in for one: one Op must yield exactly
    # one envelope. The refusal cases in this file assert ``sent == []``; this is
    # their counterpart, and it is also the only thing that would catch a
    # double-send. *Which* envelope left is pinned on the two lines below, so there
    # is no content this count is standing in for.
    assert len(wiring.sent) == 1, (  # golden-count: cardinality-is-contract
        "POSITIVE CONTROL BROKEN: a consenting project transmitted nothing, so "
        "every refusal case in this file is unfalsifiable"
    )
    assert wiring.sent[0]["request_text"] == SECRET
    assert wiring.sent[0]["event_type"] == "ProfileInvocationStarted"


def test_machine_index_grant_propagates_the_envelope(
    wiring: _RecordingClient, tmp_path: Path
) -> None:
    """Consent recorded against the project's UUID authorises egress.

    The discriminator between the two questions this gate could ask. The uuid-keyed
    machine index is level 2 of the consent chain, and checkout *routing* never
    reads it — ``effective_sync_enabled`` would default-deny here. So this case
    passes only while the gate resolves consent from the project's identity; revert
    the seam to a checkout-routing answer and it goes red.
    """
    root, project_uuid = _project(tmp_path / "index-granted")

    from specify_cli.sync.consent import record_project_opt_in

    record_project_opt_in(project_uuid, actor="propagator-explicit-opt-in")

    _propagate_one(_started_record(), root)

    # Same cardinality contract as the control above — one Op, one envelope, and a
    # duplicate send is a real failure this line is the only one that would see.
    # The envelope's content is pinned immediately below it.
    assert len(wiring.sent) == 1, (  # golden-count: cardinality-is-contract
        "a project whose UUID is recorded as consenting must be deliverable; "
        "the gate is answering a checkout question instead of a project one"
    )
    assert wiring.sent[0]["request_text"] == SECRET


# ---------------------------------------------------------------------------
# The measured leaks
# ---------------------------------------------------------------------------


def test_repo_root_outside_any_project_propagates_nothing(
    wiring: _RecordingClient, tmp_path: Path
) -> None:
    """MEASURED LEAK 1/2: reachable with no fault at all — 1 envelope before the fix.

    An Op whose ``repo_root`` does not resolve as a project root (``dispatch.py``
    takes it from ``find_repo_root()``, a git-root walk, while consent resolution
    needs a ``.kittify`` project root — the two disagree for any git checkout that
    is not a spec-kitty project). The consent chain cannot name a project, so there
    is no project that could have consented.
    """
    root = tmp_path / "git-repo-but-not-a-kittify-project"
    root.mkdir()

    _propagate_one(_started_record(), root)

    assert wiring.sent == [], f"LEAK: {wiring.transmitted}"
    assert SECRET not in wiring.transmitted


def test_faulting_consent_chain_propagates_nothing(
    wiring: _RecordingClient, tmp_path: Path
) -> None:
    """MEASURED LEAK 2/2: a resolver that RAISES must never end as egress.

    The raise is the shape FR-023 counted five times over — a structurally invalid
    ``config.yaml`` taking out a policy read that was supposed to answer a boolean.
    Patched at the routing entry point the resolver imports at call time, so the
    fault arrives from inside the real chain rather than from a stub standing in
    for it.
    """
    root, _uuid = _project(tmp_path / "faulting", sync_enabled=True)

    def _boom(_path: object = None) -> object:
        raise AttributeError("'CommentedSeq' object has no attribute 'get'")

    with patch(
        "specify_cli.sync.routing.resolve_checkout_sync_routing_readonly", _boom
    ):
        _propagate_one(_started_record(), root)

    assert wiring.sent == [], f"LEAK: {wiring.transmitted}"
    assert SECRET not in wiring.transmitted


def test_completed_event_with_faulting_chain_propagates_nothing(
    wiring: _RecordingClient, tmp_path: Path
) -> None:
    """Both event shapes pass the same gate.

    ``OpCompletedEvent`` carries ``evidence_ref`` rather than ``request_text`` and
    is built by a different envelope function, so it is asserted separately: one
    gate, two payload builders, and only the started one was measured.
    """
    root, _uuid = _project(tmp_path / "faulting-completed", sync_enabled=True)
    record = OpCompletedEvent(
        invocation_id="01HXYZABCDEFGH1JK2MN3PQRST",
        completed_at="2026-07-30T06:05:00Z",
        outcome="done",
        closed_by="agent",
        evidence_ref=SECRET,
    )

    def _boom(_path: object = None) -> object:
        raise AttributeError("'CommentedSeq' object has no attribute 'get'")

    with patch(
        "specify_cli.sync.routing.resolve_checkout_sync_routing_readonly", _boom
    ):
        _propagate_one(record, root)

    assert wiring.sent == [], f"LEAK: {wiring.transmitted}"
    assert SECRET not in wiring.transmitted


def test_unregistered_seam_propagates_nothing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """No consent resolver registered → refusal, even with a connected client.

    The other half of the retired ``None``. Production reaches this state only
    without the sync package (where there is no client either), but the registry is
    process-global and test-mutable, so the refusal is pinned rather than argued.
    """
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    (tmp_path / "home").mkdir()
    reset_adapters()
    client = _RecordingClient()
    register_saas_client_factory(lambda _root: client)
    try:
        root, _uuid = _project(tmp_path / "orphaned-registry", sync_enabled=True)

        _propagate_one(_started_record(), root)

        assert client.sent == [], f"LEAK: {client.transmitted}"
        assert SECRET not in client.transmitted
    finally:
        reset_adapters()


# ---------------------------------------------------------------------------
# Regression guards — these already held; they must keep holding
# ---------------------------------------------------------------------------


def test_never_opted_in_project_propagates_nothing(
    wiring: _RecordingClient, tmp_path: Path
) -> None:
    """The 2026-07-27 incident shape: a real project nobody ever opted in.

    Absence of a record is not consent (FR-002). Green before this fix and pinned
    so the new gate cannot regress it while closing the undetermined cases.
    """
    root, _uuid = _project(tmp_path / "never-opted-in")

    _propagate_one(_started_record(), root)

    assert wiring.sent == [], f"LEAK: {wiring.transmitted}"
    assert SECRET not in wiring.transmitted


def test_project_local_refusal_propagates_nothing(
    wiring: _RecordingClient, tmp_path: Path
) -> None:
    """An in-repo ``sync.enabled: false`` refuses — the one reviewable record."""
    root, _uuid = _project(tmp_path / "refusing", sync_enabled=False)

    _propagate_one(_started_record(), root)

    assert wiring.sent == [], f"LEAK: {wiring.transmitted}"
    assert SECRET not in wiring.transmitted
