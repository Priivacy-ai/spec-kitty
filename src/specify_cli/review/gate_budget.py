"""Deterministic, source-controlled budget policy for pre-review test scopes.

The policy in this module is intentionally pure and immutable. Runtime timing
observations may inform a later reviewed source change, but they cannot mutate
classifications in a running process.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from enum import StrEnum

__all__ = [
    "BudgetClassification",
    "ScopeBudgetAssessment",
    "ScopeBudgetRule",
    "ScopeIdentity",
    "assess_scope_budget",
]

_POLICY_NAMESPACE = "spec-kitty.pre-review-budget/v1"
_IDENTITY_PREFIX = "budget-v1:sha256:"


class BudgetClassification(StrEnum):
    """Deterministic suitability of a selected scope for the gate budget."""

    BOUNDED = "bounded"
    OVERSIZED = "oversized"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class ScopeBudgetRule:
    """One immutable, source-controlled exact-target classification rule."""

    rule_id: str
    required_target_atoms: tuple[str, ...]
    classification: BudgetClassification
    evidence: str
    guidance: str


@dataclass(frozen=True)
class ScopeIdentity:
    """Stable identity for the normalized target projection of a test scope."""

    normalized_targets: tuple[str, ...]
    policy_namespace: str
    value: str


@dataclass(frozen=True)
class ScopeBudgetAssessment:
    """Immutable result of applying the canonical budget rules to a scope."""

    classification: BudgetClassification
    scope_identity: ScopeIdentity
    effective_budget_seconds: float
    matched_rule_id: str | None
    evidence: str | None
    guidance: str

    def __post_init__(self) -> None:
        """Enforce model invariants at every construction boundary."""
        budget = float(self.effective_budget_seconds)
        if not math.isfinite(budget) or budget <= 0:
            raise ValueError("effective budget must be a positive finite number")
        object.__setattr__(self, "effective_budget_seconds", budget)

        matched = self.matched_rule_id is not None
        if self.classification is BudgetClassification.UNKNOWN and matched:
            raise ValueError("unknown classification cannot have a matched rule")
        if self.classification is not BudgetClassification.UNKNOWN and not matched:
            raise ValueError("bounded and oversized classifications require a matched rule")


_RULES: tuple[ScopeBudgetRule, ...] = (
    ScopeBudgetRule(
        rule_id="spec-kitty-architectural-full-directory",
        required_target_atoms=("tests/architectural",),
        classification=BudgetClassification.OVERSIZED,
        evidence="issue #2573 dogfood, approximately 26 minutes per leg",
        guidance=("Select a bounded test scope, or explicitly skip the pre-review gate when the operator accepts that tradeoff."),
    ),
    ScopeBudgetRule(
        rule_id="spec-kitty-gate-budget-pinned-vector",
        required_target_atoms=("tests/review/test_gate_budget.py::test_identity_matches_pinned_vector",),
        classification=BudgetClassification.BOUNDED,
        evidence="reviewed isolated contract node with no network, repository mutation, or subprocess fan-out",
        guidance="Run this stable isolated contract node under the configured timeout.",
    ),
)

_UNKNOWN_GUIDANCE = (
    "No reviewed budget metadata matches this scope; run it under the configured timeout and treat any timeout as a retrospective classification candidate."
)


def _normalize_target(target: str) -> str:
    normalized = target.replace("\\", "/")
    while normalized.startswith("./"):
        normalized = normalized[2:]
    return normalized.rstrip("/")


def _scope_identity(test_targets: tuple[str, ...]) -> ScopeIdentity:
    normalized_targets = tuple(sorted({_normalize_target(target) for target in test_targets}))
    canonical = json.dumps(
        {"namespace": _POLICY_NAMESPACE, "targets": list(normalized_targets)},
        sort_keys=True,
        ensure_ascii=True,
        separators=(",", ":"),
    ).encode("utf-8")
    digest = hashlib.sha256(canonical).hexdigest()  # noqa: TID251 - versioned scope identity, not charter content
    return ScopeIdentity(
        normalized_targets=normalized_targets,
        policy_namespace=_POLICY_NAMESPACE,
        value=f"{_IDENTITY_PREFIX}{digest}",
    )


def assess_scope_budget(test_targets: tuple[str, ...], effective_budget_seconds: float) -> ScopeBudgetAssessment:
    """Classify normalized targets against immutable exact-membership rules.

    The function reads only target metadata. It does not inspect a declared
    command, execution history, CI logs, or mutable runtime state.
    """
    identity = _scope_identity(test_targets)
    selected_targets = frozenset(identity.normalized_targets)

    for rule in _RULES:
        rule_targets = frozenset(rule.required_target_atoms)
        matches = (
            selected_targets.issuperset(rule_targets)
            if rule.classification is BudgetClassification.OVERSIZED
            else selected_targets == rule_targets
        )
        if matches:
            return ScopeBudgetAssessment(
                classification=rule.classification,
                scope_identity=identity,
                effective_budget_seconds=effective_budget_seconds,
                matched_rule_id=rule.rule_id,
                evidence=rule.evidence,
                guidance=rule.guidance,
            )

    return ScopeBudgetAssessment(
        classification=BudgetClassification.UNKNOWN,
        scope_identity=identity,
        effective_budget_seconds=effective_budget_seconds,
        matched_rule_id=None,
        evidence=None,
        guidance=_UNKNOWN_GUIDANCE,
    )
