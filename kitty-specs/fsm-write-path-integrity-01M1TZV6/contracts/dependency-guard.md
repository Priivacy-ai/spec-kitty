# Contract: Dependency Readiness Guard (WP04)

**Owner**: `src/specify_cli/status/` (`models.py`, `wp_state.py`) · **Verdict supplier**: the two shells (`contracts/emit-pipeline.md` §2 step 3)
**Binding decisions**: Q8 (`01M1V8HVDQH36X06JDK22SZV02`) · **Constraints**: C-004, C-005, NFR-002 · **Non-goal 6**: no edge/force/terminal changes

## 1. Field

```python
# src/specify_cli/status/models.py — GuardContext (+1 field, established shape)
dependency_ready: bool | None = None
```

## 2. Polarity (tri-state, fail-OPEN on `None`)

| `dependency_ready` | `planned→claimed`, `claimed→in_progress` | all other edges |
|---|---|---|
| `None` | **pass** (no verdict supplied) | pass |
| `True` | pass | pass |
| `False` | **refuse** with message `"Transition <from> -> <to> blocked: unsatisfied dependencies <ids>"`; `force` with actor+reason bypasses (existing `_check_force` path) | pass |

**Why fail-open** (recorded so nobody "fixes" it to match `subtasks_complete`, `wp_state.py:370`): `lanes/recovery.py:78` (crash-recovery progression probe) and `agent/tasks_transition_core.py:337` (FR-015 force-free backward-edge probe) call `validate_transition` with self-built contexts on exactly these edges. Fail-closed on `None` silently breaks both. It is sound because after WP03 no durable write bypasses the shells, and the shells always supply a verdict.

## 3. Guard clause placement

`wp_state.py`: one clause inside the existing `guard_for` for targets `Lane.CLAIMED` (from `PLANNED`) and `Lane.IN_PROGRESS` (from `CLAIMED`), via the `subtasks_complete` shape. Guards never consult `ctx.force` (existing rule, #1775 M2).

## 4. Resolution site (FR-013)

Shells compute, **inside L1 / the transaction**, against the shell's write surface:

```python
readiness = dependency_readiness_for_wp(
    wp_id, dependencies_for(wp_id, feature_dir), wp_lanes_from(feature_dir), provenance_from(feature_dir)
)
```
- Never before acquiring the lock (reproduces the pre-flight TOCTOU).
- Never against the primary planning dir when the write surface is the coord worktree (stale state).
- `dependency_readiness_for_wp` (`core/dependency_graph.py:34`) is reused as-is: approved OR done OR canceled-with-operator-provenance satisfies.

## 5. Demoted pre-flight sites (FR-014) — left in place, re-commented as UX

`cli/commands/implement.py:1340`, `agent/workflow_executor.py:653`, `agent/tasks_status_view.py:228`, `orchestrator_api/commands.py:1115,1440`, `runtime/next/discovery.py:150`.

## 6. Replay purity (C-005 / NFR-002)

`reducer.py` keeps zero references to `validate_transition` / `GuardContext`; `validate.py:validate_transition_legality` re-checks edge legality only. Test: a history containing a now-dep-illegal claim replays and audits with no guard finding.

## 7. Test matrix (RED-first then unit)

| Case | Expected after WP04 | RED on main? |
|---|---|---|
| direct verdict-less emit through a shell, `planned→claimed`, dep `in_progress` | refused | yes (succeeds today) |
| `GuardContext(dependency_ready=False)` → `validate_transition` on entry edges | refused | n/a (field absent today) |
| both probe sites with `dependency_ready=None` | pass | pin |
| dep `approved` (not `done`) | claim allowed | pin |
| dep `in_progress` + `force` with actor+reason | allowed, recorded | pin |
| coord topology: readiness resolved against `txn.feature_dir` | verified by fake-surface test | pin |
| `implement` re-invoked on `in_progress` WP | no-op resume, not re-gated | pin |
