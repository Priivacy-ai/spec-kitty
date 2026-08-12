"""Explicit SaaS WP04 candidate attestation and authority tests."""

from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path

import pytest

from specify_cli.saas_client.admission import (
    ContractAttestationError,
    PINNED_SAAS_WP04_CONTRACT,
    attest_saas_contract,
)

pytestmark = [pytest.mark.contract, pytest.mark.fast]

CANDIDATE_CHECKOUT = Path("/private/var/folders/h5/zqph_vqs3_77ctcqwvr_1b6m0000gn/T/spec-kitty-20260809-175108-qc7maU/saas-wp04-candidate-29cc20c6")


def test_pinned_authority_identifies_saas_wp04_not_a_version_or_branch() -> None:
    assert PINNED_SAAS_WP04_CONTRACT.producer_gate == "SaaS WP04"
    assert PINNED_SAAS_WP04_CONTRACT.commit == "29cc20c6ca5d61784af6f8b973a36131e69103af"
    assert PINNED_SAAS_WP04_CONTRACT.sha256 == "fe3a9f8d2563e3a9df386cd911ea858fd6a48913eb14c5b39d579b26bf3a4b35"
    assert PINNED_SAAS_WP04_CONTRACT.checkout_label == "saas-wp04-candidate-29cc20c6"


@pytest.mark.skipif(not CANDIDATE_CHECKOUT.exists(), reason="mission candidate checkout retained only for review")
def test_explicit_saas_wp04_candidate_matches_pinned_head_and_digest() -> None:
    attestation = attest_saas_contract(
        checkout_path=CANDIDATE_CHECKOUT,
        expected_commit=PINNED_SAAS_WP04_CONTRACT.commit,
        expected_sha256=PINNED_SAAS_WP04_CONTRACT.sha256,
        producer_gate="SaaS WP04",
    )

    assert attestation == PINNED_SAAS_WP04_CONTRACT


def test_attestation_requires_exact_clean_checkout_and_canonical_contract(tmp_path: Path) -> None:
    checkout = tmp_path / "candidate"
    checkout.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=checkout, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.test"], cwd=checkout, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=checkout, check=True)
    contract = checkout / "contracts" / "cli-saas-current-api.yaml"
    contract.parent.mkdir()
    contract.write_text("openapi: 3.1.0\n", encoding="utf-8")
    subprocess.run(["git", "add", "contracts/cli-saas-current-api.yaml"], cwd=checkout, check=True)
    subprocess.run(["git", "commit", "-qm", "candidate"], cwd=checkout, check=True)
    commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=checkout, check=True, capture_output=True, text=True).stdout.strip()
    digest = hashlib.sha256(contract.read_bytes()).hexdigest()  # noqa: TID251 - canonical contract file-integrity digest

    attestation = attest_saas_contract(
        checkout_path=checkout,
        expected_commit=commit,
        expected_sha256=digest,
        producer_gate="SaaS WP04",
    )
    assert attestation.commit == commit

    contract.write_text("openapi: 3.1.1\n", encoding="utf-8")
    with pytest.raises(ContractAttestationError, match="dirty"):
        attest_saas_contract(
            checkout_path=checkout,
            expected_commit=commit,
            expected_sha256=digest,
            producer_gate="SaaS WP04",
        )
