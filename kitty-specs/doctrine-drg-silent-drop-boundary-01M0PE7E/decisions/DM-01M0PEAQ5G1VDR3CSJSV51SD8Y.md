# Decision Moment `01M0PEAQ5G1VDR3CSJSV51SD8Y`

- **Mission:** `doctrine-drg-silent-drop-boundary-01M0PE7E`
- **Origin flow:** `specify`
- **Slot key:** `specify.context-sources.projection-strategy`
- **Input key:** `context_sources_strategy`
- **Status:** `resolved`
- **Created:** `2026-08-23T04:33:44.112640+00:00`
- **Resolved:** `2026-08-23T04:40:10.595118+00:00`
- **Opened by:** `cli`
- **Other answer:** `false`

## Question

Should context-sources.{tactics,toolguides,styleguides,doctrine-layers,additional} be replaced by DRG edges/relationships, cleaned up/removed, or a per-kind mix?

## Options

- replace-with-DRG-edges
- remove-dead-fields
- per-kind-mix
- research-squad-to-decide

## Final answer

Full consolidate on top-level *-references. Remove ALL context-sources.* fields; migrate the one live use (directives) onto directive-references (already authored by all 25 shipped profiles); extractor projects agent_profile DRG edges from the *-references surface; schema change + migration + update 25 shipped profiles. One canonical rationale-bearing DRG-provisioned delivery surface, zero dead fields. Research squad evidence: renderer reads *-references, context-sources.* is a redundant/inert second surface; additional/doctrine-layers have no edge shape.

## Rationale

_(none)_

## Change log

- `2026-08-23T04:33:44.112640+00:00` — opened
- `2026-08-23T04:40:10.595118+00:00` — resolved (final_answer="Full consolidate on top-level *-references. Remove ALL context-sources.* fields; migrate the one live use (directives) onto directive-references (already authored by all 25 shipped profiles); extractor projects agent_profile DRG edges from the *-references surface; schema change + migration + update 25 shipped profiles. One canonical rationale-bearing DRG-provisioned delivery surface, zero dead fields. Research squad evidence: renderer reads *-references, context-sources.* is a redundant/inert second surface; additional/doctrine-layers have no edge shape.")
