---
work_package_id: WP03
title: Isolate the strict-JSON test from the leaked sync toggle (#2809)
dependencies: []
requirement_refs:
- FR-001
- FR-005
- NFR-001
tracker_refs:
- '#2809'
- '#2782'
planning_base_branch: fix/loop-reliability-ci-red-burndown
merge_target_branch: fix/loop-reliability-ci-red-burndown
branch_strategy: Planning artifacts for this mission were generated on fix/loop-reliability-ci-red-burndown. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/loop-reliability-ci-red-burndown unless the human explicitly redirects the landing branch.
subtasks:
- T005
- T006
history: []
agent_profile: python-pedro
authoritative_surface: tests/sync/
create_intent: []
execution_mode: code_change
owned_files:
- tests/sync/conftest.py
role: implementer
tags: []
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "2473743"
shell_pid_created_at: "1784458502.5"
---

## ⚡ Do This First: Load Agent Profile
Load `python-pedro` via `/ad-hoc-profile-load`. Load the YAML.

## Objective
Isolate `test_strict_json_stdout::test_mission_create_json_strict_when_sync_skips_ingress` from a globally-leaked
`SPEC_KITTY_SYNC_*` toggle so it is deterministic in CI. **Red-first verify this actually greens the test before
assuming — it collides with #2782 (LM-7).**

**Authoritative grounding**: [`research.md` §2](../research.md), [`data-model.md` LM-4, LM-7, LM-8](../data-model.md).

## Context / grounding (verified on main)
- Root cause (#2809): the test is a subprocess test that `os.environ.copy()`s WITHOUT resetting
  `SPEC_KITTY_SYNC_*`; a leaked toggle disables sync in the child so the `direct ingress skipped` diagnostic never
  fires → red.
- The fixture **already exists**: `_isolate_pre_review_gate_sync_toggles` (autouse, #2794) at
  `tests/specify_cli/cli/commands/agent/conftest.py:51-70` (two `monkeypatch.delenv`). But it's agent-package-scoped.
- **`tests/sync/conftest.py` EXISTS** (~5 KB, does NOT hold the fixture). **APPEND to it, do not overwrite (LM-8).**
- **⚠ #2782 collision (LM-7):** the SAME test is tracked under #2782 with a DIVERGENT root cause (sync
  connection-refused, not the leaked toggle). It is already `@pytest.mark.regression`-quarantined
  (`test_strict_json_stdout.py:743`), routed off the blocking job.

## Subtasks
### T005 — Append the env-reset fixture
Copy the autouse `_isolate_pre_review_gate_sync_toggles` fixture (two `monkeypatch.delenv("SPEC_KITTY_SYNC_DISABLE"/
"SPEC_KITTY_SYNC_MINIMAL_IMPORT", raising=False)`) into the EXISTING `tests/sync/conftest.py` (append; keep the
current queue/emitter/auth fixtures intact).

### T006 — Red-first verify + reconcile #2782 + blast-radius check
- **BEFORE assuming the fix works (LM-7):** confirm `test_strict_json_stdout::test_mission_create_json_strict_when_sync_skips_ingress`
  actually flips red→green on current main with the fixture. If it does NOT (i.e. #2782's connection-refused cause
  is live), STOP and reconcile — do NOT blind-xfail to mute a possible product question; escalate + reference #2782.
- **Blast radius (LM-8):** the autouse `delenv` now applies to daemon/real-port tests (not HOME-isolated). Run the
  serial daemon/orphan-sweep suite: `PWHEADLESS=1 uv run --extra test pytest tests/sync/test_orphan_sweep.py -n0 -q`
  (+ a daemon test) — prove the fixture doesn't perturb harness ordering.
- On success, decide whether to strip the `@regression` quarantine marker (else a passing test stays catalogued as
  a #2782 regression). ruff + mypy clean.

## Definition of Done
The fixture is appended; `test_strict_json_stdout` is verified green on main via the fixture (or #2782 escalated if
its cause is live); serial daemon/orphan-sweep suite unperturbed; marker decision made; ruff + mypy clean.

## Reviewer guidance
Confirm the red-first verification was actually run (not assumed); confirm the conftest was APPENDED not
overwritten; confirm the serial `-n0` suite was exercised; confirm #2782 is referenced/reconciled.

## Activity Log

- 2026-07-19T10:44:58Z – claude:sonnet:python-pedro:implementer – shell_pid=2410645 – Assigned agent via action command
- 2026-07-19T10:52:58Z – claude:sonnet:python-pedro:implementer – shell_pid=2410645 – Ready for review: fixture appended to tests/sync/conftest.py (T005). Red-first (LM-7) confirmed the fixture does NOT green test_strict_json_stdout::test_mission_create_json_strict_when_sync_skips_ingress -- identical failure before/after (sync.server_auth_failure / Connection refused from final_sync phase, no SPEC_KITTY_SYNC_* refs in the file). Live cause is #2782, not #2809; @regression marker retained, not stripped. Blast-radius (LM-8): test_orphan_sweep.py -n0 (9 passed) and test_daemon.py -n0 (22 passed) unperturbed. ruff clean; mypy shows only 2 pre-existing untyped-def errors on lines untouched by this diff (verified via git stash diff).
- 2026-07-19T10:55:05Z – claude:opus:reviewer-renata:reviewer – shell_pid=2473743 – Started review via action command
