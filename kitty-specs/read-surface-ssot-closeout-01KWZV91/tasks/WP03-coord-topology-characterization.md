---
work_package_id: WP03
title: '#2404 coord-topology characterization test'
dependencies:
- WP01
- WP02
requirement_refs:
- FR-009
tracker_refs: []
planning_base_branch: design/read-surface-ssot-closeout
merge_target_branch: design/read-surface-ssot-closeout
branch_strategy: Planning artifacts for this mission were generated on design/read-surface-ssot-closeout. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into design/read-surface-ssot-closeout unless the human explicitly redirects the landing branch.
subtasks:
- T010
- T011
- T012
- T013
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "3342866"
history:
- at: '2026-07-08T06:52:05+00:00'
  actor: planner
  action: created
agent_profile: python-pedro
authoritative_surface: tests/integration/
create_intent:
- tests/integration/test_accept_matrix_coord_partition.py
execution_mode: code_change
owned_files:
- tests/integration/test_accept_matrix_coord_partition.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Load `/ad-hoc-profile-load` for `python-pedro`. Read `spec.md` (FR-009, SC-003), `plan.md` (IC-03).
**Append to `traces/*.md` when relevant.**

## Objective

Lock the #2404 class closed with an end-to-end coord-topology regression: `acceptance-matrix.json`
written + committed via **each** of the three write paths (`spec-commit`, `finalize`, `accept`
residual) lands on the coordination surface and is read back by `accept` — no stale copy.

## Context

- **Build ON #2462's landed `tests/integration/test_placement_partition_golden_path.py`** — reuse its
  coord-topology scaffolding, do NOT duplicate it. Reuse `tests/lane_test_utils.py` for a
  production-shaped minted `mission_id`/`mid8` (the #2462 CI-fixture lesson — a meta-less/empty-mid8
  fixture now hard-fails).
- **NFR-001 (critical):** assert the **kind-correct post-fix** surface. Do NOT pin the old kind-blind
  coord husk dir (Directive-041 — would freeze the bug). Carry a coord-topology divergence assertion.
- **Depends on WP01 + WP02** (the seam + accept routing must be in place).

## Subtasks

### T010 — Fixture on the golden path
New `tests/integration/test_accept_matrix_coord_partition.py`: a coord-topology mission with a valid
minted mid8, reusing the golden-path helpers.

### T011 — spec-commit path
Fill + commit `acceptance-matrix.json` via `spec-commit`; assert it lands on the coord surface and
`accept` reads it back (not a stale primary copy).

### T012 — finalize path
Same assertion via `mission_finalize` (the `kind=TASKS_INDEX` batch that includes the matrix).

### T013 — accept-residual path (SC-003)
Same via the `accept` residual commit path (WP02). Assert the wrong-kind-commit class is closed: a
mixed-partition-batch caller cannot reintroduce a stale matrix.

## Branch Strategy
Planning + merge target: `design/read-surface-ssot-closeout`. `spec-kitty agent action implement WP03 --agent <name>`.

## Definition of Done
- [ ] All three paths land the matrix on coord + read back (SC-003).
- [ ] Test asserts the kind-correct surface; does NOT pin the old coord husk dir.
- [ ] Reuses golden-path + lane_test_utils; no fixture duplication.

## Reviewer guidance (opus)
Confirm the test builds on the landed golden-path fixture. Verify it would go RED if the seam
regressed to per-batch kind. Confirm no old-coord-dir pinning (NFR-001/Directive-041).

## Activity Log

- 2026-07-08T08:48:51Z – claude:sonnet:python-pedro:implementer – shell_pid=3086246 – Assigned agent via action command
- 2026-07-08T09:16:38Z – claude:sonnet:python-pedro:implementer – shell_pid=3086246 – Ready for review: coord-topology #2404 characterization test added (T010-T013), all green + regression-pin proves it goes RED without per-file classification.
- 2026-07-08T09:19:39Z – claude:opus:reviewer-renata:reviewer – shell_pid=3342866 – Started review via action command
- 2026-07-08T09:23:51Z – user – shell_pid=3342866 – Review passed: SC-003 across all 3 real write paths (spec-commit CliRunner, finalize commit_for_mission kind=TASKS_INDEX mixed batch, accept _commit_residual_acceptance_artifacts) on ONE sequentially-evolving coord mission; read-back via the exact resolve_feature_dir_for_mission+read_acceptance_matrix seam accept uses; NFR-001 pins CoordinationWorkspace.resolve canonical path not the old husk; regression pin empirically bidirectionally-falsifiable (disabling the kind_for_mission_file->None monkeypatch flips it RED at line 436); golden-path + lane_test_utils reuse, no dup; residue-GC gap worked around in-test only + filed #2482 (out of scope, no product-code edits); 14 green, ruff clean, WP03 file mypy-clean. Note: pre-existing mypy no-any-return in tests/lane_test_utils.py (not WP03-owned, inherited from base).
