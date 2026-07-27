---
work_package_id: WP03
title: Real-port family registry + serial guard
dependencies: []
requirement_refs:
- FR-004
tracker_refs: []
planning_base_branch: feat/ci-test-topology-performance
merge_target_branch: feat/ci-test-topology-performance
branch_strategy: Planning artifacts for this mission were generated on feat/ci-test-topology-performance. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/ci-test-topology-performance unless the human explicitly redirects the landing branch.
subtasks:
- T009
- T010
- T011
phase: Phase 1 - Substrate
shell_pid_created_at: "1783884003.4"
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "1270406"
history:
- at: '2026-07-12T17:43:44Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: tests/_real_port_suites.py
create_intent:
- tests/_real_port_suites.py
execution_mode: code_change
model: ''
owned_files:
- tests/_real_port_suites.py
- tests/architectural/test_serial_port_preservation.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP03 – Real-port family registry + serial guard

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter (or any user-defined profile), and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this work package's `task_type` and `authoritative_surface`.

---

## ⚠️ IMPORTANT: Review Feedback

Check the `review_ref` field in the event log (`spec-kitty agent status`) before starting; address all feedback and log what changed in the Activity Log.

---

## Objectives & Success Criteria

FR-004 / C-002 (contracts §GC-3): keep the **whole** fixed-range
`find_free_port_in_range` daemon-test family serial `-n0` — not just the one
file (`test_orphan_sweep.py`) today's guard hardcodes. This is the safety net
WP06 (T016, hoisting orphan-sweep to its own job) and the FR-006 serial-job
sweep (T019) both depend on: parallelizing anything adjacent to this family
without this guard in place would silently scatter a fixed-range port binder
across `-n auto` workers (OS-global port binds are NOT protected by
per-worker HOME isolation).

Done means:

- A new committed registry `tests/_real_port_suites.py` (data-model E2) lists
  every test file that binds `find_free_port_in_range` (not just
  `test_orphan_sweep.py`).
- `tests/architectural/test_serial_port_preservation.py` is generalized to
  consume that registry — asserting the invariant for the **whole family**,
  globally across every job's pytest commands, exactly as it already does for
  the single file today.
- A fault-injection negative case proves the generalized guard actually bites
  when a **different** family member (not the one already covered) is placed
  under `-n auto`.

**Independent test** (per tasks.md): the guard rejects a family file placed
under `-n auto`.

## Context & Constraints

- Read FIRST: `data-model.md` §E2, `contracts/guard-contracts.md` §GC-3,
  `plan.md` §IC-03, `tasks.md` T009–T011.
- The fixed-range binder lives in `tests/sync/_daemon_harness.py`:
  `find_free_port_in_range(start, end)` (line 44). This suite's harness uses
  the range `[9400, 9425)` (`_daemon_harness.py:18`; `[9375, 9400)` is reserved
  for a later WP, do not fold it in).
- Verified fixed-range family members today (grep for `find_free_port_in_range`
  under `tests/sync/`): `test_orphan_sweep.py` (via its own local
  `_find_free_port_in_range` re-implementation, plus `_DaemonHarness`),
  `test_daemon_orphan_classification.py`, `test_daemon_cleanup_boundary.py`,
  `test_issue_1071_singleton_reconfirmation.py`. These are the seed for
  `FIXED_RANGE_SUITES` — do not add ephemeral port-0 binders (e.g. plain
  `DaemonHarness` calls that let the OS pick a port); those are deliberately
  parallel-safe and must stay excluded (data-model E2's explicit invariant).
- **Today's guard is narrower than the family.** `test_serial_port_
  preservation.py` hardcodes `_DAEMON_TEST = "tests/sync/test_orphan_sweep.py"`
  (line 41) and checks: no `-n auto`/`-n <N>` command collects it
  (`_is_parallel` + `_collects_daemon`), a serial pass still runs it
  (`serial_port_violations`, line 81), and no bare `--dist load` anywhere. All
  three checks generalize cleanly to "for every file in `FIXED_RANGE_SUITES`"
  — the existing `_covers_daemon_scope`/`_ignores_daemon`/
  `serial_port_violations` functions already operate over `commands: list[str]`
  globally (not per-job), so the generalization is "iterate the registry,"
  not "add a second scanning pass." Reuse `_gate_coverage.join_continuations`
  and `WORKFLOW_FILES` exactly as this file already does (lines 37, 111-125) —
  do not re-derive workflow parsing.
- No dependencies for this WP, but WP04 (workflow-dist lint) and WP06 (the
  orphan-sweep-to-own-job hoist, T016; the serial `integration-tests-*` sweep,
  T019) both consume the registry/guard this WP produces — land this WP
  **before** any of those touch the sync suite's job placement.

## Branch Strategy

- **Strategy**: Coord-topology mission (`meta.json` `topology: "coord"`).
  Planning artifacts live on primary; implementation happens in the lane
  worktree `spec-kitty implement WP03` creates/reuses.
- **Planning base branch**: `feat/ci-test-topology-performance`
- **Merge target branch**: `feat/ci-test-topology-performance`

## Subtasks & Detailed Guidance

### Subtask T009 – Add `tests/_real_port_suites.py`

- **Purpose**: One committed source of truth for the fixed-range family
  (data-model E2).
- **Steps**: New module, pure data (no pytest import — same discipline as
  `_arch_shard_map.py`): `FIXED_RANGE_SUITES: tuple[str, ...]` listing the 4
  seed relpaths verified in Context. Document, inline, how each was confirmed
  (grep for `find_free_port_in_range` under `tests/sync/`) so a future
  contributor knows how to re-verify/extend the list rather than guessing.
  Add a short note on the exclusion: ephemeral port-0 binders are deliberately
  absent and must stay absent.
- **Files**: `tests/_real_port_suites.py` (NEW). **Parallel?**: No —
  T010/T011 consume this.
- **Notes**: Keep this independent of `tests/_arch_shard_map.py`/
  `tests/_next_shard_map.py` — a different invariant family (serial isolation,
  not sharding), do not merge the two registries.

### Subtask T010 – Generalize `test_serial_port_preservation.py`

- **Purpose**: The guard protects the **whole** family, not one file.
- **Steps**: Replace the singular `_DAEMON_TEST` constant with iteration over
  `_real_port_suites.FIXED_RANGE_SUITES`. Generalize `_covers_daemon_scope`/
  `_ignores_daemon` (lines 62-73) to check membership against the whole
  registry (a command's positional scope covers *any* family member, or
  `--ignore`s it specifically or an ancestor directory). Keep
  `serial_port_violations` (line 81) global-across-all-jobs as it is today —
  do not narrow it to per-job. Update the module docstring's family
  description and keep `test_at_least_one_job_runs_the_daemon_test` (line 128)
  as "at least one job runs *some* family member," not just the orphan-sweep
  file specifically.
- **Files**: `tests/architectural/test_serial_port_preservation.py`.
  **Parallel?**: No — depends on T009's registry.
- **Notes**: The 3 existing fault-injection tests (parallel pool, dropped
  serial pass, bare `--dist load`; lines 151-179) must keep passing unchanged
  — they exercise the mechanism generically already via synthetic `commands`
  lists, not the real workflow, so generalizing the registry should not
  require editing them.

### Subtask T011 – Fault-injection negative: a family file under `-n auto`

- **Purpose**: Prove the generalized guard actually bites for a member
  **other than** `test_orphan_sweep.py` (today's fault-injection cases only
  ever reference the one hardcoded file — this closes that gap).
- **Steps**: Add a new fault-injection test mirroring
  `test_relation_bites_on_daemon_in_parallel_pool` (line 151) but using e.g.
  `tests/sync/test_daemon_orphan_classification.py` in a synthetic `-n auto
  --dist loadfile` command, asserting `serial_port_violations(...)` flags it.
  Also add the inverse micro-check: a command referencing only an ephemeral
  port-0 test (not in `FIXED_RANGE_SUITES`) under `-n auto` must NOT be
  flagged — proving the guard doesn't over-fire on parallel-safe tests.
- **Files**: `tests/architectural/test_serial_port_preservation.py`.
  **Parallel?**: `[P]` — independent of T010's core edit once the registry
  iteration lands (can be authored red-first against the pre-generalization
  single-file check).
- **Notes**: This is the WP's stated independent test — make it demonstrably
  fail against a version of the guard that still only knows about
  `test_orphan_sweep.py`, then pass after T010.

## Test Strategy

```bash
PWHEADLESS=1 uv run pytest tests/architectural/test_serial_port_preservation.py -q

# Sanity: registry lists exactly the verified family, nothing more/less
uv run python -c "
from tests._real_port_suites import FIXED_RANGE_SUITES
print(sorted(FIXED_RANGE_SUITES))
"
grep -rl "find_free_port_in_range" tests/sync/*.py

# Fault-injection proof (T011) — run in isolation to confirm it fails against
# the OLD single-file guard, then passes after generalizing:
uv run pytest tests/architectural/test_serial_port_preservation.py -k "bites" -q

ruff check tests/_real_port_suites.py tests/architectural/test_serial_port_preservation.py
uv run mypy tests/_real_port_suites.py
```

## Risks & Mitigations

- **Registry drifts from reality** (a new fixed-range test added later isn't
  registered). Mitigation: the inline grep-based verification note in T009 is
  the reviewer's re-check recipe; consider whether a companion completeness
  scan belongs to a later WP (out of scope here — flag if seen).
- **Over-inclusion**: accidentally registering an ephemeral port-0 binder would
  force it needlessly serial, undermining FR-006's later parallelization.
  Mitigation: T009's exclusion note + T011's inverse micro-check.
- **Guard narrows silently during generalization** (e.g. only checks the first
  registry entry). Mitigation: T011's fault-injection on a *non-first* member
  is the concrete proof this didn't happen.
- **This WP not landing before WP06 touches orphan-sweep placement** would let
  T016's job-hoist go unguarded. Sequence WP03 ahead of WP06 explicitly.

## Review Guidance

- Confirm `FIXED_RANGE_SUITES` matches a fresh `grep -rl
  find_free_port_in_range tests/sync/*.py` — no stale/missing entries.
- Confirm the fault-injection case in T011 targets a family member other than
  `test_orphan_sweep.py` and genuinely fails pre-generalization.
- Confirm the inverse (ephemeral port-0, non-family) micro-check exists and
  passes — the guard must not over-fire.
- Confirm the 3 pre-existing fault-injection tests still pass unmodified.

## Activity Log

> Append at the END, chronological. Format: `- YYYY-MM-DDTHH:MM:SSZ – agent_id – <action>`

- 2026-07-12T17:43:44Z – system – Prompt created.
- 2026-07-12T18:56:31Z – claude:sonnet:python-pedro:implementer – shell_pid=1150293 – Assigned agent via action command
- 2026-07-12T19:11:29Z – claude:sonnet:python-pedro:implementer – shell_pid=1150293 – Ready: added tests/_real_port_suites.py (FIXED_RANGE_SUITES, 4 members verified via grep -rl find_free_port_in_range tests/sync/*.py); generalized test_serial_port_preservation.py to iterate the registry (T010); added T011 fault-injection (non-orphan-sweep member bites) + inverse ephemeral micro-check + anti-vacuous canary (>0 jobs inspected). ruff/mypy clean on both files. 6/7 tests green; 1 KNOWN RED (test_no_daemon_run_in_parallel_and_serial_pass_preserved) — pre-existing ci-quality.yml gap where 3 of 4 family members rely on a marker filter, not --ignore, in the fast-tests-sync parallel job; filed https://github.com/Priivacy-ai/spec-kitty/issues/2590; fix is WP06's (owns ci-quality.yml, sequenced after this WP). Commit 720d38cc7.
- 2026-07-12T19:12:47Z – claude:opus:reviewer-renata:reviewer – shell_pid=1235344 – Started review via action command
- 2026-07-12T19:16:39Z – user – Moved to planned
- 2026-07-12T19:17:23Z – claude:sonnet:python-pedro:implementer – shell_pid=1262385 – Started implementation via action command
- 2026-07-12T19:19:44Z – claude:sonnet:python-pedro:implementer – shell_pid=1262385 – Cycle 1: converted the pending-WP06 guard to strict xfail (#2590); suite now 6 passed / 1 xfailed / 0 failed; ruff 0. Other 6 guards stay live.
- 2026-07-12T19:20:05Z – claude:opus:reviewer-renata:reviewer – shell_pid=1270406 – Started review via action command
- 2026-07-12T19:21:53Z – user – shell_pid=1270406 – Review passed (cycle 1): pending-WP06 guard now strict-xfail (#2590), suite 6 passed/1 xfailed/0 failed; other guards live
