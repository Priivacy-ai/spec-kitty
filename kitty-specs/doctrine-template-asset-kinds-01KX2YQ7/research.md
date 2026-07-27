# Phase 0 — Research

Mission `doctrine-template-asset-kinds-01KX2YQ7` · #2495 + #2469. All decisions grounded by the post-spec
3-lens squad (architect-alphonso, paula-patterns, researcher-robbie) and confirmed against source on
`feat/doctrine-template-asset-kinds-2495`.

## D-01 — Manifest validation lives in `pack_validator.py`, not `drg/validator.py`
- **Decision**: the ASSET **manifest** validation (`AssetManifest` schema + the separate containment/mime pass)
  lands in `src/specify_cli/doctrine/pack_validator.py` (`_artifact_schema_registry` :145,
  `_scan_artifact_directory` :206, `seen_ids` :223/:289). (Post-plan revised: there is no "schema-skip" branch —
  the blob is never scanned; and **global URN-uniqueness lives in `merge.py`** at `merge_three_layers`, NOT here —
  D-04/D-08 revised. `seen_ids` remains only per-pack-per-type.)
- **Rationale**: `drg/validator.py::validate_graph` (:184) only checks dangling refs / dup edges / requires-cycles
  / profile-edge symmetry — **zero** per-artifact Pydantic validation. `pack_validator.py` is where each kind's
  `(glob, model)` schema + per-pack `seen_ids` id-uniqueness are enforced from a pack checkout.

## D-02 — ASSET on-disk = sidecar `*.asset.yaml` manifest (operator decision)
- **Decision**: each asset blob has a companion `<name>.asset.yaml` (id, mime, relative path). Glob = `*.asset.yaml`.
- **Rationale**: gives ASSET a validatable glob (NOT empty-glob → resolves `test_artifact_kinds`
  `[k if not k.glob_pattern] == [TEMPLATE]`), an explicit home for id/mime/path, and mirrors the schema'd-yaml
  pattern of the 9 kinds. The blob is schema-free; the manifest is the validated surface.
- **Alternatives**: per-pack `manifest.yaml` (fewer files but one file owns all ids) and bare-file (no explicit
  id/mime; collides with the empty-glob pin) — rejected.

## D-03 — Canonical exclusion set (close-by-construction)
- **Decision**: `_NON_AUGMENTATION_ELIGIBLE_KINDS = frozenset({ArtifactKind.TEMPLATE, ArtifactKind.ASSET})`
  drives BOTH `AUGMENTATION_ELIGIBLE_KINDS`/`_AUGMENTATION_GLOBS` AND `artifact_kinds.CHARTER_KIND_TOKENS`.
- **Rationale**: today `CHARTER_KIND_TOKENS` = `ArtifactKind − {TEMPLATE}` (:168-173) and the augmentation set
  = `ArtifactKind − {TEMPLATE}` — single-member exceptions that silently pull `ASSET` in (→ `charter list`,
  `YAML_KEY_MAP` `activated_assets`). One set closes the defect class (DIRECTIVE_043). Node-declarable ≠
  augmentation-eligible ≠ charter-activatable — three properties, now cleanly separated.

## D-04 — Global asset+template URN-uniqueness, enforced ONCE over the merged node set (REVISED post-plan squad)
- **Decision**: `asset:` and `template:` URN uniqueness is enforced **once, over the fully-merged node set**
  (built-in ∪ every org pack ∪ project) at the three-layer assembly point `merge.py::merge_three_layers` (:471) —
  a single total-graph scan for `asset:`/`template:` prefixes; any duplicate → hard-fail
  (`duplicate_asset_id` / `duplicate_template_id`).
- **Rationale (revised)**: the post-plan squad (alphonso A3) showed the original org-vs-org-only tweak
  (`_merge_org_fragment` :424 silent first-wins) leaves TWO other collision surfaces untouched —
  built-in-vs-org (`_resolve_builtin_collision` :349, override-permitted) and project-vs-any
  (`merge_three_layers` :559-564, project wins) — which would silently override, not hard-fail, contradicting
  the "global" mandate. TEMPLATE and ASSET are **node-declarable but NOT augmentation-eligible**, so a same-URN
  collision across any layer carries no legitimate override/augmentation meaning → it is genuine ambiguity and
  must fail loud. A single post-merge uniqueness scan (a) makes "global" literally true, (b) collapses the three
  collision surfaces into one clean check, (c) is order-independent (any collision fails regardless of pack
  order), and (d) leaves the other 9 kinds' layered override tolerance untouched **by construction** —
  `drg/models.py` enforces URN-prefix == kind, so an `asset:`/`template:` URN can only ever collide with its own
  kind. The one shared check covers both new node-declarable kinds.

## D-05 — Bare `<kind>:<id>` URNs (REVISED post-plan squad — pack-qualification dropped)
- **Decision**: org-pack template and asset URNs are **bare** `template:<id>` / `asset:<id>`, exactly like the
  9 existing kinds. **No** `<pack>/` qualifier; **no** signature change to the URN bridge.
- **Rationale (revised)**: the post-plan squad (paula P1) proved the original `<pack>/<id>` scheme was
  **unreachable via the named surfaces**: the *single* generic bridge that mints every org-pack node URN,
  `merge.py::_bridge_org_node_to_drg_node` (:271-280), does `urn = f"{singular}:{node.id}"` — bare id, no pack
  qualifier — and `fragment.pack_name` is never threaded in (confirmed at `pack_validator.py:267,311` too).
  Pack-qualifying only the two new kinds would require either a kind-specific branch in an otherwise-generic
  bridge (a fresh 2-of-11 inconsistency) or org authors hand-writing `id: <pack>/<id>` (undocumented, fragile).
  Bare `<kind>:<id>` keeps all 11 kinds identical; cross-pack / cross-layer collisions are caught **loud** by
  the revised D-04 global-uniqueness scan instead of assumed-away. The built-in `template_catalog` producer
  (`template:<mission>/<name>`, :122-124) keeps its slash-bearing ids; the D-04 scan checks full URNs, so a
  built-in-vs-org template clash is **enforced**, not presumed disjoint.

## D-06 — Path-containment (highest-priority safety, Paula)
- **Decision**: the manifest `path` MUST be relative and normalise strictly under its owning `assets/<pack>/`
  (or `assets/built-in/`) root; any `..`-escape or absolute path → hard-fail `asset_path_escape`.
- **Rationale**: ASSET is the FIRST kind whose "addressable path" plausibly resolves to bytes (existing
  `body_path` is only ever scanned as a text blob, never opened relative to a root). Unguarded, `path:
  ../../../etc/passwd` is a traversal. Enforce at the same point as id/mime.

## D-07 — mime validation
- **Decision**: `mime` must match `type/subtype` shape AND be consistent with the path extension
  (`mimetypes.guess_type`). "requires mime" ≠ "non-empty".

## D-08 — Asset metadata lives in the sidecar ONLY; `_OrgDRGNode` stays identity-only (REVISED post-plan squad)
- **Decision**: **do NOT** add `mime` (or `path`) to `_OrgDRGNode`. Assets are authored solely via the sidecar
  `assets/<pack>/<name>.asset.yaml` manifest (id/mime/path/title), parsed and validated by `pack_validator.py`
  through an `AssetManifest` Pydantic model. `_OrgDRGNode` (`org_pack_loader.py:242-274`, `extra="forbid"`)
  remains identity-only (id/kind/title/body_path), identical for all 11 kinds.
- **Rationale (revised)**: the post-plan squad (paula P4) flagged that `_OrgDRGNode` is the **shared** fragment
  model for every kind; adding an asset-only `mime` bolts a dead, always-`None` field onto the 10 other kinds
  (`extra="forbid"` makes it worse, not better) and was incomplete anyway (mime without path). FR-006 ("an org
  author can declare mime") is satisfied by the sidecar `mime:` field — the only path enumerated in the
  AT-1..AT-7 behavioral contract — not by an inline fragment field. mime is a *validation* concern, not graph
  topology, so it need not propagate onto any DRG node model. This removes the original `extra="forbid"` blocker
  entirely (nothing to extend).

## D-09 — `ResolveTransitiveRefsResult` needs an `assets` field
- **Decision**: add an `assets: list[str]` field + wire it in the hand-written return.
- **Rationale**: `drg/query.py:132/153` is a fixed-field dataclass (`templates` etc.); the `{k:[] for k in
  NodeKind}` bucket includes ASSET but the return (:229-240) never reads `buckets[NodeKind.ASSET]` → asset
  nodes are silently DROPPED from transitive-ref results (the exact C-005 gap).

## D-10 — C-005 totality guard (upgrade the subset guard)
- **Decision**: replace/augment the existing subset guard (`test_nodekind_artifactkind.py:14`, `artifact_values
  <= node_values`) with a **totality guard** asserting every `dict[ArtifactKind…]`/`dict[NodeKind…]` mapping table
  in the codebase is total (handles every member) — so the next kind can't regress the exhaustiveness set.

## D-11 — `charter/context.py:500` is a 4th TEMPLATE-exclusion filter → route through the canonical set (post-plan squad, alphonso A1)
- **Decision**: `_render_generic_artifact_include`'s candidate-kind probe (`charter/context.py:500`, a
  `member is not ArtifactKind.TEMPLATE` comprehension) is added to **IC-02** and routed through
  `_NON_AUGMENTATION_ELIGIBLE_KINDS` (or a shared "not bare-probeable" predicate), excluding ASSET too.
- **Rationale**: the site skips TEMPLATE because templates are *qualified* IDs not addressable by a bare
  `artifact:<id>` probe (comment :493-495). ASSET URNs are **identically** non-bare-probeable, so ASSET must be
  excluded here for the same reason — otherwise adding ASSET (a) changes behavior (starts probing
  `asset:<identifier>` unqualified) and (b) becomes exactly the drifting single-member exception IC-02 abolishes
  (DIRECTIVE_044). **The totality guard will NOT catch this** — it is a filter comprehension, not a
  `dict[ArtifactKind]` mapping — so IC-02 must own it explicitly.

## D-12 — Reuse the canonical path-containment helper, don't hand-roll a 6th (post-plan squad, paula P3)
- **Decision**: the FR-010 asset path-containment check reuses the existing doctrine-layer containment
  (`drg/org_pack_config.py:210-249` `effective_root` / `OrgPackSubdirEscapeError`: resolve-then-`relative_to`,
  `strict=False`, pack-root-aware) rather than adding a sixth hand-rolled copy.
- **Rationale**: the "resolve + `relative_to` + fail-closed" shape already exists ≥5× (`org_pack_config.py`,
  `charter/governance_references.py:98-122`, `charter/scope.py:207`, `charter/synthesizer/manifest.py:243`,
  `doctrine/sources/api_source.py`). `org_pack_config.py`'s is the closest fit (doctrine layer, pack-root
  relative). If the pack-validator call context genuinely needs a different signature, the plan says so and
  justifies non-consolidation — it does not silently add copy #6.

## D-13 — Totality guard must exempt documented `.get`-defaulted partials (post-plan squad, alphonso A2)
- **Decision**: the C-005 totality guard (D-10) distinguishes **totality-required** maps from **documented
  `.get`-defaulted partials**. Four pre-existing partials are the exemption's real test cases:
  `charter/kind_vocabulary.py:75 _ID_FIELD_BY_KIND`, `:79 _PROJECT_KIND_DIRS`,
  `charter/pack_manager.py:132 _PROJECT_KIND_DIRS`, `:225 _ID_FIELD_BY_KIND`.
- **Rationale**: all four are `dict[ArtifactKind, str]` accessed via `.get` (safe for the new kinds — they fall
  through). A naive "every `dict[ArtifactKind]` must be total" guard **false-fails on Day 1** against these four
  unrelated pre-existing dicts. The guard's exemption mechanism must be *proven* against them, not merely
  asserted. `kind_vocabulary.py` was absent from every IC surface list — now added to IC-05.

## Edge mechanics HOLD (Robbie) — FR-004 is free
- `REQUIRES`/`SUGGESTS`/`INSTANTIATES`/`APPLIES` have **no kind-pair restriction** (`drg/validator.py`); only
  `SPECIALIZES_FROM`/`DELEGATES_TO` are profile-restricted. So edges to/from template/asset validate once the
  kinds are node-declarable — no relation-rule work. The generic dangling-ref check (:112) covers #2495's
  "flag an edge to a non-existent template" for free.

## Tests that move (in scope, not to be fought)
`test_artifact_kinds.py` (member-set :25 + glob :72), `test_nodekind_artifactkind.py` (→ totality guard),
`test_org_pack_augmentation.py` (eligible-set :72 + lockstep drift :362), `test_pack_context.py` (defaults),
`test_pack_validator.py` (new ASSET cases), `test_drg_merge.py`/`test_drg_relations.py`/`test_drg_filtering.py`
(new-member coverage).

## Forward-compat (#2467) — reasoned
`assets/<pack>/` uses the same hardcoded-join pattern as the 9 existing kinds (`extractor.py:318/743`); it is
**no worse-coupled** to today's single-tree layout — NFR-003 softened accordingly. C-004 holds.
