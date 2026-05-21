---
work_package_id: WP06
title: Focused-PR workflow documentation
dependencies: []
requirement_refs:
- FR-014
- FR-015
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T026
- T027
- T028
- T029
- T030
agent: ''
history:
- at: '2026-05-21T10:53:40Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: docs-drew
authoritative_surface: docs/how-to/
execution_mode: code_change
model: ''
owned_files:
- spec-kitty-mission-workflow.md
- docs/how-to/run-an-autonomous-mission.md
- docs/how-to/accept-and-merge.md
- docs/how-to/merge-feature.md
- docs/how-to/toc.yml
role: implementer
tags: []
---

# Work Package Prompt: WP06 - Focused-PR workflow documentation

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your agent profile:

```
/ad-hoc-profile-load docs-drew
```

## Objective

Document the focused-PR fallback for autonomous local runs that hit
`TARGET_BRANCH_NOT_SYNCHRONIZED`.

## Context

Issue #1258 reports that autonomous runs can leave local `main` far ahead of
`origin/main`. The runtime recommends a focused PR path, and PR #1251 succeeded
with a direct PR from `kitty/mission-<slug>` into `main`.

Implement this WP after runtime WPs where practical, even though metadata has no
dependency to avoid current lane-collapse serialization.

## Subtasks & Detailed Guidance

### T026 - Locate documentation targets

Search for existing mission workflow docs. If `spec-kitty-mission-workflow.md`
does not exist, create or update the nearest standing workflow document.

### T027 - Update official how-to docs

Create `docs/how-to/run-an-autonomous-mission.md` if no exact autonomous-run
page exists, and wire it into `docs/how-to/toc.yml` if required.

### T028 - Cite runtime remediation

Document `TARGET_BRANCH_NOT_SYNCHRONIZED` and the focused branch commands from
the issue.

### T029 - Add PR #1251 direct path

Document direct mission-branch PR and squash-merge guidance for orchestration
commit piles.

### T030 - Verify

Run applicable docs/toc tests if present:

```bash
uv run pytest tests/docs tests/architectural -k "docs or toc or link"
```

If no focused docs tests apply, record that in the WP activity log.

## Branch Strategy

Planning/base branch: `main`. Final merge target: `main`. Use the runtime
resolved lane workspace.

## Definition of Done

- Trigger error and commands are documented.
- Direct mission-branch PR path is documented.
- Reset, rebase, and force-push are explicitly excluded from remediation.
- Squash-merge guidance is included.

## Reviewer Guidance

Confirm docs match actual runtime command output and do not encourage unsafe git
history operations.

## Activity Log

- 2026-05-21T10:53:40Z -- system -- Prompt created.
