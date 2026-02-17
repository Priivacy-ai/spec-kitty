# Canonical `spec-kitty next` Command for Agent Execution Loop

**Filename:** `2026-02-17-1-canonical-next-command-runtime-loop.md`

**Status:** Proposed

**Date:** 2026-02-17

**Deciders:** CLI Team, Architecture Team

**Technical Story:** Replace command-selection burden on agents with one deterministic runtime loop entrypoint.

---

## Context and Problem Statement

Current agent workflow execution requires selecting command-specific entrypoints (for example `agent workflow implement` and `agent workflow review`). This increases agent-side branching logic and creates inconsistent next-step behavior.

The product direction requires that agents repeatedly call one command (`next`) and receive complete prompt + context for the next action.

## Decision Drivers

1. Deterministic execution loop for LLM agents.
2. Reduced command-selection cognitive load.
3. Unified behavior across missions and runtimes.
4. Compatibility with local-first operation.

## Considered Options

1. Keep command-specific entrypoints only.
2. Add `spec-kitty next` as canonical loop command (chosen).
3. Delegate step selection to SaaS only.

## Decision Outcome

**Chosen option:** Add top-level `spec-kitty next --agent <name>` as the canonical mission loop command.

### Command Contract

1. `--agent` is required.
2. Default behavior auto-completes previously issued step as success unless `--result` override is supplied.
3. Output includes both machine JSON decision payload and human-readable prompt text.
4. Decision kinds: `step`, `decision_required`, `blocked`, `terminal`.
5. `next` planning for an active run uses the frozen mission template captured at run start (not live mission file edits).
6. If template drift is detected during active run, `next` MUST return `blocked` with migration-required reason.

### Consequences

#### Positive

1. Single command for agent execution loop.
2. Deterministic UX across mission types.
3. Easier integration with diverse agent runtimes.

#### Negative

1. Migration effort from legacy `agent workflow` command family.
2. Need compatibility bridge and deprecation messaging.

#### Neutral

1. Legacy commands remain available during migration window.

## Rollout Notes

1. Runtime integration is gated on `spec-kitty-events` mission-next contract publication.
2. Do not ship CLI-side local-only mission-next event names.
3. Implement compatibility bridge from `agent workflow` to runtime-backed planning semantics.
4. Emit telemetry during migration to quantify legacy command usage.
5. Deprecate legacy flow after adoption threshold is met.

## Known Limitations (Locked In)

As of **2026-02-17**, some mission mappings/templates for `spec-kitty next` are intentionally incomplete and may return `blocked` or `terminal` before a full loop.

1. `plan` mission initial state/action mapping gap.
2. `documentation` mission state-machine/template parity gap for `next`.

These are accepted short-term constraints and MUST remain explicitly tracked via:

1. Per-mission tracking docs:
   `docs/development/tracking/next-mission-mappings/issue-plan-mission-next-mapping.md`
   `docs/development/tracking/next-mission-mappings/issue-documentation-mission-next-mapping.md`
2. `xfail(strict=True)` integration tests that express desired behavior and fail loudly on accidental drift/partial fixes.

When either mission is implemented end-to-end, the corresponding tracking doc MUST be updated to closed and the `xfail` test MUST be converted to a normal passing test in the same PR.
