---
work_package_id: WP02
title: Phase-1 tests, orphan gate, residual reconcile
dependencies:
- WP01
requirement_refs:
- FR-003
- FR-004
- FR-006
tracker_refs: []
planning_base_branch: feat/mission-type-drg-edges
merge_target_branch: feat/mission-type-drg-edges
branch_strategy: Planning artifacts for this mission were generated on feat/mission-type-drg-edges. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/mission-type-drg-edges unless the human explicitly redirects the landing branch.
subtasks:
- T006
- T007
- T008
- T009
- T010
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "194515"
shell_pid_created_at: "1784190942.9"
history:
- Seeded by /spec-kitty.tasks (edges-first two-phase decomposition)
agent_profile: python-pedro
authoritative_surface: tests/doctrine/drg/
create_intent: []
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- tests/doctrine/drg/test_mission_type_nodes.py
- tests/doctrine/drg/migration/test_extractor.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your agent profile:

```
/ad-hoc-profile-load python-pedro
```

Adopt its lens, standards, and ATDD workflow for the entirety of this work package.

## Objective

**Phase 1, #2677.** Pin the mission-type edge behavior with focused tests (RED-first through the pre-existing
generator entry point), re-pin the stale S0 placeholder, confirm the red orphan gate goes green at **10 ≤ 14
without raising the ceiling**, and reconcile the shared residual doc so its recorded residual matches the
empirical 10. Depends on WP01 (the generator emit).

## Context

- WP01 makes the generator emit the 21 `mission_type→action` `requires` edges into the monolith.
- The stale placeholder `test_mission_type_nodes_have_no_incident_edges` lives at
  `tests/doctrine/drg/test_mission_type_nodes.py:87-99` (the file is **99 lines** — the test spans 87–99).
  It currently asserts mission_type nodes have **no** incident edges (the S0 nodes-only state).
- The orphan gate is `test_shipped_graph_orphan_count_within_documented_residual` in
  `tests/specify_cli/cli/commands/test_doctrine_regenerate_graph.py` — `DOCUMENTED_ORPHAN_RESIDUAL = 14`
  (~:44). **You do not edit that file** (WP04/WP05 re-point its reader for sharding); the gate greens
  automatically once WP01's edges land. You only *verify* it (T008).
- The shared residual doc `kitty-specs/mission-lifecycle-dispatch-drg-closeout-01KV0S99/drg-orphan-residual.md`
  is a **stale "Residual orphans (14)"** snapshot from a prior mission. Its 14 rows contain **none** of the 8
  nodes you wire (they post-date it). Reviewer-renata found ~4 of the 14 rows are already stale non-orphans.

## Subtasks

### T006 — [ATDD RED] Focused generator edge tests

Add to `tests/doctrine/drg/migration/test_extractor.py` (or a new sibling test file — but `owned_files` lists
`test_extractor.py`, so prefer extending it) tests that run the generator/extractor and assert:
- `mission_type:plan` emits **exactly** its 4 `requires` edges to `action:plan/{specify,research,plan,review}`.
- A non-plan type — `mission_type:documentation` — emits its full **7**-edge sequence (witnesses FR-001's
  "every built-in mission type", not just plan).
- **No** `mission_type:*` node and no `action:*` node named in an `action_sequence` remains an orphan.
- Total `mission_type→action` `requires` edge count is **21** (SC-001).

These are the **comprehensive green-pinning** tests: WP01 already demonstrated red-first inside its own loop
(DD-12), so on this branch (which builds on WP01's lane tip) they are green-on-arrival. Your job is to pin the
full behavior comprehensively, not to re-observe red. Do NOT reorder against WP01.

### T007 — Re-pin `test_mission_type_nodes_have_no_incident_edges` (FR-004)

In `test_mission_type_nodes.py:87-99`: **invert** the assertion — mission_type nodes now DO have outbound
`requires` edges to their actions. Do **not** delete the test (stale-contract → re-pin, per the charter's
test-remediation discipline). Correct the now-stale class/method docstrings ("Nodes-only in WP01" / "no edges
are emitted" → the edge-complete contract).

### T008 — Verify the orphan gate greens at 10 (C-002)

Run `test_shipped_graph_orphan_count_within_documented_residual`; confirm it passes at **10 ≤ 14**. Do **not**
raise `DOCUMENTED_ORPHAN_RESIDUAL`. If it does not green at 10, the edge pass (WP01) is wrong — report back,
do not paper over it by touching the ceiling.

### T009 — Reconcile `drg-orphan-residual.md` (FR-006 / C-003)

Reconcile the doc so its recorded residual reads **10**, matching the empirical post-fix count:
- The 8 mission_type/plan-action nodes you wire **never enter the table** (they are no longer orphans).
- Correct/remove the ~4 already-stale non-orphan rows (verify each against the live graph before touching it).
- **Leave the 10 true standalone residual rows for #1923** — do not edit them (shared-doc collision guard).
- Fix the header/metrics count from 14 to the reconciled 10.
- This is an ADD-and-reconcile edit, **not** an edit of existing mission-type rows (there are none).

### T010 — Reproduce the gates

Before Done, reproduce locally and confirm green:
```
uv run pytest tests/doctrine/drg tests/doctrine/drg/migration -q
uv run pytest tests/architectural/test_no_legacy_terminology.py -q
uv run spec-kitty doctrine regenerate-graph --check
```

## Branch Strategy

- Planning/base + merge target: **`feat/mission-type-drg-edges`**. Lane worktree from `lanes.json`.
- Depends on WP01: `spec-kitty agent action implement WP02 --agent claude` (branch off WP01's lane tip).

## Test strategy

This WP **is** the test surface for Phase 1. RED-first: T006/T007 assertions committed before the WP01 code in
the integration order. Targeted files: `test_extractor.py`, `test_mission_type_nodes.py`.

## Definition of Done

- [ ] New edge tests assert plan=4, documentation=7, 21 total, zero mission_type/action orphans (SC-001).
- [ ] `test_mission_type_nodes_have_no_incident_edges` inverted + docstrings corrected (not deleted).
- [ ] Orphan gate green at 10 ≤ 14; ceiling unchanged (C-002).
- [ ] `drg-orphan-residual.md` reconciled to 10; stale non-orphan rows corrected; 10 standalone rows untouched.
- [ ] DRG + terminology + freshness gates green; ruff + mypy --strict clean.

## Risks & reviewer guidance

- **Do not touch the 10 standalone residual rows** — they belong to #1923; touching them creates a merge
  collision (C-003). Reviewer: diff the residual doc and confirm only mission-type-adjacent + stale rows moved.
- **Ceiling discipline (C-002)**: reviewer must confirm `DOCUMENTED_ORPHAN_RESIDUAL` is still 14.
- **Residual doc is an out-of-map edit (by design)**: `drg-orphan-residual.md` lives under another mission's
  `kitty-specs/` dir (it belongs to #1923's closeout), so it is **not** in this WP's `owned_files` (finalize
  forbids `kitty-specs/` owned paths). T009 edits it as a documented, coordinated cross-artifact change (C-003)
  — record the one-line rationale in the WP history at implement time. No other WP touches it.

## Activity Log

- 2026-07-16T08:23:00Z – claude:sonnet:python-pedro:implementer – shell_pid=174439 – Assigned agent via action command
- 2026-07-16T08:33:37Z – claude:sonnet:python-pedro:implementer – shell_pid=174439 – T009: reconciled drg-orphan-residual.md 14->10; removed 4 already-stale non-orphan rows (documentation-gap-prioritization, clean-linear-commit-history, documentation-curation-audit, zombies-tdd) now carrying live inbound edges; 10 standalone rows for #1923 untouched; ceiling DOCUMENTED_ORPHAN_RESIDUAL unchanged at 14.
- 2026-07-16T08:34:22Z – claude:sonnet:python-pedro:implementer – shell_pid=174439 – Ready: edge tests (plan=4/doc=7/21 total) + re-pinned no-incident-edges test green; orphan gate 10<=14 (ceiling unchanged); residual doc reconciled 14->10 (4 stale non-orphan rows removed, 10 #1923 rows untouched). --force used deliberately: drg-orphan-residual.md is the WP-authorized C-003 out-of-map cross-artifact edit (T009); the guard's git-restore remedy would delete required T009 work.
- 2026-07-16T08:35:45Z – claude:opus:reviewer-renata:reviewer – shell_pid=194515 – Started review via action command
- 2026-07-16T08:41:48Z – user – shell_pid=194515 – Review passed (--force: C-003 WP-authorized cross-mission drg-orphan-residual.md edit trips the lane-branch kitty-specs guard, whose git-restore remedy would delete required T009 work — documented/expected, same reason for_review used --force). Edge tests (plan=4, doc=7, 21 total, zero mission_type/sequence-action orphans) exercise real generator non-vacuously and pass; no-incident-edges test genuinely inverted+re-pinned (not deleted) + docstrings corrected, green; orphan gate green 10<=14, DOCUMENTED_ORPHAN_RESIDUAL unchanged at 14 and that file NOT in diff; residual doc reconciled 14->10 — independently verified all 4 removed rows carry live inbound edges (documentation-gap-prioritization<-styleguide:docs-freshness-sla; clean-linear-commit-history<-DIRECTIVE_046; documentation-curation-audit<-action:documentation/accept; zombies-tdd<-delete-the-assertion-not-the-test), empirical orphan count computed =10 matching the 10 untouched standalone #1923 rows exactly, no mission-type/action rows added; DRG suite 166 passed, terminology green, regenerate-graph --check fresh, ruff+mypy --strict clean on both test files, zero new suppressions; scope clean (2 owned test files + authorized residual doc only).
