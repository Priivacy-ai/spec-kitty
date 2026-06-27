# Common Docs ruler baseline run (SC-004)

Durable record of the pre-rebase ruler baselines for Mission A
(`common-docs-consolidation-01KW3Q6M`). These are the **deltas Mission B must
close**: each ruler ships report-only (exit 0) in Mission A; Mission B flips the
`--strict` / blocking defaults and drives every count to zero by backfilling
frontmatter, regenerating the lockfile, and repairing dangling `related:` edges.

- **Date measured:** 2026-06-27
- **Branch:** `docs/2165-consolidation-research`
- **Tree state:** post-merge of PR #2210 (Mission A), **pre-rebase** onto
  `main`. The counts below WILL be re-measured after integrating `main`; treat
  them as the Mission-A starting line, not a frozen contract.
- **Live docs inventory size:** 568 page rows
  (`docs/development/3-2-page-inventory.yaml`).

## Exact commands and results

### 1. Anti-sprawl structure ratchet

```
PYTHONPATH=src python scripts/docs/anti_sprawl_ratchet.py --root . --json
```

- **Exit code:** 0 (report-only)
- **Structure violations:** **142**
- `directive_ref`: `DIRECTIVE_042` (binding constant resolves)

The 142 violations are the structure deltas (missing/extra sections, naming,
ADR-frontmatter gaps, shadow-tree drift) Mission B's consolidation must retire.

### 2. `related:` path validator

```
PYTHONPATH=. python scripts/docs/related_validator.py --json
```

- **Exit code:** 0 (report-only; `--strict` is wired OFF in Mission A)
- **Edges checked:** **11**
- **Dangling edges:** **0**

`checked_count > 0` proves the ruler actually reads frontmatter; 0 dangling means
the few `related:` edges that exist today all resolve. Mission B's frontmatter
backfill will raise `checked` substantially, so this baseline grows before it
shrinks.

### 3. Page-inventory lockfile freshness (drift)

```
PYTHONPATH=. python scripts/docs/check_docs_freshness.py --inventory-lockfile
```

- **Exit code:** 0 (report-only)
- **Total findings:** 542 warnings (0 errors)
  - **`INVENTORY-LOCKFILE-DRIFT`: 536** — the rollup disagrees with a fresh
    regeneration from frontmatter (the real Mission-B backlog: pages lacking the
    canonical frontmatter the lockfile derives from).
  - `HELP-DRIFT`: 4
  - `LINK-HEALTH-FAILED`: 4 (external HTTP/transient; not lockfile drift)

The **536 `INVENTORY-LOCKFILE-DRIFT`** rows are the lockfile delta Mission B
closes by backfilling per-page frontmatter so the committed rollup matches a
fresh generation.

## Per-ruler baseline summary (deltas for Mission B)

| Ruler | Command | Exit | Baseline delta to close |
|-------|---------|------|-------------------------|
| Anti-sprawl structure ratchet | `anti_sprawl_ratchet.py --root . --json` | 0 | **142** structure violations |
| `related:` path validator | `related_validator.py --json` | 0 | **0** dangling (of 11 checked) |
| Inventory-lockfile freshness | `check_docs_freshness.py --inventory-lockfile` | 0 | **536** lockfile-drift findings |
