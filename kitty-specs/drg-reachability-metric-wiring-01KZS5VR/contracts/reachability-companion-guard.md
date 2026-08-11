# Contract — Reachability Companion Guard

The behavioral contract of the new #3009-point-3 guard. This is a test/guard contract (not an HTTP API).

## Guard: `test_shipped_graph_action_reachability_is_the_pinned_membership`

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

**Assertions** (all set-equality — NOT `<=`):
- `measured == _ACTION_UNREACHABLE_SHIPPED` (88→75 post-wiring)
- `dead == _DEAD_DOCTRINE_SHIPPED` (34) and `profile_delivered == _PROFILE_DELIVERED_SHIPPED` (41)
- totality/disjointness: `_DEAD_DOCTRINE_SHIPPED | _PROFILE_DELIVERED_SHIPPED == _ACTION_UNREACHABLE_SHIPPED`
  and the two subsets are disjoint.

**Failure behavior**: on mismatch, the message reuses the existing URN-naming differ (`_describe*`) to name
- nodes newly unreachable (in `measured`, not in the pin) — a regression, and
- nodes newly reachable (in the pin, not in `measured`) — a pin that should shrink.

**Properties**:
- **Deterministic** (NFR-003): identical result across runs on an unchanged graph; pure function of the
  loaded graph — no ordering dependence, no randomness.
- **Depth explicit**: the action channel uses `_ACTION_D2_DEPTH` (bootstrap depth); the constant is named,
  not a bare literal.
- **Guard helper location** (Renata F7): the channel-union + kind-filter helper lives IN the test module
  (not `src/`) so the dead-symbol arch gate does not flag it.
- **Complementary to incidence**: `_SHIPPED_ORPHANS` (incidence) and `_ACTION_UNREACHABLE_SHIPPED`
  (reachability) are both asserted; a node can pass incidence (has edges) yet fail reachability (no path)
  — e.g. `paradigm:atomic-design` (inert inbound edge).
- **By-design-kind exclusion test** (Renata F4): a focused case asserts at least one node of a by-design
  excluded kind (e.g. a `mission_step_contract`) is absent from `measured` even though it is unreachable —
  proving the `_BY_DESIGN_UNREACHABLE_KINDS` filter branch, not just the happy path.

## Behavioral acceptance (maps to SC-001)

| Given | When | Then |
|---|---|---|
| current shipped graph | guard runs | passes; `measured == _ACTION_UNREACHABLE_SHIPPED` (75 post-wiring; dead subset 34, profile-delivered 41) |
| a genuine inbound edge removed from a currently-reachable activated node | guard runs | fails; message names that node's URN as newly unreachable |
| a residual orphan wired to a genuine referent (this mission) | guard runs after pin update | pin shrank by exactly the now-reachable node(s); a wiring-table ledger row exists for the move |
| a node artificially added to the pin without a graph change | guard runs | fails (measured set does not contain it) — the pin cannot be padded to force green |

## Anti-requirements (NFR-001 / C-001 / C-003)

- The guard MUST NOT be satisfied by adding a node to the pin that is not genuinely unreachable, nor by
  removing a genuinely-unreachable node from the pin without wiring it — the set-equality forbids both
  (pin-padding is closed).
- **Un-gameable as an ENSEMBLE, not in isolation** (Debbie #5 / Renata F2). Set-equality alone does NOT
  force the six edges to exist — an implementer could pin the un-wired 88-baseline and go green having wired
  nothing. What forbids that is the ensemble, all of which this mission requires:
  - per-node **behavioral** red-first assertions (`target not in reachable` → `in reachable` via the
    canonical helpers) — the real ATDD artifact, not a frozenset-literal edit;
  - a **mechanical** `test_action_unreachable_shipped_members_have_ledger_coverage` cross-check (analog to
    the existing `_PROFILE_RESCUES` gate) binding every URN that enters/leaves the pin to a backtick-quoted
    wiring-table row — so the action-side delta is machine-enforced, not review-only;
  - the existing inert-edge control tests (incidence-fixed vs reachability-unreachable vs positive-control).
- No traversal re-implementation: importing and calling the canonical helpers is mandatory so the metric
  cannot drift from `resolve_context` semantics.
