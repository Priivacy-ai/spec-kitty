---
work_package_id: WP03
title: Migrate 4 residual source callers to canonical paths
dependencies:
- WP01
requirement_refs:
- FR-005
- FR-006
planning_base_branch: kitty/mission-runtime-mission-execution-extraction-01KPDYGW
merge_target_branch: kitty/mission-runtime-mission-execution-extraction-01KPDYGW
branch_strategy: Planning artifacts for this feature were generated on kitty/mission-runtime-mission-execution-extraction-01KPDYGW. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into kitty/mission-runtime-mission-execution-extraction-01KPDYGW unless the human explicitly redirects the landing branch.
subtasks:
- T007
- T008
- T009
agent: "claude:claude-sonnet-4-6:python-pedro:implementer"
shell_pid: "1313880"
history:
- date: '2026-04-23T13:58:27Z'
  author: reviewer-renata
  event: created
agent_profile: python-pedro
authoritative_surface: src/specify_cli/
execution_mode: code_change
lane: planned
owned_files:
- src/specify_cli/cli/commands/agent/status.py
- src/specify_cli/migration/rewrite_shims.py
- src/specify_cli/mission.py
- src/specify_cli/state/doctor.py
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

Migrate 5 import lines across 4 source files from `specify_cli.runtime.*` shim paths to `runtime.*` canonical paths. These files were missed by mission #95's WP09 (they were not in the occurrence map). They currently emit `DeprecationWarning` on every invocation and will break silently at 3.4.0 shim removal.

**Why depends on WP01**: These files will use `runtime.*` canonical paths after migration. Those paths are only importable once `src/runtime` is registered in `pyproject.toml` (WP01). Confirm WP01 is in `approved` or `done` lane before starting.

**Three of the 5 imports are lazy** (inside function bodies, not at module level). Read each file before editing.

---

## Context

**Run this before starting**:
```bash
spec-kitty agent tasks status --mission runtime-extraction-remediation-01KPX9DT
```
Confirm WP01 is in `approved` or `done` lane.

---

## Subtask T007 — Apply the 5 import migrations

**Purpose**: Replace each `specify_cli.runtime.*` import with its `runtime.*` canonical equivalent.

**Complete mapping** (apply all 5 changes):

| File | Remove this line | Replace with this line | Import type |
|---|---|---|---|
| `cli/commands/agent/status.py` | `from specify_cli.runtime.doctor import run_global_checks` | `from runtime.orchestration.doctor import run_global_checks` | lazy (in function body) |
| `migration/rewrite_shims.py` | `from specify_cli.runtime.home import get_kittify_home, get_package_asset_root` | `from runtime.discovery.home import get_kittify_home, get_package_asset_root` | lazy (in function body) |
| `state/doctor.py` | `from specify_cli.runtime.home import get_kittify_home` | `from runtime.discovery.home import get_kittify_home` | **two occurrences**: one module-level, one lazy |
| `mission.py` | `from specify_cli.runtime.resolver import resolve_command` | `from runtime.discovery.resolver import resolve_command` | lazy (in function body) |

**Steps**:

1. **`src/specify_cli/cli/commands/agent/status.py`** — Lazy import:
   - Read the file and find the function that imports `run_global_checks`
   - Replace `from specify_cli.runtime.doctor import run_global_checks` with `from runtime.orchestration.doctor import run_global_checks`
   - Verify: `git diff src/specify_cli/cli/commands/agent/status.py` shows only this import line

2. **`src/specify_cli/migration/rewrite_shims.py`** — Lazy import:
   - Read the file and find the function that imports from `specify_cli.runtime.home`
   - Replace the import with `from runtime.discovery.home import get_kittify_home, get_package_asset_root`
   - Verify: only the import line changed

3. **`src/specify_cli/state/doctor.py`** — Two occurrences (module-level + lazy):
   - Read the full file — there are **two** `from specify_cli.runtime.home import get_kittify_home` lines
   - Replace both with `from runtime.discovery.home import get_kittify_home`
   - Verify: `git diff src/specify_cli/state/doctor.py` shows both lines replaced

4. **`src/specify_cli/mission.py`** — Lazy import:
   - Read the file and find the function body containing `from specify_cli.runtime.resolver import resolve_command`
   - Replace with `from runtime.discovery.resolver import resolve_command`
   - Verify: only the import line changed

**Files touched**: 4 files listed above.

**Validation**: `git diff` for each file shows only the import line(s) changed.

---

## Subtask T008 — Verify no residual shim-path callers outside shim directories

**Purpose**: Confirm the occurrence map is now complete — no `src/` files outside the intentional shim directories import from `specify_cli.next.*` or `specify_cli.runtime.*`.

**Steps**:

1. Run the scan:
   ```bash
   rg "from specify_cli\.(next|runtime)" src/ -l 2>/dev/null
   ```

2. Inspect the results:
   - **Acceptable** (intentional shims): `src/specify_cli/next/` and `src/specify_cli/runtime/` directories
   - **Not acceptable**: Any other file in `src/`

3. If any unexpected files appear, check whether they are:
   - Missed by this WP (add them to the T007 mapping and fix)
   - Intentional exceptions (document in occurrence_map.yaml with rationale)

**Validation**: `rg` output contains only files under `src/specify_cli/next/` and `src/specify_cli/runtime/`.

---

## Subtask T009 — Full test suite + CLI smoke test

**Purpose**: Confirm the migrations introduce no regressions and the CLI remains functional.

**Steps**:

1. Run the full test suite:
   ```bash
   pytest tests/ --ignore=tests/auth -q --tb=short 2>&1 | tail -10
   ```
   Expected: zero new failures. Count ≥ pre-WP03 baseline.

2. Run the CLI smoke test:
   ```bash
   spec-kitty next --help
   spec-kitty agent action implement --help
   spec-kitty --version
   ```
   All three must exit 0 and print expected output.

3. Verify no more `DeprecationWarning` from the 4 migrated files:
   ```bash
   python -W error::DeprecationWarning -c "
   import sys; sys.path.insert(0,'src')
   import specify_cli.cli.commands.agent.status
   import specify_cli.migration.rewrite_shims
   import specify_cli.state.doctor
   import specify_cli.mission
   print('No DeprecationWarnings from migrated files')
   " 2>&1
   ```
   Expected: prints `No DeprecationWarnings from migrated files`.

**Validation**: Full suite passes. CLI smoke tests pass. No `DeprecationWarning` from the 4 migrated files.

---

## Branch Strategy

Work in the execution worktree allocated by `spec-kitty agent action implement WP03 --agent claude`. **Must run after WP01 is approved**.

- **Planning branch**: `kitty/mission-runtime-mission-execution-extraction-01KPDYGW`
- **Merge target**: `kitty/mission-runtime-mission-execution-extraction-01KPDYGW`

---

## After Implementation

```bash
git add src/specify_cli/cli/commands/agent/status.py \
  src/specify_cli/migration/rewrite_shims.py \
  src/specify_cli/state/doctor.py \
  src/specify_cli/mission.py

git commit -m "fix(RISK-2): migrate 4 residual source callers to runtime.* canonical paths

Migrates 5 import lines across 4 files that were missed by mission-095 WP09:
- cli/commands/agent/status.py: specify_cli.runtime.doctor → runtime.orchestration.doctor
- migration/rewrite_shims.py: specify_cli.runtime.home → runtime.discovery.home
- state/doctor.py (×2): specify_cli.runtime.home → runtime.discovery.home
- mission.py: specify_cli.runtime.resolver → runtime.discovery.resolver

Eliminates DeprecationWarning from these callers. Closes the occurrence-map
gap from mission-095. These callers will no longer break at 3.4.0 shim removal."

spec-kitty agent tasks mark-status T007 T008 T009 --status done --mission runtime-extraction-remediation-01KPX9DT

spec-kitty agent tasks move-task WP03 --to for_review --mission runtime-extraction-remediation-01KPX9DT --note "5 imports migrated; rg scan clean; full suite passes; no DeprecationWarning from migrated files"
```

---

## Definition of Done

- [ ] All 5 import lines migrated per the T007 mapping table
- [ ] `state/doctor.py` has **both** occurrences replaced (module-level + lazy)
- [ ] `git diff` for each file shows only the import line(s) changed
- [ ] `rg "from specify_cli\.(next|runtime)" src/ -l` returns only files under `src/specify_cli/next/` and `src/specify_cli/runtime/`
- [ ] Full test suite passes with zero new failures
- [ ] `spec-kitty next --help` and `spec-kitty --version` exit 0
- [ ] No `DeprecationWarning` emitted by the 4 migrated files
- [ ] `git diff HEAD -- src/runtime/ src/specify_cli/next/ src/specify_cli/runtime/` is empty (C-003/C-004 scope guard)

---

## Reviewer Guidance

- Check `git diff` for each file — only import lines should differ
- For `state/doctor.py`: verify **two** lines were updated (the file has both a module-level and a lazy import)
- Run `rg "from specify_cli\.(next|runtime)" src/ -l` — must return only shim directories
- Run the DeprecationWarning verification command from T009 step 3

## Activity Log

- 2026-04-24T03:53:17Z – claude:claude-sonnet-4-6:python-pedro:implementer – shell_pid=1313880 – Started implementation via action command
- 2026-04-24T03:57:15Z – claude:claude-sonnet-4-6:python-pedro:implementer – shell_pid=1313880 – Approved (orchestrator): 7 files migrated (4 planned + 3 discovered); rg scan clean; CLI smoke pass; scope guard clean
