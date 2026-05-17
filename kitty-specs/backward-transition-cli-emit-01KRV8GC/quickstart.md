# Quickstart: Consuming the Fixed CLI Emit Path

**Audience**: Implementers of Mission 3 (`spec-kitty-saas` materializer + drain) and any future consumer that needs to test or rely on the CLI's auto-promoted backward emit behavior.

## What Changed at the Wire Level

Before this mission, `spec-kitty agent tasks move-task <WP> --to planned --mission <slug>` from `in_review`, `approved`, `for_review`, or `in_progress` emitted:

```json
{
  "force": false,
  "reason": "move-task: in_review -> planned",
  "from_lane": "in_review",
  "to_lane": "planned",
  ...
}
```

After this mission:

```json
{
  "force": true,
  "reason": "backward rewind: in_review -> planned: feedback://<mission>/<wp>/<ts>-<hash>.md",
  "from_lane": "in_review",
  "to_lane": "planned",
  ...
}
```

The change fires when the user did NOT pass `--force` AND the target lane precedes the current lane in `[planned, claimed, in_progress, for_review, in_review, approved, done]`.

## Mission 3 (`spec-kitty-saas`) Consumer Recipe

Mission 3's materializer test that verifies the new wire shape is accepted cleanly:

```python
# In tests for spec-kitty-saas/apps/sync/tests/test_materialize.py
# (or wherever the materializer's positive-path tests live)

def test_materialize_accepts_forced_backward_rewind():
    """Auto-promoted backward emit from the CLI materializes cleanly.

    Mirrors the wire shape produced by `spec-kitty agent tasks move-task ...`
    after Mission 2 (backward-transition-cli-emit) landed.
    See: spec-kitty kitty-specs/backward-transition-cli-emit-01KRV8GC/
         contracts/auto-promote-backward-emit.md
    """
    from spec_kitty_events.conformance import load_fixtures

    fixture = next(
        fc for fc in load_fixtures("edge_cases")
        if fc.id == "wp-status-changed-approved-rewind-valid"
    )
    # The fixture.payload represents the post-fix wire shape exactly.
    result = materialize_status_event(fixture.payload)
    assert result.status == "applied"
    # No business-rule rejection; no infra terminal_failed.
```

Mission 3's drain test that verifies pre-fix wire shapes (force=False backward) are classified as business-rule rejections, not infra terminal_failed:

```python
def test_drain_classifies_unforced_backward_as_business_rule():
    from spec_kitty_events.conformance import load_fixtures

    fixture = next(
        fc for fc in load_fixtures("edge_cases")
        if fc.id == "wp-status-changed-unforced-in-review-to-planned-invalid"
    )
    result = drain.process_item(fixture.payload)
    assert result.classification == "business_rule_rejection"
    assert result.classification != "infra_terminal_failed"
    # ProjectionAnomaly recorded; readiness not degraded.
```

## Test Driver Pattern (for any consumer)

To drive `move-task` end-to-end and capture the emitted wire shape in a test:

```python
# tests pattern modeled on tests/specify_cli/cli/commands/agent/test_tasks_backward_emit.py
def test_capture_emitted_event(tmp_path):
    feature_dir = _build_synthetic_feature(tmp_path, slug="demo-mission")
    _seed_wp_in_lane(feature_dir, wp_id="WP01", lane="approved")

    result = runner.invoke(
        app,
        ["agent", "tasks", "move-task", "WP01", "--to", "planned",
         "--mission", "demo-mission"],
        catch_exceptions=False,
    )
    assert result.exit_code == 0

    # Capture the last status event
    events_file = feature_dir / "status.events.jsonl"
    events = [json.loads(l) for l in events_file.read_text().splitlines()]
    last = events[-1]

    assert last["from_lane"] == "approved"
    assert last["to_lane"] == "planned"
    assert last["force"] is True
    assert last["reason"].startswith("backward rewind: approved -> planned")
```

## How to Tell the New Shape from the Old in Production

Operators inspecting `status.events.jsonl` in a production project can identify post-fix backward events by:

- `force == true` AND
- `reason` starts with `"backward rewind: "` AND
- `from_lane` precedes `to_lane` in the canonical forward order.

Pre-fix shapes (the planning#16 bug):

- `force == false` AND
- `reason` starts with `"move-task: "` AND
- `from_lane` precedes `to_lane` in REVERSE direction (i.e. backward).

The 22 dev evidence events in `~/spec-kitty-dev/terminal-failed-evidence-2026-05-17.json` are pre-fix shapes; Mission 3 (SaaS-side classification fix) decides their fate.

## Identifying the Post-Fix Code

In `src/specify_cli/cli/commands/agent/tasks.py`:

- Function: `move_task()` at line 1336.
- Auto-promote block: ~line 1715-1740 (after the existing `emit_force = force` and `emit_reason` fallback).
- Backward-direction predicate: `_is_backward_transition()` private helper, module-level or nested inside `move_task()`.

## Out of Scope for This Quickstart

- Replaying or reclassifying the 22 dev evidence events in production. That is Mission 3 territory.
- Changing the explicit-`--force` semantics. Preserved as-is.
- Adding new fields to `StatusTransitionPayload`. Wire shape is unchanged.
