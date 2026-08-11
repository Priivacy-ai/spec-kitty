# Phase 1 Data Model — DRG Reachability Metric & Orphan Wiring

This mission adds no runtime data types. The "data model" here is (1) the DRG entities the change
touches, (2) the new companion-metric definition, and (3) the golden-constant / ledger move-set.

## DRG entities (existing — reference only)

- **DRGNode** `{ urn: "<kind>:<id>", kind, ... }` — a doctrine artifact.
- **DRGEdge** `{ source, target, relation, when?, reason?, provenance? }` — pydantic model
  (`doctrine.drg.models.DRGEdge`; construct edges via this model, not `dataclasses.replace`).
- **Relation** — enum: `scope`, `requires`, `suggests`, `vocabulary`, `specializes_from`, … The traversal
  relevant here: action channel = `scope`(d1) → `requires`(∞) + `suggests`(≤depth) from the scope set;
  profile channel = `{requires, specializes_from}`(∞) from profile seeds.
- **DRGGraph** — `{ nodes, edges }`; the shipped composed graph is `load_built_in_graph()` (reads
  `packs/built-in/*.graph.yaml`). Regenerated deterministically by `doctrine regenerate-graph` /
  `generate_graph`.

## New: reachability companion metric (`_ACTION_UNREACHABLE_SHIPPED`) — action-only, partitioned

*(Revised after post-plan squad — the primary pin is action-only, per #3009's literal "reachable from
actions" ask; the both-channel set is retained as a named partition subset.)*

**Primary definition** (action-only, whole-graph, "not reachable from any action root"):
```
_ACTION_UNREACHABLE_SHIPPED = { n.urn for n in graph.nodes
    if n.urn NOT in action_channel_reachable(graph, action_seeds, _ACTION_D2_DEPTH)
    and kind(n.urn) NOT in _BY_DESIGN_UNREACHABLE_KINDS } − action_seeds − agent_profile_seeds
```
- `_BY_DESIGN_UNREACHABLE_KINDS` = `{mission_step_contract, asset, anti_pattern, template, mission_type,
  glossary_pack}` (edgeless-by-construction / resolved by URN presence, not traversal). Action and
  agent_profile seeds are traversal roots, excluded. `anti_pattern` exclusion rationale recorded in the
  contract (Alphonso Axis-1).
- Computed via the **canonical** `action_channel_reachable` / `profile_channel_reachable` helpers. Action
  channel at `_ACTION_D2_DEPTH` (bootstrap) — a named constant, not a literal.
- **Assertion**: set-equality against the pinned frozenset; failure reuses the existing `_describe` URN
  differ. Deterministic (NFR-003). Guard helper lives **in the test module** (Renata F7).

**Value**: `88` before wiring → `75` after (measured, like-for-like exclusions). The 13 that leave:
the 3 directives (`DISCIPLINED_REFACTORING`, `RECONCILE_CHANGE_SCOPE_TENSIONS`, `USE_MUTATION_TESTING`) +
their cascaded families (7 `refactoring-*` Fowler tactics, `mutation-testing-workflow`,
`python-/typescript-mutation-tools`).

**Asserted partition (totality — Debbie #1; #3009 "record which nodes the count covers"):** the 75 splits,
total & disjoint, into two named frozensets:
- `_DEAD_DOCTRINE_SHIPPED` = **34** — reachable from **neither** channel (the genuine residual; each member
  dispositioned in IC-03). Both-channel measure moves 38 → 34; the four that leave vs the un-wired baseline
  are `RECONCILE_CHANGE_SCOPE_TENSIONS`, `spike-timebox-policy`, `glossary-maintenance-workflow`,
  `meeting-minutes-pipeline`.
- `_PROFILE_DELIVERED_SHIPPED` = **41** — action-unreachable but delivered via the profile channel's
  `{requires, specializes_from, suggests}` web (by design; group-dispositioned).

**Why the directives don't move `_DEAD_DOCTRINE_SHIPPED`**: `DISCIPLINED_REFACTORING` / `USE_MUTATION` are
already **profile-channel** reachable, so they sit in `_PROFILE_DELIVERED_SHIPPED`, not the dead set; wiring
them still shrinks the **action-only primary** pin (they leave it) and the activated-only action pins (their
cascaded activated tactics leave).

## Golden-constant / ledger move-set (IC-04)

Each move needs a `docs/plans/doctrine/delivery-reachability-wiring-table.md` composition-ledger row naming
the responsible edge (NFR-004) + a numbered-ledger entry in `test_extractor_projection.py`. Exact numeric
targets for the activated-only and incidence pins are recomputed at implement time against the regenerated
graph; direction is fixed here.

*(Corrected per Renata F1/F5: `_PROFILE_UNREACHABLE` is activated-only; only `glossary-maintenance-workflow`
is activated of the three procedures. The activated action pins move via cascaded **activated tactics**, not
the non-activated directives.)*

| Constant | File | Move | Driver / correct accounting |
|---|---|---|---|
| `_ACTION_UNREACHABLE_SHIPPED` (new, primary) | test_reachability.py | new pin, 88→**75** | action-only whole-graph; 13 leave (3 directives + families). **Needs a NEW mechanical ledger-coverage test** (F2/Debbie #5). |
| `_DEAD_DOCTRINE_SHIPPED` / `_PROFILE_DELIVERED_SHIPPED` (new subsets) | test_reachability.py | new pins, 34 / 41 | asserted partition of the primary (total & disjoint) |
| `_ACTION_UNREACHABLE_D1` / `_D2` (activated-only) | test_reachability.py | shrink | via cascaded **activated** tactics (`refactoring-*`, `mutation-testing-workflow`) + RECONCILE (the only activated directive of the three); NOT DISC/USE (not activated) |
| `_PROFILE_UNREACHABLE` (activated-only) | test_reachability.py | shrink by **2** (Debbie, verified) | `glossary-maintenance-workflow` (activated procedure) **and** `RECONCILE_CHANGE_SCOPE_TENSIONS` (activated directive, now profile-reachable via edges 2/3). `spike`/`meeting-minutes` not activated → not members |
| `_PROFILE_RESCUES` (= D2 − PROFILE_UNREACHABLE) | test_reachability.py | **gains** `glossary-maintenance-workflow` only (RECONCILE leaves both D2 and PU, so does NOT enter rescues); ledger row per member in the **existing** NFR-002 section | already mechanically gated (`test_every_profile_rescue_member_has_a_ledger_row`, section-scoped) |
| `_ACTIVATED_BUT_ORPHANED` | test_extractor_projection.py | shrink (RECONCILE leaves) | edges 2/3 — MUST only shrink (C-003) |
| `_AWAITING_REFERENCES` | test_extractor_projection.py | shrink (DISCIPLINED_REFACTORING, USE_MUTATION leave incidence-orphan status) | edges 1/4 give them incident edges |
| `_INTENTIONAL_ORPHANS` / `_SHIPPED_ORPHANS` | test_extractor_projection.py | shrink | fewer incidence orphans |
| `_ORPHANS_RESOLVED_BY_OVERLAY` | test_extractor_projection.py | reconcile if a curated extractor edge supersedes an overlay one | edges 1–4 |
| numbered-ledger entry 18 + shipped-edge-count prose | test_extractor_projection.py | new ledger entry (not a live int; byte-identity gate enforces) | +6 edges (F6) |
| `DOCUMENTED_ORPHAN_RESIDUAL` (21, `<=` ceiling) | test_doctrine_regenerate_graph.py | ratchet DOWN in SAME WP as incidence shrink | C-005 |
| `_NORMALIZATION_DELTA` (31) | test_reachability.py | **no move** | wiring does not touch store↔node slug reconciliation |

**Invariants to preserve**:
- Incidence partition stays total & disjoint: `sum(len(part)) == len(_INTENTIONAL_ORPHANS)` over
  (`_EDGELESS_BY_CONSTRUCTION`, `_AWAITING_REFERENCES`, `_NOT_A_TRAVERSAL_TARGET`,
  `_ACTIVATED_BUT_ORPHANED`).
- Reachability/incidence residuals only shrink or hold (C-003) — no node added to any defect/residual set.
- Graph regeneration is byte-identical on re-run (determinism).

## Residual truth-up (IC-03)

Every member of the pinned residual gets a disposition (Debbie #1 totality):
- **41 `_PROFILE_DELIVERED_SHIPPED`** — dispositioned as a group ("action-unreachable, delivered via the
  profile channel — by design").
- **34 `_DEAD_DOCTRINE_SHIPPED`** — each gets a one-line disposition: honest activation/runtime-only residual
  (with note: DIRECTIVE_035, DIRECTIVE_039, migrate-project-guidance, deployable-skill-authoring,
  atomic-design [inert-edge], the SPDD/documentation/java-mission clusters) | by-construction | B2-deferred-
  with-referent-named.
- **`agent_profile:human-in-charge`** is recorded ONLY as an **incidence** (#1923) residual — it is a
  profile seed, excluded from the reachability sets by construction (Debbie #2). Do not list it as a
  reachability residual.
- **Retire** `toolguide:rtk-search-tooling` (removed from disk + graph). **Promote** only the genuinely
  action-reachable of the former "6 promoted" (decision-marker-capture, no-parallel-duplicate,
  python-review-checks, red-main-release-discipline); reasons-canvas-writing + occurrence-classification are
  profile-only; atomic-design is a reachability residual (Debbie #4).
