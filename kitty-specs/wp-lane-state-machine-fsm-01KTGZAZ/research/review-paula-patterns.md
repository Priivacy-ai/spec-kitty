# Adversarial review — paula-patterns (sonnet, single-ownership)

**Change:** `fix/status-genesis-lane-bootstrap` @ `a43aa6a06`.
**Verdict:** **ISSUES-FOUND.** Single-source-of-truth for transition edges is architecturally achieved; three boundary leaks remain.

## Findings

**1. [MEDIUM] SaaS fan-out silently drops genesis→planned seed events.** `sync/emitter.py:270-271` (validator) + `status/emit.py` (`_saas_fan_out`). The external `spec_kitty_events.status.Lane` (v5.2.0) has no `genesis`. When the genesis→planned seed fans out, `_build_payload_via_model(StatusTransitionPayload, from_lane="genesis", …)` fails pydantic validation, returns `None`, prints a yellow console warning, and swallows the event. The local `_PAYLOAD_RULES["WPStatusChanged"]` lane-validator hardcodes 9 lanes without genesis — a second independent rejection. Impact: SaaS never observes the seed; replay sees a WP materialize into planned from nothing. Fix (preferred): filter genesis at the SaaS fan-out boundary (`from_lane == GENESIS` → skip / map to `from_lane=None`, matching `is_bootstrap_planned_event()`), documented as deliberate. Secondary: derive `_PAYLOAD_RULES` lane set from `CANONICAL_LANES | {"genesis"}`.

**2. [LOW] Runtime discovery defaults absent WPs to PLANNED, not GENESIS.** `runtime/next/discovery.py:118`, `runtime/next/decision.py:313,360`, `agent_utils/status.py:170`: `wp_lanes.get(wp_id, Lane.PLANNED)`. An unseeded WP appears claimable in discovery but is blocked at emit (genesis→claimed). Display/enforcement inconsistency. Fix: default to `Lane.GENESIS` so absent WPs are filtered from the claimable list.

**3. [LOW] `by_lane = {lane: [] for lane in Lane}` (`cli/commands/agent/tasks.py:3997`) includes a genesis bucket** never referenced in `display_columns` — a genesis-state WP at display time is silently dropped from the table. Fix: exclude genesis from the dict.

**4. [LOW] Stale lane-count comments:** `reducer.py:125` ("all 7 lanes"), `views.py:101` ("all 7 lanes"), `transitions.py:3` / `models.py:3` ("9-lane state machine"), `progress.py:25`. Update to reflect 10 enum members (9 active + genesis).

**5. [LOW] `test_transition_count` is tautological** now that `ALLOWED_TRANSITIONS` is derived from `allowed_targets()`; retain but annotate why.

## Parallel transition sources — grep summary
**No remaining parallel `ALLOWED_TRANSITIONS` frozensets** in `src/` beyond `_derive_allowed_transitions()` and its single consumer. `_GUARDED_TRANSITIONS` is correctly a separate concern. Remaining hardcoded lane sets are membership validators, NOT transition matrices: `sync/emitter.py:270` (Finding 1), `migration/rebuild_state.py:152` (deprecated, pre-`in_review`), `retrospective/generator.py` (analysis), `acceptance/__init__.py:61` (legacy). The single-source-of-truth claim for transition EDGES is sound.
