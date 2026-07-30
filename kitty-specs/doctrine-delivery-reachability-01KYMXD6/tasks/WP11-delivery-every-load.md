---
work_package_id: WP11
title: Delivery on every load
dependencies:
- WP15
requirement_refs:
- C-006
- C-012
- FR-010
- FR-012
- NFR-002
- NFR-003
- NFR-005
- NFR-007
planning_base_branch: feat/doctrine-delivery-reachability
merge_target_branch: feat/doctrine-delivery-reachability
branch_strategy: Planning artifacts for this mission were generated on feat/doctrine-delivery-reachability. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/doctrine-delivery-reachability unless the human explicitly redirects the landing branch.
created_at: '2026-07-28T19:48:12Z'
subtasks:
- T059
- T060
- T061
- T062
- T063
- T064
- T065
phase: Phase 4 - Delivery
history:
- at: '2026-07-28T19:48:12Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/charter/compact.py
create_intent:
- tests/charter/test_every_load_delivery.py
execution_mode: code_change
model: ''
owned_files:
- src/charter/compact.py
- src/specify_cli/cli/commands/agent/workflow.py
- src/specify_cli/cli/commands/agent/workflow_executor.py
- tests/charter/test_every_load_delivery.py
- tests/agent/test_workflow_charter_context.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# WP11 — Delivery on every load

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the profile named in the frontmatter, and behave
according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

Resolve it with **`spec-kitty agent profile show python-pedro`**. **Do not read the raw `*.agent.yaml`**.

---

## Objective

Governance is in force on **every** context load, not once per project, and the callers that omit the
mission-type grain supply it.

**This WP switches on delivery-on-every-load. It must not land ahead of WP15** (C-012) — otherwise it
ships 184 artefacts' worth of inlined bodies at every boundary, because WP15 is what makes them links.

## Context — four traps

- **"The compact returns" is four sites in two functions**: `context.py:208` (action not in
  `BOOTSTRAP_ACTIONS`, returns before state is prepared), `:237` (depth below minimum), and `:3201` /
  `:3207` in the **`--json` payload builder**, which has its own `mode` handling and its own bundle
  call at `:3213`. The `--json` path is where the reproduction observes the defect and where SC-001/002
  are measured. Miss it and the fix is half-applied.
- **`depth` means two things.** `_EXTENDED_CONTEXT_DEPTH = 3` gates styleguide/toolguide rendering
  (`:1149-1157`), and `resolve_context`'s docstring says depth "also controls extended artifact
  inclusion". At the delivered depths, the two kinds this mission delivers are gated out. Retire or
  repoint that gate, and split the overloaded parameter.
- **`CompactView` carries two kinds** (`compact.py:38`, docstring "the contract surface");
  `_render_compact_governance` (`:2788`) accepts only `directive_ids`/`tactic_ids`. Widening the
  steady-state rail is a signature change and a contract-surface widening. Assertions read the
  **rendered compact text**, not the bundle.
- **`prompt_builder` already supplies the grain correctly** via `build_with_scope` — do not "fix" it.
  Only the two callers `workflow.py:738` and `workflow_executor.py:459` omit it. And removing grain
  forwarding from `scope_router.py:71` currently breaks **no test** — add coverage, do not assume it.

**NFR-007**: the ~982 ms -> ~1.94 s latency is **accepted, not gated**. Measure and record it; do not
add a caching obligation (the memoization option is on record in the plan if a later mission wants it).

Read [`contracts/activation-delivery.md`](../contracts/activation-delivery.md) §2 (B-3, B-6 to B-9).

## Subtasks

### T059 — Retire or repoint `_EXTENDED_CONTEXT_DEPTH`
1. The kinds this mission delivers must not be gated out by a depth threshold. Retire the gate, or
   repoint it, and split the overloaded `depth` parameter (a `suggests` hop cap and a render verbosity
   tier are two concepts).

### T060 — Deliver on every load at all four sites
1. All four compact-return sites deliver the bundle rather than returning empty. Include the two in the
   `--json` builder.
2. This is a control-flow change: the compact returns currently fire before the bundle is computed.

### T061 — Widen the compact rail
1. `CompactView` / `_render_compact_governance` carry every kind, not two. This widens a documented
   contract surface — update the surface and its tests deliberately.

### T062 — Supply the grain at the two omitting callers (FR-012 grain half)
1. `workflow.py:738` and `workflow_executor.py:459` supply the mission-type grain.
2. `prompt_builder` is out of scope — it already forwards. The **error half** of FR-012 is WP07's.

### T063 — Assert delivery through the shipped command surface
1. SC-001/002 assertions run through `spec-kitty agent workflow` (the shipped surface), **not** through
   `build_charter_context` directly. A test that supplies the grain itself proves nothing about the CLI.
2. This is US3 scenario 9.

### T064 — Record the latency delta (NFR-007)
1. Measure steady-state render before/after and record the figures in the mission (plan already carries
   the baseline). Accepted, not gated.

### T065 — Red-first: present on load two
1. An activated artefact present on the first load is present on a subsequent load. Write it red first —
   today the second load renders zero.

## Branch Strategy

Planning base and merge target `feat/doctrine-delivery-reachability`. **Depends on WP15** (links are
the default before every-load turns on). `spec-kitty implement WP11` resolves the workspace.

**File-ownership note**: **`src/charter/context.py` is owned by WP10** (single owner — it cannot be
co-owned). Your every-load/render edits to `context.py` are coordinated **out-of-map edits**, safe
because the dependency chain WP10 → WP15 → WP11 serializes them behind WP10; record each with a
one-line rationale. You **own** `compact.py` and the two workflow callers. Extract helpers, do not grow
`context.py` net.

## Test strategy

```bash
PWHEADLESS=1 pytest tests/charter/test_every_load_delivery.py tests/charter/test_context.py tests/charter/test_compact.py tests/agent/test_workflow_charter_context.py -q
```

## Definition of Done

- [ ] All four compact-return sites deliver, including the two in the `--json` builder
- [ ] `_EXTENDED_CONTEXT_DEPTH` no longer gates out delivered kinds; the overloaded param is split
- [ ] The compact rail carries every kind; its contract surface is updated deliberately
- [ ] The two omitting callers supply the grain; `prompt_builder` is untouched
- [ ] SC-001/002 assert through the **shipped command surface**
- [ ] An artefact present on load one is present on load two (red-first)
- [ ] The latency delta is measured and recorded (NFR-007, accepted)
- [ ] WP15 landed first (C-012)
- [ ] `ruff` + `mypy --strict` clean; `context.py` did not grow net

## Risks

| Risk | Mitigation |
|---|---|
| Landing before WP15 -> context explosion | Binding order C-012 |
| Fixing only two of four compact returns | T060 names all four including `--json` |
| Asserting via `build_charter_context` | T063 asserts through the CLI |
| "Fixing" `prompt_builder` (already correct) | Out of scope; only the two callers |

## Reviewer guidance

1. Load context twice through the CLI; confirm the second load is non-empty.
2. Confirm all four compact-return sites deliver, including `--json`.
3. Confirm styleguides/toolguides now render (depth gate retired).
4. Confirm the latency figure is recorded and no caching was silently added or demanded.
