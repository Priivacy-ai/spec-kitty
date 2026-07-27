# Verification Ledger — Doctrine-activation freshness integrity

Tracer (seeded at planning; the falsifiable checklist; tick during implement, assess at close).

## IC-01 — #2770 shipped-DRG un-pin (early standalone, acceptance signal)
- [ ] Shipped `src/doctrine/*.graph.yaml` regenerated; `spec-kitty doctrine regenerate-graph --check` green.
- [ ] Charter→reference citation compiled; `test_no_new_charter_reference_danglers` passes with `@regression` removed.
- [ ] `TestDRGZeroDelta::{test_regenerated_graph_matches_baseline_counts, test_shipped_graph_is_fresh_and_byte_identical}` pass un-pinned; baseline re-frozen to the COMPUTED delta (not guessed).
- [ ] `test_check_reports_committed_graph_fresh` passes un-pinned.
- [ ] No `@pytest.mark.regression` remains on the 4 tests; the non-blocking CI gate no longer carries them.

## IC-02 — #2758 references.yaml fail-closed preflight
- [ ] Missing `references.yaml` no longer yields a permanent-stale `None` (red-first repro through `compute_freshness`/synthesize).
- [ ] Fail-closed preflight surfaces a single actionable "run `charter generate`" message (hoisted constant).
- [ ] 4-file hash set UNCHANGED (`bundle.py:47`, `computer.py:137`, `CANONICAL_MANIFEST.derived_files` all as-is — no narrowing).
- [ ] Hash of a COMPLETE bundle is byte-unchanged (NFR-002 preserve).

## IC-03 — #2759 seam core (parity into freshness read-path)
- [ ] Red-first: on a fresh project, `charter activate <kind> <id>` → `_compute_synthesized_drg` reports STALE (was fresh). SC-002.
- [ ] Reconcile returns the signal to FRESH.
- [ ] `run_consistency_check` REUSED (not reimplemented); called from `computer.py`, still callable from `pack.py:30` CLI.
- [ ] `deactivate` symmetric; cascade activation reconciles once.
- [ ] Fresh-seed early-exit (`computer.py:367-408`) still short-circuits (no spurious stale on never-synthesized).
- [ ] Writer-agnostic: a `merge_defaults`-seeded activation is also visible (DD-01).
- [ ] `_compute_synthesized_drg` ≤15 complexity / ≤6 returns after extraction; `_check_reference_id_parity` pre-extracted.
- [ ] NFR-002: unchanged bundle → unchanged hash; #2732 recipe/stamps/normalization/fresh-seed all intact.

## IC-04 — #2157a one-pass prerequisite gate
- [ ] Red-first: multiple charter-owed prerequisites stale → implement preflight reports ALL in one pass (was raise-on-first). SC-004.
- [ ] Per-prerequisite verdicts unchanged (aggregation is additive).
- [ ] C-004: `analysis_report.check_analysis_report_current` (2157b) UNTOUCHED.
- [ ] `["spec-kitty","charter",…]` prefix hoisted (≥3× → constant).

## IC-05 — --resynthesize + hot-path guards
- [ ] `charter activate … --resynthesize` leaves the signal FRESH immediately.
- [ ] Default `charter activate …` leaves it STALE and spawns ZERO synthesis/regenerate subprocess (spy). NFR-001.
- [ ] `deactivate --resynthesize` symmetric.
- [ ] NFR-003: upgrade migration + `org_charter` `promote_activations` trigger no synthesis (spy/assertion).
- [ ] `commit_plan` (`activation_engine.py`) UNTOUCHED (C-001); the eager orchestration lives in `specify_cli` CLI.

## Cross-cutting gates
- [ ] ruff + mypy `--strict` clean, zero new suppressions; complexity ≤15.
- [ ] `tests/architectural/` green (fences hold); `tests/doctrine/drg/` freshness green.
- [ ] terminology guard green if prose touched.
- [ ] issue-matrix: #2770/#2759/#2758/#2157 reach terminal verdicts before `done` (in-mission → fixed).
