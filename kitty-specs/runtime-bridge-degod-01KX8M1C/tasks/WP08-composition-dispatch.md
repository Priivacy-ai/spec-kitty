---
work_package_id: WP08
title: Composition dispatch + FR-008 selection seam
dependencies: [WP07]
requirement_refs:
- FR-008
- FR-004
- FR-001
tracker_refs:
- '2531'
planning_base_branch: design/runtime-bridge-degod
merge_target_branch: design/runtime-bridge-degod
branch_strategy: Planning artifacts for this mission were generated on design/runtime-bridge-degod. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into design/runtime-bridge-degod unless the human explicitly redirects the landing branch.
subtasks:
- T028
- T029
- T030
phase: Extraction spine
shell_pid: '2850453'
history:
- at: '2026-07-11T00:00:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/runtime/next/
create_intent:
- src/runtime/next/runtime_bridge_composition.py
- tests/runtime/test_bridge_composition.py
execution_mode: code_change
owned_files:
- src/runtime/next/runtime_bridge_composition.py
- src/runtime/next/runtime_bridge.py
- tests/runtime/test_bridge_composition.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP08 – Composition dispatch + FR-008 selection seam

## Context

This WP extracts the composition-dispatch cluster (~570 LOC in the god-module) into a new
sibling `runtime_bridge_composition.py`: the dispatch path, the run-state advance, and — the
FR-008 headline — the **`_should_dispatch_via_composition` selection decision** isolated as a
clean, directly testable seam. Behavior-preserving (C-001).

It depends on **WP03** (the engine-adapter) because run-state advance calls the adapter-owned
`_advance_run_state_after_composition` logic (`runtime_bridge_engine.py`, with a thin residual
compat delegate at `runtime_bridge._advance_run_state_after_composition` — see plan.md IC-02).
It depends on **WP07** (the Decision-builder) because dispatch materializes decisions through
the shared `step_or_blocked` core. WP01/WP02 remain the blocking acceptance gate.

### FR-008 — the selection seam (coordination boundary, read carefully)

`_should_dispatch_via_composition:1264` is the **selection** decision (NOT the fs-guard
`_check_composed_action_guard`, which WP06 already inverted). FR-008 asks only that this
selection be left as a **clean, testable core** a future consumer can route through **without
this mission coupling to it**. Concretely (C-005):

- **Import NO gates code.** Do not adopt or depend on the gates mission (#2535)
  `resolve_gates` seam — it is unlanded. The inversion that consumes this seam is gates WP14,
  after this mission. You leave the seam; you do not wire it.
- Keep the selection a pure/near-pure predicate with a stable signature so gates #2535 WP14
  can route through it later.

## Ordered Steps

### T028 — Create `runtime_bridge_composition.py`; move dispatch + run-state advance

1. Create `src/runtime/next/runtime_bridge_composition.py` with a responsibility docstring +
   `#2531` decomposition pointer (FR-007).
2. Move the composition-dispatch cluster from `runtime_bridge.py`: the dispatch entry, the
   run-state advance orchestration, and their private helpers. Run-state advance delegates to
   the WP03 engine-adapter for the `_advance_run_state_after_composition` logic; keep the thin
   residual compat delegate reachable at `runtime_bridge._advance_run_state_after_composition`
   (8 patch + 9 attr compat surface — research.md §Compat).
3. Import DAG (research.md §Import DAG): `composition` may import `io`/`engine`/`cores`; it must
   NOT be imported by `cores`. No `decision → runtime_bridge_*` top-level edge (C-007).

### T029 — Isolate the `_should_dispatch_via_composition` selection seam (FR-008)

1. Move `_should_dispatch_via_composition:1264` into `runtime_bridge_composition.py` as a clean,
   named, directly-callable predicate with a stable signature.
2. Confirm it imports **no gates (#2535) code** and pulls in no `resolve_gates` dependency
   (C-005). It stays a self-contained selection decision.
3. If any branch pushes the function over the ceiling, extract small named helpers so it (and
   every helper) lands **≤15** (FR-004). Remove any `# noqa: C901` touched.

### T030 — Both-branch fixture; re-export; oracle + compat green

1. Create `tests/runtime/test_bridge_composition.py`:
   - **`_should_dispatch_via_composition` both-branch fixture** (dispatch / no-dispatch) —
     FR-008 explicitly requires exercising both branches of the selection (plan.md Notes §6).
   - Dispatch + run-state advance contract-tested against stubs (FR-006) — the engine-adapter
     boundary is stubbed here; the adapter's own mutations are asserted by the WP01 oracle's
     captured `_append_event`/`_write_snapshot`.
2. Guarded re-export: every relocated-but-patched symbol reachable at `runtime_bridge.<name>`
   (FR-012); confirm re-export identity.
3. Re-run the acceptance gate (below).

## Acceptance

- `runtime_bridge_composition.py` exists; dispatch + run-state advance relocated; run-state
  advance delegates to the WP03 engine-adapter with the thin residual compat delegate intact.
- `_should_dispatch_via_composition` isolated as a clean selection seam that imports **no gates
  code** (C-005/FR-008); a **both-branch fixture** (dispatch / no-dispatch) covers it.
- Any touched function ≤15; no `# noqa: C901` relocated (FR-004).
- **Acceptance gate:** WP01 parity oracle green on all 3 entries at the full coverage floor;
  WP02 compat guard green (each relocated symbol's sentinel fires through its reaching entry).

## Safeguards

- **FR-008/C-005 boundary is load-bearing:** leave the selection a clean seam, do NOT import or
  depend on the unlanded gates (#2535) `resolve_gates`. Coupling to it here is out of scope and
  a constraint violation.
- Do not re-implement `_advance_run_state_after_composition` logic here — it is adapter-owned
  (WP03). Consume the adapter; keep only the compat delegate reachable in the residual.
- The both-branch fixture is not optional — a single-branch test leaves the FR-008 seam
  half-verified.
- Never stub `next_step` in the oracle re-run; capture-and-assert the composition side effects.

## References

- `src/runtime/next/runtime_bridge.py:1264` — `_should_dispatch_via_composition` (the FR-008 selection decision).
- `src/runtime/next/runtime_bridge.py:1800` — `_advance_run_state_after_composition` (adapter-owned via WP03; thin residual compat delegate).
- `kitty-specs/runtime-bridge-degod-01KX8M1C/research.md` §Seams / §Import DAG — composition cluster boundary.
- `kitty-specs/runtime-bridge-degod-01KX8M1C/plan.md` IC-07 + Notes §6 — dispatch, selection seam, both-branch fixture.
- `kitty-specs/runtime-bridge-degod-01KX8M1C/spec.md` — FR-008, FR-004, FR-001, C-005.

## Activity Log

- 2026-07-11T23:23:44Z – user – shell_pid=2850453 – Moved to for_review
- 2026-07-11T23:31:28Z – user – shell_pid=2850453 – Moved to approved
