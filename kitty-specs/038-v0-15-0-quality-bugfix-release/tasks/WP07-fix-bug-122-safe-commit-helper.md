---
work_package_id: WP07
title: Fix Bug
lane: "doing"
dependencies: []
base_branch: main
base_commit: e883745c9f9566a68f613dc2d690990b80620754
created_at: '2026-02-11T15:22:42.803823+00:00'
subtasks: [T045, T046, T047, T048, T049, T050, T051, T052, T053]
phase: Phase 1 - Bug Fixes
shell_pid: "1836"
agent: "claude"
---

# Work Package Prompt: WP07 – Fix Bug #122 - Safe Commit Helper

## Objectives

- safe_commit() helper created in git/commit_helpers.py
- Helper only commits intended files (preserves staging area)
- All unsafe commit calls replaced across 3+ command files
- 8 integration tests passing
- HIGH RISK fix - test thoroughly with dirty staging scenarios

**Command**: `spec-kitty implement WP07`

## Context

- **Issue**: #122 by @umuteonder
- **Bug**: Status commits capture ALL staged files (unrelated work gets committed)
- **Touchpoints**: feature.py, tasks.py, implement.py (commit helpers)
- **Fix**: Safe commit helper with explicit file staging

## Test-First Subtasks

### T045-T047: Write Failing Integration Tests

1. **T045**: Pre-stage unrelated file, run move-task, assert unrelated file remains staged
2. **T046**: Test "nothing to commit" graceful handling  
3. **T047**: Test multiple unrelated staged files preserved

### T048-T051: Implement Safe Commit Helper

**T048**: Create helper in `src/specify_cli/git/commit_helpers.py`
```python
from pathlib import Path
from typing import List
import subprocess

def safe_commit(
    repo_path: Path,
    files_to_commit: List[Path],
    commit_message: str,
    allow_empty: bool = False
) -> bool:
    """Commit only specified files, preserve staging area."""
    # Stage only intended files
    for file in files_to_commit:
        subprocess.run(["git", "add", str(file)], cwd=repo_path, check=True)
    
    # Commit
    result = subprocess.run(
        ["git", "commit", "-m", commit_message],
        cwd=repo_path,
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0 and "nothing to commit" in result.stdout:
        return True if allow_empty else False
    
    return result.returncode == 0
```

**T049-T051**: Find and replace unsafe commits in feature.py, tasks.py, implement.py

Search pattern:
```bash
grep -n "git.*commit" src/specify_cli/cli/commands/agent/*.py src/specify_cli/cli/commands/implement.py
```

### T052-T053: Verify and Commit

- Run integration tests with dirty staging area
- Commit: `fix: prevent staged files from leaking into status commits (fixes #122)`

## Activity Log

- 2026-02-11T15:22:42Z – claude – shell_pid=1836 – lane=doing – Assigned agent via workflow command
