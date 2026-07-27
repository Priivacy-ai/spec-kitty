---
work_package_id: WP04
title: Worktree-clean invariant enforcement + guard regression
dependencies:
- WP01
- WP02
- WP03
requirement_refs:
- FR-005
- FR-006
- FR-007
- FR-008
tracker_refs: []
planning_base_branch: fix/sync-worktree-clean-invariant
merge_target_branch: fix/sync-worktree-clean-invariant
branch_strategy: Planning artifacts for this mission were generated on fix/sync-worktree-clean-invariant. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/sync-worktree-clean-invariant unless the human explicitly redirects the landing branch.
subtasks:
- T015
- T016
- T017
- T018
- T019
phase: Phase 3 - Enforcement
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "64333"
history:
- at: '2026-06-30T13:20:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: debugger-debbie
authoritative_surface: tests/specify_cli/sync/test_worktree_clean_invariant.py
create_intent:
- tests/specify_cli/sync/test_worktree_clean_invariant.py
execution_mode: code_change
model: ''
owned_files:
- tests/specify_cli/sync/test_worktree_clean_invariant.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP04 – Worktree-clean invariant enforcement

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile in the frontmatter
**before parsing the rest of this prompt**, and behave according to its guidance.

- **Profile**: `debugger-debbie`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If the profile cannot be loaded, run `spec-kitty agent profile list` and select the
best match for `task_type: implement` on `authoritative_surface: tests/specify_cli/sync/`.

---

## Objective

Encode **INV-1** (the worktree-clean invariant) as a single **parametrized** contract
test across the whole covered command surface, plus a regression guard proving
`record-analysis` still catches *genuine* dirt and the allowlist did not grow. This
WP asserts the combined behavior delivered by WP01–WP03, and fails fast if any
covered command — now or in future — dirties a clean checkout.

## Context & Constraints

- New file: `tests/specify_cli/sync/test_worktree_clean_invariant.py`.
- Covered command surface (parametrize over this exact set):
  status-event emission, `sync status` (incl `--check`), `sync pull`, `sync push`, `sync run`, `tracker status`, `tracker map list`, dashboard daemon tick.
- Prior art to model on (read these first):
  - `tests/specify_cli/cli/commands/test_accept_clean_tree.py`
  - `tests/mission_runtime/test_self_bookkeeping_allowlist.py`
  - `tests/specify_cli/cli/commands/test_accept_readiness_no_write.py`
- Git helpers: `src/specify_cli/core/vcs/git.py` (porcelain/is_clean), `core/git_preflight.py`.
- The `record-analysis` allowlist is `meta.json` + `.kittify/encoding-provenance/...` (`cli/commands/agent/mission_record_analysis.py` + `mission_runtime/artifacts.py`); `config.yaml` is NOT in it and must stay out (C-001).
- **Constraints**: per-worker HOME isolation (do not touch real `~/.spec-kitty`); daemon/real-port variants run serially (`-n0`); 0 flakes; no lint/type suppressions.
- Contract reference: `contracts/worktree-clean-invariant.md`.

## Branch Strategy

- **Strategy**: `shared-lane`
- **Planning base branch**: `fix/sync-worktree-clean-invariant`
- **Merge target branch**: `fix/sync-worktree-clean-invariant`

> Depends on WP01+WP02+WP03 (asserts the combined fix). Owns the new test module
> exclusively.

## Subtasks & Detailed Guidance

### T015 — Invariant test harness + fixtures

**Steps**:
1. Build a fixture: a fresh git checkout with `SPEC_KITTY_ENABLE_SAAS_SYNC=1`, auth present (stub), and an **incomplete-identity** `config.yaml` (the realistic legacy case: missing `build_id`) — plus a variant with a tracker `binding_ref` upgrade pending.
2. Add a helper that snapshots `(git status --porcelain bytes, config.yaml content+mtime)` and asserts equality before/after.
3. Reuse `core/vcs/git.py` porcelain helpers; use per-worker HOME isolation.

**Validation**: the snapshot helper detects a real write (self-test with a deliberate touch).

### T016 — Parametrized no-dirty-tree assertion

**Steps**:
1. `@pytest.mark.parametrize` over the covered command surface.
2. For each command: snapshot → run command to completion (success or handled failure) → assert `git status --porcelain` byte-identical AND `config.yaml` unchanged (FR-001, FR-005, FR-006, AS-1).
3. Where invoking a real command is heavy (daemon tick), drive the underlying callable directly but keep it in the same parametrization.

**Validation**: passes against the WP01–WP03 implementation; fails if any command writes.

> **NFR-002 (latency) coverage**: this no-write assertion **is** the NFR-002 verification. Removing the side-effect write is the only latency change, so "≤50 ms added latency" is satisfied by construction. Do **not** add a wall-clock timing assertion — it would be flaky and violate NFR-004. Asserting "no added write" is the stable proxy for "no added latency".

### T017 — Disabled / unauthenticated variant

**Steps**:
1. Repeat the core assertion with `SPEC_KITTY_ENABLE_SAAS_SYNC` unset/false and with no auth.
2. Assert the same commands remain side-effect-free (FR-008, AS-6).

**Validation**: no writes in the disabled/unauth path.

### T018 — `record-analysis` guard regression

**Steps**:
1. Make a genuine uncommitted source edit; run `record-analysis`; assert it still exits non-zero with `DIRTY_WORKTREE` (FR-007, AS-4).
2. Assert the guard's allowlist does **not** include `.kittify/config.yaml` (introspect the allowlist constant in `mission_runtime/artifacts.py`) — proving C-001 was honored (the fix removed the write, did not allowlist it).
3. **C-002 negative assertion**: assert that running a read/sync command (e.g. `sync status --check`) does **not** invoke `doctor mission-state --fix` or any auto-repair/normalization as a side effect (patch/spy the doctor entry point and assert it is never called). This locks the "no auto-fix on sync" constraint.

**Validation**: real dirt is still caught; allowlist unchanged; no auto `doctor --fix` is triggered by a read/sync command.

### T019 — Extensibility guard + serial handling + flake check

**Steps**:
1. Structure the parametrization so adding a new covered command is a one-line addition; document that a new read/background command must satisfy INV-1 or this test fails (AS-7).
2. Mark daemon/real-port variants for serial execution (`-n0`); keep them out of the parallel path.
3. Run the module 20× to confirm 0 flakes.

**Validation**: stable across repeated runs; clear failure message naming the offending command.

## Test Strategy

```bash
PWHEADLESS=1 .venv/bin/pytest tests/specify_cli/sync/test_worktree_clean_invariant.py -q
# serial pass for daemon/real-port variants:
PWHEADLESS=1 .venv/bin/pytest tests/specify_cli/sync/test_worktree_clean_invariant.py -n0 -q
# flake check:
for i in $(seq 1 20); do PWHEADLESS=1 .venv/bin/pytest tests/specify_cli/sync/test_worktree_clean_invariant.py -q || break; done
```

## Risks & Mitigations

- **Risk**: invoking real `sync`/`tracker` commands needs network/auth. **Mitigation**: stub the server/auth layer; assert on local file state only.
- **Risk**: daemon tick is hard to drive. **Mitigation**: call the daemon's per-tick callable directly; keep it serial.
- **Risk**: flakiness from real ports. **Mitigation**: serial `-n0` for those variants; per-worker HOME isolation everywhere.

## Review Guidance

- The covered command surface matches the spec exactly.
- A deliberate write makes the test fail (negative control present).
- Guard regression asserts both: real dirt caught AND allowlist not grown.
- Daemon/real-port variants serial; no flakes in 20 runs.

## Activity Log

- 2026-06-30 — Prompt generated via /spec-kitty.tasks.
- 2026-06-30T15:48:52Z – claude:opus:debugger-debbie:implementer – shell_pid=48342 – Assigned agent via action command
- 2026-06-30T16:17:38Z – claude:opus:debugger-debbie:implementer – shell_pid=48342 – Parametrized no-dirty-tree over covered surface + guard regression + C-002 + disabled/unauth; 19/19 pass; mypy --strict+ruff green
- 2026-06-30T16:18:58Z – claude:opus:reviewer-renata:reviewer – shell_pid=64333 – Started review via action command
