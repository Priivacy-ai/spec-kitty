---
work_package_id: WP04
title: Retire the blocking NFR-003 latency gate
dependencies:
- WP03
requirement_refs:
- C-001
- FR-004
- FR-005
- NFR-003
planning_base_branch: perf/next-latency-durable-fix
merge_target_branch: perf/next-latency-durable-fix
branch_strategy: Planning artifacts for this mission were generated on perf/next-latency-durable-fix. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into perf/next-latency-durable-fix unless the human explicitly redirects the landing branch.
subtasks:
- T015
- T016
- T017
- T018
phase: Phase 2 - Guard
history:
- timestamp: '2026-08-28T18:24:17Z'
  agent: system
  action: Prompt generated via tasks phase authoring
agent_profile: python-pedro
authoritative_surface: .github/workflows/ci-quality.yml
create_intent:
- tests/ci/test_no_blocking_latency_gate.py
execution_mode: code_change
model: ''
owned_files:
- .github/workflows/ci-quality.yml
- scripts/check_nfr_003_latency.py
- scripts/ci/flake_report.py
- tests/ci/test_no_blocking_latency_gate.py
role: implementer
tags: []
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If no profile is specified, run `spec-kitty agent profile list` and select the best match.

---

## Objective

Remove the blocking single-shot wall-clock latency gate now that the durable fix (WP01/WP02) and
the off-PR statistical guard (WP03) exist. Keep the clean-wheel **structural** smoke check. This
ends the ratchet (1.00 → 1.05 → 1.60 → 2.20s) permanently.

## Context

- Depends on WP03 — never remove the guard before its off-PR replacement exists (no guard gap).
- `.github/workflows/ci-quality.yml`: the "NFR-003 latency regression gate" step is a **discrete
  named step** (~`:4076`) inside `clean-install-verification`, SEPARATE from the structural smoke
  steps (~`:4031` "run next against fixture mission" + JSON-shape assert). Remove ONLY the latency
  step. `clean-install-verification` stays in `quality-gate.needs`; its smoke steps still gate (C-001).
- `scripts/check_nfr_003_latency.py` (185 lines): delete.
- `kitty-specs/shared-package-boundary-cutover-01KQ22DS/nfr-003-baseline.json`: drop the absolute
  `ci_target_median_seconds` ceiling; leave a short historical note field pointing to
  `.github/workflows/performance.yml` as the new home (do not delete the file's provenance record).

## Subtasks

T015 In `.github/workflows/ci-quality.yml`, delete the "NFR-003 latency regression gate" step (the one running `scripts/check_nfr_003_latency.py --runs 5`). Verify the structural smoke steps (run-next-against-fixture + JSON-shape assert, ~`:4031`) remain and that `clean-install-verification` stays in `quality-gate.needs`. (WP04)

T016 Delete `scripts/check_nfr_003_latency.py`. Then `grep -rn check_nfr_003_latency` repo-wide and remove/adjust EVERY live reference — a known one is `scripts/ci/flake_report.py:78` (owned by this WP). DoD is a clean repo-wide grep, not just a workflow grep. This (deleting the sole reader of `ci_target_median_seconds`) is what satisfies FR-005's "ceiling removed" by construction. (WP04)

T017 (CONSOLIDATION-PHASE, not in-lane) Flag that `kitty-specs/shared-package-boundary-cutover-01KQ22DS/nfr-003-baseline.json` must have its absolute `ci_target_median_seconds` ceiling removed and a `_retired` note added (pointing to `performance.yml` per #3595/#3787), preserving the historical provenance. This edit is performed by the orchestrator on the mission branch at consolidation — NOT in this lane — because lane branches reject `kitty-specs/` changes at the `move-task --to for_review` gate. Do not add the baseline JSON to this lane's diff. (WP04)

T018 (MANDATORY — the by-construction proof of FR-004/NFR-003/SC-002/C-001) Add `tests/ci/test_no_blocking_latency_gate.py` asserting, by parsing `.github/workflows/ci-quality.yml`: (a) NO step in the `quality-gate.needs` blocking set invokes `check_nfr_003_latency` or any wall-clock latency ceiling; (b) the clean-wheel structural smoke step (run-next-against-fixture, ~`:4031`) is still present (C-001); (c) the sole ceiling reader is gone — `scripts/check_nfr_003_latency.py` does not exist and no repo file references `check_nfr_003_latency` (this is the in-lane-satisfiable proof of FR-005; the dead `ci_target_median_seconds` field's physical removal from the baseline JSON is provenance hygiene handled at consolidation, T017). Declare a `pytestmark` marker. This must NOT be optional. (WP04)

## Branch Strategy

Planning branch and final merge target: `perf/next-latency-durable-fix`. Depends on WP03; merge
back into `perf/next-latency-durable-fix`.

## Definition of Done (observable in this diff)

- The "NFR-003 latency regression gate" step is gone from `ci-quality.yml`; the structural smoke steps remain; `clean-install-verification` still in `quality-gate.needs`.
- `scripts/check_nfr_003_latency.py` deleted; no dangling references remain (grep clean).
- `grep -n 'check_nfr_003_latency' .github/workflows/ci-quality.yml` returns nothing.
- (Consolidation-phase, outside this lane) `nfr-003-baseline.json` ceiling drop is handled by the orchestrator on the mission branch — see T017.

## Risks / Reviewer guidance

- **Do not** remove the structural smoke (C-001) — that would let a `next` that can't run at all pass CI.
- Verify `clean-install-verification` remains a required job (only its latency STEP is removed, not the job).
- Reviewer: enumerate `quality-gate.needs` post-change and confirm no wall-clock latency assertion survives anywhere on the blocking path.
