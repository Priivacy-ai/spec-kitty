# FR-020 Investigation: approve-output source-lane anomaly

**Mission:** `legacy-sparse-and-review-lock-hardening-01KP54ZW`
**Work Package:** WP08 (research / planning artifact)
**Subtasks:** T032 (trace lane-state chain), T033 (publish and escalate)
**Date:** 2026-04-14
**Investigator:** claude:sonnet-4.6:implementer
**Related issue:** [Priivacy-ai/spec-kitty#589](https://github.com/Priivacy-ai/spec-kitty/issues/589)
**Related requirement:** FR-020 in `spec.md`

---

## 1. Summary

**Verdict: a real (low-severity) reporting bug exists — classification (a) "display bug in the approve output path," but the bug is in the *lane-state-machine choice* made by `spec-kitty agent action review`, not in the emit pipeline or the reducer.**

The user-visible output `Moved WPxx from in_progress to approved` is, strictly speaking, a **truthful report of the canonical event-log state at the moment of the transition**. The event log never contains a `for_review → approved` or `for_review → in_review` event for this workflow, because `spec-kitty agent action review` deliberately claims the WP by emitting a `for_review → in_progress` transition with `review_ref="action-review-claim"` (`src/specify_cli/cli/commands/agent/workflow.py:1317-1329`). Therefore the `old_lane` snapshot at approve time is genuinely `in_progress`, not `for_review`.

In other words: **the output is consistent with the canonical state, but the canonical state chosen by the review-claim codepath is a legacy shortcut that predates the 9-lane state machine's first-class `in_review` lane**. The anomaly Kent observed is a *semantic lie by historical design*, not a drift bug. A clean fix is low-risk and isolated, but it lives in `workflow.py` and `transitions.py` — outside the ownership scope of this mission — so we escalate rather than implement.

---

## 2. Reproduction (code walk-through, not shell run)

We did not execute a shell reproduction because the deliverable is a planning artifact and because the behavior is fully determined by three well-isolated call chains that can be inspected statically. Each chain is summarized below with file:line anchors.

### 2.1 Sequence under investigation

```
planned
  → claimed          (implementer claims)        [agent tasks move-task]
  → in_progress      (implementer works)         [agent tasks move-task]
  → for_review       (implementer hands off)     [agent tasks move-task]
  → in_progress (!)  (reviewer runs review)      [agent action review]  ← legacy-shortcut step
  → approved         (reviewer approves)         [agent tasks move-task --to approved]
```

The emitted approve event and the CLI output therefore carry `from_lane=in_progress`.

### 2.2 Step-by-step anchors

**(a) Review-claim transition — `for_review → in_progress` (not `for_review → in_review`).**
`src/specify_cli/cli/commands/agent/workflow.py:1315-1329`:

```python
with feature_status_lock(main_repo_root, mission_slug):
    # Emit the actual for_review -> in_progress transition
    emit_status_transition(
        feature_dir=feature_dir,
        mission_slug=mission_slug,
        wp_id=normalized_wp_id,
        to_lane=Lane.IN_PROGRESS,            # ← uses in_progress, NOT Lane.IN_REVIEW
        actor=agent,
        force=True,                           # review claim is always allowed
        reason="Started review via action command",
        review_ref="action-review-claim",
        ...
    )
```

This is the earliest point at which `for_review` is discarded in the event log for this WP during the review flow. The comment on line 1316 is literal and matches the code: the review command deliberately goes `for_review → in_progress`, not `for_review → in_review`. It passes `force=True` because the legal transition `for_review → in_progress` is **not** in the canonical `ALLOWED_TRANSITIONS` set (see `src/specify_cli/status/transitions.py:36-73`) — `for_review` only legally exits to `in_review`, `blocked`, or `canceled`. The `force=True` bypass is how this legacy review-claim step continues to work under the post-FR-012a (9-lane) model.

**(b) Approve transition — `from_lane` is derived from the event log.**
`src/specify_cli/status/emit.py:90-109`:

```python
def _derive_from_lane(feature_dir: Path, wp_id: str) -> str:
    events = _store.read_events(feature_dir)
    if not events:
        return Lane.PLANNED
    snapshot = _reducer.reduce(events)
    wp_state = snapshot.work_packages.get(wp_id)
    ...
    lane = wp_state.get("lane")
    if lane is not None:
        return Lane(lane)
    return Lane.PLANNED
```

And at the call site `src/specify_cli/status/emit.py:324`:

```python
from_lane = _derive_from_lane(feature_dir, wp_id)
```

This is correct. The reducer is deterministic (per `CLAUDE.md` status-model docs) and the last event for the WP before approve is the `for_review → in_progress` review-claim event from step (a). So `from_lane` on the emitted approve event is `in_progress`, which is what gets persisted into `status.events.jsonl` and what lights up SaaS telemetry. No bug in the emit pipeline or reducer.

**(c) CLI output — read from the same event-log snapshot.**
`src/specify_cli/cli/commands/agent/tasks.py:1035-1048`:

```python
# Load work package first (needed for current_lane check)
wp = locate_work_package(repo_root, mission_slug, task_id)
# Lane is event-log-only; read from canonical event log not frontmatter
_mt_feature_dir = main_repo_root / "kitty-specs" / mission_slug
try:
    from specify_cli.status.store import read_events as _mt_read_events
    from specify_cli.status.reducer import reduce as _mt_reduce

    _mt_events = _mt_read_events(_mt_feature_dir)
    _mt_snapshot = _mt_reduce(_mt_events) if _mt_events else None
    _mt_state = _mt_snapshot.work_packages.get(task_id) if _mt_snapshot else None
    old_lane = Lane(_mt_state.get("lane", Lane.PLANNED)) if _mt_state else Lane.PLANNED
except Exception:
    old_lane = Lane.PLANNED
```

And the final output statement `src/specify_cli/cli/commands/agent/tasks.py:1438`:

```python
_output_result(json_output, result, f"[green]✓[/green] Moved {task_id} from {old_lane} to {target_lane}")
```

`old_lane` is read from the reducer (event-log authority — post-3.0 behavior, correct per `docs/status-model.md`), and the event log's last-known state is `in_progress`. Therefore the string correctly reports `from in_progress to approved`.

### 2.3 What the transition matrix says about the "correct" flow

`src/specify_cli/status/transitions.py:36-73`:

```python
ALLOWED_TRANSITIONS: frozenset[tuple[str, str]] = frozenset(
    {
        ...
        ("in_progress", "for_review"),
        # Review progression: for_review is a queue state, in_review is active review
        ("for_review", "in_review"),
        # in_review outbound (all require ReviewResult in context)
        ("in_review", "approved"),
        ...
        # Direct approval paths (legacy, kept for backward compat)
        ("in_progress", "approved"),
        ("approved", "done"),
        ...
    }
)
```

The comment `Direct approval paths (legacy, kept for backward compat)` is the key evidence. The canonical 9-lane model defines the review flow as `for_review → in_review → approved`. The `in_progress → approved` edge exists only as a legacy compatibility path. The review command is using that legacy path (via `for_review → in_progress` + `in_progress → approved`) instead of the canonical path (via `for_review → in_review` + `in_review → approved`).

---

## 3. Root-cause analysis

The root cause is a **code-history mismatch** between two generations of the state model:

| Generation | Review flow | Lanes used |
|---|---|---|
| Pre-083 / pre-FR-012a | `for_review → in_progress → approved` | `in_review` was an alias or absent; `for_review` was essentially a queue |
| Post-FR-012a (current 9-lane) | `for_review → in_review → approved` | `in_review` is a first-class waypoint with guard `review_result_required` |

The review-claim codepath in `workflow.py` was not updated to the new flow when FR-012a made `in_review` first-class. It continues to emit `for_review → in_progress` (with `force=True` to bypass the matrix), so every post-3.0 review that goes through `spec-kitty agent action review` leaves a misleading `in_progress` marker in the event log. The approve event then correctly reports that marker.

**Evidence that this is the codepath at fault, not the emit pipeline:**

1. `_derive_from_lane` in `emit.py` reads from the reducer, which is deterministic and well-tested.
2. The reducer's materialize path is exercised by the 034 status-model integration suite (per `CLAUDE.md` references).
3. If an implementer moves `for_review → approved --force` *without* going through `agent action review`, the output would read `from for_review to approved` (consistent). The anomaly only appears when the review-claim codepath runs first.
4. The comment at `transitions.py:49-50` explicitly labels `in_progress → approved` as a legacy compat edge.

**Why `force=True` is required for the review claim:** `for_review → in_progress` is not in `ALLOWED_TRANSITIONS`. Without `force=True`, the review command would fail validation. This is a strong signal that the codepath is using force as a polyfill for the missing canonical transition, which is exactly what FR-012a's introduction of `in_review` was intended to remove.

---

## 4. Is this the same bug as FR-015 (review-lock self-collision)?

No. FR-015 is about `.spec-kitty/review-lock.json` tripping the uncommitted-changes guard. FR-020 is about the `from_lane` label in the approve output. They share a common surface (both observed during the same `move-task --to approved` invocation in issue #589) but have independent root causes and independent fixes.

---

## 5. Verdict

**Classification per the WP spec's four outcomes:**

> (a) a display bug in the approve output path, or
> (b) a deliberate consequence of how `spec-kitty agent action review` advances the lane state (review-claim does not advance to `in_review`), or
> (c) a reducer anomaly in `specify_cli/status/reducer.py`.

The answer is **(a) + (b) together, but neither in isolation**:

- The output is *literally* a deliberate consequence of (b): `agent action review` chose `for_review → in_progress` instead of `for_review → in_review`, and everything downstream reports the truth of that choice.
- The *user-visible effect* is (a): the output is semantically wrong because the WP spent its review window in an `in_progress`-labeled event-log state rather than the canonical `in_review` state.
- (c) is excluded: the reducer is correct, and changing the reducer to "pretend" the source lane was `for_review` would be a lie bigger than the one we have now.

**Is it a real bug?** Yes — a low-severity semantic-reporting bug, not a data-loss or state-corruption bug. The WP's canonical history is complete and auditable; it just reads `in_progress` where a 3.x-native reader would expect `in_review`. Dashboard rows, SaaS telemetry, and any downstream consumer that surfaces the review waypoint will all show `in_progress` for the duration of active review.

**Is it already fixed?** No. The `for_review → in_progress` emission in `workflow.py:1321` is still present on `main` as of this investigation (commit context: `c62a5a6c` etc. on the WP08 branch).

---

## 6. Recommended fix (NOT to be implemented in WP08)

Per WP08's ownership-isolation constraint, this fix does NOT land in this mission. File a follow-up issue and hand off.

### 6.1 The minimal change

In `src/specify_cli/cli/commands/agent/workflow.py` around line 1321:

- Change `to_lane=Lane.IN_PROGRESS` to `to_lane=Lane.IN_REVIEW`.
- Remove the `force=True` (no longer needed — `for_review → in_review` is a canonical transition per `transitions.py:43`).
- Remove `review_ref="action-review-claim"` or repurpose it — the `in_review` state is self-describing.
- Update the guard `_guard_actor_required_conflict_detection` (already exists at `transitions.py:82` mapped to `("for_review", "in_review"): "actor_required_conflict_detection"`) to accept the review command's actor/shell-pid inputs.

Elsewhere:

- `workflow.py:1278-1296` currently checks `current_lane in {Lane.FOR_REVIEW, Lane.IN_PROGRESS}` as "reviewable." This needs to extend to include `Lane.IN_REVIEW` (because a reviewer may re-attach to an in-flight review).
- `workflow.py:1287` (`is_review_claimed = ... Lane.IN_PROGRESS and .review_ref == "action-review-claim"`) becomes a lookup for `to_lane == Lane.IN_REVIEW` instead.
- `tasks.py:1426` (`if old_lane in (Lane.FOR_REVIEW, Lane.IN_PROGRESS) and target_lane in (Lane.APPROVED, Lane.PLANNED):`) extends to include `Lane.IN_REVIEW`.
- Any review-claim lookups in `_find_first_for_review_wp` (`workflow.py:1136`) that assume `in_progress` means "review-claimed" need updating.
- Add a one-liner migration note to the status-model docs: pre-this-fix missions will have `in_progress → approved` in their history where post-fix missions will have `in_review → approved`. Both are valid; aggregations that count time-in-review need to look at `review_ref` or at the most-recent lane chain.

### 6.2 Scope signal

The change spans `workflow.py`, possibly `transitions.py` (if we want to tighten guards rather than rely on force), and the `docs/status-model.md` documentation. It is multi-file but all within a single ownership lane — not a cross-cutting refactor. Estimated size: ~1 day for implementation + tests.

### 6.3 Tests to add

- New integration test `tests/integration/agent/test_review_claim_uses_in_review.py` that runs `move-task → for_review` then `agent action review WPxx --agent alice`, then asserts the latest event for WPxx has `to_lane == "in_review"` (not `in_progress`).
- Regression test that the full sequence `for_review → in_review → approved` leaves a clean `in_review → approved` event with `from_lane == "in_review"` in the approve output.
- Test that re-running `agent action review` on an already-claimed WP is idempotent and does not double-emit.

### 6.4 Follow-up issue content (to file separately)

Title: **Fix approve-output from-lane reporting: review-claim should emit `for_review → in_review` (FR-020 of mission 01KP54ZW)**

Body excerpt:

```
spec-kitty agent action review currently emits a for_review → in_progress transition
with force=True (workflow.py:1321), predating the post-FR-012a 9-lane model in which
in_review is a first-class lane. The consequence is that every subsequent approve
transition reports its from_lane as in_progress rather than in_review, which Kent
reported in #589 as confusing.

The investigation report lives at
kitty-specs/legacy-sparse-and-review-lock-hardening-01KP54ZW/research/fr020-investigation.md
and contains the full call-chain analysis, the transition-matrix evidence, and the
recommended fix (including the list of downstream call-sites that need updating in
the same change).

Scope: single-lane multi-file change in workflow.py + transitions.py guard tightening
+ docs/status-model.md migration note. Roughly 1 day.

Links back to mission 01KP54ZW for context on why the fix was escalated rather than
implemented inline.
```

---

## 7. Files inspected

| File | Lines | Purpose |
|---|---|---|
| `src/specify_cli/cli/commands/agent/workflow.py` | 982, 1136, 1216-1412 | `review` command, `_resolve_review_context`, `_find_first_for_review_wp`, review-claim emission |
| `src/specify_cli/cli/commands/agent/tasks.py` | 967-1438 | `move_task` command; `old_lane` derivation (1035-1048); approve-output string (1438) |
| `src/specify_cli/status/emit.py` | 90-109, 255-435 | `_derive_from_lane` and `emit_status_transition` pipeline |
| `src/specify_cli/status/transitions.py` | 13-94 | `CANONICAL_LANES`, `ALLOWED_TRANSITIONS`, `_GUARDED_TRANSITIONS`, `resolve_lane_alias` |
| `src/specify_cli/status/reducer.py` | (referenced) | Deterministic event-log reducer; confirmed correct by design and by existing test suite |

---

## 8. Next step (T033 escalation)

1. **This investigation document is the T032 deliverable** — committed to the research directory as part of WP08.
2. **No code changes in this WP.** Ownership isolation upheld: `workflow.py` and `transitions.py` are owned by other tracks (Lane B/C detection + preflight work and the broader status-model, respectively).
3. **Follow-up issue to be filed in `Priivacy-ai/spec-kitty`** with the title and body excerpt in §6.4. The issue should link back to this document and to #589.
4. **WP09 (CHANGELOG + issue coordination)** should pick up the cross-reference when it lands, noting that FR-020 is escalated to a follow-up issue rather than closed inside this mission.
5. **No documentation update to `docs/status-model.md` is required from WP08** — the migration note belongs in the follow-up issue's fix, where the behavior change is actually happening.

---

## 9. Appendix: answers to the WP spec's explicit questions

**Q1. Does `spec-kitty agent action review` call `emit_status_transition` to advance the lane from `for_review` to `in_review`?**

A1. **No.** It calls `emit_status_transition` with `to_lane=Lane.IN_PROGRESS` and `force=True`. See `workflow.py:1317-1329`. The transition `for_review → in_progress` is NOT in the canonical `ALLOWED_TRANSITIONS` set; `force=True` is used to bypass.

**Q2. What does `move-task --to approved` use as the `from_lane` in the emitted event?**

A2. It uses the value returned by `_derive_from_lane()` in `emit.py`, which reduces the event log and reads the current lane from the resulting snapshot. It does **not** read from frontmatter (correct, per 3.0 read-cutover). See `emit.py:90-109, 324`. The CLI output at `tasks.py:1438` uses an independently derived `old_lane` from the same reducer snapshot (`tasks.py:1035-1048`).

**Q3. Replay the transitions; what `from_lane` appears on the approve event?**

A3. By static analysis of the call chains above: `in_progress`. The review-claim step overwrote the `for_review` marker in the event log. The approve event's `from_lane` is derived from the reduced log, which now reads `in_progress`.

**Q4. Four-outcome verdict:**

A4. Hybrid **(a) + (b)** — see §5. Not a display bug in the emit pipeline, not a reducer anomaly, not a misreading by the original reporter. It is a design-era mismatch: the review-claim codepath uses a legacy lane and the approve path truthfully reports it. The fix is a scoped change to the review-claim codepath, escalated as a follow-up issue per §6.4.
