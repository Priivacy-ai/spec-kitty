# Task Metadata Validation & Auto-Repair

## Problem

**Symptom:** Review workflow fails with confusing error messages

**Root Cause:** Work package file locations don't match their frontmatter metadata

**Common Scenario:**
```
File location:  tasks/for_review/WP01-setup.md
Frontmatter:    lane: "planned"
Result:         Review command refuses to process file
```

This happens when:
1. Files are manually moved between directories
2. Git operations restore old file states
3. Multiple agents update same file with race conditions
4. Scripts fail mid-update leaving inconsistent state

## Solution

Automatic detection and repair of metadata inconsistencies.

### CLI Command

```bash
# Check single feature (auto-detected from current directory)
spec-kitty validate-tasks

# Check specific feature
spec-kitty validate-tasks --feature 001-my-feature

# Check all features
spec-kitty validate-tasks --all

# Auto-fix inconsistencies
spec-kitty validate-tasks --fix

# Fix all features
spec-kitty validate-tasks --all --fix
```

### Automatic Integration

The `/spec-kitty.review` command now automatically runs validation before review:

```markdown
## Outline

1. Run prerequisites check
2. **CRITICAL: Validate task metadata consistency**
   - Run `spec-kitty validate-tasks --fix` to auto-repair
   - Ensures frontmatter matches file locations
3. Determine review target
4. Load context
5. Conduct review
```

## How It Works

### Detection

The validator scans all work package files and checks:

1. **Lane Mismatch**: Does `lane:` field match directory?
   ```
   File: tasks/doing/WP02.md
   Lane: "planned"
   ⚠️  MISMATCH: Expected "doing"
   ```

2. **Missing Required Fields**:
   - `work_package_id` must be present
   - `lane` must be present

3. **Invalid Values**:
   - `lane` must be one of: `planned`, `doing`, `for_review`, `done`
   - `work_package_id` must match pattern: `WP\d+`

### Repair

When `--fix` is specified:

1. **Updates frontmatter** to match directory location
2. **Adds activity log entry** documenting the repair:
   ```yaml
   activity_log:
     - timestamp: "2025-11-13T22:00:04Z"
       lane: "for_review"
       agent: "system"
       shell_pid: "12345"
       action: "Auto-repaired lane metadata (was: planned)"
   ```
3. **Preserves all other metadata** - only changes the `lane` field
4. **Creates audit trail** - reviewers can see what was auto-fixed

## Usage Examples

### Example 1: Single Feature Check

```bash
cd .worktrees/001-my-feature
spec-kitty validate-tasks

# Output:
# Checking: 001-my-feature
#
# Task Metadata Mismatches: 001-my-feature
# ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━━┓
# ┃ File                          ┃ Expected Lane ┃ Actual Lane┃ Status     ┃
# ┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━━┩
# │ tasks/for_review/WP01.md      │ for_review    │ planned    │ Needs Fix  │
# │ tasks/doing/WP02.md           │ doing         │ for_review │ Needs Fix  │
# └───────────────────────────────┴───────────────┴────────────┴────────────┘
#
# Found 2 metadata mismatch(es).
# Run with --fix to automatically repair these mismatches.
```

### Example 2: Auto-Fix

```bash
spec-kitty validate-tasks --fix

# Output:
# Checking: 001-my-feature
#
# Task Metadata Mismatches: 001-my-feature
# ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━┓
# ┃ File                          ┃ Expected Lane ┃ Actual Lane┃ Status ┃
# ┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━┩
# │ tasks/for_review/WP01.md      │ for_review    │ planned    │ Fixed  │
# │ tasks/doing/WP02.md           │ doing         │ for_review │ Fixed  │
# └───────────────────────────────┴───────────────┴────────────┴────────┘
#
# Fixed 2 of 2 mismatches
# ✓ Fixed 2 metadata mismatch(es).
```

### Example 3: All Features

```bash
spec-kitty validate-tasks --all --fix

# Output:
# Checking task metadata for 3 features...
#
# Checking: 001-user-auth
#   ✓ No metadata mismatches
#
# Checking: 002-dashboard
# Task Metadata Mismatches: 002-dashboard
# [table showing fixes]
# Fixed 1 of 1 mismatches
#
# Checking: 003-api
#   ✓ No metadata mismatches
#
# Summary:
# Total mismatches found: 1
# Total mismatches fixed: 1
```

## Python API

For programmatic use:

```python
from pathlib import Path
from specify_cli.task_metadata_validation import (
    detect_lane_mismatch,
    repair_lane_mismatch,
    validate_task_metadata,
    scan_all_tasks_for_mismatches,
)

# Check single file
task_file = Path("tasks/for_review/WP01.md")
has_mismatch, expected, actual = detect_lane_mismatch(task_file)
if has_mismatch:
    print(f"Lane mismatch: expected {expected}, got {actual}")

# Repair single file
was_repaired, error = repair_lane_mismatch(
    task_file,
    agent="my-agent",
    shell_pid="12345",
    add_history=True,
    dry_run=False
)
if was_repaired:
    print("Metadata repaired!")

# Validate all metadata for a file
issues = validate_task_metadata(task_file)
for issue in issues:
    print(f"⚠️ {issue}")

# Scan entire feature
feature_dir = Path("kitty-specs/001-my-feature")
mismatches = scan_all_tasks_for_mismatches(feature_dir)
for file_path, (_, expected, actual) in mismatches.items():
    print(f"{file_path}: {actual} → {expected}")
```

## Integration with Workflows

### Review Workflow

**Before:**
1. Agent runs `/spec-kitty.review`
2. Finds file in `tasks/for_review/WP01.md`
3. Reads frontmatter: `lane: "planned"`
4. **ERROR:** "lane must be for_review"
5. Agent manually edits file or runs move script
6. Tries review again

**After:**
1. Agent runs `/spec-kitty.review`
2. **Auto-validation runs:** `spec-kitty validate-tasks --fix`
3. Mismatch detected and fixed automatically
4. Review proceeds normally

### Move Workflow

When using `tasks-move-to-lane.sh`, the script updates:
- File location (moves to new directory)
- Frontmatter `lane` field
- Activity log entry

If the script fails mid-execution, validation can detect and repair the inconsistency.

## Troubleshooting

### Issue: "File not in recognized lane directory"

**Cause:** File is not in `planned/`, `doing/`, `for_review/`, or `done/`

**Solution:** Move file to correct directory manually, then run validation

### Issue: "Multiple mismatches in same file"

**Cause:** File has multiple metadata issues beyond just `lane`

**Solution:**
```bash
# Check all issues
spec-kitty validate-tasks

# Fix lane mismatch
spec-kitty validate-tasks --fix

# Manually fix other issues reported
```

### Issue: "Validation says fixed but still broken"

**Cause:** File may have encoding issues preventing proper save

**Solution:**
```bash
# Check file encoding
file -I tasks/for_review/WP01.md

# Fix encoding if needed
spec-kitty validate-encoding --fix

# Re-run metadata validation
spec-kitty validate-tasks --fix
```

## Prevention Best Practices

1. **Always use move scripts** - Don't manually move files
   ```bash
   # Correct
   tasks-move-to-lane.sh 001-feature WP01 for_review --note "Ready for review"

   # Incorrect
   mv tasks/planned/WP01.md tasks/for_review/
   ```

2. **Run validation after git operations**
   ```bash
   git pull
   spec-kitty validate-tasks --all --fix
   ```

3. **Include in pre-review checklist**
   - Add to review workflow templates
   - Auto-validation now built into `/spec-kitty.review`

4. **Use in CI/CD**
   ```bash
   # In your CI pipeline
   spec-kitty validate-tasks --all
   if [ $? -ne 0 ]; then
       echo "Task metadata inconsistencies detected"
       exit 1
   fi
   ```

## Performance

- **Single feature scan:** < 100ms for 10 work packages
- **All features scan:** < 500ms for 5 features (50 total work packages)
- **Repair operation:** < 50ms per file

## Related Documentation

- [Review Workflow](../templates/commands/review.md)
- [Task Move Script](../scripts/bash/tasks-move-to-lane.sh)
- [Kanban Dashboard](kanban-dashboard-guide.md)

## Future Enhancements

Potential improvements:
1. Auto-validation on file save (VS Code extension)
2. Real-time dashboard highlighting of inconsistencies
3. Batch repair with confirmation prompts
4. Git hook to prevent committing inconsistent metadata
5. Validation of other frontmatter fields (assignee, review_status, etc.)
