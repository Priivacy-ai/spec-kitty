---
work_package_id: WP15
title: 'Progressive disclosure: navigable references and the fetch-everything hatch'
dependencies:
- WP10
requirement_refs:
- C-006
- C-011
- C-012
- FR-021
- FR-022
- NFR-002
- NFR-003
- NFR-005
planning_base_branch: feat/doctrine-delivery-reachability
merge_target_branch: feat/doctrine-delivery-reachability
branch_strategy: Planning artifacts for this mission were generated on feat/doctrine-delivery-reachability. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/doctrine-delivery-reachability unless the human explicitly redirects the landing branch.
created_at: '2026-07-28T19:48:12Z'
subtasks:
- T081
- T082
- T083
- T084
phase: Phase 4 - Delivery
history:
- at: '2026-07-28T19:48:12Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: architect-alphonso
authoritative_surface: tests/charter/test_progressive_disclosure.py
create_intent:
- tests/charter/test_progressive_disclosure.py
execution_mode: code_change
model: ''
owned_files:
- tests/charter/test_progressive_disclosure.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# WP15 — Progressive disclosure: navigable references and the fetch-everything hatch

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the profile named in the frontmatter, and behave
according to its guidance before parsing the rest of this prompt.

- **Profile**: `architect-alphonso`
- **Role**: `implementer`
- **Agent/tool**: `claude`

Resolve it with **`spec-kitty agent profile show architect-alphonso`**. **Do not read the raw
`*.agent.yaml`**.

---

## Objective

Make complete delivery **affordable**. Everything reachable is either delivered inline or **named with
the guidance that says when to fetch it** — never silently absent. This is the **default cadence**, and
it must be in force **before WP11 switches on delivery-on-every-load** (C-012), or that switch ships
184 artefacts' worth of inlined bodies at every action boundary.

Governed by [ADR 2026-07-28-1](../../../docs/adr/3.x/2026-07-28-1-progressive-disclosure-of-doctrine-context.md)
(**Accepted**).

## Context — why links, and why the edge already carries the guidance

NFR-003 forbids truncation (truncation is how the current defect hides), but 184 artefacts do not fit
a 32,000-token budget. **A link is not a truncation** — the artefact stays named and addressable, which
is the property NFR-003 protects. Completeness is satisfied by the **union of inlined and linked** ids
equalling `gate ∩ reachable`.

The `DRGEdge` already carries the fetch guidance:
- `when` — on `suggests` edges, **219 of 337 (65%)**, e.g. *"Use to verify the automated gates before
  handoff."* The other 118 render a **stated default**, so absence is visible, not blank.
- `reason` — on `requires`/`rejects`/`in_tension_with`.

Cadence follows the relation (C-011): **`requires` eager** (unconditional — inline the target),
**`suggests` linked** (conditional — emit the link with its `when`).

Read [ADR 2026-07-28-1](../../../docs/adr/3.x/2026-07-28-1-progressive-disclosure-of-doctrine-context.md)
in full, and NFR-003 as revised.

## Subtasks

### T081 — Emit `references[]` on the context DTO
1. Each artefact DTO returned from the charter context entrypoint gains a `references[]` element.
2. Each entry is `{id, relation, when, reason}` — the edge's own fields, unmodified.
3. Uncovered `suggests` edges render a **stated default** for `when`, never an empty string.

### T082 — `requires` eager, `suggests` linked — the default cadence
1. `requires` targets are delivered inline (eager).
2. `suggests` targets are emitted as links carrying `when` (lazy).
3. This is the default, not a mode. The bundle from WP10 feeds it.

### T083 — `--include-all` escape hatch
1. `spec-kitty charter context ... --include-all` materialises the entire reachable closure inline.
2. Its output is a **superset** of the progressive render for the same grain.
3. This is the safety property (ADR): progressive disclosure is never the reason governance failed to
   arrive.

### T084 — Red-first: named, fetchable, inlined by the hatch
1. Assert: the union of inlined ids and referenced ids equals the delivered set NFR-003 defines
   (completeness by naming).
2. Assert a linked artefact is retrievable by its id via the existing `--include` verb.
3. Assert `--include-all` output ⊇ the progressive render.
4. Write these red-first.

## Branch Strategy

Planning base and merge target `feat/doctrine-delivery-reachability`. Depends on WP10 (the bundle it
renders as links). **Blocks WP11 by binding constraint (C-012)** — WP11 must not land ahead of this.
`spec-kitty implement WP15` resolves the workspace.


**File-ownership note**: `src/charter/activation/context.py` is owned by **WP10** (single owner). Your edits to its render path are coordinated **out-of-map edits**, serialized safely behind the delivery chain by this WP's dependencies; record each with a one-line rationale.

## Test strategy

```bash
PWHEADLESS=1 pytest tests/charter/test_progressive_disclosure.py tests/charter/test_context.py -q
```

## Definition of Done

- [ ] `references[]` on the DTO, entries `{id, relation, when, reason}` from the edges
- [ ] `requires` inlined, `suggests` linked — as the **default** cadence
- [ ] Uncovered `suggests` edges render a stated default, not blank
- [ ] `--include-all` materialises the full closure; output ⊇ progressive render
- [ ] Union of inlined + linked ids equals `gate ∩ reachable` (completeness by naming)
- [ ] A red commit precedes each green commit (C-006)
- [ ] `ruff` + `mypy --strict` clean

## Risks

| Risk | Mitigation |
|---|---|
| A link nobody follows -> reaches nobody (the defect, one level up) | `--include-all` is the falsifiability hatch (in the decision, not an afterthought) |
| Landing after WP11 | Binding order C-012: WP15 before WP11 |
| 118 uncovered edges render blank | Stated default (T081) |
| Agents not instructed to fetch | Out of scope — #3056; affects utilization, not safety |

## Reviewer guidance

1. Confirm the union of inlined + linked equals the reachable-and-gated set — nothing is dropped.
2. Confirm `--include-all` is a strict superset.
3. Confirm `requires`/`suggests` cadence matches C-011.
4. Confirm WP15 is sequenced before WP11 in the lane plan.
