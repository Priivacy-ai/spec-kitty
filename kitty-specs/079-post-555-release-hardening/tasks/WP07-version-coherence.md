---
work_package_id: WP07
title: Track 7 — Version Coherence and Release Gate Verification
dependencies:
- WP01
- WP02
- WP03
- WP04
- WP05
- WP06
requirement_refs:
- FR-601
- FR-602
- FR-603
- FR-604
- FR-605
- FR-606
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T028
- T029
- T030
- T031
- T032
agent: "claude:opus:reviewer:reviewer"
shell_pid: "10806"
history:
- at: '2026-04-09T07:30:50Z'
  event: created
authoritative_surface: scripts/release/validate_release.py
execution_mode: code_change
mission_slug: 079-post-555-release-hardening
owned_files:
- .kittify/metadata.yaml
- scripts/release/validate_release.py
- src/specify_cli/release/payload.py
- tests/release/**
- pyproject.toml
tags: []
---

# WP07 — Track 7: Version Coherence and Release Gate Verification

**Spec FRs**: FR-601, FR-602, FR-603, FR-604, FR-605, FR-606
**Priority**: FINAL GATE — depends on all prior WPs being merged. Run this last.
**Estimated size**: ~340 lines

## Objective

Align `pyproject.toml` and `.kittify/metadata.yaml` versions. Extend `scripts/release/validate_release.py` with a cross-file sync check. Verify the CHANGELOG-entry-presence check runs in branch mode. Verify the structured draft release artifact. Then run the dogfood acceptance walkthrough to confirm all 8 release gates (RG-1..RG-8) pass against `/private/tmp/311/spec-kitty`.

**Important**: This WP's T028 bumps `.kittify/metadata.yaml` from `3.1.1a2` to `3.1.1a3` (matching `pyproject.toml`). The final bump to `3.1.1` (stripping the alpha suffix) is a **human action at release-cut time** after this WP passes. Do NOT pre-emptively bump to `3.1.1` stable here.

## Context

**Current state** (confirmed by Phase 0 research):
- `pyproject.toml:3` → `version = "3.1.1a3"`
- `.kittify/metadata.yaml:6` → `version: 3.1.1a2` ← **mismatch**
- `CHANGELOG.md` has `## [3.1.1a3] - 2026-04-07` but no `## [3.1.1]` stable entry.

**Existing release infrastructure**:
- `src/specify_cli/release/version.py` — `propose_version()` (pure function)
- `src/specify_cli/release/changelog.py` — `build_changelog_block()`
- `src/specify_cli/release/payload.py` — `build_release_prep_payload(channel, repo_root)` → structured draft
- `src/specify_cli/cli/commands/agent/release.py` — `spec-kitty agent release prep` command
- `scripts/release/validate_release.py` (389 lines) — already validates pyproject + CHANGELOG; does NOT check `.kittify/metadata.yaml`
- `.github/workflows/release-readiness.yml` — already calls `validate_release.py` in branch mode

**Gap**: `validate_release.py` does not check `.kittify/metadata.yaml`.

## Branch Strategy

WP07 must run after WP01–WP06 are merged. Plan in `main`, implement in the lane worktree. Merge back to `main` as the final pre-release commit.

## Subtask Guidance

### T028 — Bump `.kittify/metadata.yaml` version

**File**: `.kittify/metadata.yaml`

**Steps**:

1. Read `.kittify/metadata.yaml`. The file has a `DO NOT EDIT MANUALLY` comment — ignore this for the purposes of this WP (the bump is a controlled, intentional change as part of mission 079).

2. Change `spec_kitty.version` from `3.1.1a2` to `3.1.1a3` (matching the current `pyproject.toml` value):
   ```yaml
   spec_kitty:
     version: 3.1.1a3  # was: 3.1.1a2
   ```

3. Also update `spec_kitty.last_upgraded_at` to the current UTC timestamp.

4. Commit this change with a clear message: `"chore: bump .kittify/metadata.yaml to 3.1.1a3 to match pyproject.toml"`.

**Note**: The `DO NOT EDIT MANUALLY` comment in the file refers to normal use — users should not hand-edit it during regular spec-kitty use. This WP is intentionally editing it as part of a release-hardening mission to fix a known mismatch. That's fine and necessary.

**Validation**:
- `python -c "import yaml; d=yaml.safe_load(open('.kittify/metadata.yaml')); print(d['spec_kitty']['version'])"` → `3.1.1a3`.
- `grep '"version"' pyproject.toml` → `3.1.1a3`.
- They match.

---

### T029 — Add `validate_metadata_yaml_version_sync()` to `validate_release.py`

**File**: `scripts/release/validate_release.py`

**Steps**:

1. Add a new function after the existing `load_pyproject_version()` function:
   ```python
   def load_metadata_yaml_version(repo_root: Path) -> str:
       """Load the spec_kitty.version from .kittify/metadata.yaml."""
       metadata_path = repo_root / ".kittify" / "metadata.yaml"
       if not metadata_path.exists():
           raise ValidationError(f".kittify/metadata.yaml not found at {metadata_path}")
       
       import yaml
       data = yaml.safe_load(metadata_path.read_text())
       version = data.get("spec_kitty", {}).get("version")
       if not version:
           raise ValidationError(
               f".kittify/metadata.yaml does not have a 'spec_kitty.version' field"
           )
       return version


   def validate_metadata_yaml_version_sync(
       pyproject_version: str,
       repo_root: Path,
   ) -> None:
       """Assert .kittify/metadata.yaml version matches pyproject.toml version.
       
       Raises ValidationError if they disagree, with a message naming both files
       and both values. See FR-601, FR-602.
       """
       metadata_version = load_metadata_yaml_version(repo_root)
       if pyproject_version != metadata_version:
           raise ValidationError(
               f"Version mismatch detected:\n"
               f"  pyproject.toml:          {pyproject_version!r}\n"
               f"  .kittify/metadata.yaml:  {metadata_version!r}\n"
               f"\n"
               f"Both files must report the same version before the release can be cut.\n"
               f"Run: # Update .kittify/metadata.yaml spec_kitty.version to {pyproject_version!r}"
           )
   ```

2. In `validate_release.py:main()`, call the new function in branch mode:
   ```python
   pyproject_version = load_pyproject_version(repo_root)
   validate_metadata_yaml_version_sync(pyproject_version, repo_root)  # NEW LINE
   ```
   Place it after `load_pyproject_version()` but before the tag-specific checks.

3. Add appropriate error handling so `ValidationError` propagates and exits non-zero.

**Validation**:
- Running `python scripts/release/validate_release.py` against the working repo with matching versions → exits 0.
- Running against a scratch repo with `.kittify/metadata.yaml` version `3.1.0` while `pyproject.toml` says `3.1.1a3` → exits non-zero with the mismatch message naming both files.

---

### T030 — Verify CHANGELOG-presence check runs in branch mode; verify structured draft

**Files**: `scripts/release/validate_release.py` (verify), `src/specify_cli/release/payload.py` (verify + minor fix if needed)

**Steps — part A (CHANGELOG presence)**:

1. Read `validate_release.py:main()`. Find where `changelog_has_entry()` is called. Confirm it is called in **branch mode** (not only in tag mode). The function at lines 179-194 checks if a `## [VERSION]` header with non-empty content exists in CHANGELOG.md.

2. If `changelog_has_entry()` is only called in tag mode, move the call to branch mode as well (or call it in both modes). The behavior: if the CHANGELOG entry for the current pyproject version does not exist, fail the validation even in branch mode.

3. After making this work: `python scripts/release/validate_release.py` against a repo where CHANGELOG.md does NOT have a `## [3.1.1a3]` entry → exits non-zero with a clear "CHANGELOG entry for version X is missing" message.

**Steps — part B (structured draft artifact)**:

4. Run `spec-kitty agent release prep --channel stable --json` against `/private/tmp/311/spec-kitty`. Verify the output includes a `proposed_changelog_block` field.

5. If `build_release_prep_payload()` does not produce `proposed_changelog_block`, or if the field is empty, make a minimal fix to `src/specify_cli/release/payload.py` to surface it. The fix should be small — the infrastructure already exists in `release/changelog.py` (`build_changelog_block()`).

6. Expected: `proposed_changelog_block` is a non-empty markdown string starting with `## [3.1.1` (or the current alpha version).

**Validation**:
- `spec-kitty agent release prep --channel stable --json | python -m json.tool | grep -A5 "proposed_changelog_block"` → non-empty value.
- Running `validate_release.py` without a CHANGELOG entry → exits non-zero.

---

### T031 — Regression tests for Track 7

**Files**: `tests/release/` (new test files)

**Test T7.1 — Sync check fails on version mismatch**:
```python
# tests/release/test_validate_metadata_yaml_sync.py
def test_validate_metadata_yaml_version_mismatch_fails(tmp_path):
    # Write pyproject.toml with version = "3.1.1"
    (tmp_path / "pyproject.toml").write_text('[project]\nversion = "3.1.1"\n')
    # Write .kittify/metadata.yaml with version: 3.1.1a3
    (tmp_path / ".kittify").mkdir()
    (tmp_path / ".kittify" / "metadata.yaml").write_text(
        "spec_kitty:\n  version: 3.1.1a3\n"
    )
    
    with pytest.raises(ValidationError) as exc_info:
        validate_metadata_yaml_version_sync("3.1.1", tmp_path)
    
    assert "3.1.1" in str(exc_info.value)
    assert "3.1.1a3" in str(exc_info.value)
    assert ".kittify/metadata.yaml" in str(exc_info.value)
    assert "pyproject.toml" in str(exc_info.value)
```

**Test T7.2 — Sync check passes when versions match**:
```python
def test_validate_metadata_yaml_version_match_passes(tmp_path):
    (tmp_path / "pyproject.toml").write_text('[project]\nversion = "3.1.1"\n')
    (tmp_path / ".kittify").mkdir()
    (tmp_path / ".kittify" / "metadata.yaml").write_text(
        "spec_kitty:\n  version: 3.1.1\n"
    )
    # Should not raise
    validate_metadata_yaml_version_sync("3.1.1", tmp_path)
```

**Test T7.3 — CHANGELOG-presence check in branch mode**:
```python
# tests/release/test_validate_changelog_entry.py
def test_changelog_presence_check_fails_without_entry(tmp_path):
    # Setup: repo with matching versions but no CHANGELOG entry for current version
    changelog = "# Changelog\n\n## [3.0.0] - 2025-01-01\n\n### Fixed\n- Old fix\n"
    (tmp_path / "CHANGELOG.md").write_text(changelog)
    (tmp_path / "pyproject.toml").write_text('[project]\nversion = "3.1.1"\n')
    
    # Run validate_release in branch mode
    result = subprocess.run(
        ["python", "scripts/release/validate_release.py"],
        cwd=tmp_path,
        capture_output=True,
    )
    assert result.returncode != 0
    assert b"3.1.1" in result.stderr or b"3.1.1" in result.stdout

def test_changelog_presence_check_passes_with_entry(tmp_path):
    changelog = "# Changelog\n\n## [3.1.1] - 2026-04-09\n\n### Fixed\n- The fix\n"
    # ... setup, run, assert exit 0
```

**Test T7.4 — `build_release_prep_payload` produces valid draft**:
```python
# tests/release/test_release_payload_draft.py
def test_release_prep_payload_has_proposed_changelog_block(tmp_path):
    # Setup: a repo with at least one accepted WP
    # Call build_release_prep_payload(channel="stable", repo_root=tmp_path)
    payload = build_release_prep_payload(channel="stable", repo_root=tmp_path)
    assert "proposed_changelog_block" in payload
    block = payload["proposed_changelog_block"]
    assert isinstance(block, str)
    assert len(block) > 0
    assert "## [" in block  # Has a version header
```

**Test T7.5 — Dogfood command set (gated)**:
```python
# tests/release/test_dogfood_command_set.py
import os
import pytest

@pytest.mark.skipif(
    os.environ.get("SPEC_KITTY_DOGFOOD_TEST") != "1",
    reason="Dogfood tests run only when SPEC_KITTY_DOGFOOD_TEST=1"
)
def test_dogfood_command_set():
    """Verify all advertised core commands run cleanly against the working repo."""
    repo_root = Path("/private/tmp/311/spec-kitty")
    
    commands = [
        ["spec-kitty", "--version"],
        ["spec-kitty", "agent", "tasks", "status", "--mission", "079-post-555-release-hardening"],
    ]
    
    for cmd in commands:
        result = subprocess.run(cmd, cwd=repo_root, capture_output=True, text=True)
        assert result.returncode == 0, (
            f"Command {' '.join(cmd)} failed with exit code {result.returncode}.\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )
        assert "version" not in result.stderr.lower() or "mismatch" not in result.stderr.lower(), (
            f"Version skew error in {' '.join(cmd)}: {result.stderr}"
        )
```

---

### T032 — Dogfood acceptance: run quickstart V-7; verify RG-1..RG-8

**This subtask is a manual verification step**, not a code change.

**Prerequisite**: WP01–WP06 are all merged to `main`. WP07 T028–T031 code is in the lane worktree.

**Steps**:

1. Run the complete §7 and §8 of `quickstart.md` against `/private/tmp/311/spec-kitty`:
   - Version coherence: `python -c "..."` to verify pyproject == metadata.yaml
   - Run `python scripts/release/validate_release.py` → exits 0
   - Run the dogfood command set (5 commands, all exit 0)
   - Run structured draft generator
   - Introduce deliberate mismatch, confirm validate fails

2. Check all 8 release gates from `spec.md §11` (RG-1..RG-8) by running the corresponding verification procedure from the spec (V-1..V-8 in spec.md §14). Document whether each gate passes or fails.

3. Record the result as a commit message in this WP's final commit:
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

4. If any gate fails, DO NOT merge WP07 and DO NOT tag v3.1.1. Open an issue for the failing gate and address it before re-running T032.

**Validation**:
- All 8 RGs pass in a clean run.
- The commit message documents the gate results.

## Definition of Done

- [ ] `.kittify/metadata.yaml` and `pyproject.toml` both report `3.1.1a3`.
- [ ] `python scripts/release/validate_release.py` exits 0 against `/private/tmp/311/spec-kitty` (with CHANGELOG entry present for 3.1.1a3).
- [ ] Validation exits non-zero when versions disagree (T7.1 passes).
- [ ] Validation exits non-zero when CHANGELOG entry is missing (T7.3 passes).
- [ ] `spec-kitty agent release prep --channel stable --json` produces a payload with `proposed_changelog_block` (T7.4 passes).
- [ ] All 4 test files (T7.1–T7.4) pass under `PWHEADLESS=1 pytest tests/release/ -q`.
- [ ] T032: all 8 RGs pass and are documented in the merge commit.
- [ ] `mypy --strict` clean on `validate_release.py` and `release/payload.py` changes.
- [ ] Human release engineer has been briefed: after this WP merges, the next step is to add the `## [3.1.1]` CHANGELOG entry and bump both version files to `3.1.1`, then run `python scripts/release/validate_release.py` one final time before tagging.

## Risks

| Risk | Mitigation |
|------|-----------|
| `DO NOT EDIT MANUALLY` comment in metadata.yaml causes hesitation | It's a user-facing note, not a code constraint. Editing it as part of a controlled release is correct. Add a `# Bumped by mission 079 WP07` comment. |
| `validate_release.py` uses a module-level `ValidationError` that may be local to the file | Import or reference it correctly. If it doesn't exist, define a simple subclass: `class ValidationError(ValueError): pass`. |
| Dogfood command set test (T7.5) is gated and doesn't run in normal CI | The gating is intentional. The full dogfood acceptance is T032 (manual). T7.5 is a stub that can be run explicitly by the release engineer. |
| CHANGELOG has no `## [3.1.1a3]` entry (only `## [3.1.1a2]`) | Check CHANGELOG.md: it currently has `## [3.1.1a3] - 2026-04-07` per Phase 0 research. The check should pass. If it doesn't, the human release engineer adds the entry. |

## Reviewer Guidance

1. Confirm T028 bumps `.kittify/metadata.yaml` to `3.1.1a3`, NOT to `3.1.1` stable (the final bump is a human action).
2. Run `python scripts/release/validate_release.py` against the working repo and confirm it exits 0.
3. Deliberately change `.kittify/metadata.yaml` to `3.1.0` and confirm `validate_release.py` exits non-zero with the mismatch message.
4. Confirm T032 gate results are documented in the merge commit.
5. After WP07 merges, brief the human release engineer: add `## [3.1.1]` to CHANGELOG, bump both version files to `3.1.1`, tag. Do NOT tag without that final human action.

## Activity Log

- 2026-04-09T09:22:28Z – unknown – shell_pid=5789 – Dispatching final gate implementation
- 2026-04-09T09:29:31Z – unknown – shell_pid=5789 – Version coherence fixed (3.1.1a2->3.1.1a3), validate_release.py extended with metadata.yaml sync check (FR-601/602), CHANGELOG check already in branch mode (T030 verified), proposed_changelog_block surfaced in JSON (FR-603), 4 test files (58 tests pass), dogfood clean
- 2026-04-09T09:30:14Z – claude:opus:reviewer:reviewer – shell_pid=8221 – Started review via action command
- 2026-04-09T09:35:08Z – claude:opus:reviewer:reviewer – shell_pid=8221 – Moved to planned
- 2026-04-09T09:44:06Z – claude:opus:reviewer:reviewer – shell_pid=8846 – Cycle 2: FR-605 fixed (changelog block uses event-log status), RG-1..RG-8 all documented and PASS
- 2026-04-09T09:44:41Z – claude:opus:reviewer:reviewer – shell_pid=10806 – Started review via action command
- 2026-04-09T09:47:42Z – claude:opus:reviewer:reviewer – shell_pid=10806 – Review passed cycle 2: FR-605 fixed via event-log detection, all RGs documented and verified, release gate complete
