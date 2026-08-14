---
work_package_id: WP01
title: Unify the git-topology primitive (#3373)
dependencies: []
requirement_refs:
- FR-008
- FR-009
- FR-010
planning_base_branch: mission/write-path-integrity
merge_target_branch: mission/write-path-integrity
branch_strategy: Planning artifacts for this mission were generated on mission/write-path-integrity. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into mission/write-path-integrity unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-write-path-integrity-01KZZD69
base_commit: 8a1356aa7dff122de98644837c0ca498dc532de4
created_at: '2026-08-14T13:11:20.027050+00:00'
subtasks:
- T001
- T002
- T003
- T004
- T005
- T006
phase: Phase 1 - Substrate
history:
- at: '2026-08-14T08:00:00+00:00'
  actor: system
  action: Prompt generated during tasks phase
agent_profile: implementer-ivan
authoritative_surface: src/specify_cli/git/
create_intent:
- src/specify_cli/git/git_topology.py
- tests/git/test_git_topology.py
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/git/git_topology.py
- src/charter/resolution.py
- src/specify_cli/core/checkout_ownership.py
- src/specify_cli/git/commit_helpers.py
- src/specify_cli/workspace/context.py
- tests/git/test_git_topology.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP01 – Unify the git-topology primitive (#3373)

## ⚡ Do This First: Load Agent Profile

Load `implementer-ivan` via `/ad-hoc-profile-load` before proceeding.

## Objectives & Success Criteria

Collapse the four re-implementations of the git-common-dir/toplevel probe into **one primitive** with a
single symlink-canonicalization contract, so the checkout-identity comparison (WP03) and the
nested/toplevel classifier have one drift-free authority. This is the **substrate WP03 stands on** and
lands first.

**Done when**:
- One `git_common_dir()`/`git_toplevel()` primitive exists (`src/specify_cli/git/git_topology.py`) with:
  caching, not-a-repo classification, `.git`-interior detection, and **one** symlink-canonicalization
  contract. (SC-005)
- The four call sites consume it with **no behavior change** — each preserves its distinct error
  contract. (SC-005)
- The `effective_root ? legacy : compose_meta_json_path(...)` fork (~12×) in `mission_runtime/
  resolution.py` is one `read_dir_for(...)` helper; a static gate asserts zero other copies. (SC-007)
- One nested/toplevel classifier feeds both the `is_worktree_of` fast gate and the comparator; the
  **NESTED refusal** is preserved (existing-behavior test). (SC-008)

## Context & Constraints

- Spec: [spec.md](../spec.md) US3, FR-008/009/010, SC-005/007/008. Plan: [plan.md](../plan.md) IC-01.
- Charter: [`.kittify/charter/charter.md`](../../../.kittify/charter/charter.md).
- **The four probes answer DIFFERENT questions** — unify the *primitive*, not the *semantics*:
  - `src/charter/resolution.py` (~66-111): cached (`@lru_cache`) canonical **repo-root** resolver;
    already `.resolve()`s; classifies "not a git repository". **Hot path, ~20 callers** — preserve its
    return shape (repo root, not common-dir) and caching exactly.
  - `src/specify_cli/core/checkout_ownership.py` (`_git_common_dir`, `_git_toplevel`): ownership
    classification.
  - `src/specify_cli/git/commit_helpers.py` (`_is_worktree_of`): linkage comparison + NESTED guard.
  - `src/specify_cli/workspace/context.py` (`verify_workspace_toplevel`): is-worktree assertion.
- **Do NOT** flatten the four to the poorest contract; the primitive must be rich enough for the charter
  resolver (caching + not-a-repo), and the other three adapt to consume it.
- No topology redesign (#1878); no behavior change (this is a behavior-preserving consolidation).

## Subtasks & Detailed Guidance

### Subtask T001 – Create the `git_topology` primitive
- **Purpose**: One authority for the git-common-dir/toplevel probe.
- **Steps**: New module `src/specify_cli/git/git_topology.py`. Expose `git_common_dir(path)` /
  `git_toplevel(path)` returning canonicalized paths (single `.resolve()` contract), with a typed
  not-a-repo result/exception and `.git`-interior detection. Reuse an LRU cache (mirror
  `charter/resolution.py`'s maxsize). Keep the error *classification* (not-a-repo vs unavailable)
  distinguishable so each caller can map it to its own contract.

### Subtask T002 [P] – Migrate the charter resolver
- **Purpose**: Fold the richest (cached, classifying) copy onto the primitive without regressing ~20
  callers.
- **Steps**: Rewrite `charter/resolution.py`'s probe internals to delegate to `git_topology`, preserving
  the repo-**root** return (parent of common-dir), the `@lru_cache`, and `NotInsideRepositoryError` /
  `GitCommonDirUnavailableError` mapping. Do NOT change its public signature.
- **Files**: `src/charter/resolution.py`.

### Subtask T003 [P] – Migrate the three remaining probes
- **Steps**: Replace `_git_common_dir`/`_git_toplevel` in `checkout_ownership.py`, the probe in
  `git/commit_helpers.py::_is_worktree_of`, and `workspace/context.py::verify_workspace_toplevel` with
  primitive calls. Preserve each site's error contract (bool / structured `WorkspaceResolutionError` /
  typed).
- **Files**: `src/specify_cli/core/checkout_ownership.py`, `src/specify_cli/git/commit_helpers.py`,
  `src/specify_cli/workspace/context.py`.

### Subtask T004 – Consolidate the effective-root read-fork into `read_dir_for`
- **Purpose**: One `read_dir_for(...)` for the `effective_root is None ? legacy : compose_meta_json_path`
  derivation recurring ~12× inside the coord/topology resolvers.
- **Steps**: Add `read_dir_for(effective_root, primary_root, mission_slug, kind, ...)` and route
  `_resolve_coordination_branch`/`_resolve_topology`/`_resolve_status_surface_dir`/`mission_context_for`
  through it. No re-validation drift — the validated root is still threaded once.
- **Files**: `src/mission_runtime/resolution.py`.

### Subtask T005 – Unify the nested/toplevel classifier
- **Purpose**: One authority feeding both the fast `is_worktree_of` gate and the comparator
  classification, preserving the NESTED refusal (deleting the `_is_worktree_of` toplevel guard as
  "redundant" silently regresses NESTED — keep the two-stage semantics).
- **Files**: `src/specify_cli/git/commit_helpers.py`, `src/specify_cli/core/checkout_ownership.py`.

### Subtask T006 – Parity tests + one-copy static gates
- **Steps**: Behavior-parity tests (charter caching, not-a-repo classification, NESTED refusal stay
  green). Add static gates: exactly one `git_common_dir`/`git_toplevel` primitive (SC-005); exactly one
  `read_dir_for` (SC-007); one nested classifier (SC-008).
- **Files**: `tests/git/test_git_topology.py`, `tests/architectural/`.

## Definition of Done

- All six subtasks complete; existing suite green (no behavior change); the three one-copy gates pass;
  `ruff` + `mypy` clean.

## Risks & Reviewer Guidance

- **Reviewer**: verify the charter resolver's return shape + caching are byte-for-byte preserved (grep
  its callers). Confirm no probe was flattened to a poorer contract. Confirm the NESTED refusal test
  still bites (deleting the `_is_worktree_of` guard must fail a test).
