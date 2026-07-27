# Research: Runtime Recovery And Audit Safety

**Mission**: 067-runtime-recovery-and-audit-safety
**Date**: 2026-04-06
**Method**: Codebase exploration and validation against controller brief claims

## Research Summary

All claims from the controller brief were validated against the current codebase at commit 1b01760e. Several additional findings emerged that refine the implementation plan.

---

## R1: Merge Subsystem State

### Decision: Extend existing MergeState, fix lifecycle bugs
### Rationale: The dataclass and persistence infrastructure exist and are well-typed; the bugs are in call-site usage, not in the data model.

**Validated findings**:

- `MergeState` at `src/specify_cli/merge/state.py:66-121` — dataclass with `completed_wps`, `current_wp`, `remaining_wps` (property), `mission_id`, `strategy`, `workspace_path`, `started_at`, `updated_at`
- State persistence at `.kittify/runtime/merge/<mission_id>/state.json` via `get_state_path()`
- `clear_state()` at `state.py:208-234` — **DEAD CODE**: defined and exported but never called anywhere in the codebase
- `_run_lane_based_merge()` at `cli/commands/merge.py:237-444` — resume/abort explicitly disabled (lines 359-361: returns error "removed with legacy merge engine")
- `_mark_wp_merged_done()` at `cli/commands/merge.py:28-117` — two-step transition (for_review→approved, approved→done). Idempotent via lane-state check: early return if already `done`. No explicit event_id dedup guard, but safe in practice because lane detection prevents re-entry
- `cleanup_merge_workspace()` at `merge/workspace.py:68-96` — removes entire runtime directory with `shutil.rmtree()`, which deletes the state file along with the worktree. This is why recovery is impossible after cleanup.
- `_merge_branch_into()` at `lanes/merge.py:197-263` — uses `git update-ref` (line 251), not a normal merge commit

**Additional finding**: The merge flow is: (1) merge each lane branch into mission branch, (2) merge mission branch into target, (3) mark each WP done, (4) optionally push + cleanup. Steps 1-3 are not individually recoverable.

### Alternatives considered:
- Replace MergeState entirely → rejected: existing model is sound, bugs are in lifecycle management
- Add transaction log alongside state → rejected: over-engineering for the failure modes; per-WP state saves are sufficient

---

## R2: Implementation Recovery Surfaces

### Decision: Build `--recover` flag on existing workspace context and orphan detection
### Rationale: Core building blocks exist (find_orphaned_contexts, reuse detection, WorkspaceContext); the gap is a CLI entry point that orchestrates them for recovery.

**Validated findings**:

- `WorkspaceContext` dataclass at `workspace_context.py:36-87` with fields: `wp_id`, `feature_slug`, `worktree_path`, `branch_name`, `base_branch`, `base_commit`, `dependencies`, `created_at`, `created_by`, `vcs_backend`
- Context files at `.kittify/workspaces/{mission_slug}-{lane_id}.json` (confirmed 14 active files in repo)
- `find_orphaned_contexts()` at `workspace_context.py:345-362` — detects contexts where `worktree_path` doesn't exist on disk
- Reuse detection at `implement_support.py:76-81` — checks `.git` marker + `_has_commits_beyond_base()`
- Worktree creation via `git worktree add -b <branch> <path> <base>` at `worktree_allocator.py:137-153` — fails if branch already exists
- Branch existence check at `worktree_allocator.py:113-121` — uses `git rev-parse --verify refs/heads/<branch>`

**Circular dependency confirmed**: `implement` → needs worktree → `git worktree add -b` at `worktree_allocator.py:137-153` → needs branch to NOT exist → branch exists from crashed run. The specific line that must gain a recovery code path is `worktree_allocator.py:143`: `["git", "worktree", "add", "-b", branch, str(worktree_path), base_branch]`. Recovery must use `git worktree add <path> <existing-branch>` (without `-b`) when the branch already exists.

**Runtime run index**: `.kittify/runtime/feature-runs.json` at `next/runtime_bridge.py:57-77` — maps features to run IDs. Not directly needed for basic recovery but useful for runtime-engine reconciliation.

### Alternatives considered:
- New top-level `spec-kitty recover` command → possible but `implement --recover` is more discoverable in the context where the error occurs
- Automatic recovery on `implement` re-entry → risky: auto-recovery could mask real problems. Explicit `--recover` flag is safer.

---

## R3: Shim System Architecture

### Decision: Rewrite shim generator to emit direct commands; delete shim runtime
### Rationale: The shim runtime is pure overhead — it resolves context then returns it. Direct commands skip this indirection entirely.

**Validated findings**:

- `ActionName` at `execution_context.py:21-28` — 6 values: `tasks`, `tasks_outline`, `tasks_packages`, `tasks_finalize`, `implement`, `review`. **`accept` is missing**.
- Shim registry at `shims/registry.py:24-43` — 16 consumer skills: 9 prompt-driven, 7 CLI-driven
- `generate_shim_content()` at `shims/generator.py:53-77` — emits `spec-kitty agent shim <cmd> --agent <name> --raw-args "<args>"` markdown
- `shim_dispatch()` at `shims/entrypoints.py:86-149` — parses raw_args, calls `resolve_or_load()`, returns `MissionContext`. For prompt-driven commands: returns `None` (no-op).
- CLI shim at `cli/commands/shim.py` — 9 subcommands registered (missing: `dashboard`, `tasks-finalize`)
- `rewrite_agent_shims()` at `migration/rewrite_shims.py:149-252` — regenerates 7 CLI shims + 9 prompt templates across all configured agents

**Key insight**: `accept` is feature-level (`cli/commands/accept.py:118-131`), not WP-level. It takes `--mission` not `--wp-id`. Adding it to `ActionName` (WP-scoped resolver) is backward compat convenience. The real fix is direct command generation.

**Shim CLI registration**: `cli/commands/agent/__init__.py:24` — `app.add_typer(shim_module.app, name="shim")`

### Alternatives considered:
- Keep shim runtime but fix accept → rejected: the shim adds no value; removing it simplifies the architecture
- Gradual deprecation → rejected: clean cut is safer than maintaining two dispatch paths

---

## R4: Progress Computation

### Decision: Wire existing compute_weighted_progress() to all broken callsites
### Rationale: The correct implementation exists and is tested. This is a wiring fix, not a design task.

**Validated findings**:

- `compute_weighted_progress()` at `status/progress.py:81-162` — takes `StatusSnapshot`, returns `ProgressResult` with `percentage`, `done_count`, `total_count`, `per_lane_counts`, `per_wp`
- Default lane weights: `planned=0.0, claimed=0.05, in_progress=0.3, for_review=0.6, approved=0.8, done=1.0, blocked=0.0, canceled=0.0`
- Tests at `tests/specify_cli/status/test_progress.py` — `test_all_in_progress_is_30_percent`, `test_mixed_lanes_weighted_correctly`, `test_approved_lane_weight_is_80_percent`

**Broken callsites (7 confirmed + 1 edge case)**:

| # | File | Line | Formula | Impact |
|---|------|------|---------|--------|
| 1 | `agent_utils/status.py` | 138 | `done_count / total * 100` | Status board output |
| 2 | `cli/commands/agent/tasks.py` | 2582 | `lane_counts["done"] / len(wps) * 100` | JSON API output |
| 3 | `cli/commands/agent/tasks.py` | 2634 | `done_count / total * 100` | Display output |
| 4 | `dashboard/static/dashboard/dashboard.js` | 319 | `completed / total * 100` (JS) | Dashboard overview |
| 5 | `dashboard/static/dashboard/dashboard.js` | 401 | `completed / total * 100` (JS) | Dashboard kanban |
| 6 | `dashboard/scanner.py` | 351-390 | Emits raw lane counts only | Data source for dashboard |
| 7 | `cli/commands/next_cmd.py` | 199 | `done / total * 100` | Next command progress display |
| 8* | `merge/state.py` | 102 | `completed_wps / wp_order * 100` | Merge progress (edge case) |

*Callsite 8 is merge-specific: tracks binary completion of merge steps, not lane-weighted progress. May keep as-is since merge tracks "which WPs have been merged" not "how far along is the mission."

### Alternatives considered:
- New progress utility function → rejected: `compute_weighted_progress()` already IS the utility
- Different lane weights → deferred to planning/configuration: current weights (0/0.05/0.3/0.6/0.8/1.0) are reasonable defaults

---

## R5: WP Scope and Ownership

### Decision: Add optional `scope` field to WP frontmatter; relax validation when `scope: codebase-wide`
### Rationale: The ownership validation infrastructure exists and is sound for narrow WPs. Audit WPs need an explicit opt-out rather than a hack.

**Validated findings**:

- `ExecutionMode` enum at `ownership/models.py:14-23` — `CODE_CHANGE` and `PLANNING_ARTIFACT` only
- WP frontmatter schema at `frontmatter.py:41-58` — `WP_FIELD_ORDER` has 16 fields, no `scope`
- Ownership validation at `ownership/validation.py:81-200`:
  - `validate_no_overlap()` — enforces no two WPs own the same files
  - `validate_authoritative_surface()` — ensures authoritative_surface is prefix of owned_files
  - `validate_execution_mode_consistency()` — warns if execution_mode doesn't match file paths
- `apply_text_replacements()` at `upgrade/skill_update.py:117-142` — blind `str.replace()`, no context filter
- No occurrence classification infrastructure exists
- Policy audit at `policy/audit.py` — feature-level only (no `work_package_id` field in `PolicyAuditEvent`)

### Alternatives considered:
- New `ExecutionMode.AUDIT` value → rejected: `scope` is orthogonal to execution mode (an audit WP can be code_change or planning_artifact)
- Global audit flag on the mission → rejected: per-WP scope is more flexible; some WPs in a mission need narrow scope while others need broad scope
