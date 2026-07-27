# Quickstart: Common Docs query

## Generate / refresh the index

```bash
# Regenerate the committed docs retrieval index from docs/**/*.md
python scripts/docs/docs_index.py --write     # or: uv run python scripts/docs/docs_index.py --write

# Check for drift (CI mode — non-zero on stale index)
python scripts/docs/docs_index.py --strict     # compares committed vs regenerated
```

The freshness gate also runs as part of the docs aggregate:

```bash
python scripts/docs/check_docs_freshness.py --ci   # includes DOCS-INDEX-DRIFT
```

## Query the docs from the CLI

```bash
# Human-readable table
spec-kitty docs query "redirect"

# Machine-readable JSON (for agents/harnesses)
spec-kitty docs query "redirect" --json

# Filter to a Divio type
spec-kitty docs query "worktree" --divio-type reference --json

# Filter to pages containing a specific heading anchor
spec-kitty docs query "merge" --section preflight-validation --json
```

Example JSON element:

```json
{
  "path": "docs/architecture/git-worktrees.md",
  "title": "Git worktrees",
  "divio_type": "explanation",
  "abstract": "How worktrees isolate lane execution.",
  "anchors": [{"slug": "redirect-handling", "text": "Redirect handling", "level": 2}]
}
```

- No match → `[]` and exit 0.
- No `docs/` tree or missing index → a clear error on stderr, non-zero exit, no traceback.

## Acceptance validation

1. `spec-kitty docs query "<known-term>" --json` returns the expected page(s) with matching anchors —
   against both a fixture tree and the live `docs/`.
2. Regenerate the index twice → byte-identical (NFR-001).
3. Edit a doc heading without refreshing the index → `check_docs_freshness --ci` reds with
   `DOCS-INDEX-DRIFT`; refresh → green.
4. `docs query` over the full live tree returns in < 1s (NFR-002).
5. `ruff` + `mypy --strict` clean on all new modules (NFR-003).
