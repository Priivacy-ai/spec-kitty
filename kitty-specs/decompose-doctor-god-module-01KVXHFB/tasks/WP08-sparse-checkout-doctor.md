---
work_package_id: WP08
title: _sparse_checkout_doctor + sparse_checkout CC19 decompose
dependencies:
- WP07
requirement_refs:
- FR-003
- FR-004
- FR-005
tracker_refs:
- '2059'
planning_base_branch: prog/2059-doctor
merge_target_branch: prog/2059-doctor
branch_strategy: Planning artifacts for this mission were generated on prog/2059-doctor. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into prog/2059-doctor unless the human explicitly redirects the landing branch.
created_at: '2026-06-24T19:54:56+00:00'
subtasks:
- T022
- T023
- T024
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "3433094"
history:
- date: '2026-06-24'
  action: created
  actor: claude
agent_profile: randy-reducer
authoritative_surface: src/specify_cli/cli/commands/_sparse_checkout_doctor.py
create_intent:
- src/specify_cli/cli/commands/_sparse_checkout_doctor.py
- tests/specify_cli/cli/commands/test_sparse_checkout_doctor.py
execution_mode: code_change
owned_files:
- src/specify_cli/cli/commands/_sparse_checkout_doctor.py
- tests/specify_cli/cli/commands/test_sparse_checkout_doctor.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your assigned agent profile via the `/ad-hoc-profile-load` skill (profile: **randy-reducer**, role: implementer). Adopt its boundaries, governance scope, and initialization declaration for this work package. Then return here.

## Objective

Extract the sparse-checkout remediation cluster (E) into `_sparse_checkout_doctor.py` and **decompose the `sparse_checkout` command (CC19)** into ≤15-CC tested helpers.

## Context

- Cluster E (research §2, lines 1377-1563): `_render_sparse_finding` (1377), `_render_remediation_plan` (1429), `sparse_checkout` cmd (1451, CC19).
- The `sparse-checkout` command flags: `--fix`. Exit contract: 0 clean / 1 state-present-or-CI-refusal. The CC19 comes from the detection → finding-render → remediation-plan → `--fix`/CI-refusal branching.
- `doctor sparse-checkout` is safety-keyed by name (`compat/safety_modes.py`); the name stays byte-identical (I-7). Heavy domain imports (`specify_cli.git.sparse_checkout`) stay function-local per the existing pattern (cited `doctor.py:1476`,`:1385`).

## Subtasks

### T022 — Create `_sparse_checkout_doctor.py` + decompose
- Move Cluster E into the sibling, importing shared infra from `_doctor_shared`. Decompose `sparse_checkout` into ≤15-CC sub-helpers (e.g. detect → render-finding → build-remediation → apply-or-refuse). Keep domain imports function-local.
- `ruff check --select C901` on the sibling → zero findings.

### T023 — Delegate
- `sparse-checkout` command body becomes a thin shell delegating to the sibling, preserving the `--fix` behavior and the 0/1 (clean / state-present-or-CI-refusal) exit contract.

### T024 — Focused tests
- `test_sparse_checkout_doctor.py`: per-helper tests for finding render, remediation-plan render, the `--fix` apply path, and the CI-refusal path. ≥90% coverage; reuse fixtures from `tests/integration/sparse_checkout/*` where useful.
- WP01 golden green.

## Branch Strategy

Planning branch & merge target: **`prog/2059-doctor`** (PR-bound to `main`). Worktrees per `lanes.json`. Commit with `--to-branch prog/2059-doctor`; transitions from the primary checkout CWD.

## Test Strategy (ATDD)

RED per-helper + decomposed-branch tests before extraction; GREEN after. Golden green.

## Out-of-map edits

- `src/specify_cli/cli/commands/doctor.py` — delegate the `sparse-checkout` body. Owned by WP11; sequential chain → no concurrent writer.

## Definition of Done

- Cluster E in `_sparse_checkout_doctor.py`; `sparse_checkout` CC19 decomposed (C901 clean).
- `--fix` + CI-refusal + 0/1 exit contract byte-preserved (golden green); `sparse-checkout` name unchanged (I-7).
- ≥90% coverage; ruff + mypy --strict clean, zero new suppressions.

## Risks

- Relocating `sparse_checkout` at CC19 fails the gate.
- The CI-refusal exit path is subtle — keep its branch covered.

## Reviewer Guidance

Recommended reviewer: standard. Verify the decomposition (C901 clean), `--fix`/CI-refusal exits unchanged, name preserved, ≥90% coverage, golden green.

## Activity Log

- 2026-06-24T19:54:56Z – claude – planning – WP created (deps WP07; decompose sparse_checkout CC19).
- 2026-06-24T22:03:51Z – claude:opus:randy-reducer:implementer – shell_pid=3385089 – Assigned agent via action command
- 2026-06-24T22:16:03Z – claude:opus:randy-reducer:implementer – shell_pid=3385089 – Cluster E extracted; sparse_checkout CC19 decomposed; 98% cov; golden+integration green
- 2026-06-24T22:16:06Z – claude:opus:reviewer-renata:reviewer – shell_pid=3433094 – Started review via action command
- 2026-06-24T22:16:10Z – user – shell_pid=3433094 – Cluster E in _sparse_checkout_doctor; sparse_checkout CC19 decomposed (C901 clean); --fix+CI-refusal+0/1 exit byte-preserved (golden+sparse integration green); name unchanged (I-7); domain imports func-local; locate/interactive seams retargeted; one-way imports AST-verified; 98% coverage; mypy --strict clean
