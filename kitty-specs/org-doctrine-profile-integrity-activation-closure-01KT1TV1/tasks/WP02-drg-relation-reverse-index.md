---
work_package_id: WP02
title: DRG relation vocabulary + reverse index
dependencies: []
requirement_refs:
- FR-001
- FR-002
tracker_refs: []
planning_base_branch: mission/org-doctrine-profile-integrity-activation-closure
merge_target_branch: mission/org-doctrine-profile-integrity-activation-closure
branch_strategy: Planning artifacts for this mission were generated on mission/org-doctrine-profile-integrity-activation-closure. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into mission/org-doctrine-profile-integrity-activation-closure unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-org-doctrine-profile-integrity-activation-closure-01KT1TV1
base_commit: 6dfb443a16ab646f007302334a5d6a26aceb93e3
created_at: '2026-06-01T22:53:02.900340+00:00'
subtasks:
- T005
- T006
- T007
- T008
agent: "claude:opus:python-pedro:implementer"
shell_pid: "1687431"
history:
- at: '2026-06-01T16:49:18Z'
  actor: claude
  event: created
agent_profile: python-pedro
authoritative_surface: src/doctrine/drg/models.py
execution_mode: code_change
mission_slug: org-doctrine-profile-integrity-activation-closure-01KT1TV1
owned_files:
- src/doctrine/drg/models.py
- src/doctrine/drg/query.py
- tests/doctrine/test_drg_relations.py
role: implementer
tags: []
---

# WP02 — DRG relation vocabulary + reverse index

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load python-pedro
```

## Objective

Add the `specializes_from` relation (FR-001) as a first-class DRG relation distinct from `delegates_to` runtime handoff (FR-002), and add a reverse-adjacency accessor `DRGGraph.edges_to` that Wave 3 cascade deactivation (WP11) needs. Per C-009 the DRG is the canonical relationship model; this WP makes the vocabulary and traversal primitives ready.

## Context

- Spec: FR-001, FR-002; research R-011-A (no default-include traversal exists today; `DELEGATES_TO` has zero DRG consumers, so the no-leak property must be guarded by test).
- Data model: §2. Contract: [../contracts/wave0-foundation.md](../contracts/wave0-foundation.md) C0.2, C0.4 (edges_to).

### Code map

- `src/doctrine/drg/models.py:47` `Relation` StrEnum (`REQUIRES`, `SUGGESTS`, `DELEGATES_TO`, `ENHANCES`, `OVERRIDES`, ...). `DRGGraph.edges_from` at `:132`.
- `src/doctrine/drg/query.py:57` `walk_edges` (opt-in by relation set), `resolve_transitive_refs`.

## Branch Strategy

- Planning/base + merge target: `mission/org-doctrine-profile-integrity-activation-closure`. No dependencies — can start immediately (parallel with WP01/WP13).

## Subtasks

### T005 — Add `Relation.SPECIALIZES_FROM`

**Steps**:
1. Add `SPECIALIZES_FROM = "specializes_from"` to `Relation` (`models.py:47`).
2. Update the enum docstring to describe lineage vs delegation/enhancement/override/replacement (anchor for FR-004 docs in WP07).

**Validation**: - [ ] `Relation.SPECIALIZES_FROM.value == "specializes_from"`; - [ ] distinct from `DELEGATES_TO`.

### T006 — `DRGGraph.edges_to` reverse adjacency [P]

**Steps**:
1. Add `edges_to(self, urn: str, relation: Relation | None = None) -> list[DRGEdge]` returning incoming edges (mirror of `edges_from`).
2. Keep it O(E) scan (parity with `edges_from`); do not pre-build an index unless a perf test requires it.

**Validation**: - [ ] returns incoming edges; optional relation filter works; - [ ] `mypy` clean.

### T007 — No-leak regression test (FR-002)

**Purpose**: Guard the invariant that lineage never appears as delegation, since a future caller could query `DELEGATES_TO`.

**Steps**: In `tests/doctrine/test_drg_relations.py`, build a `DRGGraph` with a `specializes_from` edge A→B and no delegation edges; assert `edges_from(A, Relation.DELEGATES_TO) == []` and `walk_edges(graph, {A}, {Relation.DELEGATES_TO})` returns nothing reachable via the lineage edge.

**Validation**: - [ ] test fails if someone aliases lineage into delegation.

### T008 — Unit tests: edges_to + enum

**Steps**: Cover `edges_to` (with/without relation filter, no incoming edges case) and the enum membership.

**Validation**: - [ ] `pytest tests/doctrine/test_drg_relations.py` green; ruff/mypy clean.

## Definition of Done

- [ ] `SPECIALIZES_FROM` added; `edges_to` implemented; no-leak guard test present and green.
- [ ] CC-2 gates pass. No changes to `charter/drg.py` (that is WP03).

## Risks

- Adding the enum member alone is safe (StrEnum); ensure no exhaustive match statement elsewhere breaks — grep for `match`/`if relation ==` over `Relation` and confirm new member is handled or ignored gracefully (note findings for WP03/WP11).

## Reviewer Guidance (reviewer-renata)

- Confirm the no-leak test genuinely exercises a `DELEGATES_TO` query against a lineage-only graph.
- Confirm `edges_to` semantics mirror `edges_from` exactly (direction inverted).

## Activity Log

- 2026-06-01T17:29:12Z – claude:opus:python-pedro:implementer – shell_pid=1545161 – Assigned agent via action command
- 2026-06-01T17:33:05Z – claude:opus:python-pedro:implementer – shell_pid=1545161 – WP02 implementation COMPLETE and committed (RED 74667179b, GREEN 21047eac0): SPECIALIZES_FROM relation + DRGGraph.edges_to + no-leak test; ruff/mypy/pytest all green (7/7 pass). Subtasks T005-T008 marked done. BLOCKED on move to for_review: WP02 has no canonical lifecycle status in the event log (only WPCreated; this worktree was created out-of-band without a claim/start event), so move-task rejects with 'no canonical status'. No WP in this mission has lifecycle events yet. Needs operator to initialize WP02 status (e.g. implement claim / finalize-tasks) before the for_review transition can be applied.
- 2026-06-01T19:03:23Z – claude:opus:python-pedro:implementer – shell_pid=1545161 – workaround viability test
- 2026-06-01T19:09:32Z – claude:opus:python-pedro:implementer – shell_pid=1545161 – reset after test
- 2026-06-01T20:49:07Z – claude:opus:python-pedro:implementer – shell_pid=1545161 – facet3 fix e2e test
- 2026-06-01T20:49:37Z – claude:opus:python-pedro:implementer – shell_pid=1545161 – reset
- 2026-06-01T22:53:19Z – claude:opus:python-pedro:implementer – shell_pid=1687431 – Assigned agent via action command
