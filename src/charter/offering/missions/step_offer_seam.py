"""Override seam for doctrine advisory offers (FR-008; D4/C-002).

A ``MissionStep`` carries advisory offers -- today, ``recommended_model_tier``
(the step's advisory model-tier preference; ``agent_profile`` is the step's
existing advisory role offer and is untouched by this module). These are
**offers**, never routing **decisions**: charter/runtime retains sole routing
authority (C-002). A doctrine-authored offer must never silently win over an
operator/runtime-declared override.

This module is the **one named seam** (D4) through which such an offer is
resolved against an optional charter/runtime override. The precedence is
explicit and total:

    override (charter/runtime)  >  step offer (doctrine)

- If an override is supplied, it is the effective value -- unconditionally,
  even when it disagrees with the step's offer. The step's offer is still
  returned (:attr:`OfferResolution.offer`) for observability/rationale, but
  it never determines :attr:`OfferResolution.effective` when an override is
  present.
- If no override is supplied, the step's offer -- unmodified -- becomes the
  effective value.
- If neither is supplied, ``effective`` is ``None``: no preference exists at
  all, and the caller's own default applies.

Doctrine NEVER overrides a routing decision (binding per C-002). This is a
pure, deterministic resolution: no I/O, no hidden defaults beyond
"override wins."
"""

from __future__ import annotations

from dataclasses import dataclass

#: Provenance value when the step's advisory offer was used unmodified
#: (no override was supplied).
OFFER_SOURCE = "offer"
#: Provenance value when a charter/runtime override decided the effective
#: value (regardless of what the step offered).
OVERRIDE_SOURCE = "override"


@dataclass(frozen=True)
class OfferResolution:
    """The resolved effective value for one doctrine advisory offer.

    ``effective`` is what callers should act on. ``source`` records
    provenance: :data:`OVERRIDE_SOURCE` when a charter/runtime override
    decided the value, :data:`OFFER_SOURCE` when the step's own advisory
    value was used unmodified. ``offer`` is always the raw step-authored
    value, kept for observability even when it was overridden.
    """

    effective: str | None
    source: str
    offer: str | None


def resolve_model_tier_offer(*, step_offer: str | None, override: str | None) -> OfferResolution:
    """Resolve a step's ``recommended_model_tier`` offer against an optional
    charter/runtime override, with **override-wins** precedence (D4/C-002).

    Doctrine's ``step_offer`` is advisory-only: this function never lets it
    take precedence over a supplied ``override``. Returns
    ``effective=None`` when neither value is present -- there is no
    preference to apply.
    """
    if override is not None:
        return OfferResolution(effective=override, source=OVERRIDE_SOURCE, offer=step_offer)
    return OfferResolution(effective=step_offer, source=OFFER_SOURCE, offer=step_offer)
