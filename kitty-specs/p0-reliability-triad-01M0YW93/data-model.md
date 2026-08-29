# Phase 1 Data Model: entities & invariants

These are not new persisted schemas; they are the existing domain objects whose invariants each WP restores.

## Mission-type activation authority (WP01 / #3282)
- **Fields**: project has either a legacy config (`.kittify/config.yaml` holds `mission_type_activations`) or a pointer charter (`config.yaml` has `charter:` → `charter.yaml`, which holds activations).
- **Invariant (restored)**: the effective *write* target for activations MUST equal the effective *read* target resolved by `PackContext.from_config`. For pointer projects that is `charter.yaml`.
- **Preserve**: an explicitly authored empty activation list (`[]`) is intentional and must not be overwritten (additive/idempotent).

## status.json — derived projection (WP02 / #3579)
- **Fields**: `status.json` is a materialized snapshot of the append-only `status.events.jsonl` event log.
- **Invariant**: `status.json` is derived, never hand-reconciled. Recovery = rematerialize from the log (`spec-kitty agent status materialize`), then `git add`.
- **Non-invariant (guarded against)**: `status.json` MUST NOT gain a merge driver — it is in `_NON_DIVERGENT_CANONICAL_ARTIFACTS`.

## Lane worktree + recorded planning commit + dependency tips (WP03 / #3281)
- **Fields**: an execution lane has a materialized worktree (`.worktrees/<slug>-<mid8>-lane-*`), a recorded `planning_commit_sha`, and a set of approved dependency lane tips.
- **Invariant 1 (atomicity)**: allocation is all-or-nothing — a failed planning-commit merge leaves no registered worktree.
- **Invariant 2 (idempotent re-entry)**: re-running allocation over an existing worktree re-runs the planning-commit and dependency-tip merges (self-heal), never short-circuits on bare `.git` presence.
- **Invariant 3 (ancestry gate)**: a WP may reach `claimed` only when its recorded planning SHA and every approved dependency lane tip are git ancestors of workspace HEAD — status-lane approval alone is insufficient.
