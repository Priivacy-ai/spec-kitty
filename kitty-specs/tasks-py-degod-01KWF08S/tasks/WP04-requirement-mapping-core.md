---
work_package_id: WP04
title: Requirement-mapping decision core (pure)
dependencies:
- WP03
requirement_refs:
- FR-002
- FR-005
- NFR-002
tracker_refs: []
planning_base_branch: design/degod-tasks-2116
merge_target_branch: design/degod-tasks-2116
branch_strategy: Planning artifacts for this mission were generated on design/degod-tasks-2116. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into design/degod-tasks-2116 unless the human explicitly redirects the landing branch.
subtasks:
- T018
- T019
- T020
- T021
phase: Phase 3 - Pure cores
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "3057908"
history:
- at: '2026-07-01T15:16:35Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: randy-reducer
authoritative_surface: src/specify_cli/cli/commands/agent/tasks_mapping_core.py
create_intent:
- src/specify_cli/cli/commands/agent/tasks_mapping_core.py
- tests/specify_cli/cli/commands/agent/test_tasks_mapping_core.py
execution_mode: code_change
owned_files:
- src/specify_cli/cli/commands/agent/tasks_mapping_core.py
- tests/specify_cli/cli/commands/agent/test_tasks_mapping_core.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP04 – Requirement-mapping decision core (pure)

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `randy-reducer`
- **Role**: `implementer`
- **Agent/tool**: `claude`

---

## Objectives & Success Criteria

Extract `map_requirements`' FR↔WP mapping/validation into a **pure decision**, separated from the frontmatter write; wire by delete-and-sentinel.

- `plan_mapping(MappingRequest)->MappingPlan` in `tasks_mapping_core.py` — pure; consumes injected reads.
- `--cov-branch` unit tests cover offenders (malformed/unknown_spec_id), unmapped-FR, modes (wp_refs/batch/tracker_only/replace).
- Wiring deletes the inline mapping block; sentinel test proves drive; golden byte-identical.

## Context & Constraints

- Read `data-model.md` (§`MappingPlan`), `contracts/ports-and-cores.md` (`plan_mapping`), `research.md` (D7).
- Pure core returns `to_write` + `offenders` + `unmapped_fr`; the **orchestrator applies** the frontmatter write via the port (no I/O in the core — INV-4).
- **Anti-shadow-code**: T020 deletes the inline block; T021 sentinel proves drive.
- **Ownership/leeway**: own the new core + test; the `map_requirements` edit is a documented leeway edit to `tasks.py` (owned by WP09); full thinning is WP07.

## Branch Strategy

- **Planning base branch**: `design/degod-tasks-2116`
- **Merge target branch**: `design/degod-tasks-2116`

## Subtasks & Detailed Guidance

### T018 — Failing-first per-branch unit test
`test_tasks_mapping_core.py` covering malformed refs, unknown spec IDs, unmapped FRs, each mode (`wp_refs`/`batch`/`tracker_only`/`--replace` union-vs-overwrite). `--cov-branch`. RED against base.

### T019 — Implement `plan_mapping` (pure)
Pure; consumes injected reads (Fake `FsReader` in tests); no frontmatter write.

### T020 — Delete inline block + wire
Delete `map_requirements`' inline mapping block; route through `plan_mapping`; write applied via port. Golden byte-identical.

### T021 — Sentinel test + green
Fake-core sentinel proves the plan drives the write; run golden + per-core test; ruff+mypy clean.

## Test Strategy

- `PWHEADLESS=1 pytest tests/specify_cli/cli/commands/agent/test_tasks_mapping_core.py tests/specify_cli/cli/commands/agent/test_tasks_cli_contract.py -q --cov-branch`

## Risks & Mitigations

- Leaking the frontmatter write into the core breaks purity (INV-4) — return the plan, orchestrator applies it.

## Review Guidance

- Confirm purity, offenders/mode branch coverage, deleted inline block, sentinel drive, byte-identical golden.

## Activity Log

- 2026-07-01T15:16:35Z – system – Prompt created.
- 2026-07-01T21:36:35Z – claude:opus:randy-reducer:implementer – shell_pid=3011545 – Assigned agent via action command
- 2026-07-01T22:02:35Z – claude:opus:randy-reducer:implementer – shell_pid=3011545 – plan_mapping pure core: 8 branches (--cov-branch 100%), inline mapping/validation/merge/coverage block DELETED + wired + 2 sentinel tests. Write-timing reproduced: PARTIAL-write-then-refuse — core owns only PRE-write new-ref offenders (refuse before write, no write) + to_write + unmapped_fr; the post-write stale gate stays in the shell at its ORIGINAL position after the frontmatter write, so a pre-existing on-disk stale ref still refuses AFTER the partial write. Golden 42 byte-identical, ports 19, transition 48; full agent dir 878 passed; strict mypy + ruff clean.
- 2026-07-01T22:03:33Z – claude:opus:reviewer-renata:reviewer – shell_pid=3057908 – Started review via action command
- 2026-07-01T22:11:20Z – user – shell_pid=3057908 – APPROVE (reviewer-renata, verified vs code). Write-timing parity: original write loop (frontmatter writes) precedes the post-write stale-refs Exit(1) gate; new code preserves this exactly — pre-write malformed/unknown offender gates refuse BEFORE any write (no write), the frontmatter write is unchanged in position, and the post-write stale gate stays untouched at its original position AFTER the write (partial-write-on-refusal preserved; WP03 defect class NOT reintroduced). Only pure READS (existing_all_refs, tasks_md) moved earlier to feed plan_mapping — no write/refusal reordering. Coverage byte-identity: reconstruction (mapped=total-len(unmapped)) proven byte-identical to compute_coverage over post-write disk state analytically (set-partition identity) AND empirically across zero-FR/all-mapped/all-unmapped/dup-refs/FR-multi-WP; projected==post-write guaranteed by the pre-existing unknown_wps file-existence gate + idempotent re-normalize; total_mappings still uses the post-write read. Purity: plan_mapping has zero FS/git/clock I/O (grep clean, docstring-only mentions); write stays in shell. Inline block genuinely DELETED not shadowed (validate/merge/compute_coverage removed; only a comment references compute_coverage). Sentinel tests non-tautological: offenders drive exit-1 with sentinel token; to_write drives written frontmatter + total_mappings; unmapped_fr drives reported coverage. Branch cov 8/8 real branches 100%. Gates: mapping-core 18 passed; agent dir 878 passed/2 xfailed; golden contract 42 passed; strict mypy Success; ruff clean; zero suppressions added. tasks.py edit is documented WP09-owned leeway per WP prompt.
