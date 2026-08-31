# Implementation Plan: Glossary Pack Doctrine Kind

**Branch**: `research/glossary-doctrine-artefact` | **Date**: 2026-07-21 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `kitty-specs/glossary-pack-doctrine-kind-01KY30SW/spec.md`

## Summary

Mission A (keystone) of the Glossary Doctrine Overhaul program. Introduce `GLOSSARY_PACK` as a
first-order, charter-activatable doctrine `ArtifactKind`, add a `src/doctrine/glossaries/`
repository that loads `*.glossary-pack.yaml` packs, wire the kind through the DRG + charter
activation/cascade the same way `directive` is wired, ship a built-in `spec-kitty-core` pack
carrying the 104 canonical terms migrated from `.kittify/glossaries/spec_kitty_core.yaml`, and
prove the built-in pack resolves as a loaded DRG node. Enforcement fields
(`aliases`/`banned_synonyms`/`synonyms_to_avoid`) are present in the schema but unwired (Mission
B); the runtime `src/glossary/` and the casing gate are left untouched (Mission C/B).

The technical approach is a **copy-the-`directive`-kind** exercise plus one greenfield package
and one data migration — deliberately additive, no behaviour change to the runtime glossary. The
authoritative build map is in [research.md](./research.md), distilled from the pre-spec research
squad (`glossary-research/01-doctrine-glossary-kind.md`).

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: existing doctrine subsystem (`BaseDoctrineRepository`, DRG models/loader, `charter.activation_engine`/`cascade`, `DoctrineService`), `ruamel.yaml` for pack files; `pytest` / `mypy --strict` / `ruff` for gates
**Storage**: on-disk YAML — built-in `*.glossary-pack.yaml` pack file(s) under `src/doctrine/glossaries/` plus a shipped `*.graph.yaml` DRG fragment; no database
**Testing**: `pytest` (unit + `tests/architectural/` gates), ATDD red-first per WP; targeted surfaces `tests/doctrine/`, `tests/charter/`, `tests/architectural/`
**Target Platform**: cross-platform CLI/library (Linux, macOS, Windows)
**Project Type**: single project (CLI + library)
**Performance Goals**: `spec-kitty doctor doctrine --json` < 2 s with the built-in pack loaded (NFR-005)
**Constraints**: underscore URN `glossary_pack:` (NFR-001); three mirrored kind-lists move in lockstep (C-005); NO coupling into runtime `src/glossary/` (C-002); cyclomatic complexity ≤ 15; `mypy --strict` + `ruff` zero-warning; ≥ 90% new-code coverage (NFR-004)
**Scale/Scope**: 1 new `ArtifactKind`, 1 new package (`src/doctrine/glossaries/`), ~10–12 touched surfaces (enum, DRG models + loader/extractor, kind_vocabulary, pack_context, activations, org_pack_loader, charter/drg.py, DoctrineService, doctor), 1 built-in 104-term pack

## Charter Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **ATDD-first (C-011, binding).** Every WP commits a RED-first acceptance test before
  implementation. Keystone acceptance tests: the underscore-URN regression (NFR-001), the
  kind-list drift-guard (C-005), the 104-term migration fidelity test (NFR-002), and the
  non-vacuous "resolves as a loaded node" guard (NFR-003). — **PASS (planned)**
- **Canonical sources & unification (DIRECTIVE_044).** The kind is added by copying the
  canonical `directive` wiring through the real doctrine/charter chain — no improvised loader or
  hand-rolled activation. — **PASS**
- **Architectural gate discipline (DIRECTIVE_043).** The existing kind-list drift-guard
  (`test_org_pack_augmentation.py:411-431`) binds only `_ALLOWED_KINDS ↔ _ORG_DRG_CANONICAL_KINDS`
  — it does **NOT** cover `_BUILTIN_ARTIFACT_KINDS`, the list that delivers default-on (squad F2).
  We EXTEND it to a genuine three-way equality (concrete floor) + a positive "glossary_packs ∈
  default activated_kinds" assertion. The "resolves as a loaded node" guard adds a negative-control
  arm (remove the graph fragment/emission → resolution goes RED) so it is non-vacuous. — **PASS
  (planned, extension required — the current guard is insufficient as-is)**
- **Single canonical authority.** The pack becomes the canonical *doctrine* home for terminology;
  in Mission A it is additive and the runtime seed remains the authority for the casing gate
  (dual-home is temporary and tracked to Mission B/C). — **PASS (with documented transition)**
- **`__all__` convention (C-007).** Any touched module under `src/charter/` MUST declare/extend
  `__all__`; the new `src/doctrine/glossaries/` package declares `__all__`. — **PASS (planned)**
- **Terminology canon.** No `feature*` aliases; the kind/token is `glossary_pack` / `glossary-pack`. — **PASS**
- **Git/workflow (DIRECTIVE_045).** Planning artifacts on the integration branch; implementation
  in per-lane worktrees; operator merges. — **PASS**

No violations requiring Complexity Tracking.

## Project Structure

### Documentation (this mission)

```
kitty-specs/glossary-pack-doctrine-kind-01KY30SW/
├── plan.md              # This file
├── research.md          # Phase 0 — build map + decisions (folded from pre-spec squad)
├── data-model.md        # Phase 1 — GlossaryPack / GlossaryTerm / kind / DRG node
├── quickstart.md        # Phase 1 — how to verify the kind loads + activates
├── contracts/           # Phase 1 — pack YAML schema + doctrine-integration contract
└── tasks.md             # Phase 2 — /spec-kitty.tasks output (NOT created here)
```

### Source Code (repository root)

> **Naming reconciliation (squad M4).** Every existing kind keeps `plural == dir == accessor`
> (`service._built_in_dir(<plural>)` → `<root>/<plural>/built-in`; dirs `directives`, `tactics`,
> `agent_profiles`, …). The kind's plural is **`glossary_packs`**, so the package dir and accessor
> are **`glossary_packs`** — NOT `glossaries`. The built-in dir is **`built-in`** (hyphen).

```
src/doctrine/
├── artifact_kinds.py          # (edit) GLOSSARY_PACK enum member + _PLURALS["glossary_pack"]="glossary_packs" + _PATTERNS; keep OUT of _NON_AUGMENTATION_ELIGIBLE_KINDS; from_operator_token/CHARTER_KIND_TOKENS derive free
├── drg/
│   ├── models.py              # (edit) NodeKind.GLOSSARY_PACK; underscore URN glossary_pack:; fence comment vs retiring runtime GLOSSARY/GLOSSARY_SCOPE
│   ├── loader.py              # (context) globs src/doctrine/*.graph.yaml at ROOT, non-recursive
│   ├── org_pack_loader.py     # (edit) add "glossary_packs" to _ORG_DRG_KIND_ALIASES dict (NOT the derived frozenset)
│   └── migration/extractor.py # (edit) NEW per-kind emission block in extract_artifact_edges (extract helper for complexity ≤15); regenerate graph
├── glossary_packs/            # (NEW package)
│   ├── __init__.py            # declares __all__
│   ├── models.py              # GlossaryPack aggregate + GlossaryTerm (ALL seed fields; confidence: float)
│   ├── repository.py          # GlossaryPackRepository(BaseDoctrineRepository) — glob *.glossary-pack.yaml
│   └── built-in/
│       └── spec-kitty-core.glossary-pack.yaml   # 104 migrated canonical terms (all fields)
├── glossary_pack.graph.yaml   # (NEW, GENERATED by extractor) root-level DRG fragment — the resolution seam
└── service.py                 # (edit) DoctrineService.glossary_packs accessor + _built_in_dir("glossary_packs")

src/specify_cli/cli/commands/
└── _doctrine_health.py        # (edit, WP05) glossary-pack counts + invalid→unhealthy (doctor doctrine)

src/charter/
├── pack_context.py            # (edit) _BUILTIN_ARTIFACT_KINDS += "glossary_packs"; activated_glossary_packs field + _read_activated_glossary_packs + from_config/from_activation wiring
├── activations.py             # (edit) _ALLOWED_KINDS += "glossary_packs"; _SINGULAR_TO_PLURAL_KIND += {"glossary_pack":"glossary_packs"}
├── consistency_check.py       # (edit) _CLI_KIND_TO_DRG_SINGULAR += {"glossary-pack":"glossary_pack"}
├── pack_manager.py            # (edit expected-value tests) YAML_KEY_MAP derives glossary-pack → activated_glossary_packs
└── drg.py                     # (edit) two kind-map entries

tests/
├── doctrine/glossary_packs/   # repository + model + duplicate-surface validation tests
├── charter/                   # activation/cascade + default-on assertion; update exact-set tests (test_pack_manager*, test_packcontext_has_all_ten→eleven)
└── architectural/             # THREE-WAY drift-guard extension (+_BUILTIN); URN regression; non-vacuous resolves-as-loaded-node guard (with negative-control arm); C-002 import-boundary; standing pack⟺seed parity
```

**Structure Decision**: Single-project layout. New code is one greenfield package
(`src/doctrine/glossary_packs/`) plus edits to existing doctrine/charter surfaces that host the
analogous `directive` wiring. Built-in pack assets live at `src/doctrine/glossary_packs/built-in/`;
the **generated** DRG fragment ships at the doctrine **package root**
(`src/doctrine/glossary_pack.graph.yaml`) because `load_built_in_graph` globs `*.graph.yaml`
non-recursively there (squad B1). Explicitly NOT under `.kittify/glossaries/` (the seed contract
belongs to the runtime retired in Mission C).

## Implementation Concern Map

> Implementation concerns are NOT work packages. `/spec-kitty.tasks` translates these into WPs.
> **Recommended sequence (post-squad): IC-01 → IC-02 → IC-04 → IC-03 → IC-05 → IC-06 → IC-07.**
> IC-04 (graph emission/resolution) moved EARLIER — it holds the two blockers and is the
> load-bearing risk, not a lightweight finisher.

### IC-01 — Kind registration (ArtifactKind + DRG node + token)

- **Purpose**: Make `GLOSSARY_PACK` a real, charter-activatable kind and a DRG-addressable node
  with the correct underscore URN.
- **Relevant requirements**: FR-001, FR-002, FR-003, FR-010; NFR-001; C-001.
- **Affected surfaces**: `src/doctrine/artifact_kinds.py` (enum member `GLOSSARY_PACK="glossary_pack"`,
  `_PLURALS["glossary_pack"]="glossary_packs"`, `_PATTERNS`; keep out of
  `_NON_AUGMENTATION_ELIGIBLE_KINDS`), `src/doctrine/drg/models.py` (`NodeKind.GLOSSARY_PACK`, the
  underscore-URN regex/prefix assertion, comment fence vs retiring runtime `GLOSSARY`/`GLOSSARY_SCOPE`).
- **Sequencing/depends-on**: none (foundation).
- **Free (verified derived)**: `from_operator_token('glossary-pack')→glossary_pack`,
  `CHARTER_KIND_TOKENS`, and `YAML_KEY_MAP` derive from the enum once the member exists and stays out
  of the exclusion set — no logic edit to `kind_vocabulary.py`/`pack_manager.py` (only their exact-set
  tests, see IC-03). NB: `from_operator_token` is on the enum (`artifact_kinds.py:128`), `YAML_KEY_MAP`
  in `pack_manager.py` — not `kind_vocabulary.py`.
- **Risks**: URN underscore-vs-hyphen trap (NFR-001 regression is the guard); accidental inclusion in
  `{template, asset}` (explicit membership assertion).

### IC-02 — Glossary-pack repository + schema + service accessor

- **Purpose**: Load `*.glossary-pack.yaml` packs into `GlossaryPack`/`GlossaryTerm` and expose them
  via `DoctrineService.glossary_packs`.
- **Relevant requirements**: FR-004, FR-005; C-004 (enforcement fields present, unwired).
- **Affected surfaces**: new `src/doctrine/glossary_packs/` package (`models.py` with **ALL seed
  fields** — `surface`, `definition`, `confidence: float`, `status`, `see_also`,
  `introduced_in_mission`, `synonyms_to_avoid`, `aliases`, `banned_synonyms`; `repository.py`
  inheriting `BaseDoctrineRepository` glob `*.glossary-pack.yaml`; `__init__.py` with `__all__`);
  `src/doctrine/service.py` (`.glossary_packs` accessor + `_built_in_dir("glossary_packs")`).
- **Sequencing/depends-on**: IC-01.
- **Risks**: schema must carry EVERY seed field (seed has `see_also`/`introduced_in_mission` the
  first draft dropped); `confidence` is a **float**, not enum/str; `None` default for optional list
  fields (decided); duplicate term-surface → validation error (needs a synthetic fixture — the seed
  has no dups); enforcement fields round-trip for Mission B.

### IC-03 — Charter activation wiring (ALL surfaces) + default-on + three-way drift-guard

- **Purpose**: Make the kind activate/cascade/deactivate generically, ship the built-in pack active
  by default, and make the drift-guard actually protect default-on.
- **Relevant requirements**: FR-006, FR-007, FR-008, FR-009; C-005; SC-003.
- **Affected surfaces** (squad-expanded): `pack_context._BUILTIN_ARTIFACT_KINDS` +
  `activated_glossary_packs` field + `_read_activated_glossary_packs` + `from_config`/`from_activation`
  wiring; `activations._ALLOWED_KINDS` + `_SINGULAR_TO_PLURAL_KIND`;
  `drg/org_pack_loader._ORG_DRG_KIND_ALIASES` (the dict behind `_ORG_DRG_CANONICAL_KINDS`);
  `consistency_check._CLI_KIND_TO_DRG_SINGULAR`; `charter/drg.py` two map entries; **update exact-set
  tests** (`test_pack_manager*`, `test_packcontext_has_all_ten_activated_fields` 10→11). **Extend the
  drift-guard** (`test_org_pack_augmentation.py:411-431`) to a three-way equality including
  `_BUILTIN_ARTIFACT_KINDS`, plus a positive default-on assertion.
- **Default-on mechanism (named)**: three-state `None` default + `_BUILTIN_ARTIFACT_KINDS` membership
  + the root graph fragment (IC-04). No `config.yaml` entry, no `suggests`/`requires` edge.
- **Sequencing/depends-on**: IC-01, IC-02, IC-04 (needs the fragment for resolution).
- **Risks**: omitting `_BUILTIN_ARTIFACT_KINDS` silently disables default-on with a green suite —
  the extended guard is the counter; all list keys are **plural strings** (`"glossary_packs"`).

### IC-04 — Extractor emission + ROOT graph fragment + non-vacuous resolution guard (load-bearing)

- **Purpose**: Emit the pack's own DRG nodes and ship the generated root fragment so the built-in
  pack resolves as a loaded node — proven by a fakeable-failure guard.
- **Relevant requirements**: FR-011; NFR-003.
- **Affected surfaces**: `drg/migration/extractor.py` — a **new per-kind emission block** in
  `extract_artifact_edges` globbing `glossary_packs/built-in/*.glossary-pack.yaml` (extract a helper
  to hold complexity ≤15; the function is at the C901 ceiling); regenerate + commit the **generated**
  `src/doctrine/glossary_pack.graph.yaml` at the doctrine root (NOT nested); non-vacuous
  resolves-as-loaded-node test in `tests/architectural/`.
- **Sequencing/depends-on**: IC-01, IC-02. **Do this EARLY** — it is the resolution seam.
- **Risks**: `_KIND_MAP` alone is insufficient (edge-targets only); the fragment must sit at the
  package root (loader globs there non-recursively); the guard MUST include a negative-control arm
  (remove fragment/emission → resolution RED), not just assert node presence.

### IC-05 — Built-in spec-kitty-core pack + full-fidelity migration + standing parity

- **Purpose**: Author the built-in pack, migrate all 104 terms with true zero loss, and keep it in
  parity with the seed until Mission C.
- **Relevant requirements**: FR-006; NFR-002; SC-002.
- **Affected surfaces**: `src/doctrine/glossary_packs/built-in/spec-kitty-core.glossary-pack.yaml`;
  a **standing pack⟺seed parity test over the full key-set** (not a one-shot snapshot) that stays
  green until Mission C deletes the seed; round-trip test on the 3 real `synonyms_to_avoid` terms.
- **Sequencing/depends-on**: IC-02.
- **Risks**: the seed carries `see_also`/`introduced_in_mission`/`synonyms_to_avoid` beyond the
  obvious four fields — parity must be full-key superset; the seed file is READ, never modified (C-003).

### IC-06 — Doctor reporting + performance

- **Purpose**: Surface glossary-pack counts + health; invalid packs never reported healthy; keep
  doctor fast.
- **Relevant requirements**: FR-012; NFR-005; SC-001.
- **Affected surfaces**: `_doctrine_health.py` (profile-centric today — real new code, not a
  freebie); a synthetic invalid-pack fixture for the unhealthy branch; a doctor `< 2 s` assertion.
- **Sequencing/depends-on**: IC-02, IC-03.
- **Risks**: an invalid member pack must degrade aggregate health (not silently pass).

### IC-07 — Boundary + regression guards (previously unowned requirements)

- **Purpose**: Prove Mission A stays additive and regresses nothing.
- **Relevant requirements**: C-002, SC-004.
- **Affected surfaces**: an architectural import-boundary test forbidding any `src/glossary` import
  from `src/doctrine/glossary_packs/` (C-002); a regression pass over the pre-existing
  glossary/doctrine/architectural suites incl. `test_glossary_canonical_terms.py` +
  `test_no_legacy_terminology.py` (SC-004).
- **Sequencing/depends-on**: IC-02 (the package must exist to guard its imports).
- **Risks**: without the import-boundary gate, a future edit could silently recouple to the dying
  runtime — the exact failure C-002 exists to prevent.
