# Data Model: Smarter Feature Merge

This document defines the key entities and their relationships for the enhanced merge command.

## Entities

### MergeState

Persisted state for resumable multi-WP merges. Stored at `.kittify/merge-state.json`.

| Field | Type | Description |
|-------|------|-------------|
| `feature_slug` | string | Feature identifier (e.g., "017-smarter-merge") |
| `target_branch` | string | Branch being merged into (e.g., "main") |
| `wp_order` | string[] | WP IDs in merge order (topologically sorted) |
| `completed_wps` | string[] | WP IDs that have been successfully merged |
| `current_wp` | string \| null | WP currently being merged (null if between WPs) |
| `has_pending_conflicts` | boolean | True if git merge state has unresolved conflicts |
| `strategy` | string | Merge strategy: "merge", "squash", or "rebase" |
| `started_at` | string | ISO 8601 timestamp when merge started |
| `last_updated` | string | ISO 8601 timestamp of last state change |

**Example**:
```json
{
  "feature_slug": "017-smarter-feature-merge",
  "target_branch": "main",
  "wp_order": ["WP01", "WP02", "WP03", "WP04"],
  "completed_wps": ["WP01", "WP02"],
  "current_wp": "WP03",
  "has_pending_conflicts": true,
  "strategy": "merge",
  "started_at": "2025-01-18T10:30:00Z",
  "last_updated": "2025-01-18T10:45:00Z"
}
```

**Lifecycle**:
1. Created when multi-WP merge starts (after pre-flight passes)
2. Updated after each WP merge completes or conflicts
3. Deleted on successful completion or explicit `--abort`

---

### PreflightResult

Result of pre-merge validation checks. In-memory only (not persisted).

| Field | Type | Description |
|-------|------|-------------|
| `passed` | boolean | True if all checks pass |
| `wp_statuses` | WPStatus[] | Status of each WP worktree |
| `target_diverged` | boolean | True if target branch has diverged from origin |
| `target_divergence_msg` | string \| null | Explanation if diverged |
| `errors` | string[] | Blocking issues that prevent merge |
| `warnings` | string[] | Non-blocking issues to display |

---

### WPStatus

Status of a single WP worktree during pre-flight.

| Field | Type | Description |
|-------|------|-------------|
| `wp_id` | string | Work package ID (e.g., "WP01") |
| `worktree_path` | Path | Absolute path to worktree directory |
| `branch_name` | string | Git branch name |
| `is_clean` | boolean | True if no uncommitted changes |
| `error` | string \| null | Error message if not ready |

---

### ConflictPrediction

Predicted conflict for a file, generated during `--dry-run` or pre-merge analysis.

| Field | Type | Description |
|-------|------|-------------|
| `file_path` | string | Path relative to repo root |
| `conflicting_wps` | string[] | WP IDs that modify this file |
| `is_status_file` | boolean | True if matches status file pattern |
| `confidence` | string | "certain", "likely", or "possible" |

**Confidence Levels**:
- `certain`: `git merge-tree` detected actual conflict markers
- `likely`: Same lines modified in multiple WPs (git diff --stat overlap)
- `possible`: Same file modified in multiple WPs (may not conflict)

---

### ResolutionResult

Result of auto-resolving a status file conflict.

| Field | Type | Description |
|-------|------|-------------|
| `file_path` | Path | Absolute path to resolved file |
| `resolved` | boolean | True if all conflicts in file were resolved |
| `resolution_type` | string | Type of resolution applied |
| `original_conflicts` | int | Number of conflict regions found |
| `resolved_conflicts` | int | Number of conflict regions resolved |

**Resolution Types**:
- `lane`: Resolved `lane:` field by "more done" wins
- `checkbox`: Resolved checkboxes by preferring `[x]`
- `history`: Resolved `history:` by chronological merge
- `mixed`: Multiple resolution types applied
- `manual_required`: Contains non-status conflicts

---

## Relationships

```
MergeState
    │
    ├── 1:N ─→ WPStatus (via wp_order → find_wp_worktrees)
    │
    └── contains ─→ completed_wps, current_wp (subset of wp_order)

PreflightResult
    │
    └── 1:N ─→ WPStatus (wp_statuses)

ConflictPrediction
    │
    └── N:M ─→ WP IDs (conflicting_wps)

ResolutionResult
    │
    └── 1:1 ─→ File (file_path)
```

## State Transitions

### MergeState Lifecycle

```
[No State] ──(start merge)──→ [Active: current_wp=WP01]
                                        │
                     ┌──────────────────┼──────────────────┐
                     │                  │                  │
                     ▼                  ▼                  ▼
            [WP merged OK]    [Conflict detected]    [Interrupted]
                     │                  │                  │
                     │           ┌──────┴──────┐           │
                     │           ▼             ▼           │
                     │    [Auto-resolved]  [Manual req]    │
                     │           │             │           │
                     ▼           ▼             │           │
              [Next WP]   [Continue]      [--resume]  [--resume]
                     │           │             │           │
                     └─────┬─────┴─────────────┴───────────┘
                           │
                           ▼
                    [All WPs done]
                           │
                           ▼
                      [Cleanup]
                           │
                           ▼
                    [State cleared]
```

### Resolution Flow

```
[Merge conflict] ──→ [Check file pattern]
                            │
              ┌─────────────┴─────────────┐
              │                           │
              ▼                           ▼
    [Status file match]           [Non-status file]
              │                           │
              ▼                           ▼
    [Parse conflict markers]      [Manual required]
              │
              ▼
    [Apply resolution rules]
              │
              ▼
    [git add resolved file]
              │
              ▼
    [Continue merge]
```

## File Patterns

### Status File Detection

Files matching these patterns are candidates for auto-resolution:

```
kitty-specs/**/tasks/*.md     # WP files (e.g., WP01.md)
kitty-specs/**/tasks.md       # Main tasks checklist
```

### Resolution Rules

| Content Pattern | Rule | Winner |
|-----------------|------|--------|
| `lane: <value>` | "More done" wins | done > for_review > doing > planned |
| `- [x]` vs `- [ ]` | Checked wins | `[x]` |
| `history:` array | Concatenate | Merge by timestamp, dedupe |
| Other YAML | No auto-resolve | Manual |
| Non-YAML content | No auto-resolve | Manual |
