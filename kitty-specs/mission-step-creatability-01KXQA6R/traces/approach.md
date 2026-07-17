# Approach Log — Mission-Type Creatability (S-C)

Tracer (seeded at planning; append during implement).

## Planning

- Grounded in ADR 2026-07-16-2 (D3) + its 2026-07-17 Amendment (retire `template_set` as a persisted field), issue #2724, and four squads: research (robbie/alphonso/paula), adversarial verification (paula/alphonso/renata — LAND), the Q1 trace, and spec-review (renata/alphonso/paula — plan-ready).
- Baseline DRG: 280 nodes / 757 edges / 10 orphans fresh (`test_extractor_projection.py:40-42`) — the anchor NFR-002 grows intentionally from.
- 8-concern IC map with tidy-first sequencing A→B→C and single-owner shared seams (`step_projection.py` → IC-01; `test_prompt_emptiness.py` → IC-05; `extractor.py` → IC-06).
- Key grounded surfaces: `MissionType.template_set` models.py:259; `_inject_projected_fields` mission_type_repository.py:198-202 (drop `:200-202`, keep `:199`); `_resolve_template_set_slot` mission_type_profiles.py:744; `project_template_set` step_projection.py:88; `resolve_configured_template` resolver.py:395; creation caller `mission_creation.py:351-355` (`artifact_kind="spec"`); `extract_mission_type_edges` extractor.py:864; `template_catalog.template_urn`/`resolve_template_by_id`.

## Implementation

<!-- Append per-WP: what was edited, cutover atomicity proof, per-type content provenance, N (final template-ref count) + DRG delta, arch-marker re-baseline. -->

## Verification

<!-- Record: software-dev byte-parity + canonical --json order; pack-template_set-fails-loudly; NFR-003 one-walk; all 3 types creatable; 16 prompts non-empty + substance-reviewed; DRG 280+N/757+N orphans=10 fresh; by-URN==by-name + override-wins; cross-type template_file uniqueness. -->
