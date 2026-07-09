# Tasks: First-Class TEMPLATE + ASSET Doctrine Kinds

**Mission**: `doctrine-template-asset-kinds-01KX2YQ7` · #2495 (P0) + #2469 · part of #2466
**Branch**: `feat/doctrine-template-asset-kinds-2495` (planning base = merge target; PR later targets `Priivacy-ai/spec-kitty:main`)
**Plan**: [plan.md](./plan.md) · **Spec**: [spec.md](./spec.md) · **Research**: [research.md](./research.md) · **Data model**: [data-model.md](./data-model.md) · **Contract**: [contracts/asset-kind.md](./contracts/asset-kind.md)

Two doctrine-kind changes threaded through the DRG kind universe: (A #2495) make `TEMPLATE` a first-class,
edge-wireable org-pack DRG node; (B #2469) add a new loose-contract `ASSET` kind (sidecar `*.asset.yaml`
manifest, no blob schema, hard uniqueness + containment + mime). Decomposed against the plan's 6 Implementation
Concerns, hardened by the post-plan squad (bare `<kind>:<id>` URNs; one global uniqueness scan at
`merge_three_layers`; `_OrgDRGNode` unchanged / sidecar-only metadata; `context.py:500` into the canonical set;
totality guard exempts documented `.get`-partials; reuse `effective_root` containment).

## Work Package Dependency Graph

```
WP01 (enum core + canonical set)  ── root
  ├─ WP02 (loader universe + lockstep mirrors)
  │     └─ WP03 (merge compose + global uniqueness scan)
  ├─ WP04 (ASSET sidecar validator + safety)
  ├─ WP05 (extractor + doctrine-CLI suffix)
  └─ WP06 (charter-cascade exhaustiveness + context.py:500)
        WP07 (core exhaustiveness + totality guard)  ← depends WP01..WP06
          WP08 (e2e fixture + no-regression)         ← depends WP01..WP07
```

**Parallel after WP01:** WP02, WP04, WP05, WP06 (disjoint surfaces). WP03 after WP02. WP07 gathers the sweep;
WP08 is the terminal no-regression gate. **MVP:** WP01→WP02→WP03 (templates first-class) is the #2495 spine;
WP04 is the #2469 spine.

## Requirement → Work Package Coverage

| FR | WP(s) |
|----|-------|
| FR-001 (templates node-declarable + lockstep mirrors) | WP02 |
| FR-002 (templates in `_PLURAL_TO_SINGULAR`) | WP03 |
| FR-003 (templates NOT augmentation/charter via canonical set) | WP02 |
| FR-004 (edges to bare `template:<id>` validate; clash caught) | WP02, WP08 |
| FR-005 (`ArtifactKind.ASSET` + `NodeKind.ASSET` + on-disk tree) | WP01, WP04 |
| FR-006 (sidecar `AssetManifest`; `_OrgDRGNode` unchanged) | WP04 |
| FR-007 (extractor + loader/plural registration) | WP02, WP03, WP05 |
| FR-008 (global URN-uniqueness scan at `merge_three_layers`) | WP03 |
| FR-009 (mime validation) | WP04 |
| FR-010 (path-containment via reused `effective_root`) | WP04 |
| FR-011 (`_NON_AUGMENTATION_ELIGIBLE_KINDS` drives augmentation + `CHARTER_KIND_TOKENS`) | WP01, WP02 |
| FR-012 (exhaustiveness sweep + totality guard) | WP05, WP06, WP07 |

NFRs: NFR-001/004/005 land in WP08 (no-regression + negative cases); NFR-002 (ruff/mypy/complexity) is a
per-WP DoD; NFR-003 (forward-compat #2467) is honoured by WP04's convention + confirmed in WP08.

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|----|----------|
| T001 | `ArtifactKind.ASSET` member + glob `*.asset.yaml` | WP01 | | [D] |
| T002 | `NodeKind.ASSET` + URN-prefix==kind rule | WP01 | [D] |
| T003 | `_NON_AUGMENTATION_ELIGIBLE_KINDS = {TEMPLATE, ASSET}` | WP01 | | [D] |
| T004 | Drive `CHARTER_KIND_TOKENS` off the canonical set | WP01 | | [D] |
| T005 | Update member-set + glob tests | WP01 | | [D] |
| T006 | `_ORG_DRG_KIND_ALIASES`/`_ORG_DRG_CANONICAL_KINDS` += templates, assets | WP02 | | [D] |
| T007 | Drive `AUGMENTATION_ELIGIBLE_KINDS`/`_AUGMENTATION_GLOBS` off the canonical set | WP02 | | [D] |
| T008 | Move lockstep mirrors `_ALLOWED_KINDS` + `_BUILTIN_ARTIFACT_KINDS` | WP02 | | [D] |
| T009 | Update augmentation + lockstep drift-guard + pack_context tests | WP02 | | [D] |
| T010 | `_PLURAL_TO_SINGULAR` += templates, assets | WP03 | | [D] |
| T011 | `_check_node_urn_unique(prefix, nodes)` helper | WP03 | | [D] |
| T012 | Wire the scan at `merge_three_layers` (asset:+template:, all layers) | WP03 | | [D] |
| T013 | Red-first dup-URN tests (asset + template, cross-layer) | WP03 | | [D] |
| T014 | `AssetManifest` Pydantic model + register in `_artifact_schema_registry` | WP04 | | [D] |
| T015 | `_validate_asset_manifests` separate pass (invoked alongside `_validate_drg`) | WP04 | | [D] |
| T016 | Path-containment via reused `effective_root`/`OrgPackSubdirEscapeError` | WP04 | | [D] |
| T017 | mime validation (type/subtype + extension consistency) | WP04 | | [D] |
| T018 | `assets/built-in/` convention + red-first manifest tests | WP04 | | [D] |
| T019 | Extractor `scan_dirs` += assets; `_KIND_MAP` via `.get` | WP05 | | [D] |
| T020 | `doctrine.py::_SUFFIX_TO_KIND` += `*.asset.yaml` | WP05 | [D] |
| T021 | Extractor/suffix tests | WP05 | | [D] |
| T022 | `context.py:500` bare-probe filter → canonical set (excludes ASSET) | WP06 | | [D] |
| T023 | `pack_manager` (`YAML_KEY_MAP` + `.get`-partials) + `kind_vocabulary` partials | WP06 | | [D] |
| T024 | `project_drg::_KIND_TO_NODE_KIND` (`.get`, not raise) + `consistency_check` + `_activation_render` | WP06 | | [D] |
| T025 | `list_cmd::_KIND_ORDER` + `test_drg_filtering` member coverage | WP06 | | [D] |
| T026 | Charter-cascade exhaustiveness test | WP06 | | [D] |
| T027 | `ResolveTransitiveRefsResult` += `assets` field + return line | WP07 | | [D] |
| T028 | `executor::_ARTIFACT_TO_NODE_KIND` += asset,template; `template_catalog` reconcile | WP07 | | [D] |
| T029 | Totality guard test (every kind-keyed dict total OR documented `.get`-partial) | WP07 | | [D] |
| T030 | Prove the guard exempts the 4 pre-existing partials (no Day-1 false-fail) | WP07 | | [D] |
| T031 | E2E org-pack fixture: template node + edge + asset (blob + sidecar) | WP08 | |
| T032 | Negative cases: dup-id cross-layer, path-escape, malformed mime fail loud | WP08 | |
| T033 | Full doctrine/DRG/charter/pack-validator suites green; 9 kinds unchanged | WP08 | |

---

## WP01 — Enum core + canonical exclusion set

- **Goal**: add both new enum members and the one canonical exclusion set that closes the silent-leak class.
- **Priority**: P0 (root — everything depends on it). **Independent test**: `pytest tests/doctrine/test_artifact_kinds.py tests/doctrine/drg/test_nodekind_artifactkind.py`.
- **Requirements**: FR-005 (enum), FR-011, C-001.
- **Subtasks**: T001–T005.
- **Dependencies**: None
- **Prompt**: [tasks/WP01-enum-core-canonical-set.md](./tasks/WP01-enum-core-canonical-set.md)

## WP02 — Loader universe + lockstep charter mirrors

- **Goal**: make `templates` + `assets` node-declarable; drive augmentation exclusion off the canonical set; move the locked charter mirrors in lockstep.
- **Priority**: P0. **Independent test**: `pytest tests/doctrine/test_org_pack_augmentation.py tests/charter/test_pack_context.py`.
- **Requirements**: FR-001, FR-003, FR-004 (template edge-wireable), FR-007 (loader aliases), FR-011 (consumption).
- **Subtasks**: T006–T009.
- **Dependencies**: WP01
- **Risk**: the lockstep drift-guard is guaranteed-red until all mirrors move together.
- **Prompt**: [tasks/WP02-loader-universe-lockstep.md](./tasks/WP02-loader-universe-lockstep.md)

## WP03 — Merge compose + global URN-uniqueness scan

- **Goal**: compose template/asset nodes into the merged DRG and enforce global URN-uniqueness with one post-merge scan.
- **Priority**: P0. **Independent test**: `pytest tests/doctrine/test_drg_merge.py`.
- **Requirements**: FR-002, FR-007 (plural), FR-008.
- **Subtasks**: T010–T013.
- **Dependencies**: WP01, WP02
- **Risk**: NEW merge behavior — scope by URN prefix; the scan runs once at `merge_three_layers`, not per-fragment.
- **Prompt**: [tasks/WP03-merge-global-uniqueness.md](./tasks/WP03-merge-global-uniqueness.md)

## WP04 — ASSET sidecar validator + safety contract

- **Goal**: `AssetManifest` validation + a separate `_validate_asset_manifests` pass (containment reuse + mime); the `assets/` convention.
- **Priority**: P0 (the #2469 spine). **Independent test**: `pytest tests/specify_cli/doctrine/test_pack_validator.py`.
- **Requirements**: FR-005 (on-disk), FR-006, FR-009, FR-010, NFR-005.
- **Subtasks**: T014–T018.
- **Dependencies**: WP01
- **Risk**: keep pack_validator.py complexity ≤15 — the containment/mime pass is a separate helper, not inline in the branchy scan loop.
- **Prompt**: [tasks/WP04-asset-sidecar-validator.md](./tasks/WP04-asset-sidecar-validator.md)

## WP05 — Extractor + doctrine-CLI suffix

- **Goal**: register ASSET in the migration extractor and the `*.asset.yaml` suffix→kind map.
- **Priority**: P1. **Independent test**: `pytest tests/doctrine/drg/test_extractor_asset.py`.
- **Requirements**: FR-007 (extractor), FR-012 (`_SUFFIX_TO_KIND`).
- **Subtasks**: T019–T021.
- **Dependencies**: WP01
- **Prompt**: [tasks/WP05-extractor-suffix.md](./tasks/WP05-extractor-suffix.md)

## WP06 — Charter-cascade exhaustiveness + `context.py:500`

- **Goal**: cover every charter-layer kind-keyed map/filter for both new members, including the 4th TEMPLATE-exclusion filter and the `.get`-partials.
- **Priority**: P1. **Independent test**: `pytest tests/charter/test_kind_cascade_exhaustive.py tests/charter/test_drg_filtering.py`.
- **Requirements**: FR-012 (charter cascade).
- **Subtasks**: T022–T026.
- **Dependencies**: WP01
- **Risk**: `context.py:500` is a comprehension the totality guard won't catch — WP06 owns it explicitly.
- **Prompt**: [tasks/WP06-charter-cascade-exhaustiveness.md](./tasks/WP06-charter-cascade-exhaustiveness.md)

## WP07 — Core exhaustiveness + totality guard

- **Goal**: fix the dropped-asset-node return + the remaining core maps; add the C-005 totality guard with the `.get`-partial exemption.
- **Priority**: P1. **Independent test**: `pytest tests/doctrine/drg/test_kind_mapping_totality.py tests/doctrine/test_drg_relations.py`.
- **Requirements**: FR-012 (query/executor/template_catalog + guard).
- **Subtasks**: T027–T030.
- **Dependencies**: WP01, WP02, WP03, WP04, WP05, WP06
- **Risk**: the guard requires every mapping site already total; a naive "every dict must be total" guard false-fails on 4 pre-existing partials — the exemption must be proven.
- **Prompt**: [tasks/WP07-core-exhaustiveness-totality-guard.md](./tasks/WP07-core-exhaustiveness-totality-guard.md)

## WP08 — E2E fixture + no-regression

- **Goal**: a Regnology-shaped org-pack fixture (template node + edge + asset) loads/graphs/validates; negative cases fail loud; the 9 existing kinds are unchanged and the full suites are green.
- **Priority**: P0 (the acceptance gate). **Independent test**: `pytest tests/doctrine/test_template_asset_e2e.py` then the full doctrine/DRG/charter/pack-validator suites.
- **Requirements**: NFR-001, NFR-004 (+ exercises FR-004/FR-008 end-to-end).
- **Subtasks**: T031–T033.
- **Dependencies**: WP01, WP02, WP03, WP04, WP05, WP06, WP07
- **Prompt**: [tasks/WP08-e2e-fixture-no-regression.md](./tasks/WP08-e2e-fixture-no-regression.md)
