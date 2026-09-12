# Research: Charter Code Topology (M2) — brownfield seam synthesis

3-scout opus brownfield squad (two-module split, import/build closure, serialized surfaces). All file:line.

## Seam 1 — Two-module split + collision (architect)
- **Partition**: all `src/doctrine/**` (96 py) → `src/charter/offering/`; `activation/` from current `src/charter` activation code. Name-trap: `doctrine/spdd_reasons/activation.py` → offering (read-only predicate).
- **Collision**: 5 collapse (`pack_paths` `charter/pack_paths.py:22`, `provenance` `:24`, `template_catalog` `:22`, `versioning` `:11`, `primitives` `charter/primitives.py:10` — all pure re-exports → top-level `charter.*` CR-06 shims); 4 relocate-both-distinct (`resolver`/`DoctrineService` `doctrine/service.py:22` vs `charter/resolver.py:147`; `exceptions`; `errors`; `Directive` `doctrine/directives/models.py:51` vs `charter/schemas.py:237` — NEVER merge); `canonical_yaml` de-dup fold (`doctrine/yaml_utils.py:24` SSOT vs `charter/synthesizer/synthesize_pipeline.py:157` duplicate).
- **Edges**: 0 offering→activation to sever (boundary holds by construction). Gate copies `tests/architectural/test_charter_no_specify_cli_import.py` + **level-aware relative-import** resolution. Layer re-home: `conftest.py:89` landscape, `test_layer_rules.py` `_DEFINED_LAYERS`, `test_kernel_no_doctrine_import.py` `_FORBIDDEN_IMPORT_ROOTS` + retarget 2 `kernel/schema_utils.py:88,96` exemptions (never delete).

## Seam 2 — Import/build/wheel closure (architect)
- **EXCLUDE** `specify_cli.doctrine*`/`doctrine_synthesizer`/`org_charter` (separate pkg, 323 imports). Real: 730 `from doctrine.X` rewrites, 7 module-form (CR-06), 53 `src/charter` files/158 edges.
- **13 `files("doctrine")` sites** to retarget first: `doctrine/pack_paths.py:254`, `specify_cli/template/manager.py:89`, `skills/registry.py:59`, `bulk_edit/occurrence_map.py:51`, `charter/catalog.py:168`, 7 upgrade migrations, + `kernel/schema_utils.py:22`, `kernel/sibling_paths.py:45`.
- **Build**: `pyproject.toml:149,152-163,178-186,201-210,488`; `release.yml:210-245`. **R2 wheel silent-drop**: charter artifacts ship only `*.yaml` — widen to `.md/.json/.csv/.template`. Dormant `spec-kitty-doctrine` wheel → **delete** (`src/doctrine/pyproject.toml`+`hatch_build.py`+`tests/doctrine/test_hatch_build.py`+`test_doctrine_wheel_closure.py`).
- **Skills tree**: `src/doctrine/skills/` 55 dirs/83 files (OC-41) = pure `git mv` + `registry.py:44,59-61,67` + artifact glob + `release.yml:226,229`; IDs stay (M4).
- **CR-06 shim**: mechanics `runtime/next/__init__.py:15-28` (`__getattr__`); warn-once `retrospective/deprecation.py`; identity-guard `test_charter_facades_reexport_doctrine.py:30-205`; register `compat/shim-registry.yaml`.

## Seam 3 — Serialized surfaces / CR shims (paula)
Precedent for ALL: CR-01 read-both/canonical-wins/warn-once `src/charter/sync.py:245-311`.
- **CR-02** CLI group: `__init__.py:258,293`, `doctrine.py:60,67,74,81,87`. **`charter mission-type` collision is semantic** — `doctrine mission-type list` (activation-blind) vs `charter mission-type list` (activation-filtered); do NOT straight-alias.
- **CR-03** tracker → **`ownership`** (different target word!): `tracker/config.py:125-126,176-178,192,200-209,251-252`, `tracker.py:422,624-626,699-713,720-721,899`, `saas_service.py:218-219,347-348`. Machine payload = downstream contract.
- **CR-04** `doctrine.org.packs`→`charter_packs.org.packs`: `org_pack_config.py:41,404,427,462-485,~573`. 3rd shape (charter_packs → doctrine.org → legacy organisation_packs).
- **CR-05** URN `doctrine:`→`charter:`: producer `doctrine_synthesizer/apply.py:409,663` ONLY (NOT `drg/merge.py:596`/`models.py:378` — 2-part node URN space). Durable event-log contract: `tests/status/test_validate.py:549`, `tests/retrospective/test_reducer_integration.py:290`. External `spec_kitty_events` fixture = paired change.
- **CR-07** `.kittify/doctrine/`→`.kittify/charter-packs/` dual-root: 42 src files. **Normalize split-literals first**: `_DOCTRINE_BASE` `apply.py:187`, `_DOCTRINE_DIRNAME` `write_pipeline.py:62`+`reconcile.py:67` (no contiguous token — census-invisible).

## Occurrence-map verdict (SC-3)
Per-surface classes with distinct target strings (package/CLI→charter, config/path→charter_packs, tracker→ownership, URN→charter). NEVER key on the bare token. Normalize split-literals before trusting "0 remaining". External fixture tracked as paired change, not swept.
