---
work_package_id: WP08
title: Legacy mission fallback + CLI status mediation
dependencies:
- WP07
requirement_refs:
- FR-017
- FR-027
- FR-028
- FR-030
tracker_refs: []
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T035
- T036
- T037
- T038
agent: claude
history:
- at: '2026-05-28T08:55:00+00:00'
  actor: claude
  event: wp_created
  notes: Generated via /spec-kitty.tasks from plan.md PR 2 design
agent_profile: implementer-ivan
authoritative_surface: src/specify_cli/missions/_read_path_resolver.py
execution_mode: code_change
owned_files:
- src/specify_cli/cli/commands/agent/tasks.py
- src/specify_cli/cli/commands/agent/context.py
- src/specify_cli/cli/commands/agent/decisions.py
- src/specify_cli/missions/_read_path_resolver.py
- tests/integration/test_legacy_mission_fallback.py
- tests/integration/test_cli_status_mediation.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else in this prompt, invoke `/ad-hoc-profile-load` with the profile listed in this WP's frontmatter (`agent_profile`). This loads the implementer identity, governance scope, and boundaries you must operate under for this WP.

Then return here and proceed.

---

## Objective

Two related fixes that close issue #1348 for **all** missions:

1. **Legacy mission fallback** (FR-017, FR-027, SC-11): Missions created before the coordination-branch topology landed continue to work. The pre-flight gate, transaction, lock, rollback, and outbound deferral apply uniformly. Only the `destination_ref` differs (resolves to the lane branch instead of a coord branch).

2. **CLI status mediation** (FR-030): `spec-kitty agent tasks status`, `agent context resolve`, and any read-side command resolve the coordination worktree (or primary checkout in legacy mode) regardless of operator CWD. Lane agents query the CLI; the CLI knows where the truth lives.

## Context

**Spec source**: FR-017, FR-027, FR-030, SC-11.
**Predecessor WPs**: WP07 (two-stage merge).
**Contracts**: `contracts/cli_status_mediation.md`.

After WP07 landed, new missions use the coord-branch topology end-to-end. **In-flight missions created before this change** still exist in the wild; they need the same atomicity invariants without the topology shift.

## Branch Strategy

- **Planning base branch**: `main`
- **Merge target branch**: `main`
- Lane C; sequential after WP07.

---

## Subtask T035: Legacy mission detection → lane-branch destination_ref

**Purpose**: When `BookkeepingTransaction.acquire()` runs against a mission whose `meta.json` lacks `coordination_branch`, resolve the worktree to the operator's current lane worktree and resolve `destination_ref` to the lane branch.

**Steps**:
1. In `src/specify_cli/coordination/transaction.py` (WP05's `acquire()` method), add a branch:
   ```python
   @classmethod
   def acquire(cls, *, repo_root, mission_id, mission_slug, mid8, destination_ref, operation, ...):
       # Detect legacy mission
       meta = load_mission_meta(repo_root, mission_slug)
       if not meta.get("coordination_branch"):
           # Legacy mission — use lane worktree, lane branch as destination_ref
           worktree_root, destination_ref = _resolve_legacy_lane_destination(repo_root, mission_id)
           _emit_legacy_warning_once(repo_root, mission_id)
       else:
           # New topology — use coordination worktree
           worktree_root = CoordinationWorkspace.resolve(repo_root, mission_slug, mid8)
       # ... continue with existing acquire logic
   ```
2. Implement `_resolve_legacy_lane_destination(repo_root, mission_id)`:
   - Find the lane worktree the operator is currently in (resolve from CWD).
   - Read the lane branch name from `git -C <worktree> symbolic-ref HEAD`.
   - Return `(worktree_root, destination_ref)`.
3. Implement `_emit_legacy_warning_once(repo_root, mission_id)`:
   - Check for `.kittify/legacy-warning-shown-<mission_id>` marker file.
   - If absent, print one-line stderr: `"warning: mission '<slug>' uses the legacy topology (no coordination branch). New atomicity invariants apply, but consider migrating: see docs/migration/legacy-to-coordination.md"`. Create marker.
   - If present, no-op.

**Files**:
- `src/specify_cli/coordination/transaction.py`

**Validation**:
- [ ] Legacy mission `acquire()` resolves to lane worktree.
- [ ] Warning appears once per mission, suppressed thereafter.
- [ ] New-topology missions are unaffected.

## Subtask T036: Pre-flight gate + transaction + rollback apply to legacy

**Purpose**: Verify that the entire transaction machinery works in legacy mode. The pre-flight policy must still refuse when the lane branch is somehow protected (rare but possible).

**Steps**:
1. No new code needed in the transaction layer (T035 handled it). Just verify by testing.
2. Add a code comment in `transaction.py.acquire()` documenting the legacy path explicitly so future maintainers understand the two cases.
3. Verify that the surgical truncate rollback works against the lane worktree's `status.events.jsonl`. The file path resolution in `acquire()` must use the right worktree:
   ```python
   events_path = worktree_root / "kitty-specs" / f"{mission_slug}-{mid8}" / "status.events.jsonl"
   ```
   In legacy mode, this is the lane worktree (which contains the file because no sparse-checkout policy is registered on legacy lanes).
4. Optional: emit a stronger one-time warning if the lane branch ends up matching a protected ref (e.g. someone ran `git checkout main` in their lane worktree). The HEAD assertion in `safe_commit` will catch this loudly via `SAFE_COMMIT_HEAD_MISMATCH`.

**Files**:
- `src/specify_cli/coordination/transaction.py` (comments + verification)

**Validation**:
- [ ] Tests in T038 demonstrate the entire transaction works in legacy mode.

## Subtask T037: CLI status mediation

**Purpose**: Read-side commands resolve the right path. From a lane worktree's CWD, the read path is the coordination worktree (new topology) or the primary checkout (legacy).

**Steps**:
1. Create `src/specify_cli/missions/_read_path_resolver.py`:
   ```python
   from pathlib import Path
   from specify_cli.coordination.workspace import CoordinationWorkspace

   def resolve_mission_read_path(repo_root: Path, mission_slug: str, mid8: str) -> Path:
       """Return the path to read mission status data from.

       Priority:
       1. Coordination worktree (new topology) if it exists.
       2. Primary checkout view of kitty-specs/<mission>/ (legacy or fallback).
       """
       coord = CoordinationWorkspace.worktree_path(repo_root, mission_slug, mid8)
       if coord.exists():
           return coord / "kitty-specs" / f"{mission_slug}-{mid8}"
       return repo_root / "kitty-specs" / f"{mission_slug}-{mid8}"
   ```
2. Update every read-side command to use this resolver:
   - `src/specify_cli/cli/commands/agent/tasks.py` — `agent tasks status` reads `status.events.jsonl` / `status.json`.
   - `src/specify_cli/cli/commands/agent/context.py` — `agent context resolve` returns a status snapshot.
   - `src/specify_cli/cli/commands/agent/decisions.py` — `agent decision verify` reads `decisions/index.json`.
   - Any other command that reads from `kitty-specs/<mission>/...` for status purposes.
3. Each command resolves the mission handle (existing helper), then calls `resolve_mission_read_path()` to get the right base dir, then reads from there.
4. Add a clear error `STATUS_READ_PATH_NOT_FOUND` if neither coord worktree nor primary checkout has the mission dir.

**Files**:
- `src/specify_cli/missions/_read_path_resolver.py` (new)
- `src/specify_cli/cli/commands/agent/tasks.py`
- `src/specify_cli/cli/commands/agent/context.py`
- `src/specify_cli/cli/commands/agent/decisions.py`

**Validation**:
- [ ] `spec-kitty agent tasks status --mission <handle>` from a lane worktree returns the same data as from the primary checkout.
- [ ] Read-side commands work in both topologies.

## Subtask T038: Integration tests — legacy regression + CLI mediation

**Purpose**: Verify SC-11 (legacy mission regression closed) and SC-02 (lane-vs-primary read consistency).

**Steps**:
1. In `tests/integration/test_legacy_mission_fallback.py`:
   - **Fixture**: `legacy_mission` — creates a mission by emulating the pre-PR2 topology (no coord branch, lanes parented on target).
   - `test_legacy_mission_implement_uses_lane_destination()` — assert `acquire()` resolves to lane worktree + lane branch.
   - `test_legacy_mission_warning_emitted_once()` — assert warning appears on first invocation, not on subsequent.
   - `test_legacy_mission_forced_commit_failure_rolls_back()` — inject failing hook; assert SHA-256 of event log byte-identical; SC-11 regression test.
   - `test_legacy_mission_protected_lane_branch_refused()` — somehow make the lane branch match a protected pattern; assert pre-flight refuses.
2. In `tests/integration/test_cli_status_mediation.py`:
   - `test_status_from_lane_worktree_matches_primary()` — spawn `spec-kitty agent tasks status` from inside a lane worktree CWD; assert identical output to a primary-checkout call.
   - `test_status_from_random_cwd()` — spawn from `/tmp`; assert identical output (the `--mission` handle resolution doesn't depend on CWD).
   - `test_legacy_mission_read_falls_back_to_primary()` — legacy mission; read commands fall back to primary checkout.

**Files**:
- `tests/integration/test_legacy_mission_fallback.py`
- `tests/integration/test_cli_status_mediation.py`

**Validation**:
- [ ] All tests pass.
- [ ] SC-11 is explicitly verified by the failing-hook test on a legacy fixture.
- [ ] SC-02 is explicitly verified by the lane-vs-primary read test.

---

## Definition of Done

- [ ] All 4 subtasks complete (T035..T038).
- [ ] `pytest tests/integration/test_legacy_mission_fallback.py` passes.
- [ ] `pytest tests/integration/test_cli_status_mediation.py` passes.
- [ ] A legacy mission running `implement` hits the same atomicity invariants as a new-topology mission.
- [ ] Read-side commands work from any CWD.

## Risks

- **Legacy mission fixtures**: setting up a "pre-PR2" mission state in a tmp repo requires understanding the pre-existing topology. Reuse fixtures from prior mission tests if possible.
- **Marker file path**: `.kittify/legacy-warning-shown-<mission_id>` must be inside the project, not the user's home. Per-project state.
- **CLI mediation overhead**: every read-side command now does `git worktree list` once. Cache the result for the lifetime of the process to avoid repeated cost.

## Reviewer guidance

1. **Legacy detection signal**: confirm the detection is "meta.json lacks coordination_branch field", not "no coord branch exists in git". A new-topology mission with a manually-deleted coord branch should NOT be detected as legacy (FR-018 idempotency re-creates).
2. **Atomicity invariants apply uniformly**: the transaction layer code path in legacy mode is the same as new-topology mode; only path resolution differs. Verify by reading `acquire()`.
3. **CLI mediation is read-only**: confirm no read-side command writes to the worktree. (Write-side commands use `BookkeepingTransaction`, not the read resolver.)
4. **Warning UX**: confirm the warning is helpful, points to docs, and suppresses after first emit.

## References

- Spec: FR-017, FR-027, FR-030, SC-02, SC-11
- Plan: PR 2 steps 10–11
- Contract: [`contracts/cli_status_mediation.md`](../contracts/cli_status_mediation.md)
- Research: R-004, R-006 in [`research.md`](../research.md)
