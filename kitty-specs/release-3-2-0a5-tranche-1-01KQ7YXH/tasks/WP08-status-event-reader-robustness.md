---
work_package_id: WP08
title: FR-010 status event reader robustness fix (DecisionPoint events)
dependencies: []
requirement_refs:
- FR-010
- NFR-010
planning_base_branch: release/3.2.0a5-tranche-1
merge_target_branch: release/3.2.0a5-tranche-1
branch_strategy: Planning artifacts for this feature were generated on release/3.2.0a5-tranche-1. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into release/3.2.0a5-tranche-1 unless the human explicitly redirects the landing branch.
created_at: '2026-04-27T18:00:45+00:00'
subtasks:
- T036
- T037
- T038
- T039
agent: "claude:sonnet:reviewer-renata:reviewer"
shell_pid: "68759"
history:
- at: '2026-04-27T18:00:45Z'
  actor: claude
  note: WP scaffolded by /spec-kitty.tasks (added live after FR-010 surfaced as a finalize-tasks blocker)
agent_profile: implementer-ivan
authoritative_surface: src/specify_cli/status/
execution_mode: code_change
mission_id: 01KQ7YXHA5AMZHJT3HQ8XPTZ6B
mission_slug: release-3-2-0a5-tranche-1-01KQ7YXH
owned_files:
- src/specify_cli/status/store.py
- tests/status/test_read_events_tolerates_decision_events.py
role: implementer
tags:
- foundational
- regression
- live-discovered
---

# WP08 — FR-010 status event reader robustness fix (DecisionPoint events)

## ⚡ Do This First: Load Agent Profile

Before reading further or making any edits, invoke the `/ad-hoc-profile-load` skill with these arguments:

- **Profile**: `implementer-ivan`
- **Role**: `implementer`

This loads your identity, governance scope, boundaries, and self-review checklist for code-change work. The bug-fixing-checklist tactic is especially relevant here: write the failing test (T037) BEFORE you touch `read_events()`. The current tranche's own `status.events.jsonl` is your live failing-test fixture.

## Objective

Make `specify_cli.status.store.read_events()` tolerate non-lane-transition events in `status.events.jsonl` instead of raising `KeyError('wp_id')`. Today, every mission that uses the Decision Moment Protocol (`spec-kitty agent decision open`) becomes unable to run any command that calls `read_events()` — including `finalize-tasks`, `materialize`, `reduce`, the dashboard scanner, and `doctor`.

This bug was discovered live during this very mission's `/spec-kitty.tasks` run when `finalize-tasks` rejected the mission's own `DecisionPointOpened` event with `Invalid event structure on line 1: 'wp_id'`.

## Context

**Live evidence** (already captured in [spec.md](../spec.md) "Live Evidence"):

- `kitty-specs/release-3-2-0a5-tranche-1-01KQ7YXH/status.events.jsonl` line 1 is a `DecisionPointOpened` event with `event_type` field but no `wp_id`. Line 2 is a `DecisionPointResolved` event of the same shape.
- `spec-kitty agent mission finalize-tasks --mission release-3-2-0a5-tranche-1-01KQ7YXH --json` returned `{"error": "Invalid event structure on line 1: 'wp_id'", "spec_kitty_version": "3.2.0a4"}`.

**Confirmed root cause** (from [research.md R9](../research.md#r9--status-event-reader-robustness-fr-010-nfr-010)):

In `src/specify_cli/status/store.py:194–217`, `read_events()` iterates every line in `status.events.jsonl` and calls `StatusEvent.from_dict(obj)` on each. The current code:

```python
for line_number, raw_line in enumerate(fh, start=1):
    stripped = raw_line.strip()
    if not stripped:
        continue
    try:
        obj = json.loads(stripped)
    except json.JSONDecodeError as exc:
        raise StoreError(f"Invalid JSON on line {line_number}: {exc}") from exc
    event_name = obj.get("event_name")
    if isinstance(event_name, str) and event_name.startswith("retrospective."):
        continue
    try:
        resolved_mission_id = _resolve_mission_id_from_dict(obj, resolver)
        if resolved_mission_id is not None and "mission_id" not in obj:
            obj = {**obj, "mission_id": resolved_mission_id}
        event = StatusEvent.from_dict(obj)  # <-- KeyError here on missing wp_id
    except (KeyError, ValueError, TypeError) as exc:
        raise StoreError(f"Invalid event structure on line {line_number}: {exc}") from exc
    results.append(event)
```

`StatusEvent` (`src/specify_cli/status/models.py:174–252`) is a lane-transition-only dataclass that hard-requires `wp_id`. Two cooperating subsystems write to the same file with incompatible schemas:

- **Lane-transition events** (the status emitter) carry `wp_id`, `from_lane`, `to_lane`, etc.
- **Mission-level events** (the Decision Moment Protocol — `DecisionPointOpened`, `DecisionPointResolved`, `DecisionPointDeferred`, `DecisionPointCanceled`, `DecisionPointWidened`) carry `event_type` and a payload, no `wp_id`.

The reader has no event-type discrimination beyond the `retrospective.*` skip.

**Fix shape**: a duck-type guard that skips any event lacking `wp_id`. Future-proof against new mission-level event types.

See [contracts/status_event_reader_tolerates_decision_events.contract.md](../contracts/status_event_reader_tolerates_decision_events.contract.md) for the testable invariant.

## Branch Strategy

- **Planning base branch**: `release/3.2.0a5-tranche-1`
- **Final merge target**: `release/3.2.0a5-tranche-1`
- This WP has no dependencies; its lane is rebased directly onto `release/3.2.0a5-tranche-1`.
- Execution worktrees are allocated per computed lane from `lanes.json` (created by `finalize-tasks`).

## Subtasks

### T036 — Add a duck-type `wp_id` guard in `read_events()`

**Purpose**: Skip non-lane-transition events instead of raising.

**Files**:
- `src/specify_cli/status/store.py` (~5-line change inside the per-line loop)

**Steps**:

1. Open `src/specify_cli/status/store.py` and locate `read_events()` around lines 194–217.
2. Immediately after the existing `retrospective.*` skip, add the new `event_type`-presence guard:

   ```python
   event_name = obj.get("event_name")
   if isinstance(event_name, str) and event_name.startswith("retrospective."):
       continue

   # Skip mission-level events (DecisionPointOpened, DecisionPointResolved,
   # DecisionPointDeferred, DecisionPointCanceled, DecisionPointWidened, and
   # any future event-type written by a non-status-emitter subsystem) that
   # share status.events.jsonl with lane-transition events. Mission-level
   # events carry a top-level `event_type` field; lane-transition events do
   # not. Discriminating on event_type PRESENCE (not a specific value
   # allowlist) is future-proof AND preserves the existing "raise on
   # malformed lane-transition event" contract — a corrupted lane event
   # missing wp_id but ALSO missing event_type still hits StatusEvent.from_dict
   # below and raises as today. See FR-010.
   if "event_type" in obj:
       continue

   try:
       resolved_mission_id = _resolve_mission_id_from_dict(obj, resolver)
       ...
   ```

3. The `# Why:` comment is required by the global "comments" rule — the WHY is non-obvious here (the cooperating subsystems and the schema-collision) and survives reviewer scrutiny.

**Validation**:
- [ ] `read_events()` per-line loop now has a `if "event_type" in obj: continue` guard immediately after the `retrospective.*` skip.
- [ ] No other code paths in `store.py` are touched.
- [ ] `git diff src/specify_cli/status/store.py` shows exactly the new guard + comment.

**Edge Cases / Risks**:
- A malformed lane-transition event that's MISSING `wp_id` (someone wrote a buggy event) WITHOUT also having `event_type` will still raise `Invalid event structure on line N: 'wp_id'` — preserving the existing fail-loud contract for corrupted lane events. The discriminator only skips events whose wire format explicitly identifies them as non-lane-transition.

### T037 — Add `tests/status/test_read_events_tolerates_decision_events.py`

**Purpose**: Lock the new behavior so any future regression to "raise on non-wp_id event" fails at test time.

**Files**:
- `tests/status/test_read_events_tolerates_decision_events.py` (new)

**Steps**:

1. Create the new test file. Reuse the existing `tests/status/conftest.py` fixtures if a tmp `feature_dir` helper is already defined; otherwise use `tmp_path`.

   ```python
   from __future__ import annotations

   import json
   from pathlib import Path

   import pytest

   from specify_cli.status.store import read_events


   def _write_events_jsonl(feature_dir: Path, events: list[dict]) -> None:
       feature_dir.mkdir(parents=True, exist_ok=True)
       events_path = feature_dir / "status.events.jsonl"
       events_path.write_text(
           "\n".join(json.dumps(e, sort_keys=True) for e in events) + "\n",
           encoding="utf-8",
       )


   def _make_lane_event(event_id: str, wp_id: str, to_lane: str = "claimed") -> dict:
       return {
           "event_id": event_id,
           "mission_slug": "demo",
           "wp_id": wp_id,
           "from_lane": "planned",
           "to_lane": to_lane,
           "at": "2026-04-27T12:00:00+00:00",
           "actor": "test",
           "force": False,
           "execution_mode": "worktree",
       }


   def _make_decision_opened(event_id: str) -> dict:
       return {
           "event_id": event_id,
           "event_type": "DecisionPointOpened",
           "at": "2026-04-27T11:00:00+00:00",
           "payload": {
               "decision_point_id": "01TESTDECISION0000000000",
               "mission_slug": "demo",
               "input_key": "demo_question",
               "question": "demo?",
           },
       }


   def _make_decision_resolved(event_id: str) -> dict:
       return {
           "event_id": event_id,
           "event_type": "DecisionPointResolved",
           "at": "2026-04-27T11:30:00+00:00",
           "payload": {
               "decision_point_id": "01TESTDECISION0000000000",
               "mission_slug": "demo",
               "final_answer": "yes",
           },
       }


   def test_read_events_skips_decision_point_events_returns_lane_events(
       tmp_path: Path,
   ) -> None:
       feature_dir = tmp_path / "feature"

       events = [
           _make_decision_opened("01EVT0001"),
           _make_lane_event("01EVT0002", "WP01"),
           _make_decision_resolved("01EVT0003"),
           _make_lane_event("01EVT0004", "WP02"),
       ]
       _write_events_jsonl(feature_dir, events)

       result = read_events(feature_dir)

       assert len(result) == 2, [e.event_id for e in result]
       assert [e.event_id for e in result] == ["01EVT0002", "01EVT0004"]
       assert [e.wp_id for e in result] == ["WP01", "WP02"]


   def test_read_events_with_only_decision_events_returns_empty(
       tmp_path: Path,
   ) -> None:
       feature_dir = tmp_path / "feature"
       _write_events_jsonl(feature_dir, [_make_decision_opened("01EVT0001")])
       assert read_events(feature_dir) == []


   def test_read_events_still_raises_on_invalid_json(tmp_path: Path) -> None:
       feature_dir = tmp_path / "feature"
       feature_dir.mkdir(parents=True)
       (feature_dir / "status.events.jsonl").write_text("{not json", encoding="utf-8")

       from specify_cli.status.store import StoreError

       with pytest.raises(StoreError, match="Invalid JSON on line 1"):
           read_events(feature_dir)


   def test_read_events_still_raises_on_malformed_lane_event(tmp_path: Path) -> None:
       feature_dir = tmp_path / "feature"

       # has wp_id (so passes any guard) but bad lane name
       bad = _make_lane_event("01EVT0005", "WP03")
       bad["from_lane"] = "not_a_lane"
       _write_events_jsonl(feature_dir, [bad])

       from specify_cli.status.store import StoreError

       with pytest.raises(StoreError, match="Invalid event structure on line 1"):
           read_events(feature_dir)


   def test_read_events_still_raises_on_event_missing_wp_id_AND_event_type(
       tmp_path: Path,
   ) -> None:
       """A corrupted lane-transition event missing wp_id MUST still raise.

       The event_type-presence guard intentionally only skips events whose
       wire format identifies them as non-lane-transition. A lane-transition
       event missing wp_id but ALSO missing event_type is corrupted and
       must surface, not silently disappear. Preserves the contract that
       malformed lane events fail loudly.
       """
       feature_dir = tmp_path / "feature"

       # Has neither wp_id nor event_type — a corrupted lane event.
       corrupted = _make_lane_event("01EVT0006", "WP04")
       del corrupted["wp_id"]
       _write_events_jsonl(feature_dir, [corrupted])

       from specify_cli.status.store import StoreError

       with pytest.raises(StoreError, match="Invalid event structure on line 1"):
           read_events(feature_dir)
   ```

2. If `tests/status/conftest.py` provides better fixtures (e.g. for `feature_dir` setup with `meta.json`), use those. The above is a self-contained scaffold.

3. Confirm both `read_events` failure modes still raise as expected (T037's last two tests preserve the existing contract for malformed JSON / malformed lane events).

**Validation**:
- [ ] `pytest tests/status/test_read_events_tolerates_decision_events.py -q` exits 0 after T036.
- [ ] All four tests pass.
- [ ] The first test FAILS without T036 (verify locally by stashing T036 once).

### T038 — Re-run this mission's `finalize-tasks` to confirm live regression closed

**Purpose**: The current tranche's own `status.events.jsonl` is the live regression. Confirm it's resolved.

**Steps**:

1. From the repo root: `spec-kitty agent mission finalize-tasks --mission release-3-2-0a5-tranche-1-01KQ7YXH --json`.
2. Expect a JSON success payload (not an error). Capture the `commit_created` and `commit_hash` fields if present.
3. If finalize-tasks reports `commit_created: true`, do NOT run another git commit afterwards (per the `/spec-kitty.tasks` template guidance).

**Validation**:
- [ ] Command exits 0.
- [ ] No `Invalid event structure on line 1: 'wp_id'` in output.
- [ ] If finalize-tasks committed files, `git log --oneline -1` shows the commit it created.

**Note**: This subtask is the live evidence cited in the FR-010 contract and PR description. It directly confirms the bug is closed for the symptom that triggered the WP.

### T039 — Run `mypy --strict` and `ruff check` on changed surfaces

**Purpose**: No type or lint regressions.

**Steps**:

1. Run `uv run --extra lint mypy --strict src/specify_cli/status/store.py`. Expect 0 errors.
2. Run `uv run --extra lint ruff check src/specify_cli/status/ tests/status/test_read_events_tolerates_decision_events.py`. Expect 0 errors.
3. Capture both command outputs in the PR description.

**Validation**:
- [ ] Both commands exit 0.

## Test Strategy

- **Unit** (T037): four cases covering happy path (mixed events), edge case (only DecisionPoint events), and preserved-failure cases (invalid JSON, malformed lane event).
- **Live regression** (T038): the mission's own event log is the ground-truth fixture. If finalize-tasks succeeds on it after the fix, the symptom that triggered the WP is closed.

## Definition of Done

- [ ] T036–T039 complete.
- [ ] `pytest tests/status/test_read_events_tolerates_decision_events.py -q` exits 0.
- [ ] `spec-kitty agent mission finalize-tasks --mission release-3-2-0a5-tranche-1-01KQ7YXH --json` exits 0 (live regression closed).
- [ ] `mypy --strict src/specify_cli/status/store.py` exits 0.
- [ ] `ruff check src/specify_cli/status/ tests/status/test_read_events_tolerates_decision_events.py` exits 0.
- [ ] PR description includes:
  - Live evidence narrative: this WP was added to the tranche during the tranche's own `/spec-kitty.tasks` run when `finalize-tasks` rejected the mission's `DecisionPointOpened` event.
  - One-line CHANGELOG entry text for **WP02** to consolidate. Suggested: `Fix \`read_events()\` raising \`KeyError('wp_id')\` on \`DecisionPointOpened\` / \`DecisionPointResolved\` events that share \`status.events.jsonl\` with lane-transition events. Restores \`finalize-tasks\` / \`materialize\` / dashboard for any mission that uses the Decision Moment Protocol (FR-010).`
  - GitHub issue number to file at PR-open time (placeholder; replace with actual once filed).

## Risks

- **R1**: Skipping `wp_id`-less events silently could hide a malformed lane-transition event that ALSO happens to be missing `wp_id`. Mitigation: writer-side validation already rejects malformed lane events. The duck-type skip preserves existing reader behavior for every well-formed event AND tolerates the well-formed mission-level events.
- **R2**: A future change might introduce a lane-transition event variant that legitimately has no `wp_id`. The current dataclass forbids it. If such an event-type is ever introduced, the dataclass change would land alongside a reader change; this WP's guard would still degrade gracefully in the meantime (the new event would be silently skipped, surfacing as a downstream "expected event missing" instead of a hard crash).

## Reviewer Guidance

- Verify the diff in `store.py` is exactly the new guard + the explanatory comment.
- Verify the `# Why:` comment names BOTH cooperating subsystems (status emitter + Decision Moment Protocol) and references FR-010.
- Verify T037's tests preserve existing failure-mode contracts (malformed JSON still raises, malformed lane event still raises).
- Verify T038's CLI smoke confirms the live regression is closed against this mission's own event log.

## Implementation command

```bash
spec-kitty agent action implement WP08 --agent claude
```

## Activity Log

- 2026-04-27T19:30:13Z – claude:sonnet:implementer-ivan:implementer – shell_pid=67890 – Started implementation via action command
- 2026-04-27T19:34:30Z – claude:sonnet:implementer-ivan:implementer – shell_pid=67890 – Ready for review: event_type-presence guard + 4 unit tests + mypy/ruff clean
- 2026-04-27T19:35:13Z – claude:sonnet:reviewer-renata:reviewer – shell_pid=68759 – Started review via action command
