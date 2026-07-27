---
work_package_id: WP01
title: Pin claim-anchor to one canonical leg
dependencies: []
requirement_refs:
- NFR-004
planning_base_branch: fix/runtime-state-birth-cutover-all-paths
merge_target_branch: fix/runtime-state-birth-cutover-all-paths
branch_strategy: Planning artifacts for this mission were generated on fix/runtime-state-birth-cutover-all-paths. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/runtime-state-birth-cutover-all-paths unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-runtime-state-birth-cutover-all-paths-01KYH654
base_commit: e15a5c5f1a84df0deff1dfcd4b0a3ae9eb181fc2
created_at: '2026-07-27T07:52:44.765566+00:00'
subtasks:
- T001
- T002
- T003
- T004
phase: Phase 1 - Foundation
history:
- at: '2026-07-27T07:43:31Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/migration/backfill_runtime_state.py
create_intent:
- tests/specify_cli/migration/test_seed_anchor_determinism.py
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- src/specify_cli/migration/backfill_runtime_state.py
- tests/specify_cli/migration/test_seed_anchor_determinism.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP01 – Pin claim-anchor to one canonical leg

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the profile in the frontmatter before anything else.

- **Profile**: `python-pedro` · **Role**: `implementer` · **Agent/tool**: `claude`

---

## Objectives & Success Criteria

Make the runtime-state seed **payload byte-identical** across runs, machines, and
landing-path (leg) contexts, so the two stamp callers (the existing
`merge/executor.py` path and the new accept-time path in WP02) can never produce
divergent seed events. This is the prerequisite that prevents the
"flipped-but-unverifiable corpus" failure (spec edge case; risk R5).

**Done when**: running the seed twice from two different leg contexts produces
identical `status.events.jsonl` bytes, proven by a new test.

## Context & Constraints

- Read [plan.md](../plan.md) IC-02, [data-model.md](../data-model.md) "Seed
  determinism", and [research.md](../research.md) (R5).
- Seed **identity** is already deterministic (`deterministic_ulid = sha256(mission_id|wp_id|field)`; no wall-clock/random). The gap is the seed **payload**: the `at` claim anchor is resolved by `_resolve_anchor` → event-log `claimed` ts, else `_synthesize_claim_anchor` from `shell_pid_created_at` / `meta.json.created_at` (`backfill_runtime_state.py:432-483`). Its value depends on which leg carries the event log.
- Do **not** change seed identity derivation. Do **not** alter the ~319 already-migrated missions (C-003).

## Subtasks & Detailed Guidance

### Subtask T001 – Identify the canonical anchor leg

- **Purpose**: Decide the single leg from which the anchor is always resolved.
- **Steps**: Trace `_resolve_anchor`/`_synthesize_claim_anchor` and `cutover_mission`'s two-leg spine (PRIMARY `feature_dir` vs COORD `status_feature_dir`). Determine which leg holds the authoritative event log at accept-time vs merge-time and pick ONE (document the choice inline). The COORD leg holds the live event log under coord topology — favor it, but confirm both callers can resolve it.
- **Files**: `src/specify_cli/migration/backfill_runtime_state.py` (read `runtime_state_cutover.py` for the leg spine).

### Subtask T002 – Pin anchor resolution to the canonical leg

- **Purpose**: Remove leg-dependence from the payload.
- **Steps**: Make `_resolve_anchor`/`_synthesize_claim_anchor` resolve from the chosen canonical leg regardless of which `feature_dir`/`status_feature_dir` the caller passes. Keep the fail-closed behavior when no honest timestamp exists (do not silently fabricate). Preserve existing behavior for already-migrated missions.
- **Files**: `src/specify_cli/migration/backfill_runtime_state.py`.

### Subtask T003 – Red-first: payload-determinism-across-legs test [P]

- **Purpose**: Lock the invariant before the fix (DIRECTIVE_041).
- **Steps**: New test that seeds a fixture mission twice from two different leg contexts and asserts byte-identical `status.events.jsonl` (identity **and** payload). Write it RED against the pre-fix behavior, then green with T002.
- **Files**: `tests/specify_cli/migration/test_seed_anchor_determinism.py` (new).

### Subtask T004 – Assert byte-identical events across contexts

- **Purpose**: Payload-level, not just id-level, determinism (NFR-004).
- **Steps**: In the same test, diff the two `events.jsonl` blobs byte-for-byte and assert equality; also assert stability across a fixed `created_at` (machine independence).

## Test Strategy

Red-first. Run: `PWHEADLESS=1 uv run pytest tests/specify_cli/migration/test_seed_anchor_determinism.py -q`. Then the wider migration suite: `-n0 tests/specify_cli/migration/`.

## Risks & Mitigations

- **R5** payload divergence → the whole mission's invariant fails. Mitigation: this WP is the gate; WP02 depends on it.
- Over-broad edit re-serializing already-migrated missions → C-003 violation. Mitigation: change only anchor resolution, not the write path; assert no diff on a migrated fixture.

## Review Guidance

Confirm: anchor resolved from one leg only; seed identity unchanged; fail-closed on missing honest timestamp preserved; byte-level determinism test present and meaningful (not vacuous).

## Activity Log

- 2026-07-27T07:43:31Z – system – Prompt created.
