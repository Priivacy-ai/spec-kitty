# Adversarial review — architect-alphonso (sonnet, architectural soundness)

**Change:** `fix/status-genesis-lane-bootstrap` @ `a43aa6a06`.
**Verdict:** **CONCERNS.** Top: SaaS event layer not updated for genesis (silent fanout failure); secondary: `transition_to()` does not honour force, contradicting the "single source of truth" claim.

## Findings

**1. [MEDIUM] Dual API (`lane`/`current_lane`, `transition`/`transition_to`) — vocabulary debt without eliminating the old surface.** `wp_state.py`: `current_lane` delegates to `lane`; `transition_to` delegates to `transition`. Zero callers use the new names outside `wp_state.py`; all production call sites still use `.lane`/`.transition`. Half-done refactor, no deprecation marker / removal milestone. Recommendation: migrate call sites now (≈25 `wp_state_for(x).lane` sites) OR mark `lane`/`transition` `@deprecated` with a milestone. (NOTE for mission: the new interface was an explicit operator directive; keep it, but lock it in by migrating callers.)

**2. [HIGH] `WPState.transition_to()` does not honour `force` — contract diverges from `validate_transition()`.** `DoneState`/`CanceledState` `can_transition_to` return `False` regardless of `ctx.force`, so `done_state.transition_to(PLANNED, force=True)` raises. But `validate_transition` permits forced transitions not in `ALLOWED_TRANSITIONS` (with actor+reason). The FSM is NOT the single source of truth for force-override. Any caller migrating to `wp_state.transition_to()` silently loses forced terminal exits. Fix: honour `ctx.force` in the ABC `transition`, or explicitly document `validate_transition` as the force authority and narrow the ADR.

**3. [HIGH] SaaS event layer has no awareness of genesis — seed events silently drop.** `sync/emitter.py:270-271`; `spec_kitty_events.status.Lane` (v5.2.0) lacks genesis. The genesis→planned seed's SaaS fanout fails pydantic coercion → `_build_payload_via_model` returns None + console warning; local event persists but SaaS fanout is dropped. The correct SaaS representation of a genesis seed is `from_lane=None` (matching `is_bootstrap_planned_event()`) or an upstream `spec_kitty_events` enum update. Boundary contract violation; failure is silent.

**4. [MEDIUM] genesis leaks into `status.json` summary.** `reducer.py:161` `summary = {lane.value: 0 for lane in Lane}` → `"genesis": 0` in every snapshot (cross-branch fixture confirms). `test_summary_has_all_lane_keys` excludes genesis but tests a hand-built fixture, not reducer output — test & production misaligned. Contradicts "genesis never materializes into a snapshot". Fix: exclude `Lane.GENESIS` from summary init; test the reducer's real output.

**5. [LOW] `_derive_allowed_transitions` is an eager module-load constant from a deferred import.** Safe (models loaded first) but the deferred-import (`# noqa: PLC0415`) signals a latent cycle worked around rather than resolved. Consider extracting the edge matrix into a third module (`status/fsm_edges.py`) that neither `transitions` nor `wp_state` imports. Owns the debt in the ADR.

**6. [LOW] `bootstrap.py` uses `force=True` for the guard-free genesis→planned** — no bypass benefit; records `"force": true` on every seed, which may confuse consumers treating force as exceptional. Drop it or document future-proofing.

## Assessment
Substantially a true refactor for the 9 pre-existing lanes (derived matrix, green suite, `validate_transition` preserved). The FSM is only *structurally* the single source of truth (edge existence), not force-override. The ADR overstates encapsulation. The SaaS boundary (`spec_kitty_events.Lane`) was not updated in lock-step — undocumented silent consequence.
