---
work_package_id: WP05
title: Real installed-CLI two-worktree concurrency ATDD and adversarial coverage
dependencies:
- WP02
- WP03
- WP04
requirement_refs:
- FR-008
- FR-009
- FR-012
- FR-013
- NFR-001
- NFR-002
- C-004
- C-002
planning_base_branch: fix/worktree-owned-root-3328-v2
merge_target_branch: fix/worktree-owned-root-3328-v2
branch_strategy: Planning artifacts for this mission were generated on fix/worktree-owned-root-3328-v2. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/worktree-owned-root-3328-v2 unless the human explicitly redirects the landing branch.
subtasks:
- T016
- T017
- T018
- T019
history:
- at: '2026-08-11T13:37:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks-packages
agent_profile: ''
authoritative_surface: tests/e2e/test_worktree_owned_root_concurrency.py
create_intent:
- tests/e2e/test_worktree_owned_root_concurrency.py
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/cli/commands/next_cmd.py
- src/mission_runtime/resolution.py
- src/runtime/next/decision.py
- src/runtime/next/runtime_bridge.py
- tests/e2e/test_worktree_owned_root_concurrency.py
- tests/architectural/surface_resolution_audit/inventory.md
- tests/architectural/test_single_mission_surface_resolver.py
role: implementer
tags: []
tracker_refs: []
---

# Work Package Prompt: WP05 - Real installed-CLI two-worktree concurrency ATDD and adversarial coverage

## Objective

Deliver the acceptance-authority proof this whole mission exists for: a test that builds an IMMUTABLE wheel from the reviewed commit (never editable), installs it into a throwaway virtualenv, creates two REAL linked worktrees via `git worktree add` at generic (non-`.worktrees`) paths, forces temporal overlap of two subprocess CLI invocations, and asserts distinct mission IDs/slugs/refs/runtime state with zero cross-write and clean trees afterward — plus the negative/adversarial cases (nested, foreign, broken-pointer) from spec.md.

## Context

This WP is written FIRST as a RED test per the charter's ATDD-first discipline (C-011) — before this WP is marked done, confirm it was authored and run RED (refused, matching pre-WP02/WP03 behavior) at some point during the mission, even though by the time this WP is reviewed WP02-WP04 will have made it pass GREEN. Record the RED-then-GREEN transition evidence in this WP's Activity Log (this is the "test-remediation/red-first discipline" the charter's Quality & Tech-Debt Standing Orders require).

Read `quickstart.md` in full — it is the manual walkthrough this automated test codifies. Read `research.md`'s D-8 table for the exact downstream consumer (SaaS #836/#864) waiting on this specific proof — its own PR body explicitly states "the fake installed-CLI concurrency test proves environment/state routing only," which is the failure mode this WP must NOT repeat (C-004: no mocked-CLI evidence accepted).

**Before writing a new wheel-build fixture, search the repo for an existing one** (e.g., under `tests/e2e/`, `tests/packaging/`, or CI scripts referenced in `.github/workflows/`) — research did not find one during Phase 0, but re-confirm at implementation time since `main` may have advanced (research risk #4 noted concurrent-session activity moving `origin/main` during this mission's planning).

## Branch Strategy

- **Strategy**: {{branch_strategy}}
- **Planning base branch**: {{planning_base_branch}}
- **Merge target branch**: {{merge_target_branch}}

## Subtasks & Detailed Guidance

### Subtask T016 - Immutable wheel build/install fixture

- **Purpose**: Satisfy C-004 — the test must run against a real installed artifact, never `pip install -e .`.
- **Steps**:
  1. Add a session- or module-scoped pytest fixture that runs `python -m build --wheel` (or the repo's existing build tooling if `build` isn't already a dev dependency — check `pyproject.toml` first) from the commit under test, records the wheel's SHA-256 and the source commit SHA, then `pip install`s it into a fresh temporary virtualenv.
  2. Skip (not fail) this test suite gracefully with a clear message if the build toolchain is unavailable in the current CI/dev environment (e.g., no network for wheel deps) — but NEVER silently substitute an editable install as a fallback (that would violate C-004 by definition).
  3. Record the provenance fields (commit SHA, wheel SHA-256, build options) as test output/log lines so a reviewer can audit them per spec.md SC-005.
- **Files**: `tests/e2e/test_worktree_owned_root_concurrency.py` (new, ~80 lines for this subtask, or a shared fixture module if one is warranted — decide during implementation)

### Subtask T017 - Two real linked worktrees, forced-overlap concurrency

- **Purpose**: FR-012's core assertion.
- **Steps**:
  1. Using the fixture from T016, create two `git worktree add` checkouts at generic paths (e.g., `tmp_path / "agent-a"`, `tmp_path / "agent-b"`, deliberately NOT under a `.worktrees/` segment — this is load-bearing for C-006 coverage).
  2. Launch two subprocesses (the installed CLI binary, not `python -m specify_cli`) running `agent mission create ... --owned-checkout <worktree>` concurrently, synchronized to overlap via a shared start barrier (e.g., both wait on a `threading.Barrier` released by the test, or a short coordinated `sleep`).
  3. Assert: distinct `mission_id`/`mission_slug` in each subprocess's `--json` output; distinct coordination/lane ref names (`git for-each-ref`); no file from worktree A appears in worktree B or the primary checkout and vice versa (`git status --short` clean in all three after both processes exit); no orphaned lock file under the shared `git rev-parse --git-common-dir`-relative `spec-kitty-locks/` directory.
  4. Repeat the overlap test for `next --owned-checkout ... --result success` advancing both missions concurrently.
- **Files**: same file (+~150 lines)

### Subtask T018 - Determinism proof (NFR-002)

- **Purpose**: Prove the concurrency proof isn't a flaky one-off.
- **Steps**:
  1. Parametrize or loop T017's core scenario to run 20 consecutive times (can be a separate, explicitly slow-marked test invoked in CI/nightly rather than every default run, if the repo has a convention for slow-test marking — check `pyproject.toml`'s `pytest` markers config first) and assert all 20 pass with the same invariants.
  2. If flakiness is found, do NOT retry-to-green (per the repo's flakiness policy in `docs/development/testing/testing-flakiness.md`) — fix the root cause (likely a synchronization/timing bug in the barrier setup or a real race in the implementation) and record the fix.
- **Files**: same file (+~40 lines)

### Subtask T019 - Adversarial/negative coverage (FR-013)

- **Purpose**: Prove the refusal paths, not just the happy path.
- **Steps**:
  1. Nested worktree: `git worktree add` a worktree INSIDE another worktree's directory; assert `mission create --owned-checkout <nested> --json` returns `error_code == "OWNERSHIP_NESTED"`.
  2. Foreign repository: a wholly separate `git init` temp repo; assert `error_code == "OWNERSHIP_FOREIGN"`.
  3. Broken gitdir pointer: create a valid worktree, then corrupt its `.git` file's `gitdir:` target; assert `error_code == "OWNERSHIP_BROKEN_POINTER"`.
  4. No-opt-in from a generic linked worktree: assert IDENTICAL behavior to the pre-mission baseline (capture a baseline snapshot from `main` before WP02/WP03 land, compare byte-for-byte modulo timestamps/run-IDs) — this is the hardest-to-regress case and the one most worth automating precisely.
  5. First record a real installed-CLI RED where a mission created only in linked checkout A returns `MISSION_NOT_FOUND` from `next --owned-checkout A` when invoked from both primary and A. Then minimally thread the already-validated claim's effective root through `next_cmd.py` → `runtime.next.decision` → `runtime.next.runtime_bridge` → `mission_runtime.resolution`. The opted-in path must use that explicit root for mission content, primary-partition metadata, and runtime state; it must never call `get_main_repo_root` as a fallback. The no-flag path is unchanged.
  6. Re-run the real installed-wheel probe GREEN from both CWDs, then force overlap across two real linked worktrees and assert primary/A/B mission content, runtime state, and refs never cross-write.
  7. Repair the stale WP02 `effective_root` architectural descriptors in `tests/architectural/surface_resolution_audit/inventory.md` and `tests/architectural/test_single_mission_surface_resolver.py`; run the exact audit RED before updating them, then GREEN. These are the only descriptor files admitted to this amendment.
- **Requirement mapping**: FR-008, FR-009, C-002, FR-013.
- **Files**: `src/specify_cli/cli/commands/next_cmd.py`, `src/mission_runtime/resolution.py`, `src/runtime/next/decision.py`, `src/runtime/next/runtime_bridge.py`, `tests/e2e/test_worktree_owned_root_concurrency.py`, `tests/architectural/surface_resolution_audit/inventory.md`, `tests/architectural/test_single_mission_surface_resolver.py`.

## Test Strategy

- `.venv/bin/pytest tests/e2e/test_worktree_owned_root_concurrency.py -q` (mark slow/e2e per repo convention; confirm it runs in the appropriate CI job, not skipped by default fast-test filters, since it IS the mission's acceptance authority).

## Risks & Mitigations

- **Risk**: Wheel build inflates CI duration significantly. **Mitigation**: cache the built wheel across the 20-iteration determinism loop (build once, install-and-run 20 times) — only the CLI invocations need to repeat, not the build.
- **Risk**: `threading.Barrier`-based overlap forcing is itself flaky across platforms. **Mitigation**: follow the repo's existing timing-synchronization patterns if any exist in `tests/sync/test_orphan_sweep.py` or similar real-port/daemon tests (CLAUDE.md notes these run serially and have established patterns for this class of test).

## Definition of Done

- [ ] Test builds and installs an immutable wheel, never editable — provenance recorded and asserted.
- [ ] Two real linked worktrees, forced overlap, distinct identifiers, zero cross-write, clean trees — all asserted.
- [ ] 20 consecutive deterministic passes recorded.
- [ ] All four adversarial cases produce the correct distinguishable `error_code`.
- [ ] A mission created only in a linked checkout is queried and advanced by the installed CLI from primary and linked CWD with the same explicit owned root; primary/A/B content and runtime state remain isolated, with no ambient primary fallback.
- [ ] The two stale architectural descriptors are re-pinned and the surface-resolution audit is green.
- [ ] RED-then-GREEN transition evidence recorded in the Activity Log.

## Reviewer Guidance

- This is the mission's single most important WP — do not approve on "the test exists and passes once." Demand the 20-run determinism evidence and the immutable-artifact provenance record explicitly.
- Confirm the test genuinely shells out to the INSTALLED CLI binary (e.g., via `shutil.which("spec-kitty")` pointed at the throwaway venv), not an in-process function call — that distinction is the entire point of FR-012 given #864's documented "fake installed-CLI" shortfall.

**Implementation command**: `spec-kitty agent action implement WP05 --agent <name>`

## Activity Log

- 2026-08-11T13:37:00Z - system - Prompt created.
- 2026-08-11T18:40:02Z – orchestrator – shell_pid=28365 – ATDD acceptance requirement from WP03 Prime Op 01KZS0QVDFRH5S3DASD31YM4E0: real installed CLI must create a mission in a linked checkout and advance/query it from the same explicit owned root; mission content plus feature-runs/merge runtime state must remain same-root and primary must receive neither content nor runtime fallback. Run concurrently in two linked worktrees. Any content-primary divergence is blocking and must be repaired before acceptance.
- 2026-08-11T22:24:42Z – codex – shell_pid=28365 – RED: immutable pre-fix wheel e6c8e021a/a5aa5489 returned MISSION_NOT_FOUND and descriptor audit 15P/2F. GREEN: commit d51dfa893; authoritative immutable snapshot 3f300c373, non-editable wheel SHA256 6e656236457f0fc3d1f04973f4ed8dd12107e11cf7683b532cba1ecf6b9e3cfb; 24/24 in 762.05s (20 real concurrent primary/A/B iterations, adversarial envelope, bounded fail-closed retry probes), JUnit SHA256 1d21fab22d91ef6e2151cd9114748aa5d08b66773fd6764059bed2f0bc255f32. Broad 383/383; architectural 104/104; ruff/mypy/diff-check green.
- 2026-08-11T23:35:40Z – codex – shell_pid=0 – Review cycle 2 RED→GREEN: rc128 permission-denied lock error reproduced 20 retries (1F, JUnit SHA256 2e4991e2), then positive-contention-only predicate produced 4P retry suite (SHA256 a285a490), broad 383P (SHA256 b2f158ab), and fresh immutable snapshot cfb5cecbf / non-editable wheel SHA256 94965f9c016e8e86544d1e68eb7d4ee6c63263bdffcf1f6dd56d966408497f37 with 25P/781.91s (JUnit SHA256 4d4228a5). Final commit ac7c29dc.
- 2026-08-12T00:02:07Z – reviewer-renata – shell_pid=0 – Review cycle 2 Prime Kimi APPROVE (Op 01KZSJYXVRX26ASTRDVJZJSTQN): strict positive-contention retry contract independently verified; installed-wheel concurrency/refusal reproduced; raw SHA256 0329c4c1. CI-selection MEDIUM mapped to WP06/core #3343.
