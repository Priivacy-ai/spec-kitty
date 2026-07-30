# Data Model — Doctrine Delivery Activation Fast-Follow

No new persisted data stores. The "entities" are existing DRG / reachability / registry structures this
mission extends. Documented so ownership + invariants are explicit for the WPs.

## DRG edge & relation

- **`DRGEdge`** (`src/doctrine/drg/models.py:360-372`) — carries `source`, `target`, `relation`,
  `when: str|None`, `reason: str|None`. The `when` clause is the applicability condition surfaced by this
  mission. Retrieved via `DRGGraph.edges_from(urn, relation)` (`models.py:415-425`).
- **`Relation`** enum — `REQUIRES`, `SPECIALIZES_FROM`, `SUGGESTS`, `INSTANTIATES` (`template:instantiates`,
  walked by no delivery channel), `REJECTS` (the canonical anti-pattern relation, directional
  good-artefact → anti_pattern, validation-tier). `RELATION_DESCRIPTIONS[Relation.*]` carries histogram
  count-claims gated by `test_no_authored_applies_edge.py` + mirrored in `docs/architecture/
  doctrine-relationships.md` (parity `test_relation_doc_parity.py`) — **owned by the authoring WP (D15)**.
- **Invariant**: any `suggests` edge surfaced to a consumer yields a `when` (authored, or
  `STATED_DEFAULT_WHEN`). Family A edges (architect→DDD) currently lack `when` → D3 backfill.

## Reachability channels

- **`PROFILE_CHANNEL_RELATIONS`** (`reachability.py:48-50`) — `{REQUIRES, SPECIALIZES_FROM}` today;
  `+= SUGGESTS` (FR-001). Consumed by `profile_channel_reachable` (`reachability.py:99-125`) via node-level
  `walk_edges`.
- **`profile_channel_reachable(graph, seeds) -> frozenset[urn]`** — returns reached node URNs (no edges).
- **Action channel** — `action_channel_reachable`/`resolve_context` (separate walk; already does
  scope→requires→suggests). Untouched by FR-001, but the FR-004 re-measure authority (C-001).
- **Delivery partition** — `partition_delivery` (`progressive_disclosure.py:93`) splits
  requires-closure (inline/eager) from suggests-link (fetch), the precedence D1/D2 mirror.

## Reachability pins (test goldens)

- **`_PROFILE_UNREACHABLE`** — `tests/doctrine/drg/test_reachability.py:363-519`, 153 members;
  `= _activated() - profile_channel_reachable(...)`. Shrinks when FR-001 lands.
- **`_PROFILE_RESCUES`** — `test_reachability.py:525-530`, 2 members;
  `= _ACTION_UNREACHABLE_D2 - _PROFILE_UNREACHABLE`. Shifts with the above.
- **Wiring table deferred set** — `docs/plans/doctrine/delivery-reachability-wiring-table.md`, **baseline
  60** (the Family C ledger's authoritative figure; the "50"/"39" figures elsewhere in the doc are stale
  and reconciled at WP04 start — D19). Drops in FR-005.
- **`_ACTION_UNREACHABLE_D2`** — the action-channel pin in `test_reachability.py`, load-bearing for
  `_PROFILE_RESCUES`; owned by IC-05 (D16).
- **Invariant (NFR-002)**: every change to any of the above numbers carries a composition-ledger row; the
  histogram claims + byte-identical extractor golden (`_EXPECTED_NODE_COUNT`/`_EXPECTED_EDGE_COUNT`) stay
  consistent.

## Forward-API allowlist

- **`_CATEGORY_C_DELIVERY_RAIL_FORWARD_API`** — frozenset in `tests/architectural/test_no_dead_symbols.py:
  1089-1106` (9 symbols) + `_baselines.yaml` mirror row. Each entry retired when its symbol is
  `src`-consumed (FR-006). **Invariant (NFR-004)**: 0 wired symbols remain listed; 0 removed symbols are
  unreferenced in `src/`; a test-only reference does NOT qualify for removal.

## DRG writer registry

- **`MAPPING_WRITERS` / `DOCUMENT_WRITERS`** (`src/specify_cli/drg_writers/registry.py:153-176`) — canonical
  mapping serializer `model_to_graph_dict` (`extractor.py:1379`) + document serializer
  `graph_document_to_dict` (`extractor.py:1424`). **Invariant (FR-010/NFR-006)**: every `src/`
  graph-document emitter delegates to `graph_document_to_dict` AND is a registry member; the discovery gate
  fails otherwise (self-mutation proven).

## Asset repository source-path

- **`AssetRepository._source_paths[id]`** (`src/doctrine/assets/repository.py:121-133`). **Invariant
  (FR-011)**: recorded only after successful model validation, so `source_path(id)` and `get(id)` agree
  (no split-brain). Same invariant for the AgentProfileRepository twin.

## New artefacts authored

- **`anti_pattern` nodes** (`src/doctrine/anti_pattern.graph.yaml`, extends the existing 6-node corpus) —
  non-activatable, **never delivered/activated** ("never activated as a live rule", models.py:73);
  reached as the TARGET of a `tactic --REJECTS--> anti_pattern` edge (matching the 8 existing REJECTS
  edges). Every anti_pattern MUST be a REJECTS-target (`validator.py:171`). Content grounded in the linked
  `refactoring-*` tactic's attested `problem`/`when` (C-004; no invented smells).
- **`template:instantiates` edge** (`src/doctrine/action.graph.yaml`) — from `action:documentation/design`
  to the C4 mermaid `template` artefacts (C-005).
