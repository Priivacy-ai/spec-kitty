---
work_package_id: WP03
title: Mission create mints coordination branch
dependencies:
- WP02
requirement_refs:
- C-001
- C-005
- C-006
- FR-003
- FR-015
- FR-018
tracker_refs: []
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-mission-coordination-branch-atomic-event-log-01KSPTVW
base_commit: fc1aa41f62840ca1fa430e2d8fc372f384fc5421
created_at: '2026-05-28T10:48:26.399429+00:00'
subtasks:
- T011
- T012
- T013
- T014
agent: "claude:opus:reviewer-rita:reviewer"
shell_pid: "20899"
history:
- at: '2026-05-28T08:55:00+00:00'
  actor: claude
  event: wp_created
  notes: Generated via /spec-kitty.tasks from plan.md PR 2 design
agent_profile: implementer-ivan
authoritative_surface: src/specify_cli/cli/commands/agent/mission_create.py
execution_mode: code_change
owned_files:
- src/specify_cli/cli/commands/agent/mission_create.py
- src/specify_cli/missions/_create.py
- tests/specify_cli/cli/commands/agent/test_mission_create.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else in this prompt, invoke `/ad-hoc-profile-load` with the profile listed in this WP's frontmatter (`agent_profile`). This loads the implementer identity, governance scope, and boundaries you must operate under for this WP.

Then return here and proceed.

---

## Objective

`spec-kitty agent mission create` mints the per-mission coordination branch `kitty/mission-<slug>-<mid8>` parented off the canonical target branch. The branch creation is idempotent (safe to re-run on partially-created missions). The branch ref is persisted in `meta.json` and exposed in the `mission create --json` output. This WP introduces the *topology* — later WPs (WP04..WP06) add the worktree, transaction, and call-site routing.

## Context

**Spec source**: FR-003, FR-015, FR-018, C-001, C-005, C-006.
**Predecessor WPs**: WP01 (helper signature), WP02 (caller migration). PR 1 must ship first.
**Successor WPs**: WP04 (CoordinationWorkspace uses this branch), WP07 (mission merge tears it down).

**Note about file location**: `agent mission create` may live in `src/specify_cli/cli/commands/agent/mission.py` (single file) OR be split into per-subcommand files (`mission_create.py`, `mission_finalize_tasks.py`, etc.). If it's a single file, the owned_files list in this WP and WP07 will conflict (WP07 owns the finalize-tasks fix in the same file). **Before starting, verify the file layout and adjust owned_files in this WP and/or WP07 accordingly via `spec-kitty agent tasks map-requirements` or a finalize-tasks dry run.**

## Branch Strategy

- **Planning base branch**: `main`
- **Merge target branch**: `main`
- Coordination branch this WP creates (for *this* mission): `kitty/mission-mission-coordination-branch-atomic-event-log-01KSPTVW-<mid8>` — note the `-coord` suffix is NOT applied to the branch name (just the worktree path, in WP04). The branch name is exactly `kitty/mission-<slug>-<mid8>`.

---

## Subtask T011: Add coordination branch creation logic to `agent mission create`

**Purpose**: After `mission_id` / `mid8` / `mission_slug` are minted, create the coordination branch parented off the canonical target.

**Steps**:
1. Locate the `mission create` subcommand handler (likely in `src/specify_cli/cli/commands/agent/mission.py` or a sub-module).
2. After the mission identity is established but before the command returns, compute:
   ```python
   coordination_branch = f"kitty/mission-{mission_slug}-{mid8}"
   ```
   Verify `mission_slug` and `mid8` are already sanitized (per DIR-010/DIR-011). They should be — the existing logic mints them ASCII-clean.
3. Resolve the target branch via the existing branch-context helper (Python API; do not shell out). The target branch is the value persisted to `meta.json` → `target_branch`.
4. Create the branch:
   ```python
   subprocess.run(
       ["git", "-C", str(repo_root), "branch", coordination_branch, target_branch],
       check=True,
   )
   ```
5. If the branch already exists, fall through to the idempotency logic in T012.

**Files**:
- `src/specify_cli/cli/commands/agent/mission.py` (or `mission_create.py` if split)

**Validation**:
- [ ] Running `spec-kitty agent mission create <slug>` against a fresh repo creates the coordination branch.
- [ ] `git branch --list 'kitty/mission-*'` shows the new branch.
- [ ] The branch points at the same commit as the target branch.

## Subtask T012: Idempotent branch creation

**Purpose**: Re-running `mission create` against a partially-created mission must reuse the existing branch (if it's an ancestor of the canonical target) or refuse with a clear error.

**Steps**:
1. Before creating the branch, check if it already exists:
   ```python
   result = subprocess.run(
       ["git", "-C", str(repo_root), "rev-parse", "--verify", "--quiet", coordination_branch],
       capture_output=True, text=True,
   )
   if result.returncode == 0:
       # branch exists — check ancestry
       ancestry = subprocess.run(
           ["git", "-C", str(repo_root), "merge-base", "--is-ancestor",
            coordination_branch, target_branch],
           capture_output=True,
       )
       if ancestry.returncode != 0:
           raise CoordinationBranchDiverged(
               coordination_branch=coordination_branch,
               target_branch=target_branch,
           )
       # else: reuse existing branch (idempotent)
       return
   # branch missing → create as in T011
   ```
2. Define the structured error `CoordinationBranchDiverged` with `error_code="COORDINATION_BRANCH_DIVERGED"`, `coordination_branch`, `target_branch`, and a `next_step` field guiding the operator to either rebase or recreate.
3. Add a CLI option `--force-recreate-coordination-branch` that deletes and re-creates the coordination branch (operator escape hatch; not the default).

**Files**:
- `src/specify_cli/cli/commands/agent/mission.py`

**Validation**:
- [ ] Running `mission create <slug>` twice for the same slug succeeds (second run is a no-op).
- [ ] If the coordination branch is at a divergent commit, the second run raises `CoordinationBranchDiverged`.
- [ ] `--force-recreate-coordination-branch` deletes and re-creates the branch.

## Subtask T013: Persist coordination branch ref in `meta.json`; expose in `--json` output

**Purpose**: Downstream commands (lane allocator, BookkeepingTransaction, merge) need to know the coordination branch name. Persisting it in `meta.json` avoids re-derivation drift.

**Steps**:
1. After branch creation/validation, update `meta.json` to include:
   ```json
   {
     "coordination_branch": "kitty/mission-<slug>-<mid8>"
   }
   ```
2. Update the `mission create --json` output schema to include the same field at the top level:
   ```json
   {
     "result": "success",
     "mission_id": "01KSPTVWZ9...",
     "mission_slug": "...",
     "coordination_branch": "kitty/mission-...",
     ...
   }
   ```
3. Update `meta.json` reads elsewhere (search for `meta_file` / `load_meta` patterns) to expose this field through their return types.

**Files**:
- `src/specify_cli/cli/commands/agent/mission.py` (or `mission_create.py`)
- Possibly `src/specify_cli/missions/_meta.py` or similar for the meta-loading helper.

**Validation**:
- [ ] `meta.json` of a new mission contains `coordination_branch`.
- [ ] `spec-kitty agent mission create --json` output contains `coordination_branch`.
- [ ] An existing helper that reads `meta.json` (e.g. `load_mission_meta()`) exposes the new field.

## Subtask T014: Unit tests

**Purpose**: Verify branch creation, idempotency, name derivation, and divergent-branch refusal.

**Steps**:
1. In `tests/specify_cli/cli/commands/agent/test_mission_create.py` (create the file if missing):
   - `test_mission_create_mints_coordination_branch()` — assert branch exists after create.
   - `test_mission_create_idempotent()` — call twice, assert no error, branch unchanged.
   - `test_mission_create_branch_diverged()` — manually advance the branch off the target, re-run create, assert `CoordinationBranchDiverged`.
   - `test_mission_create_force_recreate()` — diverged branch + `--force-recreate-coordination-branch` flag → branch reset to target.
   - `test_branch_name_uses_mid8()` — assert the branch name includes the 8-char prefix of `mission_id`.
   - `test_meta_json_contains_coordination_branch()` — assert the field is written.
   - `test_create_json_output_contains_coordination_branch()` — assert the CLI JSON exposes it.
2. Use the existing test fixtures (tmp repos, tmp `.kittify/` configs).

**Files**:
- `tests/specify_cli/cli/commands/agent/test_mission_create.py`

**Validation**:
- [ ] All 7 test cases pass.
- [ ] Coverage on new code in `mission.py` (or `mission_create.py`) ≥ 90%.

---

## Definition of Done

- [ ] All 4 subtasks complete (T011..T014).
- [ ] `pytest tests/specify_cli/cli/commands/agent/test_mission_create.py` passes.
- [ ] A fresh `spec-kitty agent mission create my-test --json` creates a coordination branch matching `kitty/mission-my-test-<mid8>`.
- [ ] Re-running the command is a no-op.
- [ ] `meta.json` contains `coordination_branch`.

## Risks

- **File-layout overlap with WP07**: If `mission.py` is a single monolithic file, WP03 and WP07 will fight for ownership. Verify before starting; if so, run `finalize-tasks --validate-only` to surface the conflict, then either split the file (preferred, into `mission_create.py` + `mission_finalize_tasks.py` etc.) or adjust owned_files in both WPs to use line-range semantics.
- **Branch name collision**: Per the identity model (mission 083), `mid8` disambiguates. If somehow two missions ended up with the same `mid8` (≤ 1 in 2^48 chance), the second `mission create` refuses gracefully.
- **Target branch resolution race**: If the target branch is updated between mission create and branch creation, the new coordination branch points at an old commit. Acceptable; doctor will catch on re-validation.

## Reviewer guidance

1. **Idempotency**: confirm re-running `mission create` for an existing mission slug is a clean no-op (not even a "warning: branch already exists" — silent reuse).
2. **Error structure**: `CoordinationBranchDiverged` carries error_code, coordination_branch, target_branch, next_step. JSON-serializable.
3. **Sanitization**: confirm `mission_slug` and `mid8` are not double-sanitized; they should already be ASCII-clean from the identity model.
4. **--force-recreate flag**: confirm it requires explicit operator opt-in (cannot be triggered by automation).
5. **meta.json schema**: confirm the new field is documented somewhere reachable (CLAUDE.md, or a schema doc).

## References

- Spec: FR-003, FR-015, FR-018, C-001, C-005, C-006
- Plan: PR 2 step 1
- Contract: [`contracts/coordination_workspace.md`](../contracts/coordination_workspace.md) § "Coordination worktree lifecycle"
- Identity model: ADR `2026-04-09-1-mission-identity-uses-ulid-not-sequential-prefix.md`

## Activity Log

- 2026-05-28T10:48:26Z – claude:opus:implementer-ivan:implementer – shell_pid=8057 – Assigned agent via action command
- 2026-05-28T11:03:02Z – claude:opus:implementer-ivan:implementer – shell_pid=8057 – WP03 implementation complete: coordination branch minted in agent mission create, persisted in meta.json, exposed in --json output. Includes idempotency, divergence detection, force-recreate escape hatch, and 9 passing unit tests.
- 2026-05-28T11:03:45Z – claude:opus:reviewer-rita:reviewer – shell_pid=20899 – Started review via action command
- 2026-05-28T11:05:40Z – claude:opus:reviewer-rita:reviewer – shell_pid=20899 – Review passed: WP03 mints kitty/mission-<slug>-<mid8> idempotently with structured CoordinationBranchDiverged error, persists ref in meta.json, exposes it in --json output, and adds --force-recreate-coordination-branch escape hatch; all 9 unit tests pass and mypy --strict is clean on owned files.
- 2026-05-28T12:52:27Z – claude:opus:reviewer-rita:reviewer – shell_pid=20899 – Done override: Mission merged to main in 886dde756
