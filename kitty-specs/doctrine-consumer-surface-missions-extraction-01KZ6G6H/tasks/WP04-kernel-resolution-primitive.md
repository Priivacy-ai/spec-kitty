---
work_package_id: WP04
title: Kernel-owned resolution primitive + three-way convergence
dependencies: []
requirement_refs:
- FR-004
- NFR-002
planning_base_branch: research/doctrine-wheel-mission-types-public-api
merge_target_branch: research/doctrine-wheel-mission-types-public-api
branch_strategy: Planning artifacts for this mission were generated on research/doctrine-wheel-mission-types-public-api. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into research/doctrine-wheel-mission-types-public-api unless the human explicitly redirects the landing branch.
subtasks:
- T015
- T016
- T017
- T018
- T019
- T020
phase: Phase 1 - Gate preconditions
history:
- at: '2026-08-04T15:30:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/kernel/
create_intent:
- tests/architectural/test_kernel_no_doctrine_import.py
execution_mode: code_change
model: ''
owned_files:
- src/kernel/paths.py
- src/doctrine/pack_paths.py
- src/doctrine/missions/repository.py
- tests/architectural/test_kernel_no_doctrine_import.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP04 – Kernel-owned resolution primitive + three-way convergence

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

---

## Objectives & Success Criteria

`src/kernel/paths.py::get_package_asset_root()` hardcodes doctrine's mission-type vocabulary and both `src/doctrine/missions`/`src/specify_cli/missions` path shapes — a C-004 upward-layer violation. Extract a domain-agnostic primitive and converge **three** call sites onto it (not two — a post-plan review found a third, already-promoted authority this issue is explicitly named to converge).

This WP is done when:
- `src/kernel/paths.py` contains no direct `files("doctrine")` lookup and no doctrine-/specify_cli-identifying string or vocabulary.
- `doctrine.pack_paths._resolve_built_in()` **and** `doctrine.missions.repository.MissionTemplateRepository.default_missions_root()` both delegate to the same new primitive.
- `doctrine_package_dir()` is unchanged as its own public symbol.
- A new kernel-scoped architectural test proves the above, with a self-mutation non-vacuity check.
- Full existing suite (`tests/kernel`, `tests/doctrine`, `tests/charter`) is green.

## Context & Constraints

Read `spec.md` (FR-004, NFR-002, User Story 1/AS2), `plan.md` (IC-04), `research.md` (R3, R7), and `contracts/kernel-resolution-primitive.md` in full before starting — the contract file specifies the exact resolution-order contract (env override → editable-checkout ancestor walk → installed-wheel sibling → fail-closed) and postconditions.

**Verified pre-state** (re-confirm against your checkout):
- `src/kernel/paths.py::get_package_asset_root()` (~line 63-117), its `_looks_like_missions_root` (~76-84, hardcodes `("software-dev", "documentation", "research", "plan")` and the `templates`/`command-templates`/`mission-steps` shape) and `_resolve_env_root` (~86-100, candidate list includes both `src/doctrine/missions` and `src/specify_cli/missions` literally).
- `src/doctrine/pack_paths.py::_resolve_built_in()` (~line 177-203) — the algorithmically-parallel-but-domain-clean shape to model the primitive on: env override → `Path(__file__).resolve()` ancestor walk → `doctrine_package_dir()` (a lazy `files("doctrine")` call) → fail-closed `PackRootNotFound`.
- `src/doctrine/pack_paths.py::doctrine_package_dir()` (~line 206+) — **do not retire this function**. It is a separately-public, identity-pinned symbol (`tests/doctrine/test_built_in_location_authority.py` asserts its identity; `drg/migration/extractor.py` also imports it directly). Only `_resolve_built_in()`'s internal *call* to it changes.
- `src/doctrine/missions/repository.py::MissionTemplateRepository.default_missions_root()` (~line 97-108) — the **already-promoted authority**. `tests/charter/test_missions_root_authority.py`'s docstring explicitly states this convergence is deferred to issue #3091 (this mission) — you are completing already-declared scope, not inventing new scope.

**Exception translation**: since `src/kernel/` cannot import `doctrine.pack_paths.PackRootNotFound` (layer direction), your new primitive will raise its own exception type. `pack_paths._resolve_built_in()`'s call site must catch-and-re-raise as `PackRootNotFound` — `specify_cli/doctrine/pack_validator.py:793`'s `except (PackRootNotFound, BuiltInContentDirNotAvailable)` depends on that specific type surviving at this boundary.

**The interim-state trap**: any code path holding a doctrine-identifying string at any point — even transiently, even as a runtime argument rather than an import statement — reproduces the violation in spirit, not just the letter. The primitive's own anchor must be the *calling* package's own `__file__`, never a passed-in package-name string.

**Charter obligation (binding, `charter.md:496`)**: "Every module under `src/charter/` and `src/kernel/` MUST declare `__all__`." Whatever you name the new primitive, it must be added to `src/kernel/paths.py`'s existing `__all__` list — or, if you implement it as a new sibling module within `src/kernel/`, that module needs its own `__all__`. This was flagged as missing from the mission plan's own Charter Check during `/spec-kitty.analyze` — do not skip it.

## Branch Strategy

- **Strategy**: {{branch_strategy}}
- **Planning base branch**: {{planning_base_branch}}
- **Merge target branch**: {{merge_target_branch}}

## Subtasks & Detailed Guidance

### T015 – Design and implement the kernel-owned primitive

- **Purpose**: One canonical, domain-agnostic resolution algorithm.
- **Steps**: Implement a function (location and exact name your choice, e.g. `src/kernel/paths.py` itself or a new sibling module) matching `contracts/kernel-resolution-primitive.md`'s contract: env override → editable-checkout ancestor walk from the caller's own `__file__` → installed-wheel sibling of the caller's own package → fail-closed with a named exception. It must accept the caller's own anchor (`__file__`) and the sibling-relative path being sought as parameters — never a hardcoded package name.
- **Files**: `src/kernel/paths.py` (or a new sibling module).
- **Parallel?**: No — foundation for T016-T018.

### T016 – Repoint `kernel.paths.get_package_asset_root()`

- **Purpose**: Close the original violation this WP was scoped around.
- **Steps**: Replace the body of `get_package_asset_root()` with a call to the T015 primitive. Remove `_looks_like_missions_root` and `_resolve_env_root` (their logic either becomes unnecessary given the primitive's generic resolution, or — if some SPEC_KITTY_TEMPLATE_ROOT-override behavior genuinely needs to survive — is reimplemented without hardcoded vocabulary).
- **Files**: `src/kernel/paths.py`.
- **Parallel?**: No.

### T017 – Converge `pack_paths._resolve_built_in()`

- **Purpose**: One less parallel implementation.
- **Steps**: Replace `_resolve_built_in()`'s body with a call to the T015 primitive, keeping `doctrine_package_dir()` as a separate, unmodified symbol used only where it's still needed (e.g. by `extractor.py`). Add the exception-translation (primitive's exception → `PackRootNotFound`) at this call site.
- **Files**: `src/doctrine/pack_paths.py`.
- **Parallel?**: Can run alongside T018 once T015/T016 land.

### T018 – Converge `MissionTemplateRepository.default_missions_root()`

- **Purpose**: Complete the convergence WP06 of the sole-door mission explicitly deferred to this issue.
- **Steps**: Replace this classmethod's body with a call to the T015 primitive.
- **Files**: `src/doctrine/missions/repository.py`.
- **Parallel?**: Can run alongside T017 once T015/T016 land.

### T019 – New kernel-scoped architectural gate

- **Purpose**: Prove SC-002, since no existing gate covers this edge.
- **Steps**: Write an AST-walk test (same idiom as `tests/architectural/test_charter_no_specify_cli_import.py` — its own docstring explains why pytestarch's static-import-edge analysis can't see a string-literal `importlib.resources.files(...)` call) that walks every module under `src/kernel/**` and fails if any AST node contains the strings `"doctrine"`, `"specify_cli"`, or any mission-type name. Prove non-vacuity via self-mutation: temporarily reintroduce the pattern and confirm the gate reds naming the exact site, then revert.
- **Files**: `tests/architectural/test_kernel_no_doctrine_import.py` (new).
- **Parallel?**: Can run alongside T017/T018.

### T020 – Verify NFR-001

- **Purpose**: Prove no regression.
- **Steps**: Run the full existing test suite for `tests/kernel/`, `tests/doctrine/`, `tests/charter/`. All green (except pre-existing baseline-red pins per the repo's own policy — verify any red you see is genuinely pre-existing before assuming it's yours).
- **Files**: n/a (verification).
- **Parallel?**: No — final gate.

## Test Strategy

```bash
PYTHONPATH=src python -m pytest tests/kernel tests/doctrine tests/charter tests/architectural/test_kernel_no_doctrine_import.py -q
```

## Risks & Mitigations

- **Risk**: Retiring `doctrine_package_dir()` by mistake (it's easy to read "converge onto the primitive" as "delete everything in `_resolve_built_in()`"). **Mitigation**: `tests/doctrine/test_built_in_location_authority.py` will fail loudly if this happens — run it explicitly, don't just trust the broader suite.
- **Risk**: Forgetting the exception-translation at the `pack_paths.py` boundary. **Mitigation**: `pack_validator.py`'s existing `except (PackRootNotFound, ...)` clause will silently stop catching the new exception type if this is missed — grep for that call site and verify manually, since a missing except clause doesn't always produce an obvious test failure.
- **Risk**: If WP01 also touches `tests/architectural/_gate_coverage_baseline.json` in a parallel lane, this WP's new test file may need the same baseline regeneration. Check WP01's Activity Log before finalizing.

## Review Guidance

- Confirm `doctrine_package_dir()` still exists, unmodified, and is still imported by `extractor.py`.
- Confirm the new gate's non-vacuity proof (self-mutation) is actually demonstrated, not just asserted in prose.

## Activity Log

> **CRITICAL**: Activity log entries MUST be in chronological order (oldest first, newest last). Append new entries at the end.

- 2026-08-04T15:30:00Z – system – Prompt created.
