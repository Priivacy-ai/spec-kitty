# Mission Specification: First-Class TEMPLATE + ASSET Doctrine Kinds

**Mission slug**: `doctrine-template-asset-kinds-01KX2YQ7`
**Mission ID**: `01KX2YQ7GV9A6FZEZRP8Z31YX4`
**Mission type**: software-dev
**Status**: Draft (post-spec 3-lens squad hardening)
**Priority**: **P0** (operator pivot)
**Sizing**: **M** (squad-corrected from S-M — the charter-layer cascade + on-disk-shape design push it up)
**Tracker**: **#2495** (P0 — templates as first-class org-pack DRG nodes) + **#2469** (new loose-contract `assets` kind) · part of **#2466** · out-of-order re **#2467**

> **Post-spec squad note (2026-07-09).** A 3-lens adversarial squad (architect-alphonso exhaustiveness,
> paula-patterns loose-contract, researcher-robbie reality-check) materially hardened this spec. Key catches
> now folded in: the real schema validator is `pack_validator.py` (not `drg/validator.py`); a **guaranteed-red
> lockstep test** (`_ORG_DRG_CANONICAL_KINDS == charter._ALLOWED_KINDS ∪ {mission_types}`) forces charter-layer
> mirrors to move in lockstep; the augmentation exclusion is a single-member `− {TEMPLATE}` exception that
> silently leaks `ASSET` in; `ResolveTransitiveRefsResult` silently drops asset nodes; and the ASSET contract
> needed explicit **uniqueness scope, URN scheme, path-containment, and mime validation** to avoid the
> dumping-ground risk. Grounding + decisions in the tracer files.

## Purpose (stakeholder-facing)

**TL;DR**: Make an organisation's doctrine **templates** first-class, graph-addressable DRG nodes (#2495) and
add a new **loose-contract `asset`** doctrine kind (#2469) — so a doctrine pack can ship *and graph-link*
everything it contributes, not just its agents/tactics/styleguides.

Today a pack's templates and binary/loose assets are invisible to the **Doctrine Reference Graph (DRG)**:
they can only be pointed at from free-text prose, so they are second-class and un-navigable (the Regnology
all-company pack hit this — its promoted `meeting-minutes`/`lexical` templates could not be graph nodes at
all). This mission makes structured **templates** edge-wireable nodes and introduces a distinct **asset** kind
(identity + mime + addressable path via a sidecar manifest, no blob schema) with hard uniqueness + containment
rules, so a pack's DRG is complete and safe.

## Context & Motivation

Two related design-changes to the org-pack DRG kind universe:

- **(A) #2495 — templates are excluded by design.** `NodeKind.TEMPLATE` / `ArtifactKind.TEMPLATE` exist, but
  the loader omits `templates` from its node universe and builds the augmentation set as `ArtifactKind −
  {TEMPLATE}`. The exclusion conflates two distinct properties: *node-declarable* (can be a graph node + edge
  endpoint) and *augmentation-eligible* (can be layered with augmentation vocabulary). This mission **splits
  them**: templates become node-declarable while staying non-augmentation-eligible.
- **(B) #2469 — no loose-contract kind exists.** Everything in the DRG is a structured, schema'd kind. Add a
  new **loose-contract** `asset` kind for arbitrary addressable files (image, `.docx`, blob) a pack ships and
  references. Its top risk (per the issue) is rotting into an unstructured dumping ground — so it is loose only
  in *blob schema*, not in *contract*: a **sidecar `*.asset.yaml` manifest** carries id + mime + path, and
  **global id-uniqueness + path-containment + mime validation** are enforced.

**Ordering:** #2469 nominally depends on #2467 (pack-split keystone, OPEN). **Operator decision: proceed
out-of-order** — land both kinds on the *current* built-in structure; the pack-split reorganises later.

## Operator decisions (resolved — recorded, not re-litigated)

1. **ASSET is a NEW artifact kind**, not `TEMPLATE` + a `loose` flag (#2469's open question).
2. **Proceed out-of-order re #2467** (land on current built-in structure; forward-compatible).
3. **ASSET on-disk shape = a sidecar `*.asset.yaml` manifest** per asset (id, mime, relative path). This gives
   ASSET a real glob (`*.asset.yaml`, so it is NOT empty-glob), an explicit home for id/mime/path, and mirrors
   the schema'd-yaml-per-artifact pattern of the other 9 kinds. The referenced blob itself stays schema-free.

## Scope

### In scope — (A) templates first-class (#2495)

- Add `templates` to the **node-declarable universe** — and to the charter-layer mirrors that are locked to it:
  `drg/org_pack_loader.py::_ORG_DRG_KIND_ALIASES` / `_ORG_DRG_CANONICAL_KINDS`, `merge.py::_PLURAL_TO_SINGULAR`,
  **`charter/activations.py::_ALLOWED_KINDS`** and **`charter/pack_context.py::_BUILTIN_ARTIFACT_KINDS`** (the
  lockstep drift-guard `test_org_pack_augmentation.py::test_lockstep_drift_guard` breaks otherwise).
- Keep templates **out** of the augmentation-eligible set — via the new canonical exclusion set (below), not a
  single-member exception.
- Edges to/from template nodes validate (nearly free — the generic dangling-ref check already covers it; no
  kind-pair relation-rule work). Org-pack template URN = **bare** `template:<id>` (like all 11 kinds — the shared
  URN bridge mints bare `<kind>:<id>`; **no** `<pack>/` qualifier — post-plan squad, D-05 revised). The
  pre-existing `template_catalog.py` producer keeps its `template:<mission>/<name>` ids; any clash between the two
  producers is **caught loud** by the global URN-uniqueness scan (FR-008), not presumed disjoint.

### In scope — (B) new loose-contract ASSET kind (#2469)

- `ArtifactKind.ASSET` + `NodeKind.ASSET`. On disk: `assets/built-in/` + `assets/<pack>/` with a sidecar
  `*.asset.yaml` manifest per asset. Glob = `*.asset.yaml`. URN = **bare** `asset:<id>` (D-05 revised).
- Asset metadata (id/mime/path) is declared **solely in the sidecar** `*.asset.yaml`, validated by a new
  `AssetManifest` Pydantic model. `_OrgDRGNode` stays **identity-only** (unchanged — post-plan squad, D-08
  revised: adding an asset-only `mime` to the shared 11-kind fragment model is a dead field on the other 10).
- The loose-contract validation lives in **`pack_validator.py`**: the manifest is the validated surface (the
  blob is never scanned — the glob is `*.asset.yaml`, so there is **no** "skip the blob schema" branch to write).
  A **separate `_validate_asset_manifests` pass** (alongside `_validate_drg`, not inline in the branchy per-file
  loop) enforces **path-containment** (reusing `org_pack_config.effective_root` — D-12) and **mime** validation;
  **global URN-uniqueness** is enforced once at `merge_three_layers` (FR-008).
- Add `assets` to `_ORG_DRG_KIND_ALIASES` + `_PLURAL_TO_SINGULAR`; extractor `scan_dirs` + `_KIND_MAP` register
  ASSET (via `.get`, not a raising subscript). ASSET is neither augmentation-eligible nor charter-activatable.

### In scope — canonical exclusion + full exhaustiveness sweep

- Introduce **`_NON_AUGMENTATION_ELIGIBLE_KINDS = frozenset({TEMPLATE, ASSET})`** and drive **both** the
  augmentation comprehensions (`AUGMENTATION_ELIGIBLE_KINDS`/`_AUGMENTATION_GLOBS`) **and**
  `artifact_kinds.py::CHARTER_KIND_TOKENS` off it — closing the silent-leak defect class by construction.
- Cover every add-a-member exhaustiveness site so both members are handled without crash or silent drop:
  `artifact_kinds.py` (member + CHARTER_KIND_TOKENS), `drg/models.py` (NodeKind + URN-prefix rule),
  `drg/org_pack_loader.py`, `drg/merge.py`, `pack_validator.py`, `drg/validator.py` (edge endpoints),
  `drg/query.py::ResolveTransitiveRefsResult` (**new dataclass field + return line — not just iteration**),
  `drg/migration/extractor.py` (`_KIND_MAP` `.get` + `scan_dirs`), `mission_step_contracts/executor.py`
  (`_ARTIFACT_TO_NODE_KIND`), `cli/commands/doctrine.py` (`_SUFFIX_TO_KIND` — `*.asset.yaml`),
  `template_catalog.py`, and the charter cascade: `charter/synthesizer/project_drg.py::_KIND_TO_NODE_KIND`
  (raises on unknown), `charter/consistency_check.py`, `charter/_activation_render.py`, `charter/context.py`
  (`--include` **and the `:500` bare-probe filter — route via the canonical set, D-11**),
  `charter/pack_manager.py` (`YAML_KEY_MAP` + the `.get`-partials `_PROJECT_KIND_DIRS`/`_ID_FIELD_BY_KIND`),
  **`charter/kind_vocabulary.py`** (`_ID_FIELD_BY_KIND`/`_PROJECT_KIND_DIRS` `.get`-partials — the totality guard
  must **exempt** these, not false-fail; D-13), `cli/commands/charter/list_cmd.py::_KIND_ORDER`.

### Out of scope

The #2467 pack-split itself; the other #2466 children (#2468/#2470/#2471); governance-tiers #2216; any change to
the 9 existing kinds' behaviour.

## Domain Language

| Term | Meaning |
|------|---------|
| **DRG** | The typed graph of doctrine artifacts (nodes) + relations (edges) a pack contributes. |
| **`ArtifactKind`/`NodeKind`** | The kind enums. This mission adds `ASSET` to both and makes `TEMPLATE` a usable org-pack node kind. |
| **Node-declarable** | May be a DRG node + edge source/target. |
| **Augmentation-eligible** | May be layered/merged with augmentation vocabulary. **TEMPLATE and ASSET are node-declarable but NOT augmentation-eligible** (the #2495 crux). |
| **Charter-activatable** | Appears in `CHARTER_KIND_TOKENS` (charter list/activation surfaces). TEMPLATE and ASSET are **excluded** (symmetric). |
| **Loose-contract kind** | No blob Pydantic schema; validated via a sidecar `*.asset.yaml` manifest (id + mime + path) + global id-uniqueness + path-containment. `ASSET` is the first. |
| **Sidecar manifest** | `<name>.asset.yaml` beside an asset blob, declaring its `id`, `mime`, and relative `path`. |

## User Scenarios & Testing

Actors: the **doctrine-pack author**, the **pack loader/validator**, the **DRG consumer**.

- **S1 — Template as a graph node (#2495):** an author declares a `template` node in an org pack and wires an
  edge (e.g. a styleguide `requires` a companion template); the loader accepts it, the merged DRG contains the
  node + edge, and a graph query (incl. `resolve_transitive_refs`) returns it.
- **S2 — Asset shipped + addressed (#2469):** an author drops a blob + `<name>.asset.yaml` under `assets/<pack>/`
  with id + mime; the loader mints an `ASSET` node addressable as bare `asset:<id>`; an edge targets it; the
  validator passes it **without** blob schema validation.
- **S3 — Uniqueness enforced (global, all layers):** two packs (or a pack and a built-in) shipping an asset with
  the same `asset:<id>` URN — anywhere in the merged graph across built-in ∪ every org pack ∪ project — **fail
  loud** (`duplicate_asset_id`), via the single post-merge scan at `merge_three_layers` (not silent first-wins,
  not layered override). The same scan emits `duplicate_template_id` for template clashes.
- **S4 — Path containment:** an asset manifest with `path: ../../../etc/passwd` (or an absolute path) **fails
  loud** (`asset_path_escape`); paths must normalise strictly under the owning `assets/<pack>/` root.
- **S5 — mime validation:** a missing or malformed `mime` (not `type/subtype`, or inconsistent with the path
  extension) fails loud.
- **S6 — Augmentation + charter still excluded:** neither template nor asset is augmentation-eligible or
  charter-activatable; `charter list`, `YAML_KEY_MAP`, and the augmentation globs do not include them.
- **S7 — No regression:** the 9 existing kinds load/validate/graph exactly as before; the full doctrine/DRG/
  charter/pack-validator suites are green (incl. the updated lockstep + glob + member-set tests).
- **Edge cases:** an org pack with a template node but no edges (valid orphan); the totality guard asserts every
  `ArtifactKind`/`NodeKind`-keyed mapping table handles both new members.

## Functional Requirements

| ID | Requirement | Status |
|----|-------------|--------|
| FR-001 | (#2495) Add `templates` to the node-declarable universe **and its locked mirrors**: `_ORG_DRG_KIND_ALIASES`/`_ORG_DRG_CANONICAL_KINDS`, `charter/activations.py::_ALLOWED_KINDS`, `charter/pack_context.py::_BUILTIN_ARTIFACT_KINDS` (lockstep with the drift-guard test). | Draft |
| FR-002 | (#2495) Add `templates` to `merge.py::_PLURAL_TO_SINGULAR` so template nodes compose into the merged DRG. | Draft |
| FR-003 | (#2495) Templates are node-declarable but NOT augmentation-eligible and NOT charter-activatable — enforced via the canonical exclusion set (FR-011), not a single-member exception. | Draft |
| FR-004 | (#2495) Edges to/from bare `template:<id>` nodes validate (generic dangling-ref check; no relation-rule change). URNs are bare `<kind>:<id>` (D-05 revised); a clash with the pre-existing `template_catalog` `template:<mission>/<name>` producer is caught loud by the FR-008 uniqueness scan (`duplicate_template_id`), not presumed disjoint. | Draft |
| FR-005 | (#2469) Add `ArtifactKind.ASSET` + `NodeKind.ASSET`; on disk `assets/built-in/` + `assets/<pack>/` with a sidecar `*.asset.yaml` manifest (glob `*.asset.yaml`). | Draft |
| FR-006 | (#2469) Author asset metadata **solely in the sidecar** `*.asset.yaml` via a new `AssetManifest` Pydantic model (id + mime + path present + well-formed); `_OrgDRGNode` stays identity-only (D-08 revised — no asset-only `mime` on the shared fragment model). The blob is never scanned (glob `*.asset.yaml`), so there is no "skip the blob schema" branch. | Draft |
| FR-007 | (#2469) Register ASSET in the extractor (`scan_dirs` + `_KIND_MAP` via `.get`) and add `assets` to `_ORG_DRG_KIND_ALIASES` + `_PLURAL_TO_SINGULAR`. | Draft |
| FR-008 | (#2469) Enforce **global** URN-uniqueness across all three layers (built-in ∪ every org pack ∪ project) via a **single post-merge scan at `merge_three_layers`** (extract `_check_node_urn_unique`) — any duplicate `asset:` URN → hard-fail `duplicate_asset_id`; any duplicate `template:` URN → `duplicate_template_id` (replacing today's org-vs-org silent first-wins and covering the built-in/project override surfaces too). URN = bare `asset:<id>`. | Draft |
| FR-009 | (#2469) mime validation (in `_validate_asset_manifests`): `type/subtype` shape + path-extension consistency (`mimetypes.guess_type`). | Draft |
| FR-010 | (#2469) Path-containment (in `_validate_asset_manifests`, reusing `org_pack_config.effective_root`/`OrgPackSubdirEscapeError` — no 6th copy, D-12): the manifest `path` MUST be relative and normalise strictly under its owning `assets/<pack>/` (or `assets/built-in/`) root; any `..`-escape or absolute path is a hard-fail (`asset_path_escape`). | Draft |
| FR-011 | Introduce `_NON_AUGMENTATION_ELIGIBLE_KINDS = frozenset({ArtifactKind.TEMPLATE, ArtifactKind.ASSET})` and drive BOTH the augmentation comprehensions (`AUGMENTATION_ELIGIBLE_KINDS`/`_AUGMENTATION_GLOBS`) AND `artifact_kinds.py::CHARTER_KIND_TOKENS` off it (close the silent-leak class by construction). | Draft |
| FR-012 | Cover the full exhaustiveness set so both members are handled without crash/silent-drop: `drg/query.py::ResolveTransitiveRefsResult` (new `assets` field + return line), `extractor::_KIND_MAP` (`.get`), `charter/synthesizer/project_drg.py::_KIND_TO_NODE_KIND`, `charter/consistency_check.py`, `charter/_activation_render.py`, `charter/context.py` (`--include` + the `:500` bare-probe filter, D-11), `charter/pack_manager.py` (`YAML_KEY_MAP` + `.get`-partials `_PROJECT_KIND_DIRS`/`_ID_FIELD_BY_KIND`), `charter/kind_vocabulary.py` (`.get`-partials — totality-guard exemption, D-13), `cli/commands/charter/list_cmd.py::_KIND_ORDER`, `executor::_ARTIFACT_TO_NODE_KIND`, `doctrine.py::_SUFFIX_TO_KIND` (`*.asset.yaml`), `template_catalog.py`. | Draft |

## Non-Functional Requirements

| ID | Requirement | Threshold / Measure | Status |
|----|-------------|---------------------|--------|
| NFR-001 | No regression | The 9 existing kinds load/validate/graph identically; full doctrine + DRG + charter + pack-validator suites green (incl. the updated lockstep/glob/member-set tests). | Draft |
| NFR-002 | Code quality | `ruff` + `mypy` zero new issues; complexity ≤ 15; no new suppressions. | Draft |
| NFR-003 | Forward-compat with #2467 | The `assets/<pack>/` convention is **no worse-coupled than the existing 9 kinds** (same hardcoded-join pattern); a pack-split re-layout does not require re-designing the kind contract. | Draft |
| NFR-004 | End-to-end fixture | An org-pack fixture with a `template` node + edge + an `asset` (blob + sidecar manifest) loads, graph-links, and validates; plus negative cases: duplicate-id-across-packs, path-escape, malformed mime each fail loud. | Draft |
| NFR-005 | Loose-contract fail-loud | Global duplicate asset id, missing/malformed mime, and path-escape each produce a distinct structured, testable error (loose ≠ unvalidated). | Draft |

## Constraints

| ID | Constraint | Status |
|----|-----------|--------|
| C-001 | `TEMPLATE` + `ASSET` are node-declarable but NOT augmentation-eligible AND NOT charter-activatable — via `_NON_AUGMENTATION_ELIGIBLE_KINDS` (no single-member exceptions anywhere). | Draft |
| C-002 | `ASSET` is a NEW `ArtifactKind`/`NodeKind`, not `TEMPLATE` + a `loose` flag (operator decision). | Draft |
| C-003 | Loose ≠ unvalidated: only the blob is schema-free; the sidecar manifest (id/mime/path) + global id-uniqueness + path-containment ARE enforced. | Draft |
| C-004 | Proceed out-of-order re #2467; kind contract stays forward-compatible with the pack-split. | Draft |
| C-005 | **No exhaustiveness gap** — every `ArtifactKind`/`NodeKind`-keyed mapping table is **total**; upgrade the existing subset guard (`test_nodekind_artifactkind`) to a **totality guard** asserting each such table handles every member. | Draft |
| C-006 | Scope is the two kinds + the enumerated surfaces only; the #2467 pack-split and other #2466/#2216 children are OUT. | Draft |

## Success Criteria

1. A pack can declare a `template` DRG node + edges; a graph query (incl. transitive) returns it.
2. A pack can ship a blob as an `asset` (sidecar manifest, id + mime + path), addressable as bare `asset:<id>`, validated without a blob schema.
3. Global duplicate asset id, path-escape, and malformed mime each fail loud; no silent dumping-ground and no silent first-wins.
4. Templates and assets are node-declarable but excluded from both augmentation and charter-activation (the #2495 split holds, via one canonical set).
5. The 9 existing kinds are unchanged; full doctrine/DRG/charter/validator suites green; the totality guard proves no exhaustiveness gap.

## Key Entities

- **`ArtifactKind.ASSET` / `NodeKind.ASSET`** — the new loose-contract kind (sidecar-manifest shape).
- **`ArtifactKind.TEMPLATE` / `NodeKind.TEMPLATE`** — now a usable org-pack node kind.
- **`_NON_AUGMENTATION_ELIGIBLE_KINDS`** — the new canonical exclusion set driving augmentation + charter tokens.
- **`pack_validator.py`** (`_artifact_schema_registry` + a new `AssetManifest` model; a separate `_validate_asset_manifests` pass) — the real schema/manifest dispatcher; gets the ASSET manifest + mime + containment validation. Global URN-uniqueness lives at `merge.py::merge_three_layers`, not here. *(Corrected from the earlier draft's `drg/validator.py`, which only does agent-profile edges.)*
- **`_OrgDRGNode`** (`org_pack_loader.py`) — **unchanged** (identity-only for all 11 kinds; asset mime/path live in the sidecar — D-08 revised).
- **The charter-layer mirrors** — `_ALLOWED_KINDS`, `_BUILTIN_ARTIFACT_KINDS`, `CHARTER_KIND_TOKENS`, and their downstream maps.
- **`src/doctrine/assets/`** — the new asset tree (`built-in/`, `<pack>/`).

## Assumptions

1. The DRG node/edge model supports the graph mechanics; `REQUIRES`/`SUGGESTS`/etc. have no kind-pair restriction, so edges to template/asset are free once the kinds are node-declarable.
2. The Regnology all-company pack is the reference consumer; an equivalent fixture stands in as an automated test.
3. #2467 will re-layout doctrine directories later; this mission's kind contract is designed to survive that (same coupling as existing kinds).

## Dependencies

- **Nominal depends-on #2467** — deliberately taken out-of-order per operator decision; forward-compatible.
- Part of **#2466** (Doctrine/Charter extensibility & pack ecosystem).
