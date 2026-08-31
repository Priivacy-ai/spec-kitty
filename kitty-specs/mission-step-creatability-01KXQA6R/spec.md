# Mission Specification: Mission-Type Creatability via Rich Step Model

**Mission Branch**: `feat/mission-step-creatability`
**Created**: 2026-07-17
**Status**: Draft
**Input**: S-C (GitHub #2724), Prio-0 slice of step-model sub-epic #2721 under epic #2652. Grounded in ADR `docs/adr/3.x/2026-07-16-2-mission-type-step-authority-and-template-vocabulary.md` (D3), re-scoped by an operator direction change and a 3-lens adversarial verification squad, then hardened by a Q1 code trace + a 3-lens spec-review squad (all findings folded in).

> **Anchor convention**: `file:line` anchors below are *indicative* (line numbers rot); the **symbol names are canonical**. Resolve by symbol, not by line.

## Context & Intent Summary

**Primary actors**: (1) a *doctrine/mission-type author or community contributor* who authors a mission type's steps and content; (2) the *runtime* that resolves a mission type's content templates at mission-creation time.

**Trigger**: After the #2689 slice, three of four built-in mission types (`documentation`, `research`, `plan`) carry no content templates and **hard-fail at creation** (`resolve_configured_template` → `TemplateConfigurationError`). Separately, the S-B slice shipped `template_set` as a *transitional projected read-field* on `MissionType`, duplicating the rich step authority.

**Desired outcome**: The three types become creatable again, authored on the **single step authority** (`step.yaml` / `MissionStep`), with the duplicate `template_set` field retired and the `mission_type → step → template` chain graph-backed — one place to author, no split-brain.

**Load-bearing invariant**: Template resolution stays **fail-closed** — an unmapped/typeless mission type yields a typed error, never a silent software-dev default. Creatability is fixed by **authoring content**, never by relaxing a guard.

**The creation contract (Q1 — RESOLVED, see §Q1)**: at `mission create` the runtime requests the **literal `artifact_kind="spec"`** for *every* type; the `/plan`-setup phase later requests the literal `"plan"`. These keys are hardcoded and generic — not per-type. So each type must author a step whose `template.artifact_key` is exactly `"spec"` (and one `"plan"`), or it stays uncreatable despite all authoring.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Documentation/research/plan missions are creatable again (Priority: P1)

A contributor runs mission creation for a `documentation`, `research`, or `plan` mission. Today it hard-fails (no configured template mapping). After this mission, each type resolves real per-type content and creation succeeds.

**Why this priority**: This is the user-facing regression (#2689) — three of four built-in types are unusable. It is the smallest slice that restores product function.

**Independent Test**: Create one mission of each of the three types; each succeeds and produces the type's first artifact from that type's own content template.

**Acceptance Scenarios**:

1. **Given** the `research` mission type, **When** a mission of that type is created, **Then** creation succeeds and the artifact is produced from research's own content template (its own step names, not a software-dev shape).
2. **Given** the `documentation` mission type, **When** a mission is created, **Then** creation succeeds using documentation's own step names (`discover` … `publish`/`accept`).
3. **Given** the `plan` mission type, **When** a mission is created **and then** advanced to `/plan` setup, **Then** both the creation (`artifact_kind="spec"`) and the plan-setup (`artifact_kind="plan"`) template resolutions succeed with plan-domain (decomposition, no-code) content.
4. **Given** the three types collectively, **When** all 16 seeded-blank step prompts are inspected, **Then** every one carries genuine per-type content (no empty/whitespace/`TODO`/`PLACEHOLDER`/`FIXME`).

---

### User Story 2 - One template authority, no split-brain (Priority: P1)

A future contributor who wants to change a mission type's content edits exactly one surface (the step). There is no longer a duplicate, separately-authorable `template_set` field that a stale example or an LLM could re-introduce and have silently honored.

**Why this priority**: This is the tidy-first structural cutover. Doing it *before* authoring means the three new types are born clean and can never carry the split-brain.

**Independent Test**: The persisted/authorable `MissionType.template_set` field and its overlay are gone; template resolution still returns identical values for software-dev, sourced from the step projection.

**Acceptance Scenarios**:

1. **Given** the retired field, **When** the codebase is searched, **Then** no persisted/authorable `MissionType.template_set` field and no `template_set` overlay in `_inject_projected_fields` remain; consumption computes `project_template_set(steps)` from the step authority. `MissionTypeRepository.default().get("software-dev")` still constructs and resolves `{spec, plan}` identically.
2. **Given** a `mission_types/*.yaml` that (incorrectly) authors `template_set:`, **When** it is loaded, **Then** the loader **fails loudly** (`extra="forbid"` rejects the unknown key) — neither silently honored nor silently dropped.
3. **Given** software-dev, **When** its `spec`/`plan` templates are resolved, **Then** the resolved filenames are byte-for-byte identical to before the cutover, and the `mission_type show --json` output is unchanged.

---

### User Story 3 - Graph-backed mission_type → step → template chain (Priority: P2)

The DRG carries the full `mission_type → step → template` chain: authored templates are `template:` nodes, and each producing step has an `instantiates` edge to its template. The runtime resolves a template both by filesystem name (override-aware) and by URN.

**Why this priority**: Delivers the deferred #883 edge class and finishes what #2712 started. Builds on US1/US2 but is separable.

**Independent Test**: The shipped graph contains the expected `instantiates` edges; both resolution lanes return the same file; DRG freshness passes with the asserted delta.

**Acceptance Scenarios**:

1. **Given** an authored step template ref, **When** the DRG is regenerated, **Then** a `template:<mission>/<file>` node and an `instantiates` edge (`action`-sourced, in `action.graph.yaml`) exist; orphan count is unchanged (10).
2. **Given** a template addressed by URN, **When** resolve-by-URN runs, **Then** it returns the same file as resolve-by-name.
3. **Given** a URN-backed template **and** a user override at `.kittify/overrides/templates/`, **When** resolve-by-URN runs, **Then** the override file wins (the URN lane honors the 5-tier precedence, same as the name lane).

### Edge Cases

- A step carrying no `template` ref mints no edge and contributes no `template_set` key (membership stays explicit).
- A typeless / unactivated mission context still hard-fails with a typed error (no inference).
- Two mission types must not resolve the same `template_file` path (per-type filenames — asserted by a guard test, see NFR-006).
- The emptiness detector cannot distinguish genuine content from a filler sentence — content substance is a reviewer-checklist gate (NFR-004), not only a green test.
- After all 16 prompts are filled, the seeded-blank scaffold in `test_prompt_emptiness.py` becomes vacuous — it is **retired and replaced** by a positive "every sequence step has a non-empty prompt" assertion (FR-008).

## Requirements *(mandatory)*

### Functional Requirements

| ID | Title | User Story | Priority | Status |
|----|-------|------------|----------|--------|
| FR-001 | Retire persisted `template_set` field | As a contributor, I want one authoring surface. Remove the `MissionType.template_set` field (`models.py:259`) **and** delete the **entire** `template_set` overlay assignment in `_inject_projected_fields` (`mission_type_repository.py:200-202`) — **keep** the adjacent `action_sequence` overlay (`:199`, retained per C-007). The pack-authored-`template_set` loud-fail (US2.2) then comes for free: `payload = dict(raw)` (`:198`) preserves the key and `extra="forbid"` rejects it. | High (P1a) | Open |
| FR-002 | Cached step-projection consumption seam | As the runtime, I want resolution sourced from the step authority. Re-point `_resolve_template_set_slot` (`mission_type_profiles.py:744`) from `mission.template_set` to `project_template_set(steps)` via `MissionStepRepository.resolve_all_for_mission_type(type, pack_context=None)`, **memoised per `(mission_type, pack_context)`** (the repo's `default()` is not memoised — avoid a `mission-steps/` walk per resolution). | High (P1a) | Open |
| FR-003 | Migrate CLI info surface off the removed field | As a CLI user, I want `mission_type` info to keep working. Migrate the two direct model-field reads — the `--json` path (`cli/commands/mission_type.py:1491`) and the human panel (`:1509-1511`) — to the resolved context, `dict()`-wrapping the `MappingProxyType` before `json.dumps`; add the currently-missing CLI test. | High (P1a) | Open |
| FR-004 | Author `documentation` content (7 steps) | As a doc author, I want documentation missions creatable. Author prompts for `discover/audit/design/generate/validate/publish/accept` on their own step names, promoting from existing `guidelines.md`. | High (P1b) | Open |
| FR-005 | Author `research` content (5 steps) | As a researcher, I want research missions creatable. Author prompts for `scoping/methodology/gathering/synthesis/output` on their own step names, promoting from existing `guidelines.md`. | High (P1b) | Open |
| FR-006 | Author `plan` content (4 steps, author-fresh) | As a planner, I want plan missions creatable. Author prompts + scaffold templates for `specify/research/plan/review` as plan-domain (decomposition/decision, no code) — plan has no guidelines source; do NOT clone the software-dev shape despite the name collision. | High (P1b) | Open |
| FR-007 | Per-type template refs → creatability | As the runtime, I want each of the three types to project a non-null template mapping (fixes #2689). Add a `template:` ref to a step in each type with **`artifact_key: "spec"`** (satisfies the `mission create` contract, Q1) and a second with **`artifact_key: "plan"`** (satisfies `/plan` setup); each `template_file` is per-type and unique (C-003). **Blocked-by Q1** (§Q1, now resolved) and by the FR-001/002/003 cutover (tidy-first). | High (P1b) | Open |
| FR-008 | Emptiness-test coupled edit + scaffold retirement | As the author, I want the guard to reflect reality. In `tests/doctrine/missions/test_prompt_emptiness.py`: as prompts are filled, shrink `_SEEDED_BLANK_STEPS` (`:54`), drop each `xfail`, decrement the golden `16` (`:176`), update `_SEQUENCE_STEPS_BY_TYPE` (`:161`); once the census is empty, **retire** the seeded-blank scaffold and replace it with a positive assertion that every sequence-step prompt is non-empty. **A single WP owns all edits to this file** (C-011). | High (P1b) | Open |
| FR-009 | Graph-back: template nodes + `instantiates` edges | As a doctrine reader, I want the chain navigable. A **new** extractor pass (modeled on `extract_mission_type_edges`, `extractor.py:864`, which already mints from the step projection) reads the **step projection** and mints `template:<mission>/<file>` nodes (via `template_catalog.template_urn`) + emits `action:<type>/<step> --instantiates--> template:<type>/<file>` edges (`Relation.INSTANTIATES`), landing in `action.graph.yaml`. **Why a new pass** (not "unskip templates"): a step's template ref is a structured `MissionStepTemplateRef` field, not a `references:` list entry, so no existing pass (`extract_artifact_edges`/`extract_action_edges`/`extract_mission_type_edges`) traverses it — templates are **not** skipped on this branch (`_SKIP_REF_TYPES` is empty). The pass graphs **all** template refs, software-dev's 2 existing ones included. | Medium | Open |
| FR-010 | Resolve-by-URN as a second lane | As the runtime, I want URN and name resolution. Add resolve-by-URN (converging on `template_catalog.resolve_template_by_id`, using the **mission-qualified** `template:<mission>/<name>` form) alongside resolve-by-name; the `template_file` filename stays the 5-tier filesystem override key, the URN identifies the DRG node — do not collapse the lanes (C-004). **Scope bound**: add the lane + a by-URN==by-name equivalence test only; do **NOT** re-wire the name-based creation path. | Medium | Open |
| FR-011 | Deterministic step ordering at the projection source | As a DRG-freshness owner, I want stable output. The nondeterminism originates **upstream** of `project_template_set` — in `resolve_all_for_mission_type`'s `set`-based step iteration (`mission_step_repository.py`), not in the projection dict (which is already insertion-ordered). Order the projected steps by `sequence_index` at the source (mirroring `project_action_sequence`, which already sorts), which deterministically fixes **both** `project_template_set` key-order **and** the FR-009 graph pass. Additionally sort edge emission by `(source_urn, target_urn)`. Do **NOT** key-sort the dict by `artifact_key`. software-dev's order stays `{spec, plan}` (specify=idx0, plan=idx1). | Medium | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | Behavior preservation (software-dev) | software-dev's resolved template **filenames** are byte-for-byte identical pre/post cutover, and `TestSoftwareDevProjectionParity` (`test_softwaredev_roundtrip.py:68-112`) stays green. The `mission_type show --json` `template_set` **key order** canonicalizes to `sequence_index` order (deterministic) — update the CLI-test baseline to that canonical order rather than the prior `set`-dependent order (this is a determinism fix, not a behavior regression). | Correctness | High | Open |
| NFR-002 | Intentional, computable DRG delta | The FR-009 pass adds **N** template nodes and **N** `instantiates` edges, where **N = every step carrying a `template` ref across all four types, software-dev included** (software-dev contributes 2 genuinely-new **mission-qualified** `template:<mission>/<name>` nodes — distinct from, and leaving untouched, the 16 bare `template:<name>` exemplars from #2712, which stay `edges:[]`; each authored ref for the three types adds 1). **N is derived from FR-007 authoring after Q1 — computed-then-pinned at the END of authoring, never asserted upfront**; the FR-009 graph WP has a hard dependency on the authoring WP (C-012). Node delta == edge delta == N; **orphans stay 10** (each new template node has an `instantiates` in-edge), ceiling 14 untouched. Bump `_EXPECTED_NODE_COUNT`/`_EXPECTED_EDGE_COUNT` (`test_extractor_projection.py:40-41`) to `280+N`/`757+N`. **Sweep and re-baseline every arch marker**, not just projection counts: orphan-residual, `_ARCH_SHARD_N_FILES` (if the instantiates assertion is a new test file), template cardinality golden-counts; add a positive shipped-graph `instantiates` assertion; `regenerate-graph --check` + `tests/doctrine/drg/` freshness green. | Correctness | High | Open |
| NFR-003 | No uncached step-resolution | The FR-002 seam performs **exactly one** `mission-steps/` resolution per `(mission_type, pack_context)` regardless of how many template resolutions occur — asserted by a call-count/spy test (not a latency budget; `template_set` is off the FSM hot path, so `<100ms` never gates it). | Performance | High | Open |
| NFR-004 | Genuine content (two-tier gate) | **Machine floor**: every filled prompt is non-empty and free of `TODO`/`PLACEHOLDER`/`FIXME` (US1.4). **Substance gate**: each prompt is genuine per-type exemplar content, verified by an explicit reviewer-checklist item (min structural sections, per-type vocabulary) — the detector cannot verify substance, so this is a human gate, not an aspiration. | Quality | High | Open |
| NFR-005 | Quality gates | ruff + mypy --strict clean, zero new suppressions; cyclomatic complexity ≤15; literals appearing ≥3× hoisted to constants. | Maintainability | High | Open |
| NFR-006 | Cross-type filename uniqueness guard | A guard test asserts no two mission types project the same `template_file` path (prevents the plan/software-dev name-collision contaminating one filename). | Correctness | High | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | Fail-closed frozen (#2689/#2660) | Fix creatability by authoring content — never by relaxing the `resolve_configured_template` null-guard or the typeless rejection, and never by re-adding software-dev inference. A pack authoring `template_set:` must FAIL LOUDLY. | Technical | High | Open |
| C-002 | Scalar-surface reference fence (C-008) | New URN/resolver code must **never reference the scalar `template_set` surfaces**: `resolution.template_set` (`specify_cli/runtime/doctor.py:154,166`; `src/runtime/next/prompt_builder.py:441`), `MissionTypeProfile.template_set` (the scalar field `charter/mission_type_profiles.py:145`, display `:1001-1004` — **same file as the in-scope dict slot `:744`**, so no blind grep-replace on `template_set`), and `doctrine.template_set` (`charter/*`). (Note: importing `ResolvedMissionType` from `charter.mission_type_profiles` is required and allowed — the fence is on *referencing the scalar*, not on importing from `charter`.) | Technical | High | Open |
| C-003 | Per-type `template_file`; shared `artifact_key` contract | Each type authors on its own step names with its own **`template_file`** (unique across types, NFR-006). But **`artifact_key` is the shared runtime-contract vocabulary** — `"spec"` (creation) and `"plan"` (plan-setup), identical across all types (Q1); it is NOT per-type-free. No software-dev `template_file` reuse. | Technical | High | Open |
| C-004 | Name↔URN compatibility contract | Resolve-by-name and resolve-by-URN are two lanes, not one; the 5-tier filesystem override chain works for both (US3.3); software-dev's live templates unaffected. | Technical | High | Open |
| C-005 | Keep the enduring parity guard | From `TestMissionTypeRepositoryLiveProjection` (class `test_softwaredev_roundtrip.py:115`) retire **only** the `template_set` method (`:131-135`) — **KEEP** the `action_sequence` method (`:125-129`, validates the C-007-retained overlay; deleting the whole class by name drops retained coverage). Migrate **every** `.template_set` read on a `MissionType` instance (grep-driven, not a fixed line list) to `project_template_set(steps)`/`ResolvedMissionType` — explicitly includes `test_mission_type_repository.py:47` (outside the `:89-105`/`:181-197` ranges), `:89-105`, `:181-197`, `test_step_schema.py:197-211`, `test_step_projection.py:255/318`; distinguish from surviving `step.template` reads. Do NOT delete `TestSoftwareDevProjectionParity`. | Technical | High | Open |
| C-006 | Do not rename the resolved property | Leave `ResolvedMissionType.template_set` named as-is (wide blast radius, all-green, no correctness benefit; field removal already kills the split-brain; residue is derived-read-only, not authorable). | Technical | Medium | Open |
| C-007 | `action_sequence` symmetry deferred (#2751) | The identical persisted-projection pattern for `action_sequence` is OUT OF SCOPE — it crosses a different gate (DRG shipped-graph + freshness), a hard non-empty `validate_action_sequence` invariant, and the eager FSM hot-path. Filed as #2751 (blocked-by this mission). The `_inject_projected_fields` `action_sequence` overlay (`:199`) stays untouched. | Technical | High | Open |
| C-008 | No PR opened; operator merges | PR-bound mission, but we do not open a PR; the operator merges manually. | Process | Medium | Open |
| C-009 | Atomic cutover (FR-001+002+003) | The field removal, consumer re-point, and CLI migration are a **single lockstep cutover** — they land in one work package (or strictly ordered on the same tree). Removing `MissionType.template_set` while any `mission.template_set` read (`_resolve_template_set_slot:772`) or CLI read (`:1491/:1509`) remains throws `AttributeError`. | Technical | High | Open |
| C-010 | Q1 gates authoring | The `artifact_key` contract (`"spec"`/`"plan"`, §Q1) is a **hard predecessor** of FR-004/005/006/007 — authoring against a wrong key leaves the type uncreatable despite all content. | Technical | High | Open |
| C-011 | Single owner for the emptiness test | All edits to `tests/doctrine/missions/test_prompt_emptiness.py` (FR-008) are owned by **one** work package (with the three content WPs as inputs) or strictly serialized — three WPs decrementing the same golden `16` and pruning the same tuple would merge-conflict. | Technical | High | Open |
| C-012 | Projection-consumer ordering | `step_projection.py` is a shared seam: the tidy-first cutover (FR-001/002) precedes authoring (FR-004..007); FR-007 (step refs) precedes FR-009 (which reads them); FR-011 (edge ordering) lands with or before FR-009. Linearize `step_projection.py`, `mission_type_repository.py`, `models.py`, `mission_type_profiles.py`, `extractor.py`, `test_prompt_emptiness.py` in /plan. | Technical | High | Open |

### Key Entities

- **MissionStep** (`step.yaml` → `models.py:87`): the single authority; carries `sequence_index`, `in_action_sequence`, `prompt_template`, and the `template` ref (`artifact_key`, `template_file`).
- **MissionType** (`models.py:252`): frozen, `extra="forbid"`; after this mission it no longer carries a persisted `template_set` field. Has no `.steps` attribute — steps resolve via `MissionStepRepository`.
- **template: DRG node / instantiates edge**: `template:<mission>/<file>` node + `action:<type>/<step> --instantiates--> template` edge (action-sourced, in `action.graph.yaml`).
- **ResolvedMissionType** (`mission_type_profiles.py:304`): the charter→runtime bundle; `template_set` is a lazy `@cached_property` (name retained per C-006).

## Success Criteria *(mandatory)*

- **SC-001**: All four built-in mission types — including `documentation`, `research`, `plan` — are creatable end-to-end (each `mission create` succeeds, and `plan`-setup resolves too), closing #2689. *(FR-004/005/006/007, C-010)*
- **SC-002**: Zero persisted/authorable `MissionType.template_set` field references remain; a `mission_types/*.yaml` authoring `template_set:` fails loudly (regression test). *(FR-001, US2.2)*
- **SC-003**: The 16 seeded-blank step prompts all carry genuine per-type content (machine floor + reviewer-checklist substance gate); the emptiness scaffold is retired and replaced by a positive assertion. *(FR-004..008, NFR-004)*
- **SC-004**: The `mission_type → step → template` chain is graph-backed — every authored template resolves by name and by URN; DRG freshness green with the asserted `+N/+N` delta and orphans = 10. *(FR-009/010/011, NFR-002)*
- **SC-005**: software-dev behavior is unchanged (byte-for-byte template-resolution + `--json` parity). *(NFR-001)*

## Q1 (RESOLVED) — the creation `artifact_kind` contract

**Traced this session (code-verified).** At `mission create`, `mission_creation.py:351-355` calls `resolve_configured_template("spec", …)` — the **literal `"spec"`, hardcoded, generic across all types**. The `/plan`-setup path (`mission_setup_plan.py:453-457`) later requests the literal `"plan"`. There is **no per-type/per-step derivation and no alias layer** on the content-template side (`decision.py:_ALIASES` maps state→*command*-template names via `resolve_command`, an unrelated surface). Since `project_template_set` keys on `artifact_key` and the resolver does `template_set.get("spec")`, **each type must author a step whose `template.artifact_key` is exactly `"spec"`** (creatability) **and one `"plan"`** (plan phase). `template_file` is the only per-type authoring choice (which step hosts each ref + the filename, which must resolve under the type's templates dir). → This resolves the former open question and binds FR-007 + C-003 + C-010.

## Out of Scope (deferred)

- `action_sequence` symmetry cutover (**#2751**, blocked-by this mission).
- FR-009 role/model consolidation and FR-011 MISSION_STEP_CONTRACT/D6 (prior #2721 deferrals). *(Note: these are ADR-numbered items, distinct from this spec's FR-009/FR-011.)*
- S-D substeps (#2725), S-E guards (#2726).

## Traceability

- **Closes** the #2689 uncreatable regression (only content authoring closes it). **Resolves** #883 (per ADR 2026-07-16-2 — the `mission_type→template` edge class / non-software mission-type support; #883 confirmed OPEN). Slice **S-C** of ADR 2026-07-16-2 (D3), under sub-epic #2721 / epic #2652. Spawns follow-up **#2751** (`action_sequence` symmetry).
- Grounding: the 3-lens research squad + the 3-lens adversarial verification squad + the Q1 trace + the 3-lens spec-review squad — captured in `research.md`.
