---
work_package_id: WP12
title: 'Wave Q: lock finalize-tasks linter + lane-depth fixes with regression tests (FR-015)'
dependencies: []
requirement_refs:
- FR-015
planning_base_branch: kitty/mission-test-stabilization-and-debt-pass-01KSF9HJ
merge_target_branch: kitty/mission-test-stabilization-and-debt-pass-01KSF9HJ
branch_strategy: Planning artifacts for this mission were generated on kitty/mission-test-stabilization-and-debt-pass-01KSF9HJ. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into kitty/mission-test-stabilization-and-debt-pass-01KSF9HJ unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-test-stabilization-and-debt-pass-01KSF9HJ
base_commit: 9edefee8a7c517594e6a5889042f83824f14691e
created_at: '2026-05-25T14:33:47.095408+00:00'
subtasks:
- T042
- T043
- T044
agent: "claude:opus-4-7:reviewer-renata:reviewer"
shell_pid: "1890802"
history:
- by: claude
  at: '2026-05-25T16:00:00+00:00'
  action: generated
agent_profile: python-pedro
authoritative_surface: tests/specify_cli/cli/commands/
execution_mode: code_change
mission_id: 01KSF9HJBFKRBC617JVHKZXNE2
mission_slug: test-stabilization-and-debt-pass-01KSF9HJ
owned_files:
- tests/specify_cli/cli/commands/test_finalize_tasks_explicit_empty_owned_files.py
- tests/specify_cli/lanes/test_compute_lane_depths_cycle_safety.py
- docs/reference/finalize-tasks-internals.md
priority: P2
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Invoke `/ad-hoc-profile-load` with argument `python-pedro` before reading further. Pure test-authoring + reference-doc work, locking two production fixes already on `main`.

## Objective

The finalize-tasks command had two bugs that the test-stabilization mission's own scaffolding surfaced:

1. **Linter clobbered explicit `owned_files: []`** — fixed in commit `0f4e1a383` (`fix(finalize-tasks): respect explicit owned_files: [] declarations`). The fix added `_owned_files_yaml_is_explicit_empty_list(raw_content)` in `src/specify_cli/cli/commands/agent/mission.py`.
2. **`_compute_lane_depths` recursed infinitely on lane-dep cycles / self-loops** — fixed in commit `72ff0d723` (`fix(lanes): cycle-safe _compute_lane_depths to prevent recursion blow-up`). The fix added an `in_progress` guard and a self-reference filter in `src/specify_cli/lanes/compute.py`.

Both fixes are live on `main`. This WP locks them with regression tests so a future refactor can't silently undo them, and documents the affected behaviour in a discoverable reference doc.

## Branch strategy

- Planning base branch: mission lane branch
- Merge target branch: `main`
- Execution: lane workspace allocated by `finalize-tasks`.

## Context

- Commit `0f4e1a383` on `main` — the linter fix.
- Commit `72ff0d723` on `main` — the lane-depth fix.
- [`spec.md`](../spec.md) FR-015 (this WP's authoritative spec entry).
- [`docs/engineering_notes/finding/2026-05-24-mission-01KSAF14-orchestration-findings.md`](../../../docs/engineering_notes/finding/2026-05-24-mission-01KSAF14-orchestration-findings.md) — predecessor-mission findings that motivated the broader Slice Q theme.

## Subtask details

### T042 — Linter explicit-empty regression test

Create `tests/specify_cli/cli/commands/test_finalize_tasks_explicit_empty_owned_files.py`:

```python
"""Lock the fix from commit 0f4e1a383: explicit ``owned_files: []`` is honoured.

When a WP frontmatter EXPLICITLY declares ``owned_files: []`` (e.g. for a
planning-artifact / triage WP that legitimately owns nothing in src/ or
tests/), finalize-tasks MUST NOT auto-populate the field with paths
extracted from the WP body text. Auto-population is reserved for the case
where the field is absent entirely.

Regression test for FR-015 of mission test-stabilization-and-debt-pass-01KSF9HJ.
"""
from __future__ import annotations

import pytest

from specify_cli.cli.commands.agent.mission import (
    _owned_files_yaml_is_explicit_empty_list,
)


def test_explicit_empty_list_detected():
    """``owned_files: []`` literal returns True."""
    raw = "---\nowned_files: []\n---\nbody\n"
    assert _owned_files_yaml_is_explicit_empty_list(raw) is True


def test_explicit_empty_list_with_padding_detected():
    """``owned_files:  [  ]`` literal returns True (whitespace tolerant)."""
    raw = "---\nowned_files:  [  ]\n---\nbody\n"
    assert _owned_files_yaml_is_explicit_empty_list(raw) is True


def test_absent_owned_files_returns_false():
    """No ``owned_files`` key returns False."""
    raw = "---\ntitle: foo\n---\nbody\n"
    assert _owned_files_yaml_is_explicit_empty_list(raw) is False


def test_populated_owned_files_returns_false():
    """Populated list returns False — inference NOT skipped."""
    raw = "---\nowned_files:\n- src/foo.py\n---\nbody\n"
    assert _owned_files_yaml_is_explicit_empty_list(raw) is False


def test_no_frontmatter_returns_false():
    """A WP body without frontmatter returns False."""
    raw = "no frontmatter here\nowned_files: []\n"  # not in frontmatter region
    assert _owned_files_yaml_is_explicit_empty_list(raw) is False


def test_body_mention_of_empty_list_ignored():
    """``owned_files: []`` mentioned in body text (not frontmatter) returns False."""
    raw = "---\ntitle: foo\n---\nThe owned_files: [] convention is...\n"
    assert _owned_files_yaml_is_explicit_empty_list(raw) is False
```

### T043 — Lane-depth cycle-safety regression test

Create `tests/specify_cli/lanes/test_compute_lane_depths_cycle_safety.py`:

```python
"""Lock the fix from commit 72ff0d723: _compute_lane_depths handles cycles.

A self-loop or arbitrary cycle in the lane dependency graph must NOT
trigger ``RecursionError: maximum recursion depth exceeded``. Cycle
detection is best-effort (the depth value for cycle members may not
reflect graph reality), but the function MUST return a valid dict
without blowing the stack.

Regression test for FR-015 of mission test-stabilization-and-debt-pass-01KSF9HJ.
"""
from __future__ import annotations

import pytest

from specify_cli.lanes.compute import _compute_lane_depths
from specify_cli.lanes.models import ExecutionLane


def _make_lane(lane_id: str) -> ExecutionLane:
    """Minimal ExecutionLane factory for tests."""
    return ExecutionLane(
        lane_id=lane_id,
        wp_ids=[],
        write_scope=[],
        predicted_surfaces=[],
        depends_on_lanes=[],
        parallel_group=0,
    )


def test_self_loop_does_not_recurse():
    """Lane that depends on itself returns depth 0 without RecursionError."""
    lanes = [_make_lane("lane-a")]
    lane_deps = {"lane-a": {"lane-a"}}
    depths = _compute_lane_depths(lanes, lane_deps)
    assert depths == {"lane-a": 0}


def test_two_lane_cycle_does_not_recurse():
    """A → B → A cycle returns a dict without RecursionError."""
    lanes = [_make_lane("lane-a"), _make_lane("lane-b")]
    lane_deps = {"lane-a": {"lane-b"}, "lane-b": {"lane-a"}}
    depths = _compute_lane_depths(lanes, lane_deps)
    assert set(depths.keys()) == {"lane-a", "lane-b"}
    # Each lane's depth is a finite int. Exact value is best-effort.
    for d in depths.values():
        assert isinstance(d, int)
        assert d >= 0


def test_three_lane_cycle_does_not_recurse():
    """A → B → C → A returns a dict without RecursionError."""
    lanes = [_make_lane(x) for x in ("lane-a", "lane-b", "lane-c")]
    lane_deps = {"lane-a": {"lane-b"}, "lane-b": {"lane-c"}, "lane-c": {"lane-a"}}
    depths = _compute_lane_depths(lanes, lane_deps)
    assert set(depths.keys()) == {"lane-a", "lane-b", "lane-c"}


def test_clean_dag_still_computes_correct_depths():
    """The cycle-detection guard MUST NOT regress clean-DAG output."""
    lanes = [_make_lane(x) for x in ("lane-a", "lane-b", "lane-c")]
    lane_deps = {
        "lane-a": set(),
        "lane-b": {"lane-a"},
        "lane-c": {"lane-a", "lane-b"},
    }
    depths = _compute_lane_depths(lanes, lane_deps)
    assert depths == {"lane-a": 0, "lane-b": 1, "lane-c": 2}


def test_independent_lanes_get_depth_zero():
    """Lanes with no deps all get depth 0."""
    lanes = [_make_lane(x) for x in ("lane-a", "lane-b", "lane-c")]
    lane_deps = {"lane-a": set(), "lane-b": set(), "lane-c": set()}
    depths = _compute_lane_depths(lanes, lane_deps)
    assert depths == {"lane-a": 0, "lane-b": 0, "lane-c": 0}
```

### T044 — Reference doc

Create `docs/reference/finalize-tasks-internals.md`:

```markdown
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
```

## Definition of Done

- [ ] `tests/specify_cli/cli/commands/test_finalize_tasks_explicit_empty_owned_files.py` exists with 6 tests covering explicit-empty / absent / populated cases. All pass.
- [ ] `tests/specify_cli/lanes/test_compute_lane_depths_cycle_safety.py` exists with 5 tests covering self-loop / 2-cycle / 3-cycle / clean-DAG / independent-lanes. All pass.
- [ ] `docs/reference/finalize-tasks-internals.md` exists and is linked from `docs/reference/cli-commands.md` index (the `## See also` block of the relevant CLI entry).
- [ ] `ruff check tests/specify_cli/cli/commands/test_finalize_tasks_explicit_empty_owned_files.py tests/specify_cli/lanes/test_compute_lane_depths_cycle_safety.py` clean.
- [ ] `mypy --strict` clean on the new test files.

## Risks

- **`ExecutionLane` constructor drift**: the test helper `_make_lane` constructs an `ExecutionLane`. If that dataclass's required fields drift, the helper needs updating. Mitigation: import from the canonical `specify_cli.lanes.models` and use only public fields.

## Reviewer guidance

1. Verify each regression test would FAIL if the corresponding fix is reverted (delete the `in_progress` guard or the `_owned_files_yaml_is_explicit_empty_list` call site, watch the test fail, restore).
2. Verify the reference doc is linked from the CLI commands index — discoverability is the deliverable.

## Activity Log

- 2026-05-25T14:33:47Z – claude:opus-4-7:python-pedro:implementer – shell_pid=1857672 – Assigned agent via action command
- 2026-05-25T14:40:57Z – claude:opus-4-7:python-pedro:implementer – shell_pid=1857672 – FR-015 locks landed: 11 regression tests + finalize-tasks-internals reference
- 2026-05-25T14:41:53Z – claude:opus-4-7:reviewer-renata:reviewer – shell_pid=1890802 – Started review via action command
- 2026-05-25T14:45:58Z – claude:opus-4-7:reviewer-renata:reviewer – shell_pid=1890802 – Review passed: 11/11 fix-lock regression tests pass, finalize-tasks-internals reference doc linked
