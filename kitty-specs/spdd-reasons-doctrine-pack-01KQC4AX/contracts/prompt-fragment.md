# Contract: Conditional Prompt Fragment Rendering

## Marker convention

Each command template gains AT MOST ONE conditional block per applicable action, delimited by:

```
<!-- spdd:reasons-block:start -->
... markdown content describing the action-scoped REASONS guidance ...
<!-- spdd:reasons-block:end -->
```

## Renderer behavior

For each command template that contains a `spdd:reasons-block`:

- If `is_spdd_reasons_active(repo_root)` is `True`: keep the block content but strip the surrounding `<!-- spdd:reasons-block:start -->` and `<!-- spdd:reasons-block:end -->` marker lines. Content rendered verbatim.
- If `is_spdd_reasons_active(repo_root)` is `False`: remove the marker lines AND every line strictly between them (including any blank line that was added solely to separate the block from surrounding text). Result must be byte-identical to the pre-feature template (verified via golden snapshot in `tests/prompts/test_prompt_fragment_rendering.py`).

## Non-goals
- No Jinja or other expression evaluation. Block contents are static markdown.
- No nested blocks. Flat blocks only.

## Acceptance tests (WP4)

| Case | Project state | Expectation |
|---|---|---|
| 1 | inactive (no SPDD selection) | Five command-template outputs (specify, plan, tasks, implement, review) byte-identical to baseline snapshot. |
| 2 | active | Each output contains the corresponding REASONS guidance block, no marker lines. |
| 3 | active for `specify` only | Block scoped to Requirements/Entities appears in specify output; other templates may also include their action-scoped block. |
| 4 | malformed marker (missing end) | Raises a clear renderer error; does not silently truncate. |

## Action-scoped block content

| Template | Block headline | Sections referenced |
|---|---|---|
| specify.md | "REASONS Guidance — Specify" | Requirements, Entities |
| plan.md | "REASONS Guidance — Plan" | Approach, Structure |
| tasks.md | "REASONS Guidance — Tasks" | Operations, WP boundaries |
| implement.md | "REASONS Guidance — Implement WP\<id\>" | Full canvas (R, E, A, S, O, N, S) |
| review.md | "REASONS Guidance — Review" | Comparison surface (R, O, N, S) + drift classification |
