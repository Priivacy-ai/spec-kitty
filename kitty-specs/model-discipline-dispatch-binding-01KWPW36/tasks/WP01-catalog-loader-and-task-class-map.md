---
work_package_id: WP01
title: Catalog loader + action→task_type map
dependencies: []
requirement_refs:
- FR-001
- FR-002
- C-002
- C-004
tracker_refs:
- '2364'
planning_base_branch: design/model-discipline-dispatch-2364
merge_target_branch: design/model-discipline-dispatch-2364
branch_strategy: Planning artifacts for this mission were generated on design/model-discipline-dispatch-2364. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into design/model-discipline-dispatch-2364 unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-model-discipline-dispatch-binding-01KWPW36
base_commit: 4053c73530e864fadad988c37be9822ad7dff2b7
created_at: '2026-07-04T17:20:29.103002+00:00'
subtasks:
- T001
- T002
- T003
- T004
- T005
phase: Phase 1 - Implementation
assignee: ''
agent: "claude"
shell_pid: '551295'
history:
- at: '2026-07-04T15:30:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/doctrine/model_task_routing/
create_intent:
- src/doctrine/model_task_routing/loader.py
- src/specify_cli/invocation/task_class_map.py
- tests/doctrine/test_model_task_routing_loader.py
- tests/doctrine/test_task_class_map.py
execution_mode: code_change
model: ''
owned_files:
- src/doctrine/model_task_routing/loader.py
- src/specify_cli/invocation/task_class_map.py
- tests/doctrine/test_model_task_routing_loader.py
- tests/doctrine/test_task_class_map.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP01 – Catalog loader + action→task_type map

## Load Agent Profile (python-pedro)

Use the `/ad-hoc-profile-load` skill to load the `python-pedro` agent profile (role: `implementer`) before doing any work, and behave according to its guidance while executing this prompt.

## Objectives & Success Criteria

- Turn the dead `model_task_routing` catalog into a loadable, freshness-checked runtime source: `loader.py` resolves the catalog by default via `importlib.resources.files("doctrine.model_task_routing")/"catalog"/"model-to-task_type.yaml"`, accepts an injectable override `load(catalog_path: Path | None = None)`, parses YAML, validates against `ModelToTaskType`, and applies `freshness_policy`.
- Bridge dispatch verbs to catalog `task_type` vocabulary via a new `task_class_map.py`, kept in sync with `DEFAULT_ROLE_CAPABILITIES` canonical verbs.
- Missing/whole-file-invalid catalog resolves to `None` (non-fatal, absent) rather than raising; a stale catalog (per `freshness_policy`) is flagged.
- This is a foundation WP (no dependencies); WP02 consumes both the loader and the task-class map.

## Context & Constraints

- Source of truth: `kitty-specs/model-discipline-dispatch-binding-01KWPW36/spec.md` FR-001, FR-002, C-002, C-004; `plan.md` IC-01; `tasks.md` WP01 section.
- The catalog schema is `src/doctrine/schemas/model-to-task_type.schema.yaml`; the Pydantic mirror is `src/doctrine/model_task_routing/models.py` — do not touch `models.py` itself in this WP.
- **Non-fatal by contract**: a missing catalog file, or a whole-file-invalid YAML, must resolve to an absent result — never raise out of the loader. This is distinct from a malformed *entry*, which fails schema validation at load (that failure mode belongs to normal `ModelToTaskType.model_validate` behavior, not to this loader's non-fatal envelope).
- `loader.py` must be pure/deterministic — no hidden global state, no implicit caching that hides staleness.
- The action→task_type map is a **live maintenance seam**: it must track both the dispatch action/role verb namespace (`DEFAULT_ROLE_CAPABILITIES` canonical_verbs) and the catalog's `task_type` vocabulary.
- **Catalog resolution mechanism**: the loader resolves the catalog via `importlib.resources.files("doctrine.model_task_routing")/"catalog"/"model-to-task_type.yaml"` by default, AND accepts an injectable override `load(catalog_path: Path | None = None)` (the override is REQUIRED so WP03's vary-with-catalog test can point at fixture catalogs). There is no "activation convention" or activated catalog path — this is Python package data.
- Shared contract with WP05: WP05 ships the catalog at exactly `src/doctrine/model_task_routing/catalog/model-to-task_type.yaml` (package data); the loader's default path MUST match.
- Note: loader.py + task_class_map.py are ORPHANS until WP03 wires them into `invoke()` — expected; the dead-modules invariant is validated at the WP03 tip, not per-WP. Per-WP reviewers: do NOT reject WP01 on the expected loader/task_class_map orphan.
- Red-first mandatory (NFR-001 in spirit for this WP): write T001/T002 first, record them RED, then implement to green.
- Keep `ruff`/`mypy` clean; complexity ≤ 15; no literal repeated ≥3× without hoisting to a constant.

## Subtasks

- [ ] T001 [red-first] `tests/doctrine/test_model_task_routing_loader.py`: valid catalog loads + validates; missing → None; whole-file-invalid → None (non-fatal); stale (freshness) → flagged. RECORD pre-fix RED.
- [ ] T002 [red-first] `tests/doctrine/test_task_class_map.py`: known action verb → task_type; unknown → None; map stays in sync with `DEFAULT_ROLE_CAPABILITIES` verbs. RECORD RED.
- [ ] T003 [FR-001] `src/doctrine/model_task_routing/loader.py`: `load(catalog_path: Path | None = None)` resolves the catalog via `importlib.resources.files("doctrine.model_task_routing")/"catalog"/"model-to-task_type.yaml"` by default (injectable override for tests), YAML load, `ModelToTaskType.model_validate`, `freshness_policy` check. Pure/deterministic.
- [ ] T004 [FR-002] `src/specify_cli/invocation/task_class_map.py`: action/role verb → catalog `task_type`.
- [ ] T005 Turn T001/T002 green; `ruff`/`mypy` clean; complexity ≤ 15; no ≥3× literals.

## Branch Strategy

- **Strategy**: Planning artifacts are generated on design/model-discipline-dispatch-2364; completed changes merge back there.
- **Planning base branch**: `design/model-discipline-dispatch-2364`
- **Merge target branch**: `design/model-discipline-dispatch-2364`

## Definition of Done

- [ ] T001/T002 recorded RED pre-fix, then GREEN post-implementation.
- [ ] `loader.py`'s `load(catalog_path: Path | None = None)` resolves the default path via `importlib.resources.files("doctrine.model_task_routing")/"catalog"/"model-to-task_type.yaml"` (with an injectable override) →YAML→`ModelToTaskType.model_validate`→freshness; missing/whole-file-invalid catalog → `None`, non-fatal; stale catalog flagged.
- [ ] `task_class_map.py` maps known action verbs to catalog `task_type`s and returns `None` for unknown verbs; stays in sync with `DEFAULT_ROLE_CAPABILITIES`.
- [ ] `ruff check` and `mypy` clean on owned files; complexity ≤ 15; no unhoisted ≥3× literals.
- [ ] No changes outside `owned_files`.

## Activity Log

- 2026-07-04T17:50:53Z – claude – shell_pid=551295 – Moved to for_review
- 2026-07-04T17:51:49Z – user – shell_pid=551295 – APPROVE (opus, uv-run): red-first genuine; package-data path + injectable override; non-fatal + malformed-raise; scope-clean.
