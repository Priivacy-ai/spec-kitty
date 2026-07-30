# Pre-Planning Ledger — doctrine-delivery-activation-01KYQVQK

Grounding from the pre-planning squad (3 profile-loaded read-only scouts), 2026-07-29.
Base: `feat/doctrine-delivery-activation` @ `85011ce` (= upstream/main `10e970ed2` + spec commit).
Parent slice PR #3070 merged into this base.

---

## SCOUT 1 — architect-alphonso: delivery-rail core state

### Anchors (all confirmed present)
- **The walk**: `src/doctrine/drg/reachability.py:99-125` `profile_channel_reachable()` →
  `walk_edges(graph, seed_set, set(PROFILE_CHANNEL_RELATIONS), max_depth=None)`.
- **Relation set**: `reachability.py:48-50` `PROFILE_CHANNEL_RELATIONS = {REQUIRES, SPECIALIZES_FROM}`
  — this is where `Relation.SUGGESTS` is added.
- **Sole consumer**: `src/doctrine/agent_profiles/repository.py:855-877`
  `profile_channel_procedure_ids()` — filters reached set to `procedure:` only, returns bare ids,
  surfaces NO relation/`when`.
- **`when` storage**: `src/doctrine/drg/models.py:360-372` `DRGEdge.when: str|None`; edges via
  `DRGGraph.edges_from(urn, relation)` (`models.py:415-425`).
- **`action_channel_reachable`** (`reachability.py:69-96`) is a SEPARATE channel delegating to
  `resolve_context` (already does scope→requires→suggests). The two channels do NOT share a walk
  → adding `suggests` to the profile channel does not affect the action channel.

### CRITICAL SEAM FACT
`walk_edges` (`src/doctrine/drg/query.py:64-`) builds adjacency `dict[str,list[str]]` and returns
a **set of node URNs only — the edge (and its `when`) is discarded**. So
`PROFILE_CHANNEL_RELATIONS += SUGGESTS` makes nodes reachable but cannot surface `when`.
Surfacing the applicability condition requires EITHER a new edge-returning walk variant OR a
post-hoc `edges_from` lookup per reached node in the consumer, plus `(target, relation)` dedup for
diamonds. Ready-made projection: `charter/progressive_disclosure.py:52-68` `edge_to_reference()`
returns `{id, relation, when, reason}` and applies `STATED_DEFAULT_WHEN` (l.33-36) when a suggests
edge has no authored `when` — BUT it lives in the `charter` layer, not `doctrine`.

### 9 forward-API symbols — ALL currently unwired (0 real src consumers)
Pinned in `_CATEGORY_C_DELIVERY_RAIL_FORWARD_API` @ `tests/architectural/test_no_dead_symbols.py:1089-1106`.
| Symbol | Def site |
|---|---|
| `action_channel_reachable` | `doctrine/drg/reachability.py:69` |
| `PROFILE_CHANNEL_RELATIONS` | `reachability.py:48` |
| `action_seed_urns` | `reachability.py:53` |
| `agent_profile_seed_urns` | `reachability.py:58` |
| `partition_delivery` | `charter/progressive_disclosure.py:93` |
| `charter_activated_urns` | `charter/pack_context.py:496` |
| `normalize_activation_identifier` | `charter/pack_context.py:362` (intra-module only) |
| `partition_activated_unreachable` | `charter/pack_context.py:426` |
| `ActivationReachabilityPartition` | `charter/pack_context.py:389` |
The 10th rail symbol `profile_channel_reachable` IS wired (`repository.py:875`) — the retirement template.

### Delivery-bundle scaffolding
- `_ActionDoctrineBundle` — `src/charter/context.py:121-150`; `bridge_urns` field (l.150) built at
  `context.py:1129/1139-1151` = every URN visited during `resolve_context` (incl. excluded kinds like
  paradigm) → pass-through hops usable as reference sources without entering the eager set.
- `build_disclosure_payload` — `charter/progressive_disclosure.py:267-317`; `inline_urns =
  requires_closure(merged, roots)`; top-level `references` via `link_references(..., bridge_urns=...)`.
  Called from `context.py:3513-3525`.
- **10 helpers MODULE-PRIVATE**: `progressive_disclosure.py:333-338` `__all__` = only
  `{build_disclosure_payload, collect_typed_artifacts, partition_delivery, requires_closure}`.
- **Requires-closure render cadence** (landing-pass "D2c") — `context.py:1202-1253`
  `_render_action_doctrine_lines`: entries INSIDE roots' requires-closure render full body; entries
  OUTSIDE (reached via suggests) render a "fetch + when-doing" stanza — keeps the text block in budget.
  Same `requires_closure` authority as the `--json` payload.

### Reachability pins + wiring table
- `tests/doctrine/drg/test_reachability.py`: `_PROFILE_UNREACHABLE` (l.363-519) = **153 members**,
  defined `_activated() - profile_channel_reachable(...)`; `_PROFILE_RESCUES` (l.525-530) = **2**
  (`directive:DIRECTIVE_044`, `tactic:test-readability-clarity-check`) = `_ACTION_UNREACHABLE_D2 - _PROFILE_UNREACHABLE`.
- `docs/plans/doctrine/delivery-reachability-wiring-table.md`: **deferred set = 50** (l.211-220;
  breakdown l.271: directive 4 · paradigm 3 · procedure 4 · styleguide 3 · tactic 28 · toolguide 8).
  Family C asset assessment (l.598-617): C4 exemplars already ship as `template` artefacts, author NO
  new asset; canonical path = *"a template `instantiates` edge from the `documentation/design` action"*
  (= `action:documentation/design`).
- **NFR-004 gate mechanism**: Family ledgers record moved counts; gated by
  `tests/architectural/test_no_authored_applies_edge.py::TestPositiveCountClaimsAreTrue` (parses
  `RELATION_DESCRIPTIONS[Relation.*]` histogram claims in `doctrine.drg.models`, mirrored in
  `docs/architecture/doctrine-relationships.md`) + byte-identical extractor golden
  `test_extractor_projection`/`test_shipped_graph_is_fresh_and_byte_identical`
  (`_EXPECTED_NODE_COUNT`/`_EXPECTED_EDGE_COUNT + len(HAND_AUTHORED_EDGES)`).

### A/B/C/E suggests edges — all in `src/doctrine/drg/migration/hand_authored_overlay.py`
- **Family A** (l.534-564): architect-alphonso/paula/randy → `paradigm:domain-driven-design`,
  `Relation.SUGGESTS`, **`reason` only — NO `when`**.
- **Family B** (l.622-717 + 730-801): `DISCIPLINED_REFACTORING → refactoring-*` (7, each `when=`) +
  7 profile→DISCIPLINED_REFACTORING (`when="when tidying code…"`).
- **Family C** (l.878-1017): architect-alphonso → `USE_C4_MODEL_TECHNIQUES` (`when="documenting or
  reviewing system architecture"`) + 8 USE_C4 → C4 techniques (each `when=`).
- **Family E** (l.1801-2032): architect-alphonso → `reasons-canvas-writing` (`when=`),
  → `event-storming-discovery` (`when=`); terminology group edges — but those SOURCES are
  action-UNREACHABLE, not profile-sourced.

### RISKS (architect)
1. `walk_edges` drops the edge → cannot surface `when` from node walk; need edge-returning variant
   or `edges_from` re-lookup + `(target,relation)` dedup. `edge_to_reference` shape exists but in
   `charter` layer.
2. Channel isolation holds (no action-channel over-delivery) BUT sole consumer filters procedures-only;
   following suggests reaches paradigms/styleguides/directives/tactics/toolguides → consumer must decide
   WHICH kinds to deliver + HOW (NodeKind delivery table is in `context.py`, not the profile repo).
3. Pins move: `_PROFILE_UNREACHABLE` (153) shrinks; `_PROFILE_RESCUES` shifts; every wiring-table
   "INERT / stays at 50 / unchanged" claim becomes false and must reconcile in the SAME change under
   the NFR-004 golden gate.
4. `when`-coverage inconsistent: Family A profile→DDD has NO `when` (reason only) → naive surface renders
   `STATED_DEFAULT_WHEN`, not authored. Scope question: backfill Family A `when`?
5. Latent doc/pin drift: wiring-table Family A says "profile channel 39→39" while live pin is 153 — the
   "39" is NOT authoritative; reconciliation inherits this discrepancy.
6. Cycle/dedup handled at node level, but edge-returning variant reintroduces edge dedup + cadence
   precedence (inline-eager `requires` must win over `suggests`-link), mirroring `partition_delivery`'s
   requires-closure-first split.
7. Family C canonical path is action-scoping (`action:documentation/design` via template instantiates),
   NOT the profile walk — walk-extension alone may NOT discharge Family C; plan must not assume it does.

---

## SCOUT 2 — paula-patterns: hygiene items + seam risk

### Item 1 — Writer-registry blind spot (#3075)
- Mapping level ALREADY unified: `model_to_graph_dict` @ `src/doctrine/drg/migration/extractor.py:1379`;
  both named sites funnel node/edge dicts through it and are registered `MAPPING_WRITERS`
  (`registry.py:153-169`). So node/edge fields can't drop.
- DOCUMENT level NOT unified: `graph_document_to_dict` @ `extractor.py:1424` is the SOLE `DOCUMENT_WRITERS`
  member (`registry.py:171-176`). The two named sites hand-restate the 5 top-level keys:
  `rewrite_opposed_by._write_graph` (`src/specify_cli/migration/rewrite_opposed_by.py:368-380`) and
  `project_drg._serialize_graph` (`src/charter/synthesizer/project_drg.py:86-104`) → a NEW top-level
  DRGGraph field drops silently at both; neither is a DocumentWriter member.
- **THIRD, WORSE, UNNAMED site: `pack_assembler.py:495-501`** — restates 5 keys AND bypasses
  `model_to_graph_dict` via raw `.model_dump()` → drops `FIELDS_WITHHELD_FROM_GRAPH_OUTPUT` (emits
  `provenance`) + omit-when-empty rules. Not a registry member at any shape.
- Registry is hand-curated `Final` tuple, NO self-registration by design (`registry.py:20-25`); W-2 gate
  `test_registry_completeness.py:199-220` iterates MEMBERS — no discovery gate scans src/ for emitters.
  → **Real fix = route ALL document emits through `graph_document_to_dict` + register each + author a
  DISCOVERY gate** (AST/grep for dict literals carrying schema_version+nodes+edges, assert each delegates).
- Protocol typing debt: repository surface typed `object` → 12 `# type: ignore[attr-defined]`
  (`progressive_disclosure.py:216,236-237`; `context.py:552,568,1520,2526,2757,3375,3515-3518`).
  Clean fix: an `ArtifactRepository` Protocol (`get(id)->T|None`, `get_provenance(id)->str|None`); concrete
  repos already satisfy via `BaseDoctrineRepository` (`src/doctrine/base.py:329`).

### Item 2 — DRGGraphSchemaError UX (#3062)
- Defined `models.py:460`, raised `load_graph_document` (`models.py:519`); deliberately NOT a
  `DRGLoadError` subclass (`:468`) → passes through silent-degrade handlers. `loader.py:74-78` only
  re-wraps ValidationError.
- Uncaught consumer sites (catch only DRGLoadError): `pack_validator.py:523-526` + `973-977`. Fix: add
  `except DRGGraphSchemaError` → `ValidationIssue(severity="error", artifact_type="drg", file=…,
  message=str(exc), category="schema_invalid")` (`ValidationIssue` @ `pack_validator.py:92-119`).
- AssetRepository `_pre_validate` records `_source_paths[id]` @ `repository.py:121-133` BEFORE validation
  (base `_load` calls hook @ `base.py:174` before `model_validate` @ `:175`) → failed-validation id still
  gets a source_path → `source_path(id)` returns path for id `get(id)` treats absent (split-brain).
  **Fix: add a base-level `_post_validate(obj,file)` hook fired only on success; move the record there —
  and check the TWIN in AgentProfileRepository (docstring says "mirrors" it).**

### Item 3 — context.py extraction (#2532)
- context.py = **3528 lines**. Existing `context_renderers/` siblings: authority_paths, fetch_stanza,
  section_bodies, token_budget, profile_sections. Reference *rendering* already at `governance_references.py`.
- **WP13 reference-pointer helpers** (`context.py:1702-1900`): `_filter_references_for_action`,
  `_reference_source_index`, `_resolve_reference_source`, `_distribute_references_across_kinds`,
  `_select_reference_pointers` + module-global cache `_REFERENCE_SOURCE_INDEX_CACHE`. **Zero external
  consumers → lowest-risk**, but the cache MUST move with the functions.
- **WP10/WP11 delivery-table helpers** (`context.py:728-868`): `_KindDelivery`,
  `_ACTION_BUNDLE_DELIVERY_BY_KIND`, `_kind_delivery`, `action_bundle_bucket`, `action_bundle_gate`,
  `_classify_artifact_urns`. **HAVE external test importers** (`test_action_bundle_delivery.py`,
  `test_context_display_charter_md.py`, `test_unknown_kind_fails_loudly.py`) → extract only with a
  re-export shim from `charter.context` OR same-PR test-import updates.
- bridge_urns / requires-closure cadence (`context.py:145-150, 1090/1129/1150, 1202, 1238`) thread BOTH
  slices → the two extractions are not fully independent; sequence after WP01's cadence is final.

### Item 4 — Hermetic fixture
- `tests/charter/test_every_load_delivery.py:63-84` `project` fixture; line 75 `shutil.copytree(src/.kittify/
  charter, …)` includes gitignored `context-state.json`; `_prepare_context_state` reads it
  (`context.py:696`) → `first_load=False` in a populated checkout → `first.mode=="bootstrap"` fails
  locally, passes on fresh CI. Fix: `ignore=shutil.ignore_patterns("context-state.json")` OR unlink post-copy.

### RISKS (paula)
1. #3075 real fix = ONE canonical document serializer + discovery gate, not two patched sites.
2. `pack_assembler.py:495` is a third, worse writer any patch-only fix misses.
3. Registry fail-open to omission by construction → needs static discovery/AST gate (NFR-006 non-vacuous).
4. context.py extraction coupling: reference slice safe (move cache with it); delivery slice needs shim.
5. AssetRepository bug likely twinned in AgentProfileRepository → base `_post_validate` hook fixes both.

---

## SCOUT 3 — planner-priti: decomposition + related issues

### Related issues
| Issue | State | Coverage | PR verb |
|---|---|---|---|
| #3075 | OPEN | FR-010 full (3 sub-parts; C-007 gates) | Closes IFF all 3 land, else Refs+note |
| #3062 | OPEN | FR-011 full | Closes |
| #2532 | OPEN | FR-012 **slice-by-design** (not full de-god) | **Refs + residual note** (confirmed slice from brief) |
| #3063 | CLOSED | authored the topology we animate | Refs (context) |
| #3064 | OPEN | **C-006 OUT OF SCOPE — do not touch** | none |
| #2977 | OPEN | **DUPLICATE of #3075** (already assigned stijn-dejongh) | Closes (with #3075) IFF FR-010 whole |
- Adjacent collision-watch (verify no silent overlap; likely Refs): **#3056** (progressive-disclosure
  deferred half: fetch linked + backfill 118 uncovered `when` edges — adjacent to FR-002/003);
  **#2847** (promote inline anti_patterns corpus to first-class DRG nodes — **directly adjacent to FR-008**;
  keep FR-008 a bounded slice, own `anti_pattern.graph.yaml` carefully); #3061 (4 action:plan/* nodes →
  zero artefacts; FR-004 re-measure may surface); #3009/#2994 (orphan audits; watch wiring-table cross-talk).
- Hygiene: issue-matrix row + claim + tracker comment per addressed issue at implement-start; assign
  #3075/#3062/#2532/#2977 to HiC stijn-dejongh.

### Proposed decomposition (8 WPs / 3 lanes)
- **WP01 (CORE)** FR-001/002/003 + FR-006(incremental) + NFR-003 — `reachability.py`,
  `progressive_disclosure.py`, `context.py`. deps: none.
- **WP02** FR-007 C4 `template:instantiates` edge — `src/doctrine/action.graph.yaml`. dep WP01.
- **WP03** FR-008 anti-patterns + edges — `anti_pattern.graph.yaml`, `tactic.graph.yaml`. dep WP01.
- **WP04 (TERMINAL)** FR-004/005 + FR-006(final sweep) + NFR-002/004 — `test_reachability.py`,
  wiring-table, ledger, `test_no_dead_symbols.py`, `_baselines.yaml`. **deps WP01+WP02+WP03**.
- **WP05** FR-012 + NFR-001 — extract `context.py`→`context_renderers/`. dep WP01 (post-hoc).
- **WP06** FR-010 + NFR-005/006 — writer discovery gate + registration + Protocol typing. indep.
- **WP07** FR-011 — DRGGraphSchemaError UX + asset source_path. indep.
- **WP08** FR-009 — hermetic fixture. indep, **land early** (de-flakes WP01/WP05 ATDD).
- Lanes: A=WP01→WP04 (+WP05 branch); B=WP02,WP03; C=WP06,WP07,WP08 (off critical path).

### RISKS (priti)
1. **FR-007/008 MUST precede WP04** (else goldens go stale → NFR-002 violation). Open sub-question:
   does the FR-004 re-measure helper traverse `template:instantiates`/anti-pattern relations at all, or
   only `suggests`? If not in the walked relation set they won't move FR-004 counts but STILL appear as
   wiring-table Family B/C deferred rows (FR-005). → WP04-last regardless.
2. context.py shared-ownership WP01 vs WP05 — strict sequencing, WP01 owns during dev; tidy-first is
   INVERTED here (code to extract doesn't exist until WP01 lands) — justified exception.
3. progressive_disclosure + allowlist split — WP01 owns symbol-consumption; WP04 owns frozenset/baseline;
   a symbol referenced only in a test must NOT be removed.
4. #3075=#2977 dup; C-007 all-or-nothing; NFR-006 gate must be non-vacuous (self-mutation test).
5. NFR-002 per-count discipline — reviewer diffs goldens vs ledger 1:1.
6. FR-008: no invented smells (C-004); per-tactic attestation check; don't collide #2847; curator lens.
7. FR-009 land early.

---

## ORCHESTRATOR SYNTHESIS — decisions carried into the plan
- **D1 (delivery mechanism, WP01):** surface `when` via a `charter`-layer projection reusing the
  `edge_to_reference` shape (NOT a node-only walk); the doctrine walk stays node-level, the consumer does
  the edge re-lookup + `(target,relation)` dedup + requires-first cadence precedence. Prove delivery with
  an ATDD test on `resolve_context`/profile-channel output, not on the raw walk.
- **D2 (kind delivery, WP01):** following `suggests` reaches non-procedure kinds; the consumer decides
  which kinds deliver (NodeKind delivery table in `context.py`) as links-not-bodies (NFR-003), reusing the
  existing requires-closure "fetch + when-doing" cadence.
- **D3 (Family A `when`):** Family A architect→DDD edges carry no `when`; default = backfill a grounded
  `when` on those edges (derived from the existing `reason`) so delivery is authored, not STATED_DEFAULT —
  small DRG-YAML authoring folded into Lane B. (Surface at post-plan check-in.)
- **D4 (Family C two vectors):** the C4 *techniques* (paradigm/toolguide/procedure) deliver via WP01's
  profile suggests-walk (architect→USE_C4→techniques); the C4 *template artefacts* deliver via WP02's
  `template:instantiates` edge from `action:documentation/design`. Complementary, not competing.
- **D5 (inert-edge guard, WP02/WP03):** FR-007/008 edges must land in a relation an active channel walks,
  else they repeat this mission's own bug. Each WP's ATDD acceptance = "artefact is delivered/reachable",
  which FAILS on an authored-but-inert edge → self-correcting. Plan-phase: confirm which relations each
  channel walks; add the relation to the channel (with reachability proof) if needed.
- **D6 (#3075 scope, WP06):** fix the ROOT — route all THREE document-emit sites (incl. `pack_assembler`)
  through `graph_document_to_dict`, register each, author the non-vacuous discovery gate, fold Protocol
  typing. Close #3075 AND #2977 only if all land (C-007).
- **D7 (#3062, WP07):** structure the error at both pack_validator sites; fix asset `_source_paths` via a
  base `_post_validate` hook; fix the AgentProfileRepository twin in the same WP.
- **D8 (#2532 = slice, WP05):** extract reference-pointer helpers (+ their module cache) and delivery-table
  helpers (+ re-export shim for the 3 test importers); Refs #2532 (residual note), do NOT Closes.
- **D9 (ordering):** WP08 first (de-flake); WP01 core; WP02/WP03 + Family-A `when` before WP04; WP04
  terminal reconciliation; WP05 after WP01; WP06/WP07 fully parallel.

---

## POST-PLAN SQUAD (3 opus lenses: renata/paula/priti) — findings + remediation

All three verdicts = NEEDS-REMEDIATION; strong convergence. Core D1 reachability seam confirmed SOUND
(no competing walk — `link_references` filters `target in delivered`, so the consumer can't surface an
unreached node). Remediation decisions D10–D18 below; grounding facts verified against live code.

**BLOCKERS (converged):**
- **R-B1 (renata) — wrong assertion surface.** A1/A2/SC-001 named `resolve_context` = the ACTION channel:
  DDD is ALREADY action-reachable (vacuously green) AND `resolve_context` from a profile reaches nothing
  (`test_reachability.py:720` pins it; permanently red). → **D10:** assert on
  `profile_channel_reachable(graph, {agent_profile:architect-alphonso})` + the profile render path
  (`_render_profile_sections`/`profile_channel_procedure_ids`); FORBID `resolve_context`; the guaranteed
  mechanical red is `test_reachability.py:710 test_profile_relations_are_requires_and_specializes_from`.
- **R-B2 (paula M1) — C2 seam wording implements the bug.** `when` is on the INBOUND edge; the walk strips
  seeds (`visited - seed_set`), so a per-reached-node `edges_from` misses Family A/B (seed-sourced). →
  **D11:** reuse `link_references(merged, roots=profile_seeds, delivered=kind_filtered_reached,
  bridge_urns=reached ∪ seeds)` — `reached ∪ seeds == visited`, NO re-walk. Delete "per-reached-node".
- **R-B3 (paula B1 + priti B3, CONVERGED) — IC-06 not parallel.** Protocol typing removes 10 `# type:
  ignore` in `context.py` (incl. 3515-3518 ⊂ WP01's 3513-3525 block) + 2 in `progressive_disclosure.py`
  = WP01/WP05's files. → **D12: SPLIT IC-06** → **IC-06a** (registry unify + register + discovery gate +
  self-mutation; `rewrite_opposed_by`/`project_drg`/`pack_assembler`/`registry.py`/`test_registry_
  completeness.py` — genuinely parallel) + **IC-06b** (`ArtifactRepository` Protocol + 12 ignore removals;
  edits core-lane files → sequence AFTER IC-01 + IC-09, on the critical path). C-007 holds across 06a+06b.
- **R-B4 (priti B1 + renata M1, CONVERGED) — template edge inert.** `resolve_context` walks
  scope/requires/suggests/vocabulary, NOT `instantiates` (query.py:139-160, verified); 8 instantiates edges
  already exist, none walked. **GROUNDED RESOLUTION → D13:** the C4 zoom-in tactic
  (`c4-zoom-in-architecture-documentation.tactic.yaml`) already `references:` the mermaid templates, so
  once IC-01's suggests-walk reaches the C4 tactic (architect→USE_C4→c4-tactic) its template references
  deliver via the reference-pointer path. FR-007 = author the `template:instantiates` topology edge +
  ATDD "C4 templates reach the architect via the delivered C4 tactic's references" (DEPENDS ON IC-01).
  **IC-03 stays schema-tier; NO core query.py edit.** (If future appetite wants the action channel to walk
  instantiates directly, that's a separate mission.)
- **R-B5 (priti B2 + renata M2, CONVERGED) — anti-pattern relation.** **GROUNDED → D14:** the canonical
  relation is the EXISTING `Relation.REJECTS` (models.py:123 "from a good artefact to a marked
  anti-pattern"), direction **tactic → anti_pattern** (matching the 8 existing REJECTS edges +
  `validator.py:171` requiring every anti_pattern be a REJECTS-target). anti_patterns are DELIBERATELY
  never delivered/activated ("never activated as a live rule", models.py:73) → **NO inert-edge problem**;
  the deliverable is the completed REJECTS topology + green validator, at VALIDATION tier, not delivery.
  ATDD = node exists + is REJECTS-target of the refactoring tactic + validator green. Coordinate with
  #2847 (we EXTEND the existing first-class anti_pattern corpus — 6 nodes already in
  anti_pattern.graph.yaml — no new shape #2847 must migrate). Brief's "smell→tactic" phrasing is loose;
  canonical direction is tactic→anti_pattern.

**MAJORS (folded):**
- **R-M1 (priti MAJOR-1) — unowned graph-count/histogram goldens.** `_EXPECTED_NODE_COUNT`/
  `_EXPECTED_EDGE_COUNT` (`test_unknown_kind_fails_loudly.py:105`, `test_extractor_projection.py:392`) +
  `HAND_AUTHORED_EDGES` + `RELATION_DESCRIPTIONS`/`doctrine-relationships.md` histogram +
  `test_relation_doc_parity.py` MOVE when IC-03/IC-04 author YAML — owned by no IC. → **D15:** each
  authoring WP owns its OWN cardinality/histogram golden delta (IC-03 owns its instantiates edge-count +
  histogram row; IC-04 owns its node/REJECTS-edge count + histogram + relation_doc_parity). **IC-05 owns
  ONLY the reachability goldens** (pins + wiring-table deferred + dead-symbols), NOT node/edge cardinality.
  Add these 4 golden surfaces to the plan's Project Structure.
- **R-M2 (priti MAJOR-2) — `_ACTION_UNREACHABLE_D2` ownership.** Live in test_reachability.py;
  `_PROFILE_RESCUES = _ACTION_UNREACHABLE_D2 - _PROFILE_UNREACHABLE`. → **D16:** IC-05 owns
  `_ACTION_UNREACHABLE_D2` too. FR-004 profile-pin delta is a pure function of WP01 (reviewer verifies
  independent of WP02/03); WP04's WP02/03 dep is about the wiring-table deferred set, not the pins.
- **R-M3 (priti MAJOR-3 + renata m1) — allowlist retirement over-scoped.** `_symbol_has_caller` counts
  ONLY cross-file `src/` importers (tests NOT counted — so WP01 ATDD imports can't trip stale-detection;
  the WP01/WP04 split is safe). → **D17: PRE-CLASSIFY (provisional, confirmed per-symbol at impl):**
  LIKELY-WIRED (get a cross-file src consumer via the delivery projection): `agent_profile_seed_urns`,
  possibly `PROFILE_CHANNEL_RELATIONS`, possibly `partition_delivery` (~2-3). LIKELY-STAY-ALLOWLISTED
  (different concern = charter-activation reachability / action channel; no src consumer built here):
  `charter_activated_urns`, `normalize_activation_identifier`, `partition_activated_unreachable`,
  `ActivationReachabilityPartition`, `action_channel_reachable`, `action_seed_urns` (~6). **FR-006/SC-003
  retire ~2-3, NOT 9; the rest stay allowlisted-with-note — this is the honest scope.**
- **R-M4 (renata M3) — NFR-002 is REVIEW-gated not CI-gated.** `_PROFILE_UNREACHABLE` is a hardcoded
  literal asserted `measured == pin` → greens the instant the author pastes the new set; only relation/
  node/edge counts have CI gates. → **D18:** state in plan/tasks that WP04's per-member ledger-vs-diff
  review is the SOLE (non-delegable) gate for the pins + deferred number; optionally add a lightweight
  test cross-checking each moved member against a ledger row.
- **R-M5 (renata M4 + paula m1) — NFR-006 self-mutation both shapes.** Discovery gate scans dict-literal
  OR `.model_dump()` shapes; self-mutation must inject BOTH an unregistered dict-literal writer AND an
  unregistered `.model_dump()`-shaped writer, each proven to red independently. Bound the "closes the
  class" claim to the known literal/model_dump shapes + regressions (non-literal doc construction =
  residual note).
- **R-M6 (paula M2) — Family-A `when` owner.** Explicitly OWNED BY WP01 (owns Family A delivery + A1);
  it churns the extractor edge golden → coordinate with D15 (WP01 owns its Family-A edge golden delta).
- **R-M7 (paula M3) — projection out of context.py.** WP01's profile-channel projection lands in a
  `progressive_disclosure` sibling (MANDATORY, not "optional") so the 3528-line god-module doesn't grow
  before WP05 slices it.
- **R-M8 (paula M4) — `_post_validate` both load paths.** Fire at built-in AND overlay success sites
  (base.py); regression test loads a project-layer asset with a validation failure asserting `source_path`
  absent. Cover the AgentProfileRepository twin's overlay path too.

**MINORS:** renata m3 — **BASELINE IS 60, NOT 50** (wiring-table Family C ledger "deferred set unchanged
at 60"; the "50" and "39" figures are STALE/inconsistent). → **D19:** baseline = 60; reconcile the 50/60
prose as a WP04-start campsite fix; correct spec/plan/data-model to 60. renata m2 — FR-002 activates ~118
default-`when` deliveries (#3056); acknowledge the mission raises #3056's urgency (Refs). paula m2 —
confirm `link_references` requires-precedence dedup collapses diamonds (already filters `target in
delivered`; add A4 coverage).

**CREDITS (verified sound, no change):** FR→IC coverage complete; tiered rigour correct; NFR-004 gate +
NFR-006 design are right non-vacuous patterns; terminology clean; #2977 folded into #3075 correctly;
#3064 out-of-scope correctly; IC-02 fold, IC-08 tidy-first inversion, IC-09 land-early all affirmed.
