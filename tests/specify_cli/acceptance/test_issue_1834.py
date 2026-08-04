"""Regression for issue #1834 — accept overwrites recorded negative-invariant
results by re-verifying against the PRE-MERGE primary tree.

``spec-kitty accept`` runs the acceptance-matrix gate. Its
``_evaluate_acceptance_matrix`` step re-executes every negative invariant's
``verification_command`` from the **primary repo root** and **overwrites** the
recorded ``result`` in ``acceptance-matrix.json``.

Pre-merge, the primary tree cannot contain the mission's changes (they live on
lane branches until ``spec-kitty merge``). So an honest ``custom_command``
invariant — e.g. a test suite the mission ADDS — was recorded
``confirmed_absent`` (verified green on the integrated lane tree during per-WP
review), yet re-running it against the primary tree fails (the added file/test
is not there yet), flips the recorded result to ``still_present``, and the
matrix verdict computes ``fail``. Acceptance blocks even though the invariant
was genuinely satisfied on the integrated tree.

This test reproduces the clobber through the real acceptance-gate code path
(``_evaluate_acceptance_matrix``) and pins the fix: a recorded, non-pending
negative-invariant result must not be silently overwritten with a wrong result
derived solely from the pre-merge primary tree.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from specify_cli.acceptance.gates_core import (
    AcceptanceCheckDiagnostic,
    _evaluate_acceptance_matrix,
)
from specify_cli.acceptance.matrix import (
    AcceptanceCriterion,
    AcceptanceMatrix,
    NegativeInvariant,
    read_acceptance_matrix,
    write_acceptance_matrix,
)

pytestmark = pytest.mark.regression


@pytest.mark.skipif(sys.platform == "win32", reason="uses POSIX `test -f` custom_command")
def test_accept_does_not_overwrite_recorded_invariant_against_premerge_tree(
    tmp_path: Path,
) -> None:
    """NOTE:
    RED-FIRST P0 reproduction of #1834 per ADR 2026-07-17-1
    (docs/adr/3.x/2026-07-17-1-red-main-is-honest-ci-is-release-authority.md).
    Intentionally FAILS until the product bug is fixed — a red mainline is the honest
    signal of this release-blocking P0. Do NOT xfail/skip/quarantine to green; fix the
    product. Tracking issue: #1834.
    """
    # ``repo_root`` stands in for the PRE-MERGE primary tree: the mission's
    # changes (the added test suite) are NOT present here — they live on the
    # lane branch until ``spec-kitty merge``.
    repo_root = tmp_path
    mission_slug = "regression-1834"
    feature_dir = repo_root / "kitty-specs" / mission_slug
    feature_dir.mkdir(parents=True, exist_ok=True)

    # An honest, verifiable-by-command negative invariant: the mission adds a
    # protection test suite, and the invariant asserts "no protection
    # regression" by running it. On the integrated lane tree this passed, so the
    # gate recorded ``confirmed_absent`` during per-WP review.
    recorded = NegativeInvariant(
        invariant_id="NI-01",
        description="mission-added protection suite passes (no protection regression)",
        verification_method="custom_command",
        # Runs from ``repo_root``; the mission-added file is absent pre-merge, so
        # ``test -f`` exits non-zero -> the re-run computes ``still_present``.
        verification_command="test -f protection_added_by_mission.txt",
        result="confirmed_absent",
        evidence="Verified green on the integrated lane tree during WP review",
    )
    matrix = AcceptanceMatrix(
        mission_slug=mission_slug,
        criteria=[
            AcceptanceCriterion(
                criterion_id="AC-01",
                description="protection preserved",
                proof_type="negative_invariant",
                pass_fail="pass",
            )
        ],
        negative_invariants=[recorded],
    )
    write_acceptance_matrix(feature_dir, matrix)

    activity_issues: list[str] = []
    skipped_checks: list[AcceptanceCheckDiagnostic] = []
    blocked_checks: list[AcceptanceCheckDiagnostic] = []

    _evaluate_acceptance_matrix(
        repo_root,
        feature_dir,
        activity_issues,
        skipped_checks,
        blocked_checks,
        mutate_matrix=True,
    )

    persisted = read_acceptance_matrix(feature_dir)
    assert persisted is not None
    persisted_result = persisted.negative_invariants[0].result

    # The recorded, non-pending result must survive: accept must NOT overwrite a
    # verified ``confirmed_absent`` with ``still_present`` merely because the
    # pre-merge primary tree lacks the mission's changes. On buggy main the
    # re-run against ``repo_root`` clobbers it to ``still_present`` and the
    # verdict flips to ``fail`` — this assertion witnesses that overwrite.
    assert persisted_result == "confirmed_absent", (
        "accept overwrote the recorded negative-invariant result by re-verifying "
        f"against the pre-merge primary tree: recorded 'confirmed_absent' -> {persisted_result!r}"
    )
    assert persisted.overall_verdict != "fail"
