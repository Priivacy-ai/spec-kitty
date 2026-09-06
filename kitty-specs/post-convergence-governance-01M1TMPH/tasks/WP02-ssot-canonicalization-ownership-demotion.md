---
work_package_id: WP02
title: Modularity SSOT canonicalization + ownership-doc demotion (D7)
dependencies: []
requirement_refs:
- FR-004
- FR-005
- FR-006
- FR-007
tracker_refs: []
planning_base_branch: tier3/governance-enforcement
merge_target_branch: tier3/governance-enforcement
subtasks:
- T001
- T002
- T003
- T004
- T005
phase: Phase 1 - SSOT canonicalization
agent_profile: architect-alphonso
authoritative_surface: docs/architecture/
role: implementer
task_type: implement
owned_files:
- docs/architecture/05_ownership_manifest.yaml
- docs/architecture/05_ownership_map.md
- docs/architecture/00_landscape/README.md
- tests/architecture/test_ownership_manifest_schema.py
- pyproject.toml
- AGENTS.md
---

# WP02 — Modularity SSOT canonicalization + ownership-doc demotion (D7)

Name the enforced pair (`pyproject [wheel].packages` + `conftest.landscape`/`test_layer_rules`) as the
canonical modularity SSOT. Delete the stale, self-authoritative `05_ownership_manifest.yaml` and its
key-pinning schema gate (D7), and reduce `05_ownership_map.md` to a narrative pointer. Frame
`zeitgeist_client`/`saas_client` as clients of the upstream authoritative repos.

## Requirements
- **FR-004** enforced pair named canonical in `CLAUDE.md`/`AGENTS.md` + `00_landscape`.
- **FR-005** `05_ownership_manifest.yaml` deleted; `05_ownership_map.md` narrative-only.
- **FR-006** `test_ownership_manifest_schema.py` deleted (D7) + its `ruff.format.exclude` entry removed.
- **FR-007** arch docs describe the client packages as upstream clients.

## Acceptance
- The manifest and its schema test no longer exist; `pyproject` no longer lists the test in
  `ruff.format.exclude`; `test_ruff_format_exclude_ratchet` passes.
- `05_ownership_map.md` is narrative-only, names the enforced pair, and lists no deleted
  `sync/`/`saas/`/`doctrine/`/`lifecycle/`/`orchestrator/` path.
- `CLAUDE.md`/`AGENTS.md` + `00_landscape` name the enforced pair as SSOT and frame the client packages.
- `test_no_legacy_terminology` + `test_no_stale_charter_path_literals` stay green.

## Notes
- Overlaps Tier-1 PR #3885 (which edited the ownership pair); this WP supersedes those edits by deleting
  the manifest. Flag merge-ordering in the PR body.
