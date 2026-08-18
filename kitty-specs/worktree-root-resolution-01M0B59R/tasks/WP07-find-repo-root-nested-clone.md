---
work_package_id: WP07
title: find_repo_root nested-clone boundary
dependencies:
- WP01
requirement_refs:
- FR-007
planning_base_branch: fix/worktree-root-resolution
merge_target_branch: fix/worktree-root-resolution
branch_strategy: Planning artifacts for this mission were generated on fix/worktree-root-resolution. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/worktree-root-resolution unless the human explicitly redirects the landing branch.
subtasks:
- T020
- T021
phase: Phase 1 - Fail-closed adopters
history:
- at: '2026-08-18T21:17:24Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: implementer-ivan
authoritative_surface: src/specify_cli/core/paths.py
create_intent:
- tests/specify_cli/core/test_find_repo_root_nested_clone.py
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/core/paths.py
- src/specify_cli/task_utils/support.py
- tests/specify_cli/core/test_find_repo_root_nested_clone.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP07 – find_repo_root nested-clone boundary

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter (or any user-defined profile), and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `implementer-ivan`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this work package's `task_type` and `authoritative_surface`.

---

## Markdown Formatting

Wrap HTML/XML tags in backticks. Use language identifiers in code blocks.

---

## Objectives & Success Criteria

Eliminate the **nested-clone resolver disagreement**: `find_repo_root` re-anchors a nested clone (a clone living inside a primary) to the **outer primary**, while `resolve_canonical_root` correctly returns the **nested clone itself**. Align `find_repo_root` to stop at the nested-clone `.git`-directory boundary.

Done when:
- A red-first regression proves the disagreement on base: for a nested clone, `find_repo_root` returns the outer primary while `resolve_canonical_root` returns the nested clone — RED on `upstream/main`.
- After the fix, both resolvers return the nested clone for a nested-clone CWD.
- **The `get_main_repo_root` primitive is NOT globally flipped** (~130 callers) — the fix is a targeted boundary-stop in the ancestor walk, preserving deliberate linked-worktree→primary re-anchoring.
- `ruff` + `mypy` clean; complexity ≤15; existing worktree-centralization tests stay green.

## Context & Constraints

- **Sequences after WP01.** WP01 is additive-only (it does not edit `core/paths.py`), so there is no real overlap — but claim WP07 only after WP01 lands to avoid churn on `core/paths.py`.
- Squad grounding (`research.md` Decision 0): the standalone-clone re-anchor is a phantom; the nested-clone disagreement is the one genuine resolver bug. Standalone clones already resolve to self on both resolvers.
- Anchors (verify at implement time): `task_utils/support.py:45,63-72` (`find_repo_root` → `locate_project_root` + `get_main_repo_root`); `core/paths.py:254-265` (`locate_project_root` returns at a `.git` dir only if `.kittify` present, else walks UP — the boundary-cross); rule 1 `:428-430` in `resolve_canonical_root` (stops at any `.git` dir — the correct behavior to match).
- **Do NOT break** the deliberate linked-worktree→primary re-anchor: `tests/contract/test_canonical_root_when_in_worktree.py` and `tests/unit/workspace/test_root_resolver.py` assert it and MUST stay green.

## Branch Strategy

- **Strategy**: lane-per-WP (coord topology)
- **Planning base branch**: fix/worktree-root-resolution
- **Merge target branch**: fix/worktree-root-resolution

> Execution worktrees are allocated per computed lane from `lanes.json`. Do not change these fields manually.

## Subtasks & Detailed Guidance

### Subtask T020 – Red-first: nested clone re-anchored to outer primary

- **Purpose**: Prove the resolver disagreement on base (NFR-001).
- **Steps**:
  1. In `tests/specify_cli/core/test_find_repo_root_nested_clone.py`, create a primary checkout with `.kittify`, then a **nested clone** inside it (its own `.git` directory) that **MUST omit `.kittify`** — this is required, not optional: the walk-up (and thus the whole disagreement) only manifests when the nested clone lacks `.kittify`. With `.kittify` present, `locate_project_root` returns the nested clone at `paths.py:256` and both resolvers agree (no red).
  2. Assert on base: `find_repo_root(nested)` returns the OUTER primary while `resolve_canonical_root(nested)` returns the nested clone. `@pytest.mark.regression`, pin #2610.
  3. Add a control asserting a standalone (non-nested) clone already resolves to self on both (documents the phantom).
  4. Confirm RED on `upstream/main`.
- **Files**: `tests/specify_cli/core/test_find_repo_root_nested_clone.py` (new, ~90 lines).
- **Parallel?**: [P].

### Subtask T021 – Stop find_repo_root at the nested-clone boundary

- **Purpose**: Align the two resolvers.
- **Steps**:
  1. In `core/paths.py` `locate_project_root` (the ancestor walk at `:254-265`), stop at a nested `.git`-directory boundary consistently with `resolve_canonical_root` rule 1 — do not walk past a `.git` dir to an outer checkout merely because `.kittify` is absent at that level.
  2. Ensure `task_utils/support.py` `find_repo_root` inherits the corrected boundary (it delegates).
  3. Verify the deliberate linked-worktree (`.git` *file* pointer) re-anchor is untouched — only the nested `.git`-*directory* boundary changes.
  4. Run the existing worktree-centralization tests and confirm green.
- **Files**: `src/specify_cli/core/paths.py`, `src/specify_cli/task_utils/support.py`.
- **Notes**: Keep the change minimal and local (locality-of-change). Do not refactor the primitive.

## Test Strategy

- `test_find_repo_root_nested_clone.py`: red-first (T020) + green-after (both resolvers agree on the nested clone) + standalone-clone control.
- Regression guard: run `pytest tests/contract/test_canonical_root_when_in_worktree.py tests/unit/workspace/test_root_resolver.py -n0 -q` and confirm still green (deliberate re-anchor preserved).
- Run: `pytest tests/specify_cli/core/test_find_repo_root_nested_clone.py -n0 -q`.

## Risks & Mitigations

- **Risk**: over-broad boundary change regresses the deliberate linked-worktree re-anchor. **Mitigation**: gate the change on `.git` being a *directory* (nested clone), never a *file* pointer (worktree); run the two centralization test files as a guard.
- **Risk**: touching `core/paths.py` conflicts with WP01. **Mitigation**: WP01 is additive-only; sequence WP07 after WP01.

## Review Guidance

- Confirm only the `.git`-directory boundary changed; linked-worktree pointer handling is identical.
- Confirm the two centralization test files remain green.

## Activity Log

- 2026-08-18T21:17:24Z – system – Prompt created.
