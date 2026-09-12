---
work_package_id: WP04
title: check-prerequisites / record-analysis orchestrator-api verbs
dependencies:
- WP01
requirement_refs:
- FR-004
- FR-005
- NFR-001
- NFR-002
- NFR-004
- NFR-005
- C-001
- C-002
planning_base_branch: feat/design-phase-orchestrator-api-3837
merge_target_branch: feat/design-phase-orchestrator-api-3837
branch_strategy: Planning artifacts for this mission were generated on feat/design-phase-orchestrator-api-3837. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/design-phase-orchestrator-api-3837 unless the human explicitly redirects the landing branch.
subtasks:
- T015
- T016
- T017
- T018
- T019
- T020
- T021
scope: codebase-wide
history: []
agent_profile: implementer-ivan
authoritative_surface: src/specify_cli/orchestrator_api/
create_intent:
- tests/specify_cli/orchestrator_api/test_check_prerequisites_record_analysis.py
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/orchestrator_api/commands.py
- tests/specify_cli/orchestrator_api/test_check_prerequisites_record_analysis.py
- tests/specify_cli/orchestrator_api/test_commands_fail_closed.py
- tests/specify_cli/orchestrator_api/test_typed_error_fail_closed.py
role: implementer
tags: []
tracker_refs: []
---

# WP04 — check-prerequisites / record-analysis orchestrator-api verbs

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `implementer-ivan`
- **Role**: `implementer`
- **Agent/tool**: (unset — select at implementation time)

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this work package's `task_type` and `authoritative_surface`.

---

## Objective

Add `check-prerequisites` (a read-only context/query verb, FR-004) and
`record-analysis` (a write verb with a trustworthy, artifact-derived
success signal, FR-005) so an external host can drive the `analyze` design
phase without performing the cross-artifact reasoning itself (C-002) and
without trusting a subprocess exit code that SK-93 proved unreliable
(NFR-004).

## Context

**C-002 (binding)**: spec-kitty MUST NOT gain a verb that performs
`analyze`'s cross-artifact reasoning. `check-prerequisites` supplies
context only; `record-analysis` persists a finished report only — mirror
`start-review`'s "cannot perform WP implementation itself" pattern.

**FR-004 / check-prerequisites**: mirror the host CLI's `agent mission
check-prerequisites --json --include-tasks --mission <slug>`
(`src/specify_cli/cli/commands/agent/mission_check_prerequisites.py:498`),
NOT the drifted `.kittify/overrides/.../command-templates/analyze.md`
copy (spec Clarification 2 — that copy independently drifted, is a
pre-existing defect out of this mission's scope to fix). Read
`mission_check_prerequisites.py:462-560` — `check_prerequisites`
(the Typer command function itself) assembles `validation_result` via
`specify_cli.cli.commands.agent.mission.validate_feature_structure` and
emits it through `_paths_only_payload`/`_inject_branch_contract`. Your
verb must return the SAME prerequisite/task-listing fields for the SAME
mission, called in-process — decide whether to call
`validate_feature_structure` directly (cleaner layering) or the
`check_prerequisites` Typer function itself in-process (if that's this
repo's established orchestrator-api-calling-CLI-layer pattern — check
whether any of the 10 existing verbs already call an `agent mission`
Typer command function in-process before assuming this is fine; if none
do, prefer calling `validate_feature_structure` directly and replicate the
`_paths_only_payload --include-tasks`-equivalent shaping in the
orchestrator-api layer, so this verb never crosses into
CLI-command-layer code the way FR-014's operator ruling explicitly warned
against for `answer-decision` — the same "extract, don't inline"
discipline applies here to whatever extent a genuinely reusable function
already exists one layer beneath the CLI command).

**FR-005 / record-analysis / NFR-004 (SK-93) — concrete mechanism, already
fully specified in plan.md § (j); implement it exactly, do not re-derive
more loosely**:

1. **Call-start timestamp**: capture `now_utc_iso()` (the same clock
   helper `mission_v1/events.py` and `analysis_report.py` already use)
   immediately BEFORE invoking the underlying write path.
2. **Bypass the unbounded dossier-sync trigger** — `record_analysis`'s own
   `trigger_feature_dossier_sync_if_enabled` call
   (`mission_record_analysis.py:384-388`) is wrapped only in
   `contextlib.suppress(Exception)`, which bounds a *raised* exception but
   NOT a *hang*. Choose ONE of:
   - **(a)** call `write_analysis_report`/`commit_for_mission`
     (`src/specify_cli/analysis_report.py:473`) directly, excluding the
     dossier-sync tail entirely, OR
   - **(b)** if `record_analysis`'s preflight/validation logic (dirty-worktree
     check, placement resolution, empty-body check — the early-exit
     branches at `mission_record_analysis.py:228-292`) is worth reusing
     rather than reimplementing, wrap the ENTIRE `record_analysis` call in
     an explicit, enforced timeout (thread-based or signal-based) at the
     orchestrator-api layer.
   This WP's implementer decides between (a) and (b) based on how much of
   `record_analysis`'s preflight logic is reusable without the
   dossier-sync tail — plan.md deliberately leaves this as an
   implementation-detail call, not a pre-frozen architecture decision.
3. **Re-read and correlate**: after the write path returns (or the timeout
   fires), re-read `kitty-specs/<slug>/analysis-report.md` off disk.
   `success: true` ONLY if BOTH (a) the re-read `verdict` field matches the
   value THIS call submitted, AND (b) the re-read `generated_at`
   frontmatter timestamp (`analysis_report.py:505-524`) is LATER than the
   call-start timestamp from step 1. A verdict-string match alone is
   NEVER sufficient — this is the exact distinction between SC-005(a)
   (swallowed-exception-but-written → `success: true`) and SC-005(c)
   (stale-but-coincidentally-matching-verdict → `success: false`).
4. `record-analysis` accepts `--mission`, `--input-file` (or an inline
   body), `--agent`, `--policy` (mutating verb — `POLICY_METADATA_REQUIRED`
   pattern applies).

**C-001**: confirm no `spec-kitty-events`/`spec-kitty-tracker` import is
introduced (`grep -rn "spec_kitty_events\|spec_kitty_tracker"
src/specify_cli/orchestrator_api/commands.py` stays empty).

## Subtask T015: RED — author `test_check_prerequisites_record_analysis.py`

**Purpose**: Land a genuinely failing ATDD test set before either verb
exists — the SC-005 three-way split is the load-bearing part of this RED
commit, not an afterthought bolted on later.

**Steps**:
1. Create `tests/specify_cli/orchestrator_api/test_check_prerequisites_record_analysis.py`.
2. Write a test for `check-prerequisites --mission <slug>` against a
   mission mid-tasks-phase asserting field-parity with the host CLI's
   `agent mission check-prerequisites --json --include-tasks --mission
   <slug>` output — RED because the verb does not exist yet.
3. Write the three SC-005 sub-tests (all against `record-analysis`, all
   RED for the same "command not found" reason pre-implementation, but
   each pinning a DISTINCT success-determination path so none of them
   silently degrade into a duplicate of another once GREEN — see T019-T021
   below for the exact scenario each must encode):
   - swallowed-exception-but-written
   - hang-but-written (time-bound)
   - stale-but-coincidentally-matching-verdict
4. Mark `pytestmark = [pytest.mark.integration, pytest.mark.git_repo]` —
   these tests do real file I/O (`analysis-report.md` reads/writes against
   a real mission fixture dir), matching `test_transition_subtask_gate.py`'s
   precedent, not the `fast`-marked convention of
   `test_commands_fail_closed.py`. This is what makes
   `integration-tests-core-misc`'s `-m 'not windows_ci and (git_repo or
   integration or architectural) and not timing and not regression'`
   filter collect the file; `fast-tests-core-misc` will not.
5. Confirm RED on `planning_base_branch` before implementing.

**Files**: `tests/specify_cli/orchestrator_api/test_check_prerequisites_record_analysis.py` (new, ~200-280 lines — the SC-005 three-way split needs real mocking scaffolding for "hang" and "stale artifact" setup).

**Validation**: All tests in this file fail (command not found) on `planning_base_branch`.

## Subtask T016: Implement `check-prerequisites` verb (FR-004)

**Purpose**: Read-only context verb.

**Steps**:
1. Add `@app.command(name="check-prerequisites")`, options `--mission`
   (required), `--include-tasks` (bool, default matching the host CLI's
   own default). **No `--policy` required** — this is a read-only verb,
   mirroring `list-ready`'s existing no-policy contract (per spec Edge
   Cases: "Read-only verbs (check-prerequisites, design-status) do not
   require --policy").
2. Assemble the SAME prerequisite/task-listing fields the host CLI's
   `--json --include-tasks` mode returns (see Context above for the exact
   call-target decision).
3. `validate_outbound_payload(data, "orchestrator_api")` then
   `make_envelope(command=cmd, success=True, data=data)`.

**Files**: `src/specify_cli/orchestrator_api/commands.py` (~40-60 new lines).

**Validation**: T015's check-prerequisites test passes.

## Subtask T017: Implement `record-analysis` core write path (FR-005 step 1-2)

**Purpose**: Land the call-start-timestamp + bypass-dossier-sync mechanism.

**Steps**:
1. Add `@app.command(name="record-analysis")`, options `--mission`,
   `--input-file` (path) or inline body option (mirror
   `mission_record_analysis.py`'s own CLI flags), `--agent`, `--policy`
   (required — mutating verb).
2. Capture `now_utc_iso()` before invoking the underlying write path.
3. Implement whichever of options (a)/(b) from Context was chosen; if (b),
   the timeout implementation must be a REAL enforced bound (thread-based
   `Thread.join(timeout=...)` or signal-based `SIGALRM`, not a bare
   `try/except` that never actually interrupts a hang) — this is exactly
   what T020's hang-but-written test exercises.

**Files**: `src/specify_cli/orchestrator_api/commands.py` (~60-100 new lines).

**Validation**: no test yet — T018 completes the correctness loop.

## Subtask T018: Implement re-read/correlate success determination (FR-005 step 3)

**Purpose**: The artifact re-read IS the success signal, never the
underlying call's return/raise/hang behavior.

**Steps**:
1. After the write path returns (normally, via exception, or via timeout),
   unconditionally re-read `kitty-specs/<slug>/analysis-report.md`.
2. `success = (reread.verdict == submitted_verdict) and (reread.generated_at > call_start_timestamp)`.
   Both conditions required — neither alone is sufficient.
3. On `success: false`, return a structured `error_code` distinguishing
   "write did not happen" from "write happened, signal was noise" (spec
   Acceptance Scenario 4) — do not collapse both into one generic failure
   code.

**Files**: `src/specify_cli/orchestrator_api/commands.py` (part of T017's diff — same subtask boundary is a design choice, not a hard split; keep the two logically separate in the implementation for reviewability).

**Validation**: T019-T021 below all pass once this lands.

## Subtask T019: SC-005(a) — swallowed-exception-but-written test

**Purpose**: The SK-93 regression guard.

**Steps**:
1. Mock the underlying write call to RAISE, but have the artifact
   genuinely written (fresh `generated_at`, matching verdict) BEFORE the
   mocked raise fires.
2. Assert `record-analysis` still returns `success: true`.

**Files**: part of `test_check_prerequisites_record_analysis.py` (already scaffolded RED in T015; this subtask is the GREEN-confirmation pass).

**Validation**: test passes.

## Subtask T020: SC-005(b) — hang-but-written test

**Purpose**: The MAJORITY documented SK-93 failure shape (3 of 4 first-hand
occurrences) — a silent hang, not a clean bad-exit-code return.

**Steps**:
1. Mock the underlying write call to block indefinitely (e.g. a
   `threading.Event` that is never set).
2. Assert `record-analysis` still RETURNS within its enforced time bound —
   this is the one test in this WP that actually proves the timeout
   mechanism works, not just that the re-read logic is correct; use a real
   wall-clock assertion (e.g. `time.monotonic()` bracketing the call,
   asserting elapsed time is bounded), not just "eventually returned."
3. Assert `success` is determined by the re-read, not by whether the
   mocked call ever "returned."

**Files**: part of `test_check_prerequisites_record_analysis.py`.

**Validation**: test passes, and genuinely exercises the timeout path
(verify by temporarily removing the timeout and confirming the test then
hangs/times out at the pytest level — do this locally during development,
not as a committed test).

## Subtask T021: SC-005(c) — stale-but-coincidentally-matching-verdict test

**Purpose**: The SPEC-VERIFY-001 regression guard — verdict-string
equality alone is never sufficient evidence.

**Steps**:
1. Pre-seed `analysis-report.md` on disk with a verdict EQUAL to the new
   submission's verdict, but a `generated_at` BEFORE the call-start
   timestamp.
2. Mock the underlying write path to FAIL before reaching
   `write_analysis_report` (one of the early-exit branches —
   `mission_record_analysis.py:228-292`: dirty worktree, unresolved
   placement, or empty body).
3. Assert `record-analysis` reports `success: false`.

**Files**: part of `test_check_prerequisites_record_analysis.py`.

**Validation**: test passes.

## Write-Scope / Adjacent Open PRs

`orchestrator_api/commands.py` — same-file overlap with **PR #3826**
(merge-mission area) and with sibling WPs WP03/WP05/WP06/WP08 (all
additive, non-overlapping functions, all mutually independent per
plan.md's parallel-lane design) — this WP is marked `scope: codebase-wide`
for the same reason WP03 is (see WP03's Write-Scope note for the full
mechanism explanation; not repeated here). **PR #3826 merged into `main`
on 2026-09-02**; this mission's branch has not yet rebased onto that
merge as of this tasks phase, so `commands.py`'s merge-mission area on
`main` already carries #3826's changes. Sequence the MERGE of this WP
against WP03/05/06/08 explicitly, and re-verify `commands.py` against
`main`'s current state (not the now-stale #3826-still-open assumption).

## Definition of Done

- [ ] RED commit: all `test_check_prerequisites_record_analysis.py` cases
      fail on `planning_base_branch`.
- [ ] `pytestmark = [pytest.mark.integration, pytest.mark.git_repo]` on the new test file.
- [ ] `check-prerequisites` implemented, no `--policy` required, field-parity
      with the host CLI's `--json --include-tasks` output confirmed.
- [ ] `record-analysis` implemented: call-start timestamp, dossier-sync
      bypass/timeout (option a or b, documented which was chosen and why),
      re-read+correlate success determination.
- [ ] All three SC-005 sub-tests (a/b/c) green, each testing a genuinely
      distinct code path (not three copies of the same assertion).
- [ ] Negative-path additions to `test_commands_fail_closed.py`/
      `test_typed_error_fail_closed.py` (missing `--policy`, nonexistent
      mission, malformed input).
- [ ] `mypy --strict` / `ruff check` clean.
- [ ] `grep` confirms zero `spec-kitty-events`/`spec-kitty-tracker` reference introduced.

Run: `spec-kitty agent action implement WP04 --agent <name>`

## Risks

- **Fake timeout**: a `try/except TimeoutError` wrapped around a call that
  never actually raises `TimeoutError` on its own is a NO-OP timeout — T020
  must exercise a REAL hang to catch this; do not let a mocked "hang" that
  secretly returns quickly slip through as a passing test.
- **Verdict-only shortcut**: the single most tempting shortcut in this WP
  is checking `verdict == submitted` alone — T021 exists specifically to
  catch an implementer who takes it. Do not weaken T021 to make an
  incomplete implementation pass.
- **Same-file merge collision** — see Write-Scope note.

## Reviewer Guidance

- This WP is the highest-risk verb WP in the mission after WP02/WP08 (per
  plan.md — NFR-004/SK-93 is the mission's named highest-risk correctness
  requirement). Read T019-T021's tests FIRST and confirm each is a
  genuinely distinct scenario before reading the implementation.
- Confirm the timeout mechanism (if option (b) chosen) is a real enforced
  bound, not a decorative `try/except` — ask for the local "remove the
  timeout, watch the test hang" verification the implementer should have
  done during development.
- Confirm `check-prerequisites` never performs analysis reasoning itself
  (C-002) — it assembles context only.
