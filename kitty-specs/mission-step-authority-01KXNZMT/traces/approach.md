# Approach Log — Step authority (S-B)

Tracer (seeded at planning; append during implement).

## Planning

- Grounded in ADR 2026-07-16-2 (D2/D4/D5/D6) + issue #2723, hardened by a 3-lens post-spec squad
  (alphonso/paula/renata, all LAND-WITH-EDITS) and two operator decisions (relocate+project; defer FR-009/FR-011).
- Baseline DRG captured: 280/757/10 fresh (#2712-bearing base) — the 0-delta anchor (NFR-002).
- 7-concern IC map with load-bearing sequencing: schema (IC-01) + projection seam (IC-02) + software-dev parity
  scaffold (IC-07) land GREEN before the cutover (IC-03/04 remove action_sequence/template_set from the YAML).
- Key grounded surfaces: MissionStep models.py:87; _STEP_YAML_TO_MODEL repo:120; MissionType.action_sequence
  models.py:183 (+ _validate_action_sequence:197); extractor.py:835/849; runtime consumers
  runtime_bridge_composition:186/321, decision:606, mission_type_profiles:496; override consumer
  model_task_routing/evaluator.py:229.

## Implementation

<!-- Append per-WP: what was edited, projection determinism, parity/DRG results, red-flagged plan steps. -->

## Verification

<!-- Record post-cutover: DRG 280/757/10 fresh; sw-dev parity green; 3-type referential-integrity; dispatch invariance; override precedence. -->
