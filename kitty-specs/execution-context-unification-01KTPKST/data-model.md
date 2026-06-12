# Data Model — Execution-Context Unification (01KTPKST)

The `MissionExecutionContext` is a **doc-09 fragment / op-composite**, NOT a flat field bag. It is grown
on the existing `mission_runtime.ExecutionContext` substrate (which already carries
`feature_dir`, `target_branch`, `workspace_path`, `branch_name`, `execution_mode`, `mission_slug`).
Each fragment is a cohesive value object; an *operation* assembles only the fragments it needs.

> Fragment boundaries below are the **proposed** cut. The exact granularity (e.g. whether
> `allowed_command_cwd` is part of Workspace or its own fragment) is an IC-02 design decision,
> driven by which ops co-consume the values. Recorded as an open question in `research.md`.

## Fragments

### IdentityFragment
| Field | Type | Notes |
|-------|------|-------|
| `mission_id` | ULID (26) | canonical machine identity (immutable) |
| `mid8` | str (8) | **derived once** from `mission_id`; never recomputed at call sites (FR-012) |
| `mission_slug` | str | human handle |

Invariant: `mid8 == mission_id[:8]`. Single derivation point lives in this fragment.

### BranchRefFragment
| Field | Type | Notes |
|-------|------|-------|
| `target_branch` | str | **single source** (FR-012) — resolved once, not re-derived from meta.json/git per surface |
| `coordination_branch` | str \| None | `None` under flattened topology (C-001) |
| `destination_ref` | CommitTarget | the ONE ref artifacts + status resolve to (ADR-2026-06-03-2) |

### CommitTarget (value object — ADR-2026-06-03-2)
| Field | Type | Notes |
|-------|------|-------|
| `ref` | str | branch/worktree ref that receives commits for this mission |
| `kind` | enum `{primary, coordination, flattened}` | flattened ⇒ landing == coordination == target |

Invariant (FR-004): planning artifacts AND status events resolve to the **same** `destination_ref`.
Under flattened topology, `kind == flattened` and there is no primary↔coord split to reconcile.

### WorkspaceFragment
| Field | Type | Notes |
|-------|------|-------|
| `primary_root` | Path | repo root checkout — single worktree-pointer parser (IC-04) |
| `current_cwd` | Path | where the command is actually running |
| `coord_worktree` | Path \| None | `None` under flattened topology |
| `execution_workspace` | Path | lane worktree for implement/review |
| `allowed_command_cwd` | Path | guard: which CWD a surface may run git ops in |

### StatusSurfaceFragment
| Field | Type | Notes |
|-------|------|-------|
| `status_read_dir` | Path | where status events are read from |
| `status_write_dir` | Path | where status events are written |

Resolved by the existing `resolve_status_surface` (IC-01) and **carried on the context** — consumers
(esp. `status_transition._identity_for_request`) must NOT re-derive it (FR-003/FR-008/#1737).
Under flattened topology, read_dir == write_dir.

### ArtifactPlacementFragment
| Field | Type | Notes |
|-------|------|-------|
| `placement_ref` | CommitTarget | where planning artifacts (spec/plan/tasks/analysis) commit |

Used by implement-claim (#1816) and record-analysis (#1814) instead of independent primary/coord logic (IC-05).

### PromptSourceFragment
| Field | Type | Notes |
|-------|------|-------|
| `prompt_source_dir` | Path | where implement/review prompt files are resolved (FR-012) |

## State / lifecycle

- The context is **resolved once** per command invocation (`resolve_action_context`, IC-02) and threaded.
- WP lane state remains owned by the append-only `status.events.jsonl` event log (unchanged authority);
  this mission changes *who resolves where that log lives*, not the log's reducer semantics.

## Deletions (net subtraction — NFR-005)
| Surface | Disposition | IC |
|---------|-------------|-----|
| `missions/feature_dir_resolver.candidate_feature_dir_for_mission` | fold into `_read_path_resolver` | IC-03 |
| `workspace/root_resolver` worktree parser (~200 LOC) | delete; `core/paths` is the single parser | IC-04 |
| `status_service.{EventLogWriteTarget,StatusContractError,StatusReadSource,append_event_log_batch,read_wp_lane_actor}` | delete (5 dead symbols) | IC-09 |
| `status_transition._identity_for_request` coord re-derivation | replace with carried StatusSurfaceFragment | IC-01 |

## Occurrence-map schema extension (IC-10, #1815) — adjacent
| Existing | Added |
|----------|-------|
| 8 term-rename categories (single `target.term → replacement`) | `moves: [{from: [paths], to: path}]` multi-path structural-move block |

Backward-compatible: a map with only the 8 categories and no `moves:` validates exactly as today.
