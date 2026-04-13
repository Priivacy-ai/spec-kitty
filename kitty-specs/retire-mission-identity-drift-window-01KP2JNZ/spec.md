# Retire Mission Identity Drift Window

**Mission ID**: `01KP2JNZ7FRXE6PZKJMH790HA5`
**GitHub Issue**: [Priivacy-ai/spec-kitty#557](https://github.com/Priivacy-ai/spec-kitty/issues/557)
**Cross-repo Dependency**: [Priivacy-ai/spec-kitty-saas#66](https://github.com/Priivacy-ai/spec-kitty-saas/issues/66)
**ADR**: [2026-04-09-1](../../architecture/adrs/2026-04-09-1-mission-identity-uses-ulid-not-sequential-prefix.md)

## Problem Statement

The CLI's mission-identity migration (ADR 2026-04-09-1) has landed. `mission_id` (ULID) is the canonical machine-facing identity for all new missions. However, a **drift-window compatibility shim** remains in the CLI codebase: the `legacy_aggregate_id` field emitted in status events, and the `effective_aggregate_id` fallback to `mission_slug` in sync emitter methods. These shims exist solely to bridge older SaaS readers that may still index by slug instead of ULID.

The SaaS-side read-switch is tracked in `spec-kitty-saas#66`. Once that work confirms the SaaS side reads only `mission_id` and no longer depends on `legacy_aggregate_id` or slug-keyed aggregate lookup, the CLI shims become dead code and should be removed.

**This mission is explicitly blocked until `spec-kitty-saas#66` is complete and drift-window closure readiness is confirmed.**

## Motivation

- **Code hygiene**: Dead compatibility paths increase cognitive load and testing surface for no ongoing value.
- **Contract clarity**: Removing the shim makes the wire format unambiguous — `mission_id` is the only aggregate identity, full stop.
- **Issue closure**: Removing the shim is the last prerequisite for closing GitHub issue #557, which has been open since the ADR was proposed.

## Scope

### In Scope

1. **Remove `legacy_aggregate_id` from `StatusEvent.to_dict()`** — stop emitting the drift-window field in status event serialization.
2. **Remove `effective_aggregate_id` fallback in sync emitter** — make `mission_id` mandatory (not `Optional`) in `emit_mission_created`, `emit_mission_closed`, and `emit_mission_origin_bound`; stop falling back to `mission_slug` as the aggregate identity.
3. **Update tests** — remove or rewrite tests that assert `legacy_aggregate_id` presence, update contract matrix tests to reflect the final wire format, and add assertions that the removed field is absent.
4. **Update documentation** — remove drift-window references from docstrings, CLAUDE.md Mission Identity Model section, and any operator-facing docs.
5. **Define closure procedure** — checklist for closing #557 after the shim is retired.

### Out of Scope (Non-Goals)

- Re-opening the already-landed full repository identity sweep (mission creation, backfill, merge-state keying, selector migration).
- Modifying the `mission_slug` field itself — it remains as a human-readable display field.
- Any changes to the SaaS codebase (tracked separately in `spec-kitty-saas#66`).
- Bundling unrelated Sonar, auth, or workflow cleanup.
- Re-opening or resurrecting closed issue #543.
- Removing legacy event *read* tolerance — the reducer must still deserialize old events that lack `mission_id` (those events exist on disk in real projects).

## Actors

- **CLI maintainer**: performs the shim removal and verifies the final contract.
- **SaaS team**: confirms drift-window closure readiness (external dependency, not a deliverable of this mission).

## User Scenarios & Testing

### Scenario 1: New status events after shim removal

**Given** the `legacy_aggregate_id` shim has been removed,
**When** `emit_status_transition()` writes a new event to `status.events.jsonl`,
**Then** the serialized event contains `mission_id` (ULID) and `mission_slug` (human display) but does **not** contain `legacy_aggregate_id`.

### Scenario 2: Sync emitter uses mission_id as aggregate identity

**Given** `mission_id` is mandatory on all emit methods,
**When** `emit_mission_created()`, `emit_mission_closed()`, or `emit_mission_origin_bound()` is called,
**Then** `aggregate_id` in the emitted envelope is always the ULID `mission_id`, never the slug.

### Scenario 3: Legacy event deserialization is preserved

**Given** a `status.events.jsonl` file contains events written before the identity migration (no `mission_id` field),
**When** the reducer processes those events,
**Then** they deserialize without error, with `mission_id = None`, and the snapshot reflects correct lane state.

### Scenario 4: Contract matrix reflects final wire format

**Given** the identity contract matrix tests run after shim removal,
**When** a `wp_status_event` contract surface is inspected,
**Then** `identity_locations` includes `mission_id` and `mission_slug` but not `legacy_aggregate_id`.

## Functional Requirements

| ID | Requirement | Status |
|----|-------------|--------|
| FR-001 | `StatusEvent.to_dict()` must stop emitting `legacy_aggregate_id` when `mission_id` is present | Proposed |
| FR-002 | `emit_mission_created()` must require `mission_id` as a mandatory parameter (not `Optional`) and always use it as the `aggregate_id` | Proposed |
| FR-003 | `emit_mission_closed()` must require `mission_id` as a mandatory parameter and always use it as the `aggregate_id` | Proposed |
| FR-004 | `emit_mission_origin_bound()` must require `mission_id` as a mandatory parameter and always use it as the `aggregate_id` | Proposed |
| FR-005 | The reducer must continue to deserialize legacy events that lack `mission_id` without error | Proposed |
| FR-006 | Tests asserting `legacy_aggregate_id` presence (T025, T027, T028) must be replaced with tests asserting its absence | Proposed |
| FR-007 | Contract matrix `identity_locations` for `wp_status_event` must be updated to exclude `legacy_aggregate_id` | Proposed |
| FR-008 | Docstrings and inline comments referencing the drift window must be updated to reflect the final contract state | Proposed |

## Non-Functional Requirements

| ID | Requirement | Status |
|----|-------------|--------|
| NFR-001 | All existing tests pass after shim removal (zero regressions, 100% pass rate) | Proposed |
| NFR-002 | No new runtime dependencies introduced | Proposed |

## Constraints

| ID | Constraint | Status |
|------|------------|--------|
| C-001 | This mission must not begin implementation until `Priivacy-ai/spec-kitty-saas#66` is confirmed complete and drift-window closure readiness is verified | Active |
| C-002 | Legacy event deserialization (events written before the identity migration) must remain functional — read tolerance is not removed | Active |
| C-003 | `mission_slug` remains as a human-display field in events and payloads; only the compatibility shim and fallback logic are removed | Active |

## Dependencies

| Dependency | Type | Status | Notes |
|------------|------|--------|-------|
| [spec-kitty-saas#66](https://github.com/Priivacy-ai/spec-kitty-saas/issues/66) | External blocker | Open | SaaS must complete read-switch to `mission_id` before CLI shim removal |

## Assumptions

- All call sites that invoke `emit_mission_created`, `emit_mission_closed`, and `emit_mission_origin_bound` already pass `mission_id`. The parameter change from optional to mandatory will not break any active code path.
- No third-party consumers outside the spec-kitty CLI and SaaS depend on `legacy_aggregate_id`.
- The SaaS team will provide an explicit "drift-window ready to close" signal (e.g., comment on #557 or closure of saas#66).

## Success Criteria

1. The string `legacy_aggregate_id` does not appear in any production source file under `src/specify_cli/`.
2. All sync emitter methods require `mission_id` as a mandatory parameter with no fallback to `mission_slug` for aggregate identity.
3. The full test suite passes with zero regressions.
4. GitHub issue #557 is closeable — all closure criteria from the issue body are met.

## Close-Out Checklist for Issue #557

After all work packages in this mission are merged:

- [ ] `spec-kitty-saas#66` is closed (SaaS read-switch complete)
- [ ] `legacy_aggregate_id` is absent from `src/specify_cli/`
- [ ] `effective_aggregate_id` slug fallback is absent from sync emitter
- [ ] Tests assert the *absence* of the removed shim, not its presence
- [ ] CLAUDE.md Mission Identity Model section updated (no drift-window references)
- [ ] Operator docs updated if any reference the drift window
- [ ] Version bump (patch) reflects the cleanup
- [ ] PR merged, CI green
- [ ] Close #557 with a comment linking the merged PR
