# Contract — Profile-Channel `suggests` Delivery Walk

**Owning concerns**: IC-01, IC-02 · **Requirements**: FR-001/002/003, FR-006, NFR-003 · **Layer split**:
doctrine walk stays node-level; `when` surfaced in the charter/consumer layer (D1).

## C1 — Relation set

`PROFILE_CHANNEL_RELATIONS` (`src/doctrine/drg/reachability.py`) MUST include `Relation.SUGGESTS` in
addition to `REQUIRES` and `SPECIALIZES_FROM`. The action channel (`action_channel_reachable`/
`resolve_context`) is a SEPARATE walk and MUST remain unaffected.

## C2 — `when` surfacing (reuse `link_references`, do NOT re-derive)

For every artefact delivered because it was reached via a `suggests` edge, the consumer MUST surface an
applicability condition equal to that edge's `when` clause; when the edge has no authored `when`, surface
`STATED_DEFAULT_WHEN` (never empty/undefined).

**Seam (D11 — critical):** `when` lives on the edge that *reaches* the artefact (an **inbound** edge
`source → target`), and `profile_channel_reachable` returns `visited − seed_set` — it **strips the profile
seeds**, which are exactly the sources of the first-hop Family A/B edges (architect→DDD,
profile→DISCIPLINED_REFACTORING). Therefore a per-reached-node `edges_from(reached, SUGGESTS)` MISSES those
edges and surfaces no `when` for the headline families. The consumer MUST instead reuse the existing
`link_references(merged, roots=profile_seeds, delivered=<kind-filtered reached set>, bridge_urns=reached ∪
seeds)` projection (`progressive_disclosure.py:110-154` + `edge_to_reference` at :52-68), which iterates
`sources = roots ∪ delivered ∪ bridge_urns` and keeps `(target, when)` where `target ∈ delivered`. Note
`reached ∪ seeds == visited`, so **no second walk is needed** — the consumer already holds the seeds it
passed in. Do NOT author a bespoke projection or a `reachability_delivery/` copy of `link_references`.

## C3 — Delivery cadence (links, not bodies)

Suggested artefacts MUST be delivered as `when`-labelled REFERENCES (links) — the "fetch + when-doing"
stanza — not as inlined full bodies. Artefacts inside the roots' `requires`-closure keep their eager full
body (existing cadence); `suggests`-only artefacts render as links. `requires` precedence wins on a
diamond (an artefact reachable via both `requires` and `suggests` delivers eager, once). Delivery MUST
build on `_ActionDoctrineBundle.bridge_urns` + the requires-closure render cadence (C-003), not re-derive.

## C4 — Kind delivery

Following `suggests` reaches non-procedure kinds (paradigm/styleguide/directive/tactic/toolguide). The
consumer's NodeKind delivery table (`context.py`) decides which kinds deliver; the sole existing consumer
`profile_channel_procedure_ids` (procedures-only) MUST be widened accordingly (OQ-3 resolved in IC-01).

## C5 — Dedup & determinism

`(target, relation)` pairs dedup across multiple source profiles / diamonds; delivered reference lists are
deterministically ordered (stable sort by URN), matching the existing payload determinism.

## C6 — Forward-API consumption (allowlist retirement)

Each forward-API symbol used to implement this walk becomes genuinely `src`-imported-and-used. As each is
consumed it is removed from `_CATEGORY_C_DELIVERY_RAIL_FORWARD_API` + its `_baselines.yaml` mirror (final
sweep in IC-05); `test_no_dead_symbols` stays green. A symbol referenced ONLY in tests is NOT removed.

## Acceptance (ATDD — assert on the PROFILE channel, D10)

**Entry point MUST be `profile_channel_reachable(graph, {agent_profile:…})` + the profile render path
(`_render_profile_sections`/`profile_channel_procedure_ids`). `doctrine.drg.query.resolve_context` (the
ACTION channel) is FORBIDDEN as the entry point — DDD is already action-reachable there (vacuously green)
and `resolve_context` from a profile seed reaches nothing (`test_reachability.py:720`, permanently red).**

- **A0 (mechanical red)**: `test_reachability.py:710 test_profile_relations_are_requires_and_specializes_from`
  is the guaranteed walk-level red — it pins the relation set that FR-001 widens.
- **A1**: `profile_channel_reachable(graph, {agent_profile:architect-alphonso})` includes
  `paradigm:domain-driven-design` (Family A) and the render surfaces its `when` (RED today — edge A12 inert).
- **A2**: an implementer profile's channel includes the `refactoring-*` tactics (Family B) with `when`.
- **A3**: a `suggests` edge with no authored `when` surfaces `STATED_DEFAULT_WHEN` (Family A after backfill
  is authored; assert on a still-`when`-less edge to prove the default path).
- **A4**: a diamond artefact (reachable via `requires` AND `suggests`) is delivered once, eager (requires
  precedence collapses it — `target ∈ delivered` filter + partition_delivery split).
- **A5**: suggested artefacts appear as references (links), not inlined bodies (NFR-003).
- **A6**: the action channel's delivered set (`resolve_context`) is unchanged by this WP (isolation).
