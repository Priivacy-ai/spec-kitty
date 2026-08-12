# Quickstart: doctrine schema diagrams & docs curation

## Add a doctrine-artefact schema diagram

1. Find the frozen model (source of truth), e.g. `src/doctrine/agent_profiles/schema_models.py:AgentProfileSchema`.
2. In the target doctrine page (`docs/architecture/doctrine-kinds.md` etc.), author a `@startyaml` typed-placeholder block whose keys/structure mirror the model's fields, values are type/constraint placeholders, and required fields are `#highlight`-ed:
   ```
   @startyaml
   #highlight "profile-id"
   profile-id: "str (required, unique)"
   roles: ["<role>", "..."]
   routing-priority: int
   context-sources:
     doctrine-layers: ["<layer>"]
   @endyaml
   ```
3. Bind it to its model for the drift guard (comment marker `<!-- model: <path>:<Symbol> -->`).
4. Run the drift guard: `PWHEADLESS=1 python -m pytest tests/docs/test_doctrine_diagram_drift.py -q`.

## Render diagrams locally (build-time)

- The docsite build (CI) runs `scripts/docs/plantuml_render.py` after DocFX, replacing `@start*` blocks with SVGs from a pinned local `plantuml.jar` (SANDBOX; no network).
- Locally, run the same script against a built `docs/_site` to preview.

## Retire a plan cluster

1. Confirm shipped/distilled evidence (`gh issue view <n>` or an open-core-plan citation).
2. Flip `doc_status` to `superseded`/`closeout` (RECORD-tier) or move the cluster to archive; never delete.
3. Update `docs/plans/index.md`; keep `3-2-x-milestone-roadmap.md` untouched (deferred, C-001).

## Migrate a domain plan into domains/

- Follow `occurrence_map.yaml`: move the file, update every reference (index, release docs, §6 cross-refs), regenerate the docs lockfiles, and confirm zero dead links via the relative-link-fixer test.

## Gates before commit

`PWHEADLESS=1 python -m pytest tests/docs/ tests/architectural/test_no_legacy_terminology.py -q` and the doc-freshness check must be green.
