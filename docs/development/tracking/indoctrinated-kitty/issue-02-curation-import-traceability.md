# Tracking Issue 02: Curation Import Traceability

Status: OPEN
Owner: spec-kitty team
Created: 2026-02-18

## Problem

Doctrine curation candidates exist and are already marked adopted, but initiative-level tracking of provenance and adoption consistency is not centralized.

## Desired Behavior

Every adopted import candidate keeps explicit source provenance, adaptation rationale, and resulting doctrine artifact links, with schema validation as a gate.

## Acceptance Criteria

1. All `status: adopted` candidates in `src/doctrine/curation/imports/*/candidates/*.import.yaml` include non-empty `resulting_artifacts`.
2. Candidate IDs are mapped in this tracker for visibility:
   - `imp-zombies-tdd-001`
   - `imp-quickstart-atdd-016`
   - `imp-quickstart-tdd-017`
3. Each mapped candidate references at least one canonical doctrine artifact under `src/doctrine/`.
4. CI/test validation for curation schema remains green.

## Notes

- Source anchor: `src/doctrine/curation/README.md` process steps 1-9.
