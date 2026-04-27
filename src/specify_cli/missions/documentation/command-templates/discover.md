# Documentation Discovery

You are entering the **discover** step of the Documentation Kitty mission.
The runtime engine has dispatched this step with the `researcher-robbie`
profile loaded.

## Objective

Translate the operator's documentation request into a precisely scoped
specification that downstream audit, design, generate, validate, and publish
steps can act on without re-interviewing the operator.

## Expected Outputs

| Artifact | Path |
|---|---|
| Documentation specification | `kitty-specs/<mission-slug>/spec.md` |

The composition guard for this step requires `spec.md` to exist before the
mission can advance to `audit`.

## What `spec.md` Must Cover

1. **Iteration mode** — one of `initial` (greenfield documentation),
   `gap_filling` (audit existing docs and close gaps), or `feature_specific`
   (document a single feature or module). The mode chosen here determines
   whether the audit step performs a full coverage scan or a targeted one.
2. **Target audience** — who reads this documentation and what they decide
   with it (developers, operators, end users, contributors). Audience choice
   constrains tone, depth, and which Divio types matter most.
3. **Documentation goals** — the user-observable outcomes the mission must
   produce (e.g. "a new contributor can run the test suite within ten
   minutes", "every public API has a reference page").
4. **Divio types in scope** — `tutorial`, `how-to`, `reference`,
   `explanation`. Note which types are explicitly out of scope and why.
5. **Success criteria** — falsifiable statements that let a reviewer judge
   whether the documentation answered the brief.
6. **Open questions** — gaps the operator should resolve before audit
   begins; each open question must carry an owner and a deadline.

## Doctrine References

When this step dispatches via composition, the action doctrine bundle at
`src/doctrine/missions/documentation/actions/discover/` is loaded into the
agent's governance context. That bundle carries the directives, tactics, and
procedures that constrain how discovery is performed.

## Definition of Done

- `spec.md` exists in the mission's feature directory and addresses every
  section above.
- Every Open Question is either resolved in-line or carries an explicit
  owner plus deadline.
- The iteration mode and Divio scope are concrete enough that the audit
  step can begin gap analysis without re-litigating the brief.
