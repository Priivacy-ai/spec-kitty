---
work_package_id: WP08
title: 'Gate-artifact WRITE surface de-husk (#2804 + #2404)'
dependencies: []
requirement_refs:
- FR-009
planning_base_branch: feat/verdict-seam-write-unification
merge_target_branch: feat/verdict-seam-write-unification
branch_strategy: Planning artifacts for this mission were generated on feat/verdict-seam-write-unification. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/verdict-seam-write-unification unless the human explicitly redirects the landing branch.
subtasks:
- T039
- T040
- T041
- T042
- T043
history: []
agent_profile: python-pedro
authoritative_surface: src/specify_cli/acceptance/matrix.py
create_intent: []
execution_mode: code_change
owned_files:
- src/specify_cli/merge/executor.py
- src/specify_cli/cli/commands/agent/mission_finalize.py
- src/specify_cli/acceptance/matrix.py
- src/specify_cli/acceptance/gates_core.py
role: implementer
tags: []
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile
Before reading further, load your assigned profile: run `/ad-hoc-profile-load python-pedro` (or
`spec-kitty charter context --action implement`). Do not start work until the profile is loaded.

## Objective

Make gate artifacts survive `spec-kitty merge` by removing the **second write surface** at the source:
no code path authors a PRIMARY-partition `acceptance-matrix.json` under a coordination topology. Green
the existing red-first pin `test_issue_2804_merge_resets_gate_artifacts.py` (do **not** rewrite it),
suppress the PRIMARY-husk producer, add a write-side check over **every** `write_acceptance_matrix` call
site, and retire `issue-matrix.md`. This is the **genuinely parallel lane** — it touches no verdict-seam
file and no census yaml.

## Context

- **Requirements**: FR-009 (write-surface leg: single write surface at both finalize-scaffold and
  accept-fill, #2404; verified by a write-side check); SC-005. Issues #2804 + #2404.
- **Contract**: [gate-artifact-write-surface.md](../contracts/gate-artifact-write-surface.md) — G1
  single write surface (write-side check, not just merge outcome), G3 `issue-matrix.md` retired.
- **Decision**: **D-PLAN-7** (fix at the write surface, not by winning-at-merge — driver registration is
  defense-in-depth, delivered in WP09), **D-PLAN-16 / auth F3** (the actual PRIMARY-husk producer is
  `mission_finalize._scaffold_acceptance_matrix_if_lane_based:1315` → `acceptance/matrix.py::scaffold_acceptance_matrix`
  — suppress the PRIMARY scaffold under coord topology; the husk producer runs at finalize time when
  coord may be **unmaterialized**, which is why it lands on PRIMARY).
- Verified anchors: `mission_finalize.py:1315` `_scaffold_acceptance_matrix_if_lane_based` (called at
  `:1622`), `:1337` `scaffold_acceptance_matrix(...)`.
- **Note (WP10 shares this file)**: `merge/executor.py` is owned here; WP10 converges the #3218 flatten
  call site (`executor.py:1246-1302`) onto its new primitive as an out-of-map edit (WP10 depends on
  WP08). Keep your executor edits to the driver-registration/gate-artifact region, away from the flatten
  bookkeeping region, so WP10's downstream edit stays clean.

## Subtasks

### T039 — Green the carry-red pin `test_issue_2804` (do NOT rewrite it)
- **Purpose**: SC-005 / C-002. The pin is already red: a filled acceptance + issue matrix must survive a
  real merge.
- **Steps**: Run `pytest tests/regression/test_issue_2804_merge_resets_gate_artifacts.py -q`, confirm
  red, then make it green via the write-surface fix (T040/T041). Do not edit the pin.
- **Files**: (do not modify) `tests/regression/test_issue_2804_merge_resets_gate_artifacts.py`.
- **Validation**: green after T040/T041 without touching the test body.

### T040 — Suppress the PRIMARY-husk producer under coord topology
- **Purpose**: FR-009 #2404 — remove the add/add divergence at the source.
- **Steps**: In `mission_finalize.py` `_scaffold_acceptance_matrix_if_lane_based` (`:1315`) and
  `acceptance/matrix.py::scaffold_acceptance_matrix`, suppress authoring a PRIMARY-partition
  acceptance-matrix under a coordination topology (D-PLAN-16). Handle the unmaterialized-coord case
  (finalize may run before coord materializes) — do not silently fall back to PRIMARY; resolve to the
  single COORD write surface via the canonical resolver (C-001).
- **Files**: `src/specify_cli/cli/commands/agent/mission_finalize.py`, `src/specify_cli/acceptance/matrix.py`.
- **Validation**: US4 scenario 2 — under coord, accept fills COORD only (no PRIMARY husk).

### T041 — `accept` writes COORD only; reconcile the fill path
- **Purpose**: FR-009 — the accept-fill and the finalize-scaffold share one COORD write surface.
- **Steps**: In `acceptance/gates_core.py` (+ `acceptance/matrix.py`), ensure the accept-fill resolves
  the COORD acceptance-matrix home under coord topology (PRIMARY only under SINGLE_BRANCH/LANES). No
  second surface.
- **Files**: `src/specify_cli/acceptance/gates_core.py`, `src/specify_cli/acceptance/matrix.py`.
- **Validation**: T039 green; the merged branch retains filled verdicts/evidence (US4 scenario 1).

### T042 — Write-side check over EVERY `write_acceptance_matrix` call site (G1)
- **Purpose**: SC-005 — a **write-side** guarantee, not just a merge-outcome assertion.
- **Steps**: Add a check that greps/enumerates **all** `write_acceptance_matrix` (and scaffold) call
  sites and asserts none authors a PRIMARY-partition acceptance-matrix under a coordination topology.
  This is the durable regression guard (paula finding — winning-at-merge is timing-dependent).
- **Files**: a test under `tests/regression/` or `tests/acceptance/` (new; within this lane).
- **Validation**: the check reds if a new PRIMARY-husk write is introduced.

### T043 — Retire `issue-matrix.md` (G3)
- **Purpose**: FR-009 — legacy `.md` issue-matrix retired (the `.json` is authoritative).
- **Steps**: Remove `issue-matrix.md` authoring; ensure the terminal `issue-matrix.json` is the single
  artifact. Coordinate the `.md`→`.json` driver seed-drift note with **WP09** (which owns
  `merge_driver.py`/`init.py` and fixes the driver seed). Do not edit those WP09-owned files here.
- **Files**: `src/specify_cli/merge/executor.py` / `acceptance/matrix.py` as applicable (within owned set).
- **Validation**: no `issue-matrix.md` produced; `issue-matrix.json` terminal survives merge.

## Branch Strategy note

`already-confirmed`; base == target. Prepare with `spec-kitty implement WP08`. **Parallel lane** — no
dependency on the verdict-seam chain (WP01–WP07) and no census yaml. WP10 depends on WP08 (shared
`executor.py`), so merge WP08 before WP10 starts.

## Definition of Done

- SC-005: `test_issue_2804` green **without** rewriting it (T039); the write-side check confirms no
  PRIMARY-partition acceptance-matrix under coord topology (T042); `issue-matrix.md` retired (T043).
- Gate: `pytest tests/regression/test_issue_2804_merge_resets_gate_artifacts.py -q` + the write-side
  check green; `ruff` + `mypy --strict src/specify_cli/acceptance src/specify_cli/merge` clean (NFR-003).

## Risks

- **Unmaterialized coord at finalize** — the husk producer runs before coord materializes; the fix must
  route to the single surface without a silent PRIMARY fallback (D-PLAN-16 risk).
- **Executor region collision with WP10** — keep edits away from the flatten bookkeeping region.
- **Rewriting the pin** — forbidden (C-002). Green it via the write-surface fix.

## Reviewer guidance

Confirm `test_issue_2804` body is unchanged. Confirm the write-side check greps **every**
`write_acceptance_matrix` call site (not just `accept`). Confirm no PRIMARY husk under coord topology,
including the unmaterialized-coord finalize path.
