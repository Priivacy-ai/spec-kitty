---
work_package_id: WP09
title: decide_next phase-split (FR-010)
dependencies: [WP08]
requirement_refs:
- FR-010
- FR-005
- FR-004
tracker_refs:
- '2531'
planning_base_branch: design/runtime-bridge-degod
merge_target_branch: design/runtime-bridge-degod
branch_strategy: Planning artifacts for this mission were generated on design/runtime-bridge-degod. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into design/runtime-bridge-degod unless the human explicitly redirects the landing branch.
subtasks:
- T031
- T032
- T033
phase: Extraction spine
shell_pid: '2956749'
history:
- at: '2026-07-11T00:00:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/runtime/next/
create_intent:
- tests/runtime/test_bridge_decide_next.py
execution_mode: code_change
owned_files:
- src/runtime/next/runtime_bridge.py
- tests/runtime/test_bridge_decide_next.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP09 – decide_next phase-split (FR-010)

## Context

This WP rewrites the mission's worst offender — the ~535-line
`decide_next_via_runtime:2524` orchestrator (CC≈50, one of the three `# noqa: C901`
markers) — as a **linear four-phase early-return chain** over a frozen `DecideNextContext`
dataclass, landing the residual **≤15**. Behavior-preserving (C-001): the `decide_next()`
contract does not change.

It owns **only** `runtime_bridge.py` (which already exists — never in `create_intent`) plus a
new test file. It depends on **WP06** (pure cores / `evaluate_guards`), **WP07** (the
Decision-builder that the decision-materialize phase calls), and **WP08** (the composition
dispatch the dispatch phase calls) — all four phases compose already-extracted seams, so this
WP is mostly orchestration re-shaping, not new extraction. WP01/WP02 remain the blocking
acceptance gate; this WP is where the `decide_next`-owned ~15 Decision sites and its side
effects (sync emit `:2556`, coord commit `:2563`) must stay parity-identical.

### The target shape (FR-010; data-model.md §DecideNextContext)

`DecideNextContext` — a frozen dataclass (~14 fields, per the #2464 `implement`/`review`
precedent) threading the shared locals through the phases. `decide_next_via_runtime` becomes:

```
ctx = <bootstrap ctx>
for phase in (bootstrap, dependency_gate, composition_dispatch, decision_materialize):
    decision = phase(ctx)   # (ctx) -> Decision | None
    if decision is not None:
        return decision
```

Each phase returns `Decision | None`; the first non-None short-circuits.

## Ordered Steps

### T031 — `DecideNextContext` frozen dataclass (~14 fields)

1. Define `DecideNextContext` in `runtime_bridge.py` (residual) as a frozen dataclass carrying
   the shared locals the four phases need (feature dir, mission identity, run state, snapshot,
   step binding, guard facts, …; ~14 fields per data-model.md). No I/O in the dataclass — it is
   a value carrier populated by the bootstrap phase.
2. Keep it internal (NFR-004 — no new public surface); it lives in the residual, not a seam
   module, so the `decision.py:428` lazy edge to the orchestrator stays lazy (C-007).

### T032 — Rewrite `decide_next_via_runtime` as the four-phase early-return chain

1. Extract four phase functions, each `(ctx) -> Decision | None`:
   - **bootstrap** — resolve feature/mission/run, build the context (populates
     `DecideNextContext`).
   - **dependency-gate** — the dependency-readiness gate → blocked `Decision` or None.
   - **composition-dispatch** — routes through WP08's composition seam → `Decision` or None.
   - **decision-materialize** — the terminal/step/query materialize via WP07's Decision-builder
     → `Decision`.
2. Rewrite the residual `decide_next_via_runtime` as the linear chain that calls the phases in
   order and returns the first non-None. Keep its `decide_next`-owned side effects in place and
   in the same order: sync emit (`:2556`), coord-branch `DecisionGitLog` commit (`:2563`),
   `origin.mission_path` (`:2575`) — the oracle captures-and-asserts these.
3. **Remove the `# noqa: C901`** on `decide_next_via_runtime` (FR-004/NFR-002). Confirm the
   residual and every phase helper is **≤15** (`ruff --select C901` zero offenders; radon
   confirms).
4. **Sub-sequence fallback (documented):** if a single WP cannot bring the residual to ≤15,
   fall back to a phase-by-phase landing — but every phase still lands ≤15 and **no `# noqa` is
   re-added** (plan.md IC-08 / tasks.md safeguard). Record the fallback in the PR body if used.

### T033 — Assert residual ≤15; re-export; oracle + compat green

1. Create `tests/runtime/test_bridge_decide_next.py`:
   - Unit-test each phase function against stubs (FR-006): assert each returns the expected
     `Decision | None` for its short-circuit conditions.
   - A guard asserting the residual `decide_next_via_runtime` and each phase are ≤15 (e.g. drive
     `ruff --select C901` / radon over the module, or assert no `# noqa: C901` remains on these
     symbols).
2. Confirm no compat symbol lost its residual reachability (this WP re-shapes the residual — do
   not drop a re-export or lazy accessor).
3. Re-run the acceptance gate (below).

## Acceptance

- `decide_next_via_runtime` is a linear **bootstrap / dependency-gate / composition-dispatch /
  decision-materialize** early-return chain over `DecideNextContext`; residual **≤15**; the
  `# noqa: C901` on it is **removed** (FR-010/FR-004).
- Every phase helper ≤15; `runtime_bridge.py` is a thinner orchestration surface (FR-005).
- Phase functions unit-tested against stubs (FR-006).
- **Acceptance gate:** WP01 parity oracle green on all 3 entries at the full coverage floor —
  specifically the `decide_next`-owned ~15 Decision sites AND its captured side effects (sync
  emit `:2556`, coord commit `:2563`); WP02 compat guard green.

## Safeguards

- Preserve side-effect **order** and content on the `decide_next` path — the oracle
  capture-and-asserts sync emit + coord commit; reordering or dropping an emit is a parity break
  (contracts/parity-oracle.md §Side-effect isolation).
- Do not re-extract logic WP06/WP07/WP08 already own — compose their seams. This WP is
  orchestration re-shaping.
- If the ≤15 target is tight, use the documented phase-by-phase sub-sequence fallback — NEVER
  re-add `# noqa: C901` to hit green (the mission's whole point is zero suppressions).
- `runtime_bridge.py` already exists — it is edited, never created (not in `create_intent`).
- Never stub `next_step` in the oracle.

## References

- `src/runtime/next/runtime_bridge.py:2524` — `decide_next_via_runtime` (CC≈50, `# noqa: C901`).
- `src/runtime/next/runtime_bridge.py:2556` / `:2563` / `:2575` — sync emit / coord commit / `origin.mission_path` (captured side effects).
- `kitty-specs/runtime-bridge-degod-01KX8M1C/data-model.md` §DecideNextContext — the ~14-field frozen dataclass + 4 phases.
- `kitty-specs/runtime-bridge-degod-01KX8M1C/plan.md` IC-08 + Notes — phase-split, sub-sequence fallback.
- `kitty-specs/runtime-bridge-degod-01KX8M1C/contracts/parity-oracle.md` — the acceptance-gate oracle + `decide_next` side effects.
- `kitty-specs/runtime-bridge-degod-01KX8M1C/spec.md` — FR-010, FR-005, FR-004, SC-002.

## Activity Log

- 2026-07-12T00:26:05Z – user – shell_pid=2956749 – Moved to for_review
- 2026-07-12T00:51:43Z – user – shell_pid=2956749 – Moved to approved
