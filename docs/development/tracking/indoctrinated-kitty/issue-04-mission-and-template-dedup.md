# Tracking Issue 04: Mission and Template De-Duplication

Status: OPEN
Owner: spec-kitty team
Created: 2026-02-18

## Problem

Legacy mission/template content still duplicates behavioral statements that now belong in doctrine directives/tactics/template sets. This risks drift between orchestration text and canonical doctrine assets.

## Desired Behavior

Mission/command/template files keep orchestration and execution flow instructions, while behavior policies point to doctrine artifact references.
Mission-local template ownership is minimized: missions prefer shared doctrine templates, referenced through mission YAML configuration, instead of duplicating template content.

## Acceptance Criteria

1. High-duplication behavioral statements are replaced by doctrine references where canonical artifacts exist.
2. Mission command templates are reviewed for thin-wrapper behavior (no doctrine policy duplication).
3. Any retained inline behavior is explicitly justified as mission-orchestration-only.
4. Updated files include stable reference targets (IDs and/or deployed slug paths).
5. Mission configuration (`mission.yaml`) points to shared template assets when available, and mission-specific template files exist only when they are genuinely mission-unique.

## Notes

- Source anchor: `references/2026-02-17-mission-approach-fit-review.md` findings 1-2 (semantic collision and approach/tactic inconsistency).
- Source anchor: `references/spec-kitty-doctrine-integration-ideation.md` separation statement: structure vs strategy.
