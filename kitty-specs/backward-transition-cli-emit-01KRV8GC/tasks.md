# Tasks: CLI Backward-Transition Emit Path

**Mission**: backward-transition-cli-emit-01KRV8GC (mid8: 01KRV8GC)
**Target branch**: main
**Plan**: [plan.md](./plan.md) — Spec: [spec.md](./spec.md) — Research: [research.md](./research.md) — Data model: [data-model.md](./data-model.md) — Contract: [contracts/auto-promote-backward-emit.md](./contracts/auto-promote-backward-emit.md) — Quickstart: [quickstart.md](./quickstart.md)

Small mission. Two WPs.

## Subtask Index

| ID | Description | WP | Parallel |
|---|---|---|---|
| T001 | Add private helper `_is_backward_transition(current, target)` adjacent to the existing closure in `move_task()` (or as module-level helper). Use the same `FORWARD_ORDER` list literal pattern as `_lane_targets_for_emit`. | WP01 |  |
| T002 | At hotspot `tasks.py:~1712`, after the existing `emit_force = force` + emit_reason fallback, add the auto-promote block: detect backward direction, set `emit_force = True`, rewrite generic-fallback `emit_reason` to the canonical `"backward rewind: <from> -> <to>[: <feedback-ref>]"` shape (respecting user `--note`). | WP01 |  |
| T003 | New test file `tests/specify_cli/cli/commands/agent/test_tasks_backward_emit.py` with FR-008 test methods covering the four family members + forward control + skip-ahead forward expansion + feedback-ref inclusion. | WP02 |  |
| T004 | FR-009 wire-shape regression test inside the same file: load `wp-status-changed-approved-rewind-valid` from `spec_kitty_events.conformance.load_fixtures("edge_cases")`; drive `move_task` for `approved → planned`; assert emitted event's `force`, `reason`-prefix, `from_lane`, `to_lane` match the fixture. | WP02 |  |
| T005 | Verify quality gates: `uv run pytest tests/cli/commands tests/status -k "move_task or status or transition" -q` (NFR-001 ≤30s), `uv run pytest tests/ -q` (SC-004), `uv run ruff check src/specify_cli/` (NFR-003), `uv run mypy --strict src/specify_cli/cli/commands/agent/tasks.py` (NFR-003 — or the project's documented typing command for this file). | WP02 |  |

## Work Packages

### WP01 — Backward Detector + Emit-Path Fix

**Goal**: Implement the `_is_backward_transition` predicate and modify the hotspot at `tasks.py:~1710-1740` to auto-promote `emit_force=True` and synthesize the canonical reason on user-deliberate backward `move-task` requests.

**Priority**: P1 (foundation — WP02 tests target this code).

**Independent test**: After this WP and before WP02, running the existing `tests/specify_cli/cli/commands/agent/test_tasks.py` suite produces zero regressions; the new code is exercised by WP02 tests landing in the same lane.

**Included subtasks**:
- [x] T001 Add `_is_backward_transition(current_lane, target_lane) -> bool` helper. Place adjacent to `_lane_targets_for_emit` (line 1714). Use the same `FORWARD_ORDER` literal as the existing closure. Apply `resolve_lane_alias()` to both inputs. Return False if either resolved lane is outside the forward set or if target index is >= current index.
- [x] T002 Insert the auto-promote block AFTER the existing `if not emit_reason: emit_reason = ...` block (i.e., after line ~1712). Logic per `contracts/auto-promote-backward-emit.md` "Decision Procedure":
  - If `force` is truthy → return (existing path preserved).
  - If NOT `_is_backward_transition(old_lane, canonical_lane)` → return (forward / terminal / equal preserved).
  - Else: set `emit_force = True`. If `emit_reason is None or emit_reason.startswith("move-task: ")`, rewrite to `f"backward rewind: {old_lane} -> {canonical_lane}"` and append `f": {review_feedback_pointer}"` when the pointer is non-None and not the literal `"force-override"`.

**Implementation sketch**:

```python
# Module-level (or nested inside move_task):
_FORWARD_ORDER = [Lane.PLANNED, Lane.CLAIMED, Lane.IN_PROGRESS, Lane.FOR_REVIEW, Lane.IN_REVIEW, Lane.APPROVED, Lane.DONE]

def _is_backward_transition(current_lane: str, target_lane: str) -> bool:
    c = resolve_lane_alias(current_lane)
    t = resolve_lane_alias(target_lane)
    if c not in _FORWARD_ORDER or t not in _FORWARD_ORDER:
        return False
    return _FORWARD_ORDER.index(t) < _FORWARD_ORDER.index(c)

# Inside move_task, AFTER the existing emit_force / emit_reason fallback (~line 1712):
if not force and _is_backward_transition(old_lane, canonical_lane):
    emit_force = True
    if emit_reason is None or emit_reason.startswith("move-task: "):
        reason_parts = [f"backward rewind: {old_lane} -> {canonical_lane}"]
        if review_feedback_pointer and review_feedback_pointer != "force-override":
            reason_parts.append(review_feedback_pointer)
        emit_reason = ": ".join(reason_parts)
```

If the existing closure `_lane_targets_for_emit` already uses `forward = [Lane.PLANNED, ...]` as a local list, extract it once as `_FORWARD_ORDER` at module level and have both the closure and the new helper reference it (DRY). Optional — surgical alternative is to duplicate the literal.

**Parallel opportunities**: T001 and T002 touch the same file region; they should be authored together as one commit.

**Dependencies**: None (foundation).

**Risks**:
- Existing test suite expectations might break if any test invoked `move-task` with a backward target and relied on `force=False` being emitted. Research.md R-004 confirms no such test exists. Defense in depth: WP02's `uv run pytest tests/ -q` catches any unforeseen regression.

**Estimated prompt size**: ~250 lines.

**Owned files**:
- `src/specify_cli/cli/commands/agent/tasks.py` (modify, hotspot region only; no other functions touched)

### WP02 — Family + Wire-Shape Tests + Quality Gates

**Goal**: Add focused tests proving the auto-promote behavior (FR-008 a-f, FR-009) and verify all charter quality gates pass (NFR-001 through NFR-005, SC-001 through SC-005).

**Priority**: P1 (consumes WP01).

**Independent test**: The new test file passes; full unit suite passes; ruff + mypy + coverage gates green.

**Included subtasks**:
- [ ] T003 New test file `tests/specify_cli/cli/commands/agent/test_tasks_backward_emit.py`. Six methods minimum:
  - `test_in_review_to_planned_auto_promotes_force` (FR-008a)
  - `test_approved_to_planned_auto_promotes_force` (FR-008b)
  - `test_for_review_to_planned_auto_promotes_force` (FR-008c, partial — for_review variant)
  - `test_in_progress_to_planned_auto_promotes_force` (FR-008c, partial — in_progress variant)
  - `test_planned_to_claimed_does_not_auto_promote` (FR-008d, forward control)
  - `test_in_progress_to_for_review_expands_intermediate` (FR-008e, skip-ahead forward unchanged)
  - `test_backward_emit_includes_feedback_ref` (FR-008f, with `--review-feedback-file`)
- [ ] T004 In the same test file: `test_approved_to_planned_matches_mission1_fixture` — FR-009 wire-shape regression. Load fixture via `spec_kitty_events.conformance.load_fixtures("edge_cases")`. Assert on emitted-event payload: `force == True`, `reason.startswith("backward rewind: approved -> planned")`, `from_lane == "approved"`, `to_lane == "planned"`.
- [ ] T005 Run quality gates and report results:
  - `uv run pytest tests/cli/commands tests/status -k "move_task or status or transition" -q` (NFR-001 ≤30s)
  - `uv run pytest tests/ -q` (SC-004)
  - `uv run ruff check src/specify_cli/` (NFR-003)
  - `uv run mypy --strict src/specify_cli/cli/commands/agent/tasks.py` if it's the project's standing strict surface for this file; otherwise the project's documented typing command (NFR-003)
  - `uv run pytest --cov=src/specify_cli/cli/commands/agent/tasks --cov-report=term -k "backward_emit" tests/specify_cli/cli/commands/agent/test_tasks_backward_emit.py` for the new-code coverage spot check (NFR-004 ≥90%)

**Implementation sketch**:

Use the test pattern in `tests/specify_cli/cli/commands/agent/test_tasks.py` (existing tests in the same directory). Mirror its setup helpers: synthetic feature dir in `tmp_path`, minimal `tasks.md` + WP frontmatter + initial `status.events.jsonl`, invoke `move_task()` via Typer's `CliRunner`, capture emitted event by reading `status.events.jsonl`. For the FR-008e skip-ahead forward test, assert `len(events_after_call) == 3` (intermediate `in_progress → for_review` may be a single forward step, or assert based on the actual `_lane_targets_for_emit` expansion — confirm during implement).

**Dependencies**: WP01 (loads its new behavior).

**Risks**:
- Test setup for `move_task()` is non-trivial — the function takes many parameters and requires a feature dir with the right structure. Mirror `test_tasks.py` exactly; do not reinvent the setup harness.
- `tests/cli/commands/` directory (mentioned in the spec FR-008) does not exist in this repo. The actual test location is `tests/specify_cli/cli/commands/agent/`. The new file lands there; the spec's "tests/cli/commands/" reference is a doc-level approximation — verified during research.

**Estimated prompt size**: ~400 lines.

**Owned files**:
- `tests/specify_cli/cli/commands/agent/test_tasks_backward_emit.py` (new)

## Execution Order

```
WP01 (source fix) ──→ WP02 (tests + gates) ──→ Mission Review / Merge
```

Both WPs land in the same lane (WP02 depends on WP01). Single lane workflow.

## Requirement Coverage

| WP | Requirement refs |
|---|---|
| WP01 | FR-001, FR-002, FR-003, FR-004, FR-005, FR-006, FR-007, FR-011, FR-012 |
| WP02 | FR-008, FR-009, FR-010 |

NFRs 001-005, Cs 001-006 enforced by the combined WP set + WP02's verification step T005.
