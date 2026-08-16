---
work_package_id: WP06
title: Migration manifest + completeness test (terminal)
dependencies:
- WP05
- WP07
- WP08
- WP09
requirement_refs:
- FR-008
- NFR-001
- NFR-005
planning_base_branch: kitty/mission-workflow-self-doc
merge_target_branch: kitty/mission-workflow-self-doc
branch_strategy: Planning artifacts for this mission were generated on kitty/mission-workflow-self-doc. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into kitty/mission-workflow-self-doc unless the human explicitly redirects the landing branch.
subtasks:
- T012
- T013
- T014
history: []
authoritative_surface: docs/development/
create_intent:
- docs/development/agent-memory-workflow-migration-manifest.md
- tests/docs/test_workflow_migration_manifest_complete.py
execution_mode: code_change
owned_files:
- docs/development/3-2-page-inventory.yaml
- docs/development/3-2-docs-retrieval-index.yaml
tags: []
tracker_refs: []
---

## Objective
The proof artifact: a manifest mapping all 49 audited memories + a fresh completeness test (NOT the inherited G1–G6 one) + the single rollup regen for the whole mission.

## Subtasks
- **T012** Author `docs/development/agent-memory-workflow-migration-manifest.md` (distinct file from Bucket 1's). Clusters A/B/C. Every row → `home:` (created file) / `already-home:` (existing cited file, incl. `ERROR_CODES.md`, SKILL.md, the toolguides, ADRs) / `learned-fact:` (`.kittify/memory/<file>`) / `keep-private` / `charter-candidate`. Frontmatter matches `docs/development/*.md`. **Pin (F2 coupling with WP09):** `collect-universe-once` resolves to `already-home:` (`packs/built-in/toolguides/EFFICIENT_LOCAL_TOOLING.md`) OR `keep-private` — **never** `learned-fact:` (WP09 does not create that note, so a `learned-fact:` row would fail the terminal path-check).
- **T013** New `tests/docs/test_workflow_migration_manifest_complete.py`: parse the manifest at runtime (no inline gap-filler list); assert all 49 rows carry a recognised token; `home:`/`already-home:`/`learned-fact:` are path-checked (file exists), `keep-private`/`charter-candidate` pathless-recognised; an anti-tautology self-test on synthetic fixtures. `pytestmark` matching `tests/docs/` siblings.
- **T014** Regenerate BOTH rollups (`PYTHONPATH=. .venv/bin/python scripts/docs/inventory_lockfile.py --write docs/development/3-2-page-inventory.yaml` AND `scripts/docs/docs_index.py --write`), then `check_docs_freshness --ci` errors=0 (this is the mission's SINGLE rollup regen, capturing all doc changes from WP01–05).

## Rules
This WP runs last (deps on all home-producing WPs) so path-checks + the rollup regen see the complete tree. `.venv/bin/python`, never bare `uv run`.

## Done
Manifest resolves all 49; completeness test green + non-tautological; freshness errors=0.
