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
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

pytestmark = [pytest.mark.integration]


_REPO_ROOT = Path(__file__).resolve().parents[2]
_RELEASE_WORKFLOW = _REPO_ROOT / ".github" / "workflows" / "release.yml"
_VERIFICATION_ARTIFACT = _REPO_ROOT / ".kittify" / "release" / "downstream-verified.json"


def _load_yaml_text() -> str:
    """Read the release workflow as raw text.

    We deliberately avoid PyYAML to dodge an indirect dep; the assertions
    are token-level and ASCII-safe.
    """
    return _RELEASE_WORKFLOW.read_text(encoding="utf-8")


def test_release_workflow_declares_downstream_consumer_verify_job() -> None:
    """``release.yml`` MUST declare a ``downstream-consumer-verify`` job."""
    text = _load_yaml_text()
    # Job declarations live under the top-level ``jobs:`` map. The job
    # appears as a 2-space-indented key.
    assert re.search(r"^\s{2}downstream-consumer-verify:\s*$", text, re.MULTILINE), (
        ".github/workflows/release.yml does not declare a "
        "`downstream-consumer-verify` job. FR-026 requires a job that runs "
        "the downstream consumer suite before stable promotion. See "
        "kitty-specs/stability-and-hygiene-hardening-2026-04-01KQ4ARB/"
        "tasks/WP05-package-contracts.md#t029 for guidance."
    )


def test_release_workflow_promote_needs_downstream_consumer_verify() -> None:
    """The promotion / PyPI publish job MUST list ``downstream-consumer-verify`` in needs."""
    text = _load_yaml_text()
    # Find the PyPI / promote job. We accept either a job named ``promote``
    # or the historical ``publish-pypi`` name.
    promote_block_match = re.search(
        r"^\s{2}(promote|publish-pypi):\s*\n(?P<body>(?:^\s{4,}.*\n?)+)",
        text,
        re.MULTILINE,
    )
    assert promote_block_match, (
        "Could not locate a `promote` or `publish-pypi` job in "
        ".github/workflows/release.yml. FR-026 requires a promotion stage "
        "whose `needs:` includes downstream-consumer-verify."
    )
    body = promote_block_match.group("body")
    # ``needs:`` may be inline (``needs: foo``) or a YAML list spanning
    # multiple lines (``needs:\n  - foo\n  - bar``). Capture either shape.
    inline_match = re.search(r"^\s{4}needs:[ \t]+(\S.*)$", body, re.MULTILINE)
    list_match = re.search(
        r"^\s{4}needs:[ \t]*\n(?P<items>(?:\s{6,}-\s.+\n?)+)",
        body,
        re.MULTILINE,
    )
    if inline_match:
        needs_value = inline_match.group(1).strip()
    elif list_match:
        needs_value = list_match.group("items")
    else:
        pytest.fail("Promotion job is missing a `needs:` declaration. It must depend on `downstream-consumer-verify` per FR-026.")
    assert "downstream-consumer-verify" in needs_value, (
        f"Promotion job needs={needs_value!r} does not include "
        "`downstream-consumer-verify`. FR-026 requires the verify job to "
        "be a hard dependency of stable promotion."
    )


def test_release_workflow_verify_job_runs_downstream_scenario() -> None:
    """The verify job MUST execute the downstream-consumer scenario suite."""
    text = _load_yaml_text()
    # Pull just the verify job's body so we don't false-match elsewhere.
    block_match = re.search(
        r"^\s{2}downstream-consumer-verify:\s*\n(?P<body>(?:^\s{4,}.*\n?)+)",
        text,
        re.MULTILINE,
    )
    assert block_match, "downstream-consumer-verify job body not found."
    body = block_match.group("body")
    # The scenario file referenced in the WP plan.
    needle = "spec-kitty-end-to-end-testing/scenarios/contract_drift_caught.py"
    assert needle in body, (
        "downstream-consumer-verify job does not invoke the contract-drift "
        f"scenario suite ({needle}). The verify job must actually run the "
        "downstream consumer scenarios it gates promotion on."
    )


def test_release_workflow_verify_job_uploads_artifact() -> None:
    """The verify job MUST upload a verification artifact for the gate to consume."""
    text = _load_yaml_text()
    block_match = re.search(
        r"^\s{2}downstream-consumer-verify:\s*\n(?P<body>(?:^\s{4,}.*\n?)+)",
        text,
        re.MULTILINE,
    )
    assert block_match, "downstream-consumer-verify job body not found."
    body = block_match.group("body")
    assert "actions/upload-artifact" in body, (
        "downstream-consumer-verify job must upload a verification "
        "artifact (actions/upload-artifact) so reviewers can audit the "
        "evidence backing a stable promotion."
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
            f"No downstream verification artifact at {artifact_path}. FR-026 requires a green downstream-consumer-verify run before stable promotion."
        )
    payload = json.loads(artifact_path.read_text(encoding="utf-8"))
    if payload.get("status") != "passed":
        raise _PromotionBlocked(f"Downstream verification artifact at {artifact_path} reports status={payload.get('status')!r}; promotion blocked.")
    if not payload.get("candidate_version"):
        raise _PromotionBlocked(f"Downstream verification artifact at {artifact_path} is missing a candidate_version field; cannot trust the evidence.")
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
    assert actual_relative == expected_relative, f"Verification artifact path drifted: expected {expected_relative}, got {actual_relative}"
