---
work_package_id: WP02
title: Refresh-Lock Hermeticity
dependencies: []
requirement_refs:
- C-004
- FR-004
- FR-005
- FR-011
- NFR-001
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-auth-local-trust-and-multi-process-hardening-01KQW587
base_commit: e087f100e629f815be9179f984af9ff8236c53ae
created_at: '2026-05-05T13:57:52.734876+00:00'
subtasks:
- T006
- T007
- T008
- T009
- T010
phase: Phase 1 - Test Isolation
assignee: ''
agent: "codex:gpt-5:python-pedro:reviewer"
shell_pid: "59207"
history:
- at: '2026-05-05T13:41:33Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: tests/auth/concurrency/
execution_mode: code_change
model: ''
owned_files:
- tests/auth/concurrency/test_machine_refresh_lock.py
- tests/auth/concurrency/conftest.py
- tests/auth/test_token_manager.py
- tests/auth/test_refresh_flow.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP02 - Refresh-Lock Hermeticity

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `codex`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this work package's `task_type` and `authoritative_surface`.

---

## Objective

Fix #977 by making the machine refresh-lock concurrency tests hermetic even when a developer shell sets `SPEC_KITTY_SAAS_URL=https://spec-kitty-dev.fly.dev`. The test must not perform real hosted `/api/v1/me` membership rehydrate calls unless it is explicitly a hosted dev smoke test.

Implementation command: `spec-kitty agent action implement WP02 --agent <name>`

## Context & Constraints

Read:

- `/Users/robert/spec-kitty-dev/spec-kitty-20260505-085847-6BpmsS/spec-kitty/kitty-specs/auth-local-trust-and-multi-process-hardening-01KQW587/contracts/refresh-lock-hermeticity.md`
- `/Users/robert/spec-kitty-dev/spec-kitty-20260505-085847-6BpmsS/spec-kitty/kitty-specs/auth-local-trust-and-multi-process-hardening-01KQW587/research.md`

The known diagnosis: `TokenManager.refresh_if_needed()` applies a post-refresh membership hook. The fake sessions in `tests/auth/concurrency/test_machine_refresh_lock.py` lack `is_private_teamspace=True`, so the test can accidentally hit hosted `/api/v1/me` when hosted URL configuration leaks from the shell.

## Branch Strategy

- **Planning/base branch at prompt creation**: `main`
- **Final merge target for completed work**: `main`
- **Actual execution workspace is resolved later**: `/spec-kitty.implement` decides the lane workspace path and records the lane branch in `base_branch`.

## Subtasks & Detailed Guidance

### Subtask T006 - Reproduce the hosted-URL-set isolation boundary

- **Purpose**: Prove the regression without depending on live SaaS.
- **Steps**:
  1. Inspect `tests/auth/concurrency/test_machine_refresh_lock.py`.
  2. Run or reason through the test with `SPEC_KITTY_SAAS_URL` set.
  3. Add a local fake/spy that would fail if the test attempted real `/api/v1/me`.
- **Files**: `test_machine_refresh_lock.py`, possibly `conftest.py`.
- **Parallel?**: Can run independently from WP01 and WP03.
- **Notes**: Do not require actual network access for the reproduction.

### Subtask T007 - Make refresh-lock fixtures hermetic

- **Purpose**: Keep membership rehydrate out of a test that is about refresh locking.
- **Steps**:
  1. Choose one of the allowed fix shapes: fake refreshed sessions include a Private Teamspace, or monkeypatch the post-refresh membership hook in the concurrency fixture.
  2. Prefer a fixture shape that clearly documents membership rehydrate is out of scope.
  3. Keep production `TokenManager` behavior unchanged.
- **Files**: `test_machine_refresh_lock.py`, `conftest.py`.
- **Parallel?**: No; follows T006.
- **Notes**: Avoid broad environment mutation as the only defense.

### Subtask T008 - Add a no-hosted-/me regression guard

- **Purpose**: Prevent the bug from returning.
- **Steps**:
  1. Patch the membership HTTP seam or transport seam so an attempted hosted `/api/v1/me` call fails the test.
  2. Set `SPEC_KITTY_SAAS_URL` inside the test or command fixture.
  3. Assert the refresh-lock assertions still validate single-flight behavior.
- **Files**: `test_machine_refresh_lock.py`.
- **Parallel?**: No; depends on T007.
- **Notes**: The guard should be local and deterministic.

### Subtask T009 - Preserve production membership rehydrate coverage

- **Purpose**: Ensure hermetic concurrency tests do not remove real coverage elsewhere.
- **Steps**:
  1. Inspect `tests/auth/test_token_manager.py` and `tests/auth/test_refresh_flow.py`.
  2. Confirm there is still targeted coverage for post-refresh membership rehydrate when a refreshed session lacks a Private Teamspace.
  3. Add or adjust focused assertions only if the existing tests do not cover this production path.
- **Files**: `tests/auth/test_token_manager.py`, `tests/auth/test_refresh_flow.py`.
- **Parallel?**: Can be done after T007.
- **Notes**: Keep hosted calls mocked.

### Subtask T010 - Run hosted-URL-set and hosted-URL-unset verification

- **Purpose**: Provide evidence for #977.
- **Steps**:
  1. Run the focused test with hosted URL set.
  2. Run the same test with hosted URL unset.
  3. Run targeted token-manager refresh tests if they were touched.
- **Files**: no new files beyond owned tests.
- **Parallel?**: No; final verification.

## Test Strategy

```bash
SPEC_KITTY_SAAS_URL=https://spec-kitty-dev.fly.dev \
  uv run pytest tests/auth/concurrency/test_machine_refresh_lock.py -q --timeout=60

env -u SPEC_KITTY_SAAS_URL \
  uv run pytest tests/auth/concurrency/test_machine_refresh_lock.py -q --timeout=60

uv run pytest tests/auth/test_token_manager.py tests/auth/test_refresh_flow.py
```

## Definition of Done

- Hosted-URL-set refresh-lock tests pass in under 60 seconds.
- Hosted-URL-unset refresh-lock tests pass in under 60 seconds.
- The test fails if it attempts real hosted `/api/v1/me`.
- Production membership rehydrate coverage remains intact.

## Risks & Mitigations

- **Risk**: Accidentally disabling production membership rehydrate. **Mitigation**: do not modify production code in this WP.
- **Risk**: Environment cleanup hides the bug. **Mitigation**: assert no hosted membership call occurs.

## Review Guidance

Reviewers should focus on hermeticity and preservation of refresh-lock semantics. This WP should not redesign token refresh.

## Integration Verification

Before moving this WP to `for_review`, verify:

- [ ] The hosted-URL-set command passes within 60 seconds.
- [ ] The hosted-URL-unset command passes within 60 seconds.
- [ ] A test spy or fake fails if the concurrency suite attempts hosted `/api/v1/me`.
- [ ] The fake refreshed sessions or monkeypatch clearly document why membership rehydrate is out of scope.
- [ ] Existing targeted membership rehydrate tests still exercise the production path.
- [ ] No production auth code was changed by this WP.

## Out Of Scope

- Do not change `TokenManager.refresh_if_needed()` production behavior here.
- Do not remove or weaken `_apply_post_refresh_membership_hook()`.
- Do not mark the default refresh-lock suite as hosted smoke.
- Do not depend on `https://spec-kitty-dev.fly.dev` availability.

## Implementation Handoff Notes

The expected implementation is small. If you discover that changing production code seems necessary, pause and record why the fixture-only approaches from the contract are insufficient. The likely fix is to make the fake refreshed sessions include a Private Teamspace or to monkeypatch the post-refresh membership hook in the concurrency fixture.

## Suggested Fixture Shape

A strong fix usually has these traits:

1. The expired input sessions still force the refresh path.
2. The fake refresh result includes a `Team` with `is_private_teamspace=True`, making the membership hook a no-op for this test.
3. A transport or membership-fetch spy raises immediately if `/api/v1/me` is attempted.
4. The assertions continue to prove only one worker performs the refresh and peers observe the resulting session.
5. The test name or inline comment states that membership rehydrate is covered elsewhere.

If you choose monkeypatching instead, patch the narrow `_apply_post_refresh_membership_hook()` seam in the test fixture and assert it was not part of this test's contract. Do not patch broader HTTP transport globally unless the patch is the no-network guard.

## Evidence To Leave For WP05

Record these facts in the Activity Log or implementation notes:

- Which hermeticity strategy was used.
- The exact hosted-URL-set command result.
- The exact hosted-URL-unset command result.
- The production membership rehydrate test that still covers the real hook.

## Activity Log

> **CRITICAL**: Activity log entries MUST be in chronological order (oldest first, newest last).

- 2026-05-05T13:41:33Z – system – Prompt created.
- 2026-05-05T13:57:54Z – codex:gpt-5:python-pedro:implementer – shell_pid=40760 – Assigned agent via action command
- 2026-05-05T14:02:48Z – codex:gpt-5:python-pedro:implementer – shell_pid=40760 – Ready for review
- 2026-05-05T14:03:06Z – codex:gpt-5:python-pedro:reviewer – shell_pid=59207 – Started review via action command
- 2026-05-05T14:05:03Z – codex:gpt-5:python-pedro:reviewer – shell_pid=59207 – Review passed: hermetic refresh-lock tests guard hosted /api/v1/me and preserve membership rehydrate coverage
