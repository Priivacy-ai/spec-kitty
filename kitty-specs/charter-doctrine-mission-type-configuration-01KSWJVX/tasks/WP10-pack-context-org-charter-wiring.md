---
work_package_id: WP10
title: PackContext wiring into OrgCharterPolicy loader
dependencies:
- WP09
requirement_refs:
- FR-001
- FR-003
tracker_refs: []
planning_base_branch: feat/doctrine-mission-type-spec-01KSWJVX
merge_target_branch: feat/doctrine-mission-type-spec-01KSWJVX
branch_strategy: Planning artifacts for this mission were generated on feat/doctrine-mission-type-spec-01KSWJVX. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/doctrine-mission-type-spec-01KSWJVX unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-charter-doctrine-mission-type-configuration-01KSWJVX
base_commit: ee78aa62997f040dd18464b6a54b7a3dafd63479
created_at: '2026-05-30T20:03:41.796051+00:00'
subtasks:
- T063
- T064
- T065
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "3222856"
history:
- at: '2026-05-30T17:21:57Z'
  event: created
  note: Initial task breakdown
agent_profile: python-pedro
authoritative_surface: tests/specify_cli/doctrine/
execution_mode: code_change
owned_files:
- tests/specify_cli/doctrine/test_org_charter_pack_context.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your agent profile:

/ad-hoc-profile-load python-pedro

This profile contains the coding standards, testing requirements, and
architectural constraints you must follow throughout this work package.

---

# Work Package Prompt: WP10 — PackContext wiring into OrgCharterPolicy loader

## Context

WP09 implemented the `extends:` chain resolver in isolation. This WP wires it into the actual loader: `load_org_charter_policies()` receives a `PackContext` (from WP06), uses it to locate org packs, and runs each pack through `_resolve_chain()` before merging. The resolver never reads `.kittify/config.yaml` directly — all data flows through `PackContext`.

## Objective

Wire the `PackContext`-aware `load_org_charter_policies()` (implemented in WP09) into all charter callers. Ensure no config.yaml reads remain in the charter resolver path (beyond `PackContext.from_config()` itself). Write integration tests.

**Note**: The signature update of `load_org_charter_policies()` and the `_resolve_chain` wiring to `PackContext.pack_roots` were moved into WP09 (subtasks T061-sig and T062-chain), since those changes are in `src/specify_cli/doctrine/org_charter.py` which WP09 owns. This WP owns the charter-side callers and the integration test.

## Subtasks

### T063 — Audit and confirm no config.yaml reads in resolver path

Audit the call chain starting from `load_org_charter_policies()` through `_resolve_chain()` and `_merge_chain()`. Verify no direct `Path(".kittify/config.yaml").read_text()` or `yaml.safe_load(config_path.read_text())` calls exist inside these functions when a `PackContext` is provided.

The only permitted direct config.yaml read is in `PackContext.from_config()` itself (charter module, not doctrine module). Document any remaining direct reads as `# TODO: pass PackContext` comments for future cleanup.

### T064 — Confirm caller updates are scheduled in the owning WPs

The two main callers of `load_org_charter_policies()` in the charter layer are:
- `src/charter/drg.py` — owned by WP11. WP11's T064-drg task must wire PackContext there.
- `src/charter/context.py` — owned by WP01. WP01's T006 touches this file; when done, the implementer should leave a `# TODO (WP10/WP11): wire PackContext.from_config() into load_org_charter_policies() call` comment for the future WPs.

This WP (WP10) does not make source code changes. Its value is the integration test (T065) that proves the full chain works end-to-end once WP09, WP11, and WP01 have all landed in the lane.

### T065 — Integration tests

Write `tests/specify_cli/doctrine/test_org_charter_pack_context.py`:

Test cases:
- **Full chain resolution**: Two org packs where B extends A; `load_org_charter_policies` with a `PackContext` containing both pack roots returns the merged policy with unioned directives
- **PackContext pack_roots ordering**: org packs are processed in `pack_roots` order
- **Backward compatibility**: `load_org_charter_policies(repo_root, pack_context=None)` still works for projects without a PackContext
- **No config.yaml read in resolver**: mock or monkeypatch the config.yaml file; resolution works entirely from PackContext without reading config.yaml

## Acceptance Criteria

- [ ] `src/charter/drg.py` and `src/charter/context.py` call `load_org_charter_policies()` with a `PackContext`
- [ ] No new direct config.yaml reads in `_resolve_chain()` or `_merge_chain()` when PackContext is provided
- [ ] All existing charter tests still pass (backward compat via `None` default preserved)
- [ ] Integration tests for full chain resolution via PackContext pass
- [ ] `mypy --strict` clean on `src/charter/drg.py` and `src/charter/context.py`

## References

- FR-001: extends: chain resolution
- C-005: PackContext isolation — resolver never reads config.yaml
- WP06: PackContext implementation
- WP09: _resolve_chain() implementation

## Activity Log

- 2026-05-30T20:03:42Z – claude:sonnet:python-pedro:implementer – shell_pid=3208161 – Assigned agent via action command
- 2026-05-30T20:08:09Z – claude:sonnet:python-pedro:implementer – shell_pid=3208161 – Ready for review: integration tests for PackContext wiring into OrgCharterPolicy loader
- 2026-05-30T20:08:39Z – claude:opus:reviewer-renata:reviewer – shell_pid=3222856 – Started review via action command
