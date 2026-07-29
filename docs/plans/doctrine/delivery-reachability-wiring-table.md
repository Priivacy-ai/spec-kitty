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

## Family A (#3063 DDD family) — operator interview outcome, WIRED

The #3063 operator interview ATTESTED the Domain-Driven Design family (C-007(a)
satisfied by operator ruling). Hub: `paradigm:domain-driven-design`. Fourteen
edges land in `HAND_AUTHORED_EDGES`:

| # | source | relation | target | delivers reachability? |
|---|---|---|---|---|
| A1 | `action:software-dev/specify` | **`scope`** | `paradigm:domain-driven-design` | **yes — the reaching edge** |
| A2–A11 | `paradigm:domain-driven-design` | `requires` | the 10 DDD members below | yes, transitively via A1 |
| A12 | `agent_profile:architect-alphonso` | `suggests` | `paradigm:domain-driven-design` | no — composition-only (inert) |
| A13 | `agent_profile:paula-patterns` | `suggests` | `paradigm:domain-driven-design` | no — composition-only (inert) |
| A14 | `agent_profile:randy-reducer` | `suggests` | `paradigm:domain-driven-design` | no — composition-only (inert) |

The 10 `requires` members (A2–A11), each attested as DDD in its **own** text:
`tactic:bounded-context-identification`, `tactic:context-mapping-classification`,
`tactic:context-boundary-inference`, `tactic:bounded-context-canvas-fill`,
`tactic:strategic-domain-classification`, `tactic:aggregate-boundary-design`,
`tactic:entity-value-object-classification`, `tactic:domain-event-capture`,
`tactic:anti-corruption-layer`, `styleguide:aggregate-design-rules`.

### ⚠️ The specify edge is `scope`, NOT `suggests` (relation correction)

The #3063 wiring instruction named the specify→paradigm edge `suggests` **and**
required it to change action reachability + move the pinned unreachable sets.
Those two are contradictory, and the contradiction is resolved by **measurement**
(WP08 helper, R-1): a `suggests` edge whose SOURCE is an `action` node is **inert**
— `resolve_context` walks `suggests` only from scope-resolved artifacts, never
from the action node itself (`query.resolve_context` steps 2/3 seed from
`scoped_artifacts`). Measured: `specify --suggests--> ddd` leaves `d=1`/`d=2`
unchanged (118/125); `specify --scope--> ddd` grows both by 12. Only `scope`
delivers — exactly the WP09 precedent (`documentation/generate --scope--> 042`).
The `§3` mandate ("this edge DOES change action reachability; update the pins")
is satisfiable **only** by `scope`, so the edge is authored as `scope` and the
`suggests` label is corrected here. C-007: (a) DDD's own summary attests aligning
code with a deep domain model — what the software-dev specify step does; (b) the
source is an `action` node (C-007(b) clause 2).

### Attestation audit — what was EXCLUDED as non-attested

- `tactic:reference-architectural-patterns` — its own text is *general* reference-
  architecture selection by quality attributes (scalability/consistency/latency),
  with no DDD content. NOT a DDD member; the `requires` edge is **not** authored.
- `tactic:compositional-stream-boundaries`, `tactic:cross-cutting-state-via-store`,
  `tactic:atomic-state-ownership` — state/UI concerns, not DDD strategic/tactical
  design. Left out (per the #3063 ambiguity guard).

### DEFERRED — the DDD↔documentation mutual-reinforcement edge (B1)

Not authored: the DDD↔documentation mutual-reinforcement relationship is **gated
on the upcoming value-based edge properties (B1)** and is left **pending** until
that lands. Recorded here, not wired.

### Measured reachability delta (WP08 helper, R-1)

`d=1` action-reachable 118→130; `d=2` 125→137 (each +12). The twelve that become
action-reachable and leave BOTH `_ACTION_UNREACHABLE_D1`/`D2`:
`paradigm:domain-driven-design`, `directive:DIRECTIVE_031`, `directive:DIRECTIVE_032`
(the paradigm's pre-existing `directive_refs`, delivered once it is scoped),
`styleguide:aggregate-design-rules`, `tactic:aggregate-boundary-design`,
`tactic:anti-corruption-layer`, `tactic:bounded-context-canvas-fill`,
`tactic:bounded-context-identification`, `tactic:context-boundary-inference`,
`tactic:context-mapping-classification`, `tactic:domain-event-capture`,
`tactic:entity-value-object-classification`.
`tactic:strategic-domain-classification` was already action-reachable, so it is
delivered but moves no pin. The profile channel is unchanged (measured 39→39): the
three `agent_profile --suggests--> ddd` edges are inert, and the DDD paradigm stays
profile-unreachable so its new `requires` edges deliver nothing there.

## The deferred set (T052) — the operator's decision surface

These **60** activated artefacts remain action-unreachable at `d=2` after row 1
(WP09) and Family A (#3063) land. Each fails C-007(b): no action-reachable source with a textually-attested
relationship, and no `scope`-from-action path whose relationship is attested
without invention. **This is not a filed issue** — it is the surface the
after-mission operator interview rules on (C-007). Wiring any of these now would
mean either wiring to an unreachable source (#3007's error) or inventing a
relationship (the guard T050 forbids).

### Note: 5 of the 60 are edge-incident from a reachable source, depth-gated

The following already carry an inbound edge **from an action-reachable source**,
but the edge is `suggests` (or a `requires` chain) that sits **beyond the
traversal depth horizon**, so `resolve_context` does not reach them at `d=2`.
They are **not orphans** and are **not** wiring candidates: the relationship
already exists as an edge; "fixing" them would mean upgrading `suggests`→`requires`
(claiming a hard dependency the text does not attest) or deepening the bootstrap
walk — both are traversal-policy decisions for the operator, not edge authoring.
(Five former rows — `DIRECTIVE_032`, `anti-corruption-layer`,
`bounded-context-identification`, `context-mapping-classification`,
`domain-event-capture` — left this table when Family A (#3063) made them
action-reachable via the DDD paradigm.)

| artefact | reachable inbound source (relation) |
|---|---|
| `procedure:example-mapping-workshop` | `procedure:bdd-scenario-lifecycle` (requires) |
| `tactic:ownership-map-leeway` | `styleguide:planning-and-tracking` (suggests) |
| `tactic:pr-agent-worktree-isolation` | `directive:DIRECTIVE_043` (suggests) |
| `tactic:zombies-tdd` | `tactic:delete-the-assertion-not-the-test` (suggests) |
| `toolguide:github-tracker` | `styleguide:planning-and-tracking` (suggests) |

### Full deferred set (60), by kind — directive 4 · paradigm 4 · procedure 5 · styleguide 4 · tactic 35 · toolguide 8

  - `directive:DIRECTIVE_035`
  - `directive:DIRECTIVE_038`
  - `directive:DIRECTIVE_039`
  - `directive:DIRECTIVE_044`
  - `paradigm:atomic-design`
  - `paradigm:c4-incremental-detail-modeling`
  - `paradigm:specification-by-example`
  - `paradigm:structured-prompt-driven-development`
  - `procedure:documentation-gap-prioritization`
  - `procedure:drill-down-documentation`
  - `procedure:event-storming-discovery`
  - `procedure:example-mapping-workshop`
  - `procedure:migrate-project-guidance-to-spec-kitty-charter`
  - `styleguide:deployable-skill-authoring`
  - `styleguide:java-conventions`
  - `styleguide:mutation-aware-test-design`
  - `styleguide:reasons-canvas-writing`
  - `tactic:adversarial-qa-handoff`
  - `tactic:analysis-extract-before-interpret`
  - `tactic:architecture-diagram-review-checklist`
  - `tactic:atdd-adversarial-acceptance`
  - `tactic:atomic-design-review-checklist`
  - `tactic:atomic-state-ownership`
  - `tactic:c4-zoom-in-architecture-documentation`
  - `tactic:canonical-source-unification`
  - `tactic:chain-of-responsibility-rule-pipeline`
  - `tactic:code-documentation-analysis`
  - `tactic:compositional-stream-boundaries`
  - `tactic:cross-cutting-state-via-store`
  - `tactic:development-bdd`
  - `tactic:formalized-constraint-testing`
  - `tactic:mutation-testing-workflow`
  - `tactic:occurrence-classification-workflow`
  - `tactic:ownership-map-leeway`
  - `tactic:pr-agent-worktree-isolation`
  - `tactic:reasons-canvas-fill`
  - `tactic:reasons-canvas-review`
  - `tactic:refactoring-encapsulate-record` — Family B: topology authored, delivery pending
  - `tactic:refactoring-encapsulate-variable` — Family B: topology authored, delivery pending
  - `tactic:refactoring-extract-first-order-concept` — Family B: topology authored, delivery pending
  - `tactic:refactoring-move-field` — Family B: topology authored, delivery pending
  - `tactic:refactoring-move-method` — Family B: topology authored, delivery pending
  - `tactic:refactoring-state-pattern-for-behavior` — Family B: topology authored, delivery pending
  - `tactic:refactoring-strangler-fig` — Family B: topology authored, delivery pending
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

## Composition ledger (NFR-004) — Family A (#3063 DDD family)

Fourteen authored edges. Each moved count is recorded so no golden number moves
silently.

- **Shipped-graph edges 782 → 796** (+14). `len(HAND_AUTHORED_EDGES)` 18 → 32. The
  pure-extraction golden counts (`_EXPECTED_NODE_COUNT=304`, `_EXPECTED_EDGE_COUNT=764`)
  are **unchanged** — all fourteen are overlay-authored — so
  `test_extractor_projection`'s byte-identical assertion stays green once the
  fragments are regenerated (`764 + 32 = 796`). Ledger entry (9) is added to that
  module's composition ledger.
- **Relation histogram**: `requires` 262 → 272 (+10 paradigm→member edges),
  `suggests` 337 → 340 (+3 profile→paradigm edges), `scope` 158 → 159 (+1 reaching
  edge). All three are gated by
  `tests/architectural/test_no_authored_applies_edge.py::TestPositiveCountClaimsAreTrue`
  and mirrored char-for-char in `RELATION_DESCRIPTIONS` (`doctrine.drg.models`) and
  `docs/architecture/doctrine-relationships.md`; all updated.
- **`_ACTION_UNREACHABLE_D1` and `_ACTION_UNREACHABLE_D2`** each **lose the same 12
  members**: `paradigm:domain-driven-design`, `directive:DIRECTIVE_031`,
  `directive:DIRECTIVE_032`, `styleguide:aggregate-design-rules`,
  `tactic:aggregate-boundary-design`, `tactic:anti-corruption-layer`,
  `tactic:bounded-context-canvas-fill`, `tactic:bounded-context-identification`,
  `tactic:context-boundary-inference`, `tactic:context-mapping-classification`,
  `tactic:domain-event-capture`, `tactic:entity-value-object-classification`. The
  `d1↔d2` spread stays 7 (same members removed from both).
  `tactic:strategic-domain-classification` was already reachable, so it moves no
  pin.
- **`_PROFILE_UNREACHABLE` unchanged** (profile channel measured 39→39). **`_PROFILE_RESCUES`
  loses 4** (`directive:DIRECTIVE_031`, `directive:DIRECTIVE_032`,
  `tactic:anti-corruption-layer`, `tactic:domain-event-capture`) — the action
  channel now covers them, so they are no longer profile-only rescues.
- **Orphan sets unaffected** — every one of the 14 endpoints was already
  edge-incident.
- **Deferred set 72 → 60** (directive 6→4, paradigm 5→4, styleguide 5→4, tactic
  43→35; procedure 5 and toolguide 8 unchanged).

## Family B (#3063 REFACTORING family) — operator interview outcome, INERT (composition-only)

The #3063 operator interview ATTESTED a REFACTORING family (C-007(a) satisfied by
operator ruling). Its hub is a **NEW built-in directive**,
`directive:DISCIPLINED_REFACTORING`
(`src/doctrine/directives/built-in/disciplined-refactoring.directive.yaml`):
disciplined, behaviour-preserving refactoring — refactor in small steps under
green tests, name the smell before the move, one transformation at a time,
structural moves kept separate from behaviour changes. No equivalent directive
existed (`grep -ri refactor src/doctrine/directives/` found only the
`reconcile-change-scope-tensions` tension directive, which is unrelated).

### ⚠️ URN casing (relation/id correction)

The wiring instruction named the hub `directive:disciplined-refactoring`
(lower-kebab). A directive node's URN is derived from its artifact `id`, and the
`Directive` model requires `id` to match `^[A-Z][A-Z0-9_-]*$` while
`doctrine.drg.migration.id_normalizer.normalize_directive_id` upper-cases any
non-numeric slug — so the only URN a real directive artifact can yield is
`directive:DISCIPLINED_REFACTORING`, exactly the
`directive:RECONCILE_CHANGE_SCOPE_TENSIONS` precedent. The lower-kebab form is
unreachable through the schema; the canonical URN is UPPER_SNAKE, corrected here.

### The 14 authored edges (all `suggests`, all INERT under today's traversal)

The 7 directive→tactic edges each carry a per-tactic `when` = the tactic's own
attested applicability (the "problem" it solves), derived from the tactic's own
`purpose`/first-step text — **not invented**:

| # | source | relation | target | `when` (grounded in the tactic's own text) |
|---|---|---|---|---|
| B1 | `directive:DISCIPLINED_REFACTORING` | `suggests` | `tactic:refactoring-encapsulate-record` | a raw data record (dict/plain object/mutable named tuple) is accessed by field name from many call sites, blocking validation, renames, or a change of representation |
| B2 | `directive:DISCIPLINED_REFACTORING` | `suggests` | `tactic:refactoring-encapsulate-variable` | a widely-accessed module-level/global variable (or public attribute) is read and written from many locations and needs a single chokepoint for validation, monitoring, or a later type change |
| B3 | `directive:DISCIPLINED_REFACTORING` | `suggests` | `tactic:refactoring-extract-first-order-concept` | an important concept is implicit, duplicated, or scattered with no explicit name or single home |
| B4 | `directive:DISCIPLINED_REFACTORING` | `suggests` | `tactic:refactoring-move-field` | a field is read/modified more by another class than the one that declares it, so data ownership has drifted |
| B5 | `directive:DISCIPLINED_REFACTORING` | `suggests` | `tactic:refactoring-move-method` | a method uses more of another class's data and behaviour than its own host's (feature envy) |
| B6 | `directive:DISCIPLINED_REFACTORING` | `suggests` | `tactic:refactoring-state-pattern-for-behavior` | a class's methods are full of conditionals branching on the same internal state variable, and behaviour is driven by lifecycle state transitions |
| B7 | `directive:DISCIPLINED_REFACTORING` | `suggests` | `tactic:refactoring-strangler-fig` | a legacy component/path must be replaced incrementally — new alongside old, rerouting callers one at a time — because a single-step cutover is too risky |

The 7 profile→directive edges all share `when` = *"when tidying code, encountering
long classes/methods, or discovering convoluted logic"*. The **implementer-role
profiles** are every built-in profile whose role is `implementer` (resolved via
`spec-kitty agent profile list`; python-pedro is the primary):

| # | source (role: implementer) | relation | target |
|---|---|---|---|
| B8 | `agent_profile:frontend-freddy` | `suggests` | `directive:DISCIPLINED_REFACTORING` |
| B9 | `agent_profile:generic-agent` | `suggests` | `directive:DISCIPLINED_REFACTORING` |
| B10 | `agent_profile:implementer-ivan` | `suggests` | `directive:DISCIPLINED_REFACTORING` |
| B11 | `agent_profile:java-jenny` | `suggests` | `directive:DISCIPLINED_REFACTORING` |
| B12 | `agent_profile:node-norris` | `suggests` | `directive:DISCIPLINED_REFACTORING` |
| B13 | `agent_profile:python-pedro` (primary) | `suggests` | `directive:DISCIPLINED_REFACTORING` |
| B14 | `agent_profile:randy-reducer` | `suggests` | `directive:DISCIPLINED_REFACTORING` |

### Why Family B is INERT — measured, not assumed (WP08 helper, R-1)

All 14 edges are inert under today's traversal:

- The **directive is not charter-activated** in this project, so it never enters
  the `_activated()` universe the reachability pins subtract from — a new
  unactivated built-in directive cannot join `_ACTION_UNREACHABLE_*`.
- The **profile→directive** edges are `suggests`; the profile channel walks
  `{requires, specializes_from}` only, so it never follows them.
- The **directive→tactic** edges are only reachable if the directive is
  action-reachable, which it is **not** (no action scopes it; it is reached only
  via the inert profile edges). `resolve_context` walks `suggests` only *from*
  scope-resolved artifacts.

Measured before/after the edges landed with `resolve_context` via the WP08 helper:
`_ACTION_UNREACHABLE_D1` (67), `_ACTION_UNREACHABLE_D2` (60), `_PROFILE_UNREACHABLE`
(153) and `_PROFILE_RESCUES` (the same 4) are **UNCHANGED**. Family B moves **no**
reachability pin — only composition counts.

The seven refactoring tactics therefore **remain in the DEFERRED set above** —
*topology authored, delivery pending fast-follow*. Their delivery needs the
profile-channel walk to follow `suggests` (or the directive to be
action-scoped); that is a traversal-policy decision for the operator, not edge
authoring, so they are not action-reachable yet.

### Pending anti-pattern-authoring companion (NOT authored here)

The operator flagged that the `anti_pattern` kind — the code smells that are the
"problem" each refactor solves — is sensible to author for this family (smell →
refactor, i.e. `anti_pattern --…--> tactic:refactoring-*`). That is
doctrine-CONTENT authoring, **deferred to the fast-follow decision** and **not
authored in this pass**. Recorded here as a known companion so it is not lost.

## Composition ledger (NFR-004) — Family B (#3063 REFACTORING family)

One new directive node (via extraction) + fourteen `suggests` overlay edges. Each
moved count is recorded so no golden number moves silently.

- **Shipped-graph nodes 310 → 311** (+1). The directive is a real
  `*.directive.yaml`, so the extractor mints its node: pure golden
  `_EXPECTED_NODE_COUNT` **304 → 305** (`test_extractor_projection`). It carries
  **no inline references** (relationships are edges), so it mints **zero**
  extractor edges — `_EXPECTED_EDGE_COUNT` stays **764**.
- **Shipped-graph edges 796 → 810** (+14). `len(HAND_AUTHORED_EDGES)` **32 → 46**.
  `test_shipped_graph_is_fresh_and_byte_identical` stays green by construction
  (`764 + 46 = 810`) once the fragments are regenerated. Ledger entry (10) is added
  to that module's composition ledger.
- **`suggests` relation histogram 340 → 354** (+14; all 14 edges are `suggests`).
  `requires` (272) and `scope` (159) are **unchanged**. Gated by
  `tests/architectural/test_no_authored_applies_edge.py::TestPositiveCountClaimsAreTrue`
  and mirrored char-for-char in `RELATION_DESCRIPTIONS` (`doctrine.drg.models`) and
  `docs/architecture/doctrine-relationships.md`; both updated.
- **Orphan sets:** in a **pure** regeneration the directive is an orphan (its only
  edges are overlay-authored), so pure orphans **23 → 24** — it joins
  `_AWAITING_REFERENCES` (4 → 5) and `_ORPHANS_RESOLVED_BY_OVERLAY` (2 → 3). Shipped
  orphans stay **21** (the overlay wires it as both an edge source and target).
- **`_ACTION_UNREACHABLE_D1`/`D2`, `_PROFILE_UNREACHABLE`, `_PROFILE_RESCUES`
  UNCHANGED** — Family B is inert (measured). No pin moves.
- **Deferred set unchanged at 60** — the seven refactoring tactics stay deferred
  (topology authored, delivery pending); no artefact leaves the set.
