# Implementation Plan: Unify charter activation surfaces

**Branch**: `epic/2519-charter-authoring-lifecycle` | **Date**: 2026-07-10 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `kitty-specs/unify-charter-activation-surfaces-01KX5SJ9/spec.md`

## Summary

Make `config.activated_*` the single activation authority. The compiled reference set (`references.yaml`) and the DRG-graph derivation currently read the interview ledger (`answers.yaml selected_*` → `src/charter/compiler.py` → `generate.py`); repoint that derivation to read `config.activated_*`, retire `answers.selected_*` as an activation source (interview-record only), promote interview selections into `config.activated_*` (FR-007), and extend `consistency_check` to assert derived-vs-config parity and fail closed. Eliminates the dangling class that broke #2524; foundation slice that de-conflicts the authoring (#2522) and preflight (#2521) children.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: standard library + `ruamel.yaml` (config/answers I/O); the internal `charter` package (activation_engine, compiler, pack_manager, consistency_check, pack_context) and its `charter.synthesizer`/`generate` pipeline. No new third-party dependency.
**Storage**: YAML files in the project checkout — `.kittify/config.yaml` (authority), `.kittify/charter/interview/answers.yaml` (interview record), `.kittify/charter/references.yaml` (derived), `src/doctrine/graph.yaml` (derived).
**Testing**: `pytest`; `tests/doctrine/` (references-resolve/dangler, freshness, compliance), `tests/architectural/test_layer_rules.py` (charter !import specify_cli), `tests/charter/` (compiler/generate/interview). Run under the parallel profile; the doctrine + charter suites are the gate.
**Target Platform**: Linux/macOS dev + CI.
**Project Type**: single (Python CLI package; the change is in the `charter` package + its `specify_cli` command wrappers).
**Performance Goals**: unchanged — derivation runs at activate/synthesize time, not on a hot path; keep `references.yaml`/`graph.yaml` regeneration deterministic (STATIC timestamps).
**Constraints**: `charter` package must NOT import `specify_cli` (layer rule); single config write chokepoint `activation_engine.commit_plan`; `generate_graph` freshness gate stays green; no cascade engine; migration must drop zero previously-active artefacts; ruff+mypy zero-issue, complexity ≤15.
**Scale/Scope**: charter-subsystem source-of-derivation change — ~5 `charter` modules + ~4 `specify_cli/charter` command wrappers + the parity guard + a migration + regression tests. The interview→config promotion (FR-007) is the scope-risk to size (see IC-04).

## Charter Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Charter present; plan-action context compact. Alignment:

- **Single canonical authority** (Governing Principle #1) — this mission *is* the embodiment: it collapses two activation ledgers onto ONE authority (`config.activated_*`). Directly charter-aligned; the resolved decision (DM 01KX5SK7) chose exactly this. ✅
- **Require-canonical over fallback / no shadow paths** — retiring `answers.selected_*` as an activation source removes a parallel authority rather than adding one. ✅
- **Architectural alignment (layer rules)** — reconciliation logic stays in `charter`; CLI orchestration in `specify_cli` (C-001). The `test_charter_does_not_import_specify_cli` boundary is a hard gate. ✅
- **Architectural gate discipline** — the new parity guard (FR-005) must be NON-VACUOUS (a planted divergence must bite — NFR-002 self-test). ✅
- **Migration safety** — `config.activated_*` is the lossless seed (superset of the answers-derived set today). ✅

No violations → Complexity Tracking empty.

## Project Structure

### Documentation (this mission)

```
kitty-specs/unify-charter-activation-surfaces-01KX5SJ9/
├── plan.md              # This file
├── spec.md              # Committed (effb986)
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (the config-derivation contract)
└── tasks.md             # Phase 2 (/spec-kitty.tasks — NOT here)
```

### Source Code (repository root)

```
src/charter/
├── compiler.py               # IC-01: read config.activated_* instead of interview.selected_* (the derivation source switch)
├── consistency_check.py      # IC-03: extend — assert config <-> references <-> graph parity, fail closed
├── activation_engine.py      # (read) single write chokepoint commit_plan; unchanged write path
├── pack_manager.py           # (read) activate/deactivate callers
├── pack_context.py           # (read) already reads config.activated_* — reference behaviour to preserve
└── synthesizer/              # IC-01: write_pipeline/orchestrator derive references+graph from the config-sourced set

src/specify_cli/cli/commands/charter/
├── generate.py               # IC-01: compile_charter path — source the compiled set from config
├── interview.py              # IC-04: promote captured selections into config.activated_* (FR-007)
├── activate.py / deactivate.py  # (read) unchanged write path; verify resolution now follows automatically

# migration surface  # IC-05: config-seeded reconcile, zero drop

tests/
├── architectural/test_charter_references_resolve.py   # regression: activate-then-resolve (no answers edit)
├── charter/ (compiler/generate/interview)         # source-switch + interview->config
└── architectural/test_layer_rules.py              # layer boundary (unchanged, must stay green)
```

**Structure Decision**: single package; the load-bearing change is the *source of derivation* inside `charter.compiler`/`synthesizer` + the `generate` wrapper, plus the parity guard in `consistency_check`. `activation_engine`/`pack_manager`/`pack_context` are read-mostly (config write path already correct).

## Complexity Tracking

*No Charter Check violations — none.*

## Implementation Concern Map

> Concerns are NOT work packages. `/spec-kitty.tasks` translates these into WPs.

### IC-01 — Derivation source switch: references + graph read config, not answers

- **Purpose**: The core authority move (FR-001/FR-002). Repoint the compiled-reference-set + graph derivation from `interview.selected_*` to `config.activated_*`.
- **Relevant requirements**: FR-001, FR-002, NFR-004, C-003, C-005.
- **Affected surfaces**: `charter/compiler.py` (`compile_charter` reads `interview.selected_directives/...` → read config activation lists), `charter/synthesizer/*` (write_pipeline/orchestrator), `specify_cli/cli/commands/charter/generate.py` (`compile_charter` call path that stages `references.yaml`).
- **Sequencing/depends-on**: none (the spine).
- **Risks**: `references.yaml`/`graph.yaml` are committed artefacts — the switch changes their *source* but must keep output byte-deterministic (freshness gate C-003). The compiler consumes an interview-answers object today; the config activation lists have a different shape (per-kind stems vs the `DoctrineService` resolution) — the adaptation must resolve config stems→artefacts the same way the dangler test's live `DoctrineService` resolution does.

### IC-02 — Retire answers as an activation source (interview-record only)

- **Purpose**: FR-003 — make `answers.selected_*` inert for activation; it remains the captured interview record.
- **Relevant requirements**: FR-003, SC-004.
- **Affected surfaces**: the same compiler/generate path (remove the answers→activation read once IC-01 sources from config); a test proving editing `answers.selected_*` without config has no effect on the compiled set.
- **Sequencing/depends-on**: IC-01 (can't retire the source until the new source is wired).
- **Risks**: other consumers of `answers.selected_*` beyond activation (SPDD `spdd_reasons/activation.py` was flagged in research as an answers reader) — must confirm they are interview-record reads, not activation reads, or they break. **This is a discovery item for the post-plan squad.**

### IC-03 — Parity guard: consistency_check asserts config <-> references <-> graph, fail-closed

- **Purpose**: FR-005 — the regression guard so a #2524-style divergence fails locally, not at CI. NON-VACUOUS (NFR-002).
- **Relevant requirements**: FR-005, NFR-002.
- **Affected surfaces**: `charter/consistency_check.py` (extend; today it validates config vs doctrine/DRG, blind to references) + a self-test that plants a divergence and asserts the guard bites.
- **Sequencing/depends-on**: IC-01 (parity is only meaningful once derivation is config-sourced).
- **Risks**: overlap with the existing `freshness/computer.py` (which owns references/graph staleness) — must extend the RIGHT guard and not create a second, contradictory authority (the exact cross-contamination the epic warns about). Keep the guard in `consistency_check` (config-anchored) and reference, don't duplicate, freshness logic.

### IC-04 — Interview → config promotion (FR-007) — SIZE THIS

- **Purpose**: FR-007 — a freshly-interviewed charter's selections must land in `config.activated_*` (the authority), since the interview no longer feeds derivation directly.
- **Relevant requirements**: FR-007.
- **Affected surfaces**: `specify_cli/cli/commands/charter/interview.py` (+ possibly `generate.py`): after capturing `answers.selected_*`, activate those selections into `config.activated_*` (route through `activation_engine.commit_plan`, respecting the layer rule).
- **Sequencing/depends-on**: IC-01.
- **Risks / OPEN SIZING QUESTION**: is this a thin "activate the captured selections" step, or does it entangle the whole interview flow (org-pack pre-fill `apply_org_charter_to_interview`, paradigm selection, the `charter generate` compile order)? **The spec (Assumptions) explicitly allows splitting FR-007 to a follow-up if it proves large — the post-plan squad and tasks must adjudicate whether IC-04 is a thin promotion or a hidden interview rewrite, and if the latter, carve it out of this slice.**

### IC-05 — Migration: config-seeded, zero drop

- **Purpose**: FR-006 — existing projects whose compiled set was answers-derived reconcile to config-derived without dropping any active artefact.
- **Relevant requirements**: FR-006, C-004.
- **Affected surfaces**: a migration/backfill (existing migration surface) that treats `config.activated_*` as the seed and regenerates references/graph; a test on a fixture project with an answers-vs-config skew (like the observed 25-vs-24 directive skew) proving 0 drop.
- **Sequencing/depends-on**: IC-01.
- **Risks**: the reverse skew — an artefact in `answers.selected_*` but NOT `config.activated_*` would *drop* under config-authority. Research showed config is the superset today, but the migration must detect and surface (not silently drop) any answers-only artefact, promoting it into config as part of the migration. **Blast-radius discovery item for the post-plan squad.**

## Post-Plan Squad Corrections (folded 2026-07-10)

A 3-lens post-plan squad + architect-alphonso reviewed this plan. #1862 cleared as UNRELATED (different subsystem). Substantive corrections to the IC map, all grounded in code:

- **IC-01 (two derivation paths, not one).** The answers→derived source lives at BOTH `charter/compiler.py` (references.yaml) AND `specify_cli/cli/commands/charter/_synthesis.py:41-70` (interview_snapshot/drg_snapshot → project graph layer). Both must repoint to config.
- **IC-01 (#1 CORRECTNESS RISK — ID-form normalization).** `config.activated_*` holds slug-stems (`001-…`); the compiler/DRG use canonical `DIRECTIVE_001`/`directive:` URNs. The switch must map stems→canonical exactly as the live `DoctrineService` resolution does (reuse `charter.kind_vocabulary.resolve_config_id`). A stem that fails to normalize **silently drops the directive + its entire transitive closure** (tactics→styleguides→toolguides→procedures) — invisible, and lands on the two gates this slice protects. Tasks MUST pin: a stem↔canonical parity fixture for all 25 directives + a non-vacuity test that a malformed stem is *rejected, not dropped* (C-006).
- **IC-01 (content change + required test edits).** Config-sourcing is a SUPERSET, not set-equivalent: it ADDS the 8 config paradigms (answers-paradigms is empty; paradigms are selection-only, never DRG-reachable) + direct styleguides/toolguides. So `references.yaml` + `graph.yaml` content changes → regenerate + re-commit (freshness gate), and `test_dangling_baseline_is_shrink_only` must be shrunk to empty (the three baseline danglers — domain-driven-design, aggregate-design-rules, contextive — now resolve). This is the intended #2380 outcome but an UNLISTED required test edit (C-008).
- **IC-02 (new exposures + the THIRD ledger).** Beyond compiler/generate: `specify_cli/.../_synthesis.py` (second activation path) and `specify_cli/doctrine/org_charter.py:670-718` (`apply_org_charter_to_interview` — an activation-FEEDER that goes INERT once the compiler stops reading interview; **org `required_*` artefacts must be unioned into `config.activated_*` or they break**). `resolver.py:372` goes stale (latent, not a gate break). CONFIRMED SAFE (leave alone): `spdd_reasons/activation.py` reads `governance.yaml`/`directives.yaml` (ledger C), NOT answers — the research flag was a false alarm on source (C-007).
- **IC-03 (re-scope + placement correction).** (a) The "reference `freshness/computer.py`" instruction is a LAYER VIOLATION — that module is in `specify_cli` and imports `charter`; `consistency_check` cannot import it, and there is nothing to reference (freshness=temporal/advisory vs parity=set/fail-closed are disjoint). Keep them as **disjoint responsibilities**. (b) Scope parity to **config↔references at ID level** (the #2524 dangler class) + **config↔graph at KIND level** — the config↔graph ID mapping is the exact one `consistency_check.py:199-210` deliberately punted; asserting it would grow an ID-reconciliation sub-project. (c) `run_consistency_check` is CLI-only today → add a **doctrine-test-tier entry point** so the guard bites in the suite (NFR-002).
- **IC-04 + IC-05 MERGE into one indivisible promotion primitive.** The interview→config promotion (IC-04/FR-007) and the migration's answers-only backfill (IC-05/FR-006) are the SAME operation: promote answers-ROOTS ({directives ∪ paradigms}, other kinds are closure) into `config.activated_*`. The primitive lives in `charter`, called by both the migration (`specify_cli/upgrade/migrations/`, sibling of `m_3_2_0rc35_default_charter_pack`) and the interview command. **FR-007 does NOT cleanly split** — splitting IC-04 while shipping IC-05 reconciles legacy projects but regresses fresh charters (interview-selected paradigms would drop, since paradigms are selection-only and the interview never writes config). So the append-promotion primitive + both call sites STAY in-slice; only the **re-interview replace/deselect refinement** (does re-interview deactivate dropped selections?) defers to a follow-up. This needs a **new append/set primitive** (`commit_plan` is single-key + append-only + FR-021 default-materialization) — the real cost, not the CLI wiring.
- **Revised IC map:** IC-01 (both derivation paths + ID-bridge + content-regen/baseline-shrink) → IC-02 (retire + org-feeder union + third-ledger discipline) → IC-03 (config↔references ID parity + config↔graph KIND parity, test-tier, disjoint-from-freshness) → **IC-04≡IC-05 (one shared append-promotion primitive, both call sites; deselect deferred)**. FR-007 reframed accordingly in spec.

## Post-Tasks Squad Corrections (folded 2026-07-10)

A 3-lens post-tasks adversarial squad (decomposition, correctness/architect, coverage) verified the WP decomposition against live code. Two LAND-BLOCKERs + SHOULD-FIXes, all folded into the WP prompts:

- **LAND-BLOCKER — direct roots, not just directives+paradigms (WP02 T026).** `_build_references_from_service` sources non-directive kinds ONLY from directive-closure, but `aggregate-design-rules` (styleguide) + `contextive` (toolguide) are activated DIRECTLY in config and reachable from NO directive (graph-BFS confirmed). Roots-only derivation leaves them dangling → WP03 shrink-to-empty impossible → WP04 org-union drops 5 of 7 kinds. WP02 must read config-activated styleguides/toolguides (+ direct kinds) as additional roots unioned with closure. This is the same capability WP04's non-root org-required kinds need.
- **LAND-BLOCKER — absent-key None→explicit-set flip (WP06 + spec Edge Case).** `PackContext.from_config` treats an absent `activated_<kind>` key as "all built-ins active." A first-run promotion writing a bare restrictive list flips runtime to only-selected, dropping the built-ins (violates NFR-004/C-005 + the `built_in_only` Edge Case). Resolved: absent-key promotion preserves all-built-ins-active (union built-ins then append); pinned by a first-run regression.
- **C-002 write path (WP06).** FR-021 default-pack materialization is a `plan_activation` behaviour, not a `commit_plan` one — orthogonal. The primitive builds its own `ActivationPlan` and routes through `commit_plan` (one call per yaml_key); it must NOT call `save`/`_save_config` directly (sibling-writer breach) nor reuse `plan_activation`'s absent-key branch.
- **Circular import (WP06).** `activation_engine` has zero charter-internal imports by design; `YAML_KEY_MAP` lives in `pack_manager` which imports `activation_engine`. Take yaml_key as data / derive via `doctrine.artifact_kinds` — do not import `pack_manager.YAML_KEY_MAP`.
- **The actual silent-drop seam (WP02).** `_sanitize_catalog_selection` (`compiler.py:292-324`) drops unrecognized stems with an info diagnostic and continues — that IS the C-006 vector. WP02 must route config stems through the RAISING `resolve_artifact_urn`, not merely swap the source upstream of the lenient sanitizer.
- **Function-name direction (WP01).** `resolve_config_id` is URN→stem (wrong direction); the needed stem→canonical resolver with reject-not-drop is `resolve_artifact_urn` — corrected in WP01/WP02.
- **Coverage (WP03 T027).** Added the deactivate-drops regression (Acceptance Scenario 2, previously uncovered) + an SPDD-no-flip assertion (config-sourced `charter.md`→`governance.yaml` sync must not spuriously flip the SPDD gate).
- **Fixture realism (WP07 T025).** Real repo has 25-vs-25 directive parity (ID-form only) and zero answers-only paradigms — the reverse-skew fixture must be a constructed synthetic, not a mirror of live state.
- **WP04 dep edge.** WP04 now depends on WP06 (it consumes the broadened arbitrary-kind promotion primitive, not a roots-only one).
