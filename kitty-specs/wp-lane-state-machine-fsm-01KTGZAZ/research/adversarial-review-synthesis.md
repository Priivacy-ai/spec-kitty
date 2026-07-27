# Adversarial review synthesis — WP Lane FSM + Lane.GENESIS + finalize-clobber fix

**Reviewed**: branch `fix/status-genesis-lane-bootstrap` @ `a43aa6a06` (the initial implementation this mission formalizes).
**Method**: five independent subagents, each loading a Spec Kitty doctrine agent profile, attacking the change from its lens. Raw reports: `review-reviewer-renata.md`, `review-debugger-debbie.md`, `review-paula-patterns.md`, `review-architect-alphonso.md`, `review-randy-reducer.md`.

## Verdicts

| Lens | Verdict |
|------|---------|
| reviewer-renata | SHIP-WITH-FIXES |
| debugger-debbie | DEFECTS-FOUND (1 MED + 2 LOW); all four core intent claims held under falsification |
| paula-patterns | ISSUES-FOUND |
| architect-alphonso | CONCERNS |
| randy-reducer | TRIM-RECOMMENDED |

No lens returned BLOCK. The core (clobber fix + FSM single-source derivation + non-display genesis) is correct and well-tested.

## Validated under falsification (do NOT re-litigate)

- Derived `ALLOWED_TRANSITIONS` is **exactly** the prior 27 edges + 2 genesis edges (set-diff proven, 0 missing / 0 extra).
- No import cycle: `_derive_allowed_transitions` defers the `wp_state` import; importing `transitions` first in a fresh interpreter loads fine.
- Clobber fix correctly scoped: non-coordination missions still commit their primary-checkout `status.events.jsonl`/`status.json`; the skip only applies inside the coord-worktree branch.
- Genesis can never be a WP's **current** lane (zero `*→genesis` edges); it is a `from_lane`-only seed source.
- The ~30 test edits are genuine (real `genesis→planned` seeds; counts increased, never loosened).
- `ruff` clean; the mypy `no-any-return` findings are all pre-existing on `upstream/main`.

## Convergent findings (drive this mission's requirements)

**F1 — HIGH — SaaS fan-out silently drops the genesis seed event** (paula, alphonso).
`spec_kitty_events.Lane` (external contract, v5.2.0) has no `genesis`; the `genesis→planned` seed fails pydantic validation in `_saas_fan_out` / `sync/emitter.py:270-271` and is dropped with only a console warning. SaaS replay sees a WP appear in `planned` with no preceding seed. Fix: emit the seed to SaaS as `from_lane=None` (matches the existing `is_bootstrap_planned_event()` contract), or filter genesis at the SaaS boundary; secondarily, derive the hardcoded `_PAYLOAD_RULES["WPStatusChanged"]` lane set from the canonical source.

**F2 — MEDIUM — read/write layers still disagree for unseeded WPs (ADR "now agree" claim is false)** (renata, debbie, paula).
`_derive_from_lane` (write) returns `GENESIS`, but readers still default to `PLANNED`: `coordination/status_service.py::wp_lane_actor_from_events`, `coordination/status_transition.py::read_current_wp_state_transactional` fallback, `runtime/next/discovery.py`, `runtime/next/decision.py`, `agent_utils/status.py`. Consequence: `start_implementation_status` enters the PLANNED branch, the batch emit re-derives genesis, and surfaces a cryptic `Illegal transition: genesis -> claimed` with **no "run finalize-tasks" hint**, after the worktree is already allocated (dangling worktree). Off the happy path (finalize seeds first) but is exactly the #1589 class. Fix: align read-side defaults to `GENESIS` and add an explicit genesis branch in `start_implementation_status` raising an actionable `WorkPackageStartRejected` *before* workspace allocation.

**F3 — MEDIUM — `transition_to()` / `transition()` does not honour `force`, so the FSM is not the full single source of truth** (alphonso).
Terminal states (`done`/`canceled`) can be force-exited via `validate_transition` but `WPState.can_transition_to` returns `False` regardless of `ctx.force`. The FSM only owns *structural* edges, not force-override. Fix: honour `ctx.force` (with actor+reason) in the ABC `transition`, OR narrow the ADR/contract to state `validate_transition` remains the authority for forced terminal exits.

**F4 — LOW/MEDIUM — `genesis` leaks into the `status.json` summary as `"genesis": 0`** (debbie, alphonso, randy).
`reducer.py` builds `summary = {lane.value: 0 for lane in Lane}` → every snapshot carries `"genesis": 0`, contradicting the "non-display / never materializes in a snapshot" invariant. `test_summary_has_all_lane_keys` passes only because it tests a hand-built fixture, not reducer output. Fix: exclude `Lane.GENESIS` from the summary init; make the test assert the reducer's real output.

**F5 — LOW — `validate.py` accepts `genesis` as a `to_lane`** (renata). Should be `from_lane`-only (defense-in-depth; transition validation already rejects `*→genesis`).

## Leanness / hygiene (randy + others)

- **L1 (MED)** — 12 duplicated `_seed_planned` helpers across test files → consolidate to one/two shared conftest fixtures.
- **L2 (MED, OPERATOR-OVERRIDDEN)** — `current_lane` / `may_transition_to` / `transition_to` have zero internal callers; randy & alphonso recommend removing or deprecation-marking. **This contradicts the operator's explicit directive** that the FSM expose exactly this interface. Resolution: KEEP them (mandated public FSM API); optionally migrate a few internal call sites to lock them in and prove they are load-bearing.
- **L3 (LOW)** — stale docstrings: emit pipeline comment "(or 'planned')"; "9-lane" module docstrings; `tests/utils.py::_seed_canonical_wp_state` PLANNED default; annotate the now-tautological equivalence/`test_transition_count`.
- **L4 (LOW)** — `bootstrap` passes redundant `force=True` for the guard-free genesis seed.
- **L5 (LOW)** — runtime discovery `by_lane = {lane: [] for lane in Lane}` (`tasks.py:3997`) includes an always-empty genesis bucket that would silently drop a genesis WP from the table.
- **INFO** — the `_derive_allowed_transitions` deferred-import is justified; consider whether a third `status/fsm_edges.py` module would resolve the latent cycle more cleanly (architectural note, low urgency).
