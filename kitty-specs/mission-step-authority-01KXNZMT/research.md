# Research — Step authority (S-B)

Consolidated design resolution. Most decisions were settled by the ADR + the post-spec squad; this records the
resolved questions and their rationale.

## Decision: projection direction — relocate order onto the step, then project

- **Decision**: Add `sequence_index` + `in_action_sequence` to `MissionStep` (relocated from `action_sequence`); project the flat forms.
- **Rationale**: `action_sequence` encodes order + membership absent from `step.yaml` (12 step.yaml, 5 in sequence; `depends_on` empty 11/12). Projecting from today's schema is impossible → false premise. Operator chose the true physical single-authority.
- **Alternatives considered**: keep `action_sequence` authored + a consistency gate (drift = hard-fail). Lower blast radius, still kills the split-brain via a gate, but is "logical" not "physical" single-authority. Rejected by operator in favor of relocate+project.

## Decision: projection seam location — doctrine layer, one module

- **Decision**: `src/doctrine/missions/step_projection.py`, consumed by both the extractor and the runtime.
- **Rationale**: charter depends on doctrine; the seam in doctrine avoids a layering inversion and a second, drift-prone implementation.
- **Alternatives**: seam in charter (layering inversion — extractor can't import it); two implementations (drift risk — re-creates the split-brain). Both rejected.

## Decision: NFR-001 splits parity vs referential-integrity

- **Decision**: byte-parity asserted only for software-dev; 3 types get round-trip + referential-integrity.
- **Rationale**: the 3 types' step.yaml is authored FROM `action_sequence`; projecting back is circular. Only software-dev has an independent prior flat form.
- **Alternatives**: "byte-for-byte for all 4" — rejected (tautological for 3 types, steers a meaningless test).

## Decision: defer FR-009 + FR-011

- **Decision**: ship `recommended_model_tier` + override seam + one live consumer; defer full role/model consolidation (FR-009) and MISSION_STEP_CONTRACT/D6 (FR-011) to follow-ups under #2721.
- **Rationale**: FR-009 is routing surgery (C-002 collision; 3/4 sites empty, live one per-WP grain); FR-011 needs a net-new Relation (C-001 conflict) and an incomplete source. Deferring keeps NFR-002 a clean 0-delta.
- **Alternatives**: full #2723 D2/D4/D5/D6 in one mission (~10-14 WPs, non-zero DRG delta, higher sprawl) — rejected by operator.

## Decision: `recommended_role` = existing `agent_profile`

- **Decision**: no new `recommended_role` field; `agent_profile` is the advisory role offer. Only `recommended_model_tier` is net-new.
- **Rationale**: avoids a redundant fifth field/authority (squad F4). All new fields go through `_STEP_YAML_TO_MODEL` (else `extra="forbid"` strips them).

## Open question deferred to implementation (not blocking)

- **`MissionType` model caching topology** — whether the cached `action_sequence` derivation lives on the model, the repository, or a memoized accessor. Constraint: no uncached hot-path I/O (NFR-007). Decided in IC-04 during implement; the constraint (cached) is fixed, the mechanism is an implementation detail.
