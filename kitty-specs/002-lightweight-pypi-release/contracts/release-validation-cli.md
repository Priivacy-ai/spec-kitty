# Contract: Release Validation Script

## Command
```
python scripts/release/validate_release.py [--tag vX.Y.Z]
```

## Inputs
- `--tag` (optional): Explicit semantic tag to validate against; defaults to the current `GITHUB_REF_NAME` in CI or derives from git history locally.
- Repository files read:
  - `pyproject.toml`
  - `CHANGELOG.md`
  - `.git/refs/tags/*` (for latest annotated tag when `--tag` omitted)

## Outputs
- Exit code `0` when:
  - `pyproject.toml` version matches the semantic tag (including `v` prefix).
  - `CHANGELOG.md` contains a heading for the version and non-empty notes.
  - `pyproject.toml` version is greater than the most recent published tag.
- Exit code `1` when any validation fails. Script prints actionable errors:
  - Missing or malformed tag.
  - Version mismatch between files.
  - Changelog entry absent.
  - Version regression relative to the latest git tag.

## Side Effects
- No files are mutated.
- Standard output lists validation summary; standard error includes failure rationale.

## Acceptance Criteria
- Script MUST run identically in local environments and CI.
- Error messages MUST guide the maintainer to fix version/changelog/tag alignment.
- All failures MUST prevent the publish job from advancing to upload.
