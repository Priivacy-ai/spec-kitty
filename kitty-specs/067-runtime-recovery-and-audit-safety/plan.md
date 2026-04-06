# Implementation Plan: Runtime Recovery And Audit Safety

**Branch**: `main` | **Date**: 2026-04-06 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `kitty-specs/067-runtime-recovery-and-audit-safety/spec.md`
**Mission**: 067-runtime-recovery-and-audit-safety

## Summary

This mission stabilizes 5 areas of the Spec Kitty runtime: merge recovery after interruption (#416), implementation crash recovery (#415), removal of the generic agent shim runtime in favor of direct canonical commands (#412, #414), audit-mode WPs with bulk-edit safety (#442, #393), and truthful weighted progress reporting (#447, #443). The implementation extends existing infrastructure (MergeState, workspace context, progress.py) rather than rebuilding.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: typer (CLI), rich (console output), ruamel.yaml (frontmatter), subprocess (git operations)
**Storage**: Filesystem only (YAML frontmatter, JSONL event logs, JSON state files)
**Testing**: pytest with 90%+ coverage for new code; mypy --strict must pass
**Target Platform**: CLI tool (macOS, Linux)
**Project Type**: Single Python package (`src/specify_cli/`)
**Constraints**: No database; all state on filesystem; must work with 12 AI agent formats

## Charter Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Gate | Status | Notes |
|------|--------|-------|
| typer for CLI | PASS | All new commands use typer |
| rich for console output | PASS | Status/progress displays use rich |
| ruamel.yaml for YAML | PASS | Frontmatter parsing uses ruamel.yaml |
| pytest with 90%+ coverage | PASS | All WPs include test requirements |
| mypy --strict | PASS | All new code typed |
| Integration tests for CLI | PASS | WP01, WP02, WP03 all need CLI integration tests |

No charter violations.

## Project Structure

### Documentation (this feature)

```
kitty-specs/067-runtime-recovery-and-audit-safety/
├── spec.md              # Specification (complete)
├── plan.md              # This file
├── research.md          # Phase 0: validated codebase findings
├── data-model.md        # Phase 1: state model changes
├── quickstart.md        # Phase 1: implementation getting-started
└── tasks/               # Phase 2: WP files (created by /spec-kitty.tasks)
```

### Source Code (repository root)

```
src/specify_cli/
├── merge/
│   ├── state.py             # WP01: extend MergeState for recovery
│   └── workspace.py         # WP01: fix cleanup_merge_workspace() timing
├── cli/commands/
│   ├── merge.py             # WP01: make _run_lane_based_merge() resumable
│   ├── implement.py         # WP02: add --recover flag
│   ├── accept.py            # WP03: already exists (feature-level command)
│   ├── shim.py              # WP03: DELETE this file
│   └── agent/tasks.py       # WP05: fix broken progress callsite
├── lanes/
│   ├── implement_support.py # WP02: extend reuse detection for recovery
│   └── worktree_allocator.py # WP02: handle branch-already-exists case
├── shims/
│   ├── generator.py         # WP03: rewrite generate_shim_content()
│   ├── registry.py          # WP03: reference only (no changes)
│   ├── entrypoints.py       # WP03: DELETE this file
│   └── ...
├── migration/
│   └── rewrite_shims.py     # WP03: update rewrite_agent_shims() for direct commands
├── core/
│   └── execution_context.py # WP03: add "accept" to ActionName (backward compat)
├── workspace_context.py     # WP02: build on find_orphaned_contexts()
├── ownership/
│   ├── models.py            # WP04a: add scope field
│   └── validation.py        # WP04a: relax validation for codebase-wide scope
├── frontmatter.py           # WP04a: parse scope field
├── upgrade/
│   └── skill_update.py      # WP04b: reference for apply_text_replacements()
├── status/
│   └── progress.py          # WP05: already correct (wire to callsites)
├── agent_utils/
│   └── status.py            # WP05: fix broken progress callsite
├── dashboard/
│   ├── scanner.py           # WP05: pre-compute weighted progress
│   └── static/dashboard/
│       └── dashboard.js     # WP05: use pre-computed weighted_percentage
└── ...

tests/
├── specify_cli/
│   ├── merge/               # WP01: merge recovery tests
│   ├── test_workspace_context.py # WP02: recovery tests
│   ├── shims/               # WP03: direct command tests
│   ├── ownership/           # WP04a: audit scope tests
│   └── status/
│       └── test_progress.py # WP05: callsite integration tests (existing tests pass)
└── ...
```

## Work Packages (6 WPs — WP04 split into WP04a + WP04b)

### Execution Order

```
WP05 (progress, ~1 day)
  ↓
WP03 (shim removal, ~2 days) ──┐
WP01 (merge recovery, ~2 days) ┤ parallel
                                │
WP02 (impl recovery, ~2 days) ←┘ after WP01
  ↓
WP04a (audit scope, ~1 day)
WP04b (occurrence classification, ~1 day)
```

### WP05: Canonical Progress Reporting

**Issues**: #447 (primary), #443 (consolidated)
**Risk**: Low — correct module already exists and is tested
**Scope**: Wire `compute_weighted_progress()` to all broken callsites

**Validated broken callsites** (7 total, not 4):
1. `src/specify_cli/agent_utils/status.py:138` — `done_count / total * 100`
2. `src/specify_cli/cli/commands/agent/tasks.py:2582` — `lane_counts["done"] / len(work_packages) * 100`
3. `src/specify_cli/cli/commands/agent/tasks.py:2634` — `done_count / total * 100`
4. `src/specify_cli/dashboard/static/dashboard/dashboard.js:319` — `completed / total * 100`
5. `src/specify_cli/dashboard/static/dashboard/dashboard.js:401` — `completed / total * 100`
6. `src/specify_cli/dashboard/scanner.py:351-390` — emits raw lane counts, no weighting
7. `src/specify_cli/cli/commands/next_cmd.py:199` — `done / total * 100`

**Also noted** (lower priority):
8. `src/specify_cli/merge/state.py:102` — `completed_wps / wp_order * 100` (merge-specific, may keep as-is since merge tracks binary completion)

**Correct module**: `src/specify_cli/status/progress.py:81-162`
- `compute_weighted_progress(snapshot)` — takes `StatusSnapshot`, returns `ProgressResult`
- Lane weights: planned=0.0, claimed=0.05, in_progress=0.3, for_review=0.6, approved=0.8, done=1.0
- Already has tests at `tests/specify_cli/status/test_progress.py`

**Implementation approach**:
1. Python callsites (1-3): Import and call `compute_weighted_progress()` with materialized snapshot from `materialize(feature_dir)`
2. Scanner (6): Pre-compute `weighted_percentage` field in the JSON payload emitted by `scan_all_features()` by materializing the snapshot and calling `compute_weighted_progress()`
3. Dashboard JS (4-5): Read pre-computed `weighted_percentage` from scanner payload instead of computing from raw counts
4. **Callsite 7 (next_cmd.py:199) — different wiring pattern**: This callsite reads `decision.progress` which comes from the runtime engine (`next/decision.py:225-262`), not from `materialize()`. The implementor must either (a) have the runtime engine pre-compute weighted progress by calling `compute_weighted_progress()` when building the progress dict, or (b) materialize the snapshot at display time in `next_cmd.py`. Option (a) is cleaner — update `_compute_wp_progress()` in `next/decision.py` to return a `weighted_percentage` field alongside the raw counts.
5. Close #443 with cross-reference to #447

### WP03: Canonical Execution Surface Cleanup

**Issues**: #412 (shim removal), #414 (accept registration)
**Risk**: Medium — touches all 12 agent command files; migration must be correct
**Dependencies**: None (independent of other WPs)

**Current state validated**:
- `ActionName` at `src/specify_cli/core/execution_context.py:21-28` has 6 actions — `accept` missing
- Shim registry at `src/specify_cli/shims/registry.py` classifies 16 skills: 9 prompt-driven, 7 CLI-driven
- `generate_shim_content()` at `src/specify_cli/shims/generator.py:53-77` emits `spec-kitty agent shim <cmd>` dispatch
- `shim_dispatch()` at `src/specify_cli/shims/entrypoints.py:86-149` does context resolution then returns
- `rewrite_agent_shims()` at `src/specify_cli/migration/rewrite_shims.py:149-252` exists and regenerates all agent files

**Key finding**: `accept` is feature-level (not WP-level). The `ActionName` resolver is WP-scoped, so adding `accept` there is a backward-compat convenience, not the primary fix. The primary fix is making generated shim files call canonical commands directly.

**Implementation approach**:
1. Rewrite `generate_shim_content()` to emit direct canonical CLI calls per command:
   - `implement` → `spec-kitty agent action implement {ARGS} --agent {AGENT}`
   - `review` → `spec-kitty agent action review {ARGS} --agent {AGENT}`
   - `accept` → `spec-kitty agent mission accept {ARGS}`
   - `status` → `spec-kitty agent tasks status {ARGS}`
   - `merge` → `spec-kitty merge {ARGS}`
   - `dashboard` → `spec-kitty dashboard {ARGS}`
   - `tasks-finalize` → `spec-kitty agent mission finalize-tasks {ARGS}`
2. Add `"accept"` to `ActionName` Literal in `execution_context.py` for backward compatibility
3. Delete shim runtime files: `src/specify_cli/shims/entrypoints.py`, `src/specify_cli/shims/models.py`, `src/specify_cli/cli/commands/shim.py`. Note: `shims/models.py` exports `AgentShimConfig` and `ShimTemplate` but these are only re-exported through `shims/__init__.py` — no other module imports them. Clean up `__init__.py` exports after deletion.
4. Remove `agent shim` CLI registration from `src/specify_cli/cli/commands/agent/__init__.py`
5. Write migration to regenerate all agent command files using updated `rewrite_agent_shims()`
6. Test: verify `.claude/commands/`, `.codex/prompts/`, `.opencode/command/` contain direct commands (C-003)

### WP01: Merge Interruption and Recovery

**Issue**: #416
**Risk**: Medium-High — merge state is critical; concurrent agent scenarios need care
**Dependencies**: None (independent of other WPs)

**Current state validated**:
- `MergeState` at `src/specify_cli/merge/state.py:66-121` — has `completed_wps`, `current_wp`, `remaining_wps` (property)
- State persisted at `.kittify/runtime/merge/<mission_id>/state.json`
- `clear_state()` at `state.py:208-234` — **DEAD CODE** (defined but never called)
- `_run_lane_based_merge()` at `cli/commands/merge.py:237-444` — resume/abort **explicitly disabled** with error message
- `_mark_wp_merged_done()` at `cli/commands/merge.py:28-117` — idempotent via lane-state check (early return if already `done`) but no event_id dedup guard
- `cleanup_merge_workspace()` at `merge/workspace.py:68-96` — removes entire runtime directory (including state file!) after cleanup

**Root causes**:
1. `_run_lane_based_merge()` does not consult existing `MergeState` on re-entry — starts fresh every time
2. `cleanup_merge_workspace()` removes the state file as part of directory cleanup, so recovery state is lost
3. Status events are committed as a batch at the end, not per-WP
4. Resume/abort CLI paths are explicitly disabled

**Implementation approach**:
1. **Wire MergeState into the merge loop** (scope note: `_run_lane_based_merge()` currently has ZERO MergeState usage — no create, no save, no load. This is not "extending" state; it is wiring it into a function that ignores it):
   a. At function entry: create or load MergeState. If existing state has `completed_wps`, skip those WPs.
   b. Before each WP merge: set `current_wp` and save state.
   c. After each WP merge + done-recording: add to `completed_wps` and save state.
   d. After ALL WPs merged + cleanup complete: call `clear_state()`.
2. **State file preservation strategy**: `cleanup_merge_workspace()` at `merge/workspace.py:68-96` does `shutil.rmtree()` on the entire runtime directory, which destroys `state.json`. **Decision: restructure cleanup to exempt state.json** — the function should remove the worktree and temporary files but leave `state.json` intact. `clear_state()` handles state file removal as a separate explicit step after confirmed full completion. Implementation: replace `shutil.rmtree(runtime_dir)` with selective deletion that skips `_STATE_FILE`.
3. **Per-WP commit**: After each WP's merge + done-recording succeeds, commit status files immediately. Do not batch at end.
4. **Event dedup guard**: In `_mark_wp_merged_done()`, check event log for existing done transition before emitting (FR-003).
5. **macOS FSEvents delay**: Add configurable `inter_worktree_removal_delay` (default 2s on Darwin, 0 elsewhere) in cleanup loop.
6. **Tolerate missing worktrees**: On retry, skip worktree removal for already-removed worktrees. Skip branch deletion for already-deleted branches.
7. **Re-enable resume path**: Replace the "removed with legacy merge engine" error (merge.py:359-361) with actual resume logic that loads existing MergeState.

### WP02: Implementation Crash Recovery

**Issue**: #415
**Risk**: Medium — workspace state is spread across 4 surfaces
**Dependencies**: Informed by WP01 patterns (schedule after WP01)

**Current state validated**:
- Workspace context: `.kittify/workspaces/{mission_slug}-{lane_id}.json` — `WorkspaceContext` dataclass
- WP frontmatter: `base_branch`, `base_commit`, `shell_pid` fields present
- `find_orphaned_contexts()` at `workspace_context.py:345-362` — detects stale contexts where worktree path doesn't exist
- Reuse detection at `implement_support.py:76-81` — checks `.git` marker + commits beyond base
- Worktree creation uses `git worktree add -b` which **fails if branch already exists** — no recovery logic

**The circular dependency**: `implement` needs a worktree → `git worktree add -b` needs branch to NOT exist → branch exists from pre-crash run.

**Implementation approach**:
1. **New CLI command**: `spec-kitty implement --recover` (or `spec-kitty recover`, design decision for implementation)
2. **Recovery scan**:
   a. List all branches matching `kitty/mission-{slug}*` pattern
   b. Cross-reference with workspace context files in `.kittify/workspaces/`
   c. Cross-reference with status event log for lane state
3. **Worktree reconciliation**:
   a. If branch exists but worktree is missing: `git worktree add <path> <existing-branch>` (no `-b` flag)
   b. If worktree exists but context is missing: recreate context from branch/worktree state
   c. If both exist but context is stale: refresh context fields (wp_id, dependencies)
4. **Status reconciliation**: Emit any missing lane transitions (e.g., if branch exists with commits but status is still `planned`, emit `planned → claimed → in_progress`)
5. **Build on existing infrastructure**: Use `find_orphaned_contexts()` for detection, `save_context()` for reconciliation, `emit_status_transition()` for status repair

### WP04a: Audit-Mode WP Scope Relaxation

**Issues**: #442 (codebase-wide audit WPs)
**Risk**: Low-Medium — data model extension + validation relaxation
**Dependencies**: None

**Current state validated**:
- `ExecutionMode` enum at `ownership/models.py:14-23` has `CODE_CHANGE` and `PLANNING_ARTIFACT` — no audit mode
- WP frontmatter schema at `frontmatter.py:41-58` has no `scope` field
- Ownership validation at `ownership/validation.py:81-200` enforces no-overlap and authoritative-surface rules
- Policy audit at `policy/audit.py` is feature-level only

**Implementation approach**:
1. **Add `scope` field to WP frontmatter**: Optional `scope: codebase-wide` (default: per-WP narrow). Add to `WP_FIELD_ORDER` in `frontmatter.py`.
2. **Relax ownership validation**: When `scope: codebase-wide`, skip overlap checks and authoritative-surface enforcement in `validation.py`. Allow `owned_files: ["**/*"]` or similar.
3. **Audit template targets**: In mission command templates, explicitly list directories for audit coverage:
   - `src/**/command-templates/` (9 template files per mission)
   - Agent prompt directories (`.claude/commands/`, `.codex/prompts/`, etc.)
   - `docs/` directory
4. **Validation at finalize**: When a mission contains rename/cutover WPs alongside audit WPs, the finalize step should validate that audit targets cover template/doc directories.

### WP04b: Occurrence Classification for Bulk Edits

**Issues**: #393 (no guardrail for string occurrence categories)
**Risk**: Low — template/workflow change, not code infrastructure
**Dependencies**: None (can run parallel with WP04a)

**Current state validated**:
- `apply_text_replacements()` at `upgrade/skill_update.py:117-142` does blind `str.replace()` with no context filtering
- No occurrence classification infrastructure exists in the codebase

**Implementation approach**:
1. **Classification template step**: Add a structured step to cutover/rename WP templates that requires the agent to produce an occurrence classification report before making edits:

   | Category | Pattern Example | Action |
   |----------|----------------|--------|
   | import_path | `from X.module import` | RENAME |
   | class_name | `class OldName` | RENAME |
   | file_path | `.kittify/old_name/` | PRESERVE or RENAME |
   | dict_key | `"old_key"` | RENAME |
   | log_message | `"Processing old_name"` | UPDATE |
   | comment | `# old_name does X` | UPDATE |

2. **Post-edit verification step**: After bulk edits, require a grep-based verification that:
   a. No unintended occurrences of the old term remain
   b. Remaining occurrences are classified as intentional preservations
3. **Optional `context_filter` parameter**: Add to `apply_text_replacements()` so programmatic bulk edits can skip specified file patterns

## Risks and Mitigations

| Risk | WP | Mitigation |
|------|-----|-----------|
| Merge retry produces duplicate events | WP01 | Event dedup guard: check event log before emitting done transitions |
| Concurrent agents see stale MergeState | WP01 | File-lock or atomic rename for state writes |
| Recovery incorrectly infers lane state | WP02 | Conservative: only emit transitions that are provably needed based on branch commits |
| Shim removal breaks agent command files | WP03 | Test 3+ agents (claude, codex, opencode) per C-003 |
| Audit scope creates overly broad edits | WP04a | Audit scope is validation relaxation only; actual edits still per-file |
| Progress formula change breaks SaaS sync | WP05 | Pre-compute weighted_percentage in scanner; legacy `done/total` fields still emitted alongside |

## Post-Phase-1 Charter Re-Check

| Gate | Status | Notes |
|------|--------|-------|
| typer for CLI | PASS | WP02 recovery command uses typer |
| rich for console output | PASS | Recovery/progress displays use rich |
| pytest with 90%+ coverage | PASS | Each WP has explicit test requirements |
| mypy --strict | PASS | All new code typed |
| Integration tests for CLI | PASS | WP01 merge retry, WP02 recover, WP03 shim migration all need integration tests |
| No charter violations | PASS | No new dependencies introduced |
