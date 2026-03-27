---
work_package_id: WP08
title: Merge Engine v2 — Orchestration
lane: "for_review"
dependencies: [WP07]
requirement_refs:
- FR-013
- FR-014
- FR-015
- NFR-005
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
base_branch: 057-canonical-context-architecture-cleanup-WP07
base_commit: 65c6466cb7bde156b8f866f383b0977d43f7fb99
created_at: '2026-03-27T19:57:38.975398+00:00'
subtasks:
- T039
- T040
- T041
- T042
- T043
phase: Phase C - Merge
assignee: ''
agent: coordinator
shell_pid: '9348'
review_status: ''
reviewed_by: ''
review_feedback: ''
history:
- timestamp: '2026-03-27T17:23:39Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP08 – Merge Engine v2 — Orchestration

## Branch Strategy

- **Planning/base branch at prompt creation**: `main`
- **Final merge target for completed work**: `main`

---

## Objectives & Success Criteria

- Merge engine orchestrates WP merges in dependency order in the dedicated workspace.
- Resume works: interrupted merge continues from last completed WP.
- Spec-kitty-owned file conflicts are auto-resolved.
- Post-merge reconciliation emits done events from actual git ancestry.
- Merge is deterministic: same inputs → same result regardless of main repo state.

## Context & Constraints

- **Spec**: FR-013, FR-014, FR-015, NFR-005
- **Plan**: Move 4 — Merge Orchestration section
- **Depends on**: WP07 (merge workspace and state)

## Subtasks & Detailed Guidance

### Subtask T039 – Create merge/engine.py

- **Purpose**: The main merge orchestrator.
- **Steps**:
  1. Create `src/specify_cli/merge/engine.py`
  2. Implement `execute_merge(context: MissionContext | None, feature_slug: str, repo_root: Path, strategy: str = "merge", push: bool = False, dry_run: bool = False) -> MergeResult`:
     - Acquire merge lock
     - Run preflight
     - Create/reuse merge workspace
     - Checkout target branch in workspace, pull --ff-only
     - Compute merge order from dependency graph (use existing `ordering.py`)
     - For each WP in order:
       - If already completed (from resume state): skip
       - Update state: current_wp = this WP
       - Merge WP branch into workspace (`git merge <branch>` or squash/rebase)
       - If conflict: check if auto-resolvable (T040), else pause and persist state
       - Update state: mark WP complete
     - If push: push merged target branch
     - Run reconciliation (T041)
     - Cleanup workspace (unless --keep-workspace)
     - Release lock
  3. Implement `resume_merge(repo_root: Path) -> MergeResult`:
     - Load state from `.kittify/runtime/merge/<mid>/state.json`
     - Continue from current_wp
  4. Implement `abort_merge(repo_root: Path) -> None`:
     - Cleanup workspace, clear state, release lock
  5. Return `MergeResult` dataclass with: success, merged_wps, skipped_wps, conflicts, errors
- **Files**: `src/specify_cli/merge/engine.py` (new, ~200 lines)

### Subtask T040 – Create merge/conflict_resolver.py

- **Purpose**: Auto-resolve conflicts for spec-kitty-owned files.
- **Steps**:
  1. Create `src/specify_cli/merge/conflict_resolver.py`
  2. Implement `resolve_owned_conflicts(workspace_path: Path, conflicted_files: list[str]) -> ResolutionResult`:
     - For `status.events.jsonl`: append-merge (concatenate both sides, dedup by event_id, sort by timestamp)
     - For WP frontmatter (static metadata): take-theirs (latest version wins)
     - For human-authored files: do NOT auto-resolve — return as unresolved
     - **Derived files should NEVER appear as merge conflicts** because they are gitignored. If a derived file somehow conflicts, that indicates a .gitignore misconfiguration — flag it as an error, do not silently resolve.
  3. Implement `classify_conflict(file_path: str) -> ConflictType`:
     - `OWNED_EVENT_LOG` → append-merge
     - `OWNED_METADATA` → take-theirs
     - `HUMAN_AUTHORED` → manual resolution required
     - `UNEXPECTED_DERIVED` → error (should be gitignored, not in merge)
  4. Classification heuristics:
     - `*.events.jsonl` → event log
     - Files under `.kittify/derived/` or `.kittify/runtime/` → UNEXPECTED_DERIVED (flag error)
     - `meta.json`, WP frontmatter → metadata
     - Everything else → human-authored
- **Files**: `src/specify_cli/merge/conflict_resolver.py` (new, ~100 lines)
- **Parallel?**: Yes — can proceed alongside T039

### Subtask T041 – Create merge/reconciliation.py

- **Purpose**: After merge completes, reconcile done-state from actual git ancestry.
- **Steps**:
  1. Create `src/specify_cli/merge/reconciliation.py`
  2. Implement `reconcile_done_state(feature_dir: Path, merged_branches: list[str], target_branch: str, workspace_path: Path) -> list[StatusEvent]`:
     - For each WP branch that was merged:
       - Check if the WP's branch is in the merge ancestry of target branch
       - If yes and WP is not already `done`: emit a `done` event with evidence
       - Evidence includes: merge commit hash, branch name, files touched
     - Return list of emitted events
  3. Use `git branch --merged <target>` in the workspace to determine merged branches
- **Files**: `src/specify_cli/merge/reconciliation.py` (new, ~70 lines)
- **Parallel?**: Yes — can proceed alongside T039

### Subtask T042 – Wire merge CLI to new engine

- **Purpose**: Connect the existing merge CLI commands to the new engine.
- **Steps**:
  1. Update `src/specify_cli/cli/commands/merge.py`
  2. Replace calls to old `execute_merge()` (from deleted executor.py) with new `engine.execute_merge()`
  3. Add/verify CLI flags: `--resume`, `--abort`, `--dry-run`, `--context <token>`, `--push`, `--strategy`
  4. Add `--keep-workspace` flag for debugging
  5. Display merge progress using rich (WP-by-WP status)
- **Files**: `src/specify_cli/cli/commands/merge.py` (modify, ~30 lines changed)

### Subtask T043 – Tests for merge orchestration

- **Purpose**: Verify resume, conflict resolution, and reconciliation.
- **Steps**:
  1. Test full merge: 3 WPs merged in order, state progresses correctly
  2. Test resume: interrupt after WP01, resume from WP02
  3. Test conflict auto-resolution: event log append-merge, derived file regeneration
  4. Test unresolvable conflict: human-authored file conflict pauses merge
  5. Test reconciliation: done events emitted for merged WPs
  6. Test determinism: same result from different main repo checkout states
  7. Test abort: cleanup workspace, clear state
- **Files**: `tests/specify_cli/merge/test_engine.py` (new, ~200 lines)
- **Parallel?**: Yes

## Risks & Mitigations

- **Event log append-merge correctness**: Dedup by event_id + sort by timestamp must be deterministic. Test with overlapping events.
- **Rebase strategy**: More complex than merge. Defer to future work — only support merge and squash initially.

## Review Guidance

- Verify main repo checkout is never changed during merge
- Verify resume skips completed WPs
- Verify conflict resolver correctly classifies file types
- Verify reconciliation emits accurate done events

## Activity Log

- 2026-03-27T17:23:39Z – system – lane=planned – Prompt created.
- 2026-03-27T19:57:39Z – coordinator – shell_pid=9348 – lane=doing – Assigned agent via workflow command
- 2026-03-27T20:06:51Z – coordinator – shell_pid=9348 – lane=for_review – Merge engine v2 complete with resume, conflict resolution, and post-merge reconciliation
