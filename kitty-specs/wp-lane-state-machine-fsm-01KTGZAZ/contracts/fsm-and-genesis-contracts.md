# Phase 1 Contracts — FSM delegation, genesis invariant, SaaS lane delta

## Contract 1 — `validate_transition` delegates to the FSM (DM-01KTH03G)

```
validate_transition(from_lane, to_lane, ctx) -> (ok: bool, error: str | None)
    resolves aliases; then delegates to wp_state_for(resolved_from)
    so the State object decides edge + guard + force.
```

- **Pre**: `from_lane`/`to_lane` resolve to a known `Lane` (else `(False, "Unknown lane …")`).
- **Behavior**: identical `(ok, error)` results as the historical implementation for ALL
  existing (from,to,ctx) combinations (I4, I5) — including: actor-required, workspace_context,
  subtasks_complete_or_force, reviewer_approval, ReviewResult-required outbound from in_review,
  done-evidence, and force-override (force ⇒ requires actor + reason).
- **Post**: no transition-edge or guard logic remains outside the State objects.
- **Test**: parametrized parity over the full historical transition+guard matrix; a dedicated
  terminal force-exit parity test (`done`/`canceled` → any lane with force+actor+reason).

## Contract 2 — Genesis non-display invariant (I2)

- `genesis ∉ CANONICAL_LANES`; `genesis ∈ Lane`.
- Reducer summary dict EXCLUDES genesis: `{l.value: 0 for l in Lane if l is not Lane.GENESIS}`.
- `tasks.py` `by_lane`, runtime discovery candidate lists, and the kanban column map exclude
  genesis; a genesis-state WP is never silently dropped.
- `validate_canonical_event`: `genesis` valid as `from_lane` only; `to_lane=genesis` → non-canonical.
- frontmatter lane validation does not offer `genesis` as authorable.
- **Test**: assert reducer real output (not a fixture) has no genesis key; grep-style architectural
  assertion that no display/summary/discovery surface includes genesis.

## Contract 3 — Read/write parity (I3)

- `wp_lane_actor_from_events`, `read_current_wp_state_transactional` fallback,
  `runtime/next/discovery.py`, `runtime/next/decision.py`, `agent_utils/status.py`:
  default an unseeded WP to `Lane.GENESIS` (not `PLANNED`).
- `start_implementation_status` on a genesis WP raises `WorkPackageStartRejected`
  ("WP … not finalized; run `spec-kitty agent mission finalize-tasks`") **before** any
  workspace/worktree allocation.
- **Test**: each reader returns genesis for an unseeded WP; `implement` on an unseeded WP
  exits with the actionable message and leaves no `.worktrees/` entry.

## Contract 4 — `spec_kitty_events.Lane` delta (DM-01KTH03H)

- The external `spec_kitty_events.Lane` enum gains a `genesis` member (owning-package release).
- `StatusTransitionPayload` / `WPStatusChanged` accept `from_lane=genesis`.
- CLI `sync/emitter.py` `_PAYLOAD_RULES["WPStatusChanged"]` lane set is DERIVED from the
  canonical lane source (incl. genesis), not a hardcoded 9-lane list.
- The `genesis → planned` seed fans out without a swallowed `ValidationError`.
- **Compatibility**: a capability/version check guards the window before the genesis-aware
  `spec_kitty_events` release; no committed path/editable overrides (Shared Package Boundary).
- **Test**: a genesis seed produces a contract-valid SaaS payload; consumer/compatibility
  fixture covers both old and new `spec_kitty_events`.

## Contract 5 — Finalize preserves the coordination event log (baseline)

- `finalize-tasks` (coord topology) does not copy primary-checkout `status.events.jsonl`/
  `status.json` over the coord worktree's seeded copies; non-coord missions still commit theirs.
- **Test**: end-to-end coord `finalize-tasks` retains bootstrap lane events (FR-019).
