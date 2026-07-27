---
description: "Work package task list — Model-Discipline Dispatch Binding"
---

# Work Packages: Model-Discipline Dispatch Binding

**Inputs**: Design documents from `/kitty-specs/model-discipline-dispatch-binding-01KWPW36/`
**Prerequisites**: plan.md (required), spec.md rev 2 (full-evaluator scope), research.md, adversarial-review.md

**Tests**: Red-first mandatory (NFR-001) — behavior proven through `spec-kitty dispatch` / `ProfileInvocationExecutor.invoke()` payload contents, never the Pydantic model in isolation, never a stubbed recommendation. SC-001 requires the recommendation to VARY with catalog content (anti-fake).

**Organization**: Six ownership-disjoint work packages tracking IC-01…IC-06. Dependency DAG: WP01/WP04/WP05 are foundations (no deps); WP02 needs WP01+WP04; WP03 needs WP01+WP02+WP05; WP06 needs WP05.

## Work Package Summary

| WP | Title | Priority | Dependencies | Subtasks | Authoritative surface |
|----|-------|----------|--------------|----------|-----------------------|
| WP01 | Catalog loader + action→task_type map | P0 | none | T001–T005 | `src/doctrine/model_task_routing/` |
| WP02 | Routing evaluator (objective scorer) | P0 | WP01, WP04 | T007–T011 | `src/doctrine/model_task_routing/` |
| WP03 | Advisory recommendation on the dispatch payload | P0 | WP01, WP02, WP05 | T012–T019 | `src/specify_cli/invocation/` |
| WP04 | Agent-profile model/effort field | P1 | none | T018–T022 | `src/doctrine/agent_profiles/` |
| WP05 | Doctrine artifact + DRG resolution + catalog data | P1 | none | T023–T029 | `src/doctrine/` |
| WP06 | Durable no-dangling-reference invariant | P1 | WP05 | T030–T032 | `tests/architectural/` |

## Work Packages

---

## Work Package WP01: Catalog loader + action→task_type map (Priority: P0)

**Goal**: Turn the dead `model_task_routing` catalog into a loadable, freshness-checked runtime source, and bridge dispatch verbs to catalog `task_type` vocabulary.

**Independent Test**: `loader.load(catalog_path: Path | None = None)` resolves the catalog by default via `importlib.resources.files("doctrine.model_task_routing")/"catalog"/"model-to-task_type.yaml"` (with an injectable override) → parses → validates against `ModelToTaskType` → applies freshness; `task_class_map` maps a dispatch action verb to a catalog `task_type`. Missing/whole-file-invalid catalog → returns absent (non-fatal).

**Prompt**: `/tasks/WP01-catalog-loader-and-task-class-map.md`
**Requirement Refs**: FR-001, FR-002, C-002, C-004
**Dependencies**: none

### Included Subtasks
- [x] T001 [red-first] `tests/doctrine/test_model_task_routing_loader.py`: valid catalog loads + validates; missing → None; whole-file-invalid → None (non-fatal); stale (freshness) → flagged. RECORD pre-fix RED.
- [x] T002 [red-first] `tests/doctrine/test_task_class_map.py`: known action verb → task_type; unknown → None; map stays in sync with `DEFAULT_ROLE_CAPABILITIES` verbs. RECORD RED.
- [x] T003 [FR-001] `src/doctrine/model_task_routing/loader.py`: `load(catalog_path: Path | None = None)` resolves the catalog via `importlib.resources.files("doctrine.model_task_routing")/"catalog"/"model-to-task_type.yaml"` by default (injectable override for tests), YAML load, `ModelToTaskType.model_validate`, `freshness_policy` check. Pure/deterministic.
- [x] T004 [FR-002] `src/specify_cli/invocation/task_class_map.py`: action/role verb → catalog `task_type`.
- [x] T005 Turn T001/T002 green; `ruff`/`mypy` clean; complexity ≤ 15; no ≥3× literals.

### Dependencies / Risks
- None (foundation). Risk: catalog resolution is Python package data (`importlib.resources`), matched exactly by WP05's shipped file location. Note: `loader.py`/`task_class_map.py` are ORPHANS until WP03 wires them into `invoke()` — expected; the dead-modules invariant (and its `_ALLOWLIST` de-listing) is validated/owned at the WP03 tip, not here. The action→task_type map is a live maintenance seam.

---

## Work Package WP02: Routing evaluator (Priority: P0)

**Goal**: Deterministic recommendation from `task_fit` × `weights` under `objective` (quality_first = the capability lever), applying `tier_constraints` + `override_policy` precedence (advisory: emit catalog + profile candidates with provenance, enforce neither).

**Independent Test**: `evaluator.recommend(catalog, task_type, profile)` returns a deterministic recommendation; changing `task_fit`/`weights` changes the winner; a profile `model` surfaces as a provenance-tagged candidate under `advisory`.

**Prompt**: `/tasks/WP02-routing-evaluator.md`
**Requirement Refs**: FR-003, NFR-004, C-004
**Dependencies**: WP01, WP04

### Included Subtasks
- [x] T007 [red-first] `tests/doctrine/test_model_task_routing_evaluator.py`: quality_first ranks strongest-fit for a high-judgment task_type; `tier_constraints` cap respected; deterministic (same inputs → same output). RECORD RED.
- [x] T008 [red-first] override precedence under `advisory`: catalog pick + profile declaration both surfaced with provenance, neither enforced. RECORD RED.
- [x] T009 [FR-003] `src/doctrine/model_task_routing/evaluator.py`: pure scorer (no I/O) consuming WP01's loaded catalog + task_type + the WP04 profile field.
- [x] T010 [NFR-004] determinism + edge cases (no match, empty task_fit) covered.
- [x] T011 `ruff`/`mypy` clean; complexity ≤ 15.

### Dependencies / Risks
- WP01 (catalog/task_type), WP04 (profile field — read `profile.preferred_model`/`profile.effort`). Risk: capability-via-quality-objective must actually rank strongest-fit; precedence must be deterministic. Note: `evaluator.py` is an ORPHAN until WP03 wires it into `invoke()` — expected; dead-modules validated at the WP03 tip.

---

## Work Package WP03: Advisory recommendation on the dispatch payload (Priority: P0)

**Goal**: Surface the evaluator's recommendation on `InvocationPayload` through `invoke()`, advisory + non-fatal, in both `--json` and rich render.

**Independent Test**: red-first through `spec-kitty dispatch` / `invoke()` — with a catalog, the payload carries a recommendation that VARIES with catalog content; without a catalog, absent + dispatch succeeds.

**Prompt**: `/tasks/WP03-advisory-payload-wiring.md`
**Requirement Refs**: FR-004, NFR-001, NFR-002, C-001
**Dependencies**: WP01, WP02, WP05

### Included Subtasks
- [x] T012 [red-first] `tests/invocation/test_dispatch_recommendation.py`: through `invoke()`/`dispatch --json`, recommendation present with a catalog + VARIES when catalog scoring changes (anti-fake, SC-001); absent when catalog removed, dispatch still succeeds (NFR-002). RECORD pre-fix RED (no slot exists).
- [x] T013 [FR-004] `InvocationPayload` new `__slots__` recommendation field (+ `to_dict()`), runtime imports as needed.
- [x] T014 [FR-004] wire the loader+evaluator call into `ProfileInvocationExecutor.invoke()` after profile+action resolve (~executor.py:196/205), before payload construction (~:273); non-fatal (missing/stale → absent). MANDATORY: extract a pure helper `_compute_recommendation(profile, action) -> Recommendation | None` holding the loader+evaluator call and the non-fatal envelope so `invoke()` stays ≤15 cognitive complexity.
- [x] T015 [FR-004] `_render_rich_payload` (`cli/commands/dispatch.py`) recommendation line.
- [x] T016 [NFR-002] non-fatal paths asserted (missing/stale/unmatched catalog).
- [x] T017 `ruff`/`mypy` clean; complexity ≤ 15.
- [x] T018 [dead-modules tip] Remove `doctrine.model_task_routing.models` from `_ALLOWLIST` in `tests/architectural/test_no_dead_modules.py`; confirm loader.py/task_class_map.py/evaluator.py all gain their `invoke()` caller here so the no-dead-modules gate is green at the integration tip.
- [x] T019 [integration] With NO fixture override, run `spec-kitty dispatch`/`invoke()` and assert a recommendation IS produced from the REAL shipped WP05 catalog through the loader's default path.

### Dependencies / Risks
- WP01, WP02, WP05 (the shipped catalog — untested agreement between WP01's default path and WP05's file location without T019). Risk: must never fail dispatch; red-first through the CLI/`invoke()` payload, not the model in isolation. This WP owns `test_no_dead_modules.py` (de-allowlists `models`) and the complexity-extraction of `invoke()`.

---

## Work Package WP04: Agent-profile model/effort field (Priority: P1)

**Goal**: Optional per-profile `model`/`effort` field that reaches the evaluator — added to the DOMAIN model (`profile.py`) + the schema SOURCE (`schema_models.py`, regenerated), not the generated `.yaml`.

**Independent Test**: a profile declaring `model` exposes it on the loaded `AgentProfile` object (not dropped by `extra='ignore'`); an existing profile without it validates unchanged.

**Prompt**: `/tasks/WP04-agent-profile-model-field.md`
**Requirement Refs**: FR-005, NFR-003, C-005
**Dependencies**: none

### Included Subtasks
- [x] T018 [red-first] `tests/doctrine/test_agent_profile_model_field.py`: a YAML profile with `model:`/`effort:` → the value is present on the loaded `AgentProfile` (proves it reaches the domain model); a profile without it loads unchanged (NFR-003). RECORD pre-fix RED (field dropped today).
- [x] T019 [FR-005] add optional fields to `AgentProfile` in `src/doctrine/agent_profiles/profile.py`: EXACTLY `preferred_model: str | None = Field(default=None, alias="model")` and `effort: str | None = Field(default=None, alias="effort")` (mirror the `routing_priority` alias pattern, :264); `preferred_model` avoids Pydantic v2's `model_` protected namespace deterministically — no conditional aliasing.
- [x] T020 [FR-005] add the field to `src/doctrine/agent_profiles/schema_models.py` (schema source) and REGENERATE `src/doctrine/schemas/agent-profile.schema.yaml` (do not hand-edit).
- [x] T021 [NFR-003] back-compat: existing profiles load; schema parity test green.
- [x] T022 `ruff`/`mypy` clean; complexity ≤ 15.

### Dependencies / Risks
- None. Consumed by WP02. Risk: schema-only add is a silent no-op — MUST land on `profile.py`. Regenerate; never hand-edit the `.yaml`.

---

## Work Package WP05: Doctrine artifact + DRG resolution + catalog data (Priority: P1)

**Goal**: Make the charter model-discipline references real activated doctrine (DRG-driven) and ship a populated catalog.

**Independent Test**: `charter context` surfaces the model-discipline tactic guidance; `model-task-routing` (repointed token) + `autonomous-operation-protocol` resolve in the regenerated `references.yaml` via directive-reachability; the catalog validates against the schema.

**Prompt**: `/tasks/WP05-doctrine-artifact-and-drg.md`
**Requirement Refs**: FR-006, FR-007, FR-008, C-002
**Dependencies**: none

### Included Subtasks
- [x] T023 [red-first] `tests/charter/test_model_task_routing_resolves.py`: the `model-task-routing` tactic loads via DRG traversal (not just string-present) + `charter context` surfaces its body; `autonomous-operation-protocol` resolves. RECORD pre-fix RED (both dangle).
- [x] T024 [FR-006] `src/doctrine/tactics/built-in/model-task-routing.tactic.yaml` (kebab) — routing guidance + catalog pointer; schema-valid.
- [x] T025 [FR-006] `src/doctrine/graph.yaml`: add `tactic:model-task-routing` node + an activated-directive → `tactic:model-task-routing` `suggests` edge (pattern of DIRECTIVE_043/044/045).
- [x] T026 [FR-006] repoint the charter prose token in `.kittify/charter/charter.md` from `model_task_routing` → `model-task-routing`.
- [x] T027 [FR-007] one-line activated-directive → `tactic:autonomous-operation-protocol` `suggests` edge in `graph.yaml` (tactic already exists).
- [x] T028 [FR-008] populated `model-to-task_type` catalog instance at exactly `src/doctrine/model_task_routing/catalog/model-to-task_type.yaml` (package data — matches WP01's `importlib.resources` default path) (models + task_fit + `objective: quality_first` + `override_policy: advisory` + `freshness_policy`); validate against the schema.
- [x] T029 [C-002] regenerate `references.yaml` + the `_LIBRARY`/synthesis-manifest bundle (generated-lockfile step); `ruff`/`mypy`/terminology-guard clean.

### Dependencies / Risks
- None for authoring. Risk: DRG-driven resolution — a references.yaml row without a `suggests` edge still dangles. Bundle regen reds CI if skipped. Kind = tactic (confirmed).

---

## Work Package WP06: Durable no-dangling-reference invariant (Priority: P1)

**Goal**: A refactor-stable test asserting EVERY charter `→ token` reference (all sections) resolves — guarding against section-level dangling recurrence.

**Independent Test**: fails on pre-fix HEAD (both tokens dangle), passes post-WP05; asserts by parsing `→ \`token\`` prose + references.yaml id-suffix match, no literal token list pinned.

**Prompt**: `/tasks/WP06-no-dangling-reference-invariant.md`
**Requirement Refs**: FR-009, SC-004
**Dependencies**: WP05

### Included Subtasks
- [x] T030 [FR-009] `tests/architectural/test_charter_references_resolve.py`: parse all backticked-after-`→` tokens across every charter.md section; assert each resolves to a `references.yaml` id-suffix. Exclude non-backticked prose.
- [x] T031 confirm RED on pre-fix HEAD (both tokens absent) + GREEN post-WP05; refactor-stable (no literal token list). Since this WP depends on WP05 (tokens already resolve on its branch), capture RED against the pre-WP05 base (e.g. `git stash` WP05's `graph.yaml`/`charter.md` edits, or run on the mission base branch before WP05 landed); RECORD the pre-fix failure; then confirm GREEN on the integrated branch.
- [x] T032 `ruff`/`mypy` clean.

### Dependencies / Risks
- WP05 (goes green once tokens resolve). Risk: must be refactor-stable — vocabulary-derived, not line-pinned.
