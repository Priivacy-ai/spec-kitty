# Mission Specification: Governance at the deciding gate

**Mission Branch**: `research/3685-3682-enforcement-and-review-evidence`
**Created**: 2026-08-29
**Status**: Draft — v2, post-adversarial-squad (architect / reviewer / charter-doctrine lenses folded)
**Input**: Issues **#3685** (doctrine enforcement/activation delivery) + **#3682** (review-evidence gaps at the gates). One mission, landed together.

## Context (why this mission exists)

Literal-reader models have started stalling mid-mission to demand human approval and build "prove every step was signed off" scaffolding. The prose did not change — the *delivery* did. Two halves of one defect:

- **Policy half (#3685):** `DIRECTIVE_003` (decision-documentation, `enforcement: required`) is delivered into the **`implement`** action bundle (scope edge authored at `packs/built-in/missions/software-dev/actions/implement/index.yaml:4` → `action.graph.yaml:305-309`). A weak model receiving "author a durable decision artifact, alternatives, rationale, traceable" as **required during implementation** stalls. Compounding it, the delivery resolver `resolve_context` (`src/charter/offering/drg/query.py:110-160`) is **enforcement-flat and tension-blind** — `Enforcement` has no ordering primitive anywhere in the tree, and the resolver never walks `in_tension_with`/`reconciles_tension`, so no arbiter can be surfaced to break a conflict.
- **Realization half (#3682):** the place decision-documentation *should* live — the deciding gates — does not capture it. On current `main` (partly landed via #3235): the `in_review → approved` event supplies `policy_metadata: None` (`tasks_move_task.py:2189`); the review-cycle writer is symmetric but its approve caller guards to rejection-flips only (`tasks_verdict_persistence.py:852`), so first-pass approvals write no `review-cycle-N.md`; and `accept` recomputes but never **populates** `acceptance-matrix.json` from evidence.

**The fix is one outcome: move the decision-documentation obligation off `implement` to the deciding gates, and make those gates actually capture it.** Landing both halves together closes the window an implement-side removal alone would open (an architecture-altering decision made mid-implement with capture neither at implement nor yet at the gate).

**Non-goal:** no directive/tactic *prose* is rewritten; changes are at enforcement ordering, the action-scope binding, the delivery resolver, and the gate-side evidence pipeline. **Terminology:** this spec avoids the CI-banned term "cere"+"mony" (`tests/architectural/test_no_legacy_terminology.py:30`); it says **decision-documentation** / **evidence-capture**.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Decision-documentation leaves the implement bundle (Priority: P1)  [symptom fix, #3685]

The `DIRECTIVE_003` scope binding is **removed from the `implement` action** and **added to `review`**, so an agent running `implement` no longer receives a `required` "author a durable decision artifact" obligation; the obligation is delivered where the decision is *reviewed*.

**Why this priority**: this is the actual stall fix (verified: the lattice work in US3 does **not** touch 003 — 003 is not a `reconciles_tension` target of anything). Smallest blast radius, ships first.

**Independent Test**: `spec-kitty charter context --action implement --json` no longer lists `DIRECTIVE_003`; `--action review --json` now lists it. `spec-kitty doctrine regenerate-graph --check` is green (the edit is at the source index, survives regeneration).

**Acceptance Scenarios**:
1. **Given** `charter context --action implement`, **When** the bundle is assembled, **Then** `DIRECTIVE_003` is absent.
2. **Given** `charter context --action review`, **When** assembled, **Then** `DIRECTIVE_003` is present.
3. **Given** a fresh `doctrine regenerate-graph`, **When** the graph regenerates from `actions/implement/index.yaml` (003 line deleted) and `actions/review/index.yaml` (003 line added), **Then** the `implement→003` scope edge does not reappear, the `review→003` edge is present, and `--check`, the orphan lint, and the delivery-reachability ledger stay green.
4. **Given** the removal, **When** reachability is checked, **Then** `DIRECTIVE_003` remains reachable from its retained authoring actions (`plan`, `specify`, `tasks`, `retrospect`) — it does not orphan.

---

### User Story 2 — The deciding gates capture the decision evidence (Priority: P1)  [#3682]

At `move-task --to approved` the approval event carries the reviewer's `policy_metadata` and a `review_ref`; a first-pass approval auto-authors a `review-cycle-N.md`; and `spec-kitty accept` populates and validates `acceptance-matrix.json` from recorded evidence (or fails loudly on a `pending` matrix).

**Why this priority**: this is the other half of the same outcome — the obligation US1 moves off implement must be *met* at the gate, or US1 ships a governance regression. Auto-authored from the decision the reviewer already made (never a hand-filled form — that would re-create the friction #3685 warns about).

**Independent Test**: approve a WP first-pass; assert (a) the `approved` event carries non-null `policy_metadata` (tool/profile/model/shell-pid) and a `review_ref`; (b) `tasks/<WP>/review-cycle-1.md` exists with verdict `approved` and a `reproduction_command`; (c) after `spec-kitty accept`, `acceptance-matrix.json` has no `pending`/`TODO` rows, or accept blocked with a loud matrix error.

**Acceptance Scenarios**:
1. **Given** an `in_review → approved` move, **When** the event is emitted, **Then** `policy_metadata` and `review_ref` are populated (mirroring the claim/reject hops that already populate them).
2. **Given** a first-pass approval (no prior `changes_requested`), **When** it is recorded, **Then** an `approved` `review-cycle-N.md` is written via the existing symmetric writer.
3. **Given** `spec-kitty accept` on a mission whose matrix is a `pending` scaffold, **When** accept runs, **Then** the matrix is populated from recorded evidence OR accept fails/warns loudly (never silently passes).

*Reconciliation note (mandatory before implementation): #3682 is partly landed via #3235 — WP must first re-derive current-main state; the durable-open remainder is the APPROVED `policy_metadata` arm, the first-pass-approve guard relaxation, and matrix population.*

---

### User Story 3 — The enforcement lattice can't harbor a weaker arbiter, and required decision-documentation can't silently re-enter implement (Priority: P2)  [structural hygiene, #3685]

`Enforcement` gains an explicit rank order, and a structural gate asserts (a) no `reconciles_tension` directive→directive **source** is ranked below its targets, and (b) — the durable teeth — **no `required` decision-documentation directive is scoped onto `implement`**, so US1's win cannot silently regress.

**Why this priority**: hygiene + regression guard, not the acute fix (US1 is). Prevents a future `required` decision-documentation directive from re-introducing the stall class, and makes the "a tiebreaker is never weaker than what it arbitrates" invariant enforceable.

**Independent Test**: seed a fixture where a `reconciles_tension` directive source is `advisory` over a `required` target → gate (a) fails naming the edge. Add a fixture scoping a `required` decision-documentation directive onto `implement` → gate (b) fails. The shipped corpus passes both after FR-003.

**Acceptance Scenarios**:
1. **Given** `reconciles_tension: R→X` (both directives) with `rank(R) < rank(X)`, **When** the gate runs, **Then** it fails naming `R`, `X`, and both levels.
2. **Given** the shipped corpus, **When** the gate runs, **Then** it passes only after `reconcile-change-scope-tensions` is raised to `lenient-adherence` (= `max` of its directive operands 024/025).
3. **Given** a `reconciles_tension` edge whose target is a **tactic** (no enforcement field, e.g. `change-apply-smallest-viable-diff`), **When** the gate runs, **Then** that edge is **skipped** (documented rule), not treated as a violation.
4. **Given** a future directive with `enforcement: required` tagged decision-documentation scoped onto `implement`, **When** the class-level gate runs, **Then** it fails.

---

### User Story 4 — Delivery surfaces the tension arbiter as an arbiter (Priority: P3)  [#3685]

`resolve_context` surfaces `reconciles_tension`/`in_tension_with` so a delivered bundle carries, for any co-delivered tension pair, its reconciler annotated as the arbiter, and flags a co-delivered declared tension that has no reachable reconciler.

**Why this priority**: hardens the general case; US1+US2 already remove the acute stall. Lowest priority.

**Independent Test**: assemble a bundle whose scope pulls in `024`+`025`; assert the bundle's new `tension_arbiters` field maps `reconcile-change-scope-tensions → (024, 025)`; a declared tension pair with no reachable reconciler appears in `unarbitrated_tensions`.

**Acceptance Scenarios**:
1. **Given** a bundle containing a declared `in_tension_with` pair, **When** delivered, **Then** the pair's reconciler is present with an `arbitrates` annotation.
2. **Given** a co-delivered declared tension with no reachable reconciler, **When** delivered, **Then** it appears in the bundle's `unarbitrated_tensions`.

---

### Edge Cases

- **`DIRECTIVE_003` is scoped to ~15 actions, not two** (software-dev `specify/plan/tasks/implement/retrospect`, plus `research/*` and `documentation/*`). US1 removes **only** the `implement` binding and adds `review`; `plan`/`specify`/`tasks`/`retrospect` are **intentionally retained** (legitimate authoring/decision points). A plan must not strip them by analogy.
- **`review` currently has no `003` scope edge in its index** but the generated graph shows `review→003` (`action.graph.yaml:481-483`) — investigate the mint path before editing; US1's "add to review" must reconcile with whatever already produces that edge (stale graph vs a second mint path).
- **No `accept`/`post-merge` *action* nodes exist** — "at accept" is realized by the runtime `accept` command + `gates_core.py` (US2), **not** a DRG action scope; the spec must not assert `charter context --action accept`.
- **`lenient-adherence` promotion trips `validate_lenient_adherence`** (`directives/models.py:82-91`, requires non-empty `explicit_allowances`) — FR-003 must add `explicit_allowances` to the reconciler as an explicit data change, or the promoted directive fails to load.
- **Enforcement labels sort lexically to the desired order by coincidence** (`advisory < lenient-adherence < required`) — the rank must be explicit, not inherited from `StrEnum`.
- **US2 matrix on a topology whose coord surface can't resolve** — the current `cannot_evaluate` skip and `--allow-fail` escape must be addressed so the matrix can't silently pass.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: `Enforcement`/`EnforcementLevel` (`src/charter/offering/directives/models.py:22-27`) exposes an **explicit rank-based total order** (rank map + overridden `__lt__`/comparators — NOT relying on `StrEnum`'s inherited lexical compare), as the single ranking authority. A test asserts the order is rank-driven (rename-proof), not lexical.
- **FR-002**: A structural gate in `src/charter/consistency_check.py` (reusing the existing `_tension_reconciled_urns` traversal, not a second walk) asserts: for every `reconciles_tension` edge `R→X` where **both endpoints are directives**, `rank(enforcement(R)) ≥ rank(enforcement(X))`; edges whose target is a non-directive (tactic) are **skipped** by a documented rule. Non-vacuous (seeded-violation fixture fails).
- **FR-003**: `reconcile-change-scope-tensions` is raised to `lenient-adherence` (= max of directive operands 024/025), **bounded** — a reconciler is never promoted to `required` (a new constraint) — and gains the `explicit_allowances` its new level requires to pass `validate_lenient_adherence`.
- **FR-004**: A **class-level** gate (same home as FR-002) asserts no `enforcement: required` directive tagged/identified as decision-documentation is scoped onto the `implement` action.
- **FR-005**: The `DIRECTIVE_003` scope edge is removed from `packs/built-in/missions/software-dev/actions/implement/index.yaml` and added to `.../actions/review/index.yaml`; `plan`/`specify`/`tasks`/`retrospect` bindings are retained. `doctrine regenerate-graph --check`, orphan lint, and reachability ledger stay green.
- **FR-006**: `move-task --to approved` populates the approval event's `policy_metadata` (an APPROVED arm in `_mt_hop_policy_metadata`, `tasks_move_task.py`) and a `review_ref`.
- **FR-007**: A first-pass approval auto-authors an `approved` `review-cycle-N.md` — by relaxing the `!= "changes_requested"` guard in `_persist_approved_review_cycle` (`tasks_verdict_persistence.py:852`) to use the already-symmetric `create_rejected_review_cycle(..., verdict="approved")` writer; the artifact carries at least a `reproduction_command`.
- **FR-008**: `spec-kitty accept` populates `acceptance-matrix.json` criterion rows from recorded evidence (status events + review-cycle artifacts) before recomputing `overall_verdict`, or blocks loudly on a `pending` matrix — closing the `cannot_evaluate` skip / `--allow-fail` silent-pass for the matrix.
- **FR-009**: `resolve_context` surfaces `reconciles_tension`/`in_tension_with` into new additive carrier fields on `ResolvedContext` and `_ActionDoctrineBundle` (`tension_arbiters: Mapping[str, tuple[str,...]]`, `unarbitrated_tensions: list[tuple[str,str]]`), reusing the existing progressive-disclosure traversal rather than adding a second graph walk.

### Non-Functional Requirements

- **NFR-001**: No directive/tactic *prose* is rewritten (the enforcement-value + `explicit_allowances` data change on the reconciler is the only YAML edit to a directive; all else is enforcement-ordering, scope-binding, resolver, and gate-side code).
- **NFR-002**: `doctrine regenerate-graph --check` is deterministic from source after the index edits; orphan lint + reachability ledger green; no directive becomes newly unreachable (003 stays reachable via its retained actions — FR-005 verifies, not assumes).
- **NFR-003**: Delivery latency unchanged in the common (no-tension-in-scope) case; FR-009 adds bounded work only when tension edges are present.
- **NFR-004**: The enforcement ranking is a single source of truth (no second rank map); FR-009's carrier fields are additive (no versioned-contract bump — `_ActionDoctrineBundle` is designed for defaulted additive extension).
- **NFR-005**: US2 evidence is **auto-derived from the decision already made**, never a new hand-filled artifact.

### Constraints

- **C-001**: The 024/025/smallest-viable-diff tension is not resolved by deleting an operand (all three are independently valid, co-activatable); the remedy is bounded arbiter promotion (FR-003).
- **C-002**: Action-scope edges are generated from the action `index.yaml` files by the extractor (a generic index walker); edits go to `.../actions/<action>/index.yaml`, never the generated `.graph.yaml` and never `extractor.py`.
- **C-003**: The FR-002 gate lives in `consistency_check.py` (has `ProjectContext`→`DoctrineService`), not the pure-graph `drg/validator.py` (layer boundary).
- **C-004**: US1 (implement-side removal) and US2 (gate-side capture) **land in the same mission/merge** — US1 must not merge ahead of US2 (closes the no-capture window).
- **C-005**: Preserve the one opaque-label enforcement consumer (`pack_validator.py:1376`); the order is additive.
- **C-006**: Canonical command name is `spec-kitty doctrine regenerate-graph` (not `regen-graph`).

### Key Entities

- **Enforcement level** — `required | lenient-adherence | advisory` + explicit rank.
- **Directive** — `enforcement`, `explicit_allowances`, action `scope`; `DIRECTIVE_003` is the load-bearing instance.
- **Action index** — `.../actions/<action>/index.yaml`, the scope source of truth.
- **DRG edges** — `reconciles_tension`, `in_tension_with` (directive/tactic endpoints), `scope`.
- **`ResolvedContext` / `_ActionDoctrineBundle`** — delivery payload; gains additive tension-annotation fields.
- **Approval event / review-cycle / acceptance-matrix** — the gate-side evidence carriers.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: `charter context --action implement --json` delivers **zero** `required` decision-documentation directives (003 absent); `--action review --json` delivers `DIRECTIVE_003`. Before/after asserted.
- **SC-002**: A scripted **order-by-enforcement resolver** over the post-US1 `implement` bundle (bundle `directive_ids` × delivered enforcement via `DoctrineService`) confirms no `required` decision-documentation directive is delivered to implement — a deterministic CI guard (replaces the un-runnable "literal-reader" smoke).
- **SC-003**: After `doctrine regenerate-graph`, `implement→003` is absent, `review→003` present, `--check`/orphan-lint/reachability-ledger green; 003 reachable from ≥1 retained action.
- **SC-004**: FR-002 gate fails a seeded advisory-reconciler-over-lenient-operand fixture and a tactic-target fixture is skipped; FR-004 gate fails a seeded required-decision-doc-on-implement fixture; the shipped corpus passes both.
- **SC-005**: Enforcement change is exactly `reconcile-change-scope-tensions` `advisory → lenient-adherence` (histogram `25/6/3 → 25/7/2`); **no directive is newly promoted to `required`**. Before/after over the shipped corpus.
- **SC-006**: A first-pass-approved WP produces an `approved` `review-cycle-1.md` with a `reproduction_command`, and its `approved` status event carries non-null `policy_metadata` + `review_ref`.
- **SC-007**: After `spec-kitty accept` on a scaffolded-matrix mission, the matrix has zero `pending`/`TODO` rows OR accept blocked with an explicit matrix error; a repo scan shows no *new* accepted-mission-with-pending-matrix is producible.
- **SC-008**: A delivered bundle with a co-delivered `in_tension_with` pair carries its reconciler in `tension_arbiters`; a reconciler-less declared pair appears in `unarbitrated_tensions`.
- **SC-009**: FR-001 comparison is rank-driven, proven by a test that would break if a level were renamed out of lexical order.
