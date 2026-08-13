"""T050/WP11 contract pins: CLI outbound wire shapes vs the canonical SaaS contract.

Two halves, both fail-closed:

1. **Candidate attestation** (``saas_client.admission.attest_saas_contract`` /
   ``PINNED_SAAS_WP04_CONTRACT``): the CLI accepts a SaaS candidate only as an
   explicit checkout path + expected commit + expected SHA-256 of the generated
   ``contracts/cli-saas-current-api.yaml``. Any drift — digest, HEAD, dirtiness,
   a missing contract file, a wrong producer gate — must refuse with
   ``ContractAttestationError``, never degrade to a floating ref. Digests in the
   live test are computed from the explicit sibling candidate checkout's real
   bytes at runtime, never hardcoded from memory.

2. **Batch-event envelope**: the per-event wire object the real dispatcher
   produces must carry every contract-required envelope field. The required
   field set is reused from ``tests/delivery/test_envelope.py`` (the P1 #2131
   regression pin) rather than redeclared, so the two tests can never pin
   different contracts. On top of the envelope, the #3030 admission proof
   fields (``project_uuid``/``admission_generation``/``binding_audience``) and
   the WP06 delivery identity must ride every event.
"""

from __future__ import annotations

import gzip
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

import pytest

from specify_cli.delivery.dispatcher import dispatch
from specify_cli.delivery.receivers import StubReceiver, _build_payload
from specify_cli.delivery.targets import ProjectDeliveryTargetRegistry
from specify_cli.event_journal.journal import EventJournal
from specify_cli.event_journal.models import Event
from specify_cli.migration.envelope_seam import build_teamspace_envelope
from specify_cli.saas_client.admission import (
    PINNED_SAAS_WP04_CONTRACT,
    ContractAttestationError,
    attest_saas_contract,
)
from specify_cli.sync.consent import record_project_opt_in
from specify_cli.sync.layout_generation import LayoutMode
from specify_cli.sync.project_store import ProjectSyncStore
from tests.delivery.test_envelope import _REQUIRED_ENVELOPE_FIELDS

pytestmark = [pytest.mark.contract, pytest.mark.fast]

#: Explicit, named candidate checkout (never ambient ``../spec-kitty-saas``
#: discovery): the WP11 SaaS candidate this mission run pairs with. The live
#: attestation test below is skipped when the checkout is not retained.
SAAS_CANDIDATE_CHECKOUT = Path("/Users/robert/spec-kitty-dev/repos_2026-08-12_21-41-32/spec-kitty-saas")

_CONTRACT_RELPATH = Path("contracts") / "cli-saas-current-api.yaml"

#: #3030/WP06 fields the dispatcher must add on top of the emitted envelope:
#: the admission proof triple plus the wire type and the SaaS-native delivery
#: identity used for idempotent result correlation.
_REQUIRED_PROOF_FIELDS = frozenset(
    {
        "project_uuid",
        "admission_generation",
        "binding_audience",
        "type",
        "spec_kitty_delivery_identity",
    }
)

PROJECT_UUID = "aaaaaaaa-0000-0000-0000-00000000000a"
EVENT_ID = "01WP11CONTRACTENVELOPE0001"
_ACTOR = "cli-saas-contract-pin"


def _flip_last_hex_char(digest: str) -> str:
    last = digest[-1]
    return digest[:-1] + ("0" if last != "0" else "1")


def _git(checkout: Path, *arguments: str) -> str:
    return subprocess.run(
        ("git", "-C", str(checkout), *arguments),
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _hermetic_candidate(tmp_path: Path) -> tuple[Path, str, str]:
    """A clean throwaway git checkout carrying one generated contract file."""
    checkout = tmp_path / "candidate"
    checkout.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=checkout, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.test"], cwd=checkout, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=checkout, check=True)
    contract = checkout / _CONTRACT_RELPATH
    contract.parent.mkdir()
    contract.write_text("openapi: 3.1.0\n", encoding="utf-8")
    subprocess.run(["git", "add", str(_CONTRACT_RELPATH)], cwd=checkout, check=True)
    subprocess.run(["git", "commit", "-qm", "candidate"], cwd=checkout, check=True)
    commit = _git(checkout, "rev-parse", "HEAD")
    digest = hashlib.sha256(contract.read_bytes()).hexdigest()  # noqa: TID251 - canonical contract file-integrity digest
    return checkout, commit, digest


def test_pinned_wp04_authority_is_an_exact_commit_and_digest_not_a_ref() -> None:
    """The pin names one commit and one digest — nothing floating, no branch."""
    assert PINNED_SAAS_WP04_CONTRACT.producer_gate == "SaaS WP04"
    assert len(PINNED_SAAS_WP04_CONTRACT.commit) == 40
    assert set(PINNED_SAAS_WP04_CONTRACT.commit) <= set("0123456789abcdef")
    assert len(PINNED_SAAS_WP04_CONTRACT.sha256) == 64
    assert set(PINNED_SAAS_WP04_CONTRACT.sha256) <= set("0123456789abcdef")


def test_attestation_fail_closes_on_every_drift_dimension(tmp_path: Path) -> None:
    checkout, commit, digest = _hermetic_candidate(tmp_path)

    # The clean, exact candidate attests.
    attestation = attest_saas_contract(
        checkout_path=checkout,
        expected_commit=commit,
        expected_sha256=digest,
        producer_gate="SaaS WP04",
    )
    assert attestation.commit == commit
    assert attestation.sha256 == digest

    # Digest drift refuses — the central fail-closed property of the pin.
    with pytest.raises(ContractAttestationError, match="digest differs"):
        attest_saas_contract(
            checkout_path=checkout,
            expected_commit=commit,
            expected_sha256=_flip_last_hex_char(digest),
            producer_gate="SaaS WP04",
        )

    # A wrong commit refuses (no attesting whatever HEAD happens to be).
    with pytest.raises(ContractAttestationError, match="HEAD differs"):
        attest_saas_contract(
            checkout_path=checkout,
            expected_commit="0" * 40,
            expected_sha256=digest,
            producer_gate="SaaS WP04",
        )

    # A wrong producer gate refuses (the contract is SaaS WP04's, nobody else's).
    with pytest.raises(ContractAttestationError, match="SaaS WP04"):
        attest_saas_contract(
            checkout_path=checkout,
            expected_commit=commit,
            expected_sha256=digest,
            producer_gate="SaaS WP99",
        )

    # A dirty candidate refuses even when HEAD and digest still match.
    marker = checkout / "untracked-drift.txt"
    marker.write_text("drift\n", encoding="utf-8")
    with pytest.raises(ContractAttestationError, match="dirty"):
        attest_saas_contract(
            checkout_path=checkout,
            expected_commit=commit,
            expected_sha256=digest,
            producer_gate="SaaS WP04",
        )
    marker.unlink()

    # A missing generated contract refuses (never "attest what exists").
    (checkout / _CONTRACT_RELPATH).unlink()
    subprocess.run(["git", "add", "-u"], cwd=checkout, check=True)
    subprocess.run(["git", "commit", "-qm", "drop contract"], cwd=checkout, check=True)
    with pytest.raises(ContractAttestationError, match="missing"):
        attest_saas_contract(
            checkout_path=checkout,
            expected_commit=_git(checkout, "rev-parse", "HEAD"),
            expected_sha256=digest,
            producer_gate="SaaS WP04",
        )


@pytest.mark.skipif(
    not (SAAS_CANDIDATE_CHECKOUT / _CONTRACT_RELPATH).is_file(),
    reason="explicit SaaS candidate checkout not retained on this machine",
)
def test_explicit_saas_candidate_attests_from_real_bytes_and_fail_closes_on_drift() -> None:
    """Digest and HEAD are computed from the candidate's real files at runtime."""
    if _git(SAAS_CANDIDATE_CHECKOUT, "status", "--porcelain"):
        pytest.skip("explicit SaaS candidate checkout is dirty; attestation would (correctly) refuse")
    actual_commit = _git(SAAS_CANDIDATE_CHECKOUT, "rev-parse", "HEAD")
    contract_bytes = (SAAS_CANDIDATE_CHECKOUT / _CONTRACT_RELPATH).read_bytes()
    actual_digest = hashlib.sha256(contract_bytes).hexdigest()  # noqa: TID251 - canonical contract file-integrity digest

    attestation = attest_saas_contract(
        checkout_path=SAAS_CANDIDATE_CHECKOUT,
        expected_commit=actual_commit,
        expected_sha256=actual_digest,
        producer_gate="SaaS WP04",
    )
    assert attestation.commit == actual_commit
    assert attestation.sha256 == actual_digest
    assert attestation.checkout_label == SAAS_CANDIDATE_CHECKOUT.name

    # One flipped hex character in the expected digest must refuse: the pin
    # mechanism is byte-exact, not advisory.
    with pytest.raises(ContractAttestationError, match="digest differs"):
        attest_saas_contract(
            checkout_path=SAAS_CANDIDATE_CHECKOUT,
            expected_commit=actual_commit,
            expected_sha256=_flip_last_hex_char(actual_digest),
            producer_gate="SaaS WP04",
        )
    with pytest.raises(ContractAttestationError, match="HEAD differs"):
        attest_saas_contract(
            checkout_path=SAAS_CANDIDATE_CHECKOUT,
            expected_commit="f" * 40,
            expected_sha256=actual_digest,
            producer_gate="SaaS WP04",
        )


def _contract_envelope() -> dict[str, Any]:
    """A real teamspace envelope, built by the production envelope seam."""
    envelope: dict[str, Any] = build_teamspace_envelope(
        event_id=EVENT_ID,
        event_type="WPStatusChanged",
        aggregate_id="WP11",
        aggregate_type="WorkPackage",
        build_id="build-wp11",
        payload={
            "wp_id": "WP11",
            "from_lane": "in_progress",
            "to_lane": "for_review",
            "actor": _ACTOR,
        },
        node_id="node-wp11",
        lamport_clock=1,
        causation_id=None,
        correlation_id=EVENT_ID,
        timestamp="2026-08-12T00:00:00+00:00",
        project_uuid=PROJECT_UUID,
        project_slug="wp11-contract",
        repo_slug="private/wp11",
    ).model_dump()
    return envelope


def test_dispatcher_batch_event_carries_every_contract_required_field(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """capture -> dispatch -> receiver yields the full contract wire envelope."""
    home = tmp_path / "home"
    home.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("SPEC_KITTY_HOME", str(home))
    monkeypatch.setenv("SPEC_KITTY_ENABLE_SAAS_SYNC", "1")

    store = ProjectSyncStore(PROJECT_UUID)
    authority = store.layout_generation()
    if authority.read_state().mode is LayoutMode.LEGACY:
        authority.begin_cutover(_ACTOR)
        authority.publish_project_only(_ACTOR, verify_exact=lambda: True)
    record_project_opt_in(PROJECT_UUID, actor=_ACTOR)
    with store.unit_of_work() as unit:
        unit.execute(
            "INSERT INTO project_target_admissions "
            "(project_uuid, target_identity, account_identity, private_teamspace_id, "
            "configuration_generation, admission_state, admission_generation, binding_audience) "
            "VALUES (?, 'https://hosted.example.com', 'operator@example.com', 'team', 1, "
            "'admitted', '1', 'private-teamspace:team')",
            (PROJECT_UUID,),
        )

    envelope = _contract_envelope()
    with store.unit_of_work() as unit:
        journal = EventJournal(unit, authority)
        journal.append(
            Event(
                event_id=EVENT_ID,
                event_type="WPStatusChanged",
                payload=json.dumps(envelope).encode("utf-8"),
                occurred_at="2026-08-12T00:00:00+00:00",
                created_at="2026-08-12T00:00:00+00:00",
                project_uuid=PROJECT_UUID,
            )
        )
        target = ProjectDeliveryTargetRegistry(store).get_current(unit)
    assert target is not None

    receiver = StubReceiver()
    summary = dispatch(store=store, receiver=receiver, target=target, context=store.create_context())
    assert summary.selected == 1
    assert summary.delivered == 1

    received = receiver.received_events()
    assert len(received) == 1
    wire = dict(received[0].payload)

    missing_envelope = _REQUIRED_ENVELOPE_FIELDS - wire.keys()
    assert not missing_envelope, f"wire event missing contract envelope fields: {sorted(missing_envelope)}"
    missing_proof = _REQUIRED_PROOF_FIELDS - wire.keys()
    assert not missing_proof, f"wire event missing admission-proof fields: {sorted(missing_proof)}"

    # The values are the envelope's and the admitted authority's — not defaults.
    assert wire["event_id"] == EVENT_ID
    assert wire["event_type"] == "WPStatusChanged"
    assert wire["aggregate_id"] == "WP11"
    assert wire["payload"] == envelope["payload"]
    assert wire["type"] == "event"
    assert wire["spec_kitty_delivery_identity"] == EVENT_ID
    assert wire["project_uuid"] == PROJECT_UUID
    assert wire["admission_generation"] == 1
    assert wire["binding_audience"] == "private-teamspace:team"

    # And the serialized batch body — the exact bytes an HTTP receiver would
    # gzip and POST — carries the same complete per-event object (§3.1).
    body = json.loads(gzip.decompress(gzip.compress(_build_payload(received))).decode("utf-8"))
    event_body = body["events"][0]
    assert (_REQUIRED_ENVELOPE_FIELDS | _REQUIRED_PROOF_FIELDS).issubset(event_body.keys())
    assert event_body["payload"] == envelope["payload"]
