# Tracking Issue 08: Deterministic Quality Gates for Agentic Workflows

Status: OPEN
Owner: spec-kitty team
Created: 2026-02-18

## Problem

Without standardized deterministic gates, agents and maintainers detect many compliance issues too late (review/CI), causing avoidable rework and drift.

## Desired Behavior

Quality gates are enforced at the cheapest checkpoints:
- file change scope (changed/staged markdown checks),
- commit time (commit message and staged-content policy),
- shared CI gates (range-based checks).

The same model should be reusable across projects through doctrine templates and mission guidance.

## Acceptance Criteria

1. Hook templates include pre-commit and commit-msg checks that enforce markdown style and commit conventions.
2. CI enforces commit-message linting and markdown checks on changed files for pull requests and push ranges.
3. Gate definitions and rule configuration are repository-canonical and discoverable.
4. Failure diagnostics are actionable so agents can remediate deterministically.
5. Doctrine governance tracking explicitly captures this pattern as a reusable cross-project capability.

## Notes

- Source anchor: `architecture/adrs/2026-02-18-1-standardized-automated-quality-gates-for-agentic-development.md`.
- Runtime alignment goal: maximize early issue capture to reduce expensive downstream rework.
