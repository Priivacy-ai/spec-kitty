---
work_package_id: WP05
title: CI fast-shard parallelization rollout
dependencies:
- WP01
- WP02
- WP04
requirement_refs:
- FR-003
- FR-004
- FR-005
- FR-007
- FR-012
- NFR-002
tracker_refs: []
planning_base_branch: feat/test-suite-acceleration
merge_target_branch: feat/test-suite-acceleration
branch_strategy: Planning artifacts for this mission were generated on feat/test-suite-acceleration. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/test-suite-acceleration unless the human explicitly redirects the landing branch.
subtasks:
- T017
- T018
- T019
- T020
- T021
- T022
phase: Phase 3 - Parallelization
agent: claude
shell_pid: '52577'
history:
- at: '2026-06-14T17:10:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: implementer-ivan
authoritative_surface: .github/workflows/ci-quality.yml
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- .github/workflows/ci-quality.yml
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP05 – CI fast-shard parallelization rollout

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the profile before parsing the rest of this prompt.

- **Profile**: `implementer-ivan`
- **Role**: `implementer`
- **Agent/tool**: `claude`

Recommended review profile for this parallelization architecture: **architect-alphonso**.

---

## Markdown Formatting

Wrap HTML/XML tags in backticks. Use language identifiers in code blocks.

## Objectives & Success Criteria

Flip the single-process CI fast-shards to file-pinned parallel execution, collapsing the critical path (charter ~9 min → ≤5 min, NFR-002). Roll out **one shard at a time**, each gated by collection-equivalence + the WP02 ratchet. This WP solely owns `.github/workflows/ci-quality.yml`.

**Done when**: every flipped shard collects identical nodeids vs serial and is green on 3 consecutive parallel runs; the slow-test de-dup removes the double-run; daemon/port tests run serially; status is re-routed correctly.

## Context & Constraints

- **Depends on WP01** (charter timing floors fixed — precondition for the charter flip), **WP02** (equivalence + ratchet helpers), **WP04** (HOME isolation — precondition for cli/sync/agent/status flips).
- Evidence: `architecture/test-suite-acceleration-plan.md` (A1/PP-01/R6, R2/PP-07, A6/R8, C-SERIAL). The exact `-n auto --dist loadfile --durations=50` pattern already ships on `integration-tests-core-misc` (lines ~1181/1295/1307) — copy it.
- Constraints: **C-003** `--dist loadfile` only (never bare `--dist load`); FR-005 serial pass for OS-global resources.

## Branch Strategy

- **Planning base branch**: feat/test-suite-acceleration
- **Merge target branch**: feat/test-suite-acceleration

## Subtasks & Detailed Guidance

### Subtask T017 – Slow-test de-dup on the specify-cli-heavy shard

- **Purpose**: A migration perf `@slow` test runs in both the slow-tests job and a core-misc shard (~28s/push).
- **Steps**:
  1. Add `and not slow` to the marker expr on the **specify-cli-heavy** shard step ONLY (around line ~1305 region — scope to that step, not the shared core-misc expr).
  2. **Never** use `--ignore=tests/specify_cli` on the slow-tests job (it would orphan 3 NFR guards).
  3. Add a collection-count gate proving the migration perf test is collected in exactly one job and the 3 specify_cli NFR guards remain reachable.
- **Files**: `.github/workflows/ci-quality.yml`.

### Subtask T018 – Flip the charter fast shard to `-n auto --dist loadfile`

- **Purpose**: Charter is the #1 critical-path job and gates the agent shard.
- **Steps**:
  1. Gated on WP01 (the `<0.1` timing floors must be converted first).
  2. Add `-n auto --dist loadfile --durations=50` to the charter fast-shard step.
  3. Run collection-equivalence (WP02) serial vs parallel; run the ratchet 3×; **re-measure** the 9→5 min claim — do not assume.
- **Files**: `.github/workflows/ci-quality.yml`.

### Subtask T019 – Flip doctrine, cli, sync shards; exclude `release`

- **Purpose**: Broaden the win after HOME isolation lands.
- **Steps**:
  1. Gated on WP04. Flip doctrine, cli, sync fast shards with `-n auto --dist loadfile`.
  2. **Do NOT flip the `release` shard** (14 items — xdist spawn + coverage-combine overhead nets slower).
  3. Equivalence + 3× ratchet per shard before merging that shard’s flip.
- **Files**: `.github/workflows/ci-quality.yml`.

### Subtask T020 – Flip the agent shard

- **Purpose**: The agent shard relies on the real-home queue; only safe after isolation.
- **Steps**:
  1. Gated on WP04’s isolation regression test being green AND WP02’s home guard active.
  2. Flip with `-n auto --dist loadfile`; equivalence + ratchet.
- **Files**: `.github/workflows/ci-quality.yml`.

### Subtask T021 – Daemon/port serial pass for orphan-sweep

- **Purpose**: `tests/sync/test_orphan_sweep.py` binds real ports (9400–9449); HOME isolation does not protect OS-global port binds (C-SERIAL, FR-005).
- **Steps**:
  1. Run the daemon/real-port sync tests in a dedicated step with `-n0` (serial), and `--deselect`/exclude them from the parallel sync selector.
- **Files**: `.github/workflows/ci-quality.yml`.

### Subtask T022 – Status re-route + trigger widen

- **Purpose**: Status was *slower* under naive `-n auto`; fix routing rather than brute-force parallelize.
- **Steps**:
  1. Implement the fast/integration split as an **inversion** (mark all fast EXCEPT git_repo/integration — never opt-in), with a collection-count gate (must drop exactly the expected count).
  2. Widen the `integration-tests-status` trigger to `(status OR sync)` to match the fast-shard scope.
  3. Do NOT add `-n auto` to integration-status without auditing the `reset_handlers` adapter-registry tests under loadfile.
- **Files**: `.github/workflows/ci-quality.yml`.

## Test Strategy

- For each flip: `collection_equivalence.assert_equivalent(serial_args, parallel_args)` (WP02), then `ratchet` 3×.
- Confirm the de-dup collection-count gate passes.

## Risks & Mitigations

- **Risk**: bare `--dist load` breaks file-local autouse resets. **Mitigation**: always `loadfile`.
- **Risk**: flipping cli/sync/agent before WP04 corrupts the real queue DB. **Mitigation**: hard dependency on WP04.
- **Risk**: `release` shard nets slower. **Mitigation**: leave it serial.

## Review Guidance

- Confirm every flip has an equivalence + ratchet record.
- Confirm `loadfile` everywhere and the serial pass for orphan-sweep.

## Activity Log

- 2026-06-14T17:10:00Z – system – Prompt created.
