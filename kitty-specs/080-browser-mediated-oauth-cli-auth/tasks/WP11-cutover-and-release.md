---
work_package_id: WP11
title: Password Removal, Migration, and Release Preparation
dependencies:
- WP09
- WP10
requirement_refs:
- FR-013
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T081
- T082
- T083
- T084
- T085
- T086
- T087
- T088
history: []
authoritative_surface: src/specify_cli/
execution_mode: code_change
owned_files:
- src/specify_cli/auth.py
- src/specify_cli/sync/client.py
- src/specify_cli/sync/batch.py
- src/specify_cli/sync/background.py
- src/specify_cli/tracker/saas_client.py
- tests/sync/
status: pending
tags: []
---

# WP11: Password Removal, Migration, and Release Preparation

**Objective**: Complete the hard cutover. Remove all password-based auth code, update documentation, prepare GA release with 72+ hour staging validation.

**Context**: Final pre-release work. Depends on WP09 (commands), WP10 (testing).

**Acceptance Criteria**:
- [ ] No password prompts remain
- [ ] All password-based endpoints removed
- [ ] Commands fail cleanly if not authenticated (no password fallback)
- [ ] Migration guide provided
- [ ] Staging validation window ~72+ hours
- [ ] Release notes prepared
- [ ] All tests pass

---

## Subtask Guidance

### T081-T088: Password Removal & Release

**Code Cleanup**:
- Remove password prompts from `src/specify_cli/auth.py`
- Remove password-based token endpoints from all transports
- Update all auth calls to require OAuth (no fallback)
- Remove legacy test fixtures

**Migration & Docs**:
- Create migration guide: "Run `spec-kitty auth login` to authenticate"
- Update README to reference OAuth-only auth
- Add changelog entry: "BREAKING: Password-based auth removed"
- Document SaaS contract (endpoints, error codes)

**Staging Validation**:
- Deploy to staging environment for 72+ hours
- Monitor for bugs, performance issues
- Verify all features work end-to-end
- Get sign-off from SRE + product lead

**Files**:
- Modified: `src/specify_cli/auth.py`, `sync/client.py`, `batch.py`, `background.py`, `tracker/saas_client.py`
- New: Migration guide, changelog entry, release notes

---

## Definition of Done

- [ ] All password code removed
- [ ] No password fallback exists
- [ ] Commands fail clearly if not authenticated
- [ ] Migration guide provided to users
- [ ] Staging validation window completed (~72 hours)
- [ ] Release notes approved
- [ ] GA cutover authorized by SRE + product

