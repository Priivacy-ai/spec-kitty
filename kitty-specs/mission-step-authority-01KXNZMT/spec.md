# Mission Specification: Step authority — step.yaml as single source

**Mission Branch**: `feat/mission-step-authority` (stacked on the S-A doc-alignment commit; S-A + S-B land together)
**Created**: 2026-07-16
**Status**: Draft
**Input**: S-B — make `step.yaml` (`MissionStep`) the single authority for a mission type's steps; derive `action_sequence`/`template_set` as projections; re-point the DRG extractor at the step authority (GitHub issue #2723, Prio-0 slice of step-model sub-epic #2721 under epic #2652). Grounded in ADR `docs/adr/3.x/2026-07-16-2-mission-type-step-authority-and-template-vocabulary.md` (D2/D4/D5/D6).

## Context & Motivation *(why this mission exists)*

A mission type's **step** is authored in two disconnected places today — a **split-brain**:

1. **The flat form** — `action_sequence` (ordered, curated step ids) + `template_set` (step→content-template map) in `src/doctrine/missions/mission_types/<type>.yaml`. This is the **ordering/membership authority**, read by **both** the DRG extractor (`extract_mission_type_edges`, `src/doctrine/drg/migration/extractor.py:835/849`) **and** the runtime (`runtime_bridge_composition.py:186,321`, `decision.py:606`, `mission_type_profiles.py:496`).
2. **The rich form** — the `MissionStep` model (`src/doctrine/missions/models.py:87`; carries `prompt_template`, `agent_profile`, `delegates_to`, `depends_on`), authored as `mission-steps/<type>/<step>/step.yaml` and read per-`(type, step)` by the runtime — the **per-step metadata authority**. It exists for **software-dev only** (12 steps, of which only 5 are in `action_sequence`); documentation / research / plan have **no** `step.yaml`.

These are two authorities for two things — *ordering/membership* (flat) vs *per-step metadata* (rich) — that both enumerate steps and can silently disagree. This mission makes **`step.yaml` (`MissionStep`) the single authority for both**: it **relocates** the order + membership onto the step (net-new `sequence_index` + `in_action_sequence` — the data exists in `action_sequence` today, it moves onto the step), derives `action_sequence`/`template_set` as **read-projections**, removes them from the YAML, and switches **every** consumer (extractor + runtime) to one projection seam — *the graph reads what the runtime reads*.

Per ADR D2 this is **promote, not invent**: a step **is** the existing `ACTION` node enriched — no new `NodeKind`, **no new `Relation`**, the `NodeKind.ACTION` enum and `action:*` URN unchanged (same boundary S-A held). The mission adds one net-new advisory field (`recommended_model_tier`) and a `template` reference `(artifact_key, template_file)` behind an **override seam** (D4): doctrine *offers*, charter/runtime retain **routing authority**. `recommended_role` reuses the existing `agent_profile` field — no redundant field. **Deferred to follow-ups (operator + squad), tracked under epic #2721:** the full ≥4-site role/model consolidation (3 sites are empty, the live one is per-WP grain) and `MISSION_STEP_CONTRACT`/D6 (would need a net-new Relation).

**Scope decision (operator-confirmed):** the authority→projection machinery is type-general, and S-B **unifies all four shipped types onto the software-dev step structure**. software-dev already uses the canonical layout `mission-steps/<type>/<step>/{step.yaml, prompt.md, guidelines.md}`. S-B **moves** documentation/research/plan's existing per-step content (today under `missions/<type>/actions/<step>/` and `missions/<type>/templates/`) into that **same** `mission-steps/<type>/<step>/` structure/location and authors a `step.yaml` authority for each step — one consistent structure for all four types.

**No content is invented.** Where a step's prompt/exemplar content is genuinely **missing**, S-B leaves a **RED test** documenting the gap. This is an *accepted outcome* — a red test marks a real problem honestly (red-first discipline), and **S-C (#2724) fills the missing content**. S-B is structure/authority-only; it moves what exists and red-flags what does not, rather than papering over gaps with invented content.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A doctrine author edits a step in ONE place (Priority: P1)

A doctrine author changes a mission-type step (its prompt, its ordering, its agent profile). They edit `step.yaml` — the single authority — and **both** the runtime dispatch **and** the DRG see the change. There is no second place (`action_sequence`/`template_set`) to keep in sync, because those are now derived.

**Why this priority**: Eliminating the split-brain is the mission's reason to exist; every other requirement serves this single-authority outcome.

**Independent Test**: Change a step in `step.yaml`; confirm the projected `action_sequence`/`template_set` and the DRG both reflect it without editing the flat form; confirm `spec-kitty next` dispatch is unchanged in behavior.

**Acceptance Scenarios**:

1. **Given** steps authored in `step.yaml` with `sequence_index`/`in_action_sequence`, **When** the projection runs, **Then** the derived `action_sequence` equals the `in_action_sequence: true` steps ordered by `sequence_index`, and `template_set` equals the step `template` map — with `action_sequence`/`template_set` no longer present in the YAML.
2. **Given** the DRG extractor and the runtime consumers, **When** they resolve a mission type's steps, **Then** both read the **one projection seam** (not a retained flat field), producing the same `mission_type:X → action:X/<step>` `requires` edges (0 edge-count delta).
3. **Given** software-dev (12 step.yaml, 5 in sequence), **When** the projection is computed, **Then** the projected `action_sequence`/`template_set` equal today's authored values **byte-for-byte** (NFR-001a parity).

### User Story 2 - All four shipped types share one authority (Priority: P1)

A maintainer of documentation / research / plan (which had no `step.yaml`) now finds a `step.yaml` authority for each, in the same `mission-steps/<type>/<step>/` layout as software-dev. Where per-step content exists it is moved in; where it is missing (all four `plan` steps, and any others) a red test names the gap for S-C.

**Why this priority**: "Single authority" is only real if the authority exists for every shipped type; leaving 3 of 4 on the flat form would re-create the split-brain.

**Independent Test**: For each of documentation/research/plan, confirm a `step.yaml` authority exists per sequence step with correct `sequence_index`/`in_action_sequence`; confirm the projected `action_sequence` round-trips to the pre-mission value (NFR-001b); confirm steps with missing content have a red test (not invented content).

**Acceptance Scenarios**:

1. **Given** documentation/research/plan, **When** S-B lands, **Then** each has `step.yaml` descriptors covering its sequence, referencing **existing** content where present and leaving a **red test** where content is missing (no new content authored).
2. **Given** each of the 4 types, **When** the projection runs, **Then** the projected `action_sequence` (and `template_set` where non-null) equals the pre-mission authored value (byte-for-byte for software-dev; round-trip for the 3 types).

### User Story 3 - Doctrine offers role/model hints; routing stays with charter/runtime (Priority: P2)

A step declares an advisory role (its existing `agent_profile`) and a net-new `recommended_model_tier`. These are **offers** — a charter/runtime override seam lets the operator's routing win. Doctrine never becomes the routing authority.

**Why this priority**: D4 is a correctness boundary — adding a model-tier offer to the step is a win only if it stays an *offer*, never a routing authority. (The broader consolidation of the ≥4 role/model sites is a deferred follow-up.)

**Independent Test**: Set a step's `recommended_model_tier`; confirm it surfaces as a hint but a charter/runtime override takes precedence; confirm routing decisions are still made by charter/runtime, not doctrine.

**Acceptance Scenarios**:

1. **Given** a step with an `agent_profile` (advisory role) and `recommended_model_tier`, **When** charter/runtime specify a routing override, **Then** the override wins and doctrine's value is the advisory **offer** only, read through the one named seam (FR-008).
2. **Given** `recommended_model_tier` is net-new (no consumer today), **When** S-B ships the seam, **Then** at least one live consumer reads the offer so the override precedence is falsifiable (NFR-003). *(Note: the full consolidation of the ≥4 role/model authoring sites — 3 of which are empty today, the live one being per-WP instance-grain — is a deferred follow-up per C-005. S-B makes the step the single source of the model-tier **offer**, not the routing decision.)*

### Edge Cases

- **A step present but absent from the sequence** (e.g. `retrospect`, and software-dev's 7 non-sequence steps): it carries `in_action_sequence: false`, is excluded from the projection, and stays non-orphan via its own `scope` edges (D5).
- **A type with `template_set: null`** (documentation/research/plan today): every step's `template` reference stays empty so the projection yields `null` — S-B adds the schema slot but does **not** populate content.
- **The projected software-dev flat form would differ from the authored one**: this is a defect (NFR-001a parity is load-bearing) — the parity scaffold must fail loudly, not silently reconcile. (For the 3 types the round-trip is referential-integrity, NFR-001b — not parity.)
- **A step's prompt/exemplar content is genuinely missing**: S-B does NOT invent it. It moves what exists into the unified `mission-steps/<type>/<step>/` structure and leaves a **red test** documenting the missing content (accepted outcome — a real problem, per red-first discipline); S-C (#2724) fills it. A temporarily-red gate for those steps is expected, not a mission failure.
- **DRG counts change**: any change from the 280/757/10 baseline must be **intentional and asserted** (step-attribute edges), never accidental orphan growth.

## Requirements *(mandatory)*

### Functional Requirements

| ID | Title | User Story | Priority | Status |
|----|-------|------------|----------|--------|
| FR-001 | step.yaml is the single authority | As a doctrine author, I want `step.yaml` (`MissionStep`) to be the single authoritative source for a mission type's steps so I edit a step in exactly one place. | High | Open |
| FR-014 | Relocate order + membership onto the step | As a maintainer, I want net-new `sequence_index` (order) and `in_action_sequence` (membership) fields on the step schema, **relocating** the order/membership that lives only in `action_sequence` today onto the step — so the step carries everything `action_sequence` encodes (12 step.yaml, 5 in sequence for software-dev). This is the basis the projection needs; it is authored (relocated), not derived from `depends_on`. | High | Open |
| FR-002 | action_sequence is a projection | As a maintainer, I want `action_sequence` derived as a read-projection of the step authority (steps with `in_action_sequence: true`, ordered by `sequence_index`), removed as an independently-authored field from `mission_types/*.yaml`. | High | Open |
| FR-003 | template_set is a projection | As a maintainer, I want `template_set` derived as a read-projection of the step authority (step→`(artifact_key, template_file)` map), removed as an independently-authored field. software-dev projects `{spec, plan}`; the 3 null-`template_set` types project `null`. | High | Open |
| FR-004 | Extractor reads the projection | As a graph consumer, I want the DRG extractor (`extract_mission_type_edges`, `extractor.py:835/849`) to emit the mission-type/step `requires` edges from the **projection** of the step authority (never a directory listing), so the graph reads what the runtime reads and edge counts are unchanged. | High | Open |
| FR-012 | Switch ALL flat-form consumers | As a maintainer, I want **every** `action_sequence` consumer switched to the one projection seam — the extractor (`extractor.py:849`), the runtime (`runtime_bridge_composition.py:186,321`, `decision.py:606`), and `mission_type_profiles.py:496` — so no consumer re-reads a retained flat authority (which would be a 5th authority, C-003). | High | Open |
| FR-005 | Unify all 4 types onto the step structure | As a maintainer, I want documentation/research/plan's existing per-step content **moved** into the canonical `mission-steps/<type>/<step>/` layout (matching software-dev) with a `step.yaml` authority per step, so all four types share one structure and authority. | High | Open |
| FR-013 | Surface missing content as red tests | As a maintainer, I want steps whose prompt content is genuinely missing flagged by a **red test** (not invented content), so the gap is surfaced honestly and closed by S-C (#2724). Post-plan census: the disposition set is **16 steps** — documentation (7) + research (5) have `guidelines.md` but **no `prompt.md`**, and `plan` (4) has neither. **`prompt_template` stays required — structure enforced.** For the 16, seed a **blank/empty `prompt.md`** so every step has a real (but empty) prompt file; a **red test on prompt emptiness/dummy-content** flags each seeded blank until S-C fills it. A blank placeholder is not invented content; a temporarily-red emptiness gate is accepted, not a failure. | High | Open |
| FR-006 | Add recommended_model_tier (net-new) | As a doctrine author, I want a net-new advisory `recommended_model_tier` field on the step schema (authored nowhere today), added to the `_STEP_YAML_TO_MODEL` allowlist so it is not silently stripped (`extra="forbid"`). | Medium | Open |
| FR-007 | Add step template reference | As a doctrine author, I want a `template` reference field carrying `(artifact_key, template_file)` on the step schema (the projection basis for `template_set`). software-dev's `specify`/`plan` steps reference the **existing** `spec-template.md`/`plan-template.md` (a reference to existing files = structure, not content); the 3 types stay null. CONTENT authoring is S-C. | Medium | Open |
| FR-008 | Override seam (offers, not routing) | As an operator, I want `recommended_model_tier` (and the existing `agent_profile` as the step's advisory role) treated as doctrine **offers** read through **one named seam** with a defined precedence (charter/runtime override > step offer), shipping **at least one live consumer** of `recommended_model_tier` so the seam is falsifiable. | High | Open |
| FR-010 | Retain scope edges | As a graph consumer, I want the governing-doctrine `scope` edges retained (D5) so steps with `in_action_sequence: false` (e.g. `retrospect`) stay non-orphan. | Medium | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001a | Parity (software-dev) | For software-dev — the only type with an independently-authored flat form — the projected `action_sequence` **and** `template_set` equal the pre-mission authored values **byte-for-byte**. Proven by a transitional parity test (C-006) before `action_sequence`/`template_set` are removed from the YAML. This is the genuine behavior-preserving proof (12 step.yaml → 5-entry sequence). | Reliability | High | Open |
| NFR-001b | Structural correctness (3 types) | For documentation/research/plan — whose `step.yaml` is authored **from** `action_sequence`, making a parity claim circular — each authored `step.yaml` round-trips to the current `action_sequence`, and every referenced `mission-steps/<type>/<step>/` artifact that exists is moved byte-identical. Missing content is exempt (red test, FR-013). This is referential-integrity, not parity. | Reliability | High | Open |
| NFR-002 | Zero DRG delta | With the `MISSION_STEP_CONTRACT`/D6 contract edges deferred, the extractor re-point projects the **same** edges — post-mission node/edge/orphan counts equal the baseline **280 / 757 / 10**, graph fresh (#2712-bearing base). Any nonzero delta is a defect and asserted against. | Reliability | High | Open |
| NFR-003 | No routing authority leak | Doctrine `recommended_*` / step offers never override a charter/runtime routing decision — verified by a test with an override present against the live consumer shipped by FR-008. | Correctness | High | Open |
| NFR-004 | Lint/type/complexity clean | `ruff` + `mypy --strict` exit 0 with zero new suppressions; new/changed functions complexity ≤15; literals repeated ≥3× hoisted to constants. | Maintainability | High | Open |
| NFR-005 | Graph freshness | `spec-kitty doctrine regenerate-graph --check` reports **fresh** after the mission (sharded layout intact). | Reliability | High | Open |
| NFR-006 | Dispatch invariance (3 types) | Adding `step.yaml` to documentation/research/plan does not change `spec-kitty next` dispatch — verified by a per-type before/after dispatch-decision test (the composed-action path stays inert while `agent_profile` is null). | Reliability | High | Open |
| NFR-007 | No hot-path I/O regression | Deriving `action_sequence` on the `MissionType` model must not inject uncached filesystem/layered-override I/O onto the runtime hot paths (`runtime_bridge_composition.py`, `decision.py`, `mission_type_profiles.py`); the projection is computed through a cached seam. | Performance | High | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | No new NodeKind or Relation | A step is the existing `ACTION` enriched (D2); no new `NodeKind` and **no new `Relation`**, and the `NodeKind.ACTION` enum + `action:*` URN scheme are unchanged. (Reinforced by deferring `MISSION_STEP_CONTRACT`/D6, which would have needed a typed-I/O relation.) | Technical | High | Open |
| C-002 | Routing stays charter/runtime | Doctrine only **offers** role/model (D4); routing authority remains with charter/runtime — do not move routing into doctrine. | Technical | High | Open |
| C-003 | One ordering authority, not a 5th | The step becomes the single ordering/membership authority; every consumer switches to its projection (FR-012). Leaving `action_sequence` authored **and** adding step authority would create a 5th parallel authority — a failure. | Technical | High | Open |
| C-004 | No content invented; move + red-flag | S-B **moves** existing per-step content into the unified structure + authors the `step.yaml` authority + the `template` **reference slot** (references to existing files) — it does NOT invent exemplar content. Missing prompts/exemplars are surfaced by **red tests** (accepted) and filled by S-C (#2724 — content + graph-backing `template_set` as `instantiates` edges; closes #883 + the #2689 uncreatable regression). | Technical | High | Open |
| C-005 | Deferred to follow-up slices | Out of scope (own follow-ups under epic #2721): the **role/model consolidation** across the ≥4 sites (3 are empty today; the live one is per-WP instance-grain); **`MISSION_STEP_CONTRACT`/D6** (risks a net-new Relation; source `built_in_step_contracts/` keyed by action-name, incomplete); **S-D** substeps (#2725), **S-E** guards (#2726). | Business | High | Open |
| C-006 | Parity tests are transitional | The software-dev projection-parity scaffold (NFR-001a) is a disposable swap scaffold — added at the start, deleted before merge; enduring coverage is the module/integration-level projection tests + the 3-type referential-integrity check (NFR-001b), which is **not** a parity tautology and stays. | Technical | Medium | Open |
| C-007 | Land with S-A | This mission stacks on the S-A doc-alignment commit and lands together with it in one operator merge; we open no PR. Execution lanes base on the S-A-bearing HEAD (`feat/mission-step-authority`), NOT origin/main, or the 0-delta baseline measures against the wrong base. | Process | Medium | Open |
| C-008 | Scope-fence `template_set` overload | Only `MissionType.template_set` (the `dict[artifact_key→file]`) projects. The charter/project **`doctrine.template_set` scalar** (e.g. `"software-dev-default"`) is a **different domain object** — the charter template-set *selection* authority (`charter/resolver.py`, `compiler.py`, `compact.py`, `generator.py`, `catalog.py`, `prompt_builder.py`, `scope_router.py`, `governance-profile.yaml`) — and is **OUT OF SCOPE**; switching it to the step projection is corruption. The single-ordering-authority claim applies to **built-in** mission types; extension types still order via `org_pack_loader._merge_action_sequence` (a follow-up). | Technical | High | Open |

### Key Entities

- **Step (authority)** — `MissionStep` (`models.py:87`), authored as `step.yaml`. The single source for a mission type's steps. S-B adds `sequence_index` + `in_action_sequence` (order/membership, relocated from `action_sequence`), `recommended_model_tier` (net-new advisory), and a `template` reference `(artifact_key, template_file)` to its schema.
- **`action_sequence` (projection)** — ordered ids of the steps with `in_action_sequence: true`, sorted by `sequence_index`. Was independently authored; becomes a pure read-projection removed from the YAML.
- **`template_set` (projection)** — step→`(artifact_key, template_file)` map, derived from the step `template` references. Was independently authored (#2689); becomes a read-projection.
- **`recommended_role`** — reuses the existing `MissionStep.agent_profile` field (the step's advisory role/profile offer); S-B does **not** add a redundant field. Only `recommended_model_tier` is net-new.
- **Override seam** — the one named seam where doctrine offers (`agent_profile`, `recommended_model_tier`) are read and charter/runtime routing overrides win, with a live consumer (FR-008).
- **Projection seam** — the single canonical `project_action_sequence(step_authority)` / `project_template_set(...)` module consumed by **both** the doctrine extractor and the charter/runtime, avoiding a layering violation or a second implementation.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Editing a step in `step.yaml` (order, membership, template ref) changes the projected flat form and the DRG with **0** edits to any `mission_types/*.yaml` (which no longer carry `action_sequence`/`template_set`).
- **SC-002**: For **software-dev**, projected `action_sequence` + `template_set` equal the pre-mission authored values **byte-for-byte** (NFR-001a parity green); for the 3 types, each `step.yaml` round-trips to the current `action_sequence` and moved artifacts are byte-identical (NFR-001b).
- **SC-007**: All four types use the canonical `mission-steps/<type>/<step>/` layout; any step with missing prompt/exemplar content is marked by a red test naming the gap for S-C (0 invented content).
- **SC-003**: The DRG extractor reads the projection; post-mission node/edge/orphan counts equal **280 / 757 / 10** (0 delta, graph fresh).
- **SC-004**: A charter/runtime routing override wins over the step's doctrine offer in **100%** of tested cases against the live consumer (no routing-authority leak).
- **SC-005**: **Every** `action_sequence` consumer (extractor + `runtime_bridge_composition.py:186/321` + `decision.py:606` + `mission_type_profiles.py:496`) reads the one projection seam — **0** consumers re-read a retained flat authority.
- **SC-008**: `spec-kitty next` dispatch is byte-identical before/after adding `step.yaml` to documentation/research/plan (NFR-006).
- **SC-006**: All gates green — `regenerate-graph --check` fresh, `ruff` + `mypy --strict` exit 0 (zero new suppressions), arch/DRG suites pass.

## Assumptions

- **Order/membership is authored, not derived.** `sequence_index`/`in_action_sequence` are relocated from `action_sequence` (the data exists there today); the projection is a pure function of those fields — it is **not** inferred from `depends_on` (empty on 11/12 software-dev steps) or directory order (alphabetical).
- **Content availability is uneven** (verified with the squad): documentation and research have `actions/<step>/guidelines.md` for every sequence step; **the `plan` type has NO prompt/guidelines for any of its 4 sequence steps** (`plan/actions/{specify,research,plan,review}/` hold only an empty-grain `index.yaml`). So all 4 `plan` steps hit the FR-013 red-test / S-C path — `plan`'s `step.yaml` cannot be authored "structure-only referencing existing content." The plan phase must inventory have-vs-lack per step.
- The `action:*` node population already exists for all steps of all 4 types (minted by #2712 via `rglob("actions/*/index.yaml")`, `extractor.py:674`); S-B re-sources the edges, it does not mint new action nodes.
- The `MissionType` model deriving `action_sequence` from the step repo must go through a **cached** seam so no uncached filesystem I/O lands on the runtime hot paths (NFR-007).

## Traceability

| Requirement | Source |
|-------------|--------|
| FR-001, FR-002, FR-003 | ADR 2026-07-16-2 D2; issue #2723 (authority + projections) |
| FR-014 | Post-spec squad (alphonso/paula/renata): `action_sequence` order+membership absent from `step.yaml`; relocate onto the step (operator: relocate + project) |
| FR-004, FR-012 | ADR D2; `extractor.py:835/849`; runtime consumers `runtime_bridge_composition.py:186/321`, `decision.py:606`, `mission_type_profiles.py:496` |
| FR-005, FR-013, C-004 | Operator scope decisions: unify all 4 types onto software-dev's `mission-steps/<type>/<step>/` layout (move existing content); missing prompts/exemplars → red test (accepted), content filled by S-C #2724 |
| FR-006, FR-007, FR-008 | ADR D4; `recommended_model_tier` net-new; template ref `(artifact_key, file)`; override seam + live consumer |
| FR-010 | ADR D5; `scope` edges retained via `in_action_sequence: false` |
| NFR-001a, NFR-001b, C-006 | Post-spec squad F2: parity (software-dev) vs referential-integrity (3 types); transitional scaffold |
| NFR-002, NFR-005 | DRG invariance; #2712 baseline 280/757/10; 0 delta (`MISSION_STEP_CONTRACT`/D6 deferred) |
| NFR-006, NFR-007 | Post-spec squad: per-type dispatch invariance; hot-path caching (`MissionType`↔repo) |
| C-001, C-002, C-003 | ADR D2/D4; step = enriched ACTION; no new Relation; routing stays charter/runtime; one ordering authority |
| C-005 | Operator decision (defer role/model consolidation + `MISSION_STEP_CONTRACT`/D6); Sub-epic #2721 children #2725 (S-D) / #2726 (S-E) |
| C-007 | Stacked-branch landing with S-A |
