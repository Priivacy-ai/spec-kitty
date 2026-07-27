# Quickstart: Lightweight PyPI Release Workflow

Follow these steps to prepare the Spec Kitty CLI for automated PyPI releases.

## 1. Prerequisites
- Python 3.11 installed locally.
- A PyPI account with project owner permissions.
- GitHub Actions enabled for the repository.
- Maintainer access to configure repository secrets and branch protection.

## 2. Generate a PyPI API token
1. Log into https://pypi.org/manage/account/ and create a new token scoped to `spec-kitty-cli` (or `Entire account` if the project has not been registered yet).
2. Copy the generated token immediately—PyPI shows it only once.
3. Store the token in a secure password manager; you will paste it into GitHub in the next step.

## 3. Configure GitHub Actions secret (`PYPI_API_TOKEN`)
1. Navigate to **Settings → Secrets and variables → Actions → New repository secret**.
2. Set Name to `PYPI_API_TOKEN`.
3. Paste the PyPI token value and save.
4. (Optional) Add `PYPI_TEST_API_TOKEN` if you plan to publish to TestPyPI.

## 4. Prepare a release candidate branch
1. Create a feature branch from `main` (e.g., `002-lightweight-pypi-release`).
2. Update `pyproject.toml` with the new semantic version.
3. Add the matching entry to `CHANGELOG.md` and reference planned release notes.
4. Run `python -m pytest` locally and ensure all tests pass.
5. Execute `python scripts/release/validate_release.py` (once implemented) to confirm version, changelog, and tag readiness.

## 5. Merge and tag for release
1. Open a pull request from the feature branch to `main` and ensure readiness checks pass.
2. After merging, create an annotated tag `git tag vX.Y.Z && git push origin vX.Y.Z`.
3. GitHub Actions will trigger the release workflow automatically.

## 6. Monitor the workflow
1. Watch the `.github/workflows/release.yml` run for the new tag.
2. Confirm the job stages succeed: dependency install, test, build (wheel + sdist), publish via `pypa/gh-action-pypi-publish`.
3. If the job fails, review logs; the workflow surfaces actionable errors (version mismatch, missing secret, test failures).

## 7. Verify the published release
1. Visit https://pypi.org/project/spec-kitty-cli/ to confirm the new version is available.
2. Optionally install locally with `pip install spec-kitty-cli==X.Y.Z`.
3. Update release notes in GitHub Releases if you maintain public announcements.

## 8. Rotate secrets periodically
- Schedule a reminder (e.g., every 90 days) to regenerate the PyPI token.
- Update the `PYPI_API_TOKEN` secret and record the rotation date in `docs/releases/readiness-checklist.md`.
