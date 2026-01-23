# ✅ ADR Naming Convention Updated to Date-Based Format

## What Changed

**Old format:** `NNNN-descriptive-title.md` (e.g., `0001-record-architecture-decisions.md`)

**New format:** `YYYY-MM-DD-N-descriptive-title.md` (e.g., `2026-01-23-1-record-architecture-decisions.md`)

---

## Why This Is Better

### Old Format (Sequential Numbers)
- ❌ No chronological context
- ❌ Can't tell when decision was made
- ❌ Less informative

### New Format (Date-Based)
- ✅ Shows when decision was made at a glance
- ✅ Chronological ordering built-in
- ✅ Multiple ADRs per day supported (N = 1, 2, 3...)
- ✅ More informative file names
- ✅ Easier to understand decision timeline

---

## Renamed Files

All 5 ADRs renamed:

| Old Name | New Name |
|----------|----------|
| `0001-record-architecture-decisions.md` | `2026-01-23-1-record-architecture-decisions.md` |
| `0002-explicit-base-branch-tracking.md` | `2026-01-23-2-explicit-base-branch-tracking.md` |
| `0003-centralized-workspace-context-storage.md` | `2026-01-23-3-centralized-workspace-context-storage.md` |
| `0004-auto-merge-multi-parent-dependencies.md` | `2026-01-23-4-auto-merge-multi-parent-dependencies.md` |
| `0005-decorator-based-context-validation.md` | `2026-01-23-5-decorator-based-context-validation.md` |

---

## Updated Documentation

### Files Updated

✅ **All 5 ADR files** - Cross-references updated
✅ **architecture/README.md** - Naming convention documented, ADR table updated
✅ **architecture/ARCHITECTURE_DOCS_GUIDE.md** - Examples updated
✅ **architecture/NAVIGATION_GUIDE.md** - Examples updated
✅ **architecture/adr-template.md** - Template shows new format
✅ **CLAUDE.md** - Project structure updated
✅ **Summary documents** - All references updated

---

## New Naming Convention

### Format

```
YYYY-MM-DD-N-descriptive-title-with-dashes.md
```

### Parts

- **YYYY-MM-DD** - Date when decision was accepted
- **N** - Sequential number for that day (1, 2, 3, 4, ...)
- **descriptive-title** - Lowercase, hyphens, present tense verbs

### Examples

```
2026-01-23-1-record-architecture-decisions.md
2026-01-23-2-explicit-base-branch-tracking.md
2026-02-15-1-use-sqlite-for-local-storage.md
2026-02-15-2-adopt-react-for-ui-framework.md
2026-03-10-1-implement-caching-strategy.md
```

### Creating a New ADR

```bash
# 1. Get today's date
TODAY=$(date +%Y-%m-%d)

# 2. Find highest number for today
LAST_NUM=$(ls architecture/adrs/ | grep "$TODAY" | sed 's/.*-\([0-9]*\)-.*/\1/' | sort -n | tail -1)

# 3. Calculate next number
if [ -z "$LAST_NUM" ]; then
  NEXT_NUM=1  # First ADR today
else
  NEXT_NUM=$((LAST_NUM + 1))  # Increment
fi

# 4. Copy template
cp architecture/adr-template.md architecture/adrs/$TODAY-$NEXT_NUM-your-decision-title.md
```

**Or simply:**
```bash
# Check what exists today
ls architecture/adrs/ | grep 2026-01-23
# Saw: 2026-01-23-1, 2026-01-23-2, ..., 2026-01-23-5

# Next is 6
cp architecture/adr-template.md architecture/adrs/2026-01-23-6-your-decision-title.md
```

---

## Final Structure

```
architecture/
├── README.md                          # Main index
├── ARCHITECTURE_DOCS_GUIDE.md        # Comprehensive guide
├── NAVIGATION_GUIDE.md               # Navigation help
├── adr-template.md                    # Template
└── adrs/                              # 5 ADRs with date-based names
    ├── 2026-01-23-1-record-architecture-decisions.md
    ├── 2026-01-23-2-explicit-base-branch-tracking.md
    ├── 2026-01-23-3-centralized-workspace-context-storage.md
    ├── 2026-01-23-4-auto-merge-multi-parent-dependencies.md
    └── 2026-01-23-5-decorator-based-context-validation.md
```

---

## Test Status

**All tests still passing:** 48/48 ✅

```bash
$ pytest tests/unit/test_base_branch_tracking.py \
         tests/unit/test_multi_parent_merge.py \
         tests/unit/test_context_validation.py -q

============================== 48 passed in 2.36s ==============================
```

No regressions from renaming.

---

## Benefits of Date-Based Naming

1. **Chronological Context** - See when decisions were made
2. **Meaningful Ordering** - Files naturally sort by date
3. **Multiple Per Day** - Can make several decisions in one day
4. **Audit Trail** - Easy to see decision timeline
5. **Self-Documenting** - Filename includes date without looking inside

**Example Timeline:**
```
2026-01-23: 5 decisions (git repo management project)
2026-02-15: 2 decisions (hypothetical future feature)
2026-03-10: 1 decision (another feature)
```

Just by looking at filenames, you can see decision cadence and timeline!

---

## Summary

**Renamed:** All 5 ADR files to date-based format
**Updated:** All cross-references and guide documents
**Format:** `YYYY-MM-DD-N-descriptive-title.md`
**Tests:** All passing ✅
**Status:** Complete and ready for use

The new naming convention provides better chronological context while maintaining sequential ordering within each day.
