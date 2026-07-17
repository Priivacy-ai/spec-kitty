# Contracts — Step authority (S-B)

**No external API / CLI-contract surface.** This mission is entirely internal to the doctrine layer: it makes
`step.yaml` (`MissionStep`) the single authority, derives `action_sequence`/`template_set` as in-process
projections, and re-points the DRG extractor + charter/runtime consumers at that seam. There is no new HTTP
endpoint, wire format, or public CLI contract.

The behavioral contracts this mission upholds are internal invariants, verified by tests (not external schemas):

- **Projection contract** — `project_action_sequence(steps)` / `project_template_set(steps)` (pure, deterministic; `src/doctrine/missions/step_projection.py`). Verified: `tests/doctrine/missions/test_step_projection.py`.
- **Behavior-preserving resolution** — all 4 built-in mission types resolve to their pre-mission authored `action_sequence`/`template_set` through the seam. Verified: `tests/runtime/test_runtime_seam.py`, `tests/doctrine/missions/test_softwaredev_roundtrip.py`, `tests/doctrine/missions/test_referential_integrity.py`.
- **DRG invariance** — 280 nodes / 757 edges / 10 orphans, fresh (`NFR-002`). Verified: `tests/doctrine/drg/migration/test_extractor_projection.py`.
- **Override seam** — `recommended_model_tier` is an advisory offer; charter/runtime override wins (`src/doctrine/missions/step_offer_seam.py`, consumed by `model_task_routing/evaluator.py`). Verified: `tests/doctrine/model_task_routing/test_override_precedence.py`.

This directory exists to satisfy the mission's path-convention gate; there is no OpenAPI/GraphQL/CLI schema to publish.
