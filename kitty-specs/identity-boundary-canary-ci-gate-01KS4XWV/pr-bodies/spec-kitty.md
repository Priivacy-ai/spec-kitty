## Summary

Adds the spec-kitty side of a three-repo CI gate that pins the
identity-boundary canary protocol (closed
[`spec-kitty-end-to-end-testing#41`](https://github.com/Priivacy-ai/spec-kitty-end-to-end-testing/issues/41))
as a required check on every PR. This PR adds:

- A dedicated workflow `.github/workflows/canary-gate.yml` running the
  canonical-registry drift-detector test
  (`tests/sync/test_diagnose.py::TestCanonicalRegistryRecognition`) as a
  single, stable job named `drift-detector`.
- A README section explaining the gate and the sibling-repo gates in
  `spec-kitty-saas` and `spec-kitty-events`.

The dedicated workflow exists so the gate can be registered as a
required status check independently of the larger `ci-quality.yml`
matrix (whose job names vary by module slice and are brittle for
branch-protection enforcement).

## Evidence

- Mission: `kitty-specs/identity-boundary-canary-ci-gate-01KS4XWV/`
- Spec: `kitty-specs/identity-boundary-canary-ci-gate-01KS4XWV/spec.md`
- Plan: `kitty-specs/identity-boundary-canary-ci-gate-01KS4XWV/plan.md`
- Local test run: `uv run pytest tests/sync/test_diagnose.py::TestCanonicalRegistryRecognition -v` → 4 passed in 0.33s
- Cross-repo manifests: `kitty-specs/identity-boundary-canary-ci-gate-01KS4XWV/cross-repo-manifests/`

## Action required from repo admin

After this PR merges, a repo admin must register the new check as
required on the branch-protection rule for `main`:

1. Open https://github.com/Priivacy-ai/spec-kitty/settings/branches
2. Edit the rule for `main`.
3. Under "Require status checks to pass before merging", click "Add
   status check" and add the exact string:
   ```
   drift-detector
   ```
4. Save the rule.

**Why this matters**: until this admin step lands, the workflow runs
on every PR but its red status does not block merge. The mission's
contract is that the gate is enforced — that requires the
branch-protection update.

### Verification

After enabling the protection rule:

- [ ] Open a trivial follow-up PR (e.g. README typo) and confirm the
  `drift-detector` check runs and goes green.
- [ ] (Optional, with approval) Open a synthetic-violation PR that
  introduces a hand-rolled event type the drift detector should reject;
  confirm the check goes red and merge is blocked.

## Test plan

- [ ] CI: `drift-detector` job runs on this PR.
- [ ] CI: `drift-detector` job passes.
- [ ] Local: `pytest tests/sync/test_diagnose.py::TestCanonicalRegistryRecognition -v` passes.
- [ ] No modification to `ci-quality.yml` (verified by `git diff`).
- [ ] No source-code changes outside `.github/workflows/` and `README.md`.

## Tracker

- Closes (when all three sibling PRs merge): part of
  [`#1247`](https://github.com/Priivacy-ai/spec-kitty/issues/1247).
- Drift-class epic: [`#1198`](https://github.com/Priivacy-ai/spec-kitty/issues/1198).
