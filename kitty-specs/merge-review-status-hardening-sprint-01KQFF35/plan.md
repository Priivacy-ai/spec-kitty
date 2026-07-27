# Implementation Plan: Merge Abort, Review, and Status Hardening Sprint

**Branch**: `main` | **Date**: 2026-04-30 | **Spec**: [spec.md](spec.md)
**Mission ID**: 01KQFF35BPH2H8971KR0TEY8ST

## Branch Contract

- **Current branch at plan start**: `main`
- **Planning/base branch**: `main`
- **Final merge target**: `main`
- `branch_matches_target`: true

## Summary

Fix two confirmed bugs and add five enhancements across the spec-kitty CLI.
All work is internal to `src/specify_cli/`; no external dependencies are added.
The seven changes are independent enough to parallelise across two lanes, but
share several source files so the conservative default is one lane.

Seven work packages, in implementation order:

| WP | Issue | Type | Files |
|----|-------|------|-------|
| WP01 | #903 | Bug fix | `cli/commands/merge.py` |
| WP02 | #904 | Bug fix | `cli/commands/agent/tasks.py`, `agent_utils/status.py` |
| WP03 | #907 | Enhancement | `cli/commands/` (BLE001 annotations), `pyproject.toml` |
| WP04 | #906 | Enhancement | `missions/software-dev/command-templates/review.md` |
| WP05 | #905 | Enhancement | `cli/commands/agent/tasks.py` |
| WP06 | #909 | Enhancement | `agent_utils/status.py`, `cli/commands/agent/tasks.py` |
| WP07 | #908 | New feature | `cli/commands/review.py` (new), `cli/commands/__init__.py` |

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: typer, rich, ruamel.yaml (already in pyproject.toml)
**Storage**: Filesystem only — `.kittify/` JSON/JSONL/YAML, `kitty-specs/` Markdown
**Testing**: pytest, 90%+ line coverage required, mypy --strict
**Target Platform**: CLI tool (Linux/macOS)
**Performance Goals**: `merge --abort` ≤2 s; `review --mission` ≤10 s for <20 WPs
**Constraints**: Status events append-only; no new PyPI dependencies; template
  changes in source only (not generated agent copies)

## Charter Check

Charter enforces: pytest 90%+, mypy --strict, integration tests for CLI commands.

- All new CLI commands (WP07) require at least one integration test. ✓ planned
- All modified files must pass mypy --strict. ✓ enforced per WP
- No new PyPI packages. ✓ no new deps needed
- Template changes to source templates only. ✓ WP04 targets
  `src/specify_cli/missions/software-dev/command-templates/review.md` only

Charter check: **PASS**

## Project Structure

```
src/specify_cli/
├── cli/
│   ├── commands/
│   │   ├── merge.py            ← WP01 (--abort cleanup), WP03 (BLE001)
│   │   ├── review.py           ← WP07 (new file)
│   │   ├── __init__.py         ← WP07 (register new command)
│   │   └── agent/
│   │       └── tasks.py        ← WP02 (verdict check), WP05 (lane guard),
│   │                               WP06 (stall detection)
│   └── helpers.py              ← WP03 (BLE001)
├── agent_utils/
│   └── status.py               ← WP02 (status warning), WP06 (stall rendering)
└── missions/
    └── software-dev/
        └── command-templates/
            └── review.md       ← WP04 (deletion test checklist item)
```

## Execution Lanes

**Lane A** (single lane, sequential): WP01 → WP02 → WP03 → WP04 → WP05 → WP06 → WP07

WP04 (template-only) and WP07 (new file) are fully independent from the others
and can be moved to a separate lane if the implementer wants to parallelise.
All other WPs share `agent/tasks.py`; a second lane is only safe if WP04 and
WP07 are isolated.

---

## Work Package Definitions

### WP01 — merge --abort lock cleanup (#903)

**Goal**: Make `spec-kitty merge --abort` fully idempotent and complete.

**Key findings (research)**:
- `_GLOBAL_MERGE_LOCK_ID = "__global_merge__"` lives in
  `src/specify_cli/cli/commands/merge.py`
- The lock file is at `.kittify/runtime/merge/__global_merge__/lock`
- The `--abort` flag handler is in the same file's `merge()` command

**What to change**:
1. In `src/specify_cli/cli/commands/merge.py`, find the `--abort` handling block.
2. Add three idempotent cleanup steps:
   - Resolve the lock file path using the existing `_GLOBAL_MERGE_LOCK_ID`
     constant and the lock-path derivation logic already in the file. Delete it
     if it exists, `suppress(FileNotFoundError)`.
   - Delete `.kittify/merge-state.json` if it exists, `suppress(FileNotFoundError)`.
   - If git is in a merging state (`git merge --abort` succeeds when
     `.git/MERGE_HEAD` exists), run `git merge --abort`. Swallow the error if
     git is not mid-merge.
3. Exit 0 in all cases.
4. Add a test: `test_abort_clears_lock_and_state` — creates both files, runs
   abort, asserts both are gone. Run a second time; assert still exits 0.

**Acceptance**: `spec-kitty merge --abort` exits 0 whether lock/state exist or not.

---

### WP02 — stale verdict validation on force-approve (#904)

**Goal**: Block or warn when `move-task --to approved/done --force` would
leave a `verdict: rejected` review artifact in place.

**Key findings (research)**:
- `move_task()` is at `src/specify_cli/cli/commands/agent/tasks.py:1110`
- Review-cycle artifacts live at
  `kitty-specs/<slug>/tasks/<WP-dir>/review-cycle-N.md`
- `show_kanban_status()` is at `src/specify_cli/agent_utils/status.py:28`

**What to change**:

`src/specify_cli/cli/commands/agent/tasks.py`:

1. Add helper `get_latest_review_cycle_verdict(wp_dir: Path) -> str | None`
   that reads the highest-numbered `review-cycle-N.md`, parses its YAML
   frontmatter, and returns the `verdict` field value (or `None` if absent/
   unreadable).

2. In `move_task()`, after resolving the WP directory but before emitting the
   status transition, if `to_lane` is `approved` or `done` and `--force` is set:
   - Call `get_latest_review_cycle_verdict(wp_dir)`.
   - If it returns `"rejected"` and `--skip-review-artifact-check` is NOT set:
     - Print: `"WP<id> <filename> has verdict: rejected. Update the review
       artifact or pass --skip-review-artifact-check to suppress."`
     - `raise typer.Exit(1)`

3. Add `--skip-review-artifact-check` option (bool, default False) to
   `move_task()` with help text in `--help` output.

4. Add valid verdict enum check: if the verdict value is not in
   `{approved, approved_after_orchestrator_fix, arbiter_override, rejected}`,
   emit a warning (do not block — the artifact may predate this validation).

`src/specify_cli/agent_utils/status.py`:

5. In `show_kanban_status()`, after building the snapshot, iterate WPs in
   `approved` and `done` lanes. For each, call
   `get_latest_review_cycle_verdict()`. If `"rejected"`, append a warning line
   to that WP's rendered row.

**Acceptance**: Force-approve of a WP with `verdict: rejected` is blocked by
default; `--skip-review-artifact-check` bypasses it. Status board warns on
stale verdicts.

---

### WP03 — BLE001 suppression justification (#907)

**Goal**: All `# noqa: BLE001` suppressions in `src/specify_cli/auth/` and
`src/specify_cli/cli/commands/` carry an inline justification comment.

**Key findings (research)**:
- `src/specify_cli/auth/` suppressions already have justifications ✓
- `src/specify_cli/cli/commands/` has many suppressions without justification.
- Full list of un-annotated suppressions (requiring inline comment or removal):
  - `src/specify_cli/cli/helpers.py:65,259,262`
  - `src/specify_cli/cli/commands/mission_type.py:339`
  - `src/specify_cli/cli/commands/charter.py:81,127,246,249,318,982`
  - `src/specify_cli/cli/commands/materialize.py:110`
  - `src/specify_cli/cli/commands/tracker.py:103,120`
  - `src/specify_cli/cli/commands/merge.py:1026,1275`
  - `src/specify_cli/cli/commands/charter_bundle.py:251,270`

**What to change**:

For each un-annotated suppression:
1. Read the surrounding context.
2. If the swallow is genuinely safe (e.g., fail-open diagnostic), add an
   inline justification: `# noqa: BLE001 — <reason>`
3. If the swallow is not safe (masks real errors), remove the suppression and
   let the exception propagate (or catch a narrower exception type).

No `pyproject.toml` changes are required — the existing rule configuration is
sufficient. The fix is purely adding justification text to existing `# noqa`
comments.

**Acceptance**: `grep "noqa: BLE001" src/specify_cli/auth/ src/specify_cli/cli/`
shows no bare suppressions (every line has text after `BLE001`).
`uv run ruff check src/` continues to pass.

---

### WP04 — WP review DoD deletion-test checklist item (#906)

**Goal**: Add an explicit error-path reachability check to the WP review
template so reviewers must apply the deletion test.

**Key findings (research)**:
- Source template: `src/specify_cli/missions/software-dev/command-templates/review.md`
- Generated copies in `.claude/commands/`, `.amazonq/prompts/`, etc. must NOT
  be edited — they are regenerated by `spec-kitty upgrade`.

**What to change**:

In `src/specify_cli/missions/software-dev/command-templates/review.md`:

Find the error handling or test coverage checklist section. Add the following
checklist item (insert under the existing test-coverage items):

```
- [ ] **Error-path reachability (deletion test)**: For each test that
  validates an error path, verify the test would fail if the implementation
  fix were deleted. A test that only validates an exception handler's
  *structure* (e.g., that a `try/except` exists) without exercising the
  real dependency is insufficient — the fix must be reachable from the test.
  Apply the deletion test: delete the implementation change, run the test,
  confirm it fails. If it does not fail, the error path is untested.
```

**Acceptance**: The deletion-test item is present in the source template.
No generated agent copies are modified.

---

### WP05 — lane guard error message (#905)

**Goal**: Name the planning branch in the lane guard error and provide a
`git show` command for verification.

**Key findings (research)**:
- Error message is at `src/specify_cli/cli/commands/agent/tasks.py:1003`
- Current text: `"Lane branch contains forbidden planning changes under kitty-specs/!"`
- The planning branch is available from the WP's feature metadata /
  `meta.json` (`planning_base_branch` field set at mission create time)

**What to change**:

`src/specify_cli/cli/commands/agent/tasks.py`:

1. In the lane guard block (around line 1003), resolve the `planning_base_branch`
   from the mission `meta.json` (use the same `load_meta()` / `feature_dir`
   resolution already present in the file for other checks).

2. Replace the current error message with:
   ```
   kitty-specs/ changes are not allowed on lane branches.
   Planning artifacts must live on: {planning_base_branch}

   To verify a file exists on the planning branch:
     git show {planning_base_branch}:kitty-specs/<path-to-file>
   ```

3. If `planning_base_branch` cannot be resolved (legacy mission, no meta.json),
   fall back to the original error message with a note:
   `"(planning branch unknown — check kitty-specs/ on the base branch)"`

**Acceptance**: The lane guard error names the planning branch when
`meta.json` is present. Fallback message is shown for legacy missions.

---

### WP06 — stalled reviewer detection (#909)

**Goal**: Mark WPs in `in_review` with no status event for >30 min as stalled
in the kanban board and `spec-kitty next` output.

**Key findings (research)**:
- Status events are in `kitty-specs/<slug>/status.events.jsonl`, each with
  an `at` ISO timestamp.
- `show_kanban_status()` in `src/specify_cli/agent_utils/status.py` renders
  the board.
- `spec-kitty next` is at `src/specify_cli/cli/commands/next_cmd.py`.
- The stall threshold config key `review.stall_threshold_minutes` does not yet
  exist; it will be added as an optional key with default 30.

**What to change**:

`src/specify_cli/agent_utils/status.py`:

1. Add helper `get_last_event_time(events: list[StatusEvent], wp_id: str) -> datetime | None`
   that returns the `at` timestamp of the most recent event for the given WP.

2. In `show_kanban_status()`, for each WP in `in_review` lane:
   - Compute `age = now_utc - get_last_event_time(events, wp_id)`.
   - Load stall threshold from config (`review.stall_threshold_minutes`,
     default 30) via the existing config loader.
   - If `age.total_seconds() / 60 > threshold`, append
     `⚠ STALLED — no move-task in {int(age.total_seconds()//60)}m` to the
     WP row.

3. Return stalled WP IDs in the dict result so callers can act on them.

`src/specify_cli/cli/commands/next_cmd.py` (or wherever `next_step` is):

4. After the existing `show_kanban_status()` call, check returned stalled WPs.
   For each stalled WP, print an actionable block:
   ```
   ⚠ WP{id} has been in_review for {Xm} — reviewer may be stalled.
   Intervention options:
     spec-kitty agent tasks move-task {wp_id} --to approved --force --note "Approved after {Xm} stall"
     spec-kitty agent tasks move-task {wp_id} --to planned --review-feedback-file <path>
   ```

**Acceptance**: WPs stalled in `in_review` show the stall warning in status
output. `spec-kitty next` surfaces intervention commands.

---

### WP07 — spec-kitty review --mission command (#908)

**Goal**: Add `spec-kitty review --mission <slug>` as a first-class post-merge
validation gate.

**Key findings (research)**:
- No existing `review.py` in `src/specify_cli/cli/commands/`.
- CLI registration: `src/specify_cli/cli/commands/__init__.py` — add one
  `app.command()` call following the `merge` pattern.
- `baseline_merge_commit` is in `meta.json` (field populated at merge time).
- The `mission-review-report.md` output format is documented in the spec.

**What to build**:

`src/specify_cli/cli/commands/review.py` (new file):

```python
# New command: spec-kitty review --mission <slug>
# Checks: WP lane state, dead-code scan, BLE001 audit
# Writes: kitty-specs/<slug>/mission-review-report.md
```

Implement `review_mission(mission: str = typer.Option(..., "--mission"))` with
four steps:

**Step 1 — WP lane check**:
- Resolve feature dir from `--mission` handle using existing mission resolver.
- Read `status.events.jsonl`, call `materialize()` to get snapshot.
- If any WP is not in `done` lane, print the list and `raise typer.Exit(1)`.

**Step 2 — Dead-code scan**:
- Read `baseline_merge_commit` from `meta.json`. If missing, print warning and
  skip this step.
- Run `git diff {baseline}..HEAD -- src/` and parse added lines matching
  `^+.*def [A-Z_a-z]` (public function/class definitions, non-dunder).
- For each new symbol, grep `src/` excluding `tests/` for any reference. If no
  non-test reference found, record as a finding.

**Step 3 — BLE001 audit**:
- Grep `src/specify_cli/auth/` and `src/specify_cli/cli/commands/` for
  `# noqa: BLE001` where the rest of the comment line after `BLE001` is blank
  or absent.
- Record each as a finding with file:line.

**Step 4 — Write report**:
- Write `kitty-specs/<slug>/mission-review-report.md` with frontmatter:
  ```yaml
  verdict: pass | pass_with_notes | fail
  reviewed_at: <iso timestamp>
  findings: <N>
  ```
  Body: bulleted list of findings, or "No findings." if clean.

`src/specify_cli/cli/commands/__init__.py`:
- Add `from . import review as review_module` and
  `app.command(name="review")(review_module.review_mission)`.

**Acceptance**: `spec-kitty review --mission <slug>` exits 0 when all WPs are
done and no findings, writes `mission-review-report.md` with `verdict: pass`.
Exits 1 with `verdict: fail` when non-done WPs or unjustified BLE001
suppressions are found.

---

## Phase 0: Research

No external unknowns. All research is codebase archaeology completed above.
See `research.md` for full findings.

## Phase 1: Design Artifacts

- `data-model.md` — entity definitions for new/modified data shapes
- `contracts/review-command-interface.md` — CLI interface contract for WP07
