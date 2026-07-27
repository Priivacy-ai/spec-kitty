# Required-Check Name Contract

This file is the immutable contract between the three PRs this mission
opens and the post-merge branch-protection registration step a repo
admin will do separately.

## Check names (exact strings to register)

| Repo                              | Workflow file                                       | Required-check name (exact)      |
|-----------------------------------|-----------------------------------------------------|-----------------------------------|
| `Priivacy-ai/spec-kitty`          | `.github/workflows/drift-detector.yml`              | `drift-detector`                  |
| `Priivacy-ai/spec-kitty-events`   | `.github/workflows/cross-repo-harness-tests.yml`    | `cross-repo-harness-tests`        |
| `Priivacy-ai/spec-kitty-saas`     | `.github/workflows/canary-gate.yml`                 | `identity-boundary-canary`        |

The check name is the `name:` field of the single job inside each
workflow file. Branch-protection registration is keyed by this exact
string; any change to the job name in a future PR is a breaking change
to the protection contract.

## Admin action per PR (post-merge)

For each PR, after merge:

1. Navigate to `https://github.com/<repo>/settings/branches`.
2. Edit the rule for `main`.
3. Under "Require status checks to pass before merging", click "Add
   status check" and add the exact name from the table above.
4. Save the rule.

Without this admin step, the workflow still runs on every PR but its
red status does not block merge — the gate is unenforced.

## Non-goals

- This file does NOT specify the workflow's internals (steps, env,
  pinned SHA, etc.); see `plan.md` Architecture section.
- This file does NOT attempt to mutate branch protection via API; see
  spec C-003.
