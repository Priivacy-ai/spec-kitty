---
work_package_id: WP01
title: '#2770 durable un-pin (re-arm the DRG-staleness gate)'
dependencies: []
requirement_refs:
- FR-004
- NFR-004
tracker_refs:
- '#2770'
planning_base_branch: feat/doctrine-activation-freshness
merge_target_branch: feat/doctrine-activation-freshness
branch_strategy: Planning artifacts for this mission were generated on feat/doctrine-activation-freshness. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/doctrine-activation-freshness unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
agent: "claude:opus:reviewer-renata:reviewer"
history: []
agent_profile: python-pedro
authoritative_surface: tests/doctrine/drg/
create_intent: []
execution_mode: code_change
owned_files:
- tests/doctrine/drg/migration/test_extractor_projection.py
- tests/specify_cli/cli/commands/test_doctrine_regenerate_graph.py
- tests/architectural/test_charter_references_resolve.py
role: implementer
tags: []
shell_pid: "3344092"
shell_pid_created_at: "1784322960.15"
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your assigned agent profile via `/ad-hoc-profile-load python-pedro` (implementer). Do not act on the persona name alone — load the YAML.

## Objective

**Durably un-pin the four #2770 DRG-staleness tests** so they pass as ordinary, blocking
tests instead of being routed to the non-blocking regression-visibility gate. This clears
#2770 (release-sensitive, P0 per the red-main ADR 2026-07-17-1) and re-arms the gate against
future recurrence.

**Verified state (2026-07-17, this branch):** `spec-kitty doctrine regenerate-graph --check`
is **fresh** and all four tests **pass** — S-C's landing fold already regenerated the shipped
graph, wired the charter→reference citation, and set the baseline `289/765/11`. **So there is
NO regeneration, citation-wiring, or baseline change to do here.** Confirm that state first
(red-first inversion: the tests are already green *with* the marker; your change is removing
the marker and proving they stay green *without* it). If `regenerate-graph --check` is somehow
NOT fresh when you start, STOP and report — that is a different problem than this WP scopes.

**Anchor convention**: line numbers are indicative — resolve by symbol name.

## Scope fence (critical)

`@pytest.mark.regression` is a **general accepted-red regime** (ADR 2026-07-17-1) used by
~22 test files for many different issues. **Touch ONLY the 4 markers tied to #2770** — the
ones carrying a `2770` comment. Do **NOT** remove any other issue's `@regression` marker.

The 4 #2770-tied markers, by file:
- `tests/doctrine/drg/migration/test_extractor_projection.py` — **2 markers**:
  `TestDRGZeroDelta::test_regenerated_graph_matches_baseline_counts` and
  `TestDRGZeroDelta::test_shipped_graph_is_fresh_and_byte_identical`.
- `tests/specify_cli/cli/commands/test_doctrine_regenerate_graph.py` — **1 marker**:
  `test_check_reports_committed_graph_fresh`.
- `tests/architectural/test_charter_references_resolve.py` — **1 marker**:
  `test_no_new_charter_reference_danglers`.

## Subtasks

### T001 — Un-pin the two TestDRGZeroDelta markers
- Remove the `@pytest.mark.regression` decorator from both `TestDRGZeroDelta` methods in
  `test_extractor_projection.py`, and delete the now-stale "Accepted red (regression)…tracked
  by #2770" comment blocks above them.
- **Keep** the baseline constants `_EXPECTED_NODE_COUNT = 289 / _EXPECTED_EDGE_COUNT = 765 /
  _EXPECTED_ORPHAN_COUNT = 11` exactly, and keep the `# golden-count: cardinality-is-contract`
  markers. The upstream-drift explanation comment (`:46-51`) can be trimmed to past-tense but
  the numbers stay.
- Do not touch any non-#2770 content in this file.

### T002 — Un-pin test_check_reports_committed_graph_fresh
- Remove the `@pytest.mark.regression` marker + its #2770 comment from
  `test_doctrine_regenerate_graph.py::test_check_reports_committed_graph_fresh`. Nothing else.

### T003 — Un-pin test_no_new_charter_reference_danglers
- Remove the `@pytest.mark.regression` marker + its #2770 comment from
  `test_charter_references_resolve.py::test_no_new_charter_reference_danglers`. Nothing else.

### T004 — Verify green + gate clean
- `spec-kitty doctrine regenerate-graph --check` → green.
- Run the 4 tests; they pass **without** the marker:
  ```bash
  PWHEADLESS=1 uv run pytest \
    tests/doctrine/drg/migration/test_extractor_projection.py::TestDRGZeroDelta \
    tests/architectural/test_charter_references_resolve.py::test_no_new_charter_reference_danglers \
    "tests/specify_cli/cli/commands/test_doctrine_regenerate_graph.py::test_check_reports_committed_graph_fresh" \
    -p no:cacheprovider -q
  ```
- Confirm no other `@regression` marker changed: `git diff` touches only the 3 owned files and
  only the 4 #2770 markers/comments.
- The regression-visibility gate (`tests/architectural/test_suite_jobs_gate_blocking.py`) must
  still pass — it asserts the routing regime, not a specific count; if it hard-codes a
  regression-test count that now drops by 4, that is an out-of-map signal: **STOP and report**
  rather than editing that gate here (it is not in your owned set).

## Branch Strategy

Planning base + merge target: `feat/doctrine-activation-freshness`. Execution worktree is
allocated for this WP's lane from `lanes.json`. This WP has no dependencies and lands first.

## Definition of Done

- [ ] The 4 #2770 markers + stale comments removed (and only those).
- [ ] Baseline 289/765/11 unchanged; `regenerate-graph --check` green.
- [ ] The 4 tests pass as ordinary tests.
- [ ] `git diff` limited to the 3 owned test files; no other `@regression` marker touched.
- [ ] ruff clean on changed files (no import churn).

## Risks

- **Touching a non-#2770 marker** → breaks another issue's accepted-red. Mitigation: filter by
  the `2770` comment; diff-review before commit.
- **The gate hard-codes a regression count** → out-of-map; report, don't silently edit.

## Reviewer guidance (reviewer-renata, opus)

Verify the diff removes exactly 4 markers in 3 files, all #2770-tied; baseline numbers intact;
`regenerate-graph --check` green; the 4 tests green un-pinned; no scope creep into other
`@regression` users or the gate-routing test.

## Activity Log

- 2026-07-17T21:11:26Z – claude:sonnet:python-pedro:implementer – shell_pid=3330116 – Assigned agent via action command
- 2026-07-17T21:15:23Z – claude:sonnet:python-pedro:implementer – shell_pid=3330116 – Un-pinned 4 #2770 markers; graph fresh; 4 tests green un-pinned; gate clean
- 2026-07-17T21:16:02Z – claude:opus:reviewer-renata:reviewer – shell_pid=3344092 – Started review via action command
- 2026-07-17T21:20:25Z – user – shell_pid=3344092 – Review passed (renata/opus): 4 #2770 markers durably un-pinned; baselines 289/765/11 intact; graph fresh; 4 tests green un-pinned; no scope creep.
