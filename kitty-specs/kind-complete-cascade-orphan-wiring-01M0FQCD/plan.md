# Implementation Plan: Kind-Complete Cascade + Orphan Wiring

**Branch**: `feat/kind-complete-cascade-orphan-wiring` | **Date**: 2026-08-20 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `kitty-specs/kind-complete-cascade-orphan-wiring-01M0FQCD/spec.md`

## Summary

Two complementary reach gaps in the charter cascade (pure graph logic over the
merged DRG):

1. **#2829** — the cascade follows only `{requires, suggests, refines}`, so a
   `mission_type → action → scope/instantiates → artifact` path dead-ends at the
   `action` node. Measured: cascade from all four built-in mission types returns
   0. Fix: add `scope` + `instantiates` to the followed set so the closure walks
   through `action` nodes to the governance artifacts, and add a positive
   `CHARTER_ACTIVATABLE_KINDS` filter so cascade proposes only activatable kinds
   (the "kind-complete" half — drops non-activatable `template`/`asset` that the
   widened reach, and 137 pre-existing sources, surface as spurious warnings).
   Captured in an ADR.
2. **#3009 residual** — five `_ACTIVATED_BUT_ORPHANED` artifacts. Four carry a
   hand-authored overlay edge; promote each to a real source-artifact frontmatter
   edge (single-authority) so it leaves the pure-graph orphan set without
   changing the shipped edge set. The fifth (`styleguide:deployable-skill-
   authoring`) has no defensible source → record direct-activation-only. Re-ledger
   the golden node/edge/orphan counts + reachability pins **exactly once**.

Technical approach is pure-graph and data-only: no new runtime surface, no
dependency change. The cascade change is validated by new red-first cascade
tests; the orphan change is validated by the regenerated graph + the single
re-ledger.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: none added (stdlib `collections`; pydantic v2 DRG models already present)
**Storage**: doctrine graph fragments `packs/built-in/*.graph.yaml` (committed YAML); no DB
**Testing**: pytest (`tests/charter/`, `tests/doctrine/drg/`, `tests/doctrine/drg/migration/`); `ruff`; `mypy --strict`
**Target Platform**: Linux/macOS/Windows CLI (cross-platform)
**Project Type**: single (library + CLI)
**Performance Goals**: cascade traversal stays O(E) BFS over the merged DRG; no measurable regression (graph is ~300 nodes / ~757 edges)
**Constraints**: `charter/` imports only `doctrine.*` (never `specify_cli`); zero ruff/mypy suppressions; promoted overlay→frontmatter edges must keep the shipped edge set byte-identical; re-ledger exactly once atop M1–M4
**Scale/Scope**: 2 source seams (`src/charter/cascade.py`, doctrine graph frontmatter/overlay), ~5 orphan artifacts, ~3 ledger surfaces

## Constitution Check (Charter)

*GATE: Must pass before Phase 0. Re-checked after Phase 1.*

- **Single canonical authority** ✓ — the activatable-kind filter reuses
  `doctrine.artifact_kinds.CHARTER_ACTIVATABLE_KINDS` (no re-declared exclusion
  list); orphan edges are promoted **into the owning artifact's frontmatter**
  (the single authority) rather than left in the secondary overlay.
- **Architectural alignment** ✓ — `charter/cascade.py` continues to import only
  `doctrine.*`; the change stays inside the cascade seam and the doctrine graph
  data. No new module, no `specify_cli` import.
- **DDD + tiered rigour** ✓ — core graph logic (cascade traversal) gets the most
  rigour (red-first, exhaustive per-mission-type + per-relation tests); the
  data-only orphan edges get ledger-diff rigour.
- **ATDD-first / red-first** ✓ — both defects get a failing-first test (mission
  cascade = 0; orphans unreachable/unclassified) committed before the fix.
- **Terminology adherence** ✓ — "Mission" canon; no `feature*` reintroduced.
- **Excluded relations stay excluded** ✓ — ADR states why `vocabulary` and the
  tension/lineage/overlay/handoff relations are out.

No charter violations. Complexity Tracking empty.

## Project Structure

### Documentation (this mission)

```
kitty-specs/kind-complete-cascade-orphan-wiring-01M0FQCD/
├── plan.md              # This file
├── research.md          # Phase 0 — measured baselines, decision records, alternatives
├── data-model.md        # Phase 1 — relation sets, kind sets, orphan dispositions, ledger surfaces
├── quickstart.md        # Phase 1 — how to reproduce baseline + verify the fix
├── contracts/           # Phase 1 — cascade + orphan-ledger behavioral contracts
└── tasks.md             # Phase 2 (/spec-kitty.tasks — NOT created here)
```

### Source Code (repository root)

```
src/charter/cascade.py                       # REFERENCE_RELATIONS, _referenced_artifacts, _reference_adjacency (IC-01)
src/doctrine/artifact_kinds.py               # CHARTER_ACTIVATABLE_KINDS (imported, not modified)
src/doctrine/drg/migration/hand_authored_overlay.py  # remove 4 promoted overlay edges (IC-02)
packs/built-in/directives/*.directive.yaml   # DIRECTIVE_034/030/041 frontmatter += promoted refs (IC-02)
packs/built-in/*.graph.yaml                  # regenerated committed fragments (IC-02)
docs/adr/3.x/2026-08-20-*-cascade-kind-complete-relation-set.md   # ADR (IC-01)

tests/charter/test_cascade.py                # red-first mission-type cascade + kind-filter tests (IC-01)
tests/charter/test_kind_cascade_exhaustive.py# extend for activatable-kind filter (IC-01)
tests/doctrine/drg/migration/test_extractor_projection.py  # orphan-set re-ledger (IC-02)
tests/doctrine/drg/test_reachability.py      # reachability pins re-ledger (IC-02)
docs/plans/doctrine/delivery-reachability-wiring-table.md  # wiring-table ledger rows (IC-02)
```

**Structure Decision**: Single project. Two disjoint seams — the cascade engine
(charter layer, IC-01) and the doctrine graph data + ledgers (doctrine layer,
IC-02) — allow two independent work packages that converge only at the single
re-ledger.

## Implementation Concern Map

### IC-01 — Kind-complete cascade traversal + ADR

- **Purpose**: Expand the cascade followed-relation set with `scope` +
  `instantiates` so activating a `mission_type` reaches the governance artifacts
  its actions are scoped to; add a positive `CHARTER_ACTIVATABLE_KINDS` candidate
  filter so cascade proposes only activatable kinds. Record the relation-set
  decision in an ADR.
- **Relevant requirements**: FR-001, FR-002, FR-003, FR-004, FR-005, FR-006,
  FR-010, NFR-001, NFR-002, NFR-003, NFR-004, C-002, C-005, SC-001, SC-002
- **Affected surfaces**:
  - `src/charter/cascade.py` — add `Relation.SCOPE`, `Relation.INSTANTIATES` to
    `REFERENCE_RELATIONS`; filter `_referenced_artifacts` candidates to
    `CHARTER_ACTIVATABLE_KINDS` (imported from `doctrine.artifact_kinds`).
  - `tests/charter/test_cascade.py` — red-first: cascade from each built-in
    `mission_type` is non-empty and excludes `template`/`asset`; action nodes
    never emitted; excluded relations stay unfollowed; deactivation stays
    shared-reference-safe under the widened set.
  - `tests/charter/test_kind_cascade_exhaustive.py` — assert the filter uses the
    canonical set (self-mutation guard: a hypothetical extra activatable kind
    flows through; template/asset never do).
  - `docs/adr/3.x/2026-08-20-*-cascade-kind-complete-relation-set.md` — ADR.
- **Sequencing/depends-on**: none (charter-layer only). Independent of IC-02.
- **Risks**:
  - The followed set feeds **both** activation and deactivation exclusivity —
    the deactivation shared-reference-safety test must cover the widened set.
  - The filter changes output for the ~137 pre-existing template/asset-reaching
    sources; confirmed no existing cascade test pins that noise, but re-run the
    full `tests/charter/` + CLI cascade tests to be sure.
  - `instantiates` reaches real `template:` nodes today — the filter, not the
    traversal, is what keeps them out of the proposed set; test both the
    traversal reach and the filtered result so the two concerns stay separable.

### IC-02 — Residual orphan wiring + single golden re-ledger

- **Purpose**: Close the #3009 residual — promote the four defensible orphan
  overlay edges to source-artifact frontmatter (de-orphaning them in the pure
  graph), record `styleguide:deployable-skill-authoring` direct-activation-only,
  and re-ledger the golden counts + reachability pins exactly once.
- **Relevant requirements**: FR-007, FR-008, FR-009, NFR-003, C-001, C-003,
  C-004, SC-003, SC-004
- **Affected surfaces**:
  - `src/doctrine/drg/migration/extractor.py` — add symmetric
    `reason=ref.get("reason")` to the directive top-level `references` loop
    (currently only `when=ref.get("when")` at ~`:739`). Backward-compatible (no
    shipped directive ref carries `reason` today), and required so the promoted
    edges keep their curated `reason` prose — otherwise promotion silently drops
    it and rewrites the committed fragment. Author the 4 frontmatter refs as
    `{type, id, when, reason}` copying the overlay's `when`/`reason` **verbatim**
    so the regenerated edge is identical (same triple + when + reason).
  - `packs/built-in/directives/034-*.directive.yaml` — frontmatter ref →
    `styleguide:given-when-then-authoring` + `toolguide:gherkin` (`suggests`).
  - `packs/built-in/directives/030-*.directive.yaml` — frontmatter ref →
    `toolguide:sonar` (`suggests`).
  - `packs/built-in/directives/041-*.directive.yaml` — frontmatter ref →
    `styleguide:quadruple-a-test-format` (`suggests`).
  - `src/doctrine/drg/migration/hand_authored_overlay.py` — remove the 4 now-
    redundant overlay edges (`:1284`, `:1295`, `:1446`, `:1483`).
  - `packs/built-in/*.graph.yaml` — regenerated via `spec-kitty doctrine
    regenerate-graph` (edge set unchanged → byte-identity guard stays green).
  - `tests/doctrine/drg/migration/test_extractor_projection.py` — shrink
    `_ACTIVATED_BUT_ORPHANED` (−5) and `_ORPHANS_RESOLVED_BY_OVERLAY` (−4);
    add/adjust the direct-activation-only disposition for the 5th; update the
    ledger provenance comments (single re-ledger).
  - `tests/doctrine/drg/test_reachability.py` — the 4 promoted edges keep the
    shipped graph identical, so action/profile reachability pins do NOT move;
    add the mission's forcing pin analogue if the harness expects one; record
    `deployable-skill-authoring`'s direct-activation-only disposition.
  - `docs/plans/doctrine/delivery-reachability-wiring-table.md` — update the 5
    orphans' ledger rows to reflect frontmatter/direct-only disposition.
- **Sequencing/depends-on**: lands atop M1–M4 (all merged). Re-ledger happens
  here and only here.
- **Risks**:
  - Frontmatter promotion emits `suggests` for all 4 (directive→toolguide/
    styleguide → `suggests` via `_relation_for_ref_type`), matching the overlay
    — **verified**. Losslessness depends on the extractor also carrying `reason`
    on directive refs (the one-line symmetric add above); the
    directive-reference-`reason`-roundtrip needs a focused test (Sonar: new
    branch ⇒ test in the same WP). If that add proves risky, the documented
    fallback is: keep `when` in frontmatter, fold the `reason` rationale into the
    ADR/research, and accept the `reason` drop on those 4 fragment edges (triple
    unchanged → byte-identity SET guard still green).
  - The direct-activation-only disposition is a **new** concept (no existing
    per-URN set) — introduce it as a small, documented set with a rationale,
    not an ad-hoc deletion from `_ACTIVATED_BUT_ORPHANED`.
  - Re-ledger must be traced move-by-move (each count/membership change → one
    edge/relation cause) to satisfy "re-ledger once, every move traced".

## Complexity Tracking

*No Constitution Check violations — section intentionally empty.*

## Parallel Work Analysis

### Dependency Graph

```
IC-01 (cascade engine, charter layer)  ─┐
                                         ├─► converge only at final review / re-ledger sanity
IC-02 (orphan wiring + re-ledger, doctrine layer) ─┘
```

IC-01 and IC-02 touch **disjoint** files (charter cascade vs doctrine graph
data/ledgers) and can proceed in parallel lanes. They do not share a golden
surface: the cascade change moves no extractor/reachability golden count (those
measure resolve_context + profile channels + the graph edge set, not cascade
`REFERENCE_RELATIONS`), and the orphan change moves no cascade behavior. The
"re-ledger once" constraint lives entirely inside IC-02.

### Work Distribution

- **Sequential work**: none forced between the two ICs.
- **Parallel streams**: IC-01 (cascade + ADR), IC-02 (orphan wiring + re-ledger).
- **Agent assignments**: IC-01 → cascade/charter surfaces + `tests/charter/`;
  IC-02 → doctrine graph frontmatter/overlay + `tests/doctrine/drg/**` + wiring
  table. No file overlap.

### Coordination Points

- **Integration check**: after both lanes, run the combined targeted suite
  (`tests/charter/`, `tests/doctrine/drg/`, `tests/doctrine/drg/migration/`) plus
  `ruff` + `mypy --strict` on the aggregate, and confirm the re-ledger is applied
  exactly once (no double-count).
