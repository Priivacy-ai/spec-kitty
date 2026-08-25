# Design Decisions

> Capture rationale that would otherwise evaporate.

## Entries

- 2026-08-24 — Decision: create an immutable eligibility projection from the coordination-aware canonical event surface. Alternatives: frontmatter status, `lanes.json`, or repeated downstream reads. Rationale: one authority read prevents drift and preserves event-log primacy.
- 2026-08-24 — Decision: reject every direct eligible-to-canceled dependency before filtering and before mutation. Alternatives: treat it as satisfied, rewrite it, or stop at the first edge. Rationale: authored prerequisites require operator repair and complete deterministic diagnostics.
- 2026-08-24 — Decision: keep `compute_lanes` status-agnostic and use its existing empty-graph behavior only when the projection proves all known work is canceled. Alternatives: teach the allocator lifecycle state or remove the finalizer's empty-input guard globally. Rationale: preserves current invalid-input protection and #3431 semantics.
- 2026-08-24 — Decision: isolate pure projection policy in `finalization_eligibility.py`. Alternatives: expand the 2,996-line finalizer or the broader validation module. Rationale: campsite discipline and direct unit testability.
