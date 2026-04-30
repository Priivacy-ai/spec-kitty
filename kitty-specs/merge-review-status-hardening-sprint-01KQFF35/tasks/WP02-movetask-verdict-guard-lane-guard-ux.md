---
work_package_id: WP02
title: move-task verdict guard + lane guard UX
dependencies: []
requirement_refs:
- FR-005
- FR-006
- FR-007
- FR-009
- FR-010
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning and merge target are both main. Execution worktree is allocated per lanes.json.
subtasks:
- T007
- T008
- T009
- T010
- T011
- T012
- T013
- T014
agent: claude
history:
- date: '2026-04-30'
  event: created
agent_profile: python-pedro
authoritative_surface: src/specify_cli/cli/commands/agent/tasks.py
execution_mode: code_change
owned_files:
- src/specify_cli/cli/commands/agent/tasks.py
- tests/specify_cli/cli/commands/agent/test_tasks.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load python-pedro
```

---

## Objective

Two independent improvements to `src/specify_cli/cli/commands/agent/tasks.py`:

1. **Verdict guard** (#904): When `move-task --to approved/done --force` is run on a WP whose latest `review-cycle-N.md` has `verdict: rejected`, block the transition and print a clear error. Add `--skip-review-artifact-check` to bypass.

2. **Lane guard UX** (#905): When the lane guard fires because `kitty-specs/` changes are detected on a lane branch, name the planning branch in the error and provide a `git show <branch>:path` example so the reviewer can verify the file exists there.

## Context

**Verdict guard bug**: Reviewer subagent wrote `review-cycle-2.md` with `verdict: rejected` then stalled. Orchestrator ran `move-task WP05 --to approved --force`. WP05 ended up `done` but the review artifact still said `rejected`. No warning was shown. The inconsistency required a manual frontmatter rewrite to fix.

**Lane guard bug**: Reviewer tried to verify `dev-smoke-checklist.md` existed. The lane guard blocked adding it to the lane branch (correct — it lives on the planning branch). But the error gave no hint that the file was present on the planning branch. Reviewer concluded the file was missing. This caused a false rejection.

**Key facts**:
- `move_task()` is at line ~1110 of `src/specify_cli/cli/commands/agent/tasks.py`
- Lane guard error is at line ~1003 of the same file
- Review-cycle artifacts are at `kitty-specs/<slug>/tasks/<WP-dir>/review-cycle-N.md`
- `planning_base_branch` is in `meta.json` (field set at `mission create` time)

## Branch Strategy

- **Planning branch**: `main`
- **Merge target**: `main`
- **Execution workspace**: resolved by `spec-kitty agent action implement WP02 --agent claude`

---

## Subtask T007 — Add `_get_latest_review_cycle_verdict()` helper

**Purpose**: Find the highest-numbered `review-cycle-N.md` for a WP and return its `verdict` frontmatter value.

**Steps**:
1. Add a private helper function in `agent/tasks.py` (near the top of the module or alongside other helpers):
   ```python
   def _get_latest_review_cycle_verdict(wp_dir: Path) -> tuple[str | None, Path | None]:
       """Return (verdict_value, artifact_path) for the latest review-cycle-N.md, or (None, None)."""
       import re
       cycles = sorted(
           wp_dir.glob("review-cycle-*.md"),
           key=lambda p: int(m.group(1)) if (m := re.search(r"review-cycle-(\d+)\.md", p.name)) else 0,
       )
       if not cycles:
           return None, None
       artifact = cycles[-1]
       try:
           text = artifact.read_text(encoding="utf-8")
           # Parse YAML frontmatter between first pair of ---
           match = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
           if not match:
               return None, artifact
           import yaml  # ruamel.yaml or stdlib yaml
           fm = yaml.safe_load(match.group(1)) or {}
           return fm.get("verdict"), artifact
       except Exception:  # noqa: BLE001 — review-cycle artifact may be malformed; fail-open
           return None, artifact
   ```
2. Prefer `ruamel.yaml` if already used elsewhere in the file; otherwise use `yaml` (stdlib-compatible). Check existing imports.
3. The function returns both the verdict string and the artifact path so the caller can name the file in error messages.

**Files**: `src/specify_cli/cli/commands/agent/tasks.py`

**Validation**: The helper compiles. Unit-testable independently.

---

## Subtask T008 — Verdict enum validation

**Purpose**: Warn (but do not block) when a verdict value is not in the known enum set.

**Steps**:
1. Define a set of valid verdicts:
   ```python
   _VALID_VERDICTS = frozenset({"approved", "approved_after_orchestrator_fix", "arbiter_override", "rejected"})
   ```
2. In `_get_latest_review_cycle_verdict()` or in the caller, after reading `verdict`:
   - If `verdict is not None` and `verdict not in _VALID_VERDICTS`, emit a warning:
     `f"Warning: {artifact_path.name} has unrecognized verdict '{verdict}' — expected one of {sorted(_VALID_VERDICTS)}"`
   - Do NOT block on unknown verdicts — backward compat with pre-existing artifacts.

**Files**: `src/specify_cli/cli/commands/agent/tasks.py`

---

## Subtask T009 — Rejected-verdict guard in `move_task()`

**Purpose**: Block `--to approved --force` and `--to done --force` when the latest review artifact shows `verdict: rejected`.

**Steps**:
1. In `move_task()`, after resolving the WP directory (`wp_dir`) but BEFORE calling `emit_status_transition()`:
2. Add the guard:
   ```python
   if force and to_lane in {"approved", "done"} and not skip_review_artifact_check:
       verdict, artifact_path = _get_latest_review_cycle_verdict(wp_dir)
       if verdict == "rejected":
           console.print(
               f"[red]Error:[/red] {wp_id} {artifact_path.name} has verdict: rejected.\n"
               "Update the review artifact or pass --skip-review-artifact-check to suppress.",
               err=True,
           )
           raise typer.Exit(1)
   ```
3. The guard only fires when both `--force` AND `--to approved/done` are present. Normal (non-forced) transitions are not affected.
4. Apply to both `approved` and `done` transitions (FR-005, FR-007).

**Files**: `src/specify_cli/cli/commands/agent/tasks.py`

**Validation**: A force-approve on a WP with `verdict: rejected` exits 1 with the named file.

---

## Subtask T010 — `--skip-review-artifact-check` option

**Purpose**: Provide an escape hatch for operators who have acknowledged the stale verdict.

**Steps**:
1. Add a new Typer option to `move_task()`:
   ```python
   skip_review_artifact_check: bool = typer.Option(
       False,
       "--skip-review-artifact-check",
       help="Suppress the rejected-verdict check when force-approving a WP.",
   ),
   ```
2. Thread `skip_review_artifact_check` into the guard added in T009.
3. The option must appear in `--help` output (Typer does this automatically for named options).

**Files**: `src/specify_cli/cli/commands/agent/tasks.py`

**Validation**: `spec-kitty agent tasks move-task --help` shows `--skip-review-artifact-check`.

---

## Subtask T011 — Locate lane guard and load planning_base_branch

**Purpose**: Set up for the improved lane guard error message by finding the guard block and resolving the planning branch.

**Steps**:
1. Find the lane guard in `agent/tasks.py` (line ~1003):
   ```python
   guidance.append("Lane branch contains forbidden planning changes under kitty-specs/!")
   ```
2. At that point in the code, determine what context is available: Is there a feature slug? A repo_root? A meta.json path?
3. Add `planning_base_branch` resolution:
   ```python
   from specify_cli.core.mission_creation import load_meta  # or equivalent
   planning_branch: str | None = None
   try:
       meta = load_meta(feature_dir)  # use existing meta-loading utility
       planning_branch = meta.get("planning_base_branch") or meta.get("target_branch")
   except Exception:  # noqa: BLE001 — meta.json may be absent for legacy missions; fall back gracefully
       pass
   ```
4. Identify the exact import and function to use for meta loading. Check existing imports in the file.

**Files**: `src/specify_cli/cli/commands/agent/tasks.py`

---

## Subtask T012 — Rewrite lane guard error message

**Purpose**: Replace the opaque error with one that names the planning branch and shows how to verify files.

**Steps**:
1. Replace the existing message with:
   ```python
   if planning_branch:
       guidance.append(
           f"kitty-specs/ changes are not allowed on lane branches.\n"
           f"Planning artifacts must live on: {planning_branch}\n\n"
           f"To verify a file exists on the planning branch:\n"
           f"  git show {planning_branch}:kitty-specs/<path-to-file>"
       )
   else:
       guidance.append(
           "kitty-specs/ changes are not allowed on lane branches "
           "(planning branch unknown — check kitty-specs/ on the base branch)."
       )
   ```
2. Keep the conditional so legacy missions still get a useful (if less specific) message.
3. Check whether `guidance` is a list that gets joined into a final string — adjust formatting accordingly.

**Files**: `src/specify_cli/cli/commands/agent/tasks.py`

**Validation**: When `meta.json` is present, error names the planning branch. When absent, fallback message is shown.

---

## Subtask T013 — Legacy-mission fallback

**Purpose**: The fallback path (missing/invalid `meta.json`) is already handled in T011-T012. Verify it is robust.

**Steps**:
1. Confirm the `try/except` in T011 covers:
   - `meta.json` does not exist
   - `meta.json` exists but `planning_base_branch` key is absent
   - `meta.json` is malformed JSON
2. In all three cases, `planning_branch` should remain `None`, and the fallback message from T012 should be used.
3. Add a log line if a logger is available: `logger.debug("Could not resolve planning_base_branch for lane guard: %s", exc)`

**Files**: `src/specify_cli/cli/commands/agent/tasks.py`

---

## Subtask T014 — Tests

**Purpose**: Confirm verdict guard and lane guard message work correctly.

**Steps**:
1. Find or create `tests/specify_cli/cli/commands/agent/test_tasks.py`.
2. **Test `test_force_approve_blocked_by_rejected_verdict`**:
   - Create a tmp dir with a `review-cycle-1.md` containing frontmatter `verdict: rejected`.
   - Call the move_task handler (or invoke via CLI test runner) with `--to approved --force`.
   - Assert exit code 1 and that the error message names the artifact file.
3. **Test `test_force_approve_allowed_with_skip_flag`**:
   - Same setup; add `--skip-review-artifact-check`.
   - Assert the transition proceeds (mock `emit_status_transition`).
4. **Test `test_lane_guard_names_planning_branch`**:
   - Mock a `meta.json` with `planning_base_branch: "my-planning-branch"`.
   - Trigger the lane guard condition.
   - Assert the error output contains `"my-planning-branch"`.
5. **Test `test_lane_guard_fallback_no_meta`**:
   - No `meta.json` present.
   - Trigger the lane guard.
   - Assert output contains `"planning branch unknown"`.
6. Run `uv run pytest tests/specify_cli/cli/commands/agent/test_tasks.py -x`.
7. Run `uv run mypy --strict src/specify_cli/cli/commands/agent/tasks.py`.

---

## Definition of Done

- [ ] `move-task WP01 --to approved --force` exits 1 with a named error when `verdict: rejected`
- [ ] `move-task WP01 --to done --force` applies the same guard
- [ ] `--skip-review-artifact-check` bypasses the guard and is visible in `--help`
- [ ] Unknown verdict values emit a warning (not a block)
- [ ] Lane guard error names the planning branch when `meta.json` is present
- [ ] Lane guard includes a `git show <branch>:kitty-specs/` example command
- [ ] Fallback message shown for legacy missions without `meta.json`
- [ ] Tests pass: `test_force_approve_blocked_by_rejected_verdict`, `test_force_approve_allowed_with_skip_flag`, `test_lane_guard_names_planning_branch`, `test_lane_guard_fallback_no_meta`
- [ ] `uv run mypy --strict src/specify_cli/cli/commands/agent/tasks.py` — zero errors

## Reviewer Guidance

- Manually run: `spec-kitty agent tasks move-task WP01 --to approved --force` on a WP whose review-cycle-1.md has `verdict: rejected`. Confirm exit 1 and the named file in the error.
- Check `--help` output for `--skip-review-artifact-check`.
- The lane guard test verifies the message content; also read the changed message in the source to confirm it's human-readable.
