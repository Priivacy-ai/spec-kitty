---
work_package_id: WP02
title: Classification ledger of all bypass sites
dependencies: []
requirement_refs:
- FR-001
planning_base_branch: fix/read-side-placement-seam-migration
merge_target_branch: fix/read-side-placement-seam-migration
branch_strategy: Planning artifacts for this mission were generated on fix/read-side-placement-seam-migration. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/read-side-placement-seam-migration unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-read-side-placement-seam-migration-01KYHP67
base_commit: 446b09ab4c219a29984c79cdba41f73c4779b719
created_at: '2026-07-27T12:32:41.808583+00:00'
subtasks:
- T004
- T005
- T006
phase: Phase 2 - Classify
history:
- at: '2026-07-27T12:00:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: paula-patterns
authoritative_surface: docs/development/read-side-seam-classification.md
create_intent:
- docs/development/read-side-seam-classification.md
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- docs/development/read-side-seam-classification.md
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP02 – Classification ledger

## ⚡ Do This First: Load Agent Profile
Use `/ad-hoc-profile-load` to load `paula-patterns` (role implementer, agent claude).

## Objective
Produce the migration spine: classify every bypass call site. This gates WP03–WP08. Read [data-model.md](../data-model.md) (ledger schema) + [research.md](../research.md) (hard cases) + [contracts/read-side-gate.md](../contracts/read-side-gate.md).

## Subtasks
### T004 — Enumerate
Grep `src/` for `candidate_feature_dir_for_mission` (kind-blind) and `resolve_planning_read_dir` (lenient), deduped by file (exclude the definition modules `_read_path_resolver.py`, `resolution.py`). ~59 files. Record per file: symbol(s), call-count.
### T005 — Classify each site
Per the data-model verdict rules assign one of:
- **sanction-infra**: `_read_path_resolver.py` (authority), `coordination/surface_resolver.py`, `mission_runtime/write_target_degrade.py` (resolution infra).
- **stay-lenient**: diagnostic/audit/corpus-walk readers that MUST tolerate half-materialized/deleted coord (doctor, dashboard/scanner, cutover audit, status/aggregate, and similar) — record rationale.
- **migrate-fail-loud**: everything else. For kind-blind sites, determine the target `MissionArtifactKind` (which artifact does the read target — planning=PRIMARY vs status/coord). Retrospective reads → `resolve_retrospective_home`. Flag multi-kind readers (need splitting).
Cite file:line for each. When a call's fail-loud-appropriateness is genuinely ambiguous, default to stay-lenient with rationale (safer — no audit regression) and note it for reviewer.
### T006 — Write the ledger
Write `docs/development/read-side-seam-classification.md` as a table (file, symbol, sites, family, verdict, kind, rationale) with a `title`/`description`/`doc_status`/`type` frontmatter block. 100% coverage, no `unknown`. This is the authoritative input WP03–WP08 consume. **Because it is a new `docs/` page, freshen the docs gate**: add its `PageInventoryEntry` + regen the index (`PYTHONPATH=. uv run python scripts/docs/inventory_lockfile.py --write <tmp> && cp` + `docs_index.py --write`), then `check_docs_freshness.py --ci --link-check none` clean (see the E-mission closeout gotcha in memory).

## Gates
No code change (planning artifact). Sanity: the ledger's file list matches a fresh grep (no site missed).

## DoD / Review
Every bypass site has a verdict + (for kind-blind migrate) a kind + (for stay-lenient/sanction) a rationale. Finish: commit the ledger, `mark-status T004 T005 T006 --status done`, `move-task WP02 --to for_review`.
