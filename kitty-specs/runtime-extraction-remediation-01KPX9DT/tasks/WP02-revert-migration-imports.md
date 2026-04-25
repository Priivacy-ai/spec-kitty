---
work_package_id: WP02
title: Revert upgrade migration imports to shim paths
dependencies:
- WP01
requirement_refs:
- FR-003
- FR-004
planning_base_branch: kitty/mission-runtime-mission-execution-extraction-01KPDYGW
merge_target_branch: kitty/mission-runtime-mission-execution-extraction-01KPDYGW
branch_strategy: Planning artifacts for this feature were generated on kitty/mission-runtime-mission-execution-extraction-01KPDYGW. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into kitty/mission-runtime-mission-execution-extraction-01KPDYGW unless the human explicitly redirects the landing branch.
subtasks:
- T004
- T005
- T006
agent: "claude:claude-sonnet-4-6:python-pedro:implementer"
shell_pid: "1136669"
history:
- date: '2026-04-23T13:58:27Z'
  author: reviewer-renata
  event: created
agent_profile: python-pedro
authoritative_surface: src/specify_cli/upgrade/
execution_mode: code_change
lane: planned
owned_files:
- src/specify_cli/upgrade/compat.py
- src/specify_cli/upgrade/migrations/m_2_0_6_consistency_sweep.py
- src/specify_cli/upgrade/migrations/m_2_0_7_fix_stale_overrides.py
- src/specify_cli/upgrade/migrations/m_2_1_3_restore_prompt_commands.py
- src/specify_cli/upgrade/migrations/m_2_1_4_enforce_command_file_state.py
- src/specify_cli/upgrade/migrations/m_3_1_2_globalize_commands.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading further, load the assigned agent profile for this session:

```
/ad-hoc-profile-load python-pedro
```

Do not begin implementation until the profile is active.

---

## Objective

Revert 7 import lines across 6 upgrade files from `runtime.*` canonical paths back to `specify_cli.runtime.*` shim paths. This fixes **DRIFT-2** (the second blocking finding) that causes `MigrationDiscoveryError` when `spec-kitty upgrade` is run in installed environments.

**Lane note** (I1 fix): WP01 and WP02 are logically independent (no code overlap, different files). The lane system serializes them in lane-a because they share a worktree. In practice, WP02 implementation can start as soon as WP01's commit is in the worktree — it does not need to wait for WP01 to be reviewed or approved. Check `spec-kitty agent tasks status` before starting; if WP01 is `in_progress` or later, WP02 may proceed.

**Why this is broken**: Mission #95 WP09 rewrote these migration files to use `runtime.discovery.*` and `runtime.orchestration.*`. However, `runtime` is only importable when `src/` is on `sys.path`. Upgrade migration discovery happens via dynamic import — in installed environments without `src/` on the path, `from runtime.discovery.home import ...` fails with `ModuleNotFoundError`, causing the upgrade system to abort.

**Why the fix is shim paths, not canonical paths**: Migration modules are version-pinned. They must remain importable in any environment that has `spec-kitty` installed, regardless of whether `src/runtime` is on `sys.path`. The `specify_cli.runtime.*` shim paths are always importable because the shims are part of the `specify_cli` package (already in `pyproject.toml`).

---

## Context

**Constraint C-002**: Migration modules MUST use `specify_cli.runtime.*` shim paths. Do NOT use `runtime.*` canonical paths in any file under `src/specify_cli/upgrade/`.

**IMPORTANT**: Only change the import lines listed in T004. Do NOT modify any other code, comments, or logic in these files. Migration files are version-pinned artefacts; unintended changes are a correctness risk.

---

## Subtask T004 — Apply the 7 import reversions

**Purpose**: Replace each `runtime.*` import in the 6 migration files with its `specify_cli.runtime.*` equivalent.

**Complete mapping** (apply all 7 changes):

| File | Remove this line | Replace with this line |
|---|---|---|
| `upgrade/compat.py` | `from runtime.discovery.home import get_kittify_home` | `from specify_cli.runtime.home import get_kittify_home` |
| `migrations/m_2_0_6_consistency_sweep.py` | `from runtime.orchestration.doctor import check_stale_legacy_assets` | `from specify_cli.runtime.doctor import check_stale_legacy_assets` |
| `migrations/m_2_0_7_fix_stale_overrides.py` | `from runtime.discovery.home import get_package_asset_root` | `from specify_cli.runtime.home import get_package_asset_root` |
| `migrations/m_2_0_7_fix_stale_overrides.py` | `from runtime.orchestration.migrate import SHARED_ASSET_DIRS, SHARED_ASSET_FILES` | `from specify_cli.runtime.migrate import SHARED_ASSET_DIRS, SHARED_ASSET_FILES` |
| `migrations/m_2_1_3_restore_prompt_commands.py` | `from runtime.discovery.home import get_kittify_home, get_package_asset_root` | `from specify_cli.runtime.home import get_kittify_home, get_package_asset_root` | lazy — inside `apply()` |
| `migrations/m_2_1_4_enforce_command_file_state.py` | `from runtime.discovery.home import get_kittify_home, get_package_asset_root` | `from specify_cli.runtime.home import get_kittify_home, get_package_asset_root` | lazy — inside `apply()` |
| `migrations/m_3_1_2_globalize_commands.py` | `from runtime.discovery.home import get_kittify_home` | `from specify_cli.runtime.home import get_kittify_home` |

**Steps**:

1. For each row in the table above, open the file and replace the exact import line. The replacements in `m_2_1_3` and `m_2_1_4` are **lazy imports** (inside a function body, not at module level) — read each file to locate the exact line before editing.

2. After editing each file, verify no other lines changed:
   ```bash
   git diff src/specify_cli/upgrade/compat.py
   git diff src/specify_cli/upgrade/migrations/m_2_0_6_consistency_sweep.py
   # ... repeat for each file
   ```
   Expected: only the import line differs.

**Files touched**: 6 files listed in the table above.

**Validation**: `git diff` for each file shows only the import line changed. No logic, no comments, no blank lines altered.

---

## Subtask T005 — Run upgrade tests and verify no MigrationDiscoveryError

**Purpose**: Confirm that reverting the imports resolves the `MigrationDiscoveryError` and upgrade still works.

**Steps**:

1. Run the upgrade test suite:
   ```bash
   pytest tests/upgrade/ -v -q --tb=short 2>&1 | tail -15
   ```

2. If upgrade tests pass, also run a quick discovery check:
   ```bash
   python -c "
   import sys; sys.path.insert(0,'src')
   from specify_cli.upgrade.migrations import auto_discover_migrations
   auto_discover_migrations()
   print('Migration discovery OK')
   " 2>&1
   ```
   Expected: prints `Migration discovery OK` with no errors.

3. If the repo has `spec-kitty upgrade` available in PATH:
   ```bash
   spec-kitty upgrade --dry-run 2>&1 | head -20
   ```
   Expected: upgrade plan shown without `MigrationDiscoveryError`.

**Validation**: `pytest tests/upgrade/` passes. `auto_discover_migrations()` completes without error.

---

## Subtask T006 — Verify no `runtime.*` imports remain in upgrade modules

**Purpose**: Confirm the reversion is complete and no accidental `runtime.*` imports remain in the upgrade layer.

**Steps**:

1. Run:
   ```bash
   rg "from runtime\." src/specify_cli/upgrade/ 2>/dev/null && echo "FOUND (bad)" || echo "CLEAN (good)"
   ```
   Expected: `CLEAN (good)` — zero matches.

2. Confirm the shim paths are in place:
   ```bash
   rg "from specify_cli\.runtime\." src/specify_cli/upgrade/ 2>/dev/null | head -10
   ```
   Expected: shows 7 lines matching the entries from the T004 table.

**Validation**: First scan returns zero `runtime.*` hits. Second scan shows the 7 expected shim-path imports.

---

## Branch Strategy

Work in the execution worktree allocated by `spec-kitty agent action implement WP02 --agent claude`. This WP is **independent of WP01** and can run in parallel.

- **Planning branch**: `kitty/mission-runtime-mission-execution-extraction-01KPDYGW`
- **Merge target**: `kitty/mission-runtime-mission-execution-extraction-01KPDYGW`

---

## After Implementation

```bash
git add src/specify_cli/upgrade/compat.py \
  src/specify_cli/upgrade/migrations/m_2_0_6_consistency_sweep.py \
  src/specify_cli/upgrade/migrations/m_2_0_7_fix_stale_overrides.py \
  src/specify_cli/upgrade/migrations/m_2_1_3_restore_prompt_commands.py \
  src/specify_cli/upgrade/migrations/m_2_1_4_enforce_command_file_state.py \
  src/specify_cli/upgrade/migrations/m_3_1_2_globalize_commands.py

git commit -m "fix(DRIFT-2): revert upgrade migration imports to specify_cli.runtime.* shim paths

Reverts 7 import lines across 6 upgrade/migration files from runtime.*
canonical paths back to specify_cli.runtime.* shim paths.

Migration modules are version-pinned and must remain importable in
environments where runtime is not on sys.path. The shim paths are always
importable via the specify_cli package.

Fixes DRIFT-2 from post-merge review of mission-095. Resolves
MigrationDiscoveryError in installed environments."

spec-kitty agent tasks mark-status T004 T005 T006 --status done --mission runtime-extraction-remediation-01KPX9DT

spec-kitty agent tasks move-task WP02 --to for_review --mission runtime-extraction-remediation-01KPX9DT --note "7 import reversions applied; migration discovery clean; upgrade tests pass"
```

---

## Definition of Done

- [ ] All 7 import lines reverted per the T004 mapping table
- [ ] `git diff` for each file shows only the import line changed (no logic changes)
- [ ] `rg "from runtime\." src/specify_cli/upgrade/` returns zero matches
- [ ] `pytest tests/upgrade/ -q` passes
- [ ] `auto_discover_migrations()` completes without `MigrationDiscoveryError`
- [ ] `git diff HEAD -- src/runtime/ src/specify_cli/next/ src/specify_cli/runtime/` is empty (C-003/C-004 scope guard)

---

## Reviewer Guidance

- Check `git diff` for each of the 6 files — only import lines should differ
- Run `rg "from runtime\." src/specify_cli/upgrade/` — must return zero lines
- Confirm `m_2_1_3` and `m_2_1_4` lazy imports were updated (they're inside functions, not at module level)
- Run `pytest tests/upgrade/ -q` and confirm passing

## Activity Log

- 2026-04-23T15:00:14Z – claude:claude-sonnet-4-6:python-pedro:implementer – shell_pid=1136669 – Started implementation via action command
- 2026-04-23T15:02:55Z – claude:claude-sonnet-4-6:python-pedro:implementer – shell_pid=1136669 – Approved (orchestrator): 7 import reversions applied; migration discovery clean; no scope creep
