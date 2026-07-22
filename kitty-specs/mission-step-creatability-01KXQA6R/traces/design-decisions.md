# Design Decisions — Mission-Type Creatability (S-C)

Tracer (seeded at planning; append DD-07+ during implement). Records the *why*.

## DD-01 — Retire `template_set` as a persisted field (NOT keep projecting to it)

**Decision**: Remove `MissionType.template_set` as a persisted/authorable field + delete the raw-YAML overlay; compute the projection at the consumption boundary from the step authority.

**Why (operator direction change + 3-lens adversarial squad, all LAND)**: keeping `template_set` as a projected read-field is a *partial* cutover — consumption reads a flattened dict, not the authority; it perpetuates a model collision with the scalar `doctrine.template_set` (C-008 prose fence only); and it leaves a live split-brain vector (a pack-authored `template_set` would be silently honored via the `raw.get(...)` fallback). All four theories confirmed in code. Proven behavior-preserving byte-for-byte (software-dev steps already carry refs → identical projection; no `mission_types/*.yaml` authors `template_set` → fallback already dead). Chosen over the lower-effort "keep the field" because the ~4-5-site removal cost is small and the retained cost is four real problems.

## DD-02 — `action_sequence` symmetry is split off to #2751 (NOT folded in)

**Decision**: Do the identical retirement for `action_sequence` in a separate follow-up (#2751), not in S-C.

**Why (architect-alphonso)**: `action_sequence` crosses a categorically different risk surface template_set does not — the DRG shipped-graph extractor + NFR-002 freshness gate, a hard non-empty `validate_action_sequence` invariant (all-types precondition), and the *eager* FSM hot-path field under `<100ms`. ~2.5× the sites and a different gate; bundling would hide the DRG-freshness risk behind a template cutover. The `_inject_projected_fields` `action_sequence` overlay (`:199`) stays untouched (C-007).

## DD-03 — Q1: the creation `artifact_key` contract is GENERIC (`"spec"`/`"plan"`), not per-type

**Decision**: Each type authors a step with `template.artifact_key = "spec"` (satisfies `mission create`) + one with `"plan"` (satisfies `/plan` setup). `artifact_key` is the shared runtime-contract vocabulary; only `template_file` is per-type.

**Why (Q1 code trace)**: `mission_creation.py:351-355` hardcodes `resolve_configured_template("spec", …)` and `mission_setup_plan.py:453-457` hardcodes `"plan"` — generic across all types, no alias layer on the content surface (`decision.py:_ALIASES` is the *command*-template surface). Since the resolver does `template_set.get("spec")` and `template_set` is keyed on `artifact_key`, the authored key MUST be exactly `"spec"`/`"plan"` or the type stays uncreatable. This corrected the spec's earlier per-type-`artifact_key` assumption (C-003) and makes Q1 a hard predecessor of authoring (C-010).

## DD-04 — C-002 is an assertable scalar-REFERENCE fence, not an import fence

**Decision**: The C-008 fence is expressed as "new URN/resolver code must never *reference* the scalar surfaces (`resolution.template_set` / `MissionTypeProfile.template_set` / `doctrine.template_set`)" — NOT "imports nothing from `charter.*`".

**Why (paula-patterns)**: the in-scope `resolver.py` already legitimately imports `ResolvedMissionType`, `ResolutionResult`, `CharterTemplateResolver` from `charter.*` (`:35/:36/:206`), and the resolve-by-URN lane must consume `ResolvedMissionType`. A module-granular "imports nothing from charter" test either fails on existing code or is unenforceable. The scalar `MissionTypeProfile.template_set` co-habits `mission_type_profiles.py` with the in-scope dict slot (`:145/:1001` vs `:744`) — so no blind grep-replace on `template_set` in that file.

## DD-05 — Tidy-first sequencing (cutover before authoring)

**Decision**: Concern A (retire field) lands before Concern B (author content), which lands before Concern C (graph reads refs).

**Why**: authoring the three new types on the *clean* surface means they are born without the split-brain — a pack can never re-introduce `template_set` for them. And C's DRG delta N is derived from B's authoring, so C must follow B. A is behavior-preserving and safe to land first (parity guard already green).

## DD-06 — Keep the enduring parity guard; retire only the injection-half

**Decision**: `TestSoftwareDevProjectionParity` (`test_softwaredev_roundtrip.py:68-112`) STAYS (the byte-for-byte regression net for NFR-001); only `TestMissionTypeRepositoryLiveProjection` (`:131-135`, reads the removed field) + the ~6 field-pin tests are retired/migrated.

**Why (reviewer-renata)**: parity is the load-bearing correctness proof; the injection-half tests pin the *transitional shape* (the persisted field), which is exactly what's being removed. Migrate reads to `project_template_set(steps)`/`ResolvedMissionType`; distinguish from `step.template` reads which survive.

## DD-07 — One shared `iter_template_refs` traversal (post-plan paula fold-in)

**Decision**: IC-01 exposes a public `iter_template_refs(steps) -> list[(MissionStep, MissionStepTemplateRef)]` (promoting the private `_step_template_ref`, `step_projection.py:111`); both `project_template_set` (flattens to the dict) AND IC-06's graph pass (needs the `(step, ref)` pair for the `instantiates` edge) consume it.

**Why (post-plan code-state scan)**: `project_template_set` discards `step_id`, but the extractor pass needs it. Two independent step-iterations over `step.template` would re-create the exact whack-a-field this mission kills — two places that must agree on "which steps carry refs." One traversal, one place to change the ref shape. Serves the mission's own single-authority goal.

## DD-08 — PR closing keywords (post-plan priti linkage nit)

**Decision**: the eventual PR uses **`Resolves #883` as the sole closing keyword**; #2689 is referenced as **`Related to #2689` prose only** (it is a MERGED PR, not a closeable issue — a `Closes #2689` keyword is a misleading no-op). Aligns [[feedback_pr_closing_keyword_parsing]] + [[feedback_landing_pass_lessons_0704]].

## DD-09 — NFR-003 memoisation lives on `resolve_all_for_mission_type`, shared (post-plan paula d3)

**Decision**: the "exactly one walk" cache is keyed by `(mission_type, pack_context)` on `resolve_all_for_mission_type` (where the filesystem walk actually is), **shared** by both the retained `action_sequence` overlay and the new `template_set` slot — NOT a slot-local private cache, and NOT merely memoising `default()` (which only singletons the repo object). The call-count spy asserts the shared cache.

<!-- Append DD-10+ during implement. -->

