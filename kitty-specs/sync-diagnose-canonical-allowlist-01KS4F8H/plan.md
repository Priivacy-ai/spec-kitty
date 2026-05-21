# Implementation Plan — Sync Diagnose Canonical Event-Type Registry

**Branch**: `kitty/mission-sync-diagnose-canonical-allowlist-01KS4F8H`
**Date**: 2026-05-21
**Spec**: [spec.md](spec.md)
**Anchor issue**: [`Priivacy-ai/spec-kitty#1222`](https://github.com/Priivacy-ai/spec-kitty/issues/1222)

## Summary

Replace the stale hardcoded allowlist used by `spec-kitty sync diagnose`
with a recognition set computed from two canonical sources:

1. `spec_kitty_events.conformance.validators._EVENT_TYPE_TO_MODEL` — the
   shared events-package registry (85 entries on 5.1.0), already used
   by `specify_cli/status/lifecycle_events.py:210` and by the SaaS
   `spec-kitty-saas/apps/sync/cutover_contract.py`.
2. `specify_cli.sync.emitter._PAYLOAD_RULES` — local payload-rules
   (26 entries), which include CLI-internal types not in the canonical
   registry (`BuildHeartbeat`, `BuildRegistered`, `DependencyResolved`,
   `ErrorLogged`, `HistoryAdded`, `MissionOriginBound`, `WPAssigned`).

The recognition set is `union(_EVENT_TYPE_TO_MODEL.keys(), _PAYLOAD_RULES.keys())`.
Diagnose's payload validation continues to consult `_PAYLOAD_RULES` and
only fires when payload rules exist for the type — unchanged behaviour.
`emitter.VALID_EVENT_TYPES` (the **outbound** gate) is not touched; it
remains a frozen-set derived from `_PAYLOAD_RULES.keys()` and its
contract test (`tests/sync/test_forward_compatibility.py::TestValidEventTypesOnlyGatesOutgoing`)
keeps passing.

## Technical Context

**Language/Version**: Python 3.11+ (existing spec-kitty codebase).
**Primary Dependencies**: `spec_kitty_events` (already pinned in
`pyproject.toml`; no new dependency); `pydantic` (already a transitive
runtime dependency).
**Storage**: N/A — purely an in-memory recognition set.
**Testing**: `pytest` with the `fast` marker (matches the existing
`tests/sync/test_diagnose.py` convention); existing
`PWHEADLESS=1 pytest tests/sync/test_diagnose.py -v` flow.
**Target Platform**: All platforms supported by the CLI (Linux, macOS,
Windows).
**Project Type**: Single Python project (CLI).
**Performance Goals**: Recognition lookup remains O(1) — the new set
is materialised once at module-import time.
**Constraints**: No new pip dependencies; no behaviour change to
emitter or its outbound gate; diff confined to `diagnose.py` and its
tests.
**Scale/Scope**: ~10-line code change in `diagnose.py`, ~40-line test
additions in `tests/sync/test_diagnose.py`.

## Charter Check

This mission honours the charter precedence rules: doctrine first
(`spec-kitty#1198` says canonical registry is the source of truth for
event-type recognition), code second. We are *concretising* the
doctrine — deleting a local allowlist in favour of a canonical
registry. No charter exemption needed.

## Project Structure

```
kitty-specs/sync-diagnose-canonical-allowlist-01KS4F8H/
├── spec.md
├── plan.md
├── tasks.md
├── tasks/
│   ├── README.md
│   └── WP01.md
├── checklists/
│   └── requirements.md
├── analyze.md           # Phase 4 output
├── renata-review.md     # Phase 5 output
├── mission-review.md    # Phase 7 output
├── meta.json
└── status.events.jsonl
```

## Source-code surface

```
src/specify_cli/sync/
└── diagnose.py          # ONLY file modified in src/

tests/sync/
└── test_diagnose.py     # New regression + drift-detector tests appended
```

## Design

### Recognition set construction

```python
# In src/specify_cli/sync/diagnose.py, top-level constant after imports.

# Canonical registry from spec_kitty_events. We use the private
# _EVENT_TYPE_TO_MODEL because the events package does not expose a
# public alias as of 5.1.0; the same import is already in production
# at src/specify_cli/status/lifecycle_events.py:210 and is the
# documented contract surface used by spec-kitty-saas's
# apps/sync/cutover_contract.py. See spec-kitty#1198 for the
# canonical-registry doctrine.
from spec_kitty_events.conformance.validators import (
    _EVENT_TYPE_TO_MODEL as _CANONICAL_EVENT_TYPE_MODELS,
)

# Diagnose recognises ANY event type the canonical registry models
# (incoming events from the wire, replays, cross-product events) as
# well as CLI-internal types that have local payload rules in the
# emitter (BuildHeartbeat, BuildRegistered, DependencyResolved,
# ErrorLogged, HistoryAdded, MissionOriginBound, WPAssigned).
KNOWN_EVENT_TYPES: frozenset[str] = frozenset(
    set(_CANONICAL_EVENT_TYPE_MODELS.keys()) | set(_PAYLOAD_RULES.keys())
)
```

The recognition check in `_validate_extended_envelope` is then:

```python
etype = event_data.get("event_type")
if etype is not None and etype not in KNOWN_EVENT_TYPES:
    errors.append(
        f"event_type: unknown event type {etype!r}; "
        f"not in canonical registry or local payload rules"
    )
```

Note: the literal `VALID_EVENT_TYPES` import from `emitter` is removed
from `diagnose.py`; only `_PAYLOAD_RULES` and `VALID_AGGREGATE_TYPES`
remain because both are still consumed (payload validation and
aggregate-type recognition respectively).

### Why not modify `emitter.VALID_EVENT_TYPES`?

It is intentionally narrow: `tests/sync/test_forward_compatibility.py::TestValidEventTypesOnlyGatesOutgoing`
locks the exact set of **outbound** types the CLI is permitted to
emit. Widening it would silently expand the CLI's outbound surface to
include events it isn't supposed to emit (e.g. `GatePassed` and
`GateFailed` come *into* the CLI from the SaaS — the CLI never emits
them). The two surfaces (recognition vs. emission gate) are different
contracts; this mission disentangles them.

### Drift detector

A new test injects a synthetic entry into a copy of the canonical
registry via `monkeypatch.setitem` and asserts diagnose recognises it
without any change to `diagnose.py`. This proves the registry is the
genuine source of truth.

## Risks and mitigations

| Risk | Likelihood | Mitigation |
|---|---|---|
| Private-import (`_EVENT_TYPE_TO_MODEL`) breaks in a future events release | Medium | Already in production use at `lifecycle_events.py:210`; if the events package renames, both call sites flip together. Drift-detector test surfaces breakage early. |
| Widening recognition masks malformed envelopes | Low | Envelope validation via the Pydantic `Event` model is unchanged; only the `event_type` membership check is widened. Per-event-type payload validation still only fires for types in `_PAYLOAD_RULES`. |
| Tests in `test_forward_compatibility.py` break because of an unrelated bleed-through | Low | They assert against `emitter.VALID_EVENT_TYPES` which is not modified. Verified by running both test modules. |
| Renata flags scope creep into emitter | Low | The mission explicitly scopes out emitter; the plan documents why; the diff confirms emitter is untouched. |
| Other tools have their own hardcoded allowlist | Existing condition | Out of scope; documented as findings in `mission-review.md` and routed to `spec-kitty#1198` as follow-up. |

## Test strategy

### Existing tests preserved

All of `tests/sync/test_diagnose.py` continues to pass unchanged.
`test_unknown_event_type` continues to verify the rejection path; the
error message wording is widened ("expected one of [...]" becomes "not
in canonical registry or local payload rules"), so the assertion
predicate (`"event_type" in e.lower() or "unknown" in e.lower()`)
still matches.

### New tests (in `tests/sync/test_diagnose.py`)

1. **`TestCanonicalRegistryRecognition.test_recognises_every_registry_type`** — iterates over `_EVENT_TYPE_TO_MODEL.keys()`, constructs a minimal valid envelope for each, asserts the result has no "unknown event type" / `event_type` error. (FR-001)
2. **`TestCanonicalRegistryRecognition.test_recognises_cli_internal_types`** — explicitly asserts that the 7 CLI-internal types not in the canonical registry (`BuildHeartbeat`, `BuildRegistered`, `DependencyResolved`, `ErrorLogged`, `HistoryAdded`, `MissionOriginBound`, `WPAssigned`) are still recognised. (FR-002)
3. **`TestCanonicalRegistryRecognition.test_rejects_genuinely_unknown_type`** — asserts a string in neither set produces a recognition error containing the offending value. (FR-003)
4. **`TestCanonicalRegistryRecognition.test_drift_detector_picks_up_new_registry_entries`** — uses `monkeypatch.setitem` on `_EVENT_TYPE_TO_MODEL` to inject a synthetic event type, then reloads the diagnose constant via the public surface, asserts the new type is recognised — proving the canonical registry is the true source of truth, with no change to `diagnose.py`. (FR-004)

### Test commands

```
PWHEADLESS=1 pytest tests/sync/test_diagnose.py -v
PWHEADLESS=1 pytest tests/sync/test_forward_compatibility.py -v
PWHEADLESS=1 pytest tests/contract/test_handoff_fixtures.py -v
```

All three must pass.

## Complexity tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|---|---|---|
| Importing a `_`-prefixed symbol (`_EVENT_TYPE_TO_MODEL`) | The events package does not expose a public alias as of 5.1.0; the same import is already in production at `status/lifecycle_events.py:210`. | A public alias would require a coordinated change in the events package, out of scope for a CLI bugfix that the Phase 4 canary unblock depends on. |
