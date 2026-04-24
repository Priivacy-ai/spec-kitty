---
work_package_id: WP06
title: Shim Installation + Registry
dependencies:
- WP03
- WP04
requirement_refs:
- FR-005
- FR-006
planning_base_branch: kitty/mission-runtime-mission-execution-extraction-01KPDYGW
merge_target_branch: kitty/mission-runtime-mission-execution-extraction-01KPDYGW
branch_strategy: Planning artifacts for this feature were generated on kitty/mission-runtime-mission-execution-extraction-01KPDYGW. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into kitty/mission-runtime-mission-execution-extraction-01KPDYGW unless the human explicitly redirects the landing branch.
subtasks:
- T023
- T024
- T025
- T026
agent: "claude:claude-sonnet-4-6:python-pedro:implementer"
shell_pid: "791645"
history:
- date: '2026-04-22T20:03:51Z'
  author: architect-alphonso
  event: created
agent_profile: python-pedro
authoritative_surface: src/specify_cli/next/
execution_mode: code_change
owned_files:
- src/specify_cli/next/**
- src/specify_cli/runtime/**
- architecture/2.x/shim-registry.yaml
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

Convert the 14 files in `src/specify_cli/next/` (4 files) and `src/specify_cli/runtime/` (10 files) to pure re-export deprecation shims. Register both shim packages in `architecture/2.x/shim-registry.yaml`. Validate with `spec-kitty doctor shim-registry`.

**After this WP**: every Python import that uses the old paths will still work — they will emit a `DeprecationWarning` and transparently delegate to `runtime.*`. This keeps the full test suite green during WP07–WP10.

---

## Context

**Prerequisite**: WP03 and WP04 must be done (both `in_progress` → `done`/`approved`) before starting. The canonical implementations must exist in `src/runtime/` before the shims can re-export from there.

**Shim contract** (from #615 rulebook — `architecture/2.x/06_migration_and_shim_rules.md`):

Every shim file must have these four metadata constants at module level, plus a `warnings.warn` call and a `*` re-export:

```python
__deprecated__ = True
__canonical_import__ = "runtime.<subpackage>.<module>"
__removal_release__ = "3.4.0"
__deprecation_message__ = (
    "specify_cli.next.X is deprecated. "
    "Use 'from runtime.Y import Z' instead. "
    "Legacy path removed in 3.4.0."
)

import warnings
warnings.warn(__deprecation_message__, DeprecationWarning, stacklevel=2)

from runtime.<subpackage>.<module> import *  # noqa: F401, F403
from runtime.<subpackage>.<module> import __all__  # re-export __all__ if defined
```

**Read before starting**: `architecture/2.x/06_migration_and_shim_rules.md` and `architecture/2.x/shim-registry.yaml` (currently empty — zero shims at baseline).

---

## Subtask T023 — Convert `src/specify_cli/next/` to Shims

**Purpose**: Replace the 4 module bodies in `src/specify_cli/next/` with the shim template above.

**Files to convert** (4 files):

| Original file | Canonical target |
|---|---|
| `src/specify_cli/next/__init__.py` | `runtime` (top-level) |
| `src/specify_cli/next/decision.py` | `runtime.decisioning.decision` |
| `src/specify_cli/next/prompt_builder.py` | `runtime.prompts.builder` |
| `src/specify_cli/next/runtime_bridge.py` | `runtime.bridge.runtime_bridge` |

**Steps for each file**:

1. Write the shim body following the contract template. Example for `decision.py`:
   ```python
   """DEPRECATED — specify_cli.next.decision is a compatibility shim.

   Import from runtime.decisioning.decision instead:
       from runtime.decisioning.decision import decide_next, Decision, DecisionKind
   """
   __deprecated__ = True
   __canonical_import__ = "runtime.decisioning.decision"
   __removal_release__ = "3.4.0"
   __deprecation_message__ = (
       "specify_cli.next.decision is deprecated; "
       "use 'from runtime.decisioning.decision import ...' instead. "
       "Removed in 3.4.0."
   )

   import warnings
   warnings.warn(__deprecation_message__, DeprecationWarning, stacklevel=2)

   from runtime.decisioning.decision import *  # noqa: F401, F403
   ```

2. For `__init__.py`: the canonical target is the `runtime` package itself:
   ```python
   __canonical_import__ = "runtime"
   ...
   from runtime import *  # noqa: F401, F403
   ```

3. After writing each shim, verify it still makes the original symbols available:
   ```bash
   python -W default::DeprecationWarning -c "
   import warnings
   warnings.simplefilter('always')
   from specify_cli.next.decision import decide_next
   print('shim OK')
   "
   ```
   Expected: prints "shim OK" AND shows a DeprecationWarning.

**Files touched**: `src/specify_cli/next/__init__.py`, `src/specify_cli/next/decision.py`, `src/specify_cli/next/prompt_builder.py`, `src/specify_cli/next/runtime_bridge.py`

---

## Subtask T024 — Convert `src/specify_cli/runtime/` to Shims

**Purpose**: Replace the 10 module bodies in `src/specify_cli/runtime/` with shim templates.

**Files to convert** (10 files):

| Original file | Canonical target |
|---|---|
| `src/specify_cli/runtime/__init__.py` | `runtime` |
| `src/specify_cli/runtime/agent_commands.py` | `runtime.agents.commands` |
| `src/specify_cli/runtime/agent_skills.py` | `runtime.agents.skills` |
| `src/specify_cli/runtime/bootstrap.py` | `runtime.orchestration.bootstrap` |
| `src/specify_cli/runtime/doctor.py` | `runtime.orchestration.doctor` |
| `src/specify_cli/runtime/home.py` | `runtime.discovery.home` |
| `src/specify_cli/runtime/merge.py` | `runtime.orchestration.merge` |
| `src/specify_cli/runtime/migrate.py` | `runtime.orchestration.migrate` |
| `src/specify_cli/runtime/resolver.py` | `runtime.discovery.resolver` |
| `src/specify_cli/runtime/show_origin.py` | `runtime.orchestration.show_origin` |

Follow the same shim template as T023. The `__removal_release__` is `"3.4.0"` for all.

**Spot-check one shim** (e.g., `home.py`) after writing it:
```bash
python -W default::DeprecationWarning -c "
import warnings; warnings.simplefilter('always')
from specify_cli.runtime.home import get_kittify_home
print('home shim OK')
"
```

**Files touched**: 10 files in `src/specify_cli/runtime/`

---

## Subtask T025 — Add Entries to `shim-registry.yaml`

**Purpose**: Register both shim packages in the canonical registry so `spec-kitty doctor shim-registry` can validate them.

**Steps**:

1. Read `architecture/2.x/shim-registry.yaml` to understand the existing schema (currently `shims: []`).

2. Read `architecture/2.x/06_migration_and_shim_rules.md` Section 4 for the exact YAML field names and required fields.

3. Add 2 entries under `shims:`:

   ```yaml
   shims:
     - legacy_path: "specify_cli.next"
       canonical_path: "runtime"
       grandfathered: false
       removal_release: "3.4.0"
       shim_files:
         - "src/specify_cli/next/__init__.py"
         - "src/specify_cli/next/decision.py"
         - "src/specify_cli/next/prompt_builder.py"
         - "src/specify_cli/next/runtime_bridge.py"
       introduced_in_mission: "runtime-mission-execution-extraction-01KPDYGW"

     - legacy_path: "specify_cli.runtime"
       canonical_path: "runtime"
       grandfathered: false
       removal_release: "3.4.0"
       shim_files:
         - "src/specify_cli/runtime/__init__.py"
         - "src/specify_cli/runtime/agent_commands.py"
         - "src/specify_cli/runtime/agent_skills.py"
         - "src/specify_cli/runtime/bootstrap.py"
         - "src/specify_cli/runtime/doctor.py"
         - "src/specify_cli/runtime/home.py"
         - "src/specify_cli/runtime/merge.py"
         - "src/specify_cli/runtime/migrate.py"
         - "src/specify_cli/runtime/resolver.py"
         - "src/specify_cli/runtime/show_origin.py"
       introduced_in_mission: "runtime-mission-execution-extraction-01KPDYGW"
   ```

   Adjust field names if the actual schema differs — the schema file at `kitty-specs/migration-shim-ownership-rules-01KPDYDW/contracts/shim-registry-schema.yaml` is authoritative.

**Files touched**: `architecture/2.x/shim-registry.yaml`

---

## Subtask T026 — Validate: `spec-kitty doctor shim-registry`

**Purpose**: Confirm the shim registry entries pass the CI check introduced by #615.

**Steps**:

1. Run:
   ```bash
   spec-kitty doctor shim-registry --json
   ```

2. Expected output: `{"passed": true, "issues": []}` (or equivalent success shape).

3. If any issues reported: fix the YAML entries or the shim files per the error messages. Do not mark this WP done until `passed: true`.

4. Also run the scanner test to confirm no unregistered shims exist:
   ```bash
   pytest tests/architectural/test_unregistered_shim_scanner.py -v
   ```

**Files touched**: possibly `architecture/2.x/shim-registry.yaml` or shim files (fixes only)

---

## Branch Strategy

Work in the execution worktree allocated by `spec-kitty agent action implement WP06 --agent claude`. May run in parallel with WP05.

- **Planning branch**: `kitty/mission-runtime-mission-execution-extraction-01KPDYGW`
- **Merge target**: `kitty/mission-runtime-mission-execution-extraction-01KPDYGW`

---

## Definition of Done

- [ ] All 14 shim files written with the #615 contract attributes (`__deprecated__`, `__canonical_import__`, `__removal_release__`, `__deprecation_message__`, `warnings.warn`)
- [ ] Each shim re-exports its canonical target's symbols transparently
- [ ] Spot-check: importing from the legacy paths emits `DeprecationWarning` and still returns the correct symbols
- [ ] 2 entries added to `shim-registry.yaml`
- [ ] `spec-kitty doctor shim-registry --json` → `passed: true`
- [ ] `pytest tests/architectural/test_unregistered_shim_scanner.py` passes

---

## Reviewer Guidance

- Confirm every shim file has all 4 metadata constants (`__deprecated__`, `__canonical_import__`, `__removal_release__`, `__deprecation_message__`)
- Confirm `stacklevel=2` in every `warnings.warn` call (required by #615)
- Confirm `shim-registry.yaml` has `grandfathered: false` for both entries (legacy entries use `true`; new shims must be `false`)
- Run `spec-kitty doctor shim-registry --json` and paste the output in the PR description

## Activity Log

- 2026-04-23T07:51:07Z – claude:claude-sonnet-4-6:python-pedro:implementer – shell_pid=791645 – Started implementation via action command
- 2026-04-23T08:18:21Z – claude:claude-sonnet-4-6:python-pedro:implementer – shell_pid=791645 – Approved (orchestrator): 14 shims verified, DeprecationWarning emitted, symbols accessible, shim-registry 14 entries, doctor passed:true, scanner tests pass
