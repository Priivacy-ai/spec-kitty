---
work_package_id: WP02
title: Campsite-Clean — Decompose _validate_requirement_mapping
dependencies:
- WP04
requirement_refs:
- NFR-004
planning_base_branch: pr/bare-prose-requirements-uncounted
merge_target_branch: pr/bare-prose-requirements-uncounted
branch_strategy: Planning artifacts for this mission were generated on pr/bare-prose-requirements-uncounted. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into pr/bare-prose-requirements-uncounted unless the human explicitly redirects the landing branch.
subtasks:
- T008
- T009
- T010
- T011
- T012
phase: Phase 1 - Foundation (parallel with WP03; after WP04)
history:
- at: '2026-08-14T02:50:21Z'
  actor: system
  action: Prompt authored during tasks-authoring pass (not run via /spec-kitty.tasks)
- at: '2026-08-14T00:00:00Z'
  actor: claude
  action: 'Fix 1 (issue #3396 fixer pass): dependency retargeted from WP01 to WP04 — WP01 (baseline capture) was folded into WP04. WP02 no longer runs parallel with WP04 (WP04 now runs first, alone); WP02 still runs parallel with WP03.'
agent_profile: ''
authoritative_surface: src/specify_cli/cli/commands/agent/mission_finalize.py
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/cli/commands/agent/mission_finalize.py
role: ''
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP02 – Campsite-Clean — Decompose `_validate_requirement_mapping`

## ⚡ Do This First: Load Agent Profile

Use `/ad-hoc-profile-load` for this WP's agent profile, or select via
`spec-kitty agent profile list` for an `implement`-typed WP on
`src/specify_cli/cli/commands/agent/`.

---

## Objectives & Success Criteria

Land charter Standing Order 2's "campsite cleaning" FIRST commit: split
`_validate_requirement_mapping` (`mission_finalize.py:621-677`, cyclomatic complexity
**16** per `radon cc`, ceiling **15**) into a classification helper and a
report-formatting helper — **behaviour-preserving, no observable-output change**. This
must land **before** WP06 adds its new `bare_prose_requirement_ids` branch to the same
function. **Correction (recorded post-implementation, pre-merge squad, 2026-08-14)**:
the repo's actually *enforced* complexity gate is ruff's `C901` check
(`pyproject.toml:305-306`, ceiling 15), not `radon` — measured with `ruff check
--select C901` against the pre-refactor function, it reports complexity **12**, under
the enforced ceiling. This function was never in violation by the enforced tool; the
split is justified as tidy-first hygiene ahead of WP06's functional addition, not as
remediation of an enforced-gate violation.

Success: `radon cc -s src/specify_cli/cli/commands/agent/mission_finalize.py -n A`
reports every extracted helper and the reduced orchestrator at <=15; every pre-existing
test touching `_validate_requirement_mapping` passes unmodified.

## Context & Constraints

- Read plan.md's "Campsite-Clean Scope" section in full (PLAN-GOV-001) — it names the
  exact split shape this WP must implement.
- Read `.kittify/charter/charter.md` Standing Order 2 (campsite cleaning) and the
  "Sonar Expectations" section of `CLAUDE.md` (complexity ceiling 15, `S3776`/`C901`).
- **No new user-observable behaviour is introduced here.** This is why charter C-011's
  literal "failing-first ATDD test" requirement does not apply to this WP in its usual
  shape — there is no new behaviour to pin RED. The regression guard instead is: every
  pre-existing test exercising this function must stay green, unmodified, before and
  after the split. This is a tasks-authoring judgment call (no ATDD applicability
  clause exists in plan.md for a behaviour-preserving refactor); record it as such if
  challenged in review.
- WP06 depends on this WP landing first — do not defer this split into WP06's own
  commit.

## Branch Strategy

- **Strategy**: Planning artifacts were generated on `pr/bare-prose-requirements-uncounted`;
  completed changes must merge back into `pr/bare-prose-requirements-uncounted`, which
  targets base `op/3394-requirement-citation-scope` @ `ab15225ea` (plan.md's "PR Shape").
- **Planning base branch**: `pr/bare-prose-requirements-uncounted`.
- **Merge target branch**: `pr/bare-prose-requirements-uncounted`.

## Subtasks & Detailed Guidance

### Subtask T008 [P] – Re-verify current complexity

- **Purpose**: Establish a stated before/after pair for the post-split measurement.
- **Steps**: `radon cc -s src/specify_cli/cli/commands/agent/mission_finalize.py -n A`;
  confirm `F 621:0 _validate_requirement_mapping - C (16)` before editing.

### Subtask T009 – Extract the classification helper

- **Purpose**: Isolate the per-WP missing/unknown/mapped bucketing loop.
- **Steps**: Create e.g.
  `_classify_wp_requirement_refs(wp_ids, wp_requirement_refs, all_spec_requirement_ids) -> tuple[list[str], dict[str, list[str]], set[str]]`
  containing exactly the loop currently inline (lines ~633-643): iterate
  `sorted(set(wp_ids))`, bucket into `missing_requirement_refs_wps`,
  `unknown_requirement_refs`, `mapped_requirement_ids`. Pure function, no I/O.
- **Files**: `src/specify_cli/cli/commands/agent/mission_finalize.py`.

### Subtask T010 – Extract the report-formatting helper

- **Purpose**: Isolate the JSON-vs-console output branch.
- **Steps**: Create e.g. `_emit_requirement_mapping_report(payload, *, json_output)`
  containing the `json.dumps` branch and the three `console.print` loops (lines
  ~653-677), verbatim in behaviour.
- **Files**: Same file.

### Subtask T011 – Reduce the orchestrator

- **Purpose**: `_validate_requirement_mapping` becomes thin: call T009's helper,
  compute `unmapped_functional_requirements`, early-return if clean, else call T010's
  helper and `raise typer.Exit(1)`.
- **Steps**: Same call signature, same exceptions for the same inputs — no behaviour
  change.

### Subtask T012 – Verify and regression-test

- **Purpose**: Prove the split is behaviour-preserving.
- **Steps**: Re-run `radon cc` on both new helpers and the reduced orchestrator,
  confirm each <=15. Locate and run existing tests
  (`git grep -l _validate_requirement_mapping tests/` — the only hit is
  `tests/specify_cli/cli/commands/agent/test_mission_finalize_phases.py` (4 call sites);
  `test_finalize_provenance_guard.py` is a DIFFERENT, unrelated file (#3311
  provenance-preservation guard) with zero references to `_validate_requirement_mapping`
  — do not run it as a stand-in for this check) unmodified; confirm all green.

## Test Strategy

- No new test file required by this WP itself (behaviour-preserving). Reuse and keep
  green the existing coverage on `_validate_requirement_mapping` located via
  `git grep -l _validate_requirement_mapping tests/`.
- Command: run the Targeted Test Surface's relevant subset —
  `tests/specify_cli/cli/commands/agent/test_mission_finalize_phases.py` at minimum,
  plus `mypy --strict` and `ruff check` on the touched file.

## Risks & Mitigations

- Extraction accidentally changes JSON payload keys or console print ordering →
  mitigated by T012's unmodified-test-green requirement; do not alter payload dict
  keys or print-loop order during the split.

## Review Guidance

- Confirm `radon cc` shows both helpers and the orchestrator at <=15.
- Confirm zero test assertions were touched, only the internal structure.
- Confirm this WP's commit lands strictly before any WP06 commit that adds the new
  `bare_prose_requirement_ids` branch to this function.

## Activity Log

- 2026-08-14T02:50:21Z – system – Prompt created.
