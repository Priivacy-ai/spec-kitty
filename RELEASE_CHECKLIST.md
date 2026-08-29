# Release Checklist

Use this checklist for private CLI releases from `main`.

> `main` is the primary release line and publishes private GitHub Releases only
> for the duration of the EXPERIMENTAL programme.
> PyPI, GitHub Actions publishing, signing, and public release visibility are
> out of scope per `PROGRAM.md` §2 and
> `decisions/HIC-PRIVATE-CLI-RELEASES-2026-08-26.md`.
> `1.x-maintenance` is deprecated overall, reserved for critical maintenance only,
> and should not receive new releases during the programme.
> Historical 2.x release notes remain in Git tags and changelog history; new
> stable and prerelease 3.x releases ship from `main`.
>
> **No GitHub Actions in this programme.** The pre-programme `.github/workflows/`
> YAML (including `release.yml` and `release-readiness.yml`) has been deleted
> (PROGRAM.md §2, planning#57). Run release evidence locally, then publish with
> `spec-kitty-planning/bin/release-cli.sh`.

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
- [ ] Confirm no release step depends on PyPI publishing or `.github/workflows/`
  automation during the programme.

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
- [ ] Confirm `.kittify/release/shared-package-compatibility.json` is the
  authoritative 3.2.0 shared-package set and matches `pyproject.toml` plus
  `uv.lock`.
- [ ] If a SaaS consumer pin lands after the CLI candidate commit, rerun the
  shared-package drift workflow or the local drift command against the updated
  SaaS `main` before recording branch-health evidence.
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

### Release-Candidate Hygiene

The charter requires release-candidate verification to include the full CLI
suite and cross-repo behavior evidence. Run these locally from a trusted runner
before tagging; do not rely on the tag-time publish step to run live
canary or cross-repo end-to-end suites.

- [ ] Record the full CLI test-suite result from `pytest tests/ -v`.
- [ ] Run the cross-repo end-to-end suite locally:
  ```bash
  cd ../../spec-kitty-end-to-end-testing
  uv sync
  SPEC_KITTY_ENABLE_SAAS_SYNC=1 uv run pytest tests/ -v
  ```
- [ ] Run the live deployed-dev canary from the trusted-runner profile:
  ```bash
  cd ../../spec-kitty-end-to-end-testing
  ./scripts/run-canary.sh --profile local --phase all
  ```
- [ ] Record the e2e and canary result in the release PR, changelog note, or
  release issue. If either fails or is inconclusive, do not tag until the
  product issue is fixed or an explicit maintainer waiver with an issue link is
  recorded.

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

- [ ] The `Release Readiness Check` and `CI Quality` GitHub Actions jobs these bullets
  historically named no longer exist (`.github/workflows/` deleted, planning#57) — instead,
  record locally-run equivalents (Code Quality section above) and their pass/fail evidence
  in the PR.
- [ ] Confirm shared-package drift against the current SaaS consumer pins using
  `scripts/release/check_shared_package_drift.py` (see Code Quality above), since the
  `Check Shared Package Drift` workflow job no longer exists.
- [ ] The PR satisfies the active repository policy (`PROGRAM.md` §5–§9) — nothing on
  GitHub enforces this; the merge agent's review is the gate.
- [ ] Maintainer approval is recorded.
- [ ] Any release-note or install-doc feedback is resolved.

### 5. Hand Off the Release PR

- [ ] Do not merge it manually. The programme merge agent merges with a merge
      commit after the `PROGRAM.md` §5–§9 gates pass.

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

If this release depends on a newly pinned shared package, make sure the private
release will bundle that adjacent wheel from the exact pinned commit before
tagging the CLI.

### 7. Publish the Private GitHub Release

There is no automated publishing workflow in this programme —
`.github/workflows/release.yml` has been deleted (PROGRAM.md §2, planning#57).
Perform the evidence steps locally, then publish through the private release
script from the planning repo.

- [ ] Run tests (`pytest tests/ -v`).
- [ ] Validate release metadata (`python scripts/release/validate_release.py --mode branch --tag-pattern "v*.*.*"`).
- [ ] Check shared-package drift (`scripts/release/check_shared_package_drift.py`).
- [ ] Prove exact wheel installability with plain `pip` (`scripts/release/check_exact_install.py`).
- [ ] Validate candidate compatibility against the SaaS consumer contract (`scripts/release/check_candidate_consumer_compat.py`).
- [ ] From a checkout of `spec-kitty-planning` on a machine with GitHub release
  upload access, build and publish the private release:
  ```bash
  bin/release-cli.sh vX.Y.Z --repo ../spec-kitty --events-repo ../spec-kitty-events --tracker-repo ../spec-kitty-tracker
  ```
- [ ] Verify `bin/release-cli.sh`:
  - builds the `spec-kitty-cli` wheel from the tag
  - builds each required internal adjacent wheel (`spec-kitty-events`, and
    `spec-kitty-tracker` when the CLI pins it by git direct reference)
  - rewrites the CLI wheel's internal direct-git dependencies to exact adjacent
    wheel versions for the built artifact only
  - proves the wheel set installs in a fresh isolated environment
  - uploads the wheels and release notes to the private GitHub Release
- [ ] Confirm release-candidate hygiene was already recorded before the tag:
  live canary and cross-repo end-to-end suites are required pre-release
  operator evidence, not tag-time publish jobs.
- [ ] If this is a prerelease, confirm GitHub marks the release as `Pre-release`.
- [ ] Verify publication succeeded separately from branch health — a successful
  GitHub Release proves publication only; it does not prove that `main` is green.
- [ ] Re-run the local test/quality/drift commands above against the released commit
  and record the results (or every known failure, with an issue link) before using
  the release as launch-gate evidence — there is no CI Quality / Check Shared
  Package Drift workflow to query for this.
- [ ] Verify the GitHub release payload:
  ```bash
  gh release view vX.Y.Z
  gh release download vX.Y.Z --dir /tmp/spec-kitty-release-check -p "*.whl"
  ```
- [ ] Verify the private release carries every wheel a clean install needs:
  `spec-kitty-cli`, `spec-kitty-events`, and `spec-kitty-tracker` when bundled
  by `bin/release-cli.sh`.

## Post-Release Verification

### Package Availability

- [ ] Verify the private GitHub Release is visible to authenticated teammates and
  includes the wheel set plus release notes:
  ```bash
  gh release view vX.Y.Z -R spec-kitty/EXPERIMENTAL-spec-kitty
  ```
- [ ] Download the private release wheels into a clean directory:
  ```bash
  gh release download vX.Y.Z -R spec-kitty/EXPERIMENTAL-spec-kitty -p "*.whl" -D dist
  ```

### Installation and Upgrade

- [ ] Test a fresh install:
  ```bash
  uv tool install --find-links dist spec-kitty-cli
  spec-kitty --version
  ```
- [ ] Test an exact prerelease install path from the downloaded wheel set:
  ```bash
  uv tool install --find-links dist "spec-kitty-cli==X.Y.ZaN"
  spec-kitty --version
  ```
- [ ] Test upgrade from the previous stable release on a sample project.

### Communication

- [ ] If this is a minor or major release, publish release notes and migration guidance.
- [ ] If release-track policy changed, call it out explicitly:
  - `main` is the stable `3.x` line
  - `1.x-maintenance` is deprecated maintenance-only
  - PyPI is out of scope during the EXPERIMENTAL programme

## Maintenance-Line Policy

- [ ] Only cut `1.x-maintenance` releases for critical fixes.
- [ ] Do not publish `1.x-maintenance` releases during the programme unless a
  critical-fix issue explicitly calls for one.
- [ ] If a `1.x-maintenance` release is needed, use private GitHub tags/releases
  only and state clearly that the line is deprecated.

## Rollback Procedure

If a critical issue is discovered after release:

1. Cut a hotfix from `vX.Y.Z` and release `X.Y.(Z+1)` as soon as practical.
2. If the private GitHub Release artifact is broken and no hotfix is ready yet,
   mark the release as draft or replace the affected asset, then update the
   release notes with the replacement plan.
3. Prefer forward fixes over deleting published tags.

## Common Gotchas

- **Validation fails with "Version does not advance beyond latest tag"**:
  bump `pyproject.toml` to a higher semantic version.
- **Validation fails with "CHANGELOG.md lacks a populated section"**:
  add `## [X.Y.Z]` with real release notes before tagging.
- **Private release publish fails**:
  check that the publishing machine has GitHub release upload access and that
  the release tag matches the CLI version.
- **Fresh install still shows the old version**:
  verify the downloaded wheel directory contains only the intended release
  assets, then reinstall with `uv tool install --force --find-links dist spec-kitty-cli`.
- **Prerelease install does not resolve from the private wheel set**:
  stop and inspect the built wheel's `Requires-Dist`, the adjacent internal
  wheel versions, and any newly pinned shared packages.

---

**Last Updated**: 2026-08-27
