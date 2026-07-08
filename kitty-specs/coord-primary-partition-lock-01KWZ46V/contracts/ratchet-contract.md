# Contract: Architectural Ratchet Extension

The ratchet is the enforcement that keeps the strangle strangled (SC-005). This mission
**extends the existing** ratchet — it does not build a new one (a parallel gate would be
a shadow authority, violating C-001/Directive-044).

## Target files (existing)

- `tests/architectural/test_no_write_side_rederivation.py` — AST scanner over write sites.
- `tests/architectural/resolution_gate_allowlist.yaml` — `coord_authority_baseline` + entries.
- `tests/architectural/test_resolution_authority_gates.py` — integer floor guards.

## New grammar (FR-011)

The scanner today matches three grammars: `parent.parent` root-walks, `mission_id[:8]`
recompute, and `coord_branch or _current_branch`. It does **not** catch the construction
where the bypass sites actually live:

```python
CommitTarget(ref=<current-checkout expression>)
# e.g. CommitTarget(ref=current_branch), CommitTarget(ref=_get_cur_branch() or planning_branch)
```

**Contract**: extend the scanner to flag `CommitTarget(...)` (and `safe_commit(...)`
destination) whose `ref`/`destination_ref` argument is derived from a current-checkout
expression rather than a `seam.write_target(...)` call, in any module not on the
allow-list.

### Detection boundary (must not false-positive)

- **Sanctioned coord primitives** — `branch_naming.py` `coord_*` composition, `CoordinationWorkspace` internals, `mission_runtime/*` seam internals: allow-listed (they *are* the sanctioned grammar).
- **Legacy/migration** — `upgrade/migrations/*`, `migration/*`, `upgrade/autocommit.py`, `invocation/executor.py` (op-record self-bookkeeping on the operator's branch by design): allow-listed.

## Baseline (NFR-001)

| Knob | Current | This mission |
|------|---------|--------------|
| Write-side line allow-list seed | 1 (`coordination/status_transition.py:347`, deferred #1716 HEAD selector — re-anchored 343→347 by the #1842 tombstone hook) | shrink-only toward permanent-fixture floor; **must not grow** |
| Adopted-module set | 6 (`status/emit.py`, `status/work_package_lifecycle.py`, `status/lifecycle_events.py`, `status/store.py`, `coordination/status_transition.py`, `core/worktree.py`) | **expand** to include each strangled surface (`core/mission_creation.py`, then `implement.py`, `workflow.py`, `tasks_move_task.py`, `mission_record_analysis.py`) as its route lands |
| `coord_authority_baseline` | 7 | **NOT drained here** — its 5 drainable entries are kind-blind `resolve_feature_dir_for_mission` **reads** (disjoint from the routed writes); the 7→2 drain is deferred to **#2453**. This mission keeps it at 7. |
| VISIBLE-but-tracked (new-grammar allow-list) | — | allow-list `retrospective/writer.py` (sanctioned #2119 RETROSPECTIVE authority), and the residual checkout-derived write fallbacks `orchestrator_api/commands.py:1451` + `coordination/transaction.py` legacy override + `tasks_map_requirements.py:177`, each with a `tracked: #2453` rationale — flagged, not silent |

**Sequencing rule (contract)**: a module is added to the adopted set (and its baseline
decremented) **in the same WP that routes it** — never before (the ratchet would go red
without a landed route) and never after (a routed-but-unadopted module can silently
regress).

## Pass/fail

- **PASS**: every lifecycle/planning write/read resolves through the seam; the allow-list
  is at or below baseline; the new grammar finds zero un-allow-listed offenders.
- **FAIL**: any un-allow-listed `CommitTarget(ref=<checkout>)`, any allow-list growth, or a
  routed module missing from the adopted set.
