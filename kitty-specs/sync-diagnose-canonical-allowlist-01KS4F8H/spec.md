# Spec — Sync Diagnose Canonical Event-Type Registry

**Mission slug**: `sync-diagnose-canonical-allowlist-01KS4F8H`
**Mission id**: `01KS4F8HRBAQMQ5A2GNNA47JJF`
**Anchor issue**: [`Priivacy-ai/spec-kitty#1222`](https://github.com/Priivacy-ai/spec-kitty/issues/1222)
**Program context**: Mission D in the Phase 4 canary unblock for the
Teamspace MVP launch gate (`spec-kitty-end-to-end-testing#41`).
**Related**: structural drift epic [`spec-kitty#1198`](https://github.com/Priivacy-ai/spec-kitty/issues/1198).

## Problem statement

`spec-kitty sync diagnose` validates events in the offline queue using an
allowlist (`VALID_EVENT_TYPES`) derived from `emitter._PAYLOAD_RULES.keys()`
— **26** event types as of `spec_kitty_events 5.1.0`. The canonical
events registry (`spec_kitty_events.conformance.validators._EVENT_TYPE_TO_MODEL`)
exposes **85** event types. Any event type present in the queue but
absent from the local payload-rules dictionary surfaces as
`event_type: unknown event type 'X'; expected one of [...]`.

Concretely, the following common event types are recognised by the
canonical registry **and** materialise into the offline queue, but
diagnose currently reports them as unknown:

`CommentPosted`, `DecisionCaptured`, `DecisionPoint*`,
`GatePassed`, `GateFailed`, `MissionAudit*`, `MissionCancelled`,
`PlanStarted`, `PlanCompleted`, `SpecifyStarted`, `SpecifyCompleted`,
`TasksStarted`, `TasksCompleted`, `RetrospectiveCompleted`,
`ReviewRollback`, `SemanticCheckEvaluated`, `WarningAcknowledged`,
and the `retrospective.*` namespaced variants — among others.

The mismatch is by design at the emitter (`VALID_EVENT_TYPES` is the
**outbound** allowlist — it gates what the CLI is allowed to emit and
the tests `tests/sync/test_forward_compatibility.py` and
`tests/contract/test_handoff_fixtures.py` lock that surface), but it
is **not** by design at the diagnose layer, which is supposed to
recognise *any* canonical event type that could legitimately appear
in the queue regardless of whether the CLI emits it.

The false-positive "unknown event type" noise obscures real causes of
diagnose failures in the Phase 4 canary harness.

## In-scope artifacts

- `src/specify_cli/sync/diagnose.py` — single behavior change.
- `tests/sync/test_diagnose.py` — add regression and drift-detector tests.
- Mission directory under
  `kitty-specs/sync-diagnose-canonical-allowlist-01KS4F8H/`.

## Out of scope

- `emitter.VALID_EVENT_TYPES` and its callers (the outbound gate at
  `emitter.py:1647` and the tests at
  `tests/sync/test_forward_compatibility.py` and
  `tests/contract/test_handoff_fixtures.py`) — these intentionally
  describe the CLI's emitted surface.
- `emitter._PAYLOAD_RULES` — per-event-type payload validation rules
  stay where they are; diagnose continues to consult them for events
  it has rules for.
- Any other tool in the codebase that may have its own hardcoded
  allowlist. Spotted instances will be documented as follow-ups (see
  Findings in `mission-review.md`) — not fixed in this mission. That
  is the doctrine work tracked under `spec-kitty#1198`.
- Adding new payload rules. Recognition ≠ payload validation.
- No new pip dependencies; `spec_kitty_events` is already a runtime
  dependency.

## Functional requirements

| ID | Statement | Verification |
|---|---|---|
| FR-001 | `diagnose_events` recognises every event type exposed by `spec_kitty_events.conformance.validators._EVENT_TYPE_TO_MODEL` without reporting an "unknown event type" error, provided the envelope is otherwise well-formed. | Regression test iterates over `_EVENT_TYPE_TO_MODEL.keys()` and asserts no recognition error for any of them. |
| FR-002 | `diagnose_events` continues to recognise the CLI-internal event types currently in `emitter._PAYLOAD_RULES` that are **not** in the canonical registry (`BuildHeartbeat`, `BuildRegistered`, `DependencyResolved`, `ErrorLogged`, `HistoryAdded`, `MissionOriginBound`, `WPAssigned`). | Regression test asserts each is accepted. |
| FR-003 | `diagnose_events` rejects truly unknown event types (e.g. a string that is in neither set) with a clear error containing the offending value. | Existing `test_unknown_event_type` continues to pass; a new test asserts the error mentions the value. |
| FR-004 | If a future release of `spec_kitty_events` adds a new event type to `_EVENT_TYPE_TO_MODEL`, diagnose recognises it automatically — no code change in this repo. | Drift-detector test mutates a copy of the registry (via `monkeypatch`) to inject a synthetic type and asserts diagnose recognises it without further code edits. |
| FR-005 | The recognition set used by diagnose is a single value (`KNOWN_EVENT_TYPES` or equivalent) computed from the canonical registry ∪ `emitter._PAYLOAD_RULES.keys()`. No duplicate hardcoded list of event-type strings remains in `diagnose.py`. | Source inspection; the only literal event-type strings remaining in `diagnose.py` are inside error messages or docstrings. |
| FR-006 | Existing tests in `tests/sync/test_diagnose.py` continue to pass with no behaviour change for already-recognised types. | `pytest tests/sync/test_diagnose.py -v` is green. |
| FR-007 | `emitter.VALID_EVENT_TYPES` is **unchanged** (same set, same callers). | `tests/sync/test_forward_compatibility.py::TestValidEventTypesOnlyGatesOutgoing` and `tests/contract/test_handoff_fixtures.py` are still green. |

## Non-functional requirements

| ID | Statement |
|---|---|
| NFR-001 | The private-import (`_EVENT_TYPE_TO_MODEL`) is accompanied by a comment explaining (a) why it is used despite the underscore prefix and (b) the precedent already set by `specify_cli/status/lifecycle_events.py`. |
| NFR-002 | No new pip dependencies. `spec_kitty_events` is already declared in `pyproject.toml`. |
| NFR-003 | The diff is confined to `src/specify_cli/sync/diagnose.py`, the new tests, and the mission directory. No template, migration, or documentation edits unrelated to the bug. |
| NFR-004 | Producers in tests construct events via the canonical pydantic models (`spec_kitty_events.lifecycle.*Payload`, etc.) wherever the test exercises payload shape. Recognition tests, which only inspect `event_type`, may use a minimal envelope dict — but those test envelopes still pass the `Event` Pydantic model since `diagnose_events` validates the envelope. |

## Constraints / operating rules

| ID | Statement |
|---|---|
| C-001 | No SaaS DB mutation. |
| C-002 | No new pip dependencies. |
| C-003 | No edits to producers / fixtures outside this mission's scope. |
| C-004 | `unset GITHUB_TOKEN` before any `gh` write to `Priivacy-ai/*`. |
| C-005 | PR against `main`; do not push direct to `main`; `protect-main` will reject. |
| C-006 | The reviewer in implement-review is `reviewer-renata`. |
| C-007 | All event producers (test fixtures included) use canonical `spec_kitty_events.lifecycle` pydantic models when constructing payloads. No hand-rolled payload dicts where a canonical model exists. |

## Acceptance criteria

1. `pytest tests/sync/test_diagnose.py -v` is green, including the new
   regression and drift-detector tests.
2. The recognition error path no longer fires for any event type in
   `_EVENT_TYPE_TO_MODEL`.
3. The recognition error path *does* fire for a string that is in
   neither `_EVENT_TYPE_TO_MODEL` nor `emitter._PAYLOAD_RULES`.
4. `tests/sync/test_forward_compatibility.py` and
   `tests/contract/test_handoff_fixtures.py` are still green
   (FR-007).
5. `git diff main...HEAD` touches only `src/specify_cli/sync/diagnose.py`,
   `tests/sync/test_diagnose.py`, and the mission directory.
6. PR opened against `main` with `Closes Priivacy-ai/spec-kitty#1222`.
7. `mission-review.md` documents whether any other hardcoded event-type
   allowlists were spotted during the work, as follow-ups for
   `spec-kitty#1198`.

## Source of truth

- Canonical registry: `spec_kitty_events.conformance.validators._EVENT_TYPE_TO_MODEL` (5.1.0 → 85 keys).
- Local payload rules: `specify_cli.sync.emitter._PAYLOAD_RULES` (26 keys).
- Outbound emitter gate: `specify_cli.sync.emitter.VALID_EVENT_TYPES`
  (unchanged in this mission).
- Existing precedent for the private-import:
  `specify_cli/status/lifecycle_events.py:210`.
