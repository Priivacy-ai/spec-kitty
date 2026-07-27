# Mission Specification: CI suite-map bind — marker→job authority + coherence invariants (Wave 0 full)

**Mission Branch**: `tidy/ci-suite-map-2034`
**Created**: 2026-07-04
**Status**: Draft (rev 4 — plan-review squad folds: FR-010 de-vacuoused + run_all mechanism (HiC ruling), FR-011 decision table + C-005 aggregator scope, FR-012 narrowed to the real gap, FR-013 ready_for_review trigger (HiC ruling), reverse-containment, #1933 reconciliation)
**Input**: Roadmap Wave 0 (docs/plans/degod-unshim-roadmap.md:40) under epic #1868 WS5; executes #2297 + #2296; closes the #2034 marker gap and #2283 factor (a).

## Adjudicated Decisions (binding — do not re-litigate)

1. **CI-VALIDATED invariants, NOT a workflow generator.** #2297's body says "GENERATES", but the governing WS5 acceptance criterion reads "generated **or CI-validated**; divergence fails an architectural test" — and the codebase's entire CI-enforcement precedent is parse-and-assert (`_gate_coverage.py`, `test_ci_quality_path_filters.py`, `test_marker_registry_single_source.py`). A generator over the hand-tuned 2,915-line `ci-quality.yml` would mint a third source of truth (split-brain risk) with no precedent. The "machine-readable suite map" deliverable is the **parsed gate model** (`_gate_coverage.load_gates()`) plus the invariant suite bound over it. (alphonso Q1; rejected alternative recorded in research.)
2. **The #2034 census is STALE — this is a binding-layer mission, not a rescue.** Live census (debbie, 2026-07-04 @595c50ff8): PR #2294 already bound 365/369 orphan files; PR #2047 already single-sourced the marker registry (pytest.ini authoritative, guarded); ALL 9 named hidden failures now PASS (kwarg drifts fixed by degod waves, snapshots by PR #2319, SEO page deleted, home-literals cleaned); the parallel-collection nondeterminism is fixed (`sorted(...)` + docstring). True residue: **17 zero-gate tests / 4 files live (19/5 at census, glossary lock fixed pre-spec; all green)** + **~273 marker-only tests** mostly covered by path-only gates. Do not spec against the issue body's numbers.
3. **Residual job, NOT a `-m "unit or contract"` job and NOT shard-widening.** A dedicated `unit or contract` job would run 11,088 tests (~39% of suite, ~10.8k double-run). The gate is a small always-on job selecting only the residual expression (`(unit or contract) and not (<every routed runnable marker>)`) — ~252 pure-logic tests at spec time (renata re-derived; re-derive at implement per NFR-004), seconds. (alphonso Q3.)
4. **Marker-completeness is name-level; the existing orphan ratchet stays set-level.** Two complementary invariants: the new one asserts every registered marker NAME is positively referenced by ≥1 gate or CI-invisible-with-reason; `test_gate_coverage.py` keeps asserting every test's marker SET reaches ≥1 gate. No duplication of combination-reachability. (alphonso Q2.)
5. **Fix-all-before-gate; a THREE-STATE marker model (renata HIGH-2 fold — honest sizing).** Live introspection: only 8 of 37 registered markers are positively referenced in any gate `-m` expression (`fast, integration, git_repo, slow, architectural, timing, quarantine, windows_ci`); after FR-002 routes `unit`/`contract`, ~27 markers would red under a naive two-state invariant — but ~15 of those (`e2e, doctrine, agent, upgrade, distribution, orchestrator_*, regression, adversarial`…) are CI-visible via PATH gates, not invisible. Forcing them into `CI_INVISIBLE` would mislabel running tests as invisible (the C-003 dumping-ground failure). The invariant therefore models THREE states: **ROUTED-BY-MARKER** (positive `-m` token), **ROUTED-BY-PATH** (every collected test carrying the marker is reachable via ≥1 path gate — verified against the orphan model, not asserted by hand), and **CI_INVISIBLE** (reasoned allowlist for genuinely-unrun markers: `platform_darwin`, `live_adapter`, `exploratory`, `flaky`, `non_sandbox`, `timeout`, `asyncio`, `stress`…). Exact membership derived and recorded at implement time, shrink-preferred. **`unit` and `contract` are INELIGIBLE for both `CI_INVISIBLE` and ROUTED-BY-PATH** — the invariant hard-asserts they are ROUTED-BY-MARKER (renata MEDIUM-3: otherwise the allowlist could absorb them and defeat the mission). No #2317-style quarantine lane — the residual set is pure-logic and currently green. (alphonso Q5 + renata folds.)
6. **Out of scope with tracked homes**: #2283 factor (b) local venv skew → CT7/#2077 or a #2283 sub-item; factor (c) producer-conformance sweep → CT7/#2077; quarantine triage → #2295/#2309 (the new gate excludes `quarantine` by design and cannot re-surface them); mypy CI-scope expansion (WS5 sub-AC) → #1868 follow-up (needs an advisory-vs-enforced decision this mission doesn't own); **WS5 path-topology tail (#2333) → FOLDED IN-MISSION (operator ruling 2026-07-04: the remainder of Wave 0 is thin; deferring hurts)** — AC-2a src-side filter coverage, AC-6 skipped-suite fail-closed + step-summary visibility, AC-8 guard self-mapping, AC-1's `--ignore` mirror coherence are FR-010..FR-012; #2333 is closed by this mission's PR; marker-registry dedup → DONE (PR #2047), depend on it.
7. **HiC rulings on the path-topology mechanism (operator, 2026-07-04, after the plan-review squad):** (a) `ready_for_review` IS added to `ci-quality.yml`'s `on: pull_request types:` (FR-013) — without it a draft→ready PR never re-runs its draft-skipped suites (live merge-safety hole); with it, GitHub's native draft-merge block + the re-trigger make FR-011's draft exemption safe. (b) The FR-010 catch-all forces **run_all semantics** (every suite) via the existing `:84-103` OR-seam — a LOUD ALARM, not steady state: closeout adds named groups for hot unmatched dirs and records a shrink-trend obligation, reconciling #1933's keep-PR-CI-targeted intent (unmatched-hits trend to zero; mapped PRs stay targeted). Routing unmatched changes only to the core-misc jobs was REJECTED (they `--ignore` per-module dirs — wrong suites; paula). The static-only alternative was REJECTED (leaves the gap-window unrun).
8. **Path-topology authority rule (paula Q5):** path→suite topology has exactly TWO source authorities — the dorny filter block (path→group) and the job `if:` gates (group→job). Every derived surface this mission adds (the catch-all's group-reference OR-list, the aggregator's job→group table, the invariants) must be ASSERTED-AGAINST the parsed sources, never hand-maintained in parallel. A free-standing literal copy of either mapping is a REJECT (it would create the split-brain this mission exists to close).

## Squad-Verified Census (authoritative over issue bodies)

- **Gate inventory**: every `ci-quality.yml` job selects by marker (`fast`/`integration`/`git_repo`/`architectural`/`slow`/`timing`/`quarantine` + e2e-by-path); `mission-loader-coverage` and the focused lint steps are path-only; `slow-tests` runs on push only (PR-invisible, push-visible — documented, not a defect this mission fixes); the nightly schedule collapses path filters but never marker filters; **no gate selects `-m unit` or `-m contract`** (confirmed live).
- **Orphan population**: authoritative path+marker model reported 19 orphan tests / 5 files at census; the 5th file (Wave 2's glossary lock) was fixed pre-spec (marked `fast`), returning the live floor to **17 tests / 4 files** — matching the committed `_gate_coverage_baseline.json` (`orphan_test_count: 17`). Re-derive at implement (NFR-004).
- **Residual population**: ~273 nodes / 29 files carry `unit`/`contract`-class markers with no runnable routed marker (marker-only view); the residual EXPRESSION collects ~252 (renata re-derived); most are covered by path-only gates today; the residual job (FR-002) makes the whole class marker-reachable regardless.
- **Enforcement substrate**: `_gate_coverage.py` parses all 4 suite-running workflows into `Gate(paths, ignores, marker_expr)` and evaluates real collected tests via pytest's own `Expression`; `test_gate_coverage.py` is the file-level orphan ratchet; `test_ci_quality_path_filters.py` + `test_ci_architectural_gate_coverage.py` keep dorny filters honest; `test_marker_registry_single_source.py` pins pytest.ini as the registry.
- **WS5 live-gap status** (epic census at `aec70048` vs this branch): dark suite `tests/runtime/**` → **already routed** (fast-tests-next runs it) — verify-and-record, no work; phantom `needs:` (`integration-tests-charter.result`) → **renata verified LIKELY ALREADY FIXED** (declared at ~:2938 AND read at ~:2988) — re-verify at plan time and record verified-already-fixed if so; `quality-gate` aggregator excludes `mission-loader-coverage` → in FR-004's surface; vacuous `src/mission_runtime/*` diff-coverage entry → in FR-004's surface (cheap same-parse invariant).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A test authored with the documented default marker cannot be CI-invisible (Priority: P1)

A contributor writes a pure-logic test and marks it `unit` (the authoring default pytest.ini documents) or `contract`. Today that marker routes to no job — the test runs only if its file happens to carry a routed sibling marker or sit under a path-only gate. After this mission, `unit`/`contract` are positively selected by a real gate, and a registered marker that loses (or never gains) a selecting job fails an architectural test at PR time.

**Why this priority**: this is the #2034/#2283(a) root cause and the roadmap's Wave-0 rationale — every later degod wave's pure-core tests must actually run pre-merge.

**Independent Test**: register a synthetic marker in pytest.ini without routing it → the marker-completeness test REDS naming it; add it to `CI_INVISIBLE` with a reason → green; remove `unit` from the residual job's expression → REDS.

**Acceptance Scenarios**:

1. **Given** the merged branch, **When** the marker-completeness arch test runs, **Then** every marker in pytest.ini's `markers =` block is either positively referenced (non-negated token) in ≥1 gate's `-m` expression across the 4 suite-running workflows, or present in `CI_INVISIBLE` with a non-empty reason — and the test is sub-second (pure expression walk, no collection).
2. **Given** a PR that registers a new marker with no job and no allowlist entry, **When** CI runs, **Then** the architectural shard fails naming the marker (fail-closed on NEW).
3. **Given** a PR that edits a gate's `-m` expression such that a routed marker loses its only positive reference, **When** CI runs, **Then** the same test fails (fail-closed on DE-ROUTING; same mechanism, no separate machinery).

---

### User Story 2 - The unit/contract residual actually runs, cheaply (Priority: P1)

The ~252 tests carrying only authoring-taxonomy markers get a standing, always-on CI home that costs seconds — without double-running the ~10.8k unit tests that already ride `fast`/`integration` shards.

**Why this priority**: the gate is what makes US1's invariant satisfied *structurally* (the invariant demands a selecting job exist; this is that job).

**Independent Test**: `pytest -m "<residual expression>" --collect-only -q` collects ≈252 tests (re-derive) and the full selection passes locally in under a minute; the job appears in `quality-gate`'s `needs:` and result loop.

**Acceptance Scenarios**:

1. **Given** the new `unit-contract-residual` job, **When** it runs on any PR (always-on or src/tests-triggered; not draft-gated), **Then** it selects the residual expression, excludes `windows_ci` and `quarantine` per convention, and is a BLOCKING input to `quality-gate` (declared in `needs:` AND read in the result loop — no phantom).
2. **Given** the residual set as of spec time, **When** the job first runs, **Then** it is green (debbie: all 17 live orphans + residual sample currently pass; gate-unmask discipline — any red found at implement time is fixed or re-marked before the gate lands, never quarantined-by-default).
3. **Given** a future test authored `unit`-only, **When** it lands, **Then** it is selected by this job (no path dependence).

---

### User Story 3 - The workflow's duplicated topology knowledge cannot drift silently (Priority: P2)

The WS5 coherence invariants bind the relation subset this mission owns: every `needs.<job>.result` read in a run script is declared in that job's `needs:`; every dorny filter output is consumed by ≥1 job `if:`; every filter glob matches ≥1 tracked path; every diff-coverage critical-path entry is backed by a job emitting a matching `--cov`; every [ENFORCED] per-package gate is reachable from `quality-gate`. (The path-topology ACs — src-side filter coverage, skipped-suite fail-closed, guard self-mapping, `--ignore` mirrors — are IN-MISSION as US5/FR-010..FR-012 per the operator fold ruling; #2333 tracks them and closes with the PR.)

**Why this priority**: these are the WS5 AC(b)-(f) relations; the phantom-`needs:` class means a red suite can coexist with a green aggregator — the worst failure mode of the whole delivery topology.

**Independent Test**: each invariant has a fault-injection test proof at implement time (e.g., add a `needs.<x>.result` read without declaring `<x>` in a fixture copy → REDS).

**Acceptance Scenarios**:

1. **Given** the invariant suite, **When** it parses the live workflows, **Then** all live incoherences found at implement time have been FIXED in `ci-quality.yml` in the same mission (verified candidates from the epic census: the `integration-tests-charter` phantom read; `mission-loader-coverage` reachability from quality-gate; the vacuous `src/mission_runtime/*` diff-coverage entry) — and the invariants pass on the fixed workflow.
2. **Given** any future PR that reintroduces one of these incoherence classes, **When** CI runs, **Then** the architectural shard fails naming the relation violated.
3. **Given** the invariants, **When** a job is renamed or the YAML reordered without changing behavior, **Then** nothing reds (refactor-stable: keyed on parsed relations, never job names at line numbers or literal `-m` strings — C-006).

---

### User Story 4 - The orphan baseline drains to zero (Priority: P2)

The 4 files frozen in `_gate_coverage_baseline.json` (#2296) get their `ci-quality.yml` path additions (workflow-scope-gated), the baseline regenerates to zero orphans, and the ratchet floor locks there.

**Why this priority**: the clean termination condition for the Wave-0 orphan work; small, but it's the difference between "ratchet with a tolerated floor" and "zero-orphan invariant".

**Independent Test**: `python -m tests.architectural._gate_coverage --check` (or its test wrapper) reports `orphans: 0`; the baseline file records 0; the ratchet still fails-closed on any new orphan file.

**Acceptance Scenarios**:

1. **Given** the two `tests/coordination/` resolver tests and `tests/paths/test_windows_migrate.py`, **When** their dirs are added to the matching integration shard paths, **Then** they are selected by ≥1 gate and leave the baseline.
2. **Given** `tests/_support/git_template/test_git_template.py` (the issue flags "may be intentionally non-gated — decide"), **When** the mission adjudicates it, **Then** it is either routed like the others or explicitly recorded as intentionally non-gated with a rationale in the baseline/allowlist — no silent tolerated floor.
3. **Given** `ci-windows.yml`'s trigger paths (WS5 AC), **When** the mission lands, **Then** the Windows job's path triggers cover `src/**` (or the recorded per-package rationale for exclusions) so Windows-sensitive `src/mission_runtime` changes trigger it.

---

### User Story 5 - A src change can never silently skip its suites (Priority: P1, folded #2333)

Today a change confined to `src/glossary` (zero filter groups) or 43% of `src/specify_cli` children triggers the workflow but ZERO test jobs, and `quality-gate` passes because skipped-is-OK. After this mission: every `src/` surface is either matched by a filter group that gates a real job, or caught by a fail-closed catch-all that forces the full-run path; a changed-and-mapped-but-skipped suite is visible (step-summary run/skipped table) and the aggregator treats an improperly-skipped mapped suite as a failure; the guard tests and workflow files are themselves mapped (a gate edit re-runs the guards); the two hand-mirrored catch-all `--ignore` lists cannot drift from the filter topology.

**Why this priority**: this is the delivery-topology half of the same disease — the marker invariant (US1) closes the taxonomy hole, this closes the path hole. Operator ruling: too load-bearing to defer.

**Independent Test**: touch a file in `src/glossary` on a probe branch → the catch-all (or a new group) triggers ≥1 test job; simulate a mapped-suite skip with changed paths in a fixture → the aggregator arm reds; remove a dir from a catch-all `--ignore` without a filter change in a fixture → the mirror invariant reds.

**Acceptance Scenarios**:

1. **Given** the filter block post-mission, **When** the src-coverage invariant runs, **Then** every top-level `src/` package and every second-level `src/specify_cli` child is matched by ≥1 filter group whose output gates ≥1 test-running job, OR falls to the fail-closed catch-all group that forces the full-run path — zero silently-unrouted surfaces (AC-2a, fail-closed by construction rather than 75 hand-enumerated groups).
2. **Given** a PR whose changed paths map to a suite that did not run, **When** quality-gate evaluates, **Then** the run/skipped table appears in `$GITHUB_STEP_SUMMARY` and an improperly-skipped mapped suite fails the gate (AC-6; "improperly" = its filter output was true but the job did not run and was not superseded by the full-run path).
3. **Given** an edit to `.github/workflows/ci-quality.yml` or `tests/architectural/**`, **When** the filters evaluate, **Then** ≥1 test-running job (incl. the architectural shard) triggers (AC-8 guard self-mapping).
4. **Given** the two catch-all `--ignore` lists, **When** the mirror invariant runs, **Then** each list is exactly the set of test roots owned by dedicated shards (parsed relation, not literal duplication) — drift reds (AC-1 partial).

---

### Edge Cases

- A marker positively referenced ONLY by a non-blocking gate (e.g. `quarantine` in `quarantine-visibility`, which quality-gate ignores): the completeness invariant counts it as ROUTED (a job selects it) — blocking-ness is a separate, documented axis; `quarantine`'s non-blocking-by-design nature is recorded in the allowlist reasons, not conflated with reachability.
- `windows_ci` is negated in every Linux gate but positively selected by `ci-windows.yml` — the positive-token extractor must be negation-aware (pytest `Expression` AST walk), or `not windows_ci` would falsely satisfy it.
- The residual expression must be derived from the ROUTED-marker set, not hardcoded prose: when a new routed marker is added, the residual expression needs updating — the marker-completeness test should assert the residual job's expression stays consistent with the routed set (behavioral relation, not literal string pin).
- Draft-PR gating: `integration-tests-core-misc` is draft/WIP-gated; the residual job must NOT be, or a draft PR could merge-queue with the residual unrun (verify quality-gate semantics for drafts at implement time).
- The 4 suite-running workflows are the parse surface (`ci-quality`, `ci-windows`, `drift-detector`, `release`); a NEW pytest-running workflow added later must enter the model — `_gate_coverage`'s workflow list is itself an allowlist; assert it matches the live `.github/workflows/*.yml` set that invokes pytest (glob + content probe), so a fifth workflow fails closed rather than silently escaping the model.

## Requirements *(mandatory)*

### Functional Requirements

| ID | Requirement | Verification | Status |
|---|---|---|---|
| FR-001 | A new architectural test (`tests/architectural/test_marker_job_completeness.py` or equivalent) asserts: every marker registered in pytest.ini is in exactly one of three states — (i) ROUTED-BY-MARKER: positively referenced (negation-aware token extraction via pytest's `Expression` AST) in ≥1 gate's `-m` expression across all suite-running workflows; (ii) ROUTED-BY-PATH: every collected test carrying the marker is reachable via ≥1 path gate, verified against the `_gate_coverage` orphan model (not hand-asserted); or (iii) `CI_INVISIBLE`: reasoned allowlist entry. Reverse containment holds: every `CI_INVISIBLE` entry (and every ROUTED-BY-PATH claim) must reference a marker REGISTERED in pytest.ini — a marker deleted from the registry but left in the ledger reds (renata: the dumping-ground failure, other direction). `unit` and `contract` are HARD-ASSERTED ROUTED-BY-MARKER — ineligible for states (ii) and (iii). Fails closed on new unrouted markers and on de-routing edits. State (i)/(iii) checks are collection-free; state (ii) may reuse the orphan model's cached collection. | Fault-injection: synthetic marker → red; allowlist → green; de-route `unit` → red EVEN IF allowlisted (ineligibility assertion). | Planned |
| FR-002 | A new small CI job (working name `unit-contract-residual`) in `ci-quality.yml` selects the residual expression — `(unit or contract) and not (<routed runnable markers>)` — excludes `windows_ci`/`quarantine`, runs on every PR (not draft-gated), and is a blocking input to `quality-gate` (declared in `needs:` and read in the result loop). | Job green on the ~252-test residual; collect-only count recorded; quality-gate wiring asserted by FR-003's invariants. | Planned |
| FR-003 | Workflow-coherence invariants (same parse model as FR-001, extending `_gate_coverage`): (a) every `needs.<job>.result` reference in a run script is declared in that job's `needs:`; (b) every dorny filter output is consumed by ≥1 job `if:`; (c) every filter glob matches ≥1 tracked path; (d) every job named in quality-gate's result loop is in its `needs:` and vice-versa for blocking jobs. Refactor-stable: parsed relations only. | Fault-injection per relation on fixture YAML; live workflows pass post-FR-004. | Planned |
| FR-004 | BOUNDED fix-set (renata MEDIUM-4): the named candidates — `mission-loader-coverage` unreachable from quality-gate; the vacuous `src/mission_runtime/*` diff-coverage entry (both re-verified at plan time) — plus any SAME-CLASS incoherences the FR-003/FR-005 invariants surface (needs-declaration, filter-consumption, glob-liveness, cov-backing). The `integration-tests-charter` phantom read is LIKELY ALREADY FIXED (renata: declared ~:2938, read ~:2988) — re-verify and record. Incoherence classes beyond the FR-named invariant set stay bounded; the path-topology classes are now owned by FR-010..FR-012 (folded #2333). | FR-003/FR-005 suites green on the fixed live workflows; each fix (and each verified-already-fixed) listed in the PR body. | Planned |
| FR-005 | Diff-coverage critical-path backing invariant: every entry in the diff-cover critical-path list is matched by ≥1 job emitting a `--cov` for that package (closes the vacuous-entry class). | Fault-injection + live pass after FR-004 fixes. | Planned |
| FR-006 | #2296 drain: the 3 route-able orphan files get `ci-quality.yml` path additions on their matching integration shards; `tests/_support/git_template/test_git_template.py` is adjudicated (route or record intentionally-non-gated with rationale); `_gate_coverage_baseline.json` regenerates to `orphan_test_count: 0` (or the single recorded intentional exception) and the ratchet locks the new floor. | `--check` reports 0 orphans (± recorded exception); ratchet fault-injection still red on a new orphan. | Planned |
| FR-007 | `ci-windows.yml` trigger paths widened to `src/**` (or an explicit per-package exclusion list with rationale), so Windows-sensitive packages (`src/mission_runtime`) trigger the Windows job (WS5 AC). | Path filter includes `src/**`; recorded rationale for any exclusion. | Planned |
| FR-008 | Workflow-set completeness: the `_gate_coverage` model's workflow allowlist is asserted against the live set of pytest-invoking workflows in `.github/workflows/`, so a new suite-running workflow fails closed instead of escaping the model. | Fault-injection: fixture workflow invoking pytest not in the model → red. | Planned |
| FR-010 | Src-side filter coverage (AC-2a) with a NON-VACUOUS fail-closed catch-all: (a) mechanism — a trivial `any_src: ['src/**']` probe group + a script step that computes `unmatched = any_src AND NOT (union of all named group outputs)` FROM THE FILTER'S OWN OUTPUTS (the negated mega-glob mirror is FORBIDDEN — it would hand-maintain a copy of all groups); `unmatched` threads into the existing `run_all` OR-seam (~:84-103) so every per-module job forces on (run_all semantics per HiC ruling 7b, no per-job `if:` surgery); (b) targeted named groups where a natural owner shard exists (`src/glossary` at minimum); (c) the invariant is the PARSED RELATION: the unmatched-computation's group-reference set ≡ the parsed filter-group set (a group added/removed without catch-all wiring reds) AND every group output gates ≥1 test-running job — NOT "every package matched-or-caught" (vacuous by construction once a catch-all exists; paula CRITICAL); (d) refactor-stability red-negative: reordering/renaming groups without changing the parsed relation stays green. | Fault-injection: fixture group not in the OR-list → red; fixture group reorder → stays green. Probe branches: unmatched src file → run_all path fires; well-mapped file → catch-all does NOT fire (fixture-asserted via the parsed model, plus one live probe recorded). | Planned |
| FR-011 | Skipped-suite fail-closed visibility (AC-6), scoped and non-fakeable: quality-gate emits a run/skipped table to `$GITHUB_STEP_SUMMARY` and FAILS per the decision table — FAIL iff `filter_true AND job_skipped AND NOT full_run AND NOT draft_exempt` (full_run = `inputs.run_all OR catchall.unmatched`; draft_exempt = job draft-gated AND PR is draft — safe per FR-013 + GitHub's native draft-merge block). SCOPE: blocking `needs:` jobs ONLY — `quarantine-visibility` stays non-blocking (C-005 extended: FR-011 must not re-surface the quarantine set into the blocking path; renata). The job→group mapping the arm consumes is ASSERTED ≡ the parsed job-`if:` gating by an FR-003-class invariant (Decision 8) — never a free-standing bash table. The decision logic is EXTRACTED into a testable script with fixture tests incl. the draft-context case and the improperly-skipped case. | Fixture tests on the extracted script (draft case, skipped-mapped case, full-run-supersede case); mapping-invariant fault-injection; live green post-fix; the table visible in the C-007 probe run (non-draft probe — core-misc is draft-gated). | Planned |
| FR-012 | Guard self-mapping (AC-8, narrowed to the REAL gap) + `--ignore` mirror coherence (AC-1 partial): `ci-quality.yml` + `tests/architectural/**` ALREADY self-map via `core_misc` (:175/:187 — record verified-already-fixed; renata/paula convergent); the live gap is the OTHER suite-running workflows (`ci-windows.yml`, `drift-detector.yml`, `release.yml`) which appear in NEITHER the outer `on: paths:` NOR any dorny group — the fix is TWO-LAYER: widen the outer `on: pull_request/push paths:` AND add a dorny group routing them to the architectural shard. The `--ignore` mirror invariant asserts each catch-all `--ignore` list ≡ the shard-owned test-root set as a PARSED relation with a refactor-stability red-negative (reorder/rename → stays green) — a literal-mirror implementation is a review REJECT (fault-injection alone cannot discriminate it; renata). | Fault-injection per relation; reorder red-negative; live green post-fix. | Planned |
| FR-013 | `ready_for_review` added to `ci-quality.yml`'s `on: pull_request types:` (→ `[opened, synchronize, reopened, ready_for_review]`; HiC ruling 7a) so a draft→ready transition re-runs the draft-skipped suites; verified by a fixture assertion on the parsed trigger types + the C-007 probe (draft→ready flip re-triggers). | Parsed-trigger invariant + probe evidence. | Planned |
| FR-009 | Tracker closeout: #2297 closed by the PR; #2296 closed by the PR; #2034 closed by the PR (its residue is exactly FR-001/FR-002 — verify no remaining open obligation in its thread at closeout); #2283 gets a partial comment (factor (a) closed; (b)/(c) remain, pointed at CT7/#2077); **#2333 closed by the PR (folded in-mission)**; #1933 gets the reconciliation comment (catch-all = loud alarm + shrink obligation; mapped PRs stay targeted); #1868 WS5 checklist comment updating the bound ACs; roadmap Wave-0 row struck. | Comments/links verifiable; issue-matrix terminal. | Planned |

### Non-Functional Requirements

| ID | Requirement | Threshold | Status |
|---|---|---|---|
| NFR-001 | FR-001/FR-003/FR-005/FR-008 invariants are cheap enough for the architectural shard | combined < 5 s (pure parse + expression walk; no pytest collection) | Planned |
| NFR-002 | The residual job's wall-clock stays small | < 3 min end-to-end on CI (≈252 pure-logic tests at spec time; measure at implement time and record) | Planned |
| NFR-003 | No test double-run regression: the residual expression must not select tests already routed via `fast`/`integration`/etc. | duplicate-count from `_gate_coverage --check` does not increase vs the RE-DERIVED pre-mission value (committed baseline records 2,944; live census saw 3,291 — re-derive at implement, pin the honest number, shrink-only from there) | Planned |
| NFR-004 | Honest live counts (Wave-1/2 doctrine): every census number in the mission's artifacts (252, 17, 2,944…) is re-derived at implement time, never copied from this spec | re-derivation commands + outputs recorded in WP reports | Planned |
| NFR-006 | Catch-all breadth stays bounded: the `unmatched` signal fires ONLY when no named group matched (fixture-asserted via the parsed model); the closeout records the live unmatched-dir census + the shrink-trend obligation (#1933 reconciliation) | fixture assertion + census recorded in the PR body | Planned |
| NFR-005 | Every new/relocated test carries CI-selected markers (#2034's own lesson; proven for the new arch tests by FR-001 itself) | new tests selectable by ≥1 gate; verified per-file | Planned |

### Constraints

| ID | Constraint | Rationale | Status |
|---|---|---|---|
| C-001 | No workflow generator; no third source-of-truth artifact. The parsed-model + invariants form is binding (Adjudicated Decision 1). | WS5 "or CI-validated" arm; precedent; split-brain risk. | Accepted |
| C-002 | Refactor-stable invariants only: parsed behavioral relations; never job names @ line numbers, literal `-m` strings, or YAML shape pins (testing-principles styleguide / C-006 doctrine). | The invariants outlive workflow refactors. | Accepted |
| C-003 | Shrink-only: `CI_INVISIBLE` and any baseline exception carry per-entry reasons; additions are loud (the completeness test names them), removals silent. | Exception ledgers must not become dumping grounds. | Accepted |
| C-004 | `workflow` OAuth scope required for `ci-quality.yml`/`ci-windows.yml` pushes — verify the push path early (WP01-adjacent), before deep work stacks behind it. | #2296 explicitly flags the scope gate. | Accepted |
| C-005 | Do not touch quarantined tests (#2295/#2309) or re-litigate the quarantine lane; the residual expression excludes `quarantine`. | Separate tracked debt; the lane is #2317's landed design. | Accepted |
| C-006 | `pytest.ini` remains the only marker registry (PR #2047 + its guard); this mission READS it, never adds a second registry surface. `CI_INVISIBLE` maps routing-exemption reasons, not marker definitions. | Single canonical authority. | Accepted |
| C-007 | This mission lands GREEN including its own gates: pre-merge dry-run of the residual job selection + the full invariant suite on the final workflow state (gate-unmask-cannot-self-validate discipline). | A gate that first bites post-merge is a regression vector. | Accepted |

## Success Criteria *(mandatory)*

| ID | Criterion | Measurement |
|---|---|---|
| SC-001 | `-m unit` and `-m contract` are positively selected by a blocking CI gate | FR-002 job live; FR-001 invariant green; #2034's core claim no longer reproduces |
| SC-002 | Marker→job completeness fails closed | fault-injection evidence recorded (synthetic marker red; de-route red) |
| SC-003 | Orphan baseline at zero (± one recorded intentional exception) | `_gate_coverage --check` output in the closeout report |
| SC-004 | The WS5 coherence relations hold on live workflows and are guarded | FR-003/FR-005 invariants green; the fixed incoherences enumerated in the PR body |
| SC-005 | No CI-minute regression beyond the residual job's budget | NFR-002/NFR-003 measurements recorded |

## Assumptions

- The residual set stays green between spec and implement (debbie verified all 17 live orphans + samples pass); any drift is handled by the fix-all-before-gate bar (Decision 5).
- `quality-gate` remains the single blocking aggregator; branch protection semantics unchanged.
- The `workflow`-scope push path works from this checkout (verify early per C-004).

## Out of Scope

- #2283 factors (b) venv-skew doc and (c) producer-conformance sweep → CT7 (#2077).
- Quarantine triage (#2295/#2309); the quarantine lane's design.
- mypy CI-scope expansion + advisory-vs-enforced decision → #1868 follow-up.
- Marker-registry single-sourcing (done, PR #2047).
- `slow-tests` push-only semantics (documented behavior; changing it is a CI-budget decision this mission doesn't own — recorded, not fixed).
- Any test-content remediation beyond what the new gates unmask (CT1–CT5 own content classes).
