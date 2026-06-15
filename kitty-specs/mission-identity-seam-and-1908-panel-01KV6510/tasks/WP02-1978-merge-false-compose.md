---
work_package_id: WP02
title: '#1978 merge false-compose via mission_branch_name_required (P1 driver)'
dependencies:
- WP01
requirement_refs:
- FR-002
- FR-004
- FR-009
tracker_refs: []
planning_base_branch: mission/mission-identity-seam-and-1908-panel
merge_target_branch: mission/mission-identity-seam-and-1908-panel
branch_strategy: Planning artifacts for this mission were generated on mission/mission-identity-seam-and-1908-panel. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into mission/mission-identity-seam-and-1908-panel unless the human explicitly redirects the landing branch.
subtasks:
- T007
- T008
- T009
- T010
- T011
phase: Phase 2 - Route call sites
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "1331067"
history:
- at: '2026-06-15T17:53:20Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/merge/
create_intent:
- tests/merge/test_mid8_embedded_preflight.py
execution_mode: code_change
owned_files:
- src/specify_cli/cli/commands/merge.py
- src/specify_cli/merge/preflight.py
- src/runtime/next/runtime_bridge.py
- tests/merge/test_mid8_embedded_preflight.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP02 – #1978 merge false-compose (P1 driver)

## ⚡ Do This First: Load Agent Profile
Use `/ad-hoc-profile-load` for `python-pedro` (role implementer, agent claude) before anything else.

---

## Objectives & Success Criteria
Fix the merge-blocking false-negative for mid8-embedded slugs (#1978) at all three false-compose
sites by resolving the mission branch via the WP01 seam (`mission_branch_name_required(slug,
mission_id)`, which fail-closes) instead of a `kitty/mission-{slug}` f-string that drops `-{mid8}`.
This is the **P1 dogfooding driver** — this mission's own slug embeds its mid8, so its merge depends
on this fix. Read [spec.md](../spec.md) FR-002, [research.md](../research.md) R2/R5, paula F-5.

**Done when:** a mission whose slug embeds its mid8 passes merge preflight; legacy/non-embedded
missions still resolve; tests green.

## Context & Constraints
- **Depends on WP01** (uses `mission_branch_name_required`). TDD-first.
- `lanes.json.mission_branch` may be **absent** on legacy/flattened missions — do NOT rely on it
  alone; resolve via the seam (fail-closed on truly unresolvable modern missions).
- Bounded surface: only the 3 named files + the new regression test.

## Subtasks
### T007 — Failing regression (#1978)
Create `tests/merge/test_mid8_embedded_preflight.py`: build a mission whose slug ends in its mid8,
run the merge preflight, assert it currently FAILS (false-negative), then (after the fix) passes.
Add a legacy/non-embedded case that must keep working.

### T008 — `cli/commands/merge.py:1231` (`_check_mission_branch`, def L1219 — squad-corrected)
The false-compose lives inside `_check_mission_branch` at **`cli/commands/merge.py:1231`**:
`expected_branch = expected_branch or f"kitty/mission-{mission_slug}"`. Replace with a seam call:
`expected_branch = expected_branch or mission_branch_name_required(mission_slug, mission_id)`.
(NOTE: there is NO `_check_mission_branch` in `merge/preflight.py` — the squad's original T009 label
was wrong; the function is here in `merge.py`. The only `kitty/mission-` f-string in `merge.py` is
this one line.)

### T009 — `merge/preflight.py:86` (the SEPARATE preflight false-compose)
`merge/preflight.py:86` independently does `source_branch = mission_branch or
f"kitty/mission-{mission_slug}"`. Route it through `mission_branch_name_required` / the recorded
`lanes.json.mission_branch` when present, not a `kitty/mission-{slug}` reconstruction. (This is a
distinct site from T008; WP02 already owns `merge/preflight.py`.)

### T010 — `runtime/next/runtime_bridge.py:109` + its `mid8_from_slug` callers
Replace `return f"kitty/mission-{mission_slug}"` (L109) with the seam resolver (fail-closed path).
ALSO route this file's `mid8_from_slug` value-uses (≈L172/L2399) through the seam's authoritative
`resolve_mid8(slug, mission_id=…)` (FR-004 in-place-demotion fallout — WP02 owns this file, so it
routes its own callers; do not leave a now-demoted heuristic on a correctness path here).

### T011 — Gates
`ruff`+`mypy` on changed files; `PWHEADLESS=1 pytest tests/merge/ tests/lanes/ -q` (+ the new test).
- [ ] embedded-slug preflight passes; [ ] legacy still resolves; [ ] BOTH false-compose sites routed (merge.py:1231 + preflight.py:86); [ ] no residual `kitty/mission-{slug}` f-string in the 3 files; [ ] runtime_bridge `mid8_from_slug` callers routed to `resolve_mid8`; [ ] ruff/mypy clean.

## Branch Strategy
Planning base / merge target: `mission/mission-identity-seam-and-1908-panel`; lane-per-WP.

## Definition of Done
All 5 subtasks; 3 false-compose sites routed through the seam; embedded + legacy tests green.

## Reviewer Guidance
Confirm no `f"kitty/mission-{...}"` remains in the 3 files; fail-closed behavior preserved for
unresolvable modern missions; legacy path intact; the regression test actually reproduces #1978.

## Activity Log

- 2026-06-15T20:34:36Z – user – shell_pid=1071013 – Moved to planned
- 2026-06-15T20:34:37Z – claude:opus:python-pedro:implementer – shell_pid=1316676 – Started implementation via action command
- 2026-06-15T20:43:43Z – claude:opus:python-pedro:implementer – shell_pid=1316676 – Cycle 1: merge.py:2786 teardown mid8-correct (regression vs allocator path); resolve_branch_name wired into preflight search — FR-004 failover-with-warning live; #1978 + fail-closed intact; lint/mypy 0. NOTE: dead-symbol gate still flags reset_legacy_failover_warning + LEGACY_FAILOVER_SUPPRESS_ENV (test/intra-module seams; clearing needs WP01-owned branch_naming.__all__ or architectural allowlist — both UNOWNED by WP02).
- 2026-06-15T20:45:51Z – claude:opus:reviewer-renata:reviewer – shell_pid=1331067 – Started review via action command
- 2026-06-15T20:50:42Z – user – shell_pid=1331067 – Cycle-1 re-review APPROVED (reviewer-renata). --skip-review-artifact-check: rejected review-cycle-1.md is the PRIOR cycle artifact, addressed by c1 commit 3bc51f512. --force: benign kitty-specs drift on lane-b checkout (status authority is the coord worktree; lane diverges from merged mission branch) — NOT a code defect. VERIFIED: teardown merge.py:2786 routed via worktree_path(mission_id=_baseline_mission_id @L2400) — byte-identical to WP03 allocator for embedded slug (zero churn), KEEPS mid8 for un-embedded NNN- (TestWorktreeTeardownSeamRouting, real seam). resolve_branch_name in _check_mission_branch: embedded->identical+no warning (#1978 intact), legacy NNN->identical legacy+EXACTLY ONE one-shot DeprecationWarning, modern->BranchIdentityUnresolved (fail-closed). mission_branch_name_required RETAINED at pure-composer sites. Zero residual kitty/mission-{slug} f-strings in 3 files. Dead-symbols: resolve_branch_name+worktree_path cleared; residual flags = WP09 allowlist + WP01 cross-lane, not WP02 defects. ruff/mypy clean; 55 tests green; no new suppressions; tests/architectural untouched; scope clean. #1978 stays fixed.
