# Release Scripts

This directory contains helper scripts that keep local release checks aligned with the
automated release pipeline for stable releases from `main`.

## Stable Release Scope

- Branch: `main`
- Versioning: stable releases use `X.Y.Z` in `pyproject.toml`
- Tags: `vX.Y.Z`
- Publication targets: GitHub Releases and PyPI

## Testing Prereleases

Branch-mode readiness checks also accept testing prerelease versions such as
`3.1.0a0`, `3.1.0b1`, or `3.1.0rc1` in `pyproject.toml`. This is for
pre-release validation on PRs and `main` before the final stable cut.

Tagged releases remain stable-only. To publish, convert the prerelease to the
final `X.Y.Z` version and tag that exact commit as `vX.Y.Z`.

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

- `pyproject.toml` version is valid stable or testing release version
- `CHANGELOG.md` contains populated section for that version
- Version advances beyond latest existing release tag
- In tag mode: version must be stable and tag matches version (for example `v3.0.1` <-> `3.0.1`)

### `extract_changelog.py`

Extracts a version section from `CHANGELOG.md` for GitHub Release notes.

```bash
python scripts/release/extract_changelog.py 2.0.0
```

## Workflow Integration

- PR checks: `.github/workflows/release-readiness.yml`
- Tag releases: `.github/workflows/release.yml` (triggers on `v*.*.*`)

Release workflow sequence:

1. run tests
2. validate release metadata
3. build and verify artifacts
4. extract changelog notes
5. create GitHub Release

## Local Release Workflow

```bash
# 1) prepare version + changelog
vim pyproject.toml   # version = "3.1.0a0" for testing, "3.1.0" for release
vim CHANGELOG.md     # add ## [3.1.0a0] - YYYY-MM-DD (or final ## [3.1.0])

# 2) validate
python scripts/release/validate_release.py --mode branch --tag-pattern "v*.*.*"
python -m pytest
python -m build
twine check dist/*

# 3) clean build artifacts
rm -rf dist/ build/

# 4) merge to main, then convert to final and tag
#    Edit pyproject.toml to "3.1.0" and rename the changelog heading to [3.1.0]
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

## Testing

```bash
python -m pytest tests/release -v
```

## Reference

- `RELEASE_CHECKLIST.md`
- `.github/workflows/release.yml`
- `.github/workflows/release-readiness.yml`
