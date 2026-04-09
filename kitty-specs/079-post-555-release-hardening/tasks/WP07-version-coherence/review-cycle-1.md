## WP07 Review — Cycle 1

**Reviewer**: Claude Sonnet 4.6 (1M context)
**Date**: 2026-04-09

---

### Summary

FR-601, FR-602, and FR-606 pass cleanly. FR-603/604 partially pass but T032 gate documentation is incomplete. **FR-605 fails**: `proposed_changelog_block` is always empty against this repository.

---

### Issue 1 (BLOCKER): FR-605 — `proposed_changelog_block` is empty against the real repo

**Observed**: Running `spec-kitty agent release prep --channel stable --json` against `/private/tmp/311/spec-kitty` produces `"proposed_changelog_block": ""`.

**Root cause**: `build_changelog_block()` in `src/specify_cli/release/changelog.py` detects accepted WPs via `_is_accepted_wp()`, which looks for `status: done|accepted|merged` in WP frontmatter. But the 3.x status model stores status in `status.events.jsonl`, not in frontmatter. None of the 83 `kitty-specs/` missions have a `status:` field in WP frontmatter, so `build_changelog_block` always returns `("", [])` against this repository.

**Why tests pass but reality fails**: `test_release_payload_draft.py::test_proposed_changelog_block_non_empty_when_missions_present` creates a synthetic WP file with `status: done` in frontmatter via `_write_mission()`. This fixture does not reflect how real 3.x WPs are tracked, so the test passes while the real command produces an empty block.

**FR-605 requirement** (spec.md §7): "produces a non-empty proposed CHANGELOG.md block whose header references `3.1.1`."

**Required fix**: `build_changelog_block()` must be extended to also read `status.events.jsonl` (using `specify_cli.status.store.read_events()` and `specify_cli.status.reducer.materialize()`) to detect WPs with lane `approved` or `done`. Alternatively, if that scope is too large, a minimal fix is to read the final state from `status.json` (the materialized snapshot) if it exists alongside the event log, as it contains `{"WP01": "approved", ...}` per the status model. Either approach ensures the block is non-empty when missions have accepted WPs.

If this fix is out of scope for WP07, the DoD should be explicitly relaxed: remove the `bool(proposed_changelog_block) == True` assertion from the verification criteria and document why the block will always be empty in 3.x pre-release state. The current commit message incorrectly claims "proposed_changelog_block present in JSON output" passes when the value is `""`.

---

### Issue 2 (REQUIRED): T032 — RG-1..RG-8 gate results not individually documented

**Observed**: The commit message records T032 outcomes briefly but does NOT individually verify and document RG-1..RG-8 as required. The WP task prompt provides an explicit example format:

```
WP07: all RG-1..RG-8 gates pass — release ready for v3.1.1

Verified:
RG-1: init coherent (V-1 passed)
RG-2: parser hotfix in place (V-3 passed)
RG-3: planning-artifact canonical (V-4 passed)
RG-4: mission identity safe (V-2 passed)
RG-5: auth refresh fixed (V-5 passed)
RG-6: implement de-emphasized (V-6 passed)
RG-7: repo dogfoods cleanly (V-7 passed)
RG-8: no scope leak (V-8 passed)
```

**Actual commit message** only mentions: "T032 dogfood: pyproject==metadata.yaml==3.1.1a3 (PASS), validate_release.py fails due to version progression (3.1.1a3 tag already exists — expected pre-release state..." and "RG notes: validate_release.py exits 1 on version progression."

RG-2 through RG-8 are not individually verified. Since WP07 depends on WP01–WP06, the implementer should be able to assert each gate based on those WPs' merged work.

---

### What Passes

- **FR-601**: `pyproject.toml` and `.kittify/metadata.yaml` both report `3.1.1a3`. PASS.
- **FR-602**: `load_metadata_yaml_version()` and `validate_metadata_yaml_version_sync()` added, called in `run_validation()` before tag-specific checks. Deliberate mismatch test exits 1 with correct error naming both files. PASS.
- **FR-606**: `changelog_has_entry()` is called at line 385, before the `if args.mode == "tag":` block at line 393, confirming it runs in branch mode. PASS.
- **Tests T7.1/T7.2/T7.3**: 18 tests pass in the correct test environment. PASS.
- **Code quality**: `validate_metadata_yaml_version_sync()` returns `ValidationIssue | None` correctly integrated into `issues.append()` pattern. Clean.

---

### Fix Checklist for Implementer

1. Fix `build_changelog_block()` to read from event log / `status.json` snapshot for 3.x missions so `proposed_changelog_block` is non-empty against this repo. Update `test_release_payload_draft.py` to also cover the event-log path.
2. Update the commit (or add a new commit) with individual RG-1..RG-8 gate verification results as shown in the task template.
3. Verify the corrected `spec-kitty agent release prep --channel stable --json` output shows `bool(proposed_changelog_block) == True`.
