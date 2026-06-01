---
work_package_id: WP02
title: '#1301 Part A: Package Version, Vendored Tree & Daemon Allowlist'
dependencies:
- WP01
requirement_refs:
- FR-003
- FR-007
tracker_refs: []
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-p0-test-failure-resolution-1298-1305-01KT1R2G
base_commit: da92d9f36f8eb7e41466e3a97f99c03cf8af9cc4
created_at: '2026-06-01T17:06:05.053303+00:00'
subtasks:
- T005
- T006
- T007
- T008
agent: "claude:sonnet-4-6:reviewer:reviewer"
shell_pid: "40690"
history: []
agent_profile: python-pedro
authoritative_surface: src/specify_cli/
execution_mode: code_change
owned_files:
- pyproject.toml
- uv.lock
- src/specify_cli/spec_kitty_events/**
- tests/sync/test_daemon_intent_gate.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else in this prompt, load your assigned agent profile:

```
/ad-hoc-profile-load python-pedro
```

This configures your Python implementer persona. Proceed only after the profile is loaded.

---

## Objective

Fix the packaging-level root causes of the #1301 cluster:
1. Ensure `spec_kitty_events` at the pinned version is installed (no version drift).
2. Remove the vendored events tree `src/specify_cli/spec_kitty_events/` if it exists.
3. Fix the daemon allowlist in `test_daemon_intent_gate.py` so the missing call site passes.

This WP does **not** touch contract fixtures or sync lifecycle tests — those are WP03.

---

## Context

The #1301 issue (filed per DIR-013) describes `spec_kitty_events 5.0.0` being installed while `uv.lock` pins `5.2.0`. WP02 of mission `01KSF9HJ` resolved the bulk of the cascade, but three sub-items survived.

**Triage reference**: The authoritative root-cause analysis is in `docs/01KSF9HJ-triage/triage.md` on branch `kitty/mission-test-stabilization-and-debt-pass-01KSF9HJ`. To read it: `git show kitty/mission-test-stabilization-and-debt-pass-01KSF9HJ:docs/01KSF9HJ-triage/triage.md | less`. It is not on `main` and should not be merged as part of this WP.

- **Vendored copy**: `src/specify_cli/spec_kitty_events/` may have been reintroduced (violates the shared-package-boundary cutover ADR 2026-04-25-1).
- **Daemon allowlist**: `test_no_unauthorized_daemon_call_sites` fails because a new events call site was added without updating the allowlist.
- **Version drift**: May or may not still be present on current `main`; T005 confirms.

**Prerequisite**: Read `baseline-refresh.md` from WP01 first. If #1301 is marked STALE, stop and report; do not make changes.

---

## Subtask T005 — Reproduce the #1301 Cluster

**Purpose**: Confirm which tests are still failing before touching any code.

**Steps**:
```bash
pytest tests/sync/ tests/contract/ -q --tb=short -p no:cacheprovider 2>&1 | tee /tmp/wp02-before.txt
```

Record: which tests fail, the exact error messages.

Key tests to watch:
- `tests/sync/test_events.py` (12 failures driven by version drift — should clear after T006)
- `tests/sync/test_daemon_intent_gate.py::test_no_unauthorized_daemon_call_sites`
- `tests/sync/test_lifecycle_readiness.py::*`
- `tests/sync/tracker/test_origin_integration.py::*`
- `tests/contract/test_handoff_fixtures.py::*`
- `tests/contract/test_packaging_no_vendored_events.py::*`
- `tests/contract/test_example_round_trip.py::*`

**Validation**:
- [ ] Targeted run complete; failures documented
- [ ] If zero failures: mark WP02 skipped, report to user, stop

---

## Subtask T006 — Confirm Package Version and Sync

**Purpose**: Ensure `spec_kitty_events` at the pinned version is installed.

**Steps**:
1. Check what's currently installed:
   ```bash
   .venv/bin/python -c "import spec_kitty_events; print(spec_kitty_events.__version__)"
   ```
   Or: `uv pip show spec-kitty-events 2>&1`

2. Check what `uv.lock` pins:
   ```bash
   grep -A2 "spec-kitty-events" uv.lock | head -10
   ```

3. If versions differ, sync:
   ```bash
   uv sync --frozen --all-extras
   ```
   Then re-check version.

4. If `uv sync --frozen` fails (lock out of date), do NOT unlock without approval. Report the error and stop.

**Validation**:
- [ ] Installed version matches `uv.lock` pin
- [ ] No `uv sync` errors

---

## Subtask T007 — Remove Vendored Events Tree

**Purpose**: Enforce the shared-package-boundary cutover — the vendored copy must not exist.

**Steps**:
1. Check for vendored tree:
   ```bash
   ls src/specify_cli/spec_kitty_events/ 2>/dev/null && echo "VENDORED_EXISTS" || echo "VENDORED_ABSENT"
   ```

2. If `VENDORED_EXISTS`:
   ```bash
   git rm -r src/specify_cli/spec_kitty_events/
   ```
   Stage the deletion. Do NOT `rm -rf` — use `git rm` so the removal is tracked.

3. Run the packaging contract test to confirm:
   ```bash
   pytest tests/contract/test_packaging_no_vendored_events.py -q --tb=short
   ```

4. If `VENDORED_ABSENT`: skip, mark T007 complete (no-op).

**Validation**:
- [ ] `src/specify_cli/spec_kitty_events/` does not exist in the working tree
- [ ] `test_packaging_no_vendored_events` passes

---

## Subtask T008 — Fix Daemon Allowlist

**Purpose**: `test_no_unauthorized_daemon_call_sites` enumerates call sites that may trigger daemon behavior and asserts they are all on an explicit allowlist. A new call site was added to the events library without updating the allowlist.

**Steps**:
1. Read the test to understand the sentinel pattern:
   ```bash
   cat tests/sync/test_daemon_intent_gate.py
   ```
   Find: what list/set constitutes the allowlist, and how call sites are discovered.

2. Run the test with verbose output to see which call site is not allowlisted:
   ```bash
   pytest tests/sync/test_daemon_intent_gate.py::test_no_unauthorized_daemon_call_sites -v --tb=long
   ```

3. Determine whether the fix belongs in the test (add to allowlist) or in the source (remove/guard the unauthorized call). The test message should indicate which.
   - If the call site is intentional and safe: add it to the allowlist in the test.
   - If the call site should not exist: fix the source instead.

4. Apply the fix, run the test again to confirm it passes.

**Files likely modified**:
- `tests/sync/test_daemon_intent_gate.py` (most likely — updating allowlist)
- Possibly a source file under `src/specify_cli/sync/` if the call site needs to be removed

**Validation**:
- [ ] `test_no_unauthorized_daemon_call_sites` passes
- [ ] No other daemon-gate tests regress

---

## Commit

After T005–T008:
```bash
git add -p  # review changes carefully
git commit -m "fix(#1301): restore events package version, remove vendored tree, fix daemon allowlist"
```

Then run a broader slice to check for regressions:
```bash
pytest tests/sync/test_daemon_intent_gate.py tests/contract/test_packaging_no_vendored_events.py -q
```

---

## Branch Strategy

- **Planning base branch**: `main`
- **Merge target**: `main`
- **Execution worktree**: Allocated by `lanes.json`.

Implementation command:
```bash
spec-kitty agent action implement WP02 --agent claude
```

---

## Definition of Done

- [ ] `spec_kitty_events` installed version matches `uv.lock` pin
- [ ] `src/specify_cli/spec_kitty_events/` does not exist
- [ ] `test_no_unauthorized_daemon_call_sites` passes
- [ ] `test_packaging_no_vendored_events` passes
- [ ] `tests/sync/test_events.py` passes (version drift cleared)
- [ ] **FR-007**: At least one regression test added or updated to prevent silent re-drift (e.g., a test asserting `spec_kitty_events.__version__` matches the uv.lock pin, or the existing `test_packaging_no_vendored_events` is confirmed sufficient — document which)
- [ ] Changes committed with issue-scoped message
- [ ] No previously passing tests newly broken

---

## Risks

- **uv.lock out of date**: If `uv sync --frozen` fails, stop and report — do not run `uv lock` without approval.
- **Vendored tree not present**: T007 is a no-op in this case; proceed.
- **Daemon allowlist ambiguity**: If unsure whether to update the test or the source, default to updating the test allowlist and note the decision in the commit message.

## Activity Log

- 2026-06-01T17:16:49Z – claude – shell_pid=25057 – Ready for review (cycle 1/3). Fixed test_adapter_emits_mission_run_and_lifecycle_sequence by aligning assertion with git-routed decision events architecture (#1546). Added FR-007 version drift regression guard. Tests pass (1951 passed, 0 failed), lint clean.
- 2026-06-01T17:17:14Z – claude:sonnet-4-6:reviewer:reviewer – shell_pid=40690 – Started review via action command
- 2026-06-01T17:21:29Z – claude:sonnet-4-6:reviewer:reviewer – shell_pid=40690 – Review passed: vendored tree absent, version pin guard added (FR-007), daemon allowlist passes, runtime emitter test aligned with git-routed decision events. 1951 tests pass.
