---
work_package_id: WP01
title: Kind-complete cascade traversal (scope+instantiates + activatable-kind filter)
dependencies: []
requirement_refs:
- C-002
- C-005
- FR-001
- FR-002
- FR-003
- FR-004
- FR-005
- FR-006
- FR-010
- NFR-001
- NFR-002
- NFR-003
- NFR-004
planning_base_branch: feat/kind-complete-cascade-orphan-wiring
merge_target_branch: feat/kind-complete-cascade-orphan-wiring
branch_strategy: Planning artifacts for this mission were generated on feat/kind-complete-cascade-orphan-wiring. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/kind-complete-cascade-orphan-wiring unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
- T005
history:
- Created by /spec-kitty.tasks (M5 charter-resolution program)
agent_profile: python-pedro
authoritative_surface: src/charter/cascade.py
create_intent: []
execution_mode: code_change
owned_files:
- src/charter/cascade.py
- tests/charter/test_cascade.py
- tests/charter/test_kind_cascade_exhaustive.py
role: implementer
tags: []
tracker_refs:
- '2829'
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your assigned profile so your boundaries, directives, and tactics are active:

```
/ad-hoc-profile-load python-pedro
```

Then run `spec-kitty charter context --action implement --json` and apply the resolved initialization. State which directives/tactics you applied before writing code.

## Objectives & Success Criteria

Close the **#2829 cascade dead-end** and make the cascade **kind-complete**. The
charter cascade (`src/charter/cascade.py`) is pure graph logic over the merged
DRG; it currently follows `REFERENCE_RELATIONS = {requires, suggests, refines}`.

- **SC (FR-001/FR-002)**: cascade from **every** built-in `mission_type` returns a
  non-empty activatable set (measured baseline: all four return 0). The mechanism
  is following the action hop: `mission_type --requires--> action --scope-->
  governance` (and `action --instantiates--> template`).
- **SC (FR-003)**: no `template`/`asset` (nor any non-`CHARTER_ACTIVATABLE_KINDS`
  kind) appears in `cascade_activation_targets(...).activated`, in
  `referenced_but_not_cascaded(...).skipped`, or as a `deactivation_plan`
  candidate — for any source, including sources whose closure reaches
  templates/assets.
- **SC (FR-004)**: `action:` nodes (and any non-artifact node) are never emitted
  as activation targets.
- **SC (FR-005/FR-006)**: excluded relations stay unfollowed; deactivation stays
  shared-reference-safe under the widened followed set.
- **SC (FR-010)**: the change matches ADR
  `docs/adr/3.x/2026-08-20-1-cascade-kind-complete-relation-set.md` (already
  authored in planning). Do not re-author it; verify the code matches it.

## Context & Constraints

Read `kitty-specs/kind-complete-cascade-orphan-wiring-01M0FQCD/{spec.md,plan.md,research.md,data-model.md}`
and `contracts/cascade-kind-complete.contract.md`. The ADR is the authority on
the relation-set decision.

Verified current state (`upstream/main @ f82aa0ff8`):
- `REFERENCE_RELATIONS` — `src/charter/cascade.py:87-89`.
- `_reference_adjacency` (`:235`) builds forward adjacency over
  `REFERENCE_RELATIONS`; `_forward_reference_closure` (`:213`) BFS; both feed
  activation and `deactivation_plan` (`:455`) exclusivity.
- `_referenced_artifacts` (`:244`) keeps reached nodes where `_kind_of(urn) is
  not None` — i.e. any `ArtifactKind`, **including** `template`/`asset`.
- The canonical activatable authority is
  `doctrine.artifact_kinds.CHARTER_ACTIVATABLE_KINDS` (`:330`) =
  `frozenset(ArtifactKind) - {TEMPLATE, ASSET}` (10 kinds incl. `anti_pattern`).
  **Import it — do not re-declare an exclusion list** (NFR-002).
- Measured: cascade from `mission_type:documentation` over
  `REFERENCE_RELATIONS ∪ {scope, instantiates}` reaches tactic×22, directive×7,
  styleguide×2, template×8, asset×1 (+ action×7 dropped). The filter drops
  template/asset; the activatable governance survives.

Constraints: `src/charter/cascade.py` imports only `doctrine.*` (never
`specify_cli`) — C-X-1. Zero ruff/mypy suppressions (NFR-001). Traversal reach
and candidacy are **separate**: `instantiates` is followed so the closure passes
through actions; `template` targets are dropped at candidacy (C-CAS-3/5).

## Subtasks

### T001 — Red-first cascade tests (ATDD, commit RED first)

Add tests in `tests/charter/test_cascade.py` that FAIL on the current base:

1. **Mission-type reach (C-CAS-1/2)**: build the shipped graph
   (`doctrine.drg.loader.load_built_in_graph`); for each `mission_type:*` URN,
   assert `cascade_activation_targets(g, urn, CascadeScope.all()).activated` is
   non-empty and (for `documentation`) includes `directive`, `tactic`,
   `styleguide` keys. (RED now: returns empty.)
2. **No non-activatable kinds (C-CAS-3)**: for a source reaching templates/assets
   (e.g. `mission_type:documentation`), assert no `template`/`asset` key in
   `activated`; and `referenced_but_not_cascaded` for that source lists no
   template/asset. (RED after T002 without T003.)
3. **Action nodes excluded (C-CAS-4)**: assert no `action` id in any activated
   bucket.
4. **Excluded relations unfollowed (C-CAS-6)**: construct a tiny `DRGGraph` with a
   single `in_tension_with` (and separately `rejects`, `delegates_to`,
   `specializes_from`, `enhances`, `overrides`, `replaces`, `applies`,
   `vocabulary`) edge from the source; assert the cascade is empty for each.
5. **Deactivation symmetry (C-CAS-7)**: a candidate reachable via the widened set
   from another active source is skipped (named), never deactivated.

Commit this as the first commit of the lane (RED). The reviewer verifies
red→green.

### T002 — Add scope + instantiates to the followed set

In `src/charter/cascade.py`, change `REFERENCE_RELATIONS` to
`{Relation.REQUIRES, Relation.SUGGESTS, Relation.REFINES, Relation.SCOPE,
Relation.INSTANTIATES}`. Update the module docstring / the `REFERENCE_RELATIONS`
doc-comment to explain the action-hop reach and cite the ADR. No other logic
change here.

### T003 — Filter candidates to CHARTER_ACTIVATABLE_KINDS

In `_referenced_artifacts`, after resolving `kind = _kind_of(urn)`, additionally
skip nodes whose kind is not in `CHARTER_ACTIVATABLE_KINDS` (import from
`doctrine.artifact_kinds`). Keep the existing `_kind_of(urn) is None` skip (non-
artifact nodes). This single membership test is the whole filter — no per-kind
branch. Add a short comment: traversal follows `instantiates` to pass through
actions; candidacy drops non-activatable `template`/`asset` via the canonical set.

### T004 — Exhaustive filter guard [P]

In `tests/charter/test_kind_cascade_exhaustive.py`, add a class asserting the
cascade candidate filter is driven by `CHARTER_ACTIVATABLE_KINDS`: a self-mutation
style guard proving `template`/`asset` never appear as cascade candidates while
the activatable kinds do (build a minimal graph with a source referencing one of
each kind through a followed relation).

### T005 — Validate

Run and pass:
```
PYTHONPATH=src python -m pytest tests/charter/ \
  tests/specify_cli/cli/commands/charter/ -q
ruff check src/charter/cascade.py tests/charter/test_cascade.py tests/charter/test_kind_cascade_exhaustive.py
mypy --strict src/charter/cascade.py
```
Confirm no existing cascade/CLI test regressed (the 137 pre-existing template/
asset-reaching sources now cleanly omit them — a correctness improvement).
Confirm the implementation matches ADR 2026-08-20-1.

## Branch Strategy

Planning base and final merge target: `feat/kind-complete-cascade-orphan-wiring`.
During `/spec-kitty.implement` this WP runs in its computed lane worktree (from
`lanes.json`); completed changes merge back to the planning base unless the
operator redirects. Do not push to origin/main.

## Definition of Done

- T001 committed RED first; green after T002+T003.
- Cascade from all four built-in mission types non-empty; no template/asset in any
  cascade output; action nodes never emitted; excluded relations unfollowed;
  deactivation shared-reference-safe.
- Filter reads `CHARTER_ACTIVATABLE_KINDS` (no re-declared list).
- `tests/charter/` + CLI cascade tests, ruff, mypy --strict all green, zero
  suppressions. Code matches ADR 2026-08-20-1.

## Reviewer Guidance

Verify red→green on T001 (run it on the planning base — must be RED). Confirm the
filter uses the canonical set by identity, not a literal. Confirm no golden count
moved (this WP touches no graph data — extractor/reachability pins must be
untouched). Confirm C-001 layering: `cascade.py` imports only `doctrine.*`.
