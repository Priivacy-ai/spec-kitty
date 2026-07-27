---
work_package_id: WP01
title: Status Test Hang Stabilization
dependencies: []
requirement_refs:
- FR-001
- FR-002
- NFR-001
- NFR-002
- NFR-003
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-stable-320-p0-cli-stabilization-01KQSNGY
base_commit: 531e94731375f2f32f0f26d2d6c82e4892a2f031
created_at: '2026-05-04T16:14:25.781149+00:00'
subtasks:
- T001
- T002
- T003
- T004
- T005
shell_pid: "39330"
agent: "codex:gpt-5.5:python-pedro:implementer"
history:
- at: '2026-05-04T14:55:25Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
authoritative_surface: src/specify_cli/status/
execution_mode: code_change
lane: planned
owned_files:
- src/specify_cli/status/**
- src/specify_cli/sync/background.py
- src/specify_cli/cli/commands/agent/status.py
- tests/status/**
- tests/sync/test_background.py
- tests/specify_cli/status/**
tags: []
task_type: implement
---

# Work Package Prompt: WP01 - Status Test Hang Stabilization

## Objective

Fix or deterministically isolate #967: status bootstrap and emit tests can hang. The result must preserve status semantics while making local and CI validation bounded and diagnostic.

## Context

Read:

- `kitty-specs/stable-320-p0-cli-stabilization-01KQSNGY/spec.md`
- `kitty-specs/stable-320-p0-cli-stabilization-01KQSNGY/plan.md`
- `kitty-specs/stable-320-p0-cli-stabilization-01KQSNGY/contracts/status-test-boundedness.md`

The required acceptance command is:

```bash
uv run pytest tests/status -q --timeout=30
```

Default tests must be local and offline. Do not require hosted auth, tracker, SaaS sync, or network access.

## Branch Strategy

- Planning/base branch: `main`
- Final merge target: `main`
- Implementation command: `spec-kitty agent action implement WP01 --agent <name>`
- Execution worktrees are allocated later from `lanes.json`; do not create worktrees manually.

## Subtasks

### T001 - Reproduce or characterize the hang

Run the status suite with the required timeout. If it hangs or fails, capture the smallest failing test or fixture path. If it passes locally, inspect the #967 risk area by running bootstrap and emit-focused subsets.

Useful starting points:

```bash
uv run pytest tests/status -q --timeout=30
uv run pytest tests/status/test_bootstrap.py::TestBootstrapSeedsUninitialized::test_three_new_wps -q --timeout=30
uv run pytest tests/status/test_emit.py -q --timeout=30
uv run pytest tests/status/test_agent_status_emit_cli.py -q --timeout=30
rg -n "bootstrap|emit|adapter|sync|lock|event" tests/status src/specify_cli/status
```

### T002 - Isolate the nondeterministic boundary

Determine whether the hang comes from background sync fan-out, status adapters, event-loop lifecycle, file locks, materialization, or fixture teardown. Prefer monkeypatching or dependency injection at the adapter boundary when external fan-out is irrelevant to local persistence semantics.

Do not use arbitrary sleeps as the fix.

### T003 - Implement the smallest deterministic fix

Patch the narrowest module or fixture needed. If source code changes are required, keep the behavior equivalent for real status emission and materialization. If the true issue is test-only fan-out, isolate it in test fixtures with a clear reason.

### T004 - Add bounded regression tests and diagnostics

Add or update tests so future hangs fail under the 30-second timeout with enough path/context to diagnose. Include bootstrap and emit coverage if both paths are involved.

### T005 - Capture release evidence

Record the exact validation command and outcome in the final WP report. If there are pre-existing failures unrelated to this WP, follow the charter's pre-existing failure reporting rule before treating them as baseline.

## Definition of Done

- [ ] Root cause or narrowly justified isolation boundary is documented in the WP report.
- [ ] Status bootstrap/emit validation is bounded by the 30-second timeout.
- [ ] Tests preserve status semantic assertions.
- [ ] Default validation remains local and offline.
- [ ] #967 evidence is ready for WP05.

## Reviewer Guidance

Reject timeout-only or sleep-based fixes. Verify the changed tests would catch the reported hang class and that status JSON/stdout behavior was not weakened.

## Activity Log

- 2026-05-04T16:14:27Z – codex:gpt-5.5:python-pedro:implementer – shell_pid=39330 – Assigned agent via action command
