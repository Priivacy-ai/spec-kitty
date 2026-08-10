---
work_package_id: WP02
title: Swallowed assertions + empty parametrize (S5779 x14, S8998 x2)
dependencies: []
requirement_refs:
- FR-005
- FR-006
- NFR-001
- NFR-002
planning_base_branch: fix/sonar-bug-blocker-remediation
merge_target_branch: fix/sonar-bug-blocker-remediation
branch_strategy: Planning artifacts for this mission were generated on fix/sonar-bug-blocker-remediation. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/sonar-bug-blocker-remediation unless the human explicitly redirects the landing branch.
created_at: '2026-08-10T15:05:00+00:00'
subtasks:
- T004
- T005
- T006
phase: Mechanical stream - assertion restructure
history:
- at: '2026-08-10T15:05:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/
create_intent: []
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- src/specify_cli/cli/commands/charter/lint.py
- src/specify_cli/cli/commands/init.py
- src/specify_cli/cli/commands/sync.py
- src/specify_cli/sync/events.py
- tests/cross_cutting/versioning/test_version_detection.py
- tests/cross_cutting/versioning/test_version_fallback.py
- tests/next/test_plan_mission_runtime.py
- tests/specify_cli/coordination/test_transaction.py
- tests/specify_cli/migration/test_strip_frontmatter.py
- tests/specify_cli/skills/test_command_renderer.py
- tests/status/test_status_read_worktree_resolution.py
- tests/architectural/test_compat_shims.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile in the frontmatter and behave per its
guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`

---

## Objective

Fix 14 **S5779** BUG issues ("Don't use assert inside a try-except that catches AssertionError") and
2 **S8998** BUG issues ("Add at least one case to the parametrize values").

- **S5779**: an `assert` sits inside a `try` whose `except` catches `AssertionError` (often a broad
  `except Exception`), so a failing assertion is silently swallowed — the check is inert.
- **S8998**: a `@pytest.mark.parametrize` has an **empty** value list, so the test never runs.

## S5779 rule (apply to every site)

The correct fix depends on *why* the assert is inside the try:

1. **Assertion is the real check, try/except is accidental over-broad catching** → move the `assert`
   **outside** the `try`, or narrow the `except` so it no longer catches `AssertionError`. The
   assertion must be able to propagate.
2. **The code deliberately translates a failure** (e.g. converts a condition into a domain error) →
   replace the `assert` with an explicit `if not cond: raise <SpecificError>(...)`. Do not rely on
   `assert` for control flow that is caught (asserts are also stripped under `python -O`).
3. **Src sites (higher care)** — preserve the intended error translation/recovery. Do not just delete
   the guard; keep the behavior, remove the swallowing anti-pattern.

## Subtasks

### T004 — src S5779 (4 sites)

- `src/specify_cli/cli/commands/charter/lint.py:127`
- `src/specify_cli/cli/commands/init.py:838`
- `src/specify_cli/cli/commands/sync.py:1129`
- `src/specify_cli/sync/events.py:78`

For each: determine whether the `assert` is a genuine invariant (convert to `if ... raise`) or a real
check that should propagate (move out / narrow except). Add or extend a focused test that proves the
failing path now surfaces (C-002 — new branch gets a test). Run the affected command/module tests.

### T005 — test S5779 (10 sites)

- `tests/cross_cutting/versioning/test_version_detection.py:150,151,349,350`
- `tests/cross_cutting/versioning/test_version_fallback.py:50`
- `tests/next/test_plan_mission_runtime.py:208`
- `tests/specify_cli/coordination/test_transaction.py:157`
- `tests/specify_cli/migration/test_strip_frontmatter.py:178`
- `tests/specify_cli/skills/test_command_renderer.py:573`
- `tests/status/test_status_read_worktree_resolution.py:193`

In tests, the usual cause is `try: assert ... except Exception: pytest.fail(...)` or a broad guard.
Restructure so the assertion runs outside the swallowing handler (or use `pytest.raises` for the
expected-exception cases). The test must still assert the same intent — and must fail if that intent
is violated (spot-check one).

### T006 — S8998 empty parametrize (2 sites)

- `tests/architectural/test_compat_shims.py:96`
- `tests/architectural/test_compat_shims.py:104`

Determine whether the parametrize is meant to iterate over a (currently-empty) computed set of
compat shims. If real cases exist, feed them in; if the set is legitimately empty now, either assert
the emptiness explicitly (a real test) or remove the vestigial parametrize so the test body runs. Do
not leave a silently-skipped test.

## Branch Strategy

Planning base and final merge target are both `fix/sonar-bug-blocker-remediation`. Consume the
workspace `spec-kitty implement` resolves from `lanes.json`; do not reconstruct paths.

## Definition of Done

- All 14 S5779 + 2 S8998 sites fixed; no `assert` is swallowed by an `except AssertionError` in the
  owned files; no empty parametrize remains.
- Src fixes preserve intended error translation; each new branch has a test (C-002).
- Scoped `pytest` over touched files green; `ruff`/`mypy` clean on changed src.
- Zero suppressions.
- `move-task --to for_review` pre-review gate passes.

## Risks / reviewer guidance

- **Src risk (T004)**: the reviewer must confirm the error-translation behavior is preserved — a fix
  that deletes the guard and changes the surfaced error type is a regression.
- `assert` under `-O` is stripped; converting real invariants to explicit `raise` is the durable fix.
