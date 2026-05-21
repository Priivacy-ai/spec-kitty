---
work_package_id: WP01
title: Version taxonomy & bulk-edit guardrail surface
dependencies: []
requirement_refs:
- FR-001
planning_base_branch: main
merge_target_branch: main
branch_strategy: lane-based; one worktree per lane allocated at implement time
subtasks:
- T001
- T002
- T003
agent: claude
history:
- actor: planner
  at: 2026-05-21T06:52:04Z
  action: wp_authored
  notes: Initial authorship by tasks phase.
agent_profile: curator-carla
authoritative_surface: docs/development/
execution_mode: code_change
model: claude-opus-4-7
owned_files:
- docs/development/3-2-version-taxonomy.md
- kitty-specs/spec-kitty-3-2-docs-01KS4KSZ/occurrence_map.yaml
role: curator
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your agent profile:

```
/ad-hoc-profile-load curator-carla
```

This sets identity, governance scope, boundaries, and the curator review lens you must apply.

## Objective

Author the canonical 3.2 version-relevance taxonomy and produce the `occurrence_map.yaml` that gates the page-inventory frontmatter rollout (WP02) and the archive/migration page moves (WP09) under the `spec-kitty-bulk-edit-classification` skill.

## Context

- Spec FR-001 defines the five tags: `current`, `supported`, `archival`, `migration`, `internal`.
- C-008 plus research R-008 establish that adding `version_tag` frontmatter across `docs/**/*.md` is a bulk edit. The bulk-edit guardrail requires `occurrence_map.yaml` with all 8 standard categories before the first dependent WP starts.
- The `VersionTag` enum shape lives in [`data-model.md`](../data-model.md) §"VersionTag (enum)".
- Read-only survey of `docs/**` is allowed during planning per C-001 — no live doc edits.

## Subtasks

### T001 — Author 5-tag version taxonomy doc

Create `docs/development/3-2-version-taxonomy.md` with:

- Header: "3.2 Version Taxonomy".
- For each tag (`current`, `supported`, `archival`, `migration`, `internal`):
  - Plain-language definition (lifted verbatim from `spec.md` Domain Language table).
  - Adoption rule (when this tag applies; e.g., "all `docs/1x/**` pages are `archival`").
  - Banner requirement (archival and migration pages must include the banner regex from `contracts/version_leakage_check.md`).
  - Example pages (cite two or three by path).
- Reference to the `VersionTag` enum in [`data-model.md`](../data-model.md).
- Reference to the `PageInventoryEntry` schema and the inventory-validation invariants.
- A short "How filtering works" subsection summarising research R-006 (frontmatter + manifest cross-check).

### T002 — Read-only survey of `docs/**/*.md`

- From repo root, list every markdown file under `docs/`, `architecture/`, and the root `README.md` using `git ls-files`.
- Bucket counts by top-level directory (e.g., `docs/1x/`, `docs/2x/`, `docs/3x/`, `docs/tutorials/`, `docs/how-to/`, `docs/reference/`, `docs/explanation/`, `docs/migration/`, `docs/development/`, `docs/architecture/`).
- Record the survey output as an annex inside `docs/development/3-2-version-taxonomy.md` so the page inventory in WP02 has a known target count.
- **Do not** modify any of the surveyed pages.

### T003 — Author `occurrence_map.yaml`

Create `kitty-specs/spec-kitty-3-2-docs-01KS4KSZ/occurrence_map.yaml`. Use the shape documented in [`data-model.md`](../data-model.md) §"OccurrenceMap (bulk-edit guardrail)". Fill **every** one of the 8 standard categories:

| Category | Action | Notes |
|----------|--------|-------|
| `code_symbols` | `not_applicable` | No identifier renames in docs work. |
| `import_paths` | `not_applicable` | — |
| `filesystem_paths` | `rewrite` | `docs/1x/**` → `docs/archive/1x/**`; `docs/2x/**` → `docs/archive/2x/**`. WP09 executes; this WP only declares the mapping. |
| `serialized_keys` | `add` | `version_tag` frontmatter key added to every `docs/**/*.md` page per WP02 inventory. |
| `cli_commands` | `not_applicable` | — |
| `user_facing_strings` | `review` | Archive banners on moved 1.x/2.x pages (WP09). |
| `tests_fixtures` | `not_applicable` | — |
| `logs_telemetry` | `not_applicable` | — |

Cite `spec-kitty-bulk-edit-classification` skill at the top of the file with a comment so future readers find the doctrine.

## Branch Strategy

- Planning base: `main`
- Merge target: `main`
- Execution: lane-based; this WP runs in lane `A`. Implement allocates `.worktrees/spec-kitty-3-2-docs-<mid8>-lane-a/` at first claim. Subsequent lane-A WPs (WP02, WP03, WP04) reuse this worktree.

## Test Strategy

- WP-level acceptance test: `occurrence_map.yaml` must validate against the bulk-edit skill schema. The implementer runs `spec-kitty-bulk-edit-classification` skill validation as part of review.
- Taxonomy doc passes reviewer prose review (no tests).

## Definition of Done

- [ ] `docs/development/3-2-version-taxonomy.md` exists with all five tags defined and the read-only survey annex.
- [ ] `kitty-specs/spec-kitty-3-2-docs-01KS4KSZ/occurrence_map.yaml` exists with all 8 categories filled.
- [ ] `occurrence_map.yaml` passes bulk-edit skill validation.
- [ ] No files outside `owned_files` modified.
- [ ] Commit message references mission slug and WP id.

## Risks

- **Bulk-edit category miscount** — missing one of the 8 categories silently disables the guardrail. Mitigation: explicit category list above; reviewer checks every row.
- **Read-only survey accidentally edits a page** — Mitigation: implementer uses `git ls-files` and `Read`/`grep`, never `Edit` or `Write`, on docs/** during this WP.

## Reviewer Guidance

- Confirm the taxonomy doc cites `VersionTag` enum from `data-model.md`.
- Confirm all 8 bulk-edit categories appear in `occurrence_map.yaml` and that the actions match the table in T003.
- Confirm no live docs page was edited (review `git diff --stat`).
- Per [`spec-kitty-mission-workflow.md`](../../../spec-kitty-mission-workflow.md), reviewer Renata performs a final pre-implement-review pass on the mission artifacts; that is a separate review surface — for this WP, perform the implementation review as `curator-carla`.

## Implement command

```bash
spec-kitty agent action implement WP01 --agent claude
```
