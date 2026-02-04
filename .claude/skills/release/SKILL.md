---
name: release
description: Cut a new spec-kitty-cli release to PyPI. Handles version bump, CHANGELOG, tagging, and workflow monitoring.
disable-model-invocation: true
argument-hint: "[version]"
---

# Release spec-kitty-cli to PyPI

Cut a release for spec-kitty-cli. If a version is provided as `$ARGUMENTS`, use it. Otherwise, determine the next patch version from the current `pyproject.toml`.

## Pre-flight

1. Confirm you are on the `main` branch. **Tags MUST be created from `main`** — the `2.x` branch has pre-existing test failures that will cause the release workflow to fail.
2. If changes were made on `2.x`, cherry-pick them to `main` first.
3. Run the test that previously caused release failures to verify it passes:
   ```bash
   python -m pytest tests/specify_cli/cli/commands/test_sync.py -v --tb=short
   ```

## Steps

### 1. Version bump

Edit `pyproject.toml` — update the `version` field:
```
version = "X.Y.Z"
```

Use semantic versioning:
- **Patch** (0.13.X): Bug fixes, small improvements
- **Minor** (0.X.0): New features, backward compatible
- **Major** (X.0.0): Breaking changes

### 2. Update CHANGELOG.md

Add a new section **immediately after** `## [Unreleased]`:

```markdown
## [X.Y.Z] - YYYY-MM-DD

### <emoji> <Category>

**Short bold summary**:
- Bullet point details
```

**CHANGELOG categories used in this project** (with emoji headings):
- `### ✨ Added` — New features
- `### 🔧 Improved` — Enhancements to existing features
- `### 🐛 Fixed` — Bug fixes
- `### 💥 Breaking` — Breaking changes
- `### 📝 Architecture` — ADRs, design decisions
- `### 🧹 Maintenance` — Refactoring, dependency updates

Use today's date in ISO format (YYYY-MM-DD).

### 3. Commit

```bash
git add pyproject.toml CHANGELOG.md
git commit -m "chore: Bump version to X.Y.Z"
```

Include any other files that are part of the release (e.g., bug fixes).

### 4. Push to main

```bash
git push origin main
```

If changes also need to be on `2.x`, cherry-pick:
```bash
git checkout 2.x
git cherry-pick <commit-hash>
git push origin 2.x
git checkout main
```

### 5. Tag and push

```bash
git tag -a vX.Y.Z -m "Release vX.Y.Z - Brief description"
git push origin vX.Y.Z
```

### 6. Monitor the release workflow

```bash
# Find the run
unset GITHUB_TOKEN && gh run list --workflow=release.yml --limit=3

# Watch it (blocking)
unset GITHUB_TOKEN && gh run watch <run-id>

# Or check status
unset GITHUB_TOKEN && gh run view <run-id> --json status,conclusion
```

Note: `unset GITHUB_TOKEN` is needed because the env var token may have limited scopes. The keyring token has full `repo` scope.

### 7. Verify

```bash
# Check GitHub release
unset GITHUB_TOKEN && gh release view vX.Y.Z

# Check PyPI (may take 1-2 minutes to propagate)
pip install spec-kitty-cli==X.Y.Z
```

## Troubleshooting

### Release workflow fails — tests

Check the failed run logs:
```bash
unset GITHUB_TOKEN && gh run view <run-id> --log-failed | head -80
```

Common causes:
- **Import errors in tests**: Fix the test, commit, delete the tag, re-tag, push.
- **Pre-existing failures on wrong branch**: The tag was created from `2.x` instead of `main`. Delete tag, switch to main, re-tag.

To delete and re-tag:
```bash
git tag -d vX.Y.Z
git push origin :refs/tags/vX.Y.Z
# Fix the issue, commit, push
git tag -a vX.Y.Z -m "Release vX.Y.Z - Brief description"
git push origin vX.Y.Z
```

### Version/changelog mismatch

The `scripts/release/validate_release.py` script validates that:
- `pyproject.toml` version matches the tag (minus the `v` prefix)
- `CHANGELOG.md` has a populated section for the version
- Version is monotonically increasing vs existing tags

### PYPI_API_TOKEN not configured

This is a generic error message that prints whenever ANY step fails. Check the actual failing step — it's usually the tests, not the token.

### PyPI shows old version after `pip install --upgrade`

PyPI CDN caching can lag. Install the specific version:
```bash
pip install spec-kitty-cli==X.Y.Z
```

## Reference

- Release workflow: `.github/workflows/release.yml`
- Release readiness (PR checks): `.github/workflows/release-readiness.yml`
- Validation script: `scripts/release/validate_release.py`
- Changelog extractor: `scripts/release/extract_changelog.py`
- Full docs: `CONTRIBUTING.md` (Release Process section)
- Feature spec: `kitty-specs/002-lightweight-pypi-release/`
