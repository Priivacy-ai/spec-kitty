# Tasks: Kind-Complete Cascade + Orphan Wiring (M5)

**Mission**: `kind-complete-cascade-orphan-wiring-01M0FQCD`
**Planning base / merge target**: `feat/kind-complete-cascade-orphan-wiring`
**Closes**: #2829, #3009 (residual)

Two disjoint work packages map to the two implementation concerns. They touch
non-overlapping files (charter cascade vs doctrine graph data/ledgers) and can run
as parallel lanes. The single golden re-ledger lives entirely in WP02.

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|----|----------|
| T001 | Red-first cascade tests: mission-type reach 0→non-zero; no template/asset; action nodes excluded; excluded relations unfollowed; deactivation shared-reference-safe | WP01 | |
| T002 | Add `Relation.SCOPE` + `Relation.INSTANTIATES` to `REFERENCE_RELATIONS` | WP01 | |
| T003 | Filter `_referenced_artifacts` candidates to `CHARTER_ACTIVATABLE_KINDS` | WP01 | |
| T004 | Extend `test_kind_cascade_exhaustive.py` — filter uses the canonical set (self-mutation guard) | WP01 | [P] |
| T005 | Validate WP01: `tests/charter/` + CLI cascade tests, ruff, mypy --strict; confirm ADR match | WP01 | |
| T006 | Red-first orphan tests: 4 targets gain a pure-graph inbound edge (was 0); deployable-skill-authoring direct-activation-only | WP02 | |
| T007 | Add symmetric `reason=ref.get("reason")` to directive references loop + roundtrip test | WP02 | |
| T008 | Author 4 frontmatter refs (`{type,id,when,reason}` verbatim) in DIR 030/034/041; remove 4 overlay edges | WP02 | |
| T009 | Regenerate graph (byte-identity); introduce direct-activation-only disposition for the 5th | WP02 | |
| T010 | Single re-ledger: `test_extractor_projection.py` + `test_reachability.py` + wiring-table doc; trace every move | WP02 | |
| T011 | Validate WP02: `tests/doctrine/drg/**`, ruff, mypy --strict; confirm re-ledger applied once | WP02 | |

## WP01 — Kind-complete cascade traversal (IC-01)

- **Goal**: Activating a `mission_type` reaches the governance its actions scope
  to; cascade proposes only charter-activatable kinds. Closes #2829.
- **Priority**: P1. **Independent test**: cascade from each built-in
  `mission_type` non-empty (was 0) and excludes template/asset.
- **Subtasks**: T001, T002, T003, T004, T005.
- **Sketch**: red-first tests (T001) → add scope+instantiates (T002) → add
  activatable-kind filter (T003) → exhaustive filter guard (T004) → validate +
  ADR match (T005).
- **Dependencies**: none. **Parallel with**: WP02.
- **Risks**: followed set feeds activation *and* deactivation — cover both;
  `instantiates` reaches real templates, so the filter (not the traversal) keeps
  them out.
- **Estimated prompt size**: ~320 lines.

## WP02 — Residual orphan wiring + single re-ledger (IC-02)

- **Goal**: Promote the 4 defensible orphan overlay edges to source-artifact
  frontmatter (single-authority, lossless), mark
  `styleguide:deployable-skill-authoring` direct-activation-only, and re-ledger
  the golden counts + reachability pins exactly once. Closes #3009 residual.
- **Priority**: P2. **Independent test**: the 4 targets gain a pure-graph inbound
  edge; the 5th is recorded direct-activation-only; `regenerate-graph --check`
  clean; ledger movement traced.
- **Subtasks**: T006, T007, T008, T009, T010, T011.
- **Sketch**: red-first orphan tests (T006) → symmetric `reason` support (T007)
  → author frontmatter refs + remove overlay edges (T008) → regenerate + direct-
  only disposition (T009) → single re-ledger (T010) → validate (T011).
- **Dependencies**: none. **Parallel with**: WP01. Lands atop M1–M4.
- **Risks**: promotion must emit the identical `(source,target,relation,when,
  reason)` edge (byte-identity); re-ledger traced move-by-move, applied once.
- **Estimated prompt size**: ~380 lines.

## MVP

WP01 is the headline defect (#2829) and the ADR-bearing change — the natural MVP.
WP02 closes the #3009 residual and is independently valuable.
