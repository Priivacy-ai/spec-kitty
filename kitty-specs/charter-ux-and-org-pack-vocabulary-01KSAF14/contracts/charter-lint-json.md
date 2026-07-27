# Contract — `charter lint --json` (extended)

**Backed by**: FR-001 .. FR-004, FR-015

## Top-level shape (post-mission)

```json
{
  "findings": [ /* existing LintFinding shape */ ],
  "scanned_at": "2026-05-23T13:00:00+00:00",
  "feature_scope": null,
  "duration_seconds": 0.123,
  "drg_node_count": 0,
  "drg_edge_count": 0,
  "graph_state": "merged" | "built_in_only" | "missing"   /* NEW */
}
```

## `graph_state` values

| Value | Meaning | What lint actually scanned |
|---|---|---|
| `merged` | Built-in DRG plus optional org-pack fragments plus project DRG | the merged graph |
| `built_in_only` | Project DRG absent (either `synthesize` declared `built_in_only: true` or the file is simply missing) | the built-in DRG only |
| `missing` | No DRG loadable (neither project nor built-in resolvable) | nothing |

## Human-banner mapping (FR-003)

| `graph_state` | Banner line printed before the per-layer block |
|---|---|
| `merged` | (existing) `Charter Lint - layers:` + per-layer markers |
| `built_in_only` | `Charter Lint - layers:` + `[built-in]` + `[no project overlay — run \`spec-kitty charter synthesize\`]` |
| `missing` | `Charter Lint: no lintable graph found — run \`spec-kitty charter synthesize\`` |

## "No decay detected" branch

The current banner unconditionally prints `[green]No decay detected[/green]` followed by `Scanned 0 nodes`. Post-mission:

- If `graph_state == "missing"`: the "No decay detected" line MUST NOT print. Instead, the lint surface MUST print the remediation hint and exit with a non-zero return code only when the user passed `--strict` (default exit remains 0 for backward compatibility, but the banner is informative).
- If `graph_state == "built_in_only"`: "No decay detected" prints with a qualifier — `[green]No decay detected[/green] [dim](in built-in graph)[/dim]`.
- If `graph_state == "merged"` and findings empty: existing banner unchanged.

## Vocabulary

Layer markers in human output (already use `[built-in]`) remain unchanged. Per-layer markers for org packs use `[org:<pack-name>]`. Project layer marker is `[project]`. There MUST be no occurrence of `[shipped]` in any banner output (FR-016).
