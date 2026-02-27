# CLI Tracker Surface Gated by SaaS Sync Flag

**Filename:** `2026-02-27-1-cli-tracker-surface-gated-by-saas-sync-flag.md`

**Status:** Accepted

**Date:** 2026-02-27

**Deciders:** CLI Team, Platform Team, Product

**Technical Story:** Tracker command rollout must respect the existing SaaS sync feature gate and remain invisible when disabled.

---

## Context and Problem Statement

SpecKitty already uses `SPEC_KITTY_ENABLE_SAAS_SYNC` as the rollout boundary for SaaS-synced functionality. Introducing tracker commands outside this boundary creates policy drift, user confusion, and inconsistent behavior between installations.

The tracker integration introduces new CLI commands (`spec-kitty tracker ...`) and sync orchestration paths. Without strict gating, users with SaaS sync disabled could still discover partially functional tracker behavior.

## Decision Drivers

1. Preserve existing feature-flag contract for SaaS-dependent capabilities.
2. Avoid fragmented UX where command help exposes disabled products.
3. Ensure deterministic behavior in environments where SaaS sync is intentionally off.
4. Minimize operational/support burden from accidental partial enablement.

## Considered Options

1. Always register tracker commands and show runtime warnings.
2. Gate only mutating commands, keep read-only commands visible.
3. Register tracker command group only when SaaS sync flag is enabled (chosen).

## Decision Outcome

**Chosen option:** register tracker commands only when `SPEC_KITTY_ENABLE_SAAS_SYNC` is enabled, and hard-fail through legacy/direct paths with existing disabled-message semantics.

### Required Behavior

1. `tracker` command group is not registered when flag is disabled.
2. Any direct/legacy invocation path uses the same disabled response pattern as sync/auth command guards.
3. No background tracker sync hooks run when flag is disabled.

### Consequences

#### Positive

1. Feature rollout remains consistent with established policy.
2. Help surface accurately reflects usable command set.
3. Lower risk of unsupported local states.

#### Negative

1. Teams wanting tracker-only local mode must enable SaaS sync flag in v1.
2. Additional guard-path tests are required.

#### Neutral

1. Future decoupling from SaaS flag remains possible but is explicitly deferred.

### Confirmation

This decision is validated when:

1. `spec-kitty --help` excludes tracker commands when flag is off.
2. `spec-kitty --help` includes tracker commands when flag is on.
3. Direct invocation while disabled returns standard disabled guidance.

## Pros and Cons of the Options

### Option 1: Always register + runtime warnings

**Pros:**

1. Easier command discoverability during development.

**Cons:**

1. Violates established gate model.
2. Increases accidental usage/support overhead.

### Option 2: Partially gate command set

**Pros:**

1. Offers limited read-only visibility.

**Cons:**

1. Blurry policy boundary.
2. Inconsistent user expectations.

### Option 3: Full command registration gating (Chosen)

**Pros:**

1. Clear binary rollout behavior.
2. Aligns with existing sync/auth guard patterns.

**Cons:**

1. Defers tracker-only mode experimentation.

## More Information

1. CLI command registration:
   `src/specify_cli/cli/commands/__init__.py`
2. Tracker command module:
   `src/specify_cli/cli/commands/tracker.py`
3. Flag guard helper:
   `src/specify_cli/tracker/feature_flags.py`
