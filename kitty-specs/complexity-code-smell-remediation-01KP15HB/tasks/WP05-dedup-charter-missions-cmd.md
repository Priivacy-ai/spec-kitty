---
work_package_id: WP05
title: 'Deduplicate: specify_cli Charter Shim, Missions Shim, Mission CLI Command'
dependencies: []
requirement_refs:
- FR-015
- FR-016
- FR-017
planning_base_branch: feat/complexity-debt-remediation
merge_target_branch: feat/complexity-debt-remediation
branch_strategy: Planning artifacts for this feature were generated on feat/complexity-debt-remediation. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/complexity-debt-remediation unless the human explicitly redirects the landing branch.
subtasks:
- T026
- T027
- T028
- T029
- T030
history:
- date: '2026-04-13'
  action: created
  author: spec-kitty.tasks
authoritative_surface: src/specify_cli/
execution_mode: code_change
owned_files:
- src/specify_cli/charter/__init__.py
- src/specify_cli/charter/catalog.py
- src/specify_cli/charter/compiler.py
- src/specify_cli/charter/context.py
- src/specify_cli/charter/extractor.py
- src/specify_cli/charter/generator.py
- src/specify_cli/charter/hasher.py
- src/specify_cli/charter/interview.py
- src/specify_cli/charter/parser.py
- src/specify_cli/charter/resolver.py
- src/specify_cli/charter/schemas.py
- src/specify_cli/charter/sync.py
- src/specify_cli/missions/__init__.py
- src/specify_cli/missions/primitives.py
- src/specify_cli/missions/glossary_hook.py
- src/specify_cli/cli/commands/mission.py
- src/specify_cli/next/prompt_builder.py
- src/specify_cli/runtime/doctor.py
tags: []
---

# WP05 — Deduplicate: specify_cli Charter Shim, Missions Shim, Mission CLI Command

## Objective

Eliminate three structural duplications that exist because `src/specify_cli/` contains
modules whose canonical implementations now live elsewhere:

1. **Charter**: `src/specify_cli/charter/` (2 518 lines) duplicates `src/charter/`.
   Three external callers still import from `specify_cli.charter.*` submodules.
2. **Missions**: `src/specify_cli/missions/` has an intermediate two-hop shim chain
   (`__init__.py` → `primitives.py` shim → `doctrine.missions`). The intermediate
   shim files are unnecessary.
3. **Mission CLI command**: `src/specify_cli/cli/commands/mission.py` (308 lines)
   is a near-duplicate of `mission_type.py` (305 lines), the canonical version.

**FRs**: FR-015, FR-016, FR-017
**Governing tactics**: `refactoring-strangler-fig`, `change-apply-smallest-viable-diff`
**Directives**: DIRECTIVE_024 (locality), DIRECTIVE_030 (quality gate)
**Constraints**: C-005 (charter import backward compat), C-006 (missions import backward compat)
**Note — FR-018 / T031**: The OptionInfo guard for `top_level_implement()` in `workflow.py` (FR-018)
is handled by **WP01**, which owns `workflow.py`. T031 is listed under WP01 in tasks.md.

## Branch Strategy

- **Lane**: D (independent — no dependencies on WP01–WP04)
- **Planning base / merge target**: `feat/complexity-debt-remediation`
- **Worktree**: Allocated by `finalize-tasks` — check `lanes.json` for the exact path.
- **Implementation command**: `spec-kitty agent action implement WP05 --agent <name>`

## Context

### Charter duplication

`src/specify_cli/charter/` was the original implementation before `src/charter/` became
the canonical location. The three external callers still import from the old path using
submodule imports:

```
src/specify_cli/next/prompt_builder.py
    from specify_cli.charter.context import build_charter_context
    from specify_cli.charter.resolver import GovernanceResolutionError, resolve_governance

src/specify_cli/runtime/doctor.py
    from specify_cli.charter.resolver import (...)

src/specify_cli/cli/commands/agent/workflow.py
    from specify_cli.charter.context import build_charter_context
```

Because these use submodule paths (`.charter.context`, `.charter.resolver`), a package-level
re-export shim in `__init__.py` alone is not sufficient — callers must be redirected to
`charter.context` and `charter.resolver` directly.

The `src/charter/` canonical module has all the same exports plus additional files
(`defaults.yaml`, `reference_resolver.py`, `template_resolver.py`). No behaviour changes
are expected from redirecting to the canonical module.

**IMPORTANT (C-002, pre-existing)**: This WP must not touch `src/specify_cli/charter/`
files that are scope of WP03 (extractor.py, resolver.py, compiler.py, context.py, parser.py).
WP05 only handles deletion of the deprecated `specify_cli/charter/` copies; WP03 handles
refactoring the canonical `src/charter/` implementations. These are separate concerns on
separate branches. Do not merge WP05 into the same lane as WP03.

### Missions shim chain

`src/specify_cli/missions/primitives.py` and `src/specify_cli/missions/glossary_hook.py`
are already shims:

```python
# specify_cli/missions/primitives.py
from doctrine.missions.primitives import PrimitiveExecutionContext
__all__ = ["PrimitiveExecutionContext"]

# specify_cli/missions/glossary_hook.py
from doctrine.missions.glossary_hook import execute_with_glossary
__all__ = ["execute_with_glossary"]
```

The `__init__.py` then imports from these shims. This two-hop chain is unnecessary.
Five test files import from `specify_cli.missions` — they must continue to work after
the intermediate shim files are deleted (C-006 preserves this).

### Mission CLI duplication

`mission.py` and `mission_type.py` differ only in: the `app` name (`"mission"` vs
`"mission-type"`), one help string, one CLI flag alias, and minor copy tweaks. The
canonical version is `mission_type.py`. The CLI router registers both:

```python
app.add_typer(mission_module.app, name="mission")
app.add_typer(mission_type_module.app, name="mission-type")
```

Making `mission.py` a shim eliminates the duplication while preserving the `mission`
command registration path.

---

## Pre-work: Verify baseline

Before making any changes, verify the affected tests pass on the current code:

```bash
pytest tests/agent/glossary/ -x -q        # missions shim callers
pytest tests/specify_cli/cli/ -x -q       # mission CLI commands
pytest tests/ -k "charter or doctor or workflow or prompt_builder" -x -q
```

Record the baseline result. Every change in this WP must maintain a green baseline.

---

## Subtask T026 — Redirect 2 external callers from `specify_cli.charter.*` to `charter.*`

**Purpose**: Remove the 3 import lines that hold the `specify_cli.charter.*` submodule
path alive in production code (FR-015).

**Note**: `src/specify_cli/cli/commands/agent/workflow.py` also imports from
`specify_cli.charter.context`, but that file is owned by **WP01** (it contains
`emit_status_transition` call sites). WP01's T031 redirects the charter import in
`workflow.py` as part of the OptionInfo guard work. Do not touch `workflow.py` here.

**Files** (2 files, 3 import lines total):

`src/specify_cli/next/prompt_builder.py`:
```python
# Before
from specify_cli.charter.context import build_charter_context
from specify_cli.charter.resolver import GovernanceResolutionError, resolve_governance

# After
from charter.context import build_charter_context
from charter.resolver import GovernanceResolutionError, resolve_governance
```

`src/specify_cli/runtime/doctor.py`:
```python
# Before
from specify_cli.charter.resolver import (...)

# After
from charter.resolver import (...)
```

**After each file**:
```bash
mypy src/specify_cli/next/prompt_builder.py     # or whichever file was changed
pytest tests/ -k "prompt_builder or doctor" -x -q
```

**Validation**: `ruff check src/specify_cli/next/ src/specify_cli/runtime/` — zero violations.

---

## Subtask T027 — Convert `specify_cli/charter/` to a re-export shim; delete internals

**Purpose**: Collapse `specify_cli/charter/` to a single `__init__.py` re-export shim
(C-005); delete all internal implementation files (FR-015).

**Step 1 — Replace `__init__.py`**:

```python
"""Backward-compatibility shim for specify_cli.charter.

The canonical charter implementation is in src/charter/.
This package re-exports the full public surface so that
``from specify_cli.charter import X`` continues to work.
"""
from charter import (  # noqa: F401
    DoctrineCatalog,
    load_doctrine_catalog,
    CompiledCharter,
    CharterReference,
    WriteBundleResult,
    compile_charter,
    write_compiled_charter,
    CharterContextResult,
    build_charter_context,
    CharterDraft,
    build_charter_draft,
    write_charter,
    CharterInterview,
    QUESTION_ORDER,
    MINIMAL_QUESTION_ORDER,
    QUESTION_PROMPTS,
    default_interview,
    read_interview_answers,
    write_interview_answers,
    apply_answer_overrides,
    CharterParser,
    CharterSection,
    BranchStrategyConfig,
    CommitConfig,
    DoctrineSelectionConfig,
    Directive,
    DirectivesConfig,
    ExtractionMetadata,
    GovernanceConfig,
    PerformanceConfig,
    QualityConfig,
    SectionsParsed,
    CharterTestingConfig,
    emit_yaml,
    SyncResult,
    load_directives_config,
    load_governance_config,
    post_save_hook,
    sync,
    GovernanceResolution,
    GovernanceResolutionError,
    collect_governance_diagnostics,
    resolve_governance,
)

__all__ = [
    "DoctrineCatalog", "load_doctrine_catalog",
    "CompiledCharter", "CharterReference", "WriteBundleResult",
    "compile_charter", "write_compiled_charter",
    "CharterContextResult", "build_charter_context",
    "CharterDraft", "build_charter_draft", "write_charter",
    "CharterInterview", "QUESTION_ORDER", "MINIMAL_QUESTION_ORDER",
    "QUESTION_PROMPTS", "default_interview", "read_interview_answers",
    "write_interview_answers", "apply_answer_overrides",
    "CharterParser", "CharterSection",
    "BranchStrategyConfig", "CommitConfig", "DoctrineSelectionConfig",
    "Directive", "DirectivesConfig", "ExtractionMetadata",
    "GovernanceConfig", "PerformanceConfig", "QualityConfig",
    "SectionsParsed", "CharterTestingConfig", "emit_yaml",
    "SyncResult", "load_directives_config", "load_governance_config",
    "post_save_hook", "sync",
    "GovernanceResolution", "GovernanceResolutionError",
    "collect_governance_diagnostics", "resolve_governance",
]
```

**Step 2 — Delete internal files** (after verifying `__init__.py` imports cleanly):

Delete these files from `src/specify_cli/charter/`:
- `catalog.py`
- `compiler.py`
- `context.py`
- `extractor.py`
- `generator.py`
- `hasher.py`
- `interview.py`
- `parser.py`
- `resolver.py`
- `schemas.py`
- `sync.py`

**Do NOT delete `__init__.py`** (required by C-005).

**After deletion**:
```bash
python -c "from specify_cli.charter import GovernanceConfig, resolve_governance"
mypy src/specify_cli/charter/
pytest tests/ -k "charter" -x -q
```

**Validation**: `grep -r "specify_cli.charter\." src/ tests/ --include="*.py"` — zero results
(no remaining submodule imports outside the shim itself).

---

## Subtask T028 — Flatten `specify_cli/missions/` shim chain

**Purpose**: Remove the two-hop shim indirection; make `__init__.py` import directly
from `doctrine.missions` (FR-016).

**Step 1 — Update `src/specify_cli/missions/__init__.py`**:

```python
"""Backward-compatibility shim for specify_cli.missions.

The canonical implementation is in doctrine.missions.
This package re-exports the public surface so that existing
callers continue to work without modification (C-006).
"""
from doctrine.missions import PrimitiveExecutionContext, execute_with_glossary

__all__ = [
    "PrimitiveExecutionContext",
    "execute_with_glossary",
]
```

**Step 2 — Delete intermediate shim files**:
- `src/specify_cli/missions/primitives.py`
- `src/specify_cli/missions/glossary_hook.py`

**After deletion**:
```bash
python -c "from specify_cli.missions import PrimitiveExecutionContext, execute_with_glossary"
pytest tests/agent/glossary/ -x -q     # 5 files import from specify_cli.missions
```

**Validation**: All 5 glossary test files pass. `from specify_cli.missions import ...` works.

---

## Subtask T029 — Make `mission.py` a thin shim

**Purpose**: Eliminate the duplicate command logic in `mission.py` (FR-017).

**File**: `src/specify_cli/cli/commands/mission.py`

**Replace the entire file body** with:

```python
"""Backward-compatibility shim for the ``mission`` CLI subcommand.

The canonical implementation is in ``mission_type.py``. This module
re-exports ``app`` so that the CLI router's ``add_typer(mission_module.app,
name="mission")`` registration continues to work.
"""
from .mission_type import app

__all__ = ["app"]
```

The CLI `commands/__init__.py` registration is unchanged — it still registers both
`mission_module.app` (under `"mission"`) and `mission_type_module.app` (under
`"mission-type"`). After this change, both registrations point to the same underlying
`app` object.

**Validation**:
```bash
spec-kitty mission --help        # must show mission-type help
spec-kitty mission-type --help   # must show same help
pytest tests/ -k "mission" -x -q
```

---

## Subtask T030 — Quality gate

```bash
ruff check src/specify_cli/charter/ src/specify_cli/missions/ src/specify_cli/cli/commands/mission.py
mypy src/specify_cli/charter/ src/specify_cli/missions/ src/specify_cli/next/prompt_builder.py src/specify_cli/runtime/doctor.py
pytest tests/ -x --timeout=120
```

**Expected outcomes**:
- ruff: zero violations in all modified files
- mypy: zero errors
- pytest: no new failures
- `grep -r "specify_cli.charter\." src/ tests/ --include="*.py"` → zero submodule imports (note: `workflow.py` redirect handled by WP01)
- `ls src/specify_cli/charter/` → only `__init__.py` (and `__pycache__/`)
- `ls src/specify_cli/missions/*.py` → only `__init__.py`
- `wc -l src/specify_cli/cli/commands/mission.py` → ≤ 10 lines

---

## Definition of Done

- [ ] `src/specify_cli/next/prompt_builder.py` imports from `charter.*` (not `specify_cli.charter.*`)
- [ ] `src/specify_cli/runtime/doctor.py` imports from `charter.*`
- [ ] `src/specify_cli/charter/__init__.py` is a pure re-export shim from `charter.*`
- [ ] All other `.py` files in `src/specify_cli/charter/` are deleted
- [ ] `src/specify_cli/missions/__init__.py` imports directly from `doctrine.missions`
- [ ] `src/specify_cli/missions/primitives.py` and `glossary_hook.py` are deleted
- [ ] `src/specify_cli/cli/commands/mission.py` is ≤ 10 lines and re-exports `app` from `mission_type`
- [ ] `from specify_cli.charter import GovernanceConfig` works (C-005)
- [ ] `from specify_cli.missions import PrimitiveExecutionContext` works (C-006)
- [ ] `ruff check` — zero violations on all modified files
- [ ] `mypy` — zero errors
- [ ] `pytest tests/` — no new failures

## Reviewer Guidance

1. Run `grep -r "specify_cli.charter\." src/ tests/ --include="*.py"` — must return zero results.
2. Run `ls src/specify_cli/charter/` — must show only `__init__.py`.
3. Run `ls src/specify_cli/missions/*.py` — must show only `__init__.py`.
4. Run `python -c "from specify_cli.charter import GovernanceConfig, resolve_governance; print('ok')"` — must print `ok`.
5. Run `python -c "from specify_cli.missions import PrimitiveExecutionContext; print('ok')"` — must print `ok`.
6. Confirm `mission.py` is ≤ 10 lines and contains only the shim.
