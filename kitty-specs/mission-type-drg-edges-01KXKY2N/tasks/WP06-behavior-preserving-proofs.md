---
work_package_id: WP06
title: 'Behavior-preserving proofs: equality, totality, silent-degrade'
dependencies:
- WP05
requirement_refs:
- FR-010
- FR-011
- FR-013
tracker_refs: []
planning_base_branch: feat/mission-type-drg-edges
merge_target_branch: feat/mission-type-drg-edges
branch_strategy: Planning artifacts for this mission were generated on feat/mission-type-drg-edges. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/mission-type-drg-edges unless the human explicitly redirects the landing branch.
subtasks:
- T029
- T030
- T031
- T032
- T033
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "643589"
shell_pid_created_at: "1784208461.16"
history:
- Seeded by /spec-kitty.tasks (edges-first two-phase decomposition)
agent_profile: python-pedro
authoritative_surface: tests/doctrine/drg/
create_intent:
- tests/doctrine/drg/test_graph_sharding_equality.py
- tests/doctrine/drg/test_sharding_silent_degrade.py
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- tests/doctrine/drg/test_graph_sharding_equality.py
- tests/doctrine/drg/test_sharding_silent_degrade.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your agent profile:

```
/ad-hoc-profile-load python-pedro
```

Adopt its lens, standards, and TDD workflow for the entirety of this work package.

## Objective

**Phase 2, #2680 — the correctness proof (DD-9/DD-10).** Prove the sharding migration is behavior-preserving
with tests that go beyond "the merged `DRGGraph` is equal": assert the merged sharded graph equals the
pre-sharding graph under an **explicit merge-order contract**, that **every populated node-kind round-trips**
(no target-only-node loss), and — the trap the squad flagged — that the three `DRGLoadError`-swallowing
consumers produce **identical outputs** before/after (they degrade silently, so merged-graph equality alone
would be green while data is lost).

## Context

- `merge_layers` (`loader.py:107`) **concatenates** fragments in alphabetical load order; the monolith was
  globally sorted by `(source,target,relation)`. So a naive order-sensitive `DRGGraph.__eq__` would false-fail.
- **The contract is PINNED (DD-11) — do not re-decide it:** the equality proof compares
  `generate_graph(...)`'s **returned in-memory `DRGGraph`** (the composed/calibrated/sorted graph, which is
  layout-independent by construction — NOT read from disk) against `load_built_in_graph()` reloaded from the
  fragments, with the merged graph **canonically re-sorted** before comparing node/edge **sets + counts**.
- The three silent-degrade surfaces (paula-patterns): `agent_profiles/repository.py` (empty graph → lost
  `specializes_from` lineage), `charter_runtime/lint/_drg.py` (`GraphState.MISSING`),
  `specify_cli/doctrine/pack_validator.py` (empty built-in URN set → validator false-pass).

## Subtasks

### T029 — [ATDD RED] merged-graph equality under the pinned DD-11 contract (FR-011)

Add `tests/doctrine/drg/test_graph_sharding_equality.py`. The **reference is non-negotiable (DD-11, closes the
vacuous-self-compare door renata flagged)**: call `generate_graph(...)` to get the composed in-memory
`DRGGraph` (the reference — layout-independent, NOT loaded from the sharded files under test), then load the
on-disk sharded layout via `load_built_in_graph()`. Canonically re-sort the merged graph, then assert its
node **set**, edge **set**, and node/edge **counts** equal the reference, and `assert_valid` agrees.
**Forbidden**: comparing `load_built_in_graph()` against itself or against a re-read of the same fragments
(vacuous — always green). The reference MUST be the freshly-composed in-memory graph.

### T030 — Partition-totality (FR-010)

Assert every populated node-kind present in the merged graph has a corresponding `src/doctrine/<kind>.graph.yaml`
fragment, and that loading only-fragments loses **no** node — specifically that target-only kinds
(`template`, `asset`, `glossary`, `glossary_scope`, `mission_step_contract`) survive the round-trip. Compare
per-kind node counts sharded-vs-reference.

### T031 — Silent-degrade proof: profile lineage (FR-013 / DD-10)

Add `tests/doctrine/drg/test_sharding_silent_degrade.py`: assert `specializes_from` lineage resolution via
`AgentProfileRepository.resolve_profile` (or the repository's DRG traversal) returns the **same parents** it
returns from the reference graph — i.e. the sharded graph did not degrade `repository.py` to empty.

### T032 — Silent-degrade proof: charter-lint + pack-validator (FR-013 / DD-10)

In the same file, assert: charter lint's built-in DRG `GraphState` is the healthy state (not `MISSING`)
against the sharded layout; and the pack-validator's built-in URN set (`pack_validator.py`) is the full
non-empty set (equal to the reference), so org-pack dangling-edge detection still sees the built-in universe.

### T033 — Gates green

```
uv run pytest tests/doctrine/drg tests/doctrine tests/charter tests/calibration \
  tests/specify_cli/cli/commands/test_doctrine_regenerate_graph.py \
  tests/specify_cli/test_documentation_drg_nodes.py tests/specify_cli/test_research_drg_nodes.py \
  tests/specify_cli/mission_step_contracts/test_research_composition.py -q
uv run pytest tests/architectural -q
uv run spec-kitty doctrine regenerate-graph --check
```
Confirm ruff + mypy --strict clean, `assert_valid` passes, arch/DRG/freshness gates green (including the
former monolith-reader suites WP04 migrated — this is the final proof the sharding delete broke nothing).

## Branch Strategy

- Planning/base + merge target: **`feat/mission-type-drg-edges`**. Lane worktree from `lanes.json`.
- Depends on WP05 (needs the sharded layout on disk): `spec-kitty agent action implement WP06 --agent claude`.

## Test strategy

New test files only. RED-first: the equality + silent-degrade assertions capture the invariants that make the
monolith delete safe. These are the tests reviewer-renata's finding demanded (output-level, not merged-graph
only).

## Definition of Done

- [ ] Merged sharded graph equals the pre-sharding reference under the pinned DD-9 contract (node/edge
      sets + counts + `assert_valid`).
- [ ] Every populated node-kind round-trips; target-only kinds proven present (partition-totality).
- [ ] Profile `specializes_from` lineage, charter-lint `GraphState`, and pack-validator built-in URN set are
      identical before/after sharding (silent-degrade guard).
- [ ] arch/DRG/freshness gates green; ruff + mypy --strict clean; complexity ≤ 15.

## Risks & reviewer guidance

- **Order-sensitive equality trap (DD-9)**: reviewer confirms the equality test uses the pinned canonical
  contract, not a raw list `==` that could false-pass or false-fail.
- **Reference graph provenance**: reviewer confirms the pre-sharding reference is a genuine capture (not the
  sharded graph compared against itself, which would be vacuous).
- **These proofs are the gate on the whole Phase 2**: if any fails, the monolith delete (WP05) is not safe —
  do not paper over; report the regression.

## Activity Log

- 2026-07-16T11:45:59Z – claude:sonnet:python-pedro:implementer – shell_pid=501633 – Assigned agent via action command
- 2026-07-16T12:54:23Z – claude:sonnet:python-pedro:implementer – shell_pid=605226 – Assigned agent via action command
- 2026-07-16T13:26:45Z – claude:sonnet:python-pedro:implementer – shell_pid=605226 – Ready: equality vs generate_graph in-memory (non-vacuous), totality incl template, 3 silent-degrade outputs identical, full T033 proof suite green. --force: inherited kitty-specs/ diffs are pre-existing lane-base artifacts (WP05 review cycles + other-mission closeout residuals); WP06 commit de0e5d7e7 touches only tests/doctrine/drg/ + synthesis-manifest.yaml, no kitty-specs/ changes of mine.
- 2026-07-16T13:27:44Z – claude:opus:reviewer-renata:reviewer – shell_pid=643589 – Started review via action command
