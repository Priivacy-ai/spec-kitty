# Mission Specification: Verdict-Seam Boundary Hardening

**Mission Branch**: `verdict-seam-boundary-hardening-01KZG179`
**Created**: 2026-08-08
**Status**: Draft
**Input**: Follow-on hardening mission for the verdict-seam write-unification landed in PR #3245 (mission `verdict-seam-write-unification-01KZ9Q35`). Scope rationale: close the leftover work and clean up the adjacent functional/technical debt. Resolves #3254, #3236, #3244, #3255, #3256, and the folded #3211 follow-up #3217 (operator-adjudicated during pre-planning). #3216 was also folded during pre-planning, but the post-tasks adversarial squad verified its target reader (`_get_latest_review_cycle_verdict`) was **already retired by the prior mission's WP05** (#3245, FR-003) — so #3216 is closed as already-resolved and descoped from this mission. #3243 considered and left separate.

## Context *(informative)*

PR #3245 unified the **verdict authority model** — the append-only event log is now the sole authority for review-result verdicts, and read semantics are settled. What it did **not** finish is the *write-side boundary* around that authority: the `specify_cli.status` façade only partially exports the verdict bridge, so consumers still reach into `status.<submodule>` objects; two architectural guards (the module-boundary guard and the verdict-seam census) pass vacuously against exactly those shapes; the prior mission's fail-open change to the review-cycle merge driver left a latent arbiter-override crash reachable; the `accept --json` surface drops an operator advisory; and a heavyweight `@stress` durability test rides the fast test pool because no CI lane selects it.

This is a **brownfield / campsite** mission: it finishes the boundary and cleans the debt it touches, **without** altering the verdict authority model or read semantics (explicit non-goal, consistent with epic #3044's closed shape).

## User Scenarios & Testing *(mandatory)*

> "User" here is the **maintainer / agent-runtime** operating on the `status` verdict seam and the mission-review lifecycle; value is boundary integrity, crash-freedom, machine-surface parity, and CI hygiene.

### User Story 1 - Single import surface for the verdict bridge, actively enforced (Priority: P1)

A maintainer importing verdict/review-result decode logic reaches **only** the `specify_cli.status` public façade — never a `status.<submodule>` object — and the repo-wide boundary guard *fails* if anyone reintroduces a submodule-object import. The duplicated merge-blocking decode is retired in favour of the single reducer-owned function.

**Why this priority**: This is the mission's core theme — the single-authority boundary is currently *reachable-around* and the guard that should forbid it is partly vacuous, so drift is silent. Everything else is adjacent cleanup.

**Independent Test**: Grep confirms zero `from specify_cli.status import <submodule>` object imports in production code (verdict_vocab + the 4 collateral submodules); the widened boundary-guard test flags a synthetic reintroduction; the full verdict-seam suite is green.

**Acceptance Scenarios**:

1. **Given** the `verdict_vocab` public surface (8 functions + `EventVerdict` alias + `APPROVED`/`REJECTED`/`CHANGES_REQUESTED` constants) and `review_result_from_state`, **When** the façade is finalized, **Then** every one of those symbols is exported on `specify_cli.status.__all__`.
2. **Given** the 8 submodule-object consumers of `verdict_vocab` and the 4 collateral submodule-object imports (`emit`, `store`×2, `lane_reader`), **When** migration completes, **Then** each imports façade symbols and no `status.<submodule>` object reference remains in production code.
3. **Given** `_event_sourced_gate_verdict` in `post_merge/review_artifact_consistency.py` (a merge-blocking path), **When** the duplicated `review_result` decode is removed, **Then** it delegates to `review_result_from_state` with identical behavior across all five decode cases (absent slot / raw-None / non-Mapping / from_dict-raises / valid).
4. **Given** a synthetic `from specify_cli.status import verdict_vocab` (submodule-object) import, **When** the boundary guard runs, **Then** it is flagged as a violation (previously passed vacuously).
5. **Given** the widened guard, **When** the full arch suite runs, **Then** no legitimate `from specify_cli.status import <symbol>` façade import is falsely flagged.

---

### User Story 2 - Architectural census sees the genuine frontmatter reader it currently masks (Priority: P1)

The verdict-seam census stops wholesale-excluding `verdict_provenance_backfill.py` and instead excludes only the migration's write-side helpers, so `_legacy_frontmatter_verdict` — a genuine frontmatter reader — surfaces as a classified reader row instead of being silently suppressed.

**Why this priority**: Same guard-vacuity failure class as Story 1; a future live reader moved into that module would be hidden. Coordinated with Story 1 but on independent code surface (parallel lane).

**Independent Test**: The census reports `_legacy_frontmatter_verdict` as a reader row; the write-side helpers remain excluded by name; the census suite is green.

**Acceptance Scenarios**:

1. **Given** the census exclusion machinery, **When** function-level exclusion is added, **Then** `verdict_provenance_backfill.py` is removed from module-level exclusion and only its write-side helpers are excluded by name.
2. **Given** `_legacy_frontmatter_verdict`, **When** the census classifies the module, **Then** it appears as a reader row.
3. **Given** the three tests that assert the module is wholesale-excluded / contributes zero rows, **When** the narrowing lands, **Then** they are updated to assert the new function-level shape and pass.
4. **(#3217, folded)** **Given** the census's AST classifier misses helper-constructed records (`migration/backfill_runtime_state.py::_review_from_frontmatter`), **When** the classifier is extended to recognize helper-constructed reader shapes, **Then** that escapee surfaces as a classified row — so #3236 and #3217 together leave the census fully hardened, not half.

---

### User Story 3 - Arbiter override survives a conflict-marked review-cycle artifact (Priority: P1)

An arbiter override on a work package whose latest `review-cycle-N.md` was left conflict-marked by the fail-open merge driver completes without crashing and durably records the override.

**Why this priority**: This is a real latent crash on a lifecycle-critical path (the override path), reachable in production since the prior mission's merge-driver downgrade. Red-first is mandatory.

**Independent Test**: A red-first regression drives the public `persist_arbiter_decision` entry against a conflict-marked latest artifact and asserts no crash + override recorded; it is RED before the fix and GREEN after.

**Acceptance Scenarios**:

1. **Given** a `review-cycle-N.md` whose body begins with git conflict markers (no valid YAML frontmatter), **When** an arbiter override runs on that WP, **Then** the override completes without raising and the decision is durably recorded.
2. **Given** the fix, **When** the arbiter resolves the latest cycle number, **Then** it derives the number from the filename without parsing the file body.
3. **Given** the second `.latest` consumer that needs the full parsed body, **When** the fix lands, **Then** `.latest`/`from_file` parse behavior is unchanged.

---

### User Story 4 - `accept --json` surfaces the stranded-verdict advisory (Priority: P2)

A script consuming `spec-kitty accept --json` receives the SC-008 stranded-verdict backfill advisory as a structured field, so automation can surface or act on the "run `spec-kitty upgrade`" remediation hint that today only a human sees.

**Why this priority**: Real machine-surface parity gap, but advisory-only (no incorrect gate decision) → lower priority than the boundary/crash work.

**Independent Test**: A focused test invoking the accept JSON path against a stranded-verdict fixture asserts the advisory appears in a top-level `advisories` array.

**Acceptance Scenarios**:

1. **Given** a mission with a stranded terminal verdict, **When** `accept --json` runs, **Then** the SC-008 advisory appears in a top-level `advisories: list[str]` field in the JSON payload.
2. **Given** a converged mission with no stranded verdict, **When** `accept --json` runs, **Then** `advisories` is present and empty.
3. **Given** the advisory injection, **When** it is implemented, **Then** it lives entirely in the CLI emit layer and does not couple into the acceptance domain model.

---

### User Story 5 - A dedicated stress CI lane isolates the heavyweight durability test (Priority: P2)

The `@stress`-marked concurrency durability test no longer rides the fast xdist pool; a dedicated CI lane selects `-m stress` and runs those tests serially, mirroring the real-port/daemon serial pass.

**Why this priority**: Flakiness-prevention / CI hygiene; passes today but is a plausible future flake. Operator elected to include the full lane in this mission rather than split it.

**Independent Test**: CI configuration contains a stress job selecting `-m stress -n0`; the durability test is no longer swept into the fast pool selector; the `-m stress` selection collects the intended tests.

**Acceptance Scenarios**:

1. **Given** the CI workflow, **When** the stress lane is added, **Then** a job selects `-m "stress and not windows_ci"` and runs serially (`-n0`).
2. **Given** `test_two_concurrent_distinct_verdicts_are_both_durable`, **When** the marker is right-sized, **Then** it is no longer collected by the fast-pool selector.
3. **Given** the `pytest.ini` `stress` marker description, **When** the lane lands, **Then** its "excluded from the fast suite" wording is corrected to match reality.

### Edge Cases

- **Naïve guard widening**: widening `_is_bypass_import` by a bare `startswith` would flag 100+ legitimate `from specify_cli.status import <symbol>` façade imports. The widening MUST distinguish submodule *names* (filesystem `.py` check or explicit set) from `__all__` symbols.
- **Ordering hazard**: removing the duplicated decode before `review_result_from_state` is on `__all__` would red the merge-blocking gate (the local decode exists *only* because the symbol is unexported). Export first, then dedup.
- **Census over-narrowing**: excluding only `_legacy_frontmatter_verdict` surfaces the module's other 8 functions to the classifier — confirm they classify as non-readers or the census gains legitimate new rows that must be reconciled.
- **Collateral scope**: the widened guard also catches `emit`/`store`/`lane_reader` submodule-object imports unrelated to verdict_vocab; operator chose to migrate all four (no exemption ledger).
- **Conflict-marked but not *latest***: only the highest-numbered cycle artifact is parsed by the arbiter path; a conflict-marked lower-numbered sibling is already tolerated (sorts via filename regex).

## Requirements *(mandatory)*

### Functional Requirements

| ID | Title | User Story | Priority | Status |
|----|-------|------------|----------|--------|
| FR-001 | Promote full verdict_vocab surface + review_result_from_state onto `status.__all__` (export before any dependent dedup) | As a maintainer, I want the whole verdict bridge reachable as façade symbols so consumers never touch a submodule object. | High | Open |
| FR-002 | Migrate all 8 verdict_vocab submodule-object consumers to façade symbols | As a maintainer, I want every verdict_vocab consumer importing façade symbols so the single import surface holds. | High | Open |
| FR-003 | Migrate the 4 collateral submodule-object imports (emit, store×2, lane_reader) to façade symbols, fully closing the boundary with no exemptions | As a maintainer, I want no `status.<submodule>` object import anywhere in production code. | High | Open |
| FR-004 | Retire the duplicated `review_result` decode in `_event_sourced_gate_verdict`, delegating to `review_result_from_state` with behavior-preserving return adaptation | As a maintainer, I want the merge-blocking gate to reuse the reducer-owned decode rather than a fork. | High | Open |
| FR-005 | Widen the module-boundary guard to flag `from specify_cli.status import <submodule>`, targeting submodule names specifically (no false positives on façade symbols) | As a maintainer, I want the boundary guard to actively forbid submodule-object imports. | High | Open |
| FR-006 | Fold the reducer test rename (name/docstring drift on two retired-behavior tests; assertions already correct) | As a maintainer, I want test names to match behavior in the seam I'm touching. | Low | Open |
| FR-007 | Add function-level exclusion mechanism to the verdict-seam census; narrow `verdict_provenance_backfill.py` from module- to function-level so `_legacy_frontmatter_verdict` surfaces as a reader row | As a maintainer, I want the census to see genuine readers instead of masking them wholesale. | High | Open |
| FR-008 | Update the three census tests that assert wholesale exclusion to the new function-level shape | As a maintainer, I want the census tests to pin the narrowed exclusion. | Medium | Open |
| FR-009 | Red-first regression: arbiter override on a conflict-marked latest review-cycle artifact must not crash and must record the override | As a maintainer, I want a failing test that reproduces the latent crash before the fix. | High | Open |
| FR-010 | Add filename-only `ReviewCycleArtifact.latest_cycle_number()` and use it on the arbiter path; leave `.latest`/`from_file` untouched | As a maintainer, I want the arbiter to resolve the cycle number without parsing a possibly-damaged body. | High | Open |
| FR-011 | Surface the SC-008 stranded-verdict advisory in the `accept --json` payload via a uniform top-level `advisories` array injected at the CLI emit layer | As an automation author, I want the backfill advisory in the machine-readable output. | Medium | Open |
| FR-012 | Add a dedicated stress CI lane selecting `-m stress -n0` (POSIX-only) and right-size the mis-pooled durability test out of the fast pool; correct the `pytest.ini` stress-marker wording | As a maintainer, I want heavyweight stress tests isolated in their own serial lane. | Medium | Open |
| FR-013 | (#3217, folded) Extend the verdict-seam census classifier to recognize helper-constructed reader records so `_review_from_frontmatter` surfaces; coordinate with FR-007 so #3236+#3217 fully harden the census | As a maintainer, I want the census to catch helper-constructed readers, not just direct ones. | High | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | Behavior preservation on merge-blocking path | The `_event_sourced_gate_verdict` dedup (FR-004) must produce identical verdicts across all 5 decode cases; verified by tests covering each case. | Reliability | High | Open |
| NFR-002 | Guard non-vacuity | The widened boundary guard (FR-005) and narrowed census (FR-007) must each fail on a synthetic violation (teeth test), proving non-vacuous enforcement. | Reliability | High | Open |
| NFR-003 | Static-analysis cleanliness | All changed code passes `ruff` and `mypy` with zero new issues/warnings and zero new suppressions. | Maintainability | High | Open |
| NFR-004 | New-code coverage | Every new helper/branch (e.g. `latest_cycle_number`, `advisories` injector, census function-exclusion) has a focused test in the same work package. | Maintainability | High | Open |
| NFR-005 | Arch-gate re-baseline integrity | Widening the boundary guard changes no golden-count/shard-map file (verified: both files carry the architectural marker and are in `_arch_shard_map.py`; the `len==1` check is a synthetic-fixture teeth test, not a repo count). | Reliability | Medium | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | Do not change verdict authority or read semantics | The event log remains the sole verdict authority; no read-path or vocabulary change (consistent with epic #3044's closed shape). | Technical | High | Open |
| C-002 | Export-before-dedup ordering | `review_result_from_state` must be on `status.__all__` before `_event_sourced_gate_verdict` is de-duplicated (merge-blocking path). | Technical | High | Open |
| C-003 | Submodule-name-targeted guard widening | The boundary-guard widening must not falsely flag legitimate façade-symbol imports; it must recognize submodule names specifically. | Technical | High | Open |
| C-004 | Leave `.latest`/`from_file` parse contract intact | The arbiter fix must not alter `.latest`/`from_file` behavior (a second consumer needs the full parsed body). | Technical | High | Open |
| C-005 | Advisory stays in the CLI layer | The `accept --json` advisory must not couple into the acceptance domain model. | Technical | Medium | Open |
| C-006 | Red-first for the crash | FR-009's regression must be committed RED (reproducing the crash through the pre-existing public entry) before FR-010's fix. | Process | High | Open |
| C-007 | Point-cut squads + tracer files + frequent commit/push | Execute the standing-order adversarial squads at each planning point-cut; bootstrap tracer files during planning and append during implement; commit and push at point-cuts. | Process | High | Open |
| C-008 | Terminology guard before prose/doctrine pushes | Run the terminology guard when touching `src/doctrine/` or user-facing prose. | Process | Medium | Open |

### Key Entities *(include if feature involves data)*

- **`verdict_vocab` public surface**: the 8 verdict-bridge functions + `EventVerdict` type alias + `APPROVED`/`REJECTED`/`CHANGES_REQUESTED` constants that must become façade exports.
- **`status` façade (`__all__`)**: the single sanctioned import surface for status/verdict/review-result symbols.
- **`ReviewCycleArtifact`**: review-cycle `.md` artifact; the arbiter path needs only its filename-derived cycle number, a second consumer needs its parsed body.
- **Verdict-seam census rows**: reader/writer/resolver classifications the census derives per function; the unit of the function-level exclusion.
- **`accept --json` payload**: the machine-readable acceptance output gaining a uniform `advisories` array.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Zero `from specify_cli.status import <submodule>` object imports remain in production code (all 8 verdict_vocab consumers + 4 collateral migrated); confirmed by grep and a green boundary-guard suite.
- **SC-002**: The module-boundary guard and the verdict-seam census each fail on a synthetic violation (both proven non-vacuous), and pass on the real tree.
- **SC-003**: `_legacy_frontmatter_verdict` appears as a classified reader row in the census; the migration's write-side helpers remain excluded by name.
- **SC-004**: The arbiter-override regression is RED before the fix and GREEN after; an arbiter override on a conflict-marked latest artifact completes without crashing and records the override.
- **SC-005**: `spec-kitty accept --json` emits the SC-008 advisory in a top-level `advisories` array for a stranded mission and an empty array for a converged one.
- **SC-006**: CI has a stress lane selecting `-m stress -n0`; the durability test is no longer collected by the fast-pool selector; `pytest.ini` marker wording is accurate.
- **SC-007**: All changed code passes `ruff` and `mypy` with zero new issues and zero new suppressions; every new helper/branch has a focused test in its work package.
