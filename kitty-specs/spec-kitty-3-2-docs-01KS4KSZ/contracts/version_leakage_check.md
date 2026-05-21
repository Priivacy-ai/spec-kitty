# Contract: `scripts/docs/version_leakage_check.py`

**Purpose**: Enforce FR-005 / NFR-002. Detect docs pages tagged `current` that link to `archival` pages without an explicit archive or migration banner, and detect pages whose frontmatter `version_tag` disagrees with the page-inventory manifest.

## Inputs

- `--inventory PATH` (default `docs/development/3-2-page-inventory.yaml`) — `PageInventoryEntry` rows.
- `--docs-root PATH` (default `docs/`) — root directory to scan.
- `--banner-regex PATTERN` (default `r"^>\s*(?:Archive notice|Migration note)\b"`) — pattern that must appear within the first 20 non-empty lines of an `archival` or `migration` page.
- `--report PATH` (optional) — write a JSON `FreshnessReport` slice to this path.
- `--ci` flag — suppress rich output; emit plain-text lines suitable for CI annotations.

Environment: no SaaS access required. No mutation of input files at any time.

## Outputs

- stdout: rich table (interactive) or plain text (CI) listing findings. Findings use `rule_id` prefixes:
  - `LEAK-CURRENT-LINKS-ARCHIVAL` — a `current` page links to an `archival` path without a migration banner.
  - `LEAK-MISSING-BANNER` — an `archival` or `migration` page is missing the banner.
  - `LEAK-FRONTMATTER-MISMATCH` — the page's frontmatter `version_tag` disagrees with the manifest row.
  - `LEAK-MISSING-INVENTORY` — a markdown file under `docs/` is not in the manifest.
  - `LEAK-MISSING-FILE` — a manifest row points at a non-existent file.
- optional JSON report (`--report`).

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | No findings of severity `error`. Warnings allowed. |
| 1 | One or more `error` findings. |
| 2 | Input error (missing inventory file, malformed YAML). |
| 3 | Environmental setup error (cannot resolve `docs-root`, permission denied). |

## Guarantees

- Read-only. The script never writes to `docs/` or to the inventory.
- Deterministic. Given the same inputs the output is byte-identical.
- O(N) over the number of pages × number of links per page. Designed for repos with <5k pages and <50 links per page.

## Non-guarantees

- No network access. Link health (HTTP 200 vs 404) is **not** checked here; see `check_docs_freshness.py` for the orchestrated link spot-check.
- No language-aware link normalization (anchor parsing is naïve: `[text](path#anchor)` strips `#anchor` before classification).

## Test fixtures

- `tests/docs/fixtures/clean_inventory.yaml` + `tests/docs/fixtures/sample_pages/` — happy path; exit code 0.
- `tests/docs/fixtures/dirty_inventory.yaml` — one of every finding rule; exit code 1; findings count == 5.
- `tests/docs/fixtures/missing_inventory.yaml` — input error; exit code 2.

## Error taxonomy (exemplar messages)

```
LEAK-CURRENT-LINKS-ARCHIVAL  docs/how-to/install-macos.md
  -> links to docs/1x/legacy-install.md without migration banner
  fix: add archive callout above the link, or update target to docs/migration/from-2x-to-3-2.md

LEAK-MISSING-BANNER  docs/1x/index.md
  -> archival page missing banner matching /^>\s*Archive notice\b/
  fix: prepend "> Archive notice: This page documents Spec Kitty 1.x and is preserved for historical context." to the page.

LEAK-FRONTMATTER-MISMATCH  docs/explanation/mission-model.md
  -> frontmatter says version_tag=supported, manifest says version_tag=current
  fix: reconcile by updating frontmatter or by editing 3-2-page-inventory.yaml.
```
