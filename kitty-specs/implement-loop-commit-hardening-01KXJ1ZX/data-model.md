# Data Model — Implement-Loop Commit & Move-Task Hardening

Control-flow / maintainability mission; no persisted schema. The "model" is the
partition-decision it unifies and the status-surface resolution it corrects.

## The partition decision (FR-005 / FR-006 / C-007)

### The three decision sites (all to consolidate)

| Site | File | Role | Primary ref | `kind=None` routes to |
|------|------|------|-------------|-----------------------|
| Read | `implement_cores.py::resolve_precondition_ref` | idempotency compare | `"HEAD"` | PRIMARY (residue predicate) ✅ #2533-safe |
| Write | `implement.py::_partition_files_for_commit` | commit split | `planning_branch` | PRIMARY (residue predicate) ✅ |
| Write | `commit_router::_group_files_by_partition` | commit split | placement ref | **caller partition (can be COORD)** ❌ #2533 hole |

### The disagreement set (what the characterization gate pins)

`kind=None` ⟺ `kind_for_mission_file(path)` returns `None` ⟺ the path is **not** in
`_PRIMARY_ARTIFACT_KINDS ∪ _PLACEMENT_ARTIFACT_KINDS`. Concretely: **`meta.json`** (it is
in the self-bookkeeping allowlist, not the kind map) + any unrecognized mission file.

- Residue authority: `kind=None` → not a coord residue → **PRIMARY** (`"HEAD"` / target).
- Kind authority (`commit_router`): `kind_for_mission_file(file) or kind` → `None` → falls
  back to the **caller's** partition → can be COORD.

**Unified contract (C-007):** the consolidated authority MUST route `kind=None` → PRIMARY.

## Unified authority (target shape)

```
is_coordination_artifact_residue_path(path) -> bool   # EXISTING mission_runtime predicate; NOT None-> PRIMARY
primary_ref_for(context) -> str                       # one cli-local expression; read & write agree
```

- The shared partition authority is the **existing** `mission_runtime.is_coordination_artifact_residue_path`
  — NOT a net-new `partition_of` wrapper. Two of the three sites already call it
  (`implement.py:600`, `implement_cores.py:268`); the consolidation swaps
  `commit_router:404`'s `kind_for_mission_file(file) or kind` classifier onto it
  (classifier-only — `commit_router` keeps `resolve_placement_only` for its COORD ref).
  Homing a new `partition_of` in `cli/commands` would invert the `cli → coordination`
  layering (C-008); `mission_runtime` is read-only.
- The read (`"HEAD"`) / write (`planning_branch`) primary-ref unification is a SEPARATE,
  cli-local (Lane A) concern (`primary_ref_for`) that does NOT touch `commit_router`.
- A structural test asserts the three named sites resolve partition through the one predicate
  (old per-site classifier deleted or forwarding; `commit_router` no longer consults
  `is_primary_artifact_kind(kind_for_mission_file(...))` for the split) — SC-004, they cannot
  silently re-diverge. Scope is the three named claim/planning-commit sites only (not every
  predicate-consumer in the codebase).

## Status-surface resolution (FR-001)

```
move-task WP## (cwd = lane worktree)
  └─ _mt_resolve_targets → feature_dir (must derive from the canonical mission root,
        NOT a cwd-tainted locate_project_root)
        └─ _read_transactional_wp_lane → reads status.json/events from the mission root
  ⇒ transition succeeds identically whether cwd is the repo root or a lane worktree
```

## Invariants

- **INV-1 (C-007)**: `meta.json` / `kind=None` / unrecognized path → PRIMARY, on all
  (now unified) sites. The #2533 regression stays green.
- **INV-2 (C-006)**: `_resolve_bookkeeping_transaction_identifiers` keeps its public
  signature + 5-tuple return (Lane B depends on it).
- **INV-3 (C-001)**: `_mt_uncheck_rollback_subtasks` keeps two separate exception handlers
  (#2576 `rollback_uncheck_error` recording + #2513 commit-failure swallow).
- **INV-4 (FR-001)**: `move-task` result is cwd-independent (repo root == lane worktree).
- **INV-5 (NFR-004/C-008)**: no net-new public/exported symbol from the degod.
- **INV-6 (FR-002/C-009)**: on the **narrow triple** (`placement_ref is None` AND meta
  `coord_branch` truthy AND protected `planning_branch` — the `767` precondition), the
  artifact-commit AND status-commit halves BOTH fail-closed with `PlacementResolutionRequired`
  — no silent PRIMARY-on-coord divert; the `767` fallback is removed. This is the ONLY state
  where the status half's unconditional-on-`None` raise and the artifact half agree by design.
- **INV-7 (FR-002/C-004 — the #2463 None-overload guard)**: on the OTHER `placement_ref is
  None` states — flat/legacy (no `coord_branch` → `755`) and coord + non-protected
  `planning_branch` (`790` partition split) — the artifact-commit half still commits
  successfully (the C-004 strangler fallback). `placement_ref is None` is NOT unconditionally
  degenerate; 3 write-side tests + the #2533 regression drive it expecting success. WP03
  characterizes the real flat/legacy None-at-this-seam behavior before FR-002 relies on the
  narrow condition.
