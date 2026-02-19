# Governance Curation

This directory is the pull-based curation entry point for external practices.

## Intent

Capture useful external approaches, tactics, and related doctrine ideas, then
adapt and integrate them into Spec Kitty doctrine so agentic workflows can use
validated, project-aligned guidance.

## Process

1. Capture source provenance as an import candidate.
2. Classify the candidate to target doctrine concepts.
3. Record adaptation notes for Spec Kitty terminology and constraints.
4. Move status through review to adoption.
5. Link adopted candidates to resulting doctrine artifacts.

## Example Journey: ZOMBIES TDD

A lead developer reads about ZOMBIES TDD and wants implementation agents to use
it by default.

1. Add a candidate under `imports/<source>/candidates/`.
2. Classify to one or more doctrine concepts (for example `tactic`).
3. Add adaptation notes (terminology + constraints).
4. Mark candidate `adopted` after review.
5. Add resulting artifact links (for example `src/doctrine/tactics/...`).

Adoption without resulting artifact links is invalid.
