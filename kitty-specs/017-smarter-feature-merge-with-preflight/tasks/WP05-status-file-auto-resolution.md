---
work_package_id: "WP05"
title: "Status File Auto-Resolution"
phase: "Phase 3 - User Story 4 (P3)"
subtasks:
  - "T013"
  - "T014"
  - "T015"
  - "T016"
  - "T024"
  - "T028"
  - "T029"
dependencies: ["WP03"]
lane: "doing"
assignee: ""
agent: "codex"
shell_pid: "9049"
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2026-01-18T10:37:13Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP05 – Status File Auto-Resolution

## Objectives & Success Criteria

Implement automatic conflict resolution for status tracking files (YAML frontmatter in task files, checkboxes in tasks.md).

**User Story**: As a developer, I want conflicts in status tracking files resolved automatically so I only manually resolve actual code conflicts.

**Success Criteria**:
- Conflicting `lane:` values auto-resolve to "more done" value
- Conflicting checkboxes auto-resolve to checked `[x]`
- Conflicting `history:` arrays merge chronologically
- Non-status files left for manual resolution
- Cleanup continues even if some resolutions fail

**Functional Requirements Addressed**: FR-012, FR-013, FR-014, FR-015, FR-016, FR-020

## Context & Constraints

**Related Documents**:
- `kitty-specs/017-smarter-feature-merge-with-preflight/spec.md` - User Story 4 acceptance scenarios
- `kitty-specs/017-smarter-feature-merge-with-preflight/plan.md` - status_resolver.py design
- `kitty-specs/017-smarter-feature-merge-with-preflight/data-model.md` - ResolutionResult, Resolution Rules

**Constraints**:
- Post-merge Python cleanup (not git merge driver)
- Must handle malformed YAML gracefully
- Status file patterns: `kitty-specs/**/tasks/*.md`, `kitty-specs/**/tasks.md`
- Lane priority: done > for_review > doing > planned

## Subtasks & Detailed Guidance

### Subtask T013 – Implement conflict marker parser

**Purpose**: Parse git conflict markers to extract both sides of a conflict.

**Steps**:
1. Open `src/specify_cli/merge/status_resolver.py`
2. Implement `parse_conflict_markers()` to extract HEAD and theirs content
3. Handle multiple conflict regions in a single file

**Files**:
- `src/specify_cli/merge/status_resolver.py`

**Parallel?**: Yes

**Implementation**:
```python
"""Status file auto-resolution for merge conflicts."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

__all__ = ["resolve_status_conflicts", "ResolutionResult"]


@dataclass
class ConflictRegion:
    """A single conflict region in a file."""
    start_line: int
    end_line: int
    ours: str  # Content from HEAD (current branch)
    theirs: str  # Content from merging branch
    original: str  # Full conflict text including markers


@dataclass
class ResolutionResult:
    """Result of auto-resolving a status file conflict."""
    file_path: Path
    resolved: bool
    resolution_type: str  # "lane", "checkbox", "history", "mixed", "manual_required"
    original_conflicts: int
    resolved_conflicts: int


CONFLICT_PATTERN = re.compile(
    r'^<<<<<<< .*?\n(.*?)^=======\n(.*?)^>>>>>>> .*?\n',
    re.MULTILINE | re.DOTALL
)


def parse_conflict_markers(content: str) -> list[ConflictRegion]:
    """Parse conflict markers from file content.

    Args:
        content: File content with git conflict markers

    Returns:
        List of ConflictRegion objects
    """
    regions = []
    for match in CONFLICT_PATTERN.finditer(content):
        regions.append(ConflictRegion(
            start_line=content[:match.start()].count('\n'),
            end_line=content[:match.end()].count('\n'),
            ours=match.group(1),
            theirs=match.group(2),
            original=match.group(0),
        ))
    return regions
```

---

### Subtask T014 – Implement lane resolution (more-done wins)

**Purpose**: Resolve `lane:` field conflicts by choosing the "more done" value (FR-013).

**Steps**:
1. Add `resolve_lane_conflict()` function
2. Define lane priority order
3. Parse lane value from YAML content
4. Return the "more done" value

**Files**:
- `src/specify_cli/merge/status_resolver.py`

**Parallel?**: Yes

**Implementation**:
```python
LANE_PRIORITY = {
    "done": 4,
    "for_review": 3,
    "doing": 2,
    "planned": 1,
}


def extract_lane_value(content: str) -> str | None:
    """Extract lane value from YAML frontmatter content."""
    match = re.search(r'^lane:\s*["\']?(\w+)["\']?\s*$', content, re.MULTILINE)
    return match.group(1) if match else None


def resolve_lane_conflict(ours: str, theirs: str) -> str:
    """Resolve lane conflict by choosing 'more done' value.

    Args:
        ours: Content from HEAD
        theirs: Content from merging branch

    Returns:
        The content with higher lane priority, or ours if equal
    """
    our_lane = extract_lane_value(ours)
    their_lane = extract_lane_value(theirs)

    if not our_lane or not their_lane:
        return ours  # Can't determine, keep ours

    our_priority = LANE_PRIORITY.get(our_lane, 0)
    their_priority = LANE_PRIORITY.get(their_lane, 0)

    return theirs if their_priority > our_priority else ours
```

---

### Subtask T015 – Implement checkbox resolution

**Purpose**: Resolve checkbox conflicts by preferring checked `[x]` (FR-014).

**Steps**:
1. Add `resolve_checkbox_conflict()` function
2. Parse checkbox patterns `- [ ]` and `- [x]`
3. For each line with conflict, prefer checked version

**Files**:
- `src/specify_cli/merge/status_resolver.py`

**Parallel?**: Yes

**Implementation**:
```python
CHECKBOX_PATTERN = re.compile(r'^(\s*-\s*\[)([x ])\](.*)$', re.MULTILINE)


def resolve_checkbox_conflict(ours: str, theirs: str) -> str:
    """Resolve checkbox conflict by preferring checked [x].

    For each line, if either side has [x], use [x].
    """
    our_lines = ours.strip().split('\n')
    their_lines = theirs.strip().split('\n')

    # Build resolved content line by line
    result_lines = []
    max_lines = max(len(our_lines), len(their_lines))

    for i in range(max_lines):
        our_line = our_lines[i] if i < len(our_lines) else ""
        their_line = their_lines[i] if i < len(their_lines) else ""

        our_match = CHECKBOX_PATTERN.match(our_line)
        their_match = CHECKBOX_PATTERN.match(their_line)

        if our_match and their_match:
            # Both have checkboxes - prefer checked
            if their_match.group(2) == 'x' and our_match.group(2) != 'x':
                result_lines.append(their_line)
            else:
                result_lines.append(our_line)
        elif their_match and not our_line.strip():
            # Only theirs has content
            result_lines.append(their_line)
        else:
            # Default to ours
            result_lines.append(our_line)

    return '\n'.join(result_lines)
```

---

### Subtask T016 – Implement history array merge

**Purpose**: Resolve `history:` array conflicts by chronological concatenation (FR-015).

**Steps**:
1. Add `resolve_history_conflict()` function
2. Parse history entries from both sides
3. Merge and sort by timestamp
4. Deduplicate entries

**Files**:
- `src/specify_cli/merge/status_resolver.py`

**Parallel?**: Yes

**Implementation**:
```python
import yaml
from typing import Any


def parse_history_entries(content: str) -> list[dict[str, Any]]:
    """Parse history array from YAML content."""
    try:
        # Extract history section
        match = re.search(r'^history:\s*\n((?:\s+-\s+.*\n?)+)', content, re.MULTILINE)
        if not match:
            return []

        history_yaml = "history:\n" + match.group(1)
        data = yaml.safe_load(history_yaml)
        return data.get("history", []) if data else []
    except Exception:
        return []


def resolve_history_conflict(ours: str, theirs: str) -> str:
    """Resolve history array conflict by merging chronologically.

    Combines entries from both sides, sorts by timestamp, removes duplicates.
    """
    our_entries = parse_history_entries(ours)
    their_entries = parse_history_entries(theirs)

    # Combine all entries
    all_entries = our_entries + their_entries

    # Deduplicate by timestamp+action
    seen = set()
    unique_entries = []
    for entry in all_entries:
        key = (entry.get("timestamp", ""), entry.get("action", ""))
        if key not in seen:
            seen.add(key)
            unique_entries.append(entry)

    # Sort by timestamp
    unique_entries.sort(key=lambda e: e.get("timestamp", ""))

    # Rebuild the history section
    # This is simplified - in practice may need to preserve other frontmatter
    return ours  # Return ours with merged history embedded
```

---

### Subtask T024 – Integrate status resolution into executor

**Purpose**: Call status resolution after each WP merge to auto-resolve conflicts.

**Steps**:
1. Import status_resolver in executor.py
2. After `git merge` call, check for conflicts
3. Call `resolve_status_conflicts()` for matching files
4. If all resolved, `git add` and continue; else pause

**Files**:
- `src/specify_cli/merge/executor.py`
- `src/specify_cli/merge/status_resolver.py`

**Parallel?**: No (integration)

**Main function**:
```python
import subprocess
import fnmatch


def get_conflicted_files(repo_root: Path) -> list[Path]:
    """Get list of files with merge conflicts."""
    result = subprocess.run(
        ["git", "diff", "--name-only", "--diff-filter=U"],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        check=False,
    )
    files = []
    for line in result.stdout.strip().split("\n"):
        if line:
            files.append(repo_root / line)
    return files


def resolve_status_conflicts(repo_root: Path) -> list[ResolutionResult]:
    """Auto-resolve conflicts in status files after merge.

    Args:
        repo_root: Repository root path

    Returns:
        List of ResolutionResult for each processed file
    """
    conflicted = get_conflicted_files(repo_root)
    results = []

    for file_path in conflicted:
        rel_path = str(file_path.relative_to(repo_root))

        # Check if status file
        if not is_status_file(rel_path):
            results.append(ResolutionResult(
                file_path=file_path,
                resolved=False,
                resolution_type="manual_required",
                original_conflicts=1,
                resolved_conflicts=0,
            ))
            continue

        # Try to resolve
        try:
            content = file_path.read_text()
            regions = parse_conflict_markers(content)

            if not regions:
                continue

            resolved_content = content
            resolved_count = 0

            for region in regions:
                # Determine conflict type and resolve
                if "lane:" in region.ours or "lane:" in region.theirs:
                    resolved = resolve_lane_conflict(region.ours, region.theirs)
                    resolution_type = "lane"
                elif CHECKBOX_PATTERN.search(region.ours) or CHECKBOX_PATTERN.search(region.theirs):
                    resolved = resolve_checkbox_conflict(region.ours, region.theirs)
                    resolution_type = "checkbox"
                elif "history:" in region.ours or "history:" in region.theirs:
                    resolved = resolve_history_conflict(region.ours, region.theirs)
                    resolution_type = "history"
                else:
                    continue  # Can't resolve this region

                resolved_content = resolved_content.replace(region.original, resolved)
                resolved_count += 1

            # Write resolved content
            file_path.write_text(resolved_content)

            # Stage the file
            subprocess.run(
                ["git", "add", str(file_path)],
                cwd=str(repo_root),
                check=True,
            )

            results.append(ResolutionResult(
                file_path=file_path,
                resolved=resolved_count == len(regions),
                resolution_type=resolution_type,
                original_conflicts=len(regions),
                resolved_conflicts=resolved_count,
            ))

        except Exception as e:
            results.append(ResolutionResult(
                file_path=file_path,
                resolved=False,
                resolution_type="error",
                original_conflicts=1,
                resolved_conflicts=0,
            ))

    return results
```

---

### Subtask T028 – Ensure cleanup continues on partial failure

**Purpose**: Cleanup should not stop if one file fails to resolve (FR-020).

**Steps**:
1. Review executor cleanup logic
2. Wrap individual file operations in try/except
3. Collect errors, continue with remaining files
4. Report all errors at end

**Files**:
- `src/specify_cli/merge/executor.py`

**Parallel?**: No (integration)

---

### Subtask T029 – Update slash command templates for all agents

**Purpose**: Document new merge features in agent command templates.

**Steps**:
1. Update `.claude/commands/spec-kitty.merge.md`
2. Replicate updates to all 12 agent directories (use AGENT_DIRS from migrations)
3. Document: --resume, --feature, conflict forecast, auto-resolution

**Files**:
- `.claude/commands/spec-kitty.merge.md`
- `.codex/prompts/spec-kitty.merge.md`
- `.opencode/command/spec-kitty.merge.md`
- (and 9 more agent directories)

**Parallel?**: Yes

**Notes**:
- Reference AGENT_DIRS from `src/specify_cli/upgrade/migrations/m_0_9_1_complete_lane_migration.py`
- Key additions to document:
  - Pre-flight validation behavior
  - `--dry-run` now shows conflict forecast
  - Status files auto-resolved
  - `--resume` for interrupted merges
  - `--feature` for main-branch invocation

## Definition of Done Checklist

- [ ] `parse_conflict_markers()` extracts conflict regions
- [ ] `resolve_lane_conflict()` uses "more done" wins logic
- [ ] `resolve_checkbox_conflict()` prefers `[x]`
- [ ] `resolve_history_conflict()` merges chronologically
- [ ] `resolve_status_conflicts()` orchestrates resolution
- [ ] Executor calls resolution after each WP merge
- [ ] Non-status files left for manual resolution
- [ ] Cleanup continues on partial failure
- [ ] All 12 agent templates updated

## Review Guidance

**Acceptance Test**:
1. Create two WPs that both modify same task file's `lane:` field
   - WP01: `lane: for_review`
   - WP02: `lane: done`
2. Merge both - should auto-resolve to `lane: done`
3. No manual intervention required

**Edge Cases**:
- Malformed YAML → skip file, report error
- Conflict in non-YAML content within status file → manual required
- Multiple conflict types in same file → handle each region

## Activity Log

- 2026-01-18T10:37:13Z – system – lane=planned – Prompt generated via /spec-kitty.tasks
- 2026-01-18T11:23:13Z – codex – shell_pid=9049 – lane=doing – Started implementation via workflow command
