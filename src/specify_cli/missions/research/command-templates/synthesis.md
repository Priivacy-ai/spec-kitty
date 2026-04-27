# Findings Synthesis

You are entering the **synthesis** step. The gathering step produced
`source-register.csv` with at least three documented sources. The runtime
engine has dispatched this step with the `researcher-robbie` profile loaded.

## Objective

Synthesize the documented evidence into structured findings. Every conclusion
must trace back to one or more rows in the source register.

## Expected Outputs

| Artifact | Path |
|---|---|
| Findings | `kitty-specs/<mission-slug>/findings.md` |
| (optional) Evidence log | `kitty-specs/<mission-slug>/evidence-log.csv` |

The composition guard for this step requires `findings.md` to exist before
the mission can advance to `output`.

## What `findings.md` Must Cover

1. **Executive summary** — the answer to the research question, in three to
   five sentences, with confidence level.
2. **Findings by theme** — each finding cites the source `id`s that support
   it (e.g. `[SRC-001, SRC-004]`); separate primary evidence from
   interpretation.
3. **Counter-evidence** — sources that contradict or complicate the headline
   finding, called out explicitly.
4. **Limitations** — what the evidence cannot tell us; threats to validity
   carried over from `plan.md`.
5. **Open questions** — what would need to be answered next; this becomes
   input to the `output` step's recommendations.

## Doctrine References

The action doctrine bundle at
`src/doctrine/missions/research/actions/synthesis/` (authored in WP02) is
loaded into the agent's governance context when this step dispatches via
composition.

## Definition of Done

- `findings.md` exists and addresses every section above.
- Every claim in `findings.md` cites at least one source `id` from the
  register.
- Counter-evidence section is non-empty when the source register includes
  any sources that disagree.
