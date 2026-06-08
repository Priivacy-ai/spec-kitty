---
work_package_id: WP02
title: mission_runtime umbrella + layer registration + ADR
dependencies: []
requirement_refs:
- FR-001
- FR-002
- FR-005
- FR-006
- C-006
tracker_refs: []
planning_base_branch: feat/execution-state-strangler
merge_target_branch: feat/execution-state-strangler
branch_strategy: Planning artifacts for this mission were generated on 
  feat/execution-state-strangler. During /spec-kitty.implement this WP may 
  branch from a dependency-specific base, but completed changes must merge back 
  into feat/execution-state-strangler unless the human explicitly redirects the 
  landing branch.
subtasks:
- T007
- T008
- T009
- T010
phase: Phase 1 - Foundation
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "2580870"
history:
- at: '2026-06-07T05:16:24Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: architect-alphonso
authoritative_surface: 'src/mission_runtime/__init__.py'
execution_mode: code_change
model: ''
owned_files:
- src/mission_runtime/__init__.py
- tests/architectural/test_layer_rules.py
- tests/architectural/conftest.py
- tests/architectural/test_mission_runtime_surface.py
- architecture/3.x/adr/2026-06-07-1-execution-state-canonical-surface.md
role: architect
tags: []
task_type: implement
---

# Work Package Prompt: WP02 – mission_runtime umbrella + layer registration + ADR

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the profile in the frontmatter before parsing the rest.

- **Profile**: `architect-alphonso`
- **Role**: `architect`

## Objectives & Success Criteria

Stand up the net-new canonical execution-state umbrella with a **lean, well-abstracted** public API over the context objects, register it in the layer meta-guard, and ratify the design in an ADR.

- FR-001/002/005/006. SC-001. C-006 (ADR before mass code).
- The umbrella is empty-but-registered at the end of this WP; relocation is WP03.

## Context & Constraints

- Design basis: `docs/engineering_notes/runtime_and_state_overhaul/06-proposed-domains-and-splits.md` §4/§5, doc 17. Contract: [contracts/mission_runtime_api.md](../contracts/mission_runtime_api.md). Plan IC-01.
- doc 06 §4: `mission_runtime/` is the decided name; must register in `_DEFINED_LAYERS` (both files) or `test_no_unregistered_src_packages` fails. Spine: `kernel ← doctrine ← charter ← specify_cli`; `runtime`/`glossary` siblings.
- Stage-C shape only (§5); Stage-B operation service / CommitTarget is out of scope (C-008).

## Branch Strategy

- **Strategy**: coordination-branch planning; merge to target
- **Planning base branch**: feat/execution-state-strangler
- **Merge target branch**: feat/execution-state-strangler

## Subtasks & Detailed Guidance

### Subtask T007 – Design ADR
- **Steps**: Author `architecture/3.x/adr/2026-06-07-N-execution-state-canonical-surface.md` (Status/Context/Decision/Consequences) recording the module name, public API shape, context-object abstraction, and Strangler migration order. Cite doc 06 §4/§5.
- **Files**: `architecture/3.x/adr/`.

### Subtask T008 – Package skeleton + public API
- **Steps**: Create `src/mission_runtime/__init__.py` with `__all__ = ["ExecutionContext", "ExecutionMode", "resolve_action_context", "ActionContextError"]` (symbols wired in WP03). Add `context.py`/`resolution.py` stubs.
- **Files**: `src/mission_runtime/`.

### Subtask T009 – Layer-guard registration
- **Steps**: Add `mission_runtime` to `_DEFINED_LAYERS` in `tests/architectural/test_layer_rules.py` **and** the landscape fixture in `tests/architectural/conftest.py`. Place it as a charter-level sibling consistent with `runtime`.
- **Files**: `tests/architectural/test_layer_rules.py`, `tests/architectural/conftest.py`.

### Subtask T010 – Sole-resolver architectural test
- **Steps**: Add `tests/architectural/test_mission_runtime_surface.py` asserting no import-level access to `mission_runtime.resolution`/`.context` internals from outside the package (FR-005). Include an injection proof.
- **Files**: `tests/architectural/test_mission_runtime_surface.py`.

## Test Strategy

- `pytest tests/architectural/test_layer_rules.py tests/architectural/test_mission_runtime_surface.py -q` green.

## Risks & Mitigations

- Registration must be exact in both files; ADR must land first (C-006).

## Review Guidance — **Persona IC: Paula Patterns (architecture-scout / single-ownership)**

- Reviewer profile: `paula-patterns`. Verify the API is expressed over context objects (not path fragments), the `__all__` is minimal, and the sole-resolver test actually bites (no allowlist escape). Reject API surface that leaks internals.

## Activity Log

- 2026-06-07T05:16:24Z – system – Prompt created.
- 2026-06-08T04:13:42Z – claude:opus:architect-alphonso:architect – shell_pid=2557234 – Assigned agent via action command
- 2026-06-08T04:21:48Z – claude:opus:architect-alphonso:architect – shell_pid=2557234 – Ready for review: mission_runtime umbrella empty-but-registered (lean __all__ over context-object stubs), layer-guard registration in both files, sole-resolver surface test (pytestarch+AST) with injection proof, ADR 2026-06-07-1. NOTE for WP03/reviewer: pyproject.toml [tool.hatch] packages list does not yet include src/mission_runtime (not in WP02 owned files); add it when the umbrella ships to consumers.
- 2026-06-08T04:28:25Z – claude:opus:reviewer-renata:reviewer – shell_pid=2580870 – Started review via action command
