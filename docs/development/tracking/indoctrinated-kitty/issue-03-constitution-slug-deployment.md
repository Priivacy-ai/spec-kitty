# Tracking Issue 03: Constitution Slug Deployment

Status: OPEN
Owner: spec-kitty team
Created: 2026-02-18

## Problem

Doctrine artifacts are canonical in `src/doctrine/`, but deployed per-project references under `.kittify/constitution/<category>/<slug>/` are not fully tracked as a first-class initiative milestone.

## Desired Behavior

After constitution sync/resolution, active doctrine artifacts are materialized in repository-local slug directories with a reference index used by runtime tooling and agents.
Runtime consumers load those deployed references on demand by role and task context, rather than eagerly loading the full doctrine graph.
All doctrine guidance reads happen through a command wrapper layer that can emit structured access events to the existing `EventStore`.
That wrapper is the mandatory runtime entry point for doctrine lookup/load operations.

## Acceptance Criteria

1. Active directives/tactics/templates are materialized under `.kittify/constitution/<category>/<slug>/`.
2. A machine-readable reference index (for example `doctrine.refs.yaml`) links IDs to deployed local paths.
3. Deployment is deterministic and idempotent for unchanged constitution selections.
4. Missing selected artifacts fail with actionable diagnostics (no silent skips).
5. Runtime lookup supports lazy retrieval by role/task so agents pull only context-relevant doctrine artifacts.
6. Doctrine read operations are wrapped by a command-layer interface that records lookup/access telemetry in `EventStore` (including role, task context, requested artifact IDs, and resolution result).
7. Wrapper event emission covers request, resolution, and failure paths so doctrine access can be traced end-to-end.

## Notes

- Source anchor: `references/2026-02-17-doctrine-v2-final-proposal.md` (constitution-centric execution rule).
- Source anchor: ADR consequence calling out migration from mission-embedded behavior text.
- Implementation anchor: `src/specify_cli/events/store.py` (existing EventStore integration point).
