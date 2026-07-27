# Implementation Plan: Consolidate the Compiled Charter Bundle

**Branch**: `feat/consolidate-charter-bundle` | **Date**: 2026-07-18 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `kitty-specs/consolidate-charter-bundle-01KXSYB9/spec.md`; governing decision [ADR 2026-07-18-1](../../docs/adr/3.x/2026-07-18-1-charter-yaml-authoring-authority-and-extractor-retirement.md).

## Summary

Make `charter.yaml` the project **charter**: one git-tracked, authorable, pack-shaped structured artifact that OWNS the project's active doctrine — governance knobs, directive declarations, the resolving/artifact-ID catalog, and the **project activation state + overrides** — overlaying the layer-0 `default.yaml` pack. It subsumes the four compiled bundle files (`governance.yaml`, `directives.yaml`, `metadata.yaml`, `references.yaml`) and absorbs the activation state relocated out of `.kittify/config.yaml`. `charter.md` becomes a hand-authored curated companion (never a resolving input, never clobbered); the deterministic prose→triad extractor is retired. Delivered as one branch/PR, tidy-first, with no half-inverted intermediate state.

Technical approach is behavior-preserving except three intentional changes: the freshness signal now reflects charter mutations (single-file content hash), the bundle collapses four files → one, and the governance/directive/activation authoring surface moves from prose (`charter.md` + `config.yaml`) to a structured `charter.yaml`. Empirically de-risked (`research/charter-authority-inversion-assessment.md`): the "AI extractor" is dead code (extraction is deterministic regex), governance prose is display-only, and seeding `charter.yaml` from the existing structured YAML is a lossless yaml→yaml fold.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: pydantic (charter models), ruamel.yaml (comment-preserving round-trip), typer/rich (CLI), pytest, mypy, ruff
**Storage**: On-disk YAML/Markdown under `.kittify/charter/` + `.kittify/config.yaml`; git as the tracked-artifact store
**Testing**: pytest — `tests/charter/`, `tests/specify_cli/charter_runtime/`, `tests/specify_cli/charter_freshness/`, `tests/doctrine/test_activation_parity_guard.py`, `tests/architectural/` (incl. `test_shared_package_boundary.py`, `test_no_legacy_terminology.py`, migration + state-contract suites)
**Target Platform**: Cross-platform CLI (Linux/macOS/Windows), Python 3.11+
**Project Type**: single (Python package + doctrine assets + docs)
**Performance Goals**: No new hot-path subprocess on the default freshness read (NFR-002); migration is one-pass idempotent (NFR-003)
**Constraints**: ruff + mypy --strict clean, zero new suppressions; complexity ≤15; #2732 content-identity preserved (NFR-001); C-002 layer boundary (`src/charter/` ↛ `specify_cli`); fail-loud, no legacy-file fallback (C-003); one branch/PR, no half-inverted ship (NFR-005/C-006)
**Scale/Scope**: ~13 primary source surfaces + ~9 consumer/writer modules + migration + docs/skills; 15 FRs; 9 implementation concerns

## Charter Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Loaded via `spec-kitty charter context --action plan` (compact mode). Relevant binding items and this plan's compliance:

- **Single canonical authority** — the mission's *purpose* is to collapse a split-brain onto one authority (`charter.yaml`). The one expensive-to-reverse decision (manifest tracked/derived semantics + activation ownership) is recorded in ADR 2026-07-18-1 and pinned in `data-model.md`. ✅
- **Architectural gate discipline** — the layer boundary (`src/charter/` ↛ `specify_cli`) is enforced by `test_shared_package_boundary.py`; the migration lives in `specify_cli.upgrade.migrations` and the freshness parity read in `specify_cli.charter_runtime` (correct direction). ✅
- **Canonical sources** — reuse `CharterBundleManifest`, the existing pydantic models, the doctrine migration framework, and the `pack_roots` overlay; do not hand-roll parallels. ✅
- **ATDD-first / red-first** — each concern reproduces through its pre-existing entry point (charter compile/generate, `compute_freshness`, `PackContext.from_config`, the migration runner) before the change. ✅
- **Mission tracer files** — seeded at planning (`traces/`). ✅
- **Fail-loud** (DIRECTIVE / "no legacy resolver paths") — re-home the #2530 fail-closed errors onto `charter.yaml`; no `if not exists: read-legacy` branch survives. ✅

No unjustified violations. The one justified complexity (mission width) is tracked below.

## Project Structure

### Documentation (this mission)

```
kitty-specs/consolidate-charter-bundle-01KXSYB9/
├── plan.md              # This file
├── spec.md              # Mission spec (reshaped for inversion + activation ownership)
├── research.md          # Phase 0 — decisions consolidated from the assessment + squad
├── data-model.md        # Phase 1 — charter.yaml schema + the TWO pinned landmines
├── quickstart.md        # Phase 1 — validation walkthrough
├── contracts/           # Phase 1 — charter.yaml schema, manifest v2, migration contract
├── research/            # Grounding artifacts (assessment, pre-plan grounding)
├── traces/              # Mission tracer files (verification / decisions / risks)
└── tasks.md             # Phase 2 — /spec-kitty.tasks (NOT created here)
```

### Source Code (repository root)

```
src/charter/
├── schemas.py                    # IC-02: new CharterYaml model (nests GovernanceConfig/DirectivesConfig)
├── bundle.py                     # IC-02: CharterBundleManifest v2; content-hash → charter.yaml; shared filename const
├── compiler.py                   # IC-03: emit charter.yaml; remove/guard the :421 clobber; retire references writer
├── sync.py                       # IC-04: loaders → charter.yaml; delete backward scrape + post_save_hook
├── extractor.py                  # IC-04: delete SECTION_MAPPING + write_extraction_result + dead extract_with_ai
├── consistency_check.py          # IC-04: parity reads charter.yaml catalog; re-home #2530 fail-closed
├── context.py / compact.py /     # IC-05: display prose consumers re-pointed
│   context_renderers/section_bodies.py
├── language_scope.py             # IC-08: tier-3 charter.md fallback → catalog.languages
├── activation_engine.py          # IC-01: commit_plan:359 (real write primitive; diagnostics re-word)
├── pack_manager.py               # IC-01: merge_defaults / _save_config → charter.yaml (shared helper)
├── pack_context.py               # IC-01: from_config reads flat activation from charter.yaml (via pointer)
├── consistency_check.py          # IC-04: :199 activation-list read + :420 catalog read → charter.yaml
└── mission_type_profiles.py      # IC-04: _project_has_doctrine_overrides bypass reader → charter.yaml

src/doctrine/
├── spdd_reasons/activation.py    # IC-04: governance/directives bypass reader (+ cache invalidation)
└── versioning.py                 # IC-07: read_bundle_schema_version → charter.yaml
    skills/spec-kitty-charter-doctrine/*, missions/mission-steps/software-dev/charter/prompt.md  # IC-09

src/specify_cli/
├── charter_runtime/freshness/computer.py   # IC-06: charter.yaml hash; rework _compute_charter_source; retire #2758/#2759
├── upgrade/migrations/m_*.py                # IC-07: legacy → charter.yaml fold (idempotent, fail-loud)
├── state/contract.py                        # IC-07: charter.yaml git-class; retire the four
└── cli/commands/charter/{generate.py, _synthesis.py, _status_collectors.py}, charter_bundle.py, _doctrine_collect.py

docs/  # IC-09: context/charter-overview.md, context/governance-files.md, api/charter-commands.md, architecture/06_unified_charter_bundle.md
.kittify/config.yaml  # IC-01: activated_* removed (keeps agents/tooling)
.gitignore            # IC-07: four bundle-file entries removed; charter.yaml tracked
```

**Structure Decision**: single Python package. Work is concentrated in `src/charter/` (the charter layer), with consumers in `src/specify_cli/` and `src/doctrine/`, plus docs/skills. Concerns are sliced so each shared "god file" (`sync.py`, `compiler.py`, `context.py`, `bundle.py`, `generate.py`) is owned by exactly one concern (see ICM), preserving non-overlapping `owned_files` for the WPs `/tasks` will derive.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Mission width (9 concerns incl. activation-engine relocation, in one PR) | Operator-confirmed one-branch/one-PR delivery (C-006) so no half-inverted state ships; the charter.yaml schema is the expensive-to-reverse artifact and must be cut once (avoids the second schema bump #2519 exists to end) | Splitting into multiple PRs would ship a half-inverted charter (schema authoritative but consumers/extractor inconsistent) — the exact NFR-005 failure this constraint forbids |

## Implementation Concern Map

> Concerns are NOT work packages. `/spec-kitty.tasks` translates these into WPs with non-overlapping `owned_files`. Each shared god-file is assigned to exactly one concern so ownership does not overlap.

### IC-02 — charter.yaml schema + manifest keystone

- **Purpose**: Define the `CharterYaml` pydantic model (nesting the existing `GovernanceConfig`/`DirectivesConfig`) and bump `CharterBundleManifest` to v2 so `charter.yaml` is the single tracked artifact and the content-hash input set. Unblocks everything.
- **Relevant requirements**: FR-001, FR-002, NFR-001, C-004
- **Affected surfaces**: `src/charter/schemas.py` (`CharterYaml` model, flat activation fields), `src/charter/bundle.py` (manifest v2 + new `content_hash_files` field), the shared `charter.yaml` filename constant, **and the shared `load→mutate-owned-section→round-trip-save` write helper** (owned here; consumed by IC-01/IC-03 — INV-9)
- **Sequencing/depends-on**: none (keystone, first)
- **Risks**: **Landmine 1 (renata M2 / alphonso MAJOR-1)** — `_validate` forbids tracked∩derived. `charter.yaml` ∈ `tracked_files`; keep it OUT of `derived_files` (which becomes `[]`); the content-hash input set is a **distinct `content_hash_files` field** = `[charter.yaml]` — so `_validate` stays untouched (do NOT relax the disjointness rule). `SCHEMA_VERSION 1.0.0→2.0.0`; `BUNDLE_CONTENT_HASH_FILES (4)→("charter.yaml",)`. Do NOT re-scatter the filename constant (today duplicated in `bundle.py`/`sync.py`). The shared write helper makes section-preservation structural (Landmine 3 / MAJOR-3).

### IC-01 — Activation relocation (charter.yaml owns activation)

- **Purpose**: Relocate the flat activation keys (`activated_*` / `activated_kinds` / `mission_type_activations`) out of `.kittify/config.yaml` into `charter.yaml` (**flat at root**, matching `default.yaml`); re-point the activation engine and reader; resolve `charter.yaml` via the `config.yaml` `charter:` pointer.
- **Relevant requirements**: FR-012, FR-013, FR-014, FR-015, C-005, SC-008
- **Affected surfaces**: `src/charter/activation_engine.py` (`commit_plan:359` — the real write primitive; re-word its `config.yaml`-specific diagnostics/error strings; it is data-source-agnostic so a flat-root charter.yaml needs no functional change), `src/charter/pack_manager.py` (`merge_defaults`, `_save_config` — via the shared write helper), `src/charter/pack_context.py` (`PackContext.from_config` / `_load_config` — resolve charter.yaml via the `charter:` pointer then read flat activation from it; `org_packs` stay in config → two-file read), `.kittify/config.yaml` (activation keys removed; single `charter:` pointer added)
- **Sequencing/depends-on**: IC-02 (needs the charter.yaml activation schema + the shared write helper)
- **Landmine (paula BLOCKER-1/MAJOR-1)**: activation is FLAT at charter.yaml root (not nested) so `_read_activated_*` + `commit_plan` operate unchanged. `_load_config` absent→`{}` branch must distinguish "pointer present, charter.yaml missing" (raise, INV-5) from "no config at all" (default-pack fallback). Do NOT convert an absent key into `[]` (would flip all-active→none — SC-008).
- **Design note (config pointer)**: `config.yaml` keeps a one-line `charter:` pointer so the resolver locates `charter.yaml` deterministically and a charter swap (experiment / local redirect / cross-project) is a one-line change — keeping churny activation edits out of `config.yaml` (fewer multi-user merge conflicts).
- **Resolution flow**: the config → charter.yaml → pack.yaml → active-DRG chain (the charter module aggregating all doctrine artefacts into one consistent active DRG) is diagrammed in [`contracts/active-doctrine-resolution.md`](./contracts/active-doctrine-resolution.md) (Mermaid sequence + layering). IC-01/IC-04 realize it; `filter_graph_by_activation` behavior stays byte-preserved (C-008 fence).
- **Risks**: Biggest new blast radius. Preserve the fail-closed contract (`pack_context.py:223-241`) and the default-pack fallback (`load_default_pack_activation_ids`); explicit empty list stays fail-closed. Behavior-preserving — `tests/doctrine/test_activation_parity_guard.py` + pack_context/activation_engine suites must stay green. C-008 fences the ADR 2026-07-15-1 runtime-gating/DRG-node restructure OUT.

### IC-03 — charter.yaml writer + #2772 clobber guard

- **Purpose**: Emit `charter.yaml` from the compile pipeline (seeded deterministically from triad + catalog + activation); remove/guard the `compiler.py:421` `charter.md` clobber so `charter.md` is companion-only; retire the `references.yaml` writer.
- **Relevant requirements**: FR-001, FR-007, FR-011
- **Affected surfaces**: `src/charter/compiler.py` (`write_compiled_charter`, `:421`, `_write_references_yaml`), `src/specify_cli/cli/commands/charter/generate.py` (autotrack), `src/specify_cli/cli/commands/charter_bundle.py`
- **Sequencing/depends-on**: IC-02 (schema + shared write helper)
- **Risks**: Three FRs converge on `write_compiled_charter` — one owner. Must regenerate + commit spec-kitty's own `charter.yaml` here or downstream re-points fail on this repo. Invert the clobber tests to assert prose survives. **Landmine 3 (alphonso MAJOR-2)** — the charter.yaml write MUST be a **partial/merge write** (via the IC-02 shared helper): refresh only the DERIVED `catalog`+`metadata`; preserve AUTHORED `governance`/`directives`/`activation`/`overrides` byte-for-byte (ruamel round-trip). Treat `activation` as read-only input (no catalog←activation round-trip circularity). Regression test: authored governance/activation survives `charter generate --force`.

### IC-04 — Decision-path re-point + extractor retirement

- **Purpose**: Re-point every governance/directive/parity DECISION reader to `charter.yaml`; delete the prose→triad scrape and the dead AI stub.
- **Relevant requirements**: FR-004, FR-005, FR-006
- **Affected surfaces**: ALL of `src/charter/sync.py` (loaders `:307/:356` → charter.yaml; delete `sync()` scrape + `post_save_hook:224`) + ALL of `src/charter/extractor.py` (delete `SECTION_MAPPING:46`, `write_extraction_result`, dead `extract_with_ai:807`); bypass readers `src/charter/mission_type_profiles.py` (`_project_has_doctrine_overrides` — re-verify line, ~:598/:975), `src/doctrine/spdd_reasons/activation.py` (+ `clear_activation_cache`), `src/specify_cli/cli/commands/_doctrine_collect.py:555`; parity `src/charter/consistency_check.py` — re-point **BOTH** `_load_raw_activation_lists:199-200` (activation lists — paula MAJOR-2, easy to miss) **and** `_load_reference_ids_by_kind:420` (catalog) to charter.yaml; re-home #2530 fail-closed onto charter.yaml
- **Sequencing/depends-on**: IC-03 (charter.yaml must be emitted before consumers read it), IC-01 (activation read)
- **Risks**: **NFR-005 hard ordering** — if the extractor retires before the loaders re-point, `sync()` stops writing the triad and un-re-pointed loaders return empty `GovernanceConfig()` SILENTLY (governance lost, no error). Keep loader signatures stable so callers (IC-05 display, resolver) auto-follow.

### IC-05 — Display prose-consumer re-point

- **Purpose**: Re-point the display-only `charter.md`-prose consumers so no governance DECISION reads prose; `charter.md` stays a display/companion surface.
- **Relevant requirements**: FR-008
- **Affected surfaces**: `src/charter/context.py` (prose call-sites: `_extract_policy_summary:274`, `render_critical_section_bodies:1023/2754/2784`), `src/charter/compact.py`, `src/charter/context_renderers/section_bodies.py`
- **Sequencing/depends-on**: IC-04 (decision loaders stable)
- **Risks**: Touch only the prose-read call-sites; the decision loader-calls auto-follow IC-04's signature-stable loaders (keeps `context.py` ownership disjoint from IC-04).

### IC-06 — Freshness on charter.yaml

- **Purpose**: Point the freshness content-hash at `charter.yaml`; rework/retire the `charter.md`-hash staleness mechanism; remove the now-moot #2758/#2759 stopgaps.
- **Relevant requirements**: FR-003, FR-011, NFR-001, NFR-002
- **Affected surfaces**: `src/specify_cli/charter_runtime/freshness/computer.py` (`_BUNDLE_FILES`, `_compute_charter_source:270`, `first_missing_bundle_file` #2758, parity read #2759)
- **Sequencing/depends-on**: IC-02 (manifest/hash recipe)
- **Risks**: **Landmine 2** — `charter_hash` self-reference. `charter.md` is now a never-resolving companion; retire the `charter.md`-hash staleness or re-home the hash externally (synthesis manifest already holds `bundle_content_hash`). Do NOT carry a self-referential `charter_hash` into `charter.yaml.metadata`. Preserve the fresh-seed early-exit + `built_in_only` normalization (#2732). **Spurious authoring-staleness (alphonso MINOR-3)**: authored-only edits (governance) trip a whole-file hash even when the derived catalog is unchanged — decide + test either (a) ground freshness on catalog↔activation parity, or (b) document authored-edits-read-stale as acceptable to the freshness-consuming gates.

### IC-07 — Migration + fail-loud + git-class

- **Purpose**: One-pass idempotent migration folding the four legacy files (+ relocated `activated_*`) into `charter.yaml`; retire the four from emission/manifest/gitignore/state-contract; fail loud on un-migrated projects.
- **Relevant requirements**: FR-010, FR-011, NFR-003, C-003
- **Affected surfaces**: new `src/specify_cli/upgrade/migrations/m_*.py` (fold body pattern = `src/doctrine/versioning.py:299 migrate_v1_to_v2`, NOT the rc35 refresh-only shape), `src/specify_cli/state/contract.py:420-462`, `.gitignore`, `src/doctrine/versioning.py:166 read_bundle_schema_version`
- **Sequencing/depends-on**: IC-01, IC-02, IC-03, IC-04, IC-06 (the migration + retirement lands last so no consumer is orphaned)
- **Risks**: **TWO `metadata.yaml`** — touch ONLY `.kittify/charter/metadata.yaml`; NEVER `.kittify/metadata.yaml` (project identity). Idempotency = charter.yaml present + four absent + no `activated_*` in config → 0 changes. Fail-loud = four-present-no-charter.yaml raises (re-home #2530). **Copy activation lists VERBATIM** — never convert an absent key into `[]` (would flip all-active→none, SC-008); migration test asserts absent-key survives as absent (paula MINOR-2). **Existing activation-writing migrations (paula MAJOR-3)**: `m_unify_charter_activation.py` (encodes the now-REVERSED "config is the activation authority" invariant + promotes INTO config.yaml) and the rc35 pair (`m_3_2_0rc35_default_charter_pack.py`, `m_3_2_0rc35_activate_builtin_mission_types.py`, both write `activated_*` INTO config keyed on absence) — the fold MUST sequence strictly AFTER these seed config, then relocate + remove from config (INV-2), be idempotent against re-seeding, and annotate/reconcile `m_unify_charter_activation`'s reversed invariant.

### IC-08 — Language tier-3 fallback migration

- **Purpose**: Migrate the one behavioral `charter.md`-prose read (doctrine language-scoping tier-3) off prose to `catalog.languages`, so `charter.md` is behaviorally inert.
- **Relevant requirements**: FR-009
- **Affected surfaces**: `src/charter/language_scope.py` (`infer_repo_languages` tier-3, `:101-103`)
- **Sequencing/depends-on**: IC-03 (needs `catalog.languages` in charter.yaml). Otherwise independent (P2).
- **Risks**: Low; a degraded last-resort fallback today. Keep the tier-1 `references`/catalog precedence unchanged.

### IC-09 — Docs / skills / snapshots (consistent whole)

- **Purpose**: Flip every doc/doctrine surface that asserts "charter.md is THE runtime source"; update the charter-doctrine SKILL assets (deployed to consumers) and baseline snapshots — required by C-006 so the PR is a consistent whole.
- **Relevant requirements**: C-006, NFR-004 (terminology guard)
- **Affected surfaces**: `docs/context/charter-overview.md`, `docs/context/governance-files.md` (HARD contradictions), `docs/api/charter-commands.md`, `docs/architecture/06_unified_charter_bundle.md`, `src/doctrine/skills/spec-kitty-charter-doctrine/*`, `src/doctrine/missions/mission-steps/software-dev/charter/prompt.md`, baseline snapshots (`tests/specify_cli/regression/_twelve_agent_baseline/*`, `tests/specify_cli/skills/__snapshots__/*`), `docs/development/*-page-inventory.yaml` (freshen)
- **Sequencing/depends-on**: none for authoring; validate against the landed behavior. Lands in the same PR.
- **Risks**: Run `pytest tests/architectural/test_no_legacy_terminology.py` before pushing prose. ADR 2026-07-18-1 already added to the ADR inventory.

**Folds: NONE.** #2554 is already fixed (verify + close as already-remediated, out of scope). #2373 is a strictly-follow-up doctrine-synthesis-pipeline defect (under #1914). #2772 is folded (FR-007/IC-03).
