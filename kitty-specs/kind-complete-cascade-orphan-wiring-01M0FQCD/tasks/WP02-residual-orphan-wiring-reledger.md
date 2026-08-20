---
work_package_id: WP02
title: Residual orphan wiring + single golden re-ledger
dependencies: []
requirement_refs:
- C-001
- C-003
- C-004
- FR-007
- FR-008
- FR-009
- NFR-001
- NFR-003
planning_base_branch: feat/kind-complete-cascade-orphan-wiring
merge_target_branch: feat/kind-complete-cascade-orphan-wiring
branch_strategy: Planning artifacts for this mission were generated on feat/kind-complete-cascade-orphan-wiring. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/kind-complete-cascade-orphan-wiring unless the human explicitly redirects the landing branch.
subtasks:
- T006
- T007
- T008
- T009
- T010
- T011
history:
- Created by /spec-kitty.tasks (M5 charter-resolution program)
agent_profile: curator-carla
authoritative_surface: src/doctrine/drg/migration/
create_intent: []
execution_mode: code_change
owned_files:
- src/doctrine/drg/migration/extractor.py
- src/doctrine/drg/migration/hand_authored_overlay.py
- packs/built-in/directives/030-test-and-typecheck-quality-gate.directive.yaml
- packs/built-in/directives/034-test-first-development.directive.yaml
- packs/built-in/directives/041-tests-as-scaffold-not-friction.directive.yaml
- packs/built-in/directive.graph.yaml
- packs/built-in/toolguide.graph.yaml
- packs/built-in/styleguide.graph.yaml
- tests/doctrine/drg/migration/test_extractor_projection.py
- tests/doctrine/drg/test_reachability.py
- docs/plans/doctrine/delivery-reachability-wiring-table.md
role: implementer
tags: []
tracker_refs:
- '3009'
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your assigned profile so your boundaries, directives, and tactics are active:

```
/ad-hoc-profile-load curator-carla
```

Then run `spec-kitty charter context --action implement --json` and apply the resolved initialization. State which directives/tactics you applied before writing code.

## Objectives & Success Criteria

Close the **#3009 residual**: five `_ACTIVATED_BUT_ORPHANED` artifacts. Four have a
defensible source already expressed as a hand-authored **overlay** edge; promote
each to a real **source-artifact frontmatter** edge (single canonical authority),
de-orphaning it in the pure extractor graph without changing the shipped edge
set. The fifth has no defensible source → record direct-activation-only. Re-ledger
the golden counts **exactly once**.

- **SC (FR-007)**: in the **pure** extractor graph, each of
  `styleguide:given-when-then-authoring`, `toolguide:gherkin`, `toolguide:sonar`,
  `styleguide:quadruple-a-test-format` has a real inbound edge sourced from its
  owning directive's frontmatter (baseline: 0 inbound in the pure graph).
- **SC (FR-008)**: `styleguide:deployable-skill-authoring` is recorded direct-
  activation-only with a rationale and removed from the "must-shrink"
  `_ACTIVATED_BUT_ORPHANED` debt set — never given a guessed edge (C-003).
- **SC (FR-009/C-004)**: the shipped `(source,target,relation)` edge set is
  **unchanged** (promotions lossless); `regenerate-graph --check` clean; the
  golden node/edge/orphan pins + reachability pins re-ledgered once, every move
  traced.

## Context & Constraints

Read `kitty-specs/kind-complete-cascade-orphan-wiring-01M0FQCD/{spec.md,plan.md,research.md,data-model.md}`
and `contracts/cascade-kind-complete.contract.md`.

Verified current state (`upstream/main @ f82aa0ff8`):
- The 4 overlay edges (all `suggests`) live in
  `src/doctrine/drg/migration/hand_authored_overlay.py`:
  - `DIRECTIVE_034 --> styleguide:given-when-then-authoring` (`:1284`)
  - `DIRECTIVE_034 --> toolguide:gherkin` (`:1295`)
  - `DIRECTIVE_030 --> toolguide:sonar` (`:1446`)
  - `DIRECTIVE_041 --> styleguide:quadruple-a-test-format` (`:1483`)
  Each carries curated `when` **and** `reason`.
- Directive frontmatter references are `{type, id, when?}`; the extractor parses
  `when` (`extractor.py:739`) but **not** `reason`. `_relation_for_ref_type`
  (`:514`): directive→REQUIRES, everything else→SUGGESTS — so a directive→
  toolguide/styleguide ref emits `suggests`, matching the overlay.
- Orphan ledger sets: `test_extractor_projection.py` — `_ACTIVATED_BUT_ORPHANED`
  (`:763-793`), `_ORPHANS_RESOLVED_BY_OVERLAY` (`:837-845`); byte-identity guard
  `test_shipped_graph_is_fresh_and_byte_identical` (`:982`) compares
  `(source,target,relation)` SET-equality. Reachability pins in
  `test_reachability.py` — `_ACTION_UNREACHABLE_D1/D2`, `_PROFILE_UNREACHABLE`,
  `_PROFILE_RESCUES`; ledger doc `docs/plans/doctrine/delivery-reachability-
  wiring-table.md` (rows for the 5 orphans at `:878-887`) is read+asserted.

Constraints: promotions must be **lossless** (same source, target, relation,
when, reason) so the committed fragment stays byte-identical (C-004). Re-ledger
**once** (C-001). Zero ruff/mypy suppressions (NFR-001).

## Subtasks

### T006 — Red-first orphan tests (ATDD, commit RED first)

Add/extend tests proving the pre-change state:
1. In the **pure** extractor graph (no overlay), assert each of the 4 targets has
   **≥1 inbound edge** — RED now (0 inbound in the pure graph).
2. Assert `styleguide:deployable-skill-authoring` is classified direct-activation-
   only (against the new disposition) — RED now (it is only in
   `_ACTIVATED_BUT_ORPHANED`).
Commit RED first.

### T007 — Symmetric `reason` on directive references

In `src/doctrine/drg/migration/extractor.py`, the directive top-level
`references` loop (~`:734-741`) passes `when=ref.get("when")`; add
`reason=ref.get("reason")` symmetrically. Backward-compatible — no shipped
directive ref carries `reason` today, so every existing edge is unchanged. Add a
focused roundtrip test (a directive ref with `reason` yields an edge whose
`reason` matches; without `reason` yields `reason=None`).

### T008 — Promote the 4 edges to frontmatter; remove overlay duplicates

For each of DIR 030/034/041, add a `references` entry `{type, id, when, reason}`
copying the overlay's `when` and `reason` **verbatim**:
- `034`: `+ {type: styleguide, id: given-when-then-authoring, when: …, reason: …}`
  and `+ {type: toolguide, id: gherkin, when: …, reason: …}`
- `030`: `+ {type: toolguide, id: sonar, when: …, reason: …}`
- `041`: `+ {type: styleguide, id: quadruple-a-test-format, when: …, reason: …}`
Then remove those 4 `DRGEdge(...)` entries from `hand_authored_overlay.py`
(`:1284`, `:1295`, `:1446`, `:1483`) and any now-unused local constants. Preserve
every other overlay edge.

### T009 — Regenerate graph + direct-activation-only disposition

- Run `spec-kitty doctrine regenerate-graph`; confirm the committed
  `packs/built-in/*.graph.yaml` fragments are unchanged for the 4 edges (same
  triple + when + reason) — the diff should be net-zero for those edges (moved
  authority, identical output). `regenerate-graph --check` must pass.
- Introduce a small, documented **direct-activation-only** disposition (a named
  frozenset + rationale) for `styleguide:deployable-skill-authoring`, in the
  ledger test module where `_ACTIVATED_BUT_ORPHANED` lives. It leaves
  `_ACTIVATED_BUT_ORPHANED` and is honestly classified (no guessed edge).

### T010 — Single golden re-ledger (trace every move)

Update, once, with a comment tracing each move to its cause:
- `test_extractor_projection.py`: `_ACTIVATED_BUT_ORPHANED` −5 (4 promoted + 1
  direct-only); `_ORPHANS_RESOLVED_BY_OVERLAY` −4 (the 4 leave overlay-resolution
  for frontmatter). Node/edge SET pins unchanged (edge set identical).
- `test_reachability.py`: the 4 promotions keep the shipped graph identical, so
  `_ACTION_UNREACHABLE_*` / `_PROFILE_UNREACHABLE` / `_PROFILE_RESCUES` do NOT
  move — assert this explicitly; record the direct-only disposition; keep the
  totality/disjointness companion guard green.
- `docs/plans/doctrine/delivery-reachability-wiring-table.md`: update the 5
  orphans' rows (4 frontmatter, 1 direct-only).

### T011 — Validate

```
PYTHONPATH=src python -m pytest tests/doctrine/drg/ tests/doctrine/drg/migration/ -q
spec-kitty doctrine regenerate-graph --check
ruff check src/doctrine/drg/migration/ tests/doctrine/drg/
mypy --strict src/doctrine/drg/migration/extractor.py
```
Confirm the re-ledger is applied exactly once (no count double-moved) and the
shipped edge set is unchanged.

## Branch Strategy

Planning base and final merge target: `feat/kind-complete-cascade-orphan-wiring`.
Runs in its computed lane worktree (from `lanes.json`); merge back to the planning
base unless the operator redirects. Do not push to origin/main.

## Definition of Done

- T006 committed RED first; green after T007–T010.
- 4 targets have a pure-graph frontmatter inbound edge; 5th recorded direct-
  activation-only; shipped edge set byte-identical; `regenerate-graph --check`
  clean.
- `_ACTIVATED_BUT_ORPHANED` −5, `_ORPHANS_RESOLVED_BY_OVERLAY` −4; reachability
  pins unchanged; every move traced; re-ledger applied once.
- `tests/doctrine/drg/**`, ruff, mypy --strict green, zero suppressions.

## Reviewer Guidance

Verify red→green on T006 (RED on the planning base). Verify each promoted edge is
identical to the removed overlay edge (source, target, relation, when, reason) —
grep the regenerated fragment. Verify the byte-identity guard is green and the
direct-only disposition carries a rationale, not a silent deletion. Verify the
re-ledger moved counts once and only IC-02's surfaces.
