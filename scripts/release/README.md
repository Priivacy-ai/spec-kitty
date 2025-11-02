# Release Helpers

This directory will contain helper scripts that keep local release checks aligned with the automated PyPI pipeline.

## Planned Scripts

- `validate_release.py`: Parses `pyproject.toml`, `CHANGELOG.md`, and the most recent tag to ensure they agree on the release version. Exits non-zero with actionable messages when mismatches are detected.
- (Optional) `prepare_testpypi_upload.py`: Future script to publish dry-run builds to TestPyPI before mainline releases.

## Usage Expectations

Once implemented, maintainers will run `python scripts/release/validate_release.py` on feature branches prior to opening a pull request. GitHub Actions will invoke the same script to guarantee parity between local validation and CI.
