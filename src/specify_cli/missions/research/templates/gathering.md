# Source Gathering

You are entering the **gathering** step. The methodology step produced
`plan.md`. The runtime engine has dispatched this step with the
`researcher-robbie` profile loaded.

## Objective

Locate sources that satisfy the inclusion criteria from `plan.md`, register
each one with citation metadata, and emit a `source_documented` status event
per registered source.

## Expected Outputs

| Artifact | Path |
|---|---|
| Source register | `kitty-specs/<mission-slug>/source-register.csv` |
| (optional) Source archive | `kitty-specs/<mission-slug>/sources/` |

The composition guard for this step requires **both**:

1. `source-register.csv` exists in the feature directory.
2. The status events log carries at least three `source_documented` events
   for this mission. The threshold mirrors the legacy mission.yaml guard
   `event_count("source_documented", 3)`.

If either condition fails, composition emits a structured failure and the
mission does not advance to `synthesis`.

## What `source-register.csv` Must Cover

A CSV row per source with at minimum:

- `id` — stable handle (e.g. `SRC-001`).
- `citation` — BibTeX or APA-formatted citation.
- `url_or_doi` — link or DOI (when available).
- `access_date` — ISO date the source was retrieved.
- `confidence` — `high` / `medium` / `low` reflecting source quality.
- `relevance_note` — one sentence on why this source matters to the research
  question.

Each registered source must be paired with a `source_documented` event the
gathering agent emits to `kitty-specs/<mission-slug>/mission-events.jsonl`.
The runtime does NOT emit these events — registering a row in
`source-register.csv` is not enough on its own. Use
`specify_cli.mission_v1.events.emit_event("source_documented", {...},
mission_name=..., feature_dir=...)` (one call per source) so the composition
guard sees at least three matching entries before requesting advancement to
`synthesis`.

## Doctrine References

The action doctrine bundle at
`src/doctrine/missions/research/actions/gathering/` (authored in WP02) is
loaded into the agent's governance context when this step dispatches via
composition.

## Definition of Done

- `source-register.csv` exists with at least three high-quality rows.
- Three or more `source_documented` events are present in the status events
  log (`event_count("source_documented", 3)`).
- Sources span the inclusion criteria from `plan.md`; no critical evidence
  category is empty.
