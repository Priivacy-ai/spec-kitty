# Phase 0 Research: Gate-Artifact Merge Driver Unit Gate (#3232)

Pre-spec research (researcher-robbie, on `main` `ada9b45c2`). Full brief: scratchpad
`3232-scoping-brief.md`.

## Decision: test the pure row-union reconcilers directly, in memory

- **Chosen**: call `reconcile_acceptance_matrix_documents(base, ours, theirs) -> dict`
  (`src/specify_cli/cli/commands/merge_driver.py:608`) and
  `reconcile_issue_matrix_documents(base, ours, theirs) -> dict` (`:536`) with in-memory JSON dicts.
- **Rationale**: these are pure `Mapping → dict` functions (no I/O, no subprocess). The acceptance
  reconciler row-unions `criteria` (by `criterion_id`) + `negative_invariants` (by `invariant_id`) and
  **recomputes** `overall_verdict` via `AcceptanceMatrix.from_dict(...).to_dict()` (never trusts a
  side's stale verdict string). `_merge_field(base, ours, theirs)` returns `ours` when `theirs == base`
  (filled side wins cleanly over an unchanged scaffold), and embeds both values in a git-style conflict
  marker (`_field_conflict_marker`, `:355`) when both diverge — so an accepted evidence handle survives
  even inside a conflict. `AcceptanceCriterion` (`acceptance/matrix.py:139`) round-trips `evidence`/
  `notes`/unknown `extras`, so handles survive `from_dict`/`to_dict`.
- **Alternatives considered**: (a) re-pin at integration level — rejected, that is the existing ~160 s
  subprocess marker (out of scope, C-001); (b) rebuild the deleted 249-line unit gate as-was — rejected,
  it tested `_acceptance_matrix_fill_score`/`_issue_matrix_fill_score` whole-file heuristics that #3076
  **removed from `src/`** (zero grep hits); the invariant must be stated against the row-union model.

## Decision: the ownership gap is real and narrow

- **Chosen**: a ~6-test #2804-specific overlay, not a from-scratch rebuild.
- **Rationale**: the row-aware sibling `tests/specify_cli/cli/commands/test_row_aware_merge_driver.py`
  already covers the *general* row-union contract (disjoint-row union, verdict recompute-vs-stale,
  negative_invariants keying, structured conflict on same-field pass/fail, byte-determinism, corrupt-JSON
  exit). What no test pins: the **#2804-specific** "filled/accepted criterion is never reset to
  `SCAFFOLD_TODO_MARKER`, accepted evidence handle survives (incl. in a conflict marker)" framed with the
  real scaffold marker + evidence handle. The integration marker covers it end-to-end but slowly and via
  subprocess. Confirmed: no driver-level test owns this — the gap the deleted file left is unfilled.

## Decision: admit `pending` (do not fix #3231)

- **Chosen**: `ADMISSIBLE_MERGED_VERDICTS = {pass, pending, pass_pending_consolidation}` (the computed
  verdict domain minus `fail`).
- **Rationale**: a merged document that admits a scaffold row yields `overall_verdict == pending` by
  design (row-union authority, #3076 FR-008). The product concern that `pending` blocks acceptance is
  #3231 — a separate filed defect whose candidate fix would amend FR-008. This gate must therefore
  **admit** `pending`; a control that demanded `pass` would silently encode the #3231 fix. This is what
  makes the re-pin legitimate rather than a red made to disappear.

## Decision: no arch-guard / dead-symbol interaction

- **Chosen**: touch only the one test file; no baseline/golden updates.
- **Rationale**: both reconcilers are already imported by the sibling → not dead (`test_no_dead_symbols`/
  `test_no_dead_modules`/`_baselines.yaml` untouched). `test_merge_reconciliation_class_guard.py` guards
  `.gitattributes`↔driver-registry drift — orthogonal to a unit test. `tests/merge/` has no exact
  file-count arch ratchet (that ratchet is for `tests/architectural/`), so adding one file needs no
  `_ARCH_SHARD_N_FILES`/golden bump.

## Marker state note (out of scope, flagged)

The integration marker `tests/merge/test_issue_2804_merge_resets_gate_artifacts.py` on `main` still
carries its own assertion form (from the closed mission `meta-fail-closed-3162` / PR #3247, which was
**not merged**). That marker is C-001 out of scope; treat any red it shows as pre-existing, not this
mission's.
