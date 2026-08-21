# Contract: spec-kitty-tracker Consumer Surface

**Mission**: `shared-package-boundary-cutover-01KQ22DS`
**Upstream contract**: `spec-kitty-tracker` mission `tracker-pypi-sdk-independence-hardening-01KQ1ZKK` (in implement-review at the time this plan is written; rebase before WP07 lands).
**CLI version range**: `spec-kitty-tracker>=0.4,<0.5`

This contract pins the **subset** of the tracker public surface the CLI
actually imports post-cutover. The consumer test at
`tests/contract/spec_kitty_tracker_consumer/test_consumer_contract.py` asserts
each pinned symbol exists at the documented import path with the shape CLI
relies on.

Tracker's public-surface doc is finalized by the upstream mission. Until that
mission merges, this contract pins what the currently-published `0.4.2` SDK
exposes; WP07 rebases this contract against the upstream mission's published
public-surface doc when that mission lands.

---

## Pinned imports

### Top-level package surface

| Import | Used by |
|--------|---------|
| `from spec_kitty_tracker import FieldOwner` | `src/specify_cli/tracker/local_service.py` |
| `from spec_kitty_tracker import OwnershipMode` | `src/specify_cli/tracker/local_service.py` |
| `from spec_kitty_tracker import OwnershipPolicy` | `src/specify_cli/tracker/local_service.py` |
| `from spec_kitty_tracker import SyncEngine` | `src/specify_cli/tracker/local_service.py` |
| `from spec_kitty_tracker import ...` (factory entry points used by `src/specify_cli/tracker/factory.py`) | `src/specify_cli/tracker/factory.py` |

### `spec_kitty_tracker.models`

| Import | Used by |
|--------|---------|
| `from spec_kitty_tracker.models import ExternalRef` | `src/specify_cli/tracker/local_service.py` (line 168) |
| `from spec_kitty_tracker.models import ...` (the model classes used by `src/specify_cli/tracker/store.py` line 29 — confirmed during WP07) | `src/specify_cli/tracker/store.py` |

(The exact factory and model symbol names are captured by enumerating the
existing CLI tracker import sites during WP07; the contract module is
generated from that enumeration so the tests stay in sync.)

---

## Consumer-test assertions

For each import above, the consumer test:

1. `import` statement succeeds against the installed tracker package.
2. Callable symbols have the parameter names CLI passes (verified via
   `inspect.signature`).
3. Class symbols expose the attributes CLI reads (verified via `hasattr`).
4. Enum-like symbols (e.g. `OwnershipMode`) expose the enum members CLI reads.

The consumer test is a shape test, not a behavior test.

---

## SemVer interaction

The CLI's `>=0.4,<0.5` range is a conservative window pending the upstream
SDK independence mission's published SemVer policy. WP08 documents the
agreed range; WP07's consumer test ensures upstream contract changes break
CLI explicitly.

When the upstream mission publishes a `1.0` line with a finalized
SemVer policy, this CLI mission's compatibility range is bumped to follow it
(typically `>=1.0,<2.0`).

---

## Forward-looking pins (TRK-M1-04, version-gated)

`specify_cli/tracker/gateway.py` (the local Beads program gateway,
`TRK-M1-04`) additionally consumes `spec_kitty_tracker.context.LocalExecutionContext`
and the `context=`/`runner=` kwargs of `BeadsConnectorConfig`/`BeadsConnector` —
landed by the upstream TRK-M1-02/03 kernel (`0.5.x`) but not yet published to
PyPI as of this document. Every use of these symbols in `gateway.py` is
deferred into function bodies and gated by a local capability check
(`_try_import_gateway_beads_types`), so `gateway.py` imports cleanly and its
token/scope/deny-list logic works regardless of the installed tracker
version; only `build_gateway_beads_connector` needs the real symbols, and it
raises a typed `TrackerGatewayUnavailableError` rather than an unguarded
`ImportError` when they are absent.

The consumer test's `test_local_execution_context_class_exists` and
`test_beads_connector_config_accepts_context_and_beads_connector_accepts_runner`
assert this surface, skipping (not failing) when it isn't present yet. The
CLI version range stays `>=0.4,<0.5` (unchanged) until a published
`spec-kitty-tracker` release actually satisfies it; bumping the pin is a
separate, later change.

## Out of scope

- This contract does not enumerate the full tracker SDK surface.
- This contract does not assert tracker network protocol behavior, server
  contracts, or remote tracker semantics — those are upstream's tests.
- This contract does not test the CLI-internal `specify_cli.tracker.*`
  adapters; their unit tests live under `tests/specify_cli/tracker/`.

---

## Boundary invariant

CLI MUST consume tracker only via `spec_kitty_tracker.*`. The CLI-internal
`specify_cli.tracker.*` adapters MAY remain (they own CLI-side concerns: lock
management, fixture handling, local-service shims), but they MUST NOT
re-export tracker public symbols under a `specify_cli.tracker.*` namespace.
The architectural test at `tests/architectural/test_shared_package_boundary.py`
enforces this by inspecting the public exports of `specify_cli.tracker`.
