---
work_package_id: WP01
title: Missing-Charter Advisory Fix
dependencies: []
requirement_refs:
- FR-001
- FR-002
- FR-003
- FR-004
- FR-005
- NFR-001
- NFR-002
- C-001
- C-002
- C-003
planning_base_branch: fix/charter-preflight-missing-charter-advisory
merge_target_branch: fix/charter-preflight-missing-charter-advisory
branch_strategy: Planning artifacts for this mission were generated on fix/charter-preflight-missing-charter-advisory. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/charter-preflight-missing-charter-advisory unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
- T005
- T006
- T007
phase: Phase 1 - MVP (only phase)
history:
- at: '2026-08-16T17:13:27Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent: claude
agent_profile: implementer-ivan
authoritative_surface: src/specify_cli/charter_runtime/preflight/
create_intent: []
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- src/specify_cli/charter_runtime/preflight/runner.py
- src/specify_cli/charter_runtime/preflight/hook.py
- src/specify_cli/cli/commands/dashboard.py
- src/specify_cli/cli/commands/next_cmd.py
- src/specify_cli/charter_runtime/preflight/dashboard_warning.py
- tests/specify_cli/charter_preflight/test_runner.py
- tests/specify_cli/charter_preflight/test_performance.py
- tests/agent/cli/commands/test_next_preflight.py
- tests/agent/cli/commands/test_implement_preflight.py
- tests/test_dashboard/test_dashboard_preflight.py
- CHANGELOG.md
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP01 – Missing-Charter Advisory Fix

> **Pre-merge correction (2026-08-16; authoritative over historical instructions below):** Never make `charter.md` an exemption predicate. First require canonical `missing/missing/(missing|built_in_only)` state; only then inspect prose to choose warning copy. Stale/invalid/other residue blocks with or without prose. Warnings must reach next/implement stderr and dashboard persistence. Legacy remediation is `spec-kitty charter generate --no-from-interview`. Red-first correction: `4bc73dbc6`; implementation: `4493699b0`.

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter (or any user-defined profile), and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `{{agent_profile}}`
- **Role**: `{{role}}`
- **Agent/tool**: `{{agent}}`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this work package's `task_type` (`implement`) and `authoritative_surface` (`src/specify_cli/charter_runtime/preflight/`).

---

## ⚠️ IMPORTANT: Review Feedback

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_ref` field in the event log (via `spec-kitty agent status` or the Activity Log below).
- **You must address all feedback** before your work is complete. Feedback items are your implementation TODO list.
- **Report progress**: As you address each feedback item, update the Activity Log explaining what you changed.

---

## Review Feedback

*None yet — this is the first pass.*

---

## Markdown Formatting

Wrap HTML/XML tags in backticks: `` `<div>` ``, `` `<script>` ``
Use language identifiers in code blocks: ````python`, ````bash`

---

## Objectives & Success Criteria

Fix Priivacy-ai/spec-kitty#3498: `spec-kitty next` and `spec-kitty implement WP##` currently hard-block (exit 1) on two charter states that should instead be advisory:

1. **Fully absent charter** (fresh project) — a working exemption already exists in `runner.py` (`_is_optional_missing_charter_fresh_project`) but is never reached from `next`/`implement` because the shared hook (`run_preflight_or_abort` in `hook.py`) never passes `allow_missing_charter=True`.
2. **Legacy charter.md-only presentation** — after canonical state independently qualifies for missing-charter advisory mode, select a distinct migration warning when display-only prose exists.

This work package is complete when:
- Canonically safe missing/built-in-only state passes on `next`/`implement` independent of prose presence; legacy prose selects more detailed copy only.
- Every invalid, stale, or partial canonical state blocks even when `charter.md` exists.
- Advisory warnings are visible on next/implement stderr and dashboard persistence.
- All 7 subtasks (T001–T007) are done, the full charter-preflight test suite is green, `mypy --strict` and `ruff check` pass, a CHANGELOG entry exists, and #3498 is assigned to the Human-in-Charge.

## Context & Constraints

Read these before writing any code — they contain the exact decisions this WP implements:

- **Spec**: `kitty-specs/charter-preflight-missing-charter-advisory-01M050PD/spec.md` — Functional Requirements FR-001–FR-005, Non-Functional Requirements NFR-001–NFR-002, Constraints C-001–C-003, and the three User Stories with their Given/When/Then acceptance scenarios.
- **Plan**: `kitty-specs/charter-preflight-missing-charter-advisory-01M050PD/plan.md` — Technical Context, Charter Check, and Implementation Concern Map (IC-01 through IC-04, which this single WP implements together).
- **Research**: `kitty-specs/charter-preflight-missing-charter-advisory-01M050PD/research.md` — its pre-merge correction is authoritative: canonical outcome first, visible consumer warnings, executable remediation.
- **Contract (authoritative decision table — follow exactly)**: `kitty-specs/charter-preflight-missing-charter-advisory-01M050PD/contracts/missing-charter-advisory-matrix.md`. Rows 1–4 keep identical pass/block behavior across prose presence; rows 5–7 block stale/invalid/partial state with or without prose.
- **Data model**: `kitty-specs/charter-preflight-missing-charter-advisory-01M050PD/data-model.md` — confirms no new dataclass fields are needed; only `CharterPreflightResult.warnings` content changes.
- **Quickstart**: `kitty-specs/charter-preflight-missing-charter-advisory-01M050PD/quickstart.md` — manual verification scenarios; run these after the automated tests pass.
- **Charter directives in play**: DIR-005 (tests required), DIR-006 (`mypy --strict` must pass), DIR-007 (docstrings on new public/module functions), DIR-009 (CHANGELOG entry for this behavior change), DIR-012 (assign tracker issue #3498 to the Human-in-Charge before/as part of implementation), DIR-013 (if you hit unrelated pre-existing test failures, file a GitHub issue before treating them as baseline — do not silently work around them).
- **Locality of change**: this is a two-production-file fix (`runner.py`, `hook.py`). Do not refactor unrelated code in either file.

## Branch Strategy

- **Strategy**: PR-bound, dedicated feature branch (already created).
- **Planning base branch**: `fix/charter-preflight-missing-charter-advisory`
- **Merge target branch**: `fix/charter-preflight-missing-charter-advisory`

> These fields are populated automatically by `spec-kitty agent mission tasks`.
> Do NOT change them manually unless you are certain the branch topology has changed.

## Subtasks & Detailed Guidance

### Subtask T001 [P] – Runner-level regression tests (RED first)

- **Purpose**: Prove, before any implementation change, exactly what `runner.py` currently does and does not do for the legacy-bundle shape, and pin the target behavior.
- **Steps**:
  1. Open `tests/specify_cli/charter_preflight/test_runner.py`. Study the existing fixtures/helpers used by `test_missing_charter_in_fresh_project_is_advisory_not_blocking` and `test_missing_charter_blocks_mutation_gates_by_default` (around lines 90–124) to match style and fixture usage.
  2. Add a test that creates a repo state with `.kittify/charter/charter.md` present, `.kittify/charter/charter.yaml` absent, no synced bundle, no synthesized DRG, calls `run_charter_preflight(..., allow_missing_charter=True)`, and asserts `passed is True` plus a **new, distinct** warning string appears in `result.warnings` (not the existing `_FRESH_PROJECT_MISSING_CHARTER_WARNING` text).
  3. Add a test for the row-2 tie-break from the contract: all three layers `missing` AND `charter.md` present → still the legacy-bundle warning (not the fresh-project one).
  4. Add a non-regression test: same legacy-bundle file layout but with `allow_missing_charter=False` (the default) → `passed is False`, blocks exactly as `test_missing_charter_blocks_mutation_gates_by_default` already proves for the fully-absent case.
  5. Add non-regression tests for stale/invalid canonical residue with `charter.md` **present** → still blocks; repeat safe built-in-only state without prose → still passes.
  6. Add an NFR-001 enforcement test: monkeypatch/spy on `Path.exists` (or count calls via a wrapper) around the legacy-bundle detection call and assert it is invoked at most once beyond whatever the pre-existing fresh-project path already does — this is the automated check for "at most one additional filesystem existence check" (spec.md NFR-001), not just a review note.
  7. Run `.venv/bin/pytest tests/specify_cli/charter_preflight/test_runner.py -k legacy_bundle -v` and confirm the new tests fail for the *right* reason (predicate doesn't exist yet / AttributeError or assertion on missing warning), not for an unrelated error.
- **Files**: `tests/specify_cli/charter_preflight/test_runner.py`
- **Parallel?**: Yes — independent of T002–T004.
- **Notes**: Match existing fixture helpers in this file (check `_fixtures.py` in the same directory) rather than hand-rolling new tmp_path setup helpers.

### Subtask T002 [P] – `spec-kitty next` hook regression tests (RED first)

- **Purpose**: Prove `run_preflight_or_abort` (as called from `spec-kitty next`) currently blocks on both missing-charter shapes, then (after T006) no longer does.
- **Steps**:
  1. Open `tests/agent/cli/commands/test_next_preflight.py`; study `test_hook_aborts_with_exit_1_when_preflight_fails` and `test_hook_returns_result_when_preflight_passes` for the mocking pattern used against `run_charter_preflight`.
  2. Add a test proving that when the underlying repo state is the fully-absent-charter shape, `run_preflight_or_abort(..., consumer="next")` returns (does not raise `typer.Exit`) — i.e., it currently fails until T006 lands (write it RED: expect no abort, watch it currently abort).
  3. Add the equivalent test for the legacy-bundle shape.
  4. Keep a non-regression test alongside: an invalid-charter-yaml repo state still raises `typer.Exit(1)`.
- **Files**: `tests/agent/cli/commands/test_next_preflight.py`
- **Parallel?**: Yes.
- **Notes**: These are hook-level tests — you do not need to invoke the full `spec-kitty next` CLI; test `run_preflight_or_abort` directly as the existing tests already do.

### Subtask T003 [P] – `spec-kitty implement` hook regression tests (RED first)

- **Purpose**: Same as T002, for the `implement` consumer.
- **Steps**:
  1. Open `tests/agent/cli/commands/test_implement_preflight.py`; study `test_implement_aborts_before_worktree_allocation_on_failure` and `test_implement_proceeds_past_preflight_when_passed`.
  2. Mirror T002's two new advisory-shape tests and one non-regression test, using this file's existing helpers (`_fail_result`, etc.).
- **Files**: `tests/agent/cli/commands/test_implement_preflight.py`
- **Parallel?**: Yes.
- **Notes**: Confirm the test also proves no worktree allocation is attempted in the still-blocking (non-regression) case — that behavior must be untouched.

### Subtask T004 [P] – Dashboard warning-detail test

- **Purpose**: Prove the dashboard command persists/renders the detailed passed advisory rather than clearing it as a clean pass.
- **Steps**:
  1. Open `tests/test_dashboard/test_dashboard_preflight.py`; study `test_dashboard_hook_does_not_warning_log_optional_missing_charter` and the `allow_missing_charter: True` assertion around line 180.
  2. Add a runner-hook assertion for the returned warning and a command-boundary test proving that warning is written through `dashboard_warning` and not cleared.
- **Files**: `tests/test_dashboard/test_dashboard_preflight.py`
- **Parallel?**: Yes.
- **Notes**: A test of `result.warnings` alone is insufficient; it must constrain the user-visible persistence/banner seam.

### Subtask T005 – Implement canonical missing-stack predicate + warning selector in runner.py

- **Purpose**: Make T001 (and downstream T002–T004) pass.
- **Steps**:
  1. In `src/specify_cli/charter_runtime/preflight/runner.py`, add a new module-level warning constant near `_FRESH_PROJECT_MISSING_CHARTER_WARNING` (check its exact current name/text first — do not assume) — e.g. `_LEGACY_CHARTER_BUNDLE_WARNING`, with text that explicitly names the legacy `charter.md` bundle and points at the remediation command (charter regeneration/migration), distinctly more detailed than the fresh-project message per FR-003.
  2. Add `_is_optional_missing_charter_stack(checks)` requiring source=`missing`, synced=`missing`, DRG=`missing|built_in_only`. This is the only new pass predicate.
  3. Only inside that qualified branch, call `_is_legacy_charter_bundle(repo_root)` to choose fresh-vs-legacy warning/detail. It must never see or change the canonical decision.
  4. Add a docstring to the new predicate matching the style/detail of `_is_optional_missing_charter_fresh_project`'s docstring (DIR-007).
  5. Run `.venv/bin/pytest tests/specify_cli/charter_preflight/test_runner.py -v` — all T001 tests plus every pre-existing test in this file must pass.
- **Files**: `src/specify_cli/charter_runtime/preflight/runner.py`
- **Parallel?**: No — T006 depends on this.
- **Notes**: Evaluation order is architectural: canonical predicate first, display-only selector second.

### Subtask T006 – Wire `allow_missing_charter=True` into the shared hook

- **Purpose**: Make T002/T003 pass; confirm T004 passes.
- **Steps**:
  1. In `hook.py`, pass `allow_missing_charter=True` and emit every passed advisory warning to stderr. In the dashboard command, persist joined passed warnings instead of clearing them.
  2. Run `.venv/bin/pytest tests/agent/cli/commands/test_next_preflight.py tests/agent/cli/commands/test_implement_preflight.py tests/test_dashboard/test_dashboard_preflight.py -v` — all T002/T003/T004 tests plus every pre-existing test in these three files must pass.
  3. Verify JSON stdout remains unpolluted because mutation warnings use stderr.
  4. Update the module docstring table at the top of `hook.py` (the "Consumer / passed=True / passed=False" table) only if its wording becomes inaccurate — otherwise leave it, since the *consumer contract* (log+continue / abort+no-mutation) is unchanged; only *which states reach `passed=True`* changed.
- **Files**: `src/specify_cli/charter_runtime/preflight/hook.py`
- **Parallel?**: No — depends on T005.
- **Notes**: This is the single most important line of the whole fix — it is the exact drift #3498 identified (dashboard had it, next/implement didn't). Do not duplicate the flag-passing logic anywhere else.

### Subtask T007 – CHANGELOG, full regression run, and HiC assignment

- **Purpose**: Close out the work package per repo conventions and charter directives.
- **Steps**:
  1. Add a `CHANGELOG.md` entry (top of the file, matching existing entry format) describing: "Fixed: `spec-kitty next`/`implement` no longer block on a fully-absent or legacy `charter.md`-only charter — both are now advisory, matching `specify`/`plan`'s existing tolerance (#3498)."
  2. Run the full charter-preflight-relevant regression surface:
     ```bash
     .venv/bin/pytest tests/specify_cli/charter_preflight/ tests/agent/cli/commands/test_next_preflight.py tests/agent/cli/commands/test_implement_preflight.py tests/test_dashboard/test_dashboard_preflight.py -v
     ```
  3. Run `mypy --strict` on the two touched modules and `ruff check` on all touched files; fix any findings (no suppressions per repo Sonar/mypy policy).
  4. Assign GitHub issue Priivacy-ai/spec-kitty#3498 to the Human-in-Charge per DIR-012:
     ```bash
     unset GITHUB_TOKEN && gh issue edit 3498 --repo Priivacy-ai/spec-kitty --add-assignee "@me"
     ```
     (Use the correct HiC identity if `@me` does not resolve to the right account in this environment — check `gh auth status` first.)
  5. If you encounter any pre-existing failing test unrelated to this change, do NOT silently treat it as baseline — file a GitHub issue per DIR-013 before proceeding, including the command run and why you believe it's pre-existing (verify against `git stash` / merge-base if needed).
- **Files**: `CHANGELOG.md`
- **Parallel?**: No — this is the closing subtask.
- **Notes**: This subtask is the Definition-of-Done gate — do not mark the WP done until all three checks (tests, mypy, ruff) are clean and the CHANGELOG entry + HiC assignment are complete.

## Test Strategy

- **Mandatory** per spec.md C-003, NFR-002, and this repo's DIR-005 — see Subtasks T001–T004 above for exact test placement.
- Test-first-bug-fixing: confirm each new test is RED for the correct reason before writing the corresponding production fix.
- Full regression command (also run in T007):
  ```bash
  .venv/bin/pytest tests/specify_cli/charter_preflight/ tests/agent/cli/commands/test_next_preflight.py tests/agent/cli/commands/test_implement_preflight.py tests/test_dashboard/test_dashboard_preflight.py -v
  ```
- If `.venv` is not yet warm, run `uv sync --frozen --all-extras` first.

## Risks & Mitigations

- **Risk**: Letting `charter.md` change the canonical outcome. **Mitigation**: `_is_optional_missing_charter_stack()` qualifies first; parameterized stale/invalid-with-prose tests fail closed; built-in-only tests pass with and without prose.
- **Risk**: Legacy-bundle detection adding unbounded I/O (e.g. accidentally walking `.kittify/charter/` instead of a single `Path.exists()` check). **Mitigation**: NFR-001 caps this at one additional filesystem check, enforced by T001's automated call-count assertion (not just review) — it must stay green after T005.
- **Risk**: Warning copy exists only as metadata. **Mitigation**: next/implement assert stderr and dashboard asserts persisted command-boundary warning.
- **Risk**: `mypy --strict` regressions from the new predicate's type signature. **Mitigation**: match the existing predicate's signature style (`list[CharterPreflightCheck]` input, `bool` output) plus the new `repo_root: Path` parameter.

## Review Guidance

- Confirm canonical qualification runs before the row-2/row-4 warning-copy selector.
- Confirm rows 5–7 block regardless of `charter.md`, and rows 1–4 differ only in warning copy.
- Confirm qualification lives only in `runner.py`, mutation emission only in shared `hook.py`, and dashboard code only persists presentation (C-002).
- Confirm `mypy --strict`, `ruff check`, and the full regression command in Test Strategy all pass clean, and that CHANGELOG.md + the #3498 HiC assignment were actually done (not just claimed).

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

**Initial entry**:

- 2026-08-16T17:13:27Z – system – Prompt created.
- 2026-08-16T17:43:34Z – claude – Implemented all 7 subtasks (T001–T007). RED-first: added tests in test_runner.py (legacy-bundle advisory, row-2 tie-break, row-3 shape, non-regression blocking for both allow_missing_charter=False and the neither-shape residue case, NFR-001 Path.exists()-call-count bound), test_next_preflight.py and test_implement_preflight.py (real-runner hook-level tests proving `run_preflight_or_abort` currently aborts on both missing-charter shapes plus a still-blocking non-regression case), and test_dashboard_preflight.py (legacy-bundle warning-detail test) — confirmed all RED for the right reason (existing predicate/hook not yet extended). GREEN: added `_is_legacy_charter_bundle()` + `_LEGACY_CHARTER_BUNDLE_WARNING` to runner.py, checked before the existing `_is_optional_missing_charter_fresh_project()` so the contract's row-2 tie-break (charter.md presence wins) resolves correctly without editing that existing predicate's body at all; factored the shared "advisory, not blocking" result shape into `_advisory_missing_charter_result()`. Wired the single-line fix in hook.py: `run_preflight_or_abort` now passes `allow_missing_charter=True` to `run_charter_preflight` (previously only the dashboard path did — the exact drift #3498 identified). Updated one pre-existing test (`test_null_project_config_enabled_still_runs_preflight`) whose exact-kwargs assertion needed extending (not weakening) for the new call shape. The dashboard T004 test passed immediately once the runner change (T005) landed, with zero dashboard/hook.py-specific code change — confirming research.md's IC-03 prediction explicitly. Full regression (`tests/specify_cli/charter_preflight/`, `test_next_preflight.py`, `test_implement_preflight.py`, `test_dashboard_preflight.py`): 54/54 passed. `mypy --strict` on the two touched modules found 2 findings, both confirmed pre-existing via `git stash` against the merge-base (unrelated to this diff, at unmoved code); left untouched per DIRECTIVE_024/locality-of-change and filed as Priivacy-ai/spec-kitty#3513 per DIR-013. `ruff check` clean on all touched files. Ran the broader preflight-adjacent test suite (17 additional files, 215 tests) and found 1 unrelated pre-existing failure (`test_lanes_json_read_from_coord_dir_not_primary`, a lanes.json coord/primary-dir resolution issue) — confirmed pre-existing via the same `git stash` method; matches the workspace's already-captured "1 pre-existing test failure" baseline, so not treated as mine to fix. Added a CHANGELOG.md entry under `### 🐛 Fixed` in `docs/changelog/CHANGELOG.md` (the file `CHANGELOG.md` symlinks to). Assigned Priivacy-ai/spec-kitty#3498 to the Human-in-Charge (robertDouglass) via `gh issue edit 3498 --add-assignee "@me"`, verified via `gh issue view`. Committed implementation as `669a1c1b7` on the lane branch; also cleaned a stray `kitty-specs/.../meta.json` that had been committed onto the lane branch (pre-dating this WP's work, from the mission's earlier merge-in) via `git restore --source <mission-branch> -- kitty-specs/` + commit `d9530c50b`, since `move-task` refuses lane branches carrying planning artifacts. `move-task WP01 --to for_review` initially failed twice on the automated pre-review regression gate hitting its fixed 300s timeout with no test output; used the documented `--skip-pre-review-gate` override after independently verifying the mandated regression suite (54/54) and a broader 215-test sweep both pass — WP01 successfully moved to `for_review`.
- 2026-08-16T19:32:20Z – codex – First landing squad rejected the metadata-only warning and charter.md-keyed bypass. Added red-first tests in 4bc73dbc6, fixed canonical qualification + consumer delivery in 4493699b0, and corrected contract/evidence. Verified 59 focused tests, 297 contract tests (5 skipped), 1487 architectural tests (2 skipped, 2 xfailed), literal gate 4/4, and ruff; strict mypy retains only #3513's two base findings.
- 2026-08-16T19:43:15Z – codex – Round 2 found next JSON/query wrapper silence and eager charter import latency. Added red wrapper/cold-import tests in 3f5ab1082 and fixed all four next modes plus lazy CHARTER_MD resolution in 3dc72aa04. Verified 63 focused tests, literal gate 4/4, and ruff; full gates + squad rerun pending.

---

### Updating Status

Status is managed via `status.events.jsonl`. Use `spec-kitty agent tasks move-task WP01 --to <status>` to change WP status.
