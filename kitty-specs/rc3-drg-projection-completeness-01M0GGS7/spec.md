# Mission Specification: M2 — DRG projection completeness

**Mission Branch**: `drg-projection-completeness`
**Created**: 2026-08-20
**Status**: Draft (specify-phase LIGHT spec — operator decisions folded; NOT finalized/tasks)
**Author**: analyst-annie
**Batch**: 1 of 8 friction-bug specs feeding a single-branch pre-rc2 PR; run later.
**Issues**: #3605, #3604, #3488 (all in scope); adjacent #3061 (follow-on); new `_DRG_NODE_KINDS` drift fold.

---

## Problem & impact (BLUF)

Doctrine reaches an agent through two seams: the **emit seam** (the DRG extractor projects authored doctrine YAML into the committed `packs/built-in/*.graph.yaml` fragments the charter cascade traverses) and the **delivery seam** (the profile context renderers turn resolved graph reach into agent-visible text). Both have completeness gaps where authored governance validates, loads, and then is silently lost:

1. **#3605 (emit) — procedure reference rationale dropped.** The `# --- Procedures ---` loop in `src/doctrine/drg/migration/extractor.py` (~lines 878-905) mints `DRGEdge`s with no `when`/`reason`, unlike the directive/tactic/paradigm branches which route through `_reference_edge_kwargs(ref)` (extractor.py:542). Shipped procedures **do** author `reason:`, so that rationale never reaches the DRG.

2. **#3604 (emit) — type-wide governance never projected.** `extract_action_edges` only reads action-grain `actions/*/index.yaml`, emitting `action --scope--> gov`. It never reads `governance-profile.yaml`, so a mission type's **type-wide** governance (`selected_directives`/`selected_tactics`/`selected_paradigms`/styleguide) is absent from the DRG for **all four** built-in types. It surfaces most visibly as `mission_type:plan` cascading to empty (plan authors *only* type-wide governance; its action grains are intentionally empty per FR-004/FR-013).

3. **#3488 (delivery) — profile selector channels.** Filed against `3.2.6rc1`, this reported that 3 of 5 profile reference channels deliver no body and a procedure step `description` is unreachable. **Verification against current main shows the three rc1 gaps have substantially moved** (see design decisions): `operating-procedures` is now data-driven into the DRG (`_emit_operating_procedure_edges`, extractor.py:1024) with a fail-closed doctor check; step `description` now renders (WP01/FR-004); styleguide/toolguide pointer-only is now a *documented deliberate* choice (`_STYLEGUIDE_TOOLGUIDE_POINTER_ONLY_REASON`). The operator folded #3488 into M2 so the emit and delivery seams are closed **together and cannot silently re-diverge** — the durable deliverable is a structural invariant binding the two seams, on top of verifying and closing any residual.

**Impact:** authored governance (procedure rationale; a mission type's type-wide selections; a profile's cited channels) reaches the agent, or is flagged, rather than being silently dropped. This mission closes both emit gaps, verifies-and-closes the delivery residual, binds the two seams, and re-ledgers the golden graph **once** via a dedicated post-merge step.

**Code-inspection correction (carried):** #3604's governance-profile projection is a differently-shaped pass — it does **not** reuse `_reference_edge_kwargs` (its targets are bare ids, not `{type,id,when?,reason?}` reference dicts). #3605 and #3604 are two distinct emit seams that share only the golden re-ledger.

---

## Scope

### In scope
- **#3605 (emit):** Route the procedure `references` branch through `_reference_edge_kwargs(ref)` so procedure edges carry authored `when`/`reason`. Optionally generalize the five `{type,id,when?,reason?}`-shaped reference branches (directive, tactic top-level, tactic step-level, paradigm, procedure) behind one emit helper and assert structurally that every such branch routes through it.
- **#3604 (emit):** New `extract_action_edges`-shaped pass that reads each mission type's `governance-profile.yaml` and emits `mission_type:<t> --scope--> <selected_* governance>` edges (relation `scope`, source `mission_type` — operator-decided), for all four built-in types.
- **#3488 (delivery):** Verify the delivery-side code path against current main; close any residual gap so every profile selector channel either delivers a body or carries an **attested, tested pointer-only contract** (styleguide/toolguide); confirm `operating-procedures` entries reach delivery via their DRG edges and that unresolved entries are flagged; keep the step-`description` rendering. Add the seam-binding structural test (FR-010).
- **Fold:** the one-line `_DRG_NODE_KINDS` drift fix at `src/charter/synthesizer/topic_resolver.py:37` (add `mission_type`, which #3604 now emits as an edge source).
- **One batched golden re-ledger, as a dedicated post-merge step:** after both extractor edits land, a distinct step/WP runs `spec-kitty doctrine regenerate-graph` **once** and commits the updated `packs/built-in/*.graph.yaml` fragments.
- Red-first regression coverage for every fix (see Acceptance Criteria).

### Out of scope
- **#3061** — four `action:plan/*` nodes resolve to zero artefacts at d=2 (P3/deferred). Kept follow-on; re-verify (may partially resolve) after the #3604 re-ledger — no scope commitment.
- Adding `reason` to non-directive reference **models**/generated schemas for end-to-end overlay-to-frontmatter promotion. The extractor carrying the field is necessary but not sufficient; the model work is separate.
- Re-implementing the #3488 rc1 fixes already shipped on main (canonical-source / campsite discipline: verify first, do not re-fix shipped code).
- New relations, new mission types, new CLI surfaces, org/project-pack authoring changes.

---

## Requirements

### Functional Requirements

| ID | Title | User Story | Priority | Status |
|----|-------|------------|----------|--------|
| FR-001 | Procedure edges carry rationale | As a pack author, I want my procedure `reference` `reason:`/`when:` to reach the DRG so authored rationale is not silently dropped. | High | Open |
| FR-002 | Single reference-edge authority | As a maintainer, I want every `{type,id,when?,reason?}`-shaped reference branch to route through one emit helper so no future branch drops a field. | Medium | Open |
| FR-003 | Project type-wide governance | As a pack author, I want each mission type's `governance-profile.yaml` selections projected as `mission_type --scope--> gov` so cascade reaches type-wide governance. | High | Open |
| FR-004 | Plan cascades to its governance | As an operator, I want `mission_type:plan` to cascade to its directive/tactics/paradigms/styleguide, not to empty. | High | Open |
| FR-005 | Uniform across all four types | As a maintainer, I want the governance-profile pass to fire for documentation, research, software-dev, and plan identically. | High | Open |
| FR-006 | `_DRG_NODE_KINDS` recognises `mission_type` | As a maintainer, I want the topic resolver's node-kind set to include `mission_type` so the new edge source resolves. | Medium | Open |
| FR-007 | Delivery-seam residual closed | As a pack author, I want every profile selector channel to deliver a body or carry an attested, tested pointer-only contract; `operating-procedures` entries deliver via their DRG edges and unresolved entries are flagged. | High | Open |
| FR-008 | Emit↔delivery bind (anti-divergence) | As a maintainer, I want a structural test tying projection to delivery so a channel projected into the DRG is either delivered or explicitly pointer-only — the two seams cannot silently re-diverge. | High | Open |
| FR-009 | Single post-merge re-ledger | As a maintainer, I want a dedicated post-merge step to run `regenerate-graph` once after both extractor edits land, so the golden graph churns a single time. | High | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | Deterministic regeneration | `spec-kitty doctrine regenerate-graph` is byte-deterministic: a no-source-change re-run yields zero diff (`--check` clean). | Reliability | High | Open |
| NFR-002 | #3605 edge-set stability | For #3605, procedure edge **triples** (source, target, relation) are unchanged; only `when`/`reason` metadata is added. | Correctness | High | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | Canonical regen only | Golden fragments MUST be regenerated only via `spec-kitty doctrine regenerate-graph`; never hand-edited (`hand_authored_overlay.py` warns edits are dropped). | Technical | High | Open |
| C-002 | Single re-ledger | The graph MUST move exactly once, via the dedicated post-merge step (both extractor edits staged before regen). | Technical | High | Open |
| C-003 | Decided relation/grain | #3604 emits relation `scope` from source node `mission_type` (operator-decided); both are `Relation`/`NodeKind` members — no new relation. | Technical | High | Open |
| C-004 | Verify before re-fixing #3488 | Implementers MUST verify the delivery-side path on current main before changing it; the rc1 gaps are substantially shipped — close residual only. | Technical | High | Open |

### Key Entities
- **DRG edge** — `{source, target, relation, when?, reason?}`; committed in `packs/built-in/<kind>.graph.yaml`.
- **`_reference_edge_kwargs(ref)`** — single authority for `when`/`reason` on `{type,id,when?,reason?}` branches (extractor.py:542).
- **`governance-profile.yaml`** — per-mission-type type-wide governance selections.
- **`mission_type:<t>` node** — already emitted by `extract_mission_type_edges`; #3604 adds `scope` governance edges from it.
- **Profile selector channels** — directive/tactic (body-delivering), styleguide/toolguide (pointer-only), `operating-procedures` (procedure delivery via DRG `requires` edges) in `src/charter/context_renderers/profile_sections.py`.

---

## Acceptance Criteria (Given / When / Then)

**AC-001 (FR-001) — procedure reason round-trips (red-first).** *Given* a procedure YAML authoring `reason:`/`when:` on a reference, *When* the extractor runs, *Then* the resulting `procedure --…--> target` edge carries that `reason`/`when`. Mirror `test_directive_reference_reason_roundtrips` / `test_tactic_reference_reason_roundtrips` (`tests/doctrine/drg/migration/test_extractor.py:266,313`) as `test_procedure_reference_reason_roundtrips` — RED before, GREEN after.

**AC-002 (FR-002, optional) — single helper enforced.** *Given* the extractor source, *When* the structural test runs, *Then* every `{type,id,when?,reason?}`-shaped branch (directive, tactic top+step, paradigm, procedure) routes through the one emit helper; none constructs `when`/`reason` inline.

**AC-003 (FR-004) — plan cascades to type-wide governance (red-first cascade coverage).** *Given* the regenerated DRG, *When* the charter cascade runs for `mission_type:plan`, *Then* it reaches `031-context-aware-design`, the 9 `selected_tactics`, the 3 `selected_paradigms`, and the `planning-and-tracking` styleguide. Red-first: add `mission_type:plan` to the governance-bearing set the cascade test asserts over — RED before the pass, GREEN after.

**AC-004 (FR-003, FR-005) — all four types project via `scope`.** *Given* the regenerated DRG, *When* each of documentation, research, software-dev, plan is inspected, *Then* each `mission_type:<t>` node has `scope` edges to every entry of its `governance-profile.yaml` `selected_*` lists.

**AC-005 (FR-006) — node-kind recognised.** *Given* `_DRG_NODE_KINDS`, *When* a `mission_type`-sourced edge is resolved, *Then* `"mission_type"` ∈ `_DRG_NODE_KINDS`.

**AC-006 (FR-007) — delivery residual closed.** *Given* a profile citing each selector channel, *When* the profile is rendered, *Then* directive/tactic deliver inline bodies (incl. step `description`), styleguide/toolguide render the attested pointer-only stanza, and `operating-procedures` entries deliver their procedure bodies via DRG reach; an `operating-procedures` entry with no procedure node is flagged (fail-closed doctor check), not silently dropped.

**AC-007 (FR-008) — emit↔delivery bind.** *Given* the set of profile selector channels, *When* the anti-divergence structural test runs, *Then* every channel projected into the DRG is either body-delivering or carries an explicit, attested pointer-only contract — a new channel added on one seam but not the other fails the test.

**AC-008 (FR-009, NFR-001, C-002) — single post-merge re-ledger.** *Given* both extractor edits landed, *When* the dedicated post-merge step runs `spec-kitty doctrine regenerate-graph` once, *Then* the committed `*.graph.yaml` fragments update in one commit and an immediate `regenerate-graph --check` is clean.

**AC-009 (NFR-002) — #3605 triples unchanged.** *Given* pre-/post-fix procedure edge sets, *When* compared by (source, target, relation), *Then* the triple set is identical; only metadata is added.

---

## Key design decisions

- **#3605 — reuse the single authority.** Replace the inline `DRGEdge(...)` in the procedures loop with `**_reference_edge_kwargs(ref)`, matching directive/tactic/paradigm. Optionally extract a shared emit helper so all five `{type,id,when?,reason?}` branches share one path plus the AC-002 structural assertion.
- **#3604 — new differently-shaped pass; `scope` from `mission_type` (operator-decided).** Add a function that walks `packs/built-in/missions/*/governance-profile.yaml` and emits `mission_type:<t> --scope--> <selected_* target>`. Relation `scope` matches action-grain governance semantics ("governance in scope for this surface") so cascade traversal already follows it (zero traversal churn); source `mission_type` matches where the governance is authored and keeps type/action grains disjoint (FR-004/FR-013). The `mission_type:<t>` node already exists; wire the pass into top-level extraction next to `extract_action_edges`.
- **#3488 — verify-and-close, then bind (operator folded).** Current-main verification: (1) `operating-procedures` is data-driven into the DRG via `_emit_operating_procedure_edges` (extractor.py:1024) and diagnosed by `_run_operating_procedures_check` (fail-closed) — the rc1 "consumed by no renderer" gap is substantially shipped; (2) step `description` now renders (WP01/FR-004 in `format_inline_named_body`); (3) styleguide/toolguide pointer-only is a documented deliberate choice (`_STYLEGUIDE_TOOLGUIDE_POINTER_ONLY_REASON`). M2 therefore closes only the **residual** (schema/doc surfacing of the pointer-only contract for a pack author; confirming the diagnostic covers dead `operating-procedures` entries) and adds the durable **FR-008 anti-divergence bind** so the emit and delivery seams cannot silently re-diverge again.
- **Fold `_DRG_NODE_KINDS` drift.** Add `"mission_type"` to the frozenset at `topic_resolver.py:37` — one line, load-bearing because #3604 emits `mission_type` as an edge source.
- **Re-ledger = dedicated post-merge step (operator-decided).** A distinct step/WP runs the single `regenerate-graph` after both extractor edits land and commits the fragments — not "whoever lands the 2nd edit". Preserves the single-churn constraint (C-002).

---

## OPEN QUESTIONS — RESOLVED (operator decisions folded)

- **(a) #3604 relation + source grain** → **relation `scope`, source `mission_type`** (as recommended). Encoded in FR-003, AC-004, C-003.
- **(b) Fold #3488?** → **FOLDED into M2.** Emit seam (#3605/#3604) and delivery seam (#3488) are fixed together with an anti-divergence bind (FR-007, FR-008, AC-006, AC-007). #3061 remains follow-on (re-verify after re-ledger).
- **(c) Re-ledger owner** → **dedicated post-merge step** (a distinct step/WP), not "whoever lands the 2nd edit"; single-churn preserved (FR-009, C-002, AC-008).

---

## Risks / blast-radius

- **Golden double-churn avoided only by the dedicated step.** Two independent extractor edits each move the golden graph; the single-churn guarantee now rests on the post-merge step running `regenerate-graph` once after both land. Sequencing gate: neither edit is "done" until that step runs.
- **Byte-identity of the shipped graph for #3605.** Must add only `when`/`reason` metadata to existing procedure edges — the edge **triple** set must be identical (NFR-002/AC-009). Pin with the triple-diff assertion; a relation/edge change is silent graph corruption.
- **Whole-graph regeneration is broad.** `regenerate-graph` rewrites all `packs/built-in/*.graph.yaml`; any ordering/formatting non-determinism surfaces here. Mitigation: NFR-001 `--check`-clean re-run right after commit.
- **Stale-issue re-fix risk on #3488.** The rc1 report is substantially shipped; an implementer taking it at face value could re-implement or revert shipped fixes. Mitigation: C-004 verify-first + the FR-008 bind (which pins the *invariant*, not the rc1 symptom).
- **`scope`/`mission_type` locked in golden output.** Relation and source grain are baked into committed fragments; changing them later is another re-ledger. Decided (C-003) before the re-ledger.
- **Cascade-count tests move.** AC-003/AC-004 shift documented cascade counts (plan currently 0; documentation 31 / research 23 / software-dev 160 grow). Count-pinned tests update in the same PR as red-first, not retro-fitted.

---

## Issues

- **#3605** — Extractor drops authored `when`/`reason` on procedure references. *In scope (emit).*
- **#3604** — Project mission-type type-wide governance (`governance-profile.yaml`) into the DRG. *In scope (emit); relation `scope`, source `mission_type`.*
- **#3488** — Profile reference channels / delivery seam. *In scope (delivery, folded); verify-and-close residual + anti-divergence bind.*
- **`_DRG_NODE_KINDS` drift** (`src/charter/synthesizer/topic_resolver.py:37`) — new; folded one-line fix (add `mission_type`).
- **#3061** — Four `action:plan/*` nodes resolve to zero artefacts at d=2 (P3/deferred). *Follow-on; re-verify after #3604 re-ledger.*
