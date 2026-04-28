---
affected_files: []
cycle_number: 1
mission_slug: release-3-2-0a5-tranche-1-01KQ7YXH
reproduction_command:
reviewed_at: '2026-04-27T19:41:41Z'
reviewer_agent: reviewer-renata
verdict: rejected
wp_id: WP08
---

# WP08 Review — REJECTED

## Verdict

**Rejected.** The fix in `src/specify_cli/status/store.py` is correct and the
`event_type`-presence guard is the right discriminator. However, the test
suite is missing a contract-required regression test, and the stated reason
for dropping it is empirically wrong. The contract explicitly demands that
malformed lane-transition events with bad lane fields still raise
`StoreError("Invalid event structure on line N: …")`, and the dropped test
(`test_read_events_still_raises_on_malformed_lane_event`, T037 outline in the
WP file) was the only coverage of that specific failure mode.

## Production code: ACCEPTED

- `src/specify_cli/status/store.py:222` — `if "event_type" in obj: continue`
  uses the correct PRESENCE-of-`event_type` discriminator (not absence-of-`wp_id`).
- The `# Why:` comment at `store.py:207-221` correctly names the two
  cooperating subsystems (status emitter / Decision Moment Protocol),
  explains why presence-of-`event_type` is preferred over absence-of-`wp_id`,
  and references FR-010.
- mypy --strict passes on `store.py`.
- The 4 included tests pass.

## Test gap: REJECTION TRIGGER

The implementer dropped `test_read_events_still_raises_on_malformed_lane_event`
from the WP file's T037 outline. Stated reason (paraphrased): "`Lane(value)`
accepts any string, so `from_lane='not_a_lane'` does NOT raise."

**This is empirically wrong.** Verified directly:

1. `Lane` is defined as `class Lane(StrEnum):` at
   `src/specify_cli/status/models.py:23` — a strict `StrEnum`, not
   permissive. `Lane('not_a_lane')` raises
   `ValueError: 'not_a_lane' is not a valid Lane`.

2. `StatusEvent.from_dict()` at `src/specify_cli/status/models.py:240-241`
   calls `cls._coerce_lane(data["from_lane"])`, which at line 230-231 does
   `return Lane(cls._LANE_ALIASES.get(value, value))`. For
   `value="not_a_lane"`, the alias map is a no-op and `Lane("not_a_lane")`
   raises `ValueError`.

3. `read_events()` at `src/specify_cli/status/store.py:233-234` catches
   `ValueError` and re-raises as
   `StoreError(f"Invalid event structure on line {line_number}: {exc}")`.

4. End-to-end smoke test confirms a single-event JSONL with
   `from_lane="not_a_lane"` raises:
   `StoreError: Invalid event structure on line 1: 'not_a_lane' is not a valid Lane`.

So the dropped test would have passed exactly as the WP plan described. It
should be present.

## Why this matters (not nitpicking)

The contract at
`kitty-specs/release-3-2-0a5-tranche-1-01KQ7YXH/contracts/status_event_reader_tolerates_decision_events.contract.md`
section "Required behavior" item 3 states:

> Lane-transition events with malformed lane fields still raise
> `StoreError("Invalid event structure on line N: …")`.

This is the entire point of choosing `event_type` PRESENCE over `wp_id`
ABSENCE as the discriminator (see the contract's "Why presence-of-event_type"
explanation and the implementation hint). Without the dropped test, there is
no regression coverage for this property — a future developer who switches to
the (more obvious-looking but contract-violating) `if "wp_id" not in obj:`
guard would silently swallow corrupted lane events with `from_lane="not_a_lane"`
and the test suite would not catch it.

The included
`test_read_events_still_raises_on_event_missing_wp_id_AND_event_type` covers
a *different* failure mode (missing `wp_id` AND missing `event_type`), which
would still raise even under a `"wp_id" not in obj` guard variant — so it
does NOT pin the discriminator choice. Only the malformed-lane-field test
discriminates between the two implementation choices.

## What to do

Add a test (use the WP file's T037 outline verbatim, or any equivalent that
asserts `StoreError("Invalid event structure on line 1: ...")` for an event
with `wp_id` PRESENT and a bad `from_lane` / `to_lane` value):

```python
def test_read_events_still_raises_on_malformed_lane_event(tmp_path: Path) -> None:
    """A lane-transition event with a bad from_lane MUST still raise.

    Pins the discriminator choice (event_type PRESENCE, not wp_id ABSENCE).
    """
    feature_dir = tmp_path / "feature"
    bad = _make_lane_event("01EVT0005", "WP03")
    bad["from_lane"] = "not_a_lane"
    _write_events_jsonl(feature_dir, [bad])

    with pytest.raises(StoreError, match="Invalid event structure on line 1"):
        read_events(feature_dir)
```

This test will pass as-is on the current implementation. After adding it,
re-run:

```
PWHEADLESS=1 uv run --extra test python -m pytest tests/status/test_read_events_tolerates_decision_events.py -v
```

and resubmit.

## Other deviations: ACCEPTED

- **Dossier snapshot refresh commit (`4ff650ff`)** — environmental, covered
  by occurrence_map exception (same shape as WP01's `04df3393` chore
  commit). Acceptable.
- **T038 unit-only verification** instead of global CLI reinstall — the WP
  plan offered both paths and labeled the unit-only path as
  "alternatively". Acceptable per the plan.

## Out-of-scope / commit hygiene

- WP08 commit (`680bfde7`) touches only `src/specify_cli/status/store.py`
  and the new test file. Clean.
- No other in-scope changes required.
