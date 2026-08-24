"""Contract tests for deterministic pre-review scope-budget policy."""

from __future__ import annotations

import dataclasses
import inspect
import os
import subprocess
import sys

import pytest

from specify_cli.review import ScopeBudgetRule as ExportedScopeBudgetRule
from specify_cli.review import ScopeIdentity as ExportedScopeIdentity
from specify_cli.review import gate_budget
from specify_cli.review.gate_budget import (
    BudgetClassification,
    ScopeBudgetAssessment,
    ScopeBudgetRule,
    ScopeIdentity,
    assess_scope_budget,
)


pytestmark = pytest.mark.fast


PINNED_ARCHITECTURAL_IDENTITY = "budget-v1:sha256:10c1e7475c72e48b83e4910e24437646d6ecd55052ca9a3a4f413b17153946fe"
BOUNDED_PINNED_VECTOR_TARGET = "tests/review/test_gate_budget.py::test_identity_matches_pinned_vector"


def test_public_budget_metadata_types_are_exported() -> None:
    assert ExportedScopeBudgetRule is ScopeBudgetRule
    assert ExportedScopeIdentity is ScopeIdentity


@pytest.mark.parametrize(
    ("targets", "expected_targets"),
    [
        (("tests/architectural",), ("tests/architectural",)),
        (
            ("tests/unit", "tests/architectural"),
            ("tests/architectural", "tests/unit"),
        ),
        (
            (".\\tests\\architectural\\", "tests/unit/", "./tests/unit"),
            ("tests/architectural", "tests/unit"),
        ),
    ],
)
def test_exact_architectural_atom_is_oversized(targets: tuple[str, ...], expected_targets: tuple[str, ...]) -> None:
    assessment = assess_scope_budget(targets, effective_budget_seconds=300)

    assert assessment.classification is BudgetClassification.OVERSIZED
    assert assessment.scope_identity.normalized_targets == expected_targets
    assert assessment.matched_rule_id == "spec-kitty-architectural-full-directory"
    assert assessment.evidence is not None and "#2573" in assessment.evidence
    assert assessment.effective_budget_seconds == 300.0


def test_exact_pinned_vector_atom_is_bounded() -> None:
    assessment = assess_scope_budget((BOUNDED_PINNED_VECTOR_TARGET,), effective_budget_seconds=30)

    assert assessment.classification is BudgetClassification.BOUNDED
    assert assessment.scope_identity.normalized_targets == (BOUNDED_PINNED_VECTOR_TARGET,)
    assert assessment.matched_rule_id == "spec-kitty-gate-budget-pinned-vector"
    assert assessment.evidence is not None
    assert assessment.effective_budget_seconds == 30.0


def test_oversized_rule_outranks_bounded_atom() -> None:
    assessment = assess_scope_budget(
        (BOUNDED_PINNED_VECTOR_TARGET, "tests/architectural"),
        effective_budget_seconds=300,
    )

    assert assessment.classification is BudgetClassification.OVERSIZED
    assert assessment.matched_rule_id == "spec-kitty-architectural-full-directory"


def test_bounded_atom_plus_unknown_atom_remains_unknown() -> None:
    assessment = assess_scope_budget(
        (BOUNDED_PINNED_VECTOR_TARGET, "tests/e2e"),
        effective_budget_seconds=300,
    )

    assert assessment.classification is BudgetClassification.UNKNOWN
    assert assessment.matched_rule_id is None


@pytest.mark.parametrize(
    "targets",
    [
        (),
        ("tests/unit",),
        ("tests/review/test_gate_budget.py",),
        ("tests/architectural/test_layer_rules.py",),
        ("tests/architectural/test_layer_rules.py::test_imports",),
    ],
)
def test_unclassified_targets_are_unknown(targets: tuple[str, ...]) -> None:
    assessment = assess_scope_budget(targets, effective_budget_seconds=300)

    assert assessment.classification is BudgetClassification.UNKNOWN
    assert assessment.matched_rule_id is None
    assert assessment.evidence is None


def test_normalization_is_order_and_duplicate_independent() -> None:
    first = assess_scope_budget(
        ("./tests/unit/", "tests/review", "tests/unit"),
        effective_budget_seconds=15,
    )
    second = assess_scope_budget(
        ("tests/review/", "tests\\unit\\"),
        effective_budget_seconds=15,
    )

    assert first.scope_identity == second.scope_identity
    assert first.scope_identity.normalized_targets == ("tests/review", "tests/unit")


def test_pytest_node_selector_is_preserved() -> None:
    target = "./tests/review/test_gate.py::TestGate::test_timeout/"

    assessment = assess_scope_budget((target,), effective_budget_seconds=10)

    assert assessment.scope_identity.normalized_targets == ("tests/review/test_gate.py::TestGate::test_timeout",)


def test_identity_matches_pinned_vector() -> None:
    assessment = assess_scope_budget(("tests/architectural",), effective_budget_seconds=300)

    assert assessment.scope_identity.value == PINNED_ARCHITECTURAL_IDENTITY
    assert assessment.scope_identity.policy_namespace == ("spec-kitty.pre-review-budget/v1")


def test_identity_is_stable_in_fresh_process_with_different_hash_seed() -> None:
    script = """
from specify_cli.review.gate_budget import assess_scope_budget
print(assess_scope_budget((\"tests/architectural\",), 300).scope_identity.value)
"""
    env = os.environ.copy()
    env["PYTHONHASHSEED"] = "8675309"

    completed = subprocess.run(
        [sys.executable, "-c", script],
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )

    assert completed.stdout.strip() == PINNED_ARCHITECTURAL_IDENTITY


def test_declared_command_is_not_an_assessment_input() -> None:
    signature = inspect.signature(assess_scope_budget)

    assert tuple(signature.parameters) == (
        "test_targets",
        "effective_budget_seconds",
    )
    assessment = assess_scope_budget((), effective_budget_seconds=300)
    assert assessment.classification is BudgetClassification.UNKNOWN


def test_policy_values_are_frozen() -> None:
    identity = ScopeIdentity(
        normalized_targets=("tests/unit",),
        policy_namespace="spec-kitty.pre-review-budget/v1",
        value="budget-v1:sha256:example",
    )
    rule = ScopeBudgetRule(
        rule_id="test-rule",
        required_target_atoms=("tests/unit",),
        classification=BudgetClassification.BOUNDED,
        evidence="test evidence",
        guidance="run it",
    )
    assessment = ScopeBudgetAssessment(
        classification=BudgetClassification.BOUNDED,
        scope_identity=identity,
        effective_budget_seconds=10,
        matched_rule_id=rule.rule_id,
        evidence=rule.evidence,
        guidance=rule.guidance,
    )

    with pytest.raises(dataclasses.FrozenInstanceError):
        assessment.guidance = "changed"  # type: ignore[misc]


def test_assessment_cannot_promote_future_scopes() -> None:
    before = assess_scope_budget(("tests/new-suite",), effective_budget_seconds=10)
    assess_scope_budget(("tests/architectural",), effective_budget_seconds=10)
    after = assess_scope_budget(("tests/new-suite",), effective_budget_seconds=10)

    assert before == after
    assert after.classification is BudgetClassification.UNKNOWN
    assert not {
        "add_rule",
        "learn_scope",
        "promote_scope",
        "register_rule",
        "update_rule",
    }.intersection(gate_budget.__all__)


@pytest.mark.parametrize("budget", [0, -1, float("inf"), float("nan")])
def test_budget_must_be_positive_and_finite(budget: float) -> None:
    with pytest.raises(ValueError, match="positive finite"):
        assess_scope_budget(("tests/unit",), effective_budget_seconds=budget)
