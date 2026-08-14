---
description: "Work package task list for the bare-prose-requirements-uncounted mission (#3396)"
---

# Work Packages: Bare-Prose Requirements Are Silently Uncounted by the Coverage Gate

**Inputs**: `kitty-specs/bare-prose-requirements-uncounted-01KZYV3C/spec.md` (DONE),
`kitty-specs/bare-prose-requirements-uncounted-01KZYV3C/plan.md` (DONE). No
`research.md`/`data-model.md`/`quickstart.md`/`contracts/` exist for this mission —
plan.md's own "Project Structure" section states none are needed (no new data model,
no new external contract).

**Tests**: Required throughout — this mission's binding governance (charter C-011 /
spec C-002, "ATDD-First") makes a failing-first test a hard prerequisite for every
behaviour-changing work package, not an optional stakeholder request.

**Organization**: Fine-grained subtasks (`Txxx`) roll up into work packages (`WPxx`).
Each work package is independently reviewable and, other than the two declared
chokepoints (WP05, WP08), independently deliverable.

**Branch / base — read before starting any WP**: this mission's `planning_base_branch`
for ATDD RED verification is **`ab15225ea`** (tip of
`origin/op/3394-requirement-citation-scope`), **not** `main` and **not** the
CLI-computed `pr/bare-prose-requirements-uncounted` value that
`spec-kitty plan --json` reports for this mission's topology (a known tooling gap —
see plan.md's "Baseline Capture" and `tracer-tooling-friction.md`). Every WP below that
adds new behaviour states this explicitly again in its own ATDD instructions so no
implementer has to go find it. Merge target for this mission's PR is
`op/3394-requirement-citation-scope` (plan.md's "PR Shape") — GitHub will auto-retarget
to `main` once #3395 merges; no manual rebase is needed for that specific transition.

**One PR for this mission** (charter default, plan.md's "PR Shape" — confirmed, not
relitigated here). See "PR Size Note" at the end of this file for an explicit flag on
review-sitting size, left for the orchestrator/operator to decide, not acted on here.

## Subtask Format: `[Txxx] [P?] Description`

- **[P]** indicates the subtask (or its parent WP) can proceed in parallel with another
  **[P]**-marked WP whose write-scope is verified disjoint — see "Parallelism &
  Chokepoints" below. A subtask without `[P]` inside a `[P]`-marked WP still runs
  sequentially within that WP's own commit order (ATDD-first ordering is never
  parallelized away).
- Subtasks are **reference rows**, not checkboxes: record completion with
  `spec-kitty agent tasks mark-status <Txxx> --status done`.

## Path Conventions

Single project (Python CLI + library): `src/specify_cli/`, `src/runtime/next/`, `tests/`.
No web/mobile/multi-package split — see plan.md's "Project Structure".

---

## Parallelism & Chokepoints (read before scheduling any WP)

**Genuinely parallel-eligible** (disjoint write-scope, no chokepoint touched):
**WP02 + WP03 + WP04** may run concurrently once WP01 (baseline) is captured.
**WP06 + WP07** may run concurrently once WP05 (the chokepoint below) has landed.
Verified disjoint file sets — see each WP's `Requirement Refs`/file list; no two
concurrently-eligible WPs write the same file.

**Declared chokepoints — sequential, NOT parallel-eligible, by mission-brief mandate,
independent of whether their write-scope happens to be file-disjoint from other WPs**:

- **WP05** touches the runtime-state schema (`runtime_bridge_cores.py`'s `status_facts`
  / fact-object shape — the new `BareProseRequirementFacts` dataclass and the
  `"bare_prose_requirement_failures"` status_facts key) and is this mission's own
  central engineering risk (the `3823f2b00` dead-path precedent). It runs alone: no
  other WP is scheduled concurrently with it, even though WP05's own file list
  (`runtime_bridge*.py`) does not literally overlap WP06/WP07's files. This is a
  conservative reading of the mission brief's "serializes the mission whether or not
  you want it parallel" instruction — treated as full-mission serialization at that
  point, not merely a pairwise same-file guard.
- **WP08** touches the corpus ratchet, a declared shared CI gate. Same rule: scheduled
  alone, after every other implementation WP (WP02, WP03, WP05, WP06) has landed, per
  plan.md's own IC-06 risk note ("sequence this concern last among the detector-adjacent
  work" — snapshotting before the detector is final bakes in a stale signature).

**#3395 overlap is expected, not a new problem (C-005).** This mission's base is PR
#3395's still-open, unreviewed branch (`op/3394-requirement-citation-scope` @
`ab15225ea`), not `main`. Several WPs below touch files #3395 itself changes:
`src/specify_cli/requirement_mapping.py` (WP03 — also #3395's own primary file — **and
WP07**, which appends to that same file's module docstring, T036), also
`src/specify_cli/cli/commands/agent/mission_finalize.py` (WP02, WP06 — also on #3395's
list), `src/specify_cli/cli/commands/agent/tasks_map_requirements.py` (WP06/T032a —
also on #3395's list: `git diff --stat
main...origin/op/3394-requirement-citation-scope --
src/specify_cli/cli/commands/agent/tasks_map_requirements.py` shows a 16-line #3395 diff
to that exact file), and `src/runtime/next/runtime_bridge.py` (WP05 — also on #3395's
list). This is the accepted rebase risk plan.md's "#3395 Churn Risk" section already
documents — a *sequential-base* relationship (this mission builds ON TOP of #3395's
tip), not a same-base collision between concurrent branches. It does not change this
mission's own internal parallel/sequential scheduling above. One nuance worth recording:
WP06 also touches `tasks_mapping_core.py` directly, a file #3395's stated touched-file
list does **not** literally name (#3395 names its CLI-facing sibling,
`tasks_map_requirements.py` — confirmed above to be directly touched by both #3395 and
WP06/T032a — which itself imports `plan_mapping` from `tasks_mapping_core.py` at line
52) — so `tasks_mapping_core.py` is one file removed from #3395's own named list via
that same call chain, even though `tasks_map_requirements.py` itself is not.

**A sharper collision: the byte-frozen `map_requirements_success` fixture case.**
WP06/T030a re-freezes
`tests/specify_cli/cli/commands/agent/fixtures/tasks_cli/json/byte_contracts.json`'s
`map_requirements_success` case (to add `bare_prose_requirement_ids`) after T032 lands
— and #3395's own diff already modifies that exact same `expected_stdout` string (to
add `"requirement_extraction_warnings": []`; confirmed via `git diff
main...origin/op/3394-requirement-citation-scope --
tests/specify_cli/cli/commands/agent/fixtures/tasks_cli/json/byte_contracts.json`).
Whoever executes T030a MUST preserve the `requirement_extraction_warnings` field when
re-freezing this case after rebasing onto #3395's tip — do not silently overwrite or
drop it while adding `bare_prose_requirement_ids`.

**The same overlap also extends to test files, with substantially higher content
churn than the additive source-file edits above** — confirmed via
`git diff --stat main...origin/op/3394-requirement-citation-scope`: #3395 touches
`tests/specify_cli/test_requirement_mapping.py` (+186 lines — also WP03's owned test
file), `tests/next/test_runtime_bridge_unit.py` (+216 lines) and
`tests/runtime/test_bridge_cores.py` (+39 lines — both also WP05's owned test files),
and `tests/specify_cli/cli/commands/agent/test_tasks_mapping_core.py` (+41 lines — also
one of WP06's located test files, T030). Each of these four is independently and
substantially modified by both #3395 and this mission's own WP03/WP05/WP06
respectively, which is a materially higher rebase-conflict risk than plan.md's "expected
... clean rebase" reasoning covers (that reasoning is explicitly scoped to the additive
*source*-file edits, not to parallel edits inside the same test file). No action is
required beyond awareness — the WPs' own ATDD-first test additions to these files are
still correct — but an implementer should expect real merge conflicts in these four
files specifically when rebasing onto #3395's eventual tip, not only in the three
source files named above.

---

## Work Package WP01: Baseline Capture & Pre-Existing Failure Audit (Priority: P0)

**Goal**: Establish the mission's actual RED/GREEN starting point before any code
changes, per plan.md's "Baseline Capture on `ab15225ea`" section — verbatim procedure,
not the CLI-computed (and here, wrong) `planning_base_branch`.
**Independent Test**: A recorded red-test-ID list from `ab15225ea`, diffed explicitly
against issue #3284's ~23-known-red-on-`main` set, with a stated match/mismatch
verdict; any newly-discovered pre-existing failure has an upstream GitHub issue filed
before this WP is considered done (charter's Pre-existing Failure Reporting Rule).
**Prompt**: `/tasks/WP01-baseline-capture.md`
**Requirement Refs**: C-003, C-005

### Included Subtasks

T001 Create an isolated worktree/clone at `ab15225ea` (tip of
`origin/op/3394-requirement-citation-scope`): `git worktree add /tmp/baseline-ab15225ea ab15225ea`
T002 `cd /tmp/baseline-ab15225ea && uv sync --all-extras`
T003 Run the exact Targeted Test Surface command from plan.md:
```bash
PWHEADLESS=1 .venv/bin/python -m pytest \
  tests/specify_cli/test_requirement_mapping.py \
  tests/specify_cli/test_requirement_mapping_coord_surface.py \
  tests/next/ tests/specify_cli/next/ tests/runtime/ \
  -n 8 --dist loadfile -q
```
NEVER `-n auto` — deadlocks this 24-core box (documented repo-wide trap).
T004 Record the red count and failing test IDs verbatim.
T005 Diff the recorded red set against issue #3284's ~23 known-red-on-`main` tests by
name; state explicitly, in the mission's implementation record (append to
`tracer-tooling-friction.md`), whether the `ab15225ea` red set matches #3284's `main`
set — plan.md explicitly does NOT assume they match, since `ab15225ea` carries #3395's
unreviewed ~863-line rewrite that `main` does not.
T006 For any red test not already covered by a filed, referenced upstream issue, open a
new GitHub issue per the charter's Pre-existing Failure Reporting Rule (command run,
failure summary, why believed pre-existing) **before** treating it as accepted baseline.
T007 Also verify, live at execution time (not from a stale count), that every commit
strictly between `ab15225ea` and the then-current tip is `spec(...)` /
`fix(spec: ...)` / `reviews(spec: ...)` / `plan(...)` / meta-add shaped — zero
implementation-shaped commits — per plan.md's PLAN-VERIFY-003 falsifiability note.

### Implementation Notes

- No production code changes in this WP. Output is a recorded finding (baseline red
  set + #3284 diff verdict + any newly-filed issue links), appended to
  `tracer-tooling-friction.md` and/or `tracer-approach.md` per Standing Order 3
  (mission tracer files — append during implementation, never recreate).
- This WP gates every other WP's ATDD RED verification: WP03/WP05/WP06 each re-run
  their own new failing-first test against this same `ab15225ea` tip to confirm RED,
  reusing the worktree this WP establishes (or a fresh one at the same ref).

### Parallel Opportunities

- None. This WP is the mission's first step and everything else in the mission depends
  on its recorded baseline for RED verification.

### Dependencies

- None (starting package).

### Risks & Mitigations

- Misattributing a genuinely new regression as "pre-existing baseline" → mitigated by
  the explicit #3284-diff requirement (T005) and the Pre-existing Failure Reporting
  Rule (T006), both binding, not advisory.

---

## Work Package WP02: Campsite-Clean — Decompose `_validate_requirement_mapping` (Priority: P0) `[P]`

**Goal**: Land the charter Standing Order 2 "campsite cleaning" FIRST commit,
behaviour-preserving, splitting the over-ceiling `_validate_requirement_mapping`
(`src/specify_cli/cli/commands/agent/mission_finalize.py:621-677`, verified cyclomatic
complexity **16** via `radon cc`, ceiling is 15) into a classification helper and a
report-formatting helper — **before** WP06's functional addition (the new
`bare_prose_requirement_ids` field) touches the same function.
**Independent Test**: `radon cc -s src/specify_cli/cli/commands/agent/mission_finalize.py -n A`
reports every extracted helper and the reduced orchestrator at complexity <=15; every
pre-existing test exercising `_validate_requirement_mapping` (see T030 in WP06 for the
located test files) passes unmodified, proving the split changed no observable output.
**Prompt**: `/tasks/WP02-campsite-clean-validate-requirement-mapping.md`
**Requirement Refs**: (behaviour-preserving prerequisite for WP06's FR-001 CLI wiring;
Standing Order 2 / PLAN-GOV-001 — no functional FR/NFR/C is delivered by this WP itself)

### Included Subtasks

T008 [P] Re-verify current complexity with `radon cc -s src/specify_cli/cli/commands/agent/mission_finalize.py -n A` — confirm `F 621:0 _validate_requirement_mapping - C (16)` before editing, so the post-split measurement has a stated before/after pair.
T009 Extract the per-WP classification loop into a pure helper, e.g.
`_classify_wp_requirement_refs(wp_ids, wp_requirement_refs, all_spec_requirement_ids) -> tuple[list[str], dict[str, list[str]], set[str]]`
(missing/unknown/mapped bucketing — the exact loop currently inline, lines ~633-643).
T010 Extract the JSON-vs-console report branch into a report-formatting helper, e.g.
`_emit_requirement_mapping_report(payload, *, json_output)` (the three `console.print`
loops + the `json.dumps` branch, lines ~653-677).
T011 Reduce `_validate_requirement_mapping` itself to a thin orchestrator: call the
classification helper, compute `unmapped_functional_requirements`, early-return if
clean, else call the report helper and `raise typer.Exit(1)` — same external behaviour,
same call signature, same exceptions raised for the same inputs.
T012 Re-run `radon cc` on both new helpers and the reduced orchestrator; confirm each
<=15. Run the located test file
(`tests/specify_cli/cli/commands/agent/test_mission_finalize_phases.py` — the only hit
for `git grep -l _validate_requirement_mapping tests/`; `test_finalize_provenance_guard.py`
is unrelated (#3311 provenance-preservation guard, zero references to
`_validate_requirement_mapping`) — re-run the grep live at implementation time rather
than trusting this note) unmodified and green.

### Implementation Notes

- **No new user-observable behaviour** — this is why the charter's ATDD-First "failing
  test before implementation" clause does not apply in its literal form here (there is
  no new behaviour to pin RED). The regression guard instead is: every existing test
  touching this function must stay green, unmodified, before and after the split (the
  "Independent Test" above states this precisely).
- This is a judgment call this tasks-authoring pass made explicitly, since the plan
  does not spell out ATDD applicability for a behaviour-preserving refactor — see the
  final report for this note restated.

### Parallel Opportunities

- Runs concurrently with WP03 and WP04 — disjoint files
  (`mission_finalize.py` vs. `requirement_mapping.py` vs. a brand-new architectural test
  file that only reads `runtime_bridge_cores.py`).

### Dependencies

- Depends on WP01 (baseline captured first).

### Risks & Mitigations

- Extraction accidentally changes JSON payload shape or console output ordering →
  mitigated by T012's unmodified-test-green requirement; do not touch the payload dict
  keys or the print-loop ordering during extraction.

---

## Work Package WP03: New Bare-Prose Predicate — `find_bare_prose_requirement_ids` (Priority: P0) `[P]`

**Goal**: Implement IC-01 — the new, per-token, per-line, document-scoped blocking
predicate in `src/specify_cli/requirement_mapping.py`, per plan.md's "Architecture"
section algorithm. This is the foundation every other WP wires into.
**Independent Test**: Story 1's exact repro (declared NFR-001 table row + bare-prose
FR-001/FR-002 under a "Functional Requirements" heading) returns
`{"Functional Requirements": ["FR-001", "FR-002"]}`-shaped candidates; Story 2 AC3's
description-column-in-a-declared-row case returns no candidates for that row's foreign
token; Story 5's fault-injection case surfaces an explicit failure, never `[]`.
**Prompt**: `/tasks/WP03-bare-prose-predicate.md`
**Requirement Refs**: FR-001, FR-004, FR-005, C-001, C-006, C-008, NFR-001, NFR-006

### Included Subtasks

T013 [P] **ATDD RED-first, separate commit before any implementation commit.** Write
failing test(s) in `tests/specify_cli/test_requirement_mapping.py` for
`find_bare_prose_requirement_ids` against Story 1's exact repro shape. Verify RED
**against `ab15225ea`** (the mission's real `planning_base_branch` for this purpose —
not `main`, not the CLI-reported value; see the file header above and
plan.md's "ATDD-First" section for why a `main`-relative RED is a category error here:
the declared-shape machinery this mission extends does not exist on `main` at all).
T014 Implement `find_bare_prose_requirement_ids(spec_content: str) -> BareProseResult`
(a `NamedTuple`/`TypedDict` of `{section_heading: str, ids: list[str]}` entries) per the
three-step algorithm: (1) `document_declared = _declared_ids(spec_content)` unmodified;
(2) for each `(heading_text, body)` in `_requirement_named_sections(spec_content)`
(heading-scoping reused byte-identical — C-008's decision (b), do NOT broaden
`_is_requirement_heading`); (3) per line in `body`, if the line matches one of the four
`_DECLARED_ID_PATTERNS`, skip raw-token scanning of the rest of that line entirely
(the Story 2 AC3 load-bearing rule); else scan for `_REF_FIND_PATTERN` tokens and record
any not in `document_declared`.
T015 Add the module docstring recording the measured rates: 9/368 = 2.45%
(document-scoped, C-006), 139/368 = 37.77% (rejected section-scoped alternative), zero
true positives, corpus size (368) and measurement date — mirroring
`_DECLARED_ID_PATTERNS`'s existing #3395 6%-figure docstring precedent
(`requirement_mapping.py` ~lines 43-53).
T016 Add the Story 2 AC3 regression test: a table row whose ID cell is properly
declared but whose description column cites a foreign/malformed id-shaped token does
NOT produce a candidate for that row.
T017 Add the Story 5 fault-injection test: force the classification logic into an
unresolvable state (monkeypatched exception mid-computation) and assert the
caller-visible result is an explicit surfaced failure, never a silently empty result —
this is the pure-function half of Story 5; the call-site wrapping (try/except →
blocking failure string) is IC-04, delivered per call site in WP05/WP06, not here.
T018 Add the Story 4/negative-space regression test confirming #3394's repro shape
(foreign id cited in prose outside a Requirements-named section, or not matching a
declared shape inside one) stays non-blocking.

### Implementation Notes

- Pure stdlib only (`re`, `pathlib.Path`, `typing`) — `requirement_mapping.py`'s own
  module contract, unchanged by this WP.
- Do NOT widen `_DECLARED_ID_PATTERNS` or `_is_requirement_heading` (C-001, C-008) —
  this predicate is additive, reusing both unmodified.
- A probe/test importing `requirement_mapping.py` standalone (outside the full CLI
  package) must use `importlib.util.spec_from_file_location`, not the package
  `__init__` (which needs `typer`) — a known environment trap for this module.

### Parallel Opportunities

- Runs concurrently with WP02 and WP04 — disjoint files.

### Dependencies

- Depends on WP01.

### Risks & Mitigations

- Getting the per-line skip rule wrong reopens #3394 (doc-wide fallback) or
  reintroduces the description-column false-positive class — mitigated by T016/T018's
  explicit negative-space pins, and later by WP08's frozen corpus ratchet.

---

## Work Package WP04: Architectural Import-Boundary Test for `runtime_bridge_cores.py` (Priority: P1) `[P]`

**Goal**: Implement IC-08 — pin `runtime_bridge_cores.py`'s "zero-dependency leaf"
invariant (its own module docstring claim, C-007) by construction, ahead of WP05's edit
to that same file, so a future (or this mission's own) regression that adds a
cross-package import is caught mechanically, not by convention.
**Independent Test**: `pytest tests/architectural/test_bridge_cores_import_boundary.py`
passes on the current, unmodified `runtime_bridge_cores.py`; a synthetic
`import specify_cli` (or any non-stdlib, non-`runtime.next.decision` import) inserted
into a scratch copy fails the same test.
**Prompt**: `/tasks/WP04-bridge-cores-import-boundary.md`
**Requirement Refs**: C-007

### Included Subtasks

T019 [P] Add `tests/architectural/test_bridge_cores_import_boundary.py`, following the
existing precedent shape (`tests/architectural/test_kernel_no_doctrine_import.py` et
al.): parse `src/runtime/next/runtime_bridge_cores.py`'s AST `Import`/`ImportFrom`
nodes and assert every non-stdlib import target is `runtime.next.decision` (confirmed
by direct read: the file's own top-of-file imports, lines 70-77, already only carry
stdlib + `runtime.next.decision`).

### Implementation Notes

- This is a new test file only — it does not modify `runtime_bridge_cores.py` itself.
  It is safe to land before, during, or after WP05 (which does edit that file); landing
  it first (as scheduled) means WP05's own new imports are checked by construction as
  they are added, not after the fact.
- **ATDD/C-011 applicability (mirrors WP02's and WP08's own disclosure)**: this WP ships
  a new architectural test with no accompanying production behaviour change, so charter
  C-011's literal failing-first-separate-commit form does not apply — there is no
  user-observable behaviour to pin RED against. The test's own negative-case
  verification (a synthetic bad import manually confirmed, once during development, to
  fail the test, then reverted — see Test Strategy) is the substitute regression
  evidence.

### Parallel Opportunities

- Runs concurrently with WP02 and WP03 — disjoint files; this WP's only touched file
  (`tests/architectural/test_bridge_cores_import_boundary.py`) is new and read-only
  against the file it inspects.

### Dependencies

- None beyond WP01 (baseline). Plan.md notes this concern "can land any time."

### Risks & Mitigations

- Low; a mechanical AST-walk test with an existing repo-wide precedent pattern to copy.

---

## Work Package WP05: `spec-kitty next` Guard Wiring + Per-Guard Non-Vacuity Teeth Tests (Priority: P0) — CHOKEPOINT, sequential

**Goal**: Implement IC-02 + IC-05 — the mission's central, named engineering risk.
Thread the new bare-prose signal through a sibling fact object
(`BareProseRequirementFacts`) into all four guard functions FR-010 names, read
**before** each guard's `_tasks_dir_ready` short-circuit (the exact ordering fix that
makes this succeed where the reverted `_zero_declared_requirement_block` (`3823f2b00`)
failed), plus one synthetic-reversion ("teeth") test per guard proving each is
individually load-bearing.
**Independent Test**: Story 3's Independent Test — a regression test exercises
`spec-kitty next`'s tasks-boundary decision directly (not only the pure
`evaluate_guards` core) in both configurations (zero WP files; ≥1 WP file, none
referencing the bare-prose ids) and asserts the decision does not advance in either
case, naming FR-001/FR-002 specifically. Each of the (up to) four teeth tests, run
individually, fails when only that guard's wiring is reverted.
**Prompt**: `/tasks/WP05-spec-kitty-next-guard-wiring.md`
**Requirement Refs**: FR-002, FR-003, FR-004, FR-007, FR-008, FR-010, NFR-002, NFR-005,
NFR-006, C-002, C-007, C-009

### Included Subtasks

T020 **ATDD RED-first, separate commit before any implementation commit.** Write
failing tests for each of the four guards
(`_evaluate_tasks_packages_guard`, `_evaluate_tasks_finalize_guard`,
`_evaluate_composed_tasks_packages_guard`, `_evaluate_composed_tasks_terminal_guard`,
all in `src/runtime/next/runtime_bridge_cores.py`) reading the new signal before their
`_tasks_dir_ready` short-circuit, plus the zero-WP-files / ≥1-WP-file-no-match
integration cases (Story 3). Verify RED **against `ab15225ea`** — same baseline caveat
as WP03/T013; this mechanism does not exist on `main` at all.
T021 Add the sibling `BareProseRequirementFacts` frozen dataclass to
`runtime_bridge_cores.py` (`flagged: Mapping[str, tuple[str, ...]]`,
`classification_error: str | None`) beside `RequirementMappingFacts` (line 241) — NOT
an extension of that dataclass (C-007: it is WP-shaped and early-returns on absent
`tasks_dir`, exactly the coupling FR-002 requires avoiding).
T022 Add the pure `_evaluate_bare_prose_requirements(facts: BareProseRequirementFacts) -> list[str]`
beside `_evaluate_requirement_mapping` (line 253), following the same fact-port/pure-core
split.
T023 Add the residual gather step in `src/runtime/next/runtime_bridge.py` — e.g.
`_check_bare_prose_requirements_ready(feature_dir) -> list[str]`, reading `spec.md`
only, no `tasks_dir` dependency — and wrap it fail-loud (IC-04 for this call site):
catch any exception **once**, convert to an explicit non-empty failure string (mirroring
`_check_requirement_mapping_ready`'s own `except Exception as exc: return [...]` pattern
at line 919), never re-raised as a bare traceback, never downgraded to a log line. Do
**not** route this through `_log_requirement_extraction_warnings_safely` (line 835) —
that wrapper's "never crash into a gate" contract is the opposite of this new
detector's "never silently report clean" contract (Story 5 AC3); keep them textually
separate, no shared wrapper function.
T024 Add the new `"bare_prose_requirement_failures"` key to
`runtime_bridge_io.py::gather_artifact_presence` (populated the same way
`"requirement_mapping_failures"` already is, line 845) — plain-data tuple, never a new
import inside `runtime_bridge_cores.py` (C-007).
T025 Wire the fact into all four guards via `snapshot.status_facts.get("bare_prose_requirement_failures", ())`
— **`.get()` with a default, never a bare subscript** (PLAN-ARCH-001: `_snapshot()`'s
`base_status_facts` in `tests/runtime/test_bridge_cores.py` does not yet populate this
key; a bare subscript would `KeyError` in every existing caller the instant this lands).
Read it **unconditionally, before** each guard's own `_tasks_dir_ready` check — the
load-bearing ordering fix (see plan.md's code sketch under "FR-002's ordering
constraint"). `requirement_mapping_failures` itself stays a bare subscript, unchanged.
T026 Add one per-guard synthetic-reversion ("teeth") test per guard actually wired
(FR-010/NFR-005) — up to four tests, one per guard, each independently reverting only
that guard's `.get("bare_prose_requirement_failures", ())` read and asserting that
specific guard's test then fails. A single existence-proof test anywhere in the suite
does **not** satisfy this for the other guards (spec text, verbatim).
T027 Update `tests/runtime/test_bridge_cores.py`'s `_snapshot()` helper's
`base_status_facts` dict to also set `"bare_prose_requirement_failures"` by default —
fixture-accuracy hygiene, not a blocking prerequisite of T025's `.get()`-based read.
T028 Confirm SC-002 / Story 2 AC2: the full pre-existing #3394/#3395 assertions in
`tests/next/test_runtime_bridge_unit.py` and `tests/runtime/test_bridge_cores.py` —
including exact-equality assertions like
`test_cli_native_tasks_packages_extends_requirement_mapping_failures` and
`test_cli_native_tasks_finalize_missing_dependency_uses_full_stem_breaks_on_first` —
still pass, unmodified in their pinned assertions.

### Implementation Notes

- **Scope decision, already made by plan.md, implemented literally here**: wire all
  four guards, not only the three FR-003's audit proved live for the built-in
  `software-dev` mission type (see plan.md's "Story 3 / FR-002 / FR-003" section for the
  full justification: the CLI-native pair is non-primary, not proven dead; NFR-002
  argues for closing `_evaluate_tasks_finalize_guard`'s pre-existing asymmetry; FR-010
  already requires a teeth test per guard, so the marginal cost of the fourth is one
  more test).
- C-009 (composed-guard vocabulary scope): no `mission_step_contracts/` schema change
  and no orchestrator-api documentation update are needed — the new failure flows
  through the existing `Decision(kind=blocked, ...)` guard-failure-list shape every
  other guard failure already uses (plan.md's "Composed-Guard Vocabulary Scope (C-009)"
  section, already resolved; this WP implements that resolution, does not re-litigate
  it).
- NFR-006 caveat, stated honestly (not silently absorbed): the new gather step is one
  additional `Path.read_text()` per guard evaluation at the tasks boundary (it must not
  be gated behind `tasks_dir.is_dir()`) — an additional call within the same I/O class
  already in use, not a new I/O class (no network, no directory walk, no subprocess).

### Parallel Opportunities

- **None.** This WP is a declared chokepoint (runtime-state schema / shared fact-object
  shape) — see "Parallelism & Chokepoints" above. It runs alone.

### Dependencies

- Depends on WP01 (baseline) and WP03 (needs `find_bare_prose_requirement_ids` to call
  from the new gather step).

### Risks & Mitigations

- Repeating the `3823f2b00`-shaped dead path (a signal added but never actually
  reachable because a short-circuit runs first) — mitigated by T025's explicit
  before-the-short-circuit ordering and T026's per-guard teeth tests, which fail loudly
  if any single guard's wiring is dead.
- `KeyError` regressions in every pre-existing `evaluate_guards` fixture/test — mitigated
  by T025's `.get(..., ())` read (never a bare subscript) plus T027's fixture-accuracy
  follow-up.

---

## Work Package WP06: `finalize-tasks` / `map-requirements` CLI Wiring (Priority: P0)

**Goal**: Implement IC-03 — wire the same predicate into
`mission_finalize.py::_validate_requirement_mapping` (post-WP02-split orchestrator) and
`tasks_mapping_core.py::plan_mapping`, surfacing `bare_prose_requirement_ids` as a
distinct payload field on both, plus each call site's own fail-loud wrapper (IC-04).
**Independent Test**: Story 1 AC1/AC2 — the issue's exact repro spec.md drives both
`finalize-tasks` and `map-requirements`; both fail (non-zero exit / blocking JSON
result / non-clean coverage report) naming FR-001 and FR-002 explicitly, not merely
appending to `requirement_extraction_warnings`.
**Prompt**: `/tasks/WP06-finalize-tasks-map-requirements-wiring.md`
**Requirement Refs**: FR-001 (Story 1 AC1/AC2), FR-004, FR-007, FR-008, C-002

### Included Subtasks

T029 **ATDD RED-first, separate commit before any implementation commit.** Write
failing tests for `finalize-tasks` and `map-requirements` against Story 1's exact
repro spec.md fixture. Verify RED **against `ab15225ea`** (same baseline caveat as
WP03/T013 and WP05/T020).
T030 Locate the existing CLI-command-level test files before adding new ones (canonical
sources rule) — confirmed via `git grep -l _validate_requirement_mapping tests/` /
`git grep -l plan_mapping tests/`:
`tests/specify_cli/cli/commands/agent/test_mission_finalize_phases.py` (the ONLY hit for
`_validate_requirement_mapping` — **not** `test_finalize_provenance_guard.py`, which is
an unrelated #3311 provenance-preservation guard test with zero references to
`_validate_requirement_mapping`; re-run the grep live at implementation time rather than
trusting this list),
`tests/specify_cli/cli/commands/agent/test_tasks_mapping_core.py`,
`tests/specify_cli/cli/commands/agent/test_tasks_map_requirements_seam.py`,
`tests/specify_cli/cli/commands/agent/test_tasks_cli_contract_coord.py`,
`tests/specify_cli/cli/commands/agent/test_tasks_core_backed_orchestration.py`. Add new
cases to whichever of these already covers the relevant command; do not create a
parallel test file. Also in this WP's write/verification scope (byte-frozen JSON
contract, see T030a):
`tests/specify_cli/cli/commands/agent/fixtures/tasks_cli/json/byte_contracts.json` and
`tests/specify_cli/cli/commands/agent/test_tasks_json_bytes.py`.
T030a Adding `bare_prose_requirement_ids` to `MappingPlan` (T032) changes the JSON shape
of the `map_requirements_success` case pinned byte-for-byte in
`tests/specify_cli/cli/commands/agent/fixtures/tasks_cli/json/byte_contracts.json`,
asserted by `tests/specify_cli/cli/commands/agent/test_tasks_json_bytes.py`. After T032
lands, run `test_tasks_json_bytes.py`, observe the expected `map_requirements_success`
byte mismatch, and deliberately re-freeze the fixture for that one case only — do not
touch any other pinned case in the same file.
T031 **Plumbing prerequisite — `spec_content` is NOT currently in scope, correcting an
earlier drafting error in this section.** Neither `_validate_requirement_mapping`
(`mission_finalize.py`, `def _validate_requirement_mapping(...)`) nor its sole call site
has a `spec_content` parameter/argument today; `_read_spec_requirement_ids`
(`mission_finalize.py`) parses `spec_content` locally but returns only
`(all_ids, functional_ids, warnings)` — never the raw text — so no `spec_content`
variable is ever bound in the caller's scope. Before wiring the predicate, do ONE of:
(a) change `_read_spec_requirement_ids`'s return type to also yield the raw
`spec_content` and thread it through the call chain into a new
`_validate_requirement_mapping` parameter, or (b) have the caller re-read spec.md once,
mirroring the pattern used at `_check_bare_prose_requirements_ready` (WP05). Then wire
`find_bare_prose_requirement_ids` into `_validate_requirement_mapping`'s post-WP02-split
orchestrator using the now-available `spec_content`: compute the bare-prose candidates
once, and if non-empty, fail exactly like the existing missing/unknown/unmapped path
already does — add `bare_prose_requirement_ids` as an **additional**, separately-labeled
field on the JSON/console payload (not merged into `unmapped_functional_requirements` —
"declared but not yet mapped" and "never declared at all" are different remediation
stories for an operator). Wrap the detector call fail-loud (IC-04): same pattern as
WP05/T023, textually separate from any swallow-and-log wrapper. (WP02's "same call
signature, no behaviour change" constraint applies only to the pre-existing parameters —
this WP is explicitly the one allowed to add the new one.)
T032a **Plumbing prerequisite for the `plan_mapping` call site — same unscoped gap as
T031, structurally more consequential.** `MappingRequest` (`tasks_mapping_core.py`,
`class MappingRequest`) carries no `spec_content`/bare-prose field, and `plan_mapping`
(`tasks_mapping_core.py`, `def plan_mapping(req: MappingRequest) -> MappingPlan`) is
documented pure/no-I/O (INV-4) — raw spec text must never be passed into it. Extend
`MappingRequest` with a new `bare_prose_requirement_ids: frozenset[str]` field.
**Correcting an earlier drafting error in this subtask**: `spec_content` is NOT read
"earlier in the same function" as the `MappingRequest(...)` construction — it is read
as a local variable inside `_mr_resolve_read_dirs` (`tasks_map_requirements.py`,
Phase C, around line 306), a *different* function from `_mr_plan` (Phase D, line 328)
where `MappingRequest(...)` is actually constructed. Confirmed by direct read: the
shared `_MapReqState` object the two phases thread through today stores only
`spec_content`'s *derived products* (`all_spec_ids`, `functional_ids`,
`requirement_extraction_warnings`) — it does not currently carry the raw `spec_content`
string itself, so `_mr_plan` has no existing access to it. Before calling
`find_bare_prose_requirement_ids(spec_content)` at the `MappingRequest(...)`
construction site, add a new field to `_MapReqState` (e.g. `spec_content: str = ""`),
set it in `_mr_resolve_read_dirs` (Phase C) alongside the existing derived fields, and
read it back in `_mr_plan` (Phase D) — mirroring T031's own plumbing fix for
`mission_finalize.py`. Wrap that call fail-loud (IC-04) at the shell call site, same
pattern as T031/WP05-T023 — the wrapper lives in the shell, not inside `plan_mapping`.
T032 Wire the same predicate's result into `plan_mapping`/`compute_coverage`
(`tasks_mapping_core.py`): read `req.bare_prose_requirement_ids` (populated by T032a) and
add it under the same field name, `bare_prose_requirement_ids`, to the returned
`MappingPlan`. `plan_mapping` itself never calls the detector or touches raw text —
it only consumes the already-computed ids T032a supplies, preserving its pure/no-I/O
contract.
T033 Add Story 1 AC1/AC2 acceptance tests confirming both commands surface FR-001/FR-002
as a blocking result on the exact repro fixture, and confirm Story 4/negative-space
(#3394's repro shape) stays green on both commands.

### Implementation Notes

- `mission_finalize.py` and `tasks_mapping_core.py` are **separate call sites** from the
  `runtime_bridge_cores` pure core (WP05) — they duplicate its missing/unknown/unmapped
  logic rather than sharing it, so this WP's wiring is independent of WP05's, not a
  re-use of it. Both already compute coverage purely from
  `functional_spec_requirement_ids` (the declared set), so a bare-prose FR is invisible
  to them by construction today, exactly like the runtime core.

### Parallel Opportunities

- Runs concurrently with WP07 once WP05 has landed (WP05 is the chokepoint gating
  this WP's start, per "Parallelism & Chokepoints" above — WP06 does not itself touch
  any chokepoint, but is sequenced after WP05 completes as a conservative reading of
  the mission-serializing chokepoint rule).

### Dependencies

- Depends on WP02 (the campsite-clean split must land in `mission_finalize.py` first,
  so this WP's new branch lands against the already-decomposed helper shape, never
  adding a branch to the pre-split 16-complexity function) and WP03 (needs the
  predicate). Sequenced after WP05 per the chokepoint-serialization note above.

### Risks & Mitigations

- Payload-shape drift between the two CLI commands' JSON output — mitigated by using
  the identical field name (`bare_prose_requirement_ids`) in both, per plan.md's
  explicit instruction.

---

## Work Package WP07: False-Negative Sample + Broadened-Predicate Re-Verification (Priority: P2, informational) `[P]`

**Goal**: Implement IC-07 — a throwaway measurement (not shipped production code)
recording the false-negative side of the C-008 disposition (real bare-prose
`C-XXX`/`FR`/`NFR` items the current detector misses, specifically the
`C-XXX`-under-`### Constraints`-heading case), plus a re-verification of the
broadened-predicate false-positive figure plan.md already measured once
(PLAN-GOV-002: 5/368 = 1.36%, zero true positives).
**Independent Test**: Both figures — the false-negative sample count and the
re-verified broadened-predicate FP rate — are recorded in
`requirement_mapping.py`'s module docstring alongside the shipped 9/368 figure (WP03's
T015), following FR-005's own re-verification precedent.
**Prompt**: `/tasks/WP07-false-negative-sample.md`
**Requirement Refs**: FR-005, C-008 (disclosure half only — the scope decision itself is
already made in plan.md as option (b); this WP does not reopen it)

### Included Subtasks

T034 [P] Write a corpus-scan helper (script or test under `tests/` or `scripts/`,
implementation's choice) that samples `kitty-specs/*/spec.md` for genuine bare-prose
`FR-`/`NFR-`/`C-XXX` items under a `### Constraints` heading (the heading
`_is_requirement_heading` structurally cannot see) and records how many sampled specs
contain one.
T035 Re-run the broadened-predicate false-positive scan (heading match also including
"constraint") against the then-current corpus, re-verifying plan.md's PLAN-GOV-002
figure (5/368 = 1.36% newly flagged, zero true positives on manual review) rather than
reusing the plan-time number unverified.
T036 Record both figures in `requirement_mapping.py`'s module docstring, alongside the
FP rate WP03/T015 already recorded, so both figures live in one place.

### Implementation Notes

- **Explicitly informational, not a shipping gate** (Story 4 AC4). This WP does **not**
  modify `_is_requirement_heading` or any production blocking-scope decision — C-008's
  disposition (b), already settled in plan.md, forecloses that reading. Do not mistake
  this measurement for a mandate to broaden production scope.

### Parallel Opportunities

- Runs concurrently with WP06, once WP05 has landed (same chokepoint-sequencing note as
  WP06). Disjoint from WP06's files (WP07 only appends to `requirement_mapping.py`'s
  docstring, does not touch its logic; WP06 touches `mission_finalize.py` and
  `tasks_mapping_core.py`).

### Dependencies

- Depends on WP03 (needs the finalized detector/heading logic to sample against).

### Risks & Mitigations

- None functional; the only risk is scope creep (an implementer reading this as license
  to broaden `_is_requirement_heading`) — explicitly foreclosed above and in plan.md.

---

## Work Package WP08: Frozen Corpus Fixture + Non-Vacuous Ratchet (Priority: P0) — CHOKEPOINT, sequential, last

**Goal**: Implement IC-06 — commit the 9-spec baseline signature and the shrink-only,
**non-vacuous** ratchet test (charter Standing Order 5: concrete floor + self-mutation
test + shrink-only allowlist — a gate-unmask cannot self-validate).
**Independent Test**: The four assertions plan.md's "The False-Positive Fixture"
section specifies, all in the same test module: (1) no spec outside the fixture is
newly flagged; (2) every fixture spec's live `flagged_ids` is a subset of (or equal to)
its recorded set; (3) every fixture spec's live result is **non-empty** (the concrete
floor); (4) a self-mutation ("teeth") test that stubs the detector to always return
`[]` and asserts the ratchet test then **fails**, not skips.
**Prompt**: `/tasks/WP08-corpus-fixture-ratchet.md`
**Requirement Refs**: FR-005, NFR-004 (SC-006 is the success-criterion label for this
WP's deliverable)

**ATDD/C-011 applicability (mirrors WP02's own disclosure)**: this WP is test-only — it
ships a new CI gate, not a production implementation. Charter C-011's literal
"failing-first ATDD test as a separate commit before implementation" form does not apply
in its usual shape here, because there is no separate production code change to pin RED
against. T040's self-mutation ("teeth") test is this WP's load-bearing substitute: it
must be run once and observed **failing** (stubbed detector → ratchet test fails) before
the WP is marked done, giving the same red-then-green evidence C-011 asks for, applied
to the gate itself rather than to a production behaviour change.

### Included Subtasks

T037 Snapshot the 9 fixture specs' per-spec detector signatures into
`tests/fixtures/bare_prose_corpus_baseline.json` (`{"spec_path": ..., "flagged_ids": [...]}`
entries) — re-verified against the then-current corpus at this WP's execution time (the
Independent Test's own requirement), not copy-pasted from spec.md's plan-time figure
unverified.
T038 Add `tests/architectural/test_bare_prose_corpus_ratchet.py`: assertion (1) every
spec **not** in the fixture has an empty live result; assertion (2) every spec **in**
the fixture has a live result that is a subset of (or equal to) its recorded set —
never a superset (shrink/stay-equal only), mirroring `_baselines.yaml`'s per-PR edit
policy (growth requires a deliberate re-snapshot with a recorded reason).
T039 Add assertion (3) in the same module: for each of the 9 fixture specs, the live
result is **non-empty** (`assert live_ids`, not only the subset check) — the concrete
floor that (1)+(2) alone do not provide.
T040 Add assertion (4) / the self-mutation teeth test (same module or a sibling
`test_bare_prose_corpus_ratchet_teeth.py`): monkeypatch/stub
`find_bare_prose_requirement_ids` to always return `[]`, assert the ratchet test then
fails (not errors, not skips) — proving the gate itself is load-bearing.

### Implementation Notes

- This is deliberately **not** a live-scored percentage re-run at CI time — it never
  recomputes "9/368"; it only asks whether the flagged *set* grew and is still
  non-empty where it should be. A future, unrelated mission adding a new
  `kitty-specs/*/spec.md` cannot flip this gate red merely by existing.
- Sequenced last among detector-adjacent work (this WP's own stated risk in plan.md):
  snapshotting before WP05/WP06 land the final shipped shape bakes in a stale
  signature.

### Parallel Opportunities

- **None.** This WP is a declared chokepoint (the corpus ratchet is a shared CI gate)
  — see "Parallelism & Chokepoints" above. It runs alone, after every other
  implementation WP.

### Dependencies

- Depends on WP03 (needs the live detector), and — because it must snapshot the final
  shipped behaviour, not an intermediate state — is sequenced after WP05 and WP06 have
  both landed.

### Risks & Mitigations

- A vacuous, always-passing gate (a collapsed detector trivially satisfies
  shrink-only-subset checks) — this is exactly why assertions (3) and (4) exist;
  without them this WP would not satisfy Standing Order 5's non-vacuity requirement.

---

## Work Package WP09: Reflexivity — In-Flight Mission Census & PR Description (Priority: P2) — sequential, last

**Goal**: Implement Story 6 / FR-009 — state plainly what happens to every other
mission currently in flight when this change lands, including a confirmation that this
mission's own spec.md does not block.
**Independent Test**: The implementing PR's description names any currently in-flight
mission (at merge time) whose spec.md would newly block under the shipped detector, and
states the operator-facing remediation (rewrite into a declared shape — no code-level
grandfathering, per the spec's own stated policy).
**Prompt**: `/tasks/WP09-reflexivity-pr-description.md`
**Requirement Refs**: FR-009

### Included Subtasks

T041 Run the finished, fully-wired detector (`find_bare_prose_requirement_ids`) against
every `kitty-specs/*/spec.md` belonging to a mission not yet merged at the time this WP
executes (the in-flight set changes daily — plan.md explicitly defers this census to
implementation time, close to merge, rather than plan time).
T042 Confirm this mission's own spec.md does not block (Story 6 AC2) — plan.md already
verified this by construction at plan time; re-confirm live against the shipped
detector, not the plan-time claim alone.
T043 Draft the PR description content naming any newly-blocking in-flight missions and
the operator remediation path (rewrite bare-prose requirements into a declared shape).
T044 Run the full Targeted Test Surface one final time (not the full `pytest tests/`)
plus `ruff check` and `mypy --strict` on every file this mission touched, confirming
zero new issues/suppressions (NFR-003) before the PR is marked ready.

### Implementation Notes

- This WP is the mission's own close-out step — it depends on every implementation WP
  above having landed, since it audits the *shipped* detector's real-world blast radius,
  not a plan-time projection.

### Parallel Opportunities

- None — this is the mission's last step by design (the in-flight census must reflect
  the state at/near merge time).

### Dependencies

- Depends on WP02, WP03, WP05, WP06, WP08 (all implementation WPs) having landed.
  WP07 (informational) does not gate this WP.

### Risks & Mitigations

- A stale census (run too early, missing a mission that entered the in-flight set
  later) — mitigated by sequencing this WP last, as close to actual merge time as the
  mission's own execution allows.

---

## Dependency & Execution Summary

```
WP01 (baseline, sequential, first)
  └─▶ WP02 [P] ─┐
  └─▶ WP03 [P] ─┼─▶ WP05 (CHOKEPOINT, sequential, alone) ─┬─▶ WP06 ─┐
  └─▶ WP04 [P] ─┘                                          ├─▶ WP07 ─┼─▶ WP08 (CHOKEPOINT, sequential, alone, last-among-detector-work)
                                                             (WP06 ∥ WP07,                 └─▶ WP09 (sequential, last)
                                                              both after WP05)
```

- **Sequence**: WP01 → {WP02, WP03, WP04 in parallel} → WP05 (alone) →
  {WP06, WP07 in parallel} → WP08 (alone) → WP09 (alone, last).
- **Parallelization**: WP02+WP03+WP04 (Phase 1); WP06+WP07 (Phase 3). No other pairing
  is parallel-eligible — WP05 and WP08 are declared chokepoints that serialize the
  mission at those points (see "Parallelism & Chokepoints" above for the explicit
  rationale, including the judgment call on how literally to read "serializes the
  mission").
- **No MVP subset call-out**: unlike a typical incremental-delivery mission, this
  mission has no partial-ship option — Story 1 (the mission's whole reason to exist)
  is not achieved until WP05 and WP06 both land, and Story 4/SC-006's non-vacuous gate
  (WP08) is a binding completion requirement (charter Standing Order 5), not optional
  polish. All nine WPs ship together in the one PR.

---

## Requirements Coverage Summary

| Requirement ID | Covered By Work Package(s) |
|----------------|----------------------------|
| FR-001 | WP03, WP06 |
| FR-002 | WP05 |
| FR-003 | WP05 |
| FR-004 | WP03, WP05, WP06 |
| FR-005 | WP03, WP07, WP08 |
| FR-007 | WP05, WP06 |
| FR-008 | WP05, WP06 |
| FR-009 | WP09 |
| FR-010 | WP05 |
| NFR-001 | WP03 |
| NFR-002 | WP05, WP06 |
| NFR-003 | WP09 (close-out check), cross-cutting per-WP (every WP's own `Independent Test`/Implementation Notes implicitly require zero new ruff/mypy issues on its own touched files) |
| NFR-004 | WP02, WP03, WP04, WP05, WP06, WP08 (every WP adding new branches/helpers includes its own focused tests) |
| NFR-005 | WP05 |
| NFR-006 | WP03, WP05 |
| C-001 | WP03 |
| C-002 | WP03, WP05, WP06 (each states the `ab15225ea` RED baseline explicitly) |
| C-003 | WP01 |
| C-004 | cross-cutting — "Mission," never "Feature," in all new identifiers/messages across every WP; no dedicated WP, verified at WP09's close-out pass |
| C-005 | WP01 (baseline capture is where the #3395-churn risk first becomes concrete); mission-wide operating posture, see "Parallelism & Chokepoints" above |
| C-006 | WP03 |
| C-007 | WP04, WP05 |
| C-008 | WP03 (implements disposition (b)), WP07 (disclosure/false-negative side) |
| C-009 | WP05 (implements the already-resolved scope statement; no new WP needed since no schema change is required) |
| SC-006 | WP08 |

---

## Subtask Index (Reference)

| Subtask ID | Summary | Work Package | Priority | Parallel? |
|------------|---------|--------------|----------|-----------|
| T001–T007 | Baseline capture on `ab15225ea`, #3284 diff, pre-existing-failure filing | WP01 | P0 | No |
| T008–T012 | Campsite-clean split of `_validate_requirement_mapping` | WP02 | P0 | Yes (WP-level) |
| T013–T018 | New `find_bare_prose_requirement_ids` predicate, ATDD-first | WP03 | P0 | Yes (WP-level) |
| T019 | Architectural import-boundary test for `runtime_bridge_cores.py` | WP04 | P1 | Yes (WP-level) |
| T020–T028 | `spec-kitty next` guard wiring + per-guard teeth tests, ATDD-first | WP05 | P0 | No (chokepoint) |
| T029, T030, T030a, T031, T032a, T032, T033 | `finalize-tasks`/`map-requirements` CLI wiring, ATDD-first | WP06 | P0 | Yes (WP-level, with WP07) |
| T034–T036 | False-negative sample + broadened-predicate re-verification | WP07 | P2 | Yes (WP-level, with WP06) |
| T037–T040 | Frozen corpus fixture + non-vacuous ratchet | WP08 | P0 | No (chokepoint) |
| T041–T044 | Reflexivity census + PR description + final close-out | WP09 | P2 | No |

---

## PR Size Note (flag only — decision left to orchestrator/operator)

Nine work packages, four commits' worth of ATDD-first pairs (WP03, WP05, WP06, plus
WP02's behaviour-preserving pair), a chokepoint touching four separate guard functions,
and a non-vacuous corpus-ratchet gate is a substantial single-sitting review even though
every individual WP is scoped to be independently reviewable. If the aggregate diff
proves too large for one review sitting once implemented, a plausible per-WP-group
split for review purposes only (not a PR split — plan.md's "PR Shape" is binding: one
PR) would be: {WP01+WP02+WP03+WP04} as one review pass (foundation), {WP05} as its own
pass (the named central risk), {WP06+WP07+WP08+WP09} as a third pass (consumers +
closeout). This is offered as a reviewer-sequencing suggestion only; the orchestrator/
operator decides whether to act on it — this tasks-authoring pass does not split the PR
itself.
