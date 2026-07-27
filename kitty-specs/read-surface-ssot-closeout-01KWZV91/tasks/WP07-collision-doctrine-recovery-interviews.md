---
work_package_id: WP07
title: 'Collision cluster 3: doctrine/apply + recovery + interviews (A+B co-owned)'
dependencies: []
requirement_refs:
- FR-001
- FR-005
tracker_refs: []
planning_base_branch: design/read-surface-ssot-closeout
merge_target_branch: design/read-surface-ssot-closeout
branch_strategy: Planning artifacts for this mission were generated on design/read-surface-ssot-closeout. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into design/read-surface-ssot-closeout unless the human explicitly redirects the landing branch.
subtasks:
- T024
- T025
- T026
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "2780290"
history:
- at: '2026-07-08T06:52:05+00:00'
  actor: planner
  action: created
agent_profile: python-pedro
authoritative_surface: src/specify_cli/
create_intent: []
execution_mode: code_change
owned_files:
- src/specify_cli/doctrine_synthesizer/apply.py
- src/specify_cli/lanes/recovery.py
- src/specify_cli/missions/plan/plan_interview.py
- src/specify_cli/missions/plan/specify_interview.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Load `/ad-hoc-profile-load` for `python-pedro`. Read `spec.md` (FR-001, FR-003, FR-005), `plan.md`.
**Append to `traces/*.md`.**

## Objective

Co-own the A+B routing for these four A∩B collision files. **`lanes/recovery.py` is triple-loaded
and carries a NEVER-ROUTE site** — read the recovery guidance carefully.

## Context

- **`doctrine_synthesizer/apply.py`**: A reads ~@152, ~@737, ~@810 → `read_dir(kind)`; B meta reads
  ~@594, ~@784 → `load_meta*` (post-#2091). @136 is an unrelated parse — do NOT route.
- **`lanes/recovery.py`** (triple-loaded): route ONLY the **B meta read @245** onto `load_meta*`. The
  A feature_dir read **@755 is a by-design coord-aware WRITE — NEVER route it** (it feeds
  `emit_status_transition_transactional`; the source carries an explicit "MUST stay coord-aware —
  never route it" directive). WP11's FR-003 reclassifies @755 as a by-design write in the gate; this
  WP leaves @755 source-unchanged.
- **`plan_interview.py` / `specify_interview.py`**: A read ~@56 → `read_dir(kind)`; B meta read ~@58
  → `load_meta*`. (The duplicated `_get_mission_id` helper is an S1192 note — out of scope here.)
- Line numbers drifted post-#2462 — match by construct/token.

## Subtasks

### T024 — doctrine_synthesizer/apply.py A + B
Route the 3 A reads onto `read_dir(kind)` and the 2 B reads onto `load_meta*`. Leave @136 untouched.

### T025 — lanes/recovery.py B-only (NEVER route @755)
Route ONLY the B meta read @245 onto `load_meta*`. Leave @755 (the coord-aware write) source-unchanged.
Record in `traces/design-decisions.md` that @755 is intentionally not routed (FR-003 handles it in WP11).

### T026 — interviews A + B
Route `plan_interview.py` and `specify_interview.py` A reads (~@56) onto `read_dir(kind)` and B reads
(~@58) onto `load_meta*` (post-#2091).

## Branch Strategy
Planning + merge target: `design/read-surface-ssot-closeout`. `spec-kitty agent action implement WP07 --agent <name>`.

## Definition of Done
- [ ] apply.py + interviews: A→read_dir, B→load_meta*; lookalikes untouched.
- [ ] recovery.py: ONLY @245 routed; @755 source-unchanged (never-route documented).
- [ ] ruff/mypy clean; tracer updated.

## Reviewer guidance (opus)
**Critically confirm recovery.py:755 was NOT routed.** Verify A+B co-ownership, post-#2091 contracts,
and that unrelated parses were left alone.

## Activity Log

- 2026-07-08T07:31:15Z – claude:sonnet:python-pedro:implementer – shell_pid=2436761 – Assigned agent via action command
- 2026-07-08T08:00:03Z – claude:sonnet:python-pedro:implementer – shell_pid=2436761 – Ready: A+B co-routed; recovery.py:755 left as by-design write; ruff/mypy clean
- 2026-07-08T08:07:14Z – claude:opus:reviewer-renata:reviewer – shell_pid=2780290 – Started review via action command
- 2026-07-08T08:13:23Z – user – shell_pid=2780290 – Review passed: A+B co-routed, recovery.py:755 byte-unchanged (never-routed), STATUS_STATE/PRIMARY_METADATA kind-correct, post-#2091, ruff/mypy clean
