# Mission Specification: Mission-Type Roster Layering & Resolution Seam

**Mission Branch**: `kitty/mission-up-mission-type-seam-01KZY1JB`
**Created**: 2026-08-13
**Status**: Draft
**Input**: User description: "Give the mission-type roster a layered lookup so a non-built-in mission type from an org-tier doctrine pack resolves through mission create, charter activation, and action-sequence projection — end to end, not just 'loads without crashing.'"

## Provenance

This mission is **operator-directed**. There is no tracked GitHub issue behind it; the scope,
binding decisions, and constraints below were specified directly by the operator and are
recorded here rather than referenced from an issue.

## Clarifications

The following six decisions were made by the operator before this spec was written. They are
**binding decision records**, not options for a reviewer or implementer to re-litigate. Each was
independently re-verified against the live codebase (HEAD `ab0a0b9b5b5e6803775e45bebd66d1cc8d3b68dc`)
during spec authoring; any line-number drift found during that re-verification is noted inline.

### CL-001 — Seam shape: a separate, new layered lookup (not a project-dependent `default()`, not moving `action_sequence` out of `doctrine`)

`MissionTypeRepository.default()` (`src/doctrine/missions/mission_type_repository.py:48-50`, a
`@classmethod` decorated with `@functools.cache` and keyed on `cls` only) **stays built-in-only
and memoised, unchanged.** A **new, separate** layered lookup is added, entered at
`resolve_mission_type_context` (`src/charter/mission_type_profiles.py:516-618`), which already
constructs a `PackContext` one call-frame down (via `existing_mission_types()` at
`mission_type_profiles.py:424`, which builds `PackContext.from_config(repo_root)` at
`mission_type_profiles.py:507`). The new lookup imports the existing structural `_PackContextLike`
`Protocol` (`src/doctrine/missions/mission_step_repository.py:41-61`) from its sibling module in
the same package (`doctrine.missions`) — this is not a new cross-layer import; `doctrine` still
never imports `charter`.

**Rejected alternatives, with reasons:**

- **Option (a) — make `default()` itself project-dependent** by threading a `PackContext` into
  the process-wide, `cls`-keyed cache. **REJECTED**: a project-dependent value behind a
  project-blind cache is a correctness bug — the first project resolved in a process would
  poison the cache for every later one in the same process.
- **Option (b) — move the `action_sequence` projection out of
  `src/doctrine/missions/mission_type_repository.py` into the charter layer.** **REJECTED,
  measured not guessed**: doing so removes the only producer of the `action_sequence` slot from
  the one directory tree (`src/doctrine/` + `packs/built-in/`) that
  `tests/architectural/test_no_inert_schema_slots.py`'s producer-scan walks, which reds the one
  live assertion in that architectural gate today —
  `test_live_tree_has_no_new_inert_slots`'s `assert new == []`
  (`tests/architectural/test_no_inert_schema_slots.py:62-75`). The gate's supporting module,
  `_inert_slots.py`, also defines a second layer of machinery —
  `code_only_drift`/`find_code_only_suppressions`/`code_producer_writes`
  (`tests/architectural/_inert_slots.py:371-414,767-786`) — that, if wired to a test, would
  independently catch a "stale" `code_only_suppressions` baseline row with no matching producer.
  That machinery is defined but is not currently called by any pytest test, so it is not a
  presently-enforced second backstop; only the one live assertion above actually reds today.

The new factory MUST be a **module-level** `@functools.cache` keyed on
`(mission_types_dirs, pack_context)`, with a `cache_clear()` static test seam mirroring
`MissionStepRepository.cache_clear` (`src/doctrine/missions/mission_step_repository.py:324-333`,
a `@staticmethod` that calls `.cache_clear()` on the underlying module-level
`functools.cache`-wrapped factory) — **never** a classmethod cache. It must never be called at
module scope in any `charter.*` module: an import-time-IO architectural gate constrains
`charter.mission_type_profiles` / `charter.pack_context` imports to at most one
`MissionTypeRepository.default()` call at import time, and the new factory must respect the same
constraint.

### CL-002 — An ADR is the first work package (WP01)

The actual ADR document is authored in the plan/tasks phase, not in this spec — but this spec
binds that a plan/tasks-phase ADR is **required as WP01**, and the ADR must:

1. State that this mission does **not** promote mission-type to `ArtifactKind` — that is a
   separate, larger, currently-unstarted upstream effort tracked by its own ADR
   (`docs/adr/3.x/2026-08-05-1-mission-type-availability-before-kind-promotion.md`, issue
   [#2468](https://github.com/Priivacy-ai/spec-kitty/issues/2468), blocked on the keystone
   pack-split [#2467](https://github.com/Priivacy-ai/spec-kitty/issues/2467)).
2. State this mission's relation to that ADR's **"No silent contract reversal"** decision driver
   — the ADR is explicit that `#2468` (`ArtifactKind` promotion) "reverses a deliberate, tested
   'no silent fallback' contract (R-009/CL-1, [no-silent-fallback FR], pinned by
   `tests/doctrine/test_org_pack_augmentation.py`) and must carry its own decision record; it
   must not be smuggled into an availability slice." This mission's roster-layering work is the
   availability/resolution slice, explicitly **not** the contract-reversing type-promotion slice
   — the ADR authored under WP01 must say so in those terms, so a future reader cannot conflate
   the two.
3. State the org-pack layout choice explicitly (CL-005, below) as its own short decision
   record, since the referenced ADR names the **flat-vs-nested** mission-type layout as a live
   open sub-decision it deliberately left undecided ("Explicitly out of scope (deferred, not
   decided here) ... The nested-vs-flat mission-type path decision ... It belongs to the #2468
   promotion and should get its own short decision record when that slice is scoped. This ADR
   does **not** bind it.").

### CL-003 — Red-first loud-fail for the "layering without projection" silent-wrong

This is the mission's own **dominant risk** — the class of defect this whole spec exists to
prevent. Today, an org-pack mission-type YAML carrying only `schema_version` / `id` /
`display_name` (no `action_sequence`) loads CLEAN with `action_sequence = None`, which the
existing `_resolve_action_slot` (`src/charter/mission_type_profiles.py:762-807`; the
empty-sequence fallback is the `if not is_registered: return []` branch at line 789) silently
degrades to `[]`. A mission of that type would resolve "successfully" and plan **nothing** — no
error anywhere.

Roster-layering (CL-001) and action-sequence/template-set projection wiring MUST land
**atomically** (same PR), **plus** a new, explicitly named, loud failure for "mission type
`<id>` resolved from layer `<org>` has an empty action sequence." This is specified as a
**RED-FIRST regression test requirement**: the failing test pinning today's silent-degradation
behaviour must be written and committed *before* the fix that makes it loud.

### CL-004 — Delete dead code + fix a stale docstring, same PR

`resolve_mission_steps` (`src/charter/resolver.py:908`) has **zero production callers** anywhere
in `src/` (confirmed by repo-wide search — the only other hit is its own test in
`tests/charter/test_resolver.py`), is not exported in any `__all__`, and was kept alive only by
removing it from `__all__` to dodge a dead-symbol gate after its own PR reviewer flagged it as
dead code twice. It MUST be **deleted** along with its single test — it must not be wired up
into production use, which would repeat the original mistake.

Separately, the docstring of `_inject_projected_fields`
(`src/doctrine/missions/mission_type_repository.py:171`) claims, at line 177, that org/project
overrides apply "through the separate runtime consumer switch, WP06." **This claim is false**:
that WP06 (`kitty-specs/mission-step-authority-01KXNZMT/tasks/WP06-consumer-switch.md`, "Consumer
switch — every authority read → the cached seam") is about eliminating a duplicate authority
field by routing readers through a cached projection — a **caching-authority switch**, not an
org/project seam. Corroborating: `_resolve_action_slot` (`mission_type_profiles.py:762-807`)
calls `MissionTypeRepository.default()` (builtin-only). The sibling `_resolve_template_set_slot`
(`mission_type_profiles.py:841-884`) is likewise builtin-only today — its docstring at
`mission_type_profiles.py:859-860` states *template-set* resolution uses `pack_context=None`
"(builtin-only, matching the pre-cutover parity contract)." That sentence describes template_set
resolution, not action-sequence resolution — a sibling, similarly builtin-only projection — cited
here only to show the same builtin-only pattern holds across both slots. Nothing named "WP06" is
an org/project seam. This docstring MUST be corrected in the same PR — it currently misdirects
the next reader toward a seam that does not exist (which is exactly the seam this mission is
building).

### CL-004a — Delete the shadowed duplicate `list` command in the same file

`src/specify_cli/cli/commands/mission_type.py` registers two `@app.command("list")` handlers on
the same Typer app: `list_cmd` (lines 150-151, built on the legacy
`specify_cli.mission.discover_missions()` scanner over `.kittify/missions/`, backed by
`_print_available_missions` at line 122) and `list_mission_types` (lines 1429-1430, the
charter/doctrine-aware implementation FR-008 targets). Typer's registration order means the
second registration silently wins with no error or warning — `list_cmd`, `_print_available_missions`,
and the `discover_missions` import (lines 38-46) are confirmed unreachable dead code in the exact
file FR-006/FR-007/FR-008 modify. Per the canonical-source-unification standing order (chase
unification, not parity with a dead quirk) — the same standard CL-004 already applies to
`resolve_mission_steps` — this dead code MUST be deleted in the same PR as the FR-006/FR-007/FR-008
work: `list_cmd`, `_print_available_missions`, and the now-unused `discover_missions` import.

### CL-005 — Org-pack layout is flat: `<pack>/mission_types/*.yaml`

Deliberate choice, matching the existing sibling convention of `mission-steps/`
(`<pack>/mission-steps/<type>/<step>/step.yaml`) — **not** a nested
`<pack>/missions/mission_types/` layout. The project-layer roster location MUST **not** be
`.kittify/doctrine/mission_types/`: that directory shape, scanned recursively, would descend
into a per-type `governance-profile.yaml` subdirectory and mint a bogus available mission type
literally named `governance-profile`. The project-layer location is a flat
`.kittify/missions/mission_types/*.yaml`, scanned **non-recursively**, which has no such trap.

### CL-006 — Silent success is forbidden (standing charter order, restated for this mission)

Every new code path this mission adds must raise, report, or refuse when it cannot do its job —
never return `None` / empty / `"unknown"` and call it success. This governs CL-003's loud-fail
requirement directly, and also governs every CLI-surface fix in the Functional Requirements
below (none of them may retain a silent tolerate-and-lie fallback).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - An org-pack mission type resolves through the full pipeline (Priority: P1)

A project has activated an org-tier doctrine pack that defines a mission type (e.g. a
hypothetical `qa` type) not shipped built-in. An operator runs `mission create` with that
mission type, `charter activate mission-type qa`, and expects the resulting mission to receive
a real, non-empty action sequence and template set — the same resolution guarantees a built-in
type gets.

**Why this priority**: This is the mission's entire reason for existing — without it, org-pack
mission types "load without crashing" but silently produce missions that cannot plan anything.

**Independent Test**: Author a minimal org-pack mission-type YAML (id, display_name,
`action_sequence` with at least one step) under a project-layer or org-layer pack root, activate
it, run `mission create --mission-type qa`, and confirm the created mission's action sequence and
template set are non-empty and match the org-pack's declared steps — not `[]` and not silently
falling back to a built-in type's steps.

**Acceptance Scenarios**:

1. **Given** an org-tier pack declaring mission type `qa` with a populated `action_sequence`,
   **When** `charter activate mission-type qa` runs, **Then** the roster lookup resolves `qa`
   from the org layer and `charter mission-type list` reports `source_layer: "org"` for it (not
   `"unknown"`).
2. **Given** the same activated `qa` type, **When** a mission of type `qa` is created, **Then**
   the mission's projected action sequence matches the org-pack's declared steps exactly (not
   empty, not silently substituted with a built-in default).
3. **Given** the same activated `qa` type, **When** `mission-type show qa` is run, **Then** it
   succeeds and displays the org-pack's declared fields (not a hard `typer.Exit(1)` failure).

---

### User Story 2 - An org-pack mission type with a missing action sequence fails loudly (Priority: P1)

An org-pack author ships a mission-type YAML with only `schema_version` / `id` / `display_name`
— no `action_sequence` — either by mistake or because the field is still being drafted. Today
this loads clean and resolves to an empty action sequence with no error anywhere; a mission of
that type would be created and immediately have nothing to do.

**Why this priority**: This is the dominant risk this mission exists to close (CL-003). Silent
success here is explicitly the failure mode being eliminated.

**Independent Test**: Author an org-pack mission-type YAML with no `action_sequence`, activate
it, and attempt to resolve/create a mission of that type. Confirm a named, loud error is raised
— not a clean resolve to `[]`.

**Acceptance Scenarios**:

1. **Given** an org-pack mission type with no `action_sequence` field, **When** the mission-type
   context is resolved for it, **Then** the resolver raises a named error identifying the
   mission-type id and the layer it was resolved from (e.g. "mission type `qa` resolved from
   layer `org` has an empty action sequence") rather than returning an empty sequence silently.
2. **Given** the same misconfigured org-pack type, **When** `mission create` is attempted against
   it, **Then** mission creation refuses by propagating the same named exception type raised by
   FR-004 (e.g. `MissionTypeEmptyActionSequenceError`) — "same class of error" is asserted on the
   exception type, not on message substring-matching — not a silently-created mission with
   nothing to do.

---

### User Story 3 - Existing built-in mission-type resolution is unaffected (Priority: P2)

An operator who never touches org-tier or project-tier mission-type packs continues to use only
the four built-in mission types exactly as before.

**Why this priority**: The seam must be strictly additive. Regressing built-in resolution would
break every existing project.

**Independent Test**: Run the existing built-in mission-type test suite unmodified except for the
new red-first regression test (CL-003) and the deleted dead-code test (CL-004); confirm all
built-in-type behavior (`MissionTypeRepository.default()`, `mission-type show <builtin-type>`,
`charter mission-type list` for built-in types) is byte-identical to pre-mission behavior —
excluding any test already red on the mission's `planning_base_branch` for reasons unrelated to
this change, per the repo's baseline-red attribution policy (see `AGENTS.md` § Test-run
baseline-red gotcha).

**Acceptance Scenarios**:

1. **Given** no org or project mission-type packs are activated, **When** any of the four CLI
   consumer surfaces in FR-006–FR-009 are exercised for a built-in type, **Then** their output is
   unchanged from current behavior.
2. **Given** the process-wide `MissionTypeRepository.default()` cache, **When** the new layered
   lookup (CL-001) is exercised in the same process, **Then** `default()`'s cache key and
   returned built-in roster are provably unaffected (no shared mutable state, no cross-project
   pollution).

---

### Edge Cases

- What happens when an org-layer and a project-layer pack both declare the same mission-type
  `id`? (Layer-precedence order — the spec-required behavior is that project overrides org
  overrides built-in, via **full per-compound-key replacement**, matching the sibling
  `MissionStepRepository`'s own precedence docstring (`src/doctrine/missions/mission_step_repository.py:21-23`,
  "Layer precedence in full": "project > org (earliest pack_root wins) > built-in"). This is deliberately NOT the field-level
  merge that `docs/adr/3.x/2026-05-16-1-doctrine-layer-merge-semantics.md` mandates — that ADR's
  Decision and Code-changes sections scope field-merge behavior to
  `BaseDoctrineRepository._apply_org_overrides`/`_apply_project_overrides` and
  `AgentProfileRepository`; `MissionTypeRepository` does not inherit `BaseDoctrineRepository`
  and that ADR does not govern it. Concretely: a project-layer mission-type file that overrides
  an org-layer entry with the same `id` fully replaces that entry rather than overlaying it
  field-by-field — a project-layer override that omits `action_sequence` MUST trip FR-004's loud
  failure exactly as an org-layer file with no `action_sequence` would (CL-003), not silently
  inherit the org layer's value. The plan phase must confirm the resolver implements this
  full-replace semantic rather than importing field-merge by analogy to the unrelated ADR.)
- How does the system handle a project-layer `.kittify/missions/mission_types/` directory that
  does not exist at all (no project-layer packs activated)? It must resolve as "no project-layer
  contributions" — not an error, not a crash — while org/built-in layers still resolve normally.
- How does the system handle a malformed (unparsable) mission-type YAML in an org or project
  layer? It must fail loudly, naming the offending file, not silently skip it and resolve as if
  it did not exist (silent skip would itself be a silent-success violation per CL-006).
- What happens when the new module-level `@functools.cache` factory is called twice with the
  same `(mission_types_dirs, pack_context)` key across two different test processes/projects in
  the same pytest session? The `cache_clear()` test seam (mirroring
  `MissionStepRepository.cache_clear`) must be available and exercised so tests do not leak state
  across projects.
- What happens when `charter activate`'s step-removal warning path (FR-009) is evaluated for a
  mission type whose previous `action_sequence` cannot be resolved at all (e.g. was itself the
  CL-003 empty-sequence error case)? It must surface that resolution failure rather than silently
  treating "cannot resolve" as "no steps were removed."

## Requirements *(mandatory)*

### Functional Requirements

| ID | Title | User Story | Priority | Status |
|----|-------|------------|----------|--------|
| FR-001 | New module-level layered mission-type-context lookup | As a mission-type resolution seam, I want a new `functools.cache`-backed factory keyed on `(mission_types_dirs, pack_context)`, separate from `MissionTypeRepository.default()`, so that project-scoped mission-type resolution cannot poison the process-wide built-in cache. | High | Open |
| FR-002 | `resolve_mission_type_context` threads a real `PackContext` into projection | As an operator activating an org-pack mission type, I want `resolve_mission_type_context` to pass the `PackContext` it already constructs through to action-sequence and template-set projection, so that org/project mission types get real, non-empty projected fields instead of degrading to built-in-only defaults. | High | Open |
| FR-003 | `charter activate mission-type` scans org and project layers | As an operator, I want `charter activate mission-type <id>` to resolve `<id>` against built-in, org, and project layers (in that precedence order), so that activating a non-built-in mission type actually finds it instead of only ever seeing the built-in four. | High | Open |
| FR-004 | Loud failure for empty action sequence resolved from a non-built-in layer | As an operator, I want mission-type resolution to raise a named error ("mission type `<id>` resolved from layer `<layer>` has an empty action sequence") when an org/project-layer type has no `action_sequence`, so that a misconfigured mission type cannot silently resolve to a mission with nothing to do. The error MUST be raised as a specific, named exception class (e.g. `MissionTypeEmptyActionSequenceError`), following the existing `UnknownMissionTypeError` pattern already in `src/charter/mission_type_profiles.py` (class at line 193, raised for an analogous configuration-inconsistency case at lines 738 and 799) — not a bare built-in `ValueError`/`Exception`. Both the red-first regression test (CL-003/NFR-005) and the `mission create` refusal path (User Story 2 AC2) must assert on that exception type, not merely on message content. Must be red-first: the regression test pinning today's silent-`[]`-degradation is written and committed before the fix. | High | Open |
| FR-005 | Project-layer mission-type roster location is flat and non-recursive | As a doctrine-pack maintainer, I want the project-layer mission-type roster at a flat `.kittify/missions/mission_types/*.yaml`, scanned non-recursively, so that a per-type subdirectory (e.g. `governance-profile.yaml`) can never be misread as a mission-type id. | High | Open |
| FR-006 | `charter mission-type list` reports a true `source_layer` | As an operator, I want `charter mission-type list` to report the real resolution layer (`built-in` / `org` / `project`) and a real action sequence for an activated non-built-in mission type, so that the CLI stops emitting `source_layer: "unknown"` with an empty action sequence for a type that actually resolved successfully. | High | Open |
| FR-007 | `mission-type show <type>` succeeds for an activated non-built-in type | As an operator, I want `mission-type show <type>` to succeed and display the resolved fields for an activated org/project-layer mission type, so that the command stops hard-failing with `typer.Exit(1)` for a type that is genuinely available. | High | Open |
| FR-008 | `doctrine mission-type list` implements its documented layering | As an operator, I want `doctrine mission-type list` to actually enumerate built-in, org, and project mission types with a correct `source_layer` per row — matching what its own docstring already promises — instead of only ever calling the built-in-only collector. | High | Open |
| FR-009 | `charter activate`'s step-removal warnings evaluate real removed-steps for non-built-in types | As an operator re-activating a changed org/project mission type, I want `_emit_step_removal_warnings` to compare the type's actual previous and incoming `action_sequence` for non-built-in types (not silently degrade), so that I am warned about in-flight missions affected by removed steps regardless of which layer the type came from. | Medium | Open |
| FR-010 | Delete `resolve_mission_steps` dead code | As a codebase maintainer, I want `resolve_mission_steps` (`src/charter/resolver.py:908`) and its single test deleted (not wired up), so that a function with zero production callers, twice flagged dead by review, and excluded from `__all__` to dodge a dead-symbol gate, stops persisting as bait for future confusion. | Medium | Open |
| FR-011 | Correct the stale `_inject_projected_fields` docstring | As a codebase maintainer, I want the docstring of `_inject_projected_fields` (`src/doctrine/missions/mission_type_repository.py:171`) corrected so it no longer claims org/project overrides apply "through the separate runtime consumer switch, WP06" — a false claim, since that WP06 was a caching-authority switch, not an org/project seam — so the next reader is not misdirected toward a seam that does not exist. | Medium | Open |
| FR-012 | ADR authored as WP01 in the plan/tasks phase | As a reviewer, I want the plan/tasks phase to produce an ADR as the first work package, stating (a) this mission does not promote mission-type to `ArtifactKind`, (b) its relation to that separate ADR's "no silent contract reversal" driver, and (c) the flat org-pack layout decision (CL-005) as its own short decision record, so that the sequencing rationale in `docs/adr/3.x/2026-08-05-1-mission-type-availability-before-kind-promotion.md` is honored rather than silently reopened. | High | Open |
| FR-013 | Delete the shadowed `list_cmd`/`_print_available_missions`/`discover_missions` dead code | As a codebase maintainer, I want the shadowed `list_cmd` (`src/specify_cli/cli/commands/mission_type.py:150-151`), its `_print_available_missions` helper (line 122), and the now-unused `discover_missions` import (lines 38-46) deleted in the same PR as the FR-006/FR-007/FR-008 work, so that the second, silently-winning `@app.command("list")` registration (`list_mission_types`, lines 1429-1430) is the only `list` handler left in the file, per CL-004a. | Medium | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | Cache correctness under project-scoping | The new layered lookup's cache key MUST include both `mission_types_dirs` and `pack_context`; a project-A resolution followed by a project-B resolution in the same process MUST return distinct, correct results for each — verified by a same-process, two-project regression test. | Reliability | High | Open |
| NFR-002 | No silent success anywhere in the new seam | Every new code path added by this mission MUST raise, report, or refuse when it cannot do its job. No new path may return `None` / an empty collection / a placeholder string like `"unknown"` and treat that as a successful result. This applies to FR-001 through FR-009 without exception. | Reliability | High | Open |
| NFR-003 | Layer boundary preserved | `doctrine.missions` MUST NOT gain a new import of anything under `src/charter/`. The new lookup (FR-001) may only import the existing structural `_PackContextLike` `Protocol` from its sibling `doctrine.missions` module — no new cross-layer dependency direction. | Architecture | High | Open |
| NFR-004 | Import-time-IO gate respected | No module under `charter.*` may call the new factory (FR-001) or `MissionTypeRepository.default()` more than once combined at import time, consistent with the existing import-time-IO architectural gate on `charter.mission_type_profiles` / `charter.pack_context`. | Architecture | High | Open |
| NFR-005 | Red-first test ordering for the dominant-risk fix | The regression test pinning today's silent empty-action-sequence degradation (FR-004) MUST be committed RED against the pre-fix behavior before the commit that introduces the loud-failure fix, as two separate commits in that order. Reviewers verify RED on the pre-fix commit and GREEN on the final commit, per the charter's ATDD-first discipline (C-011) — but that two-endpoint check alone cannot distinguish two separate ordered commits from one combined test+fix commit, which would also pass it trivially. Verification MUST go further: reviewers identify the commit SHA that introduces the CL-003 regression test, check it out in isolation (without the fix commit), and confirm the test fails there, so the red-before-fix ordering claim is mechanically falsifiable rather than resting on implementer honesty. | Process | High | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | Estimated mission size is L | Approximately 150–190 production `src/` LOC and approximately 260 test LOC, plus the WP01 ADR (authored in the plan/tasks phase, not counted in the LOC estimate). | Planning | High | Open |
| C-002 | `ArtifactKind` promotion is out of scope | Promoting mission-type to a first-class `ArtifactKind` member is explicitly NOT part of this mission. It is a separate, larger, currently-unstarted upstream effort (issue #2468, blocked on keystone #2467) tracked by its own ADR. This mission's WP01 ADR must state the relationship (CL-002) without doing that work. | Technical | High | Open |
| C-003 | `ALLOWED_MISSION_TYPES` activation gate stays untouched | Widening the `ALLOWED_MISSION_TYPES` activation frozenset (`src/charter/activations.py`) or the bootstrap-action gate is out of scope — that frozenset is import-time-constrained and stays built-in-only for this mission; it is a separate future mission's territory. | Technical | High | Open |
| C-004 | Template-resolution and FSM discovery chains are out of scope | This mission does not touch the template-resolution chain or the FSM discovery chain. Those are a separate future mission's territory. | Technical | Medium | Open |
| C-005 | `expected-artifacts.yaml` reconciliation is out of scope | This mission does not reconcile `expected-artifacts.yaml` against the new layered mission types. | Technical | Medium | Open |
| C-006 | `action_grain.py`'s integrity duplicate-scan stays built-in-only | `src/charter/action_grain.py` deliberately stays built-in-only — it is a gate over shipped content, not a resolution path, and this mission does not widen it. | Technical | Medium | Open |
| C-007 | Provisioning and migration rosters stay built-in-only | `src/specify_cli/provisioning/default_charter.py` and the builtin-mission-type-activation migration must explicitly stay built-in-only. Widening them would silently activate org types behind the operator's back without consent — a NFR-002 violation by a different name. | Technical | High | Open |
| C-008 | `doctrine` package never imports `charter` | The new layered lookup (FR-001) must not introduce any import from `src/doctrine/` into `src/charter/`. See NFR-003. | Architecture | High | Open |

### Key Entities *(include if feature involves data)*

> **Template-debt note:** the heading above retains "feature" from the canonical
> spec-template.md (`packs/built-in/missions/software-dev/templates/spec-template.md:113`,
> mirrored in `.kittify/overrides/missions/software-dev/templates/spec-template.md:113`). That is
> inherited canonical-template wording, not text this mission's requirements introduce, and fixing
> it is out of this mission's scope — it belongs to a separate small canonical-template
> terminology-guard fix. No requirement in this spec uses "feature"; see the Terminology Note
> below.

- **Mission-type roster entry**: a single mission type's identity and resolved fields
  (`id`, `display_name`, `schema_version`, `action_sequence`, template set) as offered by one
  layer (built-in / org / project). Distinct from the *charter activation record*, which merely
  says a roster entry is turned on for a project.
- **`PackContext`**: the existing doctrine-layer construct (`doctrine.pack_paths`,
  `charter.pack_context`) carrying the resolved pack roots and repo root used to scope a
  layered lookup to one project. Already constructed inside `resolve_mission_type_context`'s
  call chain; this mission threads it further rather than inventing a new carrier type.
- **`_PackContextLike` Protocol**: the existing structural protocol
  (`src/doctrine/missions/mission_step_repository.py:41-61`) exposing `pack_roots`,
  `repo_root`, and `__hash__`, reused (not duplicated) by the new lookup's cache key.
- **Layered mission-type lookup (new)**: the module-level, `functools.cache`-backed factory this
  mission introduces at `src/doctrine/missions/mission_type_repository.py` (sibling to, not a
  replacement for, `MissionTypeRepository.default()`), keyed on `(mission_types_dirs,
  pack_context)`, with a `cache_clear()` test seam.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: An org-pack mission type with a populated `action_sequence`, activated in a test
  project, resolves through `mission create`, `charter mission-type list`, `mission-type show`,
  and `doctrine mission-type list` with correct, non-empty, non-`"unknown"` output at every one
  of those four CLI surfaces — verified by an end-to-end regression test exercising all four.
- **SC-002**: An org-pack mission type with an empty `action_sequence` fails loudly (named error
  identifying mission-type id and layer) at resolution time, with a red-first regression test
  proving the failure was silent before the fix and loud after.
- **SC-003**: 100% of existing built-in mission-type behavior across the four CLI surfaces named
  in FR-006–FR-009 is unchanged (measured by the existing test suite for those surfaces passing
  unmodified except for the new CL-003/CL-004 tests), excluding any test already red on the
  mission's `planning_base_branch` for reasons unrelated to this change, per the repo's
  baseline-red attribution policy (see `AGENTS.md` § Test-run baseline-red gotcha).
- **SC-004**: Zero new cross-layer imports from `src/doctrine/` into `src/charter/` (measured by
  the existing architectural boundary gate continuing to pass with no new allowlist entries).
- **SC-005**: `resolve_mission_steps` and its test are removed from the codebase, and
  `_inject_projected_fields`'s docstring no longer references "WP06" as an org/project seam —
  both verified by direct inspection/grep in CI.
- **SC-006**: `list_cmd`, `_print_available_missions`, and the `discover_missions` import are
  removed from `src/specify_cli/cli/commands/mission_type.py`, and `list_mission_types` remains
  the sole `@app.command("list")` handler in that file — verified by direct inspection/grep in
  CI (per FR-013 / CL-004a).

## Out of Scope

Deliberately **not** part of this mission, so an implementer does not wander:

- Widening the `ALLOWED_MISSION_TYPES` activation frozenset / bootstrap-action gate (a separate
  future mission's territory) — see C-003.
- Promoting mission-type to a first-class `ArtifactKind` (a separate, parked, unstarted upstream
  effort — see CL-002, C-002).
- The template-resolution chain and FSM discovery chain (a separate future mission's territory)
  — see C-004.
- `expected-artifacts.yaml` reconciliation — see C-005.
- `action_grain.py`'s built-in-only integrity duplicate-scan (it deliberately stays built-in-only
  — it is a gate over shipped content, not a resolution path) — see C-006.
- The provisioning and migration rosters (`src/specify_cli/provisioning/default_charter.py`, the
  builtin-mission-type-activation migration) — these must explicitly stay built-in-only; widening
  them would silently activate org types behind the operator's back without consent — see C-007.
- `src/charter/activations.py`'s `ALLOWED_MISSION_TYPES` (import-time-constrained; touching it
  risks tripping an import-time-IO architectural gate) — stays built-in-only for this mission —
  see C-003.

## Mission Sizing

**Size class: L.** Approximately 150–190 production `src/` LOC and approximately 260 test LOC,
plus the WP01 ADR (authored in the plan/tasks phase — not counted in the LOC estimate above). See
C-001.

## Terminology Note

This mission is about **mission-type** resolution — the workflow-template family a mission is
created from — not about **missions** (the work unit) themselves. Every requirement above is
scoped to mission-*type* roster/resolution behavior; where a requirement also mentions mission
*creation* (e.g. FR-002, User Story 1), that is the point where mission-type resolution feeds
into creating a mission, not a change to mission identity, mission lifecycle, or mission status
behavior. No `feature*` aliases are introduced by any requirement in this spec, per the
charter's Terminology Canon.
