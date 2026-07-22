# Pre-plan grounding — consolidate-charter-bundle (3-lens squad, 2026-07-18)

Consolidated from paula-patterns (consumer/writer surface), architect-alphonso (schema + WP-DAG + landmines), curator-carla (foldability + campsite + docs). Seeds `/plan`.

## Foldability — NO FOLDS
- **#2554** (bdd-scenario-lifecycle parity warning) — **already fixed** (all profiles corrected; `tests/architectural/test_template_governance_payload_contract.py` → 10 passed; phantom DRG node gone; different parity axis anyway). → verify + **close as already-remediated**, out of scope.
- **#2373** (build_charter_context dirty-tree) — **strictly follow-up** (doctrine-synthesis pipeline `synthesizer/write_pipeline.py`, orthogonal; under #1914 umbrella). Optional cheap no-op-stability guard only if a WP already sits on the `build_charter_context` first-load read path. Keep tracked.

## ADDENDUM (2026-07-18, post-operator-decision) — charter.yaml OWNS activation

The keystone below was RESOLVED by the operator: **charter.yaml is the project charter and OWNS activation** (relocate `activated_*` out of `.kittify/config.yaml`), pack-shaped, overlaying `default.yaml` (layer-0). ADR 2026-07-18-1 §Decision Outcome points 1–2 updated; spec C-005 flipped + C-008 fence added; FR-012/013/014 + US7 + SC-008 added. This EXPANDS the mission with an activation-engine WP.

**New surface to add (WP-cluster ~"WP-I activation relocation", tidy-first BEFORE or WITH WP-A schema):**
- `src/charter/pack_manager.py` — `commit_plan` (activation writer, `:448/519`), `merge_defaults` (`:703-755`, second writer), `_save_config` → re-point activation WRITE to `charter.yaml`.
- `src/charter/pack_context.py` — `PackContext.from_config` (`:230-271`, activation READ + `_BUILTIN_*` fallback) → read activation from `charter.yaml`; keep the fail-closed contract (`:223-241`); resolve absent key from `default.yaml` (`load_default_pack_activation_ids`).
- `.kittify/config.yaml` — remove `activated_*` section (keep `agents:` + non-doctrine); migration moves it into `charter.yaml`.
- Overlay: `charter.yaml` = project-tier charter overlaying layer-0 `src/charter/packs/default.yaml` (existing `pack_roots` overlay / `DoctrineLayerCollisionWarning`, ADR 2026-05-16-1).
- The `charter.yaml.activation`/`activated_*` section uses the SAME vocabulary as `default.yaml` (`activated_kinds`, `mission_type_activations`, `activated_directives/tactics/...`).
- **Behavior-preserving:** the activation-parity + DRG-filter suites (`tests/doctrine/test_activation_parity_guard.py`, `filter_graph_by_activation` tests, `tests/**/test_pack_context*.py`, `test_activation_engine*.py`) must stay green — this is a surface relocation, not a semantics change.
- **Fenced OUT (C-008):** ADR 2026-07-15-1 runtime activation-gating + first-class DRG nodes for mission_type/gate/asset.
- The `catalog` section stays a derived-but-committed projection (parity + freshness keep it honest); governance/directives/activation are authored.

## THE central open design decision (for /plan — expensive to reverse) [RESOLVED — see addendum]
**Manifest tracked-vs-derived + where authorable governance knobs live + charter.yaml git-class.**
- `CharterBundleManifest._validate` (`bundle.py:83-89`) forbids a path being both tracked and derived; every `derivation_sources` value must be a tracked source. Today: `tracked=[charter.md]`, `derived=[triad]`.
- Post-inversion: `charter.yaml` is authoritative/authorable (C-001) → must be **git-tracked**; but the triad it replaces is `GitClass.IGNORED` (`state/contract.py:442-462`), and nothing "derives" charter.yaml anymore.
- Wrinkle: charter.yaml is **part-authored** (governance/directives = hand-authorable) + **part-derived** (the `catalog`/references section is a config-activation+DRG transitive-closure projection, compiler-built — NOT hand-authored).
- **Recommendation (to confirm with operator):** `charter.yaml` is **git-TRACKED, single file**; governance/directives authored; the `catalog` section is a derived-but-committed projection kept honest by the existing config↔catalog **parity** check (`consistency_check.py`) + **freshness** content-hash. Repurpose the manifest's `derived_files`/`derivation_sources` from "generated & gitignored" to "content-hash input set." Do NOT split the catalog into a separate file (that re-creates the split-brain the mission removes). Do NOT carry a self-referential `charter_hash` inside charter.yaml (§ landmine 2).

## Landmine 2 — charter_hash self-reference
`_compute_charter_source` (`computer.py:270`) + `hasher.py:45,58` + `sync.py:342-343,387-388` compare charter.md SHA vs `metadata.yaml::charter_hash`. Inverted, charter.md is a never-resolving companion → this staleness mechanism is the OLD model. Retire `charter_source` staleness or re-home the hash externally (synthesis manifest already holds `bundle_content_hash`). A hash of charter.yaml cannot live inside charter.yaml (chicken-egg). WP-E.

## charter.yaml schema (from the real field shapes)
Reuse existing pydantic models as nested sub-models of a new `CharterYaml` (`src/charter/schemas.py`):
```yaml
schema_version: "2.0.0"
governance: {...}      # verbatim GovernanceConfig (schemas.py:124): testing/quality/commits/performance/branch_strategy/doctrine{selected_*,available_tools,template_set,authority_paths,governance_references}/activations[]/enforcement{}
directives: [...]      # DirectivesConfig (schemas.py:166): id,title,description,severity,references
catalog:               # references.yaml body — DERIVED projection
  mission, template_set, languages[], references[]{id,kind,title,summary,source_path,local_path}
activation: {source: .kittify/config.yaml}   # C-005 REFERENCE ONLY; config.yaml activated_* stays authority
metadata: {generated_at, bundle_schema_version: 2}   # keep bundle_schema_version (versioning.py:176 reads it); RETIRE charter_hash/extraction_mode/sections_parsed
```
Manifest bump (`bundle.py`): `SCHEMA_VERSION "1.0.0"→"2.0.0"`; `BUNDLE_CONTENT_HASH_FILES (4)→("charter.yaml",)` (single point re-targeting the #2732 hash — feeds write stampers `write_pipeline.py:685`/`resynthesize_pipeline.py:205` + reader `computer.py:475` via one recipe). **New `charter.yaml` filename = ONE shared constant** consumed by bundle/sync/compiler/consistency_check/migration (do NOT re-scatter — the four names are today duplicated in `bundle.py:36-51` Path-form + `sync.py:43-44` str-form; unify).

## Consumers the spec's FRs MISSED (add to FR-005 re-point set — split-brain hazards)
- `src/charter/mission_type_profiles.py:966 _project_has_doctrine_overrides` → `governance.yaml`, **DECISION** (mission-type hard-fail gate). Bypasses loaders.
- `src/doctrine/spdd_reasons/activation.py:36-37,62 _governance_selects_pack` → `governance.yaml`+`directives.yaml`, **DECISION** (SPDD pack activation). Has a cache (`clear_activation_cache`) to invalidate.
- `src/doctrine/versioning.py:166 read_bundle_schema_version` → `metadata.yaml` schema-version gate — repoint to charter.yaml.
- `src/charter/sync.py:224 post_save_hook` — auto-syncs on charter.md write; must be REMOVED with the scrape (nothing to scrape post-retirement).
- `src/charter/compact.py` (section anchors) — ensure in the display WP owned_files (FR-008 named context.py, not compact.py).
- `src/specify_cli/cli/commands/charter_bundle.py:68-78 _OUT_OF_SCOPE_WARNINGS` special-cases references.yaml — update with the moot-stopgap cleanup.

## Two chokepoint loaders (re-pointing these covers most decision reads)
`sync.py:307 load_governance_config`, `sync.py:356 load_directives_config`. Keep their SIGNATURES stable so the many callers (resolver.py:310, context.py:835/2549/2990, _status_collectors.py:122) auto-follow. The **6 direct bypass readers** above do NOT funnel through them — repoint explicitly.

## Recommended WP clusters (tidy-first, one branch, non-overlapping owned_files)
DAG: A → B → C → {D, E} → F ; G independent(P2); H (docs) parallel, lands same PR.
- **WP-A keystone:** `schemas.py` (CharterYaml model) + `bundle.py` (manifest v2, hash-list, shared filename constant). Unblocks all.
- **WP-B writer + #2772 clobber guard:** `compiler.py` (charter.yaml emit seeded from triad+catalog; remove/guard `:421` clobber writer; retire references writer `:1218`) + `cli/commands/charter/generate.py` (autotrack) + `cli/commands/charter_bundle.py`. **Must regenerate+commit spec-kitty's own charter.yaml here** or downstream re-points fail on this repo.
- **WP-C decision repoint + scrape retire (owns ALL of sync.py + extractor.py):** loaders→charter.yaml; delete `sync()` scrape + `post_save_hook`; delete `SECTION_MAPPING`/`write_extraction_result`/dead `extract_with_ai:807`; + the bypass readers `mission_type_profiles.py:966`, `spdd_reasons/activation.py`, `_doctrine_collect.py:555`; + parity `consistency_check.py:420` (FR-004, re-home #2530 fail-closed).
- **WP-D display repoint:** `context.py` (display prose call-sites only — decision loader-calls auto-follow) + `compact.py` + `context_renderers/section_bodies.py`.
- **WP-E freshness:** `charter_runtime/freshness/computer.py` (charter.yaml hash; rework/retire `_compute_charter_source` charter.md-hash staleness) + retire #2758 `first_missing_bundle_file`/#2759 parity read.
- **WP-F migration + fail-loud + state:** new `upgrade/migrations/m_*.py` (fold body pattern = `doctrine/versioning.py:299 migrate_v1_to_v2`, NOT the rc35 refresh-only shape; idempotent; fail-loud) + `state/contract.py:420-462` (add charter.yaml surface, retire four) + `.gitignore` + `versioning.py:166` repoint.
- **WP-G language tier-3 (FR-009, P2, independent):** `language_scope.py` solely (tier-3 charter.md fallback → catalog.languages).
- **WP-H docs/skills/snapshots (load-bearing, C-006):** `docs/context/charter-overview.md` + `governance-files.md` (HARD contradictions: "charter.md is THE runtime source"), `docs/api/charter-commands.md`, `docs/architecture/06_unified_charter_bundle.md`, `src/doctrine/skills/spec-kitty-charter-doctrine/*`, `src/doctrine/missions/mission-steps/software-dev/charter/prompt.md`, baseline snapshots (`tests/specify_cli/regression/_twelve_agent_baseline/*`, `tests/specify_cli/skills/__snapshots__/*`).

## Campsite (per-WP)
ruff C901 clean on all god-surfaces (nothing over 15). SAFE cleanups where the WP already edits: delete dead `extract_with_ai:807` (WP-C); unify the duplicated filename constants (WP-A); ADJACENT on context.py (touch only prose-read call-sites). Sonar not reachable via wired MCP (wrong project) — ruff/grep census only.

## Test clusters (→ WP owned_files)
- WP-A: `tests/charter/test_bundle_manifest_model.py`, `tests/cli/commands/test_charter_bundle_coverage.py`.
- WP-B: `test_charter_generate_autotrack.py`, compiler write tests, `tests/agent/cli/commands/test_charter_cli.py` (INVERT clobber tests → assert prose survives).
- WP-C: `test_charter_resynthesize.py`, `tests/architectural/test_charter_references_resolve.py`, `tests/charter/test_references_missing_failclosed.py`, `tests/doctrine/test_activation_parity_guard.py`.
- WP-E: `tests/specify_cli/charter_freshness/test_computer.py`, `test_freshness_hash_unification.py`, `test_preflight_one_pass.py`, `test_freshness_activation_visibility.py`, `tests/integration/test_charter_status_freshness.py`.
- WP-F: `tests/upgrade/test_unified_bundle_migration.py`, `test_charter_rename_migration.py`, `tests/specify_cli/test_state_contract.py`, `test_state_gitignore_migration.py`, `tests/cli/commands/test_charter_io.py`.
- WP-G: `tests/charter/test_language_scope.py`.
- WP-H: baseline/snapshot fixtures under `tests/specify_cli/regression/_twelve_agent_baseline/`, `tests/specify_cli/skills/__snapshots__/`, `test_worktree_charter_via_canonical_root.py`.

## Fences / discipline
- C-002 layer boundary: `src/charter/` no `specify_cli` import; migration lives in `specify_cli.upgrade.migrations` (correct direction); parity read stays in `specify_cli.charter_runtime`. `test_shared_package_boundary.py` guards.
- C-003 fail-loud: require-canonical charter.yaml; re-home #2530 fail-closed; NO `if not exists: read-legacy` branch survives.
- NFR-005 no half-inverted ship: WP-C→D/E ordering hard (if extractor retires before loaders repoint, `sync()` stops writing the triad and un-repointed loaders return empty `GovernanceConfig()` silently — governance lost, no error). Sequence strictly.
- Two `metadata.yaml`: `.kittify/metadata.yaml` (project identity — DO NOT TOUCH) vs `.kittify/charter/metadata.yaml` (bundle — migrate). Migration must target only the charter one.
- Pre-push: `pytest tests/architectural/test_no_legacy_terminology.py` before the doc/prose rewrites (CI-only gate).
