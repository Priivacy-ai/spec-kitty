---
work_package_id: WP12
title: 'B-only meta routing: status/* + merge/* + sync'
dependencies: []
requirement_refs:
- FR-005
tracker_refs: []
planning_base_branch: design/read-surface-ssot-closeout
merge_target_branch: design/read-surface-ssot-closeout
branch_strategy: Planning artifacts for this mission were generated on design/read-surface-ssot-closeout. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into design/read-surface-ssot-closeout unless the human explicitly redirects the landing branch.
subtasks:
- T037
- T038
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "2784656"
history:
- at: '2026-07-08T06:52:05+00:00'
  actor: planner
  action: created
agent_profile: python-pedro
authoritative_surface: src/specify_cli/
create_intent: []
execution_mode: code_change
owned_files:
- src/specify_cli/status/aggregate.py
- src/specify_cli/status/identity_audit.py
- src/specify_cli/status/lifecycle_events.py
- src/specify_cli/status/store.py
- src/specify_cli/merge/baseline.py
- src/specify_cli/merge/conflict_resolver.py
- src/specify_cli/merge/ordering.py
- src/specify_cli/merge/preflight.py
- src/specify_cli/merge/state.py
- src/specify_cli/sync/emitter.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Load `/ad-hoc-profile-load` for `python-pedro`. Read `spec.md` (FR-005), `plan.md` (IC-05). **Append to `traces/*.md`.**

## Objective

Route the inline `json.loads(<meta>)` reads in the `status/*`, `merge/*`, and `sync/emitter.py`
files onto `load_meta`/`load_meta_strict`/`load_meta_or_empty`. B-only files (no Thread-A collision).

## Context

- Per-site **POST-#2091** contract (FR-005): a site that now hard-fails at the #2091 guard routes to
  `load_meta_strict`/`allow_missing=False`. Routing a now-hard-failing site to `allow_missing=True`
  would MASK the guard and re-introduce removed legacy tolerance — forbidden.
- `load_meta_or_empty` only where the site genuinely tolerates a missing/empty meta post-#2091.
- Do NOT route event-log / non-meta `json.loads` lookalikes. Match by the meta-path argument.
- These sites feed IC-06's ratchet floor (WP16) — every routed site raises the routed-count floor.

## Subtasks

### T037 — Route status/* + merge/* + sync
Route each file's meta read onto the correct `load_meta*` variant. Keep behaviour identical except
where post-#2091 semantics dictate strict.

### T038 — FR-005 adjudication + tracer
Record each site's chosen contract + rationale in `traces/design-decisions.md`. ruff/mypy clean;
complexity ≤15 on touched functions.

## Branch Strategy
Planning + merge target: `design/read-surface-ssot-closeout`. `spec-kitty agent action implement WP12 --agent <name>`.

## Definition of Done
- [ ] All listed files' meta reads routed via `load_meta*` (post-#2091 contract).
- [ ] No masking `allow_missing=True`; no lookalike routed; ruff/mypy clean; tracer updated.

## Reviewer guidance (opus)
Verify post-#2091 contract per site; confirm no lookalike routed; spot-check a strict vs allow-missing
choice against the site's failure semantics.

## Activity Log

- 2026-07-08T07:31:33Z – claude:sonnet:python-pedro:implementer – shell_pid=2436761 – Assigned agent via action command
- 2026-07-08T08:06:17Z – claude:sonnet:python-pedro:implementer – shell_pid=2436761 – Ready: status/merge/sync meta routed, post-#2091 contracts, ruff/mypy clean
- 2026-07-08T08:08:00Z – claude:opus:reviewer-renata:reviewer – shell_pid=2784656 – Started review via action command
- 2026-07-08T08:14:07Z – user – shell_pid=2784656 – Review passed: 5 genuine reads routed post-#2091 (aggregate strict, identity_audit allow_missing+raise->orphan, store raise, ordering x2 on_malformed=none best-effort mission_number), 8 lookalikes correctly excluded + baseline git-blob left as-is, 2 test assertions synced still assert fail-closed, ruff/mypy clean, 1343 tests pass 0 fail
