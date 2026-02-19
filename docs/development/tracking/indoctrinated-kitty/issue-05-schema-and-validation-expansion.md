# Tracking Issue 05: Schema and Validation Expansion

Status: OPEN
Owner: spec-kitty team
Created: 2026-02-18

## Problem

Current doctrine schema coverage is strong for core artifacts, but the idea proposals call for broader contracts (notably paradigm and template-set level) and stronger cross-artifact integrity checks.

## Desired Behavior

Schema coverage and CI validation scale with doctrine model growth so malformed or inconsistent governance assets fail before runtime.

## Acceptance Criteria

1. Schema coverage explicitly includes paradigm/template-set contracts when introduced.
2. Cross-artifact checks verify referential integrity:
- directive -> tactic refs
- constitution selection -> available doctrine artifacts
- adopted import candidate -> resulting artifacts
3. Validation errors include actionable path-level diagnostics.
4. Tracker issue can only close when tests cover one valid and one invalid fixture for each newly introduced artifact type.

## Notes

- Source anchor: ADR driver for early validation.
- Source anchor: `references/2026-02-17-doctrine-folder-schema-proposal.md` schema expansion proposal.
