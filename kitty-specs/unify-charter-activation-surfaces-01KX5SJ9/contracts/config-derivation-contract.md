# Contract: config-sourced derivation of the compiled reference set

Internal contract (not HTTP). Names indicative; final shapes at implement time.

## The derivation contract

- **Input authority**: `config.activated_*` (per-kind config-stem lists).
- **Resolution**: config stems resolve to artefacts via the same `DoctrineService`/DRG resolution used by the live `_compiled_reference_id_suffixes()` in `test_charter_references_resolve.py` — NOT a bespoke walk (Decision 2).
- **Output**: `references.yaml` (compiled reference set) + the induced/built-in graph, byte-deterministic (STATIC timestamps), so the `generate_graph` freshness gate stays green.
- **Answers**: `answers.selected_*` is NOT read for this derivation (FR-003).

## The parity guard contract (consistency_check extension)

| Condition | Result |
|-----------|--------|
| every `config.activated_*` entry resolves in `references.yaml`/graph AND no extra | PASS |
| a config-activated entry missing from the derived set | FAIL-CLOSED (actionable message: "activated but unresolved — regenerate") |
| a derived entry absent from `config.activated_*` | FAIL-CLOSED |
| planted divergence (self-test) | guard BITES (NFR-002 non-vacuity) |

## The interview→config contract (FR-007)

- After the interview captures `answers.selected_*`, those selections are activated into `config.activated_*` via `activation_engine.commit_plan` (layer rule: orchestrated from the `specify_cli` command; engine call stays in `charter`).
- Splittable to a follow-up if it entangles the interview flow (see research Open Question A).

## Layer constraint (C-001)

Reconciliation/derivation logic lives in `charter`; the `charter` package must not import `specify_cli` (`test_charter_does_not_import_specify_cli`). CLI wrappers orchestrate.
