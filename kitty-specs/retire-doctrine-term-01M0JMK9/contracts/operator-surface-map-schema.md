# Contract: M2 Internal + Public Topology Map

**Produces**: `canonical-operator-surface-map.md`, `canonical-cli-route-map.md`
**Owner**: M2
**Pre-edit gate**: frozen, exhaustive, collision-resolved

Despite the historical filename, this map owns **all executable/code topology**, not only operator-facing
surfaces. No internal/public distinction removes a hit from M2.

## Required row

Each M2-owned OC/hit joins exactly one row containing:

| Field | Rule |
|---|---|
| `map_id` | stable `MAP-###` |
| `source_hit_ids`, `source_oc_ids` | non-empty exact disjoint inventory sets |
| `surface_kind` | `package|module|file|directory|symbol|import|test|fixture|build-hook|cli|serialized|api|event|workflow|distribution|wheel|metadata` |
| `legacy_coordinate` | exact source path + symbol/key/route as applicable |
| `canonical_coordinate` | exact collision-free target path + symbol/key/route |
| `collision_disposition` | `none|merge-existing|relocate`; never unresolved |
| `producers`, `readers`, `writers`, `consumers` | complete repo coordinates; external consumer has owner/tracking/milestone but cannot defer repo hits |
| `compatibility` | `none|3x-warning-alias|3x-read-migration|closed-no-channel` with CR ID when non-none |
| `tests`, `build_evidence`, `removal_test` | named M2 behavior/topology tests plus M6 absence test |
| `owner`, `removal_owner` | `M2`, and `M6` only for compatibility rows |

Unknown/blank/TBD values fail. Rows are set-equal to every M2-owned manifest hit and every discovered
producer/consumer. A source coordinate appears once. M3–M5 contain none of these hits. The manifest, and
therefore this map, covers `HEAD` outside the fixed `kitty-specs/` exclusion root; M2 never edits that
archive.

## Source package convergence

M2 maps the entire `src/doctrine/` tree into **one named offer-side sub-package inside `src/charter/`**
(the name is fixed by the map approval, M2's sole gate) before editing. The live boundary is preserved, not
dissolved: the one-way import rule (consumer/facade → offer only; the offer never imports the consumer) and
the boundary gates (`tests/architectural/test_runtime_charter_doctrine_boundary.py`,
`test_charter_sole_door_resolver_imports.py`, `test_charter_facades_reexport_doctrine.py`,
`test_shared_package_boundary.py` `_PRODUCTION_ROOTS`) are rewritten to the new package names — facade and
implementation are never merged into one module. Relative-path reuse is allowed only when collision-free.
The known collision set is enumerated as mandatory rows: modules `__init__.py`, `pack_paths.py`,
`provenance.py`, `resolver.py`, `template_catalog.py`, `versioning.py`, `errors.py`, `exceptions.py`,
`primitives.py`; symbols `Directive`, `DoctrineService`, `canonical_yaml`. A collision row must name an
exact semantic merge into an existing canonical module or an exact alternate canonical relocation; review
freezes the choice. Every `importlib.resources.files("doctrine")` site (`src/charter/catalog.py:19`,
`src/specify_cli/skills/registry.py:60`, `src/doctrine/hatch_build.py:12`) and every `.kittify/doctrine`
path literal in code (66 files, e.g. `src/charter/_doctrine_paths.py:30`, `src/specify_cli/cli/commands/
_doctrine_collect.py:243,348,564,1017`, `src/specify_cli/bulk_edit/occurrence_map.py:57`) is a mapped row.
The skills tree `src/doctrine/skills/**` is a `relocate` row (pathnames, OC-41) with its resolver
(`src/specify_cli/skills/registry.py:44,60,67`), wheel artifacts (`pyproject.toml:149,180-185`) and the
release count gate (`.github/workflows/release.yml:219-243`) retargeted; skill IDs (OC-09) stay M4. The
dormant `spec-kitty-doctrine` manifest (`src/doctrine/pyproject.toml`, `hatch_build.py`,
`release.yml:210-226`, `tests/doctrine/test_hatch_build.py`) has an explicit delete-vs-rename row. M2 then
moves files/directories, renames private/public symbols, imports, tests, fixtures, build hooks, package
metadata, distribution/wheel names, facades, and every consumer atomically by dependency slice; the 3.x
import shim (CR-06) is module-only, never a package directory named `doctrine`.

M2 cannot close while either wave-local audit reports any M2-owned (or earlier-wave-owned) code/executable
hit or matching tracked pathname, except registered 3.x compatibility rows assigned to M6; later-wave-owned
rows (M3–M5) may remain and are listed as carried-forward in the wave's occurrence map. The old source root
cannot remain as an unsupported internal implementation.

## Mandatory semantic rows

The map includes at least:

- top-level command group with every nested route (four direct commands plus the `pack`, `org`,
  `mission-type`, `asset` subgroups and the three `validate` routes), the `doctor` route, and the
  `charter mission-type` route-collision disposition (`charter` already owns a `mission-type` subgroup);
- `governance.doctrine` selection seam only as an M1-owned cross-reference, not M2 ownership;
- org-pack config (`doctrine.org.packs` — CR-04 seam: `.kittify/config.yaml:28-36`, reader
  `src/doctrine/drg/org_pack_config.py:577`, writer `:464-481`), tracker ownership block/flag/output,
  target URN (producer `src/specify_cli/doctrine_synthesizer/apply.py:409,663`; external consumer
  `spec_kitty_events` conformance fixture `retrospective_proposal_applied.json:4` with owner/milestone),
  target-kind/category/policy/hash/tool enums, JSON/event aliases, fixture/rekey flows;
- the `.kittify/doctrine` code-literal rows and the dual-root reader (CR-07, introduced by M2; data moved
  by M3); live architectural baselines/allowlists (`tests/architectural/_baselines.yaml`,
  `charter_path_literal_allowlist.yaml`, `_exemptions/doctrine.txt`) as retargeted rows — never deleted;
- every private and public Python package/module/symbol/import under the old source topology;
- exact `doctrine.api.__all__`, re-exports, factories/loaders/services, and all tests/import consumers;
- `spec-kitty-doctrine` project/distribution/wheel/build metadata and wheel-closure consumers;
- workflow, CI, script, generated-template, and build-system coordinates.

`canonical-cli-route-map.md` is the sorted projection of every `surface_kind=cli` row and records the
authoritative map hash; it must be set-equal.

## Compatibility and M6

Canonical writers emit only canonical values in 3.x. Registered old readers/imports/routes warn and are
budgeted by CR. M6 removes all compatibility code, fixtures, controls, metadata aliases, and CR records.
After M6, negative tests encode the forbidden token with numeric bytes. Exact content/path audits—not
support labels—prove absence.
