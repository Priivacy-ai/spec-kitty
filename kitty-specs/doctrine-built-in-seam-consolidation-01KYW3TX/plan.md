# Implementation Plan: Built-In Doctrine Seam Consolidation

**Branch**: `feat/relocate-builtin-doctrine-packs` | **Date**: 2026-07-31 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `kitty-specs/doctrine-built-in-seam-consolidation-01KYW3TX/spec.md`
**Design basis**: `notes/research-synthesis.md` (4-facet research squad + architecture design pass) — authoritative; not re-derived.

## Summary

Consolidate built-in doctrine **on-disk location** onto a single fail-closed authority and finish the
`packs/built-in` relocation so the "one `resolve_pack_root` seam" claim is literally true and
CI-enforced. Add `built_in_dir(kind)` (per-kind) **and `built_in_root()`** (root) as the two join
authorities; route **all** readers — including the variable-indirected charter-catalog/pack-validator
joins and the root-needing DRG/reference-pointer callers — through them; **drop** the fail-open
`DoctrineService.built_in_root` parameter (making the old nested shape unconstructable); remove
vestigial dual-read fallbacks; add an anti-regression architectural ratchet (joins-only grammar that
catches variable-indirected joins and exempts bare string markers); finish the residual
reader/operator-string repoints (the 7 owned CI reds); unify the activation-key vocabulary onto
`YAML_KEY_MAP` and fix a live glossary-pack migration drift; retire the context.py re-export shim;
sweep stale provenance strings. The seam refuses the **derived complement** of "kinds with a content
dir" — `{mission_step_contract, template, anti_pattern}` — so none can silently resolve to a
non-existent directory (relocating step-contracts/templates is #3091, out of scope). The mission's PR
lands on `feat/relocate-builtin-doctrine-packs` and therefore also **`Closes #3090`** (the relocation)
alongside #3119/#3106/#3116/#3120.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: ruamel.yaml (doctrine/charter YAML), typer/rich (CLI), pytest (tests) — no new deps
**Storage**: filesystem (`packs/built-in/**` doctrine data; `.kittify/` project config); no database
**Testing**: pytest (unit + integration + `tests/architectural/` gates); `ruff` + `mypy` zero-issue; targeted node-ids locally, CI owns the full arch sweep
**Target Platform**: Linux/macOS/Windows CLI (the `spec-kitty` package); doctrine ships as `packs/` sibling of the `doctrine` wheel package
**Project Type**: single (CLI library + shipped doctrine data)
**Performance Goals**: N/A — this is a structural/tech-debt mission; behaviour and graph identity are preserved, not changed
**Constraints**: NO production behaviour change (built-in doctrine graph identity byte-identical); fail-closed resolution (`PackRootNotFound`, never silent-empty); `ruff`/`mypy` clean; the single-authority invariant is CI-enforced (`tests/architectural/`)
**Scale/Scope**: ~25 built-in-location join sites collapse to 1 authority; ~14 coupled test files migrate off the dropped param; 9 shipped kinds + 1 carve-out; 4-site activation-vocabulary drift; ~18 provenance-string files (bulk-edit)

## Charter Check

Charter context loaded in **compact** mode (`spec-kitty charter context --action plan`). Governing
directives that bind this mission: single canonical authority (this mission's whole thesis),
architectural-gate discipline (the new ratchet), bulk-edit occurrence-classification (DIRECTIVE_035 —
`change_mode: bulk_edit`), test-remediation/red-first discipline (the 7 owned reds classified test vs
product per `notes/pr3117-ci-failures.txt`), and canonical-sources discipline. No charter conflicts;
no violations to justify.

## Project Structure

### Documentation (this mission)

```
kitty-specs/doctrine-built-in-seam-consolidation-01KYW3TX/
├── plan.md               # This file
├── research.md           # Phase 0 — design consolidation from the squad synthesis
├── data-model.md         # Phase 1 — the location-authority + vocabulary entities/contracts
├── quickstart.md         # Phase 1 — how to verify the seam + the ratchet locally
├── occurrence_map.yaml   # Bulk-edit classification (FR-008/009/012 same-string repoints)
├── contracts/            # Phase 1 — built_in_dir authority + arch-ratchet behavioural contracts
├── notes/                # Research + design synthesis, CI-failure split, source issues (seeded)
└── tasks.md              # Phase 2 (/spec-kitty.tasks — NOT created here)
```

### Source Code (repository root)

```
src/doctrine/
├── pack_paths.py             # HOME of the new built_in_dir(kind) authority + carve-out raise (IC-01)
├── artifact_kinds.py         # ArtifactKind.plural / CHARTER_KIND_TOKENS; WP01 ADDS the built-in-content-dir SSOT attribute here (IC-01)
├── service.py                # DoctrineService — drop built_in_root param + nested _built_in_dir (IC-02)
├── missions/step_contracts.py# mission_step_contract carve-out (importlib.resources; refused by seam)
└── <kind>/repository.py      # 9 repo _default_built_in_dir() → built_in_dir(kind) (IC-01)

src/charter/
├── catalog.py, compiler.py, kind_vocabulary.py   # nested dual-read fallbacks removed (IC-04)
├── resolver.py               # operator-facing error strings repointed (IC-03)
├── pack_manager.py           # YAML_KEY_MAP authority (IC-05)
├── charter_yaml_io.py        # _ACTIVATION_KEYS derived from YAML_KEY_MAP (IC-05)
└── context.py                # FR-009 re-export shim retired (IC-06)

src/specify_cli/
├── cli/commands/doctrine.py  # CWD ancestor-walk reimpl retired → seam (IC-04)
└── upgrade/migrations/m_unify_charter_activation_finalize.py  # live glossary-pack drift fix (IC-05)

packs/built-in/**             # relocated artefact YAMLs — provenance-string sweep (IC-07)

tests/
├── architectural/            # NEW anti-regression ratchet (IC-04); existing forbidden-pattern guards KEPT
├── glossary/test_gate_terms.py, doctrine/test_profile_inheritance.py, integration/test_org_pack_artifact_lifecycle.py  # 7 owned reds (IC-03)
└── doctrine/test_service*.py + ~14 coupled files  # migrate off built_in_root param (IC-02)
```

**Structure Decision**: single-project CLI library. The mission touches three source layers
(`doctrine` = the seam + service, `charter` = readers + vocabulary, `specify_cli` = migration + one
CLI resolver) plus `packs/built-in/**` data and `tests/`. The import layering
(`kernel<-doctrine<-charter<-specify_cli`) is already clean and is NOT changed — only the on-disk
location contract is consolidated.

## Complexity Tracking

No charter violations; no added architectural complexity. The mission *removes* an authority
(the fail-open param) and *centralizes* another (the location join) — net complexity decreases. The
one added surface (the arch-ratchet test) is a guard, not a runtime path.

## Implementation Concern Map

> Concerns are NOT work packages. `/spec-kitty.tasks` translates these into WPs.

### IC-01 — Single built-in-location authority (kind + root)

- **Purpose**: give "where does built-in kind K live" exactly one callable (`built_in_dir(kind)`) and "where is the built-in root" one callable (`built_in_root()`), deriving the plural from `ArtifactKind`, and refuse the **derived complement** of "kinds with a content dir" — `{mission_step_contract, template, anti_pattern}` — loudly (so `built_in_dir(template)` cannot resolve to a non-existent dir = fail-open). **Carve-out mechanism (adjudicated):** WP01 adds ONE content-dir SSOT attribute to `artifact_kinds.py` (a per-member `has_built_in_content_dir` property or a `_BUILT_IN_CONTENT_KINDS` frozenset of the 9 content-dir kinds); the complement is COMPUTED as `ArtifactKind` members minus that attribute — never `_NON_AUGMENTATION_ELIGIBLE_KINDS` (wrong set: has `asset`, omits `mission_step_contract`) and never a literal set in `pack_paths.py`.
- **Relevant requirements**: FR-001, FR-001b, FR-002, FR-005, FR-004.
- **Affected surfaces**:
  - `src/doctrine/artifact_kinds.py` — NEW content-dir SSOT attribute (the 9 content-dir kinds) the carve-out derives from.
  - `src/doctrine/pack_paths.py` — the two authorities + the derived-complement raise (computed from the artifact_kinds attribute).
  - Per-kind joins → `built_in_dir(kind)`: the 9 `src/doctrine/<kind>/repository.py` `_default_built_in_dir()`; inline charter sites `pack_manager.py:658`, `kind_vocabulary.py:170`, `compiler.py:842/843/934`, `tool_surface/bundles/claude.py:434`; **the variable-indirected joins `catalog.py:74`→`:80/89/102/111/120/129/138` (7 kinds) and `pack_validator.py:786`→`:793`** (paula MAJOR-2 — these are the exact drift class; missing them makes SC-001 false and the ratchet false-green).
  - Root calls → `built_in_root()`: `drg/loader.py:135`, `drg/migration/extractor.py:113`, `context_renderers/bootstrap_text.py:271`, `cli/commands/doctrine.py:210` (paula MAJOR-1 — no `built_in_dir(kind)` form expresses "the root").
- **Sequencing/depends-on**: none (foundation). IC-04's ratchet allow-list depends on this being complete.
- **Risks**: import-cycle safety (`pack_paths` importing `artifact_kinds` — verified leaf, safe); behaviour-preserving (repos already resolve flat); the complement carve-out MUST be derived (from "has a content dir"), not a hand-listed single kind.

### IC-02 — Remove the fail-open parameter

- **Purpose**: drop `DoctrineService.built_in_root` + the nested `_built_in_dir`, so the old shape is unconstructable and cannot silently load an empty set; migrate the ~14 coupled test files. **This WP owns the org-pack collision RED** (`test_org_pack_artifact_lifecycle.py::test_case_2...`, stale test setup — fixed by the `built_in_root=None` path here, NOT in IC-03).
- **Relevant requirements**: FR-003, FR-004, FR-007 (collision test), C-007 (`SPEC_KITTY_PACKS_ROOT` for synthetic tiers).
- **Affected surfaces**:
  - `src/doctrine/service.py` (param + `_built_in_dir` removed).
  - **~7 production construction sites** that pass `built_in_root=None` (the kwarg must be removed): `doctrine_service_factory.py:82`, `charter/compiler.py:799`, `charter/doctrine_service_builder.py:81,87`, `charter_runtime/lint/checks/org_layer.py:244,274`, `cli/commands/charter/generate.py:57` (behaviour-preserving; paula MINOR-4).
  - **5 shipped skill-template examples** carrying `DoctrineService(built_in_root=None, …)`: `src/doctrine/skills/spec-kitty-charter-doctrine/SKILL.md:121,452,662`, `spec-kitty-runtime-next/SKILL.md:234,276` (SOURCE templates — must update, not the generated copies).
  - The ~14 coupled test files enumerated in `notes/research-synthesis.md` (nested-tmp group → `SPEC_KITTY_PACKS_ROOT`/flat; real-repo-stale group incl. `test_org_pack_artifact_lifecycle.py`).
- **Sequencing/depends-on**: IC-01 (repos must self-resolve via the authority before the param is removed).
- **Risks**: the nested-tmp test group must move to flat/`SPEC_KITTY_PACKS_ROOT` shape; do NOT change the *different* already-flat repository `built_in_dir=` leaf param.

### IC-03 — Relocation completeness (residual readers + operator strings)

- **Purpose**: finish the residual repoints and kill the false-green class: the glossary-gate fixture and the profile-inheritance vacuous-pass fixture, plus shipped operator error strings; add the anti-vacuity assertion. (The org-pack collision RED is owned by IC-02, not here.)
- **Relevant requirements**: FR-008, FR-009, NFR-003 (anti-vacuity), C-006 (keep forbidden-pattern guards).
- **Affected surfaces**: `tests/glossary/test_gate_terms.py`, `tests/doctrine/test_profile_inheritance.py`, `src/charter/activation/resolver.py:187,250` (operator-facing error strings).
- **Sequencing/depends-on**: IC-02 (the param drop lands first).
- **Risks**: must NOT touch the architectural guard tests that name the old path as a forbidden pattern (occurrence_map exceptions).

### IC-04 — Remove dead alternatives + add the CI ratchet

- **Purpose**: remove the vestigial nested-`/built-in` dual-read fallbacks and the CWD ancestor-walk reimpl, and add the architectural gate that makes the single-authority invariant enforced (so a sixth resolver can't be born).
- **Relevant requirements**: FR-006, NFR-002, NFR-005 (derived carve-out marker), NFR-003.
- **Affected surfaces**: `src/charter/{catalog.py:283, compiler.py:1162, kind_vocabulary.py:179}`, `src/specify_cli/cli/commands/doctrine.py:204-210`; a **new `tests/architectural/` gate in its own file** (NOT folded into `test_no_dead_doctrine_paths.py` — cf. #3039's planned split).
- **Sequencing/depends-on**: IC-01 (the ratchet's allow-list is the two pack-paths authorities only, which must be the sole derivation sites first — including the variable-indirected joins routed there).
- **Ratchet grammar (paula MAJOR-2 + MINOR-3)**: AST-based; flag **path joins only** — a `resolve_pack_root("built-in") / …` BinOp **and** its variable-indirected form (`x = resolve_pack_root("built-in"); x / …`), plus `<path> / "built-in"` filesystem joins. **Permit** a bare `resolve_pack_root("built-in")` root call (that IS the seam via `built_in_root()`), and **exempt** the ~20 legitimate bare `"built-in"` string literals used as layer/provenance markers (`drg/models.py:330`, `drg/merge.py:917/930/1226/1229`, `pack_manager.py:134/269/639/653/661`, `mission.py:817/828`, `profiles_cmd.py:60`, `mission_type.py:1521`, `_doctrine_collect.py:719`, `charter/list_cmd.py:101`, …). Positive coverage asserts existence **through `resolve_pack_root(...)`** not a raw repo-relative `.exists()` (cf. #3036), with the `#3091` marker on the derived `{mission_step_contract, template, anti_pattern}` complement.
- **Risks**: a naive constant-scan false-reds ~20 correct marker sites; a naive BinOp-only scan false-greens the variable-indirected joins. Both grammar limbs are load-bearing.
- **Note (paula NOTE-8)**: `resolve_doctrine_root()` (`catalog.py:160`) stays live post-mission — it now feeds *template sets only*, with built-in resolved via `resolve_pack_root("built-in")` right beside it; it is NOT a built-in-location split-brain. Retiring its upward `specify_cli` fallback is deferred to #3101 (out of scope) — a deliberate, stated deferral, not an oversight.

### IC-05 — Activation-vocabulary unification + live drift fix

- **Purpose**: derive the activation-key vocabulary from `YAML_KEY_MAP` everywhere, replacing hand-written copies, and fix the live migration drift that drops `activated_glossary_packs`.
- **Relevant requirements**: FR-010, SC-005, C-004 (lands before Mission 2's resolver retarget).
- **Affected surfaces**: `src/charter/activation/pack_manager.py` (SSOT), `src/charter/activation/charter_yaml_io.py`, `src/specify_cli/upgrade/migrations/m_unify_charter_activation_finalize.py`; set-equality guard test.
- **Sequencing/depends-on**: none (independent surface).
- **Risks**: respect the migration's no-heavy-import constraint (export a cheap plain-tuple constant, not the pydantic-heavy import).

### IC-06 — Context.py re-export shim retirement (severable)

- **Purpose**: re-point the ~62 `from charter.activation.context import _x` test imports to their leaf modules and delete the FR-009 re-export block; no production behaviour change.
- **Relevant requirements**: FR-011.
- **Affected surfaces**: `src/charter/activation/context.py:25-145`; ~36 test files.
- **Sequencing/depends-on**: none (fully independent, test-only).
- **Risks**: multi-line import statements are the only hazard; the public `__all__` surface stays.

### IC-07 — Provenance-string sweep (severable, lowest)

- **Purpose**: sweep stale `src/doctrine/<kind>/built-in/` strings in relocated artefact YAMLs to `packs/built-in/<kind>/`, after confirming those fields are descriptive, not runtime-resolved.
- **Relevant requirements**: FR-012, C-005 (occurrence-map governed).
- **Affected surfaces**: ~18 `packs/built-in/**` YAMLs (`related:`/`source_files:`).
- **Sequencing/depends-on**: none.
- **Risks**: if `related:`/`source_files:` turn out to be runtime-resolved, escalate those to real readers under FR-008 (IC-03) rather than a cosmetic sweep.
