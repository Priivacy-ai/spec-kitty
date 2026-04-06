# Data Model: Runtime Recovery And Audit Safety

**Mission**: 067-runtime-recovery-and-audit-safety
**Date**: 2026-04-06

## State Changes by WP

### WP01: MergeState Lifecycle

**Existing model** (`src/specify_cli/merge/state.py:66-121`):

```
MergeState
├── mission_id: str              # Per-mission scoping key
├── mission_slug: str            # Display name
├── target_branch: str           # Target for merge
├── wp_order: list[str]          # Ordered WP IDs to merge
├── completed_wps: list[str]     # WPs successfully merged
├── current_wp: str | None       # WP currently being merged
├── has_pending_conflicts: bool   # Conflict state
├── strategy: str                # merge | squash | rebase
├── workspace_path: str | None   # Absolute worktree path
├── started_at: str              # ISO timestamp
└── updated_at: str              # ISO timestamp
Properties:
├── remaining_wps → list[str]    # wp_order minus completed_wps
└── progress_percent → float     # completed / total * 100
```

**Changes required**:
- No field additions needed — existing fields are sufficient for recovery
- `progress_percent` property: consider wiring to `compute_weighted_progress()` (WP05 synergy)

**Lifecycle changes** (behavior, not schema):

| Current | New |
|---------|-----|
| State created at merge start | Same |
| State never consulted on re-entry | **State loaded on re-entry; completed_wps skipped** |
| clear_state() defined but never called | **clear_state() called after ALL WPs merged + cleanup complete** |
| State file destroyed by cleanup_merge_workspace() | **State file preserved until explicit clear_state() after success** |
| Status events batched at end | **Status events committed per-WP immediately after merge** |
| Resume path disabled (error) | **Resume path re-enabled using existing MergeState** |

**State file path**: `.kittify/runtime/merge/<mission_id>/state.json` (no change)

---

### WP02: No Schema Changes

Recovery operates on existing data surfaces:
- Reads: workspace context files, git branches, status event log, WP frontmatter
- Writes: workspace context files (reconciliation), status events (gap-filling)

No new data models introduced. The recovery command is a stateless scan + reconciliation operation.

---

### WP03: ActionName Extension

**Existing** (`src/specify_cli/core/execution_context.py:21-28`):
```python
ActionName = Literal["tasks", "tasks_outline", "tasks_packages", "tasks_finalize", "implement", "review"]
```

**New**:
```python
ActionName = Literal["tasks", "tasks_outline", "tasks_packages", "tasks_finalize", "implement", "review", "accept"]
```

**Shim content model change**:

| Current | New |
|---------|-----|
| `spec-kitty agent shim <cmd> --agent <name> --raw-args "<args>"` | Direct canonical CLI command per command type |

Example — `implement` shim content:
```
Current: `spec-kitty agent shim implement --agent claude --raw-args "$ARGUMENTS"`
New:     `spec-kitty agent action implement $ARGUMENTS --agent claude`
```

**Files deleted**:
- `src/specify_cli/shims/entrypoints.py`
- `src/specify_cli/cli/commands/shim.py`

**CLI registration removed**:
- `agent shim` subcommand group in `cli/commands/agent/__init__.py`

---

### WP04a: WP Frontmatter Scope Field

**New field added to WP frontmatter**:

```yaml
scope: codebase-wide  # Optional. Default: omitted (implies narrow/per-WP)
```

Added to `WP_FIELD_ORDER` in `src/specify_cli/frontmatter.py`.

**Critical: this field MUST be optional with an implicit default of narrow when omitted.** It must NOT be added to any required-field validation. Every existing WP in every project omits this field — making it required would break all projects. The validation code in `frontmatter.py:283-296` checks required fields; `scope` must not appear in that list. When `scope` is absent from frontmatter, all ownership validation behaves exactly as it does today (narrow per-WP scope).

**Validation behavior change** (`src/specify_cli/ownership/validation.py`):

| Validation | scope: omitted (narrow) | scope: codebase-wide |
|-----------|------------------------|---------------------|
| `validate_no_overlap()` | Enforced | **Skipped** |
| `validate_authoritative_surface()` | Enforced | **Skipped** |
| `validate_execution_mode_consistency()` | Enforced | **Relaxed** (any mode + any paths) |

**Audit template targets** (new constants or configuration):

```
AUDIT_TARGETS = [
    "src/**/command-templates/",
    ".claude/commands/",
    ".codex/prompts/",
    ".opencode/command/",
    # ... (all 12 agent directories)
    "docs/",
]
```

---

### WP04b: No Schema Changes

Occurrence classification is a workflow/template concern:
- Template step produces structured report (categories × occurrences)
- Post-edit verification step produces grep results
- No persistent data model; output is in WP implementation artifacts

Optional code change: `apply_text_replacements()` gains optional `context_filter: Callable[[Path], bool] | None = None` parameter for programmatic bulk edits.

---

### WP05: Scanner Payload Extension

**Existing scanner output** (`dashboard/scanner.py`):
```json
{
  "kanban_stats": {
    "total": 5,
    "planned": 0,
    "doing": 1,
    "for_review": 3,
    "approved": 0,
    "done": 1
  }
}
```

**New scanner output**:
```json
{
  "kanban_stats": {
    "total": 5,
    "planned": 0,
    "doing": 1,
    "for_review": 3,
    "approved": 0,
    "done": 1,
    "weighted_percentage": 58.0
  }
}
```

`weighted_percentage` is pre-computed by calling `compute_weighted_progress()` in the scanner. Dashboard JS reads this field directly instead of computing `done/total`.

## Entity Relationship Summary

```
MergeState ──────── persisted at ──────── .kittify/runtime/merge/<id>/state.json
     │
     ├── references → WP IDs (wp_order, completed_wps)
     ├── references → target_branch
     └── lifecycle: create → update per-WP → clear after success

WorkspaceContext ── persisted at ──────── .kittify/workspaces/<slug>-<lane>.json
     │
     ├── references → WP ID, branch, worktree path
     └── recovery: scan branches → match contexts → reconcile

StatusEvent ─────── persisted at ──────── kitty-specs/<mission>/status.events.jsonl
     │
     ├── references → WP ID, lanes (from/to)
     ├── progress: reduce events → snapshot → compute_weighted_progress()
     └── dedup: event_id uniqueness

WP Frontmatter ──── persisted at ──────── kitty-specs/<mission>/tasks/WP##.md
     │
     ├── new field: scope (codebase-wide | omitted)
     └── audit mode: relaxes ownership validation
```
