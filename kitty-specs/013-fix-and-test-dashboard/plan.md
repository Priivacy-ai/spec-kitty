# Implementation Plan: Fix and Test Dashboard

**Branch**: `pr/workspace-per-work-package-v0.11.0` | **Date**: 2026-01-16 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/kitty-specs/013-fix-and-test-dashboard/spec.md`

## Summary

Add test coverage for the dashboard scanner to verify both legacy (directory-based) and new (frontmatter-based) lane formats work correctly. The dashboard functionality was verified working via Playwright testing; this feature focuses on automated test coverage to prevent regressions.

## Technical Context

**Language/Version**: Python 3.11+ (existing spec-kitty codebase)
**Primary Dependencies**: pytest, pathlib (existing)
**Storage**: Filesystem only (test fixtures create temporary directories)
**Testing**: pytest with tmp_path fixtures
**Target Platform**: Cross-platform (Linux, macOS, Windows)
**Project Type**: Single project - extending existing test suite

## Constitution Check

*No constitution file exists - no gates to check.*

## Project Structure

### Documentation (this feature)

```
kitty-specs/013-fix-and-test-dashboard/
├── spec.md              # Feature specification
├── plan.md              # This file
├── checklists/
│   └── requirements.md  # Quality checklist
└── tasks/               # Work packages (created by /spec-kitty.tasks)
```

### Source Code (repository root)

```
tests/test_dashboard/
├── test_scanner.py      # MODIFY: Add new format tests alongside existing legacy tests
└── ...

src/specify_cli/dashboard/
├── scanner.py           # Already supports both formats (verified working)
└── ...

src/specify_cli/
└── legacy_detector.py   # Already correctly detects format type
```

**Structure Decision**: Extend existing `tests/test_dashboard/test_scanner.py` with additional test cases. No new files needed.

## Implementation Approach

### Current State (verified via Playwright)

1. Dashboard loads and displays correctly
2. Kanban board shows lanes with correct counts
3. Scanner already handles both formats in production code
4. Only gap: test coverage for new format

### Changes Required

1. **Add fixture for new format features** - Create `_create_new_format_feature()` helper
2. **Add tests for new format scanning** - Test frontmatter-based lane detection
3. **Add tests for edge cases** - Missing lane defaults to "planned", malformed frontmatter handling
4. **Verify legacy tests still pass** - Existing tests should continue working

### Test Cases to Add

| Test Name | Format | What It Verifies |
|-----------|--------|------------------|
| `test_scan_new_format_feature_detects_lanes` | New | Frontmatter `lane:` field is read correctly |
| `test_scan_new_format_default_lane` | New | Missing `lane:` defaults to "planned" |
| `test_scan_new_format_multiple_lanes` | New | Tasks distributed across all 4 lanes correctly |
| `test_is_legacy_format_detects_new` | Both | `is_legacy_format()` returns False for new format |
| `test_is_legacy_format_detects_legacy` | Both | `is_legacy_format()` returns True for legacy format |

## Parallel Work Analysis

*Not applicable - single file modification, single developer.*

## Risk Assessment

**Low risk feature:**

- Only modifying test files, not production code
- Dashboard already verified working via Playwright
- Existing tests provide regression protection for legacy format
- Changes are additive (new tests), not modifications to existing tests
