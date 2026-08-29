---
work_package_id: WP03
title: 'Pack lineage: delegated resolution'
dependencies:
- WP01
- WP02
requirement_refs:
- FR-006
- FR-007
planning_base_branch: feat/pack-metadata-manifest-unification
merge_target_branch: feat/pack-metadata-manifest-unification
branch_strategy: Planning artifacts for this mission were generated on feat/pack-metadata-manifest-unification. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/pack-metadata-manifest-unification unless the human explicitly redirects the landing branch.
subtasks:
- T011
- T012
- T013
history:
- at: '2026-08-16'
  note: Authored at /spec-kitty.tasks. Parallel with WP04 after WP02.
agent_profile: python-pedro
authoritative_surface: src/specify_cli/doctrine/
create_intent:
- src/specify_cli/doctrine/pack_lineage.py
- tests/doctrine/test_pack_lineage.py
- tests/architectural/test_pack_lineage_no_parallel_resolver.py
execution_mode: code_change
owned_files:
- src/specify_cli/doctrine/pack_lineage.py
- tests/doctrine/test_pack_lineage.py
- tests/architectural/test_pack_lineage_no_parallel_resolver.py
role: implementer
tags: []
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile

Load your assigned profile first: `/ad-hoc-profile-load python-pedro` (or `spec-kitty agent profile show python-pedro` + `spec-kitty charter context --action implement --json`).

## Objective

Resolve pack lineage **without a second resolver**: feed `parent_pack` edges to the existing `org_extends.resolve_extends_order` via a data-only adapter, fail-closed on unresolvable edges, and pin the no-parallel-resolver ratchet. This is NFR-001 / C-002 — the mission's central anti-goal (no second lineage authority).

## Context

Design: [plan.md](../plan.md) IC-05 (lineage-authority decision) + [data-model.md](../data-model.md). `org_extends.resolve_extends_order` (`src/charter/activation/org_extends.py:72`) is generic over `str` keys but is fed a **name→name** map today from the live `extends:` field (`org_charter.py:517,525`). The decision: `extends:` (name) stays the **live** authority; `parent_pack` (id) resolves through an adapter; full migration to `parent_pack`-as-sole-source is deferred until `pack_id` backfill is universal.

## Subtasks

### T011 — id→name adapter into `org_extends`
Create `src/specify_cli/doctrine/pack_lineage.py`: a **data-only** adapter that builds a `{pack_id: parent_pack}` edge map and resolves each `pack_id` **to its pack `name`** — the live resolvable key `org_extends.resolve_extends_order` is fed today (name→name, `org_charter.py:517,525`) — then calls the resolver. Do **not** invent a second identity map (paula SF-2). **No new traversal/walker** — order comes only from `org_extends` (reuse its cycle detection). Test `test_pack_lineage.py` builds **in-memory `PackDescriptor` fixtures** (from WP02's model) and must **NOT** read `packs/built-in/pack.yaml` (that file is WP04-owned; reading it would serialize lane-c behind lane-d and break the WP03∥WP04 parallelism — priti SF-1). Assert a fixture parent chain resolves in the same order the name-keyed path would.

### T012 — Fail-closed edges + positive read-back [P]
An unresolvable `parent_pack` (e.g. a pre-backfill pack with no `pack_id`) and an unknown `accompanies_doctrine_pack` target **fail closed** — surface a structured error (mirror `org_extends`' `ExtendsBaseNotFoundError`), never a silent no-op / inert field. Tests (in-memory fixtures): (a) unresolvable edge raises; does not silently return an empty order; (b) **FR-007 positive read-back** — a *set* `accompanies_doctrine_pack` resolves to its doctrine pack at the pack level (US2 scenario 3), not just the error path.

### T013 — No-parallel-resolver arch ratchet [P]
Create `tests/architectural/test_pack_lineage_no_parallel_resolver.py`: an **AST import/call scan** asserting that lineage resolution routes only through `org_extends.resolve_extends_order` and that no new order-producing traversal is introduced in the pack modules. Must be **falsifiable** — inject a fake second walker in a fixture and confirm the test fails.

## Definition of Done
- `parent_pack` resolves through `org_extends` with 0 new resolvers; unresolvable/unknown edges fail closed; the arch ratchet is non-vacuous (fails on an injected walker); `ruff`/`mypy` clean.

## Reviewer guidance
The load-bearing check: confirm there is genuinely **no second walker** and the ratchet would catch one. Confirm `extends:` remains the live authority (this WP does not retire it).
