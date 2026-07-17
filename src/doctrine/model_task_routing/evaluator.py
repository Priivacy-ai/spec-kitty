"""Deterministic objective-function scorer for model-task routing (FR-003).

This module is a PURE function library: no filesystem access, no network,
no hidden/global state. It consumes:

- a loaded :class:`~doctrine.model_task_routing.models.ModelToTaskType`
  catalog (WP01's :func:`~doctrine.model_task_routing.loader.load` result),
- a ``task_type`` string, and
- an :class:`~doctrine.agent_profiles.profile.AgentProfile` (WP04's
  ``preferred_model``/``effort`` fields, YAML aliases ``model``/``effort``),

and returns a :class:`RoutingRecommendation`. Same inputs always produce an
equal recommendation (NFR-004) -- there is no caching to invalidate and
nothing to mock; callers can rely on plain equality in tests.

Objective semantics
--------------------
``routing_policy.objective`` selects how a model's per-task ``task_fit``
score and the objective-function components (cost/risk/latency,
desirability-normalized) combine into a ranking:

- ``quality_first`` is the **capability lever** (there is no separate
  capability tier in the schema, per spec.md non-goals): the model with
  the strongest ``task_fit`` for the task_type wins outright; the
  weighted sum only breaks ties between equally-fit models. This holds
  even when ``routing_policy.weights`` themselves are not quality-heavy.
- Any other objective (``balanced``, ``cost_first``) falls back to the
  plain weighted sum across quality/cost/risk/latency.

``tier_constraints`` are applied as a hard filter *before* scoring: a
model whose cost tier exceeds the constraint's ``max_tier`` for the
task_type is excluded from candidacy entirely, regardless of objective.

Override precedence (C-004: only ``advisory`` is exercised)
-------------------------------------------------------------
Under ``override_policy.mode == "advisory"``, the evaluator emits BOTH
the catalog's computed pick and the profile's declared
``preferred_model`` as separate, provenance-tagged
:class:`RoutingCandidate` entries (``source="catalog"`` /
``source="profile"``) -- it enforces neither. ``gated``/``required``
modes are read-but-not-differentiated here (out of scope, C-004); the
resolved mode is still carried on the recommendation for callers to
inspect.

Step model-tier offer (FR-008; D4/C-002; live consumer, WP08)
---------------------------------------------------------------
``evaluate`` optionally accepts ``recommended_model_tier`` (a
``MissionStep``'s advisory model-tier offer, read from the caller's own
step lookup) and ``model_tier_override`` (a charter/runtime override).
Both are resolved through the one named seam,
:func:`doctrine.missions.step_offer_seam.resolve_model_tier_offer`, with
**override-wins** precedence, and the resolution is surfaced on
:attr:`RoutingRecommendation.model_tier`. This is additive and advisory
only -- it never changes ``catalog_candidate``/``profile_candidate``
scoring, so routing authority never leaks into doctrine (C-002). When
neither argument is supplied (the default), ``model_tier`` is ``None``
and evaluator behavior is byte-for-byte unchanged from before this offer
existed.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from doctrine.agent_profiles.profile import AgentProfile
from doctrine.missions.step_offer_seam import OfferResolution, resolve_model_tier_offer
from doctrine.model_task_routing.models import (
    Confidence,
    CostTier,
    LatencyTier,
    ModelEntry,
    ModelToTaskType,
    RoutingObjective,
    RoutingWeights,
    TaskFit,
    TierConstraint,
)

_COST_DESIRABILITY: dict[CostTier, float] = {
    CostTier.LOW: 1.0,
    CostTier.MEDIUM: 0.66,
    CostTier.HIGH: 0.33,
    CostTier.PREMIUM: 0.0,
}
_COST_TIER_ORDER: dict[CostTier, int] = {
    CostTier.LOW: 0,
    CostTier.MEDIUM: 1,
    CostTier.HIGH: 2,
    CostTier.PREMIUM: 3,
}
_RISK_DESIRABILITY: dict[Confidence, float] = {
    Confidence.HIGH: 1.0,
    Confidence.MEDIUM: 0.66,
    Confidence.LOW: 0.33,
}
_LATENCY_DESIRABILITY: dict[LatencyTier, float] = {
    LatencyTier.LOW: 1.0,
    LatencyTier.MEDIUM: 0.66,
    LatencyTier.HIGH: 0.33,
}
_NEUTRAL_DESIRABILITY = 0.5

_SOURCE_CATALOG = "catalog"
_SOURCE_PROFILE = "profile"


@dataclass(frozen=True)
class RoutingCandidate:
    """A single provenance-tagged routing candidate.

    ``score`` is the catalog-computed weighted objective score for
    ``source="catalog"`` candidates; it is ``None`` for
    ``source="profile"`` candidates, which carry no catalog-derived
    score -- they are the human/profile-declared value, surfaced as-is.
    """

    model_id: str
    source: str
    score: float | None = None
    rationale: str | None = None
    effort: str | None = None


@dataclass(frozen=True)
class RoutingRecommendation:
    """The evaluator's output: a task_type-scoped, provenance-tagged set
    of candidates plus the objective/override-mode that produced them.

    ``model_tier`` is the resolved ``recommended_model_tier`` offer
    (:func:`doctrine.missions.step_offer_seam.resolve_model_tier_offer`),
    or ``None`` when the caller supplied neither a step offer nor an
    override -- the default, behavior-preserving state (WP08).
    """

    task_type: str
    objective: str
    override_mode: str
    candidates: tuple[RoutingCandidate, ...]
    model_tier: OfferResolution | None = None

    @property
    def catalog_candidate(self) -> RoutingCandidate | None:
        """The catalog-computed pick, or ``None`` on no match."""
        return next((c for c in self.candidates if c.source == _SOURCE_CATALOG), None)

    @property
    def profile_candidate(self) -> RoutingCandidate | None:
        """The profile-declared model, or ``None`` when undeclared."""
        return next((c for c in self.candidates if c.source == _SOURCE_PROFILE), None)


def _tier_allowed(
    model: ModelEntry, task_type: str, tier_constraints: list[TierConstraint]
) -> bool:
    """Apply the ``tier_constraints`` hard filter for ``task_type``.

    A model whose cost tier exceeds the constraint's ``max_tier`` is
    excluded from candidacy outright -- this runs before any scoring so a
    capped model can never win, regardless of objective.
    """
    constraint = next((tc for tc in tier_constraints if tc.task_type == task_type), None)
    if constraint is None:
        return True
    return _COST_TIER_ORDER[model.cost.tier] <= _COST_TIER_ORDER[constraint.max_tier]


def _matching_fit(model: ModelEntry, task_type: str) -> TaskFit | None:
    return next((fit for fit in model.task_fit if fit.task_type == task_type), None)


def _weighted_score(model: ModelEntry, fit: TaskFit, weights: RoutingWeights) -> float:
    """The plain objective-function weighted sum across all four axes."""
    quality = fit.score
    cost = _COST_DESIRABILITY.get(model.cost.tier, _NEUTRAL_DESIRABILITY)
    risk = (
        _RISK_DESIRABILITY.get(fit.confidence, _NEUTRAL_DESIRABILITY)
        if fit.confidence is not None
        else _NEUTRAL_DESIRABILITY
    )
    latency = (
        _LATENCY_DESIRABILITY.get(model.latency_tier, _NEUTRAL_DESIRABILITY)
        if model.latency_tier is not None
        else _NEUTRAL_DESIRABILITY
    )
    return (
        weights.quality * quality
        + weights.cost * cost
        + weights.risk * risk
        + weights.latency * latency
    )


def _ranking_key(
    objective: RoutingObjective,
) -> Callable[[tuple[ModelEntry, TaskFit, float]], tuple[float, float]]:
    """Bind the objective into a sort key for ``max()`` over ``(model, fit,
    weighted)`` triples.

    Under ``quality_first`` (the capability lever), raw task_fit score is
    the primary key and the weighted sum only breaks ties. Otherwise the
    weighted sum alone decides -- both branches return a 2-tuple so the
    keys stay comparable within a single ``max()`` call.
    """

    def key(entry: tuple[ModelEntry, TaskFit, float]) -> tuple[float, float]:
        _, fit, weighted = entry
        if objective is RoutingObjective.QUALITY_FIRST:
            return (fit.score, weighted)
        return (weighted, weighted)

    return key


def _best_catalog_candidate(catalog: ModelToTaskType, task_type: str) -> RoutingCandidate | None:
    """Score every tier-allowed, task_type-matching model and return the
    winner as a ``source="catalog"`` candidate, or ``None`` on no match."""
    policy = catalog.routing_policy
    matches: list[tuple[ModelEntry, TaskFit, float]] = []
    for model in catalog.models:
        if not _tier_allowed(model, task_type, policy.tier_constraints):
            continue
        fit = _matching_fit(model, task_type)
        if fit is None:
            continue
        matches.append((model, fit, _weighted_score(model, fit, policy.weights)))

    if not matches:
        return None

    best_model, best_fit, best_weighted = max(matches, key=_ranking_key(policy.objective))
    return RoutingCandidate(
        model_id=best_model.id,
        source=_SOURCE_CATALOG,
        score=best_weighted,
        rationale=best_fit.rationale,
    )


def _profile_candidate(profile: AgentProfile) -> RoutingCandidate | None:
    """The profile's declared model as a ``source="profile"`` candidate,
    or ``None`` when the profile has no ``preferred_model``."""
    if not profile.preferred_model:
        return None
    return RoutingCandidate(
        model_id=profile.preferred_model,
        source=_SOURCE_PROFILE,
        effort=profile.effort,
    )


def _resolve_model_tier(
    recommended_model_tier: str | None, model_tier_override: str | None
) -> OfferResolution | None:
    """Resolve the step's model-tier offer via the one named seam.

    Returns ``None`` -- not an :class:`OfferResolution` with empty
    fields -- when the caller supplies neither argument, so
    ``RoutingRecommendation.model_tier`` stays absent for every existing
    caller that does not yet pass a step offer (behavior-preserving).
    """
    if recommended_model_tier is None and model_tier_override is None:
        return None
    return resolve_model_tier_offer(step_offer=recommended_model_tier, override=model_tier_override)


def evaluate(
    catalog: ModelToTaskType,
    task_type: str,
    profile: AgentProfile,
    *,
    recommended_model_tier: str | None = None,
    model_tier_override: str | None = None,
) -> RoutingRecommendation:
    """Compute a routing recommendation. Pure, deterministic, never raises
    on "no match"/empty ``task_fit`` -- it returns fewer candidates instead.

    Under ``override_policy.mode == "advisory"`` (the only mode exercised,
    C-004), both the catalog pick and the profile's declared model are
    surfaced with provenance; neither is enforced over the other.

    ``recommended_model_tier`` (a step's advisory offer, FR-008) and
    ``model_tier_override`` (a charter/runtime override) are both
    optional and default to ``None``: omitting both reproduces prior
    behavior exactly (``model_tier=None`` on the result). When either is
    supplied, they are resolved through
    :func:`doctrine.missions.step_offer_seam.resolve_model_tier_offer`
    with override-wins precedence (D4/C-002) -- this never influences
    ``catalog_candidate``/``profile_candidate``, only the surfaced
    ``model_tier`` resolution.
    """
    catalog_pick = _best_catalog_candidate(catalog, task_type)
    profile_pick = _profile_candidate(profile)
    candidates = tuple(c for c in (catalog_pick, profile_pick) if c is not None)

    policy = catalog.routing_policy
    return RoutingRecommendation(
        task_type=task_type,
        objective=str(policy.objective.value),
        override_mode=str(policy.override_policy.mode.value),
        candidates=candidates,
        model_tier=_resolve_model_tier(recommended_model_tier, model_tier_override),
    )
