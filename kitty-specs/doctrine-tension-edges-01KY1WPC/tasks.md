---
description: "Work package task list for Doctrine Tension as First-Class DRG Edges"
---

# Work Packages: Doctrine Tension as First-Class DRG Edges

**Inputs**: `kitty-specs/doctrine-tension-edges-01KY1WPC/{spec.md, plan.md, research.md, data-model.md, contracts/, quickstart.md, occurrence_map.yaml}`
**Prerequisites**: plan.md, spec.md, data-model.md, contracts/, occurrence_map.yaml (this mission runs under `change_mode: bulk_edit` — every WP's diff is checked against `occurrence_map.yaml` at review time)

**Tests**: Included — spec.md's Correctness Invariants (INV-001..005) and Success Criteria (SC-001..005) are only provable with tests, and NFR-005 requires focused tests for every new branch/helper.

**Organization**: 41 subtasks (`T001`-`T041`) roll up into 8 work packages (`WP01`-`WP08`), sequenced per plan.md's Implementation Concern Map (IC-01..IC-07) and Constraint C-006's green-at-every-boundary migration order.

**Prompt Files**: Each work package references a matching file in `tasks/`. This file is the high-level checklist; implementation detail lives in the prompt files.

## Path Conventions

Single project — `src/doctrine/`, `src/charter/`, `src/specify_cli/`, `tests/`, `docs/`. No frontend/backend split (per plan.md Project Structure).

---

## Work Package WP01: Relation vocabulary + NodeKind foundation (Priority: P0)

**Goal**: Add the three `Relation` enum members, the relation-description registry (with final description text), the `anti_pattern` `NodeKind`, and `DRGNode.tags`.
**Independent Test**: `Relation.IN_TENSION_WITH`/`RECONCILES_TENSION`/`REJECTS` and `NodeKind.ANTI_PATTERN` exist and round-trip through `DRGNode`/`DRGEdge` validation; `RELATION_DESCRIPTIONS` has all 3 entries.
**Prompt**: `tasks/WP01-relation-vocabulary-foundation.md`
**Requirement Refs**: FR-001, FR-002, FR-003, FR-004, FR-012

### Included Subtasks

- [x] T001 Add `IN_TENSION_WITH`, `RECONCILES_TENSION`, `REJECTS` to `Relation` (`src/doctrine/drg/models.py`)
- [x] T002 Add `RELATION_DESCRIPTIONS` registry with final description text for the 3 new relations (`src/doctrine/drg/models.py`)
- [x] T003 [P] Add `ANTI_PATTERN` to `NodeKind` + URN-prefix wiring in `DRGNode._validate_urn` (`src/doctrine/drg/models.py`)
- [x] T004 [P] Add `tags: list[str] = Field(default_factory=list)` to `DRGNode` (`src/doctrine/drg/models.py`)
- [x] T005 Add corresponding `ArtifactKind` member (`src/doctrine/artifact_kinds.py`)
- [x] T006 Unit tests: enum values, `RELATION_DESCRIPTIONS` completeness, `DRGNode.tags` round-trip, `anti_pattern:<id>` URN acceptance (new `tests/doctrine/drg/test_models.py`; extend `tests/doctrine/drg/test_nodekind_artifactkind.py` and `test_kind_mapping_totality.py`)

### Implementation Notes

- T001/T002 are the same file, sequential. T003/T004 touch the same file but are independent edits — parallel-safe in intent, sequential in practice within one WP.
- T006 extends two existing totality/mapping tests, not just the new file — `test_kind_mapping_totality.py` likely asserts every `NodeKind` maps somewhere; adding `ANTI_PATTERN` without updating its expectations will break it (a useful regression signal, not a bug to route around).

### Parallel Opportunities

- T003/T004/T005 touch different declarations and can be drafted concurrently by the same implementer before running tests.

### Dependencies

- None — foundation package, must land first (C-006 step 1).

### Risks & Mitigations

- `ANTI_PATTERN` ripples into `_SINGULAR_TO_PLURAL`/`_SINGULAR_TO_PER_KIND_FIELD` (WP04) and `_SINGULAR_TO_PLURAL_KIND` (WP04) — this WP only adds the enum member; WP04 owns the activation-filter wiring. Do not add those mappings here — it would create an ownership conflict.

---

## Work Package WP02: Hand-author tension/reconciliation/rejection edges (Priority: P0)

**Goal**: Author the new-relation edges and marked anti-pattern nodes directly in the per-kind DRG graph fragments (`*.graph.yaml`) — the extractor has no frontmatter mechanism for these three relations, so they are hand-authored, not derived.
**Independent Test**: Loading `directive.graph.yaml`/`tactic.graph.yaml`/`paradigm.graph.yaml` produces a graph containing the 024↔025 and smallest-viable-diff↔025 `in_tension_with` edges, the 6 anti-pattern nodes, the 8 `rejects` edges, and the new `reconcile-change-scope-tensions` directive with its 3 `reconciles_tension` edges.
**Prompt**: `tasks/WP02-hand-author-tension-edges.md`
**Requirement Refs**: FR-006, FR-007, FR-011

### Included Subtasks

- [x] T007 Hand-author `in_tension_with` edge, `directive:024-locality-of-change` ↔ `directive:025-boy-scout-rule` (lex-smaller URN as source) in `src/doctrine/directive.graph.yaml`
- [x] T008 Hand-author `in_tension_with` edge, `tactic:change-apply-smallest-viable-diff` ↔ `directive:025-boy-scout-rule` (INV-005 — the recovered tactic↔directive tension) across `tactic.graph.yaml`/`directive.graph.yaml`
- [x] T009 Create the 6 marked anti-pattern/smell nodes (`anemic-domain-model`, `big-ball-of-mud`, `big-upfront-design`, `code-is-the-documentation`, `database-driven-design`, `single-diagram-architecture`) with `kind: anti_pattern` + `tags` in `paradigm.graph.yaml`
- [x] T010 Author the 8 `rejects` edges from the relevant paradigms to the 6 nodes from T009 in `paradigm.graph.yaml`
- [x] T011 Create `src/doctrine/directives/built-in/reconcile-change-scope-tensions.directive.yaml` (new built-in directive; body explains how to weigh the 024/025/smallest-viable-diff tensions) + its `reconciles_tension` edges to all three in `directive.graph.yaml`/`tactic.graph.yaml`
- [x] T012 Verify the new content loads without validation errors (existing graph-load tests) and record how the shipped-graph freshness canary will need to tolerate these hand-authored edges once WP03 regenerates the graph (do not modify the canary here — that is WP03's job)

### Implementation Notes

- This is authored content, not a schema/model change — depends on WP01 for the enum members to exist (Pydantic will reject an edge referencing an unknown `Relation`).
- T011's new directive needs *ordinary* `requires`/`scope` edges too if applicable — those remain extractor-derived from its frontmatter as normal; only the `reconciles_tension` edges are hand-authored.
- Do not remove any `opposed_by` content here — that is WP03, sequenced after this WP so the pack never loses tension information mid-migration (C-006).

### Parallel Opportunities

- T007/T008 (directive/tactic graph) and T009/T010 (paradigm graph) touch different files and can proceed in parallel.

### Dependencies

- Depends on WP01.

### Risks & Mitigations

- The shipped-graph freshness canary (`test_shipped_graph_yaml_is_fresh` et al.) currently expects the committed graph to be byte-identical to a fresh extractor run — WP03 must reconcile that expectation with these hand-authored additions surviving regeneration. Flag this explicitly in the WP02→WP03 handoff rather than silently hoping WP03 notices.

---

## Work Package WP03: Retire `opposed_by` / `Contradiction` (Priority: P0)

**Goal**: Remove the `opposed_by` field/schema-property, the extractor logic that mints `replaces` from it, and the `Contradiction` model — in the C-006-mandated order (YAML+extractor together, then schema, then field+model together) — without losing WP02's hand-authored edges.
**Independent Test**: `grep -rn "opposed_by" src/ docs/ tests/` returns zero hits; `doctrine.shared.models.Contradiction` and its `__all__` entry are gone; the dead-symbol gate (scoped to that symbol) is green; the 024↔025 `replaces` cycle no longer exists in the regenerated graph and WP02's `in_tension_with`/`rejects`/`reconciles_tension` edges survive.
**Prompt**: `tasks/WP03-retire-opposed-by.md`
**Requirement Refs**: FR-005, NFR-002

### Included Subtasks

- [x] T013 Remove the `opposed_by`-minting block(s) from `src/doctrine/drg/migration/extractor.py` (the block that emits a `Relation.REPLACES` edge from an `opposed_by` frontmatter entry)
- [x] T014 Remove `opposed_by:` from the 5 built-in YAML sources (`024-locality-of-change.directive.yaml`, `025-boy-scout-rule.directive.yaml`, `change-apply-smallest-viable-diff.tactic.yaml`, and the 3 paradigm files: `brownfield-onboarding`, `c4-incremental-detail-modeling`, `domain-driven-design`)
- [x] T015 Remove the `opposed_by` property + `contradiction` definition from `src/doctrine/schemas/{directive,paradigm,tactic}.schema.yaml`
- [x] T016 Remove the `opposed_by` field from `src/doctrine/{directives,tactics,paradigms}/models.py`; remove the `Contradiction` model + its `__all__` entry from `src/doctrine/shared/models.py`; remove now-dead imports
- [x] T017 Remove/repoint the opposed_by-specific tests: the extractor test at `tests/doctrine/drg/migration/test_extractor.py` (`test_directive_opposed_by_produces_replaces`), the 3 tests in `tests/doctrine/test_directive_consistency.py`, and update `tests/doctrine/fixtures/paradigm/valid/with-tactic-refs.yaml`
- [x] T018 Regenerate the shipped `*.graph.yaml` fragments and reconcile the freshness canary so it accepts WP02's hand-authored edges while still catching genuine drift; confirm zero `opposed_by` hits and a green dead-symbol gate

### Implementation Notes

- Follow C-006's order strictly: T013+T014 together (blocks that stop minting AND the YAML that would otherwise still trigger them), then T015, then T016. Authoring the edge before its enum member (already done in WP01/WP02) or dropping the schema property before the YAML would produce a red state.
- **Anticipated small out-of-map edit**: T018 touches `src/doctrine/*.graph.yaml` — files WP02 owns — only to regenerate/drop the now-stale `opposed_by`-derived `replaces` edges. Do not re-author or remove WP02's new edges; this is a one-line-rationale out-of-map touch (per the occurrence-map exception process), not a claim of ownership over those files.
- The dead-symbol gate must be scoped to the `Contradiction` symbol specifically (module/class, not the bare word) — `src/specify_cli/charter_runtime/lint/checks/contradiction.py`'s unrelated `ContradictionChecker` and its importers/tests are explicitly out of scope (see `occurrence_map.yaml` exceptions) and must not be touched.

### Parallel Opportunities

- T014/T015 (different files, same removal) can proceed in parallel; T016 should follow both (needs the schema gone first per C-006 step ordering intent, though Python import removal doesn't strictly require it — keep the stated order for reviewability).

### Dependencies

- Depends on WP02 (edges must exist before the field they replace is dropped).

### Risks & Mitigations

- Highest-risk WP for silent breakage (touches schema + models + extractor + built-in content + tests in one pass). Run the full `tests/doctrine/` suite plus `ruff`/`mypy` before marking done, not just the touched test files.
- This WP is the primary surface governed by `occurrence_map.yaml`'s `bulk_edit` classification — review will run the diff-compliance check against it.

---

## Work Package WP04: Read-surface wiring — validator + activation filter (Priority: P1)

**Goal**: Validate `rejects` targets (INV-004), wire the `anti_pattern` kind through the activation-filter's kind/per-ID gates, and confirm symmetric `in_tension_with` query (INV-001).
**Independent Test**: A `rejects` edge to an unmarked node raises a validation error; an `anti_pattern` node's activation is gated the same way every other kind is gated; querying a stored `in_tension_with` edge from either endpoint returns the pair.
**Prompt**: `tasks/WP04-read-surface-wiring.md`
**Requirement Refs**: FR-004

### Included Subtasks

- [x] T019 Add `"anti_pattern": "anti_patterns"` to `_SINGULAR_TO_PLURAL` and the corresponding `"activated_anti_patterns"` entry to `_SINGULAR_TO_PER_KIND_FIELD` (`src/charter/drg.py`); mirror the plural mapping in `_SINGULAR_TO_PLURAL_KIND` (`src/charter/activations.py`)
- [x] T020 Add `activated_anti_patterns: frozenset[str] | None` field to `PackContext` (`src/charter/pack_context.py`), following the existing per-kind field pattern
- [x] T021 Add `rejects`-target validation to `src/doctrine/drg/validator.py`: a `rejects` edge whose target lacks `kind == NodeKind.ANTI_PATTERN` is a validation error (INV-004)
- [x] T022 Test: symmetric read (INV-001) — a single stored `in_tension_with` edge is discoverable from both endpoint URNs via the graph's existing query helpers (new `tests/doctrine/drg/test_validator.py` or extend an existing DRG test)
- [x] T023 Tests: `anti_pattern` kind activation-gating behaves like every other kind (extend `tests/charter/test_drg_filtering.py` / `test_activation_filtered_drg.py`); `rejects`-target validation error case (new `tests/doctrine/drg/test_validator.py`)

### Implementation Notes

- **Verified, no code change needed**: `src/charter/cascade.py::_kind_of` resolves generically via `ArtifactKind(prefix)` — once WP01's `ArtifactKind` member exists, `_kind_of` handles `anti_pattern` URNs correctly with zero edits. Do not touch `cascade.py` in this WP.
- Before T019/T020, confirm whether `anti_pattern` nodes should default-allow (skip the per-kind config gate entirely, since they're validation targets rather than user-activatable content) or be config-gated like every other kind. FR-004 explicitly calls for wiring through `_SINGULAR_TO_PLURAL`/`_SINGULAR_TO_PER_KIND_FIELD`, so the spec's answer is config-gated — implement it that way even though `_node_is_activated`'s default-allow-for-unknown-kind behavior would otherwise make this optional.

### Parallel Opportunities

- T019/T020 (activation-filter kind wiring) and T021 (validator) touch unrelated files and can proceed in parallel.

### Dependencies

- Depends on WP01 only (needs `ANTI_PATTERN`/`ArtifactKind` to exist). This WP's tests use synthetic constructed graphs, not the real built-in pack, so it needs neither WP02's authored edges nor WP03's removal — it runs in parallel with both.

### Risks & Mitigations

- Three near-duplicate singular→plural dicts (`drg.py`, `activations.py`, and potentially a third) must all move together or activation/CLI parsing diverges — cross-check all call sites of each dict before considering this WP done.

---

## Work Package WP05: Consistency-check finding + activate warning (Priority: P1)

**Goal**: Advisory, always-on `tension_unreconciled` finding on `ConsistencyReport` (excluded from `coherent`, fail-closed on load errors) and the matching `charter activate` warning.
**Independent Test**: Per `contracts/tension-finding.md` — co-activated unreconciled pair produces exactly one finding with both resolution paths; only-one-side-active produces none; removing the built-in reconciler makes the 024/025 finding reappear, restoring it clears it (SC-002).
**Prompt**: `tasks/WP05-consistency-check-and-activate-warning.md`
**Requirement Refs**: FR-009, FR-010

### Included Subtasks

- [x] T024 Add `TensionFinding` (sorted URN pair + the two fixed resolution-path strings) and `unreconciled_tensions: list[TensionFinding]` on `ConsistencyReport` (`src/charter/consistency_check.py`), excluded from the `coherent` reduction, and update `to_json()`
- [x] T025 Implement the tension scan over the activation-filtered graph: one finding per co-activated `in_tension_with` pair, keyed on the sorted URN pair for dedup (Edge Case: symmetric authoring drift), with no transitive closure (INV-002 — `A⋈B` + `B⋈C` never synthesizes `A⋈C`)
- [x] T026 Implement the reconciliation check: a pair is resolved only when an active artefact has `reconciles_tension` edges to **both** sides (half-reconciled — only one edge — does not resolve, US2 sc2)
- [x] T027 Make the DRG load for this check fail closed into `verification_errors` — any exception during the scan surfaces there, never silently reduces to an empty finding list
- [x] T028 Add the `charter activate` warning using the same `TensionFinding` shape, alongside existing activation warnings (locate the activate command in `src/specify_cli/cli/commands/charter/`)
- [x] T029 Tests (`contracts/tension-finding.md` is the spec): NFR-001 positive assertion (finding present when warranted — a no-op returning `[]` must fail this test); non-finding case (only one side active); SC-002 before/after (remove `reconcile-change-scope-tensions` → findings appear; restore → clear); half-reconciled case (new `tests/charter/test_tension_unreconciled.py`; extend `tests/charter/test_consistency_check.py`)

### Implementation Notes

- T024-T027 are one logical unit (the finding + its computation) — do not split the dedup/non-transitivity logic from the fail-closed error handling; a scan that computes findings correctly but swallows exceptions fails FR-009 just as badly as one with no logic at all.
- T028 depends on T024's `TensionFinding` shape existing first.

### Parallel Opportunities

- Limited — T024→T025→T026→T027 are a dependency chain within this WP. T028 can start once T024 lands.

### Dependencies

- Depends on WP01, WP02 (needs the built-in reconciler + tension edges to exist for SC-002's live assertion). No technical dependency on WP04 — this WP's scan only ever looks at `in_tension_with`/`reconciles_tension` edges among directive/tactic nodes, never `rejects` edges or `anti_pattern` nodes, so WP04's activation-filter wiring is orthogonal — this WP runs in parallel with WP04.

### Risks & Mitigations

- NFR-001's "a no-op checker returning `[]` fails this requirement" is a real trap — write the positive-finding test before the implementation (red-first) so it's impossible to accidentally ship a checker that never fires.

---

## Work Package WP06: Orphan-lint fix + cascade exclusion regression (Priority: P1)

**Goal**: Remove the phantom `governs`/`supersedes` orphan-lint branches (FR-008, closes #2737) and add the regression test proving the three new relations stay out of cascade's `REFERENCE_RELATIONS` allowlist (FR-013).
**Independent Test**: `charter lint`'s `orphaned_directive` findings equal exactly `{DIRECTIVE_035, DIRECTIVE_039}`; activating one side of a tension never auto-activates the other (INV-003).
**Prompt**: `tasks/WP06-orphan-lint-and-cascade-exclusion.md`
**Requirement Refs**: FR-008, FR-013

### Included Subtasks

- [x] T030 Remove the `governs` (directive) and `supersedes` (adr) branches — and their module-docstring references — from `_ORPHAN_RULES` in `src/specify_cli/charter_runtime/lint/checks/orphan.py` (neither is a real `Relation` enum member)
- [x] T031 Test: `orphaned_directive` findings equal exactly `{DIRECTIVE_035, DIRECTIVE_039}` — count == 2, zero false positives on referenced directives (extend `tests/specify_cli/charter_lint/checks/test_orphan.py`)
- [x] T032 Add a regression test asserting `{Relation.IN_TENSION_WITH, Relation.RECONCILES_TENSION, Relation.REJECTS} & cascade.REFERENCE_RELATIONS == frozenset()` (extend `tests/charter/test_cascade.py`) — exclusion is by omission, so this test IS the FR-013 deliverable, not a supporting check for a code change
- [x] T033 Regression test (INV-003): activating one side of a tension pair does not auto-activate the other; activating `reconcile-change-scope-tensions` does not activate 024/025/the tactic (new `tests/charter/test_tension_cascade_exclusion.py`)

### Implementation Notes

- T030 is the only source change in this WP — T032 requires no `cascade.py` edit (the three relations are simply never added to the allowlist); do not "fix" this by writing a denylist check, which would reintroduce the per-kind branching the cascade engine's design deliberately avoids (C-003).
- Do not touch `src/charter/cascade.py` itself in this WP — WP04 already confirmed `_kind_of` needs no change, and `REFERENCE_RELATIONS` needs no change either (correct-by-omission).

### Parallel Opportunities

- T030/T031 (orphan-lint) and T032/T033 (cascade) are independent pairs and can proceed in parallel.

### Dependencies

- Depends on WP01 (needs the 3 relations to exist to assert their absence from the allowlist) and WP02 (INV-003's test needs the actual tension/reconciler edges to exist).

### Risks & Mitigations

- A cascade test that only checks "no crash" instead of "specific relations absent from the allowlist" would pass vacuously — assert the frozenset intersection explicitly, not just call-and-observe.

---

## Work Package WP07: `spec-kitty migrate` downstream compatibility subcommand (Priority: P2)

**Goal**: New CLI subcommand rewriting org-pack-authored `opposed_by` → `in_tension_with`/`rejects` edges (FR-015, resolved decision: no deprecation window).
**Independent Test**: Per `contracts/migrate-opposed-by.md` — `--dry-run` reports planned rewrites without writing; a real run rewrites and removes `opposed_by`; a second run against an already-migrated pack is a no-op; an unclassifiable entry produces a clear diagnostic, not a raw traceback.
**Prompt**: `tasks/WP07-migrate-opposed-by-subcommand.md`
**Requirement Refs**: FR-015

### Included Subtasks

- [x] T034 Implement the rewrite logic in a new `src/specify_cli/migration/rewrite_opposed_by.py`: classify each `opposed_by` entry (tension-style → `in_tension_with` edge; anti-pattern-rejection-style → `rejects` edge, creating/linking an `anti_pattern`-marked target node), modeled on `migration/backfill_identity.py`
- [x] T035 Wire `spec-kitty migrate rewrite-opposed-by [--pack PATH] [--dry-run] [--json]` in `src/specify_cli/cli/commands/migrate_cmd.py`, following the existing subcommand conventions (e.g. `backfill-identity`)
- [x] T036 Diagnostic path: an unclassifiable `opposed_by` entry exits non-zero with a clear message naming the entry and why it couldn't be classified — never a raw Pydantic validation traceback
- [x] T037 Tests: idempotency (second run on an already-migrated pack is a no-op), `--dry-run` writes nothing, successful rewrite removes the `opposed_by` key, unclassifiable-entry diagnostic (new `tests/specify_cli/migration/test_rewrite_opposed_by.py`)

### Implementation Notes

- This WP is fully additive/new code — it does not touch any file another WP owns. It can start as soon as WP01's relations exist; it does not need WP02/WP03 to be done first (it operates on *external* org-pack YAML, not this repo's built-in content).

### Parallel Opportunities

- Can run fully in parallel with WP02-WP06 once WP01 is done.

### Dependencies

- Depends on WP01 only.

### Risks & Mitigations

- Without this command, removing `opposed_by` from `additionalProperties: false` schemas (WP03) breaks downstream consumers with only a validation error pointing at the symptom. Land this WP before or alongside WP03's release, not long after.

---

## Work Package WP08: Relation doc-parity (Priority: P3)

**Goal**: Mirror the three new relations' descriptions into `docs/architecture/doctrine-relationships.md` and build the enum↔doc parity check (does not exist today — a deliverable per Assumption A2).
**Independent Test**: Per US5 — parity check passes when registry and doc match; mutating one relation's description in the doc only makes the check fail, naming that relation (red-first).
**Prompt**: `tasks/WP08-relation-doc-parity.md`
**Requirement Refs**: FR-012

### Included Subtasks

- [x] T038 Add matching entries for the 3 new relations to `docs/architecture/doctrine-relationships.md`, verbatim against WP01's `RELATION_DESCRIPTIONS` text
- [x] T039 Build the enum↔doc parity check comparing `RELATION_DESCRIPTIONS` values to the doc file's text for the 3 relations (new module/test — no such check exists today)
- [x] T040 Red-first test: mutate one relation's description in the doc only → parity check fails naming that relation; revert → passes (new `tests/doctrine/test_relation_doc_parity.py`)
- [x] T041 Wire the parity check into the test suite (or `charter lint`, if that is the more consistent home) so it runs automatically, not as a manual step

### Implementation Notes

- Read-only with respect to `src/doctrine/drg/models.py` — this WP consumes WP01's registry, it does not edit it. If the registry's placeholder text needs wordsmithing, that edit belongs in WP01, not here (avoids an ownership conflict on `models.py`).

### Parallel Opportunities

- Can run fully in parallel with WP02-WP07 once WP01 is done.

### Dependencies

- Depends on WP01 only.

### Risks & Mitigations

- A parity check that only verifies presence (both sides have *a* description) rather than content-equality would satisfy the letter and miss the point of NFR-004 — the red-first test in T040 is the guard against that shortcut.

---

## Dependency & Execution Summary

- **Sequence**: WP01 → WP02 → {WP03, WP04, WP06 in parallel (WP04 needs only WP01; WP03 and WP06 need WP02)} → WP05 (needs WP01+WP02 only, but is easiest to land once WP03 is settled to avoid reviewing against a moving target) → {WP07, WP08 in parallel from WP01}.
- **Parallelization**: WP07 and WP08 need only WP01 and can run the entire time WP02-WP06 are in progress. WP04 needs only WP01 and can run in parallel with WP02/WP03. WP05 needs only WP01+WP02 and can run in parallel with WP03/WP04/WP06. Within WP02, directive/tactic-graph edits (T007/T008) and paradigm-graph edits (T009/T010) are independent.
- **MVP Scope**: WP01 + WP02 + WP03 deliver the core data-model migration (US3 — `opposed_by` retired, tensions modeled as edges). WP05 is required to make the tension visible to an operator (US1 — the mission's actual reason to exist), so a genuinely usable MVP is WP01-WP05.

---

## Requirements Coverage Summary

| Requirement ID | Covered By Work Package(s) |
|----------------|----------------------------|
| FR-001 | WP01 |
| FR-002 | WP01, WP05 |
| FR-003 | WP01 |
| FR-004 | WP01, WP04 |
| FR-005 | WP03 |
| FR-006 | WP02 |
| FR-007 | WP02 |
| FR-008 | WP06 |
| FR-009 | WP05 |
| FR-010 | WP05 |
| FR-011 | WP02 |
| FR-012 | WP01, WP08 |
| FR-013 | WP06 |
| FR-014 | WP01, WP02, WP03, WP04, WP05 (cross-cutting — see plan.md Change Surface Map) |
| FR-015 | WP07 |
| NFR-001 | WP05 |
| NFR-002 | WP03 |
| NFR-003 | WP06 |
| NFR-004 | WP08 |
| NFR-005 | All WPs (cross-cutting quality gate — ruff/mypy/tests, not mapped to one WP by design) |

---

## Subtask Index (Reference)

| Subtask ID | Summary | Work Package | Priority | Parallel? |
|------------|---------|---------------|----------|-----------|
| T001 | Add 3 new Relation enum members | WP01 | P0 | No |
| T002 | Add RELATION_DESCRIPTIONS registry | WP01 | P0 | No |
| T003 | Add ANTI_PATTERN NodeKind | WP01 | P0 | Yes |
| T004 | Add DRGNode.tags field | WP01 | P0 | Yes |
| T005 | Add ArtifactKind member | WP01 | P0 | Yes |
| T006 | Foundation unit tests | WP01 | P0 | No |
| T007 | Author 024↔025 in_tension_with edge | WP02 | P0 | Yes |
| T008 | Author tactic↔025 in_tension_with edge (INV-005) | WP02 | P0 | Yes |
| T009 | Create 6 anti-pattern nodes | WP02 | P0 | Yes |
| T010 | Author 8 rejects edges | WP02 | P0 | Yes |
| T011 | Create reconcile-change-scope-tensions directive | WP02 | P0 | No |
| T012 | Verify new content loads; note freshness-canary handoff | WP02 | P0 | No |
| T013 | Remove opposed_by-minting extractor blocks | WP03 | P0 | No |
| T014 | Remove opposed_by from 5 built-in YAML files | WP03 | P0 | Yes |
| T015 | Remove opposed_by/contradiction from 3 schema files | WP03 | P0 | Yes |
| T016 | Remove opposed_by field + Contradiction model | WP03 | P0 | No |
| T017 | Remove/repoint opposed_by-specific tests | WP03 | P0 | No |
| T018 | Regenerate graph.yaml; reconcile freshness canary | WP03 | P0 | No |
| T019 | Wire anti_pattern into activation-filter kind maps | WP04 | P1 | Yes |
| T020 | Add activated_anti_patterns to PackContext | WP04 | P1 | Yes |
| T021 | Add rejects-target validation (INV-004) | WP04 | P1 | Yes |
| T022 | Symmetric-read test (INV-001) | WP04 | P1 | No |
| T023 | Activation-gating + validation tests | WP04 | P1 | No |
| T024 | Add TensionFinding + unreconciled_tensions | WP05 | P1 | No |
| T025 | Implement tension scan (dedup, non-transitive) | WP05 | P1 | No |
| T026 | Implement reconciliation check | WP05 | P1 | No |
| T027 | Fail-closed DRG load error handling | WP05 | P1 | No |
| T028 | Add charter activate warning | WP05 | P1 | No |
| T029 | Consistency-check + activate tests | WP05 | P1 | No |
| T030 | Remove phantom orphan-lint branches | WP06 | P1 | Yes |
| T031 | Orphan-lint exact-set test | WP06 | P1 | Yes |
| T032 | Cascade REFERENCE_RELATIONS exclusion test | WP06 | P1 | Yes |
| T033 | Cascade non-auto-activation test (INV-003) | WP06 | P1 | Yes |
| T034 | Implement rewrite_opposed_by module | WP07 | P2 | No |
| T035 | Wire migrate rewrite-opposed-by CLI command | WP07 | P2 | No |
| T036 | Unclassifiable-entry diagnostic | WP07 | P2 | No |
| T037 | Migration idempotency + CLI tests | WP07 | P2 | No |
| T038 | Add relation descriptions to doc | WP08 | P3 | Yes |
| T039 | Build enum↔doc parity check | WP08 | P3 | No |
| T040 | Red-first parity test | WP08 | P3 | No |
| T041 | Wire parity check into test suite | WP08 | P3 | No |

---

> 8 work packages, 41 subtasks. Average ~5 subtasks/WP — within the 3-7 ideal range on every WP.
