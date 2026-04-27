# Documentation Publication

You are entering the **publish** step. The validate step produced
`audit-report.md` recording which quality gates passed. The runtime engine
has dispatched this step with the `reviewer-renata` profile loaded.

## Objective

Prepare the documentation for release: confirm publication readiness from
the audit evidence, package the deployment handoff, and record the
post-publish living-documentation expectations so the docs do not rot
after release.

## Expected Outputs

| Artifact | Path |
|---|---|
| Release handoff | `kitty-specs/<mission-slug>/release.md` |

The composition guard for this step requires `release.md` to exist before
the mission can advance to `accept`.

## What `release.md` Must Cover

1. **Release readiness statement** — a concise verdict ("ready to publish"
   or "blocked"), grounded in the gate verdicts in `audit-report.md`. Do
   not override a `validate`-step failure; if a gate failed and was not
   remediated, this step blocks.
2. **Deployment handoff** — the build command, output directory, target
   host (e.g. GitHub Pages, Read the Docs, internal mirror), and any CI
   workflow that owns publication. Reviewers should be able to deploy
   without re-deriving these facts.
3. **Versioning and changelog** — the documentation version this release
   represents and a one-paragraph changelog summarizing the artifacts
   added or updated relative to the prior published version.
4. **Living-documentation sync plan** — the cadence and owners for the
   next audit cycle (next gap analysis, regeneration of reference docs
   after API changes, broken-link sweeps). Documentation that is not
   maintained becomes wrong; name the maintainer.
5. **Known gaps deferred** — anything the validate step accepted as
   deferred is repeated here so it is visible at release time and
   carried forward to the next iteration.
6. **Rollback plan** — how to revert the publication if a defect is
   found post-release.

## Doctrine References

When this step dispatches via composition, the action doctrine bundle at
`src/doctrine/missions/documentation/actions/publish/` is loaded into the
agent's governance context.

## Definition of Done

- `release.md` exists and addresses every section above.
- The readiness statement matches the audit-report verdict; mismatches
  are escalated, not papered over.
- A maintainer is named for post-publish living-documentation upkeep.
