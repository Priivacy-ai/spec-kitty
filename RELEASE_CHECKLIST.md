# Release Checklist

Use this checklist to ensure consistent, high-quality releases of spec-kitty.

## Pre-Release Preparation

### Version Planning

- [ ] Determine version number using [Semantic Versioning](https://semver.org/):
  - **Patch** (X.Y.Z): Bug fixes, small improvements
  - **Minor** (X.Y.0): New features, backward compatible
  - **Major** (X.0.0): Breaking changes

### Code Quality

- [ ] Run full test suite: `pytest tests/ -v`
  - All tests passing
  - No unexpected failures
  - Check for XPASS (unexpectedly passing tests that should be reviewed)

- [ ] **CRITICAL: Verify all migrations are registered**:
  ```bash
  pytest tests/specify_cli/upgrade/test_migration_robustness.py::TestMigrationRegistryCompleteness -v
  ```
  - **Why**: Prevents release blocker bug (0.13.2) where migrations existed but weren't imported
  - **Impact**: If this test fails, migrations won't run during `spec-kitty upgrade`
  - **Fix**: Add missing imports to `src/specify_cli/upgrade/migrations/__init__.py`

- [ ] Run linting and formatting checks:
  ```bash
  ruff check .
  ruff format --check .
  ```

- [ ] Verify test coverage for new features:
  ```bash
  pytest tests/ --cov=src/specify_cli --cov-report=term-missing
  ```

### Documentation Updates

- [ ] Update `CHANGELOG.md`:
  - Add new version section with date
  - List all changes under appropriate categories:
    - **Added**: New features
    - **Fixed**: Bug fixes
    - **Changed**: Breaking changes or major updates
    - **Deprecated**: Features marked for removal
    - **Removed**: Removed features
    - **Security**: Security fixes
  - Reference relevant issues/PRs
  - Follow [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) format

- [ ] Update `pyproject.toml`:
  - Bump `version` field to new version number
  - Verify dependencies are up to date
  - Check Python version requirements

- [ ] Review README.md:
  - Ensure installation instructions are current
  - Update version badges if present
  - Verify examples still work

- [ ] Check ADRs (Architecture Decision Records):
  - If new ADR added, verify it's in `architecture/adrs/`
  - Ensure ADR is linked from relevant docs

### Migration Testing (if migrations included)

- [ ] Test migrations on sample projects:
  ```bash
  # Create test project with old version
  spec-kitty init test-project
  cd test-project

  # Upgrade to new version
  spec-kitty upgrade --dry-run  # Preview changes
  spec-kitty upgrade             # Apply migrations
  ```

- [ ] Verify migration idempotency:
  ```bash
  spec-kitty upgrade  # Run again
  # Should report "No migrations needed"
  ```

- [ ] Test migration rollback (if applicable):
  - Verify projects can downgrade safely
  - Check for data loss scenarios

### Agent Compatibility (if agent templates changed)

- [ ] Verify all 12 agents updated:
  - [ ] Claude Code (`.claude/commands/`)
  - [ ] GitHub Copilot (`.github/prompts/`)
  - [ ] GitHub Codex (`.codex/prompts/`)
  - [ ] OpenCode (`.opencode/command/`)
  - [ ] Google Gemini (`.gemini/commands/`)
  - [ ] Cursor (`.cursor/commands/`)
  - [ ] Windsurf (`.windsurf/workflows/`)
  - [ ] Qwen Code (`.qwen/commands/`)
  - [ ] Kilocode (`.kilocode/workflows/`)
  - [ ] Augment Code (`.augment/commands/`)
  - [ ] Roo Cline (`.roo/commands/`)
  - [ ] Amazon Q (`.amazonq/prompts/`)

- [ ] Test slash commands with at least 2 different agents:
  ```bash
  # In a test project with agent configured
  /spec-kitty.specify
  /spec-kitty.plan
  /spec-kitty.tasks
  /spec-kitty.implement
  /spec-kitty.review
  ```

### Breaking Changes Review

If this is a major or minor version with breaking changes:

- [ ] Document breaking changes in CHANGELOG.md "Changed" section
- [ ] Create migration guide if needed (e.g., `docs/upgrading-to-X.Y.0.md`)
- [ ] Add deprecation warnings for features to be removed in next major version
- [ ] Update examples in documentation to reflect breaking changes

## Release Process

### 1. Create Release Branch

```bash
git checkout -b release/X.Y.Z
```

### 2. Commit Version Bump

```bash
git add pyproject.toml CHANGELOG.md
git commit -m "chore: Bump version to X.Y.Z"
```

### 3. Push and Create Pull Request

```bash
git push origin release/X.Y.Z
gh pr create --title "Release X.Y.Z: [Brief description]" \
             --body "$(cat <<'EOF'
## Release X.Y.Z

### Summary
[Brief description of what's in this release]

### Checklist
- [x] Version bumped in pyproject.toml
- [x] CHANGELOG.md updated
- [x] All tests passing
- [x] Migrations tested
- [x] Documentation updated

### Testing
- Tested on: [Python versions]
- Tested agents: [List agents tested]
- Tested migrations: [Yes/No]

### Breaking Changes
[List any breaking changes or "None"]
EOF
)" \
             --base main
```

### 4. Wait for CI and Review

- [ ] GitHub Actions "Release Readiness Check" passes:
  - Version properly bumped
  - CHANGELOG.md has entry for new version
  - Tests pass
  - Package builds successfully

- [ ] Get approval from maintainer
- [ ] Address any review feedback

### 5. Merge Release PR

- [ ] Use "Merge commit" strategy (NOT squash)
  - Preserves commit history
  - Important for changelog generation

```bash
# After approval, merge via GitHub UI or:
gh pr merge --merge --delete-branch
```

### 6. Create and Push Release Tag

```bash
git checkout main
git pull origin main
git tag -a vX.Y.Z -m "Release vX.Y.Z

[Brief description of what's in this release]

Key changes:
- [Feature 1]
- [Feature 2]
- [Bug fix 1]
"
git push origin vX.Y.Z
```

### 7. Monitor Automated Publishing

- [ ] Watch GitHub Actions workflow: `.github/workflows/release.yml`
  ```bash
  gh run watch
  ```

- [ ] Verify workflow completes successfully:
  - Tests pass
  - Package builds
  - Published to PyPI
  - GitHub release created

- [ ] Check PyPI release:
  ```bash
  # Wait a few minutes for PyPI to update
  pip install --upgrade spec-kitty-cli
  spec-kitty --version  # Should show new version
  ```

- [ ] Verify GitHub release created:
  ```bash
  gh release view vX.Y.Z
  ```

## Post-Release Verification

### Installation Testing

- [ ] Test fresh installation:
  ```bash
  pip install --upgrade spec-kitty-cli
  spec-kitty --version
  spec-kitty init test-project
  cd test-project
  spec-kitty --help
  ```

- [ ] Test upgrade from previous version:
  ```bash
  pip install spec-kitty-cli==X.Y.[Z-1]  # Previous version
  spec-kitty init old-project
  pip install --upgrade spec-kitty-cli
  cd old-project
  spec-kitty upgrade
  ```

### Documentation

- [ ] Update any external documentation sites
- [ ] Post release announcement (if major/minor version):
  - GitHub Discussions
  - Project website
  - Social media (if applicable)

### Issue Cleanup

- [ ] Close resolved issues with release version:
  ```
  Fixed in vX.Y.Z
  ```

- [ ] Update project board / milestones:
  - Move completed issues to "Done"
  - Create next milestone if needed

## Rollback Procedure (if needed)

If critical issues discovered after release:

### Option 1: Hot Fix Release

1. Create hotfix branch from tag:
   ```bash
   git checkout -b hotfix/X.Y.Z+1 vX.Y.Z
   ```

2. Fix issue, commit, test

3. Follow release process for X.Y.Z+1

### Option 2: Yank Release (PyPI)

**Only for critical security issues or broken installations**

```bash
# Yank from PyPI (makes version invisible to pip install)
# Contact PyPI maintainers or use PyPI web interface
```

**Note:** Yanking should be avoided. Prefer hotfix releases.

## Version-Specific Checklists

### For Research Mission Changes (0.13.0+)

- [ ] Test CSV schema validation:
  - evidence-log.csv schema enforcement
  - source-register.csv schema enforcement
  - Detection migration informational output

- [ ] Verify agent templates updated:
  - Research CSV Schemas section present
  - Canonical schemas documented
  - Append-only examples included

### For Agent Management Changes (0.12.0+)

- [ ] Test config-driven behavior:
  ```bash
  spec-kitty agent config list
  spec-kitty agent config add claude
  spec-kitty agent config remove codex
  spec-kitty agent config status
  spec-kitty agent config sync
  ```

- [ ] Verify migrations respect agent config
- [ ] Test with projects with/without config.yaml

### For Workspace-per-WP Changes (0.11.0+)

- [ ] Test workspace creation per work package
- [ ] Test dependency graph handling
- [ ] Test parallel WP execution
- [ ] Test merge workflow with multiple WPs

## Common Gotchas

### Migration Issues

- **Migration not detected**: Ensure migration is registered with `@MigrationRegistry.register`
- **Migration runs multiple times**: Check idempotency, should be safe to run repeatedly
- **Migration breaks existing projects**: Always test on sample projects before release

### Version Mismatch

- **PyPI shows old version**: Wait 5-10 minutes for PyPI to update indexes
- **Local installation wrong version**: Clear pip cache: `pip cache purge`

### CI Failures

- **Tests timeout**: Check for infinite loops in new code
- **Import errors**: Verify package structure in `pyproject.toml`
- **Release workflow fails**: Check `PYPI_API_TOKEN` secret is set

### Test Environment Differences (Lessons from v0.13.6)

**Problem**: Tests pass locally but fail in CI with git command errors.

**Common Causes:**

1. **Git Default Branch Name Mismatch**
   ```
   Error: Command '['git', 'branch', 'feature-branch', 'main']' returned non-zero exit status 128
   ```
   - **Cause**: `git init` creates different default branch names in different environments
     - Local (macOS with git 2.30+): Creates "main"
     - CI (Ubuntu with older git): Creates "master"
     - User's machine: Depends on `init.defaultBranch` config

   - **Fix**: Always use `git init -b main` to explicitly set branch name
     ```python
     # ❌ BAD (environment-dependent)
     subprocess.run(["git", "init"], cwd=repo, check=True)

     # ✅ GOOD (explicit)
     subprocess.run(["git", "init", "-b", "main"], cwd=repo, check=True)
     ```

   - **Files affected in v0.13.6**:
     - `tests/unit/test_multi_parent_merge_empty_branches.py`
     - `tests/unit/test_move_task_git_validation.py`

2. **Rich Console Formatting Differences**
   ```
   AssertionError: assert 'exists but is not a valid worktree' in output
   # Output has double spaces: 'exists but is not  a valid worktree'
   ```
   - **Cause**: Rich console adds ANSI color codes; `capsys.readouterr()` strips them but leaves spacing artifacts
   - **Fix**: Normalize whitespace before assertions
     ```python
     import re
     output = re.sub(r'\s+', ' ', captured.out)  # Normalize all whitespace
     assert "expected text" in output
     ```

   - **File affected in v0.13.6**:
     - `tests/specify_cli/test_implement_validation.py`

3. **"PYPI_API_TOKEN not configured" Error (Misleading)**
   - **What it looks like**: GitHub Actions shows "PYPI_API_TOKEN secret is not configured"
   - **What it actually means**: Generic error message from failure handler
   - **Real cause**: Usually test failures or validation errors earlier in workflow
   - **Fix**: Check actual step that failed (tests, validation, build) before assuming it's a token issue
   - **v0.13.6 experience**: Message appeared 3 times, but real issue was git test failures

**Debugging Strategy:**

1. **Add Test Output Capture** (Added in v0.13.6):
   ```yaml
   - name: Run tests
     run: |
       python -m pytest -v --tb=short 2>&1 | tee pytest-output.txt
       exit ${PIPESTATUS[0]}

   - name: Upload test output
     uses: actions/upload-artifact@v4
     if: always()
     with:
       name: pytest-output
       path: pytest-output.txt
       retention-days: 7
   ```

2. **Check System Reminder Messages**: When workflow fails, CI output may include system reminders with actual error details

3. **Test Locally with CI-like Environment**:
   ```bash
   # Simulate CI Python version
   python3.11 -m pytest

   # Simulate CI git version
   git --version
   # If different from local, test with docker:
   docker run -v $(pwd):/code -w /code python:3.11 python -m pytest
   ```

**Preventive Measures:**

- [ ] Always use `git init -b main` in test fixtures
- [ ] Normalize whitespace when testing console output
- [ ] Don't assume default git config matches local environment
- [ ] Test with pytest (not just `PYTHONPATH=src pytest`) to match CI
- [ ] Review system reminder messages in CI output for real errors

## Checklist Summary

Quick reference for minimum release steps:

1. ✅ All tests pass
2. ✅ Version bumped in `pyproject.toml`
3. ✅ CHANGELOG.md updated
4. ✅ Release PR created and approved
5. ✅ Release PR merged (merge commit, not squash)
6. ✅ Tag created and pushed
7. ✅ GitHub Actions workflow completes
8. ✅ PyPI installation verified

---

**Last Updated**: 2026-01-27 (for version 0.13.6)
**Next Review**: After each major or minor release

## Release History Notes

### v0.13.6 (2026-01-27) - Lessons Learned

**Issues Encountered:**
1. Tests passed locally (1733/1733) but failed in CI (5 failed, 5 errors)
2. Git default branch mismatch (local: "main", CI: "master")
3. Rich console formatting created double-space artifacts in assertions
4. Misleading "PYPI_API_TOKEN not configured" error (actual cause: test failures)

**Resolution:**
- Fixed git fixtures: `git init` → `git init -b main`
- Normalized whitespace in assertions: `re.sub(r'\s+', ' ', output)`
- Added pytest output artifact capture for debugging
- Total release attempts: 4
- Time to resolution: ~30 minutes

**Improvements Made:**
- Enhanced release workflow with test output artifacts
- Documented CI environment gotchas
- Added git fixture best practices
- Clarified misleading error messages

**Key Learning**: Always test that new test fixtures work in CI environments with different git/console configurations, not just locally.
