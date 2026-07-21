# Mission Specification: Doctrine Tension as First-Class DRG Edges

**Mission Branch**: `doctrine/drg-missing-links-analysis`
**Created**: 2026-07-21
**Status**: Draft
**Input**: Model doctrine tension as first-class DRG edges, retiring the legacy `opposed_by` field. Anchored on Accepted ADR `docs/adr/3.x/2026-07-21-1-in-tension-with-drg-edge.md`. Anchor ticket #2537 under epic #2466; folds #2737. Out of scope: cascade-all-kinds (#2829), `delegates_to` swarm (#2827).

> **Refined 2026-07-21** after a 4-lens adversarial/enhancement squad (doctrine-daphne, reviewer-renata, architect-alphonso, paula-patterns). Non-decision findings are remediated below; three escalated decisions (D1/D2/D3) were resolved by the operator and folded into the requirements (see Resolved Decisions).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Operator sees co-activated tension and how to resolve it (Priority: P1)

An operator activates a doctrine artefact (or runs a consistency check) on a pack in which two artefacts that are *in tension* — e.g. "Locality of Change" (DIRECTIVE_024) and "Boy Scout Rule" (DIRECTIVE_025) — are both active. Instead of the competition being invisible (so an agent silently picks a winner), the tooling surfaces an advisory finding that names both artefacts and states the two ways to resolve it.

**Why this priority**: This is the mission's reason to exist — making silent doctrine competition visible with a concrete resolution path.

**Independent Test**: On a pack with two co-activated in-tension artefacts and no reconciliation, `charter consistency-check` and `charter activate` both emit exactly one `tension_unreconciled` finding naming both artefacts and both resolution paths; the run stays coherent (advisory).

**Acceptance Scenarios**:

1. **Given** two artefacts declared `in_tension_with` each other, both in the active set, and no active reconciler, **When** the operator runs `charter consistency-check`, **Then** exactly one `tension_unreconciled` finding lists the pair and both resolution-path strings ("deactivate one side" AND "activate a reconciler"), and `coherent` stays `true`.
2. **Given** the same pair, **When** the operator activates one of them via `charter activate`, **Then** a warning surfaces the tension alongside the existing warnings.
3. **Given** an in-tension pair where only one side is in the active set, **When** consistency-check runs, **Then** no tension finding is raised.

---

### User Story 2 - Tension is resolved by a reconciliation artefact (Priority: P1)

The operator (or pack author) resolves a flagged tension not by dropping a rule, but by activating a reconciliation artefact whose body explains how to weigh the two rules and which links to both via `reconciles_tension`.

**Why this priority**: The resolution path is half the value. The built-in default pack ships 024+025 in tension, so it must carry such an artefact to stay coherent.

**Independent Test**: Adding an active artefact with `reconciles_tension` edges to both sides of a flagged pair clears the finding; removing either edge (or deactivating the artefact) re-raises it.

**Acceptance Scenarios**:

1. **Given** a flagged in-tension pair `(A, B)`, **When** an active artefact `R` has `reconciles_tension` edges to both `A` and `B`, **Then** the pair is treated as resolved and no finding is raised.
2. **Given** the same `R` but with only one `reconciles_tension` edge (to `A` only), **When** consistency-check runs, **Then** the pair remains flagged (half-reconciled does not resolve).
3. **Given** the built-in default pack with the shipped reconciliation directive `reconcile-change-scope-tensions` active, **When** consistency-check runs out of the box, **Then** the 024/025 (and smallest-viable-diff/025) tensions are reconciled and no finding is raised.

---

### User Story 3 - `opposed_by` is retired in favour of composable edges (Priority: P2)

A doctrine maintainer removes the legacy `opposed_by` field entirely. Genuine tensions become `in_tension_with` edges; rejections of anti-patterns become `rejects` edges pointing at first-class, marked anti-pattern/smell nodes. No surface anywhere still reads `opposed_by`.

**Why this priority**: `opposed_by` is mis-encoded (extractor maps it to `replaces`, producing a nonsensical mutual 024↔025 cycle), inconsistently consumed (dead for tactics), and fights the field→edge migration.

**Independent Test**: `grep -rn "opposed_by"` over `src/`, `docs/`, and `tests/` returns zero hits; the `doctrine.shared.models.Contradiction` symbol and its `__all__` entry are removed (dead-symbol gate green); the 024↔025 `replaces` cycle is replaced by a single `in_tension_with` edge; the 8 paradigm anti-pattern rejections are `rejects` edges to 6 marked nodes.

**Acceptance Scenarios**:

1. **Given** the migrated codebase, **When** `opposed_by` is searched across `src/`, `docs/`, and `tests/`, **Then** there are zero occurrences (field, schema, model, extractor, YAML, docs, tests).
2. **Given** a `rejects` edge, **When** its target node is inspected, **Then** the target is a first-class node carrying `tags: [anti-pattern]` (or `[smell]`) — not an extractor-invented phantom, and not still declared `kind: paradigm`/`kind: tactic` without the marker.
3. **Given** the migration, **When** the built-in `replaces` edge set is enumerated, **Then** it is exactly empty — every current `replaces` edge is `opposed_by`-derived (the 024↔025 cycle → `in_tension_with`; the 8 paradigm edges → `rejects`), and no new `replaces` edge is introduced. (This guards C-001: the *canonical* pack-layer `replaces` semantics are untouched precisely because the built-in layer authors none.)

---

### User Story 4 - Directives stop being falsely flagged as orphaned (Priority: P2)

A pack author running `charter lint` no longer sees all built-in directives flagged `orphaned_directive`. The phantom `governs` (directive) and `supersedes` (adr) orphan-lint branches — neither of which is a real relation the model can author — are removed. Only the genuinely-disconnected directives surface.

**Why this priority**: Persistent false-positive noise on every otherwise-green run for every consumer (#2737).

**Independent Test**: `charter lint` on the built-in layer flags `orphaned_directive` for **exactly** `{DIRECTIVE_035, DIRECTIVE_039}` — the two directives with zero incoming edges — and for no directive that is referenced via `scope`/`requires`/`suggests`.

**Acceptance Scenarios**:

1. **Given** the built-in layer, **When** `charter lint` runs after the fix, **Then** the set of `orphaned_directive` findings equals exactly `{DIRECTIVE_035, DIRECTIVE_039}` (count == 2) — genuine orphans still surface; referenced directives do not.
2. **Given** the orphan rule set and its module docstring, **When** inspected, **Then** neither `governs` nor `supersedes` appears (they are not `Relation` enum members).

---

### User Story 5 - Every new relation is self-describing with doc parity (Priority: P3)

Anyone reading the code or the relation reference doc finds the same human-readable definition for each new DRG relation. The three new relations (`in_tension_with`, `reconciles_tension`, `rejects`) are defined once, identically, in both places, and a parity check prevents drift.

**Why this priority**: Single canonical authority — relation semantics must not drift between code and docs. Lower priority for runtime behaviour, but a binding quality bar for the new vocabulary. (See Assumption A2 — the enforcement comparator is a deliverable of this mission, not pre-existing.)

**Independent Test**: Each new `Relation` member has a description in the canonical relation-description registry; `docs/architecture/doctrine-relationships.md` holds matching text; a parity test fails (red-first) when one description is mutated and passes when they match.

**Acceptance Scenarios**:

1. **Given** the three new relations, **When** the registry and the relation doc are compared by the parity check, **Then** each relation's description matches and the check passes.
2. **Given** the parity check, **When** one relation's description is deliberately mutated in code only, **Then** the check fails with a drift finding naming that relation.

### Edge Cases

- **Symmetric authoring drift**: a tension authored in both directions with divergent reasons — resolved by storing one canonical edge (lexicographically-smaller URN as source) queried both ways; the checker keys findings on the sorted URN pair so `(A,B)` and `(B,A)` dedupe to one finding.
- **Non-transitivity**: `A in_tension_with B` and `B in_tension_with C` must NOT synthesize `A in_tension_with C`; the checker inspects only declared pairs and computes no closure.
- **Half-reconciled pair**: a reconciler with only one of the two `reconciles_tension` edges does not resolve the pair.
- **N-way / reconciler-in-tension**: a reconciler is an ordinary artefact subject to the same tension rules; resolution is per declared pair — N mutually-in-tension artefacts require a `reconciles_tension` edge to each participating node, and a reconciler that is itself in tension is just another declared pair with its own reconciler (no special-casing, no regress).
- **`rejects` at an unmarked node**: a `rejects` edge whose target is not marked `tags: [anti-pattern]`/`[smell]` is a validation error.
- **Cascade must not manufacture conflict**: activating one side of a tension must not auto-activate the other; activating a reconciler must not drag in the pair (the three new relations are excluded from cascade — enforced by a regression test, since exclusion is by-omission from the `REFERENCE_RELATIONS` allowlist).
- **Partial migration**: a surface updated on the write side but not the read/checkup side (e.g. a `tags` key authored in a graph fragment but silently dropped at load because `DRGNode` has no `tags` field) — must be prevented; see the Change Surface Map.

## Doctrine Schema & Model Change Surface *(mandatory — read / write / checkup)*

The mission changes the doctrine **schema** and **code models**, and those changes MUST propagate consistently across three surfaces. A change that lands on one surface but not the others is a defect (this is the acceptance backbone for FR-014 / NFR-002).

**Schema changes** (`src/doctrine/schemas/`):
- Remove the `opposed_by` property and the `contradiction` definition from `directive.schema.yaml`, `tactic.schema.yaml`, `paradigm.schema.yaml` (all `additionalProperties: false` — see D1 for downstream impact).

**Code-model changes** (`src/doctrine/drg/models.py`):
- Add `IN_TENSION_WITH`, `RECONCILES_TENSION`, `REJECTS` to the `Relation` enum.
- Add a **canonical relation-description registry** (single `Relation → description` mapping — the one seam feeding both the enum surface and the doc-parity check; a bare `StrEnum` member cannot carry a description). Scope for this mission: the three new relations (Assumption A2).
- Add a new first-class `NodeKind` value (`anti_pattern`/`smell`) for `rejects` targets (D2 resolved), and wire it through `ArtifactKind`, `_SINGULAR_TO_PLURAL`, `_SINGULAR_TO_PER_KIND_FIELD`, the activation filter (`_node_is_activated`), the cascade `_kind_of`, and the schemas. Also add a `tags: list[str]` field to the **`DRGNode`** model (Pydantic v2 defaults to `extra='ignore'`, so an un-modelled key is silently dropped on load) so any marker round-trips; validation of `rejects` targets lives in `drg/validator.py`. The anti-pattern marker's home is `DRGNode`/`NodeKind`/`validator.py` — **not** a per-artifact "node schema" (none exists).
- Remove the `opposed_by` field from `directives/models.py`, `tactics/models.py`, `paradigms/models.py`, and the now-dead `Contradiction` model + its `__all__` entry from `shared/models.py`.

**Propagation across surfaces** (each verified independently):

| Surface | What must change | Verification |
|---------|------------------|--------------|
| **Write** (authoring / emission) | Extractor stops minting `replaces` from `opposed_by` (blocks at `extractor.py:373-391, 484-499`); built-in YAML drops `opposed_by`; graph fragments **hand-author** `in_tension_with` / `reconciles_tension` / `rejects` edges + `tags`-marked nodes (the extractor can no longer generate them). The DRGNode graph-writer must emit `tags`. | No field-authored relationships remain (`test_relationship_migration.py`); `opposed_by` absent from all YAML; extractor `opposed_by` blocks removed; `test_directive_opposed_by_produces_replaces` (`test_extractor.py:183`) removed/repointed. |
| **Read** (query / load / render) | DRG queries treat `in_tension_with` symmetrically (union of `edges_from`/`edges_to` off one canonical edge — both helpers exist, verified); `DRGNode.tags` loads; anti-pattern nodes are re-kinded/tagged atomically with the edge rewrite; agent context can render "these compete; here is the reconciliation". | Symmetric-query test returns the pair from either endpoint; read-side guard: no node is both `kind: paradigm`/`tactic` and anti-pattern-marked unless both landed together; `tags` survives round-trip. |
| **Checkup** (validation / lint / gates) | `charter consistency-check` gains the advisory `tension_unreconciled` finding — added to `ConsistencyReport` but **excluded** from the `coherent` boolean reduction, and its DRG load **fails closed** into `verification_errors` (not swallowed); `charter activate` warns; orphan lint drops the phantom `governs`/`supersedes` branches **and their module docstring**; the enum↔doc parity check is added; dead-symbol gate enforces `Contradiction` removal (symbol-scoped, not word-grep); the shipped-graph **freshness canary** (`test_shipped_graph_yaml_is_fresh`) must accept the hand-authored edges post extractor-retirement; a cascade-exclusion regression test asserts the three new relations stay out of `REFERENCE_RELATIONS`. | The scenarios in US1/US2/US4/US5; grep-zero for `opposed_by`; the three `opposed_by` tests in `test_directive_consistency.py:349/376/403` removed/repointed (not left vacuously green); the `valid/with-tactic-refs.yaml` fixture updated. |

## Assumptions & Scope Notes

- **A1 — the advisory tension check is independent of cascade closure (defends the #2829 out-of-scope line).** `filter_graph_by_activation` (`src/charter/drg.py`) retains edges by endpoint survival off the *activation set*, relation-agnostic — not by cascade reachability. The flagship 024↔025 case is directive↔directive, both directly activated in the default pack, so the `in_tension_with` edge survives and the check fires without kind-complete cascade. #2829 would only add cross-kind tensions whose sides are reachable *only* via cascade; those cannot be co-active today, so no-finding is the correct result, not a bug.
- **A2 — glossary/doc parity scope and mechanism.** FR-012 is scoped to the **three new relations** for this mission (reconciled with NFR-004/SC-005; backfilling the existing 12 relations is a follow-up, explicitly not this mission). Descriptions live in a single canonical relation-description registry; the human-readable doc surface is `docs/architecture/doctrine-relationships.md` (kept in sync per DIRECTIVE_037). The enum↔doc **parity comparator does not exist today** — building it (with a red-first mutate-a-description test) is an explicit deliverable of this mission, which enlarges US5 beyond pure data entry.
- **A3 — symmetric query is supported.** `DRGGraph.edges_from`/`edges_to` exist (verified), so single-edge storage + both-direction query needs no new graph primitive.

## Resolved Decisions

All three squad-escalated decisions are resolved (recorded via the decision protocol).

- **D1 — downstream/org-pack `opposed_by` compatibility → ADD MIGRATION/DEPRECATION PATH.** Removing `opposed_by` from `additionalProperties: false` schemas would hard-break any downstream/org-pack YAML that authored it. This mission ships a consumer migration (rewrite `opposed_by` → edges) and/or a clear upgrade-time diagnostic + deprecation window, following the `backfill-identity`/`doctor` precedent. See **FR-015**.
- **D2 — anti-pattern/smell node kind → NEW FIRST-CLASS `NodeKind`.** `rejects` targets become a new `NodeKind` (`anti_pattern`/`smell`), not `kind: paradigm`/`tactic` phantoms carrying a tag. This ripples through `ArtifactKind`, `_SINGULAR_TO_PLURAL`, the activation filter, and schemas — a deliberately larger blast radius chosen for semantic honesty (an anti-pattern is not an active paradigm). See **FR-004** + Change Surface Map.
- **D3 — tension check under implicit all-active → ALWAYS ON.** The tension check runs regardless of explicit activation (no short-circuit special-case; simplifies the logic). **Consequence (operator-directed):** the new curated default charter — tracked work that will NOT enable all doctrine elements — becomes a **P0 release-blocker** for this mission's release, because always-on tension checking requires a default charter that does not co-activate unreconciled tensions. See **FR-009** + **C-008**.

## Requirements *(mandatory)*

### Functional Requirements

| ID | Title | User Story | Priority | Status |
|----|-------|------------|----------|--------|
| FR-001 | `in_tension_with` relation | As a doctrine author, I want a symmetric, non-transitive `in_tension_with` relation stored as one canonical edge (lex-smaller URN as source) so competing co-valid artefacts are queryable structure. | High | Open |
| FR-002 | `reconciles_tension` relation | As an operator, I want a `reconciles_tension` relation so an active reconciliation artefact bridging BOTH sides of a tension resolves it (one edge alone does not). | High | Open |
| FR-003 | `rejects` relation | As a doctrine author, I want a directional `rejects` relation to express rejection of a named anti-pattern (distinct from tension and from supersession). | High | Open |
| FR-004 | Anti-pattern/smell node kind | As a maintainer, I want `rejects` targets to be a new first-class `NodeKind` (`anti_pattern`/`smell`) (D2 resolved), wired through `ArtifactKind`/`_SINGULAR_TO_PLURAL`/activation-filter/schemas, so an anti-pattern is never mistaken for an active paradigm and every `rejects` edge terminates at a validatable node of the correct kind. | High | Open |
| FR-005 | Remove `opposed_by` + `Contradiction` | As a maintainer, I want `opposed_by` (field, schema property, `contradiction` definition) and the `Contradiction` model + `__all__` entry removed everywhere so there is a single edge-based representation. | High | Open |
| FR-006 | Migrate genuine tensions | As a maintainer, I want 024↔025 and change-apply-smallest-viable-diff↔025 migrated to single `in_tension_with` edges, replacing the mis-minted `replaces` cycle; the recovered tactic↔directive tension must be authored AND surface in the checker (see US-invariant INV-005). | High | Open |
| FR-007 | Migrate anti-pattern rejections | As a maintainer, I want the paradigm `opposed_by` anti-pattern usages migrated to exactly **8 `rejects` edges** terminating at **6 marked target nodes** (`anemic-domain-model`, `big-ball-of-mud`, `big-upfront-design`, `code-is-the-documentation`, `database-driven-design`, `single-diagram-architecture`); the target nodes are re-kinded/tagged atomically with the edge rewrite (no half-migrated `kind: paradigm` + anti-pattern node). | Medium | Open |
| FR-008 | Remove phantom orphan-lint branches | As a pack author, I want the `governs` (directive) and `supersedes` (adr) orphan-lint branches AND the module docstring references removed, so `orphaned_directive` flags exactly `{DIRECTIVE_035, DIRECTIVE_039}` — genuine orphans still surface (closes #2737). Deleting the directive branch outright (yielding 0 findings) is NOT acceptable. | High | Open |
| FR-009 | Advisory `tension_unreconciled` finding (always on) | As an operator, I want `charter consistency-check` to emit an advisory finding for co-activated unreconciled tension over the activation-filtered graph, running **regardless of explicit activation** (D3: always on — the no-explicit-activation short-circuit does not skip the tension check); the finding is added to `ConsistencyReport` but excluded from the `coherent` boolean; the DRG load fails closed. | High | Open |
| FR-010 | Activate-time tension warning | As an operator, I want `charter activate` to surface the tension as a warning alongside existing warnings. | Medium | Open |
| FR-011 | Built-in reconciliation artefact | As an operator, I want a shipped built-in reconciliation directive `reconcile-change-scope-tensions` with `reconciles_tension` edges to 024, 025, and smallest-viable-diff, so the default pack is coherent out of the box. (Load-bearing subject to D3.) | High | Open |
| FR-012 | Relation self-description + doc parity | As a reader, I want each of the three new `Relation` members to carry a description in the canonical registry, matched verbatim in `docs/architecture/doctrine-relationships.md`, with a parity check enforcing it (Assumption A2). | Medium | Open |
| FR-013 | Cascade exclusion (regression-tested) | As a system, I want `in_tension_with`/`reconciles_tension`/`rejects` excluded from cascade `REFERENCE_RELATIONS`, guarded by a regression test (exclusion is by-omission, so the test is the deliverable). | High | Open |
| FR-014 | Consistent surface propagation | As a maintainer, I want schema/model changes to propagate across write, read, and checkup surfaces; the Change Surface Map's per-surface Verification column is the binding checklist. | High | Open |
| FR-015 | Downstream `opposed_by` migration | As a consumer/org-pack author, I want removing `opposed_by` from the (`additionalProperties: false`) schemas to NOT silently break my pack: ship a migration that rewrites authored `opposed_by` → `in_tension_with`/`rejects` edges and/or a clear upgrade-time diagnostic + deprecation window (D1 resolved), modelled on the `backfill-identity`/`doctor` precedent. | High | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | Advisory, never hard-block, but MUST fire | The tension check MUST NOT flip `coherent` to false; AND an unreconciled active tension pair MUST produce exactly one finding (a no-op checker returning `[]` fails this) — cross-ref US1 sc1 / US2 sc2. Default pack `consistency-check` returns `coherent=true` with 0 unreconciled findings. | Reliability | High | Open |
| NFR-002 | Migration completeness | `grep -rn "opposed_by"` over `src/`, `docs/`, and `tests/` returns 0; the `doctrine.shared.models.Contradiction` symbol + `__all__` entry are removed (dead-symbol gate scoped to that symbol, not the word "Contradiction" which occurs unrelated elsewhere); `test_relationship_migration.py` "no field-authored relationships" invariant holds. | Correctness | High | Open |
| NFR-003 | Orphan set is exact, not just bounded | After the fix, `orphaned_directive` findings equal exactly `{DIRECTIVE_035, DIRECTIVE_039}` (count == 2) with 0 false positives on referenced directives — NOT merely `≤ 2` (which 0 would satisfy by deleting the rule). | Correctness | High | Open |
| NFR-004 | Doc parity enforced | Each new relation's registry description equals its `doctrine-relationships.md` definition; the parity check reports 0 drift and fails red when a description is mutated. Scope: the three new relations. | Maintainability | Medium | Open |
| NFR-005 | Quality gates | New/changed code passes `ruff` and `mypy` with zero issues; every new branch/helper has focused tests in the same PR. | Maintainability | High | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | `replaces` stays canonical | `replaces` and the pack-augmentation family (`enhances`/`overrides`/`specializes_from`) are canonical (multi-tier pack composition, not self-hosted in SK). Do NOT remove them; only `opposed_by`-derived `replaces` edges are touched. Post-migration built-in `replaces` set is empty (US3 sc3). | Technical | High | Open |
| C-002 | Symmetric single-edge storage + dedup | `in_tension_with` is stored as ONE canonical edge (lex-smaller URN as source), queried both directions; no transitive closure. The checker keys findings on the sorted URN pair so opposite-direction authorings dedupe to one finding. | Technical | High | Open |
| C-003 | Cascade contract preserved | The three new relations are excluded from cascade `REFERENCE_RELATIONS`; the cascade engine keeps its pure-reachability, no-per-kind-logic contract. Guarded by regression test (FR-013). | Technical | High | Open |
| C-004 | Out-of-scope items | Cascade-all-kinds (#2829) and `delegates_to` runtime swarm (#2827) are out of scope (see A1 for why the tension check is nonetheless coherent without #2829). | Business | High | Open |
| C-005 | Edge-authored, not field-derived | Relationships are authored as DRG edges, consistent with extractor retirement (ADR 2026-07-18-1); no new field-form relationship is introduced. Hand-authored edges must survive the shipped-graph freshness canary. | Technical | High | Open |
| C-006 | Green-at-every-boundary migration order | The destructive/additive migration MUST be sequenced (or made WP-atomic) so no gate boundary is red: (1) enum members + descriptions + `DRGNode.tags`; (2) author edges + marked nodes in graph fragments; (3) drop `opposed_by` from YAML AND the extractor blocks together; (4) drop the schema property; (5) drop the field + `Contradiction` model + imports together; (6) checks/lint/docstring + parity; (7) dead-symbol gate. Authoring an edge before its enum member (Pydantic) or dropping the schema property before the YAML are the specific red states to avoid. | Technical | High | Open |
| C-007 | Bulk-edit classification | Removing `opposed_by`/`Contradiction` across ~15 sites is a bulk edit (DIRECTIVE_035). The mission runs under `change_mode: bulk_edit` with an occurrence map produced at plan, unless the operator records pure-removal as exempt. | Process | Medium | Open |
| C-008 | New default charter is a P0 release-gate | Because the tension check is always-on (D3), this mission's release MUST NOT ship before the new curated default charter (tracked separately; will NOT enable all doctrine elements) lands — otherwise always-on checking against an all-active default could surface unreconciled tensions. The default pack stays coherent in the interim only via the FR-011 reconciliation artefact; the curated default charter is the durable fix and is a **P0 release-blocker** for this mission. | Business | High | Open |

### Key Entities

- **Relation**: the DRG edge vocabulary; gains `in_tension_with`, `reconciles_tension`, `rejects`, each self-describing via the relation-description registry.
- **`in_tension_with` edge**: symmetric, non-transitive link between two co-valid, co-activatable artefacts (one canonical stored edge).
- **`reconciles_tension` edge**: link from an active reconciliation artefact to each side of a tension pair.
- **`rejects` edge**: directional link from a good artefact to a marked anti-pattern/smell node.
- **Anti-pattern/smell node**: a new first-class `NodeKind` (`anti_pattern`/`smell`) for `rejects` targets (D2), wired through `ArtifactKind`/activation-filter/schemas; `DRGNode.tags` remains available for finer marking.
- **Reconciliation artefact**: built-in directive `reconcile-change-scope-tensions`, whose body carries the guidance for weighing the tension pairs.
- **`tension_unreconciled` finding**: the advisory consistency-check/activate output for a co-activated, unreconciled tension pair.

## Correctness Invariants (acceptance)

Promoted from edge cases so a failing test is derivable from each (ADR Confirmation (i)-(v)):

- **INV-001 (symmetric read)**: **Given** a single stored `A --in_tension_with--> B`, **When** queried from either `A` or `B`, **Then** the pair is returned from both endpoints.
- **INV-002 (non-transitivity)**: **Given** `A⋈B` and `B⋈C` declared, **When** the checker runs, **Then** no `A⋈C` pair is synthesized or flagged.
- **INV-003 (cascade exclusion)**: **Given** an artefact `A` in tension with `B`, **When** `A` is activated, **Then** `B` is not auto-activated; and activating reconciler `R` does not activate `A` or `B`.
- **INV-004 (unmarked reject target)**: **Given** a `rejects` edge whose target lacks the anti-pattern/smell tag, **When** the graph is validated, **Then** a validation error is raised.
- **INV-005 (recovered tactic tension)**: **Given** the migration, **When** the graph is loaded, **Then** the `change-apply-smallest-viable-diff ↔ DIRECTIVE_025` `in_tension_with` edge exists and flags when both are co-active.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: An operator co-activating two in-tension artefacts sees, in both `charter activate` and `charter consistency-check`, a finding naming both artefacts and asserting BOTH resolution-path strings are present (a finding mentioning only one path fails).
- **SC-002**: With the always-on check (D3), the built-in default pack reports `coherent = true` with 0 unreconciled-tension findings out of the box, AND removing the reconciliation directive `reconcile-change-scope-tensions` makes the 024/025 (and smallest-diff/025) findings appear — proving the artefact is what clears them (a live assertion, not vacuous). Durable coherence depends on the curated default charter (C-008).
- **SC-003**: `charter lint` `orphaned_directive` findings equal exactly `{DIRECTIVE_035, DIRECTIVE_039}` (count == 2), with 0 false positives — #2737 closed.
- **SC-004**: `opposed_by` no longer exists anywhere in `src/`, `docs/`, or `tests/`; the mis-encoded 024↔025 `replaces` cycle is gone; the built-in `replaces` edge set is empty and no non-`opposed_by` `replaces` semantics changed.
- **SC-005**: Each of the three new DRG relations has a human-readable definition discoverable identically in the relation-description registry and `docs/architecture/doctrine-relationships.md`, with a parity check that goes red on drift.
