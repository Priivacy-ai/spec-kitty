# Issue Matrix — ci-suite-map-bind-01KWNPMP

<!-- Schema: issue | title (optional) | verdict | evidence ref (mandatory) -->
<!-- Valid verdicts: fixed | verified-already-fixed | deferred-with-followup | in-mission -->

| Issue | Title | Verdict | Evidence ref |
|---|---|---|---|
| #2297 | closes: Wave 0 (full) — CI suite-map authority | in-mission | FR-001..FR-008 via the WS5 "generated or CI-validated" arm: parsed-model invariants (Adjudicated Decision 1), residual job, coherence fixes. PR closes. |
| #2296 | closes: Wave-0 tail — 4 orphan path additions | in-mission | FR-006: 3 files routed via shard path additions; `_support/git_template` adjudicated route-or-record; baseline → 0. PR closes. |
| #2034 | closes: no gate selects `unit`/`contract` | in-mission | Census rev (Squad-Verified Census): all 9 named failures already fixed; registry dedup done (#2047); remaining core = FR-001 invariant + FR-002 gate. PR closes after a closeout re-read of the thread for residual obligations. |
| #2283 | partial: test-delivery topology | deferred-with-followup | Factor (a) closed by FR-001/FR-002; factors (b)/(c) stay OPEN under #2283, pointed at CT7 #2077 (closeout comment, FR-009). |
| #1868 | parent epic (WS5 seam) | deferred-with-followup | Native parent; WS5 ACs bound here: marker→job authority (CI-validated arm), needs-coherence, filter-consumption, glob-liveness, diff-cov backing, workflow-set completeness, orphan baseline→0, ci-windows widening. Staying OPEN under #1868: the mypy-scope AC only (path-topology tail folded in via #2333). |
| #1931 | test-quality epic (cross-ref) | deferred-with-followup | Context home for #2034; no children folded (priti sweep: none domain-matching). Remainder continues under #1931. |
| #2295 | 17 CI-quarantined tests triage | deferred-with-followup | OUT (C-005): quarantined by #2294, excluded from the new gate by design; stays open under #2295. |
| #2309 | daemon-reaper kill-gate contradiction | deferred-with-followup | OUT (C-005): subset of the #2295 quarantine set; stays open under #2309. |
| #2077 | CT7 mechanise sweeps (cross-ref) | deferred-with-followup | Receives #2283 factors (b)/(c) per the closeout comment; stays open under #2077. |
| #2333 | closes: WS5 path-topology tail | in-mission | FOLDED IN-MISSION per operator ruling 2026-07-04 (Wave-0 remainder thin; deferring hurts): FR-010 src-side filter coverage + fail-closed catch-all, FR-011 skipped-suite fail-closed + step-summary, FR-012 guard self-mapping + --ignore mirrors. PR closes. |
| #1933 | slowest-groups nightly / keep PR CI targeted | deferred-with-followup | Tension with FR-010 adjudicated (HiC ruling 7b): the run_all catch-all is a loud alarm with a shrink obligation, NOT steady-state full-runs; mapped PRs stay targeted. Reconciliation comment at closeout; remainder stays under #1933. |
| #2316 | upgrade-UX uv-tool drift (skipped tests) | deferred-with-followup | OUT — not domain-matching (upgrade-domain behavioral adjudication, no marker/job-topology surface); stays under #2316. |
| #2329 | accept hardcoded src/+tests/ paths (Go) | deferred-with-followup | OUT — different "src": the software-dev mission's accept-path convention in consumer repos, not this repo's CI dorny globs; stays under #2329/#2330. |
| #2330 | Go-friction umbrella | deferred-with-followup | OUT — same reasoning as #2329; cross-referenced only; stays under #2330. |
| #2109 | 4 red orphan tests | verified-already-fixed | CLOSED on tracker; priti verified all 4 pass on main post-#2294/#2299. Reference only. |
| #2294 | orphan-file binding PR (365/369 bound) | verified-already-fixed | MERGED prior PR, cited in census prose (spec.md:11, research.md:11) as the source of the 17-test/4-file orphan floor. Reference only. |
| #2319 | snapshot-drift fix PR | verified-already-fixed | MERGED prior PR, cited in census prose (spec.md:11) as fixing the snapshot cases among #2034's 9 named failures. Reference only. |
| #2047 | marker-registry dedup (PR) | verified-already-fixed | MERGED; pytest.ini single source + guard test. This mission depends on it (C-006). |
