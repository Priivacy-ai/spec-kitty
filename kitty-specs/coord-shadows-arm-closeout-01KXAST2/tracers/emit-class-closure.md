# Tracer: emit-layer class closure (IC-EMIT)

**Concern**: `_infer_subtasks_complete` stops failing open and reads the primary surface at ALL
FOUR callers; #2511 per-door patch retired after `status_transition.py:444` is fixed.

## Planning intent
- 4 production callers: `status/emit.py` ~:535 & ~:690, `coordination/status_transition.py` ~:444,
  `status/aggregate.py` ~:717. 5th (`orchestrator_api/commands.py` ~:1418-1430) = #2511 door → removed.
- Row semantics → `count_wp_section_subtask_rows`; surface → `resolve_planning_read_dir(kind=TASKS_INDEX)`.
- ORDERING: FR-003 (status_transition.py:444) BEFORE FR-005 removal, else orchestrator door re-opens.
- Headline regression: native `agent status --to for_review` w/o `--subtasks-complete` on a coord
  mission with unchecked rows → BLOCKED (via aggregate.py:717), through the production emit path.
- Do NOT touch `tasks_shared._check_unchecked_subtasks` (already correct).

## Implementation log
_(append: each caller threaded, whether request.repo_root was populated at aggregate.py:717, the
FR-005 removal + dead-code-gate result, the regression test location)_

## Close-out assessment
_(at close: is the class provably closed on BOTH native + orchestrator paths? any 5th caller found?)_
