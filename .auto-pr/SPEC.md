# Spec — Issue #662: Resolve automated CI workflow duplication

> Source: https://github.com/Priivacy-ai/spec-kitty/issues/662

## Problem

Both `release-readiness.yml` and `ci-quality.yml` trigger on PR/push and each runs a large test suite independently. This doubles CI time and GH Actions minutes with no additional signal — the same tests run twice across two different workflows.

## Acceptance criteria

- [x] `release-readiness.yml` does not run pytest when triggered via `workflow_run` from ci-quality on PRs (ci-quality already ran the tests)
- [x] PRs touching release files (pyproject.toml, CHANGELOG.md, scripts/release/**) still trigger release-readiness directly and run targeted release tests
- [x] Release-only checks (metadata validation, packaging, SBOM, vulnerability scan, package drift, install verification) remain and run on all triggers
- [x] Nightly schedule still runs full non-Windows suite standalone (no ci-quality dependency)
- [x] Manual/workflow_dispatch still runs full non-Windows suite standalone

## Approach

1. Remove the three pytest steps from `release-readiness.yml`: `Verify test isolation`, `Run release workflow tests` (PR-only), `Run full non-Windows suite` (non-PR).
2. Add a `ci-quality-pass` job that depends on `ci-quality.yml` completing (PR events only). This job waits for ci-quality and then runs the release-specific validations that ci-quality does NOT perform.
3. Keep all release-specific validations in `release-readiness.yml`: `Validate release metadata`, `Test packaging`, `Fetch compatibility references`, `Validate shared package drift`, `Verify exact installability`, `Validate candidate against SaaS consumer contract`, `Generate readiness summary`.
4. The nightly schedule and manual dispatch skip the `needs:` dependency and run release validations directly — ci-quality has its own nightly schedule.

## Files likely touched

- `.github/workflows/release-readiness.yml` — remove test steps, add ci-quality dependency for PR runs

## Risk / blast radius

- **Scope**: small
- **Breaking**: no — removes redundant test execution only
- **Migration needed**: no

## Test plan

- **Unit**: Verify release-readiness.yml is valid YAML and passes actionlint
- **Integration**: CI runs with this PR show release-readiness depending on ci-quality; both must pass
- **Visual**: N/A

## Out of scope

- Modifying ci-quality.yml (already comprehensive)
- Adding new tests
- Changing release validation logic
