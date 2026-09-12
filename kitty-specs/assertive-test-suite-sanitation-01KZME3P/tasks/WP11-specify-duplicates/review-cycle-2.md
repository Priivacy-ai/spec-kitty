# WP11 review cycle 2 — changes requested

## Verdict

Reject. Cycle-1 causal/coherence/receipt blockers are closed. One final completeness blocker remains; no fourth cycle is permitted.

## Independently verified

- Frozen 3,140→2,663 nodes (`-477`); focused 2,662 passed/1 skip.
- Production trace: 100 failures/358 controls/1 skip; structural faults 358/358.
- YAML/JSON 77/77 match; all 15 DELETE rows/40 members agree.
- All survivor/replacement refs collect and have causal/static proof; bounded receipts and hashes valid; Ruff/diff clean; no production edit.

## Final-cycle blocker

AST comparison finds 143 removed base functions less 11 dashboard migrations = 132 true deletions. Ledger covers 89, leaving 43 without terminal proof: 20 mid8 caller, 10 mid8 contract-sensitive, seven historical matrix, two template-lane, two dashboard glossary, one shim registry, one WP18 meta reader. Ten are incorrectly labeled `SPLIT_NON_EQUIVALENT` despite deletion.

Terminally map all 43 to collected survivor+proof or bounded no-survivor proof; reconcile the ten normalized rows; add fail-closed set equality proving `(base - head - migrations) == terminal deletions` and `132 = 89 + 43`. Rerun gates. No deletion expansion.

Additional final-cycle input-boundary check: `WP11-08faab8d1a9c` deletes the VCS-lock truth-table cases `(None, {}) → False` and `({}, {}) → False`, but its cited survivor does not contain those partitions and the generic production-call fault does not prove them dominated. Add both inputs to the survivor or supply a targeted no-unique-kill proof.
