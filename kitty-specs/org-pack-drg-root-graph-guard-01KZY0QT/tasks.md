---
description: "Work package task list for org-pack-drg-root-graph-guard (#3384)"
---

# Work Packages: Org Pack DRG Root Graph Guard

**Inputs**: `kitty-specs/org-pack-drg-root-graph-guard-01KZY0QT/spec.md` (passed),
`kitty-specs/org-pack-drg-root-graph-guard-01KZY0QT/plan.md` (passed),
`kitty-specs/org-pack-drg-root-graph-guard-01KZY0QT/reviews/spec.ruling.md`,
`kitty-specs/org-pack-drg-root-graph-guard-01KZY0QT/reviews/plan.ruling.md` (both binding on
this file; neither is relitigated here).

**Tests**: Required. Charter C-011 (ATDD-first) and spec.md's C-003 both bind this mission to
failing-first regression tests per FR — this is not the "tests only if explicitly requested"
default case.

**Organization**: Fine-grained subtasks (`Txxx`) roll up into work packages (`WPxx`). This
mission produces exactly **one** work package — see "Why one WP" below.

**Prompt Files**: `tasks/WP01-org-pack-drg-root-graph-guard.md`.

## Subtask Format: `[Txxx] [P?] Description`

Subtasks are **reference rows**, not checkboxes: record completion with
`spec-kitty agent tasks mark-status <Txxx> --status done`. The reduced event-log snapshot is
the sole subtask-completion authority.

## Path Conventions

Single project (CLI library). All source paths are under `src/charter/`; all new test paths are
under `tests/charter/`.

---

## Why one WP (binding decision #6 / plan.md's own PR Shape conclusion)

plan.md's "PR Shape" section already concludes this mission is right-sized for a single PR and
"plausibly" a single WP: the entire functional change is one function's evolution
(`load_validated_graph`'s org-layer branch, factored into `_load_org_layer` +
`_dedup_org_layer_edges` + `OrgDRGFragmentError`, all inside one existing ~100-line file), a
documentation-only comment update in one sibling file, and one new test module covering all
four User Stories. IC-01 → IC-02 → IC-03 (per plan.md's Implementation Concern Map) are not
independently shippable: IC-02 extends the `_load_org_layer` body IC-01 creates, and IC-03
wraps the same two load call sites IC-01 establishes. Splitting them into separate WPs would
create an artificial dependency chain (WP-per-IC, each blocked on the last) for no
parallelization benefit — nothing in IC-02/IC-03 can start before IC-01 lands, and there is no
second engineer this would free up. This is a **sizing decision made from the actual subtask
count** (9 subtasks — inside the outer 3–10 bound, though landing in the canonical tasks-prompt
sizing rubric's 8–10 ⚠️ warning tier rather than the 3–7 ✓ target tier), not a shortcut — see the
subtask breakdown in WP01 below.

**Line-count dimension** (the canonical rubric's second sizing axis, checked explicitly here —
not left silently unperformed): the realized `tasks/WP01-org-pack-drg-root-graph-guard.md` is
728 lines (`wc -l`, re-measured after this fix round's corrections), over the canonical
tasks-prompt's 700-line ceiling
(`packs/built-in/missions/mission-steps/software-dev/tasks/prompt.md:209`, "MAXIMUM PROMPT SIZE:
700 lines per WP"; sizing rubric row "Estimated lines: 700+? ❌ SPLIT"). This is accepted as a
deliberate, measured exception rather than a silent breach: the excess is concentrated in
genuinely load-bearing per-subtask detail (concrete file/function/primitive citations, per-test
RED "reverted-code check" notes, and the Review Guidance checklist a single-function-evolution WP
of this precision needs) rather than padding, and splitting IC-01/IC-02/IC-03 into per-IC WPs
purely to shrink one file's line count would recreate the artificial WP-per-IC dependency chain
already rejected above, for zero parallelization benefit.

**Chokepoints**: none. This mission does not touch the migration chain, the runtime-state
schema, the event contract, or add a new shared CI gate — confirmed by plan.md's Seam and
Generated Artifacts sections (entire change is `src/charter/_drg_helpers.py` +
`src/charter/action_doctrine_bundle.py` comment + `tests/charter/`, no kernel/CLI-layer touch).

**Campsite-clean**: none folded. plan.md's Campsite-Clean Scope section already scanned both
touched files (AST literal-repetition pass, complexity read) during planning and found no
domain-matched debt worth folding. The first commit of WP01 is the first ATDD RED test, not a
preceding cleanup commit.

**Open-PR conflict check** (re-verified at tasks time, per the mission brief's requirement to
re-run the plan-phase sweep): `gh pr list --repo Priivacy-ai/spec-kitty --state open --json
number,title,files` was re-run against all 18 currently-open PRs (#2239–#3383). None touch
`src/charter/_drg_helpers.py`, `src/charter/action_doctrine_bundle.py`, or any path under
`tests/charter/`. PRs #3300 and #3293 each touch `.kittify/charter/governance.yaml` among
roughly 100–150 other files in their respective diffs; neither touches this mission's
`owned_files`.

---

## Work Package WP01: Guard + drg/ merge + malformed-content visibility for org DRG root load (Priority: P1)

**Goal**: Close #3384 — an org pack whose only DRG content lives at `<org_root>/drg/*.graph.yaml`
(the only layout the shipped authoring guide documents) currently zeroes every action-scoped
doctrine count silently. WP01 delivers all three implementation concerns from plan.md
(IC-01 guard, IC-02 root+`drg/` merge/dedup, IC-03 malformed-content visibility) as one
function's evolution inside `src/charter/_drg_helpers.py`, plus a documentation-only comment
update in `src/charter/action_doctrine_bundle.py`, plus one new regression test module.

**Independent Test**: `pytest tests/charter/test_org_root_graph_guard.py -v` — all 9 tests pass;
`pytest tests/charter/ tests/architectural/` passes (excluding pre-existing #3284 red, per
C-005); `mypy --strict` and `ruff check` are clean on both changed source files.

**Prompt**: `tasks/WP01-org-pack-drg-root-graph-guard.md`

**Requirement Refs**: FR-001, FR-002, FR-003, FR-004, FR-005, FR-006, NFR-001, NFR-002, C-001,
C-002, C-003, C-004, C-005

### Included Subtasks

T001 Capture the pre-existing baseline red set for `tests/charter/` + `tests/architectural/` on `planning_base_branch`, per plan.md's Baseline procedure (C-005)
T002 [RED] Commit failing ATDD tests for IC-01 (FR-001, FR-002, FR-005; User Stories 1 & 2) — `test_drg_only_pack_preserves_or_grows_typed_counts`, `test_drg_fragment_node_reaches_resolved_bundle`, `test_empty_org_pack_degrades_to_no_pack_baseline`
T003 [GREEN] Implement IC-01 — add `_load_org_layer()` combined existence-guard (`has_graph_files`-style, across `org_root` and `org_root/drg/`) in `src/charter/_drg_helpers.py`; wire into `load_validated_graph`; make T002's tests pass
T004 [RED] Commit failing ATDD tests for IC-02 (FR-003, FR-006; User Story 4) — `test_root_and_drg_both_present_neither_node_dropped`, `test_identical_edge_triple_deduped_to_one_not_dropped`
T005 [GREEN] Implement IC-02 — extend `_load_org_layer` to merge root+`drg/` via `merge_layers(root_graph, drg_graph)`; add `_dedup_org_layer_edges()` reusing `doctrine.drg.validator.duplicate_edge_triples` (C-001); make T004's tests pass
T006 [RED] Commit failing ATDD tests for IC-03 (FR-004; User Story 3 + the plan ruling's root-level broadening) — `test_malformed_yaml_drg_fragment_raises_distinguishable_failure`, `test_schema_invalid_drg_fragment_raises_same_distinguishable_shape`, `test_malformed_root_graph_with_valid_drg_sibling_raises_distinguishable_failure`, `test_malformed_root_graph_no_drg_directory_raises_distinguishable_failure` (kept as two distinct tests per the plan ruling / PLAN-FRESH2-003)
T007 [GREEN] Implement IC-03 — add `OrgDRGFragmentError(Exception)`; wrap the root-level and `drg/`-level loads independently in `_load_org_layer`, each `try/except DRGLoadError as exc: raise OrgDRGFragmentError(...) from exc`; verify the three new symbols correctly stay out of `_drg_helpers.py`'s `__all__` (C-002/C-007); make T006's tests pass
T008 Update the comment near `_load_action_doctrine_bundle`'s existing `except DRGLoadError` block in `src/charter/action_doctrine_bundle.py` (~lines 152–156 lead into the catch at ~line 200) to state the catch now fires only for project-layer malformed content — doc-only, no functional change
T009 Run the full targeted gate set (`mypy --strict`, `ruff check`, `pytest tests/charter/ tests/architectural/` including `test_no_dead_symbols.py` / `test_no_legacy_terminology.py` / `test_layer_rules.py` by name) and diff the resulting red set against T001's captured baseline (C-005)

### Implementation Notes

- Strict RED-before-GREEN ordering per subtask commit is mandatory (charter C-011 / spec.md
  C-003): T002 commits before T003, T004 before T005, T006 before T007. Each RED commit must
  fail for the *reason the test names* (see the WP prompt's per-test "Reverted-code check" for
  what a passing-when-it-shouldn't test would mean), not for an unrelated collection error.
- T001 precedes all RED/GREEN pairs and is not itself part of the red-first-per-FR discipline —
  it is a once-per-mission baseline capture, per plan.md's own distinction.
- T008 is a comment-only change with no test attached — it does not get its own RED/GREEN pair.
- T009 is the mission's non-negotiable Definition-of-Done gate; do not report the WP done
  without it passing (net of C-005's pre-existing-red exclusion).

### Parallel Opportunities

None. All nine subtasks are sequential — each GREEN subtask's implementation extends the same
function body the next RED subtask's tests will exercise (`_load_org_layer`'s growing surface),
and T008/T009 both depend on all three IC's implementation commits having landed. This mirrors
plan.md's own IC-01 → IC-02 → IC-03 sequencing note.

### Dependencies

None (only work package in this mission).

### Risks & Mitigations

- **Risk**: a conforming-but-incomplete IC-03 implementation fires the root-level
  `OrgDRGFragmentError` wrap only when `drg/` also exists alongside the malformed root graph —
  silently reopening this mission's own defect class for the standalone
  malformed-root-no-`drg/`-at-all shape. **Mitigation**: T006 commits
  `test_malformed_root_graph_no_drg_directory_raises_distinguishable_failure` as its own
  distinct test (not folded into the combined-case test) — this is the load-bearing test the
  plan ruling (PLAN-FRESH2-003) named explicitly for exactly this hazard.
- **Risk**: the root+`drg/` dedup step (T005) reimplements `(source, target, relation)`
  comparison independently instead of reusing the canonical primitive, creating a second
  definition of "duplicate" (violates C-001 / DIR-044). **Mitigation**: T005's implementation
  guidance in the WP prompt names `doctrine.drg.validator.duplicate_edge_triples` explicitly as
  the only permitted comparison; the reviewer checks the diff imports it rather than
  reimplementing the triple-equality check.
- **Risk**: `OrgDRGFragmentError` accidentally gets added to `_drg_helpers.py`'s `__all__`,
  which would make `tests/architectural/test_no_dead_symbols.py` treat it as a public export
  needing a `src/`-internal caller it will never have (by design it propagates uncaught to the
  CLI boundary). **Mitigation**: T007 explicitly checks this; plan.md's `__all__` Export
  Discipline table is the binding reference.
- **Risk**: this mission's rollout note (plan.md, "Mid-flight rollout note") — a pre-existing
  root+`drg/` org pack whose `drg/` content was previously dormant (never even inspected by
  `load_graph_or_dir`, which prefers a root-level `graph.yaml`) and happens to be malformed will
  hard-fail for the first time once this fix lands, for both the `drg/`-fragment and
  root-level-graph malformed shapes. This is intended (IC-03 doing exactly what FR-004
  requires), not a WP-level risk to mitigate in code — the WP's Definition of Done requires this
  be stated plainly in the mission's PR description, mirroring the #3385 non-goal disclosure.

---

## Dependency & Execution Summary

- **Sequence**: WP01 only — T001 → T002 → T003 → T004 → T005 → T006 → T007 → T008 → T009, in
  that order, per the Implementation Notes above.
- **Parallelization**: None available within this mission (see WP01's Parallel Opportunities).
- **MVP Scope**: WP01 in full — there is no smaller shippable slice; FR-001/FR-002 alone (IC-01
  without IC-02/IC-03) would leave FR-003's merge requirement and FR-004's failure-visibility
  requirement unmet, both High/Medium priority in spec.md.

---

## Requirements Coverage Summary

| Requirement ID | Covered By Work Package(s) |
|----------------|----------------------------|
| FR-001 | WP01 |
| FR-002 | WP01 |
| FR-003 | WP01 |
| FR-004 | WP01 |
| FR-005 | WP01 |
| FR-006 | WP01 |
| NFR-001 | WP01 |
| NFR-002 | WP01 |
| C-001 | WP01 |
| C-002 | WP01 |
| C-003 | WP01 |
| C-004 | WP01 |
| C-005 | WP01 |

---

## Subtask Index (Reference)

| Subtask ID | Summary | Work Package | Priority | Parallel? |
|------------|---------|--------------|----------|-----------|
| T001 | Capture pre-existing baseline red set (C-005) | WP01 | P1 | No |
| T002 | [RED] IC-01 tests (FR-001/002/005; US1&2) | WP01 | P1 | No |
| T003 | [GREEN] IC-01 combined guard implementation | WP01 | P1 | No |
| T004 | [RED] IC-02 tests (FR-003/006; US4) | WP01 | P2 | No |
| T005 | [GREEN] IC-02 root+drg/ merge + dedup implementation | WP01 | P2 | No |
| T006 | [RED] IC-03 tests (FR-004; US3 + root-broadening) | WP01 | P1 | No |
| T007 | [GREEN] IC-03 OrgDRGFragmentError + independent wraps | WP01 | P1 | No |
| T008 | action_doctrine_bundle.py comment update (doc-only) | WP01 | P3 | No |
| T009 | Full targeted gate set + baseline-red diff | WP01 | P1 | No |

---

> This mission is intentionally a single work package — see "Why one WP" above. Do not split
> without operator sign-off; the plan phase already ruled on this mission's shape.
