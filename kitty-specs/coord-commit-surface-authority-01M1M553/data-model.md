# Data Model: Coord Commit-Surface Authority

This mission changes decision logic, not persisted schema. The "entities" below are the conceptual inputs/outputs of the commit-surface decision the mission unifies.

## Entities

### Mission surface context (decision input)
The tuple the unified authority helper consumes.

| Attribute | Source | Values |
|-----------|--------|--------|
| `topology` | `meta.json` / `resolve_topology(repo_root, slug)` | `SINGLE_BRANCH`, `LANES`, `COORD`, `LANES_WITH_COORD` |
| `primary_target` | `_resolve_mission_target_branch(repo_root, slug)` | branch name (e.g. `main`, `trunk`, `fix/x`) |
| `primary_protected` | `ProtectionPolicy.resolve(repo_root).is_protected(primary_target)` — protection of the **primary target branch**, NOT the current checkout | bool (true for `main`/`master`; `SPEC_KITTY_ALLOW_PROTECTED_BRANCH_COMMITS=1` folds to False) |
| `current_branch` | `get_current_branch(checkout)` post `--start-branch` switch | branch name |
| `pr_bound` | create flag | bool |
| `artifact_kind` | `resolve_placement_only(..., kind)` | primary-kind vs coordination-kind |

### Authoritative surface (decision output)
| Attribute | Meaning |
|-----------|---------|
| `surface` | `primary` \| `coordination` — where the artifact-kind's commit must land |
| `ref` | the concrete branch that owns the commit |
| `non_committable_verdict` | `RouteToCoord` (coord-kind → coord surface; redundant primary commit suppressed; exit 0) \| `Refuse(remedy)` (planning-kind on protected primary; exit 1) \| `NoOp(reason)` (genuine no-op only; exit 0). No bare `skip`. Wrong-surface → `Refuse`, never `NoOp`. |

### Coordination branch/worktree (per-mission identity — unchanged)
| Attribute | Derivation | Note |
|-----------|-----------|------|
| worktree path | `.worktrees/<slug>-<mid8>-coord` | per-mission; no cross-mission collision (research D-002) |
| branch name | `kitty/mission-<slug>-<mid8>` | per-mission; **must not be minted as a stranded label** when coord routing is inert (the #2533 defect) |

## Key relationships / invariants

- **INV-1 (authority coherence)**: the surface a kind commits to == the surface its status/state is materialized from. Violated today by #2533 (writes to primary, coord worktree stranded).
- **INV-2 (topology honesty)**: `topology: coord` is minted only when coordination routing is actually reachable (protected primary, or a real coord partition) — never as pure overhead on an unprotected feature branch.
- **INV-3 (no silent misroute)**: a requested commit either lands on the resolved authoritative ref or the command refuses; never `success` for a write that did not land, never a silent fallback that changes the surface without signalling (guards the `_resolve_mid8 → None` path, OQ-3).
- **INV-4 (shared-rule consultation)**: commit-bearing commands (`move-task`, `map-requirements`) and `commit_router` derive their verdict from ONE `resolve_surface_authority` rule; identical `{artifact_kind, topology, primary_protected}` → identical verdict (exit codes may differ *by kind*, not by hardcoded per-command logic). `mark-status` is event-log-only (not a commit consumer).

## State transitions touched
No new lane states. The mission touches the **commit boundary** at create-time (topology mint), at spec-commit / coord-router placement, and at the three task-command commits — reconciling them to INV-1..INV-4. The 9-lane WP state machine is unchanged.
