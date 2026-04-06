# Tasks: Runtime Recovery And Audit Safety

**Mission**: 067-runtime-recovery-and-audit-safety
**Date**: 2026-04-06
**Target branch**: main
**Total**: 32 subtasks across 6 work packages

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|-----|----------|
| T001 | Wire MergeState lifecycle into `_run_lane_based_merge()` | WP01 | |
| T002 | Restructure state file preservation in cleanup | WP01 | |
| T003 | Add event_id dedup guard in `_mark_wp_merged_done()` | WP01 | [P] |
| T004 | Re-enable resume/abort CLI path | WP01 | |
| T005 | Add retry tolerance (FSEvents delay, missing worktrees/branches) | WP01 | [P] |
| T006 | Write tests for merge recovery | WP01 | |
| T007 | Build recovery scan for orphaned branches and workspace contexts | WP02 | |
| T008 | Implement worktree reconciliation from surviving branches | WP02 | |
| T009 | Implement status reconciliation for missing lane transitions | WP02 | [P] |
| T010 | Add `--recover` flag to implement CLI command | WP02 | |
| T011 | Write tests for crash recovery scenarios | WP02 | |
| T012 | Rewrite `generate_shim_content()` for direct canonical commands | WP03 | |
| T013 | Add `"accept"` to ActionName Literal | WP03 | [P] |
| T014 | Delete shim runtime files and CLI registration | WP03 | |
| T015 | Update `rewrite_agent_shims()` for new generator output | WP03 | |
| T016 | Write migration to regenerate all agent command files | WP03 | |
| T017 | Write tests verifying direct commands across agent surfaces | WP03 | |
| T018 | Add `scope` field to WP_FIELD_ORDER in frontmatter.py | WP04 | |
| T019 | Relax ownership validation for codebase-wide scope | WP04 | |
| T020 | Define audit template target paths | WP04 | [P] |
| T021 | Add finalize-time validation for template/doc coverage | WP04 | |
| T022 | Write tests for audit scope validation | WP04 | |
| T023 | Create occurrence classification template step | WP05 | |
| T024 | Create post-edit verification template step | WP05 | [P] |
| T025 | Add optional `context_filter` to `apply_text_replacements()` | WP05 | [P] |
| T026 | Write tests for occurrence classification guardrails | WP05 | |
| T027 | Replace broken progress formula in `agent_utils/status.py` | WP06 | [P] |
| T028 | Replace broken progress formulas in `cli/commands/agent/tasks.py` | WP06 | [P] |
| T029 | Update scanner to pre-compute `weighted_percentage` | WP06 | |
| T030 | Update dashboard JS to read pre-computed progress | WP06 | |
| T031 | Update `next_cmd.py` via runtime engine weighted progress | WP06 | |
| T032 | Write tests for weighted progress across surfaces | WP06 | |

## Execution Order and Dependencies

```
WP06 (progress, no deps)  ─────────────────────────┐
WP03 (shim removal, no deps)  ─────────────────────┤ parallel
WP01 (merge recovery, no deps)  ───────────────────┤
                                                    │
WP02 (impl recovery, depends: WP01) ←──────────────┤
                                                    │
WP04 (audit scope, no deps)  ──────────────────────┤ parallel
WP05 (occurrence classification, no deps) ──────────┘
```

Recommended start: WP06 (lowest risk, highest operator impact, ~1 day).

## Work Packages

### WP01: Merge Interruption and Recovery

**File**: [tasks/WP01-merge-interruption-recovery.md](tasks/WP01-merge-interruption-recovery.md)
**Issues**: [#416](https://github.com/Priivacy-ai/spec-kitty/issues/416)
**Priority**: P1
**Dependencies**: None
**Estimated prompt size**: ~450 lines

- [ ] T001 Wire MergeState lifecycle into `_run_lane_based_merge()` — create/load at entry, save after each WP, skip completed (WP01)
- [ ] T002 Restructure state file preservation — exempt state.json from `cleanup_merge_workspace()` rmtree, `clear_state()` only after full success (WP01)
- [ ] T003 Add event_id dedup guard in `_mark_wp_merged_done()` before emitting done transitions (WP01)
- [ ] T004 Re-enable resume/abort CLI path — replace disabled error at merge.py:359-361 with MergeState-based logic (WP01)
- [ ] T005 Add retry tolerance — macOS FSEvents inter-worktree-removal delay, skip missing worktrees/branches (WP01)
- [ ] T006 Write tests for interrupted merge/retry recovery behavior (WP01)

### WP02: Implementation Crash Recovery

**File**: [tasks/WP02-implementation-crash-recovery.md](tasks/WP02-implementation-crash-recovery.md)
**Issues**: [#415](https://github.com/Priivacy-ai/spec-kitty/issues/415)
**Priority**: P1
**Dependencies**: WP01
**Estimated prompt size**: ~400 lines

- [ ] T007 Build recovery scan — detect orphaned branches matching mission pattern, cross-reference workspace contexts and status events (WP02)
- [ ] T008 Implement worktree reconciliation — `git worktree add <path> <existing-branch>` without `-b` flag (WP02)
- [ ] T009 Implement status reconciliation — emit missing lane transitions based on branch state (WP02)
- [ ] T010 Add `--recover` flag to implement CLI command with full recovery orchestration (WP02)
- [ ] T011 Write tests for crash recovery scenarios (branch exists, worktree missing, etc.) (WP02)

### WP03: Canonical Execution Surface Cleanup

**File**: [tasks/WP03-canonical-execution-surface-cleanup.md](tasks/WP03-canonical-execution-surface-cleanup.md)
**Issues**: [#412](https://github.com/Priivacy-ai/spec-kitty/issues/412), [#414](https://github.com/Priivacy-ai/spec-kitty/issues/414)
**Priority**: P1
**Dependencies**: None
**Estimated prompt size**: ~500 lines

- [ ] T012 Rewrite `generate_shim_content()` to emit direct canonical CLI commands per command type (WP03)
- [ ] T013 Add `"accept"` to ActionName Literal in execution_context.py for backward compatibility (WP03)
- [ ] T014 Delete shim runtime files: entrypoints.py, models.py, shim.py; remove CLI registration (WP03)
- [ ] T015 Update `rewrite_agent_shims()` in migration/rewrite_shims.py for new generator output (WP03)
- [ ] T016 Write migration to regenerate all existing agent command files across configured agents (WP03)
- [ ] T017 Write tests verifying direct commands in .claude/, .codex/, .opencode/ (C-003) (WP03)

### WP04: Audit-Mode WP Scope Relaxation

**File**: [tasks/WP04-audit-mode-scope-relaxation.md](tasks/WP04-audit-mode-scope-relaxation.md)
**Issues**: [#442](https://github.com/Priivacy-ai/spec-kitty/issues/442)
**Priority**: P2
**Dependencies**: None
**Estimated prompt size**: ~350 lines

- [ ] T018 Add `scope` field to WP_FIELD_ORDER in frontmatter.py — optional, implicit narrow default (WP04)
- [ ] T019 Relax ownership validation (no_overlap, authoritative_surface) for `scope: codebase-wide` WPs (WP04)
- [ ] T020 Define audit template target paths as constants covering all agent dirs + docs/ (WP04)
- [ ] T021 Add finalize-time validation warning when audit WPs don't cover template/doc directories (WP04)
- [ ] T022 Write tests for audit scope validation behavior (narrow vs. codebase-wide) (WP04)

### WP05: Occurrence Classification for Bulk Edits

**File**: [tasks/WP05-occurrence-classification-bulk-edits.md](tasks/WP05-occurrence-classification-bulk-edits.md)
**Issues**: [#393](https://github.com/Priivacy-ai/spec-kitty/issues/393)
**Priority**: P2
**Dependencies**: None
**Estimated prompt size**: ~350 lines

- [ ] T023 Create occurrence classification template step for cutover/rename WP mission templates (WP05)
- [ ] T024 Create post-edit verification template step with grep-based confirmation (WP05)
- [ ] T025 Add optional `context_filter` parameter to `apply_text_replacements()` in skill_update.py (WP05)
- [ ] T026 Write tests for occurrence classification guardrail enforcement (WP05)

### WP06: Canonical Progress Reporting

**File**: [tasks/WP06-canonical-progress-reporting.md](tasks/WP06-canonical-progress-reporting.md)
**Issues**: [#447](https://github.com/Priivacy-ai/spec-kitty/issues/447), [#443](https://github.com/Priivacy-ai/spec-kitty/issues/443)
**Priority**: P1
**Dependencies**: None
**Estimated prompt size**: ~450 lines

- [ ] T027 Replace broken progress formula in `agent_utils/status.py:138` with `compute_weighted_progress()` (WP06)
- [ ] T028 Replace broken progress formulas in `cli/commands/agent/tasks.py:2582,2634` (WP06)
- [ ] T029 Update scanner to pre-compute `weighted_percentage` field in emitted JSON payload (WP06)
- [ ] T030 Update dashboard JS at lines 319 and 401 to read pre-computed `weighted_percentage` (WP06)
- [ ] T031 Update `next_cmd.py:199` — wire runtime engine `_compute_wp_progress()` to return weighted progress (WP06)
- [ ] T032 Write tests for shared weighted-progress calculation across CLI/dashboard/next surfaces (WP06)
