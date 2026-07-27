# Contracts — unified partition authority, cwd resolution, protected-branch warning

Internal contracts (no HTTP surface). These are the seams the tests pin.

## 1. Unified partition authority (FR-005 / C-007)

- **The authority is the EXISTING `mission_runtime.is_coordination_artifact_residue_path(path)`**
  — NOT a net-new `partition_of` wrapper. Two of the three sites already call it
  (`implement.py:600`, `implement_cores.py:268`).
  - `is_coordination_artifact_residue_path(path)` True → COORD.
  - else → PRIMARY. In particular `kind=None` (meta.json, unrecognized) → **PRIMARY** (C-007).
- **Consolidation = classifier-only swap** of `commit_router:404`'s
  `kind_for_mission_file(file) or kind` onto the residue predicate. `commit_router` KEEPS
  `resolve_placement_only` for its actual COORD ref (`other_ref`). No cli-side `partition_of`
  (redundant + inverts `cli → coordination` layering, C-008); no `mission_runtime` edit
  (read-only).
- **Primary-ref expression** unified SEPARATELY (cli-local, Lane A): read (`"HEAD"`) and
  write (`planning_branch`) derive the primary ref from one place so they agree by
  construction — does NOT touch `commit_router`.
- **Structural guarantee (SC-004)**: `implement.py::_partition_files_for_commit`,
  `commit_router::_group_files_by_partition`, and `implement_cores.py::resolve_precondition_ref`
  resolve their partition via the shared predicate; a test asserts no independent classifier
  remains for these three named sites (old code deleted or forwarding) AND that
  `commit_router` no longer consults `is_primary_artifact_kind(kind_for_mission_file(...))`
  for the split. Scope: the three named sites only (not every predicate-consumer).
- **Regressions that MUST stay green**: the #2533 solo-PR-bound-coord claim repro
  (`test_implement.py::TestSoloPrBoundCoordMissionClaimPrecondition`), the #2648
  narrow-triple fail-close pin, AND the 3 write-side `placement_ref=None` success tests.

## 2. move-task cwd-independent status surface (FR-001)

- **Given** `move-task WP## --to <lane>` with cwd inside a lane worktree, **then** the
  status surface is resolved from the canonical mission root (not the worktree), and the
  transition outcome equals the repo-root invocation.
- The repo-root invocation MUST remain green (no regression).

## 3. Narrow-triple placement fail-close (FR-002 / C-009)

- The silent protected-`planning_branch` coord-divert (`implement.py:767-789`) is **removed**
  and replaced with a loud fail-close on the NARROW triple.
- **Given** the narrow triple — `placement_ref is None` AND meta `coord_branch` truthy AND
  `is_protected(planning_branch)` (exactly the `767` precondition, exactly where the status
  half already raises) — **then** the artifact-commit step raises `PlacementResolutionRequired`
  with the SAME operator remediation message as the status-commit step
  (`_resolve_claim_commit_target`, `implement_cores.py:608`), so both halves fail-closed
  together; no partial or silent commit. Implementation: raise explicitly at that arm
  (Option B) — NOT delete-and-let-`790`-hit-a-generic-`typer.Exit(1)` (Option A raises the
  wrong type/message).
- **Given** any OTHER `placement_ref is None` state — flat/legacy (no `coord_branch`) or
  coord + non-protected `planning_branch` — **then** the commit still SUCCEEDS (C-004
  strangler). `placement_ref is None` is overloaded (#2463); do NOT fail-close on bare `None`.
- The regression test drives the narrow-triple state and asserts the loud fail-close (not a
  warning, not a divert); AND asserts the 3 write-side `None` success cases + the #2533
  regression stay green.

## 4. Degod contracts (behavior-preserving — FR-003/FR-004)

- Public signatures + return shapes preserved for Lane-B-imported symbols
  (`_resolve_bookkeeping_transaction_identifiers` 5-tuple, `_feature_dir_file_paths`,
  `_planning_artifact_source_dir`) — C-006.
- Preserved invariants (characterized first): cascade order + ambiguous-handle RAISE;
  `console._file=None` reset; `_mt_uncheck_rollback_subtasks` two-handler separation (C-001).
- No net-new public/exported symbol (C-008); extracted helpers module-private.
- `_do_move_task` parameters ≤ 13 measured post-#2639-rebase (parameter-object) — C-005.

## Guard contracts (MUST NOT change)

- `mission_runtime/*` read-only (partition sets, `is_coordination_artifact_residue_path`).
- No new artifact-kind→partition mapping literal (reuse the residue predicate).
- move-task / commit semantics unchanged beyond the two named bug fixes.
