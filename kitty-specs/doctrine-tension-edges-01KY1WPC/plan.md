# Implementation Plan: Doctrine Tension as First-Class DRG Edges

**Branch**: `doctrine/drg-missing-links-analysis` | **Date**: 2026-07-21 | **Spec**: [spec.md](./spec.md)
**Input**: Mission specification from `kitty-specs/doctrine-tension-edges-01KY1WPC/spec.md`

## Summary

Model doctrine tension as first-class, queryable DRG structure — `in_tension_with`
(symmetric, non-transitive), `reconciles_tension` (bridges both sides of a pair), and
`rejects` (directional, terminates at a new `anti_pattern`/`smell` `NodeKind`) — and
retire the mis-encoded `opposed_by` field/`Contradiction` model in favour of these
edges. `charter consistency-check` gains an advisory, always-on `tension_unreconciled`
finding (excluded from `coherent`, fail-closed on load errors); `charter activate`
surfaces the same tension as a warning. The built-in default pack ships a
reconciliation directive (`reconcile-change-scope-tensions`) so it stays coherent out
of the box. Downstream/org-pack `opposed_by` compatibility is handled by a new
`spec-kitty migrate` subcommand (FR-015, resolved below) rather than a deprecation
window, per D1.

**External release dependency (C-008, not in this mission's scope)**: the tension
check is always-on by design (D3), so a curated default charter that does not
co-activate unreconciled tensions is a P0 release-blocker for this mission — tracked
as a **separate** mission (none exists locally as of plan time; verified by search).
FR-011's reconciliation artefact is the interim mitigation that keeps today's
all-active default pack coherent until that separate mission lands. This plan does
not create that mission; it only depends on it at release time.

## Technical Context

**Language/Version**: Python 3.11+ (existing project standard, `pyproject.toml`)
**Primary Dependencies**: pydantic v2 (`DRGNode`/`Relation`/model changes), existing
`src/doctrine/` and `src/specify_cli/` packages, ruamel.yaml (graph-fragment YAML
authoring, already a project dependency). No new third-party dependencies.
**Storage**: N/A — file-based doctrine YAML sources loaded into an in-memory DRG graph;
no database.
**Testing**: pytest, following existing `tests/doctrine/` and `tests/specify_cli/`
layout; `ruff` + `mypy` zero-issue gate (repo standard); dead-symbol gate (symbol-scoped
to `Contradiction`, per NFR-002's explicit carve-out for the unrelated
`ContradictionChecker` symbol).
**Target Platform**: CLI/library, cross-platform (macOS/Linux/CI) — no OS-specific
surface.
**Project Type**: Single project (existing `src/doctrine/`, `src/specify_cli/`) — no
new top-level component, no frontend/backend split.
**Performance Goals**: N/A — doctrine graphs are small-N (dozens of artifacts);
no new performance target beyond existing `consistency-check` latency.
**Constraints**: Must not flip `ConsistencyReport.coherent` to `false` (NFR-001); DRG
load for the tension check fails closed into `verification_errors`, never swallowed
(FR-009); migration must stay green-at-every-boundary per the 7-step order in C-006;
cascade `REFERENCE_RELATIONS` contract (pure-reachability, no per-kind logic) must not
regress (C-003).
**Scale/Scope**: 3 new `Relation` enum members + description registry; 1 new
`NodeKind`; 1 new field on `DRGNode` (`tags`); 21 `opposed_by` occurrences across 3
schema files, 3 `models.py`, 1 extractor, 5 built-in artifact YAML files, 4 test/fixture
files, plus the `Contradiction` model's sole definition site; 1 new CLI subcommand
(FR-015); 1 new built-in reconciliation directive (FR-011).

## Charter Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Evaluated against `.kittify/charter/charter.md` policy summary:

| Principle | Assessment |
|---|---|
| Single canonical authority | Relation vocabulary, the description registry, and `NodeKind` each have one owning module (`src/doctrine/drg/models.py`); no duplicate definitions introduced. **Pass.** |
| Architectural alignment | Change is internal to the existing `src/doctrine/` bounded context; no shared-package-boundary crossing, no new external dependency. **Pass.** |
| DDD + tiered rigour | `Relation`, `NodeKind`, and the tension/reconciliation edges are modelled as domain concepts inside the doctrine bounded context, matching the existing `DRGNode`/`DRGGraph` pattern. **Pass.** |
| ATDD-first | Every FR/NFR/Constraint in spec.md is already tied to a User Story acceptance scenario or a promoted Correctness Invariant (INV-001..005); this plan drives Phase 0/1 outside-in from those. **Pass.** |
| Glossary & terminology adherence | FR-012/NFR-004 make relation self-description + doc-parity a binding requirement, not an afterthought — addressed by the relation-description registry design (data-model.md). **Pass.** |
| Bulk-edit discipline (DIRECTIVE_035) | `change_mode: bulk_edit` set; `occurrence_map.yaml` committed covering all 8 categories for the 21-site `opposed_by`/`Contradiction` removal. **Pass.** |
| Sonar (complexity ceiling 15, no repeated literals ≥3, no empty excepts) | Flagged as an implement-time constraint, not a plan-time violation: `NodeKind` wiring touches multiple lookup tables (`ArtifactKind`, `_SINGULAR_TO_PLURAL`, `_SINGULAR_TO_PER_KIND_FIELD`, activation filter, cascade `_kind_of`) — tasks must hoist any ≥3-repeated kind-string literal to a constant and keep each touched function ≤15 complexity. |

No Charter Check violations requiring justification. **Complexity Tracking table
omitted** (nothing to justify).

## Project Structure

### Documentation (this mission)

```
kitty-specs/doctrine-tension-edges-01KY1WPC/
├── plan.md              # This file
├── research.md           # Phase 0 output
├── data-model.md         # Phase 1 output
├── quickstart.md         # Phase 1 output
├── contracts/            # Phase 1 output
├── occurrence_map.yaml   # Bulk-edit classification (DIRECTIVE_035)
└── tasks/                # Phase 2 output (/spec-kitty.tasks — NOT created by this command)
```

### Source Code (repository root)

Single project — no new top-level directories. Concrete paths this mission touches:

```
src/doctrine/
├── drg/
│   ├── models.py            # Relation enum + registry, NodeKind, DRGNode.tags
│   ├── validator.py         # rejects-target validation (INV-004)
│   └── migration/
│       └── extractor.py     # stop minting replaces from opposed_by
├── directives/
│   ├── models.py             # remove opposed_by field
│   └── built-in/
│       ├── 024-locality-of-change.directive.yaml
│       ├── 025-boy-scout-rule.directive.yaml
│       └── reconcile-change-scope-tensions.directive.yaml   # new (FR-011)
├── tactics/
│   ├── models.py
│   └── built-in/change-apply-smallest-viable-diff.tactic.yaml
├── paradigms/
│   ├── models.py
│   └── built-in/{brownfield-onboarding,c4-incremental-detail-modeling,domain-driven-design}.paradigm.yaml
├── shared/models.py           # remove Contradiction + __all__ entry
└── schemas/{directive,paradigm,tactic}.schema.yaml   # drop opposed_by property + contradiction def

src/charter/
├── drg.py                    # anti_pattern kind wiring: _SINGULAR_TO_PLURAL, _SINGULAR_TO_PER_KIND_FIELD
├── activations.py            # anti_pattern kind wiring: _SINGULAR_TO_PLURAL_KIND
├── pack_context.py           # new activated_anti_patterns field
├── cascade.py                # REFERENCE_RELATIONS — verified: no code change needed (exclusion by omission)
└── consistency_check.py      # tension_unreconciled finding (TensionFinding, unreconciled_tensions), fail-closed load

src/specify_cli/
├── cli/commands/charter/_app.py         # activation-time tension warning
├── charter_runtime/lint/checks/orphan.py  # orphan-lint: drop governs/supersedes branches (FR-008)
├── cli/commands/migrate_cmd.py          # wire new migrate subcommand (FR-015)
└── migration/rewrite_opposed_by.py      # FR-015 rewrite logic (backfill_identity.py precedent)

docs/architecture/doctrine-relationships.md   # relation doc-parity target (FR-012)

tests/doctrine/
├── drg/migration/test_extractor.py       # repoint/remove opposed_by test
├── test_directive_consistency.py         # repoint/remove 3 opposed_by tests
└── fixtures/paradigm/valid/with-tactic-refs.yaml
```

**Structure Decision**: no structural change — all work lands inside the existing
`src/doctrine/`, `src/charter/`, and `src/specify_cli/` packages, following current
module boundaries. The `src/charter/` paths above were verified against the actual
codebase during `/spec-kitty.tasks` (superseding this plan's earlier placeholder
guess of `src/specify_cli/charter_runtime/{consistency,activate}.py`, which do not
exist); the Change Surface Map in spec.md remains the binding cross-surface checklist.

## Implementation Concern Map

> Implementation concerns are NOT work packages. `/spec-kitty.tasks` decides how these
> map to WPs. Sequencing here reflects C-006's green-at-every-boundary migration order.

### IC-01 — Relation vocabulary + NodeKind foundation

- **Purpose**: Add the three `Relation` enum members, the canonical relation-description
  registry, the new `anti_pattern`/`smell` `NodeKind`, and `DRGNode.tags`. This is the
  foundation every other concern builds on (C-006 step 1).
- **Relevant requirements**: FR-001, FR-002, FR-003, FR-004, FR-012 (registry only)
- **Affected surfaces**: `src/doctrine/drg/models.py`
- **Sequencing/depends-on**: none — must land first
- **Risks**: `NodeKind` addition ripples through `ArtifactKind`, `_SINGULAR_TO_PLURAL`,
  `_SINGULAR_TO_PER_KIND_FIELD`, the activation filter, and cascade `_kind_of` — each
  touch point must be updated together or activation/cascade silently mis-handles the
  new kind.

### IC-02 — Hand-author edges + marked anti-pattern nodes

- **Purpose**: Author the `in_tension_with`/`reconciles_tension`/`rejects` edges and the
  6 marked anti-pattern/smell nodes directly in graph fragments (extractor can no longer
  generate them per ADR 2026-07-18-1). Includes the new built-in
  `reconcile-change-scope-tensions` directive (FR-011).
- **Relevant requirements**: FR-006, FR-007, FR-011
- **Affected surfaces**: `src/doctrine/directives/built-in/`, `src/doctrine/tactics/built-in/`,
  `src/doctrine/paradigms/built-in/`, new `reconcile-change-scope-tensions.directive.yaml`
- **Sequencing/depends-on**: IC-01 (enum members must exist before edges reference them —
  Pydantic validation would reject an unknown relation)
- **Risks**: the shipped-graph freshness canary (`test_shipped_graph_yaml_is_fresh`) must
  accept these hand-authored edges post-extractor-retirement; INV-005 (recovered tactic
  tension) must be authored here, not just the flagship 024↔025 pair.

### IC-03 — Retire `opposed_by` / `Contradiction`

- **Purpose**: Remove the `opposed_by` YAML property + extractor-minting logic together
  (C-006 step 3), then the schema property (step 4), then the field + `Contradiction`
  model + imports (step 5).
- **Relevant requirements**: FR-005, NFR-002
- **Affected surfaces**: `src/doctrine/drg/migration/extractor.py`, built-in YAML (opposed_by
  keys), `src/doctrine/schemas/{directive,paradigm,tactic}.schema.yaml`,
  `src/doctrine/{directives,tactics,paradigms}/models.py`, `src/doctrine/shared/models.py`
- **Sequencing/depends-on**: IC-02 (edges must exist before the field they replace is
  dropped, or the built-in pack loses tension information mid-migration)
- **Risks**: dead-symbol gate must be scoped to the `Contradiction` symbol specifically —
  a bare word-grep would false-positive on the unrelated `ContradictionChecker` (see
  occurrence_map.yaml exceptions).

### IC-04 — Read-surface wiring

- **Purpose**: Confirm/exercise symmetric `in_tension_with` query (both directions off one
  stored edge), wire the new `NodeKind` through the activation filter, and add `rejects`-target
  validation in `drg/validator.py`.
- **Relevant requirements**: FR-004 (validator half), INV-001, INV-004
- **Affected surfaces**: `src/doctrine/drg/validator.py`, activation filter in
  `src/charter/drg.py` (`_node_is_activated`)
- **Sequencing/depends-on**: IC-01, IC-03
- **Risks**: A3 confirms `edges_from`/`edges_to` already support this without a new graph
  primitive — do not add one.

### IC-05 — Checkup surface: consistency-check, activate warning, orphan-lint, cascade exclusion

- **Purpose**: Advisory `tension_unreconciled` finding (always-on, excluded from `coherent`,
  fail-closed DRG load); `charter activate` warning; remove phantom `governs`/`supersedes`
  orphan-lint branches + docstring; cascade-exclusion regression test.
- **Relevant requirements**: FR-008, FR-009, FR-010, FR-013, NFR-001, NFR-003
- **Affected surfaces**: `src/specify_cli/charter_runtime/` (consistency-check + activate),
  orphan-lint module, cascade `REFERENCE_RELATIONS` allowlist + regression test
- **Sequencing/depends-on**: IC-01, IC-02, IC-04
- **Risks**: NFR-001 requires the checker to actually fire (a no-op returning `[]` fails
  the requirement) — needs a positive assertion test, not just an absence-of-crash test.

### IC-06 — FR-015 downstream migration subcommand

- **Purpose**: New `spec-kitty migrate` subcommand rewriting org-pack-authored `opposed_by`
  → `in_tension_with`/`rejects` edges, modeled on `migration/backfill_identity.py` +
  `cli/commands/migrate_cmd.py`. No deprecation window (resolved decision).
- **Relevant requirements**: FR-015
- **Affected surfaces**: `src/specify_cli/migration/<new module>.py`,
  `src/specify_cli/cli/commands/migrate_cmd.py`
- **Sequencing/depends-on**: IC-01 (needs the target relations to rewrite into)
- **Risks**: must handle the `additionalProperties: false` schema rejecting un-migrated
  `opposed_by` cleanly (clear error naming the migration command), not a raw validation
  traceback.

### IC-07 — Doc-parity + documentation

- **Purpose**: Populate `docs/architecture/doctrine-relationships.md` with the three new
  relation descriptions (matching the registry verbatim) and build the enum↔doc parity
  check (does not exist today — a deliverable, per Assumption A2).
- **Relevant requirements**: FR-012, NFR-004
- **Affected surfaces**: `docs/architecture/doctrine-relationships.md`, new parity-check
  test/module
- **Sequencing/depends-on**: IC-01
- **Risks**: parity check must be red-first (fails when a description is mutated) —
  a check that only verifies presence, not content-equality, would satisfy the letter
  and miss the point.
