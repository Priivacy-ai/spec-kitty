# Release Readiness Checklist

This checklist keeps the lightweight PyPI pipeline safe and predictable. Complete every step before tagging a release.

## 1. Feature Branch Validation
- [ ] Branch is up to date with `main`.
- [ ] `pyproject.toml` version bumped using semantic versioning.
- [ ] Matching changelog entry created under `CHANGELOG.md`.
- [ ] New or changed functionality covered by tests where applicable.
- [ ] `python -m pytest` passes locally and in CI.
- [ ] `scripts/release/validate_release.py` reports **READY**.

## 2. Secret & Configuration Audit
- [ ] `PYPI_API_TOKEN` secret defined in repository settings.
- [ ] (Optional) `PYPI_TEST_API_TOKEN` secret configured for dry runs.
- [ ] Last rotation date recorded below (update when rotating):
  - `PYPI_API_TOKEN`: `TODO-ROTATION-DATE`
- [ ] No credentials added to tracked files (`git status` clean of secrets).

## 3. Merge to `main`
- [ ] Pull request reviewed and approved.
- [ ] CI on the merge commit passes (tests + validation job).
- [ ] `main` branch protection rules confirmed active (no direct pushes).

## 4. Tag & Publish
- [ ] Annotated tag created: `git tag vX.Y.Z -m "Release X.Y.Z"`.
- [ ] Tag pushed: `git push origin vX.Y.Z`.
- [ ] GitHub Actions workflow `.github/workflows/release.yml` succeeds.

## 5. Post-Release Verification
- [ ] New version visible on https://pypi.org/project/spec-kitty-cli/.
- [ ] Install verification run: `pip install spec-kitty-cli==X.Y.Z`.
- [ ] Release notes published/updated in repository releases page.
- [ ] Follow-up tasks logged for any automation failures encountered.
