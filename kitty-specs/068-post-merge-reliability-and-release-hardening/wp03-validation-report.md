# WP03 Diff-Coverage Validation Report

**Validated at commit**: `e361b104cbecf8fb24bf8c9f504d0f0868c14492`
**Workflow path**: `.github/workflows/ci-quality.yml`
**Sample PR**: #452 — Mission 067 squash-merge (the large multi-WP squash that motivated this mission; 43 status events, multiple lane merges collapsed into one commit via `git push` linear-history workaround)

## Critical-path threshold (enforced)

- Threshold: 90%
- Current behavior: hard-fails if diff coverage on critical-path files < 90% (no `continue-on-error` on the step; exits non-zero via `diff-cover --fail-under=90`)
- Critical-path file list source: inline `--include` patterns in the `[ENFORCED] Critical-path diff coverage (90% on core modules)` step (lines 861–869 of `.github/workflows/ci-quality.yml`): `src/kernel/*`, `src/doctrine/*`, `src/charter/*`, `src/specify_cli/status/*`, `src/specify_cli/core/mission_detection.py`, `src/specify_cli/dashboard/handlers/*`, `src/specify_cli/dashboard/scanner.py`, `src/specify_cli/merge/*`, `src/specify_cli/next/*`

## Full-diff threshold (advisory)

- Threshold: none (no `--fail-under` flag)
- Current behavior: emits a `diff-cover` report with `|| true` appended to the shell command, meaning the step always exits 0; the step is prefixed `[ADVISORY]` and named "Full diff coverage report (informational)" — never hard-fails under any circumstance

## Findings

- [x] Critical-path enforce/advisory split is correctly implemented — satisfied by line 839 of ci-quality.yml which names the step `[ENFORCED] Critical-path diff coverage (90% on core modules)` with no `continue-on-error` and a hard `--fail-under=90`, while line 871 names the second step `[ADVISORY] Full diff coverage report (informational)` with `|| true` to suppress exit codes
- [x] Hard-fail surfaces match the intended critical-path file set — satisfied by the `--include` list at lines 861–869 of ci-quality.yml which restricts enforcement to kernel, doctrine, charter, status, mission_detection, dashboard handlers, merge, and next modules (exactly the modules flagged as highest-risk in the mission spec)
- [x] Advisory report is clearly labeled as advisory in CI output — satisfied by the `[ADVISORY]` prefix in the step name at line 871 of ci-quality.yml, which is visible in the GitHub Actions UI step list for every PR run
- [x] Large PRs that meet critical-path coverage but miss full-diff coverage pass the build — satisfied by the `|| true` at line 885 of ci-quality.yml which ensures the full-diff step always exits 0 regardless of coverage percentage; PR #452 (large squash-merge touching many non-critical-path files) passed the diff-coverage job because its changes to non-critical-path surfaces were not subject to the 90% floor

## Decision

**[x] close_with_evidence** — current main already satisfies the policy intent. Issue #455 closed with link to this report.
**[ ] tighten_workflow** — residual mismatch found. Workflow adjusted per FR-012.

## Rationale

Current main's `ci-quality.yml` (validated at commit `e361b104`) implements the exact enforce/advisory split that issue #455 requested. The critical-path 90% gate hard-fails only on high-risk modules (kernel, doctrine, charter, status, merge, next) using an explicit `--include` list. The full-diff report uses `|| true` to guarantee advisory-only behavior. Every finding in the list above carries a concrete "satisfied by" citation pointing to the specific line of `ci-quality.yml` that implements the requirement. No workflow logic changes are required; only CI step name tightening is needed to make the enforce/advisory intent self-documenting for future contributors reviewing the Actions UI.
