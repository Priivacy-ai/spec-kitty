# Contract: Inventory Artifact Schema (IC-02)

**Governs**: `kitty-specs/retire-doctrine-term-01M0JMK9/inventory.md`
**Requirements**: FR-006, FR-007, NFR-001, SC-002.
**Consumed by**: M1–M6 (work lists + re-baselining), SC-002 verification.

## Audit procedure (NFR-001 — mechanical, case-insensitive)

The inventory is produced by a **mechanical audit**, run before any classification (evidence before conclusion):

1. Enumerate all tracked files: `git ls-files` (excludes `.git`; worktrees and vendor dirs are not tracked in this repo — if any appear, record them as excluded with reason).
2. Case-insensitive hit count per file: `git grep -ic 'doctrine' -- $(git ls-files)` (or equivalent; the exact command is recorded in frontmatter).
3. Every file with count > 0 must appear in the raw audit record. No sampling, no hand-tallies.

## Artifact structure

### Frontmatter (YAML)

```yaml
base_commit: <SHA at audit time>
date: <YYYY-MM-DD>
audit_command: |
  <exact command(s) used, verbatim>
total_hits: <int — sum of all per-file counts>
```

### Section 1 — Raw audit record

Per-file table: `path | hit_count`. This is the mechanical output, unmodified. (Large tables may be grouped by top-level directory with per-file rows preserved — grouping is presentation, not aggregation away of files.)

### Section 2 — Occurrence class table (OC-##)

One row per occurrence class, columns:

| Column | Rule |
|--------|------|
| `id` | `OC-##`, stable, assigned at inventory time (OC-I2: never reused) |
| `surface_category` | exactly one of S1..S9 (taxonomy in `data-model.md` §1) |
| `path_patterns` | glob/path patterns the class matches |
| `occurrence_count` | line-based count at base commit (from Section 1) |
| `representative_examples` | ≤ 3 quoted lines with `file:line` |
| `classification` | `in-scope` (all OC rows are in-scope by construction; classification-outs get their own table) |
| `operator_typed` | bool — operators/harnesses type this identifier (the ADR's classification applies) |
| `assigned_mission` | mission slug or `deferred:<milestone>` (filled in `stacked-plan.md`; the inventory may leave it as `TBD` only until IC-04 runs — final state: no TBDs) |

### Section 3 — Classification-out table (X1/X2/X3)

One row per classification-out group: `id | category (internal-identifier / legacy-marked-historical / quoted-data) | path_patterns | occurrence_count | rule_applied (one line citing C-003/C-005 or the guard exemption)`.

### Section 4 — Completeness statement (SC-002 pass condition)

Arithmetic check, stated explicitly:

```
total_hits = sum(Section 2 occurrence_count) + sum(Section 3 occurrence_count)
```

**0 unclassified hits is the pass condition.** Any hit not covered by Section 2 or 3 fails SC-002.

## Invariants

- **INV-I1 (per-wave snapshot)**: each stack wave re-runs this audit at its base commit and records drift. Expected drift source: concurrent catfooding missions adding `kitty-specs/` hits (self-classify as X2 at merge). Drift is recorded, not silently absorbed.
- **OC-I1 (exhaustiveness)**: every tracked-file hit belongs to exactly one OC row or X row.
- **OC-I3 (string-level scope)**: classification is per occurrence string, not per file path — user-facing artifacts inside `src/doctrine/` (skills at `src/doctrine/skills/`) are in scope; identifiers anywhere are X1.
