# Phase 0 Research — WP Lane State Machine Canonicalization

The primary research for this mission is the **five-lens adversarial review** of the
baseline implementation (see `research/review-*.md` + `research/adversarial-review-synthesis.md`).
This file consolidates the resolved design decisions and the migration approach.

## Decision DM-01KTH03G — Guard/force ownership: FULL ownership in the State objects

- **Decision**: The guard matrix (actor presence, subtasks-complete, review-result,
  done-evidence) AND force-override move INTO the `WPState` objects.
  `validate_transition(from, to, ctx)` becomes a thin delegator to
  `wp_state_for(from).transition_to(to, ctx)` (or a `can_transition_to`/structured-result
  variant for the `(ok, error)` return). Each lane is a full StateObject.
- **Rationale**: Operator directive — "the FSM wired in FULLY, old paths fully shifted,
  force paths through the State objects." Eliminates the dual-locus (edges in states,
  guards/force in `validate_transition`) that the architect lens (review F3/alphonso-2)
  flagged: terminal force-exit was permitted by `validate_transition` but rejected by
  the FSM. One object owns its full behavior.
- **Alternatives considered**: keep the rich guards in `validate_transition` as a
  composed layer (smaller blast radius) — rejected by the operator as still half-wired.
- **Risk control**: behavior preservation is mandatory (NFR-001). The existing
  transition + guard test suites are the envelope; migrate guard-by-guard keeping the
  suite green; pin terminal force-exit parity with a dedicated test.

## Decision DM-01KTH03H — SaaS genesis: bump `spec_kitty_events.Lane`

- **Decision**: Add `genesis` to the external `spec_kitty_events.Lane` enum via the
  owning-package workflow, so the `genesis → planned` seed fans out as a real
  transition (not dropped, not mapped to `from_lane=None`).
- **Rationale**: Operator choice for faithful SaaS replay over the in-repo
  `from_lane=None` workaround. Resolves review F1/alphonso-3 (silent SaaS drop) at the
  contract level rather than masking it.
- **Process (Shared Package Boundary charter)**: change the `spec_kitty_events` repo
  first; publish a versioned artifact with compatibility notes; update CLI dependency
  constraints/lockfile; run consumer/compatibility tests. **No committed path,
  editable, or branch overrides.** Until the released version is available, guard the
  CLI side with compatibility fixtures / a capability check so older `spec_kitty_events`
  does not crash.
- **Alternatives considered**: `from_lane=None` bootstrap-planned mapping (in-repo, no
  external dep) — rejected by the operator in favor of contract fidelity.

## Validated baseline (do not re-litigate — falsified by the review)

- Derived `ALLOWED_TRANSITIONS` == historical 27 edges + 2 genesis edges (exact).
- No import cycle in `_derive_allowed_transitions` (deferred `wp_state` import).
- Finalize clobber fix correctly scoped (non-coord missions still commit status files).
- `genesis` can never be a WP's *current* lane (zero `*→genesis` edges).
- Baseline tests genuine (real `genesis→planned` seeds; counts increased), `ruff` clean,
  `mypy` neutral.

## Open research for Phase 1 / tasks

- The exact guard-to-state mapping (which `_GUARDED_TRANSITIONS` guard belongs to which
  source state's `transition_to`), and the return-shape of the delegated
  `validate_transition` (preserve `(ok, error_message)`).
- The `spec_kitty_events` compatibility gate (capability check vs version pin) for the
  window before the genesis-aware release ships.
