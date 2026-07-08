---
work_package_id: WP14
title: 'B-only meta routing: cli/commands + context/core/missions + transaction.py'
dependencies: []
requirement_refs:
- FR-005
tracker_refs: []
planning_base_branch: design/read-surface-ssot-closeout
merge_target_branch: design/read-surface-ssot-closeout
branch_strategy: Planning artifacts for this mission were generated on design/read-surface-ssot-closeout. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into design/read-surface-ssot-closeout unless the human explicitly redirects the landing branch.
subtasks:
- T041
- T042
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "3003181"
history:
- at: '2026-07-08T06:52:05+00:00'
  actor: planner
  action: created
agent_profile: python-pedro
authoritative_surface: src/specify_cli/
create_intent: []
execution_mode: code_change
owned_files:
- src/specify_cli/cli/commands/retrospect.py
- src/specify_cli/cli/commands/tracker.py
- src/specify_cli/cli/commands/_coordination_doctor.py
- src/specify_cli/context/mission_resolver.py
- src/specify_cli/core/mission_creation.py
- src/specify_cli/core/vcs/detection.py
- src/specify_cli/missions/_resolve_planning_branch.py
- src/specify_cli/mission.py
- src/specify_cli/mission_loader/command.py
- src/specify_cli/dashboard/scanner.py
- src/specify_cli/git/sparse_checkout.py
- src/specify_cli/lanes/worktree_allocator.py
- src/specify_cli/release/changelog.py
- src/specify_cli/coordination/transaction.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Load `/ad-hoc-profile-load` for `python-pedro`. Read `spec.md` (FR-005, C-004), `plan.md` (IC-05). **Append to `traces/*.md`.**

## Objective

Route the B-only meta reads in the cli/commands + context/core/missions cluster onto `load_meta*`,
including **`coordination/transaction.py`'s reads OUTSIDE the C-004-frozen 751-771 block**.

## Context

- **`coordination/transaction.py` (C-004):** route the file's meta reads that are OUTSIDE lines
  751-771. **Leave 751-771 (the legacy HEAD override) byte-unchanged** and add a byte-unchanged
  regression asserting that block is untouched (#1878 territory).
- `core/mission_creation.py`: route its genuine meta reads; note the `contextlib.suppress@~469` item
  is NOT in scope here (it wraps a create-time write; deferred campsite NOTE, not this WP).
- Per-site POST-#2091 contract (FR-005); no masking `allow_missing=True` on hard-failing sites.

## Subtasks

### T041 — Route cli + context + core + missions cluster
**First, enumerate the per-site inventory** (this cluster is ~25 `json.loads` sites across 13 files):
`grep -nE "json\.loads?\(" <each owned file>`, and for EACH genuine meta read record its chosen
`load_meta*` variant + `allow_missing`/`on_malformed` (post-#2091) in `traces/design-decisions.md`
BEFORE routing — do not wave-through "route the cluster". Then route the meta reads in `retrospect.py`,
`tracker.py`, `_coordination_doctor.py`,
`context/mission_resolver.py`, `core/mission_creation.py`, `core/vcs/detection.py`,
`missions/_resolve_planning_branch.py`, `mission.py`, `mission_loader/command.py`, `dashboard/scanner.py`,
`git/sparse_checkout.py`, `lanes/worktree_allocator.py`, `release/changelog.py` onto `load_meta*`.

### T042 — transaction.py (C-004)
Route transaction.py's meta reads OUTSIDE 751-771; leave 751-771 byte-unchanged; add a regression
asserting the block's bytes are unchanged. Record the boundary decision in `traces/design-decisions.md`.

## Branch Strategy
Planning + merge target: `design/read-surface-ssot-closeout`. `spec-kitty agent action implement WP14 --agent <name>`.

## Definition of Done
- [ ] Cluster meta reads routed (post-#2091).
- [ ] transaction.py: reads outside 751-771 routed; 751-771 byte-unchanged + regression.
- [ ] ruff/mypy clean; tracer updated.

## Reviewer guidance (opus)
**Critically confirm transaction.py:751-771 is byte-unchanged (C-004)** with a guarding regression.
Confirm mission_creation.py:469 was NOT folded here. Check post-#2091 contracts.

## Activity Log

- 2026-07-08T08:12:08Z – claude:sonnet:python-pedro:implementer – shell_pid=2804699 – Assigned agent via action command
- 2026-07-08T08:38:15Z – claude:sonnet:python-pedro:implementer – shell_pid=2804699 – Routed ~25 meta.json read sites across 14 files onto load_meta*; transaction.py:751-771 legacy-HEAD-override left byte-unchanged with content-anchored regression test; mission_creation.py:469 write-suppress correctly NOT touched. Full per-site inventory in agent final report (traces/ guard-blocked on lane).
- 2026-07-08T08:39:05Z – claude:opus:reviewer-renata:reviewer – shell_pid=3003181 – Started review via action command
- 2026-07-08T08:45:46Z – user – shell_pid=3003181 – Review passed: 25 sites routed post-#2091, transaction.py 751-771 byte-unchanged + content-pinned regression, mission_creation.py:469 untouched, lookalikes excluded
