# Mission Specification: Bare-Prose Requirements Are Silently Uncounted by the Coverage Gate

**Mission Branch**: `bare-prose-requirements-uncounted-01KZYV3C`
**Created**: 2026-08-14
**Status**: Draft
**Input**: GitHub issue [#3396](https://github.com/Priivacy-ai/spec-kitty/issues/3396), filed as a deliberate follow-up to #3394 / PR #3395 (`op/3394-requirement-citation-scope`). This mission branches from PR #3395's branch rather than `main` — see Clarifications below for the binding operator decision and its accepted consequences.

## Context *(informative)*

PR #3395 fixed #3394: `parse_requirement_ids_from_spec_md` (`src/specify_cli/requirement_mapping.py`) now scopes requirement-ID extraction to four **declared** shapes — table row, id-naming heading, bulleted/numbered list item, bold-led paragraph — so a requirement ID merely *cited* in prose (e.g. "...see FR-021's default-pack materialization") is no longer mistaken for a requirement the citing spec itself defines.

That fix leaves a gap #3395 deliberately did not close, filed separately as #3396: a spec that declares *some* requirements correctly **and** writes *others* as bare, unbulleted, unbolded prose sentences —

```markdown
### Functional Requirements

FR-001 the loader must reject an unknown pack.
FR-002 the error must name the offending path.

| ID | Requirement |
|----|-------------|
| NFR-001 | Resolution completes within 200ms |
```

— produces FR-001/FR-002 that match none of the four declared shapes. They are therefore excluded from `_declared_ids()`'s output entirely: not merely "unmapped," but never added to `functional_requirement_ids` in the first place. `finalize-tasks` and `map-requirements` can report full FR coverage while these two requirements were never counted, mapped, or checked against any work package. `spec-kitty next`'s readiness path (`_check_requirement_mapping_ready` → `runtime_bridge_cores._evaluate_requirement_mapping`) inherits the same blindness, because it consumes the same declared-id extraction.

The obvious "fix" — treat any raw `FR-NNN` token that is not in the declared set as unmapped, doc-wide — is precisely the bug #3394 reported and #3395 fixed; it would hard-fail every spec that legitimately cites a foreign requirement ID. `find_undeclared_requirement_citations` (added in #3395, currently advisory-only) already performs **section-scoped** detection: it can tell "raw tokens under a heading whose title names Requirements, none of which matched a declared shape" apart from "a token cited elsewhere in the document." That distinction is most of what a correct, non-doc-wide fix needs — but it has never been corpus-validated as a **blocking** signal, and a narrow blocking attempt on this exact seam (`_zero_declared_requirement_block`, commit `3823f2b00` on this checkout — see Clarifications for the hash discrepancy versus the issue text's `ae7eba9b2`) was already tried and reverted for being provably inert at the CLI level. This mission's central engineering risk is repeating that same dead-path shape under a different name.

This mission is explicitly framed, per operator direction, as another instance of this repository's **silent-success failure class** (tracked incidents #3133, #3212, #3282, #3336) — a code path that counts `0` uncovered requirements and calls it clean, when the true count is nonzero and simply invisible to the counter.

## Clarifications

### Session 2026-08-14

- **Q: #3396's defect only exists once PR #3395 lands, and #3395 is still open with no review decision. How should this mission sequence against it?**
  **A (operator, 2026-08-14): "Branch from #3395's branch now."** Accepted consequence, stated at decision time: the mission's diff carries #3395's ~863-line unreviewed parser rewrite; #3395 has no `reviewDecision` and could still change shape; this repo has no protected staging branch, so if #3395 changes, this mission eats the rebase.

## User Scenarios & Testing *(mandatory)*

> "User" here is the **maintainer / agent-runtime** driving `spec-kitty agent tasks finalize-tasks`, `map-requirements`, and `spec-kitty next`'s tasks-boundary readiness check; value is that a spec's real, uncovered functional requirements cannot silently ride an "all mapped" report or an advisory-only log line into an advanced mission.

### User Story 1 - A spec mixing declared and bare-prose requirements is blocked, not merely logged (Priority: P1)

A spec.md that declares some requirements in a recognized shape (table row / heading / bullet / bold paragraph) **and** writes others as bare, unbulleted, unbolded prose sentences inside a heading section whose title names "Requirements" surfaces those bare-prose requirements through a **blocking** path — not only the existing non-blocking `requirement_extraction_warnings` advisory.

**Why this priority**: This is the mission's whole reason to exist. Today the exact repro in the issue body (`FR-001 the loader must reject...` / `FR-002 the error must name...` alongside a correctly declared `NFR-001` table row) produces zero declared FR ids for FR-001/FR-002, so nothing about the mapping decision, coverage report, or `spec-kitty next` gate can ever notice them — only an advisory log line does, and advisories are opt-in reading.

**Independent Test**: A fixture spec.md matching the issue's exact repro shape (mixed declared NFR + bare-prose FR-001/FR-002 inside a "Functional Requirements"-titled section) drives `finalize-tasks`, `map-requirements`, and `spec-kitty next`'s tasks-boundary readiness check; all three surface a blocking failure naming FR-001 and FR-002, not only a warning.

**Acceptance Scenarios**:

1. **Given** the issue's exact repro spec.md (declared NFR-001 table row + bare-prose FR-001/FR-002 under a "Functional Requirements" heading), **When** `spec-kitty agent tasks finalize-tasks` runs, **Then** it fails (non-zero exit / blocking JSON result), naming FR-001 and FR-002 as uncounted — not merely appending them to `requirement_extraction_warnings`.
2. **Given** the same fixture, **When** `spec-kitty agent tasks map-requirements` computes coverage, **Then** it reports FR-001/FR-002 as requiring resolution before coverage can be considered complete, not silent 100% coverage over the (smaller) declared set.
3. **Given** the same fixture and a mission at the `tasks_packages`/`tasks_finalize` step boundary, **When** `spec-kitty next` evaluates advance-vs-stay, **Then** the returned `Decision` is `blocked` (or equivalent non-advancing kind) with a failure message naming FR-001 and FR-002, reachable through the mechanism verified in Story 3 (independent of `tasks_wp_files` presence/ordering).

---

### User Story 2 - #3394's repro shape stays green (negative-space regression) (Priority: P1)

A spec.md that declares its own requirements correctly and merely *cites* a foreign, already-shipped requirement ID in prose elsewhere in the document (#3394's original repro) continues to pass every gate named in Story 1, exactly as #3395 already fixed it.

**Why this priority**: This is the negative-space pin without which Story 1 cannot ship — any implementation that widens detection without honoring the *declared* scoping decision from #3394/#3395 reintroduces the exact bug that mission fixed. The two stories are inseparable: a change that only satisfies Story 1 and breaks Story 2 is not an acceptable outcome of this mission.

**Independent Test**: The existing #3394/#3395 negative-space test fixtures and cases in `tests/specify_cli/test_requirement_mapping.py`, `tests/next/test_runtime_bridge_unit.py`, and `tests/runtime/test_bridge_cores.py` remain green, unmodified in their pinned assertions, after this mission's implementation lands.

**Acceptance Scenarios**:

1. **Given** a spec.md whose own requirements are all declared in a recognized shape, and whose prose cites a foreign FR id (e.g. "...easy to miss, see FR-021's default-pack materialization") outside any Requirements-named section or not matching a declared shape inside one, **When** any of the three surfaces from Story 1 run, **Then** none of them block on the cited foreign id.
2. **Given** the full pre-existing #3394/#3395 test suite (declared-shape extraction, negative-space citation cases, the reverted-block regression tests), **When** this mission's implementation lands, **Then** every pre-existing assertion in those files still passes unmodified — this mission may *add* tests but must not weaken or delete an existing #3394/#3395 assertion to make Story 1 pass.
3. **Given** a table row whose **description column** cites an external convention or foreign id (the exact shape that drove the rejected doc-wide prototype's ~6% false-positive rate in #3395's own measurement), **When** the new blocking detector runs, **Then** it does not block — the row's ID cell is still recognized as declared and the description-column citation is not treated as a second, undeclared requirement.

---

### User Story 3 - The blocking signal actually reaches `spec-kitty next`'s advance-vs-stay decision (Priority: P1)

The new blocking signal changes what `spec-kitty next` actually decides at the tasks boundary — for a spec containing bare-prose requirements, in **both** of the following configurations: (a) zero work-package files exist yet, and (b) work-package files exist and none of them (correctly, since the ids aren't declared) reference the bare-prose requirement ids.

**Why this priority**: This is the constraint the operator named as non-negotiable and the exact shape of the prior failure. `_zero_declared_requirement_block` (commit `3823f2b00` on this checkout) was reverted because all three guards that consume `requirement_mapping_failures` — `_evaluate_tasks_packages_guard`, `_evaluate_composed_tasks_packages_guard`, `_evaluate_composed_tasks_terminal_guard` (`src/runtime/next/runtime_bridge_cores.py`) — check `_tasks_dir_ready` (which requires `tasks_wp_files` to be present) *before* ever reading `requirement_mapping_failures`. With zero WP files, the guard short-circuits to `MISSING_TASK_FILES_MESSAGE` and never sees the new signal at all; with ≥1 WP file, the pre-existing missing/unknown-ref checks already caught the block's own precondition whenever it held — so the block changed nothing reachable. Shipping a signal with that same shape again, under a new name, would repeat a change already proven to be dead code.

This mission's fix must therefore do one of two things, and must say explicitly which:
  (a) make the new signal's evaluation independent of, or ordered *before*, the `tasks_wp_files`-first check in whichever guard(s) it needs to reach `spec-kitty next`'s decision, or
  (b) gate a *different* step than the one those three guards protect (e.g. block earlier, at `tasks_finalize` itself, or at the point the CLI computes coverage before any WP exists) — and explain why that step change is sufficient to satisfy Story 1's acceptance scenarios.

**A fourth call site the issue text did not name, discovered during this spec's investigation**: `_evaluate_tasks_finalize_guard` (`runtime_bridge_cores.py`, the CLI-native vocabulary's handler for `step_id == "tasks_finalize"`) does **not** read `requirement_mapping_failures` at all today — only the *composed* `"tasks"` vocabulary's terminal guard (`_evaluate_composed_tasks_terminal_guard`) does, via `legacy_step_id`. If production `spec-kitty next` dispatches the CLI-native `tasks_finalize` step_id at the point missions actually reach this boundary, a fix wired only into the three guards the issue named would be silently dead for a fourth reason, independent of the `tasks_wp_files`-ordering trap. The plan phase MUST audit which step_id vocabulary is live for the CLI's actual `tasks_finalize` dispatch before choosing where to wire the new signal, and must wire it into whichever vocabulary (or both) `spec-kitty next` actually exercises in production.

**Independent Test**: A regression test (or set of tests) exercises `spec-kitty next`'s tasks-boundary decision directly (not just the pure `_evaluate_requirement_mapping`/`evaluate_guards` core in isolation) against both configurations above — zero WP files, and ≥1 WP file none of which reference the bare-prose ids — and asserts the returned `Decision.kind` does not advance past the tasks boundary in either case, with the failure detail naming the specific uncounted FR ids.

**Acceptance Scenarios**:

1. **Given** a spec.md with bare-prose FR-001/FR-002 and zero WP files materialized yet, **When** `spec-kitty next` is asked what happens next at the tasks-packages boundary, **Then** the decision does not advance, and the failure detail is traceable to the bare-prose requirements (not only the generic "materialize WP packages first" message that would fire regardless).
2. **Given** the same spec.md with ≥1 WP file present, none of which declare `requirement_refs` for FR-001/FR-002 (because those ids were never offered by `map-requirements`, since they are undeclared), **When** `spec-kitty next` evaluates the tasks-finalize/terminal boundary, **Then** the decision does not advance, and the failure detail names FR-001/FR-002 specifically — proving this is not merely the pre-existing missing/unknown-ref check incidentally catching the same case.
3. **Given** the plan phase's audit of which step_id vocabulary (`tasks_finalize` CLI-native vs. composed `"tasks"` with `legacy_step_id`) is live for production `spec-kitty next` dispatch at this boundary, **When** the implementation wires the new signal, **Then** plan.md documents the finding and the wiring covers the live vocabulary — with a test proving the guard actually invoked in production reads the new signal, not only a guard reachable solely via test-only construction.
4. **Given** a synthetic unit test that reverts the wiring (a "teeth" test, mirroring `NFR-002`'s non-vacuity pattern elsewhere in this repo), **When** the wiring is removed, **Then** the test fails — proving the new signal's guard-reachability is actually exercised, not merely present in source.

---

### User Story 4 - Corpus-validated, with the false-positive rate recorded in-repo (Priority: P1)

Before the new detector gates anything, it is measured against the real `kitty-specs/` corpus (366 files at #3395's own measurement; re-count at implementation time since the corpus grows — 369 directories present as of this spec's authoring, which already includes this mission's own scaffold) for false positives, and the measured rate is recorded in-repo — not only in a mission transcript or PR description that later becomes unreachable.

**Why this priority**: This is the reason the all-undeclared hard-fail prototype was rejected in #3395 (~6% FP rate, driven by legitimate citations of external conventions inside description columns of correctly-declared table rows — already pinned as a negative-space case in Story 2's Scenario 3). The section-scoped detector this mission promotes to blocking has never itself been corpus-measured as a *blocking* signal. Shipping it unmeasured would repeat the exact evidentiary gap #3395 refused to ship past.

**Independent Test**: A corpus-validation pass (script or test, run against the full `kitty-specs/*/spec.md` tree) computes how many real specs would newly block under the new detector, manually or systematically classifies each as a true or false positive, and the resulting false-positive rate is written into the repository — in a module docstring/comment on the new detection code, following the precedent already set by `_DECLARED_ID_PATTERNS`'s own docstring in `src/specify_cli/requirement_mapping.py` (lines ~43-53), which records #3395's 6% figure and the rejected prototype's rationale in exactly this way.

**Acceptance Scenarios**:

1. **Given** the full `kitty-specs/*/spec.md` corpus at implementation time, **When** the new blocking detector runs against every file, **Then** the count of specs it would newly flag, and the count of those flags that are genuine bare-prose requirements versus false positives, is recorded.
2. **Given** that measurement, **When** the implementing work package lands, **Then** the measured false-positive rate is recorded in-repo (module docstring/comment co-located with the detection code), by explicit numeric value — not "low," not "acceptable," a number, mirroring the existing 6% figure's precedent.
3. **Given** the measured rate, **When** it is non-trivially higher than the rate a maintainer would accept for a mandatory gate (this mission's plan phase sets and justifies the bar; a rate anywhere near #3395's rejected 6% is presumptively too high for a *blocking* gate), **Then** the mission narrows the detector further (e.g. tighter section-title matching, additional shape exclusions) and re-measures — it does not ship an unacceptably noisy gate with a "we recorded the number" fig leaf.
4. **Given** the recorded false-positive rate, **When** a future maintainer reads the detector's module docstring, **Then** they can find the number, the corpus size and date it was measured against, and the rationale — without needing to reconstruct it from a mission transcript.

---

### User Story 5 - The detector never silently reports clean when it cannot classify (Priority: P1)

When the new detection path encounters a case it genuinely cannot classify with confidence — an ambiguous shape, a parse edge case, a malformed heading, an exception during section-scoping — it raises, reports, or refuses; it never silently returns `0` uncounted requirements, `None`, or an `unknown`-and-therefore-ignored classification that a caller would read as "coverage is clean."

**Why this priority**: This is the operator's explicit framing: #3396 IS an instance of this repository's silent-success failure class (#3133, #3212, #3282, #3336), not an ordinary feature gap. The fix for a silent-success defect that itself silently swallows its own edge cases is not a fix — it is the same defect class recurring one layer deeper. This governs Stories 1-4's implementation, not a separable feature.

**Independent Test**: A fault-injection test forces the new detector's section-scoping or shape-classification logic into a state it cannot cleanly resolve (e.g. a monkeypatched exception mid-computation, or a constructed input at the edge of the heading-section boundary logic) and asserts the caller-visible result is a surfaced failure/report — not a quietly empty result indistinguishable from "nothing to flag."

**Acceptance Scenarios**:

1. **Given** the new blocking-detector computation raises an unexpected exception, **When** `finalize-tasks`/`map-requirements`/`spec-kitty next` catch it, **Then** the surfaced result is an explicit failure naming what could not be classified and why — never a swallowed exception that falls through to "0 uncounted, proceed."
2. **Given** an ambiguous input the detector's shape rules were not designed to resolve confidently (documented as such in the new code's own comments, mirroring the existing declared-shape docstring's edge-case documentation style), **When** the detector runs, **Then** it treats the ambiguous case as requiring review (surfaced, non-silent) rather than defaulting to "not a requirement, ignore."
3. **Given** this new fail-loud behavior, **When** it is contrasted against the deliberately fail-*safe*, never-crash-into-a-gate design of the existing `_log_requirement_extraction_warnings_safely` advisory wrapper (`src/runtime/next/runtime_bridge.py`, ~line 835), **Then** the spec/plan explicitly distinguish the two: the *advisory* computation must never crash into a false gate failure (existing, unchanged behavior); the *new blocking detector*, when it genuinely cannot classify, must not silently report clean — these are two different failure-handling contracts for two different code paths, and the implementation must not conflate them (e.g. by routing the new detector through the same swallow-and-log-at-DEBUG wrapper).

---

### User Story 6 - Reflexivity: missions mid-flight when this ships (Priority: P2)

The mission states plainly what happens to every other mission currently running when this change lands — including this mission itself.

**Why this priority**: This change touches `spec-kitty next`'s advance-vs-stay guard, the machinery every other running mission (including the one authoring this spec) depends on to know whether it can proceed. An unstated behavior change to shared control-plane machinery is a process risk independent of whether the code is correct.

**Independent Test**: The plan/tasks phases document, and the implementing work package's PR description states, which currently-in-flight missions (if any, at merge time) have a spec.md containing bare-prose requirement shapes that would newly block at the tasks boundary, and what the operator's remediation path is (rewrite the offending requirements into a declared shape; no code-level grandfathering is proposed by this spec).

**Acceptance Scenarios**:

1. **Given** this change ships and a mission currently at or approaching the `tasks_packages`/`tasks_finalize` boundary has a spec.md containing bare-prose requirements, **When** that mission's `spec-kitty next` is next invoked, **Then** it newly blocks where it previously advanced (or advanced silently past uncounted requirements) — this is the intended, disclosed behavior change, not a regression to be hidden.
2. **Given** this mission's own spec.md (this document), **When** the new detector runs against it, **Then** it does not block — every requirement in this document is written in one of the four declared shapes (table row `| ID | Title | ... |`), which the author has verified by construction while writing this spec.
3. **Given** the operator merges this change, **When** any other in-flight mission is newly blocked by it, **Then** the remediation is documented (rewrite bare-prose requirements into a declared shape) rather than silently defaulted around.

### Edge Cases

- **Description-column citations in correctly-declared tables** (Story 2, Scenario 3): the #3395-measured 6% false-positive driver. The new detector must not re-trigger on a table row whose ID cell is properly declared but whose description/body column happens to mention a foreign or malformed id-shaped token.
- **Heading-title matching for "Requirements" sections**: `_is_requirement_heading` (`src/specify_cli/requirement_mapping.py`) matches any heading whose text contains "requirement" case-insensitively — this could over-match a heading like "Non-Requirements Notes" or under-match a section titled without the literal substring (e.g. "What This Spec Must Do"). The corpus validation in Story 4 is the empirical check on this; the plan phase should record whether any corpus specs hit this boundary.
- **Section boundary edge cases**: `_requirement_named_sections` scopes a section from its heading to the next heading of *any* level. A bare-prose requirement written just before a lower-level sub-heading that re-enters the same logical section may fall outside the detected scope; Story 5 (never silently clean) governs whether that's flagged as ambiguous or genuinely excluded.
- **Zero WP files vs. ≥1 WP file with none referencing the bare-prose ids**: two structurally different reasons `spec-kitty next` might already be "blocked" or "not blocked" today; Story 3 requires both configurations to be tested, since the reverted `_zero_declared_requirement_block` only ever addressed (and only in a way proven inert for) something adjacent to the first.
- **The CLI-native `tasks_finalize` vs. composed `"tasks"`/`legacy_step_id` vocabulary split**: `_evaluate_tasks_finalize_guard` does not read `requirement_mapping_failures` today at all; only the composed terminal guard does. This is a pre-existing asymmetry this mission's wiring choice must not paper over silently (Story 3's fourth-call-site note).
- **The `main`-branch red-first impossibility**: this mission's `planning_base_branch` is PR #3395's branch (`op/3394-requirement-citation-scope`), not `main`. On `main`, the declared-shape extraction mechanism this mission extends does not exist yet at all, so a red-first ATDD test for this mission's blocking behavior cannot be run RED against `main` — only against the actual `planning_base_branch`. The plan phase must state this explicitly rather than silently assuming a `main`-relative RED baseline (C-011 binding; see Constraints).
- **Pre-existing test baseline**: issue #3284 tracks ~23 known-red tests on `main`; this mission must not assume a clean baseline in any acceptance criterion, and any newly-discovered pre-existing failure must be reported per the charter's Pre-existing Failure Reporting Rule before being treated as accepted baseline.

## Requirements *(mandatory)*

### Functional Requirements

| ID | Title | User Story | Priority | Status |
|----|-------|------------|----------|--------|
| FR-001 | Promote section-scoped bare-prose-requirement detection from advisory-only to a blocking signal, reusing `_requirement_named_sections` / `find_undeclared_requirement_citations`-style scoping (not doc-wide detection) | As a maintainer, I want a spec's bare-prose requirements surfaced through a blocking path, not only a log line. | High | Open |
| FR-002 | Wire the new blocking signal into `spec-kitty next`'s tasks-boundary advance-vs-stay decision in a way that is demonstrably NOT gated behind the `tasks_wp_files`/`_tasks_dir_ready` short-circuit that made `_zero_declared_requirement_block` provably inert | As a maintainer, I want the new signal to actually change `spec-kitty next`'s decision, not repeat dead code under a new name. | High | Open |
| FR-003 | Audit which step_id vocabulary (`tasks_finalize` CLI-native vs. composed `"tasks"`/`legacy_step_id`) production `spec-kitty next` actually dispatches at the finalize boundary, and wire the new signal into the live vocabulary (documented finding, not an assumption) | As a maintainer, I want the fix to reach the guard `spec-kitty next` actually invokes in production, not only the guard named in the issue text. | High | Open |
| FR-004 | Preserve #3394's repro shape as non-blocking: a spec whose own requirements are all declared correctly, citing a foreign id in prose, must not block under the new detector | As a maintainer, I want the #3394 fix to remain intact while #3396 closes. | High | Open |
| FR-005 | Corpus-validate the new blocking detector against the full `kitty-specs/*/spec.md` corpus, classify each new-would-block spec as true/false positive, and record the measured false-positive rate in-repo (module docstring/comment, following the existing 6% figure's precedent) | As a maintainer, I want the gate's real-world noise level measured and durably recorded before it can block anyone. | High | Open |
| FR-006 | If the measured false-positive rate is unacceptably high for a mandatory gate, narrow the detector and re-measure before shipping — do not ship a noisy gate with the number merely recorded | As a maintainer, I want corpus validation to actually gate the ship decision, not just document a number after the fact. | High | Open |
| FR-007 | Ensure the new detector never silently reports "0 uncounted" or "clean" when it cannot confidently classify an input; ambiguous or exceptional cases surface as an explicit failure/report | As a maintainer, I want this fix to not itself become another silent-success defect. | High | Open |
| FR-008 | Keep the new blocking detector's failure-handling contract distinct from the existing advisory wrapper's fail-safe (`_log_requirement_extraction_warnings_safely`) contract — do not route the new blocking computation through the same swallow-and-log-at-DEBUG path | As a maintainer, I want the advisory's "never crash into a gate" guarantee to stay intact while the new detector's "never silently clean" guarantee is independently enforced. | High | Open |
| FR-009 | Document, in plan.md and the implementing PR description, which currently in-flight missions (if any at merge time) would newly block under this change, and the operator-facing remediation | As an operator, I want to know what breaks for in-flight missions before this ships, not discover it live. | Medium | Open |
| FR-010 | Add a non-vacuity ("teeth") test proving the new signal's guard-reachability is actually exercised by removing/reverting the wiring and asserting the test fails | As a maintainer, I want proof the new signal is load-bearing, not merely present in source (mirrors this repo's `architectural-gate-non-vacuity` doctrine). | High | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | No doc-wide regression | The new detector must remain section-scoped (Requirements-named headings only); it must never fall back to doc-wide raw-token scanning as a blocking mechanism — that is precisely the #3394 bug. | Reliability | High | Open |
| NFR-002 | Silent-success prohibition | No new code path may return an empty/zero/`None`/`unknown` result for "cannot classify" in a way indistinguishable from "nothing to flag" (FR-007/FR-008). | Reliability | High | Open |
| NFR-003 | Static-analysis cleanliness | All changed/added code passes `ruff` and `mypy --strict` with zero new issues and zero new suppressions. | Maintainability | High | Open |
| NFR-004 | New-code coverage | Every new branch/helper (section-scoped blocking classifier, guard-wiring change, corpus-validation script/test) has a focused test in the same work package. | Maintainability | High | Open |
| NFR-005 | Guard non-vacuity | The new blocking wiring must fail a synthetic reversion (teeth) test, proving it is load-bearing at the guard(s) it targets (FR-010). | Reliability | High | Open |
| NFR-006 | Performance | Detection remains pure regex/string-splitting over already-read spec.md content — no new filesystem or network I/O added to the hot `spec-kitty next` path. | Performance | Medium | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| C-001 | No widening of declared-shape scoping | The four `_DECLARED_ID_PATTERNS` shapes settled by #3394/#3395 are not touched or widened by this mission; #3396 adds a distinct blocking classifier, it does not reopen what counts as "declared." | Technical | High | Open |
| C-002 | ATDD red-first, base-branch caveat | A failing-first test must exist as a separate commit before any implementation commit (charter C-011). This mission's `planning_base_branch` is PR #3395's branch (`op/3394-requirement-citation-scope`), not `main` — the red-first test cannot go RED against `main`, because the declared-shape mechanism this mission extends does not exist there yet. Plan/tasks must state this explicitly and verify RED against the actual `planning_base_branch`. | Process | High | Open |
| C-003 | No clean-baseline assumption | Issue #3284 tracks ~23 known-red tests on `main`. No acceptance criterion in this mission may assume a clean baseline; any newly-discovered pre-existing failure is reported via a GitHub issue per the charter's Pre-existing Failure Reporting Rule before being treated as accepted baseline. | Process | Medium | Open |
| C-004 | Terminology canon | "Mission," never "Feature," in all new/changed user-facing text, error messages, and code identifiers introduced by this mission. | Process | Medium | Open |
| C-005 | Rebase-on-#3395-change risk | This mission's diff sits on top of #3395's unreviewed, still-open (`reviewDecision` empty) parser rewrite. If #3395 changes shape before merge, this mission absorbs the rebase — an accepted, explicitly acknowledged consequence of the operator's branch-now decision (see Clarifications), not a defect to work around silently. | Process | Medium | Open |
| C-006 | Corpus validation gates shipping, not just records it | Per FR-006: an unacceptably high measured false-positive rate blocks shipping the blocking behavior until narrowed and re-measured — it is not satisfied merely by writing a high number into a docstring. | Process | High | Open |

### Key Entities *(include if feature involves data)*

- **Bare-prose requirement candidate**: a raw `FR-`/`NFR-`/`C-`-shaped token found inside a heading section whose title names "Requirements," that matches none of the four declared shapes — the object this mission's new detector classifies and, when genuine, blocks on.
- **Requirements-named section**: the `(heading_text, body)` scoping already produced by `_requirement_named_sections` (`src/specify_cli/requirement_mapping.py`) — the boundary within which this mission's blocking detection operates, deliberately narrower than the whole document.
- **Blocking signal / guard-consumption point**: the as-yet-undetermined (plan-phase decision, FR-002/FR-003) location(s) in `runtime_bridge.py` / `runtime_bridge_cores.py` where the new signal must be read so it actually changes `spec-kitty next`'s advance-vs-stay `Decision` — the central risk object of this mission, given the `3823f2b00` revert precedent.
- **Corpus false-positive record**: the durable, in-repo (module docstring/comment) statement of the new detector's measured false-positive rate against the `kitty-specs/*/spec.md` corpus, corpus size, and measurement date — following the precedent of the existing #3395 6% figure recorded in `src/specify_cli/requirement_mapping.py`.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The issue's exact repro spec.md (declared NFR + bare-prose FR-001/FR-002) blocks `finalize-tasks`, `map-requirements`, and `spec-kitty next`'s tasks-boundary decision, all naming FR-001/FR-002 explicitly.
- **SC-002**: The full pre-existing #3394/#3395 test suite (`tests/specify_cli/test_requirement_mapping.py`, `tests/next/test_runtime_bridge_unit.py`, `tests/runtime/test_bridge_cores.py`) passes unmodified in its pinned assertions after this mission lands; #3394's repro shape stays green.
- **SC-003**: A regression test proves the new signal reaches `spec-kitty next`'s decision in both the zero-WP-files and the ≥1-WP-files-none-referencing configurations, independent of the `tasks_wp_files`-first guard ordering that made the reverted `_zero_declared_requirement_block` inert; a teeth test proves this wiring is load-bearing (fails when reverted).
- **SC-004**: The plan phase documents which step_id vocabulary (`tasks_finalize` CLI-native vs. composed `"tasks"`) is live for production `spec-kitty next` dispatch at the finalize boundary, and the implementation's wiring covers it.
- **SC-005**: The new detector is corpus-validated against the full `kitty-specs/*/spec.md` corpus (369+ specs at this writing; re-measured at implementation time); the measured false-positive rate is recorded in-repo, by explicit numeric value, co-located with the detection code.
- **SC-006**: If the measured false-positive rate is unacceptably high for a mandatory gate, the detector is narrowed and re-measured before the blocking behavior ships — the mission does not ship a noisy gate with only a recorded number as mitigation.
- **SC-007**: No new code path returns an empty/zero/silent result for a case the detector cannot confidently classify; a fault-injection test proves ambiguous/exceptional cases surface as an explicit failure, not silent "clean."
- **SC-008**: Plan.md and the implementing PR description name any currently in-flight missions that would newly block under this change (including this mission's own spec.md, verified clean by construction) and state the operator-facing remediation.
- **SC-009**: All changed/added code passes `ruff` and `mypy --strict` with zero new issues/suppressions; every new branch/helper has a focused test in its work package.
