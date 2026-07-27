---
work_package_id: WP04
title: workflow.py campsite-first + feature_dir routing
dependencies: []
requirement_refs:
- FR-001
tracker_refs: []
planning_base_branch: design/read-surface-ssot-closeout
merge_target_branch: design/read-surface-ssot-closeout
branch_strategy: Planning artifacts for this mission were generated on design/read-surface-ssot-closeout. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into design/read-surface-ssot-closeout unless the human explicitly redirects the landing branch.
subtasks:
- T014
- T015
- T016
- T017
- T018
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "3262844"
history:
- at: '2026-07-08T06:52:05+00:00'
  actor: planner
  action: created
agent_profile: python-pedro
authoritative_surface: src/specify_cli/cli/commands/agent/workflow.py
create_intent:
- tests/specify_cli/cli/commands/agent/test_workflow_render_helpers.py
execution_mode: code_change
owned_files:
- src/specify_cli/cli/commands/agent/workflow.py
- tests/specify_cli/cli/commands/agent/test_workflow_render_helpers.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Load `/ad-hoc-profile-load` for `python-pedro`. Read `spec.md` (FR-001/FR-002), `plan.md` (IC-04),
and `campsite-workflow-py.md` (the SAFE/ADJACENT/OUT scout report). **Append to `traces/*.md`.**

## Objective

Per DIRECTIVE_025 tidy-first: campsite-clean the SAFE items in `workflow.py` (a 2907-line god-module)
**first, tested**, THEN route its two drainable feature_dir sites. `workflow.py` is not a cross-thread
collision file — it is Thread-A-only.

## Context

- `workflow.py` `implement` (complexity 109) and `review` (complexity 102) are the file's worst
  offenders; full degodding is OUT (filed #2464). This WP does only the SAFE campsite + the routing.
- **workflow.py has FOUR coord_authority sites — ALL must be routed** (WP11 drains the allowlist
  7→2, and all 4 workflow.py entries are in that allowlist; leaving any unrouted blocks floor-2):
  - **@1468** (`implement`, `feature_dir = ...`) — feedback-context **READ** → `read_dir(kind)`
  - **@1663** (`implement`, `_impl_feature_dir = ...`) — dossier-sync **READ** → `read_dir(kind)`
  - **@2710** (`review`, `_rv_feature_dir = ...`) — baseline-test **READ** → `read_dir(kind)`
  - **@2747** (`review`, `sub_artifact_dir = ... / "tasks" / wp_slug`) — review-cycle sub-artifact
    dir (`mkdir` + `review-cycle-N.md`), a **genuine WRITE** → `write_target(kind)`
  Routing the two single-line `implement` reads is NOT the #2464 degodding — do them here.
- **The reads and the @2747 write DIVERGE — do NOT dedupe** @2710 (read) with @2747 (write).
- Line numbers drifted post-#2462 — match by construct/token. The allow-list write locator says
  `2670`; the live write site is `2747` (WP11 freshens the locator).

## Subtasks

### T014 — SAFE: delete redundant return @1281 (S3626)
Remove the redundant `return` in `_ensure_workspace_materialized`. Zero behaviour change, no new test.

### T015 — SAFE: extract `_render_isolation_banner(wp_id, mode)` (S1192)
Extract the 9× duplicated blank-box banner line from `implement`(~1807-1824)/`review`(~2636-2652).
Add 2 pure-function tests (one per mode) in `test_workflow_render_helpers.py`. Behaviour-preserving.

### T016 — SAFE: extract `_render_wp_prompt_wrapper(wp_text)`
Extract the byte-identical 9-line prompt-wrapper block from `implement`(~1916-1924)/`review`(~2795-2803).
1 pure-function test. Behaviour-preserving.

### T017 — Route all THREE READ sites → `read_dir(kind)`
Route the three `resolve_feature_dir_for_mission` READS — `implement` @1468 (feedback-context),
`implement` @1663 (dossier-sync), and `review` @2710 (baseline-test) — onto
`placement_seam(...).read_dir(kind)` with the kind-correct `MissionArtifactKind` per site (NFR-001 —
the kind-correct surface; do NOT pin the old kind-blind coord husk, Directive-041). All three are
plain reads (verified). Leaving @1468/@1663 unrouted would block WP11's floor-2 drain.

### T018 — Route the @2747 WRITE → `write_target(kind)`
Route the review-cycle sub-artifact dir (`... / "tasks" / wp_slug`) onto `write_target(kind)` (genuine
write). Keep it DISTINCT from the @2710 read (they diverge). Document the read/write divergence in
`traces/design-decisions.md` so a reviewer does not flag "accidental duplication."

## Branch Strategy
Planning + merge target: `design/read-surface-ssot-closeout`. `spec-kitty agent action implement WP04 --agent <name>`.

## Definition of Done
- [ ] SAFE campsite items done + tested; `implement`/`review` behaviour unchanged.
- [ ] **ALL FOUR workflow.py sites routed**: @1468 + @1663 + @2710 → read_dir; @2747 → write_target.
- [ ] Read/write divergence kept distinct (not deduped); ruff/mypy clean; helpers ≤15; tracer updated.

## Reviewer guidance (opus)
Confirm campsite items are behaviour-preserving with tests. **Confirm all FOUR coord_authority sites
are routed (both `implement` reads @1468/@1663, not just the `review` pair) — a missed `implement`
read blocks WP11's floor-2 drain.** Confirm the read/write divergence is preserved (NOT deduped) and
kind-correct routing (NFR-001).

## Activity Log

- 2026-07-08T08:20:40Z – claude:sonnet:python-pedro:implementer – shell_pid=2861886 – Assigned agent via action command
- 2026-07-08T09:06:20Z – claude:sonnet:python-pedro:implementer – shell_pid=2861886 – Ready: 3 SAFE campsite items + 4 workflow.py sites routed (3 read/1 write); removed 4 workflow.py coord_authority entries, baseline 7->3, floors re-pinned per drain; WP11 does final floor-2 reconciliation
- 2026-07-08T09:08:53Z – claude:opus:reviewer-renata:reviewer – shell_pid=3262844 – Started review via action command
- 2026-07-08T09:16:50Z – user – shell_pid=3262844 – Review passed: campsite + 4 sites routed; @2747 via read_dir(WORK_PACKAGE_TASK) sound (write_target has no Path projection, same physical dir for PRIMARY, commit via move-task); gate baseline/floor 7->3 shrink-only, WP11 reconciles final 2
