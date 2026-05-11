# Research: TeamSpace Mission-State Repair Coordination

## Repair Scope

**Decision**: Repair `spec-kitty`, `spec-kitty-saas`, `spec-kitty-events`. Evaluate `spec-kitty-runtime` after Mission 2 audit.
**Rationale**: These three repos were identified in the #920 survey as containing the bulk of legacy status rows (2772 `feature_slug`, 1624 `work_package_id`, 424 `legacy_aggregate_id`). Runtime's open issue (#17) is about side-log classification, which PR #19 already addressed; runtime repair is unlikely needed.
**Alternatives considered**: Including runtime upfront — rejected because it adds scope risk without evidence of blockers.

## PR #1017 Gate

**Decision**: Gate cleared. PR #1017 ("Close mission-state migration readiness gaps") merged 2026-05-11T09:40:29Z.
**Rationale**: PR #1017 tightens `spec-kitty-events>=5.0.0`, blocks legacy-shaped sync batches, and adds dry-run audit blocker behavior. Running `--fix` before this merge would produce incomplete repair.
**Alternatives considered**: Proceeding without #1017 — rejected per start-here.md WP01 constraint.

## Branch Strategy Per Repo

**Decision**: Each repo gets a `repair/teamspace-mission-state-history` branch targeting `main`.
**Rationale**: The repair is a standalone data migration commit — it must not be mixed with implementation changes. A dedicated branch name makes it easy to identify in git history.
**Alternatives considered**: Committing directly to main — rejected (no review step).

## spec-kitty-runtime Inclusion Criterion

**Decision**: Include runtime only if `missions_with_teamspace_blockers > 0` in its baseline audit.
**Rationale**: Runtime's status history is primarily about side logs (`run.events.jsonl`), which PR #19 classified as `local_only_side_log`. These should not produce TeamSpace blockers. Including runtime unconditionally adds scope without expected benefit.
**Alternatives considered**: Always include runtime — rejected to keep repair scope minimal.

## SPEC_KITTY_ENABLE_SAAS_SYNC=1 Requirement

**Decision**: Set this env var for all `doctor mission-state` commands that touch dry-run or TeamSpace validation on this machine.
**Rationale**: start-here.md explicitly requires it for SaaS/sync/TeamSpace behavior on this machine.
**Alternatives considered**: Running without the flag — rejected; may produce incomplete or incorrect dry-run output.
