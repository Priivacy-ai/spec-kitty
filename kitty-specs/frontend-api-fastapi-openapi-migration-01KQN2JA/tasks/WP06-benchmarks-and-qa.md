---
work_package_id: WP06
title: Benchmarks, Release Checklist, Final QA
dependencies:
- WP05
requirement_refs:
- NFR-001
- NFR-002
- NFR-004
planning_base_branch: feature/650-dashboard-ui-ux-overhaul
merge_target_branch: feature/650-dashboard-ui-ux-overhaul
branch_strategy: Planning artifacts for this feature were generated on feature/650-dashboard-ui-ux-overhaul. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feature/650-dashboard-ui-ux-overhaul unless the human explicitly redirects the landing branch.
subtasks:
- T029
- T030
- T031
- T032
- T033
agent: claude
history:
- date: '2026-05-02'
  event: created
  note: Auto-generated alongside tasks.md
agent_profile: implementer-ivan
authoritative_surface: scripts/
execution_mode: code_change
owned_files:
- scripts/bench_dashboard_startup.py
- kitty-specs/frontend-api-fastapi-openapi-migration-01KQN2JA/release-checklist.md
- kitty-specs/frontend-api-fastapi-openapi-migration-01KQN2JA/spec.md
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load implementer-ivan
```

## Objective

Verify NFRs locally, record results, and produce the release-readiness artifact for the branch. After this WP the mission is ready for `/spec-kitty.review` and `/spec-kitty.merge`.

## Subtasks

### T029 — `scripts/bench_dashboard_startup.py`

Measures cold-start p50 for both stacks. Spawns `spec-kitty dashboard --transport <stack>` with a `--bench-exit-after-first-byte` flag (added in WP02 if not already there); times process spawn → first byte. 5 runs per stack, reports p50.

### T030 — Run benchmarks; record numbers

Run the benchmark script locally on the same machine for both stacks. Record p50 numbers in `release-checklist.md` (T031). Compare against NFR-001 (≤ 25 % regression) and NFR-002 (≤ 30 % regression on `/api/features` median).

### T031 — `release-checklist.md`

Mirrors the parent mission's release-checklist structure: operator/date/commit slots, SC-006 live verification block, NFR numbers block, rollback test block. The release checklist is the artifact the eventual release tag references for verification.

### T032 — Run full test suite

```bash
PYENV_VERSION=3.13.12 uv run --no-sync pytest tests/test_dashboard/ tests/architectural/ tests/sync/ -q
```

Confirm zero regressions. Document the pass count in the release checklist.

### T033 — Spec book-keeping

Update spec FR checkbox status (no code change; book-keeping only). Confirm every FR has a corresponding test or governance artifact landed.

## Definition of Done

- [ ] Benchmark script runs locally and produces a numeric report.
- [ ] NFR-001 and NFR-002 numbers are within thresholds (or, if not, a documented justification + reviewer signoff).
- [ ] Release checklist exists with all slots populated except SC-006 live verification (manual; filled at release time).
- [ ] Full test suite passes.
- [ ] Spec FR checkboxes reflect actual landed status.

## Reviewer guidance

- Confirm benchmark numbers come from a real run (script artifact attached or inline in checklist).
- Confirm rollback procedure was actually tested (set `dashboard.transport: legacy`, restart, confirm).
- Confirm no FR has a checkbox marked complete without corresponding code/test/doc.

## Risks

- Benchmark variance between machines. Mitigation: document the machine specs alongside the numbers; treat the threshold as advisory if the variance is high.
- NFR-001 / NFR-002 miss: if FastAPI cold-start exceeds the threshold on the test machine, decide whether to:
  1. Optimise (lazy-import heavy modules; defer router registration)
  2. Adjust the threshold with reviewer signoff and a documented rationale
  3. Hold the mission until optimisation lands
  Default action: try optimisation first; escalate before adjusting NFR.

## Activity Log

- 2026-05-02T20:33:22Z – claude – Moved to claimed
- 2026-05-02T20:33:25Z – claude – Moved to in_progress
- 2026-05-02T20:35:30Z – claude – Moved to in_review
- 2026-05-02T20:35:57Z – claude – Moved to approved
- 2026-05-02T20:36:06Z – claude – Done override: Lane-less mission run on parent feature/650-dashboard-ui-ux-overhaul branch
