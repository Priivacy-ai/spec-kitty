---
affected_files: []
cycle_number: 2
mission_slug: 075-mission-build-identity-contract-cutover
reproduction_command:
reviewed_at: '2026-04-08T05:33:48Z'
reviewer_agent: unknown
verdict: rejected
wp_id: WP02
---

# WP02 Review Cycle 1 — Changes Requested

Review date: 2026-04-07
Reviewer: claude (automated review)

## Issue 1: Out-of-scope changes to WP01-owned files (BLOCKER)

**Files affected**: `src/specify_cli/status/models.py` and `src/specify_cli/status/validate.py`

These files are owned exclusively by WP01 (Lane A). WP02 must not touch them.

The diff shows three changes to `models.py`:
1. Removed the `from specify_cli.core.identity_aliases import with_tracked_mission_slug_aliases` import
2. In `StatusEvent.from_dict()`: changed `data.get("mission_slug") or data.get("feature_slug", "")` to `data.get("mission_slug", "")`
3. In `StatusSnapshot.to_dict()`: unwrapped the `with_tracked_mission_slug_aliases(...)` call to a plain dict

And one change to `validate.py`:
- Changed the validation message/condition for `mission_slug` (was accepting `feature_slug` as a legacy fallback, now only accepts `mission_slug`)

**How to fix**: Revert all changes to `models.py` and `validate.py`. Use:
```bash
git checkout kitty/mission-075-mission-build-identity-contract-cutover -- src/specify_cli/status/models.py src/specify_cli/status/validate.py
```

WP01 (Lane A) has already handled these files in its own branch. When Lane A merges to main before Lane B, these files will be correctly updated. WP02 must not duplicate or conflict with that work.

## Issue 2: Prohibited compatibility shim in WPMetadata production code (BLOCKER)

**File**: `src/specify_cli/status/wp_metadata.py`, lines 116–121

The `_normalize_legacy_fields` model validator contains this block:

```python
# Legacy: older WP files used 'feature_slug' instead of 'mission_slug'
# Promote to mission_slug and drop the legacy key so extra="forbid" doesn't reject it.
if "feature_slug" in data:
    if not data.get("mission_slug"):
        data["mission_slug"] = data["feature_slug"]
    del data["feature_slug"]
```

This is a runtime compatibility bridge that silently accepts `feature_slug` on every inbound parse of every WP file. It violates C-003 of the feature spec:

> "No compatibility bridge on any live remote-facing surface. Any shim must be upgrade-only and unreachable from normal runtime/public API flows."

`WPMetadata` is used by every WP frontmatter read at runtime — this shim is reachable from normal runtime flows. The spec requires fail-closed behavior: if a WP file still contains `feature_slug` after the migration, parsing should fail with a clear error, not silently coerce it.

**How to fix**: Remove lines 116–121 from `_normalize_legacy_fields`. The `feature_slug` bridge must be removed entirely. Any WP files that still contain `feature_slug` in their frontmatter should be updated by the upgrade migration, not silently coerced at parse time.

After removing those lines, also verify that `extra="forbid"` on the model config ensures `feature_slug` in frontmatter would raise a `ValidationError` (it should, since `feature_slug` is no longer a declared field).

## Summary of required changes

1. Revert `src/specify_cli/status/models.py` to the base branch version
2. Revert `src/specify_cli/status/validate.py` to the base branch version
3. Remove the `feature_slug` compatibility block (lines 116–121) from `_normalize_legacy_fields` in `src/specify_cli/status/wp_metadata.py`
4. Re-run `mypy --strict` and `pytest tests/specify_cli/status/ tests/specify_cli/core/ -v` to verify all acceptance criteria still pass

## Note on WP05 dependency

WP05 depends on WP02. If you rebase WP02 significantly, notify WP05's agent to rebase onto the updated WP02 branch before it continues implementation.
