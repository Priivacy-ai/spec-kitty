---
work_package_id: WP09
title: Kill charter.context survivors
dependencies:
- WP07
requirement_refs:
- FR-011
- FR-013
- FR-014
- FR-015
- NFR-002
- NFR-003
- NFR-004
- NFR-005
- NFR-006
- NFR-007
planning_base_branch: feature/711-mutant-slaying
merge_target_branch: feature/711-mutant-slaying
branch_strategy: Planning artifacts for this feature were generated on feature/711-mutant-slaying. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feature/711-mutant-slaying unless the human explicitly redirects the landing branch.
subtasks:
- T041
- T042
- T043
- T044
- T045
- T046
phase: Phase 3 - Charter core
history:
- at: '2026-04-20T13:10:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
authoritative_surface: tests/charter/
execution_mode: code_change
owned_files:
- tests/charter/test_context.py
tags: []
task_type: implement
---

# Work Package Prompt: WP09 – Kill charter.context survivors

## Objectives & Success Criteria

- Drive mutation score on `charter.context` to **≥ 60 %** (FR-011, NFR-002). Current baseline: 227 survivors. Fresh re-sample required.

## Context & Constraints

- **Source under test**: `src/charter/context.py` — charter context bootstrap (first-load vs compact-load), policy-summary extraction, action-doctrine routing, reference loading.
- **Test file**: `tests/charter/test_context.py` (already carries `pytestmark = [pytest.mark.fast, pytest.mark.non_sandbox]` for the AST-walking tests — do NOT remove the `non_sandbox` marker without justification).
- **Precondition**: Re-sample `uv run mutmut run "charter.context*"`.

## Branch Strategy

- **Strategy**: lane-per-WP (`spec-kitty implement WP09 --base WP07`)
- **Planning base branch**: `feature/711-mutant-slaying`
- **Merge target branch**: `feature/711-mutant-slaying`

## Subtasks & Detailed Guidance

### Subtask T041 – Kill policy-summary-extraction survivors

- Policy summary is a human-readable rollup of doctrine policies. Mutations in summary construction are often string-literal substitutions.
- Assert the exact substring of each policy section in the summary (do not rely on length or substring-match for "a policy was emitted").

### Subtask T042 – Kill action-doctrine-routing survivors

- Context routes doctrine by action name (`specify`, `plan`, `tasks`, `implement`, `review`, `accept`, `merge`).
- **Non-Identity Inputs**: use all seven action names in tests. A mutation that conflates two actions' doctrine payloads is killed only by a test that distinguishes them.
- **Parallel?**: `[P]` with T043–T045.

### Subtask T043 – Kill reference-loading survivors

- References may be loaded lazily. Mutations around lazy-load caching.
- Test that loading the same reference twice returns the cached object (not re-read from disk).
- Test cache invalidation paths if present.
- **Parallel?**: `[P]` with T042, T044, T045.

### Subtask T044 – Kill first-load-vs-compact-load survivors

- `mode` field in the bootstrap JSON switches between `"bootstrap"` (first load) and `"compact"` (subsequent loads).
- **Bi-Directional Logic**: test transitions `first_load → True → False → False` across multiple invocations. Assert mode changes correctly.
- **Parallel?**: `[P]` with T042, T043, T045.

### Subtask T045 – Kill bootstrap-edge-case survivors

- Missing charter, empty references manifest, malformed manifest — each should degrade gracefully.
- Test: missing `.kittify/charter/charter.md` → context still loads with a clear fallback message.
- Test: malformed manifest → specific warning, no crash.
- **Parallel?**: `[P]` with T042, T043, T044.

### Subtask T046 – Rescope mutmut, verify ≥ 60 %, append findings residuals

- `rm mutants/src/charter/context.py.meta`
- `uv run mutmut run "charter.context*"` → ≥ 60 %.
- Append residuals. If still > 100 survivors, document follow-up in findings doc.

## Risks & Mitigations

- **Risk**: `charter.context` is large and the 15-min NFR-004 budget may be tight.
  - **Mitigation**: Scope mutmut to specific functions if necessary (`charter.context.x_<function>*`).
- **Risk**: Mode-transition tests leak state (context is often module-level cached).
  - **Mitigation**: Reset context state in a fixture teardown; or construct fresh context objects per test.

## Review Guidance

- Scoped mutmut score ≥ 60 %.
- `non_sandbox` marker on `test_context.py` preserved (it's load-bearing for the AST-walking tests that already exist in the file).
- All seven action names covered in T042.

## Activity Log

- 2026-04-20T13:10:00Z – system – Prompt created.
- 2026-04-20T18:28:54Z – unknown – Descoped: Phase 3 charter.* modules deferred to future mission
