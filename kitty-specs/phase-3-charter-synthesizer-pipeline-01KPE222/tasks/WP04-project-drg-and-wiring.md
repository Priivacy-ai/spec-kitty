---
work_package_id: WP04
title: Project DRG writer + no-dangling-ref enforcement + consumer wiring (plan alias WP3.7)
dependencies:
- WP02
requirement_refs:
- FR-007
- FR-008
- FR-009
- FR-018
- FR-020
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-phase-3-charter-synthesizer-pipeline-01KPE222
base_commit: 9d239e76b5e1eef0f31811a179a5de91ff0c8149
created_at: '2026-04-17T17:44:38.778044+00:00'
subtasks:
- T021
- T022
- T023
- T024
- T025
- T026
shell_pid: '65770'
history:
- at: '2026-04-17T16:43:25Z'
  actor: tasks
  event: generated
authoritative_surface: src/charter/
execution_mode: code_change
mission_id: 01KPE222CD1MMCYEGB3ZCY51VR
mission_slug: phase-3-charter-synthesizer-pipeline-01KPE222
owned_files:
- src/charter/synthesizer/project_drg.py
- src/charter/synthesizer/validation_gate.py
- src/charter/compiler.py
- src/charter/context.py
- tests/charter/synthesizer/test_project_drg.py
- tests/charter/synthesizer/test_validation_gate.py
- tests/charter/synthesizer/test_charter_compile_project_root.py
- tests/charter/synthesizer/test_context_reflects_synthesis.py
tags: []
---

# WP04 · Project DRG writer + no-dangling-ref enforcement + consumer wiring

## Objective

Three closely-linked deliverables:

1. **Emit** an additive project DRG overlay at `.kittify/doctrine/graph.yaml` (the path `_drg_helpers.py` already reads). Reuse `src/doctrine/drg/models.py::DRGGraph` verbatim; the synthesizer is a thin composer.
2. **Gate** the WP03 promote step on `validate_graph(merge_layers(shipped, project))` returning zero errors (FR-008). Additive-only enforcement (FR-020) rejects overlays that shadow shipped URNs.
3. **Wire** `.kittify/doctrine/` into the `DoctrineService` project-root candidate list in `compiler.py::_default_doctrine_service` and `context.py::_build_doctrine_service` (FR-009). Discovery is **conditional on directory presence** — legacy projects see byte-identical behaviour.

## Context

Read before writing code:
- [plan.md §KD-1](../plan.md) — thin-composer rule; `src/doctrine/drg/` is read-only.
- [data-model.md §E-5](../data-model.md) — overlay discipline (URNs disjoint from shipped; no dangling refs).
- [research.md §R-0-9](../research.md) — the three candidate-list test cases (legacy / present / empty).
- `src/doctrine/drg/validator.py` — FR-008 gate calls this.
- `src/doctrine/drg/graph.py::merge_layers` — the additive-merge contract.
- `src/charter/_drg_helpers.py` — **read touchpoint only**, already resolves `.kittify/doctrine/graph.yaml`; no diff.
- `src/charter/compiler.py::_default_doctrine_service` and `src/charter/context.py::_build_doctrine_service` — existing candidate list for `DoctrineService.project_root`; extend, don't rewrite.

## Branch strategy

- Planning base: `main`
- Merge target: `main`
- Execution worktree: allocated by finalize-tasks (Lane B — parallel with WP03)
- Branch name: `kitty/mission-phase-3-charter-synthesizer-pipeline-01KPE222-lane-b`

## Subtasks

### T021 — `project_drg.py` [P]

**File**: `src/charter/synthesizer/project_drg.py`

Thin composer over `src/doctrine/drg` primitives:
- `emit_project_layer(targets, adapter_outputs, spec_kitty_version) -> DRGGraph` — builds a `DRGGraph` with:
  - One node per target: `DRGNode(urn=f"{target.kind}:{target.artifact_id}", ...)`.
  - Edges derived from each target's `source_urns` (direction per existing DRG conventions: project node *requires* or *derived_from* the source).
  - `generated_by = f"spec-kitty charter synthesize {spec_kitty_version}"`.
- `persist(graph, staging_dir)` — serialize via the same YAML canonicalizer WP03 uses; write into `staging/doctrine/graph.yaml` via `PathGuard.write_text`. Promote will move it to `.kittify/doctrine/graph.yaml`.

No new edge-removal semantics; no new merge semantics. If you're tempted to write reusable DRG graph code, that's a signal to push it to `src/doctrine/drg/` later, not in this WP (KD-1).

### T022 — `validation_gate.py` [P]

**File**: `src/charter/synthesizer/validation_gate.py`

Public: `validate(staging_dir, shipped_drg) -> None`.

Flow:
1. Load the staged project overlay from `staging/doctrine/graph.yaml`.
2. Compute `merged = merge_layers(shipped_drg, project_overlay)` using the existing primitive.
3. Call `validate_graph(merged)` (from `src/doctrine/drg/validator.py`).
4. If any errors: raise `ProjectDRGValidationError(errors=[...], merged_graph_summary=...)` with enough structure for a `rich`-rendered CLI panel that names the dangling URN, the offending artifact, and the source reference that triggered it (US-5).

WP03's `write_pipeline.promote(validation_callback=...)` takes this `validate` function as its gate. On raise, WP03 routes the staging dir to `.failed/` and surfaces the structured error.

NFR-004: fail-closed within 5s. The validator is already fast on the scales we care about; add a timing assertion in `test_validation_gate.py`.

### T023 — Additive-only enforcement (FR-020)

Inside `project_drg.emit_project_layer`, before emitting any node, assert that `target.urn` is NOT already present in `shipped_drg.nodes`. If it is, raise `ProjectDRGValidationError` with a message that names the colliding URN. This is the FR-020 / EC-6 lock: synthesized artifacts carry *new* URNs; they do not shadow shipped URNs.

Same rule for edges: any `DRGEdge` whose `(source, target, kind)` triple already exists in shipped must be rejected as a duplicate-edge violation.

### T024 — Extend `src/charter/compiler.py::_default_doctrine_service`

**File**: `src/charter/compiler.py` (edit)

Locate the current candidate-list logic. Extend it to append `.kittify/doctrine/` **before** the existing `src/doctrine` / `doctrine` candidates — if it exists. Use a helper:

```python
_PROJECT_ROOT_CANDIDATES: tuple[str, ...] = (
    ".kittify/doctrine",   # NEW (Phase 3 synthesis target)
    "src/doctrine",        # existing (code-local shipped-layer path)
    "doctrine",            # existing
)

def _resolve_project_root(repo_root: Path) -> Path | None:
    for candidate in _PROJECT_ROOT_CANDIDATES:
        path = repo_root / candidate
        if path.is_dir():
            return path
    return None
```

**Conditional on directory presence**: if `.kittify/doctrine/` does not exist, the function returns the next candidate — identical behaviour to 3.x today (R-2 mitigation).

### T025 — Extend `src/charter/context.py::_build_doctrine_service`

**File**: `src/charter/context.py` (edit)

Mirror the same candidate-list extension. Both `compiler._default_doctrine_service` and `context._build_doctrine_service` should converge on the same helper — either extract a shared `_resolve_project_root` into `src/charter/_doctrine_paths.py` (a new small module **owned by WP04**; add it to `owned_files` before finalizing) or duplicate the tuple in both files with a comment cross-reference. Prefer the shared helper — duplication invites drift.

If you add `_doctrine_paths.py`, it lives under `src/charter/` (not the synthesizer subpackage) because `DoctrineService` wiring predates the synthesizer.

### T026 — Tests

**Files**:
- `tests/charter/synthesizer/test_project_drg.py` — overlay composition; additive-only node collision rejection; edge duplicate rejection; YAML serialization round-trip; overlay nodes carry correct `generated_by`.
- `tests/charter/synthesizer/test_validation_gate.py` — accept valid overlay; reject dangling URN (one case per link direction); reject duplicate edge; reject cycle; fail-closed within 5s (NFR-004); `ProjectDRGValidationError` contains the offending URN + artifact + source reference.
- `tests/charter/synthesizer/test_charter_compile_project_root.py` — **three locked cases** (R-2):
  1. No `.kittify/doctrine/` directory → `project_root` == whichever existing candidate resolves (legacy 3.x behaviour, byte-identical).
  2. `.kittify/doctrine/` present with synthesized content → `project_root` points there.
  3. `.kittify/doctrine/` present but empty → `project_root` points there but repositories resolve to empty overlays with no shipped-layer impact.
- `tests/charter/synthesizer/test_context_reflects_synthesis.py` — end-to-end (FR-018 / SC-005): run full synthesis against the fixture adapter → invoke `charter context --action specify` → assert at least one project-specific item present in output that was NOT present before synthesis.

## Definition of Done

- All 6 subtasks complete.
- `pytest tests/charter/synthesizer/test_{project_drg,validation_gate,charter_compile_project_root,context_reflects_synthesis}.py` green.
- `mypy --strict` clean on WP04 files (including edits to `compiler.py` / `context.py`).
- Coverage ≥ 90% on new modules (NFR-001).
- R-2 three-case test is green — legacy projects byte-identical to 3.x today.
- SC-005 proven: `charter context --action specify` surfaces at least one project-specific item post-synthesis.

## Risks & premortem

- **R-2 · Candidate-list ripple** — Mitigation: directory-presence gating + the three-case test. Any PR that makes legacy projects see different behaviour is a regression.
- **R-9 · Silent project-layer DRG reads during interview** — WP02 owns the mitigation (shipped-only DRG at interview time); WP04 must not reintroduce a merge during interview-driven paths.
- **KD-1 leak** — Mitigation: any PR that adds generic graph logic in `project_drg.py` (as opposed to thin composition over `src/doctrine/drg`) is a signal to push the logic into `src/doctrine/drg/` later; flag in review.

## Reviewer guidance

1. `project_drg.emit_project_layer` — thin composer test: does every line call a `src/doctrine/drg` primitive or synthesize a node/edge? If any block looks like reusable graph logic, push back.
2. `validation_gate.validate` — does the raised error carry enough structure for a useful CLI panel?
3. `_resolve_project_root` — directory-presence gating is load-bearing. Is the three-case test unambiguous?
4. `test_context_reflects_synthesis` — is the pre/post assertion strict enough? "At least one" is the spec floor; too permissive and regressions slip through.
5. Cross-check: WP03's `write_pipeline.promote` wires `validation_gate.validate` as its `validation_callback` before step 3 (`os.replace`). If WP03 merges first, WP04 connects the wire; if WP04 merges first, WP03's contract must already accept a callback. Coordinate in the parallel lanes.

## Next command

```bash
spec-kitty agent action implement WP04 --agent <your-agent>
```
