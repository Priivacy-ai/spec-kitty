---
work_package_id: WP03
title: record-analysis commit-subject conventional-commit fix (FR-006)
dependencies: []
requirement_refs:
- FR-006
- C-004
planning_base_branch: fix/dossier-guard-reexport-analyze-cleanup-3676
merge_target_branch: fix/dossier-guard-reexport-analyze-cleanup-3676
branch_strategy: Planning artifacts for this mission were generated on fix/dossier-guard-reexport-analyze-cleanup-3676. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/dossier-guard-reexport-analyze-cleanup-3676 unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-dossier-guard-reexport-analyze-cleanup-01M0NHRT
base_commit: a513bcf27bc2678ab280e3462dbd9e8d14760b06
created_at: '2026-08-23T00:16:01.756295+00:00'
subtasks:
- T010
- T011
- T012
history: []
agent_profile: python-pedro
authoritative_surface: src/specify_cli/cli/commands/agent/mission_record_analysis.py
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/cli/commands/agent/mission_record_analysis.py
- tests/specify_cli/cli/commands/agent/test_mission_record_analysis.py
role: implementer
tags: []
tracker_refs: []
---

# WP03: record-analysis commit-subject conventional-commit fix (FR-006)

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this work package's `task_type` and `authoritative_surface`.

---

## Objective

Fix GitHub issue #3678: the `record-analysis` commit's subject
(`f"Add analysis report for mission {slug}"`, currently constructed at
`mission_record_analysis.py:365`) fails commitlint — it has no `type(scope):` prefix at all, so
`type-enum`, `type-case`, `type-empty`, and `subject-empty` all reject it. Give it a
conventional-commit-compliant subject of the shape `docs(<scope>): <free-text subject>` — `type`
MUST be `docs` — WITHOUT touching `commitlint.config.cjs` (C-004).

## Mission-wide baseline — confirm before your first commit

This mission's baseline capture command spans all five touched test files and must run once,
before the FIRST implementation commit of the WHOLE MISSION (not per-WP). WP01 (sequenced first)
owns primary responsibility for capturing it. Before your own first commit in this WP: confirm
the mission-wide baseline was already captured — check
`kitty-specs/dossier-guard-reexport-analyze-cleanup-01M0NHRT/tracer-tooling-friction.md` for an
F-0N entry recording it. If not present, run it now yourself and record the result in
`tracer-tooling-friction.md` (append, never overwrite; otherwise follow the existing entries'
format) BEFORE proceeding. The exact command:

**Concurrency note (all four WPs in this mission are `dependencies: []` / `parallel_group: 0` and
may be dispatched to genuinely concurrent worktrees):** `tracer-tooling-friction.md` is a single
shared file that is intentionally NOT listed in any WP's `owned_files`/lane `write_scope` — this
was investigated during the fix pass that added this note: adding it there would make
`_globs_overlap`'s exact-path-equality rule treat every WP pair as write-scope-overlapping, and
`compute_lanes`/`validate_ownership` would then either collapse all four independent lanes into
one or reject the manifest outright as an ownership conflict at `finalize-tasks --validate-only`
— both strictly worse than the race this note addresses, since either would destroy this
mission's intentional four-way parallelism. Because two WPs racing this check-then-act baseline
capture could both independently conclude "not present" and append competing entries, if YOU are
the WP that finds the baseline genuinely not yet captured, append it under a fresh
UTC-timestamped heading — `## F-<UTC-timestamp, e.g. 2026-08-23T00:12:04Z> — <title>` — instead of
a guessed sequential `F-0N` number, so two genuinely concurrent appends cannot collide on the same
heading even without a file lock or inter-agent coordination. Do not renumber or touch any other
WP's entry. **(Added round-2, TASKS-FRESH-003.)** The timestamp only guarantees the appended
section's *heading text* won't collide — it does NOT prevent a literal `git` merge conflict on
this shared, untracked-by-any-lane file when two WP branches that both appended to it are
combined; that conflict remains possible and expected under real concurrency. Whoever lands second
and hits it must resolve by **keeping both entries** (never discarding one) — a normal two-way
content merge on an append-only file, not a conflict requiring judgment about which append "wins."

```bash
pytest tests/architectural/test_dossier_emitter_positional_guard.py \
       tests/dossier/test_events.py \
       tests/architectural/test_no_dead_symbols.py \
       tests/specify_cli/test_analysis_report.py \
       tests/specify_cli/test_analysis_report_charter_yaml_staleness.py -q
```

**Disposition rule (restated)**: `main` carries ~23 known-red tests + 2 errors under issue #3284
(confirmed OPEN). Red genuinely inside #3284's set → cite #3284, file nothing new. Red OUTSIDE
#3284's set → file a new GitHub issue (charter §486, binding absolutely per spec.md's corrected
precedence: charter > operator standing orders > CLAUDE.md) — not optional, not an
operator-escalation candidate for this specific case.

## Context

**(a) This WP's place in the concern map.** WP03 is IC-03/FR-006 in plan.md's Implementation
Concern Map, deliberately split OUT of the combined IC-03 concern (which also covers FR-007, the
SK-63 path-relativization WP owned by WP01). plan.md's IC-03 entry states this explicitly: FR-006's
commit-subject change "is independent of FR-007 within this concern and could be split into its
own WP if task planning finds that useful, since both live in the same file family but touch
disjoint code paths (`mission_record_analysis.py`'s `message=` string vs.
`analysis_report.py`'s hash-entry helpers)." This mission's task-authoring pass took that option:
WP03 owns ONLY `mission_record_analysis.py:365`, disjoint from WP01's `analysis_report.py` and
test files.

**(b) Independence.** `dependencies: []` — WP03 is fully independent of all three other WPs in
this mission.

**(c) Fix-direction resolution.** spec.md's Grounding Correction 4 resolves this in full: the
mission brief offered two options and tentatively leaned toward widening
`commitlint.config.cjs`'s ignore regex. Grounding found two things: (a) the brief's own
illustrative alternative message, `f"Add analysis for mission {slug}"`, does NOT actually satisfy
the current ignore regex `/^(Add|Update) (meta|spec|tasks|plan) for (feature|mission) /` —
`analysis` is not in the `(meta|spec|tasks|plan)` alternation, confirmed by reading
`commitlint.config.cjs` directly — so a message-only change would require the regex to also
widen, or a different message shape entirely; (b) ledger entry SK-64 (the workspace-root
SPEC-KITTY-LEDGER.md) already investigated this exact defect first-hand on a related mission,
measured it ("2 of 52 commits fail commitlint, and both are that same record-analysis message"),
and states its own fix-direction preference order explicitly: "(1) have record-analysis emit a
conforming subject... fixes the cause and needs no ignore-list growth; or (2) extend the ignore
regex." This spec adopts SK-64's option (1): give the `record-analysis` commit a real
conventional-commit subject (`type(scope): subject`) rather than widening
`commitlint.config.cjs`. `commitlint.config.cjs` is NOT touched by this mission (C-004).

**(d) §106 change-scope reconciliation for this file.** Per spec.md's §106 section and plan.md's
own §106 table, `mission_record_analysis.py` is touched because it is "#3678's own named defect;
the sole call site constructing the non-conforming commit message." Tracker references: #3678,
ledger SK-64.

### Subtask T010: RED-first — add a fixture exercising the current non-conforming subject, confirm RED

- **Purpose**: charter C-011 ATDD-first — prove the CURRENT subject fails commitlint before
  changing it.
- **Steps**: add a fixture (unit-level string-shape proxy AND/OR a real `commitlint` invocation —
  plan.md states both are in scope, and the LIVE commitlint run is authoritative per SC-005's
  Independent Test framing) that exercises the CURRENT non-conforming subject shape
  `f"Add analysis report for mission {slug}"` against commitlint's rules (`type-enum`,
  `type-case`, `type-empty`, `subject-empty`). The unit-level proxy MUST NOT hardcode a
  separately-typed copy of the subject string as its assertion target — per plan.md's binding
  "Revert discipline" ("a unit test asserting the constructed `message=` string matches the
  shape"), it must assert against the REAL, live-constructed value: mock
  `specify_cli.coordination.commit_router.commit_for_mission` (the same import-path-patch pattern
  established at `tests/specify_cli/cli/commands/review/test_issue_matrix_finalize_lint.py:134-136`)
  inside a real CLI invocation of `record-analysis`, capture the `message=` kwarg the mock
  receives, and assert your commitlint-shape / string-shape checks against THAT captured value —
  never against a second, independently-typed literal. This is what makes the fixture non-vacuous:
  it fails if `mission_record_analysis.py`'s construction is reverted, because the captured
  `message=` value would then change back to the old shape. Run it and confirm RED — commitlint
  reports at least one problem (no recognized `type(scope):` prefix) against the captured subject,
  or the unit-level assertion against the captured `message=` value fails. Commit this as its own
  commit, before any implementation commit, with a `test(record-analysis):` scoped
  conventional-commit subject. (Note: keep this test's own commit subject itself
  commitlint-conforming — it is a NEW test-authoring commit, not the fixed `record-analysis` code
  path, so it should just use a normal conforming type prefix like any other commit in this
  repo.)
- **Files**: `tests/specify_cli/cli/commands/agent/test_mission_record_analysis.py` — this is
  WP03's ONE test file for this fixture (it already exists; add to it, do not create a new
  module). Do **NOT** touch `tests/specify_cli/test_analysis_report.py` or
  `tests/specify_cli/test_analysis_report_charter_yaml_staleness.py` — those are WP01's
  exclusively-owned files (a separate, independent `dependencies: []`/`parallel_group: 0` lane);
  writing to either would create a real cross-lane file conflict this mission's IC-03 split was
  designed to avoid. `test_mission_record_analysis.py` is now listed in this WP's own
  `owned_files` (frontmatter and `wps.yaml`) and in `lanes.json`'s `lane-c.write_scope` — confirm
  this before your first commit if in doubt.
- **Validation**: the new test/fixture is confirmed RED (commitlint reports a problem against the
  captured subject, or the unit-level assertion against the captured `message=` kwarg fails)
  against the current `message=f"Add analysis report for mission {slug}"` construction.

### Subtask T011: GREEN — change the `message=` construction to the `docs(<scope>): <subject>` shape

- **Purpose**: implement the actual fix at `mission_record_analysis.py:365` (confirm the exact
  current line number before editing — line numbers may have shifted slightly since spec/plan
  authoring).
- **Steps**: change `message=f"Add analysis report for mission {_analysis_mission_slug}"` to a
  conventional-commit-compliant f-string of the shape `f"docs(<scope>): <free-text subject>"`
  where `type` is pinned to `docs` (per FR-006, matching this repo's own established convention
  for tool-authored analyze/review commits — e.g. the cited
  `docs(review): commit pre-merge verification and fresh sweep for implementation diff` example
  from Grounding Correction 4). The exact scope token and free-text subject wording are left to
  implementation (FR-006 says so explicitly) — a reasonable choice is
  `docs(mission): record analysis report for mission {slug}` or similar, but confirm the chosen
  wording actually passes commitlint's `subject-empty`/`type-case` rules (lowercase type,
  non-empty subject) before finalizing. Preserve the existing
  `contextlib.suppress(subprocess.CalledProcessError, OSError, RuntimeError, ValueError)`
  wrapping around the `commit_for_mission(...)` call UNCHANGED — this mission fixes the subject
  format only, not the surrounding commit-failure handling (spec.md Acceptance Scenario 4 is
  explicit that this suppression behavior is out of scope).
- **Files**: `src/specify_cli/cli/commands/agent/mission_record_analysis.py` (one line changed).
- **Validation**: the T010 fixture/test now passes GREEN (commitlint reports 0 problems against
  the new subject shape, or the unit-level assertion passes).

### Subtask T012: Verify — live commitlint run, SC-005, tracer-file note for the mission's own analyze-phase self-test

- **Purpose**: close out with concrete, run evidence — the authoritative evidence per plan.md's
  "Revert discipline" is the LIVE commitlint run against a real `record-analysis` commit, not the
  unit-level proxy alone.
- **Steps**: (a) if feasible within this WP's scope, exercise `record-analysis` against a
  scaffolded/test mission and run `commitlint --from <parent-sha> --to <analysis-commit-sha>` (or
  the repo's equivalent invocation) confirming 0 problems, WITHOUT any change to
  `commitlint.config.cjs`; if a full live exercise is impractical inside this WP's own execution,
  at minimum confirm the unit-level fixture from T010/T011 is green and note explicitly in the
  WP's completion record that the live commitlint proof will additionally come from THIS
  MISSION'S OWN `record-analysis` commit later in its own lifecycle (see next point); (b) note
  explicitly, per plan.md's "Reflexivity" section: this mission's own later `record-analysis`
  invocation is the first real-world exercise of this exact fix — if that commit fails
  commitlint, that is FR-006 NOT YET DONE (not a pre-existing/unrelated failure), and per the
  binding recovery path there, add a RED-first fixture reproducing the actual observed failing
  subject, confirm RED against the currently-landed WP03 implementation, then amend
  `mission_record_analysis.py`'s `message=` construction again until commitlint reports 0
  problems — fix forward within this mission before PR-prep, do not open the PR with a
  known-failing self-test.
- **Files**: none new beyond T010 (unless a live-commitlint integration test is added here).
- **Validation**: commitlint reports 0 problems against the new subject shape (live run and/or
  unit-level proxy, per above); T012 completion recorded via
  `spec-kitty agent tasks mark-status T012 --status done`.

## §591 ATDD-First Discipline (C-011, binding) — explicit statement for this WP

RED-first commit (T010) adds a fixture that exercises the real `commitlint` invocation (or the
local unit-level string-shape proxy — plan.md says both are in scope, live commitlint is
authoritative) against the CURRENT non-conforming subject
`f"Add analysis report for mission {slug}"`, confirmed RED (commitlint reports a problem), as its
own commit. GREEN commit (T011) changes the `message=` construction to the
`docs(<scope>): <subject>` shape, re-confirms GREEN (0 problems).

## Definition of Done

- [ ] Mission-wide baseline confirmed captured (existing F-0N entry found, or captured fresh and
      recorded per the "Mission-wide baseline" section above).
- [ ] RED-first commit landed and confirmed RED against the current non-conforming subject
      (T010).
- [ ] GREEN commit landed changing `message=` to the `docs(<scope>): <subject>` shape (T011).
- [ ] commitlint reports 0 problems against the new subject (live and/or unit-proxy, T012).
- [ ] `commitlint.config.cjs` untouched (C-004) — zero diff.
- [ ] The existing `contextlib.suppress(subprocess.CalledProcessError, OSError, RuntimeError, ValueError)`
      behavior around `commit_for_mission(...)` is byte-for-byte unchanged.

## Risks

Low risk, single string-literal change. The main risk is choosing a scope/subject wording that
technically satisfies `type-enum`/`type-case` but fails `subject-empty` or an unanticipated
commitlint rule — mitigated by actually running commitlint against the chosen wording (T012)
rather than assuming it passes.

## Reviewer Guidance

Reviewers should specifically: confirm the new subject is `docs(<scope>): <subject>` shaped with
`docs` as the literal type; confirm `commitlint.config.cjs` has zero diff; confirm the
`contextlib.suppress(...)` wrapping is unchanged; and — critically — check this mission's OWN
`record-analysis` commit later in the PR (per Reflexivity) to confirm it is itself
commitlint-clean, as first-party live proof the fix works.

## Implementation Command

```bash
spec-kitty agent action implement WP03 --agent claude
```
