# Contract: spec-kitty-events Consumer Surface

**Mission**: `shared-package-boundary-cutover-01KQ22DS`
**Upstream contract**: `spec-kitty-events` mission `events-pypi-contract-hardening-01KQ1ZK7`, merged at sha `81d5ccd4`. Authoritative public surface listed in `spec-kitty-events/docs/public-surface.md`.
**CLI version range**: `spec-kitty-events>=4.0.0,<5.0.0`

This contract pins the **subset** of the events public surface the CLI actually
imports post-cutover. The consumer test at
`tests/contract/spec_kitty_events_consumer/test_consumer_contract.py` asserts:

1. Each pinned symbol exists at the documented import path.
2. Each pinned symbol has the structural shape (callable signature / class
   attributes) the CLI relies on.

Upstream may add new symbols freely (MINOR bump). Upstream removing or
renaming a pinned symbol below MUST be a MAJOR bump and MUST break this
consumer test, forcing the CLI to update before merging.

---

## Pinned imports

### Top-level package surface

| Import | Used by |
|--------|---------|
| `from spec_kitty_events import Event` | `src/specify_cli/sync/diagnose.py`, sync emitter, glossary events |
| `from spec_kitty_events import ErrorEntry` | sync emitter |
| `from spec_kitty_events import ConflictResolution` | sync conflict path |
| `from spec_kitty_events import normalize_event_id` | sync emitter, decisions emit |
| `from spec_kitty_events import LamportClock` | sync emitter |
| `from spec_kitty_events import EventStore` | sync persistence |
| `from spec_kitty_events import InMemoryEventStore` | tests |

### `spec_kitty_events.decisionpoint`

| Import | Used by |
|--------|---------|
| `from spec_kitty_events.decisionpoint import DecisionPointOpened` | `src/specify_cli/decisions/emit.py` |
| `from spec_kitty_events.decisionpoint import DecisionPointResolved` | `src/specify_cli/decisions/emit.py` |
| `from spec_kitty_events.decisionpoint import InterviewPayload` (or current 4.0.0 name) | `src/specify_cli/decisions/emit.py` |

### `spec_kitty_events.decision_moment`

| Import | Used by |
|--------|---------|
| `from spec_kitty_events.decision_moment import DecisionMomentOpened` (or current 4.0.0 name) | `src/specify_cli/decisions/emit.py` |
| `from spec_kitty_events.decision_moment import Widened` | `src/specify_cli/decisions/emit.py` |

### `spec_kitty_events.cutover`

| Import | Used by |
|--------|---------|
| `from spec_kitty_events import CUTOVER_ARTIFACT` | optional cutover-signal validation |
| `from spec_kitty_events import assert_canonical_cutover_signal` | optional cutover-signal validation |

(The exact decisionpoint / decision_moment symbol names are confirmed against
the events package on rebase; the CLI's current `decisions/emit.py` imports
fixed names that may need to be re-checked against the 4.0.0 surface during
WP04.)

---

## Consumer-test assertions

For each import above, the consumer test:

1. `import` statement succeeds against the installed events package.
2. Callable symbols have the parameter names CLI passes (verified via
   `inspect.signature`).
3. Class symbols expose the attributes CLI reads (verified via `hasattr`).
4. Exception symbols are subclasses of `BaseException`.

The consumer test is **not** a behavior test; it is a shape test. Behavior
tests live where the behavior is exercised (in CLI integration tests).

---

## SemVer interaction

Per `spec-kitty-events/docs/public-surface.md`:

- Adding a new symbol to events `__all__` → MINOR bump → CLI's compatibility
  range `<5.0.0` accepts it without action.
- Removing or renaming a pinned symbol → MAJOR bump → CLI's compatibility
  range REJECTS the new release at install time. CI catches the mismatch via
  the consumer test running against a pinned newer version, OR via the
  clean-install verification job failing to install.

This is the entire point of the consumer-test contract: upstream contract
changes break CLI explicitly, never silently.

---

## Out of scope

- This contract does not enumerate the *full* events public surface. Only the
  subset CLI imports.
- This contract does not assert anything about events behavior under load,
  concurrency, or storage backends — those are upstream's tests.
- This contract does not bind future CLI-side imports; new CLI consumers of
  events MUST extend this contract in the same PR that adds the new import.
