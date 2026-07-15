# Contracts — resolver-seam-completion-01KXK0KG

This mission is an **internal charter/doctrine seam change** — it has no external
REST/GraphQL/wire API contracts. The "contracts" it establishes are **code-level
invariants**, verified by tests rather than schema files:

- **Cross-grain disjointness (FR-013)** — the doctrine-integrity gate
  `tests/doctrine/drg/test_cross_grain_integrity.py` (all shipped type×action pairs
  are disjoint; a purpose-authored collision MUST fail) with its non-vacuity twin.
- **Single union authority (C-002)** — `src/charter/action_grain.py` is the sole
  home of the type⊕action union; the two former test-side unions now read
  `bundle.governance`.
- **Activation gating byte-identical (C-001)** — `existing_mission_types` /
  `activated_mission_types` / `.action_sequence` unchanged (regression-pinned in
  `TestGovernanceThunkSeversCoupling`).
- **Hot-path laziness (NFR-001)** — `.action_sequence` triggers no
  `load_action_index`; the union materializes only on first `.governance` access
  (spy-verified in `test_runtime_bridge_dispatch.py`).
- **DRG node contract** — `mission_type:<id>` nodes in `graph.yaml`, freshness-gated.
