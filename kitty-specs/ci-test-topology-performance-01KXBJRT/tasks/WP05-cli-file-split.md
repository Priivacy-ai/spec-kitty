---
work_package_id: WP05
title: fast-tests-cli file split
dependencies: []
requirement_refs:
- FR-005
tracker_refs: []
planning_base_branch: feat/ci-test-topology-performance
merge_target_branch: feat/ci-test-topology-performance
branch_strategy: Planning artifacts for this mission were generated on feat/ci-test-topology-performance. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/ci-test-topology-performance unless the human explicitly redirects the landing branch.
subtasks:
- T021
phase: Phase 2 - Topology
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "1250658"
shell_pid_created_at: "1783883705.3"
history:
- at: '2026-07-12T17:43:44Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: tests/specify_cli/cli/commands/charter/test_charter_activate_commands
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- tests/specify_cli/cli/commands/charter/test_charter_activate_commands*.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP05 – fast-tests-cli file split

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter (or any user-defined profile), and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this work package's `task_type` and `authoritative_surface`.

---

## ⚠️ IMPORTANT: Review Feedback

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_ref` field in the event log (via `spec-kitty agent status` or the Activity Log below).
- **You must address all feedback** before your work is complete. Feedback items are your implementation TODO list.
- **Report progress**: As you address each feedback item, update the Activity Log explaining what you changed.

---

## Review Feedback

*[If this WP was returned from review, the reviewer feedback reference appears in the Activity Log below or in the status event log.]*

---

## Markdown Formatting

Wrap HTML/XML tags in backticks: `` `<div>` ``, `` `<script>` ``
Use language identifiers in code blocks: ````python`,````bash`

---

## Objectives & Success Criteria

Break the `fast-tests-cli` job's single-worker tail (FR-005). `--dist loadfile` pins every test in a file to one xdist worker, so the heaviest file in `tests/specify_cli/cli/` caps the job's wall-clock floor regardless of how many other workers are idle. The offender is `tests/specify_cli/cli/commands/charter/test_charter_activate_commands.py` — 14 subprocess-driven CLI tests across two classes (`TestActivateCommand`, `TestCascadeOutputAbsence`) that together pin ~150s of the run's tail. Split this one file into balanced sibling files so `loadfile` can fan them across workers.

Done when:
- `test_charter_activate_commands.py`'s 14 tests are redistributed across 2–3 sibling files with no single file left dominating the job's tail.
- Collection-equivalence holds: the exact same set of test node-ids (module-qualified names may change, but the underlying test *identities* — same fixtures, same assertions, same markers — must all still be collected and none duplicated) is proven before/after via a diffed `pytest --collect-only` run, per the stability ratchet (see `CLAUDE.md` "Local parallel test run" section and the project's collection-equivalence discipline already used for prior `PENDING-CI: T0xx flip` comments in `ci-quality.yml`).
- No `ci-quality.yml` edit is required — `fast-tests-cli`'s command (`tests/cli/ tests/specify_cli/cli/ -m "fast and not windows_ci" -n auto --dist loadfile`) already collects the whole `tests/specify_cli/cli/` tree by directory; splitting one file into siblings under the same directory changes nothing about job selection, only distribution.

## Context & Constraints

- Read `kitty-specs/ci-test-topology-performance-01KXBJRT/spec.md` FR-005: *"`fast-tests-cli` MUST no longer serialize its tail on one `--dist loadfile` worker: split/regroup `test_charter_activate_commands.py` so its tests fan out, with collection-equivalence re-verified per the stability ratchet."*
- Read `kitty-specs/ci-test-topology-performance-01KXBJRT/plan.md` IC-04 (per-job parallelization) — this WP is the concrete instance of that concern for `fast-tests-cli`, and is called out there as depending on nothing else (a root WP, per `tasks.md`'s dependency graph: `WP05 (root)`).
- Current file: `tests/specify_cli/cli/commands/charter/test_charter_activate_commands.py` (263 lines, 14 `def test_*` methods across `class TestActivateCommand` (lines 55–206, 11 tests: `test_activate_directive_happy_path`, `test_activate_config_yaml_updated`, `test_activate_unknown_artifact_id_exits_1_without_mutating`, `test_activate_unknown_kind_exits_1`, `test_activate_cascade_flag_accepted`, `test_activate_accepts_options_after_positional_args`, `test_activate_cascade_calls_with_true`, `test_activate_mission_type_kind`, `test_activate_already_active_emits_warning`, `test_activate_no_action_sequence_flag_exists`, `test_activate_output_contains_activated`) and `class TestCascadeOutputAbsence` (lines 206–263, 3 tests: `test_activate_cascade_no_not_yet_implemented`, `test_activate_cascade_no_deferred`, `test_activate_cascade_still_activates`).
- The job that runs this file (`fast-tests-cli`, `.github/workflows/ci-quality.yml` ~L1368) selects by **directory**, not by literal filename: `tests/cli/ tests/specify_cli/cli/ -m "fast and not windows_ci"`. Any new sibling file(s) placed alongside the original under `tests/specify_cli/cli/commands/charter/` are picked up automatically — no workflow edit, no `needs:`/roster change, and this WP therefore has **no dependency on WP06**.
- Every test in this file uses `project_root: Path` (a CLI-invocation fixture that shells out via `CliRunner`/subprocess) — this is why the file is slow and why `loadfile` pins it to one worker; splitting distributes that subprocess cost across workers, it does not reduce the per-test cost.

## Branch Strategy

- **Strategy**: Coordination-topology mission — this WP's changes land on a lane/feature branch and merge back through the mission's coordination branch (`kitty/mission-ci-test-topology-performance-01KXBJRT`) into the mission target branch. Confirm the exact lane assignment via `lanes.json` (materialized by `spec-kitty agent mission tasks-finalize`) at implement time — do not assume a lane id here.
- **Planning base branch**: `feat/ci-test-topology-performance`
- **Merge target branch**: `feat/ci-test-topology-performance`

> These fields are populated automatically by `spec-kitty agent mission tasks`.
> Do NOT change them manually unless you are certain the branch topology has changed.

## Subtasks & Detailed Guidance

### T021 – Split into balanced sibling files + collection-equivalence re-verification

Break this single subtask into explicit sequential steps — do not treat "split the file" as one atomic edit; each step below is independently checkable.

1. **Analyze durations and grouping** (`Purpose`: pick a split that actually balances wall-clock, not just line count).
   - Run `uv run pytest tests/specify_cli/cli/commands/charter/test_charter_activate_commands.py -m "fast and not windows_ci" --durations=0 -q` locally and record each test's individual duration.
   - Group by natural seams first, then rebalance by duration: `TestActivateCommand` (11 tests, the happy-path/error/cascade-flag/positional-args/output-content tests) is the natural first split boundary from `TestCascadeOutputAbsence` (3 tests, the "cascade no" deferral-output tests) — but confirm via the duration data whether `TestActivateCommand` itself needs a second cut (e.g. separate the cascade-related tests `test_activate_cascade_flag_accepted`, `test_activate_cascade_calls_with_true`, `test_activate_mission_type_kind` from the remaining error/happy-path tests) to keep no single sibling file above roughly the mean per-file duration of the other files already in `tests/specify_cli/cli/commands/charter/`.
   - **Files**: read-only in this step; record findings as a short note in this WP's Activity Log or a scratch comment before editing.

2. **Split the file** (`Purpose`: produce 2–3 sibling files with disjoint classes/tests, same shared fixtures).
   - Create sibling files following the naming convention `test_charter_activate_commands_<group>.py` (e.g. `test_charter_activate_commands_core.py` for the happy-path/error tests, `test_charter_activate_commands_cascade.py` for the cascade-flag and cascade-output tests) — pick group names that describe the seam, not `_1`/`_2`.
   - Preserve every shared fixture, import, and helper exactly (module-level `project_root` fixture, any shared constants) — duplicate or extract to a local `conftest.py`/helper module in the same directory if more than one sibling needs it, rather than copy-pasting divergent fixture definitions.
   - Preserve every test's body, name, markers, and docstring verbatim — this is a *file* split, not a rewrite; do not "improve" assertions while moving them (that would confound the collection-equivalence check below with unrelated behavior changes).
   - Delete the original `test_charter_activate_commands.py` once its contents are fully redistributed (do not leave an empty stub file — an empty file with no tests is dead weight, not a passthrough).
   - **Files**: new sibling `test_charter_activate_commands_*.py` files under `tests/specify_cli/cli/commands/charter/`; delete the original.
   - **Parallel?**: Can be done in one pass; no other WP touches this directory.

3. **Re-verify collection-equivalence (the stability ratchet)**.
   - Before deleting the original, capture its collected node-ids: `uv run pytest tests/specify_cli/cli/commands/charter/test_charter_activate_commands.py --collect-only -q -m "fast and not windows_ci" | sort > /tmp/before-nodeids.txt`.
   - After the split, capture the sibling files' collected node-ids: `uv run pytest tests/specify_cli/cli/commands/charter/test_charter_activate_commands_*.py --collect-only -q -m "fast and not windows_ci" | sort > /tmp/after-nodeids.txt`.
   - Diff the two sets **by test identity** (module path will differ; compare the count and the per-test method-name multiset, not raw node-id string equality): `diff <(sed 's#.*::#::#' /tmp/before-nodeids.txt) <(sed 's#.*::#::#' /tmp/after-nodeids.txt)` must be empty (14 tests before, 14 tests after, same class::method names, none dropped, none duplicated).
   - Confirm the wider directory selection used by `fast-tests-cli` (`tests/specify_cli/cli/`) collects the same total count before/after your change (`--collect-only -q -m "fast and not windows_ci" | wc -l`).
   - Record the before/after counts and the diff result in this WP's Activity Log entry — this is the concrete evidence a reviewer checks per the "PENDING-CI" collection-equivalence discipline already used elsewhere in `ci-quality.yml` (see the `T018`/`T019`/`T021`-flip comments in `fast-tests-charter`/`fast-tests-sync`/`fast-tests-cli` for the established pattern this mission's own T021 subtask ID echoes).

4. **Run the split files locally** to confirm they pass standalone and under `-n auto --dist loadfile` (mirroring the real job's flags):
   ```bash
   uv run pytest tests/specify_cli/cli/commands/charter/test_charter_activate_commands_*.py \
     -m "fast and not windows_ci" -q --tb=short -n auto --dist loadfile --durations=25
   ```
   Confirm via `--durations=25` output that no single sibling file now dominates the tail the way the original monolith did.

## Test Strategy

Tests are the deliverable for this WP — the "product" is the rebalanced test-file topology itself, proven by:

- Standalone run of the new sibling files:
  ```bash
  uv run pytest tests/specify_cli/cli/commands/charter/test_charter_activate_commands_*.py -v --tb=short
  ```
- Collection-equivalence diff (must be empty, 14 tests both sides):
  ```bash
  uv run pytest tests/specify_cli/cli/commands/charter/test_charter_activate_commands_*.py --collect-only -q -m "fast and not windows_ci" | wc -l
  ```
- Full `fast-tests-cli` selection, parallel, to confirm no collision/duplication introduced at the directory level:
  ```bash
  uv run pytest tests/cli/ tests/specify_cli/cli/ -m "fast and not windows_ci" -q --tb=short -n auto --dist loadfile --durations=25
  ```
- `ruff check` and `mypy` on every new/changed test file (no suppressions).
- If WP04's `test_workflow_dist_lint.py` has landed by the time this WP runs, re-run it (`uv run pytest tests/architectural/test_workflow_dist_lint.py -q`) to confirm the unchanged `ci-quality.yml` selection still passes GC-4 — this WP makes no workflow edit, so it should be a no-op confirmation, not a new failure.

## Risks & Mitigations

- **Risk**: Splitting by class boundary alone (11 vs 3) may not actually balance wall-clock if the 11-test class itself contains the slowest individual tests. **Mitigation**: base the split on the recorded `--durations=0` data from step 1, not assumed class symmetry — re-cut within `TestActivateCommand` if the duration data shows a skew.
- **Risk**: A naive split accidentally drops a shared module-level fixture or constant used by both classes, causing a collection error in one sibling. **Mitigation**: run `--collect-only` on each sibling file individually (not just combined) before considering the split done.
- **Risk**: Reviewers or CI infra expect the literal filename `test_charter_activate_commands.py` to exist (e.g. a stale reference in docs or another test that imports from it). **Mitigation**: `git grep -n "test_charter_activate_commands"` across the repo before deleting the original file, and update any hit.
- **Risk**: Renaming methods' *module* qualification changes their full node-id, which could break an unrelated allowlist keyed on exact node-ids (e.g. a ratchet/coupling-analysis allowlist per the "content-address ratchet allowlists" pattern used elsewhere in this codebase). **Mitigation**: `git grep -n "test_charter_activate_commands"` also across `tests/architectural/` and any `baselines/`/allowlist files, not just source; update any pinned reference.

## Review Guidance

- Confirm the before/after collection-equivalence evidence (14 tests, same method names, none dropped/duplicated) is present in the Activity Log, not just asserted.
- Confirm no `ci-quality.yml` edit was made — this WP's `owned_files` is scoped to the test files only; if a workflow edit appears necessary, that is a signal the split changed job selection and must be escalated, not silently folded into WP06's surface.
- Confirm test bodies were moved verbatim (diff each moved test against its original to confirm no incidental behavior change rode along with the file split).
- Confirm `--durations=25` evidence shows the tail is actually broken up (no single new sibling file dominating), not just that the file count increased.

## Activity Log

> **CRITICAL**: Activity log entries MUST be in chronological order (oldest first, newest last).

### How to Add Activity Log Entries

**When adding an entry**:

1. Scroll to the bottom of this Activity Log section
2. **APPEND the new entry at the END** (do NOT prepend or insert in middle)
3. Use exact format: `- YYYY-MM-DDTHH:MM:SSZ – agent_id – <action>`
4. Timestamp MUST be current time in UTC (check with `date -u "+%Y-%m-%dT%H:%M:%SZ"`)
5. Agent ID should identify who made the change (claude-sonnet-4-5, codex, etc.)

**Format**:

```
- YYYY-MM-DDTHH:MM:SSZ – <agent_id> – <brief action description>
```

**Why this matters**: The acceptance system reads the LAST activity log entry as the current state. If entries are out of order, acceptance will fail even when the work is complete.

**Initial entry**:

- 2026-07-12T17:43:44Z – system – Prompt created.

---

### Updating Status

Status is managed via `status.events.jsonl`. Use `spec-kitty agent tasks move-task WP05 --to <status>` to change WP status.
- 2026-07-12T18:56:40Z – claude:sonnet:python-pedro:implementer – shell_pid=1150293 – Assigned agent via action command
- 2026-07-12T19:14:19Z – claude:sonnet:python-pedro:implementer – shell_pid=1150293 – Ready: collection parity 2206/2781 wide-dir (before=after), 14/14 charter-subdir method-name diff empty, ruff 0, tests green (14 passed, split run 55.64s vs monolith 72.18s)
- 2026-07-12T19:15:07Z – claude:opus:reviewer-renata:reviewer – shell_pid=1250658 – Started review via action command
- 2026-07-12T19:20:13Z – user – shell_pid=1250658 – Review passed: collection-equivalence verified 14->14, ruff clean, monolith removed
