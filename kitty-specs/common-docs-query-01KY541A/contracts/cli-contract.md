# CLI Contract: `spec-kitty docs query`

## Command

```
spec-kitty docs query <TERM> [--json] [--divio-type <TYPE>] [--section <ANCHOR-SLUG>]
```

Registered as a `docs` Typer sub-app (`src/specify_cli/cli/commands/docs.py`), added next to
`glossary` in `src/specify_cli/cli/commands/__init__.py`. The command imports `DocsQueryEntry` /
`DocsIndexStore` from the **packaged** `specify_cli.docs.index_model` (`src→src`) — it MUST NOT import
`scripts.*` (unpackaged; would fail in the installed CLI).

## Arguments & options

| Name | Kind | Required | Behavior |
|------|------|----------|----------|
| `TERM` | positional `str` | yes | Case-insensitive substring matched against each page's `title`, any anchor `text`/`slug`, and `abstract`. Empty/whitespace → usage error (exit 2). |
| `--json` | flag | no | Emit machine-readable JSON (see shape below) via `print(json.dumps(...))`. Without it, render a Rich table for humans. |
| `--divio-type` | `str` | no | Restrict to pages of this Divio type. MUST validate against `DivioType` (`tutorial\|how-to\|reference\|explanation\|none`); invalid value → usage error (exit 2). |
| `--section` | `str` | no | Restrict to pages containing an anchor whose `slug` equals this value. |

## JSON result shape (`--json`)

A JSON array (possibly empty). Each element:

```json
{
  "path": "docs/architecture/execution-lanes.md",
  "title": "Execution lanes",
  "divio_type": "explanation",
  "abstract": "How Spec Kitty allocates worktrees per computed lane.",
  "anchors": [
    {"slug": "lane-allocation", "text": "Lane allocation", "level": 2}
  ]
}
```

- `anchors` contains only the anchors that MATCHED the term/`--section` filter (FR-003), in document
  order. When the match was on `title`/`abstract` only (no anchor matched) `anchors` MAY be empty.
- Keys are always present; `abstract` may be `""`.

## Behavioral contract

| # | Given | When | Then |
|---|-------|------|------|
| 1 | index has a page matching TERM | `docs query "<term>" --json` | that page appears with `path`, `title`, matching `anchors`, `abstract`, `divio_type`; **exit 0** |
| 2 | no page matches | `docs query "<term>" --json` | prints `[]`; **exit 0** (NOT an error) |
| 3 | `--divio-type reference` | matching pages exist of other types | only `reference` pages returned |
| 4 | `--section <slug>` | some pages contain that anchor | only those pages returned |
| 5 | invalid `--divio-type` value | — | usage error, **exit 2**, no traceback |
| 6 | no `docs/` tree / index file missing | `docs query "x"` | clear error message to stderr, non-zero exit; **no Python traceback** |
| 7 | human mode (no `--json`) | match exists | Rich table with path/title/type/matching-anchors; NO Rich markup leaks into piped output |

## Non-goals (contract-level)

- No HTTP/REST/GraphQL surface (C-002).
- No full-text body search — matching is over title/anchor/abstract only (C-003).
- Anchors are source-heading slugs, not guaranteed byte-identical to rendered DocFX fragments (C-005).
