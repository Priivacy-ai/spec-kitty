# Implementation Plan: Single-Authority Resolution Parity

**Branch**: `spec/charter-resolution-parity` | **Date**: 2026-08-19 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `kitty-specs/single-authority-resolution-parity-01M0CEBQ/spec.md`

**Mission**: M1 of the charter-resolution program (`docs/plans/charter-resolution/`). Closes #3490, #3426, #2981. Rolls up to reach epic #3530 and fail-loud epic #3410. Enabling; runs in parallel with M2 (`drg-read-path-bridge-01M0CHVZ`).

## Summary

Doctrine authored in an **org pack** or **project overlay** silently under-loads or drops out of charter activation, while equivalent **built-in** doctrine loads completely. Two independent causes produce the same fake-green symptom:

1. **Recursion divergence.** Built-in discovery `rglob`s; org/project discovery `glob`s (non-recursive). Worse, the *loader* (`doctrine/base.py`, `doctrine/agent_profiles/repository.py`) and the *charter-activation resolver* (`charter/kind_vocabulary.py`) each decide recursion independently and disagree per kind (measured 71% tactic undercount; nested org styleguides silently un-activatable — #3426).
2. **Hand-restated kind vocabulary.** The plural↔singular doctrine-kind map is copied by hand in several charter modules; two copies (`_activation_render.py`) have drifted two kinds behind and fail open, and all the string-keyed copies escape the existing consistency gate (#2981).

The fix makes org/project discovery **unconditionally recursive** to match built-in (C-001), routes loader and resolver through **one shared recursion authority** in the doctrine layer so they agree by construction (FR-002/C-006), derives the plural↔singular kind vocabulary from **one authority** collapsing the hand copies (FR-004), widens the `--include` selector to accept every charter-activatable kind (FR-006), and adds a **parity/totality gate** that fails loudly on any future recursion divergence or kind-map inconsistency — including string-keyed maps the current gate cannot see (FR-007).

The mission is deliberately scoped to produce **no golden-count ripple and no cascade-reach change** (C-004): the DRG read-path bridge (#3572), cascade completeness (#2829), delivery/reach (#3488/#3489/#3176), and project-tier node emission (#3038) are separate program missions.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: ruamel.yaml (YAML I/O); pydantic (artifact schemas); pytest (gate/ATDD). No new dependencies added — pure internal refactor.
**Storage**: Filesystem doctrine corpus (`packs/built-in/<plural>/`, org pack roots `<root>/<plural>/`, project overlay `.kittify/doctrine/<dir>/`). No datastore.
**Testing**: pytest (`tests/doctrine/`, `tests/charter/`); markers `doctrine`/`fast`; AST-based totality gate in `tests/doctrine/drg/test_kind_mapping_totality.py`.
**Target Platform**: Linux/macOS/Windows dev + CI (cross-platform per DIR-001).
**Project Type**: single (library CLI — `src/doctrine`, `src/charter`, `src/specify_cli`).
**Performance Goals**: N/A (discovery already file-bounded; `rglob` over kind-specific globs adds no measurable cost on the small doctrine corpus).
**Constraints**: `charter` MUST NOT import `specify_cli` — the shared authority lives in the `doctrine` layer (C-006); recursion stays kind-specific so `.provenance/*.yaml` sidecars and `.md` files are never captured (C-002); new code passes `ruff` + `mypy --strict` with **zero** suppressions (C-005); **no golden-count ripple / no cascade-reach change** (C-004).
**Scale/Scope**: ~4 loader seams, ~2 resolver seams, ~4 kind-map duplicators, 1 selector renderer, 1 gate file. Effort: **M**.

### Supply-chain note (planning discipline)
This mission adds/upgrades/removes **no** dependency in any ecosystem. The `supply_chain_security_check` step is therefore N/A — recorded here explicitly rather than left silent (per plan step contract): there is no registry-authenticity, freshness, or lifecycle-script surface to examine.

## Constitution / Charter Check

*GATE: Must pass before Phase 0. Re-checked after Phase 1.*

- **Single canonical authority** (charter governing principle): this mission *is* the enforcement of that principle for recursion policy and kind vocabulary — it removes restated copies and replaces them with derived authorities. ✅ Aligned.
- **ATDD-first / red-first** (Quality & Tech-Debt Standing Order): every fix is proven by a test that fails before and passes after (nested org tactic dropped pre-fix; nested styleguide un-activatable pre-fix; drifted singular render; unsupported selector kind). ✅ Planned.
- **Architectural gate discipline / layer boundary**: `charter → doctrine` import direction preserved; `charter` never imports `specify_cli` (C-006). Enforced by existing `test_runtime_charter_doctrine_boundary.py`. ✅
- **Terminology adherence**: no user-facing prose changes introducing forbidden terms; `Mission` canon respected. Run `tests/architectural/test_no_legacy_terminology.py` pre-push. ✅
- **Zero-suppression code quality** (C-005 / charter Code Quality): no `# noqa`/`# type: ignore`/per-file-ignore additions. ✅
- **DIR-002** Python 3.11+; **DIR-005** tests for new functionality. ✅

No charter violations. No entries required in Complexity Tracking.

## Project Structure

### Documentation (this mission)

```
kitty-specs/single-authority-resolution-parity-01M0CEBQ/
├── plan.md              # This file
├── research.md          # Phase 0 — decisions, rationale, adversarial evidence
├── data-model.md        # Phase 1 — authority/gate entities & invariants
├── quickstart.md        # Phase 1 — how to verify the fix end to end
├── contracts/
│   ├── recursion-authority.md   # Shared recursion-policy authority contract
│   ├── kind-vocabulary.md       # Derived charter-activatable plural↔singular contract
│   └── parity-gate.md           # Falsifiable loader↔resolver + string-map gate contract
└── tasks/               # Phase 2 output (/spec-kitty.tasks — NOT created here)
```

### Source Code (repository root)

```
src/doctrine/
├── artifact_kinds.py                     # ArtifactKind enum + PROJECT_KIND_DIRS (derive-authority precedent)
│                                         #   → add derived CHARTER-ACTIVATABLE plural↔singular authority
│                                         #     (ArtifactKind − {template, asset} = 10 kinds incl anti_pattern)
├── discovery_recursion.py  (NEW)         # Single shared org/project recursion authority (C-001, C-006)
├── base.py                               # _project_scan: glob → recursive (consults authority)
├── agent_profiles/repository.py          # _load: org/project recursive=False → True (consults authority)
├── styleguides/repository.py             # DELETE redundant _project_scan rglob override
├── assets/repository.py                  # DELETE redundant _project_scan rglob override
└── drg/org_pack_loader.py                # existing derive helpers (reference; may host/adjacent the new vocab authority)

src/charter/
├── kind_vocabulary.py                    # _org_scan_dirs / _layer_scan_dirs: recursive from shared authority
├── activations.py                        # _SINGULAR_TO_PLURAL_KIND / _PLURAL_TO_SINGULAR_KIND ← derived (_ALLOWED_KINDS left — non-goal)
├── _activation_render.py                 # _singular_kind inverse / _KIND_TO_PROPERTY ← derived (fixes drift)
├── synthesizer/project_drg.py            # _KIND_TO_NODE_KIND (string-keyed, intentionally partial) — gate-covered, unchanged mapping
└── context_renderers/template_include.py # _render_doctrine_artifact_include: + glossary_pack (render) + anti_pattern (recognized)

tests/
├── doctrine/drg/test_kind_mapping_totality.py   # EXTEND: string-keyed map coverage + recursion parity gate
├── doctrine/…                                    # loader recursion red-first tests
└── charter/…                                     # resolver parity + vocab + selector red-first tests
```

**Structure Decision**: Single-project library layout. The shared recursion authority is a **new small module in the `doctrine` layer** (`src/doctrine/discovery_recursion.py`) so both the loader (`doctrine.*`) and the resolver (`charter.*`, which imports *down* into `doctrine`) read the same policy — satisfying C-006 (charter must not import specify_cli; doctrine is the lowest layer). The derived charter-activatable plural↔singular vocabulary is added to `doctrine.artifact_kinds` (or a doctrine sibling) beside the existing `PROJECT_KIND_DIRS` precedent, and every charter copy imports it.

## Key design decisions (locked by spec; confirmed against current code)

1. **Unconditional recursion (C-001).** `doctrine.base.BaseDoctrineRepository._project_scan` becomes recursive; the two subclass `rglob` overrides (`StyleguideRepository`, `AssetRepository`) are deleted as redundant; `agent_profiles/repository.py::_load` flips its org and project scans to `recursive=True` (built-in was already `True`). This is a policy, not a per-kind flag.
2. **One shared recursion authority (FR-002/C-006).** A doctrine-layer authority expresses "org/project overlay discovery is recursive." Both loader seams and the resolver's `_org_scan_dirs`/`_layer_scan_dirs` derive their recursion from it, so divergence is impossible without bypassing the authority — which the gate catches.
3. **Derived 10-kind charter-activatable vocabulary (FR-004/FR-005/C-003).** The charter-activatable set is `ArtifactKind − {template, asset}` = **10 kinds including `anti_pattern`** — deliberately *not* the 9-kind `CHARTER_KIND_TOKENS` (which also excludes `anti_pattern` via `_NON_AUGMENTATION_ELIGIBLE_KINDS`). A new derived plural↔singular authority replaces the 4 hand copies. The two drifted `_activation_render.py` copies gain `glossary_pack` and `anti_pattern` (the drift *is* the bug).
4. **Selector widening (FR-006).** `_render_doctrine_artifact_include`'s hardcoded 6-kind `renderers` dict is the "Unsupported selector kind" source. Add `glossary_pack` (renders via `service.glossary_packs`) and make `anti_pattern` a **recognized** kind (resolves to a normal "no such artifact" rather than an "unknown selector kind" error, since anti-patterns ship no standalone artifact files). `_resolve_include_kind` already accepts every kind via `ArtifactKind.from_operator_token`.
5. **Falsifiable gate (FR-007/NFR-003/C-002).** Extend `test_kind_mapping_totality.py` to (a) discover **string-keyed** kind maps and validate their key/value consistency (keys are legit `ArtifactKind` tokens; intentionally-partial maps like `_KIND_TO_NODE_KIND` are explicitly exempted from *totality* but still key-validated), and (b) a **behavioral loader↔resolver recursion parity** check that, per kind, asserts a nested artifact is discovered by *both* the loader and the resolver — reintroducing `recursive=False` in either site reddens the gate and names the kind. A **negative** test proves `.provenance/*.yaml` and `.md` are never captured (C-002).

## Complexity Tracking

*No Constitution/Charter violations — table intentionally empty.*

## Parallel Work Analysis

### Dependency Graph (implementation concerns → suggested WP grouping for `/spec-kitty.tasks`)

```
        ┌─────────────────────────────────────────────────────────────┐
        │ Foundation                                                    │
        │  A. Shared recursion authority (doctrine/discovery_recursion) │
        │  B. Derived charter-activatable plural↔singular vocab authority│
        └───────────────┬───────────────────────────┬──────────────────┘
                        │                           │
        ┌───────────────▼──────────┐   ┌────────────▼───────────────┐
        │ C. Loader recursion       │   │ E. Kind-vocab collapse     │
        │    (base, agent_profiles, │   │    (activations,           │
        │     delete 2 overrides)   │   │     _activation_render)    │
        └───────────────┬──────────┘   └────────────┬───────────────┘
        ┌───────────────▼──────────┐   ┌────────────▼───────────────┐
        │ D. Resolver recursion     │   │ F. Selector widening       │
        │    (kind_vocabulary       │   │    (template_include:      │
        │     _org/_layer_scan_dirs)│   │     glossary_pack+anti_ptn)│
        └───────────────┬──────────┘   └────────────┬───────────────┘
                        └───────────────┬───────────┘
                        ┌───────────────▼───────────────────────────┐
                        │ G. Parity/totality gate (extend            │
                        │    test_kind_mapping_totality): string-keyed│
                        │    coverage + loader↔resolver recursion +   │
                        │    C-002 negative test + falsifiability     │
                        └─────────────────────────────────────────────┘
```

- **A + B are the foundation** (shared authorities); everything else consumes them.
- **C→D** (recursion: loader then resolver, both reading A) and **E→F** (vocabulary: collapse then selector, both reading B) are two **independent streams** that can proceed in parallel after the foundation.
- **G (gate) lands last** — it binds C/D (recursion parity) and covers B/E's maps (string-keyed totality). Its falsifiability proof (reintroduce a divergence → red; restore → green) is the mission's durability guarantee.

### Work Distribution
- **Sequential prerequisite**: A (recursion authority) and B (vocab authority) before their respective consumer streams.
- **Parallel streams**: recursion stream {A→C→D} vs vocabulary stream {B→E→F} touch disjoint files (doctrine loaders + kind_vocabulary vs activations/_activation_render/template_include) — low conflict risk.
- **Integration**: G (the gate) is the join; it must run green with the fixes and red when either divergence is reintroduced.

### Coordination Points
- **Golden-count guard (C-004)**: before finalizing, run the DRG/cascade golden-count tests; **if any golden count moves, STOP** — scope has exceeded M1 (that ripple belongs to M2). This check is a mandatory gate in the tasks/implement phase.
- **Byte-identical flat output (NFR-002)**: assert flat-layout activation output is unchanged (recursion only *adds* nested discovery; `rglob` over a flat dir == `glob`).
- **Terminology + boundary guards**: `tests/architectural/test_no_legacy_terminology.py` and `test_runtime_charter_doctrine_boundary.py` green pre-push.
