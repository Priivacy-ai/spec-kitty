## File Writing Guidelines - UTF-8 Encoding

**CRITICAL**: All markdown files you create MUST use only UTF-8 compatible characters.

### Character Usage Rules

✅ **USE THESE (UTF-8 safe)**:
- Standard ASCII: a-z, A-Z, 0-9, common punctuation
- Standard emoji: 📊 🔬 📜 ✅ ❌ (these are fine!)
- Unicode symbols typed directly: × ÷ → ← ≈ ≠ ≤ ≥
- Proper UTF-8 quotes: "double" and 'single'
- Accented characters: café naïve Zürich

❌ **NEVER USE (causes encoding errors)**:
- Windows-1252 smart quotes: " " ' ' (from Word/Outlook)
- Copy-pasted content from Microsoft Office without validation
- Characters that appear as `�` or strange symbols
- Byte sequences like `†` `â€™` `â†'` (these are encoding corruption)

### Safe Character Alternatives

| Instead of | Use | UTF-8 Code |
|-----------|-----|------------|
| Smart quotes " " | Standard quotes " | 0x22 |
| Smart quotes ' ' | Standard quotes ' | 0x27 |
| Em dash — | Standard dash - | 0x2D |
| Arrow → (from copy-paste) | ASCII arrow -> or Unicode → | 0xE2 0x86 0x92 |
| Multiplication × (Windows) | Lowercase x or Unicode × | 0xC3 0x97 |
| Bullet • (Word) | Asterisk * or Unicode • | 0xE2 0x80 0xA2 |

### When Writing Files

1. **Type symbols directly** rather than copy-pasting from web/Office
2. **Use markdown syntax** for formatting instead of special characters
3. **Prefer simple ASCII** when possible (-> instead of →)
4. **Validate after writing** if you've copy-pasted anything

### If You Must Copy-Paste

If copying research citations, quotes, or content from external sources:

1. Paste into a plain text editor first
2. Replace any smart quotes with standard quotes
3. Replace em dashes with standard hyphens
4. Verify no `�` or strange symbols appear
5. Then write to the file

### Claude Code Specific

**IMPORTANT**: When using Claude Code's Write or Edit tools:
- The tools handle UTF-8 correctly automatically
- BUT if you copy-paste content from external sources into your prompt, those characters will be preserved in the file
- Always review pasted content for smart quotes and special characters before writing

### Validation

After creating any markdown file, you can validate it:

```bash
# Quick check
python3 -c "open('your-file.md', 'r', encoding='utf-8').read()"

# If no error = file is valid UTF-8
# If UnicodeDecodeError = file has encoding issues

# Or use the validation tool
python scripts/validate_encoding.py kitty-specs/your-feature/
```

### Why This Matters

Files with encoding errors:
- **Won't display in the dashboard** (empty pages)
- **Break API endpoints** (return 0 bytes)
- **Cause silent failures** (no error messages)
- **Waste debugging time** (hard to diagnose)

The dashboard now shows warnings for encoding issues, but prevention is better than recovery!
