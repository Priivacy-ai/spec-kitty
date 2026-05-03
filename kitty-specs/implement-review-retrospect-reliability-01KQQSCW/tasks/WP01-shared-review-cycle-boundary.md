---
work_package_id: WP01
title: Shared Review-Cycle Boundary
dependencies: []
requirement_refs:
- FR-003
- FR-004
- FR-006
- FR-007
- NFR-001
- NFR-003
- NFR-004
- C-003
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-implement-review-retrospect-reliability-01KQQSCW
base_commit: 2ba9bbb6f5efbb32adf787a534d3a8f01f13fd55
created_at: '2026-05-03T21:14:04.180618+00:00'
subtasks:
- T001
- T002
- T003
- T004
- T005
shell_pid: "3047"
agent: "codex:gpt-5:default:reviewer"
history:
- at: '2026-05-03T20:58:32Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
authoritative_surface: src/specify_cli/review/
execution_mode: code_change
owned_files:
- src/specify_cli/review/cycle.py
- src/specify_cli/review/artifacts.py
- tests/review/test_cycle.py
priority: P0
tags: []
---

# Work Package Prompt: WP01 - Shared Review-Cycle Boundary

## Objective

Create the narrow shared invariant boundary for rejected review cycles. The boundary owns artifact creation, required frontmatter validation, canonical `review-cycle://...` pointer generation/resolution, legacy `feedback://` normalization, and rejected `ReviewResult` derivation.

## Branch Strategy

- Planning/base branch at prompt creation: `main`
- Final merge target for completed work: `main`
- Execution worktrees are allocated later by `spec-kitty next --agent <agent> --mission 01KQQSCWP7HAJRR93F98AESKH4`.

## Context

- Spec: `kitty-specs/implement-review-retrospect-reliability-01KQQSCW/spec.md`
- Plan: `kitty-specs/implement-review-retrospect-reliability-01KQQSCW/plan.md`
- Contract: `kitty-specs/implement-review-retrospect-reliability-01KQQSCW/contracts/review-cycle-domain.md`
- Existing artifact model: `src/specify_cli/review/artifacts.py`

## Subtasks

### T001 - Add the narrow boundary and result types

Create `src/specify_cli/review/cycle.py`. Define small typed results for:

- Created rejected review cycle.
- Resolved pointer.
- Validation errors and warnings.

Keep the module free of CLI rendering and status persistence.

### T002 - Implement canonical pointer builder and validator

Build and validate `review-cycle://<mission>/<wp-task-file-slug>/review-cycle-N.md`.

Reject malformed segments, path traversal, empty mission slugs, empty WP slugs, and filenames that do not match `review-cycle-N.md`.

### T003 - Implement pointer resolver with legacy normalization warnings

Resolve:

- `review-cycle://...` under `kitty-specs/<mission>/tasks/<wp-slug>/`.
- `feedback://...` through the legacy git common-dir path with a deprecation warning.
- Sentinels such as `force-override` and `action-review-claim` as no-artifact operational tokens.

### T004 - Add required-frontmatter validation

Validate required review artifact fields before returning a pointer/result to callers. Required fields include mission identity or slug, WP id, cycle number, verdict, reviewed timestamp, reviewer identity, and artifact or feedback identity.

### T005 - Add focused unit tests

Add `tests/review/test_cycle.py` covering:

- Successful rejected cycle creation.
- Missing/empty feedback failure before artifact write.
- Invalid frontmatter failure.
- Canonical pointer resolution.
- Legacy `feedback://` resolution warning.
- Rejected `ReviewResult` references the canonical pointer.

## Definition of Done

- [ ] The boundary returns no pointer or review result on validation failure.
- [ ] New persisted pointers are canonical `review-cycle://...` URIs.
- [ ] Legacy pointers remain readable with warning.
- [ ] `uv run pytest tests/review/test_cycle.py -q` passes.

## Risks

- Do not turn this into a review runtime. It is only the pre-mutation invariant boundary.

## Implementation Command

```bash
spec-kitty agent action implement WP01 --agent <name>
```

## Activity Log

- 2026-05-03T21:14:06Z – codex:gpt-5:default:implementer – shell_pid=47989 – Assigned agent via action command
- 2026-05-03T21:40:00Z – codex:gpt-5:default:implementer – shell_pid=47989 – Ready for review
- 2026-05-03T21:40:15Z – codex:gpt-5:default:reviewer – shell_pid=3047 – Started review via action command
- 2026-05-03T21:40:18Z – codex:gpt-5:default:reviewer – shell_pid=3047 – Review passed: focused tests cover shared review-cycle boundary
- 2026-05-03T21:59:05Z – codex:gpt-5:default:reviewer – shell_pid=3047 – Moved to done
