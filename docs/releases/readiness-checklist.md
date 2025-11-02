# Release Readiness Checklist

This checklist keeps the lightweight PyPI pipeline safe and predictable. Complete every step before tagging a release.

## 1. Feature Branch Validation

- [ ] Branch is up to date with `main`
- [ ] `pyproject.toml` version bumped using semantic versioning (major.minor.patch)
- [ ] Matching changelog entry created under `CHANGELOG.md` with format `## [X.Y.Z]`
- [ ] Changelog entry is populated (not empty) with release notes
- [ ] New or changed functionality covered by tests where applicable
- [ ] All tests pass: `python -m pytest`
- [ ] Release validator passes: `python scripts/release/validate_release.py --mode branch`
- [ ] Package builds successfully: `python -m build`
- [ ] Distribution metadata valid: `twine check dist/*`

## 2. Secret & Configuration Audit

- [ ] `PYPI_API_TOKEN` secret defined in repository settings (Settings > Secrets and variables > Actions)
- [ ] Token has appropriate PyPI project permissions (upload to spec-kitty-cli)
- [ ] Last rotation date recorded below (update when rotating):
  - `PYPI_API_TOKEN`: [UPDATE-WHEN-ROTATING]
  - Recommended rotation: Every 6 months or after any security incident
- [ ] No credentials added to tracked files (`git status` clean of secrets)
- [ ] `.env` files (if present) are in `.gitignore`

### How to Create PyPI API Token

1. Log in to https://pypi.org
2. Go to Account Settings > API tokens
3. Click "Add API token"
4. Name: "spec-kitty-cli GitHub Actions"
5. Scope: "Project: spec-kitty-cli" (or "Entire account" for testing)
6. Copy the token (starts with `pypi-`)
7. **IMPORTANT**: Save immediately - you won't see it again!

### How to Add Token to GitHub

1. Go to repository Settings > Secrets and variables > Actions
2. Click "New repository secret"
3. Name: `PYPI_API_TOKEN`
4. Value: Paste the token from PyPI
5. Click "Add secret"

## 3. Pull Request & Pre-Merge Checks

- [ ] Pull request created targeting `main` branch
- [ ] PR description references issue or explains changes
- [ ] All CI checks pass (tests + release-readiness workflow)
- [ ] Release readiness workflow validates:
  - Version bump is monotonic (new version > latest tag)
  - Changelog entry exists and is populated
  - Tests pass
  - Package builds successfully
- [ ] PR reviewed and approved (if using branch protection)
- [ ] No direct pushes to `main` (use PR workflow)

## 4. Merge to `main`

- [ ] Merge PR to `main` (via GitHub UI for merge commit)
- [ ] CI on the merge commit passes
- [ ] `main` branch protection rules active (Settings > Branches):
  - "Require pull request reviews before merging" enabled
  - "Require status checks to pass before merging" enabled
  - Required status check: `release-readiness` (check-readiness job)
- [ ] Protect-main workflow passes (allows PR merges, blocks direct pushes)

## 5. Tag & Publish

- [ ] Pull latest `main`: `git checkout main && git pull origin main`
- [ ] Verify you're on the merge commit: `git log -1`
- [ ] Create annotated tag: `git tag vX.Y.Z -m "Release X.Y.Z"`
  - Tag format MUST be `vX.Y.Z` (e.g., `v0.2.4`, `v1.0.0`)
  - Version MUST match `pyproject.toml`
- [ ] Push tag: `git push origin vX.Y.Z`
- [ ] GitHub Actions workflow `.github/workflows/release.yml` triggered automatically
- [ ] Monitor workflow: Go to Actions tab > "Publish Release"

### What the Release Workflow Does

1. ✅ Checks out code with full git history
2. ✅ Sets up Python 3.11 with pip caching
3. ✅ Installs build tools (build, twine, pytest, etc.)
4. ✅ Runs full test suite
5. ✅ Validates release metadata (tag mode): `python scripts/release/validate_release.py --mode tag --tag vX.Y.Z`
6. ✅ Builds distributions (wheel + sdist)
7. ✅ Checks distributions with twine
8. ✅ Generates SHA256 checksums for audit trail
9. ✅ Uploads build artifacts to GitHub
10. ✅ Extracts changelog section for the version
11. ✅ Creates GitHub Release with:
    - Release notes from changelog
    - Wheel file (.whl)
    - Source distribution (.tar.gz)
    - Checksum file (SHA256SUMS.txt)
12. ✅ Publishes to PyPI using `PYPI_API_TOKEN`

## 6. Post-Release Verification

- [ ] Workflow succeeded (green checkmark in Actions tab)
- [ ] GitHub Release created: https://github.com/spec-kitty/spec-kit/releases
- [ ] New version visible on PyPI: https://pypi.org/project/spec-kitty-cli/
- [ ] Installation verification: `pip install --upgrade spec-kitty-cli`
- [ ] Version check: `spec-kitty --version` shows new version
- [ ] Smoke test: Run basic CLI command to verify functionality
- [ ] Artifacts uploaded (check Actions > Workflow run > Artifacts)

## Troubleshooting

### Validation Fails in Branch Mode

**Error**: "Version X.Y.Z does not advance beyond latest tag vA.B.C"
- **Fix**: Bump version in `pyproject.toml` to be greater than the latest tag
- Check latest tag: `git tag --list 'v*' --sort=-version:refname | head -1`

**Error**: "CHANGELOG.md lacks a populated section for X.Y.Z"
- **Fix**: Add changelog entry with format `## [X.Y.Z]` and add release notes below

### Workflow Fails During Release

**Error**: "PYPI_API_TOKEN secret is not configured"
- **Fix**: Add token to repository secrets (see Section 2)

**Error**: "Tests failed"
- **Fix**: Run tests locally, fix failures, push fix, retag

**Error**: "twine check failed"
- **Fix**: Check `pyproject.toml` metadata, ensure all required fields are present

### Tag Already Exists

If you need to recreate a tag:
```bash
# Delete local tag
git tag -d vX.Y.Z

# Delete remote tag
git push origin :refs/tags/vX.Y.Z

# Create new tag
git tag vX.Y.Z -m "Release X.Y.Z"

# Push new tag
git push origin vX.Y.Z
```

### Direct Push to Main Blocked

**Error**: "Direct push to main branch detected!"
- **Fix**: Create feature branch, cherry-pick changes, open PR
- See protect-main workflow output for detailed instructions

## Workflow Reference

- **Release**: `.github/workflows/release.yml` - Tag-triggered PyPI publish
- **Readiness**: `.github/workflows/release-readiness.yml` - PR validation
- **Protect Main**: `.github/workflows/protect-main.yml` - Direct push guard
- **Validator**: `scripts/release/validate_release.py` - Version/changelog checker
- **Changelog Extractor**: `scripts/release/extract_changelog.py` - GitHub Release notes

## External Resources

- [PyPI Project Page](https://pypi.org/project/spec-kitty-cli/)
- [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)
- [Semantic Versioning](https://semver.org/spec/v2.0.0.html)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [PyPA Publishing Guide](https://packaging.python.org/guides/publishing-package-distribution-releases-using-github-actions-ci-cd-workflows/)
