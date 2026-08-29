---
work_package_id: WP12
title: Profile channel delivery
dependencies:
- WP08
- WP11
requirement_refs:
- C-006
- C-007
- C-008
- FR-016
- FR-020
- NFR-002
- NFR-005
- NFR-006
planning_base_branch: feat/doctrine-delivery-reachability
merge_target_branch: feat/doctrine-delivery-reachability
branch_strategy: Planning artifacts for this mission were generated on feat/doctrine-delivery-reachability. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/doctrine-delivery-reachability unless the human explicitly redirects the landing branch.
created_at: '2026-07-28T19:48:12Z'
subtasks:
- T066
- T067
- T068
- T069
- T070
phase: Phase 4 - Delivery
history:
- at: '2026-07-28T19:48:12Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: doctrine-daphne
authoritative_surface: src/doctrine/agent_profiles/repository.py
create_intent:
- tests/charter/test_profile_channel_delivery.py
- tests/doctrine/agent_profiles/test_profile_resolution.py
execution_mode: code_change
model: ''
owned_files:
- src/doctrine/agent_profiles/repository.py
- tests/charter/test_profile_channel_delivery.py
- tests/doctrine/agent_profiles/test_profile_resolution.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# WP12 — Profile channel delivery

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the profile named in the frontmatter, and behave
according to its guidance before parsing the rest of this prompt.

- **Profile**: `doctrine-daphne`
- **Role**: `implementer`
- **Agent/tool**: `claude`

Resolve it with **`spec-kitty agent profile show doctrine-daphne`**. **Do not read the raw
`*.agent.yaml`** — this WP is *about* the fact that reading the raw profile drops the doctrine it
resolves. Live the fix.

---

## Objective

A loaded profile delivers **every kind it resolves** — profiles are how the implement loop hands
governance to an agent working a work package, and today they carry only directives and tactics.

## Context

`_render_profile_directives` / `_render_profile_tactics` (`context.py:2757-2758`) are the only profile
render paths. A profile that resolves a procedure, styleguide, toolguide, or asset reaches its agent
with none of them. `procedure:onboard-external-agent-to-pack` — reached from
`agent_profile:doctrine-daphne` by a `requires` edge — is the live instance, and it is PR #3007's own
exemplar fix arriving nowhere.

**The profile channel is a separate traversal** (WP08's profile helper), not a `resolve_context` seed
set: profiles have zero outbound `scope` edges. And `profile` is `str | None`, so the channel is
**conditional on caller configuration** — measure it under a named, non-fail-open configuration.

**Deciding which kinds a profile should deliver is a doctrine question, not only a render one.** Where
the profile schema does not attest that a kind belongs, **defer under C-007** rather than inventing it.

Read [`contracts/activation-delivery.md`](../contracts/activation-delivery.md) R-3, R-3a, R-3b.

## Subtasks

### T066 — Kind-coverage decision, attested not invented
1. Determine which kinds a loaded profile legitimately delivers, from what the profile schema and its
   resolution actually attest (its `operating-procedures`, its cited tactics/styleguides).
2. Where a kind is not attested, record it as a C-007 deferral — do not invent the relationship.

### T067 — Render every attested kind
1. Extend the profile render path beyond directives and tactics to the attested kinds.
2. Coordinate the render boundary with WP11 (shared `context.py`); you own the profile section.

### T068 — Deliver the exemplar procedure
1. `procedure:onboard-external-agent-to-pack`, resolved from `doctrine-daphne`, reaches an agent under
   that profile. This is the concrete proof.

### T069 — Guard the conditional-profile shape
1. `profile` is `str | None`. Assert delivery under a named profile; do not let an absent profile
   silently fall into a fail-open path (the shape FR-018 retires for activation keys).

### T070 — Red-first
1. An agent under a loaded profile receives a profile-resolved procedure. Write it red first — today it
   receives none.

## Branch Strategy

Planning base and merge target `feat/doctrine-delivery-reachability`. Depends on WP08 (the profile
reachability helper). Parallel with WP10/WP11 on the render surface — **file collision** on
`context.py`, so serialize within the lane. `spec-kitty implement WP12` resolves the workspace.


**File-ownership note**: `src/charter/activation/context.py` is owned by **WP10** (single owner). Your edits to its render path are coordinated **out-of-map edits**, serialized safely behind the delivery chain by this WP's dependencies; record each with a one-line rationale.

## Test strategy

```bash
PWHEADLESS=1 pytest tests/charter/test_profile_channel_delivery.py tests/doctrine/agent_profiles/test_profile_resolution.py -q
```

## Definition of Done

- [ ] The kind-coverage decision is attested by the profile schema, not invented
- [ ] Attested kinds beyond directives/tactics render in the profile channel
- [ ] The exemplar procedure reaches an agent under `doctrine-daphne`
- [ ] The conditional-profile shape does not fail open
- [ ] Unattested kinds are C-007 deferrals, recorded
- [ ] A red commit precedes each green commit (C-006)
- [ ] `ruff` + `mypy --strict` clean

## Risks

| Risk | Mitigation |
|---|---|
| Inventing a kind→profile relationship | Attestation requirement; defer under C-007 |
| Folding profiles into `resolve_context` | Use WP08's separate profile traversal |
| Fail-open on absent profile | T069 guards it |

## Reviewer guidance

1. Load `doctrine-daphne` and confirm its resolved procedure reaches the agent context.
2. Confirm each newly-delivered kind is attested by the profile, not adjacency.
3. Confirm an absent profile does not fall into a fail-open render.
