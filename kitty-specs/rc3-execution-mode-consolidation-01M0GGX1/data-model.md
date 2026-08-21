---
type: reference
updated: 2026-08-21
---

# Data Model: M7 — ExecutionMode / enum consolidation

This is a code-hygiene mission: no new domain entities, no schema change. The
"entities" here are the three `ExecutionMode` types and their edges to consumers.
Verified against `upstream/main` @ `c44b4bcf87` (2026-08-21).

## Entities (the three types)

### E1 — `WorkProductKind` (renamed from `ownership.models.ExecutionMode`)

- **Kind:** `StrEnum`
- **Axis modelled:** what a work package *produces*.
- **Members (names & string values UNCHANGED):**
  - `CODE_CHANGE = "code_change"` — WP produces source/test changes.
  - `PLANNING_ARTIFACT = "planning_artifact"` — WP produces planning/doc artifacts only.
- **Wire contract:** member **string values** are persisted in WP frontmatter
  (`execution_mode:`) and must not change (FR-002). Only the **class name** changes.
- **Extension point (M6 headroom):** M6 will ADD a non-diff completion-mode member;
  M7 must not preclude that (AC-5).

### E2 — `mission_runtime.context.ExecutionMode` — RETIRED

- **Kind:** `enum.Enum`
- **Members:** `WORKTREE` / `CODE_CHANGE` — DEAD (no member consumers in `src/`).
- **Disposition:** deleted, together with its re-export and surface pin
  (governance-gate change, FR-001).

### E3 — `spec_kitty_events.status.ExecutionMode` — EXTERNAL, unchanged

- **Kind:** `str, Enum` (published PyPI package `spec_kitty_events`).
- **Members:** `worktree` / `direct_repo`.
- **Axis modelled:** worktree-vs-direct status-payload execution mode.
- **Disposition:** untouched; becomes the *only* surviving live `ExecutionMode`.
  Consumed at `src/specify_cli/cli/commands/agent/tasks_transition_core.py:218,229`.

## Edges — E1 consumers to update (class-name references)

| Module | Reference kind |
|--------|----------------|
| `src/specify_cli/ownership/models.py` | definition + field type `execution_mode: <NewName>` + docstrings |
| `src/specify_cli/ownership/__init__.py` | import + `__all__` entry |
| `src/specify_cli/ownership/inference.py` | import + `infer_execution_mode` return annotation + members |
| `src/specify_cli/ownership/validation.py` | import + member comparisons |
| `src/specify_cli/core/worktree.py` | import + members (default + coercion) |
| `src/specify_cli/lanes/compute.py` | import + member comparison |
| `src/specify_cli/lanes/implement_support.py` | import + member comparison |
| `src/specify_cli/workspace/context.py` | import + coercion + member comparison |
| `src/specify_cli/cli/commands/agent/mission_parsing.py` | import + member + docstring `:data:` ref |

**Invariants preserved:** the field name `execution_mode`, the function name
`infer_execution_mode`, and member names/values are all unchanged — so runtime
behavior and on-disk frontmatter are identical. Only the class *symbol* is renamed.

## Edges — E2 retirement surface

| Location | Change |
|----------|--------|
| `src/mission_runtime/context.py:42` | delete the class |
| `src/mission_runtime/context.py:359` | drop the module `__all__` entry |
| `src/mission_runtime/__init__.py:32` | drop the import |
| `src/mission_runtime/__init__.py:82` | drop the package `__all__` entry |
| `tests/architectural/test_mission_runtime_surface.py:53` | unpin the symbol |
| `docs/adr/3.x/2026-06-07-1-...canonical-surface.md:76,84` | remove from `__all__` snippet + description; add dated retirement note |

**Verified dead:** `MissionExecutionContext.execution_mode` is `str | None`
(`context.py:306`) — a raw string, not this enum; no `.WORKTREE`/`.CODE_CHANGE`
member access anywhere. Deletion is behavior-neutral.

## Test-side consumers of E1 (rename, no alias)

Per canonical-source discipline (no back-compat alias — that would leave the clash
alive), these test files import/reference the renamed class and are updated in WP03:

`tests/integration/test_planning_artifact_wp.py`,
`tests/lanes/test_compute.py`,
`tests/lanes/test_compute_planning_artifact.py`,
`tests/lanes/test_compute_planning_artifact_deps.py`,
`tests/lanes/test_dependent_wp_scheduling.py`,
`tests/lanes/test_issue_1860_branch_identity_dual_era.py`,
`tests/specify_cli/lanes/test_compute_lane_depths_cycle_safety.py`,
`tests/specify_cli/ownership/test_audit_scope.py`,
`tests/specify_cli/ownership/test_inference.py`,
`tests/specify_cli/core/test_worktree.py` (class-name label only).

## New artifact — re-drift guard test

A new `tests/architectural/` test asserting the footgun cannot return:
- no `class ExecutionMode` anywhere under `src/` (grep-style, 0 results);
- no live enum pairing `worktree` with `code_change`;
- the retired symbol is absent from the mission_runtime surface;
- **permits** M6's additive member on `WorkProductKind` (assert absence-of-footgun,
  not an exact member set).
