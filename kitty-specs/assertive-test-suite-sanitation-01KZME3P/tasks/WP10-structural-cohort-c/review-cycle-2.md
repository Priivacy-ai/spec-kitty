---
review_cycle: 2
reviewer: reviewer-renata
verdict: changes_requested
wp_id: WP10
implementation_commits:
  - b7cf68425
  - 95a4f6729
---

# WP10 review cycle 2 — changes requested

The survivor remediation is now strong: all 42 retained paths have current authority, nonzero corpus, an exact retained node plus controlled-fault node, content-addressed replay, and restored-green proof. Independent replay passed 55 selected probes and the complete cohort (`535 passed, 2 xfailed`). Exact collection remains `841 -> 537` (`-304`); Ruff, focused mypy, diff, ownership, production/map, and WP09-isolation checks pass.

## Blocking issue — deletion equivalence remains grouped above the causal-family level

Cycle 1 required every deleted behavioral family to name and execute its real stronger survivor, or restore the unique case. The cycle-2 artifact adds one mapping per deleted **file**, but three deleted files contain heterogeneous production paths, inputs, and oracles. Their single successor is therefore not causal proof for all members:

- `tests/integration/test_cross_seam_consumers.py` groups nine tests over `_identity_for_request`, `_resolve_bookkeeping_transaction_identifiers`, legacy/meta-less/mid8 identity cases, and two AST shape checks. Its recorded successor, `tests/sync/test_project_identity_resolver_3030.py`, does not call either deleted function and cannot catch those regressions. Actual candidate survivors include `tests/specify_cli/cli/commands/test_implement_bookkeeping_identifiers.py`, `tests/coordination/test_status_write_authority.py`, and `tests/specify_cli/coordination/test_status_transition_adoption.py`; bind each distinct family to exact nodes or classify it explicitly as structural/no-authority.
- `tests/specify_cli/cli/commands/test_wp03_bypass_writers_fr008.py` groups classifier behavior, safe-commit kind threading, protected-refusal diagnostics, direct-call AST checks, and task-tail byte-identity. `tests/architectural/test_write_surface_placement_guard.py` covers placement behavior, not every diagnostic and task-tail oracle. Split those families and either cite exact surviving nodes or record why the prose/shape pin has no current authority.
- `tests/specify_cli/test_egress_consolidation_3110.py` groups consent transport, exact definition/layout checks, diagnostic branches, and rationale/prose. The consent-gate successor covers egress refusal only. Split the remaining families into their actual successor or no-authority dispositions.

The 12 DELETE rows in `WP10.yaml` still carry empty `production_paths`, null `oracle`/`contract_claim`, and generic shared shape/migration probes. `wp10-probes-cycle2.json` repeats the same file-level grouping. Update the deletion rows/artifact to one row per genuinely equivalent family (identical production path, authority, corpus, oracle, and fault), record the exact executed successor node and result where one exists, and record concrete authority/caller search evidence where no survivor is warranted. Restore only a case that cannot be proven redundant or non-authoritative.

## WP anti-pattern checklist

1. Dead code: **N/A** — no production APIs added.
2. Synthetic-fixture test: **PASS** — retained probes traverse their live enforcement callables.
3. Silent empty return: **N/A** — no production paths changed.
4. FR coverage: **FAIL** — heterogeneous deleted behavioral families lack exact causal successor/no-authority proof.
5. Frozen surface: **PASS**.
6. Locked decision: **PASS**.
7. Shared-file ownership: **PASS** — no production, central shard-map, or WP09 edits.
8. Production fragility: **N/A** — no production raises added.

