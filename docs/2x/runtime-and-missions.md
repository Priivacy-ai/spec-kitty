# 2.x Runtime and Missions

## Canonical Agent Loop

2.x treats `spec-kitty next --agent <name>` as the canonical loop entrypoint for agent execution.

ADR reference:

1. `architecture/adrs/2026-02-17-1-canonical-next-command-runtime-loop.md`

## Mission Discovery Ownership

Mission discovery and loading are runtime-owned and resolved through explicit precedence rather than duplicated ad hoc loaders.

ADR and implementation references:

1. `architecture/adrs/2026-02-17-2-runtime-owned-mission-discovery-loading.md`
2. `src/specify_cli/runtime/home.py`
3. `src/specify_cli/runtime/resolver.py`

## Mission Assets

Packaged mission defaults for 2.x live under doctrine:

1. `src/doctrine/missions/software-dev/`
2. `src/doctrine/missions/plan/`
3. `src/doctrine/missions/research/`
4. `src/doctrine/missions/documentation/`

## Status/Event Model Alignment

2.x status behavior is event-driven with canonical transition semantics and reducer materialization.

ADR references:

1. `architecture/adrs/2026-02-09-1-canonical-wp-status-model.md`
2. `architecture/adrs/2026-02-09-2-wp-lifecycle-state-machine.md`
3. `architecture/adrs/2026-02-09-3-event-log-merge-semantics.md`
4. `architecture/adrs/2026-02-09-4-cross-repo-evidence-completion.md`
