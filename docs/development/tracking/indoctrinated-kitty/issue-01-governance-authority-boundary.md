# Tracking Issue 01: Governance Authority Boundary

Status: OPEN
Owner: spec-kitty team
Created: 2026-02-18

## Problem

The ADR defines a constitution-centric model, but legacy mission/config content still contains embedded behavioral rules. This weakens the authority boundary between orchestration (`Mission`) and governance (`Constitution` + doctrine artifacts).

## Desired Behavior

Mission artifacts remain orchestration-only (states, transitions, guards, required outputs). Governance activation is resolved through constitution selections.

## Acceptance Criteria

1. Mission files do not introduce new embedded governance rules that duplicate directives/tactics.
2. Constitution selection fields (`selected_paradigms`, `selected_directives`, `selected_agent_profiles`, `available_tools`, `template_set`) are the source of active governance selection.
3. Runtime checks fail clearly when constitution references unknown profiles/tools.
4. Architecture references remain aligned with ADR confirmations in `2026-02-17-1-explicit-governance-layer-model.md`.

## Notes

- Source anchor: ADR confirmation section (mission/orchestration boundary, constitution authority).
