# Design Decisions — Step authority (S-B)

Tracer (seeded at planning; append during implement). Records the *why*.

## DD-01 — Relocate order/membership onto the step (NOT keep-and-gate)

**Decision**: Add net-new `sequence_index` + `in_action_sequence` to `MissionStep`, **relocating** the order +
membership that only `action_sequence` encodes today, and make `action_sequence` a pure projection.

**Why (post-spec squad, unanimous)**: `action_sequence` carries order + membership (software-dev: 12 step.yaml,
only 5 in sequence) that is absent from `step.yaml` — `depends_on` is empty on 11/12 steps, so no topo sort or dir
order reproduces the authored sequence. Projecting from today's schema is a **false premise**. The operator chose
**relocate + project** over the lower-blast-radius **keep-action_sequence + consistency-gate** alternative — a true
physical single-authority. It's "promote," not "invent": the ordering data exists in `action_sequence`; it moves
onto the step. Trade-off accepted: the `MissionType` model must derive `action_sequence` via a cached seam
(NFR-007), a bigger blast radius (~7-9 WPs) than the gate approach.

## DD-02 — Projection seam lives in the doctrine layer (one module, both consumers)

**Decision**: One canonical module (`src/doctrine/missions/step_projection.py`) owns
`project_action_sequence`/`project_template_set`; both the doctrine DRG extractor AND the charter/runtime import it.

**Why**: The extractor is doctrine-layer; the runtime reads via charter. Charter depends on doctrine, not the
reverse — so the seam MUST live in doctrine to avoid a layering inversion, and MUST be a single implementation to
avoid a second projection that could drift (the exact split-brain we're closing). "One canonical seam" discipline.

## DD-03 — NFR-001 splits: parity (software-dev) vs referential-integrity (3 types)

**Decision**: Byte-for-byte parity is asserted ONLY for software-dev; the 3 types get referential-integrity.

**Why (squad F2)**: documentation/research/plan have no prior independently-authored `step.yaml` — their step.yaml
is authored FROM `action_sequence`, so projecting it back is **circular** (tautologically true, proves nothing).
Only software-dev has an independent flat form to preserve. Parity scaffold is transitional (C-006); the 3-type
referential-integrity (round-trip + moved-artifact byte-identity + missing→red) is the enduring check.

## DD-04 — Defer FR-009 (role/model consolidation) + FR-011 (MISSION_STEP_CONTRACT/D6)

**Decision**: S-B ships only `recommended_model_tier` + the override seam + one live consumer. The full ≥4-site
consolidation (FR-009) and the D6 contract graph primitive (FR-011) move to follow-ups under #2721.

**Why**: (a) FR-009 — 3 of the 4 role/model "authoring sites" are empty today; the one live site (WP-frontmatter
`agent_profile`) is per-WP instance-grain and cannot be a step cache. Full consolidation = routing surgery,
colliding with C-002. (b) FR-011 — expressing "typed I/O" needs a relation none of REQUIRES/SCOPE/INSTANTIATES
means → a net-new Relation, contradicting C-001; source (`built_in_step_contracts/`) is keyed by action-name and
incomplete. Deferring both keeps NFR-002 a clean **0-delta** assertion (no contract edges) and S-B bounded.

## DD-05 — `recommended_role` reuses `agent_profile`; only `recommended_model_tier` is net-new

**Decision**: Do not add a `recommended_role` field; the existing `MissionStep.agent_profile` IS the step's
advisory role offer. Add only `recommended_model_tier`.

**Why (squad F4)**: `agent_profile` already carries the step's advisory profile. A separate `recommended_role`
would be a redundant fifth field/authority. All new fields must be added to `_STEP_YAML_TO_MODEL`
(`mission_step_repository.py:120`) or `extra="forbid"` silently strips them (a parity test could pass while the
field is dropped — add a field-round-trip test).

## DD-06 — Missing prompts: seed blank prompt files, keep the field required (NOT optional)

**Decision (operator)**: `prompt_template` stays a **required** `str` — structure is enforced. The 16 prompt-less
steps (documentation 7 + research 5 guidelines-only; plan 4 content-less) get a **seeded blank/empty `prompt.md`**
so every step has a real prompt file and schema validation passes. A **red test on prompt emptiness/dummy-content**
flags each seeded blank until S-C (#2724) fills it.

**Why**: Making the field optional would weaken the schema and let prompt-less steps pass silently. A required field
+ seeded blank + emptiness red test **enforces the structure** (every step must have a prompt file) while surfacing
the content gap honestly and mechanically. A blank placeholder is not invented content (C-004) — it is an explicit,
red-flagged gap. Belongs to WP05 (seed + emptiness test), not WP01 (no schema relaxation).

<!-- Append DD-07+ during implement. -->
