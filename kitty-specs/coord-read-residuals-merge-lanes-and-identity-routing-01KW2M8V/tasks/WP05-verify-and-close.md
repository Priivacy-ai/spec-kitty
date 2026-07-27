---
work_package_id: WP05
title: Verify & close — full-gate dry run, floor, issue-matrix terminal
dependencies:
- WP01
- WP02
- WP03
- WP04
requirement_refs:
- FR-010
- NFR-001
- NFR-003
tracker_refs:
- '#2185'
- '#2186'
- '#2187'
planning_base_branch: mission/coord-read-residuals-2185-2186
merge_target_branch: mission/coord-read-residuals-2185-2186
branch_strategy: Planning artifacts for this mission were generated on mission/coord-read-residuals-2185-2186. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into mission/coord-read-residuals-2185-2186 unless the human explicitly redirects the landing branch.
subtasks:
- T026
- T027
- T028
phase: Phase 4 - Close-out
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "1246694"
history:
- at: '2026-06-27T11:00:00Z'
  actor: system
  action: Prompt regenerated via /spec-kitty.tasks (canonical regeneration from corrected spec/plan)
agent_profile: python-pedro
authoritative_surface: tests/architectural/
create_intent:
- tests/architectural/test_coord_read_residuals_closeout.py
execution_mode: code_change
model: ''
owned_files:
- tests/architectural/test_coord_read_residuals_closeout.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP05 – Verify & close

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load `python-pedro` (implementer) before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

## Objectives & Success Criteria

- Cross-cutting verification: full architectural gate green (incl. the new call-shape arm — **both** shapes) with no un-pinned strangers; floor consistent with the recorded census; zero STATUS legs re-routed (WP04 STATUS-from-husk assertions are the primary proof); issue-matrix #2185/#2186/#2187 reach a terminal verdict, with #2185 backed by WP04 **behavioral** evidence (not a pin drain).

## Context & Constraints

- Spec [spec.md](../spec.md) (US3; SC-004/005; FR-010; NFR-001/003), [plan.md](../plan.md). Depends on WP01–WP04.
- **Gate-added-in-mission can't catch offenders in its own merge** → the dry run (T026) is the backstop and must demonstrate RED-on-revert, not just static green.
- This WP edits only the close-out artifacts (`issue-matrix.md`, `traces/`); it RUNS the gate/tests but does not edit the gate test files (owned by WP01).

## Branch Strategy
- **Planning base branch**: `mission/coord-read-residuals-2185-2186`
- **Merge target branch**: `mission/coord-read-residuals-2185-2186`

## Subtasks & Detailed Guidance

### T026 – Full-gate dry run + RED-on-revert proof
- Run the full `tests/architectural/` suite (and the `integration`/`git` CI-only shards locally per post-merge arch-gate discipline). Confirm the new call-shape arm (both shapes) is green and flags nothing un-pinned; `ruff` + `mypy` clean. **Beyond static-green:** actually **RUN the WP04 integration test and the WP01/WP02/WP03 per-site tests, and demonstrate RED-on-revert** — revert a routed read to coord-aware and confirm the test fails on a returned domain value, then restore. Static gate-green alone does NOT satisfy.

### T027 – Floor + NFR-001 confirm (close-out regression test) [P]
- Author `tests/architectural/test_coord_read_residuals_closeout.py` — a mission-level regression guard that asserts: (1) `ROUTED_CANONICALIZER_FLOOR` matches the recorded census (or, if seam-routing did not move the census, that this is stated plainly — no re-pinned-integer "gain"); (2) the FR-007 arm (both shapes) flags nothing un-pinned across the in-scope module families; (3) no STATUS leg was re-routed to PRIMARY. **NFR-001 primary evidence = the WP04 STATUS-from-husk assertions** (events / `recovery.py:664` / `status_feature_dir` legs still read the coord husk); this close-out test's diff-grep for re-routed STATUS legs is a **secondary** cross-check.

### T028 – Issue-matrix terminal + traces [P]
- Set #2185/#2186/#2187 to `fixed` in `issue-matrix.md` with evidence refs. **#2185 must cite the WP04 behavioral (revert-fails) evidence** — pins are admissible evidence only for **#2187**; do NOT cite a merge/lanes/core pin drain (none exists). #2186 cites the WP01 identity tests + the WP03 `:132` route. Append the implement-phase entries to the three `traces/` files (`approach-trace.md`, `design-trace.md`, `tooling-friction-trace.md`); validate the quickstart scenario.

## Test Strategy
- Whole-suite verification; this WP gates the mission `done`.

## Definition of Done

- Full `tests/architectural/` green (incl. the both-shape arm) with no un-pinned strangers; `ruff` + `mypy` clean.
- RED-on-revert demonstrated for the WP04 integration test + per-site tests.
- Floor consistent with census (or honestly recorded as un-moved); zero STATUS legs re-routed.
- Issue-matrix #2185/#2186/#2187 terminal with evidence refs (#2185 = behavioral; #2187 = pin).
- Three `traces/` files appended; quickstart validated.

## Risks & Mitigations
- A STATUS leg silently re-routed → T027 diff-grep + the WP04 integration test's STATUS-from-husk assertions.
- Gate-added-in-mission can't self-validate → the T026 pre-merge full-gate dry run is the backstop.

## Review Guidance
- `reviewer-renata`: confirm the terminal issue-matrix verdicts are evidence-backed (#2185 behavioral, not a pin), the gate dry run actually ran with RED-on-revert demonstrated, and the three traces are appended.

## Activity Log
- 2026-06-27T11:00:00Z – system – Prompt regenerated (canonical /spec-kitty.tasks from corrected spec/plan).
- 2026-06-27T11:43:39Z – claude:opus:python-pedro:implementer – shell_pid=1188002 – Assigned agent via action command
- 2026-06-27T12:13:09Z – claude:opus:python-pedro:implementer – shell_pid=1188002 – WP05 T026/T027: live FR-007 arm scan CLEAN (0 un-pinned, 12 identity + 10 lanes.json sites routed) + floor honesty + NFR-001; T026 surfaced 4 cumulative arch-gate baseline failures (pre-existing-to-WP05, close-out items)
- 2026-06-27T12:13:10Z – claude:opus:reviewer-renata:reviewer – shell_pid=1246694 – Started review via action command
- 2026-06-27T12:38:09Z – user – shell_pid=1246694 – Review passed: live FR-007 arm is a real production scan over the in-scope tree (0 un-pinned, anti-vacuity floor present, injected coord-aware offender flagged RED); floor honesty recorded (census un-moved by seam routing); NFR-001 pins WP04 behavioral proofs; 4 surfaced arch failures confirmed pre-existing cumulative debt via file-removal method (close-out items, not WP05)
