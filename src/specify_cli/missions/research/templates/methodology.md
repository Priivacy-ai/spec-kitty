# Methodology Design

You are entering the **methodology** step. The previous step (`scoping`)
produced `spec.md`. The runtime engine has dispatched this step with the
`researcher-robbie` profile loaded.

## Objective

Document the research methodology in enough detail that another researcher
could reproduce the gathering, analysis, and synthesis steps and reach the
same conclusions from the same sources.

## Expected Outputs

| Artifact | Path |
|---|---|
| Methodology plan | `kitty-specs/<mission-slug>/plan.md` |

The composition guard for this step requires `plan.md` to exist before the
mission can advance to `gathering`.

## What `plan.md` Must Cover

1. **Methodology choice** — qualitative / quantitative / mixed; literature
   review vs. empirical vs. desk research; rationale grounded in the spec's
   research question.
2. **Source strategy** — which kinds of sources count as evidence (peer-
   reviewed papers, industry reports, primary interviews, code archaeology),
   and how each will be located.
3. **Inclusion / exclusion criteria** — explicit rules for what makes a source
   admissible.
4. **Citation standards** — BibTeX or APA; access-date tracking; confidence
   levels.
5. **Reproducibility plan** — how the source register and evidence trail let
   a peer reviewer rerun the synthesis.
6. **Threats to validity** — selection bias, recency bias, language coverage,
   commercial conflict-of-interest, and how each is mitigated.

## Doctrine References

When this step dispatches via composition, the action doctrine bundle at
`src/doctrine/missions/research/actions/methodology/` (authored in WP02) is
loaded into the agent's governance context.

## Definition of Done

- `plan.md` is complete and consistent with `spec.md`.
- The methodology section is concrete enough that the next step can begin
  source registration without re-litigating method choices.
- Reproducibility plan names the artefacts (`source-register.csv`,
  `evidence-log.csv`) the gathering and synthesis steps will produce.
