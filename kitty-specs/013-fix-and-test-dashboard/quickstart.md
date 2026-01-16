# Quickstart: Fix and Test Dashboard

## Goal

Add test coverage for dashboard scanner to verify both legacy and new lane formats.

## Key Files

| File | Action |
|------|--------|
| `tests/test_dashboard/test_scanner.py` | ADD new test cases |
| `src/specify_cli/dashboard/scanner.py` | READ ONLY (already working) |
| `src/specify_cli/legacy_detector.py` | READ ONLY (already working) |

## Test Patterns

### Existing Legacy Format Fixture

```python
def _create_feature(tmp_path: Path) -> Path:
    """Creates LEGACY format with tasks/planned/ subdirectory"""
    feature_dir = tmp_path / "kitty-specs" / "001-demo-feature"
    (feature_dir / "tasks" / "planned").mkdir(parents=True)
    # ... creates WP in tasks/planned/WP01-demo.md
```

### New Format Fixture (to add)

```python
def _create_new_format_feature(tmp_path: Path) -> Path:
    """Creates NEW format with flat tasks/ directory"""
    feature_dir = tmp_path / "kitty-specs" / "002-new-feature"
    (feature_dir / "tasks").mkdir(parents=True)
    # ... creates WP in tasks/WP01-demo.md (no subdirectory)
    # Lane determined by frontmatter: lane: doing
```

## Verification Commands

```bash
# Run scanner tests only
pytest tests/test_dashboard/test_scanner.py -v

# Run all dashboard tests
pytest tests/test_dashboard/ -v

# Run with coverage
pytest tests/test_dashboard/test_scanner.py -v --cov=src/specify_cli/dashboard/scanner
```

## Success Checklist

- [ ] New format tests pass
- [ ] Legacy format tests still pass
- [ ] `is_legacy_format()` detection tests pass
- [ ] Edge case tests pass (missing lane defaults to "planned")
