# Research Scoping

You are entering the **scoping** step of the Deep Research Kitty mission. The
runtime engine has dispatched this step with the `researcher-robbie` profile
loaded.

## Objective

Translate the operator's research request into a precisely scoped specification
that downstream methodology, gathering, and synthesis steps can act on without
guessing intent.

## Expected Outputs

Produce a spec document that names the research question, scope boundaries,
stakeholders, and success criteria.

| Artifact | Path |
|---|---|
| Research specification | `kitty-specs/<mission-slug>/spec.md` |

The composition guard for this step requires `spec.md` to exist before the
mission can advance to `methodology`.

## What `spec.md` Must Cover

1. **Primary research question** — one sentence, falsifiable where possible.
2. **Scope boundaries** — what is in scope, what is explicitly out of scope.
3. **Stakeholders / audience** — who the findings are for; what they will
   decide with the output.
4. **Success criteria** — how a reader judges whether the research answered
   the question.
5. **Open questions** — gaps the operator should resolve before methodology.
6. **Risks / threats to validity** — anticipated risks to the research
   integrity (selection bias, source availability, time-bounding).

## Doctrine References

When this step dispatches via composition, the action doctrine bundle at
`src/doctrine/missions/research/actions/scoping/` is loaded into the agent's
governance context. That bundle (authored in WP02) carries the directives,
tactics, and procedures that constrain how scoping is performed.

## Definition of Done

- `spec.md` exists in the mission's feature directory and addresses every
  section above.
- All five Open Questions are either resolved or carry an explicit owner +
  deadline.
- The scope statement is tight enough that a methodology step can pick it up
  without re-interviewing the operator.
