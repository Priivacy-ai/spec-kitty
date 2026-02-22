# Release Scripts

This directory contains helper scripts that keep local release checks aligned with the
automated GitHub-only release pipeline for the `2.x` branch.

## 2.x Release Scope

- Branch: `2.x`
- Versioning: semantic versions (`X.Y.Z`) in `pyproject.toml`
- Tags: `v2.<minor>.<patch>`
- Publication target: GitHub Releases only (no PyPI publish from `2.x`)

## Scripts

### `validate_release.py`

Validates release readiness by checking version alignment, changelog completeness, and
version progression relative to existing tags.

#### Usage

```bash
# Branch mode (for PRs and local development)
python scripts/release/validate_release.py --mode branch --tag-pattern "v2.*.*"

# Tag mode (for release workflow)
python scripts/release/validate_release.py --mode tag --tag v2.0.0 --tag-pattern "v2.*.*"
```

#### What it validates

- `pyproject.toml` version is valid semantic version (`X.Y.Z`)
- `CHANGELOG.md` contains populated section for that version
- Version advances beyond latest existing release tag
- In tag mode: tag matches version (for example `v2.0.0` <-> `2.0.0`)

### `extract_changelog.py`

Extracts a version section from `CHANGELOG.md` for GitHub Release notes.

```bash
python scripts/release/extract_changelog.py 2.0.0
```

## Workflow Integration

- PR checks: `.github/workflows/release-readiness.yml` (targets `2.x`)
- Tag releases: `.github/workflows/release.yml` (triggers on `v2.*.*`)

Release workflow sequence:

1. run tests
2. validate release metadata
3. build and verify artifacts
4. extract changelog notes
5. create GitHub Release

## Local Release Workflow

```bash
# 1) prepare version + changelog
vim pyproject.toml   # version = "2.0.0"
vim CHANGELOG.md     # add ## [2.0.0] - YYYY-MM-DD

# 2) validate
python scripts/release/validate_release.py --mode branch --tag-pattern "v2.*.*"
python -m pytest
python -m build
twine check dist/*

# 3) clean build artifacts
rm -rf dist/ build/

# 4) merge to 2.x, then tag
git tag v2.0.0 -m "Release 2.0.0"
git push origin v2.0.0
```

## Troubleshooting

### Version does not advance

```bash
git tag --list 'v2.*.*' --sort=-version:refname | head -1
```

Then bump `pyproject.toml` to a higher semantic version.

### Missing changelog entry

Add:

```markdown
## [2.0.0] - 2026-02-22
```

with non-empty notes below the heading.

### Tag/version mismatch

If tag and `pyproject.toml` do not match:

```bash
git tag -d v2.0.0
git push origin :refs/tags/v2.0.0
git tag v2.0.0 -m "Release 2.0.0"
git push origin v2.0.0
```

## Testing

```bash
python -m pytest tests/release -v
```

## Reference

- `RELEASE_CHECKLIST.md`
- `.github/workflows/release.yml`
- `.github/workflows/release-readiness.yml`
