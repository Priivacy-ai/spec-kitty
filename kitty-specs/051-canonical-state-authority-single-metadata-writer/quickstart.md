# Quickstart: Canonical State Authority & Single Metadata Writer

**Feature**: 051-canonical-state-authority-single-metadata-writer

## What Changed

### Before (scattered writes, Activity Log dependency)

```python
# Acceptance read Activity Log body text to check lane state
entries = activity_entries(wp.body)
if entries[-1]["lane"] != "done":
    fail("WP not done")

# meta.json written directly by 18 different code paths
meta_path.write_text(json.dumps(meta, indent=2, sort_keys=True) + "\n")
# ... with inconsistent formatting across sites
```

### After (canonical state, single writer)

```python
# Acceptance reads canonical status snapshot
from specify_cli.status.reducer import materialize
snapshot = materialize(feature_dir)
if snapshot[wp_id].lane != "done":
    fail("WP not done")

# meta.json written through one API
from specify_cli.feature_metadata import record_acceptance
record_acceptance(feature_dir, accepted_by="claude", mode="standard", ...)
```

## Using the Metadata API

### Reading metadata

```python
from specify_cli.feature_metadata import load_meta

meta = load_meta(feature_dir)  # Returns dict or None
```

### Writing metadata (mutation helpers)

```python
from specify_cli.feature_metadata import (
    record_acceptance,
    record_merge,
    finalize_merge,
    set_vcs_lock,
    set_documentation_state,
    set_target_branch,
)

# Record acceptance (both standard and orchestrator use this)
record_acceptance(
    feature_dir,
    accepted_by="claude",
    mode="standard",  # or "orchestrator"
    from_commit="abc123",
    accept_commit="def456",
)

# Record merge
record_merge(
    feature_dir,
    merged_by="claude",
    merged_into="2.x",
    strategy="merge",
    push=True,
)

# Set VCS lock
set_vcs_lock(feature_dir, vcs_type="git", locked_at="2026-03-18T12:00:00+00:00")
```

### Validation

```python
from specify_cli.feature_metadata import validate_meta

errors = validate_meta(meta)
if errors:
    for e in errors:
        print(f"Validation error: {e}")
```

## Key Principles

1. **Canonical state is the only truth**: `status.events.jsonl` for lanes, `meta.json` for metadata
2. **Compatibility views are derived**: frontmatter lane, Activity Log, tasks.md status block — readable but not authoritative
3. **One writer for meta.json**: All mutations go through `feature_metadata.py`
4. **Atomic writes**: temp file + `os.replace()` — no partial corruption
5. **Stable formatting**: `json.dumps(meta, indent=2, ensure_ascii=False, sort_keys=True) + "\n"`
