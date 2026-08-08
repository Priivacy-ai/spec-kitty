# Phase 1 Data Model: Docs Quality Gate Hardening

This mission has no persistent datastore; the "data" are the authorities and structures the gates read, plus their invariants.

## Authorities & structures

### Command set
- **`CONSUMER_SKILLS`** — `frozenset[str]`, `src/specify_cli/shims/registry.py`. 15 members today. Canonical authority (C-001).
  - Invariant (import-time asserted): `PROMPT_DRIVEN_COMMANDS | CLI_DRIVEN_COMMANDS == CONSUMER_SKILLS` (`registry.py:87`) and `CANONICAL_COMMANDS == CONSUMER_SKILLS` (`command_installer.py:81`).
- **Documented heading set** — the set of `## /spec-kitty.<name>` headings in `docs/api/slash-commands.md`. 12 today; must equal `CONSUMER_SKILLS` (symmetric-difference empty).

### Published page set
- **DocFX content entries** — `docs/docfx.json` `build.content[]`, 2 entries: root (`src="."`, 19 include globs) and `archive` (`src="archive"`).
- **Include glob** — a single `files` markdown pattern (e.g. `guides/**.md`). 19 globs in the root entry. The unit of the non-vacuity guard (D3).
- **Page set** — union of pages resolved from include globs, minus `DEFAULT_EXCLUSIONS` (`archive/**`, …). 675 today. Guarded by `MINIMUM_EXPECTED_PAGES = 500` aggregate floor (preserved, C-002).

### docs-freshness workflow
- **Structural properties** (FR-005 assertion targets): PR `paths:` filter present & excludes `tests/**` + `kitty-specs/**`; unfiltered `push: main` backstop present; documented safety-invariant comment present.

## Validation rules / invariants

| Rule | Source FR | Statement |
|------|-----------|-----------|
| R-1 | FR-001/SC-002 | `documented_heading_set == CONSUMER_SKILLS` (both directions); else gate exits non-zero naming the symmetric difference. |
| R-2 | FR-003/SC-003 | For each declared include glob `g`: `count(raw_matches(g)) >= 1` (pre-exclusion); else raise loud naming `g`. |
| R-3 | FR-003/C-002 | Aggregate floor `len(page_set) >= 500` preserved (additive to R-2). |
| R-4 | FR-003 | R-2 evaluated pre-exclusion so a fully-excluded tree (`archive`) does not false-fail. |
| R-5 | FR-004 | R-2 failure path is reachable through `description_length_check.py`'s resolver entry point (shared resolver). |
| R-6 | FR-005/SC-005 | docs-freshness workflow retains {paths-filter-excludes-tests/kitty-specs, unfiltered push:main backstop, invariant comment}; else structure test fails. |

## Non-entities (explicitly out)

- Live GitHub branch-protection required-check list — not repo-readable; not a data source for any test (D4).
- `related_validator.py` floor, non-docs CI workflows — tracked in #3264/#3265, not modeled here.
