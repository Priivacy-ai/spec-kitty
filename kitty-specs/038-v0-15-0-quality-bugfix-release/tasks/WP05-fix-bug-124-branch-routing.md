---
work_package_id: WP05
title: Fix Bug
lane: "done"
dependencies: []
base_branch: main
base_commit: e15a6b31500437333efc357888c680009d9b7b33
created_at: '2026-02-11T15:22:44.639976+00:00'
subtasks: [T029, T030, T031, T032, T033, T034, T035, T036, T037, T038]
phase: Phase 1 - Bug Fixes
shell_pid: "45299"
agent: "codex"
review_status: "has_feedback"
reviewed_by: "Robert Douglass"
---

# Work Package Prompt: WP05 – Fix Bug #124 - Branch Routing Unification

## Objectives

- Unified branch resolution function used across all commands
- No implicit fallback to main/master (respect current branch)
- Clear notifications when current != target
- 5 integration tests passing
- Fix across 4 command files committed atomically

**Command**: `spec-kitty implement WP05`

## Context

- **Issue**: #124 by @fabiodouek
- **Files**: 4 command modules with duplicated branch logic
  - `cli/commands/implement.py:1050-1097`
  - `cli/commands/agent/workflow.py`
  - `cli/commands/agent/tasks.py`
  - `cli/commands/agent/feature.py`
- **Bug**: Auto-checks out master during operations without user awareness
- **Fix**: Unify branch resolution, stop implicit fallback

## Test-First Subtasks

### T029-T031: Write Failing Integration Tests

1. **T029**: Run from feature branch → verify no auto-checkout to master
2. **T030**: Verify worktree base branch is current branch (not master)
3. **T031**: Verify status commits land on current branch

### T032-T036: Implement Unified Resolver

**T032**: Create unified function in `src/specify_cli/git/branch_utils.py`
```python
def resolve_target_branch(
    feature_slug: str,
    repo_path: Path,
    current_branch: str,
    respect_current: bool = True
) -> BranchResolution:
    """
    Resolve target branch for feature operations.
    
    Returns BranchResolution with:
    - target: Target branch from meta.json
    - current: User's current branch
    - should_notify: True if current != target
    - action: "stay_on_current" or "checkout_target"
    """
    # Read meta.json
    meta = load_meta_json(repo_path / "kitty-specs" / feature_slug)
    target = meta.get("target_branch", "main")
    
    if current == target:
        return BranchResolution(target, current, False, "proceed")
    
    if respect_current:
        # Show notification, stay on current
        return BranchResolution(target, current, True, "stay_on_current")
    else:
        # Auto-checkout allowed
        return BranchResolution(target, current, True, "checkout_target")
```

**T033-T036**: Replace duplicated logic in all 4 files
- Each file: Import resolve_target_branch, replace custom logic, add notification

### T037-T038: Verify and Commit

- Run integration tests on all 4 commands
- Commit: `fix: unify branch resolution, stop implicit master fallback (fixes #124)`

## Implementation Notes

**Pattern to replace** (in all 4 files):
```python
# OLD (auto-checkout):
if current_branch != target_branch:
    subprocess.run(["git", "checkout", target_branch])
    # ... do work ...
    subprocess.run(["git", "checkout", current_branch])  # Restore

# NEW (respect current):
resolution = resolve_target_branch(feature_slug, repo_path, current_branch)
if resolution.should_notify:
    console.print(f"[yellow]Note:[/yellow] On '{resolution.current}', target is '{resolution.target}'")
# Proceed on current branch (no checkout)
```

**Search for auto-checkout patterns**:
```bash
cd /Users/robert/ClaudeCowork/Spec-Kitty-Cowork/spec-kitty
grep -r "git checkout" src/specify_cli/cli/commands/ | grep -v "\.pyc"
```

## Activity Log

- 2026-02-11T14:37:04Z – unknown – shell_pid=75658 – lane=for_review – Moved to for_review
- 2026-02-11T15:20:56Z – unknown – shell_pid=75658 – lane=planned – Moved to planned
- 2026-02-11T15:29:02Z – unknown – shell_pid=1928 – lane=for_review – Moved to for_review
- 2026-02-11T15:29:12Z – codex – shell_pid=8729 – lane=doing – Started review via workflow command
- 2026-02-11T15:53:48Z – codex – shell_pid=8729 – lane=for_review – Ready for review: Added comprehensive unit test coverage for Bug #124 branch resolution. All 21 tests passing (5 new unit tests + 4 integration tests + 12 existing). Implementation was already complete, this WP adds test coverage and documentation.
- 2026-02-11T15:54:04Z – codex – shell_pid=38006 – lane=doing – Started review via workflow command
- 2026-02-11T15:56:41Z – codex – shell_pid=38006 – lane=planned – Moved to planned
- 2026-02-11T16:03:29Z – claude – shell_pid=45117 – lane=doing – Started review via workflow command
- 2026-02-11T16:03:39Z – claude – shell_pid=45117 – lane=for_review – Moved to for_review
- 2026-02-11T16:03:56Z – codex – shell_pid=45299 – lane=doing – Started review via workflow command
- 2026-02-11T16:05:40Z – codex – shell_pid=45299 – lane=done – Review passed: branch routing fix verified, no auto-checkout regressions found
