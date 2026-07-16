# Mission Specification: Mission-Type DRG Edges + Graph Sharding

**Mission slug**: `mission-type-drg-edges-01KXKY2N`
**Mission type**: software-dev
**Status**: Draft
**Epic**: #2652 (specify_cli/missions retirement / mission-type unification) — ADR slice **S0** completion
**Tracker issues**: **#2677** (mission_type DRG edges, closes) + **#2680** (graph sharding, closes). Relates: #2651 (minted the nodes), #1923 (orphan curation — coordinate on the shared residual doc only).

---

## Two phases (edges-first, then the enabler)

This mission runs in two phases, in order. **The order was reversed from the original plan after the
post-plan investigation squad (architect-alphonso + paula-patterns + reviewer-renata) proved the sharding
enabler is a ~22-site migration, not a bounded tidy-first step — and that sharding-first would take the
mission's own orphan gate red.** See `traces/design-decisions.md` DD-0.

1. **Phase 1 — Mission-type edges (#2677).** Emit `mission_type → action` `requires` edges into the current
   single-file `src/doctrine/graph.yaml`, regenerate + commit it, and turn the **red-on-`main` orphan gate
   green** (18 → 10). This is the small, verified, time-sensitive deliverable (~2 src + ~2 test files) and it
   lands first so nothing holds it hostage.
2. **Phase 2 — Graph sharding (#2680).** Behavior-preserving reshaping of the now-edge-complete monolith into
   deterministic per-kind `*.graph.yaml` fragments. This is a genuine migration: it introduces a **canonical
   built-in-graph seam**, switches **~6 source + ~16 test** monolith readers through it, deletes the monolith
   atomically, and updates the freshness + orphan gates to read the sharded layout **while keeping them
   green**. It kills the concurrent-mission `graph.yaml` merge-conflict class before the graph grows further.

Phase 2 is sequenced **after** Phase 1 (not before) precisely because the orphan gate's reader
(`_count_orphans` in `test_doctrine_regenerate_graph.py`) reads the monolith directly — the edges must clear
the gate against the monolith first, and Phase 2 then preserves that green state as it re-points every reader.

---

## Purpose

#2651 made `mission_type:<id>` and `action:<type>/<action>` **first-class DRG nodes** but deliberately
deferred their **edges** — `src/doctrine/drg/models.py:46` literally reads
`MISSION_TYPE = "mission_type"  # (nodes only, no edges yet)`. Eight nodes are therefore **orphans** in the
shipped graph (`mission_type:{software-dev,documentation,research,plan}` + `action:plan/{plan,research,review,specify}`),
pushing the shipped-graph orphan count to **18 > the documented ceiling of 14** — a gate that is **red on
`main` today** (`test_shipped_graph_orphan_count_within_documented_residual`).

This mission wires the **minimal-correct** composition edge — each mission type **requires its ordered
action steps** — which:
- de-orphans all 8 nodes (mission_type nodes gain outbound edges; the plan action nodes gain inbound edges);
- returns the orphan count to **10 ≤ 14** (the ceiling is **not** raised — per #2677 "wire, don't raise");
- makes the mission-type **charter cascade** meaningful for the first time (it traverses `requires`);
- reflects the real composition the design authority already mandates (a mission type's steps resolve
  *through* it).

It then **shards** the (now edge-complete) generated graph so future mission-type slices (template/asset/guard
nodes) — and every concurrent doctrine mission — stop colliding on one 129 KB generated blob.

**Design authority:** `docs/architecture/883-mission-type-authority-brief.md`,
`docs/architecture/mission-type-resolution.md`, and ADR `2026-07-14-2` (mission type is the load-bearing
root whose steps/gates/governance resolve through it) — with the ADR-`2026-07-15-1` **S0** slice framing
("mission_type as a first-class DRG node").

### Deliberate boundary (why only one edge class)

The operator's full design intent — mission types connect to **steps, WP templates, assets, and guards** —
maps onto the graph as follows, and only the first is in scope now:
- **steps** → the `action_sequence` **is** the steps; they are already `action:*` DRG nodes (24 exist). ✅ in scope.
- **WP templates** → the `template:` node population that would be targeted does not exist (`template_set` is
  `null` for 3 of 4 types); minting it is #883's explicitly-deferred template slice. ❌ future.
- **assets** → there is **no asset node population at all** (`src/doctrine/assets/built-in/` has only a
  README). ❌ future (nothing to point at).
- **guards/gates** → there is **no `GUARD`/`GATE` NodeKind**; modelling gates as DRG artefacts is a net-new
  expansion. ❌ future (separate slice).

Only `mission_type → action` touches the 8 orphans; the other three classes contribute nothing to them and
require minting node populations first. This mission ships the orphan-resolving edge and honestly leaves the
rest as tracked future scope.

---

## Domain Language

| Term | Meaning |
|------|---------|
| **DRG** | Doctrine Reference Graph (`src/doctrine/graph.yaml` → per-kind `*.graph.yaml` fragments after Phase 2) — nodes (URN-keyed artefacts) + edges (typed relations). |
| **Orphan** | A DRG node with **no** inbound or outbound edge (`_count_orphans` = `urns - incident`). |
| **`mission_type:<id>`** | Root DRG node for a built-in mission type. |
| **`action:<type>/<step>`** | DRG node for one action of a mission type (from `<type>/actions/<step>/index.yaml`). |
| **`action_sequence`** | The ordered list of steps a mission type defines, declared in `mission_types/<id>.yaml`. |
| **`requires` relation** | The composition-of-mandatory-parts DRG relation the charter cascade traverses. |
| **Built-in-graph seam** | The single canonical accessor (`load_built_in_graph()` / `built_in_graph_source()`) that every consumer routes through to read the shipped graph — introduced by Phase 2 so sharding is not a whack-a-field edit. |
| **Fragment** | One per-kind `src/doctrine/*.graph.yaml` file (Phase 2), merged by `load_graph_or_dir`. |

---

## User Scenarios & Testing

Actors: **doctrine authors**, **the charter cascade**, **the DRG loader/consumers**, and **CI**.

### Scenario 1 — The mission-type graph is edge-complete (de-orphaning) — Phase 1, #2677

- **Trigger**: `spec-kitty doctrine regenerate-graph` runs the extractor over the doctrine tree.
- **Happy path**: each `mission_type:X` emits a `requires` edge to every `action:X/<step>` in its
  `action_sequence`. `mission_type:plan → action:plan/{specify,research,plan,review}` gives the plan action
  nodes an inbound edge and the plan type node its outbound edges.
- **Rule**: after regeneration, **no `mission_type:*` node and no `action:*` node in any `action_sequence`
  is an orphan**; the shipped-graph orphan count is `10 ≤ 14`.

### Scenario 2 — The charter cascade becomes meaningful — Phase 1

- **Trigger**: `charter activate mission-type <X> --cascade`.
- **Happy path**: the cascade traverses the new `requires` edges from `mission_type:X` — previously a no-op
  for mission types (no outbound edges existed).

### Scenario 3 — The gate stays green without raising the ceiling — Phase 1

- **Trigger**: CI runs `test_shipped_graph_orphan_count_within_documented_residual`.
- **Happy path**: passes because the count is `10 ≤ 14`; `DOCUMENTED_ORPHAN_RESIDUAL` is **unchanged at 14**.

### Scenario 4 — The generated graph is sharded — Phase 2, #2680

- **Trigger**: `spec-kitty doctrine regenerate-graph` runs the generator.
- **Happy path**: the generator writes deterministic per-kind `src/doctrine/*.graph.yaml` fragments (one
  fragment **per populated node-kind**; each fragment owns a disjoint set of nodes + the edges whose **source**
  node is that kind); every consumer loads via the **built-in-graph seam** → `load_graph_or_dir`, which
  merges the fragments into one `DRGGraph` equal to the pre-sharding graph. The monolith `graph.yaml` is
  **deleted in the same change**. Behavior is unchanged; only the on-disk layout + load path differ.
- **Rule**: the merged graph equals the pre-sharding graph (same node/edge **sets**, same `assert_valid`
  result, same output on every consumer surface); a change touching one kind regenerates only that kind's
  fragment → a localized diff.

### Scenario 5 — No consumer silently degrades when the monolith is deleted — Phase 2

- **Trigger**: any code path that reads the shipped graph after the monolith is replaced by fragments.
- **Happy path**: profile lineage (`specializes_from`), charter lint's built-in DRG state, and pack-validator's
  built-in URN set are **identical** before and after sharding — because all readers were routed through the
  seam. **Failure mode guarded against**: three current readers *swallow* `DRGLoadError` and degrade to an
  empty graph (`agent_profiles/repository.py`, `pack_validator.py`, `charter_runtime/lint/_drg.py`), so a
  naive delete would give green tests with silently-lost data. The behavior-preserving proof asserts on these
  three surfaces' **outputs**, not merely on merged-graph equality.

### Edge cases

- **`retrospect` actions**: `action:{documentation,research,software-dev}/retrospect` nodes exist but
  `retrospect` is in **no** `action_sequence`. They are already non-orphan (they carry `scope` edges), so
  they need no mission-type edge — but the spec must **decide explicitly** whether to append `retrospect`
  to sequences or leave it (default: leave; it's not an orphan).
- **Dangling-target safety**: every action in **all four** `action_sequence`s has a matching `actions/<step>/`
  index dir today (verified for software-dev 5, documentation 7, research 5, plan 4 — zero dangling), so no
  `mission_type→action` edge is dangling. The mission must keep this invariant (a sequence step with no index
  dir would fail the validator's dangling-target check — a desirable coupling).
- **Byte-identity freshness (both phases)**: the generated graph MUST be regenerated and committed in the same
  change, or `test_regenerate_twice_is_byte_identical` / `test_check_reports_committed_graph_fresh` go red. In
  Phase 1 this is the monolith; in Phase 2 the freshness twins must be re-pointed at the sharded layout.
- **Loader precedence trap**: `load_graph_or_dir` **prefers** a `graph.yaml` when one exists in the target dir
  and *ignores* `*.graph.yaml` fragments (`loader.py:93-95`). So Phase 2 MUST delete the monolith atomically
  in the same commit that writes fragments, or every dir-load silently reads the stale monolith. A test
  asserts "fragments present ∧ monolith absent".
- **Fragment location**: fragments live at **`src/doctrine/*.graph.yaml`** (NOT `src/doctrine/drg/`), because
  the 6 already-shard-safe consumers glob `resolve_doctrine_root()` = `src/doctrine/`. A test pins fragment
  dir == loader glob root.

---

## Requirements

### Functional Requirements — Phase 1: Mission-Type Edges (#2677)

| ID | Requirement | Status |
|----|-------------|--------|
| FR-001 | The DRG generator emits, for every built-in mission type, a `requires` edge `mission_type:<id> → action:<id>/<step>` for each `<step>` in that type's `action_sequence` (`mission_types/<id>.yaml`). | Draft |
| FR-002 | `src/doctrine/graph.yaml` is regenerated (via `spec-kitty doctrine regenerate-graph`) and committed in the same change, so the freshness gate (byte-identity) passes. | Draft |
| FR-003 | After regeneration, zero `mission_type:*` nodes and zero `action:*` nodes named in an `action_sequence` are orphans; the shipped-graph orphan count is ≤ the unchanged ceiling of 14 (not raised). | Draft |
| FR-004 | The stale S0 placeholder test `test_mission_type_nodes_have_no_incident_edges` (`tests/doctrine/drg/test_mission_type_nodes.py:87-99`) is **re-pinned** to assert the new `requires` edges exist (invert the "no edges" assertion), not deleted — **including** correcting the now-stale class/method docstrings ("Nodes-only in WP01" / "no edges are emitted"). | Draft |
| FR-005 | The `models.py:46` comment ("nodes only, no edges yet") is corrected to reflect that mission_type nodes now carry `requires` edges to their actions; the obsolete "do not add a `_KIND_MAP` entry until edges exist" caveat (`extractor.py:778`) is reconciled with the `_KIND_MAP` decision (C-007). | Draft |
| FR-006 | The residual doc (`kitty-specs/mission-lifecycle-dispatch-drg-closeout-01KV0S99/drg-orphan-residual.md`) is **reconciled with the empirical residual**: its stale "Residual orphans (14)" snapshot lists 14 rows, **none of which are the 8 mission_type/plan-action orphans** this mission wires (they post-date the doc). Reconcile the doc so the recorded residual matches the empirical **10** after this mission wires its 8 — i.e. the 8 wired nodes never enter the table, and the ~4 already-stale non-orphan rows are corrected/removed. This is an ADD-and-reconcile edit, **not** an edit of existing mission-type rows (there are none). Coordinate the stale-row corrections with #1923 (C-003). | Draft |

### Functional Requirements — Phase 2: Graph Sharding (#2680)

| ID | Requirement | Status |
|----|-------------|--------|
| FR-007 | The DRG generator writes the shipped graph as **deterministic per-kind `*.graph.yaml` fragments at `src/doctrine/`** (partition: one fragment **per populated node-kind**; each fragment owns a disjoint node set + the edges whose **source** node is that kind), replacing the single `src/doctrine/graph.yaml`. Fragment location is pinned at `src/doctrine/*.graph.yaml` (== the loader glob root); assignment and intra-fragment ordering are stable across runs. | Draft |
| FR-008 | **A canonical built-in-graph seam is introduced FIRST** (e.g. `load_built_in_graph() -> DRGGraph` in `src/doctrine/drg/loader.py`, wrapping `load_graph_or_dir(resolve_doctrine_root())`), and **every** shipped-graph reader is routed through it — replacing the bespoke single-file path-builders. The audited src readers are: `agent_profiles/repository.py` (`_default_drg_path` at ~:270-278 + `:289`), `specify_cli/doctrine/pack_validator.py:513`, `specify_cli/calibration/walker.py:430-437` (`_built_in_graph_path`), `specify_cli/charter_runtime/lint/_drg.py:52,85`. Already-safe `load_graph_or_dir` consumers (`_drg_helpers.py`, `compiler.py`, `reference_resolver.py`, `_status_collectors.py`, `_doctrine_collect.py`, `_profile_health_render.py`) route through the seam too. **Org-pack fragment readers** (`pack_assembler.py:209`, `pack_validator.py:527/:977`) are OUT — they read `pack/drg/*.graph.yaml`, not the built-in graph. | Draft |
| FR-009 | The **~16 test modules** that reconstruct the monolith path are migrated to a single shared fixture over the seam (no per-module `.../graph.yaml` path constant). Inventory: `tests/doctrine/conftest.py` (`SHIPPED_GRAPH_PATH`), `test_service.py`, `test_debugger_debbie_artifacts.py`, `test_paula_patterns_artifacts.py`, `test_mattpocock_skill_doctrine.py`, `test_relationship_migration.py`, `test_directive_consistency.py`, `test_template_asset_e2e.py`, `drg/test_resolve_transitive_refs.py`, `drg/test_tiered_standards_non_orphan.py`, `drg/test_glossary_node_kind.py`, `drg/test_shipped_graph_valid.py`, `drg/test_cross_grain_integrity.py`, `charter/test_surface_calibration.py`, `charter/test_model_task_routing_resolves.py`, `charter/test_merged_graph_on_live_path.py`. **Critically** `tests/specify_cli/cli/commands/test_doctrine_regenerate_graph.py` — its `_count_orphans` (`:47`) reads the monolith directly and IS the orphan gate; it must read the sharded layout so the gate (green at 10 from Phase 1) **stays green**. | Draft |
| FR-010 | **Partition-totality**: the generator emits a fragment for **every populated node-kind** — including target-only kinds that own nodes but no source edges (`template`, `asset`, `glossary`, `glossary_scope`, `mission_step_contract`, and pre-existing `mission_type` before Phase 1). A test asserts every node-kind round-trips (no target-only-node loss); node/edge counts of the merged graph equal the pre-sharding graph exactly. | Draft |
| FR-011 | **Ordering-determinism / equality contract**: because `merge_layers` concatenates fragments in alphabetical load order while the monolith is globally sorted by `(source,target,relation)`, the equality proof (SC-S1) and the freshness gate must have an explicit, stable contract — either the merged graph is re-sorted to the canonical order before comparison, or each fragment is independently canonically sorted and the freshness gate is byte-identity **per fragment**. The chosen contract is documented in the design-decisions tracer. | Draft |
| FR-012 | `spec-kitty doctrine regenerate-graph` (+ `--check`) and the freshness gate (`test_regenerate_twice_is_byte_identical`, `test_check_reports_committed_graph_fresh`) write/verify the **sharded** layout, and the write step **deletes the old `src/doctrine/graph.yaml` atomically** in the same change (loader-precedence trap). A test asserts "fragments present ∧ monolith absent". | Draft |
| FR-013 | **Behavior-preserving output proof (silent-degrade guard)**: tests assert that profile `specializes_from` lineage resolution, charter lint's built-in DRG `GraphState`, and pack-validator's built-in URN set are **identical** before/after sharding — not merely that the merged `DRGGraph` is equal. This guards the three `DRGLoadError`-swallowing readers. | Draft |
| FR-014 | `snapshot.py`'s filename-keyed doctrine categorization (`snapshot.py:62` maps exact `"graph.yaml"` → `drg_fragments`; `:200` maps the `drg/` dir) is reviewed and updated so `src/doctrine/*.graph.yaml` fragments categorize correctly. | Draft |
| FR-015 | No in-YAML `import:`/`!include` directive is introduced; sharding uses only the existing directory-of-fragments + `merge_layers` primitive. | Draft |
| FR-016 | Load-bearing **docstrings** (code prose) that assert "edges live in `src/doctrine/graph.yaml`" (the `models.py` families: `directives/`, `procedures/`, `tactics/`, `paradigms/`, `styleguides/`, `agent_profiles/` incl. `schema_models.py` + `profile.py`; plus `shared/exceptions.py`, `shared/errors.py`, `directives/common_docs.py`) are updated to the sharded layout. **Excludes** the *runtime* `build_migration_hint` emitted string (pinned by ~10 tests — deferred per DD-13) and non-shipped docs-tree `.md` references (both tracked follow-ups). Docstring edits must not alter any string a test asserts. | Draft |

### Non-Functional Requirements

| ID | Requirement | Threshold / Measure | Status |
|----|-------------|---------------------|--------|
| NFR-001 | The new edges introduce no dangling targets, no `requires` cycles, no duplicate edges. | `src/doctrine/drg/validator.py` `assert_valid` passes on the regenerated graph (both phases). | Draft |
| NFR-002 | Deterministic, stable regeneration. | Two regenerations are byte-identical (monolith in Phase 1; sharded layout in Phase 2); edge ordering follows the existing URN / `(source,target,relation)` sort. | Draft |
| NFR-003 | ruff + mypy --strict clean, zero new suppressions; complexity ≤ 15; new branch/helper gets a focused test. | `ruff check src tests` + `mypy --strict` clean on touched files. | Draft |
| NFR-004 | Phase 2 introduces no import-time filesystem I/O beyond what the current monolith read already does. | The seam is called at the same call-time points as today's readers (lazy/function-local where the current site is). | Draft |

### Constraints

| ID | Constraint | Status |
|----|------------|--------|
| C-S1 | **Phase 1 before Phase 2 (reversed from the original plan).** The mission-type edges land first against the **monolith** and clear the red orphan gate (18 → 10). Sharding (Phase 2) is behavior-preserving reshaping of the now-edge-complete graph, and must keep every gate green as it re-points readers. Rationale + squad evidence in DD-0. | Draft |
| C-S2 | **The canonical seam is imposed BEFORE any consumer is switched** (FR-008). Sharding without the seam is a whack-a-field edit across ~22 sites; with it, each reader changes once and future graph changes route through one accessor. | Draft |
| C-S3 | Phase 2 is **behavior-preserving**: no node/edge content change, no validation-result change — only the on-disk fragment layout + the load path. The proof asserts BOTH merged-graph set-equality (FR-010) AND the three silent-degrade surfaces' outputs (FR-013). | Draft |
| C-S4 | **Deterministic sharding** — stable node/edge→fragment assignment + stable intra-fragment ordering with an explicit merge-order equality contract (FR-011), or the byte-identity freshness gate false-fails. No in-YAML `import:`/`!include` (FR-015). | Draft |
| C-S5 | **Atomic monolith retirement** — the `graph.yaml` delete and the fragment writes land in the same commit; fragment dir == loader glob root (`src/doctrine/`). The loader-precedence trap (`loader.py:93`) makes a non-atomic cutover a silent stale-read (FR-012). | Draft |
| C-001 | Only the `mission_type → action` edge class is in scope. `mission_type → {WP templates, assets, guards}` and minting `mission_step_contract`/`asset`/`GUARD` node populations are **out of scope** (future slices; they touch no orphan). | Draft |
| C-002 | Do NOT raise `DOCUMENTED_ORPHAN_RESIDUAL` (14). #2677 is "wire, don't raise"; the fix must bring the count under the existing ceiling. | Draft |
| C-003 | This mission wires the 8 mission-type/plan-action orphans; #1923 curates the *other* **10** valid standalones. FR-006 reconciles `drg-orphan-residual.md`, which #1923 also owns — the plan MUST decide sequencing/ownership of that shared doc to avoid a merge collision (do not touch the 10 standalone rows; only correct the ~4 stale non-orphan rows + record the 8 wired). | Draft |
| C-004 | Relation choice: use `requires` (composition-of-mandatory-ordered-parts; cascade-aligned) rather than `instantiates`. Record the decision in the design-decisions tracer if the reviewer prefers otherwise. | Draft |
| C-005 | ATDD red-first: the failing edge/orphan assertion is committed first through the pre-existing extractor/graph entry point (Phase 1); the failing sharding-equality/silent-degrade assertions are committed first (Phase 2). | Draft |
| C-006 | Ground the edge semantics in the #883 brief + mission-type-resolution ADR — do not improvise a novel relation. | Draft |
| C-007 | The plan MUST decide whether to add a `"mission_type"` entry to `_KIND_MAP` (`extractor.py:122-131`). Harmless today (mission_type nodes are pre-created in Step 4b, so the backfill loop never fires for these edges), but the generate-graph backfill silently drops edge endpoints missing from `_KIND_MAP` — adding the entry is safer against future partial-node states. | Draft |
| C-008 | Regenerating may **reweight existing edges** via `calibrate_surfaces` (the new edges enter `all_edges` before calibration). Expect a `graph.yaml` diff possibly wider than the 21 new lines in Phase 1 — this is expected (freshness satisfied by regenerate+commit; validator still passes), NOT a bug. Note: because calibration is a **global** reweight, its diff is NOT localized by sharding (a claim the original fold made and the squad refuted). | Draft |

---

## Success Criteria

| ID | Criterion |
|----|-----------|
| SC-001 | Regenerating the DRG yields `mission_type:X → action:X/<step>` `requires` edges for every step in each type's `action_sequence` (**21 total** = software-dev 5 + documentation 7 + research 5 + plan 4); focused tests assert `mission_type:plan` emits exactly its 4 plan edges **and** a non-plan type (e.g. `mission_type:documentation`) emits its full 7-edge sequence — so FR-001's "every built-in mission type" is directly witnessed. |
| SC-002 | The shipped-graph orphan count is 10 (≤ 14) and `test_shipped_graph_orphan_count_within_documented_residual` is green **without** raising the ceiling — after Phase 1 (monolith) AND still after Phase 2 (sharded). |
| SC-003 | `assert_valid` passes (no dangling / cycle / duplicate); regeneration is byte-identical (monolith Phase 1; sharded layout Phase 2). |
| SC-004 | The charter cascade for a mission type traverses the new edges (previously a no-op). |
| SC-S1 | After Phase 2, the shipped graph is `src/doctrine/*.graph.yaml` fragments (one per populated node-kind), the monolith is deleted, all consumers load via the built-in-graph seam, and a test proves the merged graph is **equal** to the pre-sharding graph (node/edge sets, `assert_valid`) under the FR-011 ordering contract. A single-kind change regenerates only that kind's fragment. |
| SC-S2 | `regenerate-graph --check` reports the sharded layout fresh; "fragments present ∧ monolith absent" holds; no in-YAML import directive exists. |
| SC-S3 | Profile lineage, charter-lint DRG state, and pack-validator built-in URN set are byte-for-byte identical before/after sharding (silent-degrade guard, FR-013). |
| SC-005 | `ruff check src tests` + `mypy --strict` clean; the arch/DRG gates green on the mission branch. |

---

## Key Entities

- **`extract_mission_type_edges`** (new, `src/doctrine/drg/migration/extractor.py`) — the Phase-1 edge-emit
  pass, a sibling of the existing `_discover_mission_type_nodes` (`extractor.py:768`); reads each type's
  `action_sequence` and emits the `requires` edges into `all_edges` before calibration/sort.
- **`load_built_in_graph()` / `built_in_graph_source()`** (new, `src/doctrine/drg/loader.py`) — the Phase-2
  canonical seam wrapping `load_graph_or_dir(resolve_doctrine_root())`; the single accessor every consumer
  routes through.
- **`src/doctrine/graph.yaml` → `src/doctrine/*.graph.yaml`** — the generated artefact, regenerated + committed
  (monolith in Phase 1; per-kind fragments in Phase 2, monolith deleted).
- **`Relation.REQUIRES`** / **`NodeKind.{MISSION_TYPE,ACTION}`** (`src/doctrine/drg/models.py`) — existing.
- **`test_mission_type_nodes.py`** — the S0 placeholder test, re-pinned (Phase 1).
- **`test_doctrine_regenerate_graph.py`** — orphan-ceiling + freshness gates; `_count_orphans` re-pointed at
  the sharded layout in Phase 2.

---

## Assumptions

- `action_sequence` in each `mission_types/<id>.yaml` is the authoritative step list, and every step has a
  matching `actions/<step>/` index dir (verified on current main).
- `requires` is the correct relation (cascade-aligned); reviewer may adjust to `instantiates` with rationale.
- The concurrent-mission `graph.yaml` merge-conflict class is real (47 commits touched it; ~20 live branches
  carry a diff) — the sharding cutover itself will collide with open doctrine branches, so it lands early in
  its own phase and is socialized.

---

## Out of Scope (tracked future slices)

- `mission_type → WP template` edges + minting `template:` nodes for the mission-dir templates (`template_set`
  slot; #883 template deferral).
- `mission_type → asset` edges + an asset offer surface (no asset nodes exist).
- `mission_type → guard` edges + a new `GUARD` NodeKind (gates-as-DRG-artefacts).
- `mission_step_contract` node population (steps are already covered by action nodes).
- The #1923 curation of the other **10** valid residual orphans.
- The *runtime* `build_migration_hint` text update (`shared/errors.py`/`exceptions.py`) + its ~10 pinning
  tests — deferred per DD-13 (cosmetic staleness; the `src/doctrine/` dir it names still exists). A cohesive
  follow-up to file after this mission merges.
- The ~14 non-shipped docs-tree `.md` references to a monolithic `graph.yaml` (mechanical; follow-up).

---

## Dependencies

- Builds on #2651 (the mission_type/action nodes it wires). No dependency on #2657/#2659 (different subsystem).
- ADR authority: `2026-07-15-1` (S0), `2026-07-14-2`, `883-mission-type-authority-brief.md`.
