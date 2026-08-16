---
work_package_id: WP04
title: Thread PackContext into action-sequence and template-set projection
dependencies:
- WP03
requirement_refs:
- C-004
- FR-002
- NFR-002
tracker_refs: []
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T008
- T009
- T010
phase: Phase 3 - PackContext threading (IC-02)
assignee: ''
agent: claude
history:
- at: '2026-08-13T00:00:00Z'
  actor: system
  action: Prompt generated during /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/charter/mission_type_profiles.py
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- src/charter/mission_type_profiles.py
- tests/charter/test_mission_type_profiles.py
- tests/runtime/test_runtime_seam.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP04 – Thread PackContext into action-sequence and template-set projection

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load `python-pedro` and behave according to its guidance
before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

---

## Objectives & Success Criteria

`resolve_mission_type_context` (`src/charter/mission_type_profiles.py`, live-verify — plan.md
cites `516-618`) already constructs a `PackContext` one call-frame down
(`existing_mission_types()` → `PackContext.from_config(repo_root)`, live-verify — plan.md cites
line `507`). Keep that object and thread it into both projection slots — WP03's new layered
factory now exists for this WP to call.

Two structurally different edits, both FR-002:

1. **`_resolve_template_set_slot`** (live-verify — plan.md cites `841-884`) genuinely hardcodes
   `pack_context=None` in its `MissionStepRepository.default().resolve_all_for_mission_type(...)`
   call (live-verify — plan.md cites line `878`) — replace that argument with the real
   `PackContext`.
2. **`_resolve_action_slot`** (live-verify — plan.md cites `762-807`) has **no** `pack_context`
   parameter at all today — its fix is a repository-call swap (from
   `MissionTypeRepository.default()`, live-verify — plan.md cites line `793`, to WP03's new
   layered factory), not argument-threading. Add a `pack_context` parameter to this function.

**Success criteria**:

- An org-pack type with a populated `action_sequence`, activated in a test project, projects
  real, non-empty action-sequence and template-set fields through `resolve_mission_type_context` —
  User Story 1 AC2.
- **The full-replace precedence edge case is implemented correctly, not imported by analogy from
  the wrong ADR** (see Context below) — a project-layer override that omits `action_sequence` must
  trip the same loud failure an org-layer omission would (full-replace, not silent field-level
  inherit). Note: the loud failure itself is WP06's job (FR-004/IC-05, which depends on this WP) —
  this WP's job is making sure the *projection* semantic is full-replace, so WP06's raise site has
  correct data to work with.
- `tests/runtime/test_runtime_seam.py`'s existing golden parity check for all 4 built-in types
  keeps passing byte-identically — User Story 3 AC1. This is the mission's regression backstop:
  if this WP's threading accidentally changes built-in-type behavior, this test catches it.

## Context & Constraints

- **Read plan.md's IC-02 section in full**, especially its Risks bullet: the full-replace-not-
  field-merge semantic (spec.md Edge Cases) "must be implemented as full-replace, not accidentally
  imported by analogy from that unrelated ADR" —
  `docs/adr/3.x/2026-05-16-1-doctrine-layer-merge-semantics.md` mandates field-level merge, but
  that ADR's Decision and Code-changes sections scope field-merge behavior to
  `BaseDoctrineRepository._apply_org_overrides`/`_apply_project_overrides` and
  `AgentProfileRepository` specifically. **`MissionTypeRepository` does not inherit
  `BaseDoctrineRepository`** (`src/doctrine/base.py`) — confirm this live
  (`grep -n "class MissionTypeRepository" src/doctrine/missions/mission_type_repository.py`) —
  and that ADR does not govern it. Concretely: a project-layer mission-type file that overrides an
  org-layer entry with the same `id` fully replaces that entry rather than overlaying it
  field-by-field. Get this right — a reviewer will specifically check for accidental field-merge
  behavior copied from the unrelated ADR's pattern.
- **This WP depends on WP03** — the new layered factory must exist before this WP can call it. Do
  not attempt to re-implement or duplicate WP03's factory; import and call it.
- **NFR-002 (no silent success)** applies here: every new code path this WP adds must raise,
  report, or refuse when it cannot do its job. Neither `_resolve_action_slot` nor
  `_resolve_template_set_slot` should introduce a new silent-empty-result path as a side effect of
  the pack_context threading — the existing `UnknownMissionTypeError` hard-fail for a genuinely
  unresolvable type must keep working exactly as before.
- **This WP is a strict prerequisite for WP06** (the loud-fail fix) — WP06 cannot fire its new
  exception until a non-built-in type can actually resolve (non-`None`) via this WP's threading.
  Per plan.md's own Summary: "only once this mission's own IC-01/IC-02 change lands does `mission`
  become resolvable (non-`None`) for a non-built-in type via the new layered lookup — and only
  then does `return list(mission.action_sequence or [])` become the live, silently-degrading path
  for a type whose YAML omits `action_sequence`." Do not be surprised if, at the end of this WP
  (before WP06 lands), the silent-`[]`-degradation is briefly *live* in the codebase — that is
  expected and is exactly the gap WP06 closes next.

## Branch Strategy

- **Strategy**: Planning artifacts for this mission were generated on
  `kitty/mission-up-mission-type-seam-01KZY1JB`. During `/spec-kitty.implement` this WP may branch
  from a dependency-specific base, but completed changes must merge back into
  `kitty/mission-up-mission-type-seam-01KZY1JB` unless the human explicitly redirects the landing
  branch.
- **Planning base branch**: `kitty/mission-up-mission-type-seam-01KZY1JB`
- **Merge target branch**: `main`

## Subtasks & Detailed Guidance

> **Red-first commit ordering (C-011, ATDD-First Discipline — binding)**: despite T008/T009/T010's
> numeric order, T010's tests are written and committed FIRST, proven RED against the pre-WP04
> code (the hardcoded `pack_context=None` still in place, `_resolve_action_slot` still calling
> `MissionTypeRepository.default()`), and only then do T008/T009's implementation edits land as the
> commit(s) that turn T010's tests GREEN. T010 keeps its `T010` subtask ID — WP06's prompt
> cross-references "WP04/T010" by that exact id — only the *commit/authoring order* changes, not
> the id numbering.

### Subtask T010 – Full-replace precedence test, golden-parity regression, org-pack real-projection test (write and commit FIRST — red-first)

- **Purpose**: prove User Story 1 AC2, the full-replace edge case, and User Story 3 AC1 (no
  regression to built-in behavior) — written and proven RED **before** T008/T009's implementation
  exists, per C-011.
- **Steps**:
  1. Add a test: an org-pack type with a populated `action_sequence`, activated in a test project,
     resolves through `resolve_mission_type_context` with the real, non-empty projected fields
     matching the org-pack's declared steps exactly (not empty, not silently substituted with a
     built-in default) — User Story 1 AC2. Write this against the current (pre-T008/T009) code and
     confirm it fails — the hardcoded `pack_context=None` and `MissionTypeRepository.default()`
     call mean the org-pack type cannot resolve real projected fields yet.
  2. Add a test: a project-layer file overriding an org-layer entry with the same `id`, where the
     project-layer file **omits** `action_sequence` — confirm the *projection* resolves to the
     project-layer's (empty) value, not a field-merged inherit of the org-layer's populated value.
     (This test proves the full-replace semantic; it does not yet assert the loud failure — that
     assertion is added in WP06 once the raise site exists. If you want this test to also assert
     the eventual loud failure, you may, but it will need to be updated/finalized once WP06 lands;
     document that dependency in your commit message if you do.) Confirm this test also fails
     against the pre-T008/T009 code before implementing.
  3. Extend `tests/runtime/test_runtime_seam.py`'s existing golden parity check to confirm all 4
     built-in types still resolve byte-identically after this WP's threading (User Story 3 AC1).
     This one may stay green against pre-WP04 code (built-in types already resolve correctly) — its
     purpose is regression coverage, not a red-first pin; note that distinction in your commit
     message.
  4. Commit steps 1-2's tests (RED, confirmed failing for the reasons above) as this WP's first
     commit, before any of T008/T009's implementation edits.
- **Files**: `tests/charter/test_mission_type_profiles.py`, `tests/runtime/test_runtime_seam.py`.
- **Parallel?**: Sequenced BEFORE T008/T009 — write and commit these tests first, confirmed RED
  against the pre-WP04 baseline, per C-011's red-first discipline.

### Subtask T008 – Thread `pack_context` into `_resolve_template_set_slot`

- **Purpose**: FR-002, the template-set half — implements the fix that turns T010 step 1's RED test
  GREEN.
- **Steps**: replace the hardcoded `pack_context=None` argument with the real `PackContext` object
  `resolve_mission_type_context` already constructs; confirm `MissionStepRepository`'s own
  `resolve_all_for_mission_type` signature already accepts a `pack_context` parameter (it does —
  this is the sibling module's already-live pattern) so no change is needed on that side. Confirm
  T010's org-pack real-projection test now passes.
- **Files**: `src/charter/mission_type_profiles.py`.
- **Parallel?**: Can proceed alongside T009 (different function in the same file, but land together
  for review coherence) — both are sequenced after T010's RED commit.

### Subtask T009 – Add `pack_context` parameter to `_resolve_action_slot`, swap to the new layered factory

- **Purpose**: FR-002, the action-sequence half — this is the branch WP06's loud-fail raise site
  will live inside. Implements the fix that turns T010 step 2's RED test GREEN.
- **Steps**: add a `pack_context` parameter to `_resolve_action_slot`; replace the
  `MissionTypeRepository.default()` call with WP03's new layered factory, passing through the
  `mission_types_dirs`/`pack_context` the caller supplies; confirm `resolve_mission_type_context`
  passes its own already-constructed `PackContext` through to this call. Confirm T010's
  full-replace-precedence test now passes.
- **Files**: `src/charter/mission_type_profiles.py`.
- **Parallel?**: Can proceed alongside T008 — both are sequenced after T010's RED commit.
- **Notes**: Do NOT add the new `MissionTypeEmptyActionSequenceError` raise site in this WP — that
  is WP06's job, sequenced as its own red-first/green-fix pair. This WP's job is only making the
  non-built-in type *resolvable* (non-`None`), which is a prerequisite, not the fix itself.

## Test Strategy

- **Per-AC / per-SC**: User Story 1 AC2 (org-pack type's projected fields match the org-pack's
  declared steps exactly), User Story 3 AC1 (built-in output unchanged for all 4 built-in types
  across the four CLI surfaces — this WP's golden-parity test is the mechanism, though the actual
  CLI-surface assertions land in WP07).
- **Test surface**: `tests/charter/test_mission_type_profiles.py` (extended — preserve the file's
  existing `MissionTypeProfile`/`resolve_mission_type_context` test classes, including its
  "T034"/WP05 docstring reference per plan.md's note — do not replace them),
  `tests/runtime/test_runtime_seam.py` (extended).
- **Commands**: `uv run pytest tests/charter/test_mission_type_profiles.py
  tests/runtime/test_runtime_seam.py -v`
- **Red-first / commit ordering (C-011)**: T010 steps 1-2 (the org-pack real-projection test and
  the full-replace-precedence test) are RED-first — write and commit them before T008/T009 exist,
  confirm they fail against the pre-WP04 baseline (hardcoded `pack_context=None` /
  `MissionTypeRepository.default()`), then commit T008's and T009's implementation edits as the
  commit(s) that turn those two tests GREEN. T010 step 3 (the golden-parity extension) is a
  regression backstop, not a red-first pin — it may already be green against built-in types before
  T008/T009 land. A reviewer verifies RED on WP04's `planning_base_branch` (`main`) and GREEN on
  the WP's final commit, mirroring WP03/WP05/WP06's red-first verification in this same mission.

## Risks & Mitigations

- **Risk**: accidentally importing field-merge behavior from
  `docs/adr/3.x/2026-05-16-1-doctrine-layer-merge-semantics.md`'s pattern by analogy.
  **Mitigation**: explicit confirmation that `MissionTypeRepository` does not inherit
  `BaseDoctrineRepository`; the full-replace test in T010 step 2 is the falsifiable proof.
- **Risk**: this WP's threading silently changes built-in-type output.
  **Mitigation**: the golden-parity extension in T010 step 3 is the regression backstop.
- **Risk**: scope creep into WP06's raise site. **Mitigation**: T009's explicit note — this WP
  makes non-built-in types *resolvable*, it does not add the loud-fail exception.

## Gate Set (this WP's Definition of Done)

- **`fast-tests-charter` + `integration-tests-charter`** (`--cov=charter --cov-fail-under=55`) —
  `mission_type_profiles.py` is directly in scope.
- **`diff-coverage` (critical-path, 90%, `[ENFORCED]`)** over `src/charter/*` — every new branch in
  both threaded functions needs a directly-testing unit test.
- **`arch-adversarial`** — must not regress any architectural gate.
- **`Typer 0.26 JSON error surface`, `patch() target validation`, `Bandit`, `pip-audit`,
  `commitlint`** — always-on in `lint`.
- `make lint` locally before handing off.

## Review Guidance

- Confirm the full-replace test (T010 step 2) genuinely exercises project-overrides-org with an
  omitted field, not merely two independent single-layer resolutions.
- Confirm the golden-parity extension actually re-runs all 4 built-in types, not a subset.
- Confirm no `BaseDoctrineRepository`-style field-merge helper was introduced or reused.
- Confirm `_resolve_action_slot`'s repository-call swap targets WP03's new factory, not a
  re-implementation.

## Activity Log

> **CRITICAL**: Activity log entries MUST be in chronological order (oldest first, newest last).

- 2026-08-13T00:00:00Z – system – Prompt created.
