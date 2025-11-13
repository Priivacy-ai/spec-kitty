# UTF-8 Encoding Validation & Automatic Repair

## Problem

**Symptom:** Dashboard renders blank/crashes when viewing features

**Root Cause:** Markdown files contain Windows-1252 encoded characters (smart quotes, special symbols) that break strict UTF-8 decoding

**Common Sources:**
- LLMs copying smart quotes from specifications
- Copy-paste from Microsoft Word/Outlook
- Text editors with smart quote auto-replacement
- Character substitution in chat interfaces

## Real Example

```
File: data-model.md
Byte 3082: 0x92 (Windows-1252 RIGHT SINGLE QUOTATION MARK)
Expected: ' (ASCII apostrophe 0x27)

Result: Dashboard loader crashes with UnicodeDecodeError
Effect: Entire UI goes blank - no features visible
```

## Solution Architecture

Multi-layered approach addresses the problem at 5 levels:

### Layer 1: Server-Side Resilience ✓

**File:** `src/specify_cli/dashboard/scanner.py`

**Behavior:**
- Dashboard attempts UTF-8 read
- On failure, automatically sanitizes file and retries
- Creates .bak backup before fixing
- Shows error card in UI if auto-fix fails
- Never lets single bad byte crash entire dashboard

**Code:**
```python
from specify_cli.dashboard.scanner import read_file_resilient

content, error = read_file_resilient(file_path, auto_fix=True)
if content is None:
    # Display error card in UI with fix instructions
    pass
```

### Layer 2: Character Sanitization Module ✓

**File:** `src/specify_cli/text_sanitization.py`

**Capabilities:**
- Detects 15+ problematic character types
- Maps each to safe ASCII/UTF-8 equivalent
- Provides file and directory sanitization
- Supports dry-run mode for preview
- Line-precise error reporting

**Character Mappings:**
```python
PROBLEMATIC_CHARS = {
    "\u2018": "'",      # LEFT SINGLE QUOTATION → apostrophe
    "\u2019": "'",      # RIGHT SINGLE QUOTATION → apostrophe
    "\u201c": '"',      # LEFT DOUBLE QUOTATION → straight quote
    "\u201d": '"',      # RIGHT DOUBLE QUOTATION → straight quote
    "\u2013": "--",     # EN DASH → double hyphen
    "\u2014": "---",    # EM DASH → triple hyphen
    "\u00b1": "+/-",    # PLUS-MINUS → +/-
    "\u00d7": "x",      # MULTIPLICATION → x
    "\u00f7": "/",      # DIVISION → /
    "\u2026": "...",    # ELLIPSIS → three periods
    "\u00b0": " degrees", # DEGREE → " degrees"
    "\u00a0": " ",      # NO-BREAK SPACE → space
}
```

**Usage:**
```python
from specify_cli.text_sanitization import sanitize_file

# Check and fix a file
was_modified, error = sanitize_file(
    Path("data-model.md"),
    backup=True,
    dry_run=False
)
```

### Layer 3: CLI Validation Command ✓

**Command:** `spec-kitty validate-encoding`

**Options:**
```bash
# Check single feature (auto-detected from current directory)
spec-kitty validate-encoding

# Check specific feature
spec-kitty validate-encoding --feature 001-my-feature

# Check all features
spec-kitty validate-encoding --all

# Auto-fix issues (creates .bak backups)
spec-kitty validate-encoding --feature 001-my-feature --fix

# Fix without backups
spec-kitty validate-encoding --all --fix --no-backup

# Dry-run to preview changes
spec-kitty validate-encoding --feature 001-my-feature
```

**Output Example:**
```
Checking encoding for feature: 001-user-auth

Files with Encoding Issues: 001-user-auth
┏━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━┓
┃ File             ┃ Status      ┃
┡━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━┩
│ data-model.md    │ Fixed       │
│ research.md      │ Fixed       │
└──────────────────┴─────────────┘

Example issues in data-model.md:
  Line 112, col 45: ''' (U+2019) → "'"
  Line 214, col 12: '"' (U+201C) → '"'
  Line 225, col 8: '±' (U+00B1) → '+/-'
  ... and 12 more

✓ Fixed 2 file(s) with encoding issues.
Backup files (.bak) were created.
```

### Layer 4: Pre-Commit Hook ✓

**File:** `templates/git-hooks/pre-commit-encoding-check`

**Installation:**
```bash
# Manual installation
cp templates/git-hooks/pre-commit-encoding-check .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit

# Or during project setup
# (spec-kitty init automatically installs this hook)
```

**Behavior:**
- Runs automatically before each commit
- Checks only staged .md files
- Blocks commit if encoding errors found
- Shows exact line/column of problematic characters
- Provides fix command to run

**Example Block:**
```
Checking encoding for staged markdown files...
✗ Encoding error in data-model.md at byte 3082
  Found problematic characters (likely Windows-1252 smart quotes)
  Line 112, col 45: ''' (U+2019) → "'"
  Line 214, col 12: '"' (U+201C) → '"'

❌ Commit blocked: Encoding errors detected in markdown files

To fix these issues:
  1. Run: spec-kitty validate-encoding --all --fix
  2. Review the changes
  3. Re-stage the fixed files: git add <files>
  4. Commit again

Or to bypass this check (not recommended):
  git commit --no-verify
```

### Layer 5: LLM Prompt Warnings ✓

**File:** `templates/AGENTS.md`

**Updated Content:**
- Explicit character blacklist with examples
- Real crash examples from production
- Safe alternatives table
- Auto-fix command reference
- Copy-paste best practices

**Key Section:**
```markdown
## 2. UTF-8 Encoding Rule

**When writing ANY markdown, JSON, YAML, CSV, or code files, use ONLY UTF-8 compatible characters.**

❌ **Windows-1252 smart quotes**: " " ' ' (from Word/Outlook/Office)
❌ **Em/en dashes and special punctuation**: — –
❌ **Multiplication sign**: × (0xD7 in Windows-1252)
❌ **Plus-minus sign**: ± (0xB1 in Windows-1252)
❌ **Degree symbol**: ° (0xB0 in Windows-1252)

**Real examples that crashed the dashboard:**
- "User's favorite feature" → "User's favorite feature" (smart quote)
- "Price: $100 ± $10" → "Price: $100 +/- $10"
- "Temperature: 72°F" → "Temperature: 72 degrees F"
```

## Prevention Workflows

### For AI Agents

**In slash command templates:**
```markdown
## Character Encoding Checkpoint

Before writing any files, review your content for:
- Smart quotes (" " ' ')
- Special dashes (— –)
- Mathematical operators (± × ÷)
- Degree symbols (°)

Use ASCII alternatives:
- Quotes: " and '
- Dash: -
- Operators: +/-, x, /
- Temperature: degrees
```

**After file creation:**
```bash
# Validate immediately after writing artifacts
spec-kitty validate-encoding --fix
```

### For Human Developers

**Copy-paste workflow:**
1. Paste into plain-text editor (VS Code, vim, nano)
2. Search for curly quotes and dashes
3. Replace manually or use editor's find-replace:
   - Find: `[""]` → Replace: `"`
   - Find: `['']` → Replace: `'`
4. Save and validate:
   ```bash
   spec-kitty validate-encoding --feature <id> --fix
   ```

**IDE Integration:**
```json
// VS Code settings.json
{
  "editor.autoClosingQuotes": "never",
  "editor.smartQuotePaste": false,
  "[markdown]": {
    "editor.defaultFormatter": "esbenp.prettier-vscode",
    "editor.formatOnSave": true
  }
}
```

## Testing the Solution

### Create Test File with Bad Encoding

```bash
# Create test file with Windows-1252 smart quotes
python3 << 'EOF'
from pathlib import Path

# Write file with cp1252 encoding
content = "User's "favorite" feature costs $100 ± $10"
Path("test-bad-encoding.md").write_bytes(content.encode('cp1252'))
print("Created test-bad-encoding.md with Windows-1252 encoding")
EOF
```

### Test Validation

```bash
# Should detect encoding error
python3 -c "
from pathlib import Path
try:
    Path('test-bad-encoding.md').read_text(encoding='utf-8')
    print('ERROR: Should have failed')
except UnicodeDecodeError as e:
    print(f'SUCCESS: Detected encoding error at byte {e.start}')
"
```

### Test Auto-Fix

```bash
# Fix the file
spec-kitty validate-encoding --fix

# Verify it's now valid UTF-8
python3 -c "
from pathlib import Path
content = Path('test-bad-encoding.md').read_text(encoding='utf-8')
print('SUCCESS: File is now valid UTF-8')
print(f'Content: {content}')
"
# Output should show: User's "favorite" feature costs $100 +/- $10
```

### Test Dashboard Resilience

```bash
# 1. Create feature with bad encoding
mkdir -p kitty-specs/999-encoding-test
echo "User's "test"" > kitty-specs/999-encoding-test/spec.md

# 2. Start dashboard
spec-kitty dashboard

# 3. Visit http://localhost:3000
# Expected: Dashboard shows features, auto-fixes file on access
# No blank page, clear error message if fix fails
```

## Monitoring & Diagnostics

### Check Encoding Health Across All Features

```bash
# Generate report of all encoding issues
spec-kitty validate-encoding --all > encoding-report.txt

# Count affected files
grep "Encoding Error" encoding-report.txt | wc -l

# Auto-fix everything
spec-kitty validate-encoding --all --fix
```

### Dashboard Logs

```bash
# View dashboard encoding errors
tail -f ~/.spec-kitty/dashboard.log | grep -i "encoding\|unicode"

# Expected entries:
# WARNING: UTF-8 decoding failed for data-model.md at byte 3082
# INFO: Attempting to auto-fix encoding for data-model.md
# INFO: Successfully fixed encoding for data-model.md
```

### Git Pre-Commit Testing

```bash
# Create bad file and attempt commit
echo "User's "test"" > spec.md
git add spec.md
git commit -m "Test encoding check"

# Expected: Commit blocked with error details
# Fix and retry:
spec-kitty validate-encoding --fix
git add spec.md
git commit -m "Test encoding check"  # Should succeed
```

## Troubleshooting

### Issue: "Dashboard still blank after fix"

**Diagnosis:**
```bash
# Clear browser cache
# Restart dashboard
spec-kitty dashboard

# Check for remaining encoding errors
spec-kitty validate-encoding --all
```

**Solution:**
```bash
# Force re-scan
rm -rf ~/.spec-kitty/dashboard-cache/
spec-kitty dashboard
```

### Issue: "Auto-fix changed content incorrectly"

**Diagnosis:**
```bash
# Check backup files
ls -la *.bak

# Compare changes
diff data-model.md data-model.md.bak
```

**Solution:**
```bash
# Restore from backup
cp data-model.md.bak data-model.md

# Manual fix with review
spec-kitty validate-encoding --feature 001-test
# Review suggested changes
# Apply manually if needed
```

### Issue: "Pre-commit hook not running"

**Diagnosis:**
```bash
# Check hook exists
ls -la .git/hooks/pre-commit

# Check permissions
stat -f "%A %N" .git/hooks/pre-commit
```

**Solution:**
```bash
# Reinstall hook
cp templates/git-hooks/pre-commit-encoding-check .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit

# Test it
echo "User's test" > test.md
git add test.md
git commit -m "Test"  # Should block
```

## Performance Considerations

**File Reading:**
- First attempt: Strict UTF-8 (fast)
- On error: Sanitize + retry (slower but rare)
- Caching: Dashboard caches successful reads

**Bulk Validation:**
- Parallel processing for `--all` mode
- Progress indicator for large repos
- Skips already-valid files

**Git Hook:**
- Only checks staged .md files
- Skips binary files automatically
- Minimal overhead (~100ms for 10 files)

## Migration Guide

### For Existing Projects

```bash
# 1. Check current encoding health
spec-kitty validate-encoding --all

# 2. Review issues reported
# Backup critical files first!

# 3. Fix all issues
spec-kitty validate-encoding --all --fix

# 4. Verify dashboard works
spec-kitty dashboard

# 5. Install pre-commit hook to prevent future issues
cp templates/git-hooks/pre-commit-encoding-check .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit

# 6. Commit the fixes
git add kitty-specs/
git commit -m "fix: Sanitize Windows-1252 characters in markdown files"
```

### For New Projects

```bash
# spec-kitty init automatically:
# - Copies AGENTS.md with encoding warnings
# - Installs pre-commit hook
# - Configures dashboard with auto-fix enabled

# Just run:
spec-kitty init my-project
```

## API Reference

### Python Module

```python
from specify_cli.text_sanitization import (
    sanitize_markdown_text,
    sanitize_file,
    sanitize_directory,
    detect_problematic_characters,
    PROBLEMATIC_CHARS,
)

# Sanitize text in memory
clean_text = sanitize_markdown_text("User's "test"")
# Returns: User's "test"

# Detect issues
issues = detect_problematic_characters("User's test")
# Returns: [(1, 4, ''', "'")]

# Fix file
was_modified, error = sanitize_file(
    Path("spec.md"),
    backup=True,
    dry_run=False
)

# Fix directory
results = sanitize_directory(
    Path("kitty-specs/001-feature"),
    pattern="**/*.md",
    backup=True,
    dry_run=False
)
```

### Dashboard Scanner

```python
from specify_cli.dashboard.scanner import read_file_resilient

# Read with auto-fix
content, error = read_file_resilient(
    Path("spec.md"),
    auto_fix=True
)

if error:
    print(f"Error: {error}")
else:
    print(f"Content: {content}")
```

## Related Documentation

- [AGENTS.md](../templates/AGENTS.md) - Complete agent rules including encoding
- [Dashboard Guide](../docs/kanban-dashboard-guide.md) - Dashboard troubleshooting
- [Contributing](../CONTRIBUTING.md) - Code quality standards

## Future Enhancements

Potential improvements:
1. Real-time encoding validation in web editor
2. Browser extension for paste sanitization
3. Integration with Prettier/ESLint for markdown
4. Encoding health metrics in dashboard
5. Auto-fix on file save (VS Code extension)
6. Character allow-list mode (stricter than current)
