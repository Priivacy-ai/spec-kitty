---
work_package_id: WP13
title: 'B-only meta routing: retrospective + post_merge + runtime/next + charter'
dependencies: []
requirement_refs:
- FR-005
tracker_refs: []
planning_base_branch: design/read-surface-ssot-closeout
merge_target_branch: design/read-surface-ssot-closeout
branch_strategy: Planning artifacts for this mission were generated on design/read-surface-ssot-closeout. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into design/read-surface-ssot-closeout unless the human explicitly redirects the landing branch.
subtasks:
- T039
- T040
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "3030733"
history:
- at: '2026-07-08T06:52:05+00:00'
  actor: planner
  action: created
agent_profile: python-pedro
authoritative_surface: src/
create_intent: []
execution_mode: code_change
owned_files:
- src/specify_cli/retrospective/gate.py
- src/specify_cli/retrospective/generator.py
- src/specify_cli/retrospective/summary.py
- src/specify_cli/post_merge/retrospective_terminus.py
- src/runtime/next/_internal_runtime/engine.py
- src/runtime/next/_internal_runtime/planner.py
- src/runtime/next/runtime_bridge.py
- src/charter/_io.py
- src/charter/mission_type_profiles.py
- src/specify_cli/charter_activate.py
- src/specify_cli/cli/commands/charter/_widen.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Load `/ad-hoc-profile-load` for `python-pedro`. Read `spec.md` (FR-005), `plan.md` (IC-05), and the
Shared Package Boundary note in `CLAUDE.md`. **Append to `traces/*.md`.**

## Objective

Route the B-only meta reads in `retrospective/*`, `post_merge`, `runtime/next/*`, and `charter/*`
onto `load_meta*` — **respecting the shared-package boundary for `runtime/next/`**.

## Context

- **`runtime/next/` shared-package boundary (critical):** route onto
  `specify_cli.mission_metadata.load_meta` ONLY where a `specify_cli` import is already sanctioned in
  that module. Where it is NOT sanctioned, do NOT introduce the import — either defer the site (an
  IC-06 allow-list entry with rationale + a filed follow-up issue) or stand up a runtime-local
  authority (a bigger call — flag it, do not improvise). Consult
  `tests/architectural/test_shared_package_boundary.py`.
- `retrospective/summary.py` has up to 4 sites; route each. Post-#2091 contract per FR-005.
- `charter/*` reads route onto `load_meta*` as normal `specify_cli`-adjacent code (verify imports).

## Subtasks

### T039 — Route retrospective + post_merge + charter
**First, enumerate the per-site inventory** (~22 `json.loads` sites — note `summary.py`×6 and
`runtime_bridge.py`×6 concentrations): `grep -nE "json\.loads?\(" <each owned file>`, and record each
genuine meta read's chosen `load_meta*` variant + post-#2091 contract in `traces/design-decisions.md`
BEFORE routing. Then route the meta reads in `retrospective/{gate,generator,summary}.py`, `post_merge/retrospective_terminus.py`,
`charter/{_io,mission_type_profiles}.py`, `charter_activate.py`, `cli/commands/charter/_widen.py`.

### T040 — runtime/next boundary adjudication
For each `runtime/next/*` site, decide route-vs-defer per the shared-package boundary. Record each
decision (and any deferral's allow-list entry + filed issue) in `traces/design-decisions.md`.

## Branch Strategy
Planning + merge target: `design/read-surface-ssot-closeout`. `spec-kitty agent action implement WP13 --agent <name>`.

## Definition of Done
- [ ] retrospective/post_merge/charter meta reads routed (post-#2091).
- [ ] runtime/next sites either routed (sanctioned import) or deferred with allow-list entry + issue.
- [ ] `test_shared_package_boundary.py` green; ruff/mypy clean; tracer updated.

## Reviewer guidance (opus)
**Critically verify no unsanctioned `specify_cli` import was added into `runtime/next/`.** Confirm
deferrals carry a filed issue. Check post-#2091 contracts.

## Activity Log

- 2026-07-08T08:11:59Z – claude:sonnet:python-pedro:implementer – shell_pid=2804699 – Assigned agent via action command
- 2026-07-08T08:40:07Z – claude:sonnet:python-pedro:implementer – shell_pid=2804699 – Ready: retrospective/runtime/charter meta routed; runtime/next boundary respected; ruff/mypy clean
- 2026-07-08T08:41:11Z – claude:opus:reviewer-renata:reviewer – shell_pid=3030733 – Started review via action command
- 2026-07-08T08:44:12Z – user – shell_pid=3030733 – Review passed: retro/runtime/charter routed post-#2091, runtime/next boundary respected (24 green), 2 charter-layer sites correctly deferred (layer rule), lookalikes excluded
