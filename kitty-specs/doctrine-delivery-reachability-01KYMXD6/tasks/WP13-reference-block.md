---
work_package_id: WP13
title: Reference block distribution and resolvable pointers
dependencies:
- WP11
requirement_refs:
- C-006
- FR-013
- FR-014
- NFR-002
- NFR-005
planning_base_branch: feat/doctrine-delivery-reachability
merge_target_branch: feat/doctrine-delivery-reachability
branch_strategy: Planning artifacts for this mission were generated on feat/doctrine-delivery-reachability. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/doctrine-delivery-reachability unless the human explicitly redirects the landing branch.
created_at: '2026-07-28T19:48:12Z'
subtasks:
- T071
- T072
- T073
- T074
- T075
phase: Phase 5 - Polish
history:
- at: '2026-07-28T19:48:12Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: tests/charter/test_reference_block.py
create_intent:
- tests/charter/test_reference_block.py
execution_mode: code_change
model: ''
owned_files:
- tests/charter/test_reference_block.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# WP13 — Reference block distribution and resolvable pointers

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the profile named in the frontmatter, and behave
according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

Resolve it with **`spec-kitty agent profile show python-pedro`**. **Do not read the raw `*.agent.yaml`**.

---

## Objective

Every pointer an agent is handed **opens**, and the block's composition varies by action instead of
being exhausted by a fixed kind order.

## Context

- **Two cap sites, not one**: `context.py:1169` (live, `filtered_references[:10]`) and `:1531` inside
  `_render_bootstrap`. The `:1531` renderer is **called from nowhere in `src/`** — only from
  `tests/charter/test_context.py:815`. It is a render path reachable only from the test suite, itself
  an instance of this mission's thesis. **Ruling: delete it.** If you find a live caller, that is a
  finding, not a reason to keep it.
- **The cap is order-rigged.** `_filter_references_for_action` (`:1484`) is a **no-op for every
  doctrine kind** (213 -> 213), and the emit order is fixed: user + 8 paradigms + `DIRECTIVE_001` fill
  slots 1-10; the first tactic sits at index 34. So filtering is not the fix — **distribution** is.
- **No test pins either cap** (proven by mutation: `[:10] -> [:1]` leaves the suite unchanged). So the
  criteria need new coverage, not an adjusted assertion.
- **`.kittify/charter/_LIBRARY/` does not exist**, so all 10 emitted pointers are dead today.
- SC-006 needs a **non-vacuity floor** or it passes over an emitted set of zero.

Read [`contracts/activation-delivery.md`](../contracts/activation-delivery.md) §4 (F-1 to F-6).

**Independent — no inbound dependency.** May land any time. Shares `context.py` with the delivery WPs
(file collision), so serialize within the lane.

## Subtasks

### T071 — Per-kind distribution replacing the order-rigged cap
1. Replace both `[:10]` windows with a selection distributed across kinds, so later kinds are reachable.
2. The emitted set for an action is not exhausted by the first kind in a fixed order.

### T072 — Delete the test-only `_render_bootstrap`
1. Remove `_render_bootstrap` (`:1513`) and its cap at `:1531`. Update `test_context.py:815` to target
   the live renderer.
2. If a live `src/` caller surfaces, stop and report it — do not keep the dead renderer.

### T073 — Resolvable pointers
1. Every emitted pointer resolves to an existing document. The `_LIBRARY` path scheme must point at
   something real, or the pointers must be constructed from resolvable locations.

### T074 — Non-vacuity floor and cross-action variation
1. Assert a stated minimum number of pointers emitted per action for `software-dev`.
2. Assert the emitted sets differ across at least two actions.

### T075 — Red-first: mutating the cap turns a test red
1. Today `[:10] -> [:1]` changes nothing. After this WP, a mutation to the distribution must fail a
   test. Write it red first.

## Branch Strategy

Planning base and merge target `feat/doctrine-delivery-reachability`. No inbound dependency. File
collision with WP10/WP11/WP12/WP15 on `context.py` — serialize within the lane. `spec-kitty implement
WP13` resolves the workspace.


**File-ownership note**: `src/charter/context.py` is owned by **WP10** (single owner). Your edits to its render path are coordinated **out-of-map edits**, serialized safely behind the delivery chain by this WP's dependencies; record each with a one-line rationale.

## Test strategy

```bash
PWHEADLESS=1 pytest tests/charter/test_reference_block.py tests/charter/test_context.py -q
```

## Definition of Done

- [ ] Both cap sites addressed; `_render_bootstrap` deleted (or a live caller reported)
- [ ] Selection distributed across kinds; later kinds reachable
- [ ] Every emitted pointer resolves
- [ ] SC-006 non-vacuity floor asserted; sets differ across two actions
- [ ] Mutating the distribution turns a test red (the cap is now pinned)
- [ ] A red commit precedes each green commit (C-006)
- [ ] `ruff` + `mypy --strict` clean

## Risks

| Risk | Mitigation |
|---|---|
| Fixing one cap site | Both named (T071, T072) |
| "Every pointer resolves" passes vacuously | Non-vacuity floor (T074) |
| Deleting a live renderer | It has no `src/` caller; verify and report if it does |

## Reviewer guidance

1. Render the block for two actions; confirm the emitted sets differ and every pointer opens.
2. Confirm `_render_bootstrap` is gone and nothing in `src/` referenced it.
3. Mutate the distribution; confirm a test goes red.
