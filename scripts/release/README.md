# Release Scripts

This directory contains helper scripts that keep local release checks aligned with the automated PyPI pipeline.

## Scripts

### `validate_release.py`

Validates release readiness by checking version alignment, changelog completeness, and semantic version progression.

**Purpose**: Ensures `pyproject.toml`, `CHANGELOG.md`, and git tags are synchronized before releasing.

**Usage**:

```bash
# Branch mode (for PRs and local development)
python scripts/release/validate_release.py --mode branch

# Tag mode (for release workflow)
python scripts/release/validate_release.py --mode tag --tag v0.2.4

# With custom paths
python scripts/release/validate_release.py \
  --mode branch \
  --pyproject path/to/pyproject.toml \
  --changelog path/to/CHANGELOG.md
```

**Modes**:

- **Branch Mode** (`--mode branch`):
  - Used during development and in PR readiness checks
  - Validates:
    * Version in `pyproject.toml` is valid semantic version (X.Y.Z)
    * CHANGELOG.md contains a populated section for the current version
    * New version > latest git tag (monotonic progression)
  - Does NOT require a tag to be present
  - Exit code: 0 (success) or 1 (validation failed)

- **Tag Mode** (`--mode tag`):
  - Used during release workflow when tag is pushed
  - Validates everything from branch mode, plus:
    * Tag matches version in `pyproject.toml` (e.g., `v0.2.4` matches `0.2.4`)
    * Tag is properly formatted (`v*.*.*`)
  - Tag can be specified via:
    * `--tag` flag: `--tag v0.2.4`
    * `GITHUB_REF_NAME` environment variable (automatic in CI)
    * `GITHUB_REF` environment variable (fallback)
  - Exit code: 0 (success) or 1 (validation failed)

**Options**:

- `--mode {branch,tag}` - Validation mode (required)
- `--tag TAG` - Explicit tag (e.g., v1.2.3), defaults to environment detection in tag mode
- `--pyproject PATH` - Path to pyproject.toml (default: `pyproject.toml`)
- `--changelog PATH` - Path to changelog file (default: `CHANGELOG.md`)
- `--fail-on-missing-tag` - Treat missing tag detection as hard failure

**Output**:

```
Release Validator Summary
-------------------------
Mode: branch
pyproject.toml: /path/to/pyproject.toml
CHANGELOG.md: /path/to/CHANGELOG.md
Version: 0.2.4
Tag: N/A

All required checks passed.
```

**Error Example**:

```
ERROR: Version 0.2.3 does not advance beyond latest tag v0.2.19. (Hint: Select a semantic version greater than previously published releases.)
ERROR: CHANGELOG.md lacks a populated section for 0.2.4. (Hint: Add release notes under a '## 0.2.4' heading.)
```

**Integration**:

- **Local Development**: Run before opening a PR
- **CI (PR)**: `.github/workflows/release-readiness.yml` runs in branch mode
- **CI (Release)**: `.github/workflows/release.yml` runs in tag mode

### `extract_changelog.py`

Extracts the changelog section for a specific version to populate GitHub Release notes.

**Purpose**: Automatically generates release notes from `CHANGELOG.md` during the release workflow.

**Usage**:

```bash
python scripts/release/extract_changelog.py 0.2.4
```

**Output**: The changelog content for version 0.2.4 (without the heading)

**Example**:

Given `CHANGELOG.md`:
```markdown
## [0.2.4] - 2025-11-02

### Added
- Automated PyPI release workflow
- Release readiness guardrails

### Changed
- Updated packaging metadata
```

Command: `python scripts/release/extract_changelog.py 0.2.4`

Output:
```markdown
### Added
- Automated PyPI release workflow
- Release readiness guardrails

### Changed
- Updated packaging metadata
```

**Integration**: Used by `.github/workflows/release.yml` to populate GitHub Release body

## Workflow Integration

### Release Readiness (PR Checks)

`.github/workflows/release-readiness.yml`:
```yaml
- name: Validate release metadata
  run: python scripts/release/validate_release.py --mode branch
```

### Release Publication (Tag Push)

`.github/workflows/release.yml`:
```yaml
- name: Validate release metadata
  run: python scripts/release/validate_release.py --mode tag --tag "${GITHUB_REF_NAME}"

- name: Extract changelog for release
  run: |
    VERSION="${GITHUB_REF_NAME#v}"
    python scripts/release/extract_changelog.py "${VERSION}" > release-notes.md
```

## Local Development Workflow

### Before Opening a PR

```bash
# 1. Bump version in pyproject.toml
vim pyproject.toml  # Change version = "0.2.4"

# 2. Add changelog entry
vim CHANGELOG.md    # Add ## [0.2.4] section

# 3. Run validator
python scripts/release/validate_release.py --mode branch

# 4. If validation passes, test build
python -m build
twine check dist/*

# 5. Clean up
rm -rf dist/ build/

# 6. Open PR
git add pyproject.toml CHANGELOG.md
git commit -m "Prepare release 0.2.4"
git push
```

### Dry Run a Tag Release Locally

```bash
# Simulate tag mode validation
python scripts/release/validate_release.py --mode tag --tag v0.2.4

# Test changelog extraction
python scripts/release/extract_changelog.py 0.2.4
```

## Troubleshooting

### "Version does not advance beyond latest tag"

**Problem**: Your version is equal to or less than an existing tag.

**Solution**:
1. Check latest tag: `git tag --list 'v*' --sort=-version:refname | head -1`
2. Bump version in `pyproject.toml` to be higher
3. Re-run validator

### "CHANGELOG.md lacks a populated section"

**Problem**: No changelog entry for your version, or the entry is empty.

**Solution**:
1. Add section to `CHANGELOG.md`:
   ```markdown
   ## [0.2.4] - 2025-11-02

   ### Added
   - Your changes here
   ```
2. Ensure the section has content (not just whitespace)
3. Re-run validator

### "Tag does not match project version"

**Problem**: Tag is `v0.2.4` but `pyproject.toml` has `0.2.5`.

**Solution**:
1. Either update `pyproject.toml` to match the tag
2. Or delete and recreate the tag:
   ```bash
   git tag -d v0.2.4
   git push origin :refs/tags/v0.2.4
   git tag v0.2.5 -m "Release 0.2.5"
   git push origin v0.2.5
   ```

### "No release tag detected"

**Problem**: Running in tag mode but no tag was provided or detected.

**Solution**:
- Use `--tag` flag: `--tag v0.2.4`
- Or set environment variable: `export GITHUB_REF_NAME=v0.2.4`

## Dependencies

The validator uses minimal dependencies for portability:

- **Python 3.11+** (uses `tomllib` from stdlib)
- **Fallback**: `tomli` package for older Python versions (if needed)

No external packages required for basic operation. The script works in CI without additional installation beyond build tooling.

## Testing

Run the validator test suite:

```bash
python -m pytest tests/release/test_validate_release.py -v
```

Test coverage includes:
- Branch mode success with version bump
- Branch mode failure without changelog entry
- Tag mode validation with tag alignment
- Tag mode failure on version regression

## Future Enhancements

Planned scripts (not yet implemented):

- `prepare_testpypi_upload.py`: Publish dry-run builds to TestPyPI before mainline releases
- `rotate_pypi_token.sh`: Automated token rotation helper with checklist

## Reference

- **Documentation**: `docs/releases/readiness-checklist.md`
- **Feature Spec**: `kitty-specs/002-lightweight-pypi-release/spec.md`
- **Workflows**: `.github/workflows/{release,release-readiness,protect-main}.yml`
