# Phase 0 Research: CLI Backward-Transition Emit Path

**Date**: 2026-05-17
**Mission**: backward-transition-cli-emit-01KRV8GC

This document resolves the five open questions named in `plan.md`'s risk register and pins concrete decisions for Phase 1 design.

---

## R-001 — Existing `_lane_targets_for_emit` Behavior on Backward Pairs

### Decision

**No refactor required.** The existing helper already returns `[target]` (the single target lane) for backward pairs — the `if target_idx > current_idx` guard short-circuits when target precedes current, falling through to the unconditional `return [target]`. FR-006 (single event for backward emits) is satisfied by the existing code path.

### Rationale

Source at `src/specify_cli/cli/commands/agent/tasks.py:1714-1724`:

```python
def _lane_targets_for_emit(current_lane: str, requested_lane: str) -> list[str]:
    current = resolve_lane_alias(current_lane)
    target = resolve_lane_alias(requested_lane)
    forward = [Lane.PLANNED, Lane.CLAIMED, Lane.IN_PROGRESS, Lane.FOR_REVIEW, Lane.IN_REVIEW, Lane.APPROVED, Lane.DONE]
    if current in forward and target in forward:
        current_idx = forward.index(current)
        target_idx = forward.index(target)
        if target_idx > current_idx:
            return forward[current_idx + 1 : target_idx + 1]
    return [target]
```

For backward pairs (`target_idx < current_idx`), both inner `if`s evaluate, but the inner `if target_idx > current_idx` is False — fall through to `return [target]`. For non-forward-set lanes (e.g. `blocked`, `canceled`), the outer `if current in forward and target in forward` is False — same fall-through. Single event in both cases.

### Impact on plan

The plan's "Backward transition_targets pruning" step (Implementation Strategy step 4) does NOT require a code change. The existing helper does the right thing. The new test in WP02 will still assert exactly one event is emitted for backward auto-promoted moves, as a regression guard.

**Plan refactor (extracting `_CANONICAL_FORWARD_ORDER` as a module-level constant) is OPTIONAL.** It can stay nested inside `move_task()` since the new `_is_backward_transition` helper can either (a) duplicate the `forward` list literal, or (b) extract it. Option (b) is preferred for DRY, but the diff stays surgical either way.

---

## R-002 — `--review-feedback-file` Parameter Threading

### Decision

The `--review-feedback-file` Typer option is declared at `tasks.py:1345` (typed `Path | None`). It is resolved to an absolute `feedback_candidate` path at line 1485-1486 and to a `_review_cycle.pointer` at line 1538 (`review_feedback_pointer = _review_cycle.pointer`). By the time control reaches the hotspot at line 1710, the local variable `review_feedback_pointer` is set (either to the URI form of the feedback file, `"force-override"`, or `None`).

**Use `review_feedback_pointer` as the source of `<feedback-ref>` in the auto-promoted reason shape.** When it is non-empty AND not the literal `"force-override"`, append `": <review_feedback_pointer>"` to the canonical reason.

### Rationale

- Existing emit code at line 1789 already passes `review_ref=emit_review_ref` (set at lines 1639-1644). The plumbing for feedback pointers is in place.
- Re-deriving the URI shape from `mission_slug`/`wp_id`/`timestamp` is unnecessary because the existing CLI already builds it.
- The literal `"force-override"` sentinel is used when `--force` is passed without a feedback file (line 1644). It should not be appended to the canonical reason; the reason should fall back to the bare `"backward rewind: <from> -> <to>"` form.

### Alternatives Considered

| Alternative | Rejected because |
|---|---|
| Synthesize a fresh URI from `mission_slug`/`wp_id`/`timestamp`/`hash` | Duplicates work the CLI already does. The existing pointer is canonical. |
| Pass through `--review-feedback-file` raw path | Loses the URI shape that Mission 1's contract anchor recommends. |

---

## R-003 — `emit_reason` May Be Set Before the Hotspot

### Decision

`emit_reason` is set in two upstream branches BEFORE line 1710:

- Line 1650: `emit_reason = note_text if note_text else None` (from `--note` option).
- Lines 1651-1652: `if force and not emit_reason: emit_reason = f"Force move to {target_lane}"` (when `--force` is passed without `--note`).

Then at line 1711 (current bug): `if not emit_reason: emit_reason = f"Force move to {target_lane}" if force else f"move-task: {old_lane} -> {target_lane}"`.

**Implementation plan**: the auto-promote check fires AFTER line 1711's `if not emit_reason` block. If `emit_reason` is already set (because the user passed `--note`), the auto-promote leaves the user's reason text intact (respecting user intent) but still sets `emit_force = True` for backward moves. If `emit_reason` is empty, the auto-promote rewrites it to the canonical shape.

### Rationale

- User-supplied `--note` text should be preserved (operator intent).
- The contract anchor (Mission 1) requires `force=True` and a non-empty `reason` — both conditions are satisfied whether the reason text is the canonical shape or user-supplied.
- A future tightening could require the user-supplied note to START with `"backward rewind: <from> -> <to>"` for backward moves — but that's a UX call outside this mission's scope. For now, preserve user intent; consumers (Mission 3 SaaS materializer) classify by `force=True` + lane direction, not by reason prefix.

### Alternatives Considered

| Alternative | Rejected because |
|---|---|
| Overwrite user `--note` text on backward moves | Violates user intent. |
| Refuse the move-task if user-note doesn't match the canonical shape | Tightens UX without contract requirement; out of scope. |
| Prepend `"backward rewind: <from> -> <to>: "` to the user's `--note` | Adds complexity; the canonical shape is normative, not prescriptive at the wire level. Mission 1 says "recommended" not "required" for the reason shape; `force=True + non-empty reason` is the actual contract. |

---

## R-004 — Pre-existing Tests Asserting `force=False` on Backward Moves

### Decision

**No matches found.** A repo-wide grep over `tests/` for combinations of `move_task` + `force.*False` + backward-lane targets (`planned`, `claimed`, `in_progress`, etc.) returns zero hits asserting the old (broken) behavior.

The grep matches that DID return are unrelated:
- Rich `Console(force_terminal=False, ...)` in test setup helpers.
- `--force` flag invocations on the `intake` command (unrelated to `move-task`).

### Rationale

The pre-existing `move-task` tests under `tests/specify_cli/cli/commands/agent/test_tasks.py` and adjacent files focus on:
- Lane transition validity (matrix check).
- Subtask gate enforcement.
- Review feedback file requirement (already enforced for `--to planned`).

None of them assert the specific wire-shape property that the planning#16 bug produced (`force=False` for backward moves). The bug was *behavioral*; pre-existing tests did not codify it as desired behavior.

### Impact on plan

No existing test needs to be modified or deleted. WP02 adds new tests; the full-suite regression check (`uv run pytest tests/ -q`) confirms no test inadvertently codified the old behavior.

---

## R-005 — FR-009 Fixture Loads Cleanly From `spec_kitty_events`

### Decision

The fixture `wp-status-changed-approved-rewind-valid` is registered in `spec_kitty_events/conformance/fixtures/manifest.json` (Mission 1, merged) and loadable via:

```python
from spec_kitty_events.conformance import load_fixtures
fixtures = {fc.id: fc for fc in load_fixtures("edge_cases")}
fixture = fixtures["wp-status-changed-approved-rewind-valid"]
# fixture.payload is the raw dict (from edge_cases/valid/wp_status_changed_approved_rewind.json)
```

Field shape (from Mission 1's WP01 commit, verified post-merge):

```json
{
  "wp_id": "WP07",
  "from_lane": "approved",
  "to_lane": "planned",
  "actor": "user",
  "force": true,
  "reason": "backward rewind: approved -> planned: feedback://mission-backward-transition-demo/WP07/20260517T141000Z-bbbb.md",
  "execution_mode": "worktree",
  "review_ref": "feedback://mission-backward-transition-demo/WP07/20260517T141000Z-bbbb.md",
  "evidence": null,
  "mission_slug": "mission-backward-transition-demo"
}
```

### Rationale

- Mission 1 mission-review verdict was PASS; fixture is committed and accessible from the installed `spec_kitty_events` package.
- The test's assertion shape is: `force == fixture.payload["force"]`, `reason.startswith("backward rewind: approved -> planned")`, `from_lane == "approved"`, `to_lane == "planned"`. The test does NOT compare the exact `reason` text byte-for-byte (because the feedback-ref differs across invocations); the prefix check is the contract.

### Alternatives Considered

| Alternative | Rejected because |
|---|---|
| Hard-code the expected wire shape in this mission's test | Duplicates Mission 1's contract; would drift if Mission 1 ever changes the fixture shape (e.g. adds a recommended field). |
| Compare emitted reason byte-for-byte to fixture reason | The feedback-ref is run-specific (synthetic fixture has a fixed URI; live emit has a real path). Prefix match is the contract. |

---

## R-006 — Test Driver Pattern

### Decision

Use the existing test pattern in `tests/specify_cli/cli/commands/agent/test_tasks.py`. These tests construct a synthetic feature dir in a `tmp_path`, write minimal `tasks.md` + WP frontmatter + `status.events.jsonl` to set up state, then invoke `move_task()` via Typer's `CliRunner`. The emitted event is captured by reading `status.events.jsonl` after the call.

Place new tests at `tests/specify_cli/cli/commands/agent/test_tasks_backward_emit.py` (mirroring the existing naming convention `test_tasks_*.py`).

### Rationale

- Existing pattern handles all the setup boilerplate (feature dir, manifest, lock-file conventions).
- `CliRunner` exercises the full Typer pipeline including option parsing — most authentic test surface.
- Reading `status.events.jsonl` post-call is the same approach the existing tests use; no test helper to invent.

### Alternatives Considered

| Alternative | Rejected because |
|---|---|
| Unit-test the new `_is_backward_transition` helper in isolation | Too narrow; the contract is at the emitted-event level, not the helper return value. The integration test covers both. |
| Mock `emit_status_transition` and capture call kwargs | Loses end-to-end fidelity; the mock could drift from the real signature. Reading the event log is the authentic check. |

---

## Open Questions Carried Forward

None. All Phase 0 questions resolved.
