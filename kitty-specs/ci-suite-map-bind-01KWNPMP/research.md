# Research — ci-suite-map-bind-01KWNPMP (Phase 0)

Decisions derive from the pre-spec 3-lens squad (debugger-debbie live census, planner-priti tracker sweep, architect-alphonso design lens — all 2026-07-04 against `tidy/ci-suite-map-2034` @595c50ff8) + the post-spec renata pass (folded as spec rev 2) + the operator fold ruling (rev 3). Divergences adjudicated from source, never averaged.

## R1 — Generator vs CI-validated invariants (the priti/alphonso divergence)

Priti read #2297's body ("a single machine-readable suite-map that GENERATES the marker selection…") as mandating generation. Alphonso rejected the generator: no generated-workflow precedent in this codebase (graph.yaml's byte-for-byte pattern fits denormalized data with a clean generator, not imperative hand-tuned CI); a suite-map source file would be a THIRD artifact with its own split-brain risk; the entire existing enforcement family (`_gate_coverage.py`, `test_ci_quality_path_filters.py`, `test_marker_registry_single_source.py`) is parse-and-assert. **Adjudicated from the governing source**: epic #1868 WS5's acceptance criterion itself reads "generated **or CI-validated**; divergence fails an architectural test" — the CI-validated arm is explicitly sanctioned. Decision: bind invariants over the parsed model; the "machine-readable suite map" IS `_gate_coverage`'s `Gate` model. (Spec Adjudicated Decision 1 / C-001.)

## R2 — The #2034 census is stale; the honest surface

Debbie re-derived everything live: PR #2294 bound 365/369 orphan files (17 pre-existing reds quarantined → #2295/#2309); PR #2047 single-sourced the marker registry (pytest.ini authoritative, `test_marker_registry_single_source.py` guards it — 2 passed); ALL 9 of #2034's named hidden failures now PASS (exact-nodeid runs; the SEO case's input file was deleted); the shims/test_registry parallel-collection nondeterminism is fixed (`sorted(...)`). Live orphan floor: 17 tests / 4 files (after the pre-spec fix of Wave 2's glossary lock, which the ratchet caught as a new orphan — proof the machinery works). Only 8 of 37 registered markers are positively `-m`-referenced by any gate; no gate selects `unit`/`contract`; no unfiltered run exists (the nightly collapses path filters, never marker filters).

## R3 — Three-state marker model (renata HIGH-2 fold)

A naive routed-or-invisible invariant would red ~27 of 37 markers, and ~15 of those (`e2e, doctrine, agent, upgrade, distribution, orchestrator_*, regression, adversarial`…) are CI-visible via PATH gates — forcing them into `CI_INVISIBLE` would mislabel running tests as invisible (the C-003 dumping-ground failure). Decision: three states — ROUTED-BY-MARKER (positive token, negation-aware `Expression` AST walk), ROUTED-BY-PATH (every collected test carrying the marker reaches ≥1 path gate, verified against the orphan model — not hand-asserted), CI_INVISIBLE (reasoned ledger). `unit`/`contract` are HARD-INELIGIBLE for states 2 and 3 (renata MEDIUM-3: otherwise the allowlist defeats the mission).

## R4 — Residual job, not `-m "unit or contract"`, not shard-widening

`unit or contract` selects 11,088 tests (~39% of suite, ~10.8k already routed → duplicate blowup). The residual expression collects ~252 (renata re-derived; debbie's marker-only view saw 273/29 files — the delta is expression semantics; re-derive at implement, NFR-004). Shard-widening (`fast or unit`) pulls unit-only tests into path-scoped shards inconsistently. Decision: one small always-on job; `windows_ci`/`quarantine` excluded per convention; blocking in quality-gate (declared AND read — the invariants pin it).

## R5 — FR-004 is bounded; one named candidate already fixed

Renata verified `integration-tests-charter` is declared in quality-gate's `needs:` (~:2938) AND read (~:2988) — the epic-census phantom is likely already fixed (re-verify at plan/implement; record verified-already-fixed). Still-live named candidates: `mission-loader-coverage` absent from quality-gate's needs/loop; `src/mission_runtime/*` in diff-cover critical paths with zero `--cov=src/mission_runtime` emitters. The fix-set is bounded to named candidates + same-class discoveries of the FR-named relations; anything beyond is out (was #2333's class — now folded, see R8).

## R6 — Escape-hatch design: allowlist, not quarantine

The #2317 quarantine-lane precedent solves env-flaky TESTS; this mission's unroutable dimension is MARKERS. The `CI_INVISIBLE` reasoned ledger is the structural twin of the quarantine lane's honest stay-behind reasons, at the right granularity. Fix-all-before-gate for the residual tests themselves (currently all green — debbie ran the orphan set: 17 passed + 1 skipped, and the glossary pair: 2 passed).

## R7 — Tracker topology (priti)

Native parent #1868 (WS5 is exactly this seam); #1931 is the historical/context home — cross-reference only (no domain-matching campsite folds among its children). #2109 already CLOSED (verified). #2295/#2309 stay independent (the residual expression excludes `quarantine`; cannot re-surface them). #2283 factors (b)/(c) → CT7 #2077. Claims posted at spec time on #2297/#2296/#2034 (full) + #2283 (partial) + #1868 (WS5 update).

## R8 — The #2333 fold (operator ruling, rev 3)

Renata's HIGH-1 found the spec silently dropped WS5 AC-2a/AC-6/AC-8/AC-1-partial; rev 2 deferred them to #2333 as a different risk class (aggregator semantics + filter-block surgery). **Operator overruled the deferral** (2026-07-04): the Wave-0 remainder is thin; deferring hurts. Folded as FR-010..FR-012 with these design decisions:
- **AC-2a via fail-closed catch-all, not 75 enumerated groups**: targeted filter groups only where a natural owner shard exists (`src/glossary` at minimum); everything unmatched falls to a new catch-all group that forces the full-run path. The invariant pins matched-or-caught (satisfiable by construction, refactor-stable) rather than a hand-census.
- **AC-6 as an aggregator arm**: "improperly skipped" = filter output true ∧ job not run ∧ not superseded by the full-run path. The quality-gate decision logic should be extracted into a testable script if the inline bash resists fixture testing (Sonar testable-extraction doctrine). Riskiest edit in the mission — probe PR before merge (C-007).
- **AC-8**: `.github/workflows/**` + `tests/architectural/**` mapped to the architectural shard (a gate edit re-runs the guards).
- **AC-1 partial**: the two catch-all `--ignore` lists asserted equal (as parsed sets) to the shard-owned test-root topology — relation, not literal mirror.

## Rejected alternatives (recorded)

- Workflow generator + byte-for-byte freshness gate (R1) — no precedent, third artifact, high blast radius.
- Dedicated `-m "unit or contract"` job (R4) — 11k tests, duplicate blowup.
- Widening existing shards' `-m` expressions (R4) — inconsistent path-scoping, shard bloat.
- Two-state marker invariant (R3) — mislabels ~15 path-routed markers.
- #2317-style quarantine lane for unroutable markers (R6) — wrong granularity.
- Deferring the path-topology tail to #2333 (R8) — overruled by operator; folded.
