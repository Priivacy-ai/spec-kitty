"""Integration: downstream-consumer verification gates stable promotion (FR-026).

WP05 of mission ``stability-and-hygiene-hardening-2026-04-01KQ4ARB``
implements FR-026 by requiring that no candidate release of a cross-repo
package is promoted to stable until at least one downstream consumer has
verified compatibility against it.

The contract surface is twofold:

1. The release workflow (``.github/workflows/release.yml``) declares a
   ``downstream-consumer-verify`` job and the ``promote`` / publish
   stage's ``needs:`` graph includes it. This test parses the workflow
   YAML and asserts both the job's existence and the dependency edge.

2. A local verification artifact at
   ``.kittify/release/downstream-verified.json`` records evidence from
   the verify run. The test exercises a small helper that refuses to
   "promote" without that artifact, mirroring the behavior the workflow
   enforces.

Retired (planning#57): the 4 LIVE checks formerly in section 1 above
(``test_release_workflow_declares_downstream_consumer_verify_job``,
``test_release_workflow_promote_needs_downstream_consumer_verify``,
``test_release_workflow_verify_job_runs_downstream_scenario``,
``test_release_workflow_verify_job_uploads_artifact``, plus the
``_load_yaml_text`` helper and ``_RELEASE_WORKFLOW`` constant) asserted the
workflow-side half of FR-026 against the real
``.github/workflows/release.yml`` — the leftover pre-programme GitHub
Actions YAML deleted per PROGRAM.md §2. With no workflow YAML left to parse,
that half has no remaining subject matter and was removed with the file.
Section 2's local promotion-refusal contract never read a workflow file and
stays as the authoritative FR-026 guard on the artifact-gate behavior.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

pytestmark = [pytest.mark.integration]


_REPO_ROOT = Path(__file__).resolve().parents[2]
_VERIFICATION_ARTIFACT = (
    _REPO_ROOT / ".kittify" / "release" / "downstream-verified.json"
)


# ---------------------------------------------------------------------------
# Local promotion-refusal logic: mirror the workflow's gate behavior.
# ---------------------------------------------------------------------------


class _PromotionBlocked(Exception):
    """Raised when promotion is refused for missing downstream verification."""


def _promote_if_verified(artifact_path: Path) -> dict:
    """Refuse to promote unless an up-to-date verification artifact exists.

    This is the contract a release script (or operator) must satisfy. It
    deliberately does not network or shell out -- the workflow's
    ``downstream-consumer-verify`` job is the entity that materializes the
    artifact; this helper only enforces "no artifact, no promotion".
    """
    if not artifact_path.is_file():
        raise _PromotionBlocked(
            f"No downstream verification artifact at {artifact_path}. FR-026 "
            "requires a green downstream-consumer-verify run before stable "
            "promotion."
        )
    payload = json.loads(artifact_path.read_text(encoding="utf-8"))
    if payload.get("status") != "passed":
        raise _PromotionBlocked(
            f"Downstream verification artifact at {artifact_path} reports "
            f"status={payload.get('status')!r}; promotion blocked."
        )
    if not payload.get("candidate_version"):
        raise _PromotionBlocked(
            f"Downstream verification artifact at {artifact_path} is missing "
            "a candidate_version field; cannot trust the evidence."
        )
    return payload


def test_promotion_blocked_without_artifact(tmp_path: Path) -> None:
    """Promotion attempts MUST refuse when no verification artifact exists."""
    missing = tmp_path / "downstream-verified.json"
    with pytest.raises(_PromotionBlocked, match="No downstream verification artifact"):
        _promote_if_verified(missing)


def test_promotion_blocked_when_artifact_reports_failure(tmp_path: Path) -> None:
    """Promotion attempts MUST refuse when the artifact records a failure."""
    artifact = tmp_path / "downstream-verified.json"
    artifact.write_text(
        json.dumps(
            {
                "status": "failed",
                "candidate_version": "9.9.9-rc.1",
                "consumer": "spec-kitty-saas",
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(_PromotionBlocked, match="status='failed'"):
        _promote_if_verified(artifact)


def test_promotion_proceeds_with_passing_artifact(tmp_path: Path) -> None:
    """A complete, passing artifact unblocks promotion."""
    artifact = tmp_path / "downstream-verified.json"
    artifact.write_text(
        json.dumps(
            {
                "status": "passed",
                "candidate_version": "9.9.9-rc.1",
                "consumer": "spec-kitty-saas",
                "verified_at": "2026-04-26T12:00:00Z",
            }
        ),
        encoding="utf-8",
    )
    payload = _promote_if_verified(artifact)
    assert payload["candidate_version"] == "9.9.9-rc.1"
    assert payload["status"] == "passed"


def test_verification_artifact_path_is_documented_constant() -> None:
    """The verification-artifact path MUST live at the documented well-known path.

    Pinning the constant here means a future operator running the workflow
    locally cannot quietly land verification under a different filename.
    The workflow YAML and this constant must agree.
    """
    # We do not require the artifact to exist on disk; only that the path
    # constant matches the documented location.
    expected_relative = Path(".kittify") / "release" / "downstream-verified.json"
    actual_relative = _VERIFICATION_ARTIFACT.relative_to(_REPO_ROOT)
    assert actual_relative == expected_relative, (
        f"Verification artifact path drifted: expected {expected_relative}, "
        f"got {actual_relative}"
    )
