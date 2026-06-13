---
work_package_id: WP07
title: Terminus Retrospective Triggering
dependencies: []
requirement_refs:
- FR-007
tracker_refs: []
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T031
- T032
- T033
- T034
- T035
agent: "claude:sonnet-4-6:reviewer:reviewer"
shell_pid: "95242"
history:
- date: '2026-06-12'
  author: spec-kitty.tasks
  note: Initial generation
agent_profile: python-pedro
authoritative_surface: src/specify_cli/post_merge/
execution_mode: code_change
owned_files:
- src/specify_cli/post_merge/retrospective_terminus.py
- src/specify_cli/cli/commands/merge.py
- tests/specify_cli/test_retrospective_triggering.py
priority: P1-Critical
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load python-pedro
```

---

## Objective

Ensure the terminus retrospective fires on ALL mission completion paths, not only the `spec-kitty next` terminal-decision branch. Consolidate the dead `run_terminus` code with the live `_run_retrospective_learning_capture` path. Emit `RetrospectiveSkipped` event when capture fails or is skipped. Fix `_record_path_str` stale path.

**This WP handles the TRIGGERING half. WP08 (generator ingestors) handles the content half and is independent — both can be developed in parallel.**

---

## Context

### The Bug (Issue #1164)

The retrospective capture is gated inside `spec-kitty next`'s terminal-decision branch — a branch that merge-completed missions never cross, because `merge` advances the lane directly to `done` without going through `next`. As a result, no merged mission ever produces a `retrospective.yaml`.

### Dead Code in `run_terminus`

`retrospective_terminus.py` contains `run_terminus`, which has the right postcondition logic (check for `retrospective.yaml`, emit `RetrospectiveSkipped` if absent). But it is dead code — nothing calls it on the merge path.

### Target Invariant

After `spec-kitty merge` completes, EXACTLY ONE of:
1. `kitty-specs/<slug>/retrospective.yaml` exists with non-empty `findings` or `ran_no_findings=true`
2. `status.events.jsonl` contains a `retrospective.skipped` or `retrospective.capture_failed` event

### `RetrospectiveSkipped` Event Schema

```json
{
  "event_id": "<ULID>",
  "at": "<ISO-8601>",
  "actor": "system",
  "feature_slug": "<slug>",
  "wp_id": null,
  "from_lane": null,
  "to_lane": null,
  "event": "retrospective.skipped",
  "reason": "<human-readable reason>",
  "evidence": null
}
```

---

## Subtasks

### T031 — Add merge-completion postcondition check for `retrospective.yaml`

1. Read `src/specify_cli/cli/commands/merge.py` and/or `src/specify_cli/merge/executor.py` for the merge completion exit point.
2. After a successful merge completion, add a postcondition call:
   ```python
   from specify_cli.post_merge.retrospective_terminus import run_retrospective_postcondition
   run_retrospective_postcondition(feature_dir=feature_dir, feature_slug=slug, actor="system")
   ```
3. `run_retrospective_postcondition` is the new public entry point (see T032).
4. If the postcondition raises (e.g., config unavailable), catch and emit `retrospective.capture_failed` event, then continue — do NOT abort the merge.

### T032 — Consolidate `run_terminus` dead code with `_run_retrospective_learning_capture`

1. Read `src/specify_cli/post_merge/retrospective_terminus.py` in full.
2. Read `_run_retrospective_learning_capture` (likely in `merge/executor.py`).
3. Create a new public function `run_retrospective_postcondition(feature_dir, feature_slug, actor)` that:
   - Checks if `kitty-specs/<slug>/retrospective.yaml` exists.
   - If YES: return (already captured).
   - If NO: call `_run_retrospective_learning_capture` (or its equivalent) to attempt capture.
   - On success: retrospective.yaml created.
   - On failure: emit `RetrospectiveSkipped` or `retrospective.capture_failed` event.
4. Remove or clearly mark `run_terminus` as deprecated in favor of this new function.
5. Do NOT duplicate the capture implementation — reuse `_run_retrospective_learning_capture`.

### T033 — Emit `RetrospectiveSkipped`/`CaptureFailed` event on failure/skip

1. In `run_retrospective_postcondition`, when skipping or failing:
   - Construct the `RetrospectiveSkipped` event dict (see schema above).
   - Append it to `kitty-specs/<slug>/status.events.jsonl` using the existing `append_event()` from `status.store`.
2. Use `event="retrospective.skipped"` when the capture was intentionally skipped (e.g., user opted out).
3. Use `event="retrospective.capture_failed"` when the capture was attempted but failed.
4. Populate `reason` with a human-readable explanation.

### T034 — Fix `_record_path_str` to use correct canon path

1. Read `retrospective_terminus.py` for `_record_path_str` (or similar).
2. Identify the stale path it references (likely a pre-083 path like `kitty-specs/<NNN-slug>/` instead of the mission-id-based path).
3. Fix to use the canonical path from the `feature_dir` resolver (same one used by the accept and finalize commands).

### T035 — Regression test: merge path → retrospective.yaml or skip event

File: `tests/specify_cli/test_retrospective_triggering.py` (new)

Write pytest tests that:
1. Set up a mission in a temp repo.
2. Simulate a successful merge completion (call the merge postcondition directly or via the CLI).
3. Assert EITHER:
   - `kitty-specs/<slug>/retrospective.yaml` exists, OR
   - `status.events.jsonl` contains an event with `event` in `("retrospective.skipped", "retrospective.capture_failed")`
4. Assert the merge does NOT abort due to a retrospective failure.
5. Also test: if `retrospective.yaml` already exists → postcondition is a no-op (idempotent).

---

## Branch Strategy

**Planning base**: `main` | **Merge target**: `main`

```bash
spec-kitty agent action implement WP07 --agent <name>
```

---

## Definition of Done

- [ ] Merge completion calls `run_retrospective_postcondition`
- [ ] `run_terminus` dead code consolidated into new public function
- [ ] `RetrospectiveSkipped`/`CaptureFailed` event emitted when capture fails
- [ ] `_record_path_str` uses correct canon path
- [ ] `test_retrospective_triggering.py` passes
- [ ] Merge does NOT abort on retrospective failure (fail-open at merge level)
- [ ] `mypy --strict` zero issues
- [ ] `ruff check .` zero issues

## Risks

- **Fail-open at merge**: The retrospective postcondition must NOT block a successful merge. Use `try/except` with event emission on failure.
- **`append_event` atomicity**: Confirm `append_event` is safe to call from the merge path (no file locking issues with concurrent daemons).
- **Idempotency**: If `run_retrospective_postcondition` is called twice (e.g., retried merge), it must not create duplicate events or re-run the generator. The `retrospective.yaml` existence check handles this.

## Activity Log

- 2026-06-13T07:59:40Z – claude:sonnet-4-6:implementer:implementer – shell_pid=55522 – Assigned agent via action command
- 2026-06-13T08:07:40Z – claude:sonnet-4-6:implementer:implementer – shell_pid=55522 – Ready for review: terminus retrospective triggering implemented
- 2026-06-13T08:07:53Z – claude:sonnet-4-6:reviewer:reviewer – shell_pid=95242 – Started review via action command
- 2026-06-13T08:15:27Z – user – shell_pid=95242 – Review passed: retrospective triggering wired at merge.py:2894-2898 after _run_lane_based_merge, fail-open correct, canonical meta.json path used for mission_id, exported from __init__.py, 10/10 tests pass. mypy errors only in planner.py (pre-existing, not in WP07 scope).
