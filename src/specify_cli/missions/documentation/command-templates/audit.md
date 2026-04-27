# Documentation Audit

You are entering the **audit** step. The previous step (`discover`) produced
`spec.md` naming the iteration mode, audience, and Divio types in scope. The
runtime engine has dispatched this step with the `researcher-robbie` profile
loaded.

## Objective

Inventory existing documentation against the Divio coverage matrix, identify
gaps relative to the spec's goals, and prioritize the gaps so the design
step can plan with full visibility into where effort is most needed.

## Expected Outputs

| Artifact | Path |
|---|---|
| Gap analysis | `kitty-specs/<mission-slug>/gap-analysis.md` |

The composition guard for this step requires `gap-analysis.md` to exist
before the mission can advance to `design`.

## What `gap-analysis.md` Must Cover

1. **Coverage matrix** — a table whose rows are documentation areas
   (features, modules, user journeys) and whose columns are the four Divio
   types (`tutorial`, `how-to`, `reference`, `explanation`). Each cell is
   `present`, `partial`, or `missing` with a path reference where relevant.
2. **Methodology** — how documents were classified (frontmatter `type:`,
   directory convention, or content heuristics) and the confidence level
   for each classification call.
3. **Prioritized gaps** — gaps ranked by user impact:
   - **HIGH**: missing tutorials or reference for core features (blocks
     new users or integrators).
   - **MEDIUM**: missing how-tos for advanced features, or missing
     tutorials for secondary features.
   - **LOW**: missing explanations (nice-to-have context).
4. **Iteration-mode behavior** — `initial` mode treats every cell as
   missing; `gap_filling` audits the full surface; `feature_specific`
   restricts the matrix to the named feature.
5. **Recommendations** — concrete suggestions the design step can act on
   (which gaps to close in this mission, which to defer).

## Doctrine References

When this step dispatches via composition, the action doctrine bundle at
`src/doctrine/missions/documentation/actions/audit/` is loaded into the
agent's governance context.

## Definition of Done

- `gap-analysis.md` exists and addresses every section above.
- Every HIGH-priority gap has a one-line justification grounded in the
  spec's audience and goals.
- The coverage matrix is concrete enough that the design step can begin
  planning Divio-specific work without re-running the audit.
