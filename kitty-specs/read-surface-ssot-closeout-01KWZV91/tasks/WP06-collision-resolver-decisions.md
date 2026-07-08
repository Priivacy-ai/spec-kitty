---
work_package_id: WP06
title: 'Collision cluster 2: context/resolver.py + decisions/service.py (A+B co-owned)'
dependencies: []
requirement_refs:
- FR-001
- FR-005
tracker_refs: []
planning_base_branch: design/read-surface-ssot-closeout
merge_target_branch: design/read-surface-ssot-closeout
branch_strategy: Planning artifacts for this mission were generated on design/read-surface-ssot-closeout. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into design/read-surface-ssot-closeout unless the human explicitly redirects the landing branch.
subtasks:
- T022
- T023
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "2700616"
history:
- at: '2026-07-08T06:52:05+00:00'
  actor: planner
  action: created
agent_profile: python-pedro
authoritative_surface: src/specify_cli/
create_intent: []
execution_mode: code_change
owned_files:
- src/specify_cli/context/resolver.py
- src/specify_cli/decisions/service.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Load `/ad-hoc-profile-load` for `python-pedro`. Read `spec.md` (FR-001, FR-005, C-001 honesty note),
`plan.md`. **Append to `traces/*.md` when relevant.**

## Objective

Co-own the A+B routing for these two A∩B collision files (linearization — never split across lanes).

## Context

- **Thread A**: `context/resolver.py` (~@172), `decisions/service.py` (~@117, ~@144) →
  `placement_seam(...).read_dir(kind)`, kind-correct (NFR-001).
- **Thread B**: `context/resolver.py` (~@75), `decisions/service.py` (~@125) → `load_meta*`
  (post-#2091 contract; do not mask the guard).
- **C-001 honesty note**: `resolver.py` is itself a read authority; route its own kind-blind reads,
  but do NOT claim a single funnel over the `*_feature_dir_for_mission` primitives (the gate covers
  the gated resolver, not every primitive). Do not over-reach.
- `decisions/service.py` @170 is an unrelated event-log parse — do NOT route it (Thread-B lookalike).

## Subtasks

### T022 — context/resolver.py A + B
Route the A read (~@172) onto `read_dir(kind)` and the B meta read (~@75) onto `load_meta*`. Mind the
C-001 boundary — no over-claiming.

### T023 — decisions/service.py A + B
Route both A reads (~@117, ~@144) onto `read_dir(kind)` and the B meta read (~@125) onto `load_meta*`.
Leave the @170 event-log parse untouched.

## Branch Strategy
Planning + merge target: `design/read-surface-ssot-closeout`. `spec-kitty agent action implement WP06 --agent <name>`.

## Definition of Done
- [ ] Both files A→read_dir, B→load_meta* (post-#2091); @170 event-log parse untouched.
- [ ] C-001 boundary respected; ruff/mypy clean; tracer updated.

## Reviewer guidance (opus)
Confirm A+B co-owned. Verify the @170 lookalike was NOT routed. Check C-001 honesty-note adherence.

## Activity Log

- 2026-07-08T07:31:06Z – claude:sonnet:python-pedro:implementer – shell_pid=2436761 – Assigned agent via action command
- 2026-07-08T07:58:34Z – claude:sonnet:python-pedro:implementer – shell_pid=2436761 – Ready: A+B co-routed (resolver.py Thread-A already fixed by #2115, left untouched w/ C-001 comment; decisions/service.py A+B routed via STATUS_STATE kind after PRIMARY_METADATA broke WP04's coord-aware regression test), @170 lookalike untouched, ruff clean, mypy pre-existing-only, 1072 tests green
- 2026-07-08T07:58:58Z – claude:opus:reviewer-renata:reviewer – shell_pid=2700616 – Started review via action command
- 2026-07-08T08:04:43Z – user – shell_pid=2700616 – Review passed: A+B co-routed both files; resolver.py Thread-A left kind-blind by design w/ C-001 honesty comment (handle->dir-name canon, content reads already WORK_PACKAGE_TASK-routed); decisions/service.py A->STATUS_STATE kind-correct (ledger+events are coord-authority state, must agree with emit.py write target; PRIMARY_METADATA regressed test_open_resolves_coord_aware_handle); B->load_meta(allow_missing=False,on_malformed=raise) both files, no FR-005 masking; @170 event-log JSONL parse untouched (lookalike); ruff clean; 3 mypy no-any-return pre-existing-only (identical on base); 1072 tests green
