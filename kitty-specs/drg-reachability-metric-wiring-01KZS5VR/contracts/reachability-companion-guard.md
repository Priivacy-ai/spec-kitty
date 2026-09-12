# Contract — Reachability Companion Guard

The behavioral contract of the #3009-point-3 guard. This is a test/guard contract (not an HTTP API).

**SOFTENED (operator landing decision, PR #3342):** the exact-membership set-equality pin
(`measured == _ACTION_UNREACHABLE_SHIPPED`, `dead == _DEAD_DOCTRINE_SHIPPED`,
`profile_delivered == _PROFILE_DELIVERED_SHIPPED`) this contract originally mandated has been
intentionally dropped, consistent with mission `assertive-test-suite-sanitation-01KZME3P`'s
"test plausible graph behavior, not exact ever-growing membership" — an ever-growing frozenset
literal that every future doctrine activation must hand-edit is a maintenance liability, not a
load-bearing correctness signal on its own. The companion metric is now asserted by two
mechanisms instead:
1. **Live partition invariants** — `test_partition_is_total_and_disjoint` asserts, against the
   graph measured at test time (not a frozen literal), that `dead | profile_delivered == measured`
   and the two subsets are disjoint.
2. **Fixed anti-gaming gate** — `TestActionUnreachableShippedLedgerCoverage` still asserts, via
   the fixed `_WIRED_THIS_MISSION` set (13 URNs, unaffected by future unrelated doctrine
   activation growth), that every member this mission wires is BOTH genuinely action-reachable
   AND named in a wiring-table ledger row. This is what remains un-gameable: an implementer
   cannot silently claim delivery with nothing wired, because the thirteen wired URNs are
   independently proven reachable via the canonical helpers, not via a set-equality literal that
   could be pasted in unchanged.

## Guard: `_shipped_reachability_partition` + `TestReachabilityCompanionGuard`

**Location**: `tests/doctrine/drg/test_reachability.py`

**Input**: the shipped composed graph `load_built_in_graph()`.

**Computation** (MUST use canonical helpers, MUST NOT re-implement traversal):
1. `action_reach = action_channel_reachable(graph, action_seed_urns(graph), _ACTION_D2_DEPTH)`
2. `profile_reach = profile_channel_reachable(graph, agent_profile_seed_urns(graph))`
3. Primary (action-only) — the #3009 "reachable from actions" measure:
   `measured = { n.urn for n in graph.nodes
                 if n.urn not in action_reach
                 and kind_of(n.urn) not in _BY_DESIGN_UNREACHABLE_KINDS }
              - action_seed_urns(graph) - agent_profile_seed_urns(graph)`
4. Partition subsets: `dead = { u in measured if u not in profile_reach }` (both-channel dead);
   `profile_delivered = measured - dead`.

**Assertions** (live, against the measured partition — no frozen-literal set-equality):
- totality/disjointness: `dead | profile_delivered == measured` and the two subsets are disjoint.
- the by-design-excluded kinds (`_BY_DESIGN_UNREACHABLE_KINDS`) never appear in `measured`, even
  when genuinely unreachable.
- `_shipped_reachability_partition` is a thin composition of the canonical helpers (no
  reimplemented walk) — proven by `test_measured_calls_canonical_helpers_not_a_reimplemented_walk`.

**Properties**:
- **Deterministic** (NFR-003): identical result across runs on an unchanged graph; pure function of the
  loaded graph — no ordering dependence, no randomness.
- **Depth explicit**: the action channel uses `_ACTION_D2_DEPTH` (bootstrap depth); the constant is named,
  not a bare literal.
- **Guard helper location** (Renata F7): the channel-union + kind-filter helper lives IN the test module
  (not `src/`) so the dead-symbol arch gate does not flag it.
- **By-design-kind exclusion test** (Renata F4): a focused case asserts at least one node of a by-design
  excluded kind (e.g. a `mission_step_contract`) is absent from `measured` even though it is unreachable —
  proving the `_BY_DESIGN_UNREACHABLE_KINDS` filter branch, not just the happy path.

## Behavioral acceptance (maps to SC-001)

| Given | When | Then |
|---|---|---|
| current shipped graph | guard runs | passes; `dead \| profile_delivered == measured`, subsets disjoint (measured 75-ish post-wiring: dead subset ~34, profile-delivered ~41 — descriptive, not pinned) |
| a genuine inbound edge removed from a currently-reachable activated node | guard runs | the partition invariants still hold (the node simply re-enters `measured`/`dead`); if the node is one of the fixed `_WIRED_THIS_MISSION` thirteen, `TestActionUnreachableShippedLedgerCoverage` fails, naming it |
| a residual orphan wired to a genuine referent (this mission) | guard runs | the live partition reflects the new reachability with no literal to update; if the node is a `_WIRED_THIS_MISSION` member, its ledger-coverage assertion goes green |
| an implementer claims delivery with nothing wired | guard runs | `TestActionUnreachableShippedLedgerCoverage.test_wired_this_mission_members_are_action_reachable` fails — the fixed thirteen URNs are still measured-unreachable |

## Anti-requirements (NFR-001 / C-001 / C-003)

- **Un-gameable as an ENSEMBLE, not in isolation** (Debbie #5 / Renata F2). The live partition
  invariants alone do NOT force the six edges to exist — they hold trivially on any graph. What
  forbids a null-delta claim is the ensemble, all of which this mission requires:
  - per-node **behavioral** red-first assertions (`target not in reachable` → `in reachable` via the
    canonical helpers) — the real ATDD artifact, not a frozenset-literal edit;
  - the **fixed anti-gaming gate** — `TestActionUnreachableShippedLedgerCoverage` binds every
    `_WIRED_THIS_MISSION` member to (a) genuine measured action-reachability and (b) a
    backtick-quoted wiring-table row — so the action-side delta is machine-enforced, not
    review-only, and immune to future unrelated doctrine-activation churn (unlike the dropped
    ever-growing pin);
  - the existing inert-edge control tests (incidence-fixed vs reachability-unreachable vs positive-control).
- No traversal re-implementation: importing and calling the canonical helpers is mandatory so the metric
  cannot drift from `resolve_context` semantics.
