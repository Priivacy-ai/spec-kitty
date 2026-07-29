---
title: "Delivery-reachability wiring table (FR-015)"
description: "One row per candidate artefact: its proposed inbound source, that source's MEASURED action-reachability (via WP08's helper), and the wire/defer disposition under C-007. The deferred set is the operator's decision surface."
doc_status: active
updated: '2026-07-29'
related:
  - kitty-specs/doctrine-delivery-reachability-01KYMXD6/spec.md
  - kitty-specs/doctrine-delivery-reachability-01KYMXD6/contracts/activation-delivery.md
  - kitty-specs/doctrine-delivery-reachability-01KYMXD6/tasks/WP09-wiring-edges.md
---

# Delivery-reachability wiring table (FR-015, WP09)

This is the enumerated wiring table FR-015 requires. Its purpose is to make
"obvious" a **computation** rather than a judgement, so this work package does
not reproduce PR #3007's failure — 4 edges authored to sources that were
themselves unreachable, so the wired artefacts still reached nobody.

## The disposition rule (C-007, operator ruling 2026-07-28)

An unreachable **activated** artefact is *obvious* (in scope to wire now) **iff**:

- **(a)** the relationship is **attested in the artefact's own text** — not
  inferred from topic adjacency — **and**
- **(b)** the proposed inbound source is **itself action-reachable** under the
  WP08 measure, **or** the edge is a `scope` edge from an **action** node.

Everything failing **(b)** is **deferred** to an after-mission operator
interview. `wire` = passes (a)+(b); `defer` = fails (b).

## How every reachability value here was measured (R-1)

Reachability is **measured, never eyeballed**. Every `source action-reachable?`
value below is the result of *calling* WP08's helper
`doctrine.drg.reachability.action_channel_reachable`, which itself *calls*
`doctrine.drg.query.resolve_context` (the single canonical walk) once per action
seed and unions the result. No BFS was reimplemented — R-1 forbids it, and every
hand-rolled walk in this mission's history produced a wrong number.

Baseline, shipped built-in graph before this WP:

| measure | value |
|---|---|
| nodes / edges | 310 / 781 |
| action-reachable artefacts, `d=1` (compact) | 111 |
| action-reachable artefacts, `d=2` (bootstrap) | 118 |
| resolved activated artefacts (node form) | 184 |
| activated **and** action-unreachable at `d=2` | 78 |

## The wiring table

`source action-reachable?` is the **measured** value for the *proposed source*
(the value C-007(b) turns on). For a `scope`-from-action row the source is an
`action` node, which is the reachability seed itself — C-007(b)'s second clause.

| # | candidate artefact | proposed inbound source | source action-reachable? (measured) | disposition |
|---|---|---|---|---|
| 1 | `directive:DIRECTIVE_042` | `action:documentation/generate` (`scope`) | **n/a — action seed** (C-007b clause 2) | **wire** |
| 2 | `asset:common-docs-structural-lint` | `directive:DIRECTIVE_042` (`requires`, already present) | **False → True after row 1 lands** | **wire (transitive)** |
| 3 | `styleguide:common-docs` | `directive:DIRECTIVE_042` (`suggests`, already present) | **False → True after row 1 lands** | **wire (transitive)** |
| 4 | `tactic:common-docs-curation` | `directive:DIRECTIVE_042` (`suggests`, already present) | **False → True after row 1 lands** | **wire (transitive)** |
| 5 | `tactic:common-docs-find` | `directive:DIRECTIVE_042` (`suggests`, already present) | **False → True after row 1 lands** | **wire (transitive)** |
| 6 | `tactic:common-docs-scaffold` | `directive:DIRECTIVE_042` (`suggests`, already present) | **False → True after row 1 lands** | **wire (transitive)** |
| 7 | `tactic:common-docs-write` | `directive:DIRECTIVE_042` (`suggests`, already present) | **False → True after row 1 lands** | **wire (transitive)** |
| 8 | `paradigm:atomic-design` | `tactic:atomic-design-review-checklist` (`suggests`, already present from PR #3007) | **False** | **defer** |
| 9 | `styleguide:reasons-canvas-writing` | `paradigm:structured-prompt-driven-development` (`suggests`, already present from PR #3007) | **False** | **defer** |
| 10 | `tactic:occurrence-classification-workflow` | `directive:DIRECTIVE_035` (`requires`, already present from PR #3007) | **False** (DIRECTIVE_035 has no reaching inbound edge) | **defer** |

Rows 8–10 are the re-adjudication of PR #3007's three still-inert wirings: each
already carries an inbound edge, but its source is itself action-unreachable
(measured **False**), so the target reaches nobody. That is precisely the
incidence-vs-reachability gap this mission exists to close — an inbound edge is
**not** reachability (R-6). They are **not** re-wired (that would repeat the
#3007 error); they are recorded here and deferred.

### Why only ONE edge is authored

Row 1 (`action:documentation/generate --scope--> directive:DIRECTIVE_042`) is
the only **new** edge. DIRECTIVE_042 already carries `requires`/`suggests` edges
to the asset, the styleguide and the four common-docs tactics; making 042 itself
action-reachable delivers all six transitively (rows 2–7). Measured after the
edge lands: `d=1` and `d=2` action-reachable each grow by exactly **7**
(111→118, 118→125), the seven artefacts in rows 1–7. Minimal edge, maximal
delivery (avoid gold-plating / locality-of-change).

## The `common-docs` cluster (T050) — wired

`asset:common-docs-structural-lint` is the first shipped doctrine ASSET
(WP10/WP11 of the delivery rail ship assets). It has four inbound `requires`
edges, from DIRECTIVE_042, `styleguide:common-docs`, `tactic:common-docs-curation`
and `tactic:common-docs-scaffold` — and **all four sources were measured
unreachable**. The whole documentation-authoring family (042, the common-docs
styleguide, the common-docs `find`/`write`/`curation`/`scaffold` tactics, and the
docs styleguides `divio-type-discipline` / `docs-accessibility` /
`docs-freshness-sla` / `plain-language` / `publication-authority`) is a
strongly-connected **island**: every edge pointing into it originates **inside**
it, and **no `action` node scopes any member** (measured — the documentation
step contracts scope DIRECTIVE_010/037/003/001/018 and a handful of tactics,
never 042 or common-docs).

C-007(b) offers two ways in. Both were tested against the graph, not guessed:

1. **Edge from an action-reachable source** — measured **impossible**. Every
   artefact that even *mentions* common-docs / the structural lint / DIRECTIVE_042
   in its own text is itself action-unreachable (the cluster members plus the
   five docs styleguides). No reachable directive, tactic or procedure attests a
   relationship into the cluster, so any such edge would be topic-adjacency — the
   exact C-007(a) violation, and the #3007 failure mode.
2. **A `scope` edge from an action node** — **available and attested.**
   DIRECTIVE_042's own `scope:` text reads *"Applies whenever a documentation
   file under the Common Docs root is created, moved, renamed…"*. The
   `documentation/generate` action's `write_docs` step writes `docs/**/*.md`
   under the mission — i.e. it **creates documentation files**, exactly 042's
   stated trigger. The relationship is therefore attested in 042's own text
   (C-007a), and the source is an action node (C-007b clause 2). This is a
   recorded relationship, **not an invented one** — so the "defer instead of
   invent" guard does not fire.

**Disposition: WIRE**, via row 1.

## B2 handoff — the scope edge's canonical home

The edge lands in `HAND_AUTHORED_EDGES`
(`src/doctrine/drg/migration/hand_authored_overlay.py`), because that is where
WP09's wiring edges land per the contract and the WP prompt. The **canonical**
home for an action→artefact `scope` edge is the documentation mission **step
contract action index** — `src/doctrine/missions/built_in_step_contracts/documentation-generate.step-contract.yaml`
would list `042-common-docs` as a `delegates_to` candidate, and the extractor
would mint the scope edge from it. That surface is **outside WP09's owned
files**, so WP09 authors the reaching edge in the overlay and records the
migration here.

**Mission B2 (`drg-edge-migration-extractor-retirement-01KYFV8C`) retires the
overlay generator.** When it does, it must **not** silently drop this edge: it
migrates `action:documentation/generate --scope--> directive:DIRECTIVE_042` into
the documentation step-contract action index (and may, per 042's full scope
text, additionally scope 042 in `documentation/design`, `/publish`, `/validate`
and `/accept` — WP09 authored only the single minimal edge needed for
reachability). This is a **known** migration, inherited deliberately, not a
surprise.

## The deferred set (T052) — the operator's decision surface

These **72** activated artefacts remain action-unreachable at `d=2` after row 1
lands. Each fails C-007(b): no action-reachable source with a textually-attested
relationship, and no `scope`-from-action path whose relationship is attested
without invention. **This is not a filed issue** — it is the surface the
after-mission operator interview rules on (C-007). Wiring any of these now would
mean either wiring to an unreachable source (#3007's error) or inventing a
relationship (the guard T050 forbids).

### Note: 10 of the 72 are edge-incident from a reachable source, depth-gated

The following already carry an inbound edge **from an action-reachable source**,
but the edge is `suggests` (or a `requires` chain) that sits **beyond the
traversal depth horizon**, so `resolve_context` does not reach them at `d=2`.
They are **not orphans** and are **not** wiring candidates: the relationship
already exists as an edge; "fixing" them would mean upgrading `suggests`→`requires`
(claiming a hard dependency the text does not attest) or deepening the bootstrap
walk — both are traversal-policy decisions for the operator, not edge authoring.

| artefact | reachable inbound source (relation) |
|---|---|
| `directive:DIRECTIVE_032` | `tactic:paula-patterns-architecture-scout-review` (suggests) |
| `procedure:example-mapping-workshop` | `procedure:bdd-scenario-lifecycle` (requires) |
| `tactic:anti-corruption-layer` | `tactic:paula-patterns-architecture-scout-review` (suggests) |
| `tactic:bounded-context-identification` | `tactic:strategic-domain-classification` (suggests) |
| `tactic:context-mapping-classification` | `tactic:strategic-domain-classification` (suggests) |
| `tactic:domain-event-capture` | `tactic:paula-patterns-architecture-scout-review` (suggests) |
| `tactic:ownership-map-leeway` | `styleguide:planning-and-tracking` (suggests) |
| `tactic:pr-agent-worktree-isolation` | `directive:DIRECTIVE_043` (suggests) |
| `tactic:zombies-tdd` | `tactic:delete-the-assertion-not-the-test` (suggests) |
| `toolguide:github-tracker` | `styleguide:planning-and-tracking` (suggests) |

### Full deferred set (72), by kind — directive 6 · paradigm 5 · procedure 5 · styleguide 5 · tactic 43 · toolguide 8

  - `directive:DIRECTIVE_031`
  - `directive:DIRECTIVE_032`
  - `directive:DIRECTIVE_035`
  - `directive:DIRECTIVE_038`
  - `directive:DIRECTIVE_039`
  - `directive:DIRECTIVE_044`
  - `paradigm:atomic-design`
  - `paradigm:c4-incremental-detail-modeling`
  - `paradigm:domain-driven-design`
  - `paradigm:specification-by-example`
  - `paradigm:structured-prompt-driven-development`
  - `procedure:documentation-gap-prioritization`
  - `procedure:drill-down-documentation`
  - `procedure:event-storming-discovery`
  - `procedure:example-mapping-workshop`
  - `procedure:migrate-project-guidance-to-spec-kitty-charter`
  - `styleguide:aggregate-design-rules`
  - `styleguide:deployable-skill-authoring`
  - `styleguide:java-conventions`
  - `styleguide:mutation-aware-test-design`
  - `styleguide:reasons-canvas-writing`
  - `tactic:adversarial-qa-handoff`
  - `tactic:aggregate-boundary-design`
  - `tactic:analysis-extract-before-interpret`
  - `tactic:anti-corruption-layer`
  - `tactic:architecture-diagram-review-checklist`
  - `tactic:atdd-adversarial-acceptance`
  - `tactic:atomic-design-review-checklist`
  - `tactic:atomic-state-ownership`
  - `tactic:bounded-context-canvas-fill`
  - `tactic:bounded-context-identification`
  - `tactic:c4-zoom-in-architecture-documentation`
  - `tactic:canonical-source-unification`
  - `tactic:chain-of-responsibility-rule-pipeline`
  - `tactic:code-documentation-analysis`
  - `tactic:compositional-stream-boundaries`
  - `tactic:context-boundary-inference`
  - `tactic:context-mapping-classification`
  - `tactic:cross-cutting-state-via-store`
  - `tactic:development-bdd`
  - `tactic:domain-event-capture`
  - `tactic:entity-value-object-classification`
  - `tactic:formalized-constraint-testing`
  - `tactic:mutation-testing-workflow`
  - `tactic:occurrence-classification-workflow`
  - `tactic:ownership-map-leeway`
  - `tactic:pr-agent-worktree-isolation`
  - `tactic:reasons-canvas-fill`
  - `tactic:reasons-canvas-review`
  - `tactic:refactoring-encapsulate-record`
  - `tactic:refactoring-encapsulate-variable`
  - `tactic:refactoring-extract-first-order-concept`
  - `tactic:refactoring-move-field`
  - `tactic:refactoring-move-method`
  - `tactic:refactoring-state-pattern-for-behavior`
  - `tactic:refactoring-strangler-fig`
  - `tactic:reference-architectural-patterns`
  - `tactic:reverse-speccing`
  - `tactic:secure-regex-catastrophic-backtracking`
  - `tactic:terminology-extraction-mapping`
  - `tactic:test-readability-clarity-check`
  - `tactic:test-to-system-reconstruction`
  - `tactic:work-package-completion-validation`
  - `tactic:zombies-tdd`
  - `toolguide:contextive`
  - `toolguide:github-tracker`
  - `toolguide:maven-review-checks`
  - `toolguide:mermaid-diagramming`
  - `toolguide:plantuml-diagramming`
  - `toolguide:python-mutation-tools`
  - `toolguide:terminology-guard`
  - `toolguide:typescript-mutation-tools`

## Composition ledger (NFR-004) — counts this WP moves

The single authored edge moves these counts. Each is recorded so no golden
number moves silently.

- **Shipped-graph edges 781 → 782** (+1). `len(HAND_AUTHORED_EDGES)` 17 → 18. The
  pure-extraction golden counts (`_EXPECTED_NODE_COUNT=304`, `_EXPECTED_EDGE_COUNT=764`)
  are **unchanged** — the edge is overlay-authored, not extractor-derived — so
  `test_extractor_projection`'s byte-identical assertion (`… == _EXPECTED_EDGE_COUNT + len(HAND_AUTHORED_EDGES)`)
  stays green by construction once the fragments are regenerated. Ledger entry (8)
  is added to that module's composition ledger.
- **`scope`-relation histogram 157 → 158.** `RELATION_DESCRIPTIONS[Relation.SCOPE]`
  (`doctrine.drg.models`) and its char-for-char mirror in
  `docs/architecture/doctrine-relationships.md` state "(157 edges)"; both move to
  "(158 edges)". This count **is** gated —
  `tests/architectural/test_no_authored_applies_edge.py::TestPositiveCountClaimsAreTrue`
  parses the claim and asserts it against the live graph — so the prose is a
  contract, updated here, not left to drift.
- **`_ACTION_UNREACHABLE_D1` and `_ACTION_UNREACHABLE_D2`** (WP08,
  `tests/doctrine/drg/test_reachability.py`) each **lose the same 6 members**:
  `directive:DIRECTIVE_042`, `styleguide:common-docs`,
  `tactic:common-docs-curation`, `tactic:common-docs-find`,
  `tactic:common-docs-scaffold`, `tactic:common-docs-write`. The `d1↔d2` spread
  stays 7 (same members removed from both); `_PROFILE_UNREACHABLE` and
  `_PROFILE_RESCUES` are unaffected (the profile channel is unchanged, and the 6
  are profile-unreachable too). Orphan sets are unaffected (042 and the asset were
  already edge-incident). Ledgered in that module's docstring.
