---
work_package_id: WP01
title: Deterministic Scope-Budget Policy
dependencies: []
requirement_refs:
- C-004
- C-007
- FR-008
- FR-009
- FR-010
- NFR-007
planning_base_branch: fix/pre-review-gate-operator-flow
merge_target_branch: fix/pre-review-gate-operator-flow
branch_strategy: Planning artifacts for this mission were generated on fix/pre-review-gate-operator-flow. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/pre-review-gate-operator-flow unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
phase: Phase 1 - Policy foundation
history:
- at: '2026-08-23T15:30:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/review/gate_budget.py
create_intent:
- src/specify_cli/review/gate_budget.py
- tests/review/test_gate_budget.py
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/review/gate_budget.py
- tests/review/test_gate_budget.py
role: implementer
tags: []
task_type: implement
tracker_refs:
- '#2573'
---

# Work Package Prompt: WP01 – Deterministic Scope-Budget Policy

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `codex`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for `task_type: implement` and `authoritative_surface: src/specify_cli/review/gate_budget.py`.

---

## ⚠️ IMPORTANT: Review Feedback

Before implementing, inspect the current WP event log for `review_ref`. Address every review item and append progress chronologically to the Activity Log.

## Objective and success criteria

Create the single immutable budget authority described in `plan.md` and `contracts/scope-budget-policy.md`. It derives a stable preflight identity from normalized `ScopeResult.test_targets`, represents `bounded`/`oversized`/`unknown`, and initially classifies only target sets containing the exact atom `tests/architectural` as oversized.

Done when pure tests prove exact matching, normalized deterministic identity, unknown fallback, and that runtime observations cannot mutate policy.

## Context and constraints

- This is candidate-head policy only; baseline capture happens earlier and is out of this command's progress budget.
- Normalize separators, leading `./`, redundant trailing slashes, duplicates, and order. Preserve pytest node selectors.
- `tests/architectural/test_x.py` is not the exact oversized atom and remains unknown.
- Do not parse arbitrary `test_command()` argv, inspect CI logs, estimate duration, or add persistence/write APIs.
- A target superset containing the exact atom is oversized.
- Do not repurpose post-run `scope_source_identity()`; use a versioned budget-policy namespace.

## Subtasks

### T001 – Red-first policy contract

Add failing tests for singleton/superset exact-atom matches, descendant unknown fallback, Windows separator normalization, leading/trailing cleanup, deduplication/order independence, and pytest-node preservation.

### T002 – Immutable model

Implement frozen `BudgetClassification`, `ScopeBudgetRule`, `ScopeIdentity`, and `ScopeBudgetAssessment` values with one public assessment function. Keep rule storage module-private and source-controlled.

### T003 – Initial production rule and identity

Add exactly one production oversized rule for membership of normalized `tests/architectural`. Derive a stable identity from the normalized tuple plus a fixed policy namespace; prove repeatability and order independence.

### T004 – Compatibility and anti-learning proof

Test that unclassified targets, descendants, empty targets, and a broad suite encoded only in arbitrary command argv remain `unknown`. Prove the public surface exposes no mutation/promotion API and an assessment does not change subsequent classifications.

## Test strategy

Run `pytest tests/review/test_gate_budget.py -q`, then lint/type-check the two owned files. All clocks and metadata are deterministic; no network or subprocess is needed.

## Review guidance

Reject prefix matching, runtime timing stores, mutable registries, command parsing, or reuse of the post-run parse-comparability identity.

## Activity Log

- 2026-08-23T15:30:00Z – system – Prompt created.
