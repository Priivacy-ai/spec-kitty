---
work_package_id: WP02
title: Merge stale-lane halt names a reachable remedy (#3579)
dependencies: []
requirement_refs:
- FR-003
- FR-004
planning_base_branch: fix/p0-reliability-triad
merge_target_branch: fix/p0-reliability-triad
branch_strategy: Planning artifacts for this mission were generated on fix/p0-reliability-triad. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/p0-reliability-triad unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-p0-reliability-triad-01M0YW93
base_commit: 980b4b81302641d4dd71170a5b0e5f96d8c6d35f
created_at: '2026-08-26T13:17:09.215842+00:00'
subtasks:
- T005
- T006
- T007
history:
- '2026-08-26: authored by tasks flow'
agent_profile: python-pedro
authoritative_surface: src/specify_cli/lanes/stale_check.py
create_intent: []
execution_mode: code_change
model: claude-sonnet-4-6
owned_files:
- src/specify_cli/lanes/stale_check.py
- tests/lanes/test_stale_check.py
- tests/lanes/test_merge.py
role: implementer
tags: []
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load python-pedro
```

## Objective

On a merge stale-lane halt, `_stale_remediation` (planning-lane branch) returns a raw `git checkout … && git merge …` remedy. That raw merge produces a `status.json` conflict git cannot reconcile, and the halt names **neither** of the tool's own remedies. Make the remediation name `spec-kitty agent status materialize` — which rebuilds `status.json` from the append-only event log — followed by `git add`, giving a reachable resolution.

**Do NOT** register a `status.json` merge driver: `status.json` is in `_NON_DIVERGENT_CANONICAL_ARTIFACTS` (defined in `tests/architectural/test_merge_reconciliation_class_guard.py`, NOT `merge.py`), so a driver fails the T013 completeness guard (C-002). See `research.md` (WP02) and `contracts/behavioral-contracts.md` (C-WP02).

## Branch Strategy
- Planning base / merge target: `fix/p0-reliability-triad`. Enter the lane via `spec-kitty agent action implement WP02 --agent claude`.

## Subtasks

### T005 — RED test first
- In `tests/lanes/test_stale_check.py`, add a test driving `check_lane_staleness()` → `_stale_remediation()` for a planning lane, asserting the remediation string contains `spec-kitty agent status materialize`. RED on current code (pre-fix text is raw git only). The existing raw-git assertions live at ~lines 132 and 174 (and 100/102, 165-166).

### T006 — Fix the remediation text
- Edit `_stale_remediation` (planning-lane branch, `src/specify_cli/lanes/stale_check.py`) so the emitted remediation, after the `git merge`, names `spec-kitty agent status materialize --mission <id> && git add <status.json>` as the resolution for the `status.json` conflict.
- `_stale_remediation(lane, lane_branch, mission_branch)` carries **no mission id/slug** in scope. Decide deliberately: either emit a literal `<id>` placeholder in the guidance text, or thread the slug from the same-file caller `check_lane_staleness` (both in-map). Do NOT parse the id out of the branch name.
- Keep it text-only (minimal fix). Introduce NO `status.json` merge driver and NO `.gitattributes` change.

### T007 — Lockstep assertions + guards
- Update the existing raw-git assertions in `tests/lanes/test_stale_check.py` (~132, ~174) in lockstep with the new text.
- **`tests/lanes/test_merge.py:218-219`** also asserts the remediation substring via `consolidate_lane_into_mission` — update it in lockstep (this file is in WP02's owned set specifically for this).
- Run `pytest tests/architectural/test_merge_reconciliation_class_guard.py -n0 -q` — the T013 arch guard must stay GREEN (proves no driver was added).
- Record a one-line note that the advertised `materialize` remedy is verified for the **same-schema** conflict WP02 targets; the cross-schema all-zeros edge is #3531 (out of scope, flagged).

## Definition of Done
- New stale-lane remediation test RED before, GREEN after.
- `test_stale_check.py` + `test_merge.py` remediation assertions updated and green.
- T013 arch guard green (no status.json driver).
- ruff + mypy clean.

## Risks / Reviewer guidance
- The `merge.py`-side "incorporate + rematerialize" variant is Out of Scope — keep the fix to the remediation text unless the reviewer explicitly widens it.
- Reviewer confirms the remediation names only tool commands (no hand-edit of a generated file), matching SC-002 (which is narrowed to remediation-text verification).
