---
work_package_id: WP08
title: Reachability as named sets, per channel
dependencies:
- WP01
- WP06
requirement_refs:
- C-006
- C-008
- C-009
- FR-016
- NFR-002
- NFR-004
- NFR-005
planning_base_branch: feat/doctrine-delivery-reachability
merge_target_branch: feat/doctrine-delivery-reachability
branch_strategy: Planning artifacts for this mission were generated on feat/doctrine-delivery-reachability. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/doctrine-delivery-reachability unless the human explicitly redirects the landing branch.
created_at: '2026-07-28T19:48:12Z'
subtasks:
- T042
- T043
- T044
- T045
- T046
- T047
phase: Phase 3 - Activation
history:
- at: '2026-07-28T19:48:12Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: doctrine-daphne
authoritative_surface: src/doctrine/drg/reachability.py
create_intent:
- src/doctrine/drg/reachability.py
- tests/doctrine/drg/test_reachability.py
execution_mode: code_change
model: ''
owned_files:
- src/doctrine/drg/reachability.py
- tests/doctrine/drg/reachability_fixtures/**
- tests/doctrine/drg/test_reachability.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# WP08 — Reachability as named sets, per channel

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the profile named in the frontmatter, and behave
according to its guidance before parsing the rest of this prompt.

- **Profile**: `doctrine-daphne`
- **Role**: `implementer`
- **Agent/tool**: `claude`

Resolve it with **`spec-kitty agent profile show doctrine-daphne`** — the *resolved* definition. **Do
not read the raw `*.agent.yaml`**: the unresolved base drops the lineage this profile depends on, which
is precisely the defect this mission fixes.

---

## Objective

Reachability becomes an **asserted named set per delivery channel**, computed by **calling** the
canonical traversal — never reimplementing it. The count becomes a membership assertion, so a nominal
wiring cannot pass as a fix.

## Context — the trap this WP exists to close, and the one it must not fall into

**The trap it closes**: PR #3007 wired 8 orphans; only 4 became reachable from any action, because 4
attached to sources that were themselves unreachable. `_ACTIVATED_BUT_UNREACHABLE`
(`test_extractor_projection.py:299`) measures **edge incidence**, not reachability, despite its name.

**The trap it must not fall into**: **every hand-rolled BFS in this mission's history produced a
different number** (91 / 88 / 78 / 59 / 103). The assertion **must call
`doctrine.drg.query.resolve_context`**, not a reimplementation. `resolve_context` walks `scope` at
depth 1, then `requires` transitively from directly-scoped artefacts only, then `suggests` capped at
depth, and never follows `instantiates`.

### Two channels, two traversals (this is the load-bearing design)

| channel | traversal | seed |
|---|---|---|
| **action** | `resolve_context`, at d=1 (compact, steady state, stricter) and d=2 (bootstrap) | action nodes |
| **profile** | `walk_edges` over `{requires, specializes_from}` | activated agent profiles |

**Profiles are NOT a `resolve_context` seed set.** Measured: `agent_profile` nodes have 97 outbound
`requires`, 4 `specializes_from`, and **zero outbound `scope`**, so `resolve_context` from a profile
returns 0 artefacts at every depth. The profile channel is a separate traversal. Do not fold it into
`resolve_context` — it will silently measure nothing.

Read [`contracts/activation-delivery.md`](../contracts/activation-delivery.md) §3 (R-1 to R-6), and
[`research/post-plan-squad-findings.md`](../research/post-plan-squad-findings.md) §1.

**Depends on WP06** — the identifier normalization must land first, or the pinned set includes ~25
not-a-node entries that C-009 bars from progress.

## Subtasks

### T042 — Action-channel reachability helper
1. `src/doctrine/drg/reachability.py`: a function that **calls** `resolve_context` for a seed set at a
   given depth and returns the set of reachable urns.
2. No BFS. If you find yourself writing `walk_edges` for the action channel, stop — use
   `resolve_context`.

### T043 — Profile-channel reachability helper [P]
1. A separately named function walking `{requires, specializes_from}` from activated profile seeds via
   `walk_edges`.
2. Name it so no one mistakes it for the action traversal.

### T044 — Rename the incidence set; land the named sets beside it
1. Rename `_ACTIVATED_BUT_UNREACHABLE` -> `_ACTIVATED_BUT_ORPHANED` (it measures incidence). Same for
   `_orphan_urns` semantics — keep the incidence check, correct its name.
2. Land the real per-channel reachability sets **beside** it, as pinned named frozensets with
   membership assertions.

### T045 — Assert action-channel membership at d=1 and d=2
1. Two pinned sets: `_ACTION_UNREACHABLE_D1`, `_ACTION_UNREACHABLE_D2`.
2. Membership assertions — a new unreachable artefact fails the suite **naming itself**, not a count.
3. Partition per WP06: `not-a-node` entries excluded from any progress claim (C-009).

### T046 — Assert profile-channel membership
1. `_PROFILE_UNREACHABLE` pinned set, membership assertion.
2. Note the conditional-profile shape (`profile` is `str | None`); assert under a named, non-fail-open
   configuration.

### T047 — Red-first: nominal wiring is caught
1. In a fixture, wire an artefact to a source that is itself unreachable. The reachability assertion
   must report it **unreachable** — cascade/incidence would report it fixed.
2. This is the WP's reason to exist; write it first and watch it catch the PR #3007 failure shape.

## Branch Strategy

Planning base and merge target `feat/doctrine-delivery-reachability`. Depends on WP01 (a clean graph
serialization) and WP06 (normalization). `spec-kitty implement WP08` resolves the workspace.

**File-ownership note**: `test_extractor_projection.py` is shared with WP07 (repoints
`_charter_activated_urns`) and WP09 (consumes the pinned sets). Serialize within one lane, or split the
rename (yours) from the repoint (WP07's) carefully.

## Test strategy

```bash
PWHEADLESS=1 pytest tests/doctrine/drg/test_reachability.py tests/doctrine/drg/migration/test_extractor_projection.py -q
```

## Definition of Done

- [ ] The action helper **calls `resolve_context`**; no reimplemented walk exists in `src/`
- [ ] The profile helper is a distinct `walk_edges` traversal, distinctly named
- [ ] `_ACTIVATED_BUT_UNREACHABLE` is renamed to reflect that it measures incidence
- [ ] Per-channel reachability sets are pinned frozensets with **membership** assertions
- [ ] A nominally-wired-but-unreachable artefact is reported unreachable (T047, red-first)
- [ ] The `not-a-node` partition is excluded from progress (C-009)
- [ ] A red commit precedes each green commit (C-006)
- [ ] `ruff` + `mypy --strict` clean

## Risks

| Risk | Mitigation |
|---|---|
| Reimplementing the walk -> a fifth wrong number | Call `resolve_context`; DoD forbids a BFS in src |
| Folding profiles into `resolve_context` -> measures 0 | Separate `walk_edges` traversal |
| Renaming the incidence set but keeping its meaning ambiguous | Rename + comment; membership not cardinality |
| Pinning before WP06 lands | Dependency on WP06 |

## Reviewer guidance

1. `grep -rn "walk_edges\|scope.*requires.*suggests" src/doctrine/drg/reachability.py` — the action
   path must call `resolve_context`, not walk manually.
2. In a fixture, wire an orphan to an unreachable source; confirm it is reported unreachable.
3. Confirm the assertions are membership (name the artefact on failure), not count comparisons.
4. Confirm `not-a-node` entries are not counted as progress.
