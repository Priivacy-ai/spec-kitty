# Indoctrinated Kitty Initiative Tracker

This directory tracks the initiative to extract governance behavior from legacy Spec Kitty files into doctrine artifacts, then activate those artifacts through constitution-level selection.

Status rules:

1. `OPEN`: scoped and accepted, not started.
2. `IN_PROGRESS`: active implementation.
3. `BLOCKED`: waiting on dependency or decision.
4. `CLOSED`: implementation complete and acceptance criteria verified.

## Source Inputs

1. ADR: `architecture/adrs/2026-02-17-1-explicit-governance-layer-model.md`
2. Curation flow + candidates: `src/doctrine/curation/`
3. Doctrine ideation and fit review:
- `references/2026-02-17-doctrine-v2-final-proposal.md`
- `references/2026-02-17-doctrine-folder-schema-proposal.md`
- `references/2026-02-17-mission-approach-fit-review.md`
- `references/spec-kitty-doctrine-integration-ideation.md`
- `references/domain_concepts.puml`
4. Initiative visual (canonical): `architecture/diagrams/indoctrinated-kitty.png`
5. Ongoing implementation baseline:
- `src/specify_cli/constitution/`
- `src/specify_cli/glossary/`

## Initiative Outcomes

1. Mission definitions are orchestration-first and stop duplicating doctrine behavior text.
2. Doctrine artifacts become the canonical behavioral source (`paradigms`, `directives`, `tactics`, `template sets`, `agent profiles`).
3. Constitution becomes the activation authority for selected doctrine assets.
4. Curation remains pull-based, traceable, and schema-validated.
5. Deployed doctrine references are materialized under `.kittify/constitution/<category>/<slug>/` (for example directives and tactics) with machine-readable index links.
6. Project terminology remains stable and canonical to prevent context drift, reduce misinterpretation, and provide fast concept lookup for `designer`, `implementer`, and `reviewer` agents.
7. Rich Agent Profiles enable project-specific doctrine behavior by bundling preconfigured paradigms, tactics, templates, and directives per role.
8. Missions keep dedicated templates minimal and reference shared doctrine templates through mission YAML configuration wherever possible.
9. Agent behavior resolves doctrine guidance lazily: load only the minimum role/task-relevant artifacts required for execution and compliance.
10. Doctrine guidance reads are routed through a single command-wrapper entry point integrated with `EventStore`, enabling observability for debugging and optimization.

## Tracked Issues

| Issue                                                        | Description                                                                                         | Status |
|--------------------------------------------------------------|-----------------------------------------------------------------------------------------------------|--------|
| [`Issue 01`](issue-01-governance-authority-boundary.md)      | Enforce constitution-first governance authority over mission-level behavior text.                   | OPEN   |
| [`Issue 02`](issue-02-curation-import-traceability.md)       | Keep curation imports traceable from source provenance to adopted doctrine artifacts.               | OPEN   |
| [`Issue 03`](issue-03-constitution-slug-deployment.md)       | Materialize selected doctrine artifacts under `.kittify/constitution/<category>/<slug>/`, with wrapper-based reads and `EventStore` tracing. | OPEN   |
| [`Issue 04`](issue-04-mission-and-template-dedup.md)         | Remove duplicated doctrine behavior from mission/template content and replace with references.      | OPEN   |
| [`Issue 05`](issue-05-schema-and-validation-expansion.md)    | Expand schema and cross-artifact validation coverage for governance assets.                         | OPEN   |
| [`Issue 06`](issue-06-stable-terminology-and-role-lookup.md) | Stabilize terminology and improve fast role-based concept lookup via glossary artifacts.            | OPEN   |
| [`Issue 07`](issue-07-rich-agent-profiles.md)                | Define and operationalize rich agent profiles for role-specific doctrine stack behavior.            | OPEN   |
