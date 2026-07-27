---
work_package_id: WP01
title: Retrospect schema reconciliation
dependencies: []
requirement_refs:
- FR-001
- FR-002
- FR-003
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
- T005
agent: ''
history:
- at: '2026-05-21T10:53:40Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: runtime-riley
authoritative_surface: src/specify_cli/retrospective/
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/retrospective/**
- src/specify_cli/cli/commands/agent_retrospect.py
- tests/cli/test_agent_retrospect_synthesize.py
- tests/cli/commands/test_retrospect.py
role: implementer
tags: []
---

# Work Package Prompt: WP01 - Retrospect schema reconciliation

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your agent profile:

```
/ad-hoc-profile-load runtime-riley
```

## Objective

Make `spec-kitty agent retrospect synthesize --mission <slug>` accept the same
`retrospective.yaml` shape that `spec-kitty retrospect create --mission <slug>`
writes.

## Context

Issue #1255 reports pydantic `extra_forbidden` errors for create-written fields
including `mission_id`, `mission_slug`, `mission_type`, `target_branch`,
`created_at`, `created_by`, `policy_source`, `findings_status`,
`evidence_refs`, `generator_version`, and `provenance_history`.

Read:

- `kitty-specs/autonomous-runtime-safety-followups-01KS52BD/spec.md`
- `kitty-specs/autonomous-runtime-safety-followups-01KS52BD/plan.md`
- `kitty-specs/autonomous-runtime-safety-followups-01KS52BD/research.md`
- `kitty-specs/autonomous-runtime-safety-followups-01KS52BD/contracts/runtime-safety-followups.md`

## Subtasks & Detailed Guidance

### T001 - Reproduce the schema mismatch

Add a failing regression fixture that resembles a freshly-created retrospective
record. Keep it minimal but include the fields named in #1255.

### T002 - Align reader and writer schema

Prefer a shared pydantic model if the change stays local. If not, configure the
synthesize reader to ignore informational extras while keeping behavior-driving
fields validated.

### T003 - Cover dry-run/default synthesize

Assert the default synthesize path accepts the create-shaped record and reports
the existing dry-run outcome.

### T004 - Cover `--apply`

Assert `--apply` accepts the same record and reaches the existing apply outcome.

### T005 - Verify

Run focused tests:

```bash
uv run pytest tests/cli/test_agent_retrospect_synthesize.py tests/cli/commands/test_retrospect.py
uv run mypy --strict src/specify_cli/retrospective src/specify_cli/cli/commands/agent_retrospect.py
```

## Branch Strategy

Planning/base branch: `main`. Final merge target: `main`. Actual execution
workspace is resolved later from `lanes.json`; trust the path printed by
`spec-kitty implement` or `spec-kitty next`.

## Definition of Done

- Create-shaped retrospective record is accepted by synthesize.
- Dry-run and `--apply` paths are covered.
- Existing malformed/missing/I/O error behavior is preserved.
- No files outside `owned_files` changed.

## Reviewer Guidance

Check that the fix does not silently allow malformed proposal/findings payloads.

## Activity Log

- 2026-05-21T10:53:40Z -- system -- Prompt created.
