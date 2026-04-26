# Publication Output

You are entering the **output** step. The synthesis step produced
`findings.md`. The runtime engine has dispatched this step with the
`reviewer-renata` profile loaded — this step is a review and publication
gate, not a synthesis continuation.

## Objective

Prepare findings for publication: verify citation completeness, methodology
clarity, and trace integrity from conclusions back to documented sources.
Then capture an explicit publication-approval gate.

## Expected Outputs

| Artifact | Path |
|---|---|
| Publication-ready report | `kitty-specs/<mission-slug>/report.md` |

The composition guard for this step requires **both**:

1. `report.md` exists in the feature directory.
2. The status events log carries a `publication_approved` gate event for
   this mission — i.e. `gate_passed("publication_approved")`. **This is the
   publication approval gate.** Without it, composition emits a structured
   failure and the mission does not advance to `accept`.

## What `report.md` Must Cover

1. **Publication-ready prose** — `findings.md` rewritten for the audience
   named in `spec.md`; technical density tuned for that audience.
2. **Citation appendix** — full bibliography matching the rows in
   `source-register.csv`; access dates preserved.
3. **Methodology appendix** — `plan.md` distilled to the level the audience
   needs to evaluate the research's reproducibility.
4. **Reviewer notes** — what the reviewer (this step's agent) checked for,
   what residual risks remain, and the explicit recommendation.

## Publication Approval Gate

Before requesting advancement, the reviewer must:

- Confirm every claim in `report.md` ties back to at least one source in the
  register, no orphaned conclusions.
- Confirm the methodology appendix is sufficient for an external auditor.
- Emit the `publication_approved` gate event via the status events surface.
  The composition guard reads this event and refuses to advance until it
  appears.

## Doctrine References

The action doctrine bundle at
`src/doctrine/missions/research/actions/output/` (authored in WP02) is
loaded into the agent's governance context when this step dispatches via
composition. The bundle's guidelines include the literal token
`gate_passed("publication_approved")` for downstream automation to grep on.

## Definition of Done

- `report.md` exists, is publication-ready, and addresses every section
  above.
- The publication approval gate event has been emitted; the composition
  guard reports `gate_passed("publication_approved")` true.
- No claim in `report.md` lacks a citation in the register.
