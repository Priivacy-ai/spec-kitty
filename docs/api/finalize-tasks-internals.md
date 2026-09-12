---
title: finalize-tasks internals reference
description: Deep dive into finalize-tasks internals - empty owned_files handling, status events, lane-depth cycle safety, and the planning_commit_sha refresh override.
doc_status: active
updated: '2026-09-09'
---
# `finalize-tasks` internals reference

Three non-obvious behaviours an operator may encounter when running
`spec-kitty agent mission finalize-tasks`. All have regression tests
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

## 3. Refreshing the recorded planning commit after an amendment (#4141)

`finalize-tasks` freezes `planning_commit_sha` into `lanes.json` at first
run. Once execution has begun (any WP past `planned`), a re-finalize
PRESERVES that recorded SHA (#3311) — correct for an ownership-only
amendment, which must not silently clobber established planning provenance.
But preserve-only left no sanctioned way to advance the SHA after a
legitimate planning amendment (a WP dependency-field fix, an `/spec-kitty
.analyze` remediation) landed mid-execution: every subsequently allocated
lane kept merging the stale planning snapshot, the `move-task` gates
(branch-currency / `kitty-specs/` contamination / uncommitted-changes) fired
on the resulting drift, and the only in-tool path was `--force` on every
transition.

The fix adds an explicit, advance-only override:

```bash
spec-kitty agent mission finalize-tasks --mission <slug> --refresh-planning-commit
```

- With execution begun, the recorded SHA is re-pointed to the current
  target-branch tip, so lanes merge the amended planning state at their next
  allocation/reuse.
- The override is refused (exit 1, `lanes.json` untouched) when the recorded
  SHA is not an *ancestor* of the tip — a history rewrite or a foreign
  provenance SHA, not an amendment. Resolve the divergence manually instead.
- Without the flag, the #3311 preserve behavior is unchanged, but a
  re-finalize that detects drift (recorded SHA ≠ branch tip) now warns on
  the console and names the flag; the `--json` success payload carries the
  decision structurally under `planning_commit`
  (`action` / `sha` / `previous_sha` / `branch_tip`).

Locked by tests in:

- `tests/specify_cli/cli/commands/agent/test_issue_4141_refresh_planning_commit.py`
- `tests/specify_cli/cli/commands/agent/test_mission_finalize_phases.py` (the
  `_preserve_or_capture_planning_commit_sha` / `_report_planning_sha_decision`
  branch tests)

Weakening the ancestor refusal, or making the refresh the default (no flag),
is a regression.
