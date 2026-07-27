# Data Model — Test-Suite Friction Remediation

This mission has **no persistent data model**. The "entities" are test-infrastructure surfaces and their invariants. Documenting them makes the guard contracts testable.

## E-01 — Reachability record (dead-code gate)
- **Fields**: symbol qualname, defining module, set of reference sites (static import + **first-party dynamic `module.attr` access** — new in IC-01), allowlist membership + reason.
- **Invariant**: a symbol is *dead* iff it has zero reference sites of any recognised kind. IC-01 adds dynamic-access sites to the recognised set.
- **Transition**: `permanently-allowlisted-because-invisible` → `recognised-live` (IC-01/#2559) → allowlist row removed (FR-002). Or `live` → `dead` after IC-02 delete → symbol removed (not allowlisted).
- **Guard**: `tests/architectural/test_no_dead_symbols.py`, `_symbol_key.py`.

## E-02 — Grandfathered-legacy allowlist entry (E-01 subtype)
- **Fields**: symbol, category (`category_b_grandfathered_legacy` | `category_b_t001_unblinded`), classification (genuinely-dead | live-by-dynamic-access | load-bearing `doctrine.*` re-export).
- **Invariant**: only *genuinely-dead* entries are removable; count MUST decrease from baseline **193** but MUST NOT reach 0 while live entries exist.
- **Guard**: same file; IC-03/FR-004.

## E-03 — Ratchet allowlist comparand (positional-anchor ban)
- **Fields**: descriptor keyed by `composite_key(enclosing_qualname, normalized_token_line)`.
- **Invariant (IC-04/FR-005)**: NO comparand may be, or be derived from, a raw `(rel_path, int_line)` positional anchor — including an `int` laundered through a seed tuple + loop var into `composite_key(source, N)`.
- **Guard**: `test_ratchet_positional_anchor_ban.py` (extended), enforced across all of `tests/architectural/`.

## E-04 — Lane enumeration assertion
- **Fields**: the exact set of `Lane` member names.
- **Invariant (IC-05/FR-006)**: the test asserts the exact frozenset of names, not `len(Lane) == N`. Adding/removing a lane forces a content edit.
- **Guard**: `tests/status/test_models.py`.

## E-05 — Emit/wiring observable contract
- **Fields**: the observable artifact per seam — persisted event in `status.events.jsonl`, HTTP response body, rendered output, config on disk.
- **Invariant (IC-06/FR-007)**: the test asserts the observable artifact with NO `@patch` on the module under test; at most one real-outcome test per seam is kept, wiring twins demoted/deleted.
- **Guard**: `tests/status/test_agent_status_emit_aggregate_wiring.py` + siblings.

## E-06 — Mission factory output
- **Fields**: `meta.json` produced by `tests/_factories.make_mission(**overrides)`.
- **Invariant (IC-07/FR-008)**: byte-identical AFTER normalizing the auto-minted `{mission_id, mid8, created_at}` (minus explicit overrides) to a direct `create_mission_core()` call; single schema authority.
- **Guard**: a new factory-parity test; `tests/_factories/__init__.py` non-empty with ≥1 real importer.

## E-07 — Shard group registry
- **Fields**: `SHARD_GROUPS` keyed by group name (`arch`, `next`), each a `ShardGroup`; an expected-group manifest.
- **Invariant (IC-10/FR-011)**: assembly is order-independent via idempotent `register(group)`; the completeness guard asserts the manifest and fails as "group not registered" (never bare `KeyError`); no group's test universe is silently unmarked.
- **Guard**: `tests/architectural/test_arch_shard_marker_completeness.py`, new `tests/_shard_registry.py`.

## E-08 — CI gate membership
- **Fields**: workflow jobs, each with {invokes-pytest: bool}; `quality-gate.needs`; a reasoned `NON_BLOCKING_ALLOWLIST`.
- **Invariant (IC-11/FR-012)**: `{pytest-jobs} - NON_BLOCKING_ALLOWLIST ⊆ quality-gate.needs`; every allowlist entry carries a why-non-blocking rationale.
- **Guard**: new guard beside `test_workflow_coherence.py` over `_gate_coverage.WorkflowModel`.

## E-09 — Coverage discovery set (Sonar)
- **Fields**: the set of coverage XML paths the sonarcloud job discovers; the produced `coverage-ui-e2e.xml`.
- **Invariant (IC-12/FR-013)**: `coverage-ui-e2e.xml` (from the `ui-e2e.yml` head-SHA run) is a member of the discovered set.
- **Guard**: `test_coverage_consumer_needs`-style assertion.

## E-10 — Golden-count assertion inventory (Lane C)
- **Fields**: each `len(<collection>) == <int>` site in `tests/` → classification (`keep`: cardinality-is-contract | `convert`: set/frozenset-equality expresses it); an annotation escape hatch `# golden-count: cardinality-is-contract`; a `convert`-set baseline count.
- **Invariant (IC-14/FR-014)**: the `convert` baseline strictly decreases per burndown WP and never regrows; a NEW un-annotated golden-count assertion fails the recurrence guard.
- **Guard**: new AST guard beside the architectural guards (subject to the new-guard-file DoD).

## E-11 — gc2b exact-selection ratchet (Lane B)
- **Fields**: the `tests/architectural/baselines/*.txt` node-id selection set; scope = {orphan-only | advisory | exact}.
- **Invariant (IC-13/FR-015)**: routine test-file add/remove does NOT trip the ratchet red; the load-bearing orphan-detection signal is preserved (scope-to-orphan) or made advisory.
- **Guard**: the gc2b selection guard itself, re-scoped.

## Ratchet/parity catalog (E-* meta, FR-016)
- Not a code entity — a running tracer table (`tracer-design-decisions.md`) recording each ratchet/pinning and behavioural-parity suite touched, keyed by test file, with columns {category, pins-invariant-or-shape, CaaCS churn, verdict}. The close-out verdict feeds a follow-up mission.
