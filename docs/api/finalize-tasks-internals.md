---
title: finalize-tasks internals reference
description: Deep dive into the finalize-tasks internal command behavior. Learn about empty owned_files handling, status events, and dependency-depth cycle detection.
doc_status: active
updated: '2026-06-09'
---
# `finalize-tasks` internals reference

Two non-obvious behaviours an operator may encounter when running
`spec-kitty agent mission finalize-tasks`. Both have regression tests
under `tests/specify_cli/cli/commands/` and `tests/specify_cli/lanes/`.

## 1. Explicit empty `owned_files`

The finalize-tasks linter normally infers `owned_files` from path-like
strings in the WP body. This is helpful when the author never set the
field. It surprises an operator who EXPLICITLY set `owned_files: []`
because the WP is a triage / planning-artifact / acceptance task that
owns no source or test files.

The fix at commit `0f4e1a383` adds a pre-check: when the frontmatter
contains the literal pattern `^owned_files:\s*\[\s*\]\s*$`, inference
is skipped for that field. Authors who legitimately own no files write:

```yaml
---
work_package_id: WP01
execution_mode: planning_artifact
owned_files: []
authoritative_surface: docs/triage/
---
```

The ownership validator still rejects this if the WP is marked
`execution_mode: code_change` (a code-change WP that owns no files is
suspicious by definition).

## 2. Lane-depth cycle safety

`_compute_lane_depths` walks the lane-dependency DAG and assigns each
lane a depth (parallel group). The original implementation recursed
without cycle detection: any self-loop or cycle in `lane_deps` blew the
recursion stack with `maximum recursion depth exceeded`.

The fix at commit `72ff0d723` adds an `in_progress` guard and a
self-reference filter. Cycle detection is best-effort:

- A lane currently being computed is treated as depth-0 when
  re-encountered (breakpoint).
- Self-references in `lane_deps` are filtered before the recursion.

For a clean DAG (the common case) output is unchanged. For a cyclic
graph, the function returns a dict with each lane present and an
integer depth — but the depth value may not reflect graph reality. The
proper fix for a cyclic lane graph is to validate the inputs upstream
(in the WP-dependency parser), not to "solve" the cycle in the depth
function.

Both fixes are locked by tests in:

- `tests/specify_cli/cli/commands/test_finalize_tasks_explicit_empty_owned_files.py`
- `tests/specify_cli/lanes/test_compute_lane_depths_cycle_safety.py`

Removing those tests, or weakening their assertions to permit recursion,
is a regression.
