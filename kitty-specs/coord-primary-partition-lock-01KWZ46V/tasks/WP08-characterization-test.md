---
work_package_id: WP08
title: Characterization test (regression lock)
dependencies:
- WP02
- WP03
- WP04
- WP05
- WP06
requirement_refs:
- C-007
- FR-006
- FR-009
- NFR-002
- NFR-004
tracker_refs: []
planning_base_branch: design/coord-primary-partition-lock
merge_target_branch: design/coord-primary-partition-lock
branch_strategy: Planning artifacts for this mission were generated on design/coord-primary-partition-lock. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into design/coord-primary-partition-lock unless the human explicitly redirects the landing branch.
subtasks:
- T038
- T039
- T040
- T041
- T042
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "1882036"
history:
- at: '2026-07-07T20:40:00+00:00'
  actor: planner
  action: created
agent_profile: python-pedro
authoritative_surface: tests/integration/
create_intent:
- tests/integration/test_placement_partition_golden_path.py
execution_mode: code_change
owned_files:
- tests/integration/test_placement_partition_golden_path.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Load `python-pedro` (implementer) via `/ad-hoc-profile-load`. Read `spec.md`, `plan.md` (IC-06),
`research.md` (D9), `quickstart.md`. **Depends on WP02–WP06.** The C-007 "#2429 gate" is **likely
already satisfied** (squad M2): `resolve_planning_read_dir` is already kind-aware post-#2119 and the
session-reaper rebase did not touch it — **verify** the surface is present/stable and proceed; do NOT
hold indefinitely. Pin against the current surface. Implement via
`spec-kitty agent action implement WP08 --agent claude`.

## Objective

Lock the strangle behaviorally: an end-to-end characterization test that walks the mission lifecycle,
exercises a write **mutation** through the seam, and asserts one partition-correct authority
independent of CWD, across coord and non-coord topologies.

## Subtasks

### T038 — Golden path
- `tests/integration/test_placement_partition_golden_path.py`: drive `mission create → commit spec →
  setup-plan → agent tasks status → agent decision verify` and assert each resolves the same
  partition-correct authority (planning → primary; lifecycle → coord for a coord mission).

### T039 — Lifecycle mutation
- Add ≥1 lifecycle mutation (`move-task` or a status transition) and assert its bookkeeping lands on
  the coord surface for a coord mission and primary for a non-coord one — verifying WRITE fidelity, not just reads.

### T040 — CWD independence
- Run the assertions from the repo root AND from an unrelated CWD (e.g. a temp dir); results must be identical. Cover a coord-routing and a `SINGLE_BRANCH`/`LANES` mission.

### T041 — Edge states + #2404-lite
- Assert: flatten transition (reads stored topology, not husk), deleted/unmaterialized coord (resolve via branch ref, no misleading error), protected-primary (routes to lane/PR path or explicit diagnostic). Add the **#2404-lite** assertion: accept-time ACCEPTANCE_MATRIX read resolves from the correct partition (not a stale `-coord` worktree). Cross-link #2404.

### T042 — Determinism + budget
- Ensure the test is deterministic and CWD-independent; wall-clock < 30 s (NFR-002); passes on repeated runs. Use `PWHEADLESS=1`-compatible patterns; no real-port/daemon dependency.

## Campsite (Sonar)

New test file — keep helpers ≤15; no pre-existing campsite.

## Branch Strategy

Base / merge target `design/coord-primary-partition-lock`. Worktree per computed lane. **Depends on
WP02–WP06** — sequence LAST (needs the routed behavior + bug fixes). The #2429 gate is likely moot
(squad M2 — `resolve_planning_read_dir` already kind-aware); verify the surface and proceed rather
than holding.

## Definition of Done

- Golden path + mutation + CWD-independence + edge states + #2404-lite all asserted and green.
- < 30 s, deterministic, passes 3 consecutive runs (NFR-002).
- `ruff` + `mypy` clean.

## Risks & Reviewer guidance

- **C-007**: pin against the current kind-aware `resolve_planning_read_dir` (gate likely already satisfied — verify, don't hold).
- The test must characterize CURRENT planning-on-primary + coord-for-bookkeeping (not the stale coord-authority premise).
- Reviewer confirms the mutation assertion actually exercises a WRITE through the seam (the split-brain's real locus).

## Activity Log

- 2026-07-07T23:30:53Z – claude:sonnet:python-pedro:implementer – shell_pid=1744022 – Assigned agent via action command
- 2026-07-08T00:13:51Z – claude:sonnet:python-pedro:implementer – shell_pid=1744022 – Ready; golden-path+mutation+CWD-independent+edges+#2404-lite; <30s
- 2026-07-08T00:15:03Z – claude:opus:reviewer-renata:reviewer – shell_pid=1882036 – Started review via action command
