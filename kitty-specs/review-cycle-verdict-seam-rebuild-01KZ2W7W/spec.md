# Mission Specification: Review-Cycle Verdict Seam Rebuild

**Mission Branch**: `pr/review-verdict-write-integrity-01KZ1CGF`
**Created**: 2026-08-03
**Revised**: 2026-08-03 (post-spec adversarial squad — see Revision History)
**Status**: Draft
**Input**: Fast-follow to closed PR #3156, plus issues #3157, #3158, #3159, #3160.

## Baseline

Every current-state claim, count, and success criterion in this document is anchored to the tip of `pr/review-verdict-write-integrity-01KZ1CGF`, which carries the eleven landing folds from the closed PR #3156. The measured baseline for that tip is committed at `research/baseline-8466727eb.md`; re-derive it rather than trusting a SHA quoted in prose.

The **regression baseline** for NFR-001 is a different commit: **`8466727eb`**, the merge-base with `main`. That is deliberate. This branch ships the predecessor's implementation *and* its eleven folds as one PR, so a failure introduced by any of them is new to `main` even though it predates this mission. Measuring against the branch tip would launder the entire predecessor PR.

## Why this mission exists

PR #3156 fixed a real bug: approving a rejected work package advanced the lane but wrote nothing, so a stale `rejected` verdict stayed authoritative and blocked every later gate.

It fixed it by adding a second writer, a second directory resolver, an optional commit step and a content-identity guard — each defending against one failure rather than making the failure impossible. A five-lens adversarial squad then found seven MAJOR defects; four were folded onto this branch, and a second squad found that two of those folds are themselves incomplete.

The pattern is the point. This is one shape producing many symptoms, and patching them individually produces the next one.

## Revision History

This spec was rejected by all four post-spec lenses (`architect-alphonso`, `reviewer-renata`, `planner-priti`, `debugger-debbie`) and substantially rewritten. What changed, and why, because the errors are instructive:

| Original claim | Finding | Resolution |
|---|---|---|
| FR-008: #3157 is a lane read/write coherence defect | **Refuted by reproduction.** The reducer sorts by `(e.at, e.event_id)`; the test hard-codes `at="2026-08-01T10:00:00+00:00"`, authored 2026-07-21. Changing it to `2027-08-01` passes with **zero product code touched**. The product is correct. | FR-014: fix the test, ban the class. The original FR would have licensed rewriting a correct guard. |
| SC-001: a second reject→approve round currently fails | **Refuted.** Fixed by fold `95d8dbc6f`; its test passes. The real defect is the opposite: a second **rejection** with identical feedback is permanently refused. And SC-001 contradicted this spec's own US6. | FR-004 + US1 AC5. Taken literally, the original would have had an implementer delete the content-identity guard and re-open #990/#2996(b). |
| "3 writers, 2 resolvers, 5 frontmatter readers" | **All three understated** (≥5 / ≥3 / ~20), and the lenses disagreed on how to count. | NFR-007 now requires the architectural check to be built **first** and to *produce* the census. No numerals are pinned. |
| FR-001 (v1): verdict and transition are atomic | **Not achievable.** The verdict commits to the primary branch; the lane event commits to the coordination branch inside a transaction that structurally refuses outside paths. | Re-anchored — but the first re-anchor was also wrong; see the row below. |
| FR-001 (v2): the artifact is a *projection* of the event | **Also false, and measured.** `ReviewResult` carries four fields; `ReviewCycleArtifact` carries eleven. `body`, `affected_files`, `reproduction_command`, `cycle_number`, `override_actor`, `override_reason` have no counterpart, so the artifact is not reconstructible from the log. And `reduce()` never mentions `review_result` — the reduced snapshot has no verdict at all. The relation is the **inverse**: `reference` is a `feedback://` URI and `feedback_path` is a pointer, so the event is an *index* and the artifact is the *payload*. | FR-001 (v3) states the true split: the event is authoritative for **which verdict and where**; the artifact is authoritative for **what the reviewer said**. Neither is a projection of the other. |
| NFR-001 measured against "the mission's own base commit" | Launders the eleven folds; constrains the number zero but not the method. | Baseline pinned to `8466727eb`; method prohibition added. |
| `change_mode: bulk_edit` with renames in scope | **No legal execution order.** The gate is mission-scoped and freezes the occurrence map before any WP runs, over symbols this mission rewrites. | `change_mode: normal`. Renames deferred to a successor mission whose map is authored against post-rebuild code. |

Four reproduced failure modes absent from the original are now in scope: concurrent-write verdict loss, orphan-survives-failed-transition, crash-between-write-and-commit, and `skip_target_branch_commit` on protected-primary coord.

**Operator-authorized deviation.** The binding clause is **DIRECTIVE_025 (Boy Scout Rule)** — *"filed as issues and deferred, never silently absorbed"* — not DIRECTIVE_024 (Locality of Change), which is advisory. The out-of-domain requirements are **FR-018 and FR-019** (#3159, #3160); an earlier revision named FR-016/FR-017, which are coverage-shard independence and test-name truthfulness, both squarely in domain. The charter reconciles 024 and 025 by permitting *"deferring genuinely broad refactors with a rationale"* — two single-check CI greens are not a broad refactor, they are filed issues, and their inclusion is recorded. Retaining them is charter-legal, not an exception.

## Definitions

**Affected suites** — load-bearing in NFR-001 and SC-007, so defined explicitly rather than left to the implementer:

```
tests/review/
tests/status/
tests/regression/test_2646_stale_verdict_closes_via_fr001.py
tests/integration/test_review_cycle_rejection_only.py
tests/integration/test_ac5_hash_guard.py
tests/integration/test_wp_file_hash_stability.py
tests/post_merge/test_review_artifact_consistency.py
tests/specify_cli/cli/commands/agent/
```

**Durably persisted** — written **and** committed, such that a branch switch cannot lose it. A record present on disk but absent from git index membership is *not* durably persisted, and no read path may treat it as authoritative.

**Verdict record** — the artifact recording one review decision. It is authoritative for its own *content* (the reviewer's prose, affected files, reproduction command). It is **not** authoritative for which verdict is current — see below.

**Verdict authority (the split, measured)** — the status event is authoritative for **which verdict is current and where its content lives**; the verdict record is authoritative for **what the reviewer actually said**. Neither reconstructs the other:

- `ReviewResult` on `StatusEvent` carries four fields — `reviewer`, `verdict`, `reference`, `feedback_path`. `reference` is a `feedback://` URI; `feedback_path` is a pointer. It is an **index entry**.
- `ReviewCycleArtifact` carries eleven, six of which (`body`, `affected_files`, `reproduction_command`, `cycle_number`, `override_actor`, `override_reason`) exist nowhere on the event. It is the **payload**.
- `reduce()` does not surface `review_result` today. Nothing downstream of the reducer can read it, so the index exists but has no reader.

This split is the mission's actual subject. A consumer asking *"is this work package approved?"* must reach the event; a consumer asking *"why was it rejected?"* must reach the artifact; and the two must never disagree about the first question.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A recorded verdict means the transition happened (Priority: P1)

A reviewer's decision and the lane move are the same fact. There is no state in which a durably recorded approval exists for a work package that never moved, and none in which a work package moved on evidence that was never durably persisted.

**Why this priority**: the mission's core invariant, and the one with a safety consequence — the merge gate reads the recorded verdict, so a fabricated or orphaned `approved` makes it report green for work nobody approved. Reproduced.

**Independent Test**: force failure in **both** directions — inject a transition failure after the verdict would be written, and a durable-write failure after the transition succeeded — and assert the authoritative store never disagrees with the outcome.

**Acceptance Scenarios**:

1. **Given** a work package whose latest verdict is `rejected`, **When** a reviewer approves it and the transition completes, **Then** the approval is durably persisted and the work package is in the approved lane.
2. **Given** the same work package, **When** the transition fails after the verdict would have been written, **Then** no approved verdict is readable by any consumer, and the latest verdict is still `rejected`.
3. **Given** a transition that has completed, **When** the durable write fails, **Then** the work package has not moved.
4. **Given** a process killed between the write and the commit, **When** the reviewer retries the identical command, **Then** it succeeds and records the correct verdict — with no manual cleanup.
5. **Given** a reviewer who finds the same defect a second time, **When** they submit reviewer feedback identical to a prior cycle's, **Then** the rejection is accepted and recorded as a new cycle.
6. **Given** two agents recording distinct verdicts for one work package simultaneously, **When** both complete, **Then** two distinct records exist, or the second is refused with a diagnostic — never a silent overwrite.
7. **Given** a verdict directory with a gap in its cycle numbering, **When** a new verdict is recorded, **Then** no existing record is overwritten. *(FR-006)*
8. **Given** `--no-auto-commit`, **When** a verdict is recorded, **Then** the `--json` payload carries a named key stating the record was written but not durably persisted. *(FR-013)*
9. **Given** the matrix of verdict × target lane × topology × auto-commit setting, **When** each cell is exercised through the real command surface, **Then** durability behaves as that cell specifies, and removing the commit call turns each cell red. *(FR-015)*

---

### User Story 2 - An arbiter waiver stays a waiver, and clears the gate (Priority: P1)

An arbiter who knowingly proceeds over a standing rejection produces an override record with its stated reason — not an approval review nobody performed. That override then satisfies the merge gate on its own.

**Why this priority**: the second half is what makes the first half safe. Suppressing the fabricated approval alone would leave the work package with a `rejected` latest verdict and nothing recording the arbitration. Note a correction: `--skip-review-artifact-check` is a flag on `agent tasks move-task`, **not** on the merge command — an earlier revision described operators reaching for it at merge time, which is not a thing that can happen. The flag is the override's *creation* mechanism. Raised to P1 because the naive fix (an early return) suppresses the record without replacing it.

**Independent Test**: run the override path; assert no approval verdict is written, the override is durably persisted on the same partition as the record it annotates, and the merge gate accepts it without `--skip-review-artifact-check`.

**Acceptance Scenarios**:

1. **Given** a work package with a standing rejection, **When** an arbiter overrides with a stated reason, **Then** the override is durably persisted and no approval verdict is written.
2. **Given** an override that survives a fresh clone of the branch, **When** the merge gate evaluates the work package, **Then** it passes. (A *complete* override already passes today; what does not survive is the record itself, because the arbiter writer never commits.)
3. **Given** an override whose persistence fails, **When** the command returns, **Then** the failure is surfaced — never swallowed into a warning.

---

### User Story 3 - Every component agrees where a verdict lives (Priority: P1)

Reads and writes of a work package's verdict resolve the same location, for every work-package filename the system accepts.

**Why this priority**: not debt — a live correctness hole, and a prerequisite for C-001. The merge-time backstop that justifies the guard relaxation resolves through one of the divergent paths, so the surviving control is subject to this very defect. Promoted to P1 accordingly.

**Independent Test**: for each accepted filename separator, assert every read and write path resolves one identical directory. Includes a pre-existing record written under a retired path.

**Acceptance Scenarios**:

1. **Given** a work package file using any accepted separator (`-`, `_`, `.`, or none), **When** its verdict is read, written, evaluated by the merge gate, or displayed, **Then** all paths address the same directory.
2. **Given** a repository with verdict records written under a now-retired path, **When** the mission's changes land, **Then** those records are detected and reconciled or reported — never silently orphaned.
3. **Given** a work-package filename the system cannot resolve unambiguously, **When** it is processed, **Then** it is refused with a diagnostic rather than silently degraded to the bare work-package id.

---

### User Story 4 - Verdict readers fail the same way (Priority: P2)

Every component reading a verdict reaches the same conclusion about a damaged record — and that conclusion is fail-closed.

**Why this priority**: the divergence is not body text, it is **failure polarity**. A measured census over one damaged record found **four** distinct behaviours, not two:

| Reader | Behaviour on a non-UTF-8 record |
|---|---|
| `agent_utils/status.py` (kanban) | returns `None` — **fail-open** |
| `review/cycle.py` provenance scan | skips and continues (fold `97a9ecfae`) |
| `post_merge/review_artifact_consistency.py` (merge gate) | structured finding — **fail-closed** |
| `review/arbiter.py` override reader | **uncaught crash**, inconsistent with the JSON branch three lines above it |

An earlier revision claimed the merge gate crashes. It does not — that was already fixed, and stating it wrongly would have sent an implementer hunting a defect that is not there. The live problems are the fail-open kanban reader on a surface operators trust, and the uncaught arbiter crash.

**Independent Test**: a damaged verdict record; assert every reader either refuses consistently or skips consistently, and that no safety-relevant reader fails open.

**Acceptance Scenarios**:

1. **Given** a verdict record that is not valid UTF-8 or is unreadable, **When** any reader in the census reads it, **Then** it resolves to its declared polarity — no reader crashes uncaught, and no safety gate treats the record as "no verdict".
2. **Given** such a record, **When** a reviewer records a new verdict, **Then** it succeeds.

---

### User Story 5 - Names and tests tell the truth (Priority: P3)

No test in the affected suites has a name or contract key that contradicts its assertions, and the flagship end-to-end test exercises the ordinary path.

**Why this priority**: no wrong runtime outcome, but it is how several of these defects survived review — a maintainer greps for a guard, finds a green test named for it, and concludes the guard exists.

**Independent Test**: an enumerated audit table over the affected-suites path list — every test, its name, its assertion summary, its verdict.

**Acceptance Scenarios**:

1. **Given** any test in the affected suites, **When** its name and contract key are compared to its assertions, **Then** they agree.
2. **Given** the flagship end-to-end test, **When** it runs, **Then** it asserts the non-forced path.

---

### User Story 6 - Time-dependent tests cannot rot (Priority: P3)

No test encodes an absolute wall-clock timestamp that changes the test's meaning as the date passes.

**Why this priority**: #3157 was exactly this, and it silently starves five CI coverage shards — including `fast-tests-review`, the only shard covering this mission's own write surface. An earlier revision claimed a second live instance in the #2646 fixture; that was checked by running it (`2 passed`) and withdrawn — its events are all hard-coded, so its order is stable. The measured surface: **218 test files carry absolute event timestamps, but only 28 also emit `now()` events**. Banning the literal would flag ~580 sites at roughly 87% false positive and require an allowlist that would have exempted #3157 itself. Banning the *mixture* has a 28-file surface and is shippable.

**Independent Test**: the #3157 test passes with no product change; an architectural check fails when an absolute event timestamp is introduced.

**Acceptance Scenarios**:

1. **Given** the #3157 lifecycle test, **When** it runs at any future date, **Then** it passes without product changes.
2. **Given** a new test that appends a hard-coded event timestamp into the same event log as a `now()`-generated one, **When** the architectural check runs, **Then** it fails. A fixture whose events are *all* hard-coded has stable relative order forever and must **not** be flagged.

---

### User Story 7 - The board is clean (Priority: P3)

Coverage shards stop being starved by unrelated failures, and two pre-existing mainline reds are resolved.

**Why this priority**: P3 by intrinsic value, but **FR-016 is a hard prerequisite for measuring this mission at all** and must be sequenced first. `fast-tests-review` is the only CI shard running `tests/review/` with `--cov=src/specify_cli/review`, and it is gated on `fast-tests-status`, which #3157 keeps red. Until FR-014 and FR-016 land, this mission's primary write surface produces no coverage XML, NFR-004 cannot be measured in CI, and SC-009 is unverifiable there. FR-018/FR-019 remain genuinely droppable; FR-016 does not.

**Independent Test**: a push to the mainline produces coverage for every shard currently gated on another shard's result; the two named checks pass.

**Acceptance Scenarios**:

1. **Given** a push to the mainline with one shard failing, **When** the workflow runs, **Then** every coverage shard still runs and reports.
2. **Given** the mainline, **When** the profile-cited-directives parity check runs, **Then** it passes against the resolved activation set rather than budget-dependent rendered text.
3. **Given** a command whose flag surface has grown, **When** the frozen contract check runs, **Then** it passes against a re-pin naming each added flag and the commit that introduced it.

---

### Edge Cases

Evidence status is stated per item, because an earlier revision of this spec claimed four reproductions while `research/` held evidence for one. **Reproduced** means an artifact in `research/` or a cited probe output. **Reproduction owed** means the defect is asserted from code reading and its reproduction is the first task of the work package that fixes it — a red test before the fix, per the charter's ATDD-first discipline.

- **Concurrent verdict writes.** *Reproduction owed.* Two agents, distinct verdicts, no lock on the write path — asserted to leave one record with both callers reporting success. Two records or an explicit refusal; never silent loss.
- **Transition fails after the verdict is written.** *Reproduced* — `research/wave3-partial-atomicity.diff`. Leaves a committed `approved` orphan; the retry short-circuits and reports success while writing nothing.
- **Process killed between write and commit.** *Reproduction owed.* The `try/except` compensator does not run. The rejection can then never be re-submitted; the approval path moves the work package on an uncommitted verdict.
- **Protected-primary under coord topology.** *Reproduction owed.* `skip_target_branch_commit` is not threaded to the verdict writer, so neither verdict can be recorded at all.
- **Cycle-number gaps.** *Reproduced* — `next_cycle_number()` returns 3 for `['review-cycle-1.md', 'review-cycle-3.md']`, colliding with a live record. Numbering is count-based.
- **A prior record is unreadable.** Recording a new verdict still succeeds, and no reader fails open.
- **A record exists under a retired resolver path.** Detected and reconciled or reported.
- **A pre-ADR mission has its review cycles on the primary surface.** Measured: 45 such missions, and **every one** has had its coordination branch deleted by merge, so the seam raises `CoordinationBranchDeleted` before any read happens. The read must **absorb that exception** to PRIMARY — an empty-directory check is the wrong shape and would not fire. It must never report "no verdict"; that failure mode on a safety gate is what the partition change must not introduce.
- **Both surfaces hold a record for the same work package.** COORD wins under a coordination topology. This is a deliberate inversion of a landed field report (PR #2834), which pinned the opposite while review cycles were PRIMARY.
- **Validation failure or interrupted write.** Treated as a failed write, leaving no partial record.

## Domain Language

| Canonical term | Meaning | Avoid |
|---|---|---|
| **Verdict record** | The artifact projecting one review decision. Not the authority after FR-001. | "review cycle file", "rejection file" — it holds both verdicts. |
| **Authoritative verdict** | The verdict carried on the status event. The single source of truth. | "the verdict in the file". |
| **Arbiter override** | A knowing decision to proceed over a standing rejection, with a stated reason. | "approval", "force approve" — US2 exists because these differ. |
| **Durably persisted** | Written **and** committed. | "saved", "written". |

## Requirements *(mandatory)*

### Functional Requirements

| ID | Title | User Story | Priority | Status |
|----|-------|------------|----------|--------|
| FR-001 | One authority per question, and a reader for it | As a maintainer, I want the status event to be the sole authority for *which* verdict is current, the artifact to be the sole authority for its *content*, and the event's verdict to be readable downstream of the reducer — so that no consumer has to choose between two answers to the same question. | High | Open |
| FR-022 | The authority can express an override | As an auditor, I want the authoritative verdict vocabulary to distinguish an arbiter override from an approval, so that making the event authoritative does not force a waiver to be recorded as an approval. | High | Open |
| FR-002 | No readable verdict survives a failed transition | As an auditor, I want a failed transition to leave no verdict any consumer can read, so that the merge gate cannot pass work nobody approved. | High | Open |
| FR-003 | Interruption-safe, including process kill | As a reviewer, I want an interrupted command — including a killed process — to leave a state my identical retry can recover from with no manual cleanup. | High | Open |
| FR-004 | Repeat feedback is recordable, without disarming the guard | As a reviewer, I want to re-report a recurring defect in the same words and have it recorded. The content-identity check is **narrowed, not removed**: re-submitting a file that *is* a prior verdict record (path identity, or content that parses as one) stays refused — that is the #990 / #2996(b) control. Distinct reviewer prose that merely repeats earlier prose is admissible. Deleting the content leg to satisfy this FR is a C-002 violation. | High | Open |
| FR-005 | Concurrent verdicts are serialized | As a maintainer, I want two simultaneous verdicts to produce two records or an explicit refusal, so that a verdict is never silently destroyed. | High | Open |
| FR-006 | Verdict numbering never overwrites | As an auditor, I want a new record to never overwrite an existing one, so that history cannot be destroyed by a gap in numbering. | High | Open |
| FR-023 | Review cycles are a first-class artifact kind on the right partition | As a maintainer, I want review-cycle artifacts to carry their own kind that resolves COORD under coordination topologies and PRIMARY otherwise, so the verdict authority and the verdict record stop landing on different branches. Read **and** write paths resolve through that one kind; a caller-supplied directory is not a substitute for either. Governed by ADR 2026-08-03-1, which also names the classifier and commit-router work this requires — the read seam follows the kind automatically, the write side does not. | High | Open |
| FR-007 | One resolution, including slug derivation | As a maintainer, I want every read and write of a verdict to resolve one identical location for every accepted filename, so that a verdict cannot be written where nothing looks for it. | High | Open |
| FR-008 | Records under retired paths are reconciled | As an operator upgrading an existing repository, I want records written under a path this mission retires to be detected and reconciled or reported, so that a standing rejection cannot silently vanish. **"Retired path" is defined by the FR-007 census, not chosen by the implementer**: for every resolver the census marks `retire`, a reconciliation pass exists and its test seeds a record at that resolver's output *before* consolidation lands. A reconciliation that finds nothing because it was pointed at no resolver is a census failure, not a pass. The trigger must be stated (upgrade migration, read-time reconciliation, or a repair command), and whether cross-branch records under coord topology are in scope. | High | Open |
| FR-009 | The arbiter seam resolves and persists correctly | As an auditor, I want override evidence written where it is read from, on the correct partition, with failures surfaced rather than swallowed. | High | Open |
| FR-010 | Override durability closes the gate path that is still open | As an arbiter, I want my override to be **durably persisted** and to clear the merge gate, so that arbitration survives a branch switch. A *complete* override already clears the gate without any flag (`test_2684_review_override_recognition.py`, 3 passed) — the residual is that the arbiter writer never commits, and the incomplete-override path. | High | Open |
| FR-011 | Overrides never fabricate an approval | As an auditor, I want an override recorded as an override, so that a waiver is never indistinguishable from a review approval. | High | Open |
| FR-012 | Every verdict reader declares its failure polarity | As a maintainer, I want every reader in the NFR-007 census to resolve to one of two *declared* polarities — refuse, or skip-and-continue — with no reader crashing uncaught and no safety-gate reader failing open. | High | Open |
| FR-013 | The one sanctioned non-durable path announces itself | As an orchestrator, I want `--no-auto-commit` — the **only** sanctioned way to end with a verdict written but uncommitted — to emit a named key in `--json` as well as human output. Every *other* route to that state is a defect closed by FR-002, not a case to warn about; this FR must not be read as licensing them. | High | Open |
| FR-014 | Time-dependent test rot is prevented | As a maintainer, I want #3157's test corrected and the *mixing* of hard-coded and `now()`-generated event timestamps in one event log banned by a check, so that a test cannot silently start failing because a date passed. | Medium | Open |
| FR-015 | Durability is covered across the real matrix | As a maintainer, I want the durable path exercised through the real command surface across verdict, target lane, topology and auto-commit, so that a regression is caught. | High | Open |
| FR-016 | Coverage shards are independent, and stay that way | As a maintainer, I want **no** coverage shard gated on another shard's `result`, so that one failure cannot starve the diff-coverage gate. Both edge classes are in scope: the `fast-tests-*` chain gated on `fast-tests-status.result != 'failure'`, and the `integration-tests-*` shards gated on their `fast-tests-*` counterpart's `result == 'success'`. Fixing one edge is not compliance. A topology assertion — the repo already has `tests/architectural/ci_topology_census.json` — must fail when a new result-gated edge is added. | High | Open |
| FR-017 | Truthful test names and an unforced flagship test | As a maintainer, I want no test name or contract key contradicting its assertions, and the flagship test to assert the ordinary path. | Medium | Open |
| FR-021 | Behaviour changes reach the changelog | As an operator, I want FR-001, FR-010 and FR-011's observable changes to the review and merge contract recorded in `docs/changelog/CHANGELOG.md`, because DIR-009 makes that binding and the predecessor honoured it. | High | Open |
| FR-018 | Profile-cited parity is budget-independent | As a maintainer, I want the parity check to assert resolved activation, preceded by evidence the divergence is truncation and not a real activation change. | Low | Open |
| FR-019 | Grown flag surfaces are re-pinned with evidence | As a maintainer, I want each added flag named with the commit that introduced it, and the re-pin to fail on removal as well as addition. | Low | Open |
| FR-020 | The contract artifact is executable, not decorative | As a contributor, I want the verdict-recording seam documented in a contract artifact that the **NFR-007 check reads as its expected-set fixture**, so the document fails CI when it and the code diverge. A prose file nothing consults would discharge this FR while going stale immediately. The six existing doc surfaces naming the retired seam (`docs/plans/investigations/review-artifact-write-integrity-3044.md`, two `docs/plans/engineering-notes/` pages, both changelog paths, and `workflow.py`'s inventory docstring) are reconciled in the same work package. | Medium | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | Regression baseline and method | Zero failures in the affected suites beyond the two recorded in `research/baseline-8466727eb.md`. Verification is a **diff against that committed node-id set**, not a re-run. A failure may not be resolved by: re-running; a skip/xfail/quarantine marker; widening a threshold without a recorded investigation; deleting an assertion; **deleting the test; moving the test out of the affected-suites paths; reducing its parametrization; narrowing an assertion; or excluding it at collection or marker-selection level.** The affected-suites node-id set is a floor — it may grow, never shrink. A test that does not exist at `8466727eb` can never be "retained as pre-existing" and must be fixed outright. | Reliability | High | Open |
| NFR-002 | Complexity ceiling | Every touched function ends at cyclomatic complexity ≤15, verified by `ruff` `C901` (`pyproject.toml` `max-complexity = 15`). | Maintainability | High | Open |
| NFR-003 | Zero new lint or type debt | `ruff` and `mypy --strict` report zero issues on every touched file, with zero new suppressions. | Maintainability | High | Open |
| NFR-004 | Changed-line coverage | Changed lines meet or exceed the repository's 90% diff-coverage threshold. | Quality | High | Open |
| NFR-005 | Verdict recording stays responsive | Recording one verdict including durable persistence completes within the existing 2-second budget (`tests/review/test_cycle.py`). **Countable clause, restated:** at most one `commit_artifact` invocation per verdict record. The original wording said "one durable-persistence invocation", which was measured unsatisfiable — every verdict costs two (one `commit_artifact` for the record, one `commit_status` for the event) and FR-001's authority split *requires* both. The clause must name one port method or it is red by definition. | Performance | Medium | Open |
| NFR-006 | The new serialization holds no lock across a subprocess | Any serialization **introduced by FR-005** must not hold an inter-process lock across a `git` subprocess invocation. This does not apply retroactively: `coordination/transaction.py` already holds `feature_status_lock` across `subprocess.run(['git', ...])` by design, so a repo-wide reading of this NFR would be red before the mission starts. That pre-existing hold is out of scope and is not to be 'fixed' opportunistically. | Reliability | High | Open |
| NFR-007 | The census is produced by a check, not asserted | An architectural check enumerating verdict writers, location resolvers, and frontmatter readers is authored **first** and produces the starting census. Reduction targets are set from its output; no numeral is pinned in advance. Each check must fail when a new member is introduced. | Maintainability | High | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | The guard relaxation stands, conditionally | The fail-closed rejected-verdict refusal is not reinstated — **once, for every accepted filename, the merge gate reaches a verdict for the work package that the writer wrote.** Rewritten at planning time: the original predicate ("the backstop resolves the same location the writer writes to") is **voided** rather than dischargeable once FR-001 makes the event authoritative, because the gate then resolves no location for the verdict at all — satisfiable by construction. The replacement is testable under both the current fan-out and the unified resolver, and stays meaningful after FR-001. C-001's own site is `tasks_transition_core.py`'s `_guard_rejected_verdict`. | Technical | High | Open |
| C-002 | Landed folds are a behaviour floor, not a code floor | Three folds may have their **mechanism** replaced without a decision record — `ca53e0bbd`'s `_content_identity`, `0ffdf8ab5`'s compensator, `95d8dbc6f`'s two-leg writer. What may **not** weaken, whatever mechanism carries it: (a) a verdict record re-submitted as feedback is refused, by path **and** by content — this is the #990 control and C-007 requires the PR to claim #990 closed; (b) a failed durable write leaves no orphan; (c) a self-generated approval body never collides with a prior record. The regression tests pinned at those three commits stay green throughout. The other eight folds are **not** revertible — a decision record does not license it. | Technical | High | Open |
| C-003 | Renames are out of scope | `meta.json` carries no `change_mode` key — the only valid value is `bulk_edit`, and an absent key is how a non-bulk mission is represented. No identifier rename lands in this mission; the naming debt in #3158 items 1–2 is deferred to a successor whose occurrence map is authored against post-rebuild code. | Process | High | Open |
| C-004 | Canonical sources | Consolidation targets the existing canonical surface. Where a module declares itself the single authority for a concern, that module is the target — unless an enforced layer boundary forbids it, in which case the conflict is recorded and the item deferred rather than worked around. | Technical | High | Open |
| C-005 | Two named pins stay red | `tests/regression/test_issue_2804_merge_resets_gate_artifacts.py` and `tests/regression/test_issue_3086_merge_delete_branch_flattens_coordination_metadata.py` are deliberate red-first signals and are not greened. **The red-first classification is available only for these two paths**; no other failure may be discharged by classification. | Process | High | Open |
| C-006 | Reviewable stack, not a monolith | The branch is already ~55 files ahead of `main`. Work lands as a reviewable sequence of PRs into the mission branch, which merges to `main` once — not as one unreviewable diff. | Process | High | Open |
| C-007 | Predecessor closing clauses are carried, and the epic claim is honest | The PR carries `Closes` clauses for #2275, #2996, #990, #2697, #2646, and the five predecessor reproductions are pinned as regression gates through the rebuild. **Epic #3044's children are #2275, #2996, #990 and #3088** — verified, not assumed. #3088 is out of this mission's scope and stays open, so the epic cannot close and the PR must not claim it does. An earlier revision named #3158 as the blocker; #3158 is not a child of #3044. | Process | High | Open |

### Key Entities

- **Authoritative verdict**: the `ReviewResult` carried on the status event — reviewer, verdict, and a pointer to the content. Authoritative for *which* verdict is current. Today it has no reader downstream of the reducer; FR-001 gives it one.
- **Verdict record**: the on-disk artifact. Authoritative for its own content — the reviewer's prose, affected files, reproduction command, cycle number, and override annotation. Addressed by the event's pointer, not derived from it.
- **Arbiter override**: a decision to proceed over a standing rejection with a mandatory reason. A first-class outcome alongside approval and rejection — not a variant of either.
- **Location resolution**: the single derivation from work-package identity to verdict-record directory, including slug derivation.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A reviewer can re-report a recurring defect using byte-identical feedback and have the rejection recorded, across the full filename × topology matrix. Currently refused — reproduced: `ReviewCycleError: feedback_source content duplicates a prior review-cycle artifact (review-cycle-1.md) verbatim`.
- **SC-002**: Under injected failure in **either** direction — transition-after-write and write-after-transition — zero work packages reach a state where a readable verdict disagrees with the completed outcome.
- **SC-003**: After an interruption including `SIGKILL`, the identical retry both exits zero **and** records the correct verdict, with zero manual cleanup steps.
- **SC-004**: Two concurrent distinct verdicts produce two records or one explicit refusal, over **at least 50 iterations at 2+ concurrent processes** (not threads — `feature_status_lock` is inter-process). Asserted to lose one record today; the probe is owed before the fix.
- **SC-005**: Zero arbiter overrides produce an approval record — in the artifact **or** in the authoritative verdict — and the override is distinguishable from an approval by a consumer reading only the event.
- **SC-012**: Zero readers in the NFR-007 census crash uncaught on a damaged verdict record, and zero safety-gate readers return a "no verdict" result for one.
- **SC-013**: Zero tests in the affected suites append a hard-coded event timestamp into an event log that also receives a `now()`-generated one, enforced by the FR-014 check.
- **SC-011**: Zero consumers answer "is this work package approved?" by parsing artifact frontmatter. The event's verdict is readable downstream of the reducer, and every gate consults it. Verified by the NFR-007 check, not by inspection.
- **SC-006**: For every accepted filename separator, every read, write, gate and display path resolves one identical directory — verified by the FR-007 check, not by inspection. Under a coordination topology that directory is on the COORD surface; under `SINGLE_BRANCH` / `LANES` it is PRIMARY. Zero consumers resolve a review-cycle path from a caller-supplied directory.
- **SC-007**: Zero tests contradicting their own assertions, within a **machine-derivable** denominator: every test in a file this mission's diff touches, plus every test in the affected suites whose name or `requirement_refs` references a guard, verdict, durability, override or provenance concept. Evidenced by an enumerated audit table. The full path list is **2820 tests** — an unbounded hand audit would be silently scoped down, so the denominator is stated as a rule a reviewer can re-derive.
- **SC-008**: The architectural checks required by NFR-007 exist and fail when a new writer, resolver, or frontmatter reader is introduced. Reduction is measured against the census those checks produce.
- **SC-009**: Every failure remaining in the affected suites reproduces at `8466727eb` and is listed by test node id against an open tracked issue.
- **SC-010**: A push to the mainline with one shard failing still produces coverage for every shard currently gated on another shard's result.

## Traceability

| User Story | Functional Requirements | Success Criteria |
|---|---|---|
| US1 — recorded verdict means the transition happened | FR-001, FR-002, FR-003, FR-004, FR-005, FR-006, FR-013, FR-015 | SC-001, SC-002, SC-003, SC-004, SC-011 |
| US2 — a waiver stays a waiver and clears the gate | FR-022, FR-009, FR-010, FR-011 | SC-005 |
| US3 — every component agrees where a verdict lives | FR-023, FR-007, FR-008 | SC-006 |
| US4 — verdict readers fail the same way | FR-012 | SC-012 |
| US5 — names and tests tell the truth | FR-017, FR-020, FR-021 | SC-007 |
| US6 — time-dependent tests cannot rot | FR-014 | SC-013 |
| US7 — the board is clean | FR-016, FR-018, FR-019 | SC-010 |

Non-functional requirements are not story-scoped; they are cross-cutting and are verified independently:

| Non-Functional Requirement | Success Criteria | Verified by |
|---|---|---|
| NFR-001 — regression baseline and method | SC-009 | diff against `research/baseline-8466727eb.md` |
| NFR-002 — complexity ceiling | — | `ruff --select C901` on the diff |
| NFR-003 — zero new lint or type debt | — | `ruff` + `mypy --strict` on touched files |
| NFR-004 — changed-line coverage | — | diff-coverage gate (blocked until FR-016 lands — see US7) |
| NFR-005 — verdict recording stays responsive | — | the existing 2-second budget assertion |
| NFR-006 — new serialization holds no lock across a subprocess | — | inspection of the FR-005 critical section only |
| NFR-007 — census produced by a check | SC-008 | the census check's own output |

## Assumptions

- The eleven folds are correct except where C-002 pre-authorizes change; two are known incomplete and their completion is in scope (FR-002, FR-012).
- The guard relaxation stands, conditionally — see C-001. Its premise is not yet verified.
- #2804 was reopened during this spec's review; NFR-001 and SC-009 depend on it staying open while its pin is red.
- `research/wave3-partial-atomicity.diff` and `research/wave3-partial-test.py.txt` are unverified predecessor provenance and carry **no authority**; they are evidence that a defect was observed, not that a fix is correct.
- `research/baseline-8466727eb.md` is different: it is a measured run and **is** authoritative for NFR-001's starting failure set.

## Dependencies

- **Predecessor**: PR #3156, closed unmerged. Its branch and eleven folds are this mission's base.
- **Folded in**: #3157 (test date-bomb + coverage-shard fan-out), #3158 items 3 and 4, #3159, #3160.
- **Deferred to a successor**: #3158 items 1–2 (renames, per C-003), items 5–6 (the fourth conftest fixture copy, and `review/cycle.py`'s CLI-port imports — neither has an FR here), and the repo-wide frontmatter consolidation. A correction on that last one: an earlier revision said two readers "sit below `specify_cli`" and an ADR-level amendment was required. That is false — **all five readers are inside `specify_cli`**; two *consumers* sit below it (`mission_runtime/resolution.py`, `runtime/next/discovery.py`), and only the first is ledgered in `test_layer_rules.py`. Consolidating means adding one row to a frozenset with a rationale, not an ADR. It is deferred on **breadth**, not on an architectural block. FR-012 addresses the in-domain polarity defect only, and crosses no boundary.
- **Inherited, must not silently lapse**: #2275, #2996, #990, #2697, #2646 — see C-007. Epic #3044 stays open on #3088, which this mission does not assess.
- **Tracked, out of scope**: #2809, #3115, #3140 (partially folded here), #2804 and #3086 (C-005).
