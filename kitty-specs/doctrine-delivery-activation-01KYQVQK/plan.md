# Implementation Plan: Doctrine Delivery Activation Fast-Follow

**Branch**: `feat/doctrine-delivery-activation` | **Date**: 2026-07-29 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `kitty-specs/doctrine-delivery-activation-01KYQVQK/spec.md`

Grounding authority: [pre-planning-ledger.md](./pre-planning-ledger.md) (3 pre-planning scouts +
3-lens post-plan squad, file:line anchored). Decisions D1–D9 (pre-planning) and **D10–D19 (post-plan
squad remediation)** there are load-bearing for this plan; the IC map below already reflects D10–D19.

> **Post-plan corrections applied (D10–D19):** (1) delivery/reachability asserted on the **profile
> channel** (`profile_channel_reachable`), never `resolve_context` (the action channel — vacuous/red);
> (2) `when` surfaced by reusing `link_references(roots=profile_seeds, …)`, no re-walk; (3) **IC-06 split**
> into IC-06a (parallel registry/gate) + IC-06b (sequenced Protocol typing); (4) FR-007 templates deliver
> via IC-01's suggests-walk reaching the C4 tactic's references (schema-tier); (5) FR-008 anti-patterns use
> the existing **`REJECTS`** relation at validation tier (never delivered by design → no inert problem);
> (6) graph-count/histogram goldens owned by their **authoring** WP, IC-05 owns only reachability goldens;
> (7) forward-API retirement is **~2–3 wired symbols, not 9** (the rest stay allowlisted-with-note);
> (8) NFR-002 pins are **review-gated, not CI-gated**; (9) **baseline deferred set = 60, not 50**.

## Summary

Animate the inert #3063 doctrine delivery topology. The **core** extends the profile-channel
reachability walk (`src/doctrine/drg/reachability.py`, `PROFILE_CHANNEL_RELATIONS`) to follow
`suggests` edges and surface each edge's `when` clause as the delivered doctrine's applicability
condition — delivered as `when`-labelled links (not eager bodies), reusing the existing
requires-closure "fetch + when-doing" cadence. Because the node-level walk primitive drops the
edge, `when` is surfaced in the **consumer/charter layer** via the existing `edge_to_reference`
projection shape, not by mutating the doctrine walk to carry edges. Once the walk delivers, the
reachability pins (`_PROFILE_UNREACHABLE`=153, `_PROFILE_RESCUES`=2) and the wiring table (deferred
set = 50) are re-measured **via the canonical helper** and reconciled under the no-silent-golden-
movement gate, and each of the 9 forward-API symbols is retired from the dead-symbols allowlist as it
becomes `src`-consumed. Two companion deliverables complete the families (C4 templates via a
`template:instantiates` edge; refactoring anti-patterns via edges, grounded in attested tactic text),
and four trailing hygiene tickets are closed (#3075 writer-registry root fix + discovery gate; #3062
schema-error UX + asset source-path twin fix; #2532 context.py extraction slice; the non-hermetic
delivery fixture).

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: internal — `doctrine.drg` (reachability/query/models/migration), `charter`
(context, progressive_disclosure, pack_context, synthesizer), `specify_cli.doctrine`
(pack_validator/pack_assembler), `specify_cli.drg_writers.registry`; pydantic, ruamel.yaml, pytest, mypy.
**Storage**: DRG hand-authored overlay + `*.graph.yaml` fragments; test golden baselines
(`tests/architectural/_baselines.yaml`), docs ledger (`delivery-reachability-wiring-table.md`). N/A DB.
**Testing**: pytest — targeted node-ids only (NEVER the full `tests/architectural/` suite locally; it
breaks the session — CI owns the sweep). `uv run pytest` in lanes (bare python imports PRIMARY src).
ATDD red-first per WP. Key suites: `tests/doctrine/drg/test_reachability.py`,
`tests/charter/test_every_load_delivery.py`, `tests/charter/test_action_bundle_delivery.py`,
`tests/architectural/test_no_dead_symbols.py`, `test_no_authored_applies_edge.py`,
`test_registry_completeness.py`.
**Target Platform**: Linux/macOS/Windows CLI (doctrine engine).
**Project Type**: single (library/CLI).
**Performance Goals**: NFR-003 context-bloat bound — suggested doctrine delivered as links + `when`
labels, never full bodies; no per-context eager body dump of the suggested set.
**Constraints**: C-001 consume the 9-symbol forward API, never re-derive the walk; C-002 the 10
progressive_disclosure composition helpers are module-private; C-003 build on `_ActionDoctrineBundle`
`bridge_urns` + requires-closure cadence; C-004 anti_pattern non-activatable, edge-reached, grounded;
C-005 template via edge not re-home; C-006 out-of-scope (value-edge props, DDD↔docs mutual edge, #3064);
C-007 close #3075 only if all 3 sub-parts land; C-008 canonical sources + PR/operator-merge discipline.
**Scale/Scope**: 12 FR / 6 NFR / 8 C → 9 implementation concerns → ~9 WPs (IC-06 splits into 06a/06b).
Base = upstream/main `10e970ed2`. Baseline deferred set = **60** (wiring-table Family C ledger; the "50"/
"39" figures are stale and reconciled at WP04 start). Forward-API retirement ≈ 2–3 wired symbols.

## Charter Check

*GATE: passes before Phase 0; re-checked after design.*

- **Single canonical authority** ✅ — reuse the delivery-rail forward API + `graph_document_to_dict`
  canonical serializer; #3075 fix is root-unification (one serializer + discovery gate), NOT a second
  writer. No parallel walk (C-001). `_post_validate` hook fixes the asset+profile repos at the base
  ownership boundary, not two whack-a-field patches.
- **Architectural alignment** ✅ — doctrine walk stays node-level; `when` surfaced in the charter/
  consumer layer where `edge_to_reference` already lives. No cross-layer leak of edge objects into
  `doctrine.drg.query`.
- **Domain-driven + tiered rigour** ✅ — core-tier surfaces (walk, reconciliation, writer gate) get full
  rigour + non-vacuous gates; DRG-YAML authoring (templates/anti-patterns) gets schema-validation tier.
- **ATDD-first** ✅ — every WP lands a failing-first test through the pre-existing entry point
  (`profile_channel_reachable` + the profile render path — NOT `resolve_context`, D10; `doctrine validate`;
  `test_no_dead_symbols`; `validator.py` for anti-patterns; the fixture). Delivery-bearing WP acceptance =
  "artefact is DELIVERED/reachable" (fails on an inert edge); anti-pattern WP acceptance = "REJECTS
  topology complete + validator green" (validation-tier, never delivered — D14).
- **Terminology** ✅ — Mission canon; no `feature*`; doctrine domain terms are canonical.
- **Gate discipline** ✅ — NFR-006 writer-discovery gate carries a self-mutation test; NFR-002 golden
  moves each carry a ledger row; NFR-004 dead-symbols gate stays green post-retirement.
- **Git/workflow** ✅ — new fast-follow branch off fresh upstream/main; PRs only; operator merges; no
  version numbers assigned in scope.

No violations → Complexity Tracking empty.

## Project Structure

### Documentation (this mission)

```
kitty-specs/doctrine-delivery-activation-01KYQVQK/
├── spec.md                     # committed (85011ce)
├── plan.md                     # this file
├── research.md                 # Phase 0 grounding (points to pre-planning-ledger.md)
├── data-model.md               # DRG/edge/reachability entities touched
├── quickstart.md               # how to verify delivery + run the targeted suites
├── contracts/
│   ├── suggests-delivery-walk.md      # the profile-channel suggests+when delivery contract
│   └── drg-writer-discovery-gate.md   # the writer-registry unification + discovery gate contract
├── pre-planning-ledger.md      # scout grounding (durable)
├── tracer-approach.md / tracer-design-decisions.md / tracer-tooling-friction.md
└── tasks.md                    # Phase 2 (/spec-kitty.tasks)
```

### Source Code (repository root)

```
src/doctrine/drg/
├── reachability.py               # PROFILE_CHANNEL_RELATIONS (+= SUGGESTS), profile_channel_reachable, 4 seed helpers
├── query.py                      # walk_edges (node-level; unchanged) — edge re-lookup done in consumer
├── models.py                     # DRGEdge.when, edges_from, RELATION_DESCRIPTIONS histogram claims
└── migration/
    ├── hand_authored_overlay.py  # A/B/C/E suggests edges; Family-A `when` backfill; anti-pattern edges
    └── extractor.py              # graph_document_to_dict (canonical doc serializer), model_to_graph_dict

src/doctrine/
├── action.graph.yaml             # template:instantiates edge from action:documentation/design (FR-007)
├── anti_pattern.graph.yaml       # authored anti_pattern nodes + smell↔tactic edges (FR-008)
├── tactic.graph.yaml             # refactoring-* tactic edge endpoints
├── assets/repository.py          # _source_paths ordering fix (FR-011)
└── base.py                       # new _post_validate hook (fixes asset + agent_profile twin)

src/charter/
├── reachability_delivery/ (new or in progressive_disclosure) # when-surfacing projection for profile channel
├── progressive_disclosure.py     # edge_to_reference/STATED_DEFAULT_WHEN reuse; forward-API consumption
├── pack_context.py               # 4 activation forward-API symbols wired
├── context.py                    # bundle cadence; helpers extracted → context_renderers/ (FR-012)
├── context_renderers/            # NEW sibling modules: reference_pointers.py, delivery_table.py
└── synthesizer/project_drg.py    # _serialize_graph → graph_document_to_dict (FR-010)

src/specify_cli/
├── migration/rewrite_opposed_by.py   # _write_graph → graph_document_to_dict (FR-010, #2977)
├── doctrine/pack_assembler.py        # _serialize prune → graph_document_to_dict (FR-010 THIRD site)
├── doctrine/pack_validator.py        # except DRGGraphSchemaError → ValidationIssue (FR-011)
└── drg_writers/registry.py           # register all document writers + discovery-gate authority

tests/
├── doctrine/drg/test_reachability.py           # _PROFILE_UNREACHABLE/_PROFILE_RESCUES/_ACTION_UNREACHABLE_D2 (IC-05)
├── doctrine/drg/test_unknown_kind_fails_loudly.py  # _EXPECTED_NODE_COUNT/_EXPECTED_EDGE_COUNT (owned by IC-03/IC-04 per D15)
├── doctrine/drg/migration/test_extractor_projection.py  # extractor node/edge goldens + HAND_AUTHORED_EDGES (IC-03/IC-04)
├── architectural/test_no_authored_applies_edge.py  # RELATION histogram claims (IC-03/IC-04 per their edges)
├── doctrine/test_relation_doc_parity.py        # doctrine-relationships.md mirror parity (IC-03/IC-04)
├── charter/test_every_load_delivery.py         # hermetic fixture (FR-009, IC-09)
├── architectural/test_no_dead_symbols.py       # _CATEGORY_C_DELIVERY_RAIL_FORWARD_API shrink ~2-3 (IC-05)
├── architectural/_baselines.yaml               # mirror rows for allowlist + ratchet (IC-05)
├── architectural/test_registry_completeness.py # + writer-discovery gate + BOTH-shape self-mutation (IC-06a, NFR-006)
└── charter/context_renderers/ + drg tests      # new-helper coverage, delivery/when tests
docs/plans/doctrine/delivery-reachability-wiring-table.md  # deferred set 60→lower + ledgers (IC-05 pins; IC-03/04 histogram)
docs/architecture/doctrine-relationships.md               # RELATION histogram mirror (IC-03/IC-04)
```

**Structure Decision**: single-project library layout; changes are surgical extensions to the existing
doctrine/charter seams named above. No new top-level packages beyond `context_renderers/` siblings and
optional charter-layer delivery projection module.

## Complexity Tracking

*No Charter Check violations — table intentionally empty.*

## Implementation Concern Map

> Concerns, not WPs. `/spec-kitty.tasks` translates these into executable work packages (expected ~8,
> matching the ledger decomposition: IC-02 folds into the core + reconciliation WPs, not a standalone WP).

### IC-01 — Profile-channel `suggests` walk + `when` surfacing + delivery cadence

- **Purpose**: The core delivery vector — make the profile channel follow `suggests` and surface each
  edge's `when` as the applicability condition, delivered as links-not-bodies.
- **Relevant requirements**: FR-001, FR-002, FR-003; NFR-003.
- **Affected surfaces**: `src/doctrine/drg/reachability.py` (`PROFILE_CHANNEL_RELATIONS += SUGGESTS`);
  `src/charter/progressive_disclosure.py` — **the profile-channel `when`-projection lands here (or a
  sibling), MANDATORY, NOT inline in context.py (R-M7/D-M7)** — reusing `link_references`/
  `edge_to_reference`/`STATED_DEFAULT_WHEN`; `src/charter/context.py` (minimal: kind-delivery table entry
  + call site only); sole consumer `src/doctrine/agent_profiles/repository.py:profile_channel_procedure_ids`
  (widen beyond procedures); **`src/doctrine/drg/migration/hand_authored_overlay.py:534-564` — Family-A
  architect→DDD `when` backfill OWNED HERE (D3/R-M6)**, incl. its Family-A edge-count golden delta (D15).
- **Sequencing/depends-on**: none (CORE).
- **Risks**: (D11) `when` is on the INBOUND edge and the walk strips seeds (`visited − seed_set`) → do NOT
  do a per-reached-node `edges_from`; reuse `link_references(merged, roots=profile_seeds,
  delivered=kind_filtered_reached, bridge_urns=reached ∪ seeds)` (`reached ∪ seeds == visited`, no re-walk).
  (D2) walk reaches non-procedure kinds → consumer decides which kinds deliver, links-not-bodies (NFR-003),
  requires-precedence dedup collapses diamonds. **(D10) ATDD asserts on `profile_channel_reachable(graph,
  {agent_profile:architect-alphonso})` + the profile render path — NEVER `resolve_context` (action channel:
  DDD already reachable there = vacuous; profile-seeded reaches nothing = permanently red). Mechanical red
  = `test_reachability.py:710`.** Action channel untouched (separate walk).

### IC-02 — Forward-API allowlist retirement (incremental, ~2–3 symbols)

- **Purpose**: Retire ONLY the forward-API symbols this mission genuinely wires with a **cross-file `src/`
  consumer**; keep the rest allowlisted-with-note. `_symbol_has_caller` counts cross-file src importers
  only (tests NOT counted → WP01 ATDD imports can't trip stale-detection; manufacturing a fake importer is
  itself the anti-pattern the gate warns against).
- **Relevant requirements**: FR-006; NFR-004.
- **Pre-classification (D17, provisional — confirm per-symbol at impl)**: LIKELY-WIRED (delivery
  projection gets a cross-file src consumer): `agent_profile_seed_urns`, possibly `PROFILE_CHANNEL_RELATIONS`,
  possibly `partition_delivery`. LIKELY-STAY-ALLOWLISTED (charter-activation / action-channel concern, no
  src consumer built here): `charter_activated_urns`, `normalize_activation_identifier`,
  `partition_activated_unreachable`, `ActivationReachabilityPartition`, `action_channel_reachable`,
  `action_seed_urns`.
- **Affected surfaces**: consumption edits in `progressive_disclosure.py`/`reachability.py` (owned with
  IC-01); frozenset `_CATEGORY_C_DELIVERY_RAIL_FORWARD_API` + `_baselines.yaml` mirror (owned with IC-05).
- **Sequencing/depends-on**: IC-01 (consumption) then IC-05 (final gate sweep).
- **Risks**: split ownership — consumption edits (IC-01) vs frozenset edits (IC-05); a test-only reference
  must NOT be removed. `profile_channel_reachable` (the wired 10th symbol) is the retirement template.

### IC-03 — Family C4 template topology + delivery via the C4 tactic (schema-tier)

- **Purpose**: Author the `template:instantiates` edge from `action:documentation/design` to the C4 mermaid
  templates (wiring-table canonical topology), so the templates deliver to the architect via IC-01's
  suggests-walk reaching the C4 zoom-in tactic (which already `references:` the templates). Not re-homed as
  assets.
- **Relevant requirements**: FR-007; C-005.
- **Affected surfaces**: `src/doctrine/action.graph.yaml`; **its own edge-count + `suggests`/`instantiates`
  histogram golden delta (D15)** — `test_extractor_projection` `_EXPECTED_EDGE_COUNT` region +
  `RELATION_DESCRIPTIONS`/`doctrine-relationships.md` histogram row for the added edge.
- **Sequencing/depends-on**: **IC-01 (delivery rides IC-01's suggests-walk reaching the C4 tactic — D13)**;
  before IC-05 (wiring-table Family C row).
- **Risks**: (D13) `resolve_context`/profile channel do NOT walk `instantiates` (verified) — so the
  `instantiates` edge is topology completion, NOT the delivery vector; delivery = the C4 tactic's
  `references:` surfaced once IC-01 makes the tactic profile-reachable. ATDD = "C4 templates reach the
  architect via the delivered C4 tactic's references" (fails if IC-01's reference-delivery doesn't carry
  them → real signal, not an inert-edge false-green). Schema-tier — NO core query.py edit.

### IC-04 — Refactoring anti-patterns via `REJECTS` (validation-tier)

- **Purpose**: Author `anti_pattern` artefacts for the code smells each `refactoring-*` tactic solves and
  wire `tactic --REJECTS--> anti_pattern` edges (the existing canonical relation + direction), grounded in
  each tactic's attested `problem`/`when`.
- **Relevant requirements**: FR-008; C-004.
- **Affected surfaces**: `src/doctrine/anti_pattern.graph.yaml` (extends the existing 6-node corpus),
  `src/doctrine/tactic.graph.yaml` / `hand_authored_overlay.py` (REJECTS edges, matching the existing 8);
  **its own node/edge-count + histogram + `test_relation_doc_parity` golden delta (D15)**.
- **Sequencing/depends-on**: before IC-05 (wiring-table Family B row); no IC-01 delivery dep — anti_patterns
  are NEVER delivered by design.
- **Risks**: (D14) `REJECTS` is validation-tier — anti_patterns are "never activated as a live rule"
  (models.py:73); the deliverable is the completed REJECTS topology + green `validator.py:171` (every
  anti_pattern must be a REJECTS-target), NOT context delivery → NO inert-edge problem. ATDD = node exists
  + is REJECTS-target of its refactoring tactic + validator green. C-004: no invented smells — a tactic
  lacking attested `problem`/`when` → defer that anti-pattern with a note. Coordinate with #2847 (we EXTEND
  the existing first-class corpus; introduce no shape #2847 must migrate). curator/doctrine lens recommended.

### IC-05 — Reachability reconciliation: pins + wiring table + ledger + final allowlist sweep

- **Purpose**: Re-measure the profile-reachable set via the canonical helper and reconcile the
  **reachability** goldens (pins + wiring-table deferred set) + the final allowlist sweep. Owns ONLY
  reachability goldens — **NOT node/edge cardinality or the relation histogram** (those belong to the
  authoring WPs IC-03/IC-04 per D15).
- **Relevant requirements**: FR-004, FR-005; FR-006 (final frozenset sweep); NFR-002, NFR-004.
- **Affected surfaces**: `tests/doctrine/drg/test_reachability.py` (`_PROFILE_UNREACHABLE`,
  `_PROFILE_RESCUES`, **and `_ACTION_UNREACHABLE_D2` — D16**); `docs/plans/doctrine/
  delivery-reachability-wiring-table.md` (deferred set from **60** + Family ledgers + reconcile the stale
  50/39 prose — D19); `tests/architectural/test_no_dead_symbols.py` frozenset + `_baselines.yaml` mirror
  (the ~2–3 wired symbols from IC-02's pre-classification).
- **Sequencing/depends-on**: **IC-01 AND IC-03 AND IC-04** (TERMINAL) — WP02/WP03 dep is about the
  wiring-table Family rows (NOT the profile pins, which are a pure function of IC-01/SUGGESTS — reviewer
  can verify that delta independently). Else the Family rows re-stale (NFR-002).
- **Risks**: **NFR-002 is REVIEW-gated, not CI-gated (D18)** — `_PROFILE_UNREACHABLE` is a hardcoded
  literal asserted `measured == pin`, greens the instant the author pastes the new set; only the
  cardinality/histogram goldens (owned by IC-03/04) have CI gates. WP04's per-member ledger-vs-diff review
  is the SOLE, non-delegable gate for the pins + deferred number (optionally add a lightweight
  member-vs-ledger cross-check test). Measure ONLY via `action_channel_reachable`/`profile_channel_reachable`
  (C-001) — never hand-roll. Baseline 60; "39"/"50" are stale (D19).

### IC-06a — DRG writer-registry unification + discovery gate (#3075/#2977, parallel)

- **Purpose**: Root-fix the writer blind spot — route ALL three document-emit sites through the canonical
  `graph_document_to_dict`, register each, and add a non-vacuous discovery gate. File-disjoint from the
  core lane → genuinely parallel.
- **Relevant requirements**: FR-010 (writer half); NFR-006.
- **Affected surfaces**: `src/specify_cli/migration/rewrite_opposed_by.py:_write_graph`,
  `src/charter/synthesizer/project_drg.py:_serialize_graph`, **`src/specify_cli/doctrine/pack_assembler.py`
  (third, worse site — bypasses the mapping funnel via raw `.model_dump()`)**; `src/specify_cli/
  drg_writers/registry.py` (register + discovery-gate authority); `tests/architectural/
  test_registry_completeness.py` (+ discovery gate + self-mutation battery).
- **Sequencing/depends-on**: none (parallel, Lane C).
- **Risks**: NFR-006 non-vacuity — the self-mutation battery MUST inject BOTH an unregistered **dict-literal**
  writer AND an unregistered **`.model_dump()`-shaped** writer, each proven to red independently (D-M5;
  else the pack_assembler shape stays unproven). Bound the claim: "closes the known literal + model_dump
  shapes + regressions"; non-literal doc construction is a residual note. Registry is fail-open by design.

### IC-06b — Repository `ArtifactRepository` Protocol typing (#3075, sequenced)

- **Purpose**: Replace the `object`-typed repository surfaces with an `ArtifactRepository` Protocol
  (`get`/`get_provenance`) and REMOVE the 12 `# type: ignore[attr-defined]`.
- **Relevant requirements**: FR-010 (typing half); NFR-005.
- **Affected surfaces**: `src/charter/progressive_disclosure.py:216,236-237`; `src/charter/context.py`
  (10 ignore sites incl. 3515-3518). Concrete repos already satisfy via `BaseDoctrineRepository`.
- **Sequencing/depends-on**: **AFTER IC-01 AND IC-08 (D12/R-B3)** — it edits the exact `context.py`/
  `progressive_disclosure.py` hunks IC-01 rewrites and IC-08 extracts; NOT parallel, on the critical path.
- **Risks**: C-007 all-or-nothing closure — #3075 AND #2977 close only if IC-06a AND IC-06b both land; else
  leave both open with a residual note. `mypy --strict` net-removes ignores (NFR-005), adds none.

### IC-07 — `DRGGraphSchemaError` UX + asset source-path fix (#3062)

- **Purpose**: Surface `DRGGraphSchemaError` as a structured `ValidationIssue` during `doctrine validate`
  instead of a raw traceback; fix the asset `_source_paths` split-brain (record only after validation),
  and the AgentProfileRepository twin, at the base ownership boundary.
- **Relevant requirements**: FR-011.
- **Affected surfaces**: `src/specify_cli/doctrine/pack_validator.py:523-526,973-977` (add
  `except DRGGraphSchemaError`); `src/doctrine/base.py` (new `_post_validate` success-path hook fired at
  **BOTH** load paths — built-in `_load` AND overlay `_apply_overlay_layer` — D-M8);
  `src/doctrine/assets/repository.py:121-133` + the AgentProfileRepository twin (both overlay paths).
- **Sequencing/depends-on**: none (independent, Lane C).
- **Risks**: (D-M8) wiring `_post_validate` only at the built-in site leaves the overlay layer's split-brain
  — fire at every success site paired with `_pre_validate`, no-op base default; regression test loads a
  **project-layer** asset with a validation failure and asserts `source_path` absent. Base-hook must not
  change other repos' success-path behaviour.

### IC-08 — `context.py` helper extraction (#2532 slice)

- **Purpose**: Extract the WP13 reference-pointer helpers (+ their module cache) and the WP10/WP11
  delivery-table helpers to `context_renderers/` siblings, behaviour-preserving.
- **Relevant requirements**: FR-012; NFR-001.
- **Affected surfaces**: `src/charter/context.py` (1702-1900 reference-pointer; 728-868 delivery-table) →
  `src/charter/context_renderers/reference_pointers.py` + `delivery_table.py`.
- **Sequencing/depends-on**: **IC-01** (post-hoc — extracts the FINAL cadence shape IC-01 creates; the
  usual tidy-first ordering is INVERTED here, justified because the code to extract doesn't exist until
  IC-01 lands).
- **Risks**: reference-pointer slice has zero external consumers but is coupled to module-global
  `_REFERENCE_SOURCE_INDEX_CACHE` (move it with the functions); delivery-table slice has 3 external test
  importers → extract with a re-export shim OR same-PR test-import updates. `Refs #2532` (residual note),
  NOT `Closes` (this is a slice, not full de-god of the 3528-line module).

### IC-09 — Hermetic delivery-test fixture (#fixture)

- **Purpose**: Make `test_every_load_delivery::project` exclude/reset `context-state.json` so `first_load`
  is always True unless the test sets it — eliminating the local-only false-red.
- **Relevant requirements**: FR-009.
- **Affected surfaces**: `tests/charter/test_every_load_delivery.py:63-84` (line 75 copytree).
- **Sequencing/depends-on**: none (independent) — **land EARLY** to de-flake IC-01/IC-08 ATDD cycles.
- **Risks**: minimal; `ignore_patterns("context-state.json")` or unlink-after-copy.
