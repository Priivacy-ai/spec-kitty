"""Behavioural contract for WP04 — negative-invariant provenance & deferral.

Pins contract ``negative-invariant-provenance.md`` C1–C5, C8, C9 and data-model
``NegativeInvariant`` NI-1..NI-5 / the fourth ``overall_verdict`` value.

These are pure-unit + filesystem/``grep`` tests: a :class:`GateExecutionContext`
is constructed directly (a frozen value object — no git required) and negative
invariants are judged against a real temp tree. No git shelling occurs, so the
suite carries only the ``integration`` marker (real subprocess ``grep`` +
filesystem), not ``git_repo``.

Fixtures use production-shaped identifiers (a real mission slug with its ULID
suffix, 40-hex refs, real ``TopologySurface`` values) rather than toy
placeholders, so a shape assumption that would break on real data breaks here.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from mission_runtime import TopologySurface
from specify_cli.acceptance.execution_context import (
    GateExecutionContext,
    LifecyclePhase,
)
from specify_cli.acceptance.matrix import (
    DEFERRED_TO_CONSOLIDATION,
    PROVENANCE_LEGACY_UNRECORDED,
    PROVENANCE_RECORDED,
    TERMINAL_INVARIANT_RESULTS,
    VERDICT_PASS_PENDING_CONSOLIDATION,
    AcceptanceCriterion,
    AcceptanceMatrix,
    NegativeInvariant,
    enforce_negative_invariants,
    scaffold_acceptance_matrix,
    validate_matrix_evidence,
)

pytestmark = pytest.mark.integration

# Production-shaped fixtures — a real mission slug and 40-hex refs, not toy ids.
MISSION_SLUG = "lifecycle-gate-execution-context-01KY72GQ"
PRIMARY_REF = "9f2c1a7e4b3d0a6f8c2e1d5b7a9040f3e6c8b1d2"
CONSOLIDATED_REF = "1a2b3c4d5e6f7081920a3b4c5d6e7f8091a2b3c4"


def _context(
    surface: Path,
    *,
    surface_kind: TopologySurface = TopologySurface.PRIMARY,
    ref: str = PRIMARY_REF,
    phase: LifecyclePhase = LifecyclePhase.ACCEPT,
) -> GateExecutionContext:
    """A gate context bound to *surface* — constructed directly, no git needed."""
    return GateExecutionContext(
        surface=surface,
        surface_kind=surface_kind,
        ref=ref,
        phase=phase,
        mission_slug=MISSION_SLUG,
    )


# ---------------------------------------------------------------------------
# T020 / C2 — provenance round-trip
# ---------------------------------------------------------------------------


def test_provenance_fields_round_trip() -> None:
    """C2: every provenance field survives a ``to_dict``/``from_dict`` cycle."""
    recorded = NegativeInvariant(
        invariant_id="NI-legacy-route-absent",
        description="the retired /v1/features route stays absent from the router",
        verification_method="grep_absence",
        verification_command="add_route\\(.*/v1/features",
        result="confirmed_absent",
        evidence="grep found zero matches",
        scope="src/specify_cli",
        verified_ref=PRIMARY_REF,
        verified_surface_kind=TopologySurface.PRIMARY.value,
        provenance_origin=PROVENANCE_RECORDED,
    )
    deferred = NegativeInvariant(
        invariant_id="NI-new-package-clean",
        description="the mission's new package carries no TODO markers",
        verification_method="grep_absence",
        verification_command="TODO",
        result=DEFERRED_TO_CONSOLIDATION,
        scope="src/specify_cli/acceptance/post_consolidation.py",
        deferred_reason="scoped path absent on the primary surface pre-consolidation",
        deferred_to_phase="POST_CONSOLIDATION",
    )
    for original in (recorded, deferred):
        restored = NegativeInvariant.from_dict(original.to_dict())
        assert restored == original


def test_to_dict_omits_unset_provenance_for_byte_stability() -> None:
    """A pre-schema-shaped invariant serialises without null provenance keys."""
    legacy = NegativeInvariant(
        invariant_id="NI-01",
        description="legacy route absent",
        verification_method="grep_absence",
        verification_command="legacy_route",
        result="confirmed_absent",
    )
    data = legacy.to_dict()
    for key in (
        "verified_ref",
        "verified_surface_kind",
        "deferred_reason",
        "deferred_to_phase",
        "provenance_origin",
    ):
        assert key not in data, f"{key} should be omitted when unset (byte-stability)"
    # And it still round-trips to the same value via defaults (C2).
    assert NegativeInvariant.from_dict(data) == legacy


# ---------------------------------------------------------------------------
# T021 / C1 / NI-1 — provenance validation, with the typed legacy escape
# ---------------------------------------------------------------------------


def test_ni1_recorded_terminal_without_provenance_is_error() -> None:
    """C1: a ``recorded`` terminal result missing provenance is a validation error."""
    matrix = AcceptanceMatrix(
        mission_slug=MISSION_SLUG,
        negative_invariants=[
            NegativeInvariant(
                invariant_id="NI-recorded-no-provenance",
                description="route absent",
                verification_method="grep_absence",
                verification_command="legacy_route",
                result="confirmed_absent",
                provenance_origin=PROVENANCE_RECORDED,
                # verified_ref / verified_surface_kind deliberately null
            )
        ],
    )
    errors = validate_matrix_evidence(matrix)
    assert any("verified_ref and verified_surface_kind" in e for e in errors)


def test_ni1_recorded_terminal_with_provenance_is_accepted() -> None:
    """C1: a ``recorded`` terminal result carrying full provenance validates clean."""
    matrix = AcceptanceMatrix(
        mission_slug=MISSION_SLUG,
        negative_invariants=[
            NegativeInvariant(
                invariant_id="NI-recorded-ok",
                description="route absent",
                verification_method="grep_absence",
                verification_command="legacy_route",
                result="confirmed_absent",
                verified_ref=PRIMARY_REF,
                verified_surface_kind=TopologySurface.PRIMARY.value,
                provenance_origin=PROVENANCE_RECORDED,
            )
        ],
    )
    assert validate_matrix_evidence(matrix) == []


def test_ni1_legacy_unrecorded_accepts_null_provenance() -> None:
    """C1: ``legacy_unrecorded`` — and ONLY that origin — permits null provenance."""
    matrix = AcceptanceMatrix(
        mission_slug=MISSION_SLUG,
        negative_invariants=[
            NegativeInvariant(
                invariant_id="NI-legacy",
                description="route absent (recorded before provenance existed)",
                verification_method="grep_absence",
                verification_command="legacy_route",
                result="confirmed_absent",
                provenance_origin=PROVENANCE_LEGACY_UNRECORDED,
            )
        ],
    )
    assert validate_matrix_evidence(matrix) == []


def test_ni1_invalid_provenance_origin_is_error() -> None:
    """An unknown ``provenance_origin`` is rejected (anti-phantom: no surface value here)."""
    matrix = AcceptanceMatrix(
        mission_slug=MISSION_SLUG,
        negative_invariants=[
            NegativeInvariant(
                invariant_id="NI-bad-origin",
                description="route absent",
                verification_method="grep_absence",
                verification_command="legacy_route",
                result="confirmed_absent",
                # A TopologySurface value is NOT a valid provenance_origin.
                provenance_origin=TopologySurface.PRIMARY.value,
            )
        ],
    )
    errors = validate_matrix_evidence(matrix)
    assert any("provenance_origin must be one of" in e for e in errors)


@pytest.mark.parametrize("result", ["pending", DEFERRED_TO_CONSOLIDATION])
def test_ni1_pending_and_deferred_are_provenance_exempt(result: str) -> None:
    """Scheduled-not-yet-judged states carry no surface to attribute — exempt."""
    matrix = AcceptanceMatrix(
        mission_slug=MISSION_SLUG,
        negative_invariants=[
            NegativeInvariant(
                invariant_id="NI-unjudged",
                description="route absent",
                verification_method="grep_absence",
                verification_command="legacy_route",
                result=result,
                provenance_origin=PROVENANCE_RECORDED,  # even 'recorded' is fine here
            )
        ],
    )
    assert validate_matrix_evidence(matrix) == []


# ---------------------------------------------------------------------------
# T022 / C3 / NI-2 — terminal-set preservation guard
# ---------------------------------------------------------------------------


def test_deferred_is_not_a_terminal_result() -> None:
    """NI-2: the fourth value is deliberately OUTSIDE the frozen terminal set."""
    assert DEFERRED_TO_CONSOLIDATION not in TERMINAL_INVARIANT_RESULTS
    assert set(TERMINAL_INVARIANT_RESULTS) == {
        "confirmed_absent",
        "still_present",
        "verification_error",
    }


def test_ni2_recorded_terminal_preserved_verbatim(tmp_path: Path) -> None:
    """C3: a recorded terminal result + its provenance survive a later run verbatim.

    Even when the gate re-runs against a *different* surface/ref (the accept-time
    pre-merge primary root), the recorded judgement is never overwritten or
    re-executed — provenance included.
    """
    recorded = NegativeInvariant(
        invariant_id="NI-added-suite-green",
        description="mission-added protection suite passes",
        verification_method="custom_command",
        verification_command="test -f protection_added_by_mission.txt",
        result="confirmed_absent",
        evidence="Verified green on the integrated lane tree during WP review",
        verified_ref=CONSOLIDATED_REF,
        verified_surface_kind=TopologySurface.CONSOLIDATED.value,
        provenance_origin=PROVENANCE_RECORDED,
    )
    context = _context(tmp_path, surface_kind=TopologySurface.PRIMARY, ref=PRIMARY_REF)
    (result,) = enforce_negative_invariants(tmp_path, [recorded], context=context)
    assert result == recorded  # verbatim — result AND provenance unchanged
    assert result.verified_ref == CONSOLIDATED_REF
    assert result.verified_surface_kind == TopologySurface.CONSOLIDATED.value


def test_ni2_deferred_not_frozen_stays_intact_at_accept(tmp_path: Path) -> None:
    """A ``deferred_to_consolidation`` value is not frozen by the terminal guard.

    Pre-consolidation it is left intact (judged later by the post-consolidation
    op), but it is NOT swept into the terminal-preservation set — that is what
    keeps NI-4 / C6 re-judgement possible.
    """
    deferred = NegativeInvariant(
        invariant_id="NI-deferred",
        description="new package clean",
        verification_method="grep_absence",
        verification_command="TODO",
        result=DEFERRED_TO_CONSOLIDATION,
        scope="src/specify_cli/acceptance/post_consolidation.py",
        deferred_reason="absent pre-consolidation",
        deferred_to_phase="POST_CONSOLIDATION",
    )
    context = _context(tmp_path)
    (result,) = enforce_negative_invariants(tmp_path, [deferred], context=context)
    assert result.result == DEFERRED_TO_CONSOLIDATION
    assert result == deferred


# ---------------------------------------------------------------------------
# T023 / C4 / C9 / NI-3 — defer semantics
# ---------------------------------------------------------------------------


def test_ni3_pending_scoped_absent_defers_not_still_present(tmp_path: Path) -> None:
    """C4: a pending invariant whose scoped subject is absent defers, never still_present."""
    pending = NegativeInvariant(
        invariant_id="NI-mission-package-clean",
        description="the mission's new package carries no debug prints",
        verification_method="grep_absence",
        verification_command="print\\(",
        # This source dir does NOT exist on the pre-merge primary tree (tmp_path).
        scope="src/specify_cli/acceptance/post_consolidation.py",
        result="pending",
    )
    context = _context(tmp_path, phase=LifecyclePhase.ACCEPT)
    (result,) = enforce_negative_invariants(tmp_path, [pending], context=context)
    assert result.result == DEFERRED_TO_CONSOLIDATION
    assert result.result != "still_present"
    assert result.deferred_reason
    assert result.deferred_to_phase == "POST_CONSOLIDATION"


def test_c9_scoped_existing_dir_judged_not_deferred(tmp_path: Path) -> None:
    """C9: a grep_absence scoped to a dir that already exists is judged pre-consolidation."""
    src = tmp_path / "src" / "specify_cli"
    src.mkdir(parents=True)
    (src / "router.py").write_text("def add_route(path):\n    return path\n", encoding="utf-8")
    pending = NegativeInvariant(
        invariant_id="NI-legacy-route-absent",
        description="the retired /v1/features route stays absent",
        verification_method="grep_absence",
        verification_command="/v1/features",  # absent from the existing dir
        scope="src/specify_cli",
        result="pending",
    )
    context = _context(tmp_path, phase=LifecyclePhase.ACCEPT)
    (result,) = enforce_negative_invariants(tmp_path, [pending], context=context)
    assert result.result == "confirmed_absent"  # judged, NOT deferred
    assert result.provenance_origin == PROVENANCE_RECORDED


def test_judged_result_is_stamped_recorded_with_surface_and_ref(tmp_path: Path) -> None:
    """NI-1: a freshly judged result carries the surface + ref it was established against."""
    src = tmp_path / "src"
    src.mkdir()
    (src / "clean.py").write_text("x = 1\n", encoding="utf-8")
    pending = NegativeInvariant(
        invariant_id="NI-no-eval",
        description="no eval() in the tree",
        verification_method="grep_absence",
        verification_command="eval(",
        scope="src",
        result="pending",
    )
    context = _context(
        tmp_path, surface_kind=TopologySurface.PRIMARY, ref=PRIMARY_REF
    )
    (result,) = enforce_negative_invariants(tmp_path, [pending], context=context)
    assert result.result == "confirmed_absent"
    assert result.provenance_origin == PROVENANCE_RECORDED
    assert result.verified_ref == PRIMARY_REF
    assert result.verified_surface_kind == TopologySurface.PRIMARY.value


def test_enforce_without_context_preserves_legacy_behaviour(tmp_path: Path) -> None:
    """Back-compat: no context → judge pending, no provenance stamp, no deferral."""
    src = tmp_path / "src"
    src.mkdir()
    (src / "clean.py").write_text("x = 1\n", encoding="utf-8")
    pending = NegativeInvariant(
        invariant_id="NI-legacy-caller",
        description="no eval()",
        verification_method="grep_absence",
        verification_command="eval(",
        scope="src",
        result="pending",
    )
    (result,) = enforce_negative_invariants(tmp_path, [pending])
    assert result.result == "confirmed_absent"
    # Unstamped: the legacy default origin, accepted by validation.
    assert result.provenance_origin == PROVENANCE_LEGACY_UNRECORDED
    assert result.verified_ref is None


# ---------------------------------------------------------------------------
# T024 / C5 / NI-5 — the fourth overall_verdict value
# ---------------------------------------------------------------------------


def _passing_criterion() -> AcceptanceCriterion:
    return AcceptanceCriterion(
        criterion_id="FR-002",
        description="gate judges the surface it is handed",
        proof_type="automated_test",
        pass_fail="pass",
    )


def _deferred_invariant() -> NegativeInvariant:
    return NegativeInvariant(
        invariant_id="NI-deferred",
        description="mission package clean",
        verification_method="grep_absence",
        verification_command="TODO",
        scope="src/specify_cli/acceptance/post_consolidation.py",
        result=DEFERRED_TO_CONSOLIDATION,
        deferred_reason="absent pre-consolidation",
        deferred_to_phase="POST_CONSOLIDATION",
    )


def test_ni5_deferred_yields_pass_pending_consolidation() -> None:
    """NI-5: a deferred invariant makes the verdict distinguishable, not a plain pass."""
    matrix = AcceptanceMatrix(
        mission_slug=MISSION_SLUG,
        criteria=[_passing_criterion()],
        negative_invariants=[_deferred_invariant()],
    )
    assert matrix.overall_verdict == VERDICT_PASS_PENDING_CONSOLIDATION


def test_c5_pass_pending_consolidation_does_not_block() -> None:
    """C5: the deferral verdict is neither ``fail`` nor ``pending`` — accept is not blocked."""
    matrix = AcceptanceMatrix(
        mission_slug=MISSION_SLUG,
        criteria=[_passing_criterion()],
        negative_invariants=[_deferred_invariant()],
    )
    verdict = matrix.overall_verdict
    assert verdict not in {"fail", "pending"}


def test_ni5_pending_criterion_dominates_deferral() -> None:
    """An unverified criterion still dominates — deferral does not mask real pending work."""
    matrix = AcceptanceMatrix(
        mission_slug=MISSION_SLUG,
        criteria=[
            AcceptanceCriterion(
                criterion_id="FR-003",
                description="unjudgeable defers",
                proof_type="automated_test",
                pass_fail="pending",
            )
        ],
        negative_invariants=[_deferred_invariant()],
    )
    assert matrix.overall_verdict == "pending"


def test_ni5_still_present_dominates_deferral() -> None:
    """A real violation dominates a co-present deferral — fail wins."""
    matrix = AcceptanceMatrix(
        mission_slug=MISSION_SLUG,
        criteria=[_passing_criterion()],
        negative_invariants=[
            _deferred_invariant(),
            NegativeInvariant(
                invariant_id="NI-violation",
                description="forbidden symbol present",
                verification_method="grep_absence",
                verification_command="forbidden_symbol",
                result="still_present",
                verified_ref=PRIMARY_REF,
                verified_surface_kind=TopologySurface.PRIMARY.value,
                provenance_origin=PROVENANCE_RECORDED,
            ),
        ],
    )
    assert matrix.overall_verdict == "fail"


def test_clean_terminal_only_matrix_still_passes() -> None:
    """No deferral outstanding → an ordinary clean ``pass`` (regression guard)."""
    matrix = AcceptanceMatrix(
        mission_slug=MISSION_SLUG,
        criteria=[_passing_criterion()],
        negative_invariants=[
            NegativeInvariant(
                invariant_id="NI-clean",
                description="route absent",
                verification_method="grep_absence",
                verification_command="legacy_route",
                result="confirmed_absent",
                verified_ref=PRIMARY_REF,
                verified_surface_kind=TopologySurface.PRIMARY.value,
                provenance_origin=PROVENANCE_RECORDED,
            )
        ],
    )
    assert matrix.overall_verdict == "pass"


# ---------------------------------------------------------------------------
# T025 / C8 / AH-3 — single authoritative home
# ---------------------------------------------------------------------------


def test_c8_existing_home_matrix_prevents_second_copy(tmp_path: Path) -> None:
    """C8: when the declared home already holds a matrix, no second copy is scaffolded.

    Models coord topology: the authoritative matrix lives at ``home_dir`` (the coord
    surface) and the primary ``feature_dir`` is empty. The scaffolder must return the
    home copy and NEVER author a divergent primary one (#2882).
    """
    home_dir = tmp_path / "coord"
    feature_dir = tmp_path / "primary"
    home_dir.mkdir()
    feature_dir.mkdir()
    # The authoritative matrix already exists on the declared home.
    write_home = scaffold_acceptance_matrix(home_dir, MISSION_SLUG, requirement_ids=["FR-002"])
    assert write_home == home_dir / "acceptance-matrix.json"

    returned = scaffold_acceptance_matrix(
        feature_dir,
        MISSION_SLUG,
        requirement_ids=["FR-002"],
        home_dir=home_dir,
    )
    assert returned == home_dir / "acceptance-matrix.json"
    assert not (feature_dir / "acceptance-matrix.json").exists(), (
        "a second primary-scaffold copy was authored — C8/AH-3 violated"
    )


def test_c8_absent_home_scaffolds_single_primary_copy(tmp_path: Path) -> None:
    """When the home has no matrix yet, exactly one copy is authored at feature_dir."""
    home_dir = tmp_path / "coord"
    feature_dir = tmp_path / "primary"
    home_dir.mkdir()
    feature_dir.mkdir()
    returned = scaffold_acceptance_matrix(
        feature_dir,
        MISSION_SLUG,
        requirement_ids=["FR-002"],
        home_dir=home_dir,
    )
    assert returned == feature_dir / "acceptance-matrix.json"
    assert (feature_dir / "acceptance-matrix.json").exists()
    assert not (home_dir / "acceptance-matrix.json").exists()


def test_c8_default_home_is_idempotent(tmp_path: Path) -> None:
    """Without a home_dir the check falls back to feature_dir and stays idempotent."""
    feature_dir = tmp_path / "primary"
    feature_dir.mkdir()
    first = scaffold_acceptance_matrix(feature_dir, MISSION_SLUG, requirement_ids=["FR-002"])
    assert first is not None
    original = first.read_text(encoding="utf-8")
    # A re-run must not clobber operator-curated content.
    second = scaffold_acceptance_matrix(feature_dir, MISSION_SLUG, requirement_ids=["FR-999"])
    assert second == first
    assert first.read_text(encoding="utf-8") == original
