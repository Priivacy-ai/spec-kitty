---
work_package_id: WP09
title: Source File Occurrence Migration
dependencies:
- WP06
requirement_refs:
- FR-015
planning_base_branch: kitty/mission-runtime-mission-execution-extraction-01KPDYGW
merge_target_branch: kitty/mission-runtime-mission-execution-extraction-01KPDYGW
branch_strategy: Planning artifacts for this feature were generated on kitty/mission-runtime-mission-execution-extraction-01KPDYGW. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into kitty/mission-runtime-mission-execution-extraction-01KPDYGW unless the human explicitly redirects the landing branch.
subtasks:
- T033
- T034
- T035
- T036
agent: "claude:claude-sonnet-4-6:python-pedro:implementer"
shell_pid: "930883"
history:
- date: '2026-04-22T20:03:51Z'
  author: architect-alphonso
  event: created
agent_profile: python-pedro
authoritative_surface: src/doctrine/
execution_mode: code_change
owned_files:
- src/doctrine/resolver.py
- src/kernel/__init__.py
- src/specify_cli/__init__.py
- src/specify_cli/mission.py
- src/specify_cli/core/project_resolver.py
- src/specify_cli/state/doctor.py
- src/specify_cli/migration/rewrite_shims.py
- src/specify_cli/upgrade/compat.py
- src/specify_cli/upgrade/migrations/m_2_0_6_consistency_sweep.py
- src/specify_cli/upgrade/migrations/m_2_0_7_fix_stale_overrides.py
- src/specify_cli/upgrade/migrations/m_2_1_3_restore_prompt_commands.py
- src/specify_cli/upgrade/migrations/m_2_1_4_enforce_command_file_state.py
- src/specify_cli/upgrade/migrations/m_3_1_2_globalize_commands.py
- src/specify_cli/cli/commands/agent/status.py
- src/specify_cli/cli/commands/config_cmd.py
- src/specify_cli/cli/commands/doctor.py
- src/specify_cli/cli/commands/init.py
- src/specify_cli/cli/commands/migrate_cmd.py
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

Apply the `occurrence_map.yaml` rewrites to all non-CLI, non-test source files that import from `specify_cli.next.*` or `specify_cli.runtime.*`. Shims keep these working during the deprecation window, but the canonical imports are cleaner and eliminate the `DeprecationWarning` noise.

---

## Context

**Authority**: `kitty-specs/runtime-mission-execution-extraction-01KPDYGW/occurrence_map.yaml` (generated in WP01) — use it as the authoritative list. The files listed in this WP's `owned_files` are a pre-scan estimate. The actual set is the `source_caller` category in occurrence_map.yaml.

**Prerequisite**: WP06 shims are in place. Any import from the old paths still works (via shim). You are migrating callers to the canonical paths for cleanliness, not for correctness.

**Special caution — upgrade migrations**: Migration files under `src/specify_cli/upgrade/migrations/` often import from `specify_cli.runtime.home` or `specify_cli.runtime.resolver` for asset path resolution. These imports must be verified semantically — confirm the new `runtime.discovery.home` / `runtime.discovery.resolver` exports the exact same function signature before rewriting. If there is any doubt, leave the migration module using the shim path and document the exception in occurrence_map.yaml.

---

## Subtask T033 — Rewrite Cross-Package Source Callers

**Purpose**: Update files in `src/doctrine/` and `src/kernel/` — these are top-level packages that should import from `runtime.*` directly, not through `specify_cli.*`.

**Steps**:

1. Read `occurrence_map.yaml` → `source_caller` category. Find the entries for `src/doctrine/resolver.py` and `src/kernel/__init__.py`.

2. For each import listed in the occurrence map, apply the rewrite:
   ```python
   # Before:
   from specify_cli.runtime.home import get_kittify_home

   # After:
   from runtime.discovery.home import get_kittify_home
   ```

3. For `src/doctrine/resolver.py` — this is in the `doctrine` package which has architectural boundary rules. Confirm that `doctrine` importing from `runtime` is allowed (it should be: `runtime.may_be_called_by: cli_shell` means runtime can be called by doctrine as well? Actually no — `may_be_called_by: [cli_shell]` means ONLY cli_shell may import runtime. If `doctrine` is importing runtime, that is a boundary violation).

   **If doctrine imports from runtime**: this is a dependency-rules violation. Do NOT rewrite the import. Instead, add a note in the occurrence_map.yaml that this caller violates FR-007 and must be refactored separately (different mission). Leave the shim import in place.

4. Verify with ruff and mypy after each file rewrite:
   ```bash
   ruff check src/doctrine/resolver.py
   mypy --strict src/doctrine/resolver.py --ignore-missing-imports
   ```

**Files touched**: Per occurrence_map.yaml `source_caller` entries for `src/doctrine/` and `src/kernel/`

---

## Subtask T034 — Rewrite Remaining `specify_cli` Source Callers

**Purpose**: Update `specify_cli.*` non-CLI files that import from `specify_cli.next.*` or `specify_cli.runtime.*`.

**Known callers** (verify against occurrence_map.yaml):
- `src/specify_cli/__init__.py`
- `src/specify_cli/mission.py`
- `src/specify_cli/core/project_resolver.py`
- `src/specify_cli/state/doctor.py`
- `src/specify_cli/migration/rewrite_shims.py`
- `src/specify_cli/cli/commands/agent/status.py`
- `src/specify_cli/cli/commands/config_cmd.py`
- `src/specify_cli/cli/commands/doctor.py`
- `src/specify_cli/cli/commands/init.py`
- `src/specify_cli/cli/commands/migrate_cmd.py`

**Steps**:

1. For each file in the occurrence map's `source_caller` list, apply the import rewrites listed in the map.

2. For CLI command files not covered in WP05 (e.g., `config_cmd.py`, `doctor.py`, `init.py`, `migrate_cmd.py`): these are additional CLI entry points. Apply the same thin-adapter check as WP05 — confirm they only use runtime for service calls, not decisioning.

3. After all rewrites:
   ```bash
   ruff check src/specify_cli/__init__.py src/specify_cli/mission.py \
     src/specify_cli/core/ src/specify_cli/state/ src/specify_cli/migration/ \
     src/specify_cli/cli/commands/
   ```

**Files touched**: Per occurrence_map.yaml

---

## Subtask T035 — Rewrite Upgrade Migration Modules

**Purpose**: Update upgrade migrations that import from `specify_cli.runtime.*`. Exercise extra caution: migrations are version-pinned and may run on arbitrary old project states.

**Known callers**:
- `src/specify_cli/upgrade/compat.py`
- `src/specify_cli/upgrade/migrations/m_2_0_6_consistency_sweep.py`
- `src/specify_cli/upgrade/migrations/m_2_0_7_fix_stale_overrides.py`
- `src/specify_cli/upgrade/migrations/m_2_1_3_restore_prompt_commands.py`
- `src/specify_cli/upgrade/migrations/m_2_1_4_enforce_command_file_state.py`
- `src/specify_cli/upgrade/migrations/m_3_1_2_globalize_commands.py`

**Steps**:

1. For each migration file: read the import and understand WHY it imports from `specify_cli.runtime.*`. Common use:
   - `from specify_cli.runtime.home import get_kittify_home` — used to find the global runtime home directory
   - `from specify_cli.runtime.resolver import resolve_template` — used to find template paths during migration

2. Verify the `runtime.discovery.*` equivalents have the same function signatures as the old `specify_cli.runtime.*` originals. If signatures differ (even slightly), do not rewrite — leave the shim import and document.

3. If signature is identical: apply the rewrite.

4. After rewrites, run the migration integration test (if one exists):
   ```bash
   pytest tests/upgrade/ -v --tb=short
   ```

**Files touched**: Per occurrence_map.yaml `source_caller` entries for `src/specify_cli/upgrade/`

---

## Subtask T036 — Validate: ruff + mypy + partial test run

**Purpose**: Confirm all WP09 rewrites are syntactically correct and type-clean.

**Steps**:

1. Run ruff on all modified files:
   ```bash
   ruff check src/doctrine/ src/kernel/ src/specify_cli/__init__.py \
     src/specify_cli/mission.py src/specify_cli/core/ src/specify_cli/state/ \
     src/specify_cli/migration/ src/specify_cli/upgrade/ src/specify_cli/cli/commands/
   ```

2. Run mypy:
   ```bash
   mypy --ignore-missing-imports src/doctrine/ src/kernel/ \
     src/specify_cli/mission.py src/specify_cli/core/
   ```

3. Run a targeted pytest subset covering the modified areas:
   ```bash
   pytest tests/upgrade/ tests/init/ tests/kernel/ tests/agent/ -v --tb=short
   ```

4. Record any files left on shim paths (exceptions) in occurrence_map.yaml under an `exceptions` key with rationale.

**Validation**: ruff and mypy exit clean; targeted pytest subset exits 0.

---

## Branch Strategy

Work in the execution worktree allocated by `spec-kitty agent action implement WP09 --agent claude`. May run in parallel with WP07 and WP08.

- **Planning branch**: `kitty/mission-runtime-mission-execution-extraction-01KPDYGW`
- **Merge target**: `kitty/mission-runtime-mission-execution-extraction-01KPDYGW`

---

## Definition of Done

- [ ] All `source_caller` entries in occurrence_map.yaml either: (a) rewritten to `runtime.*` import, or (b) documented as an exception with rationale
- [ ] `ruff check` exits clean on all modified files
- [ ] `mypy` exits clean on modified source packages
- [ ] `pytest tests/upgrade/ tests/init/ tests/kernel/` exits 0
- [ ] Any boundary violations (e.g., doctrine importing runtime) documented in occurrence_map.yaml as exceptions

---

## Reviewer Guidance

- For each migration file rewrite: verify old and new function signatures are identical (not just names — also parameter lists and return types)
- Check `occurrence_map.yaml` exceptions section: anything left as an exception must have a rationale
- Confirm `src/doctrine/resolver.py` was either rewritten (if allowed by boundary rules) or kept on shim path (if it would violate FR-007)

## Activity Log

- 2026-04-23T11:56:03Z – claude:claude-sonnet-4-6:python-pedro:implementer – shell_pid=930883 – Started implementation via action command
- 2026-04-23T12:12:47Z – claude:claude-sonnet-4-6:python-pedro:implementer – shell_pid=930883 – Approved: 11 source files migrated to runtime.*; 461 upgrade+agent tests pass; exceptions documented; ruff clean on modified files
