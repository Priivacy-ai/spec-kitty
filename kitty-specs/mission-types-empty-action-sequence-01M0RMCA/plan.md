# Implementation Plan: Org/project-layer mission types resolve an empty action sequence

**Branch**: `fix/mission-types-empty-action-sequence-3701` | **Date**: 2026-08-24 | **Spec**: [`spec.md`](./spec.md)
**Input**: Mission specification from `kitty-specs/mission-types-empty-action-sequence-01M0RMCA/spec.md`

**Note**: This is a bug-fix / infrastructure-defect mission (spec.md Summary), not a new user-facing
feature. There is no new user story to design a UI or API surface for — the "design" here is a
four-function argument-threading fix inside one existing seam. All line numbers below were
re-verified against this checkout's actual `src/doctrine/missions/mission_type_repository.py`
during plan authoring (2026-08-24), not copied from spec.md's own citations, per this mission's
own instruction to verify rather than trust. No drift was found against spec.md's citations.

## Summary

`_inject_projected_fields()` (`src/doctrine/missions/mission_type_repository.py:209-253`) hardcodes
`pack_context=None` in its call to `MissionStepRepository.default().resolve_all_for_mission_type(mission_type_id, pack_context=None)`
(line 245). Because none of its three callers up the chain forward a `pack_context` value into it
either, every org/project mission type that relies on step-file projection (no explicit
`action_sequence:` authored in its own `<type>.yaml`) resolves `action_sequence = None`/`[]`, and
every governed entry point then raises `MissionTypeEmptyActionSequenceError`
(`src/charter/mission_type_profiles.py:259`).

The fix threads one already-in-hand `pack_context` value through the existing four-function call
chain — `_inject_projected_fields` → `_load_layered_mission_type_file` → `scan_mission_types_dir`
→ `resolve_layered_mission_types` — so that every layer's own step-file projection sees the real,
fully-layered step set instead of a built-in-only one. This is a pure argument-threading change:
no new I/O, no new control flow, no model/schema change. Concretely, three call sites inside
`resolve_layered_mission_types` (built-in-equivalent layer, org layer, project layer — all three
currently call `scan_mission_types_dir(base_dir)` / `scan_mission_types_dir(org_dir)` /
`scan_mission_types_dir(project_dir)` without forwarding the `pack_context` parameter that
function already receives) start passing `pack_context=pack_context`, and each function down the
chain gains (or forwards) a `pack_context: _PackContextLike | None = None` parameter so the value
reaches `_inject_projected_fields`'s `resolve_all_for_mission_type` call. `MissionTypeRepository._load()`
(the built-in-only, `cls`-keyed cache, line 165) is deliberately **not** touched — its zero-argument
call already resolves to `pack_context=None` via the new default (FR-005/C-001).

## Technical Context

**Language/Version**: Python 3.11+ (charter: "Technical Standards" → "Languages and Frameworks").
**Primary Dependencies**: none added — `ruamel.yaml`, `pydantic` (via `MissionType`), and the
sibling `doctrine.missions.mission_step_repository` module (`_PackContextLike`, `MissionStepRepository`)
are all already-imported, already-used surfaces in this file. No `pyproject.toml`/`uv.lock` change.
**Storage**: N/A — this is a pure in-memory YAML-load/projection seam; no persistence changes.
**Testing**: `pytest`, targeted per charter's "Run only the affected test packages" guidance —
`tests/doctrine/missions/test_mission_type_repository.py` and `tests/runtime/test_runtime_seam.py`
(C-007's own test-file bound). Both files carry `pytestmark = [pytest.mark.fast, ...]`
(`test_mission_type_repository.py:32` — `fast, doctrine, corpus`; `test_runtime_seam.py:67` —
`unit, fast`), so this mission's tests land entirely in the fast tier, not integration.
**Target Platform**: N/A — this is CLI/library-internal doctrine-layer code, not
platform-differentiated.
**Project Type**: Single project (this repository, the `spec-kitty` CLI/doctrine codebase itself).
**Performance Goals**: NFR-004 — no new filesystem walk; threading an already-resolved
`pack_context` value is an argument-forwarding change, not new I/O. Charter's blanket "<2s for
typical projects" CLI budget is unaffected because no new I/O is added.
**Constraints**: C-001 through C-008 (spec.md Constraints table) — most load-bearingly C-007
(blast radius: one file, four functions, plus the two named test files) and C-008 (all four
functions type `pack_context` as `_PackContextLike | None`, never the concrete `PackContext`
class, even under `TYPE_CHECKING`).
**Scale/Scope**: One file (`src/doctrine/missions/mission_type_repository.py`), four function
signatures, three internal call-site edits inside `resolve_layered_mission_types`, one edit inside
`_inject_projected_fields`'s body, one edit inside `_load_layered_mission_type_file`'s body, one
edit inside `scan_mission_types_dir`'s body. Two test files gain new test classes/cases. Zero
other `src/` files change (`charter/pack_manager.py:865`'s call site is verified unaffected —
see FR-008 below).

## Charter Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

This mission has no Phase 0 research step (no `NEEDS CLARIFICATION` markers survive spec.md — both
candidate decision forks were resolved before spec authoring, per spec.md's own `## Clarifications`
section) and no Phase 1 data-model/contracts step (no data model changes — see Contracts below).
Gates checked directly against the charter:

- **Architectural alignment** (charter Governing Principles): the fix stays entirely inside the
  doctrine layer's own existing seam (`src/doctrine/missions/`) and does not reach into or around
  the charter layer. PASS — see Seam below.
- **Single canonical authority / no duplicate authority** (charter Governing Principles,
  `DIRECTIVE_044`): no new resolver, no second `pack_context`-threading mechanism is introduced —
  this mission extends the *existing* `resolve_layered_mission_types` roster-layering pattern
  (already used for the type roster itself, #3397) to also cover the projection seam, mirroring
  `_resolve_template_set_slot`'s already-working pattern (spec.md Decision 1). PASS.
  C-002 binds this: no `template_set`-style migration is introduced.
- **ATDD-first / red-first** (charter `ATDD-First Discipline`, C-011; Standing Order #4): NFR-001's
  red-first test is the WP's first committed test, authored and witnessed red before the fix lands.
  See "Red-first/ATDD and SC-004's concrete stash/rerun/stash-pop moment" below. PASS (by
  construction, enforced there).
- **Campsite cleaning** (Standing Order #2, `DIRECTIVE_025`): see Campsite-clean below — no
  domain-matched debt found inside the four touched functions' bounds; the opening commit is
  named but minimal-scope.
- **Locality of change / smallest-viable-diff** (`RECONCILE_CHANGE_SCOPE_TENSIONS`, `DIRECTIVE_024`):
  C-007 already pins the file set (one `src/` file, two test files). No extension beyond that
  touched area is contemplated. PASS.
- **Tracker ticket assignment rule**: the orchestrator (not this plan-authoring pass) is
  responsible for assigning issue #3701 to the HiC before/while implementation begins — noted here
  so the implement phase does not skip it, not re-litigated in this plan.
- **Terminology canon** (`Mission` not `Feature`): no new user-facing strings are introduced by
  this fix; N/A beyond the existing file's own vocabulary, which already conforms.

No Charter Check violations requiring justification — **Complexity Tracking is not filled in**
(empty per its own "Fill ONLY if Charter Check has violations" instruction).

## Project Structure

### Documentation (this mission)

```
kitty-specs/mission-types-empty-action-sequence-01M0RMCA/
├── spec.md                        # Reviewed baseline (complete, committed, not edited by this plan)
├── plan.md                        # This file
├── tracer-tooling-friction.md     # Seeded at planning; appended by this pass and by implementation
├── tracer-approach.md             # Seeded at planning; appended by this pass and by implementation
├── tracer-design-decisions.md     # Seeded at planning; appended by this pass and by implementation
└── tasks.md                       # Phase 2 output (/spec-kitty.tasks — NOT produced by this plan)
```

No `research.md`, `data-model.md`, `quickstart.md`, or `contracts/` are produced — there is no
open research question (both Clarifications forks are already resolved in spec.md), no new/changed
data model (see Contracts below), and no new consumer-facing quickstart. Producing empty
placeholder files for phases with nothing to say would be scope-inflation against
`RECONCILE_CHANGE_SCOPE_TENSIONS`'s smallest-viable-diff step.

### Source Code (repository root)

```
# Option 1: Single project — this IS the structure; no alternative considered
src/doctrine/missions/
├── mission_type_repository.py     # THE file this mission changes (4 functions + 3 internal call sites)
├── mission_step_repository.py     # _PackContextLike Protocol (read, not modified) — already imported
├── models.py                      # MissionType, validate_action_sequence (read, not modified)
└── step_projection.py             # project_action_sequence (read, not modified)

src/charter/
├── pack_manager.py                 # :865 call site — verified unaffected (FR-008), not modified
├── pack_context.py                 # PackContext concrete class — read for shape only, never imported
│                                    # into src/doctrine/ (C-008)
└── mission_type_profiles.py        # _resolve_action_slot / MissionTypeEmptyActionSequenceError —
                                     # consumer, unaffected in signature, benefits from the fix
                                     # transitively; not modified by this mission

tests/doctrine/missions/
└── test_mission_type_repository.py # NFR-001 red-first test + supporting fixtures added here

tests/runtime/
└── test_runtime_seam.py            # NFR-002 golden-parity extension added here
                                     # (TestGoldenParityUnaffectedByPackContextThreading)
```

**Structure Decision**: Single project, no new directories or modules. The change is entirely
signature/body edits inside one already-existing file, plus additions inside two already-existing
test files — this is the smallest possible structural footprint for a four-function
argument-threading fix (C-007).

## Complexity Tracking

*Fill ONLY if Charter Check has violations that must be justified* — empty; no violations found.

## Implementation Concern Map

This mission uses **exactly one Implementation Concern**, stated explicitly rather than omitted,
because the template's own trigger ("multiple distinct architectural areas") does not apply here:
the four touched functions are not separate architectural areas but a single call chain (one
seam, `_inject_projected_fields` → `_load_layered_mission_type_file` → `scan_mission_types_dir` →
`resolve_layered_mission_types`) that must be threaded together as one coherent unit — threading
only part of the chain would leave the defect unfixed. Splitting this into multiple ICs would
misrepresent the change's actual shape and risk `/spec-kitty.tasks` slicing it into WPs with a
false independence boundary. One IC, one seam, one WP is the honest decomposition (also see PR
shape below).

### IC-01 — Thread `pack_context` through the projection seam

- **Purpose**: Fix the projection seam so org/project mission types with steps-only
  `action_sequence` projection resolve correctly instead of `None`/`[]`, without perturbing
  built-in resolution or `MissionTypeRepository._load()`'s built-in-only cache.
- **Relevant requirements**: FR-001, FR-002, FR-003, FR-004, FR-005, FR-006, FR-007, FR-008;
  NFR-001, NFR-002, NFR-003, NFR-004; C-001 through C-008 (all bind this one concern — there is no
  requirement in spec.md that falls outside it).
- **Affected surfaces**:
  - `src/doctrine/missions/mission_type_repository.py`:
    - `_inject_projected_fields` (line 209): add keyword-only `pack_context: _PackContextLike | None = None`;
      forward it into the `resolve_all_for_mission_type(mission_type_id, pack_context=pack_context)`
      call at line 245 (replacing the hardcoded `pack_context=None`).
    - `_load_layered_mission_type_file` (line 313): add keyword-only
      `pack_context: _PackContextLike | None = None`; forward it into the
      `_inject_projected_fields(raw, mission_type_id=yaml_file.stem, pack_context=pack_context)`
      call at line 347 (currently omits the argument entirely).
    - `scan_mission_types_dir` (line 359): add keyword-only `pack_context: _PackContextLike | None = None`;
      forward it into the `_load_layered_mission_type_file(f, pack_context=pack_context)` call in
      its list-comprehension return.
    - `resolve_layered_mission_types` (line 410): already receives `pack_context` as a required
      positional parameter (typed `_PackContextLike | None` at line 412, pre-existing, confirming
      C-008's citation) — no signature change needed here. The fix is inside its **body**: its
      three `scan_mission_types_dir(...)` calls (built-in-equivalent layer, org layer, project
      layer) must each pass `pack_context=pack_context` instead of omitting the argument.
  - `tests/doctrine/missions/test_mission_type_repository.py`: new test class/cases for NFR-001
    (red-first, steps-only-projection reproduction) — sibling to the existing
    `TestLayeredMissionTypesCacheKeyAndClear` class (line 458), reusing its `_StubPackContext`
    (line 431) and `_write_layered_yaml`/`_mission_type_yaml` helpers where they fit, extending
    (not duplicating) them for a steps-only fixture (a `mission-steps/<id>/<step>/step.yaml` tree,
    which the existing helpers do not yet write).
    - **NFR-001's own case may be org-tier or project-tier (either satisfies the red-first pin),
      but spec.md's Acceptance Scenario 5 is a separate, mandatory, project-tier-specific
      requirement and needs its own named case regardless of which tier NFR-001's case uses**: a
      dedicated `test_project_tier_steps_only_projection_resolves` (or equivalently named) case
      that points `_StubPackContext.repo_root` at a synthetic project root carrying its own
      `.kittify/missions/mission_types/<id>.yaml` (no `action_sequence:` key) plus a sibling
      `mission-steps/<id>/<step>/step.yaml` tree — exercising `resolve_layered_mission_types`'s
      project layer (`pack_context.repo_root` / `.kittify/missions/mission_types/*.yaml`, per
      `mission_type_repository.py`'s own layer-precedence docstring), not its org layer
      (`pack_context.pack_roots`). This asserts the same non-empty, correctly-ordered
      `action_sequence` outcome as NFR-001's case, but is traceable specifically to spec.md's
      Acceptance Scenario 5 (line 62) rather than folded into whichever single tier NFR-001's own
      case happens to pick.
  - `tests/runtime/test_runtime_seam.py`: extend `TestGoldenParityUnaffectedByPackContextThreading`
    (line 184) for NFR-002 — its existing `test_builtin_type_unaffected_by_real_pack_context_with_org_root`
    already resolves built-in types under `pack_context=None` vs. a real `PackContext`; confirm
    (or add an explicit parity assertion if the existing parametrized test does not already cover
    the exact "same value under both" comparison for `action_sequence` specifically) that this
    stays true post-fix, since `resolve_layered_mission_types`'s built-in-equivalent-layer call is
    now also passed the real `pack_context` for the first time (previously effectively `None` for
    that layer's own projection).
- **Sequencing/depends-on**: none — this is the only concern.
- **Risks**:
  - The built-in-equivalent layer's `scan_mission_types_dir` call inside `resolve_layered_mission_types`
    now receives the *real* `pack_context` for the first time (previously it was always effectively
    unthreaded for that layer too, since `_inject_projected_fields` hardcoded `None` regardless of
    what `scan_mission_types_dir` was passed). This means a built-in type whose steps are
    genuinely overridden by an *active* org/project pack could see a different (correctly layered)
    `action_sequence` post-fix than pre-fix — this is the **intended** fix, not a regression, but
    it is the one place golden-parity testing must be precise: NFR-002/FR-007's parity claim is
    "byte-identical under an *unrelated* org pack" (spec.md Acceptance Scenario 3), not "byte-identical
    under any org pack whatsoever" (a pack that *does* override a built-in type's steps is expected,
    correctly, to change that type's resolution — that is what the projection seam is for). The
    plan flags this precisely so the WP-implementer does not misread FR-007/NFR-002 as a
    no-org-pack-can-ever-affect-built-in-types invariant.
  - `functools.cache` on `resolve_layered_mission_types` already keys on `(mission_types_dirs, pack_context)`
    (NFR-003) — no new caching risk, since no new cached call is introduced; only the *body* of an
    already-cached function changes what it forwards downward.

## Seam

The change lands entirely on **the doctrine layer's existing internal seam**,
`src/doctrine/missions/mission_type_repository.py`. No CLI command in this mission reaches past a
service boundary into kernel internals: `src/kernel/` is untouched, and the doctrine layer's own
existing service boundary (`MissionStepRepository`, already imported) is used exactly as designed
— this mission does not add a new import, only changes what value is passed to an
already-used method (`resolve_all_for_mission_type`). Tier order (`kernel <- doctrine <- charter`,
`tests/architectural/conftest.py:90`) is preserved: no new upward import from `doctrine` into
`charter` is introduced (C-008 is precisely the guard against that temptation — see below). No
unguarded core-loop → sync coupling is introduced: this seam is a pure, synchronous,
filesystem-read-then-Pydantic-validate function chain with no event emission, no sync-store
interaction, and no background/async coupling of any kind, before or after this fix.

## Generated artifacts

This change does **not** touch any generated doctrine schema, Contextive glossary file, or
agent-command copy. Verified concretely, not asserted:

- **Doctrine schemas** (`scripts/generate_schemas.py --check`, the `[ENFORCED] Verify generated
  doctrine schemas are up to date` lint step, `.github/workflows/ci-quality.yml:653`): these
  schemas are generated from the Pydantic models under `src/doctrine/` (`MissionType`,
  `MissionStep`, etc., in `models.py`). This mission does not touch `models.py` — `MissionType`'s
  fields, including `action_sequence: list[str] | None`, are unchanged; only the *data fed into*
  `MissionType.model_validate(payload)` changes (via `_inject_projected_fields`'s `payload`), not
  the model's own shape. No schema regeneration is needed or triggered.
- **Contextive glossary** (`scripts/generate_contextive_glossaries.py check`, gated on changes
  under `glossary/**`, `src/specify_cli/**`, `src/charter/**`, `.kittify/traceability/**` —
  `.github/workflows/ci-quality.yml:861`): `src/doctrine/**` is **not** in this path filter at
  all, and this mission touches no file under any of the four gated paths. The Contextive check
  will not even run against this mission's diff (the job's own path-filter step skips it), let
  alone find drift.
- **Agent-command copy** (`.claude/`, `.amazonq/`, etc., generated via `spec-kitty upgrade` from
  `packs/built-in/missions/mission-steps/`): this mission touches no mission-step template source,
  so nothing propagates to any agent-copy surface.

## Contracts

No contract moves. Verified against each contract surface named in the mission brief:

- **Doctrine schemas**: unaffected, per Generated artifacts above.
- **Mission step contracts** (`mission-steps/<type>/<step>/step.yaml` shape, `MissionStep` model):
  unchanged — this mission changes *what argument* is passed when *reading* those files
  (`pack_context`), not their schema or how they are parsed.
- **Action indices**: unaffected — `MissionType.action_sequence`'s own shape
  (`list[str] | None`, `validate_action_sequence`'s non-empty invariant) is untouched (C-006); only
  which step tree feeds the projection that populates it changes.
- **Orchestrator-api surface**: unaffected — this mission touches no `orchestrator-api`-facing
  code; `resolve_layered_mission_types` and its chain are internal doctrine-layer functions with
  no direct HTTP/API exposure.
- **Vendored `spec-kitty-events`**: unaffected — no event schema, envelope, or payload is touched;
  this fix has no event-emission behavior at all (see Seam above).
- **C-002/C-007 bound this explicitly**: C-002 forbids any `template_set`-style migration of
  `action_sequence` off the `MissionType` model (none is made); C-007 bounds the diff to the one
  named file and two named test files (checkable via SC-006's `git diff --name-only` mechanism at
  merge time). No contract file is in that bounded set, so none moves.

## Campsite-clean

Per Standing Order #2 (`DIRECTIVE_025`), this mission's opening campsite-clean is named as its own
**distinct, behaviour-preserving first commit** — but concretely, no domain-matched debt was found
inside the four functions this mission touches that can be folded in *without* violating C-007's
bounded blast radius:

- The two per-file YAML-parse/validate blocks in `MissionTypeRepository._load()` (lines 157-174)
  and `_load_layered_mission_type_file` (lines 340-354) are near-duplicated (the non-mapping check,
  the id/filename-stem mismatch `ValueError`, the `_inject_projected_fields` call shape). This
  *looks* like classic campsite-clean material (extract a shared helper) — but `_load()` is one of
  the functions spec.md's own FR-005/C-001 explicitly requires to stay **untouched** (its
  zero-argument call site must remain valid with no source change, and threading a
  project-dependent value into its `cls`-keyed cache would poison it — the exact hazard FR-005
  exists to prevent). Extracting a shared helper would necessarily touch `_load()`'s body, making
  it a fifth touched function under C-007's four-function bound. This mission therefore explicitly
  **does not** fold this duplication — it is real, domain-adjacent debt, but out of this mission's
  bounded scope, not absent.
  - **Disposition**: not folded. If it is worth doing, it belongs to a future mission whose own
    scope is "consolidate `MissionTypeRepository._load()` and `_load_layered_mission_type_file`'s
    duplicated per-file validation" — that mission would need its own justification for touching
    `_load()`'s cache-safety-sensitive body, which this mission's C-007/C-001 bound explicitly
    forecloses.
  - No such tracked follow-up issue exists yet; this plan does not open one preemptively (out of
    this plan-authoring pass's own scope) but flags it here for `sk-review`'s SPEC-KITTY-LEDGER
    sweep to consider.
- No other debt (complexity-ceiling risk, repeated literals ≥3, dead code, empty exception
  handlers) was found inside the four touched functions themselves during this plan's reading —
  each is already well under the Sonar complexity ceiling (15; none exceeds roughly 5-6 logical
  branches), and their docstrings, while long, are prose/documentation, not code debt.

**Conclusion**: the opening campsite-clean commit for this mission is a **minimal-scope / no-op
commit** — named as its own commit per DIRECTIVE_025's standing order, but carrying no functional
changes, because no in-bounds domain-matched debt exists near this seam. (If tasks-phase slicing
determines a literal empty commit is not useful, the alternative — recorded here so the
WP-implementer is not left guessing — is to fold the "no debt found" finding into the first real
commit's message rather than force an empty commit; this is a call for the tasks/implement phase,
not re-litigated further here.)

## Blast radius on downstream workspaces

This is an internal doctrine-layer signature change with new parameters that default to `None`
(preserving today's exact behavior for every caller that does not pass one). Concretely:

- **If this mission ships correctly**: every existing caller (including the one signature-affected
  external caller, `charter/pack_manager.py:865`, which keeps passing no `pack_context` per FR-008)
  continues to behave identically to today. Only callers that *already* pass a real `pack_context`
  through `resolve_layered_mission_types` gain the fix — previously broken org/project mission
  types with steps-only projection start resolving correctly. **Corrected caller count** (re-verified
  against this checkout via `grep -rn "resolve_layered_mission_types(" src/`, including through the
  `charter.missions` re-export alias, rather than trusted from
  `mission_type_repository.py:22-31`'s module comment, which is scoped to a prior mission's WP04
  historical framing and predates the later WP07 additions below — an earlier draft of this plan
  trusted that comment uncritically, which is exactly the failure mode this mission's own "verify
  rather than trust" standard exists to catch): there are **three** production `src/` callers, not
  one —
  1. `_resolve_action_slot` (`charter/mission_type_profiles.py:976`), underlying `charter activate
     mission-type` and `agent mission create --mission-type`;
  2. `resolve_layered_roster` (`specify_cli/cli/commands/charter/mission_type.py:87`), backing
     `charter_mission_type_list` — the `spec-kitty charter mission-type list` CLI command — and
     reused (via import) by `show_mission_type`
     (`specify_cli/cli/commands/mission_type.py:1454`) to back `mission-type show`;
  3. `_resolve_layered_roster` (`specify_cli/cli/commands/_mission_type_audit.py:170`), wired into
     `doctor.py`'s mission-type audit CLI surface (`run_mission_type_audit`,
     `doctor.py:581`) for its `resolved`/`activated-unresolvable` classification.

  All three already thread a real `PackContext` today, so all three are affected identically by
  this fix — this does not change C-007's file-set bound (none of these three callers need code
  changes), but it does mean `spec-kitty charter mission-type list --json`, `mission-type show`,
  and the audit CLI's `resolved`/`activated-unresolvable` classification all show changed,
  *intended* output for an affected org/project mission type post-fix (a positive change, not a
  regression). No existing, previously-*working* caller changes behavior (NFR-002/FR-007's
  golden-parity guarantee). **Test coverage for the two additional entry points**: neither needs
  its own dedicated golden-parity test — both `resolve_layered_roster` and
  `_resolve_layered_roster` call `resolve_layered_mission_types` directly and do no independent
  projection of their own, so NFR-002/SC-003's golden-parity test on `resolve_layered_mission_types`
  itself already covers every value these two callers observe; this is stated explicitly here so
  the reasoning is not left implied.
- **If this mission ships wrong** (e.g., a bug in the threading, or a violation of NFR-002's
  parity guarantee): the blast radius is still narrow — `resolve_layered_mission_types` has three
  production callers today (named above), not one, but all three reach the fix exclusively through
  that one function (none re-derives projection independently), so a threading bug would affect all
  three identically rather than three independent surfaces. A regression would surface as either
  (a) a built-in type's `action_sequence` silently changing (caught by NFR-002/FR-007's
  golden-parity test, which is specifically designed to catch exactly this, and which — per the
  same-function reasoning above — covers all three callers), or (b) an org/project
  type still failing incorrectly (caught by NFR-001's red-first reproduction test, or later
  user-visible as `MissionTypeEmptyActionSequenceError` persisting — the exact symptom this
  mission exists to close, so a shipped-wrong fix would be immediately visible against the issue's
  own repro transcript, not a silent regression).
- **Downstream workspaces** (`team-kitty-missions`, `muster-missions`, or any other repo that
  consumes `spec-kitty` as an installed CLI/library rather than this dev checkout): they are
  **unaffected until they upgrade** to a released `spec-kitty` version containing this fix — this
  is dev-checkout-internal doctrine-layer code, not something a downstream workspace vendors or
  imports directly. Once a downstream workspace does upgrade, the risk to it specifically is: (1)
  near-zero if it only uses built-in mission types (golden-parity guarantees no observable change);
  (2) the *intended, desired* behavior change if it activates an org/project mission type with
  steps-only projection (it goes from broken — `MissionTypeEmptyActionSequenceError` on every
  governed read — to working, which is a strict improvement, not a new hazard); (3) the only
  plausible *new* hazard is if a downstream workspace's org/project pack has a mission type whose
  step tree, once correctly layered (project > org > built-in-equivalent), now includes step
  overrides that were previously silently ignored (because the built-in-only projection ignored
  them) — such a workspace could see its `action_sequence` *change* post-upgrade, which is the
  IC-01 Risk noted above, and is correct-per-design (the override was always intended to apply; it
  was the bug that it did not). This is called out explicitly rather than hidden, per this plan's
  own honesty requirement, but it is not a "this mission breaks things" risk — it is "this mission
  makes previously-inert configuration data start taking effect," which is exactly what shipping
  the fix is for.

## The gate set

Enforced CI gates that apply to this mission's PR, and why (verified against
`.github/workflows/ci-quality.yml` and sibling reusable workflows directly, not assumed):

- **commitlint** (`ci-quality.yml` `lint` job, `id: commitlint`, `[ENFORCED] Run commit message
  linting`): applies to every commit on this PR, unconditionally. The mission's own commits
  (including this plan's `safe-commit`) must be conventional-commit-shaped.
- **Markdown lint** (`[ENFORCED] Run markdown style linting on changed files`,
  `.markdownlint-cli2.jsonc`): **does not apply** to `plan.md`, `spec.md`, or the tracer files —
  verified directly: `.markdownlint-cli2.jsonc`'s `ignores` array includes `kitty-specs/**`
  explicitly. This mission's markdown changes are entirely under `kitty-specs/mission-types-empty-action-sequence-01M0RMCA/`,
  so the gate is inert for this diff, not merely "probably fine." (Any markdown this mission does
  NOT currently plan to touch — none exists outside `kitty-specs/` — would need re-checking against
  this gate if scope changed; it has not.)
- **Generated doctrine schemas up-to-date** (`[ENFORCED] Verify generated doctrine schemas are up
  to date`, always-on in the `lint` job, no path filter): applies unconditionally to every PR, but
  is a no-op pass for this mission — see Generated artifacts above, no model change.
- **Contextive glossary sync** (`[ENFORCED] Check Contextive glossary files are up-to-date`,
  path-filtered to `glossary/**`, `src/specify_cli/**`, `src/charter/**`, `.kittify/traceability/**`):
  does not even execute against this diff — `src/doctrine/**` is outside its path filter, and this
  mission touches nothing else in the filtered set (see Generated artifacts above).
- **Banned-API lint (TID251)** (`[ENFORCED] banned-API lint gate (TID251)`, `ruff check src tests
  --select TID251`, always-on): applies unconditionally. Relevant here because C-008 is exactly
  the kind of rule TID251-style import-banning exists to catch structurally — but C-008's own bar
  (never import the concrete `charter.pack_context.PackContext` class into `src/doctrine/`, even
  under `TYPE_CHECKING`) is enforced by `tests/architectural/conftest.py:90`'s tier-order pin, not
  by a TID251 rule specifically; both gates are relevant and both must pass, for different specific
  mechanisms.
- **`patch()` target validation** (`[ENFORCED] Validate patch() target strings (closes #394)`,
  `scripts/check_patch_targets.py`, always-on): applies because this mission's tests use
  `unittest.mock.patch` (the existing `TestGoldenParityUnaffectedByPackContextThreading` pattern
  patches `"charter.pack_context.PackContext.from_config"` as a string target) — any new `patch()`
  calls this mission's tests add must use validated, real target strings, not typo'd/stale paths.
- **Bandit + pip-audit** (`[ENFORCED] Run bandit security scan`, `[ENFORCED] Run pip-audit CVE
  scan`, always-on): apply unconditionally; no new dependency, no new subprocess/eval/pickle-style
  pattern is introduced by this fix, so both are expected to pass trivially, but they are real
  gates on this PR regardless.
- **`uv.lock` vs `pyproject.toml`** (`uv-lock-check` job, `uv lock --check`): applies structurally
  to every PR, but is a no-op for this mission — **no dependency changes** (stated explicitly, not
  merely implied): no new import, no new package.
- **Test shards with coverage floors**:
  - **kernel (90%)** (`module-kernel.yml`, `--cov=src/kernel`): does **not** apply — this mission
    touches nothing under `src/kernel/`.
  - **The real, applicable coverage floor for this mission is `diff-coverage (critical-path,
    enforced)`** (`ci-quality.yml:3280-3383`, `diff-cover ... --fail-under=90 --include
    'src/kernel/*' 'src/doctrine/*' 'src/charter/*' ...`): `src/doctrine/*` is in the enforced
    critical-path list, and this mission's only `src/` change is under `src/doctrine/missions/`.
    This is a **90% floor on this mission's own *changed lines***, computed from the
    `coverage-fast-doctrine.xml` report `fast-tests-doctrine` (`module-doctrine-fast.yml`,
    `--cov=doctrine --cov=charter`) emits, aggregated at the `diff-coverage` job. **Correction to
    the mission brief's framing**: the brief names this "the mission-loader coverage floor" — that
    literal CI job (`mission-loader-coverage`, `ci-quality.yml:1437`) is scoped to
    `--cov=src/specify_cli/mission_loader` and `tests/unit/mission_loader/` +
    `tests/integration/test_mission_run_command.py`, which is a **different subsystem** this
    mission does not touch at all. The gate that actually binds this mission's new/changed
    branches is `diff-coverage`'s critical-path inclusion of `src/doctrine/*`, not the
    literally-named `mission-loader-coverage` job. Both are real CI jobs; only one applies here.
    **Held how**: NFR-001's new red-first test and NFR-002's golden-parity extension are *direct
    unit tests* of the four touched functions/call sites (not incidental exercise through a larger
    integration test) — every new branch this mission adds (the `pack_context is not None` forward
    at each of the three call sites, the keyword-default-`None` path preserving `_load()`'s
    behavior) gets a dedicated assertion, per IC-01's Affected Surfaces above.
- **`clean-install-verification`** (`ci-quality.yml:3970`, required check): applies unconditionally
  as a required check on every PR (per the job's own listing at `ci-quality.yml:4301`/`4412`) —
  structurally proves `spec-kitty next` runs from a clean install. Not expected to interact with
  this mission's change specifically (no packaging/entry-point change), but it is a required gate
  regardless and must be green.
- **`make lint` / `make typecheck` / `make test` are NOT the real CI gates.** Stated plainly, per
  this mission's own instruction: `ruff`/`mypy` run in CI as `[INFO]`-labeled advisory steps
  (`ci-quality.yml:871`, `:902` — "Run ruff report (advisory)", "Run mypy report (advisory)"), not
  enforced gates; `make test`, if it exists as a local target, is a narrow local-iteration surface,
  not the CI-authoritative suite (which runs `pytest` directly across the module-scoped reusable
  workflows named above). These are useful for **fast local iteration only** — they do not
  substitute for verifying against the actual named CI gates above.
- **SonarCloud does NOT run on pull requests.** Verified directly at `ci-quality.yml:3502`: the
  `sonarcloud` job's own `if:` condition is `github.event_name == 'schedule' ||
  github.event_name == 'workflow_dispatch'` — no `pull_request` branch at all. This PR will not
  receive a Sonar verdict; do not promise or wait for one.

**"We'll run the tests" is not a gate statement.** The gate statements above are the concrete,
named CI jobs and what specifically each one checks against this mission's diff — not a promise to
run something and see.

## Test baseline

Per SC-005's own triage mechanism (spec.md), this mission's baseline-red capture is: **before any
implementation commit touches `mission_type_repository.py`**, the WP-implementer runs the exact
scoped invocation —

```
pytest tests/doctrine/missions/test_mission_type_repository.py tests/runtime/test_runtime_seam.py
```

— against the **unmodified base commit** (this checkout's current HEAD, `d470d524845e25ab1ec3e2609635b8f10817b7e9`,
the spec-phase-complete baseline this plan itself was authored against), and records the full
result (pass/fail counts, and the specific test ids of any red, if present) in `tracer-approach.md`
or `tracer-design-decisions.md`. This captures whether either of these two test files carries any
of the ~23 known-red-test / 2-error baseline already on `main` (issue #3284) *before* this
mission's own changes land, so that:

- A test id red on **both** the base-commit run and the post-fix run is **pre-existing** — logged
  against a tracked issue (per SC-005: "not #3284's own breakdown, which does not enumerate either
  of these two test files" — a fresh issue reference if genuinely new, or #3284 itself if it turns
  out to already cover it) and left red, never "fixed" as part of this mission's scope, never
  silently waved through as "the suite is red" either.
- A test id green on the base-commit run and red on the post-fix run is **mission-introduced** and
  must be fixed before this mission's PR is marked ready for review.

This mirrors SC-005 exactly (same invocation, same two files, same base-commit-diff triage
mechanism) — no separate/invented baseline mechanism is used. This baseline run is a **distinct,
recorded step**, not an implicit assumption: at the time of this plan's authoring, no baseline
result had yet been captured (this plan does not itself run implementation-phase pytest — that is
the WP-implementer's first concrete action, tracked here so it is not skipped or assumed clean).

## Red-first/ATDD and SC-004's concrete stash/rerun/stash-pop moment

Per spec.md's own SC-004 (owning actor and moment already named there, restated concretely and
tied to this plan's IC-01 so it is traceable to a specific phase, not left as prose):

1. The WP-implementer authoring IC-01 first writes NFR-001's test (the steps-only-projection
   reproduction, in `tests/doctrine/missions/test_mission_type_repository.py`) **before** touching
   `mission_type_repository.py`'s production code — this is the WP's ATDD red-first commit (charter
   `ATDD-First Discipline`, C-011: "The ATDD test is committed as a separate commit... BEFORE any
   implementation commits").
2. Before marking IC-01's WP done, the implementer:
   - `git stash` the production-code changes to `mission_type_repository.py` (the fix itself),
     leaving the new NFR-001 test in place.
   - Rerun the new test; confirm it **fails**, reproducing today's `None`/`[]` result.
   - `git stash pop`.
   - Rerun the new test; confirm it now **passes**.
   - Record **both runs** — the exact command and the observed result (pass/fail, and ideally the
     specific `action_sequence` value observed in each run) — in `tracer-approach.md` or
     `tracer-design-decisions.md`, so the pre-merge (`sk-review`) squad can verify the claim was
     witnessed, not re-derive it independently.
3. **A test that still passes with the fix reverted is a severity-4 finding, not coverage.** This
   is stated plainly per charter Standing Order #4 (`DIRECTIVE_041`/`DIRECTIVE_034`, test
   remediation & red-first discipline) — it is a binding standing order, not a stylistic
   preference. If the stash/rerun step in (2) shows the new test still passing pre-fix, the test
   does not actually pin the defect and must be corrected (a stronger fixture, a stricter
   assertion, or both) before the WP can be marked done — this is not optional polish.

This is the *only* red-first test explicitly required by spec.md (NFR-001). NFR-002 (golden
parity) is explicitly **not** a red-first pin — spec.md and the existing
`TestGoldenParityUnaffectedByPackContextThreading` class's own docstring (`test_runtime_seam.py:194-201`)
state built-in types already resolve correctly pre-fix, so that class's existing tests already
exercise this path incidentally; NFR-002's extension is a regression backstop, not a red-first
reproduction, and should not be forced into an artificial red-first shape it does not fit.

## PR shape

**Default PR shape for this repository is one PR per mission** — this repository's own machinery
(`accept` → `merge`) assumes one mission branch, and this is explicitly **not** `tk`'s
one-PR-per-WP rule (a different repository's convention). Given this mission's blast radius (one
`src/` file, four function signatures, three internal call-site edits, two test files, one
unchanged external caller verified unaffected), **one PR is reviewable in a single sitting**: the
entire production diff is a handful of small, mechanically-related edits inside one file's four
already-well-documented functions, and the test additions are scoped to exactly two files (C-007's
own bound). There is no basis here for splitting into multiple PRs or for treating this as a
multi-WP mission requiring separate review passes per WP — IC-01 above is deliberately the single
concern this mission decomposes into, and `/spec-kitty.tasks` should reflect that as (most likely)
a single WP, or at most a small number of WPs that still land in one PR. This is stated explicitly
because it determines what a later `sk-review` pass gates over: one aggregate diff review, not a
per-WP review sequence.

## Tracer files

`tracer-tooling-friction.md`, `tracer-approach.md`, and `tracer-design-decisions.md` were already
seeded during the spec phase (confirmed present, non-empty, at the start of this plan-authoring
pass). This plan-authoring pass appends to all three (see their updated content, committed
alongside this plan) rather than recreating them:

- **`tracer-tooling-friction.md`**: `.venv/bin/spec-kitty plan --mission mission-types-empty-action-sequence-01M0RMCA --json`
  hung indefinitely (killed after ~2 combined minutes across two attempts, one foregrounded to a
  120s tool timeout and one backgrounded and manually killed) emitting repeated
  `Warning: event journal capture failed: project sync store is locked` /
  `Warning: Explicit-context event capture failed: machine layout cutover did not publish within
  the bounded wait` — a genuine non-terminating hang, not a slow-but-completing command. `plan.md`
  already existed at the expected path from an earlier scaffold pass (stale content, using an
  older "Constitution Check"/"Parallel Work Analysis" template shape rather than the current
  canonical `packs/built-in/missions/software-dev/templates/plan-template.md` — itself worth
  flagging as drift), so the scaffold command's *locate* purpose was already satisfied; this plan
  was authored by directly editing that already-located file per this mission's own task
  instructions, rather than re-attempting the hanging command a third time or hand-editing any
  mission *state* (meta.json, status events) to work around it.
- **`tracer-approach.md`** / **`tracer-design-decisions.md`**: this plan's own verification pass
  (re-checking every line number spec.md cites against the live file, confirming the exact
  three-call-site fix location inside `resolve_layered_mission_types`'s body, confirming the CI
  gate set directly against `.github/workflows/ci-quality.yml` rather than trusting the mission
  brief's own framing — correcting the "mission-loader coverage floor" framing to the actual
  `diff-coverage` critical-path gate) is appended there.
