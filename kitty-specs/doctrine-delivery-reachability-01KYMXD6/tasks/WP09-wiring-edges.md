---
work_package_id: WP09
title: Wiring edges that actually reach
dependencies:
- WP08
requirement_refs:
- C-006
- C-007
- C-008
- FR-015
- NFR-002
- NFR-004
- NFR-005
planning_base_branch: feat/doctrine-delivery-reachability
merge_target_branch: feat/doctrine-delivery-reachability
branch_strategy: Planning artifacts for this mission were generated on feat/doctrine-delivery-reachability. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/doctrine-delivery-reachability unless the human explicitly redirects the landing branch.
created_at: '2026-07-28T19:48:12Z'
subtasks:
- T048
- T049
- T050
- T051
- T052
phase: Phase 3 - Activation
history:
- at: '2026-07-28T19:48:12Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: doctrine-daphne
authoritative_surface: src/doctrine/drg/migration/hand_authored_overlay.py
create_intent:
- docs/plans/doctrine/delivery-reachability-wiring-table.md
execution_mode: code_change
model: ''
owned_files:
- src/doctrine/drg/migration/hand_authored_overlay.py
- src/doctrine/directives/**
- src/doctrine/tactics/**
- src/doctrine/procedures/**
- docs/plans/doctrine/delivery-reachability-wiring-table.md
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# WP09 — Wiring edges that actually reach

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the profile named in the frontmatter, and behave
according to its guidance before parsing the rest of this prompt.

- **Profile**: `doctrine-daphne`
- **Role**: `implementer`
- **Agent/tool**: `claude`

Resolve it with **`spec-kitty agent profile show doctrine-daphne`**. **Do not read the raw
`*.agent.yaml`** — the unresolved base drops the lineage this mission delivers.

---

## Objective

Author the edges that make activated artefacts **genuinely reachable**, with each proposed source's
own reachability **measured, not assumed** — so this WP does not reproduce the PR #3007 failure it
exists to correct.

## Context — the obvious/non-obvious line is computable, not a matter of taste

C-007's two-part test for whether an unreachable artefact is "obvious" (in scope) vs deferred:

> **obvious** iff (a) the relationship is **attested in the artefact's own text** — not inferred from
> topic adjacency — **and** (b) the proposed source is **itself action-reachable** under the WP08
> measure, or the edge is a `scope` edge from an action node.

Everything failing (b) is C-007-deferred to an after-mission operator interview. Without (b),
"obvious" collapses into implementer taste — which is exactly how PR #3007 wired 4 edges to
unreachable sources.

**In scope by consequence of the asset-delivery ruling**: the `common-docs` cluster.
`asset:common-docs-structural-lint` has four inbound `requires` edges and **all four sources are
unreachable** — a strongly-connected island no action scopes. WP10/WP11 deliver assets; without wiring
this cluster, the delivery path ships and the only shipped asset still fails to arrive.

**Destination**: edges land where the overlay authors them (`hand_authored_overlay.py` /
`_CURATED_ARTIFACT_EDGES`). **Mission B2 retires that generator** — record the handoff so B2 inherits a
known migration, not a surprise. Authoring edges regenerates up to 14 `*.graph.yaml` fragments; every
count that moves is a composition-ledger row (NFR-004).

Read [`contracts/activation-delivery.md`](../contracts/activation-delivery.md) FR-015 table shape, and
[`research/drg-writer-and-reachability-inventory.md`](../research/drg-writer-and-reachability-inventory.md) §3.

## Subtasks

### T048 — Build the FR-015 wiring table
1. Create `docs/plans/doctrine/delivery-reachability-wiring-table.md`: one row per candidate artefact — `{urn, proposed
   inbound source, source_action_reachable (measured), disposition}`.
2. `source_action_reachable` is a **measured value from WP08's helper**, not a judgement.
3. Disposition is `wire` (passes C-007 a+b) or `defer` (fails b).

### T049 — Author the edges that pass C-007
1. For each `wire` row, author the edge in the overlay.
2. Re-run WP08's reachability assertion — the artefact must now be action-reachable, not merely
   edge-incident.

### T050 — Wire the `common-docs` cluster
1. The cluster's four sources are all unreachable. Author the edge(s) that bring at least one source
   into the action-reachable set, so the asset transitively arrives.
2. If no source can pass C-007 without inventing a relationship, that is a **defer** with a recorded
   reason — say so; do not invent an edge to force the asset through.

### T051 — Ledger the composition deltas (NFR-004)
1. Each authored edge moves node/edge counts and possibly relation histograms. Add a composition-ledger
   row per delta — including relation-only moves where cardinality is unchanged.
2. No golden count moves without a ledger row.

### T052 — Record the deferred set
1. Every `defer` row goes into a recorded list for the after-mission operator interview (C-007).
2. This is not a filed issue yet — it is the operator's decision surface.

## Branch Strategy

Planning base and merge target `feat/doctrine-delivery-reachability`. Depends on WP08 (the reachability
measure). `spec-kitty implement WP09` resolves the workspace.

## Test strategy

```bash
PWHEADLESS=1 pytest tests/doctrine/drg/test_reachability.py tests/doctrine/drg/migration/test_extractor_projection.py -q
```

## Definition of Done

- [ ] Every `wire` row's artefact is **action-reachable** under WP08's measure after landing — not just edge-incident
- [ ] Every row carries a **measured** `source_action_reachable`, not an assertion
- [ ] The `common-docs` cluster is wired, or its non-wiring is a recorded `defer` with a reason
- [ ] Every moved count has a composition-ledger row (NFR-004)
- [ ] The deferred set is recorded for the operator interview (C-007)
- [ ] The B2 handoff (curated-table retirement) is documented
- [ ] A red commit precedes each green commit (C-006)

## Risks

| Risk | Mitigation |
|---|---|
| Wiring to an unreachable source (the PR #3007 failure) | C-007(b) + re-run WP08's assertion |
| Inventing a relationship to force the asset through | Attestation test C-007(a); defer instead |
| Golden counts move silently | NFR-004 ledger row per delta |
| B2 inherits an unknown migration | Record the handoff |

## Reviewer guidance

1. For each wired artefact, run WP08's measure and confirm it is **action-reachable**, not incident.
2. Confirm each `source_action_reachable` is a real measurement.
3. Confirm no edge was authored on topic adjacency without textual attestation.
4. Confirm the ledger has a row for every moved count.
