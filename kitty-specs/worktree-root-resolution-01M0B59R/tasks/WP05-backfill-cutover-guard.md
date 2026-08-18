---
work_package_id: WP05
title: backfill cutover guard false-green fix
dependencies:
- WP01
requirement_refs:
- FR-005
planning_base_branch: fix/worktree-root-resolution
merge_target_branch: fix/worktree-root-resolution
branch_strategy: Planning artifacts for this mission were generated on fix/worktree-root-resolution. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/worktree-root-resolution unless the human explicitly redirects the landing branch.
subtasks:
- T016
- T017
phase: Phase 1 - Fail-closed adopters
history:
- at: '2026-08-18T21:17:24Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: implementer-ivan
authoritative_surface: src/specify_cli/migration/runtime_state_cutover.py
create_intent:
- tests/specify_cli/migration/test_backfill_cutover_guard.py
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/migration/backfill_runtime_state.py
- src/specify_cli/migration/runtime_state_cutover.py
- tests/specify_cli/migration/test_backfill_cutover_guard.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP05 – backfill cutover guard false-green fix

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter (or any user-defined profile), and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `implementer-ivan`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this work package's `task_type` and `authoritative_surface`.

---

## Markdown Formatting

Wrap HTML/XML tags in backticks. Use language identifiers in code blocks.

---

## Objectives & Success Criteria

Make `migrate backfill-runtime-state`'s **cutover guard** invoking-checkout-aware so it can no longer report success merely because it verifies against **the same redirected primary/coord path it just wrote** when invoked from a lane worktree.

Done when:
- A red-first regression proves the false-green on base: invoked from a lane worktree, `verify_backfill` passes by reading the redirected path (issue #3049) — RED on `upstream/main`.
- After the fix, the guard is invoking-checkout-aware: it either verifies against the checkout the invocation is responsible for, or fails closed / refuses, so a lane invocation no longer produces a false pass.
- **The write target itself is unchanged** — writing runtime state into the coord/primary event log is deliberate (spec C-003, `canonicalize_feature_dir` "never `Path.cwd`"). Only the *guard's* false-green is the defect.
- `ruff` + `mypy` clean; complexity ≤15.

## Context & Constraints

- Root-cause class: `docs/plans/investigations/write-path-topology-root-cause.md` (#3129) lists #3049 as a confirmed member — *"writes outside a linked worktree; guard reads the same redirected path."* Remediation pattern is fail-closed checkout-identity awareness (#3128), not a checkout-local redirect.
- Prereq **WP01** provides `resolve_checkout_identity(cwd, intent)` in `src/specify_cli/core/checkout_identity.py`. Consume it; do not re-derive `.git` classification.
- Supporting docs: `kitty-specs/worktree-root-resolution-01M0B59R/spec.md` (FR-005, C-003), `plan.md`, `contracts/resolver-and-verdict-contracts.md` (C-3), `research.md` (Decision 2).
- Anchors (verify at implement time): `cli/commands/migrate_cmd.py:870` resolves `locate_project_root()` (primary); write target `migration/backfill_runtime_state.py:1438-1470` `canonicalize_feature_dir`. **Guard: `verify_backfill` is defined in `migration/backfill_runtime_state.py`** (invoked via `status/cutover_eligibility.py:210,250`) — NOT in `runtime_state_cutover.py`. It reads `feature_dir` event log + `read_dir` frontmatter (both already re-anchored to primary/coord). `runtime_state_cutover.py` holds the surrounding cutover machinery (`_verify_phase`, `cutover_mission`, `_resolve_primary_home_or_degrade:142-227`), whose coord-vs-primary comparison (both derived from the re-anchored `feature_dir`) does not catch lane-invocation. Both modules are in `owned_files`.

## Branch Strategy

- **Strategy**: lane-per-WP (coord topology)
- **Planning base branch**: fix/worktree-root-resolution
- **Merge target branch**: fix/worktree-root-resolution

> Execution worktrees are allocated per computed lane from `lanes.json`. Do not change these fields manually.

## Subtasks & Detailed Guidance

### Subtask T016 – Red-first: cutover guard passes against the redirected path from a lane

- **Purpose**: Prove the false-green exists on base before fixing it (NFR-001).
- **Steps**:
  1. In `tests/specify_cli/migration/test_backfill_cutover_guard.py`, build a fixture with a primary checkout containing a mission, plus a linked lane worktree of it.
  2. From the lane worktree, invoke the real backfill flow (through the CLI entry or the `verify_backfill` seam it calls) such that the write lands in the coord/primary event log.
  3. Assert the **current** behavior: `verify_backfill` reports success by reading the same redirected path — capture this as the red-first assertion. Mark `@pytest.mark.regression` and pin issue #3049 in a comment.
  4. Confirm RED on `upstream/main` (author the test to fail against unfixed code).
- **Files**: `tests/specify_cli/migration/test_backfill_cutover_guard.py` (new, ~110 lines).
- **Parallel?**: [P] — test authoring can precede the fix.
- **Notes**: Do NOT assert "writes into the invoking checkout" — the write target is deliberately primary/coord (C-003). Assert on the **guard's** honesty (false-green vs lane-aware/refusal).

### Subtask T017 – Make the cutover guard invoking-checkout-aware

- **Purpose**: Close the false-green while preserving the deliberate write target.
- **Steps**:
  1. In `migration/backfill_runtime_state.py` (where `verify_backfill` is defined), thread the invoking-checkout identity (from WP01's `resolve_checkout_identity`, `intent=WRITE`) into `verify_backfill`.
  2. When the invocation is from a foreign lane worktree (not owner), the guard MUST NOT pass merely by reading the redirected path — either verify against the checkout the invocation is responsible for, or fail closed / refuse via the single `FailClosedRefusal` seam (message names the checkout).
  3. If the surrounding cutover machinery in `migration/runtime_state_cutover.py` (`_verify_phase`/`cutover_mission`) needs the identity threaded through to reach `verify_backfill`, adjust those call sites too — without changing the canonical write target.
  4. Keep the owner-invocation path behaving exactly as today (no new refusal from the primary).
- **Files**: `src/specify_cli/migration/runtime_state_cutover.py`, `src/specify_cli/migration/backfill_runtime_state.py`.
- **Notes**: Complexity ≤15 — extract a small helper if `verify_backfill` grows a branch. No new blanket suppressions.

## Test Strategy

- `tests/specify_cli/migration/test_backfill_cutover_guard.py`: the red-first regression (T016) plus a green-after assertion that a lane invocation no longer produces a false pass, and an owner-invocation test proving unchanged behavior.
- Run: `pytest tests/specify_cli/migration/test_backfill_cutover_guard.py -n0 -q` (migration/state tests run serially).
- Classify any unrelated red per the charter baseline-red gotcha before attributing it here.

## Risks & Mitigations

- **Risk**: over-correcting by redirecting the write target (violates C-003). **Mitigation**: only the guard changes; add an explicit test asserting the write still lands in the canonical coord/primary log.
- **Risk**: `_resolve_primary_home_or_degrade` degrade path masks the lane case. **Mitigation**: assert the guard distinguishes owner vs foreign invocation, not just coord-vs-primary.

## Review Guidance

- Confirm the write target is unchanged and only the guard gained identity awareness.
- Confirm the red-first test is genuinely red on base and the message names the checkout on refusal.

## Activity Log

- 2026-08-18T21:17:24Z – system – Prompt created.
