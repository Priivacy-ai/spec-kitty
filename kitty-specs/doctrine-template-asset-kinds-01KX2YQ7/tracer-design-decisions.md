# Tracer — Design Decisions

Mission `doctrine-template-asset-kinds-01KX2YQ7` · #2495 (P0) + #2469. **Append material decisions during implement.**

## Operator decisions (resolved at spec — do not re-litigate)
- **D1 — ASSET is a NEW kind** (ArtifactKind.ASSET + NodeKind.ASSET), NOT TEMPLATE + a `loose` flag. Resolves #2469's open question.
- **D2 — Proceed OUT of dependency order re #2467** (pack-split keystone, OPEN). Land both kinds on the CURRENT built-in structure; #2467 re-layouts dirs later. The kind contract + `assets/<pack>/` convention are designed forward-compatible.

## The crux (#2495)
- **D3 — Split node-declarable from augmentation-eligible.** The org-pack loader conflated them (templates excluded from
  BOTH). Templates become **node-declarable** (DRG node + edge endpoint) while staying **NOT augmentation-eligible**
  (no augmentation vocabulary → stay out of AUGMENTATION_ELIGIBLE_KINDS / _AUGMENTATION_GLOBS). ASSET is the same:
  node-declarable, not augmentation-eligible.

## Loose contract (#2469)
- **D4 — Loose ≠ unvalidated.** No Pydantic schema for ASSET, but the validator ENFORCES id + mime + addressable path
  presence AND a **hard id-uniqueness rule** (the issue's top risk: no unstructured dumping ground). Fail-loud on dup id / missing mime.

## The exhaustiveness risk (both kinds)
- **D5 — A new enum member ripples.** Ripple surfaces to cover (verified by grep, 85 files ref ArtifactKind / 17 ref NodeKind,
  but the switch/iteration/mapping sites are the risk): artifact_kinds.py (member + augmentation-exclusion comprehension),
  drg/models.py (NodeKind), drg/org_pack_loader.py (_ORG_DRG_KIND_ALIASES + AUGMENTATION_ELIGIBLE_KINDS + _AUGMENTATION_GLOBS),
  drg/merge.py (_PLURAL_TO_SINGULAR), drg/validator.py (schema-skip + asset uniqueness), drg/query.py (`{k:[] for k in NodeKind}` :210,
  `for kind in NodeKind` :225 — auto-includes but verify no downstream KeyError), drg/migration/extractor.py (_KIND_MAP :122 + scan_dirs :743),
  mission_step_contracts/executor.py (_ARTIFACT_TO_NODE_KIND :31), cli/commands/doctrine.py (_SUFFIX_TO_KIND :640), template_catalog.py (TEMPLATE empty-glob).
  Add a new-member guard test so future omissions fail (C-005).

## Post-spec squad hardening (2026-07-09, alphonso/paula/robbie — all folded into spec)
- **D6 (operator) — ASSET on-disk = sidecar `*.asset.yaml` manifest** (id, mime, relative path). Glob `*.asset.yaml`
  (NOT empty-glob → resolves the `test_artifact_kinds` `[k if not k.glob_pattern] == [TEMPLATE]` pin). Blob stays schema-free.
- **D7 — validator is `pack_validator.py`, NOT `drg/validator.py`.** `_artifact_schema_registry`/`_scan_artifact_directory`
  is the real per-kind schema + per-pack id dispatcher; `drg/validator.py` only does agent-profile edges. Spec Key-Entities corrected.
- **D8 — canonical exclusion set (close-by-construction, DIRECTIVE_043).** `_NON_AUGMENTATION_ELIGIBLE_KINDS = {TEMPLATE, ASSET}`
  drives BOTH the augmentation comprehensions AND `artifact_kinds.CHARTER_KIND_TOKENS` (currently `− {TEMPLATE}` single-member
  exception → silently leaks ASSET into charter-activatable + `YAML_KEY_MAP` `activated_assets`). One set, no per-site exceptions.
- **D9 — uniqueness = GLOBAL across the merged graph**, enforced at `merge.py` (org-vs-org collision is silent first-wins today,
  `merge.py:424` — becomes hard-fail for ASSET). URN = `asset:<pack>/<id>` (pack-qualified, mirrors `template_catalog`'s `template:<mission>/<name>`).
- **D10 — path-containment** (Paula, highest-priority): ASSET is the FIRST kind whose path resolves to bytes; `../../etc/passwd`
  unguarded today. Manifest path must be relative + normalise under `assets/<pack>/`; escape/absolute → hard-fail `asset_path_escape`.
- **D11 — mime validation**: type/subtype shape + path-extension consistency (`mimetypes.guess_type`); "requires mime" ≠ non-empty.
- **D12 — LOCKSTEP charter mirrors.** `_ORG_DRG_CANONICAL_KINDS == charter.activations._ALLOWED_KINDS ∪ {mission_types}` is a
  drift-guard test (`test_org_pack_augmentation.py:362-384`) — GUARANTEED RED on FR-001 unless `_ALLOWED_KINDS` + `pack_context._BUILTIN_ARTIFACT_KINDS` move in lockstep. Also: `_OrgDRGNode` has `extra="forbid"` + no `mime` field → FR-006 unimplementable until extended.
- **D13 — C-005 upgraded to a TOTALITY guard.** The only existing new-member guard (`test_nodekind_artifactkind` subset check)
  doesn't guard the mapping tables. New test: every `dict[ArtifactKind…]`/`dict[NodeKind…]` table is total.
- **Sizing → M** (Robbie: honest at model level, undersized by ~one surface-class = the charter cascade). Edge validation is FREE (no kind-pair relation restriction).
- **`ResolveTransitiveRefsResult`** (drg/query.py) has fixed named fields → asset nodes silently DROPPED on return; needs a
  dataclass field + return line, not just the `{k:[] for k in NodeKind}` iteration.

## Post-PLAN squad hardening (2026-07-09, alphonso/paula/robbie — folded into spec+plan+research+data-model+contracts+quickstart)
- **D14 — bare `<kind>:<id>` URNs (REVERSES D9's pack-qualified scheme).** Paula P1: the *single* shared URN bridge
  `merge.py::_bridge_org_node_to_drg_node:271-280` mints `urn = f"{singular}:{node.id}"` — bare, no pack qualifier —
  and `fragment.pack_name` is never threaded in. So `asset:<pack>/<id>` was **unreachable** via the named surfaces
  without either a kind-specific bridge branch (2-of-11 inconsistency) or authors hand-writing slash ids. → All 11 kinds
  keep bare `<kind>:<id>`; collision safety moves to D15.
- **D15 — global URN-uniqueness = ONE post-merge scan at `merge_three_layers` (REFINES D9).** Alphonso A3: the org-vs-org-only
  tweak left built-in-vs-org (`_resolve_builtin_collision:349`, override) and project-vs-any (`:559-564`, project wins) as
  silent-override, contradicting "global". Since TEMPLATE/ASSET are node-declarable-only (no augmentation/override semantics),
  a same-URN clash at ANY layer is genuine ambiguity → hard-fail. A single total-graph scan for `asset:`/`template:` prefixes
  (`_check_node_urn_unique`) makes "global" literally true, is order-independent, collapses 3 surfaces to 1, and leaves the
  other 9 kinds untouched **by construction** (models.py enforces prefix==kind). Emits `duplicate_asset_id` / `duplicate_template_id`.
- **D16 — `_OrgDRGNode` stays identity-only (REVERSES D12's `mime`-field add).** Paula P4: `_OrgDRGNode` is the SHARED 11-kind
  fragment model; an asset-only `mime` is a dead always-None field on the other 10 (and was incomplete — mime without path).
  Asset mime/path live **solely in the sidecar** `*.asset.yaml` (`AssetManifest` model) — the only AT-tested authoring path.
  FR-006 satisfied there. The `extra="forbid"` "blocker" dissolves (nothing to extend). No "skip the blob schema" branch either
  (glob `*.asset.yaml` → blob never scanned; D7's phrasing overstated).
- **D17 — `charter/context.py:500` is a 4TH TEMPLATE-exclusion filter → into IC-02.** Alphonso A1 (sharpest): a
  `member is not ArtifactKind.TEMPLATE` comprehension (`_render_generic_artifact_include` bare-probe); ASSET URNs are identically
  non-bare-probeable → must exclude ASSET for the same reason. It is a comprehension, NOT a dict → **the totality guard won't catch it**;
  IC-02 routes it through the canonical set explicitly.
- **D18 — totality guard must EXEMPT documented `.get`-partials (REFINES D13).** Alphonso A2: four pre-existing `.get`-defaulted
  `dict[ArtifactKind]` partials (`kind_vocabulary.py:75/79`, `pack_manager.py:132/225`) would make a naive "every dict must be total"
  guard **false-fail on Day 1**. Guard distinguishes totality-required maps from documented `.get`-partials, proven against these four.
  `kind_vocabulary.py` was absent from every prior surface list → added to IC-05.
- **D19 — reuse the canonical containment helper, no 6th copy.** Paula P3: the "resolve + relative_to + fail-closed" shape exists ≥5×;
  `drg/org_pack_config.py:210-249` (`effective_root`/`OrgPackSubdirEscapeError`, doctrine-layer, pack-root-aware) is the reuse home for FR-010.
- **D20 — containment+mime run in a SEPARATE `_validate_asset_manifests` pass** (alongside `_validate_drg`), NOT inline in the branchy
  `_scan_artifact_directory` loop — pack_validator.py is 1082 LOC; keep complexity ≤15 (also extract `_check_node_urn_unique` in merge.py).
- **Robbie foldable/deprecation sweep: CLEAR.** No open issue folds (#2467/#2468/#2470/#2471/#2216 all not-same-surface or #2467-gated);
  no anchor lands on a #2467-scheduled-for-removal surface. Proceeding out-of-order is safe.

## Decisions made during implement
_(append here)_
