---
work_package_id: WP02
title: All-consumer adoption, fetch reporting & contract
dependencies:
- WP01
requirement_refs:
- FR-004
- FR-007
- FR-008
tracker_refs: []
subtasks:
- T007
- T008
- T009
- T010
- T011
- T012
phase: Phase 1 - Thread A integration
assignee: ''
agent: claude
history:
- at: '2026-06-23T09:00:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/charter/
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- src/charter/drg.py
- src/charter/pack_context.py
- src/charter/context.py
- src/specify_cli/doctrine/org_charter.py
- src/specify_cli/doctrine/snapshot.py
- src/specify_cli/cli/commands/doctor.py
- src/specify_cli/charter_runtime/lint/checks/org_layer.py
- kitty-specs/layered-doctrine-org-layer-01KRNPEE/contracts/config-schema.yaml
- tests/integration/test_org_pack_subdir_e2e.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP02 – All-consumer adoption, fetch reporting & contract

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile in the frontmatter before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

---

## Objectives & Success Criteria

Route **every** pack-root consumer through `OrgPackConfig.effective_root` (WP01) so a subdir-rooted pack loads everywhere — most importantly the `doctor doctrine` health path. Report the effective root at fetch, and align the config-schema contract.

**Done when:**
- All enumerated consumers read the effective root; none re-derive from raw `local_path`.
- A git-sourced fixture pack rooted under `pack/` makes `doctor doctrine` report **healthy** (SC-001).
- No-subdir configs are byte-identical in behavior (SC-002).
- `doctrine fetch` reports artifact count at the effective root; a wrong `subdir` shows 0 (SC-003).
- Contract schema includes `subdir`. `ruff`+`mypy` clean.

## Context

- Spec FR-004/007/008, SC-001/002/003. Depends on WP01's `effective_root`.
- **Squad-enumerated consumer sites** (the BLOCKER fan-out — `research/post-spec-squad-findings.md`):
  - `src/charter/drg.py:137` → `load_org_pack(...)` — **the doctor-health path** (`doctor.py`→`load_org_drg`→`load_org_pack`). Highest priority.
  - `src/charter/pack_context.py:344` `_read_org_packs`; `src/charter/context.py:746` direct `org-charter.yaml` read.
  - `src/specify_cli/doctrine/org_charter.py:570` `load_org_charter_policy`; `src/specify_cli/cli/commands/doctor.py:2608` `_build_pack_entries`; `src/specify_cli/charter_runtime/lint/checks/org_layer.py:236` `DoctrineService(org_roots=...)`.
- Fetch: `src/specify_cli/doctrine/snapshot.py` orchestrates `source.fetch(local_path)`; clone target stays `local_path` (C-003). Report the count under the effective root post-fetch.
- Existing integration tests to mirror: `tests/integration/test_org_pack_artifact_lifecycle.py`, `tests/integration/test_org_pack_missing_path_hard_fails.py`.

## Subtasks & Detailed Guidance

### T007 — Adopt in `charter/drg.py`
- Where `build_org_drg_fragments`/loader reads `pack.local_path` (≈:137), use `pack.effective_root(repo_root)`. This is the load-bearing fix — without it `doctor doctrine` stays red.

### T008 — Adopt in `charter/pack_context.py` + `charter/context.py`
- `_read_org_packs` (pack_context.py:344) builds `PackContext.pack_roots` — use effective root. `context.py:746` direct `pack_path / "org-charter.yaml"` — use effective root.

### T009 — Adopt in `org_charter.py` + `doctor.py` + `org_layer.py`
- `org_charter.py:570` `load_org_charter_policy(pack.local_path)`; `doctor.py:2608` `_build_pack_entries` (snapshot/artifact counts/charter summary); `org_layer.py:236` lint `org_roots`. All → effective root.

### T010 — Fetch effective-root reporting
- In `snapshot.py`, after `source.fetch(local_path)` succeeds, compute the artifact count under `pack.effective_root(repo_root)` (not the clone root) for the reported `artifacts_written`/operator output (FR-007). Do not change the clone target (C-003).

### T011 — Contract schema [P]
- Update `kitty-specs/layered-doctrine-org-layer-01KRNPEE/contracts/config-schema.yaml` (`additionalProperties: false`) to add optional `subdir: string` with a description matching `contracts/config-schema-delta.md`.

### T012 — Integration tests (`tests/integration/test_org_pack_subdir_e2e.py`)
- **SC-001**: build a fixture pack with `org-charter.yaml` + `drg/fragment.yaml` under `pack/`, config `subdir: pack`; drive `doctor doctrine` (or `_collect_org_layer_data`/`load_org_drg`) and assert `errors == []` / healthy. Use realistic, production-shaped fixture content.
- **SC-002**: a no-subdir pack still resolves/validates identically (regression).
- **SC-003**: a wrong `subdir` → fetch reports 0 artifacts at the effective root.

## Branch Strategy

- **Strategy**: {{branch_strategy}}
- **Planning base branch**: {{planning_base_branch}}
- **Merge target branch**: {{merge_target_branch}}
- Execution worktree allocated per computed lane from `lanes.json`. **Implement WP01 first** (`spec-kitty agent action implement WP02 --agent claude` gates on WP01 approved/done).

## Definition of Done

- [ ] All 6 consumer sites use `effective_root`; grep proves no remaining raw `pack.local_path` root-reads in the FR-004 set.
- [ ] SC-001 integration test green (the non-fakeable acceptance anchor).
- [ ] SC-002 + SC-003 tests green. Contract schema updated.
- [ ] `ruff`+`mypy` clean; complexity ≤ 15.

## Risks & Reviewer Guidance

- **Risk**: missing one consumer = silent partial fix. The SC-001 end-to-end test is the catch-all; reviewer should also grep for `\.local_path` root-reads across the consumer set.
- **Reviewer**: confirm the clone target is unchanged (C-003) and only resolution/reporting moved to the effective root. Confirm fixtures are production-shaped (real ULIDs/paths), not toy placeholders.
