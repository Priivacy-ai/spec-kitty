---
work_package_id: WP01
title: Protection-preserved suite (ATDD-first)
dependencies: []
requirement_refs:
- FR-008
tracker_refs: []
planning_base_branch: fixups/code-engine-stabilization
merge_target_branch: fixups/code-engine-stabilization
branch_strategy: Planning artifacts for this mission were generated on fixups/code-engine-stabilization. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fixups/code-engine-stabilization unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-tooling-stability-guard-coherence-01KTRC04
base_commit: add42e46c5442ecd2d1c8c00015fab3fa5c727f1
created_at: '2026-06-10T14:49:31.204776+00:00'
subtasks:
- T001
- T002
- T003
phase: Phase 0 - Regression Guard
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "92560"
history:
- at: '2026-06-10T11:47:55Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: ''
authoritative_surface: tests/git/
execution_mode: code_change
model: ''
owned_files:
- tests/git/test_protection_preserved.py
- tests/git/protected_target_fixtures.py
role: ''
tags: []
task_type: implement
---

# Work Package Prompt: WP01 – Protection-preserved suite (ATDD-first)

## ⚡ Do This First: Load Agent Profile
Use `/ad-hoc-profile-load` to load the assigned profile (or pick the best implementer match for `tests/git/`). Behave per its guidance before reading on.

---

## Objectives & Success Criteria
This is the mission's **C-003 ratchet**, authored BEFORE any guard conversion (NFR-005, charter C-011).
- **Invariants that hold TODAY and must stay green through every later WP:** direct push to origin/main is blocked; a commit to a protected ref that is neither the resolved placement nor capability-authorized is refused.
- **Per-channel bypass repros** that demonstrate today's FIVE privilege channels and flip when WP03 deletes them: marked `xfail(strict=True, reason="channel deleted in WP03")`.
- **SC-6 fixture skeleton** for the protected-target e2e (consumed by WP05).
- **Done when:** suite runs deterministically; invariants pass; the 5 bypass repros xfail-for-the-right-reason; fixture importable.

## Context & Constraints
- Design (absolute): `kitty-specs/tooling-stability-guard-coherence-01KTRC04/{spec.md (FR-008, C-003, NFR-005), contracts/guard-and-findings-contracts.md (C-GUARD-2, C-GUARD-4), research.md, research/plan-review-debugger-debby.md}`.
- The five channels (`src/specify_cli/git/commit_helpers.py`): (1) `_is_protected_branch_exception` message-prefix list (~:360-366, :466); (2) `allow_protected_branch_in_test_mode` bool; (3) `allow_completed_op_on_protected_branch` bool; (4) the op-record file-content exception (`_is_completed_op_record_exception`); (5) env hatches. Read the module first.
- Tests use REAL git repos under `tmp_path` (no mocks — 01KTPKST's mutation-tested precedent); no `test-feature-*` leakage.

## Branch Strategy
- Planning base / merge target: `fixups/code-engine-stabilization`. Populated by finalize-tasks.

## Subtasks & Detailed Guidance

### T001 — Protection-preserved invariants (green today, stay green)
- **Steps**: build a tmp git repo WITH `.kittify/` (debby RISK-5: without it `_is_spec_kitty_project` is false and the guard is skipped entirely — verify this precondition in the fixture). Assert: (a) `safe_commit` to a protected branch with a plain message + no capability → refused (`ProtectedBranchCommitError` or current equivalent); (b) the public CLI path refuses likewise; (c) document (assert) that no test pushes to any remote — the direct-push protection is policy + CI, encode it as "no code path in commit_helpers performs a push".
- **Files**: `tests/git/test_protection_preserved.py`, `tests/git/protected_target_fixtures.py`.

### T002 — Per-channel bypass repros (xfail-strict until WP03)
- **Steps**: one test per channel, each demonstrating the CURRENT bypass succeeds (that's the bug) — written inverted: assert the bypass is REFUSED, marked `xfail(strict=True, reason="privilege channel; deleted in WP03")`. Channels: #1334 prefix-crafted message (use the live repro from the ticket: `release: …` etc. on a protected branch); `allow_protected_branch_in_test_mode=True`; `allow_completed_op_on_protected_branch=True`; an op-record file whose content matches the completed-op exception; the env hatch(es) found in the module. Include a module docstring convergence note: "flips in WP03".
- **Notes**: xfail-strict means WP03 MUST remove the markers when it deletes the channels — the designed convergence.

### T003 — SC-6 fixture skeleton
- **Steps**: a reusable fixture (`protected_target_fixtures.py`) that builds a fresh spec-kitty project (`.kittify/` + git) whose target branch is "protected" per the guard's detection; exported for WP05's e2e. Deterministic, tmp-scoped.

## Definition of Done
- Suite green (invariants) + 5 xfails counted; `ruff` + `mypy` clean on new files; deterministic across runs; no leakage.

## Risks & Mitigations
- *Vacuous tests* → each invariant must fail if the guard is disabled (spot-check by temporarily neutering locally — do not commit that).
- *Fixture skips guard* → assert the `.kittify/` precondition inside the fixture.

## Review Guidance
- Recommended: **reviewer-renata**. Verify tests hit the REAL guard path; xfails fail-for-the-right-reason; fixture asserts its own preconditions.

## Activity Log
- 2026-06-10T11:47:55Z – system – Prompt created.
- 2026-06-10T15:03:16Z – user – shell_pid=37277 – Protection-preserved suite (ATDD-first) complete. 4 invariants pass (plain-commit-to-protected refused via helper + public CLI; .kittify-precondition non-vacuity spot-check; no git push in commit_helpers); 5 per-channel bypass repros xfail-strict (channels 1-5: _is_protected_branch_exception prefix list / allow_protected_branch_in_test_mode / allow_completed_op_on_protected_branch / _is_completed_op_record_exception file-content / SPEC_KITTY_ALLOW_PROTECTED_BRANCH_COMMITS env hatch) — each flips in WP03 forcing marker removal. SC-6 ProtectedTargetRepo fixture exported for WP05. Gates: pytest 4 passed/5 xfailed deterministic; ruff + mypy clean. Commit 81e3fa7a4.
- 2026-06-10T15:16:59Z – claude:opus:reviewer-renata:reviewer – shell_pid=92560 – Started review via action command
- 2026-06-10T15:23:48Z – user – shell_pid=92560 – Review PASSED (reviewer-renata). Work IS committed on kitty/mission-...-01KTRC04-lane-a @ 81e3fa7a4 (3 files, +441, scope=tests/git/ only); verified ahead of both mission base and fixups target, NOT yet in fixups. --force used solely to bypass a move-task base-resolution false-negative ('no implementation commits') that diffs against the wrong base; the commit is present and verified. Evidence: 4 invariants pass; non-vacuity proven via --runxfail (all 5 channels fail for the RIGHT reason - live bypass genuinely succeeds: ch1/2/3 DID NOT RAISE ProtectedBranchRefused, ch4 _is_completed_op_record_exception returns True on a valid 26-char Crockford ULID op-id, ch5 env hatch suppresses ProtectedBranchCommitError). 5 xfail(strict), no XPASS, coupled to WP03 deletion. .kittify precondition self-asserted + guard-skipped-without-.kittify spot-check. SC-6 ProtectedTargetRepo importable for WP05, hermetic, no leakage. ruff+mypy clean; deterministic.
