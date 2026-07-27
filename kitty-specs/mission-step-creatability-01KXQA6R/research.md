# Research — S-C (Mission-Type Creatability via Rich Step Model)

Consolidated grounding for #2724. Two squads fed this mission: a **3-lens content/architecture grounding squad** (researcher-robbie, architect-alphonso, paula-patterns) and a **3-lens adversarial verification squad** (paula-patterns, architect-alphonso, reviewer-renata) that stress-tested the direction change. All lenses were profile-loaded and read-only.

---

## 1. Direction change: retire `template_set`, don't keep projecting to it

S-B shipped `template_set` as a **projected read-field** on `MissionType` ("reuse the existing mechanism to limit blast radius"). The operator challenged this on reflection; four theories, **all confirmed in code**:

1. **Partial missiontypes-as-doctrine.** Epic #2721 and S-B's own code both label `template_set` "transitional." Authoring is graph-backed (step.yaml); consumption still reads a flattened dict, not the authority. Half-cutover.
2. **Model collision.** Dict `MissionType.template_set` (6 sites) vs scalar `doctrine.template_set` (40+ sites, `charter/*`), co-located in `specify_cli/runtime/` (`resolver.py:395` dict vs `doctor.py:149`/`prompt_builder.py:441` scalar), separated only by a prose C-008 fence (docstrings).
3. **Semantic confusion.** `MissionType` exposes three views of one structure: `steps` (authority) + `action_sequence` (list projection) + `template_set` (dict projection).
4. **Split-brain from contributions.** The live raw-YAML fallback `mission_type_repository.py:200-201` (`raw.get("template_set")`) + the still-authorable field `models.py:259` would **silently honor** a community/pack-authored `template_set` whenever steps lack refs. The exact two-surface split-brain S-B set out to kill — dormant, not dead.

**Key structural finding**: the dict `template_set` has **one behavioral consumer** — `resolve_configured_template` (`resolver.py:403`) — and the flattening happens inside a thunk (`_resolve_template_set_slot`, `mission_type_profiles.py:744`) that already re-fetches the mission from the repository. The resolver never needed the flattened field.

---

## 2. Grounding squad — content + step topology (researcher-robbie)

**Per-type step topology (each on its OWN names; do NOT assume specify/plan shape):**
- `documentation`: `discover → audit → design → generate → validate → publish → accept` (7 sequence) + `retrospect` (`in_action_sequence: false`, excluded).
- `research`: `scoping → methodology → gathering → synthesis → output` (5 sequence) + `retrospect` (excluded). (`research/mission-runtime.yaml` also lists `accept`, but there is no `mission-steps/research/accept/` dir — not part of the 16.)
- `plan`: `specify → research → plan → review` (4 sequence). Name-collides with software-dev but is decomposition/decision (no code) — highest authoring cost.

**16-file acceptance surface** (`retrospect ×2` excluded): all 18 `mission-steps/<type>/<step>/prompt.md` are 0 bytes; the 16 in scope are documentation(7) + research(5) + plan(4).

**Guard `tests/doctrine/missions/test_prompt_emptiness.py`** is *mutated, not just satisfied*:
- `_SEEDED_BLANK_STEPS` (16 tuples) + `_is_empty_or_dummy` (flags zero-bytes / whitespace / `TODO`/`PLACEHOLDER`/`FIXME`).
- `TestSeededBlankPromptsAreNamedGaps` marks each `xfail(strict=False)` → filling flips to XPASS (signal, not hard pass).
- `test_seeded_prompt_is_zero_bytes` asserts `st_size == 0` **with no xfail** → hard-RED on the first byte written. **S-C must edit this file**: shrink `_SEEDED_BLANK_STEPS`, drop each xfail, decrement the golden `16` (`# golden-count: cardinality-is-contract`), update `_SEQUENCE_STEPS_BY_TYPE`.

**Content disposition**: `prompt.md` ≠ `guidelines.md`. documentation/research ship rich `guidelines.md` → **promote** into the software-dev prompt shape. plan has **no** `guidelines.md` and empty `templates/` → **author-fresh** (+ author its scaffold templates). DD-06 rationale: `kitty-specs/mission-step-authority-01KXNZMT/traces/design-decisions.md:57-67`.

---

## 3. Grounding squad — DRG + resolver architecture (architect-alphonso)

- **Node/URN convention** (mirror exactly): `template:<kebab>` for #2712's 16 exemplars (`template.graph.yaml`, currently `edges: []`); mission-qualified `template:<mission>/<name>` via `template_catalog.template_urn` (module exists, **not** wired into `generate_graph`). Steps are `action:<type>/<step>` nodes (no new NodeKind).
- **Graph-back seam**: new pass paralleling `extract_mission_type_edges` (`extractor.py:864`), minting from the **step projection** (deterministic) not `discover_templates` (filesystem scan → freshness flap). `Relation.INSTANTIATES` already exists (`drg/models.py:82`). Instantiates edges are `action:`-sourced → land in `action.graph.yaml`; `template.graph.yaml` stays nodes-only. Partition already modeled by the unit test `test_extractor.py:822-878`.
- **DRG delta (intentional)**: +N nodes / +N edges (N = steps with a template ref; software-dev already has 2 ungraphed: specify→spec, plan→plan). **Orphans stay 10** (new template nodes have an instantiates in-edge). Bump `_EXPECTED_NODE/EDGE_COUNT` (`test_extractor_projection.py:40-42`) to 280+N/757+N; ceiling 14 (`test_doctrine_regenerate_graph.py:78`) untouched. Add a positive shipped-graph instantiates assertion (none exists today).
- **Resolve-by-URN = second lane**: today resolution is name-based end-to-end (`resolve_configured_template:346` → `template_set[artifact_kind]` → filename → `resolve_template:318` → 5-tier filesystem). `template_catalog.resolve_template_by_id` already exists and terminates in the same Stage-2 `resolve_template`. The filesystem↔URN duality is a **compatibility contract** (ADR D3 line 104) — do not collapse.
- **#2660 invariant**: `resolver.py:378-384` typeless rejection + no software-dev inference; the new URN mode must inherit the identical fail-closed posture (no defaulting an unqualified URN to `software-dev`).

---

## 4. Grounding squad — boundary/regression risks (paula-patterns)

Ranked: (R1) `template_set` dict/scalar duality co-located in `specify_cli/runtime/`; (R2) collapsing name/URN kills the 5-tier override chain; (R3) fix by authoring, not by relaxing the `:395` guard (#2689/#2660); (R4) emptiness test gameable by a filler sentence + a coupled-edit whack-a-field; (R5) cross-type contamination (per-type `template_file`; but note the spec-review correction: `artifact_key` is the SHARED `"spec"`/`"plan"` runtime contract, not per-type); (R6) `instantiates` has no emission path today → new emission trips orphan-residual + `_ARCH_SHARD_N_FILES` + golden-count markers. **Correction (verified by the spec-review squad on branch `feat/mission-step-creatability`):** templates are **not** skipped by the extractor (`_SKIP_REF_TYPES` is empty; `_KIND_MAP["template"]=NodeKind.TEMPLATE`) — the earlier "extractor.py:358-360 skips template targets" reading is stale. The real reason a new pass is required is that a step's template ref is a **structured `MissionStepTemplateRef` field**, not a `references:` list entry, so no existing edge pass traverses it.

---

## 5. Adversarial verification squad — the "small blast radius" claim (LAND, with corrections)

**Verdict: LAND the `template_set` cutover in S-C; HOLD `action_sequence` for a separate slice.** All claims survived attack; empirically proven byte-for-byte parity for all four types; **no `mission_types/*.yaml` authors `template_set`** → the raw-YAML fallback is already dead code.

**paula-patterns (refute: 1 consumer / no boundary widening)** — CLAIM 1 SURVIVES (one behavioral production consumer, `resolver.py:403`), corrections: there is **no `ProfileBundle` class** (it's `ResolvedMissionType`); the `:1001` display is `MissionTypeProfile.template_set`, a *scalar*, unrelated. CLAIM 2 conclusion holds but the mechanism was FALSE — `MissionType` is `frozen, extra="forbid"` with **no `.steps` field**; the thunk must resolve steps via `MissionStepRepository.resolve_all_for_mission_type(type, pack_context=None)`. Surviving risks: (HIGH) stored field is schema-pinned by ~6 test files; (MED) `mission_type.py:1491` `--json` serialization contract; (LOW) a future pack authoring `template_set` without steps must fail loudly, not be silently dropped.

**architect-alphonso (refute: action_sequence symmetry is cheap)** — CLAIM 3 SURVIVES (template_set cutover ~4-5 sites, resolver signature + fail-closed guards untouched; `template_set` is not imported by the DRG extractor — why it's cheap). CLAIM 4 PARTIALLY-REFUTED — `action_sequence` is NOT "template_set with more call sites": it drags in (1) the DRG shipped-graph extractor + NFR-002 freshness gate, (2) a hard non-empty `validate_action_sequence` invariant (all-types precondition), (3) an **eager** FSM hot-path field (`ResolvedMissionType.action_sequence:332`) with extends-chain resolution under `<100ms` (`runtime_bridge_composition.py:186/321`, `decision.py:606`). Net: ~4 sites (template_set) vs ~9-12 (both), and it crosses a categorically different gate → **do NOT fold in; distinct slice.**

**reviewer-renata (refute: no correctness/fail-closed regression)** — CLAIMS A/B/C all SURVIVE. Proven at runtime: `stored == project_template_set(steps)` byte-for-byte (software-dev `{'plan':'plan-template.md','spec':'spec-template.md'}`; the 3 types `None`). Fail-closed guards sit one layer above the change (untouched). `_template_set_thunk` is `compare=False` + `template_set` is a `@cached_property` → equality/determinism unaffected. **Coupled edits the spec MUST guard**: (1) `mission_type.py:1491,1509` read the model field, UNTESTED → AttributeError on removal; migrate + `dict()`-wrap the MappingProxy before `json.dumps` + add test; (2) injection removal must be lockstep with field removal (`extra="forbid"`); (3) the new slot must pass `pack_context=None` and be **cached** (`MissionStepRepository.default()` is NOT memoised → naive rewrite = filesystem walk per resolution); (4) **decline** the `ResolvedMissionType.template_set` rename. **KEEP** `TestSoftwareDevProjectionParity` (test_softwaredev_roundtrip.py:68-112) — it's the enduring regression net; retire only the injection-half + the ~6 field-pin tests. Also: `project_template_set` doesn't sort (set-backed) → sort for determinism (S-C graph-backs).

---

## 6. Net decision → spec

- **Retire the persisted `template_set` field + dead fallback; consume via cached `project_template_set(steps)` (pack_context=None)** — FR-001/FR-002.
- **Migrate the CLI reads + add the missing test** — FR-003.
- **Author the 3 types on their own step names; own the emptiness-test coupled edit; genuine content** — FR-004..008, NFR-004.
- **Graph-back via the step projection; resolve-by-URN as a second lane; intentional DRG delta; sort for determinism** — FR-009..011, NFR-002.
- **Frozen**: fail-closed (#2689/#2660), C-008 scalar fence, per-type shapes, name↔URN contract, keep the enduring parity guard, don't rename the resolved property — C-001..006.
- **Deferred**: `action_sequence` symmetry (distinct slice), FR-009/FR-011 prior deferrals — C-007.
- **Open (→ /plan)**: Q1 artifact_kind trace at mission creation for the 3 types.

Key files: `src/doctrine/missions/{models.py,step_projection.py,mission_type_repository.py}`, `src/charter/mission_type_profiles.py`, `src/specify_cli/runtime/resolver.py`, `src/specify_cli/cli/commands/mission_type.py`, `src/doctrine/drg/migration/extractor.py`, `src/doctrine/template_catalog.py`, `src/doctrine/{template,action,mission_type}.graph.yaml`, `tests/doctrine/missions/test_prompt_emptiness.py`, `tests/doctrine/missions/test_softwaredev_roundtrip.py`, `tests/doctrine/drg/migration/test_extractor_projection.py`. ADR: `docs/adr/3.x/2026-07-16-2-mission-type-step-authority-and-template-vocabulary.md` (D3).
