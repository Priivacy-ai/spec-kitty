# Implementation Plan: CI suite-map bind — marker→job authority + coherence invariants (Wave 0 full)

**Branch**: `tidy/ci-suite-map-2034` | **Date**: 2026-07-04 | **Spec**: [spec.md](spec.md) (rev 3 — renata-hardened + #2333 folded in-mission)
**Input**: Mission specification from `/kitty-specs/ci-suite-map-bind-01KWNPMP/spec.md`

## Summary

Bind the WS5 CI suite-map seam via the AC's **CI-validated** arm (Adjudicated Decision 1 — no workflow generator): a three-state marker-completeness invariant (ROUTED-BY-MARKER / ROUTED-BY-PATH / reasoned `CI_INVISIBLE`, with `unit`/`contract` hard-asserted ROUTED-BY-MARKER), a small always-on `unit-contract-residual` CI job (~252 pure-logic tests), the WS5 coherence invariants (needs-declaration, filter-output consumption, glob-liveness, diff-cov backing, workflow-set completeness) plus fixes for the live incoherences they surface (bounded set), the #2296 orphan-baseline drain to zero, `ci-windows.yml` path widening, AND the folded #2333 path-topology tail (operator ruling): src-side filter coverage with a fail-closed catch-all, skipped-suite fail-closed visibility in quality-gate, guard self-mapping, `--ignore` mirror coherence. Executes #2297 + #2296 + #2333; closes #2034 and #2283 factor (a).

## Technical Context

**Language/Version**: Python 3.11 (repo standard; `.python-version` 3.11.15)
**Primary Dependencies**: pytest (+ `_pytest.mark.expression.Expression` — private-API dependency carried forward from `_gate_coverage.py`, pinned + loud-fail documented), PyYAML (workflow parsing), pytest-xdist; no new external dependencies
**Storage**: N/A — governance state = `tests/architectural/_gate_coverage_baseline.json` (regenerated to 0 orphans), the new `CI_INVISIBLE` mapping (in-test constant or sibling data file, reasoned per entry), `pytest.ini` markers block (read-only authority, C-006)
**Testing**: new invariants live in `tests/architectural/` (CI-selected via the architectural shard, NFR-005); fault-injection proofs per invariant on fixture YAML; the residual job's own selection dry-run pre-merge (C-007); full `tests/architectural/` sweep + targeted gate-coverage runs per WP
**Target Platform**: Linux CI (ci-quality.yml) + Windows CI (ci-windows.yml trigger widening only)
**Project Type**: single — existing layout; new arch tests + `ci-quality.yml`/`ci-windows.yml` edits + baseline regen
**Performance Goals**: NFR-001 invariants < 5 s combined (states i/iii collection-free; state ii reuses the orphan model's cached collection); NFR-002 residual job < 3 min on CI
**Constraints**: C-001 no generator/third artifact; C-002 refactor-stable parsed relations only; C-003 shrink-only reasoned ledgers; C-004 `workflow` OAuth scope verified EARLY; C-005 quarantine untouched; C-006 pytest.ini sole registry; C-007 land green incl. own gates
**Scale/Scope (post-fold)**: 37 registered markers × 56 parsed gates (debbie re-derived); ~252-test residual; 4 orphan files to drain; 2 workflow files edited (incl. quality-gate aggregator semantics + the 20-group filter block); ~6-9 invariant tests; 2 named + N same-class incoherence fixes (bounded, FR-004); src-coverage census 347/801 unmatched specify_cli files + src/glossary zero-group → catch-all + targeted groups

## Charter Check

*GATE: evaluated against `.kittify/charter/charter.md` (compact context).*

- **Single canonical authority**: ✅ the mission's essence — pytest.ini stays the only marker registry (C-006); the parsed gate model stays the only selection model; explicitly REJECTS minting a third source (Adjudicated Decision 1). Path-topology authority rule (Decision 8): the filter block + job `if:` gates are the ONLY two source authorities; every derived surface (catch-all OR-list, aggregator job→group table, invariants) is asserted-against the parsed sources — a free-standing literal copy is a reject.
- **Quality & Tech-Debt Standing Orders**: ✅ squad cadence honored (pre-spec 3-lens + post-spec renata → rev 2); campsite: the glossary-lock orphan fix already shipped pre-spec; canonical sources (issue bodies superseded by the live census, recorded).
- **ATDD-first / red-first**: adapted — every invariant lands with fault-injection proof (synthetic marker → red; de-route → red; ineligibility → red even-if-allowlisted); the residual job's green run on the real set is the acceptance evidence.
- **Architectural gate discipline**: ✅ all ratchets shrink-only with honest re-derived counts (NFR-003/NFR-004); gate-unmask discipline bound as C-007 (pre-merge dry-run of the mission's own gates).
- **Terminology canon**: ✅.
- **Git/workflow discipline**: ✅ planning on `tidy/ci-suite-map-2034`; lands on upstream main via PR only; operator merges. C-004 workflow-scope risk surfaced as an early verification task.

No violations → Complexity Tracking empty.

## Project Structure

### Documentation (this mission)

```
kitty-specs/ci-suite-map-bind-01KWNPMP/
├── spec.md               # rev 3 (renata-hardened + #2333 fold)
├── issue-matrix.md       # tracker verdicts (incl. #2333 in-mission)
├── plan.md               # this file
├── research.md           # Phase 0: squad-synthesis decisions R1–R8
├── quickstart.md         # per-WP and merge-time validation commands
├── contracts/            # N/A-by-design record (executable contracts = the invariant tests themselves)
└── tasks.md + tasks/     # Phase 2 (/spec-kitty.tasks)
```

`data-model.md`: N/A by design — no data entities; the "model" is `_gate_coverage.Gate` which already exists. Recorded so downstream gates don't read absence as omission.

### Source Code (repository root)

```
ADD:
tests/architectural/test_marker_job_completeness.py   # FR-001 three-state invariant + CI_INVISIBLE ledger + ineligibility hard-assert
tests/architectural/test_workflow_coherence.py        # FR-003 needs/filter/glob relations + FR-005 cov-backing + FR-008 workflow-set completeness
                                                      # (single file or split — tasks decide; both reuse _gate_coverage parsing)
tests/architectural/test_src_filter_coverage.py       # FR-010 src-coverage invariant + FR-012 ignore-mirror + guard self-mapping relations
                                                      # (naming/split per tasks; same parse substrate)

EDIT:
tests/architectural/_gate_coverage.py                 # extend the parse model where needed (needs: lists, filter outputs/consumers,
                                                      # diff-cover critical-paths, --cov emitters) — additive, no behavior change to existing checks
tests/architectural/_gate_coverage_baseline.json      # regenerate: orphans → 0 (FR-006), honest duplicate count re-derived (NFR-003)
.github/workflows/ci-quality.yml                      # FR-002 unit-contract-residual job (+ quality-gate needs/result wiring);
                                                      # FR-006 shard path additions (tests/coordination, tests/paths [+ _support adjudication]);
                                                      # FR-004 bounded incoherence fixes (mission-loader-coverage reachability, mission_runtime cov backing);
                                                      # FR-010 filter-block: targeted groups + fail-closed src/** catch-all;
                                                      # FR-011 quality-gate: run/skipped step-summary table + improperly-skipped-mapped-suite failure arm;
                                                      # FR-012 guard self-mapping groups (.github/workflows/**, tests/architectural/**)
.github/workflows/ci-windows.yml                      # FR-007 trigger paths → src/** (or reasoned exclusions)

NO-TOUCH:
pytest.ini                                            # read-only authority (C-006) — unless FR-004 verification demands a marker doc fix (record if so)
tests/architectural/test_gate_coverage.py             # existing set-level ratchet stays as-is (Decision 4); only the baseline regenerates
```

**Structure Decision**: single-project layout unchanged; all new enforcement lives in `tests/architectural/` beside its precedents.

## Implementation Concern Map

> Concerns are not WPs; `/spec-kitty.tasks` translates them. Squad topology guidance (paula, ~7 WPs):
> WP01 scope-preflight → WP02 sole-owner `_gate_coverage.py` extension → Lane A serializes ALL `ci-quality.yml` edits
> (residual job + fixes + drain / catch-all + FR-013 + self-mapping / aggregator arm last, riskiest) →
> Lane B invariant tests author in parallel on fixtures but LAND after Lane A (they red on live workflows until then;
> FR-001 + FR-002 green together at every landed commit) → closeout. Two spine files, both single-owner.

### IC-01 — Workflow-scope preflight (C-004)

- **Purpose**: prove the push path for `.github/workflows/` edits from this checkout BEFORE work stacks behind it (a trivial probe branch push; document the result).
- **Sequencing**: first, tiny.
- **Risks**: scope missing → the whole FR-002/FR-004/FR-006/FR-007 surface is blocked; discovering that late is the failure mode #2296 warns about.

### IC-02 — Parse-model extension (FR-003/FR-005/FR-008 substrate)

- **Purpose**: extend `_gate_coverage.py` additively: parse `needs:` lists, `needs.<job>.result` reads in run scripts, dorny filter outputs + `if:` consumers, filter globs, the diff-cover critical-path list, `--cov` emitters, and the pytest-invoking-workflow set. Pure parsing, no assertions yet.
- **Sequencing**: after IC-01; enables IC-03/IC-04.
- **Risks**: over-parsing the 2,915-line workflow (keep to the relations the FRs name — C-002); breaking the existing orphan model's consumers (additive-only; existing tests stay green untouched). NOTE (paula): `_gate_coverage.py` is a SECOND single-owner spine — extend it in ONE early WP, read-only thereafter (Wave-2 spine lesson).

### IC-03 — Marker-completeness invariant (FR-001)

- **Purpose**: the three-state test + `CI_INVISIBLE` reasoned ledger + `unit`/`contract` ineligibility hard-assert + fault-injection proofs. Derive the honest state membership (8 routed-by-marker today; the routed-by-path vs invisible split per marker, verified against the orphan model).
- **Sequencing**: after IC-02. NOTE: the invariant reds on `unit`/`contract` until FR-002's job exists — the invariant and the residual job must be green TOGETHER at every commit that ships both (tasks sequence them in one lane or same WP).
- **Risks**: mislabeling a path-routed marker invisible (the C-003 dumping-ground renata flagged); the negation-aware token extractor mishandling `not windows_ci` (edge case pinned in spec).

### IC-04 — Coherence invariants (FR-003/FR-005/FR-008)

- **Purpose**: needs-declaration, filter-consumption, glob-liveness, quality-gate loop↔needs symmetry, cov-backing, workflow-set completeness — each with fixture fault-injection.
- **Sequencing**: after IC-02; before/with IC-05 (the fixes make the live workflows pass).
- **Risks**: relation-set creep beyond the FR-named six (bounded by FR-004's class rule); false positives on conditional `if:` label logic (parse to the relation; don't evaluate GitHub expressions).

### IC-05 — Workflow edits: residual job + bounded fixes + drain + widening (FR-002/FR-004/FR-006/FR-007)

- **Purpose**: the `unit-contract-residual` job (always-on, not draft-gated, blocking in quality-gate needs+loop); re-verify the 3 named FR-004 candidates (charter phantom likely already fixed → record); fix `mission-loader-coverage` reachability + `mission_runtime` cov backing; add `tests/coordination`/`tests/paths` shard paths + adjudicate `_support/git_template`; regenerate the baseline to 0; widen `ci-windows.yml` triggers.
- **Sequencing**: after IC-03/IC-04 exist locally (they define green); `ci-quality.yml` edits stay single-owner.
- **Risks**: draft-gating semantics (verify quality-gate behavior for drafts); duplicate-count regression (NFR-003 re-derive); the residual set hiding a non-pure test (debbie sampled green; the full run is the proof).

### IC-06 — Path-topology: filter coverage + guard self-mapping + ignore mirrors (FR-010, FR-012, FR-013; folded #2333, squad-hardened)

- **Purpose**: mechanism per HiC ruling 7b + paula: `any_src` probe group + script step computing `unmatched` FROM the filter's own outputs (negated mega-glob FORBIDDEN), threaded into the existing `run_all` OR-seam (~:84-103) — run_all semantics, no per-job `if:` surgery; targeted groups where a natural owner exists (`src/glossary` at minimum); FR-013 `ready_for_review` trigger type; two-layer self-mapping for the NON-ci-quality workflows (outer `on: paths:` + dorny group; ci-quality/tests-architectural already self-map via core_misc — record); invariants are PARSED RELATIONS (catch-all OR-list ≡ group set; ignore-lists ≡ shard-owned roots) with reorder red-negatives.
- **Sequencing**: after IC-02 (parse substrate); the workflow edits co-tenant with IC-05's file — same single owner or serialized lanes.
- **Risks**: the catch-all mis-scoped → every PR runs the full suite (CI-minute blowup — the catch-all must trigger ONLY on unmatched src changes, verify with probe diffs); 75-child enumeration temptation (the catch-all is the fail-closed answer; enumerate only natural owners); ignore-mirror relation must be parsed (set equality vs shard-owned roots), not literal list duplication (C-002).

### IC-07 — Aggregator semantics: skipped-suite fail-closed + visibility (FR-011; folded #2333)

- **Purpose**: quality-gate emits the run/skipped table to `$GITHUB_STEP_SUMMARY`; FAIL iff `filter_true AND job_skipped AND NOT full_run AND NOT draft_exempt` (paula's decision table, spec FR-011); SCOPE = blocking `needs:` jobs only (quarantine-visibility stays non-blocking — C-005); the job→group mapping asserted ≡ parsed job-`if:` gating (Decision 8), never a bash table; decision logic EXTRACTED into a testable script with fixture tests (draft case, skipped-mapped case, supersede case). Draft semantics resolved by FR-013 + GitHub's native draft-merge block.
- **Sequencing**: after IC-05 (the residual job + needs wiring settle the aggregator's input set); the single riskiest edit in the mission — the aggregator guards every merge.
- **Risks**: false-red on legitimately-skipped suites (superseded-by-full-run and not-triggered must be distinguished from improperly-skipped); breaking the aggregator breaks every PR — needs fixture-level tests of the gate script logic itself (extract the decision into a testable script if the bash is untestable, per Sonar/testability doctrine) + a probe PR run before merge (C-007).

### IC-08 — Closeout (FR-009)

- **Purpose**: tracker comments (#2297/#2296/#2034/#2333 close-by-PR; #2283 partial; #1868 WS5 checklist — after this mission only the mypy-scope AC stays open), roadmap Wave-0 strike, pre-merge dry-run evidence (C-007), NFR re-derivations recorded.
- **Sequencing**: last.
- **Risks**: premature issue closure (the PR closes; comments don't).

## Complexity Tracking

*(empty — no charter violations)*
