---
work_package_id: WP01
title: Canonical project consent authority
dependencies: []
requirement_refs:
- FR-001
- FR-002
- FR-006
- FR-007
- FR-008
- FR-012
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-per-project-sync-consent-ledgers-01KZNNZS
base_commit: 873544c4e3a2c7ca5723f11cb2456b37f30b9c45
created_at: '2026-08-10T11:32:53.872579+00:00'
subtasks:
- T001
- T002
- T003
- T004
- T005
phase: Phase 1 - Consent authority
history:
- timestamp: '2026-08-10T11:25:00Z'
  agent: codex
  action: Prompt generated via mission task materialization
authoritative_surface: src/
create_intent:
- tests/sync/test_project_consent_authority_3262.py
execution_mode: code_change
owned_files:
- src/specify_cli/sync/consent.py
- src/specify_cli/sync/routing.py
- tests/sync/test_project_consent_authority_3262.py
- tests/architectural/test_egress_consent_boundary.py
tags: []
tracker_refs: []
---

# Work Package Prompt: WP01 – Canonical project consent authority

Build the single source of truth for whether a project may use hosted sync.

Start red. Prove that a project without explicit consent is denied even when
`SPEC_KITTY_ENABLE_SAAS_SYNC=1`. Then change the resolver so global flags can
only disable or expose rollout surfaces, never grant egress consent.

## Requirements

- FR-001, FR-002, FR-006, FR-007, FR-008, FR-012
- Plan concern: IC-01

## Acceptance

- Default project consent is denied.
- Explicit project opt-in/out is represented by the canonical decision object.
- Environment/config rollout flags cannot grant consent.
- Architectural tests catch bypass transmitters.

## Implementation evidence — 2026-08-10

Current origin HEAD already implements the source-side WP01 invariant in
`src/specify_cli/sync/consent.py`: `_answer_env()` returns `None` unconditionally,
and the terminal default says `SPEC_KITTY_ENABLE_SAAS_SYNC` arms the machine but
never grants per-project consent.

Focused validation:

```bash
SPEC_KITTY_NO_UPGRADE_CHECK=1 env -u SPEC_KITTY_ENABLE_SAAS_SYNC \
  uv run --group dev --extra test pytest \
  tests/sync/test_consent_resolver_3030.py \
  tests/cli/commands/test_sync_commands.py \
  tests/architectural/test_egress_consent_boundary.py -q
```

Result: `94 passed, 2 xfailed in 57.43s`.

Key existing pins:

- `tests/sync/test_consent_resolver_3030.py::test_absence_denies_even_with_the_env_var_armed`
- `tests/sync/test_consent_resolver_3030.py::test_project_local_refusal_outranks_the_env_override`
- `tests/sync/test_consent_resolver_3030.py::test_repo_default_grant_does_not_consent_for_an_unrecorded_uuid`
