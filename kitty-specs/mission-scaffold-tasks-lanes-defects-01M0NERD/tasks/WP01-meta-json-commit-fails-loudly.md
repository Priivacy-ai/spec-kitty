---
work_package_id: WP01
title: FR-001 - meta.json commit raises on hard git failure (mission_creation.py)
dependencies: []
requirement_refs:
- FR-001
- FR-005
- NFR-001
- NFR-003
- C-001
- C-005
planning_base_branch: fix/mission-scaffold-lanes-defects-3673
merge_target_branch: fix/mission-scaffold-lanes-defects-3673
branch_strategy: Planning artifacts for this mission were generated on fix/mission-scaffold-lanes-defects-3673. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/mission-scaffold-lanes-defects-3673 unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
- T005
- T006
- T007
history: []
agent_profile: implementer-ivan
authoritative_surface: src/specify_cli/core/
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/core/mission_creation.py
- tests/core/test_mission_create_checkout_restore.py
- tests/specify_cli/core/test_feature_creation.py
- tests/core/test_mission_creation_topology.py
role: implementer
tags: []
tracker_refs: []
---

# WP01 - FR-001: meta.json commit raises on hard git failure

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `implementer-ivan`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this work package's `task_type` and `authoritative_surface`.

---

## Objective

Make the `meta.json` commit inside `create_mission_core` (`src/specify_cli/core/mission_creation.py`)
raise on a hard git failure instead of silently swallowing the exception, at both call sites
(primary mission-type and `documentation` mission-type), while leaving the legitimate
nothing-to-commit no-op case unchanged. This closes FR-001 / SC-001 / NFR-003.

## Context

**No dependency on WP02.** WP01 and WP02 are independent write scopes (`mission_creation.py`
vs `mission_finalize.py`) with no shared production code and no ordering requirement between
them — see `tasks.md`'s Dependencies section for the explicit statement. Either WP may be
implemented first, second, or in parallel.

**PR shape**: this WP lands as part of the single mission PR (plan.md §12 — one PR, the diff
fits in one sitting). Do not open a separate PR for this WP.

**Exact seam** (plan.md §1, verified against this checkout's HEAD on
`fix/mission-scaffold-lanes-defects-3673`, 2026-08-22 — re-verify the line numbers yourself
before editing, they may have drifted):

| Call site | Lines | Change |
|---|---|---|
| Primary mission-type | `write_meta(feature_dir, meta)` at **766**; `with contextlib.suppress(Exception):` at **767**; `_commit_feature_file(...)` at **768** | Remove the `contextlib.suppress(Exception)` wrapper so a hard git failure raises. |
| `documentation` mission-type (Acceptance Scenario 4) | `with contextlib.suppress(Exception):` at **792**; `_commit_feature_file(...)` at **793** | Identical fix, same pattern, second call site — the fix must not be partial to the primary branch. |

`_commit_feature_file`'s own docstring already documents "raises on hard failures and silently
succeeds when there is nothing to commit" — you are not changing that contract, only removing
the code that discards the raise. The existing rollback machinery
(`_restore_git_state_after_failed_create`) already handles the cleanup on this path; **do not
build new rollback machinery.**

**No new CLI surface (C-001/FR-005, binding).** No new command, subcommand, flag, or disguised
escape hatch anywhere in `src/specify_cli/`. This WP's diff should be a pure removal of the
`suppress` wrapper at the two call sites (plus tests) — if your diff ends up touching CLI
command registration at all, that is scope drift, stop and reconsider.

**C-005 baseline-red protocol (plan.md §9) — run this BEFORE your first implementation
change, not after:**
1. Run the specific test file/test you are about to extend against the current branch:
   `.venv/bin/python -m pytest <path::test_name> -q`.
2. Run the **same** test against the merge-base / `upstream/main` (a `PYTHONPATH=<worktree>/src`
   swap against a clean checkout of the merge-base commit, or an equivalent `git
   worktree`/`git stash` comparison — not a bare re-read of the ledger).
3. Classify: red-on-branch+green-on-base = your regression (must not ship); red-on-both =
   pre-existing, out of scope, note it in your validation summary; only failures red on your
   branch and green on the base are yours to fold in.
4. Record the classification in your WP validation notes so a reviewer can confirm it.

Full policy: `docs/development/testing/testing-flakiness.md#test-run-baseline-red-gotcha`
and `CLAUDE.md`'s "Test-run baseline-red gotcha" section.

**No campsite-clean step needed for this WP** — plan.md §10 already checked
`mission_creation.py`'s two call sites (trivial, single `with` + call) and found nothing near
the complexity ceiling.

### Subtask T001: Establish the C-005 baseline-red protocol for this WP's test surface

**Purpose**: Confirm, before writing any test or implementation change, which of this WP's
target test files are already red on the merge-base, so nothing pre-existing gets misattributed
to this WP later.

**Steps**:
1. Identify the merge-base commit for `fix/mission-scaffold-lanes-defects-3673` against
   `upstream/main` (or `origin/main` if that is this checkout's remote name — verify with
   `git remote -v`).
2. Run `.venv/bin/python -m pytest tests/core/test_mission_create_checkout_restore.py -q` and
   `.venv/bin/python -m pytest tests/specify_cli/core/test_feature_creation.py -q` on the
   current branch; record pass/fail counts.
3. Run the same two files against the merge-base commit (via `PYTHONPATH=<worktree>/src`
   against a clean merge-base checkout, or an equivalent worktree/stash comparison).
4. Classify per the C-005 protocol above. Note the result in your WP validation summary
   (which tests, if any, are pre-existing red and therefore out of scope).

**Files**: none changed — this is a read-only verification step.
**Validation**: a written classification (in your final report / validation notes) for every
test in the two files, not just a pass/fail count.

### Subtask T002: Red-first test — FR-001 primary call site raises on hard commit failure

**Purpose**: Prove the fix by writing a test that fails against the current (pre-fix) code and
passes once T005's fix lands.

**Steps**:
1. In `tests/core/test_mission_create_checkout_restore.py`, add a test that forces
   `_commit_feature_file` to raise during `create_mission_core`'s primary-mission-type `meta.json`
   commit (line 766-768) — e.g. monkeypatch `_commit_feature_file` to raise a `RuntimeError`/
   `subprocess.CalledProcessError` from within the code path currently wrapped by
   `contextlib.suppress(Exception)` at line 767, or simulate a locked `.git/index` / failing
   pre-commit hook if the file's existing fixture conventions support that more directly.
2. Assert: (a) `create_mission_core` (or the `specify` CLI invocation, whichever this file's
   existing tests drive) raises / exits non-zero; (b) the underlying git error text is present
   in the raised exception or CLI output — not swallowed into a generic message; (c) confirm
   this test is RED against the current (pre-T005) code before moving on.
3. Add the NFR-003 rollback-correctness assertion in the same or a sibling test: snapshot
   branch/HEAD-commit/index-tree before the forced failure, force it, snapshot again, assert
   all three are identical (this file's documented purpose is exactly this kind of
   before/after snapshot comparison — follow its existing pattern).

**Files**: `tests/core/test_mission_create_checkout_restore.py` (extend, ~40-60 new lines).
**Validation**: new test(s) fail against current code; will pass once T005 lands.

### Subtask T003: Red-first test — FR-001 no-op case is unaffected (Acceptance Scenario 3)

**Purpose**: Prove the fix distinguishes "nothing to commit" (still silent, unchanged) from
"hard failure" (now raises) — this is Acceptance Scenario 3 and must not regress.

**Steps**:
1. In `tests/specify_cli/core/test_feature_creation.py` (this file already mocks
   `_commit_feature_file` broadly across ~10 tests), add or extend a test asserting that when
   there is genuinely nothing new to commit for `meta.json`, `specify`/`create_mission_core`
   still succeeds exactly as today, following the file's existing mocking pattern.
2. This test should already pass today (it is asserting unchanged behavior) — run it before
   and after T005's change and confirm it stays green both times; it exists to catch a
   regression, not to be red-first in the usual sense.

**Files**: `tests/specify_cli/core/test_feature_creation.py` (extend, ~20-30 new lines).
**Validation**: passes both before and after T005.

### Subtask T004: Red-first test — FR-001 documentation-branch call site (Acceptance Scenario 4)

**Purpose**: Prove the fix is not partial to the primary mission-type branch — the second call
site (line 792-793) gets identical raise-and-rollback behavior.

**Steps**:
1. First, check whether `tests/core/test_mission_creation_topology.py` already carries
   documentation-mission-type fixtures (per plan.md §11's guidance to "verify at WP-start which
   file already has documentation-mission fixtures before creating a new one"). If it does, add
   your test there; if not, add it to `tests/specify_cli/core/test_feature_creation.py` next to
   T002/T003's tests, using the same forced-failure technique as T002 but targeting the
   `mission == "documentation"` branch (lines 792-793).
2. Assert the identical raise-and-rollback behavior as T002, at this second call site.
3. Confirm RED against current (pre-T005) code.

**Files**: `tests/core/test_mission_creation_topology.py` OR
`tests/specify_cli/core/test_feature_creation.py` (whichever already has the doc-mission
fixtures — state which one you used and why in your validation notes).
**Validation**: red before T005, green after.

### Subtask T005: Implement the fix — remove the `contextlib.suppress(Exception)` wrapper

**Purpose**: The actual production-code fix for FR-001.

**Steps**:
1. In `src/specify_cli/core/mission_creation.py`, remove the `with
   contextlib.suppress(Exception):` wrapper at line **767** so the `_commit_feature_file(...)`
   call at line **768** raises on a hard failure instead of being swallowed. Re-verify the exact
   line numbers against your own checkout first — plan.md's citations were verified 2026-08-22
   and may have drifted by the time you implement.
2. Apply the identical fix at the second call site: remove the `with
   contextlib.suppress(Exception):` wrapper at line **792** so `_commit_feature_file(...)` at
   line **793** also raises.
3. Do not touch anything else in this file. Do not add a new parameter, flag, or recovery path
   — this is strictly "let the existing raise propagate" (C-001, binding).
4. Ensure `_restore_git_state_after_failed_create`'s existing rollback still fires correctly on
   this newly-surfaced raise (it should — it is presumably already the caller's exception
   handler for `create_mission_core`'s other raising paths; confirm this by reading its call
   site, do not assume).

**Files**: `src/specify_cli/core/mission_creation.py` (2 lines removed / restructured at each
of 2 call sites — a small diff).
**Validation**: T002 and T004's tests now pass; T003 still passes; NFR-001's JSON assertion
(T006) passes.

### Subtask T006: Verify/extend NFR-001 JSON error payload assertion (Acceptance Scenario 2)

**Purpose**: Confirm the `--json` error payload names the failed step (`meta.json commit`) and
the underlying git error text, so a calling agent can distinguish this failure from any other
`specify` failure without parsing prose.

**Steps**:
1. Check whether T002's test (or an existing `--json`-mode test in
   `tests/specify_cli/core/test_feature_creation.py` / `tests/core/test_mission_create_checkout_restore.py`)
   already covers the `--json` invocation path. If not, add a sibling test that invokes the
   same forced-failure fixture with `--json` and asserts the JSON payload identifies the failed
   step and surfaces the underlying git error text (not a generic "something went wrong").
2. This is the same failure path as T002 — you are asserting the JSON-mode shape of the same
   exception, not a new code path.

**Files**: extends whichever file T002 used.
**Validation**: JSON payload assertion passes.

### Subtask T007: Final validation pass

**Purpose**: Confirm the WP is done — tests green, no regressions, no scope drift.

**Steps**:
1. Run the full targeted test surface for this WP:
   `.venv/bin/python -m pytest tests/core/test_mission_create_checkout_restore.py tests/specify_cli/core/test_feature_creation.py tests/core/test_mission_creation_topology.py -q`
   and confirm all pass (or, for any pre-existing red identified in T001, confirm it is still
   the same pre-existing red — not newly introduced or newly fixed).
2. Re-run the C-005 classification from T001 one more time post-implementation and record any
   change.
3. Self-check `ruff check` and `mypy --strict` cleanliness on
   `src/specify_cli/core/mission_creation.py` locally (CI's mypy gate is advisory-only per
   plan.md §8, but the charter still expects local discipline).
4. Run the fast SC-005 grep pass (plan.md §4's secondary mechanism) against your own diff:
   `git diff <merge-base>...HEAD -- src/specify_cli/ | grep -E '^\+.*\.(command|add_typer)\('`
   — expect zero hits for this WP's diff. Note: the **authoritative** SC-005 verification (the
   `registered_commands`/`registered_groups` walk) is WP02's responsibility per plan.md §4 and
   this mission's tasks.md — do not duplicate it here, this is only a fast local self-check.
5. CI's `mission-loader-coverage` job will run on this WP's diff — it is triggered via the
   `core_misc` path filter (`src/specify_cli/core/**`), which `mission_creation.py` matches,
   even though this WP adds no code under `src/specify_cli/mission_loader` (plan.md §8).
   Confirm no import-time side effect on `src/specify_cli/mission_loader` from this WP's
   change (expected: none, since the diff is a pure `contextlib.suppress` removal) and record
   that the >=90% coverage floor is expected to hold trivially — state this explicitly rather
   than silently assuming it, per plan.md §8's own instruction.
6. Record a one-paragraph validation summary: tests run, C-005 classification, ruff/mypy
   status, SC-005 fast-pass result, and the `mission-loader-coverage` confirmation from step 5.

**Files**: none (validation only).
**Validation**: all of the above pass or are explained.

## Definition of Done

- `contextlib.suppress(Exception)` removed at both `mission_creation.py:767` and `:792` (line
  numbers as re-verified at implementation time).
- T002/T004's forced-failure tests are green; T003's no-op test remains green; NFR-003's
  rollback-snapshot assertion passes; NFR-001's JSON payload assertion passes.
- No new CLI command, subcommand, or flag introduced anywhere.
- C-005 baseline-red classification recorded for every test in this WP's target files.
- CI's `mission-loader-coverage` job (triggered via the `core_misc` path filter on this WP's
  own file) is confirmed to hold trivially — no import-time side effect on
  `src/specify_cli/mission_loader` — with the result recorded in the validation summary, per
  plan.md §8.
- Each subtask's completion is recorded via
  `spec-kitty agent tasks mark-status <Txxx> --status done` (event-sourced; not a checkbox).

## Risks

- **Rollback machinery assumption**: this WP assumes `_restore_git_state_after_failed_create`
  already fires correctly on the newly-surfaced raise. If it does not (e.g. the raise now
  propagates through a code path that never reaches the existing handler), that is a real
  finding — do not silently patch around it by adding new rollback logic; flag it and confirm
  the correct fix stays within FR-001's scope (letting the existing raise propagate) rather than
  inventing a second rollback path.
- **Test file selection for T004**: plan.md flags explicit uncertainty about whether
  `test_mission_creation_topology.py` already has documentation-mission fixtures. Verify before
  writing, and say which file you used.

## Reviewer Guidance

Focus on: (1) the diff is exactly the two `contextlib.suppress` removals, nothing else in
`mission_creation.py` changed; (2) T002/T004 genuinely reproduce a hard git failure (not a
weaker condition that happens to raise for an unrelated reason); (3) the C-005 classification
is honestly reported, not silently assumed clean; (4) no new CLI surface anywhere in the diff.

Implementation command: `spec-kitty agent action implement WP01 --agent claude`
