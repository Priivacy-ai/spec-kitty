---
work_package_id: WP02
title: Page inventory (active bulk edit)
dependencies:
- WP01
requirement_refs:
- FR-002
planning_base_branch: main
merge_target_branch: main
branch_strategy: lane-based; one worktree per lane allocated at implement time
subtasks:
- T004
- T005
- T006
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
- docs/development/3-2-page-inventory.yaml
role: curator
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your agent profile:

```
/ad-hoc-profile-load curator-carla
```

## Objective

Author the machine-readable page inventory that classifies every docs page in the repo with a `version_tag`, `divio_type`, and ownership metadata. This is the source of truth for the leakage check (WP04), the IA doc (WP08), and the archive/migration plan (WP09).

## Context

- FR-002 requires 100% coverage of pages under `docs/`, `architecture/`, and root `README.md`.
- Schema is `PageInventoryEntry` from [`data-model.md`](../data-model.md). YAML on disk is one list, one entry per page.
- Bulk-edit guardrail from WP01 applies: this WP is the rollout of `serialized_keys.add: version_tag` against the docs tree. Implement-review MUST verify Bulk Edit Gate compliance.
- Heuristics for `version_tag`:
  - Paths under `docs/1x/**` → `archival`.
  - Paths under `docs/2x/**` → `archival`.
  - Paths under `docs/3x/**` or `docs/migration/from-3-1-*` → `migration` or `supported` (per plan default for decision `01KS4KTGTN4DBE60JFWKEA2FJB`, fold 3.1 as `migration`).
  - Paths under `docs/development/**`, `docs/architecture/**`, `architecture/**` → `internal`.
  - Everything else under `docs/**` not yet edited for 3.2 → `current` provisionally; flag with `notes` for manual review.

## Subtasks

### T004 — Author `docs/development/3-2-page-inventory.yaml`

- Walk the file set from WP01's survey annex.
- For each markdown file, write one `PageInventoryEntry` row with:
  - `path` (repo-relative)
  - `tag` (one of the 5 enum values)
  - `divio_type` (one of `tutorial`/`how-to`/`reference`/`explanation`/`none`)
  - `owning_workstream` (A/B/C/D/E/F or `none`)
  - `current_target` (boolean; True iff `tag == current`)
  - `citation_refs` (empty list except for harness or external-cite pages)
  - `notes` (optional)
- Sort entries by `path` for deterministic diff.

### T005 — Validate inventory invariants

Run the leakage rules from `data-model.md` §"PageInventoryEntry":

- Every `path` points to an existing file.
- `tag == archival` ⇒ `current_target == false`.
- `tag == current` ⇒ `current_target == true`.
- `tag == migration` pages have the migration banner pattern in their body (verified later by `version_leakage_check.py`; for this WP, record the planned banner location in `notes`).

For any row that fails, fix the row or add a `notes` entry naming the conflict so WP04's leakage check can target it.

### T006 — Flag manual-review pages

Add `notes: "MANUAL_REVIEW: <reason>"` for any page where the heuristic was ambiguous (e.g., a `docs/explanation/` page that quotes 2.x material verbatim). The IA doc in WP08 resolves these flags by reviewing each page and deciding `current`, `supported`, or `migration`.

## Branch Strategy

- Planning base: `main`
- Merge target: `main`
- Lane: `A`. Reuses the lane-A worktree from WP01.

## Test Strategy

- Bulk-edit gate: implementer + reviewer verify the inventory rollout matches the `serialized_keys.add` rule in `occurrence_map.yaml` (one entry per docs page, no duplicates).
- Schema validation: WP04's tests load this YAML via `_inventory.py` and reject malformed rows. The implementer should perform a dry-run load against the shipped `data-model.md` shape before commit.

## Definition of Done

- [ ] `docs/development/3-2-page-inventory.yaml` exists with one row per docs page.
- [ ] All five tag values appear at least once (current, supported, migration, archival, internal).
- [ ] Every row passes the invariants from T005.
- [ ] Bulk-edit gate green per `occurrence_map.yaml`.
- [ ] No files outside `owned_files` modified.

## Risks

- **Inventory drift** — pages added between WP01 survey and WP02 rollout. Mitigation: re-run `git ls-files docs/ architecture/` immediately before authoring the YAML; resolve any new file.
- **Tag mis-classification** — false-positive `current` tag on a page that quotes archival material. Mitigation: aggressive use of `MANUAL_REVIEW` notes; WP08's IA doc cleans them up.

## Reviewer Guidance

- Diff `git diff --stat` should show exactly one new file under `owned_files`.
- Confirm the row count equals the page count from WP01 survey annex.
- Confirm no `version_tag` frontmatter is yet written into live docs pages — that rollout is intentionally deferred to a future mission after this docs refresh lands, per C-001 planning-only constraint. The inventory is the canonical surface for the current mission.

## Implement command

```bash
spec-kitty agent action implement WP02 --agent claude
```
