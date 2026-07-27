# Phase 1 Data Model: Documentation Quality Hardening Gate

This is a tooling mission — the "data model" is the in-memory records, the function contracts that produce them, and the invariance/sync state. No persistent schema/database.

## Entities & value objects

### `Unresolvable` (modified) — `scripts/docs/relative_link_fixer.py`

The gate's finding record. **Gains a `line` field** (NFR-003 / R-05).

| Field | Type | Description |
|---|---|---|
| `file` | `str` | repo-relative posix path of the doc containing the dead link |
| `link` | `str` | the bare-relative link target as written in the body |
| `line` | `int` (NEW) | 1-based line number of the link within the file (frontmatter-adjusted) |

Ordering: deterministic — sorted by `(file, line, link)` for NFR-002.

### `EXCLUDE_PREFIXES` (mutated) — `relative_link_fixer.py:93-96`

`tuple[str, ...]`. Today `("docs/adr/", "docs/changelog/")`. Terminal state after IC-05: `()` (empty → gate covers all of `docs/`).

### ADR migration record (transient) — OBSOLETE

> **OBSOLETE post-rebase (ccd278061)** — `migrate_adr_body_links` and the shared-transform model were planned for the byte-invariance comparator. The comparator was retired upstream; WP05 now applies link repairs directly to ADR bodies with no transform module. See spec.md Scope Change.

### ADR census state — `tests/docs/test_adr_content_invariance.py` (`TestCensus` only)

| Constant/source | Before WP06 | After WP06 |
|---|---|---|
| `_EXPECTED_CENSUS` | 117 | 119 |
| `_DATE_PREFIX` filter | excludes non-dated `adr-*.md` | widened (`_is_census_adr` helper) to include the 2 non-dated ADRs |
| `_EXPECTED_INVARIANT` | ~~116~~ | **OBSOLETE** — does not exist post-rebase (ccd278061) |
| `_SANCTIONED_SELF_AMENDMENT` | ~~reconciliation ADR~~ | **OBSOLETE** — does not exist post-rebase (ccd278061) |
| baseline source (git blob) | ~~merge-base blob~~ | **OBSOLETE** — no comparator; census only |

### CHANGELOG sync state — `scripts/docs/sync_changelog.py` (NEW)

| Artifact | Role |
|---|---|
| `docs/changelog/CHANGELOG.md` | canonical source (YAML frontmatter + body) |
| `CHANGELOG.md` (root) | generated = canonical body with frontmatter stripped |
| shared region | canonical body *after* the frontmatter block |

Invariant: `read(root) == generate(read(canonical))`.

## State transitions

- **Gate scope**: `EXCLUDE_PREFIXES = ("docs/adr/","docs/changelog/")` → `()`. Legal only after IC-02 + IC-03 land (else the live-tree gate goes red on the 32 unfixed links).
- **ADR body**: `broken-link body` → `repaired body` (plain edits; no comparator, no shared transform — byte-invariance gate retired by ccd278061).
- **CHANGELOG**: `hand-synced, divergent` → `generated, convergent` (root derived from canonical).

## Invariants

- **INV-1 (C-001/C-002)**: ~~every ADR body is byte-identical to its baseline after applying only `migrate_adr_body_links`~~ — **OBSOLETE post-rebase (ccd278061)**. The byte-invariance gate was retired upstream; C-001 is withdrawn. See spec.md Scope Change.
- **INV-2 (FR-004)**: the gate scan is non-vacuous — `len(files_scanned) > 0` and `links_examined > 0`, else failure.
- **INV-3 (SC-005)**: exactly one body-link resolver exists in CI after the mission.
- **INV-4 (FR-007/C-002)**: root CHANGELOG ≡ generated(canonical) and remains Keep-a-Changelog-valid for `extract_changelog.py`.
- **INV-5 (C-007)**: the integrated branch passes a full-tree dry-run (`EXCLUDE_PREFIXES=()`) before merge.
