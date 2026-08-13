---
work_package_id: WP02
title: mission create explicit-ownership integration
dependencies:
- WP01
requirement_refs:
- FR-001
- FR-004
- FR-008
- FR-009
- FR-010
- C-001
- C-002
planning_base_branch: fix/worktree-owned-root-3328-v2
merge_target_branch: fix/worktree-owned-root-3328-v2
branch_strategy: Planning artifacts for this mission were generated on fix/worktree-owned-root-3328-v2. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/worktree-owned-root-3328-v2 unless the human explicitly redirects the landing branch.
subtasks:
- T006
- T007
- T008
- T009
history:
- at: '2026-08-11T13:37:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks-packages
agent_profile: ''
authoritative_surface: src/specify_cli/core/mission_creation.py
create_intent:
- tests/mission_runtime/test_create_time_write_target.py
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/cli/commands/agent/mission_create.py
- src/specify_cli/core/mission_creation.py
- src/mission_runtime/__init__.py
- tests/agent/test_agent_feature.py
- tests/architectural/test_mission_runtime_surface.py
- tests/mission_runtime/test_create_time_write_target.py
role: implementer
tags: []
tracker_refs: []
---

# Work Package Prompt: WP02 - mission create explicit-ownership integration

## Objective

Add a new, explicit, validated CLI affordance to `spec-kitty agent mission create` that lets a caller declare the invoking worktree as the mission's owned root, using WP01's `resolve_ownership_claim()` — WITHOUT touching `allow_worktree_context` (FR-010/NFR-003) and WITHOUT changing behavior for any caller that omits the new flag (FR-004/C-001/C-002).

## Context

Today, `create_mission_core()` (`src/specify_cli/core/mission_creation.py:206-321`) refuses unconditionally when `Path.cwd()` is inside a worktree (line 309-314), regardless of what `repo_root` was passed. The refusal is disconnected from `repo_root` resolution entirely. This WP adds a new keyword parameter (see `contracts/checkout-ownership-cli-contract.md` for the exact `--owned-checkout` flag contract) that, when supplied, is validated via WP01's primitive BEFORE the existing guard fires — and only bypasses the guard when validation returns `OWNED`.

Read `plan.md` IC-02 and `contracts/checkout-ownership-cli-contract.md` in full before starting.

**Critical existing behavior to preserve** (regression net = `tests/agent/test_agent_feature.py::test_blocks_create_feature_from_worktree_with_main_repo_hint` and `::test_blocks_create_feature_from_worktree_with_worktrees_fallback_hint`, plus `tests/specify_cli/core/test_feature_creation.py::test_worktree_context_raises`): every one of these must still pass UNCHANGED — they exercise the no-opt-in path.

## Branch Strategy

- **Strategy**: {{branch_strategy}}
- **Planning base branch**: {{planning_base_branch}}
- **Merge target branch**: {{merge_target_branch}}

## Subtasks & Detailed Guidance

### Subtask T006 - Add `--owned-checkout` to the CLI surface

- **Purpose**: Expose the new affordance on `spec-kitty agent mission create`.
- **Steps**:
  1. In `src/specify_cli/cli/commands/agent/mission_create.py`, add a new `typer.Option` parameter `owned_checkout: Path | None = typer.Option(None, "--owned-checkout", help="...")` to `create_mission` (the function currently spanning lines ~404-533).
  2. Thread it into the call to `create_mission_core()` (the `_run_create_core_phase` helper, lines 250-309) as a new keyword — do NOT reuse or alias `allow_worktree_context`.
  3. Resolve `owned_checkout` with `.resolve()` before passing it down (consistent with how `repo_root` is resolved elsewhere in this file).
- **Files**: `src/specify_cli/cli/commands/agent/mission_create.py` (~20 line diff)
- **Parallel?**: Sequenced before T007 (same file, different function).

### Subtask T007 - Wire `create_mission_core()` to consult WP01's primitive

- **Purpose**: Replace the unconditional refusal with a validated branch.
- **Steps**:
  1. In `create_mission_core()` (`src/specify_cli/core/mission_creation.py:206-321`), add a new keyword parameter `owned_checkout: Path | None = None` (distinct from the existing `allow_worktree_context: bool = False` — do NOT remove or rename that parameter; it stays for its existing test-only purpose).
  2. Before the existing guard (lines 309-314), if `owned_checkout is not None`: call `resolve_ownership_claim(owned_checkout, resolved_primary=<the already-being-resolved repo_root>)`. On `OWNED`, skip the `is_worktree_context` refusal entirely for this invocation and proceed using `owned_checkout` as the effective worktree root for the write path (T008). On any other result, raise the corresponding structured error (see FR-011 / contracts) BEFORE reaching the existing generic `MissionCreationError`.
  3. When `owned_checkout is None`, behavior must be BYTE-IDENTICAL to today — the existing guard at lines 309-314 fires exactly as before.
- **Files**: `src/specify_cli/core/mission_creation.py` (~40 line diff)
- **Validation**: Re-run `tests/specify_cli/core/test_feature_creation.py::test_worktree_context_raises` — must still pass unmodified.

### Subtask T008 - Thread `owned_checkout` into `safe_commit` as `worktree_root`

- **Purpose**: Satisfy FR-008/FR-009 — mission-create writes must land in the owned checkout, not always `repo_root==repo_root`.
- **Steps**:
  1. Add `resolve_create_time_write_target(planning_branch: str) -> CommitTarget` to `src/mission_runtime/resolution.py` and export it from `src/mission_runtime/__init__.py`. This is the single canonical target seam for the create-time interval before mission identity is readable from the primary checkout. It accepts only an explicit non-empty short planning-branch name, rejects `refs/heads/...`, and performs no CWD/environment/topology/mission-directory lookup.
  2. After `create_mission_core()` derives `planning_branch` through its existing target/current-branch logic, and only when its `OwnershipClaim.validation_result == OWNED`, resolve that explicit branch through the bootstrap seam and pass the resulting `CommitTarget` into `_commit_feature_file()`. Extend `_commit_feature_file()` with an optional already-resolved create-time target; when present, call `safe_commit(repo_root=<canonical resolved_primary>, worktree_root=<owned_checkout>, target=<resolved target>, ...)` — mirroring `coordination/transaction.py`'s `BookkeepingTransaction` pattern (research D-5) rather than the current always-equal call. Do not call `placement_seam()` in this pre-readable-identity window: the primary checkout cannot yet expose the new mission's metadata.
  3. When no `OwnershipClaim` is present (default path), keep the existing `placement_seam(...).write_target(...)` and `safe_commit(repo_root=repo_root, worktree_root=repo_root, ...)` behavior exactly as today; the bootstrap seam must not run.
  4. Confirm mission-directory scaffolding (spec.md/meta.json/tasks/README.md writes) is written under `owned_checkout`, not `resolved_primary`, when ownership is `OWNED` (FR-008: mission/ref write isolation).
  5. In `tests/mission_runtime/test_create_time_write_target.py`, prove short-branch passthrough, refusal of empty/fully-qualified refs, independence from CWD/environment/mission metadata, and that the existing placement seam remains the default after identity becomes readable.
  6. In `tests/architectural/test_mission_runtime_surface.py`, add the new package-root export to the exact `_PUBLIC_SURFACE` contract. This non-vacuous gate maps the seam's no-internal-import requirement to C-002/FR-009: `mission_creation.py` must consume the canonical umbrella symbol, never import `mission_runtime.resolution` directly.
- **Files**: `src/specify_cli/core/mission_creation.py`, `src/mission_runtime/resolution.py`, `src/mission_runtime/__init__.py`, `tests/mission_runtime/test_create_time_write_target.py`, `tests/architectural/test_mission_runtime_surface.py`
- **Validation**: Manual check per `quickstart.md` step 3 — inspect that the created mission's files exist under the owned checkout path, and `git status --short` in the primary checkout remains clean.

### Subtask T009 - Regression tests for the unchanged default path + new opted-in path

- **Purpose**: Prove FR-004/C-001/C-002 hold and FR-001 works.
- **Steps**:
  1. In `tests/agent/test_agent_feature.py`, add a new test asserting `--owned-checkout` from a real linked worktree (via `tmp_path` + `git worktree add`) succeeds and the mission lands under that worktree.
  2. Confirm the three EXISTING worktree-refusal tests in this file still pass with ZERO modification to their assertions (only add new tests; do not touch the existing ones beyond what's needed to keep them passing after T006/T007's signature changes).
  3. Add a test for the `NESTED`/`FOREIGN_OR_MISMATCHED` refusal surfaced through the CLI (`--json` output `error_code`), per `contracts/checkout-ownership-cli-contract.md`.
- **Files**: `tests/agent/test_agent_feature.py` (~80 line diff)

## Test Strategy

- `.venv/bin/pytest tests/agent/test_agent_feature.py tests/specify_cli/core/test_feature_creation.py tests/core/test_mission_create_activation_gate.py -q`
- `.venv/bin/pytest tests/mission_runtime/test_create_time_write_target.py tests/mission_runtime/test_placement_seam.py -q`
- Manually run `quickstart.md` steps 2-3 and 7 (no-opt-in + nested/foreign cases) against a local build.

## Risks & Mitigations

- **Risk**: `_print_worktree_navigation_hint`'s substring match on `"worktree"` (mission_create.py:228-247) could mis-fire for the NEW error classes if their messages also contain the word "worktree". **Mitigation**: gate that hint's substring match to ONLY the unchanged `MissionCreationError` type, not the new structured exceptions from WP01.
- **Risk**: Changing `create_mission_core()`'s signature could break `tests/_factories/__init__.py::make_mission()`'s keyword-forwarding. **Mitigation**: add `owned_checkout` as a new, optional, keyword-only parameter at the end of the signature — never reorder existing parameters.

## Definition of Done

- [ ] `--owned-checkout` succeeds for a real linked worktree at a generic (non-`.worktrees`) path.
- [ ] All pre-existing worktree-refusal tests pass unmodified.
- [ ] `NESTED`/`FOREIGN_OR_MISMATCHED`/`BROKEN_POINTER` surface as distinguishable `--json` `error_code` values.
- [ ] No production call site newly introduces `allow_worktree_context=True` (verify with `tests/architectural/test_no_production_worktree_guard_bypass.py`).

## Reviewer Guidance

- Confirm `allow_worktree_context` and `owned_checkout` are fully independent parameters — no aliasing, no shared code path that could be confused for the other.
- Confirm the mission's files genuinely land under the owned checkout (not just a `--json` field claiming they do) — check on disk.
- Confirm the bootstrap target seam is used only after exact-root ownership validation and cannot discover a target from ambient state; reject any use as a general replacement for `placement_seam()`.

**Implementation command**: `spec-kitty agent action implement WP02 --agent <name>`

## Activity Log

- 2026-08-11T13:37:00Z - system - Prompt created.
