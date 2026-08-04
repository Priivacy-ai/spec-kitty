---
work_package_id: WP01
title: Extend the charter factory - accessor, builder unification, 6 mechanical kinds
dependencies: []
requirement_refs:
- C-001
- FR-001
- FR-005
- FR-008
- FR-010
planning_base_branch: feat/charter-sole-door-bypass-closure
merge_target_branch: feat/charter-sole-door-bypass-closure
branch_strategy: Planning artifacts for this mission were generated on feat/charter-sole-door-bypass-closure. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/charter-sole-door-bypass-closure unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
- T005
- T026
- T027
- T028
- T029
- T030
- T031
- T032
phase: Phase 1 - Foundation (owns src/charter/resolver.py exclusively)
history:
- at: '2026-08-03T14:10:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
- at: '2026-08-03T15:00:00Z'
  actor: system
  action: Post-tasks squad restructure - merged former WP07 in (paula-patterns finding); corrected accessor method names, dropped the wrong __getattr__-removal step, softened the resolver.py:402-413 precedent claim (debugger-debbie, reviewer-renata findings)
agent_profile: python-pedro
authoritative_surface: src/charter/resolver.py
create_intent:
- tests/charter/test_doctrine_service_builder_unification.py
- tests/charter/test_doctrine_service_lineage_accessor.py
- tests/charter/test_resolver_activation_gating.py
execution_mode: code_change
model: ''
owned_files:
- src/charter/resolver.py
- src/charter/doctrine_service_builder.py
- src/specify_cli/doctrine_service_factory.py
- src/specify_cli/charter_runtime/lint/checks/org_layer.py
- src/specify_cli/cli/commands/charter/generate.py
- tests/charter/test_doctrine_service_builder_unification.py
- tests/charter/test_doctrine_service_lineage_accessor.py
- tests/charter/test_resolver_activation_gating.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP01 – Extend the charter factory: accessor, builder unification, 6 mechanical kinds

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load `python-pedro` (implementer role, claude agent) before parsing
the rest of this prompt.

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this work
package's `task_type` and `authoritative_surface`.

---

## ⚠️ IMPORTANT: Review Feedback

Check the `review_ref` field in the event log (via `spec-kitty agent status`) before starting. Address all
feedback; log changes in the Activity Log.

---

## Objectives & Success Criteria

**This WP was expanded by a post-tasks adversarial squad** (originally split into WP01+WP07, restructured
because both edited `src/charter/resolver.py` and the split forced an awkward 3-lane serialization for no
real benefit — see `research.md`'s "Post-Tasks Squad Findings" section, appended after this restructure).
This WP is now the **sole owner** of `src/charter/resolver.py` for the whole mission, and covers three
things:

1. **A new public accessor** for lineage/mutation-capable `AgentProfileRepository` access — the filtered
   `agent_profiles` property cannot support `register_overlay()` or `get_provenance()`; WP02/WP04 need it.
2. **One unified builder function** — the two named builders plus the inline "build raw, conditionally
   wrap" pattern in `org_layer.py:244,275` and `generate.py:56` collapse onto one function.
3. **Activation-gating for 6 more kinds** (`directive`, `tactic`, `styleguide`, `toolguide`,
   `mission_step_contract`, `glossary_pack`) — confirmed mechanical, a copy of the existing `paradigms`
   property pattern.

**Success criteria**:
- The accessor's public method name and return shape are **pinned below, not left to implementer choice** —
  quote it verbatim in any WP that depends on this one.
- Exactly one function builds an activation-aware `DoctrineService`; `org_layer.py`/`generate.py` call it.
  `org_layer.py:252-253`'s `except ImportError: pass` no longer silently returns an unwrapped service.
- All 6 new kinds gated with the identical three-state semantics already proven for
  `paradigms`/`procedures`/`agent_profiles`; a bare-project equality regression test per kind.
- A single regression test proves the unified builder's output is identical across **all 9** gated
  properties (not staged in two passes across two WPs, per the prior structure's mistake).

## Context & Constraints

- Read `research.md`'s "D3", "R2", and "R5" sections and `contracts/charter-doctrine-service-contract.md`'s
  "Lineage/mutation accessor semantics" and "Gated properties" sections.
- Read `contracts/mission-type-and-builder-contracts.md`'s "Unified builder contract" section for the exact
  `active_languages`/`org_roots` resolution rule.
- **Pinned accessor contract** (post-tasks squad correction — the original prompt only offered "e.g." naming,
  which left three dependent WPs free to each invent something different):
  ```
  charter.resolver.DoctrineService.agent_profile_repository -> agent_profiles.repository.AgentProfileRepository
  ```
  A `@property` returning the raw, lineage-capable repository object directly. Dependent WPs call
  `factory.agent_profile_repository.register_overlay(...)` or `.get_provenance(...)` — verified against the
  actual call sites' real needs (not `get_ancestors`/`resolve_profile`, which the original prompt wrongly
  named): `projection.py:84` needs `register_overlay()` only; `registry.py:64` and `org_profiles.py:117`
  need `get_provenance()`. Confirm each call site's actual need against its own code before assuming this
  list is exhaustive — it is the verified set as of this squad pass, not a guess.
- **Softened precedent claim** (debugger-debbie finding): `resolver.py:402-413` is an `isinstance(dict)`
  compatibility fallback for raw services/mocks, not a real lineage-traversal precedent — with the charter
  wrapper, `agent_profiles` is a dict and `.get()` runs, so no lineage traversal actually happens there.
  Treat the accessor's mutation/lineage semantics (below) as a fresh design decision this WP makes, not as
  "matching existing precedent."
- Single canonical authority: do not invent a second factory or a second builder.

## Branch Strategy

- **Strategy**: lane-per-WP (normalized by `finalize-tasks`)
- **Planning base branch**: feat/charter-sole-door-bypass-closure
- **Merge target branch**: feat/charter-sole-door-bypass-closure

## Subtasks & Detailed Guidance

### Subtask T001 – Implement the pinned lineage/mutation accessor

- **Purpose**: Give `projection.py:84`, `registry.py:64`, and `org_profiles.py:117` one shared, public way
  to reach mutation/provenance operations without reaching into `._inner`.
- **Steps**:
  1. Add `agent_profile_repository` as a `@property` on `charter.resolver.DoctrineService` returning the
     raw `AgentProfileRepository` instance (the pinned contract above).
  2. Semantics: `register_overlay()` mutates the underlying repository's lineage graph; it does **not**
     create a way to read an unfiltered profile through the gated `agent_profiles` property afterward — that
     property's three-state filter still applies on every read, including reads that follow a mutation.
  3. `get_provenance()` is a read-only lookup on the raw repository — confirm its current signature/return
     type by reading `AgentProfileRepository.get_provenance` directly (do not assume a shape).
- **Files**: `src/charter/resolver.py`.
- **Parallel?**: No — T002-T003 depend on this landing first.

### Subtask T002 – Unify the two named builder functions

- **Purpose**: Close the C-001 violation: two "canonical" builders with silently different output.
- **Steps**:
  1. Read both `specify_cli.doctrine_service_factory.build_activation_aware_doctrine_service` and
     `charter.doctrine_service_builder._build_activation_aware_doctrine_service` in full.
  2. Pick the *fuller* behaviour on each axis: always compute
     `active_languages=infer_repo_languages(repo_root)`; always self-resolve `org_roots` via
     `resolve_org_roots`.
  3. Collapse to one function; make the other a thin re-export or delete-and-repoint callers.
- **Files**: `src/charter/doctrine_service_builder.py`, `src/specify_cli/doctrine_service_factory.py`.
- **Parallel?**: Yes, alongside T001 (different files).

### Subtask T003 – Retarget the inline construction sites; fix the fail-open bug

- **Purpose**: Close the 3 additional construction sites the post-plan squad found, and their fail-open bug.
- **Steps**:
  1. `org_layer.py:244-253` and `:275`: replace the inline construction + `try/except ImportError: pass`
     pattern with a call to T002's unified builder. The builder must **fail closed** — never silently return
     an unwrapped service when `pack_context is not None` was requested.
  2. `generate.py:56`: replace the inline construction + wrap with a call to the unified builder.
- **Files**: `src/specify_cli/charter_runtime/lint/checks/org_layer.py`,
  `src/specify_cli/cli/commands/charter/generate.py`.
- **Parallel?**: Yes, alongside T001.

### Subtask T004 – Regression test: unified builder identical output across all 9 gated properties

- **Purpose**: Prove T002's unification closed the divergence — non-fakeable equality, and (post-tasks
  squad correction) written ONCE against the full 9-property surface, not staged across two WPs.
- **Steps**:
  1. Construct the unified builder with the same `repo_root`, exercising each former call site's original
     argument shape (with/without explicit `org_roots`; with/without a language-diverse fixture).
  2. Assert identical output for all 9 gated properties that exist after this WP lands (`paradigms`,
     `procedures`, `agent_profiles`, `directives`, `tactics`, `styleguides`, `toolguides`,
     `mission_step_contracts`, `glossary_packs`) AND the builder's `active_languages`/`org_roots`
     resolution.
- **Files**: `tests/charter/test_doctrine_service_builder_unification.py` (new).
- **Parallel?**: No — depends on T002, T003, T026-T030.
- **Notes**: ATDD red-first — write failing against the pre-unification two builders, then implement T002.

### Subtask T005 – ATDD test: accessor semantics

- **Purpose**: Prove T001's semantics hold, not just that the accessor exists.
- **Steps**:
  1. Test 1: call `register_overlay()` with a non-activated profile via the accessor; assert the gated
     `agent_profiles` property still excludes it.
  2. Test 2: call `get_provenance()` via the accessor for a known profile; assert it returns the expected
     provenance data (read against the repository's actual current return shape).
- **Files**: `tests/charter/test_doctrine_service_lineage_accessor.py` (new).
- **Parallel?**: No — depends on T001.

### Subtasks T026-T030 – Add the 6 remaining mechanical properties

For `directives` (T026), `tactics` (T027), `styleguides` (T028), `toolguides` (T029),
`mission_step_contracts` and `glossary_packs` (both covered under T030's mechanical pass, since all 6 are
the identical copy-paste operation done together):

- **Purpose**: Mechanical copy of the existing `paradigms` property pattern (`src/charter/resolver.py:96`).
- **Steps**:
  1. Read the exact `paradigms` property implementation (getter logic, which `PackContext.activated_*`
     field it reads, how it applies the three-state filter to `self._inner.paradigms.list_all()`).
  2. Add a new `@property` with the same structure, swapping in the target kind's name and `PackContext`
     field (e.g. `directives`/`activated_directives`).
  3. **Do not** attempt to remove anything from the `__getattr__` fallback (post-tasks squad correction —
     the original prompt's step 3 was wrong): `resolver.py:136-140`'s `__getattr__` is a generic catch-all
     with no per-kind list; a new `@property` shadows it automatically. There is nothing to edit there.
- **Files**: `src/charter/resolver.py`.
- **Parallel?**: Yes — all 6 kinds are independent property additions in the same file; write them together
  in one pass.

### Subtask T032 – Bare-project equality regression test, all 6 new kinds

- **Purpose**: Non-fakeable proof — an existence check passes even if some entries silently leaked away;
  this must be equality.
- **Steps**: For a bare `PackContext` (no activated packs), assert `wrapped.<prop> == unwrapped_inner.<prop>`
  for each of the 6 new properties, per `contracts/charter-doctrine-service-contract.md`'s "Non-regression
  obligations" section.
- **Files**: `tests/charter/test_resolver_activation_gating.py` (new).
- **Parallel?**: No — depends on T026-T030.
- **Notes**: Write RED first as the ATDD contract for FR-005.

## Test Strategy

- `pytest tests/charter/ -v`.
- `mypy --strict src/charter/resolver.py src/charter/doctrine_service_builder.py
  src/specify_cli/doctrine_service_factory.py`.
- Do NOT run the full `pytest tests/` suite — targeted surfaces only.

## Risks & Mitigations

- **Guessing the accessor semantics instead of the pinned contract above.** If it seems ambiguous, that is a
  finding to report, not a decision to make silently.
- **Writing T004 in two passes again.** The whole point of this restructure was one 9-property proof —
  don't reintroduce the staged version.
- **Assuming `get_provenance()`'s signature instead of reading it.** The pinned method names are verified,
  but their exact signatures were not re-derived by this squad pass — read the actual repository code.

## Review Guidance

- Confirm the accessor is named exactly `agent_profile_repository` and returns the raw repository object.
- Confirm T004's test asserts equality across all 9 properties in one test file, not two.
- Confirm no attempt was made to edit `__getattr__`.
- Confirm zero remaining direct constructions of the raw `DoctrineService` at `org_layer.py`/`generate.py`.

## Activity Log

- 2026-08-03T14:10:00Z – system – Prompt created.
- 2026-08-03T15:00:00Z – system – Post-tasks squad restructure: merged former WP07 into this WP.
- 2026-08-03T17:25:31Z – unknown – shell_pid=0 – Cycle 2: fixed cycle-1 review findings. BLOCKER 1 (org_layer.py raw construction): added charter.resolver.DoctrineService.raw_repository(kind) accessor (Option A, generic per-kind form of agent_profile_repository) and retargeted org_layer.py's two provenance-scan sites (_build_scan_service) through charter.doctrine_service_builder._build_doctrine_service + charter.resolver.DoctrineService(inner, pack_context=None) instead of raw doctrine.service.DoctrineService construction; OrgOverridesBuiltinChecker now calls service.raw_repository(kind) instead of getattr(service, kind). BLOCKER 2 (duplicate builder bodies): build_activation_aware_doctrine_service now delegates to _build_activation_aware_doctrine_service(repo_root) -- exactly one function constructs the wrapper. MAJOR 3 (tautological T004 test): replaced the self-comparing charter_builder(x).prop == specify_cli_builder(x).prop assertion with comparison against an independently-derived raw_repository(prop).list_all() projection for both entry points. MINOR 4: replaced all object.__getattribute__(result, _inner) reach-arounds in tests/charter/test_doctrine_service_builder_unification.py with the public raw_repository() accessor. MINOR 6: confirmed baseline mypy --strict error count is 1 (resolver.py Returning Any from function declared to return dict[str, Any]), not 2 as previously reported. Validation: ruff clean on all 8 files; mypy --strict 1 pre-existing baseline error; tests/specify_cli/test_provenance_integration.py 9/9 passed; tests/charter/test_doctrine_service_builder_unification.py 12/12 passed; tests/architectural/test_org_activation_seam.py + test_layer_rules.py 29/29 passed; tests/specify_cli/cli/commands/charter/ 94/94 passed; tests/specify_cli/test_doctrine_service_factory.py + tests/specify_cli/charter_runtime/ 26 passed/3 skipped.
