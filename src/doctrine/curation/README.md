# Governance Curation

This directory is the pull-based curation entry point for external practices.

## Intent

Capture useful external approaches, tactics, and related doctrine ideas, then
adapt and integrate them into Spec Kitty doctrine so agentic workflows can use
validated, project-aligned guidance.

## Process

1. Register the external source in `imports/<source-id>/manifest.yaml`.
2. Create one candidate file per imported concept in `imports/<source-id>/candidates/*.import.yaml`.
3. Capture provenance in candidate `source` fields (title, type, publisher, URL/path, accessed date).
4. Add `source_references` with traceable local citations (`path`, `lines`, `note`) to support later DRY extraction.
5. Add `external_references` for attribution when needed. Mark these as attribution-only (`extraction_action: none`) because they do not drive doctrine extraction directly.
6. Classify each candidate to doctrine targets (`tactic`, `directive`, etc.) and document rationale.
7. Record adaptation notes that translate source language into Spec Kitty terminology and constraints.
8. Curate the concept into doctrine artifacts (for example `src/doctrine/tactics/*.tactic.yaml`).
9. Update related directives to link curated tactics (for example `tactic_refs` in `TEST_FIRST`).
10. Mark candidate status through review to `adopted`, and ensure `resulting_artifacts` points to created doctrine files.
11. Re-run schema and curation validation to confirm the import is machine-valid.

## Candidate Template

Use `src/doctrine/curation/import-candidate.template.yaml` as the canonical scaffold for new candidates.

## Example Journey: ZOMBIES TDD

A lead developer reads about ZOMBIES TDD and wants implementation agents to use
it by default.

1. Add a candidate under `imports/<source>/candidates/`.
2. Classify to one or more doctrine concepts (for example `tactic`).
3. Add adaptation notes (terminology + constraints).
4. Add source references for every extracted idea.
5. Mark candidate `adopted` after review.
6. Add resulting artifact links (for example `src/doctrine/tactics/...`).

Adoption without resulting artifact links is invalid.
