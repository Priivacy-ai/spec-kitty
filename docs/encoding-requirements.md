# UTF-8 Encoding Requirements for Spec Kitty

## Overview

All markdown files in Spec Kitty projects **must be encoded as UTF-8**. This includes:
- `spec.md`
- `plan.md`
- `tasks.md`
- `research.md`
- `data-model.md`
- `quickstart.md`
- All files in `contracts/`
- All files in `research/`
- Task prompts in `tasks/*/WP*.md`

## Why UTF-8?

UTF-8 is the universal standard encoding for text files because it:
- Supports all Unicode characters (emoji, accented characters, symbols)
- Is backward compatible with ASCII
- Is the default encoding for modern editors and tools
- Is required by Python 3's text mode file operations

## Common Encoding Issues

### Symptom: Dashboard shows empty pages or "Error reading artifact"

**Cause:** File contains characters that are not valid UTF-8.

**Example error:**
```
UnicodeDecodeError: 'utf-8' codec can't decode byte 0xd7 in position 975
```

### Most Common Issues

| Problem | Cause | Fix |
|---------|-------|-----|
| Byte `0xd7` | Multiplication sign (×) encoded as Windows-1252 | Replace with UTF-8: `0xC3 0x97` |
| Bytes `0x86 0x92` | Arrow (→) as Windows-1252 dagger+quote | Replace with UTF-8: `0xE2 0x86 0x92` |
| Byte `0x93` | Left double quote as Windows-1252 | Replace with UTF-8 quotes |
| Bytes `0x91`, `0x92` | Smart quotes from Word/Windows | Replace with UTF-8 quotes |

### How Files Get Corrupted

1. **Copied from Windows applications** (Word, PowerPoint, etc.)
2. **Edited in tools with non-UTF-8 defaults** (older Windows Notepad)
3. **Terminal copy-paste** from mixed-encoding sources
4. **AI-generated content** that includes special characters

## Detection & Fixing

### Quick Check

```bash
# Check a single file
python3 -c "open('spec.md', 'r', encoding='utf-8').read()"

# If it prints nothing = file is valid UTF-8
# If it throws UnicodeDecodeError = file has encoding issues
```

### Using the Validation Tool

```bash
# Check all markdown files in a feature
python scripts/validate_encoding.py kitty-specs/001-my-feature/

# Check entire project
python scripts/validate_encoding.py --scan-all

# Preview fixes without making changes
python scripts/validate_encoding.py --dry-run kitty-specs/

# Fix all encoding issues automatically
python scripts/validate_encoding.py --fix kitty-specs/
```

### Manual Fix

If you know the source encoding (usually Windows-1252 for copied text):

```python
#!/usr/bin/env python3
# Read with source encoding
with open('broken-file.md', 'rb') as f:
    data = f.read()

# Decode as Windows-1252
text = data.decode('windows-1252', errors='replace')

# Fix common character issues
text = text.replace('\u0086\u0092', '→')  # Arrow
text = text.replace('\u0093', '→')        # Arrow variant
text = text.replace('\u0091', ''')        # Left single quote
text = text.replace('\u0092', ''')        # Right single quote

# Write as UTF-8
with open('broken-file.md', 'w', encoding='utf-8') as f:
    f.write(text)
```

## Dashboard Behavior

When the dashboard encounters encoding errors, it now:

1. **Logs the error** to the server console with file path and byte position
2. **Displays a warning** in the UI: "⚠️ Encoding Error in filename"
3. **Attempts recovery** by reading with `errors='replace'` (shows � for invalid bytes)
4. **Continues functioning** rather than silently failing with empty content

## Prevention

### Editor Setup

Ensure your editor saves files as UTF-8:

- **VS Code**: Default is UTF-8 (check bottom-right status bar)
- **Sublime Text**: Add to settings: `"default_encoding": "UTF-8"`
- **Vim**: Add to .vimrc: `set encoding=utf-8 fileencoding=utf-8`
- **Emacs**: Add to .emacs: `(setq default-buffer-file-coding-system 'utf-8-unix)`

### Pre-commit Hook

Add to `.git/hooks/pre-commit`:

```bash
#!/bin/bash
# Validate UTF-8 encoding before commit

echo "Validating UTF-8 encoding..."

if ! python3 scripts/validate_encoding.py --check kitty-specs/; then
    echo "❌ Encoding errors found. Run 'python scripts/validate_encoding.py --fix kitty-specs/' to fix"
    exit 1
fi

echo "✅ All files are valid UTF-8"
```

Make it executable:
```bash
chmod +x .git/hooks/pre-commit
```

### CI/CD Validation

Add to GitHub Actions workflow:

```yaml
- name: Validate UTF-8 Encoding
  run: python scripts/validate_encoding.py --scan-all
```

## Troubleshooting

### "File shows � characters in dashboard"

This means the file had encoding errors and was read with `errors='replace'`. The � symbol marks where invalid bytes were found.

**Solution:** Run the encoding validation tool to properly convert the file.

### "Copy-paste from browser/email broke my file"

Rich text sources often include smart quotes, em dashes, and other non-ASCII characters.

**Solution:**
1. Paste into a UTF-8 aware editor first
2. Or run `validate_encoding.py --fix` after pasting

### "I need to use special characters"

UTF-8 supports all special characters! Just make sure your editor saves as UTF-8:

- ✅ Multiplication sign: ×  (not x or *)
- ✅ Arrow: → (not ->)
- ✅ Emoji: 🔬 📊 📜
- ✅ Accented characters: café, naïve, Zürich
- ✅ Math symbols: ≈ ≠ ≤ ≥
- ✅ Quotes: "double" 'single' (not "curly" from Word)

## Related Issues

- Dashboard returning empty responses for artifacts
- "Research not found" even though file exists
- Silent failures in API endpoints

All of these are usually caused by encoding errors.

## References

- Python PEP 263: Defining Python Source Code Encodings
- RFC 3629: UTF-8, a transformation format of ISO 10646
- [Wikipedia: Windows-1252](https://en.wikipedia.org/wiki/Windows-1252)
- [Spec Kitty Postmortem: 2025-11-04 Encoding Issues](../kitty-specs/incidents/2025-11-04-encoding-postmortem.md)
