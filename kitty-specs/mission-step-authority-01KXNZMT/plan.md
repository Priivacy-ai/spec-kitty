# Implementation Plan: Step authority — step.yaml as single source (S-B)

**Branch**: `feat/mission-step-authority` (stacked on the S-A commit) | **Date**: 2026-07-16 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `kitty-specs/mission-step-authority-01KXNZMT/spec.md` (committed `8bde47098`, hardened by a 3-lens post-spec squad + two operator decisions).

## Summary

Collapse the mission-type **step split-brain** by making `step.yaml` (`MissionStep`) the single authority. The
order + membership that live only in `action_sequence` today are **relocated** onto the step (net-new
`sequence_index` + `in_action_sequence`); `action_sequence`/`template_set` become **read-projections** through one
canonical seam that **both** the DRG extractor and the runtime consume; every flat-form consumer is switched to it.
All four mission types are unified onto software-dev's `mission-steps/<type>/<step>/` layout (moving existing
content; red-flagging genuinely missing content for S-C). Two advisory schema fields (`recommended_model_tier`,
a `template` reference) land behind a charter/runtime **override seam** with a live consumer.

The mission is behavior-preserving except the intentional schema additions: **DRG stays 280/757/10 fresh (0
delta)**; software-dev's projected `action_sequence`/`template_set` equal today's authored values byte-for-byte;
`spec-kitty next` dispatch is unchanged. FR-009 (full role/model consolidation) and FR-011 (MISSION_STEP_CONTRACT /
D6) are **deferred** to follow-ups (operator + squad decision), which keeps NFR-002 a clean 0-delta assertion and
C-001 at "no new NodeKind **or Relation**".

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: `src/doctrine/missions/` (`models.py`, `mission_step_repository.py`), `src/doctrine/drg/migration/extractor.py`, `src/doctrine/model_task_routing/evaluator.py`; charter/runtime consumers (`runtime_bridge_composition.py`, `decision.py`, `mission_type_profiles.py`). No new dependencies.
**Storage**: N/A — YAML/Markdown doctrine data + a git file move; no DB migration.
**Testing**: pytest — a **transitional parity scaffold** (software-dev, C-006), **referential-integrity** tests (3 types), **DRG 0-delta** + freshness (`spec-kitty doctrine regenerate-graph --check`), **per-type dispatch-invariance** (`spec-kitty next`), **override-precedence** (against the live consumer), and `tests/architectural/`. ATDD red-first: the parity scaffold + schema land **before** `action_sequence`/`template_set` are removed from the YAML.
**Target Platform**: Linux/CI
**Project Type**: single (doctrine + drg + charter/runtime consumers)
**Performance Goals**: no hot-path regression — `MissionType` deriving `action_sequence` via the step repo must go through a **cached** seam (NFR-007); the runtime paths (`runtime_bridge_composition.py`, `decision.py`, `mission_type_profiles.py`) must not gain uncached filesystem/layered-override I/O.
**Constraints**: DRG **280/757/10 fresh, 0 delta** (NFR-002); no new `NodeKind`/`Relation` (C-001); routing stays charter/runtime (C-002); one ordering authority — every consumer switches (C-003); no content invented — move + red-flag (C-004); `ruff` + `mypy --strict` clean, zero new suppressions, complexity ≤15.
**Scale/Scope**: 4 mission types; software-dev has 12 step.yaml (5 in sequence); ~7 implementation concerns → est. **7–9 WPs**.

### Baseline (proof anchor)

```
spec-kitty doctrine regenerate-graph --check → fresh
BASELINE  nodes=280  edges=757  orphans=10   (#2712-bearing base)
```

### Key existing surfaces (grounded)

| Surface | Location | Role in S-B |
|---------|----------|-------------|
| `MissionStep` | `src/doctrine/missions/models.py:87` | gains `sequence_index`, `in_action_sequence`, `recommended_model_tier`, `template` ref; `recommended_role` **reuses** `agent_profile` |
| `_STEP_YAML_TO_MODEL` | `src/doctrine/missions/mission_step_repository.py:120` | new fields MUST be added here — model is `extra="forbid"`, else silently stripped |
| `MissionType.action_sequence` / `template_set` | `src/doctrine/missions/models.py:183-184` (`_validate_action_sequence` :197) | become projections; the non-empty validator must move to/through the projection, not the raw field |
| `extract_mission_type_edges` | `src/doctrine/drg/migration/extractor.py:835/849` | re-point to read the projection (never a dir listing); 0 edge delta |
| runtime consumers | `runtime_bridge_composition.py:186,321`, `decision.py:606`, `mission_type_profiles.py:496` | switch to the projection seam (C-003) |
| model-tier consumer | `src/doctrine/model_task_routing/evaluator.py:229` (`evaluate`) | the FR-008 live consumer of `recommended_model_tier` |

## Charter Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Single canonical authority** — PASS (the point): step.yaml becomes the one authority; one projection seam; every consumer switched.
- **Architectural alignment / layering** — PASS: projection seam lives in the **doctrine** layer so the doctrine extractor and charter/runtime both import it (charter depends on doctrine, not the reverse). No layering inversion.
- **ATDD-first / red-first** — PASS: parity scaffold + schema precede YAML-field removal; missing content is honestly red (FR-013).
- **Architectural gate discipline** — PASS: DRG 0-delta + freshness asserted; no gate relaxed.
- **DDD tiered rigour** — PASS: core doctrine model changes carry focused tests; the projection is a pure, testable function.
- **No new primitives** — PASS: no new `NodeKind`/`Relation` (FR-011/D6 deferred).

No unjustified violations → Complexity Tracking empty.

## Project Structure

### Documentation (this mission)

```
kitty-specs/mission-step-authority-01KXNZMT/
├── plan.md · research.md · data-model.md · quickstart.md
├── issue-matrix.md (seeded) · checklists/requirements.md
├── traces/{design-decisions,approach,tooling-friction}.md
└── tasks.md               # Phase 2 (/spec-kitty.tasks — NOT here)
```

### Source Code (repository root)

```
src/doctrine/missions/
├── models.py                     # MissionStep + MissionType schema changes
├── mission_step_repository.py    # _STEP_YAML_TO_MODEL allowlist
├── step_projection.py            # NEW — the canonical projection seam (project_action_sequence/template_set)
├── mission_types/*.yaml          # REMOVE action_sequence + template_set (cutover)
└── mission-steps/<type>/<step>/  # unify all 4 types here (move content + step.yaml)
src/doctrine/drg/migration/extractor.py   # re-point to the projection
src/doctrine/model_task_routing/evaluator.py  # override-seam live consumer
# runtime consumers switched: runtime_bridge_composition.py, decision.py, mission_type_profiles.py
tests/…                           # parity scaffold, referential-integrity, dispatch-invariance, DRG 0-delta
```

**Structure Decision**: The projection seam is a NEW pure module in `src/doctrine/missions/` (proposed
`step_projection.py`) consumed by both the doctrine extractor and the charter/runtime — one implementation, no
layering inversion, no second copy. The `MissionType` model consumes the projection through a **cached** accessor
(NFR-007) rather than reading the filesystem on hot paths.

## Complexity Tracking

*No Charter Check violations — intentionally empty.*

## Implementation Concern Map

> Concerns are NOT work packages. `/spec-kitty.tasks` maps them to WPs. Sequencing is load-bearing: the schema
> (IC-01) + projection seam (IC-02) + software-dev parity scaffold (IC-07) MUST land and be green **before** the
> cutover (IC-03/IC-04 remove `action_sequence`/`template_set` from the YAML). Note `models.py` is touched by both
> IC-01 (MissionStep) and IC-04 (MissionType) — linearize those or keep them in one WP to avoid an ownership clash.

### IC-01 — Step schema extension

- **Purpose**: Add `sequence_index` (int), `in_action_sequence` (bool), `recommended_model_tier` (advisory), and a `template` ref `(artifact_key, template_file)` to `MissionStep`; register all in `_STEP_YAML_TO_MODEL`. `recommended_role` reuses `agent_profile`.
- **Requirements**: FR-014, FR-006, FR-007.
- **Surfaces**: `models.py` (MissionStep), `mission_step_repository.py:120`.
- **Depends-on**: none (first).
- **Risks**: `extra="forbid"` silently strips un-allowlisted fields — a parity test can pass while a field is dropped; add a field-round-trip test.

### IC-02 — Projection seam (canonical, doctrine-layer)

- **Purpose**: New pure module `project_action_sequence(steps)` / `project_template_set(steps)` — `action_sequence` = `in_action_sequence:true` steps ordered by `sequence_index`; `template_set` = step template map. The single seam both the extractor and runtime consume.
- **Requirements**: FR-002, FR-003, C-003 (one seam).
- **Surfaces**: `src/doctrine/missions/step_projection.py` (new).
- **Depends-on**: IC-01.
- **Risks**: determinism (stable sort by `sequence_index`) for the freshness gate; layering (must live in doctrine, not charter).

### IC-03 — Extractor re-point

- **Purpose**: `extract_mission_type_edges` emits `mission_type→action` `requires` edges from the projection (not `action_sequence`, never a dir listing); assert 0 edge delta.
- **Requirements**: FR-004, NFR-002.
- **Surfaces**: `extractor.py:835/849`.
- **Depends-on**: IC-02 + software-dev parity green (IC-07).
- **Risks**: reading the 12 step.yaml dir instead of the projected 5 → edge blow-up; must read the projection.

### IC-04 — Runtime consumer switch + cutover + caching

- **Purpose**: Switch `runtime_bridge_composition.py:186/321`, `decision.py:606`, `mission_type_profiles.py:496` and the `MissionType` model to the projection seam (cached, NFR-007); **remove** `action_sequence`/`template_set` from `mission_types/*.yaml`; reconcile `_validate_action_sequence`.
- **Requirements**: FR-012, NFR-007, C-003.
- **Surfaces**: the three runtime files, `models.py` (MissionType), `mission_types/*.yaml`.
- **Depends-on**: IC-02 + IC-03 + parity green.
- **Risks**: a missed consumer = a 5th authority (C-003); hot-path uncached I/O (NFR-007); the non-empty `action_sequence` validator.

### IC-05 — Four-type structural unification + red-flags

- **Purpose**: Move documentation/research per-step content into `mission-steps/<type>/<step>/`; author `step.yaml` (with `sequence_index`/`in_action_sequence`) for all sequence steps of all 4 types; **red test** every step with genuinely missing content (all 4 `plan` steps + any others) — no content invented.
- **Requirements**: FR-005, FR-013, C-004, NFR-001b.
- **Surfaces**: `src/doctrine/missions/mission-steps/<type>/…`, moving from `missions/<type>/actions/…` + `templates/…`.
- **Depends-on**: IC-01 (schema) for the step fields.
- **Risks**: `plan` has NO prompts (empty index.yaml) → all 4 are red; keep moved artifacts byte-identical; do not perturb dispatch (NFR-006).

### IC-06 — Override seam + live consumer

- **Purpose**: Read `recommended_model_tier` (and `agent_profile` as the advisory role) through one named seam with precedence charter/runtime override > step offer; wire `model_task_routing/evaluator.py:229` as the live consumer so NFR-003 is falsifiable.
- **Requirements**: FR-008, NFR-003, C-002.
- **Surfaces**: `evaluator.py` + the seam module.
- **Depends-on**: IC-01.
- **Risks**: leaking routing authority into doctrine (C-002) — the override must always win.

### IC-07 — Proofs (parity / referential-integrity / dispatch-invariance / DRG delta)

- **Purpose**: The load-bearing test surfaces — software-dev **parity** scaffold (transitional, red-first, C-006), 3-type **referential-integrity** (NFR-001b), **dispatch-invariance** per type (NFR-006), **DRG 0-delta** + freshness (NFR-002/005).
- **Requirements**: NFR-001a, NFR-001b, NFR-002, NFR-005, NFR-006.
- **Surfaces**: `tests/…` (doctrine + drg + runtime).
- **Depends-on**: parity scaffold authored **before** the IC-04 cutover; the rest verify post-change.
- **Risks**: writing a tautological "parity" test for the 3 authored types (it must be referential-integrity, not parity).

## Post-Plan Squad Refinements (BINDING for /tasks)

Three-lens post-plan squad (paula/alphonso/priti, all LAND-WITH-EDITS). The following are load-bearing and
supersede any looser phrasing above.

### Grounding corrections
- **`models.py` single-owner (or finalize REJECTS).** `MissionStep` (IC-01) and `MissionType` (IC-04) are two classes in **one file**. Pull the `MissionType` model-shape change — make `action_sequence`/`template_set` **absence-tolerant** and **relocate `_validate_action_sequence`'s non-empty+unique invariant onto the projection** — **forward into the schema WP (WP01)**. The cutover then touches YAML + consumer files only, never `models.py`.
- **`prompt_template` stays REQUIRED (structure enforced) — do NOT make it optional.** Post-plan census: documentation (7) + research (5) steps have `guidelines.md` but **no `prompt.md`**; `plan` (4) has neither → **16-step** disposition. For the 16, **seed a blank/empty `prompt.md`** so the required `prompt_template` points at a real file (schema validation passes); a **red test on prompt emptiness/dummy-content** flags each seeded blank until S-C fills it. A blank placeholder is not invented content (C-004). This is WP05 (seed blanks + emptiness red test), NOT a WP01 schema relaxation.
- **`template_set` projection keys on `artifact_key`** (`spec` ≠ step-id `specify`), dropping template-less steps (software-dev: only 2 of 12 carry one). The resolver reads `template_set["spec"]` — projecting on step-id silently breaks it.
- **Scope-fence the `doctrine.template_set` scalar** (C-008) — only `MissionType.template_set` (dict) projects; the charter selection scalar is untouched.
- **Switch sites (re-targeted):** the real authority reads are `_resolve_action_slot` (`mission_type_profiles.py:694/697`) + `_resolve_template_set_slot` (`:750`) — **not** the `:496` bundle pass-through. Runtime/CLI consumers funnel through the charter bundle → switch transitively (no missed 5th authority).
- **Cache boundary (NFR-007) = `MissionTypeRepository._load` injection + memoized `default()`** via `@functools.cache` (reuse the idiom at `mission_type_repository.py:140`) — **NOT** a computed property on the frozen model (impossible; puts I/O in a frozen domain model). `default()` is un-memoized today and would amplify per-call `step.yaml` I/O without this.
- **Extractor gains a `MissionStepRepository` coupling** (it reads raw dicts today): pin it **builtin-only** (`pack_context=None`, so overrides never leak into the shipped graph) and **projection-filtered** (never a dir listing). Assert **`in_action_sequence:false` steps mint no edge** (retrospect + software-dev's 7 non-sequence steps) — else NFR-002 0-delta breaks.
- **Re-point raw-YAML test helpers** (`tests/doctrine/drg/test_mission_type_nodes.py:98`, `.../migration/test_extractor.py:700`) to the projection at cutover — they go red otherwise.
- **`extends`-fallback check** (`mission_type_profiles.py:694`): a projected-empty child would trip the non-empty validator before the runtime can inherit the parent — one-line check across the 4 built-in types in the consumer-switch WP.

### WP decomposition (8 WPs; DAG joins at WP07; zero owned_files overlap)

| WP | Scope | Deps | owned_files (sketch) |
|----|-------|------|----------------------|
| **WP01** Schema foundation | MissionStep fields (`sequence_index`,`in_action_sequence`,`recommended_model_tier`,`template`; `prompt_template` **stays required**) + `_STEP_YAML_TO_MODEL`; MissionType absence-tolerant + validator relocated to projection; field-round-trip test (extra="forbid" trap) | — | `models.py`, `mission_step_repository.py`, `tests/doctrine/missions/test_step_schema*` |
| **WP02** Projection seam + caching | new `step_projection.py`: pure `project_action_sequence`/`project_template_set` (artifact-key) **+ cached accessors** (repo injection + memoized `default()`); module tests; projection-side non-empty/unique invariant (WP01→WP02 contract) | WP01 | `step_projection.py`, `tests/.../test_step_projection*` |
| **WP03** Software-dev step data | author `sequence_index`/`in_action_sequence` on sw-dev's 12 step.yaml; round-trip to today's sequence | WP01,WP02 | `mission-steps/software-dev/**/step.yaml`, `tests/.../test_softwaredev_roundtrip*` |
| **WP04** Extractor re-point | extractor reads projection (builtin-only, filtered, no dir listing); DRG 0-delta 280/757/10 + freshness; `in_action_sequence:false`→no-edge; re-point raw-YAML test helpers | WP02,WP03 | `extractor.py`, `tests/.../test_extractor_projection*` |
| **WP05** 4-type unification | move documentation/research content → `mission-steps/<type>/<step>/` + author step.yaml (`prompt_template` required); **seed blank `prompt.md` for the 16 prompt-less steps** (doc 7 + research 5 + plan 4) + **red test on prompt emptiness/dummy-content**; referential-integrity (3 types) + dispatch-invariance (NFR-006) | WP01,WP02 | `mission-steps/{documentation,research,plan}/**` (moves from `missions/{…}/actions|templates/**`), `tests/.../test_referential_integrity*`, `tests/.../test_prompt_emptiness*` |
| **WP06** Consumer switch | switch `_resolve_action_slot:694/697` + `_resolve_template_set_slot:750` + `decision.py:606` + `runtime_bridge_composition.py:186/321` to the cached seam; extends-fallback check; seam-equivalence tests | WP02,WP03,WP05 | those runtime files, `tests/.../test_runtime_seam*` |
| **WP07** YAML cutover + scaffold lifecycle | remove `action_sequence`/`template_set` from `mission_types/*.yaml`; **owns the transitional parity scaffold add→prove-green→delete** (intra-WP order: (1) add scaffold, prove green while YAML authored; (2) remove YAML; (3) delete scaffold); full aggregate gate local (arch/DRG/terminology, ruff/mypy, regenerate-graph --check) | WP04,WP06 | `mission_types/*.yaml`, `tests/.../test_softwaredev_parity_scaffold.py` (added+deleted here) |
| **WP08** Override seam + live consumer | named offer seam (override > step offer); wire `evaluator.py:229` as the live `recommended_model_tier` consumer (NFR-003) | WP01 | new `step_offer_seam.py`, `model_task_routing/evaluator.py`, `tests/.../test_override_precedence*` |

**Parallelism:** after WP01 → {WP02, WP08}; after WP02 → {WP03, WP05}; WP04←WP03; WP06←WP03,WP05; all join WP07. ~2 lanes. IC-07's proofs are **distributed to their change WPs** (no monolithic proofs WP). If WP05 exceeds 7 subtasks, split plan-only out.

**Landing (C-007):** lanes base on the S-A-bearing HEAD (`feat/mission-step-authority`), NOT origin/main. FLAT mission still writes `lanes.json` + DFS cycle check at finalize. No PR → **WP07's local aggregate-gate-green is the only merge-readiness signal** — weight it accordingly.
