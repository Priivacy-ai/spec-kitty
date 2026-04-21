# Release Checklist

Use this checklist for releases from `main`.

> `main` is the primary release line and publishes both GitHub releases and PyPI packages.
> `1.x-maintenance` is deprecated overall, reserved for critical maintenance only, and should not receive new PyPI releases.
> Historical 2.x release notes remain in Git tags and changelog history; new stable and prerelease 3.x releases ship from `main`.

## Pre-Release Preparation

### Version Planning

- [ ] Choose the version with [Semantic Versioning](https://semver.org/):
  - Patch (`X.Y.Z`): bug fixes and small improvements
  - Minor (`X.Y.0`): new features, backward-compatible platform changes
  - Major (`X.0.0`): breaking changes
- [ ] If cutting a prerelease, use a Python-compatible prerelease suffix (`X.Y.ZaN`, `X.Y.ZbN`, or `X.Y.ZrcN`) and plan to publish the final stable cut later as `X.Y.Z`.
- [ ] Confirm the release is intended for `main`, not `1.x-maintenance`.
- [ ] If the release also changes branch policy, docs, or distribution channels, include that in `CHANGELOG.md`.

### Release-Line Sanity

- [ ] Confirm the default branch is `main`.
- [ ] Confirm `1.x-maintenance` exists and is marked maintenance-only.
- [ ] Confirm open PRs are targeted intentionally:
  - New product work should target `main`.
  - Maintenance-only fixes should target `1.x-maintenance`.
- [ ] Confirm PyPI Trusted Publishing is configured for `spec-kitty-cli` against `.github/workflows/release.yml`.

### Code Quality

- [ ] Run the full test suite:
  ```bash
  pytest tests/ -v
  ```
- [ ] Verify migration registry completeness:
  ```bash
  pytest tests/upgrade/test_migration_robustness.py::TestMigrationRegistryCompleteness -v
  ```
- [ ] Run release validation in branch mode:
  ```bash
  python scripts/release/validate_release.py --mode branch --tag-pattern "v*.*.*"
  ```
- [ ] Run linting and formatting checks appropriate for changed files:
  ```bash
  ruff check .
  ruff format --check .
  ```
- [ ] Build the package and verify metadata:
  ```bash
  python -m build
  twine check dist/*
  ```
- [ ] Verify shared package drift against the current stack:
  ```bash
  python scripts/release/check_shared_package_drift.py \
    --saas-pyproject ../spec-kitty-saas/pyproject.toml \
    --runtime-pyproject /path/to/spec-kitty-runtime/pyproject.toml
  ```
- [ ] Verify the built wheel installs cleanly with plain `pip`:
  ```bash
  python scripts/release/check_exact_install.py --package spec-kitty-cli
  ```
- [ ] Verify the built wheel satisfies the SaaS consumer contract:
  ```bash
  python scripts/release/check_candidate_consumer_compat.py \
    --package spec-kitty-cli \
    --consumer-contract ../spec-kitty-saas/contracts/consumer-compatibility.json
  ```

### Documentation and Metadata

- [ ] Bump `version` in `pyproject.toml`.
- [ ] Add a populated `## [X.Y.Z] - YYYY-MM-DD` section to `CHANGELOG.md`.
- [ ] For prereleases, use the exact prerelease heading (`## [X.Y.ZaN] - YYYY-MM-DD`, etc.).
- [ ] Remove any `tool.uv.override-dependencies` entries for `spec-kitty-*` packages before tagging.
- [ ] Review `README.md` release-track messaging:
  - `main` should be described as the stable `3.x` line.
  - `1.x-maintenance` should be described as deprecated maintenance-only.
- [ ] Review installation docs if distribution channels changed.
- [ ] If new ADRs were added, verify they are filed under the correct versioned architecture path.

### Upgrade and Migration Checks

- [ ] Test upgrade on a representative existing project:
  ```bash
  spec-kitty upgrade --dry-run
  spec-kitty upgrade
  ```
- [ ] Verify idempotency:
  ```bash
  spec-kitty upgrade
  ```
- [ ] If migrations changed agent assets or templates, smoke-test at least two agent integrations.

## Release Process

### 1. Create the Release Branch

```bash
git checkout main
git pull origin main
git checkout -b release/X.Y.Z
```

### 2. Commit Release Metadata

```bash
git add pyproject.toml CHANGELOG.md README.md RELEASE_CHECKLIST.md
git commit -m "chore(release): prepare X.Y.Z"
```

### 3. Push and Open the Release PR

```bash
git push origin release/X.Y.Z
gh pr create --base main --title "Release X.Y.Z" --fill
```

### 4. Wait for CI and Review

- [ ] `Release Readiness Check` passes.
- [ ] `CI Quality` passes or has explicitly accepted non-blocking failures.
- [ ] Maintainer approval is recorded.
- [ ] Any release-note or install-doc feedback is resolved.

### 5. Merge the Release PR

- [ ] Use a linear-history merge strategy that matches branch protection (`rebase` if available).

```bash
gh pr merge --rebase --delete-branch
```

### 6. Tag the Release from `main`

```bash
git checkout main
git pull origin main
git tag -a vX.Y.Z -m "Release vX.Y.Z"
git push origin vX.Y.Z
```

For prereleases, use the exact prerelease tag instead:

```bash
git tag -a vX.Y.ZaN -m "Release vX.Y.ZaN"
git push origin vX.Y.ZaN
```

If this release depends on a newly pinned shared package, release that upstream
package first, verify it is installable from PyPI, and only then tag the CLI.

### 7. Monitor Automated Publishing

- [ ] Watch `.github/workflows/release.yml`:
  ```bash
  gh run watch
  ```
- [ ] Verify the workflow:
  - runs tests
  - validates release metadata
  - checks shared-package drift
  - proves exact wheel installability with plain `pip`
  - validates candidate compatibility against the SaaS consumer contract
  - builds distributions
  - publishes to PyPI
  - creates the GitHub release
- [ ] If this is a prerelease, confirm GitHub marks the release as `Pre-release`.
- [ ] Verify the GitHub release payload:
  ```bash
  gh release view vX.Y.Z
  gh release download vX.Y.Z --dir /tmp/spec-kitty-release-check
  ```

## Post-Release Verification

### Package Availability

- [ ] Verify PyPI shows the new version:
  ```bash
  python -m pip index versions spec-kitty-cli
  ```
- [ ] Verify the GitHub release is public and includes the wheel, sdist, and checksums.
- [ ] If this is a prerelease, verify installation with:
  ```bash
  python -m pip install --upgrade --pre "spec-kitty-cli==X.Y.ZaN"
  ```

### Installation and Upgrade

- [ ] Test a fresh install:
  ```bash
  python -m pip install --force-reinstall spec-kitty-cli==X.Y.Z
  spec-kitty --version
  ```
- [ ] Test an exact prerelease install path in a clean virtualenv:
  ```bash
  python -m venv /tmp/spec-kitty-release-check
  /tmp/spec-kitty-release-check/bin/python -m pip install --upgrade pip
  /tmp/spec-kitty-release-check/bin/python -m pip install "spec-kitty-cli==X.Y.ZaN"
  /tmp/spec-kitty-release-check/bin/spec-kitty --version
  ```
- [ ] Test upgrade from the previous stable release on a sample project.

### Communication

- [ ] If this is a minor or major release, publish release notes and migration guidance.
- [ ] If release-track policy changed, call it out explicitly:
  - `main` is the stable `3.x` line
  - `1.x-maintenance` is deprecated maintenance-only
  - no new `1.x` PyPI releases are planned

## Maintenance-Line Policy

- [ ] Only cut `1.x-maintenance` releases for critical fixes.
- [ ] Do not publish new `1.x` releases to PyPI.
- [ ] If a `1.x-maintenance` release is needed, use GitHub tags/releases only and state clearly that the line is deprecated.

## Rollback Procedure

If a critical issue is discovered after release:

1. Cut a hotfix from `vX.Y.Z` and release `X.Y.(Z+1)` as soon as practical.
2. If the PyPI artifact is broken and no hotfix is ready yet, yank the PyPI release and update the GitHub release notes with the replacement plan.
3. Prefer forward fixes over deleting published tags.

## Common Gotchas

- **Validation fails with "Version does not advance beyond latest tag"**:
  bump `pyproject.toml` to a higher semantic version.
- **Validation fails with "CHANGELOG.md lacks a populated section"**:
  add `## [X.Y.Z]` with real release notes before tagging.
- **PyPI publish fails**:
  check PyPI Trusted Publishing configuration for the workflow and repository, not a legacy token secret.
- **Fresh install still shows the old version**:
  wait a few minutes for package indexes to refresh, then retry with `pip cache purge` if needed.
- **Prerelease install does not resolve**:
  stop and inspect the published dependency metadata, starting with the built
  wheel's `Requires-Dist` and any newly pinned shared packages.

---

**Last Updated**: 2026-04-21
