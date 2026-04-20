---
work_package_id: WP01
title: Package Bootstrap and Dependency Hygiene
dependencies: []
requirement_refs:
- FR-010
- C-005
planning_base_branch: kitty/mission-migration-shim-ownership-rules-01KPDYDW
merge_target_branch: kitty/mission-migration-shim-ownership-rules-01KPDYDW
branch_strategy: Planning artifacts for this feature were generated on kitty/mission-migration-shim-ownership-rules-01KPDYDW. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into kitty/mission-migration-shim-ownership-rules-01KPDYDW unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-migration-shim-ownership-rules-01KPDYDW
base_commit: 0a5c5d1eed4d096c227a79bc7e879a90e6a54f40
created_at: '2026-04-19T12:59:36.875691+00:00'
subtasks:
- T001
- T002
shell_pid: "1343633"
agent: "claude"
history:
- date: '2026-04-19'
  event: created
agent_profile: python-implementer
authoritative_surface: pyproject.toml
execution_mode: code_change
mission_id: 01KPDYDWVF8W838HNJK7FC3S7T
mission_slug: migration-shim-ownership-rules-01KPDYDW
owned_files:
- pyproject.toml
tags: []
---

# WP01 — Package Bootstrap and Dependency Hygiene

## Objective

Establish the `src/specify_cli/compat/` package that will house all compatibility-shim infrastructure, confirm there are zero existing unregistered shims at mission start, and lock the `packaging` library as an explicit project dependency.

## Context

The plan introduces a new `src/specify_cli/compat/` package to hold registry loading, validation, and the doctor-check engine. A key discovery: `src/specify_cli/shims/` already exists but is the **agent-skill shims** domain (consumer/internal skill routing) — it is completely unrelated to Python compatibility shims. Do not touch it.

The `packaging` library is used for semver comparison (R1 decision in `research.md`). It is currently a transitive dependency; this WP makes it explicit to prevent breakage if the transitive path changes.

## Branch Strategy

- **Planning branch / working branch**: `kitty/mission-migration-shim-ownership-rules-01KPDYDW`
- **Merge target**: `main` (via `spec-kitty merge` at mission close)
- Execution worktree is resolved by `spec-kitty agent action implement WP01 --agent <name>`

---

## Subtask T001 — Audit Existing Shims (Zero-Baseline)

**Purpose**: Confirm that no module under `src/specify_cli/` currently carries `__deprecated__ = True`, establishing the clean baseline that allows the registry to start empty.

**Steps**:
1. Run:
   ```bash
   grep -r "__deprecated__" src/specify_cli/ --include="*.py" -l
   ```
2. Expected result: no output (zero matches).
3. If any matches are found: stop and report them to the user — do NOT proceed until they are reconciled.
4. Document the result as a comment inside `src/specify_cli/compat/__init__.py` (created in T003):
   ```python
   # Baseline audit (2026-04-19): zero modules under src/specify_cli/ carry
   # __deprecated__ = True at mission start. Registry begins empty.
   ```

**Files**:
- Read-only audit; result documented in `src/specify_cli/compat/__init__.py` (T003)

**Validation**:
- [ ] `grep -r "__deprecated__" src/specify_cli/ --include="*.py" -l` returns zero lines
- [ ] If non-zero, implementation is halted and findings are reported

---

## Subtask T002 — Lock `packaging` as Explicit Dependency

**Purpose**: Make `packaging` an explicit `[project.dependencies]` entry in `pyproject.toml` so the semver comparator in `compat/doctor.py` has a guaranteed, version-pinned import rather than relying on a transitive path.

**Steps**:
1. Read `pyproject.toml` and search `[project.dependencies]` for any entry matching `^packaging`.
2. If absent: add `"packaging>=23.0"` to the list (alphabetical order is preferred but not mandatory).
3. Run `uv sync` to confirm the dependency resolves without conflict.
4. Run `python -c "import packaging.version; print(packaging.version.Version('3.2.0'))"` to verify the import works.

**Files**:
- `pyproject.toml` — add one dependency line if absent

**Validation**:
- [ ] `grep "packaging" pyproject.toml` shows an entry under `[project.dependencies]`
- [ ] `uv sync` exits 0
- [ ] `python -c "import packaging.version"` exits 0

---

## Subtask T003 — Create `src/specify_cli/compat/` Package

**Purpose**: Scaffold the new `compat` package with a properly documented `__init__.py`. The package will be populated by WP02.

**Steps**:
1. Create `src/specify_cli/compat/__init__.py` with:
   ```python
   """Compatibility-shim infrastructure for spec-kitty.

   This package owns:
   - Loading and validating architecture/2.x/shim-registry.yaml
   - Classifying each registered shim (pending/overdue/grandfathered/removed)
   - The engine behind `spec-kitty doctor shim-registry`

   Public API (populated by registry.py and doctor.py):
       check_shim_registry, ShimRegistryReport, RegistrySchemaError

   NOTE: src/specify_cli/shims/ is a DIFFERENT domain (agent-skill shims).
   Do not confuse the two packages.

   # Baseline audit (2026-04-19): zero modules under src/specify_cli/ carry
   # __deprecated__ = True at mission start. Registry begins empty.
   """
   from __future__ import annotations

   # Populated after WP02 lands:
   # from specify_cli.compat.registry import RegistrySchemaError
   # from specify_cli.compat.doctor import ShimRegistryReport, check_shim_registry
   # __all__ = ["check_shim_registry", "ShimRegistryReport", "RegistrySchemaError"]
   ```

2. Confirm the package is importable:
   ```bash
   python -c "import specify_cli.compat; print('ok')"
   ```

**Files**:
- `src/specify_cli/compat/__init__.py` (new)

**Validation**:
- [ ] `src/specify_cli/compat/__init__.py` exists
- [ ] `python -c "import specify_cli.compat"` exits 0
- [ ] mypy --strict passes on the new file

---

## Definition of Done

- [ ] Zero shims found by audit (or findings reported and blocked)
- [ ] `packaging>=23.0` is an explicit dep in `pyproject.toml`
- [ ] `src/specify_cli/compat/__init__.py` created and importable
- [ ] `mypy --strict src/specify_cli/compat/` passes
- [ ] `pytest tests/` exits 0 (no regressions from the pyproject.toml edit)

## Risks

- If `uv sync` fails after adding `packaging`: check for version conflicts with other deps. The `packaging` library is extremely stable; conflicts are unlikely but possible with pinned transitive versions.
- If `src/specify_cli/compat/` name conflicts with an installed package: verify with `python -c "import compat"` in a clean environment — unlikely since `compat` is not a well-known top-level package name.

## Activity Log

- 2026-04-19T12:59:37Z – claude – shell_pid=1334330 – Assigned agent via action command
- 2026-04-19T13:14:46Z – claude – shell_pid=1334330 – T001: zero deprecated shims confirmed. T002: packaging>=23.0 already present. T003 moved to WP02 scope.
- 2026-04-19T13:24:15Z – claude – shell_pid=1343633 – Started review via action command
- 2026-04-19T13:24:58Z – claude – shell_pid=1343633 – Review passed: T001 zero __deprecated__ assignments confirmed, T002 packaging>=23.0 at pyproject.toml:62. No file changes; both subtasks pre-satisfied.
