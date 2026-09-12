# Tasks: Charter as Sole Door: Close Bypass Access Paths

**Input**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/`, `quickstart.md` from
`kitty-specs/charter-sole-door-bypass-closure-01KZ3WAA/`

Subtask completion is event-sourced (`spec-kitty agent tasks mark-status <Txxx> --status done`), not a
markdown checkbox. Rows below are reference only.

**Restructured by a post-tasks adversarial squad** (architect-alphonso, reviewer-renata, debugger-debbie,
paula-patterns) after first generation — see each WP's Activity Log / History for what changed and why.
Headline fixes: (1) **CRITICAL** — WP02/WP03/WP04's `dependencies: []` frontmatter never actually declared
WP01, despite the prose saying so everywhere (found independently by 3 of 4 delegates); (2) former WP07
merged into WP01 (both edited `src/charter/resolver.py`; the split forced an awkward 3-lane serialization
for no benefit); (3) the durability-gate WP (former WP09) had 2 of its 5 gates moved to the WPs whose
surface they actually guard (WP04 absorbed Gate 5, WP06 absorbed Gate 4); (4) several accessor method names,
line-number citations, and one WP's core premise were corrected after independent verification against the
live code.

## Subtask Index

| ID | Description | WP | Parallel |
|----|---|----|----|
| T001 | Implement the pinned `agent_profile_repository` accessor on `charter.resolver.DoctrineService` | WP01 | |
| T002 | Unify the two named builder functions into one (`active_languages` always computed, `org_roots` always self-resolved) | WP01 | |
| T003 | Retarget `org_layer.py:244,275` and `generate.py:56` onto the unified builder; fix fail-open `except ImportError: pass` | WP01 | |
| T004 | Regression test: unified builder identical output across ALL 9 gated properties (one pass, not staged) | WP01 | |
| T005 | ATDD test: accessor semantics (`register_overlay()`, `get_provenance()`) | WP01 | |
| T026-T031 | Add 6 mechanical properties (`directives`/`tactics`/`styleguides`/`toolguides`/`mission_step_contracts`/`glossary_packs`) | WP01 | [P] |
| T032 | Bare-project equality regression test per kind (6 tests): wrapped == unwrapped inner service | WP01 | |
| T006 | Capture pre-mission p95 baseline (raw timing series) for `spec-kitty agent tasks status` on a 100+-WP fixture | WP02 | |
| T007 | Migrate `runtime_bridge_io.py:576` onto the factory via WP01's accessor (`resolve_profile`) | WP02 | [P] |
| T008 | Migrate `projection.py:84` onto the factory via WP01's accessor (`register_overlay` only) | WP02 | [P] |
| T009 | Migrate `tasks_status_cmd.py:712,823`; re-measure p95 in the same session, compare against T006 | WP02 | |
| T010 | Confirm `charter/profile_resolution.py:81` is a genuine bootstrap case, document, do NOT migrate | WP02 | [P] |
| T011 | Migrate `charter/compiler.py:802` onto the factory | WP03 | [P] |
| T012 | Migrate `_doctrine_asset.py:75` onto the factory | WP03 | [P] |
| T013 | Migrate `_doctrine_collect.py`'s 4 sites (lines 193/283/420/828) onto the factory's unfiltered mode | WP03 | |
| T014 | Regression test: unfiltered mode returns catalog identical to the raw unwrapped service | WP03 | |
| T015 | Migrate `registry.py:64` off `._inner.agent_profiles` onto WP01's accessor (`get_provenance`) | WP04 | [P] |
| T016 | Migrate `org_profiles.py:117` off `._inner.agent_profiles` onto WP01's accessor (`get_provenance`) | WP04 | [P] |
| T017 | Gate 5 (absorbed): mission-wide zero-tolerance `._inner`-on-doctrine-service gate, self-mutation proven, true-negative tested | WP04 | |
| T018 | Add resolution methods (distinct names, no collision) to `charter.resolver.DoctrineService` | WP05 | |
| T019 | Resolve the construction-contract mismatch for `CharterTemplateResolver`'s one real caller (`repo_root` vs `missions_root`) | WP05 | |
| T020 | Retarget `CharterTemplateResolver` (thin delegate or retire in favour of direct factory use) | WP05 | |
| T021 | Regression test: tier resolution via factory matches the old direct-call result | WP05 | |
| T022 | Make `builtin_missions_root()` a thin delegate to `MissionTemplateRepository.default_missions_root()` | WP06 | [P] |
| T023 | Retarget `runtime/home.py`'s `dev_roots` fallback onto `default_missions_root()` | WP06 | [P] |
| T024 | Equality regression test for both retargeted sites | WP06 | |
| T025 | Document `home.py`'s residual `#2986`-shared risk, the `#3091`-deferred convergence, AND 3 newly-found untouched residual hardcodes | WP06 | |
| T040 | Gate 4 (absorbed): hardcoded missions-root path-literal gate + self-mutation proof | WP06 | |
| T034 | Add activation filtering to `resolve_mission_type_context()` (NOT `MissionTypeProfileRepository`'s own file) | WP08 | |
| T035 | Bare-project regression test: set-equality against `builtin_mission_type_id_set()` | WP08 | |
| T036 | Regression test: a subset of activated mission-types returns only that subset | WP08 | |
| T037 | Gate 1: zero-tolerance, qualname-resolving `AgentProfileRepository` gate + composite-key exclusions + self-mutation proof | WP09 | [P] |
| T038 | Gate 2: zero-tolerance, qualname-resolving `DoctrineService` gate + composite-key exclusions + self-mutation proof | WP09 | [P] |
| T039 | Gate 3: `doctrine.resolver` direct-import forward-looking regression guard + self-mutation proof | WP09 | [P] |
| T042 | Add `issue-matrix.json` rows + citable docs record for #2986/#3036/#3039/#3091/#3022 | WP10 | [P] |
| T043 | Post a tracker comment on each of the 5 deferred issues; paste `gh issue view --comments` output as evidence | WP10 | [P] |
| T044 | Add the NFR-004 `CHANGELOG.md` entry (9-kind gating, `.kittify/profiles` exclusion, deferred `pack_paths` convergence) | WP10 | [P] |

## Work Packages

### WP01 — Extend the charter factory: accessor, builder unification, 6 mechanical kinds (Priority: P1)

**Goal**: One canonical builder; one new lineage/mutation accessor; 6 new activation-gated properties.
**Requirements**: C-001, FR-001, FR-005, FR-008, FR-010.
**Independent test**: construct the unified builder from both former call sites' inputs — identical output
across all 9 gated properties; bare-project equality holds for each of the 6 new kinds.
**Subtasks**: T001-T005, T026-T032 (10 subtasks — over the 3-7 ideal / at the 10 max, a deliberate
consolidation the post-tasks squad recommended over a 3-way split that all touched the same file).
**Dependencies**: none (first). **Estimated size**: ~240 lines (still within the 700-line hard cap despite
subtask count, since most of T026-T031 is copy-paste of one pattern).
**Risks**: the accessor's semantics are pinned in the prompt — implement against that text, do not
re-derive. Write T004's identical-output proof once, against the full 9-property surface, not staged.

### WP02 — Migrate `AgentProfileRepository` sites + NFR-005 measurement (Priority: P1)

**Goal**: Close 4 of 5 in-scope direct `AgentProfileRepository` construction sites (the 5th,
`profile_resolution.py:81`, is confirmed a genuine bootstrap case and is documented, not migrated); prove no
perf regression.
**Requirements**: FR-001, NFR-005.
**Independent test**: grep confirms zero direct construction at the 4 migrated sites; p95 latency (raw
timing series, same session) within 10% of baseline.
**Subtasks**: T006-T010. **Dependencies**: WP01 (fixed — the original frontmatter omitted this; found by 3
of 4 post-tasks squad delegates independently). **Estimated size**: ~400 lines.
**Risks**: T006 MUST run before T009 touches `tasks_status_cmd.py`. `projection.py:84` needs
`register_overlay()` only (not `get_ancestors()`, which is unused there).

### WP03 — Migrate raw `DoctrineService` sites (Priority: P1)

**Goal**: Close the 6 originally-flagged raw `DoctrineService` construction sites (the 3 additional sites
found by the post-plan squad — `org_layer.py`/`generate.py` — are WP01's).
**Requirements**: FR-002.
**Independent test**: grep confirms zero raw construction outside the factory/builder; `_doctrine_collect.py`
diagnostics still see the full unfiltered catalog.
**Subtasks**: T011-T014. **Dependencies**: WP01 (fixed — see WP02's note). **Estimated size**: ~350 lines.
**Risks**: a plain activation-aware swap on `_doctrine_collect.py` silently narrows doctor/health output —
must use `pack_context=None` explicitly. Line numbers are 193/283/420/828 (corrected — the original
citations had drifted +2 lines).

### WP04 — Close the `._inner` reach-around + Gate 5 (Priority: P1)

**Goal**: Eliminate the escape hatch that would otherwise defeat every other WP's gating; ship its own
durability gate (absorbed from the former WP09).
**Requirements**: FR-010, FR-007.
**Independent test**: zero `._inner` attribute access on a doctrine-service-typed expression outside
`src/charter/**`, gate-enforced with a self-mutation proof (both true-positive and true-negative tested).
**Subtasks**: T015-T017. **Dependencies**: WP01 (fixed). **Estimated size**: ~210 lines.
**Risks**: both sites need `get_provenance()` (corrected — not `register_overlay()`). The gate must not
false-positive on unrelated `._inner` attributes in `auth/transport.py`/`events/decision_log.py`.

### WP05 — Consolidate the template/command resolver axis onto the factory (Priority: P1)

**Goal**: Fold `CharterTemplateResolver` (a second charter-layer door) into the factory — a *reframed* goal
(post-tasks squad correction: the original "stops importing doctrine.resolver directly" premise was false;
nothing outside `src/charter/**` ever imported it).
**Requirements**: FR-003.
**Independent test**: tier resolution via the factory matches the old `CharterTemplateResolver` result;
`doctrine/resolver.py` itself is untouched.
**Subtasks**: T018-T021. **Dependencies**: WP01 (T018 adds methods to `src/charter/resolver.py`, WP01's
sole declared owner — a sequenced, dependency-gated out-of-map edit).
**Estimated size**: ~340 lines.
**Risks**: pick new method names — do NOT reuse `CharterTemplateResolver`'s existing
`resolve_command_template`/`resolve_content_template` names, which have different signatures (a real
naming-collision risk found by the squad).

### WP06 — Consolidate missions-root path hardcodes + Gate 4 (Priority: P1)

**Goal**: Retarget the 2 duplicate missions-root hardcodes onto one promoted authority; ship its own
durability gate (absorbed from the former WP09); name 3 newly-found untouched residual duplicates honestly.
**Requirements**: FR-004, FR-007.
**Independent test**: equality regression test — both retargeted sites resolve identically to
`default_missions_root()`; gate self-mutation proof fails on a reintroduced hardcode.
**Subtasks**: T022-T025, T040. **Dependencies**: none (parallel). **Estimated size**: ~300 lines.
**Risks**: do not claim `pack_paths.built_in_dir` convergence. Do not silently omit the 3 newly-found
residual hardcodes (`kernel/paths.py`, `template/manager.py`, `list_cmd.py` — verify exact citations before
writing, the squad's line numbers were not independently re-checked) — name them, don't fix or hide them.

### WP08 — Mission-type activation gating (Priority: P1)

**Goal**: Gate the `mission-type` token via `resolve_mission_type_context()`, not `DoctrineService` or
`MissionTypeProfileRepository`'s own file (ownership boundary with WP06).
**Requirements**: FR-006.
**Independent test**: a bare project's mission-type set equals `builtin_mission_type_id_set()`; an activated
subset returns only that subset.
**Subtasks**: T034-T036. **Dependencies**: none (parallel). **Estimated size**: ~250 lines.
**Risks**: T035's assertion MUST be set-equality against `builtin_mission_type_id_set()`, not a fakeable
subset check.

### WP09 — Durability gates 1-3 (Priority: P2)

**Goal**: Ship non-vacuous, zero-tolerance, qualname-resolving architectural gates for the three genuinely
cross-cutting bypass categories (Gates 4 and 5 moved to WP06/WP04 — each only ever guarded its own WP).
**Requirements**: FR-007, NFR-001, NFR-003.
**Independent test**: each gate's self-mutation proof (function-local/nested injection) fails when the
guarded shape is reintroduced, naming the offending site.
**Subtasks**: T037-T039. **Dependencies**: WP01, WP02, WP03, WP05 (must run after these land — a gate
written before the bypasses close is either vacuous or immediately red). **Estimated size**: ~300 lines.
**Risks**: Gate 2's exclusion line numbers must be re-verified against the post-WP03 worktree state, not
assumed. Gate 3 is a forward-looking regression guard, not proof of a WP05 closure — there was no violation
outside `src/charter/**` to close in the first place.

### WP10 — Deferred-issue tracker hygiene + CHANGELOG entry (Priority: P2)

**Goal**: Give the five confirmed-deferred issues a durable tracker trace, not just PR-description prose;
add the CHANGELOG entry NFR-004 requires (added by `/spec-kitty.analyze` finding E1 — the original task
breakdown had zero coverage for this NFR).
**Requirements**: FR-011, NFR-004.
**Independent test**: each of #2986/#3036/#3039/#3091/#3022 carries an `issue-matrix.json` row, a citable
docs record, and a tracker comment naming this mission — with the comment's existence proven via pasted
`gh issue view --comments` output (non-fakeable evidence requirement, post-tasks squad correction);
`CHANGELOG.md` names all three NFR-004 items.
**Subtasks**: T042-T044. **Dependencies**: none (fully independent of code; can run any time).
**Estimated size**: ~150 lines.

## Sequencing Summary

```
WP01 ─┬─> WP02 ──┐
      ├─> WP03 ──┤
      ├─> WP04 ──┤──> WP09 (Gates 1-3, last; depends on WP01/02/03/05)
      └─> WP05 ──┘
WP06 (independent, ships its own Gate 4)
WP08 (independent)
WP10 (fully independent, any time)
```

`src/charter/resolver.py` is edited by WP01 (sole declared owner: accessor, builder unification, 6
mechanical properties) and WP05 (tier-axis methods, a sequenced, dependency-gated out-of-map edit — WP05
depends on WP01, never parallel with it). The former 3-way split (WP01/WP05/WP07) was consolidated to
WP01+WP05 after a post-tasks squad found the split added a serialization stage for no benefit.

MVP scope: WP01-04 (the direct-construction closure + accessor + Gate 5) delivers the largest single chunk
of the "sole door" claim independently of WP05/06/08's axis/path/mission-type work.
