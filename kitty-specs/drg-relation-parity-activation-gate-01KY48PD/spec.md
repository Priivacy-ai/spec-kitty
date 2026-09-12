# Mission Specification: DRG completeness (#2843) — relation-description parity + activation-gate consolidation

**Mission Branch**: `kitty/mission-drg-relation-parity-activation-gate-01KY48PD` (coord topology; plans/base on `doctrine/drg-completeness-2843`)
**Created**: 2026-07-22
**Status**: Draft
**Input**: GitHub issue #2843 (re-scoped to items 2+3 after operator split; item 1 → mission #2847). Parent epic #2466. Pre-spec 4-lens research: `docs/plans/engineering-notes/drg-completeness-2843-research.md`. Hardened by a post-spec adversarial squad (renata/alphonso/daphne, 2026-07-22) whose code-grounded findings are folded in below.

## User Scenarios & Testing *(mandatory)*

Two independent slices. Either can ship alone and deliver value; they touch disjoint
subsystems (Item B = charter activation layer; Item A = DRG enum + docs).

### User Story 1 — Activation gate stops silently dropping directive nodes (Priority: P1)

A charter/doctrine maintainer configures a pack that populates `activated_directives`
(a per-kind activation allow-list, authored as config **stems** like
`001-architectural-integrity-standard`). Today `charter/drg.py::_node_is_activated`
Step 3 (`drg.py:319`) compares canonical node ids (`DIRECTIVE_001`) against those config
stems; because they never match, a populated list **silently drops every directive node**
from the filtered graph. It only looks healthy because per-kind activation lists are
~always `None` (default-allow). This is a latent correctness bug, not a cosmetic refactor.

**Why this priority**: It is a live correctness defect in the governance layer — the
moment any pack starts using per-kind activation, doctrine silently disappears. Fixing
it (routing the one gate through the resolver that already normalizes stems→canonical,
and collapsing the two genuine workarounds that grew around it) is the highest-value slice.

**Independent Test**: Against the real built-in corpus, populate `activated_directives`
with a directive named by its config **stem** (whose canonical id differs), run
`filter_graph_by_activation`, and assert the directive node **survives**. Red on today's
code, green after the fix — no Item A work required.

**Acceptance Scenarios**:

1. **Given** a built-in graph and a `PackContext` whose `activated_directives` names one
   directive by its config stem, **When** `filter_graph_by_activation` runs, **Then** the
   corresponding canonical directive node is retained (not dropped) and non-activated
   directives are excluded.
2. **Given** the same list named by config stem, run against the **merge-base** code,
   **When** the gate runs, **Then** it drops the node (RED) — while a **control** using a
   list whose entry already equals the canonical id stays GREEN on the merge-base
   (canonical matches canonical at `drg.py:319`). This RED/GREEN sibling pair is the
   attribution proof that the defect is the stem≠canonical mismatch and not an incidental
   populated-list error. (Config is authored with stems; a canonical-id in config is not a
   supported input form — see C-002. This scenario uses the canonical-id list only as a
   test control, not as a claim that the gate accepts both forms.)
3. **Given** the tension-scan reimplementation (`_node_is_tension_scan_active` +
   `_build_tension_active_urns` + `_resolve_activated_urns_for_kind`) is deleted so tension
   consistency consumes the one gate, **When** the tension consistency check runs, **Then**
   it produces the same verdicts as before (it already encoded the correct per-ID resolution).
4. **Given** each of the five consumers of `filter_graph_by_activation`, **When** its
   before/after test runs: with `activated_directives` **`None`** (default-allow, the
   production shape) the filtered graph is **byte-identical to the merge-base**; with a
   **populated** list the consumer emits the **corrected** per-ID result — a named
   observable per consumer (retained nodes / resolved references / report field), NOT
   equality with the buggy baseline (the fix's whole purpose is that this output changes).

---

### User Story 2 — Every DRG Relation is self-describing, with an enforced single-source doc surface (Priority: P2)

A doctrine author inspecting the reference graph wants each `Relation` member to carry a
description, the code-side registry complete, and the one parity-enforced doc surface to
match the code exactly so it cannot drift.

**Why this priority**: Documentation/hygiene parity — valuable and independently
shippable, but not a live correctness defect. Runs as a parallel lane.

**Independent Test**: Assert `RELATION_DESCRIPTIONS` covers all `Relation` members (both
the completeness gate in `tests/doctrine/drg/test_models.py` and the content-equality gate
in `tests/doctrine/test_relation_doc_parity.py` pass) — no Item B work required.

**Acceptance Scenarios**:

1. **Given** the `Relation` enum (15 members), **When** the completeness gate runs, **Then**
   `set(RELATION_DESCRIPTIONS) == set(Relation)` and every description is a non-empty string.
2. **Given** `docs/architecture/doctrine-relationships.md` restructured so every one of the
   15 relations has its own `### …` section whose body equals its `RELATION_DESCRIPTIONS`
   entry (whitespace-normalized), **When** `tests/doctrine/test_relation_doc_parity.py` runs
   with `_SCOPED_RELATIONS` widened 3→15, **Then** code and that doc are in lockstep. This is
   the **single parity-enforced doc surface**.
3. **Given** the contested `applies` (1 edge) vs `scope` (157 edges) pair, **When** their
   descriptions are authored, **Then** `RELATION_DESCRIPTIONS[APPLIES] != RELATION_DESCRIPTIONS[SCOPE]`
   and each names its distinct edge-role; and the never-emitted relations
   (`vocabulary`/`refines`/`delegates_to`, zero edges everywhere) are described as
   intended-but-dormant, while the org-pack overlay relations (`enhances`/`overrides`,
   zero edges *in built-in by design*, plus legacy `replaces`) are described by their actual
   emission status — not as actively-exercised built-in relations.

### Edge Cases

- A future `Relation` member added without a description → the completeness gate in
  `test_models.py` fails (this mission converts that gate from a `== {3}` pin to
  `== set(Relation)`).
- `activated_directives` left `None` (default-allow) → behavior is byte-identical to today
  (the production shape; the fix only changes the populated path).
- The `applies`/`scope` adjudication changes how a relation is *described* but MUST NOT
  rewire existing edges (157 live `scope` edges make edge re-classification out of scope).
- `_check_graph_kind_parity` is deliberately KIND-granular today; re-pointing it to per-ID
  is an intended **behavior upgrade** (FR-003), explicitly exempt from AC4's "unchanged" clause.

## Requirements *(mandatory)*

### Functional Requirements

| ID | Title | User Story | Priority | Status |
|----|-------|------------|----------|--------|
| FR-001 | Route the activation gate through the existing resolver | As a charter maintainer, I want `_node_is_activated` to resolve a populated per-kind allow-list's config stems to canonical URNs (via the existing `resolve_artifact_urn`) before matching, so activated directive nodes are retained, not silently dropped. | High | Open |
| FR-002 | Reuse `resolve_artifact_urn` (no new resolver) | As a maintainer, I want the gate to **reuse** the existing `charter.kind_vocabulary.resolve_artifact_urn` (which already does stem→canonical and is already consumed by the compiler projection and the tension-scan) rather than mint a second normalizer. The gate signature gains the `doctrine_root`/`org_roots` the resolver needs (available via `pack_context.pack_roots`); exact siting (resolve-in-filter vs at-`PackContext` vs at-gate-boundary) is a `/plan` decision. | High | Open |
| FR-003 | Collapse the two genuine workaround sites | As a maintainer, I want the tension-scan reimplementation deleted so it consumes the one gate, and `_check_graph_kind_parity` re-pointed from KIND-granular to per-ID (an intended **behavior upgrade** owned with tests, exempt from the AC4 "unchanged" clause). | High | Open |
| FR-004 | Verify-first blast-radius finding | As a maintainer, I want empirical confirmation of whether any production `.kittify/config.yaml` populates per-kind `activated_*` lists, recorded in the analysis report to frame the fix as latent-bug vs live-regression. | High | Open |
| FR-005 | Backfill relation descriptions | As a doctrine author, I want `RELATION_DESCRIPTIONS` (`src/doctrine/drg/models.py`) to describe all 12 currently-undescribed `Relation` members (the enum's other 3 are already described). | Medium | Open |
| FR-006 | Restructure the parity doc surface | As a doctrine author, I want `docs/architecture/doctrine-relationships.md` restructured so each of the 15 relations has a dedicated `### …` section body equal to its registry entry — this is NOT a constant bump: ~7 relations currently have no heading, the grouped `enhances`/`overrides`/`replaces` heading must be split into three, and the multi-paragraph Lineage/Delegation prose reduced to (or re-homed from) the registry text — then widen `_SCOPED_RELATIONS` 3→15. Update the now-stale "the other twelve are out of scope / a follow-up" docstrings in `test_relation_doc_parity.py` and the doc's "Tension vocabulary" prose. | Medium | Open |
| FR-007 | Convert the code-side completeness gate | As a maintainer, I want `tests/doctrine/drg/test_models.py` (which today pins `RELATION_DESCRIPTIONS == {the 3}`) converted to `== set(Relation)` completeness, and its non-empty-string sibling re-parametrized over all members — so backfilling does not red an unacknowledged gate (would otherwise violate NFR-002). | Medium | Open |
| FR-008 | Extend `docs/context/doctrine.md` as prose (non-enforced) | As a doctrine author, I want the `docs/context/doctrine.md` glossary extended to cover the relations for reader completeness, explicitly as **paraphrased prose NOT under the parity test** (the glossary deliberately paraphrases; forcing verbatim equality is out of scope). | Low | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | Red-first, attributable defect characterization | A characterization test exercising the pre-existing `filter_graph_by_activation` entry point against the real built-in corpus is RED before FR-001; the RED is proven attributable to stem≠canonical by a paired canonical-id **control** that is GREEN on the merge-base (AC2). No hermetic `id==stem` fixtures. | Reliability | High | Open |
| NFR-002 | Consumer regression net, real observables | Each of the five consumers (`mission_step_contracts/executor.py:182`, `charter/reference_resolver.py:67`, `charter/compiler.py:1037` closure, `charter/consistency_check.py::_check_drg_cross_kind_refs` at `:424`, `charter/context.py:928`) carries a before/after test asserting a **named observable** (not a smoke "doesn't crash"): `None`-path byte-identical to merge-base; populated-path emits the corrected per-ID result. Full `tests/doctrine/` + `tests/charter/` suites add 0 net failures vs the merge-base. | Reliability | High | Open |
| NFR-003 | Relation description completeness + distinctness | `set(RELATION_DESCRIPTIONS) == set(Relation)` with all non-empty; `test_relation_doc_parity.py` green across all 15 scoped relations on the one enforced surface; and the mechanical distinctness floor of AC3 holds (`applies` desc ≠ `scope` desc). | Correctness | High | Open |
| NFR-004 | Quality gates clean | `ruff check` and `mypy --strict` report 0 issues on touched modules; cyclomatic complexity ≤15 on every touched function; no new blanket `# noqa` / `# type: ignore` / per-file ignores. | Maintainability | High | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | references.yaml projection stays (already correct) | The compiler `_resolve_config_activated_ids` (`compiler.py:88`) building `references.yaml` is a catalog id-list PROJECTION that already resolves stems correctly via `resolve_artifact_urn` — it never had the bug and is NOT rerouted or deleted. (It is independent-correct, not a "workaround" — only the tension-scan and `_check_graph_kind_parity` are genuine workarounds.) | Technical | High | Open |
| C-002 | Config holds stems; require-canonical at the gate | Per-kind activation lists are authored as config stems; the gate resolves stems→canonical via the single resolver and matches on canonical URN. It does NOT add a dual-branch that also tolerates raw canonical-ids in config (that is not a supported input form) — require-canonical, not tolerate-both. | Technical | High | Open |
| C-003 | ATDD red-first for Item B | Item B follows red-first discipline (DIRECTIVE_041 / charter C-011 ATDD): the NFR-001 characterization test (with its GREEN canonical-id control) lands red through the pre-existing entry point before any production fix. | Process | High | Open |
| C-004 | Single resolver, reused | No competing stem→canonical resolver is introduced; the gate reuses `charter.kind_vocabulary.resolve_artifact_urn`. | Technical | Medium | Open |
| C-005 | Item 1 out of scope | Anti-pattern corpus promotion (inline `anti_patterns:` → first-class DRG nodes) is mission #2847, NOT this mission. This mission delivers items A+B only. | Scope | Medium | Open |
| C-006 | Terminology + edge-preservation | Canonical Mission terminology (run the terminology guard before pushing doctrine/prose); the `applies`/`scope` adjudication describes intent only and MUST NOT rewire existing graph edges (157 live `scope` edges). | Regulatory | Medium | Open |

### Key Entities

- **`Relation` enum + `RELATION_DESCRIPTIONS`** (`src/doctrine/drg/models.py`): 15-member vocabulary and its self-describing map; 12 members currently undescribed. Pinned by two gates: `test_relation_doc_parity.py` (content-equality vs the doc) and `test_models.py` (registry completeness — today a `== {3}` pin, FR-007 converts it).
- **Activation gate** (`charter/drg.py`: `_node_is_activated` at `:319`, `filter_graph_by_activation` at `:325`): the single per-kind filter; the stem-vs-canonical compare is the defect.
- **`PackContext.activated_<kind>`**: config-derived per-kind activation lists holding config STEMS; `pack_context.pack_roots` supplies the resolver's roots.
- **`resolve_artifact_urn`** (`charter/kind_vocabulary.py:186`): the EXISTING stem→canonical resolver the gate reuses (already consumed by `compiler.py:122` and the tension-scan at `consistency_check.py:899`).
- **The two genuine workaround sites**: `_check_graph_kind_parity` (`consistency_check.py:776`, KIND→per-ID upgrade) and the tension-scan trio (`consistency_check.py:874-956`, deleted). The compiler projection (C-001) is independent-correct and stays.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A populated `activated_directives` list retains its canonical directive nodes — proven by a characterization test RED on the merge-base and GREEN after the fix, with a canonical-id control GREEN on the merge-base establishing attribution.
- **SC-002**: `set(RELATION_DESCRIPTIONS) == set(Relation)`; both code-side gates green — the completeness gate (`test_models.py`) and the content-equality parity gate (`test_relation_doc_parity.py`, all 15 scoped relations) on the single enforced surface `doctrine-relationships.md`. (`docs/context/doctrine.md` extended as prose, explicitly non-enforced.)
- **SC-003**: The two genuine activation workaround sites collapse — the tension-scan reimplementation deleted (net workaround LOC removed), `_check_graph_kind_parity` re-pointed to per-ID; the `references.yaml` projection retained untouched.
- **SC-004**: All five consumer before/after tests pass with named observables; full `tests/doctrine/` + `tests/charter/` suites add 0 net failures vs the merge-base; `ruff` + `mypy --strict` clean.
