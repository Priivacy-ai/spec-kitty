---
work_package_id: WP01
title: Fix Merge Target Resolution & Template
lane: "done"
dependencies: []
base_branch: 2.x
base_commit: 9ce9079ad35e68fccc9c681277136c34e7c40dd9
created_at: '2026-03-10T11:48:01.299687+00:00'
subtasks:
- T001
- T002
- T003
phase: Phase 1 - Runtime Fix
assignee: ''
agent: claude-opus
shell_pid: '96321'
review_status: "approved"
reviewed_by: "Robert Douglass"
history:
- timestamp: '2026-03-10T11:44:58Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
requirement_refs:
- FR-001
- FR-002
- FR-003
- FR-004
- FR-005
- FR-006
---

# Work Package Prompt: WP01 – Fix Merge Target Resolution & Template

## IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately.
- **You must address all feedback** before your work is complete.
- **Mark as acknowledged**: When you understand the feedback and begin addressing it, update `review_status: acknowledged` in the frontmatter.

---

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Implementation Command

```bash
spec-kitty implement WP01
```

No dependencies — branches directly from `2.x`.

---

## Objectives & Success Criteria

Fix the CRITICAL bug where top-level `spec-kitty merge --feature <slug>` ignores `meta.json` `target_branch` and defaults to `resolve_primary_branch()`. After this WP:

1. `spec-kitty merge --feature <slug>` resolves target from `meta.json` when `--target` is not provided (FR-001)
2. Explicit `--target` still overrides `meta.json` (FR-002)
3. Missing/malformed `meta.json` falls back to `resolve_primary_branch()` (FR-003)
4. No `--feature` flag preserves existing behavior (FR-004)
5. Merge template routes agents to canonical `spec-kitty merge --feature <slug>` only (FR-005)
6. Nonexistent target branch produces a hard error (FR-006)

## Context & Constraints

- **Spec**: `kitty-specs/049-fix-merge-target-resolution/spec.md`
- **Plan**: `kitty-specs/049-fix-merge-target-resolution/plan.md`
- **Constraint C-002**: Do NOT modify `spec-kitty agent feature merge` in `src/specify_cli/cli/commands/agent/feature.py` — it's already correct
- **Constraint C-003**: No new dependencies
- **Constraint C-004**: Reuse `get_feature_target_branch()` from `src/specify_cli/core/feature_detection.py` (lines 645-696)

### Reference: The correct pattern (already working in agent merge path)

File: `src/specify_cli/cli/commands/agent/feature.py` lines 1336-1343:

```python
# Resolve target branch dynamically if not specified
if target is None:
    from specify_cli.core.feature_detection import get_feature_target_branch
    if feature:
        target = get_feature_target_branch(repo_root, feature)
    else:
        from specify_cli.core.git_ops import resolve_primary_branch
        target = resolve_primary_branch(repo_root)
```

### Reference: The broken code (to be fixed)

File: `src/specify_cli/cli/commands/merge.py` lines 721-724:

```python
# Resolve target branch dynamically if not specified
if target_branch is None:
    from specify_cli.core.git_ops import resolve_primary_branch
    target_branch = resolve_primary_branch(repo_root)
```

### Reference: How `get_feature_target_branch()` works

File: `src/specify_cli/core/feature_detection.py` lines 645-696:

- Reads `kitty-specs/<slug>/meta.json`
- Returns `meta["target_branch"]` if present
- Falls back to `resolve_primary_branch()` if meta.json is missing, malformed, or lacks the field
- Handles worktree paths (calls `_get_main_repo_root()`)
- Already battle-tested via the agent merge path

---

## Subtasks & Detailed Guidance

### Subtask T001 – Fix target resolution logic in merge.py

**Purpose**: Port the correct resolution pattern from `feature.py` to `merge.py` so top-level merge respects `meta.json` `target_branch`.

**Steps**:

1. Open `src/specify_cli/cli/commands/merge.py`
2. Locate lines 721-724 (the target resolution block)
3. Replace with:

```python
# Resolve target branch dynamically if not specified
if target_branch is None:
    if feature:
        from specify_cli.core.feature_detection import get_feature_target_branch
        target_branch = get_feature_target_branch(repo_root, feature)
    else:
        from specify_cli.core.git_ops import resolve_primary_branch
        target_branch = resolve_primary_branch(repo_root)
```

4. Verify the `feature` variable is in scope at this point. In the `merge` command function, `feature` is a typer Option parameter — confirm it's the feature slug string (or None).

**Files**:
- `src/specify_cli/cli/commands/merge.py` (modify lines 721-724)

**Validation**:
- [ ] When `--feature` is provided without `--target`, target resolves from `meta.json`
- [ ] When `--feature` is not provided, target resolves from `resolve_primary_branch()` (unchanged)
- [ ] When both `--feature` and `--target` are provided, `--target` wins (because `target_branch` is not None, this block is skipped entirely)

**Edge Cases**:
- `feature` parameter might be passed as `None` when not provided — the `if feature:` guard handles this
- `get_feature_target_branch()` already handles worktree paths internally

---

### Subtask T002 – Add branch existence validation

**Purpose**: When target branch is resolved from `meta.json`, validate that the branch actually exists. If not, fail hard with a clear error (FR-006). No silent fallback.

**Steps**:

1. After the target resolution block (after T001's change), add validation:

```python
# Validate resolved target branch exists (FR-006: hard error, no silent fallback)
if feature and target_branch:
    from specify_cli.core.git_ops import run_command
    # Check local branch
    ret_local, _, _ = run_command(
        ["git", "rev-parse", "--verify", f"refs/heads/{target_branch}"],
        capture=True, check=False,
    )
    if ret_local != 0:
        # Check remote branch
        ret_remote, _, _ = run_command(
            ["git", "rev-parse", "--verify", f"refs/remotes/origin/{target_branch}"],
            capture=True, check=False,
        )
        if ret_remote != 0:
            error_msg = (
                f"Target branch '{target_branch}' (from meta.json) does not exist "
                f"locally or on origin. Check kitty-specs/{feature}/meta.json."
            )
            if json_output:
                print(json.dumps({
                    "spec_kitty_version": SPEC_KITTY_VERSION,
                    "error": error_msg,
                }))
            else:
                console.print(f"[red]Error:[/red] {error_msg}")
            raise typer.Exit(1)
```

2. Verify `run_command` is already imported or available in merge.py. Check the existing imports at the top of the file. If `run_command` is not imported, use the import pattern already used elsewhere in merge.py (it's likely imported from `specify_cli.core.git_ops`).

3. The validation must only fire when `feature` is provided (don't validate for the no-feature fallback path — that's existing behavior).

**Files**:
- `src/specify_cli/cli/commands/merge.py` (add after the resolution block)

**Validation**:
- [ ] Nonexistent branch with `--feature` produces clear error message
- [ ] Error includes `meta.json` path hint
- [ ] JSON output mode returns structured error
- [ ] No-feature path is unaffected (validation only runs when `feature` is truthy)

**Notes**:
- Check if merge.py uses `run_command` from `git_ops` or `subprocess.run` directly. Match the existing pattern.
- The `check=False` parameter (or equivalent) is critical — we want to inspect the return code, not raise on failure.

---

### Subtask T003 – Align merge.md template to canonical command path

**Purpose**: Make frontmatter and body of the merge command template reference only `spec-kitty merge --feature <slug>`. Remove any reference to `spec-kitty agent feature merge`.

**Steps**:

1. Open `src/specify_cli/missions/software-dev/command-templates/merge.md`
2. Read the current content carefully
3. Update the template so that:
   - **Frontmatter `description`** describes the merge command generically (no mention of agent path)
   - **All code blocks** use `spec-kitty merge --feature <feature-slug>` (not `agent feature merge`)
   - **All prose** references the canonical path only
   - **No mention** of `spec-kitty agent feature merge` anywhere in the file

4. The current template body already uses `spec-kitty merge --feature <feature-slug>` in code blocks — verify the frontmatter matches. If the frontmatter currently references `agent feature merge`, change it.

5. Preserve the template's structure and all non-command content (prohibited behaviors, interpretation rules, etc.)

**Files**:
- `src/specify_cli/missions/software-dev/command-templates/merge.md` (modify)

**Validation**:
- [ ] `grep -i "agent feature merge" merge.md` returns no matches
- [ ] Frontmatter and body reference the same command path
- [ ] Template structure preserved (sections, prohibited behaviors, interpretation rules)

**Notes**:
- This is the SOURCE template. Agent copies (`.claude/commands/`, `.codex/prompts/`, etc.) are generated by migrations — do NOT edit those.
- The change propagates to all 12 agents on next `spec-kitty upgrade`.

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Regression in no-feature merge path | WP02 test case #6 explicitly covers backward compat |
| `run_command` import mismatch | Check existing merge.py imports before adding validation |
| Template structure broken | Preserve all non-command sections unchanged |

## Review Guidance

Reviewers should verify:
1. **merge.py**: The resolution block matches the pattern in `feature.py` lines 1337-1343
2. **merge.py**: Branch validation only fires when `feature` is truthy
3. **merge.py**: JSON output error format matches other error responses in the file
4. **merge.md**: Zero occurrences of `agent feature merge` in the template
5. **merge.md**: All code blocks show `spec-kitty merge --feature <feature-slug>`
6. **No changes** to `src/specify_cli/cli/commands/agent/feature.py` (C-002)

## Activity Log

- 2026-03-10T11:44:58Z – system – lane=planned – Prompt created.
- 2026-03-10T11:48:01Z – claude-opus – shell_pid=94798 – lane=doing – Assigned agent via workflow command
- 2026-03-10T11:49:54Z – claude-opus – shell_pid=94798 – lane=for_review – Fixed merge.py target resolution (T001+T002). Template already correct (T003). Ready for review.
- 2026-03-10T11:51:15Z – claude-opus – shell_pid=96321 – lane=doing – Started review via workflow command
- 2026-03-10T11:53:14Z – claude-opus – shell_pid=96321 – lane=done – Review passed: Target resolution correctly ported from feature.py, branch validation uses correct run_command API, template already canonical. All constraints satisfied. | Done override: Review approved; branch merge into 2.x pending spec-kitty merge
