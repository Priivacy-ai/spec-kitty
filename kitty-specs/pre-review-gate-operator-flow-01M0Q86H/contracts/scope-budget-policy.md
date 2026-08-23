# Contract: Deterministic Pre-Review Scope Budget Policy

## Purpose

Decide, before subprocess launch, whether a resolved test scope is explicitly suitable, explicitly oversized, or not yet classified for the interactive pre-review gate.

## Input

- `ScopeResult.test_targets`;
- positive effective head-run timeout in seconds.

## Output

One immutable `ScopeBudgetAssessment`:

```text
classification: bounded | oversized | unknown
scope_identity: stable string
normalized_targets: ordered unique tuple
effective_budget_seconds: positive number
matched_rule_id: string | null
evidence: string | null
guidance: string
```

## Normative behavior

1. Normalize a copy of targets; never rewrite executed argv.
2. Derive identity from a fixed budget-policy namespace plus normalized targets; do not reuse post-run `scope_source_identity()`.
3. Match source-controlled exact target atoms by membership.
4. Return `unknown` when no rule matches.
5. Refuse execution only for `oversized`.
6. Warn and execute for `unknown` under the existing timeout.
7. Expose no runtime write, learning, or promotion API.
8. A new classification requires a reviewed source change with evidence.

## Initial rule

Any normalized target set containing the exact atom `tests/architectural` is `oversized`, based on #2573 dogfood evidence of roughly 26 minutes for that full-directory target. Descendant file targets do not match this rule. A suite encoded only inside a declared command remains `unknown`; arbitrary command parsing is outside 3.2.6.

## Non-goals

- CI runtime prediction;
- workflow scheduling or shard changes;
- log ingestion/backfill;
- per-machine caches;
- automatic classification after timeout;
- refusal of an unknown scope.
