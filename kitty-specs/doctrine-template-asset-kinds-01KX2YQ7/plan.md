# Implementation Plan: First-Class TEMPLATE + ASSET Doctrine Kinds

**Branch**: `feat/doctrine-template-asset-kinds-2495` | **Date**: 2026-07-09 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `kitty-specs/doctrine-template-asset-kinds-01KX2YQ7/spec.md`

## Summary

Make org-pack **templates** first-class DRG nodes (#2495) and add a new loose-contract **ASSET** kind
(#2469), extracting against the existing DRG model. Two design moves: (1) **split node-declarable from
augmentation-eligible** via a single canonical `_NON_AUGMENTATION_ELIGIBLE_KINDS = {TEMPLATE, ASSET}` set that
drives *both* the augmentation comprehensions and `CHARTER_KIND_TOKENS` (closing the silent-leak class by
construction); (2) give ASSET a **sidecar `*.asset.yaml` manifest** (id/mime/path) validated by
`pack_validator.py` (the blob is never scanned — the glob is `*.asset.yaml`), with **path-containment + mime**
enforced in a separate manifest pass and **global URN-uniqueness** enforced once at `merge_three_layers`. The
post-spec squad's grounding (validator relocation, charter-mirror lockstep, the transitive-refs dropped-node)
plus the post-plan squad's reversals (bare `<kind>:<id>` URNs; `_OrgDRGNode` unchanged / sidecar-only mime;
one global-uniqueness scan; `context.py:500`; totality-guard `.get`-exemption) are all confirmed against source
and planned below.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: standard library (`enum.StrEnum`, `frozenset`, `mimetypes`, `pathlib`); existing
Pydantic (schema'd kinds) + YAML loader (manifest parse). **No new runtime dependencies.**
**Storage**: Filesystem — the doctrine tree; new `assets/built-in/` + `assets/<pack>/` with `*.asset.yaml`
manifests beside blobs.
**Testing**: `pytest`. Updated member-set/glob/lockstep tests (`test_artifact_kinds`,
`test_nodekind_artifactkind`, `test_org_pack_augmentation`); **new totality guard** over every
`ArtifactKind`/`NodeKind`-keyed mapping table (with a documented `.get`-partial exemption); new `pack_validator`
ASSET cases (manifest + path-escape + mime) + merge dup-URN cases (asset + template); an **e2e org-pack fixture**
(template node + edge + asset). ATDD-first: the uniqueness/containment/mime fail-loud tests are written red
before the enforcement lands.
**Target Platform**: the doctrine + charter layer of the Spec Kitty CLI.
**Project Type**: single (Python library + CLI).
**Performance Goals**: none.
**Constraints**: one canonical exclusion set (no single-member exceptions anywhere — incl. the `context.py:500`
bare-probe filter); global `asset:`+`template:` URN-uniqueness enforced by a single post-merge scan at
`merge_three_layers`; **bare** `<kind>:<id>` URNs (no pack-qualification — the shared bridge mints bare ids);
path-containment via the reused `org_pack_config.effective_root` helper (no 6th copy); forward-compatible
with #2467 (no worse-coupled than existing kinds); `ruff`+`mypy` zero-new; complexity ≤ 15 (extract
`_check_node_urn_unique` + `_validate_asset_manifests` helpers rather than inlining).
**Scale/Scope**: 2 new enum members; ~17 exhaustiveness surfaces across `src/doctrine/` (artifact_kinds, drg/*,
template_catalog, new assets/) + `src/charter/` (activations, pack_context, synthesizer/project_drg,
consistency_check, _activation_render, context, pack_manager, **kind_vocabulary**) + `src/specify_cli/`
(doctrine/pack_validator, mission_step_contracts/executor, cli/commands/doctrine, cli/commands/charter/list_cmd);
~8 test files updated + new totality guard (with a `.get`-partial exemption) + e2e fixture.

## Charter Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Charter loaded (`plan` action, `software-dev-default`).

| Principle | Disposition |
|---|---|
| **Single canonical authority** | ✅ The `_NON_AUGMENTATION_ELIGIBLE_KINDS` set becomes the ONE source for the augmentation + charter-token exclusion (replacing scattered `− {TEMPLATE}` exceptions). |
| **Close-by-construction (DIRECTIVE_043)** | ✅ The canonical set + the totality guard make the "add-a-member exhaustiveness" defect class structurally impossible to regress. |
| **DDD + tiered rigour** | ✅ Core doctrine/DRG surfaces get full rigour + tests; the loose-contract ASSET is loose only in *blob schema*, not contract. |
| **ATDD-first / red-first** | ✅ Uniqueness/containment/mime fail-loud + the e2e fixture authored red first. |
| **Terminology canon** | ✅ New doctrine kind names; run the terminology guard + docs-freshness (glossary regen if a new term is introduced) before push. |
| **Realistic test data** | ✅ The e2e fixture uses a Regnology-shaped pack (real template + asset shapes), not toy placeholders. |

**No charter violations.**

## Project Structure

### Documentation (this mission)

```
kitty-specs/doctrine-template-asset-kinds-01KX2YQ7/
├── plan.md · research.md · data-model.md · quickstart.md · contracts/
└── tracer-approach.md · tracer-design-decisions.md · tracer-tooling-friction.md
```

### Source Code (repository root)

```
src/doctrine/
├── artifact_kinds.py          # + ArtifactKind.ASSET; CHARTER_KIND_TOKENS driven off _NON_AUGMENTATION_ELIGIBLE_KINDS
├── drg/models.py              # + NodeKind.ASSET (+ URN-prefix rule for asset/template)
├── drg/org_pack_loader.py     # _ORG_DRG_KIND_ALIASES += templates,assets; _NON_AUGMENTATION_ELIGIBLE_KINDS (_OrgDRGNode UNCHANGED — D-08 revised)
├── drg/org_pack_config.py     # REUSE effective_root/OrgPackSubdirEscapeError for asset path-containment (D-12)
├── drg/merge.py               # _PLURAL_TO_SINGULAR += templates,assets; single post-merge GLOBAL uniqueness scan (asset:+template:) at merge_three_layers
├── drg/query.py               # ResolveTransitiveRefsResult += assets field + return line (was silently dropped)
├── drg/migration/extractor.py # _KIND_MAP via .get; scan_dirs += assets
├── template_catalog.py        # keep template:<mission>/<name> ids; clash caught by the uniqueness scan (not presumed disjoint)
└── assets/                    # NEW: built-in/ + the *.asset.yaml sidecar-manifest convention

src/charter/                   # the lockstep mirror cascade
├── activations.py             # _ALLOWED_KINDS += templates,assets (lockstep w/ drift-guard test)
├── pack_context.py            # _BUILTIN_ARTIFACT_KINDS += templates,assets
├── synthesizer/project_drg.py # _KIND_TO_NODE_KIND (.get, not raise)
├── context.py                 # :500 bare-probe filter → route via canonical set (IC-02); + IC-05 mapping sites
├── kind_vocabulary.py         # _ID_FIELD_BY_KIND:75 / _PROJECT_KIND_DIRS:79 (.get partials — totality-guard exemption)
├── consistency_check.py · _activation_render.py · pack_manager.py (YAML_KEY_MAP + _PROJECT_KIND_DIRS:132 + _ID_FIELD_BY_KIND:225)

src/specify_cli/
├── doctrine/pack_validator.py # THE validator: AssetManifest(id/mime/path) + separate _validate_asset_manifests pass (containment reuse + mime). Global uniqueness lives in merge.py, NOT here
├── mission_step_contracts/executor.py  # _ARTIFACT_TO_NODE_KIND += asset,template
└── cli/commands/{doctrine.py,charter/list_cmd.py}  # _SUFFIX_TO_KIND (*.asset.yaml), _KIND_ORDER

tests/  # member-set/glob/lockstep updates + NEW totality guard + e2e org-pack fixture + negative cases
```

**Structure Decision**: Single Python project. The change is a doctrine-kind addition threaded through the
DRG kind universe, the charter-layer mirrors, and the validator — extracted **against** the existing DRG
node/edge model (no model change beyond adding the two members; `_OrgDRGNode` stays unchanged — D-08 revised). Edge validation is free
(no kind-pair relation restriction, confirmed).

## Complexity Tracking

*No Charter Check violations — table intentionally empty.*

## Implementation Concern Map

> Concerns are NOT work packages. `/spec-kitty.tasks` translates these into WPs.

### IC-01 — TEMPLATE first-class + lockstep mirrors (#2495)
- **Purpose**: make `templates` a node-declarable org-pack DRG kind, moving the locked charter mirrors in lockstep.
- **Requirements**: FR-001, FR-002, FR-004.
- **Surfaces**: `org_pack_loader.py` (`_ORG_DRG_KIND_ALIASES`), `merge.py` (`_PLURAL_TO_SINGULAR`), `charter/activations.py` (`_ALLOWED_KINDS`), `charter/pack_context.py` (`_BUILTIN_ARTIFACT_KINDS`), `test_org_pack_augmentation.py` (lockstep drift-guard). Reconcile the `template_catalog` URN.
- **Depends-on**: none. **Risk**: the lockstep drift-guard is guaranteed-red until all mirrors move together.

### IC-02 — Canonical exclusion set (close-by-construction)
- **Purpose**: `_NON_AUGMENTATION_ELIGIBLE_KINDS = {TEMPLATE, ASSET}` drives the augmentation comprehensions, `CHARTER_KIND_TOKENS`, AND the `context.py:500` bare-probe filter; no single-member `is not TEMPLATE` exceptions survive.
- **Requirements**: FR-003, FR-011; C-001.
- **Surfaces**: `artifact_kinds.py` (`CHARTER_KIND_TOKENS`), `org_pack_loader.py` (`AUGMENTATION_ELIGIBLE_KINDS`/`_AUGMENTATION_GLOBS`), **`charter/context.py:500`** (`_render_generic_artifact_include` candidate-kind probe — the 4th TEMPLATE-exclusion filter surfaced by the post-plan squad; D-11).
- **Depends-on**: precedes IC-03 (ASSET must be excluded the moment it's added). **Risk**: miss a derivation site → silent leak. The `context.py:500` site is a **comprehension, not a dict → the totality guard will NOT catch it**; IC-02 owns it explicitly.

### IC-03 — ASSET kind + sidecar manifest + loose validator (#2469)
- **Purpose**: `ArtifactKind.ASSET` + `NodeKind.ASSET`; `*.asset.yaml` sidecar manifest validated by a new `AssetManifest` Pydantic model; extractor/loader registration. (Note: there is **no** "skip the blob's schema" branch — the glob is `*.asset.yaml`, so the blob is never scanned. The manifest is the validated surface, exactly like the 9 kinds' yaml — D-02/paula P2.)
- **Requirements**: FR-005, FR-006, FR-007.
- **Surfaces**: `artifact_kinds.py`, `drg/models.py`, `drg/org_pack_loader.py` (`_ORG_DRG_KIND_ALIASES` only — `_OrgDRGNode` stays identity-only, D-08 revised), `merge.py` (`_PLURAL_TO_SINGULAR`), `pack_validator.py` (`_artifact_schema_registry` += `AssetManifest`; `_scan_artifact_directory`), `extractor.py`, `src/doctrine/assets/`.
- **Depends-on**: IC-02 (exclusion set in place first). **Risk**: FR-006 `mime:` is authored in the **sidecar** (not `_OrgDRGNode`) — the original `extra="forbid"` blocker is dissolved by keeping asset metadata sidecar-only.

### IC-04 — ASSET safety contract (uniqueness + containment + mime)
- **Purpose**: global URN-uniqueness (a **single post-merge scan** at `merge_three_layers`, covering `asset:` AND `template:` across all three layers, replacing the org-vs-org-only silent first-wins), path-containment (`asset_path_escape`), mime validation (type/subtype + extension). Red-first fail-loud tests.
- **Requirements**: FR-008, FR-009, FR-010; NFR-005.
- **Surfaces**: `merge.py::merge_three_layers` (global uniqueness scan → extract `_check_node_urn_unique`; also emits `duplicate_template_id`, closing #2495's two-template-producer clash), `pack_validator.py` (a **separate** `_validate_asset_manifests` pass alongside `_validate_drg` — NOT inline in the branchy per-file loop; 1082 LOC / complexity ≤15), reusing `drg/org_pack_config.py:210-249` `effective_root`/`OrgPackSubdirEscapeError` for containment (D-12, no 6th copy), `drg/models.py` (bare URN `asset:<id>`).
- **Depends-on**: IC-03. **Risk**: the scan is NEW merge behavior — scoped by URN prefix so the other 9 kinds' override tolerance is untouched **by construction** (models.py enforces prefix==kind). D-04↔IC-04 reconciled: uniqueness is genuinely *global* (all 3 layers), because these node-declarable-only kinds have no override/augmentation semantics that would make a cross-layer collision meaningful (alphonso A3).

### IC-05 — Exhaustiveness sweep + totality guard
- **Purpose**: every totality-required `ArtifactKind`/`NodeKind`-keyed mapping table handles both new members; a totality guard test makes future omissions fail **while exempting documented `.get`-defaulted partials**.
- **Requirements**: FR-012; C-005.
- **Surfaces**: `drg/query.py` (`ResolveTransitiveRefsResult` field + return), `extractor::_KIND_MAP` (`.get`), `charter/synthesizer/project_drg.py`, `charter/consistency_check.py`, `charter/_activation_render.py`, `charter/context.py`, `charter/pack_manager.py` (`YAML_KEY_MAP` + **`_PROJECT_KIND_DIRS`:132 / `_ID_FIELD_BY_KIND`:225**), **`charter/kind_vocabulary.py` (`_ID_FIELD_BY_KIND`:75 / `_PROJECT_KIND_DIRS`:79 — absent from every prior IC list)**, `cli/commands/charter/list_cmd.py` (`_KIND_ORDER`), `executor::_ARTIFACT_TO_NODE_KIND`, `doctrine.py::_SUFFIX_TO_KIND`, `template_catalog.py`.
- **Depends-on**: IC-01..IC-04 (needs both members present). **Risk**: the guard must **distinguish totality-required maps from `.get`-defaulted partials**, proven against the four pre-existing partials above (`kind_vocabulary.py:75/79`, `pack_manager.py:132/225`) — a naive "every `dict[ArtifactKind]` must be total" guard **false-fails on Day 1** (D-13). This is the "invisible" surface set the spec's first draft missed — the totality guard is the backstop, but it must not itself over-fire.

### IC-06 — E2E fixture + no-regression (NFR-001/004)
- **Purpose**: a Regnology-shaped org-pack fixture (template node + edge + asset with manifest) loads/graphs/validates; negative cases (dup-id-across-packs, path-escape, malformed mime) fail loud; the 9 existing kinds unchanged; full doctrine/DRG/charter/validator suites green.
- **Requirements**: NFR-001, NFR-004.
- **Depends-on**: all. **Risk**: run the full doctrine+charter+arch suites locally (CI-only shards) before hand-off.
