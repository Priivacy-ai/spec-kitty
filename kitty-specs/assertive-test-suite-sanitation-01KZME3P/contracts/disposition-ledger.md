# Contract: Disposition Ledger

The canonical aggregate is generated as `docs/reports/test-sanitation/assertive-test-suite-sanitation-01KZME3P/dispositions.yaml` from the global machine census plus non-overlapping WP-owned shards under `docs/reports/test-sanitation/assertive-test-suite-sanitation-01KZME3P/dispositions/WP##.yaml`. Adjudication WPs never edit the aggregate or another WP's shard.

## Required invariants

1. `schema_version` is `test-sanitation/v1`.
2. Every source-discovered test-like unit and collected node reconciles in the lightweight machine census.
3. Every deletion, consolidation, temporary exception, fix, materially changed survivor, and deletion-justifying survivor has exactly one deep candidate row in one WP shard.
4. Families share production path, oracle, outcome, marker/route class, cost class, platform scope, and verdict; any divergence expands to nodes.
5. Every ledgered `KEEP` references causal proof that reaches Act and fails the intended oracle and has non-null production path, oracle, contract, and authority.
6. Every `DELETE` identifies non-causality/obsolete authority or a survivor with equivalent causal ownership.
7. `FIX_TEST` and `FIX_PRODUCT` cannot be terminal.
8. `CONSOLIDATE` is terminal only after a survivor and deleted members exist.
9. `TEMPORARY` requires one-time HiC approval, issue, owner, expiry within 30 days, and an irreplaceable environmental/platform profile; it cannot renew or cover inert/correctness/timing candidates.
10. Paths and nodeids are repository-relative and deterministic.

The validator fails closed on unknown verdicts, stale members, invalid grouping fields, expired/renewed/forbidden temporary states, missing class-profile proof, duplicate membership, or incomplete discovery reconciliation.
