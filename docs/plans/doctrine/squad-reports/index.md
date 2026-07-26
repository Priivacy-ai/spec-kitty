---
title: Squad reports — creed and FoundationalValues hardening
description: "Raw four-lens squad reports behind the hardened creed/FoundationalValues design: architect, doctrine-curator, reviewer, and implementer."
doc_status: draft
updated: '2026-07-26'
related:
- docs/plans/doctrine/creed-and-values-design-hardened.md
---
# Squad reports — creed and FoundationalValues hardening

Raw, profile-loaded, read-only squad reports from 2026-07-26. These are the evidence base for
[`creed-and-values-design-hardened.md`](../creed-and-values-design-hardened.md); the hardened
design is the synthesis, these are the workings.

- [Architect lens — seams, types, and concrete shapes](architect.md) — where each part plugs in,
  the `impacts`-as-field decision, the value-bearing kind set, and the composition invariant
  enforced as a type.
- [Doctrine-curator lens — exemptions, accreditation, provenance](doctrine-curator.md) — the
  per-kind exemption table, the `value_impact` vs `value_bias` split, accreditation placement,
  and the drift-detection layers.
- [Reviewer lens — adversarial pass and the 39% verdict](reviewer.md) — the sign-channel noise
  finding, the one-cost-axis census, the creed-ranking collapse measurement, and the interview
  loop.
- [Implementer lens — feasibility and the prototype slice](implementer.md) — real Pydantic
  models, the `delta` representation decision, the coverage gate, and the one-day pre-registered
  prototype.

Where two lenses diverged (`toolguide` and `agent_profile` membership), the hardened design
adjudicates on semantics and says so.

## See also

- [Doctrine plans index](../index.md)
