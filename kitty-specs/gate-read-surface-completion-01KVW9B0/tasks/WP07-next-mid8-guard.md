---
work_package_id: WP07
title: '#2091 next-command empty-mid8 regression guard (Lane B)'
dependencies:
- WP00
requirement_refs:
- FR-006
tracker_refs:
- '#2091'
planning_base_branch: feat/gate-read-surface-completion
merge_target_branch: feat/gate-read-surface-completion
branch_strategy: Planning artifacts for this mission were generated on feat/gate-read-surface-completion. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/gate-read-surface-completion unless the human explicitly redirects the landing branch.
subtasks:
- T025
- T026
phase: Phase 2 - Lock-the-fix (Lane B, parallel)
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "4027586"
history:
- at: '2026-06-24T08:00:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: tests/runtime/next/
create_intent:
- tests/runtime/next/test_next_coord_branch_mid8_guard.py
execution_mode: code_change
model: ''
owned_files:
- tests/runtime/next/test_next_coord_branch_mid8_guard.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP07 – #2091 next-command empty-mid8 regression guard (Lane B)

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile in the frontmatter
**before parsing the rest of this prompt**, and behave according to its guidance.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If the profile cannot be loaded, run `spec-kitty agent profile list` and select the
best match for `task_type: implement` on `authoritative_surface: tests/runtime/next/`.

---

## Objective

Add a **dedicated red-first regression guard** driving the exact #2091 failure — an empty
`mid8` producing a malformed coordination branch (`git worktree add` exit 128) — through the
`next` entry point. **The product fix already exists** (`runtime/next/runtime_bridge.py`); this
WP **locks it** with a scenario-driving guard, then closes #2091 within the mission matrix.

Lane B — parallel with Lane A's spine; no dependency on the Lane A re-points (WP01–WP06).
Depends only on **WP00** (the write-surface foundation that fixes the editable CLI so this
WP's implement loop can run); WP00 is shared by every lane, not part of Lane A's spine.

## Context & Constraints

Ground truth — read before editing:
- [spec.md](../spec.md) FR-006; NFR-002 (revert the product guard to prove RED).
- [plan.md](../plan.md) IC-08.
- [data-model.md](../data-model.md) Lane B table (#2091 row).

Live-verified fix:
- `_wrap_with_decision_git_log` in `src/runtime/next/runtime_bridge.py:185`.
- `:213` import `resolve_mid8`; `:214-215` derive `_mid8` from `mission_id` (declared-identity
  keyed); `:224-229` the guard: `if coord_routing_topology and not _mid8: raise
  DecisionGitLogUnavailable(...)` (the #2091 fix — refuses to build a malformed coord branch
  on an empty mid8).

**Note (research):** the fix is at `src/runtime/next/runtime_bridge.py`, NOT
`_internal_runtime/` — anchor the guard at the correct module.

**Negative scope**: do NOT change product code. This WP adds a test only. The "lock" is a
red-first guard that goes RED if the `:224-229` guard is reverted.

## Branch Strategy

- **Strategy**: `parallel-lane` (Lane B — independent of Lane A)
- **Planning base branch**: `feat/gate-read-surface-completion`
- **Merge target branch**: `feat/gate-read-surface-completion`

> WP07 OWNS `tests/runtime/next/test_next_coord_branch_mid8_guard.py` exclusively.

## Subtasks & Detailed Guidance

### Subtask T025 – Red-first empty-mid8 guard via the `next` entry point

- **Purpose**: Drive the reported failure (empty mid8 → malformed coord branch) through the
  pre-existing `next` entry point.
- **Files**: new `tests/runtime/next/test_next_coord_branch_mid8_guard.py`.
- **Steps (red-first — DIRECTIVE_034)**:
  1. Build a coord-topology mission fixture where `mid8` resolves EMPTY.
     > **Remediation (reviewer-renata post-tasks) — FACTUAL FIX:** `resolve_mid8`
     > (branch_naming.py) returns `""` **iff `mission_id is None`** (or the resolved id is
     > <8 chars) — NEVER when `mission_id` merely "equals the slug" (a slug is ≥8 chars and
     > yields `slug[:8]`, a non-empty mid8). The previously stated seed condition
     > ("mission_id equals the slug / cannot derive a mid8") would NOT reproduce the bug →
     > a **false-green guard**. Seed the empty-mid8 condition correctly: a `meta.json` with
     > **no `mission_id`** (`mission_id` absent / `None`), e.g. a pre-083 legacy mission, so
     > `resolve_mid8` returns `""` and the `:224-229` guard fires.
  2. Drive the `next` entry point (the pre-existing command path that calls
     `_wrap_with_decision_git_log`) — NOT `resolve_mid8` directly. Assert the guard raises
     `DecisionGitLogUnavailable` (or the well-formed-branch behavior) — it does NOT proceed to
     `git worktree add` with a malformed `kitty/mission--lane-...` branch.
  3. Assert the POSITIVE path: a normal mission (resolvable mid8) builds a well-formed
     `kitty/mission-<slug>-<mid8>-lane-<id>` coord branch.
  4. Real ULID/mid8 fixtures (`01KVW9B0XFXPKTBE77QT3KRSW8` / `01kvw9b0`) for the positive case.

### Subtask T026 – Prove RED by reverting the product guard

- **Purpose**: NFR-002 — prove the guard is non-vacuous by reverting the fix.
- **Files**: `tests/runtime/next/test_next_coord_branch_mid8_guard.py` (test + recorded proof).
- **Steps**:
  1. Temporarily revert the `:224-229` guard in `runtime_bridge.py` (locally, do NOT commit the
     revert), run the new test, confirm it goes RED (the malformed branch / 128 path is
     reached). Restore the guard, confirm GREEN.
  2. Record the revert-and-restore evidence in the activity log (the red-first proof).
  3. Close #2091 within the mission matrix (verified-already-fixed / regression-guarded).

## Test Strategy

- `pytest tests/runtime/next/test_next_coord_branch_mid8_guard.py -q`.
- **Real-port / daemon note**: if this exercises real worktree/`git worktree add`, run it
  serially (`-n0`) per the parallel-test rules. Prefer mocking `git worktree add` to assert the
  branch NAME passed (avoids real-port flakiness) while still driving the guard.
- Red-first evidence (revert+restore) recorded.
- `ruff check` + `mypy` on the test — zero issues, no suppressions.

## Definition of Done

- [ ] Empty-mid8 seeded by the CORRECT condition: a `meta.json` with **no `mission_id`**
  (`mission_id is None`) — NOT "mission_id equals the slug" (which yields `slug[:8]`, a
  non-empty mid8, and would not reproduce the bug).
- [ ] Red-first guard drives the #2091 empty-mid8 → malformed coord branch failure through the
  `next` entry point (not `resolve_mid8` directly).
- [ ] Positive path asserts a well-formed `kitty/mission-<slug>-<mid8>-lane-<id>` branch.
- [ ] RED proven by reverting the `runtime_bridge.py:224-229` guard (evidence recorded);
  GREEN with the guard.
- [ ] No product code changed (test-only lock).
- [ ] #2091 closed within the mission matrix.
- [ ] ruff + mypy clean; no suppressions.

## Risks & Mitigations

- **Wrong module anchor**: Mitigation: `src/runtime/next/runtime_bridge.py` (NOT
  `_internal_runtime/`) per research.
- **Real-port flakiness**: Mitigation: mock `git worktree add`, assert branch name; or run `-n0`.
- **Vacuous guard**: Mitigation: T026 revert-proof.

## Review Guidance

- Confirm the test drives `next`, not `resolve_mid8` directly.
- Confirm the empty-mid8 fixture seeds `mission_id` **absent/None** (not "equals the slug")
  — a fixture built on the wrong condition is green-before-and-after and the revert-proof
  catches nothing.
- Confirm the revert-and-restore RED evidence is recorded (a guard green-before-and-after the
  fix captures nothing).
- Confirm the branch-name assertion is on the well-formed `<slug>-<mid8>` form.

## Activity Log

- 2026-06-24T08:00:00Z – system – Prompt created.
- 2026-06-24T15:13:42Z – claude:opus:python-pedro:implementer – shell_pid=3973220 – Assigned agent via action command
- 2026-06-24T15:31:37Z – claude:opus:python-pedro:implementer – shell_pid=3973220 – 7 tests in tests/runtime/next/test_next_coord_branch_mid8_guard.py. Fixture: meta.json with coordination_branch but NO mission_id (correct empty-mid8 condition per reviewer-renata correction). T026 revert-proof: reverted guard -> RED (DID NOT RAISE; CoordinationWorkspace.resolve mocked to prevent masking), restored -> GREEN. ruff zero issues. mypy zero issues in test file. No product code changed. Closes #2091 in mission matrix.
- 2026-06-24T15:32:13Z – user – shell_pid=3973220 – Lane-h code 40f87f84b; status from main
- 2026-06-24T15:32:15Z – claude:opus:reviewer-renata:reviewer – shell_pid=4027586 – Started review via action command
- 2026-06-24T15:35:54Z – user – shell_pid=4027586 – Review passed: test-only regression guard for #2091. CORRECTED FIXTURE CONDITION verified — meta.json seeds NO mission_id so resolve_mid8(slug, mission_id=None) returns '' (not false-green slug[:8]); TestFixtureConditionVerification pins this. REVERT-PROOF verified by reviewer: disabling guard at runtime_bridge.py:224-229 → both empty-mid8 tests RED (DID NOT RAISE DecisionGitLogUnavailable), positive/fixture tests stay green; restore → 7/7 green. Real entry point: _wrap_with_decision_git_log (next path); CoordinationWorkspace.resolve mocked only to isolate — guard fires at :224 before reaching the mock (proven by revert). No product change (git diff = 1 test file, status clean after revert/restore). Positive path uses realistic 26-char ULID. ruff clean; mypy clean on test file (sole error is pre-existing schema.py product issue, not WP07).
