# Research — Mission-Type DRG Edges + Graph Sharding

Design resolved by **three** squad passes: pre-spec (architect-alphonso), post-spec (reviewer-renata +
paula-patterns) on the edges, and — after graph sharding (#2680) was bundled in — a **post-plan investigation
squad** (architect-alphonso + paula-patterns + reviewer-renata) on the two-phase mission. Grounded in
`docs/notes/mission-type-completion-arc-research.md` §2 and the #883 brief / mission-type-resolution ADR. No
open `[NEEDS CLARIFICATION]`.

## D-0 — Why sharding is bundled here, and why it runs SECOND (durable rationale, for posterity)

**Operator's governing rationale (verbatim):** *"we need to do it anyway, so I prefer to keep it close to the
change it risks impacting. that gives us the clearest warning/errors."* The DRG graph must be sharded regardless
(the monolithic 129 KB generated `graph.yaml` is a merge-conflict magnet — 47 commits have touched it, ~20 live
branches carry a diff — and the mission-type arc's future slices grow it further). Rather than defer sharding to
a disconnected later mission where the impact link is lost, it rides **next to the mission-type edge change it
most affects**, so any breakage surfaces adjacent to its cause.

**Why edges run first, not sharding (the post-plan squad's correction).** The fold was initially sequenced
sharding-first as a "tidy-first enabler" touching ~1 call-site. The post-plan squad refuted that against the
code and the order was reversed:

| Finding | Evidence | Consequence |
|---------|----------|-------------|
| Blast radius ≈ **22 sites**, not 1 | ~6 src readers (2 hardcode `.../graph.yaml`: `pack_validator.py:513`, `calibration/walker.py:437`; + `charter_runtime/lint/_drg.py`, `agent_profiles/repository.py`) + ~16 test modules; no canonical seam | Sharding is a migration, not a footnote → own phase + a seam (DD-6) |
| Sharding-first breaks the mission's **own gate** | `_count_orphans` (`test_doctrine_regenerate_graph.py:47`) reads the monolith directly | Edges must clear the 18→10 gate against the monolith FIRST; sharding preserves it |
| 3 readers **swallow `DRGLoadError`** | `repository.py` / `pack_validator.py` / `_drg.py` degrade to empty | Naive delete = green tests, silently-lost lineage/lint/validation → output-level proofs (DD-10) |
| Plan **contradicted itself** on fragment location | FR-007 `src/doctrine/` vs plan block `src/doctrine/drg/`; the 6 safe consumers glob `src/doctrine/` | Proof it wasn't code-traced → location pinned (DD-7) |
| "Localizes calibration diff" **refuted** | `calibrate_surfaces` is a *global* reweight | Benefit claim dropped; C-008 diff-width is unavoidable, not a bug |

**Resolution:** keep bundled (proximity rationale), but **Phase 1 = edges (#2677)** against the monolith
(small, verified, clears the red gate), **Phase 2 = sharding (#2680)** as a behavior-preserving migration
gated by a canonical seam + partition-totality + a merge-order equality contract + the three silent-degrade
output proofs. Full decision chain: `traces/design-decisions.md` DD-0, DD-6..DD-10. The edge design itself
(D-1..D-6 below) survived the squad unchanged — 21 edges, residual 10, `requires`, `_KIND_MAP`.

## D-1 — One edge class resolves all 8 orphans

`mission_type:X → action:X/<step>` (`requires`), sourced from `action_sequence`. The 4 `mission_type:*` nodes
gain outbound edges; the 4 `action:plan/*` nodes (orphaned because plan's action indices are all-empty →
no outbound `scope` edge) gain inbound edges. Non-plan action nodes already carry `scope` edges (non-orphan),
so the class touches only the 8. Count 18→10 (≤ ceiling 14). **Verified against the live `graph.yaml`** by both
post-spec agents. Total edges: **21** (software-dev 5 + documentation 7 + research 5 + plan 4).

## D-2 — Relation is `requires` (not `instantiates`)

`requires` = composition-of-mandatory-ordered-parts; it is the relation the **charter cascade** traverses,
so wiring it makes the currently-no-op mission-type cascade meaningful (Scenario 2 / SC-004). Grounded, not
improvised. Reviewer may revisit with rationale.

## D-3 — Dangling / cycle / duplicate safety

`action_sequence ⊆ actions/<step>/` verified for all 4 types (0 dangling). `mission_type → action` cannot
cycle (action nodes never point back to mission_type; only `scope` outbound). Dedup via existing `_ensure`/
`_add_edge`. `assert_valid` passes.

## D-4 — `_KIND_MAP` decision

`_KIND_MAP` (`extractor.py:122-131`) has no `"mission_type"` entry; the generate-graph backfill loop silently
drops endpoints missing from it. Harmless now (mission_type nodes are pre-created in Step 4b), but add the
entry (safer against future partial-node states) + retire the obsolete `:778` caveat.

## D-5 — Calibration diff-width

New edges enter `all_edges` before `calibrate_surfaces`; regeneration may reweight existing edges → a
`graph.yaml` diff wider than 21 lines. Expected, not a bug (freshness satisfied by regenerate+commit;
validator passes).

## D-6 — Boundary (deferred future scope)

`mission_type → {WP templates, assets, guards}` need node populations that don't exist (`template_set` null
for 3/4 types; zero asset nodes; no `GUARD` NodeKind). Deferred per #883; none touch the 8 orphans.
