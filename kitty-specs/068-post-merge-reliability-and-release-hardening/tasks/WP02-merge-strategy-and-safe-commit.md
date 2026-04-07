---
work_package_id: WP02
title: Merge Strategy And Status-Events Safe Commit
dependencies:
- WP01
requirement_refs:
- FR-005
- FR-006
- FR-007
- FR-008
- FR-009
- FR-019
- FR-020
- NFR-003
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning/base branch is main. Final merge target is main. Execution worktree is allocated by spec-kitty implement WP02 and resolved from lanes.json. WP02 depends on WP01 (run_check import); the lane planner will sequence them in the same lane or order their merges.
subtasks:
- T008
- T009
- T010
- T011
- T012
- T013
- T014
history:
- at: '2026-04-07T08:46:34Z'
  actor: claude
  action: created
authoritative_surface: src/specify_cli/cli/commands/merge.py
execution_mode: code_change
mission_number: '068'
mission_slug: 068-post-merge-reliability-and-release-hardening
owned_files:
- src/specify_cli/cli/commands/merge.py
- src/specify_cli/lanes/merge.py
- src/specify_cli/merge/config.py
- .kittify/config.yaml
- tests/cli/commands/test_merge_strategy.py
- tests/cli/commands/test_merge_status_commit.py
priority: P1
status: planned
---

# WP02 — Merge Strategy And Status-Events Safe Commit

## Objective

Wire `--strategy` end-to-end through `spec-kitty merge` so it stops being silently discarded (#456). Default to **squash** for the mission→target step, preserve **merge-commit** semantics for the lane→mission step. Add a push-error parser that emits a remediation hint when a push is rejected by linear-history protection. Insert the `safe_commit` call that fixes the FR-019 status-events loss bug (#416 known residual gap, the root cause of mission 067's lost done-events). Wire the WP01 stale-assertion analyzer call into the merge runner via direct library import.

## Context

This is the largest single chain of edits in the mission. Six of the seven subtasks land in `_run_lane_based_merge` or its immediate neighbors. WP02 also owns the new `src/specify_cli/merge/config.py` for the `MergeConfig` accessor, the `.kittify/config.yaml` schema update, and the FR-019/FR-020 regression test.

**Critical sequencing within the WP**:
1. T008 (config types) — pure dataclasses, lands first
2. T009 (CLI flag wiring) — needs T008
3. T010 (lower-level lane merge) — needs T009 to know what value to read
4. T011 (push-error parser) — independent of T009/T010 but lives in the same file
5. T012 (safe_commit insertion) — independent code, but lands after T009..T011 to avoid merge.py conflicts
6. T013 (run_check call) — depends on WP01 having landed; can be the very last edit
7. T014 (tests) — landed after the production code

**Key spec references**:
- FR-005: `--strategy` flag flows end-to-end from CLI to `_run_lane_based_merge`
- FR-006: default to `squash` for mission→target
- FR-007: lane→mission keeps merge-commit semantics
- FR-008: `.kittify/config.yaml` `merge.strategy` key honored
- FR-009: parse push errors with the locked token list; fail-open on unknown
- FR-019: insert `safe_commit` after the mark-done loop and before worktree-removal
- FR-020: regression test asserting `git show HEAD:kitty-specs/<mission>/status.events.jsonl` contains `to_lane: done` for every WP after the merge command returns
- C-001: squash default is non-negotiable
- C-002: NO GitHub API calls; reactive parsing only
- NFR-003: 100% success against `require_linear_history = true` on the integration test matrix

**Key planning references**:
- `contracts/merge_strategy.md` for full signatures, token list, insertion point
- `data-model.md` for `MergeStrategy` enum, `MergeConfig` schema, status event shape
- `research.md` "Current-Main Analysis" for the `_run_lane_based_merge` line numbers (may have shifted since the spec was written — read the current file at WP02 start time)

## Branch Strategy

- **Planning/base branch**: `main`
- **Final merge target**: `main`
- **Execution worktree**: allocated by `spec-kitty implement WP02` and resolved from `lanes.json`. The lane planner will sequence WP02 after WP01 because of the dependency.

To start work:
```bash
spec-kitty implement WP02
```

If the command warns that WP01 is not yet done, wait or coordinate with the WP01 implementer.

## Subtasks

### T008 — `MergeStrategy` enum + `MergeConfig` + `load_merge_config` + `.kittify/config.yaml` schema

**Purpose**: Establish the type system for merge strategies and the project-level config accessor. This is the dependency that T009/T010 read from.

**Files**:
- New: `src/specify_cli/merge/config.py`
- Modified: `.kittify/config.yaml` (add `merge.strategy` schema example)

**Steps**:
1. Create `src/specify_cli/merge/config.py` with:
   - `MergeStrategy` Enum with values `MERGE = "merge"`, `SQUASH = "squash"`, `REBASE = "rebase"` (str-Enum so typer can auto-bind)
   - `MergeConfig` dataclass with `strategy: MergeStrategy | None = None`
   - `load_merge_config(repo_root: Path) -> MergeConfig` reading `.kittify/config.yaml` via the existing `ruamel.yaml` infrastructure
2. **Validation**: if `merge.strategy` is present in config but not one of the three allowed values, raise a startup `ConfigError` with a clear message. NO silent fallback.
3. Update `.kittify/config.yaml` in this repo to include the schema example:
   ```yaml
   # Merge strategy for spec-kitty merge command (mission → target step).
   # One of: merge | squash | rebase. Default: squash.
   # Lane → mission merges always use merge commits regardless of this setting.
   merge:
     strategy: squash
   ```
4. Re-export `MergeStrategy`, `MergeConfig`, `load_merge_config` from `src/specify_cli/merge/__init__.py`

**Validation**: `python -c "from specify_cli.merge.config import MergeStrategy, MergeConfig, load_merge_config"` succeeds. `load_merge_config(repo_root)` returns the populated config from `.kittify/config.yaml`.

### T009 — Wire `--strategy` CLI flag through to `_run_lane_based_merge`

**Purpose**: Stop discarding the `--strategy` flag. Resolve from CLI flag → config key → squash default. Pass the resolved strategy down into the function that runs the merge.

**Files**:
- Modified: `src/specify_cli/cli/commands/merge.py`

**Steps**:
1. Find the existing `--strategy` typer option in the `merge()` command (currently declared but discarded around line 469 per spec analysis — verify against current main; line numbers may have shifted)
2. Change its type to `Optional[MergeStrategy]` and accept the enum
3. After the option is parsed, compute `resolved_strategy`:
   ```python
   resolved_strategy = (
       strategy
       or load_merge_config(repo_root).strategy
       or MergeStrategy.SQUASH
   )
   ```
4. Pass `resolved_strategy` into `_run_lane_based_merge(...)` as a new keyword argument
5. Add `strategy: MergeStrategy` to the `_run_lane_based_merge` signature
6. Do NOT yet use the value inside `_run_lane_based_merge` — that's T010's job. Just plumb it through.

**Validation**: `spec-kitty merge --feature <slug> --strategy squash --dry-run` shows the strategy in the dry-run output. Without a flag, the dry-run shows `squash` resolved from default.

### T010 — Honor the strategy parameter in `lanes/merge.py` for the mission→target step

**Purpose**: Make the strategy parameter actually do something. The lower-level merge code currently hardcodes merge commits at `lanes/merge.py:227` (per spec analysis — verify). Change the mission→target step to switch on the strategy.

**Files**:
- Modified: `src/specify_cli/lanes/merge.py`

**Steps**:
1. Find the mission→target merge invocation (search for `git merge` calls; the hardcoded one per the spec is around line 227)
2. Pass the strategy parameter from `_run_lane_based_merge` down to this layer (add a parameter to whatever helper does the mission→target merge)
3. Switch on strategy:
   - `MergeStrategy.SQUASH`: `git merge --squash <mission-branch>` then `git commit -m "feat(<mission_slug>): squash merge of mission"`
   - `MergeStrategy.REBASE`: `git rebase <mission-branch>` (or `git merge --ff-only` after a rebase, depending on how the code structures the call)
   - `MergeStrategy.MERGE`: existing behavior (`git merge --no-ff <mission-branch>`)
4. **Critical**: the **lane → mission** merge step is NOT touched. Lane→mission MUST keep its existing merge-commit semantics regardless of the strategy parameter. Identify the lane→mission helper and confirm it does NOT receive the strategy parameter.

**Validation**: Manual test with a synthetic 2-WP mission: each strategy produces the expected git history shape on the target branch (1 squash commit, or rebased commits, or 1 merge commit). Lane→mission still produces a merge commit.

### T011 — Push-error parser + remediation hint helper + wire to push failure path

**Purpose**: When a push is rejected by linear-history protection, parse the error and emit a hint pointing the user at `--strategy squash` and the config key. Fail open on unknown rejection messages.

**Files**:
- Modified: `src/specify_cli/cli/commands/merge.py`

**Steps**:
1. Add the locked token tuple at module level:
   ```python
   LINEAR_HISTORY_REJECTION_TOKENS: tuple[str, ...] = (
       "merge commits",
       "linear history",
       "fast-forward only",
       "GH006",
       "non-fast-forward",
   )
   ```
2. Add `_is_linear_history_rejection(stderr: str) -> bool` doing case-insensitive substring match
3. Add `_emit_remediation_hint(console: Console) -> None` printing the hint with rich markup pointing at `--strategy squash` and `merge.strategy` config key
4. Find the existing push call site (likely around the end of `_run_lane_based_merge` or in a helper). Wrap the push in a try/except that captures stderr.
5. On non-zero exit, call `_is_linear_history_rejection(stderr)`. If true, call `_emit_remediation_hint(console)`. If false, fail open — no hint.

**Validation**: a unit test feeds each of the 5 token strings into `_is_linear_history_rejection` and asserts True. An unrelated stderr (e.g., `"connection refused"`) returns False.

### T012 — Insert `safe_commit` between mark-done loop and worktree-removal (FR-019)

**Purpose**: Fix the bug that lost mission 067's done events. Persist `status.events.jsonl` and `status.json` to git via `safe_commit` after the per-WP `_mark_wp_merged_done` loop and before any worktree-removal step.

**Files**:
- Modified: `src/specify_cli/cli/commands/merge.py`

**Steps**:
1. Find `_run_lane_based_merge` in `cli/commands/merge.py`. Find the per-WP loop that calls `_mark_wp_merged_done` (which internally calls `emit_status_transition` → `_store.append_event`). Verify it's still in the same place; the spec said roughly lines 277-464 but the file may have changed.
2. Find the worktree-removal step that comes after the loop. The insertion point is between the loop and that step.
3. Add the import at the top of the file if not already present:
   ```python
   from specify_cli.git import safe_commit
   ```
4. Insert the `safe_commit` call exactly per `contracts/merge_strategy.md`:
   ```python
   safe_commit(
       repo_path=main_repo,
       files_to_commit=[
           feature_dir / "status.events.jsonl",
           feature_dir / "status.json",
       ],
       commit_message=f"chore({mission_slug}): record done transitions for merged WPs",
       allow_empty=False,
   )
   ```
5. The variables `main_repo`, `feature_dir`, and `mission_slug` should already be in scope at the insertion point. If not, look up the existing variable names in `_run_lane_based_merge` for the equivalents and use those.

**Validation**: a manual run of `spec-kitty merge` against a synthetic 2-WP mission produces a new git commit with subject `chore(<slug>): record done transitions for merged WPs`. `git show HEAD:kitty-specs/<slug>/status.events.jsonl` contains `to_lane: done` entries.

### T013 — Import + call `run_check` from WP01 in the merge runner; render in merge summary

**Purpose**: Wire the WP01 stale-assertion analyzer into the merge runner via direct library import (NOT subprocess). Print the findings as part of the merge summary.

**Files**:
- Modified: `src/specify_cli/cli/commands/merge.py`

**Dependency**: WP01 must have landed first.

**Steps**:
1. Add the import at the top of the file:
   ```python
   from specify_cli.post_merge.stale_assertions import run_check, StaleAssertionReport
   ```
2. After the safe_commit step (T012's insertion point) and after the worktree-removal step, before the final merge summary print, call `run_check`:
   ```python
   stale_report = run_check(
       base_ref=merge_base_sha,  # use the variable name actually in scope
       head_ref="HEAD",
       repo_root=main_repo,
   )
   ```
3. Append a "Stale assertion findings" section to the merge summary block. Render via rich (use the same console object that prints the rest of the summary). If `stale_report.findings` is empty, print "No likely-stale assertions detected."
4. **Critical**: do NOT shell out to `subprocess.run(["spec-kitty", "agent", "tests", "stale-check", ...])`. The contract is direct library import.

**Validation**: a manual run of `spec-kitty merge` against a synthetic mission with a renamed function in source and an assertion against the old name in tests produces a stale-assertion finding in the merge summary.

### T014 — Test suite covering FR-005..FR-009, FR-019, FR-020, NFR-003

**Purpose**: Lock the WP02 contracts. The most important test is the FR-020 regression test using the mechanically-correct `git show HEAD:` direct assertion.

**Files**:
- New: `tests/cli/commands/test_merge_strategy.py`
- New: `tests/cli/commands/test_merge_status_commit.py`

**Tests** (per `contracts/merge_strategy.md` test surface table):
- `test_strategy_flag_flows_through` — `--strategy squash` reaches `_run_lane_based_merge`
- `test_default_strategy_is_squash` — no flag, no config → squash
- `test_lane_to_mission_uses_merge_commit` — `--strategy squash` does NOT change lane→mission semantics
- `test_config_yaml_strategy_honored` — `merge.strategy: rebase` produces a rebase merge
- `test_invalid_config_strategy_raises` — bogus value raises startup error
- `test_push_rejection_emits_hint_for_known_tokens` — each of the 5 tokens triggers the hint
- `test_push_rejection_fails_open_for_unknown` — unrelated stderr does NOT emit a hint
- `test_done_events_committed_to_git` — **the critical FR-019/FR-020 regression test**:
  ```python
  def test_done_events_committed_to_git(synthetic_mission_repo):
      repo, mission_slug, wps = synthetic_mission_repo  # fixture creates 2+ WPs
      _run_lane_based_merge(...)  # run end-to-end
      result = subprocess.run(
          ["git", "show", f"HEAD:kitty-specs/{mission_slug}/status.events.jsonl"],
          cwd=repo, capture_output=True, text=True, check=True,
      )
      events = [json.loads(line) for line in result.stdout.splitlines() if line.strip()]
      done_wps = {e["wp_id"] for e in events if e["to_lane"] == "done"}
      assert done_wps == set(wps)
  ```
  **DO NOT** add a `git reset --hard HEAD` step — that's a no-op for a file already at HEAD and proves nothing. The direct `git show HEAD:` assertion is the mechanically-correct proof.
- `test_protected_linear_history_succeeds_default` — NFR-003 integration test against a synthetic remote with `receive.denyNonFastForwards` and a pre-receive hook checking for merge commits

**Validation**: `pytest tests/cli/commands/test_merge_strategy.py tests/cli/commands/test_merge_status_commit.py -v` exits zero. No network calls.

## Test Strategy

Tests are required by the spec. Use synthetic git fixtures (`tmp_path` + a fixture that scaffolds a mini spec-kitty mission with 2+ WPs). For NFR-003, set up a synthetic bare remote with `receive.denyNonFastForwards = true` and a custom hook.

## Definition of Done

- [ ] `src/specify_cli/merge/config.py` exists with `MergeStrategy`, `MergeConfig`, `load_merge_config`
- [ ] `.kittify/config.yaml` includes the `merge.strategy` schema example
- [ ] `--strategy` flag is no longer discarded (T009 wiring complete)
- [ ] `lanes/merge.py` honors the strategy parameter for mission→target (T010)
- [ ] Lane→mission merges still produce merge commits (T010)
- [ ] Push-error parser + remediation hint wired to push failure path (T011)
- [ ] `safe_commit` call inserted after mark-done loop and before worktree-removal (T012, FR-019)
- [ ] Merge runner imports `run_check` from `specify_cli.post_merge.stale_assertions` and renders findings in the merge summary (T013, depends on WP01)
- [ ] All FR-005..FR-009, FR-019, FR-020 tests pass
- [ ] FR-020 test uses `git show HEAD:` direct assertion (NOT `git reset --hard HEAD`)
- [ ] NFR-003 protected-branch integration test passes
- [ ] `mypy --strict` passes on all modified files
- [ ] `ruff` clean

## Risks

- **Line numbers in spec/contracts may have shifted**: the spec quotes `merge.py:277-464` and `merge.py:469`/`merge.py:484` from analysis at commit `7307389a`. Read the current file before editing. The structural insertion point ("after the per-WP `_mark_wp_merged_done` loop and before the worktree-removal step") is what matters, not the exact line.
- **`safe_commit` argument names**: verify against `src/specify_cli/git/commit_helpers.py:38`. The contract reflects the current signature (`repo_path`, `files_to_commit`, `commit_message`, `allow_empty`), but if it changed, adapt.
- **Lane→mission accidental coupling**: it would be easy to accidentally apply the strategy to lane→mission merges as well. The contract is explicit: lane→mission stays merge-commit. Add an explicit assertion in T014 that verifies this.
- **WP01 dependency**: T013 cannot land until WP01's library exists. The lane planner will sequence them; the WP02 implementer should not attempt to stub `run_check` locally.

## Reviewer Guidance

- Verify `safe_commit` is called BEFORE any worktree-removal or `cleanup_merge_workspace` step
- Verify the `safe_commit` payload is exactly `[status.events.jsonl, status.json]` for the mission feature directory — NOT including `.kittify/runtime/merge/...` (out of scope per spec)
- Verify `--strategy merge` produces a merge commit on the target branch and `--strategy squash` produces a single squash commit
- Verify lane→mission merges still produce merge commits regardless of `--strategy`
- Run the FR-020 regression test by hand: `pytest tests/cli/commands/test_merge_status_commit.py::test_done_events_committed_to_git -v`
- Confirm the test does NOT use `git reset --hard HEAD` anywhere
- Verify the push-error parser fails open on `"connection refused"` and similar unrelated errors

## Next steps after merge

WP02 is the longest sequential chain. Once it lands, mission 068's two highest-impact code changes (FR-019 events fix + FR-005..FR-009 strategy wiring) are both shipped. The remaining WPs (WP03, WP04, WP05) can run in parallel lanes if they haven't already.
