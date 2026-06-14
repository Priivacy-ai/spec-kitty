---
work_package_id: WP06
title: Templated git-repo fixture and structural hygiene
dependencies:
- WP04
requirement_refs:
- FR-010
tracker_refs: []
planning_base_branch: feat/test-suite-acceleration
merge_target_branch: feat/test-suite-acceleration
branch_strategy: Planning artifacts for this mission were generated on feat/test-suite-acceleration. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/test-suite-acceleration unless the human explicitly redirects the landing branch.
subtasks:
- T023
- T024
- T025
- T026
- T027
phase: Phase 4 - Structural
agent: claude
shell_pid: '2425'
history:
- at: '2026-06-14T17:10:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: implementer-ivan
authoritative_surface: tests/_support/git_template/
create_intent:
- tests/_support/git_template/__init__.py
execution_mode: code_change
model: ''
owned_files:
- tests/_support/git_template/**
- tests/sync/test_orphan_sweep.py
- tests/sync/test_daemon_self_retirement.py
- tests/sync/test_edge_cases.py
- tests/sync/test_offline_replay.py
- tests/architectural/test_no_prompt_filtering_added.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP06 – Templated git-repo fixture and structural hygiene

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the profile before parsing the rest of this prompt.

- **Profile**: `implementer-ivan`
- **Role**: `implementer`
- **Agent/tool**: `claude`

---

## Markdown Formatting

Wrap HTML/XML tags in backticks. Use language identifiers in code blocks.

## Objectives & Success Criteria

Replace repeated real `git init` with a templated baseline repo for the common case, and finish the lower-leverage structural cleanups — each behind its own safeguard.

**Done when**: template-backed tests pass; bespoke repo tests are unchanged; the high-volume concurrency variant survives in a nightly path; the collect-only consolidation preserves node→selector attribution.

## Context & Constraints

- Evidence: `architecture/test-suite-acceleration-plan.md` (A3/PP-03, R10 part 2/PP-06c, B2/PP-04a, R9). `contracts/behavioral-contracts.md` (C-VOLUME).
- **Depends on WP04** (templated fixture must be parallel-safe under isolated home).
- Constraints: C-004 (retain high-volume nightly variant), C-006 (no prod signature change).
- The fixture lives in a NEW `tests/_support/git_template/` package — do NOT touch `tests/_support/coverage_safety/` (WP02).

## Branch Strategy

- **Planning base branch**: feat/test-suite-acceleration
- **Merge target branch**: feat/test-suite-acceleration

## Subtasks & Detailed Guidance

### Subtask T023 – Templated bare-repo fixture

- **Purpose**: 233 files run real `git init`. Build one template, clone per test.
- **Steps**:
  1. Create `tests/_support/git_template/__init__.py` exposing a session-built **bare** repo template and a `clone_template(dest) -> Path` helper (filesystem clone is far cheaper than `git init` + initial commit).
  2. Expose a `templated_repo` fixture (function-scoped clone). Preserve any `cache_clear()` semantics the repo-root resolver relies on.
- **Files**: `tests/_support/git_template/`.
- **Notes**: Template is a plain bare repo — **no** worktrees, no detached/unborn special state.

### Subtask T024 – Adopt via execution-allowlist

- **Purpose**: Safely switch the common case to the template without breaking transitive callers.
- **Steps**:
  1. Adopt by **execution-allowlist**: run the target tests with the autouse `git init` removed and allowlist every `NotInsideRepositoryError` site — do NOT grep-by-symbol (it misses ~18 transitive callers).
  2. Keep bespoke `git init` for unborn/detached/`--bare`/worktree tests.
  3. Split this into its own commit, separate from T023 (template build), for reviewability.
- **Files**: conftests/tests adopting the fixture (record exact files in the Activity Log; prefer staying within owned_files — a small justified out-of-map edit is acceptable if recorded).

### Subtask T025 – Trim sync concurrency loops + nightly variant

- **Purpose**: Concurrency loops at `range(50)`/`range(20)` dominate fast-sync (~2.5s).
- **Steps**:
  1. In `tests/sync/test_orphan_sweep.py` (line ~322), `test_daemon_self_retirement.py` (~301), `test_edge_cases.py` (~223), and `test_offline_replay.py` (multiple), reduce default loops (50→20, 20→10), updating the loop range AND any `4*count`-style assertion in lockstep; keep ≥4 threads.
  2. **Retain** a high-volume (≥50) variant marked `@slow`/nightly — corruption-catch power is volume-sensitive (C-004).
- **Files**: the four sync test files above.

### Subtask T026 – xfail strictness hygiene

- **Purpose**: Two zero-value `xfail(strict=False)` guards.
- **Steps**:
  1. Case 1 (genuinely xfails today): flip to `strict=True`.
  2. Case 2: file a real tracked issue and reference it before any skip; do NOT convert to a bare skip with a `#TBD` placeholder.
- **Files**: locate the two xfail sites (record in Activity Log; small out-of-map edits acceptable with rationale).

### Subtask T027 – Consolidate the 8× subprocess `--collect-only` test

- **Purpose**: `tests/architectural/test_no_prompt_filtering_added.py` shells out to `pytest --collect-only` 8 times (~28s).
- **Steps**:
  1. Keep the invariant `legacy_nodes - new_nodes == {}` over IDENTICAL path universes.
  2. Prefer **parallelizing/​de-duplicating** the distinct collections over merging them; node→selector attribution must be unchanged.
- **Files**: `tests/architectural/test_no_prompt_filtering_added.py`.

## Test Strategy

- `.venv/bin/pytest tests/sync -n auto --dist loadfile -q` (with the daemon serial pass separate) green.
- Template-backed tests pass under `-n auto`; bespoke repo tests unchanged.
- The nightly high-volume concurrency variant runs and passes.

## Risks & Mitigations

- **Risk**: grep-by-symbol adoption misses transitive callers. **Mitigation**: execution-allowlist.
- **Risk**: silently weakening the concurrency stress guard. **Mitigation**: keep the ≥50 nightly variant.

## Review Guidance

- Confirm template = bare repo only; bespoke setups untouched.
- Confirm the high-volume variant still exists in CI somewhere.

## Activity Log

- 2026-06-14T17:10:00Z – system – Prompt created.
