# Release Scripts

This directory contains helper scripts that keep local release checks aligned with the
automated release pipeline for stable and prerelease releases from `main`.

## Stable Release Scope

- Branch: `main`
- Versioning: stable releases use `X.Y.Z` in `pyproject.toml`
- Tags: `vX.Y.Z`
- Publication targets: GitHub Releases and PyPI

## Prerelease Publish Scope

- Branch: `main`
- Versioning: prereleases use `X.Y.ZaN`, `X.Y.ZbN`, or `X.Y.ZrcN`
- Tags: `vX.Y.ZaN`, `vX.Y.ZbN`, or `vX.Y.ZrcN`
- Publication targets: GitHub Releases and PyPI
- Installer behavior: users must pass `--pre` (or pin the exact prerelease) to `pip`

Branch-mode readiness checks accept both stable and prerelease versions.
Tag-mode publish checks now accept matching prerelease tags as well, and GitHub
marks those releases as prereleases automatically.

## Scripts

### `validate_release.py`

Validates release readiness by checking version alignment, changelog completeness, and
version progression relative to existing tags.

#### Usage

```bash
# Branch mode (for PRs and local development)
python scripts/release/validate_release.py --mode branch --tag-pattern "v*.*.*"

# Tag mode (for release workflow)
python scripts/release/validate_release.py --mode tag --tag v3.0.1 --tag-pattern "v*.*.*"
```

#### What it validates

- `pyproject.toml` version is a valid stable or prerelease version
- `CHANGELOG.md` contains populated section for that version
- Version advances beyond latest existing release tag
- In tag mode: tag matches version (for example `v3.0.1` <-> `3.0.1`, `v3.1.0a0` <-> `3.1.0a0`)

### `extract_changelog.py`

Extracts a version section from `CHANGELOG.md` for GitHub Release notes.

```bash
python scripts/release/extract_changelog.py 2.0.0
```

## Workflow Integration

- PR checks: `.github/workflows/release-readiness.yml`
- Tag releases: `.github/workflows/release.yml` (triggers on stable and prerelease `v*.*.*` tags)

Release workflow sequence:

1. run tests
2. validate release metadata
3. build and verify artifacts
4. extract changelog notes
5. create GitHub Release

## Local Release Workflow

```bash
# 1) prepare version + changelog
vim pyproject.toml   # version = "3.1.0a0" for prerelease, "3.1.0" for stable
vim CHANGELOG.md     # add ## [3.1.0a0] - YYYY-MM-DD (or final ## [3.1.0])

# 2) validate
python scripts/release/validate_release.py --mode branch --tag-pattern "v*.*.*"
python -m pytest
python -m build
twine check dist/*

# 3) clean build artifacts
rm -rf dist/ build/

# 4a) prerelease publish from main
git tag v3.1.0a0 -m "Release 3.1.0a0"
git push origin v3.1.0a0

# 4b) stable publish from main
#     Edit pyproject.toml to "3.1.0" and rename the changelog heading to [3.1.0]
git tag v3.1.0 -m "Release 3.1.0"
git push origin v3.1.0
```

## Troubleshooting

### Version does not advance

```bash
git tag --list 'v*.*.*' --sort=-version:refname | head -1
```

Then bump `pyproject.toml` to a higher stable or prerelease version.

### Missing changelog entry

Add:

```markdown
## [3.0.1] - 2026-03-31
```

with non-empty notes below the heading.

### Tag/version mismatch

If tag and `pyproject.toml` do not match:

```bash
git tag -d v3.0.1
git push origin :refs/tags/v3.0.1
git tag v3.0.1 -m "Release 3.0.1"
git push origin v3.0.1
```

### Installing a prerelease from PyPI

```bash
python -m pip install --upgrade --pre spec-kitty-cli
# or pin an exact build
python -m pip install --upgrade "spec-kitty-cli==3.1.0a0"
```

## Testing

```bash
python -m pytest tests/release -v
```

## Reference

- `RELEASE_CHECKLIST.md`
- `.github/workflows/release.yml`
- `.github/workflows/release-readiness.yml`
