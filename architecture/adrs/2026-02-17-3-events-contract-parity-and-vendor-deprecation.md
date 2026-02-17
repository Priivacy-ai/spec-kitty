# Events Contract Parity and Vendored Module Deprecation

**Filename:** `2026-02-17-3-events-contract-parity-and-vendor-deprecation.md`

**Status:** Proposed

**Date:** 2026-02-17

**Deciders:** Architecture Team, CLI Team, SaaS Team, Events Team

**Technical Story:** Resolve contradictory state where CLI depends on external `spec-kitty-events` while still carrying vendored event code.

---

## Context and Problem Statement

Spec Kitty currently contains a vendored events module while also depending on external `spec-kitty-events`. This creates risk of contract drift and ambiguous authority for envelope/reducer semantics.

Additionally, consumer version pins are currently inconsistent across repositories.

## Decision

1. `spec-kitty-events` is the sole contract authority.
2. CLI and SaaS MUST pin the same exact `spec-kitty-events` version.
3. Vendored event module in CLI is deprecated and scheduled for removal after migration gates pass.
4. CI parity checks are required to prevent version drift.

## Decision Drivers

1. Deterministic cross-repo replay.
2. Single source of truth for event contracts.
3. Reduced semantic ambiguity during incident/debug workflows.
4. Better release discipline across repositories.

## Consequences

### Positive

1. Replay/projection parity becomes enforceable.
2. Event contract evolution is explicit and auditable.
3. Lower chance of hidden drift bugs.

### Negative

1. Requires coordinated release cadence and contract-bump workflow.
2. Migration work to remove vendored compatibility layer.

### Neutral

1. Temporary compatibility shims may be needed during transition.

## Enforcement

1. Add CI checks for exact version parity in consumers.
2. Add CI checks rejecting vendored-only contract extensions.
3. Document contract-bump process in release notes.
