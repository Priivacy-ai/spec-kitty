---
work_package_id: WP06
title: Re-home completeness baselines to the module partition
dependencies:
- WP03
- WP05
requirement_refs:
- FR-013
planning_base_branch: mission/modular-per-package-ci
merge_target_branch: mission/modular-per-package-ci
branch_strategy: Planning artifacts for this mission were generated on mission/modular-per-package-ci. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into mission/modular-per-package-ci unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
phase: Phase 3 - Consolidation
history:
- timestamp: '2026-08-15T00:00:00Z'
  agent: system
  action: Prompt generated via /spec-kitty.tasks
authoritative_surface: tests/_shard_registry.py
create_intent: []
execution_mode: code_change
owned_files:
- tests/_arch_shard_map.py
- tests/_next_shard_map.py
- tests/_shard_registry.py
- tests/architectural/test_arch_shard_marker_completeness.py
- tests/architectural/test_ci_collection_completeness.py
- tests/architectural/test_marker_job_completeness.py
- tests/specify_cli/skills/test_command_installer.py
tags: []
tracker_refs: []
---

# Work Package Prompt: WP06 – Re-home completeness baselines

**Implements**: FR-013. IC-06. **Depends on WP03 + WP05** (module partition + gate shape final).

## Goal

Relocate the completeness baselines that assume the current test partition so they match the module-owned split,
ensuring every relocated test resolves to exactly one CI home (avoid the double-marker CI-home trap).

## Scope

- Golden-count ceilings: `test_command_installer.py:707` (`len(CANONICAL_COMMANDS) == 15`),
  `test_twelve_agent_parity.py:188` (`== 12`) — re-point to the module-owned homes if counts/locations move.
- CI path filters routing these tests: `ci-quality.yml:497` (`src/specify_cli/skills/**`), `:834`
  (`tests/specify_cli/regression/**`), focused regression step `:838-846` — update to the new homes.
- Shard/marker maps: `tests/_shard_registry.py`, `tests/_arch_shard_map.py`, `tests/_next_shard_map.py` — update
  path→shard assignment for any relocated tests.
- Marker/collection completeness oracles: `test_marker_job_completeness.py`,
  `test_arch_shard_marker_completeness.py`, `test_ci_collection_completeness.py` — must stay green.

## ATDD / red-first (C-008)

- **T001 (RED first)**: after relocation, `test_marker_job_completeness.py` and the collection-completeness
  oracle assert every relocated test resolves to exactly one CI gate. Reproduce the trap (a relocated test with
  no home) RED, then fix.
- **T002**: golden-count + path-filter assertions reference the module-owned homes and pass.

## Validation surface (targeted)

```bash
PWHEADLESS=1 pytest tests/architectural/test_marker_job_completeness.py tests/architectural/test_arch_shard_marker_completeness.py tests/architectural/test_ci_collection_completeness.py -q
```

## Acceptance (FR-013)

- Every relocated test resolves to exactly one CI home; golden-count + path-filter assertions point at the
  module homes; marker/collection oracles green.
