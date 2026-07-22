# Implementation Plan: DRG completeness (#2843) — relation-description parity + activation-gate consolidation

**Branch**: `doctrine/drg-completeness-2843` (coord topology) | **Date**: 2026-07-22 | **Spec**: `kitty-specs/drg-relation-parity-activation-gate-01KY48PD/spec.md`
**Input**: Feature specification (hardened by the post-spec adversarial squad) at `kitty-specs/drg-relation-parity-activation-gate-01KY48PD/spec.md`

## Summary

Two independent slices closing the residue PR #2833's landing left open (epic #2466; item 1 → #2847):

- **Item B (P1) — activation-gate correctness.** `charter/drg.py::_node_is_activated` Step 3 (`drg.py:319`) compares a directive node's **canonical** id (`DIRECTIVE_001`) against `PackContext.activated_directives`, which holds config **stems** (`001-architectural-integrity-standard`). They never match, so a populated list drops every directive node. **Verified LIVE, not merely latent** (see research.md, D1): this repo's `.kittify/config.yaml` populates `activated_directives` with 26 stems, `PackContext` stores them un-normalized (`pack_context.py:364`), and three live callers run the filter — the main `DoctrineService.get()` path is exempt, so it silently under-resolves directives in charter-mediated resolution rather than crashing. Fix = route the gate through the **existing** `charter.kind_vocabulary.resolve_artifact_urn` (stem→canonical), collapse the two genuine workarounds, and net-test the five consumers with real observables.
- **Item A (P2) — relation-description parity.** Backfill `RELATION_DESCRIPTIONS` for the 12 undescribed `Relation` members; convert the code-side completeness gate; restructure the one parity-enforced doc surface (`doctrine-relationships.md`) into 15 per-relation sections and widen `_SCOPED_RELATIONS` 3→15; extend `context/doctrine.md` as non-enforced prose.

**Technical approach** (resolver siting decision — research.md D2, refined by the post-plan squad): **resolve-in-gate, batched once per call**. `filter_graph_by_activation` builds a resolved `dict[kind, frozenset[canonical_urn] | None]` once (lifting `_build_tension_active_urns` from the deleted trio) via the **existing** `resolve_artifact_urn`, and `_node_is_activated` consumes it as a pure membership check — **no public gate-signature change**, `PackContext.activated_*` keeps holding stems, and `drg.py` stays IO-lean. `doctrine_root` comes from `resolve_doctrine_root()` (the compiler projection's source, pinned equal by test), `org_roots` from `pack_roots[1:]`; unknown stems are **skipped-with-report** (never raise). Rejected: normalize-at-`PackContext`-construction (Option B), which changes what the shared field holds and ripples to every stem-expecting reader.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: internal — `charter` (drg, kind_vocabulary, pack_context, consistency_check, compiler, reference_resolver, context), `doctrine.drg` (models); pydantic, ruamel.yaml. No new third-party deps.
**Storage**: N/A (in-memory DRG graph + YAML doctrine artifacts; `RELATION_DESCRIPTIONS` is a Python dict, not serialized into any `*.graph.yaml`)
**Testing**: pytest — red-first characterization test against the real built-in corpus + this repo's populated config; per-consumer before/after tests with named observables; `test_relation_doc_parity.py` (content-equality) + `tests/doctrine/drg/test_models.py` (registry completeness); `ruff` + `mypy --strict`
**Target Platform**: Linux/macOS/Windows dev + CI (cross-platform CLI library)
**Project Type**: single (Python library)
**Performance Goals**: N/A — activation lists are small; stem→canonical resolution is cheap/cacheable and runs only in charter-mediated filter paths
**Constraints**: no gate-signature change (roots sourced from `PackContext`); `PackContext.activated_*` stays stems; require-canonical (no dual-branch tolerating raw canonical-ids in config, C-002); the `references.yaml` compiler projection is untouched (C-001); no edge rewiring (C-006); `ruff`/`mypy --strict` clean, complexity ≤15, no new suppressions (NFR-004)
**Scale/Scope**: ~2 focused lanes; Item B touches `charter/drg.py` + `consistency_check.py` (delete tension-scan trio, re-point `_check_graph_kind_parity`) + 5 consumer test files; Item A touches `drg/models.py`, `doctrine-relationships.md` (restructure), `context/doctrine.md`, `test_relation_doc_parity.py`, `test_models.py`

## Charter Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Charter present (`software-dev-default`, mode compact). Relevant binding gates and how this plan complies:

- **ATDD-first / red-first (C-011 / DIRECTIVE_041)**: Item B lands the NFR-001 characterization test (with a GREEN canonical-id control) red through the pre-existing `filter_graph_by_activation` entry point before the fix. ✅ planned.
- **Canonical sources & unification (DIRECTIVE_044)**: the gate **reuses** `resolve_artifact_urn` — no second normalizer (C-004). ✅
- **Close-the-defect-class-by-construction (DIRECTIVE_043)**: require-canonical at the gate (C-002), not tolerate-both — the stem≠canonical class cannot recur. ✅
- **Test-and-typecheck quality gate (DIRECTIVE_030)**: `ruff` + `mypy --strict` clean, ≤15 complexity, no new suppressions (NFR-004); every new branch/helper gets a focused test (NFR-002). ✅
- **Living-documentation-sync (DIRECTIVE_037) / Common-Docs (DIRECTIVE_042)**: Item A edits existing docs in place (no new/moved files); the just-retired anti-sprawl ratchet does not interact. ✅
- **Terminology canon (C-006)**: run the terminology guard before pushing doctrine/prose. ✅

No charter violations. No Complexity Tracking entries required.

## Project Structure

### Documentation (this mission)

```
kitty-specs/drg-relation-parity-activation-gate-01KY48PD/
├── plan.md              # This file
├── research.md          # Phase 0 — resolver-siting decision (D2) + verify-first LIVE-bug finding (D1) + doc-restructure sizing (D3)
├── data-model.md        # Phase 1 — the resolved activation set + Relation registry
├── quickstart.md        # Phase 1 — run the red-first + parity gates
├── contracts/           # Phase 1 — activation-gate behavioral contract + relation-completeness contract
└── tasks.md             # Phase 2 (/spec-kitty.tasks — NOT created here)
```

### Source Code (repository root)

```
src/
├── charter/
│   ├── drg.py                 # Item B: _node_is_activated / filter_graph_by_activation (resolve-in-gate)
│   ├── kind_vocabulary.py     # Item B: resolve_artifact_urn (REUSED, not extended unless roots plumbing needs it)
│   ├── consistency_check.py   # Item B: delete tension-scan trio; re-point _check_graph_kind_parity KIND→per-ID
│   ├── pack_context.py         # Item B: activated_* stays stems (unchanged shape); source of roots
│   ├── compiler.py            # Item B: references.yaml projection UNTOUCHED (C-001); closure is a consumer
│   ├── reference_resolver.py  # Item B: consumer #2
│   └── context.py             # Item B: consumer #5
├── specify_cli/mission_step_contracts/executor.py   # Item B: consumer #1
└── doctrine/drg/models.py     # Item A: RELATION_DESCRIPTIONS backfill

docs/
├── architecture/doctrine-relationships.md   # Item A: restructure → 15 per-relation sections (the single parity surface)
└── context/doctrine.md                       # Item A: extend as non-enforced prose

tests/
├── charter/                   # Item B: 5-consumer before/after tests + red-first characterization
└── doctrine/
    ├── test_relation_doc_parity.py    # Item A: widen _SCOPED_RELATIONS 3→15; update stale non-goal docstrings
    └── drg/test_models.py             # Item A: convert == {3} pin to == set(Relation) completeness
```

**Structure Decision**: Single Python-library project; changes are localized to the `charter/` activation layer (Item B) and the `doctrine/drg` enum + `docs/` parity surface (Item A). No new packages or directories.

## Complexity Tracking

*No Charter Check violations — section intentionally empty.*

## Implementation Concern Map

> Concerns are NOT work packages. `/spec-kitty.tasks` translates these into executable WPs.

### IC-01 — Activation-gate canonical-URN correctness (Item B core)

- **Purpose**: Stop the per-ID gate silently dropping directive (and any stem-keyed kind) nodes by resolving activated stems→canonical through the existing resolver.
- **Relevant requirements**: FR-001, FR-002, FR-004, NFR-001, C-002, C-003, C-004
- **Affected surfaces**: `charter/drg.py` (`_node_is_activated`, `filter_graph_by_activation`); `charter/kind_vocabulary.py` (`resolve_artifact_urn`, reused); roots sourced from `charter/pack_context.py`
- **Sequencing/depends-on**: none (parallel to IC-04/05). Red-first (NFR-001/C-003) precedes the fix.
- **Decided (post-plan squad, see contract)**: unknown stems → **skip-with-report** (catch `UnknownArtifactIdError`, `continue`; `_check_unknown_references` reports), NEVER raise (raising throws through all 5 consumers incl. the fail-closed-report `_check_graph_kind_parity`). Resolve **once per filter** (lift `_build_tension_active_urns`), not per-node (complexity ≤15 + fs-walk cost). `doctrine_root` from `resolve_doctrine_root()` (== compiler-projection source, pinned by test), `org_roots` = `pack_roots[1:]`. Compare full URN vs `node.urn`; add `drg.py`'s own singular→`ArtifactKind` constant (existing map is in `consistency_check.py`, which imports `drg`).
- **Risks**: the fix is **behavior-changing in this repo's charter-mediated paths** (directives previously dropped now retained) — expected and intended, but any test asserting the current buggy filtered output must be updated, not preserved.

### IC-02 — Workaround collapse (Item B consolidation)

- **Purpose**: Remove the two genuine workarounds now that the gate is correct — delete the tension-scan reimplementation so it consumes the one gate, and re-point `_check_graph_kind_parity` from KIND-granular to per-ID.
- **Relevant requirements**: FR-003, SC-003
- **Affected surfaces**: `charter/consistency_check.py` (`_node_is_tension_scan_active`/`_build_tension_active_urns`/`_resolve_activated_urns_for_kind` deleted; `_check_graph_kind_parity` re-pointed; **also delete the then-orphaned `_DRG_SINGULAR_TO_ACTIVATED_KINDS_MEMBER`** — its only two uses (`:835`, `:920`) both vanish). `compiler.py` `references.yaml` projection explicitly NOT touched (C-001).
- **Sequencing/depends-on**: IC-01 (the gate must be correct before consumers rely on it).
- **Risks**: `_check_graph_kind_parity` KIND→per-ID is a deliberate **behavior upgrade** (exempt from the "unchanged" clause), owned with its own tests; the tension-scan deletion must preserve verdicts (it already encoded correct per-ID resolution).

### IC-03 — Five-consumer regression net (Item B safety)

- **Purpose**: Prove the corrected gate does not regress any of the five `filter_graph_by_activation` consumers, with real observables.
- **Relevant requirements**: NFR-002, SC-004
- **Affected surfaces**: tests for `mission_step_contracts/executor.py:182`, `reference_resolver.py:67`, `compiler.py:1037` closure, `consistency_check.py::_check_drg_cross_kind_refs` (`:424`), `context.py:928`
- **Sequencing/depends-on**: IC-01.
- **Risks**: each test must assert a **named observable** (retained nodes / resolved refs / report field), `None`-path byte-identical + populated-path corrected — not a smoke test (NFR-002).

### IC-04 — Relation registry + code-side gate (Item A core)

- **Purpose**: Make `RELATION_DESCRIPTIONS` complete and adjudicate the contested/dormant relations.
- **Relevant requirements**: FR-005, FR-007, NFR-003, C-006
- **Affected surfaces**: `src/doctrine/drg/models.py`; `tests/doctrine/drg/test_models.py` (convert `== {3}` → `== set(Relation)` + non-empty over all)
- **Sequencing/depends-on**: none (parallel to IC-01/02/03).
- **Risks**: `applies` vs `scope` is an adjudication (distinctness floor: descriptions differ); `vocabulary`/`refines`/`delegates_to` unemitted everywhere vs `enhances`/`overrides`/`replaces` 0-in-built-in-by-design (org-pack overlay) — describe by actual emission status, no edge rewiring (C-006).

### IC-05 — Doc parity surface restructure (Item A docs)

- **Purpose**: Bring the single parity-enforced doc surface into lockstep and extend the glossary prose.
- **Relevant requirements**: FR-006, FR-008, NFR-003, SC-002
- **Affected surfaces**: `docs/architecture/doctrine-relationships.md` (restructure into 15 per-relation `###` sections — ~7 new, split the grouped `enhances/overrides/replaces` heading, trim Lineage/Delegation prose to registry text); `tests/doctrine/test_relation_doc_parity.py` (widen `_SCOPED_RELATIONS` 3→15, update stale non-goal docstrings); `docs/context/doctrine.md` (non-enforced prose)
- **Sequencing/depends-on**: IC-04 (descriptions must exist before the doc can match them).
- **/tasks slicing note (priti)**: splittable into **05a** (parity-surface restructure + `_SCOPED_RELATIONS` widen + stale-docstring fixes — test-gated, verbatim-precision) and **05b** (`context/doctrine.md` non-enforced prose — editorial), both depending only on IC-04 and parallel to each other.
- **Risks**: this is a doc **restructure**, not a constant bump (per-relation headings + verbatim body equality); the content-equality comparator raises `LookupError` on a missing heading, so every relation needs its own section.
