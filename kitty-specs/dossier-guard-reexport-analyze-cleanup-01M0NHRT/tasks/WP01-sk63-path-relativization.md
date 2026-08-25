---
work_package_id: WP01
title: SK-63 path-relativization — record-analysis input-artifact paths (FR-007)
dependencies: []
requirement_refs:
- FR-007
- NFR-001
- NFR-002
- C-001
- C-003
planning_base_branch: fix/dossier-guard-reexport-analyze-cleanup-3676
merge_target_branch: fix/dossier-guard-reexport-analyze-cleanup-3676
branch_strategy: Planning artifacts for this mission were generated on fix/dossier-guard-reexport-analyze-cleanup-3676. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/dossier-guard-reexport-analyze-cleanup-3676 unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-dossier-guard-reexport-analyze-cleanup-01M0NHRT
base_commit: a513bcf27bc2678ab280e3462dbd9e8d14760b06
created_at: '2026-08-23T00:15:15.726453+00:00'
subtasks:
- T001
- T002
- T003
- T004
- T005
history: []
agent_profile: python-pedro
authoritative_surface: src/specify_cli/analysis_report.py
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/analysis_report.py
- tests/specify_cli/test_analysis_report.py
- tests/specify_cli/test_analysis_report_charter_yaml_staleness.py
role: implementer
tags: []
tracker_refs: []
---

# WP01: SK-63 path-relativization — record-analysis input-artifact paths (FR-007)

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this work package's `task_type` and `authoritative_surface`.

---

## Objective

Fix ledger entry SK-63's path-relativization defect (FR-007 / NFR-001 / NFR-002): stop writing
absolute, username-bearing filesystem paths into the committed `analysis-report.md`'s
`input_artifacts` block. `_artifact_hash_entry`, `_charter_path`, and
`collect_input_artifact_hashes` in `src/specify_cli/analysis_report.py` currently record
`str(path)` — an absolute path under the contributor's `$HOME` — for every hash-input artifact.
This WP relativizes each recorded path against its correct governing root:

- `repo_root` for the three hash-input artifacts (`spec.md`, `plan.md`, `tasks.md`).
- `canonical_root` — the root `_charter_path` already resolves via
  `resolve_canonical_repo_root(repo_root)` — for the `charter` entry specifically, because of the
  #1823 cross-root worktree fix that this WP must NOT break (a linked worktree's analysis report
  legitimately hashes the MAIN checkout's charter, a path genuinely outside the passed-in
  `repo_root`).

A relativization failure must raise/surface an explicit error from `write_analysis_report`'s
call path, while `check_analysis_report_current`'s established never-raises contract (every code
path returns a typed `AnalysisFreshness`) must stay intact — the new failure mode gets caught and
mapped to `AnalysisFreshness(ok=False, reason=...)` inside that function, not left to propagate
into its caller `_require_current_analysis_report` (`cli/commands/agent/workflow.py`).

## Mission-wide baseline — capture FIRST, before any commit

This WP is sequenced FIRST in the mission (front-loaded as the highest-complexity, riskiest
concern). Before the FIRST implementation commit of the WHOLE MISSION lands (not just this WP's
own commits), run this EXACT command (do not alter it) and record the pass/fail result in
`tracer-tooling-friction.md` (append, do not overwrite; use the next available F-0N number — check
the file's existing entries first, do not assume a specific number) before proceeding to any
implementation commit.

**Concurrency note (all four WPs in this mission are `dependencies: []` / `parallel_group: 0` and
may be dispatched to genuinely concurrent worktrees):** `tracer-tooling-friction.md` is a single
shared file that is NOT — and, per the investigation below, deliberately cannot be — listed in any
WP's `owned_files`/lane `write_scope` (adding it there would make `_globs_overlap`'s
exact-path-equality rule treat every WP pair as write-scope-overlapping, which
`compute_lanes`/`validate_ownership` would then either collapse into a single lane or reject
outright as an ownership conflict at `finalize-tasks --validate-only` — both outcomes are strictly
worse than the race this note addresses, since they would destroy this mission's intentional
four-way parallelism). Because two WPs racing this check-then-act baseline capture could both
independently conclude "not present" and append competing entries, the fallback append below uses
a fresh UTC-timestamped heading rather than a guessed sequential number, so two genuinely
concurrent appends cannot collide on the same heading even without any file lock or
inter-agent coordination (chosen over "re-read immediately before commit and use the next number
after that" because a timestamp is unconditionally collision-safe for independent WP-implementer
agent processes that cannot coordinate a read-then-write critical section against each other,
whereas a re-read-and-retry protocol can still race on the final commit itself). If you are the
WP that finds the baseline genuinely not yet captured, append it under a heading of the form
`## F-<UTC-timestamp, e.g. 2026-08-23T00:12:04Z> — <title>` instead of the next sequential `F-0N`
— do not renumber or touch any other WP's entry. **(Added round-2, TASKS-FRESH-003.)** The
timestamp only guarantees the appended section's *heading text* won't collide — it does NOT
prevent a literal `git` merge conflict on this shared, untracked-by-any-lane file when two WP
branches that both appended to it are combined; that conflict remains possible and expected under
real concurrency. Whoever lands second and hits it must resolve by **keeping both entries** (never
discarding one) — a normal two-way content merge on an append-only file, not a conflict requiring
judgment about which append "wins."

```bash
pytest tests/architectural/test_dossier_emitter_positional_guard.py \
       tests/dossier/test_events.py \
       tests/architectural/test_no_dead_symbols.py \
       tests/specify_cli/test_analysis_report.py \
       tests/specify_cli/test_analysis_report_charter_yaml_staleness.py -q
```

**Disposition rule (restated in full)**: `main` carries ~23 known-red tests + 2 errors under
issue #3284 (confirmed OPEN). Any red found in this baseline that is genuinely inside #3284's
already-reported set → cite #3284, file nothing new. Any red found in this mission's
touched-test-surface that is NOT inside #3284's set → file a new GitHub issue, charter-compelled
(not optional, not an operator-escalation candidate for this specific case; corrected precedence:
charter > operator standing orders > CLAUDE.md), including the exact command run, the failure
summary, and the reasoning for believing it is pre-existing.

## Context

**(a) Why this WP exists.** SK-63 is folded into this mission per spec.md D3/§106: both #3678's
commit-subject fix and this path-relativization fix live in the same `record-analysis` write-path
call chain (`mission_record_analysis.py` calls `write_analysis_report`, which calls into
`analysis_report.py`'s `_artifact_hash_entry` / `collect_input_artifact_hashes`), so fixing both
together is proportional and directly connected per §106. SK-63's OTHER half — the retry/backoff
hang bound and the missing `committed:` field — is explicitly OUT of scope for this mission
(C-003): that reaches into the sync/telemetry layer, a genuinely different subsystem with a
different failure mode (a hang, not a public-repo data leak), and stays open in the ledger.

**(b) §106 change-scope reconciliation for this WP's specific files.** Citing spec.md's §106
section and plan.md's own §106 table verbatim: `src/specify_cli/analysis_report.py` is touched
because it is "SK-63's path-relativization half (D3-folded); the actual four absolute-path write
sites the mission brief mis-attributed to `mission_record_analysis.py`." The two test files are
touched because they carry the 5 affected charter-path assertions Grounding Correction 3
enumerates — 2 in `tests/specify_cli/test_analysis_report.py`, 3 in
`tests/specify_cli/test_analysis_report_charter_yaml_staleness.py` — each a "direct, necessary
consequence of FR-007."

**(c) Independence.** This WP has `dependencies: []` and runs fully independent of the other
three WPs in this mission (IC-01 dossier-guard widening, IC-02 re-export trim, IC-03/FR-006
commit-subject fix). Per plan.md's Implementation Concern Map, IC-03's own sequencing note states
"none against IC-01/IC-02" and that FR-007's path-relativization change and its five test-assertion
updates are "tightly coupled... and should land together," while FR-006's commit-subject change
"is independent of FR-007 within this concern" — which is why this mission's `wps.yaml` splits
FR-007 into this WP (WP01) and FR-006 into a separate WP (WP03), both still IC-03.

### Subtask T001: Confirm/capture the mission-wide baseline

- **Purpose**: satisfy the Baseline capture requirement above as this WP's own first action,
  since WP ordering across the mission is not fixed at authoring time and this WP is sequenced
  first.
- **Steps**: run the exact pytest command from the "Mission-wide baseline" section above;
  classify every red line per the disposition rule; append the result to
  `tracer-tooling-friction.md` using the fresh UTC-timestamped heading form from the "Mission-wide
  baseline" section above (`## F-<UTC-timestamp> — <title>`), NOT a guessed sequential `F-0N`
  number (concurrency note above explains why); otherwise follow the existing entries' format (a
  "Verified first-hand, <date>" line, the command/output evidence, and the disposition).
- **Files**: `kitty-specs/dossier-guard-reexport-analyze-cleanup-01M0NHRT/tracer-tooling-friction.md`
  (append only).
- **Validation**: the tracer file has a new entry recording the exact command, its outcome, and
  the disposition (cited to #3284, or a newly filed issue number, for every red line).

### Subtask T002: RED-first — update the 5 existing charter-path assertions + add the two NFR-002 test functions, confirm ALL RED

- **Purpose**: charter C-011 ATDD-first discipline — prove the current code is wrong (writes
  absolute paths) BEFORE fixing it.

Reproduce spec.md's Grounding Correction 3 exact file:line list of the five affected sites:

- `tests/specify_cli/test_analysis_report.py:238` (`test_charter_hash_resolves_canonical_root_from_worktree`) — `assert hashes["charter"]["path"] == str(charter_file.resolve())`
- `tests/specify_cli/test_analysis_report.py:260` (`test_charter_hash_falls_back_to_repo_root_outside_git`) — `assert hashes["charter"]["path"] == str(charter_file)`
- `tests/specify_cli/test_analysis_report_charter_yaml_staleness.py:52` (`test_analysis_report_staleness_hashes_charter_yaml_when_md_absent`)
- `tests/specify_cli/test_analysis_report_charter_yaml_staleness.py:94` (`test_analysis_report_staleness_no_regression_both_files_present`)
- `tests/specify_cli/test_analysis_report_charter_yaml_staleness.py:137` (`test_analysis_report_staleness_hashes_charter_md_when_yaml_absent`)

- **Steps**:
  1. Update each of the five sites to assert the NEW `canonical_root`-relative path string instead
     of the absolute resolved path (e.g. `str(charter_file.resolve().relative_to(canonical_root))`
     or the implementation's equivalent). Do NOT change any other assertion in these tests — the
     sha256 checks, `"charter" in hashes`, and freshness/success checks stay exactly as they are.
     For `:260` specifically (the outside-git fallback test), `canonical_root` there equals the
     passed `repo_root` (per plan.md's Concrete-shape point 1), so the expected value is
     `str(charter_file.relative_to(repo_root))` or the implementation's equivalent — the
     underlying fallback behavior (`_charter_path` degrading to `canonical_root = repo_root`
     outside git) is unchanged, only the assertion's expected string changes.
  2. Explicitly out of scope, needs no change: `tests/specify_cli/test_analysis_report.py:416`
     (`assert emitted["path"] == str(report_path)`, inside
     `test_record_analysis_command_persists_report`) — this asserts the analysis-report file's OWN
     location (`AnalysisReportResult.to_dict()`'s `"path": str(self.path)`), not
     `input_artifacts[*]["path"]`. `_artifact_hash_entry`/`_charter_path` never touch it. Do not
     modify this assertion.
  3. Add TWO new test functions constructing an unrelativizable-path condition (per NFR-002) — NOT
     one combined test — so each of T003 and T004 has its own independently-reportable GREEN
     state (a single combined function cannot report "half passing" in pytest: it would still
     FAIL/ERROR as a whole once the first assertion block starts passing but the second still hits
     the same now-uncaught exception):
     - `test_write_analysis_report_raises_on_unrelativizable_path` (or equivalent name) — asserts
       ONLY that `write_analysis_report` raises/surfaces an explicit error for an unrelativizable
       `spec.md`/`plan.md`/`tasks.md` path. This is the test T003 turns GREEN.
     - `test_check_analysis_report_current_reports_relativization_failure_without_raising` (or
       equivalent name) — asserts ONLY that `check_analysis_report_current` returns
       `AnalysisFreshness(ok=False, reason=...)` — never raises — for the equivalent condition.
       This is the test T004 turns GREEN.
     Both may share fixture/setup helpers; keep the two assertion bodies in separate `def test_...`
     functions so pytest can report each independently.
  4. Run all 7 changed/new assertions/tests (5 updated charter-path assertions + the 2 new NFR-002
     test functions) against the CURRENT (pre-fix) code and confirm every one is RED: the five
     updated assertions fail because the code still returns the absolute path; both new NFR-002
     test functions fail because there is no relativization-failure handling yet.
  5. Commit this as its own commit, before any implementation commit, with a
     `test(analysis-report):` scoped conventional-commit subject.
- **Files**: `tests/specify_cli/test_analysis_report.py`,
  `tests/specify_cli/test_analysis_report_charter_yaml_staleness.py`.
- **Validation**:
  `pytest tests/specify_cli/test_analysis_report.py tests/specify_cli/test_analysis_report_charter_yaml_staleness.py -q`
  shows all 7 sites failing (RED) — the 5 updated assertions and both new NFR-002 test
  functions — confirmed and recorded before proceeding to T003.

### Subtask T003: GREEN — implement the `_charter_path` tuple-return change + shared relativize-or-raise helper + `_artifact_hash_entry`/`collect_input_artifact_hashes` updates

- **Purpose**: implement plan.md IC-03's "Concrete shape" points 1-4 verbatim — this shape is
  BINDING, not optional guidance.

Reproduce plan.md's exact binding shape as numbered steps:

1. **`_charter_path` keeps its own resolution logic verbatim; only its return shape changes.**
   `_charter_path(repo_root: Path) -> tuple[Path | None, Path]` now returns
   `(charter_path, canonical_root)` instead of bare `Path | None`. `canonical_root` is exactly the
   value the function's EXISTING body already computes
   (`resolve_canonical_repo_root(repo_root)`, falling back to `canonical_root = repo_root` on
   `NotInsideRepositoryError`) — that try/except is UNTOUCHED, so
   `test_charter_hash_falls_back_to_repo_root_outside_git`'s underlying fallback behavior is
   preserved unchanged. Not-found case: `(None, canonical_root)`. Found case:
   `(charter_path, canonical_root)`. The caller (`collect_input_artifact_hashes`) checks
   `if charter_path is not None`. No second `resolve_canonical_repo_root` call anywhere in the
   fix — the single-call tuple-return design structurally prevents a duplicated try/except.
2. **`collect_input_artifact_hashes` (currently lines 217-226) consumes the tuple.**
   `charter_path, canonical_root = _charter_path(repo_root)`. If `charter_path is None`:
   `inputs["charter"] = {"path": None, "sha256": None}` (unchanged). Otherwise: relativize
   `charter_path` against `canonical_root` via the shared helper (step 4 below) and record the
   relative string, plus `_sha256_file(charter_path)` unchanged (hashing still reads the absolute
   path; only the recorded `path` string changes). In practice this relativization always
   succeeds because `_charter_path` only ever constructs `charter_path` as
   `canonical_root / CHARTER_YAML` or `canonical_root / CHARTER_MD` — but the shared
   raise-on-failure helper is used uniformly rather than special-cased, so a future change to
   `_charter_path` cannot silently reintroduce the absolute-path leak without the helper catching
   it.
3. **`_artifact_hash_entry` (currently lines 179-185) gains a `governing_root: Path` parameter**:
   `_artifact_hash_entry(path: Path, governing_root: Path) -> dict[str, str | None]`, called for
   spec.md/plan.md/tasks.md with `governing_root=repo_root`. When `path.exists()`: relativize via
   the shared helper — a relativization failure raises (this is the hypothetical
   symlink-escaping-`repo_root` case, spec.md Acceptance Scenario 3). When `path` does NOT exist:
   UNCHANGED from today — still `{"path": str(path), "sha256": None}`, still absolute (deliberate
   non-change: `write_analysis_report` requires all three inputs to exist before calling
   `collect_input_artifact_hashes`, so this branch never fires on the path that produces the
   committed artifact).
4. **One shared relativize-or-raise helper** performing `path.relative_to(governing_root)`,
   translating a `ValueError` into a raised exception — both call sites (charter branch,
   `_artifact_hash_entry`) go through this ONE helper (do not duplicate the logic ad hoc per call
   site).
5. **Exception type**: reuse `AnalysisReportError` (`src/specify_cli/analysis_report.py:124`) or
   introduce a narrowly-scoped `PathRelativizationError(AnalysisReportError)` subtype —
   implementer's choice, but `check_analysis_report_current`'s catch (T004) must be specific to
   it, never a broad `except Exception:`.

- **Files**: `src/specify_cli/analysis_report.py` (~30-50 line diff across the four touched
  functions/helper).
- **Validation**: the T002 charter-path assertion updates now pass GREEN;
  `test_write_analysis_report_raises_on_unrelativizable_path` (T002's first NFR-002 test function)
  now passes GREEN, independently and cleanly reportable by pytest as its own passing test.
  `test_check_analysis_report_current_reports_relativization_failure_without_raising` (T002's
  second NFR-002 test function) is still RED until T004 — this is an ordinary, individually
  reportable RED on its own test function, not a "half-passing" state on a shared one.

### Subtask T004: GREEN — add the try/except in `check_analysis_report_current` (NFR-002 non-raising contract)

- **Purpose**: implement plan.md IC-03's "Concrete shape" point 6 — `check_analysis_report_current`
  currently has NO try/except of any kind around its `collect_input_artifact_hashes` call
  (verified against the live code at `analysis_report.py:458-544`, call at line 515 pre-change)
  and MUST get one added, or the relativization failure propagates into
  `_require_current_analysis_report` (`cli/commands/agent/workflow.py`) — exactly the regression
  NFR-002 forbids.
- **Steps**: wrap the `collect_input_artifact_hashes(...)` call inside
  `check_analysis_report_current` in
  `try: ... except <exception type from T003 step 5>: return AnalysisFreshness(ok=False, path=path, stale=True, missing=False, reason=<describes the relativization failure>, mismatches={})`.
  Confirm `write_analysis_report` (line ~397) intentionally keeps NO try/except around its own
  call into `collect_input_artifact_hashes` (line ~412) — this is by design (unchanged), so the
  same exception propagates there uncaught, satisfying NFR-002 Acceptance Scenario 3.
- **Files**: `src/specify_cli/analysis_report.py`.
- **Validation**:
  `test_check_analysis_report_current_reports_relativization_failure_without_raising` (T002's
  second NFR-002 test function) now passes GREEN, independently and cleanly reportable by pytest
  (returns typed `AnalysisFreshness(ok=False, ...)` rather than raising).

### Subtask T005: Verify — full green run, NFR-001 grep check, revert discipline, SK-63 tracer note

- **Purpose**: close out the WP with concrete, run evidence — not an assumed pass.
- **Steps**:
  (a) run
  `pytest tests/specify_cli/test_analysis_report.py tests/specify_cli/test_analysis_report_charter_yaml_staleness.py -q`
  and confirm 0 failures;
  (b) run the mission-wide baseline command again (same 5-file command from T001) and confirm no
  new red beyond what T001 recorded;
  (c) generate a fresh `analysis-report.md` via the exercised `write_analysis_report` path and run
  `grep -E '"path":\s*"(/home|/Users)/' <path-to-generated-report>` confirming ZERO matches
  (SC-006/NFR-001);
  (d) record in this mission's own analyze-phase awareness: per plan.md's "Reflexivity" section,
  THIS mission's own later `record-analysis` invocation is the first live exercise of this fix —
  if it fails (commitlint OR a leaked path), that is FR-006/FR-007 NOT YET DONE, fix forward
  within this mission before PR-prep, per the binding recovery path in plan.md's Reflexivity
  section (do not treat it as a pre-existing/unrelated failure).
- **Files**: none new; verification only.
- **Validation**: all pytest runs green; grep returns zero matches; T005 completion recorded via
  `spec-kitty agent tasks mark-status T005 --status done`.

## §591 ATDD-First Discipline (C-011, binding) — explicit statement for this WP

RED-first commit (T002) updates the 5 existing charter-path assertions (per spec.md Grounding
Correction 3's exact 5 file:line sites, cited above) to the NEW `canonical_root`-relative expected
values, AND adds the two new NFR-002 test functions (one per behavior — see T002 step 3)
constructing an unrelativizable-path condition — confirm ALL of these (7 total) are RED against the
current (pre-fix) code, as one commit, before any implementation commit. GREEN commits (T003, T004)
implement the 7-point "Concrete shape" from plan.md IC-03; T003 turns the write-half NFR-002 test
function independently GREEN, T004 turns the non-raising-half NFR-002 test function independently
GREEN. The review squad will check out the commit immediately before the first GREEN implementation
commit and re-run the 7 changed/new assertions expecting RED, then check out final expecting GREEN.

## §106 change-scope reconciliation for this WP

Citing spec.md's D3 and §106 section, and plan.md's own §106 table, verbatim in substance: this WP
folds in item 4 (SK-63's path-relativization half) from the §106 table — "SK-63's
path-relativization half (D3-folded); the actual four absolute-path write sites the mission brief
mis-attributed to `mission_record_analysis.py`" — and items 5/6 (the two test files) — direct,
necessary consequences of FR-007. Tracker references: #3676 (mission umbrella), ledger SK-63,
ledger SK-64 (Grounding Correction 4, cited for context though SK-64 is more directly WP03's
concern).

## Definition of Done

- [ ] Mission-wide baseline captured and disposed, recorded in `tracer-tooling-friction.md` (T001).
- [ ] RED-first commit landed and confirmed RED against pre-fix code (T002).
- [ ] GREEN implementation commits landed (T003, T004).
- [ ] All pytest assertions in both owned test files pass GREEN.
- [ ] NFR-001/SC-006 grep check (`grep -E '"path":\s*"(/home|/Users)/'`) against a freshly
      generated `analysis-report.md` returns zero matches.
- [ ] `check_analysis_report_current`'s non-raising contract is preserved, verified by
      `test_check_analysis_report_current_reports_relativization_failure_without_raising` (T002's
      second NFR-002 test function).
- [ ] `test_charter_hash_resolves_canonical_root_from_worktree`'s underlying cross-root/#1823
      resolution behavior still holds — not just the updated assertion text.
- [ ] No absolute `$HOME`/username-bearing path written anywhere in this WP's own committed
      artifacts (C-001).

## Risks

- The #1823 cross-root worktree behavior is easy to accidentally regress if a second
  `resolve_canonical_repo_root` call is introduced (explicitly forbidden by the Concrete Shape).
  **Mitigation**: the single-call tuple-return design in T003 step 1 structurally prevents this.
- A too-broad `except Exception:` in T004 would swallow unrelated errors. **Mitigation**: catch
  only the specific exception type from T003 step 5.

## Reviewer Guidance

Reviewers should specifically re-run: the exact 5 charter-path assertion sites (confirm each now
asserts the relative form, and confirm sha256/other assertions in those same tests are untouched);
both NFR-002 test functions end to end; a manual generation of `analysis-report.md` with the NFR-001 grep;
and confirm `check_analysis_report_current` still never raises by inspecting the new try/except.

## Implementation command

```
spec-kitty agent action implement WP01 --agent claude
```
