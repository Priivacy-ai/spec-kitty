# Activation Topology Map — M2b `charter-activation-split` (FROZEN, pre-edit)

**Status**: Awaiting operator approval. **No `git mv` until approved.** Frozen against merged `main` `34790048ed` (M1 + M2 + landing pass). Authority: ADR `2026-08-22-2` §5; M2 map MAP-000/C01-C12; facade contract `charter-mediated-doctrine-selection-01KRTZCA`. Informed by the M2b brownfield scout.

**Goal**: make the C-004 boundary a real package wall — relocate the activation-side charter modules into `src/charter/activation/`, make `charter/__init__.py` lazy, close all importers, collapse the C-004 gate to `charter.activation.*`.

**Scale (census)**: 66 top-level `charter/*.py` + subpackages. **355 files** import an activation module by `charter.<name>` (75 `src/`, 239 tests, 40 charter-internal). Latent offering→activation violations: **0** (boundary already holds in practice).

## MAP-A — three-way partition

### STAY top-level `charter.*` — 13 offering facades (MAP-C12 binding; moving them breaks runtime→charter→offering)
`pack_paths`, `provenance`, `template_catalog`, `versioning`, `primitives`, `profiles`, `mission_steps`, `missions`, `model_routing`, `glossary_packs`, `spdd_reasons`, `assets`, `repository_protocol` — pure re-exports of `charter.offering.*`, unchanged.

### STAY top-level `charter.*` — shared primitives (neither layer owns)
`parser`, `bundle`, `hasher`, `__init__` (gets the lazy conversion, MAP-B), `resolution` (git-root resolver + offering-facade — layer-neutral).

### MOVE → `src/charter/activation/`
- **MAP-000 named**: `activation_engine`, `_activation_render`, `activations`, `cascade`, `kind_vocabulary`, `pack_manager`, `pack_context`, `compiler`, `context`, `context_json`, `context_contract`, `context_state`, `context_result_builders`, `interview`, `sync` (CR-01 rides along), `default_pack`, `scope`, `scope_router`, `org_expected_artifacts`, `org_extends`, `org_pack_discovery`, `resolver` (activation wrapper — MAP-C06, NEVER merged with `offering/resolver`), `exceptions` (`CharterActivationError`), `schemas` (charter Directive).
- **Derived activation internals** (0 external importers, transparent): `catalog`, `_catalog_miss`, `_io`, `_doctrine_paths`, `charter_md_parsing`, `charter_yaml_io`, `compact`, `_diagnostics`, `_drg_helpers`, `doctrine_service_builder`, `action_grain`, `action_doctrine_bundle`, `governance_references`, `invocation_context`, `language_scope`, `mission_type_key`, `mission_type_profiles`, `mission_type_profile_repository`, `profile_resolution`, `progressive_disclosure`, `reference_resolver`, `consistency_check`, `template_resolver`.
- **Subpackages**: `synthesizer/**` (MAP-000 explicit) → `activation/`.

## MAP-A-DECISION — two operator calls (block the map freeze)

- **DEC-1 — `drg.py` hybrid (89 importers, the single largest surface).** It is BOTH an offering-type re-export facade (`ArtifactKind`, `DRGNode`, `NodeKind`) AND activation logic (`filter_graph_by_activation`, `load_org_drg`, `merge_three_layers`). **Recommendation: SPLIT** — the offering-type re-exports stay as a top-level `charter.drg` facade; only the activation logic moves to `activation/`. Alternative (MAP-000 literal): move the whole module → then 89 callers wanting a pure offering type reach it *through* the activation package (allowed direction, inverted semantics).
- **DEC-2 — 5 subpackages not in MAP-000's explicit list**: `context_renderers/` (15), `evidence/` (4), `neutrality/` (2), `corpus/` (1), `packs/` (1). Scout default: → `activation/` (charter-internal, small). Confirm, or a neutral top-level home.

## MAP-B — lazy `charter/__init__.py`
Replace the 15 eager `from .X import Y` blocks with a PEP-562 `__getattr__` lazy re-export table (`_LAZY: name → owning submodule`), caching into `globals()` on first access (the `src/doctrine.py` / `runtime/next/__init__.py:15-28` shape). `__all__` kept verbatim. **All 15 verified free of import-time side effects → safe.** Effect: `import charter.offering.*` no longer drags the activation layer (un-xfails `test_interview_mapping_mission_alias`). Does NOT fix deep-path imports (MAP-C).

## MAP-C — importer closure (355 files)
Deep-path `from charter.<name> import …` breaks on the move (lazy `__init__` doesn't help deep imports). **Rewrite call sites to `charter.activation.<name>`**: 75 `src/` (occurrence-map governed bulk edit) + 239 tests (same pass). The 40 charter-internal importers travel with the move — **relative** imports (`from .compiler import`) survive; only absolute `charter.X` self-references re-point. Thin top-level shims ONLY if an external/serialized surface needs one (none found — CR-01 rides inside `sync.py`; its 58 callers are deep-path rewrites).

## MAP-D — C-004 gate collapse
`tests/architectural/test_charter_offering_does_not_import_activation.py`: shrink `_ACTIVATION_MODULES` to `{"charter.activation"}` (the subpackage rule catches all `charter.activation.*`); no orphan stays forbidden (all 4 interim entries move). Keep the level-aware walker + `tmp_path` non-vacuity cases unchanged.

## MAP-E — shims unaffected
`src/doctrine.py` (CR-06) re-exports only `charter.offering` — untouched. CR-02..07 target offering/config/URN/path surfaces, not activation module paths — no CR shim breaks.

## Sequencing (execution order)
1. **DEC-1/DEC-2 resolved** → freeze this map.
2. Split `drg.py` (if DEC-1=split) before the bulk mv.
3. Lazy `__init__` (MAP-B) — proves the eager-drag gone independent of the move.
4. `git mv` the activation set → `activation/` (relative imports intact).
5. Rewrite the 75 `src/` + 239 test deep-path callers (occurrence-map governed).
6. Collapse the C-004 gate (MAP-D); un-xfail the roster test.
7. **Full-sweep verify** — arch shards + docs freshness + terminology baselines (the M2 landing-pass blind spot), not just affected trees.

**Approval requested**: MAP-A partition, DEC-1 (drg split), DEC-2 (5 subpkgs → activation), and MAP-C (rewrite call sites, not shims). On approval, execution begins at step 2.

---

## Census refresh (landing, 2026-08-30 — rebase base `16aba180f1`)

The MAP-C census above is **frozen against `34790048ed`**. The landing pass
rebased this mission onto `16aba180f1` (17 commits ahead, incl. #3804 and
#3806 governance-at-the-gate). Re-running the deep-path importer census
(`from|import charter.<moved-module>` + mock-target string literals, over
`src/` and `tests/`) against the new base found the frozen 355/66 census had
drifted: **#3806 added deep-path call sites outside it** —

- 5 new `tests/charter/` files (`test_enforcement_lattice`,
  `test_decision_documentation_on_implement`, `test_action_bundle_tension_arbiters`,
  `test_directive_003_implement_to_review`, incl. two `patch("charter._drg_helpers…")`
  mock targets), and
- 5 additional function-local self-imports inside `consistency_check.py`
  (`charter._drg_helpers`, `charter.doctrine_service_builder`,
  `charter.context_state`) — the base had 3, main carried 8.

All were re-pointed to `charter.activation.*` in the landing folds
(`fix(landing): re-point #3806 census-drift importers…`,
`docs(landing): re-point shipped charter import samples…`). Post-refresh the
deep-path straggler count to any moved module is **0** across `.py` imports,
`.py` mock-target string literals, and the shipped `.md` code samples. The
frozen 355/66 counts are left as the historical MAP-C snapshot; this addendum
is the authoritative post-rebase delta.
