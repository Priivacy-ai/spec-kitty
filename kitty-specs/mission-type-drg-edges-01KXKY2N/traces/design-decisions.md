# Tracer — Design Decisions

Seeded at planning; append during implement; assess at close.

## DD-0 — Bundle graph sharding (#2680) with the edges, but sequence edges FIRST (operator directive + post-plan squad)

**Governing operator rationale (verbatim):** "we need to do it anyway, so I prefer to keep it close to the
change it risks impacting. that gives us the clearest warning/errors." Sharding is not deferred to a
disconnected future mission — it rides next to the mission-type edge work (the change that grows the graph
and that sharding most affects), so any breakage surfaces adjacent to its cause rather than in an unrelated
later PR where the impact link is lost.

**History of this decision:**
- *First cut (wrong):* sharding folded in as **Phase 1**, ahead of the edges, framed as a "tidy-first
  enabler" touching ~1 call-site.
- *Post-plan investigation squad* (architect-alphonso + paula-patterns + reviewer-renata, all profile-loaded,
  read-only) proved that framing false against the code:
  1. **Blast radius ≈ 22 sites**, not 1: ~6 src readers (3 hard-break, incl. 2 hardcoding `.../graph.yaml`;
     `pack_validator.py:513`, `calibration/walker.py:437`, `charter_runtime/lint/_drg.py`) + ~16 test modules,
     each pinning the monolith path. No canonical seam exists to route them through.
  2. **Sharding-first takes the mission's OWN gate red**: `_count_orphans`
     (`test_doctrine_regenerate_graph.py:47`) reads the monolith directly, so deleting it breaks the exact
     18→10 orphan gate #2677 exists to green.
  3. **Not code-traced**: FR-007 said fragments at `src/doctrine/*.graph.yaml`; the plan's structure block said
     `src/doctrine/drg/*.graph.yaml` — the 6 already-safe consumers glob `src/doctrine/`, so the plan's own
     location would raise `DRGLoadError`.
  4. **Silent-degrade masking**: 3 readers swallow `DRGLoadError` → a naive delete gives green tests with lost
     profile lineage / charter-lint DRG / pack validation.
  5. **Claimed benefit refuted**: `calibrate_surfaces` is a *global* reweight, so sharding does NOT localize
     the C-008 diff (the original fold's stated benefit).
- *Operator decision:* **keep bundled (proximity rationale above), but resequence + rescope.**

**Resolved shape:** **Phase 1 = edges (#2677)** against the monolith → clears the red gate 18→10 (small,
verified, ~2 src + 2 test files, no correctness traps). **Phase 2 = sharding (#2680)** — behavior-preserving
migration of the now-edge-complete graph: impose the canonical seam FIRST (DD-6), switch all ~22 readers,
delete the monolith atomically (DD-7), partition every populated node-kind (DD-8), prove equality under an
explicit merge-order contract (DD-9) AND on the three silent-degrade surfaces' outputs (DD-10), and re-point
`_count_orphans` + the freshness twins at the sharded layout so every gate stays green. **Explicitly NOT** an
in-YAML `import:`/`!include` directive.

## DD-6 — Impose a canonical built-in-graph seam before switching any consumer (paula-patterns)

Add `load_built_in_graph()` / `built_in_graph_source()` in `src/doctrine/drg/loader.py` wrapping
`load_graph_or_dir(resolve_doctrine_root())`. Four bespoke monolith-path builders + ~16 test path constants
route through it. Without the seam, sharding is a whack-a-field edit repeated across ~22 sites; with it, each
reader changes once and future graph-layout changes touch one accessor. Ordering: seam first, then switch.

## DD-7 — Atomic monolith retirement; fragments at `src/doctrine/*.graph.yaml` (architect + paula)

`load_graph_or_dir` PREFERS a `graph.yaml` when present and ignores `*.graph.yaml` fragments (`loader.py:93`).
So Phase 2 MUST delete `src/doctrine/graph.yaml` in the same commit that writes fragments, or every dir-load
silently reads the stale monolith. Fragment dir is pinned at `src/doctrine/` (== the loader glob root the 6
safe consumers already use), NOT `src/doctrine/drg/`. A test asserts "fragments present ∧ monolith absent".

## DD-8 — Partition by SOURCE-node kind, one fragment per POPULATED node-kind (architect)

Edges are assigned to the fragment of their source node's kind; every populated node-kind gets a fragment —
including target-only kinds (`template`, `asset`, `glossary`, `glossary_scope`, `mission_step_contract`) that
own nodes but no source edges. A partition that emits fragments only for kinds-with-edges silently drops
target-only nodes on reload → orphan count + `assert_valid` change → behavior NOT preserved. Totality is a
tested invariant.

## DD-9 — Explicit merge-order equality contract (architect)

The monolith is globally sorted by `(source,target,relation)`; `merge_layers` concatenates fragments in
alphabetical load order. The equality proof and freshness gate need a stable contract: either re-sort the
merged graph to canonical order before comparison, or canonically sort each fragment and make freshness
byte-identity per fragment. Pin the choice in the plan/implement tracer before writing the equality test, so
SC-S1 proves byte-identity rather than accidentally passing on an order-sensitive `__eq__`.

## DD-10 — Behavior-preserving proof asserts on consumer OUTPUTS, not just merged-graph equality (paula)

Three readers swallow `DRGLoadError` and degrade to empty. Merged-graph equality alone can be green while
profile lineage, charter-lint DRG state, or pack-validator URN sets silently regress. The proof asserts those
three surfaces' outputs are identical before/after (FR-013 / SC-S3).

## DD-1 — One edge class (`mission_type → action`, `requires`), not four

## DD-11 — Merge-order equality contract, PINNED (post-task squad, closes DD-9 dangling + vacuous-compare)

The freshness gate and the equality proof use **different, explicitly-pinned** mechanisms (DD-9 left this open;
the post-task squad — priti Gap 3, renata M3/vacuous-compare — required it decided before implement):

- **Freshness gate (WP04/WP05):** each fragment is written in canonical intra-fragment order (nodes by URN,
  edges by `(source,target,relation)`). `regenerate-graph --check` + `test_regenerate_twice_is_byte_identical`
  assert **per-fragment byte-identity**. `_count_orphans` + the freshness twins read via
  `built_in_graph_source()` (the dir), so they are **layout-agnostic** — valid for the monolith (WP04, present)
  and the fragments (WP05, present) with no re-edit.
- **Equality proof (WP06):** the pre-sharding reference is `generate_graph(...)`'s **returned in-memory
  `DRGGraph`** (the composed/calibrated/sorted graph — layout-independent by construction), compared against
  `load_built_in_graph()` reloaded from the fragments. Because `merge_layers` concatenates fragments in file
  order, the merged graph is **canonically re-sorted** before comparing node/edge **sets + counts**. This is
  non-vacuous (never sharded-vs-itself) and robust.

## DD-12 — Red-first lives inside WP01's loop; WP02 is the green-pinning follow-on (renata M5)

C-005 (ATDD red-first) cannot be *observed* across the WP01→WP02 boundary because WP02 `depends: WP01` (its
tests would be green-on-arrival). Resolution: WP01 authors a failing edge assertion, watches it RED, then
implements to GREEN **within its own loop** (its DoD carries the red-first step). WP02 is the comprehensive
green-pinning + re-pin + residual-reconcile follow-on. The misleading "commit RED first (before WP01)" wording
in WP02 is dropped. Red-first discipline is preserved and demonstrable — just inside WP01, not across the seam.

## DD-13 — Runtime migration-hint text update is DEFERRED (scope discipline)

FR-016 is scoped to **docstrings** (code prose asserting "edges live in `src/doctrine/graph.yaml`"), which
edit safely without breaking tests. The **runtime** `build_migration_hint` (`src/doctrine/shared/errors.py`,
`exceptions.py`) also names the monolith path, but ~10 test files pin that emitted string verbatim. Changing
it here would balloon the mission into a ~10-file re-pin unrelated to the edge/shard work. Trade-off accepted:
after sharding, the hint names `src/doctrine/graph.yaml` (a now-absent file, though the `src/doctrine/` dir it
points into still exists — cosmetic staleness, not a correctness break). **Deferred to a tracked follow-up**
(hint text + its pinning tests, as one cohesive change). Recorded in spec Out-of-Scope.

## DD-1 — One edge class (`mission_type → action`, `requires`), not four

The operator's full intent (mission_type → steps/templates/assets/guards) reduces, for the orphan fix, to
`mission_type → action` from `action_sequence`: steps ARE the action nodes; templates/assets/guards need
node populations that don't exist (deferred, #883). Grounded in the #883 brief + mission-type-resolution ADR.

## DD-2 — Relation `requires` (cascade-aligned)

`requires` is what the charter cascade traverses → wiring it makes the mission-type cascade meaningful.
Chosen over `instantiates`. Revisit only with reviewer rationale.

## DD-3 — Add `_KIND_MAP["mission_type"]` (post-spec squad, C-007)

Harmless today (nodes pre-created) but safer against future partial-node states; the generate-graph backfill
silently drops endpoints missing from `_KIND_MAP`. Retire the obsolete `:778` caveat.

## DD-4 — Ceiling stays 14; residual is 10 (post-spec correction)

#2677 is "wire, don't raise." Post-fix the true residual is 10 (the other 10 valid standalones are #1923's).
FR-006 notes this; the 14 ceiling is unchanged headroom. C-003 coordinates with #1923 only on the shared
residual doc (touch only mission-type/plan-action rows).

## DD-5 — Calibration diff-width accepted

Regeneration may reweight existing edges (calibration runs after the new edges join `all_edges`) → a wider
`graph.yaml` diff than the 21 new lines. Expected; freshness + validator still pass.
