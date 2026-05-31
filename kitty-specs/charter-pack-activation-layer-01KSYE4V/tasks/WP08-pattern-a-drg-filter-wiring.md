---
work_package_id: WP08
title: 'Pattern A: DRG Filter Wiring (4 call sites + _node_is_activated)'
dependencies:
- WP02
- WP03
requirement_refs:
- FR-013
- FR-015
- FR-019
- FR-031
- FR-032
- FR-035
- FR-036
- FR-038
tracker_refs: []
planning_base_branch: pr/charter-doctrine-mission-type-configuration
merge_target_branch: pr/charter-doctrine-mission-type-configuration
branch_strategy: All changes land on pr/charter-doctrine-mission-type-configuration.
subtasks:
- T034
- T035
- T036
- T037
- T038
agent: claude
history:
- at: '2026-05-31T11:44:22Z'
  event: created
  actor: claude
agent_profile: python-pedro
authoritative_surface: src/charter/drg.py
execution_mode: code_change
owned_files:
- src/charter/drg.py
- src/charter/context.py
- src/charter/reference_resolver.py
- src/charter/compiler.py
- src/specify_cli/mission_step_contracts/executor.py
- tests/charter/test_activation_filtered_drg.py
- tests/charter/test_context.py
- tests/charter/test_drg_filtering.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load python-pedro
```

You are **python-pedro** (Python implementer). Make only the changes described,
validate after each subtask, and do not touch files outside `owned_files`.

---

## Objective

Wire `filter_graph_by_activation` — already present in `src/charter/drg.py:666`
with zero production callers — into the 4 call sites documented in the `drg.py`
comment block at lines 712–738. Also extend `_node_is_activated` with a per-
artifact-ID second gate using the 8 `activated_*` frozensets added in WP02.

**Satisfied requirements**: FR-013, FR-015, FR-031, FR-032, FR-035, FR-036, FR-038.

**Layer rule**: `doctrine.*` must NEVER import from `charter.*`. `doctrine.drg` is
NOT modified. All filtering stays in `charter.*` and `specify_cli.*`.

**ATDD rule**: Every test whose call target changes signature must be updated in
this WP. No stale mocks.

---

## Context

The 4 wiring sites (from `research.md §2` and the `drg.py` comment block):

1. `src/charter/context.py:523` — `_load_action_doctrine_bundle()` → filter merged DRG before `resolve_context()`
2. `src/charter/reference_resolver.py:40` — `resolve_references_transitively()` → filter before `resolve_transitive_refs()`
3. `src/charter/compiler.py:499` — `_resolve_transitive_reference_graph()` → filter after load
4. `src/specify_cli/mission_step_contracts/executor.py:170` → filter before `resolve_context()`

All sites must thread `PackContext` from the enclosing `ProjectContext` via
`ctx.require_pack_context()`. Passing `None` is only allowed in test isolation.

**Commit cadence**: after T034 (self-contained `drg.py` change), then T035+T036
together, then T037+T038 together, then the ATDD test pass.

---

## Subtasks

---

### T034 — Extend `_node_is_activated` with per-artifact-ID gate

**Requirement**: FR-038 | **File**: `src/charter/drg.py`

Read `_node_is_activated` (near line 650) and `_SINGULAR_TO_PLURAL` in full before
editing. The existing function currently checks only `activated_kinds`.

1. Add constant `_SINGULAR_TO_PER_KIND_FIELD` immediately after `_SINGULAR_TO_PLURAL`:

   ```python
   _SINGULAR_TO_PER_KIND_FIELD: dict[str, str] = {
       "directive":             "activated_directives",
       "tactic":                "activated_tactics",
       "styleguide":            "activated_styleguides",
       "toolguide":             "activated_toolguides",
       "paradigm":              "activated_paradigms",
       "procedure":             "activated_procedures",
       "agent_profile":         "activated_agent_profiles",
       "mission_step_contract": "activated_mission_step_contracts",
   }
   ```

2. Extend `_node_is_activated` with the per-artifact-ID gate after the existing
   kind-level check:

   ```python
   # Step 2: per-artifact-ID gate (FR-038, WP08)
   per_kind_field = _SINGULAR_TO_PER_KIND_FIELD.get(node_kind)
   if per_kind_field is not None:
       per_kind_set = getattr(pack_context, per_kind_field, None)
       if per_kind_set is not None:
           # artifact_id="" (malformed URN) → bypass (default-allow)
           if artifact_id and artifact_id not in per_kind_set:
               return False
   ```

3. Smoke test:
   ```bash
   cd /home/stijn/Documents/_code/SDD/fork/spec-kitty
   python -c "from charter.drg import filter_graph_by_activation, _node_is_activated; print('OK')"
   ```

4. Confirm that `_SINGULAR_TO_PLURAL` still exists unchanged — you must not modify
   the existing kind-level gate logic, only append the second gate after it.

**ATDD**: `pytest tests/charter/test_activation_filtered_drg.py -x -v` must pass.
Existing tests rely on `None` per-kind-sets, which bypass the new gate — they should
continue to pass without modification.

```bash
cd /home/stijn/Documents/_code/SDD/fork/spec-kitty
pytest tests/charter/test_activation_filtered_drg.py -x -v 2>&1 | tail -15
```

---

### T035 — Wire `filter_graph_by_activation` in `context.py`

**Requirement**: FR-032, FR-035 | **File**: `src/charter/context.py`

1. Read `_load_action_doctrine_bundle()` in full (≈line 523). Identify the merge
   step that produces `merged` and the subsequent `resolve_context(merged, ...)` call.

2. Trace upward: find which caller of `_load_action_doctrine_bundle()` has a
   `ProjectContext` or `PackContext` in scope. Add `pack_context: PackContext | None = None`
   to `_load_action_doctrine_bundle()`'s signature and thread it from that caller via
   `ctx.require_pack_context()`.

3. Before the `resolve_context(merged, ...)` call, insert:

   ```python
   if pack_context is not None:
       merged = filter_graph_by_activation(merged, pack_context)
   ```

4. Import `filter_graph_by_activation` from `charter.drg` and `PackContext` from
   `charter.pack_context` at the top of the file if not already present.

5. Confirm the `drg.py` comment block at lines 712–738 names this function — your
   wiring must match exactly what that comment documents.

**Validation**:
```bash
cd /home/stijn/Documents/_code/SDD/fork/spec-kitty
python -c "from charter.context import _load_action_doctrine_bundle; print('OK')"
```

---

### T036 — Wire in `reference_resolver.py`

**Requirement**: FR-032, FR-036 | **File**: `src/charter/reference_resolver.py`

1. Read `resolve_references_transitively()` in full (≈line 40).
2. Add `pack_context: PackContext | None = None` to its signature if absent.
3. Before `resolve_transitive_refs(graph, ...)`, insert:

   ```python
   if pack_context is not None:
       graph = filter_graph_by_activation(graph, pack_context)
   ```

4. Add required imports (`filter_graph_by_activation`, `PackContext`) if absent.
5. Thread `pack_context` through from callers inside `charter.*` that already hold one.
   Leave `None` for callers that do not yet have a context — the guard prevents breakage.
6. Check all callers of `resolve_references_transitively()` in `charter.*` and
   `specify_cli.*`. Callers already holding a `PackContext` should forward it.

**Validation**:
```bash
cd /home/stijn/Documents/_code/SDD/fork/spec-kitty
python -c "from charter.reference_resolver import resolve_references_transitively; print('OK')"
```
If `tests/charter/test_context.py` exists and tests `resolve_references_transitively`,
run it and confirm it passes. If its call signature changed, update the test to pass
`pack_context=None` explicitly.

---

### T037 — Wire in `compiler.py`

**Requirement**: FR-032, FR-035 | **File**: `src/charter/compiler.py`

Add `pack_context: PackContext | None = None` to `_resolve_transitive_reference_graph()`
(≈line 499). After the graph is loaded but before resolution:

```python
if pack_context is not None:
    graph = filter_graph_by_activation(graph, pack_context)
```

Thread `pack_context` up from the public `compile()` entry point using
`ctx.require_pack_context()` if a `ProjectContext` is in scope there.

**Validation**:
```bash
cd /home/stijn/Documents/_code/SDD/fork/spec-kitty
python -c "from charter.compiler import _resolve_transitive_reference_graph; print('OK')"
```

---

### T038 — Wire in `executor.py`

**Requirement**: FR-031, FR-033 | **File**: `src/specify_cli/mission_step_contracts/executor.py`

At the step execution path (≈line 170), before `resolve_context(graph, ...)`:

```python
if pack_context is not None:
    graph = filter_graph_by_activation(graph, pack_context)
```

Import `filter_graph_by_activation` from `charter.drg`. `executor.py` is in
`specify_cli.*` so this import is permitted. Obtain `pack_context` from the
surrounding `ProjectContext` via `ctx.require_pack_context()`, or construct
`PackContext.from_config(repo_root / ".kittify" / "config.yaml", repo_root)` if no
context object exists. Passing `None` is acceptable until callers are migrated.

**All-4-wired check** (run after T035–T038):

```bash
grep -r "filter_graph_by_activation" src/ --include="*.py" \
    | grep -v "__all__" | grep -v "def filter_graph_by_activation"
# Expected: ≥ 4 lines covering context.py, reference_resolver.py, compiler.py, executor.py
```

---

## ATDD — Tests in `test_drg_filtering.py`

Create or extend `tests/charter/test_drg_filtering.py`. Required test classes:

**`TestNodeIsActivatedPerArtifactIdGate`** (6 tests, all must pass without skips):

```python
from charter.drg import _node_is_activated
from charter.pack_context import PackContext
from pathlib import Path

def _pc(**kw) -> PackContext:
    return PackContext(pack_roots=(Path("."),), repo_root=Path("."), **kw)

class TestNodeIsActivatedPerArtifactIdGate:
    def test_non_listed_id_filtered(self):
        assert not _node_is_activated("directive", "dir-blocked",
                                      _pc(activated_directives=frozenset({"dir-ok"})))

    def test_listed_id_passes(self):
        assert _node_is_activated("directive", "dir-ok",
                                  _pc(activated_directives=frozenset({"dir-ok"})))

    def test_none_passes_all(self):
        assert _node_is_activated("directive", "any-id", _pc(activated_directives=None))

    def test_empty_frozenset_blocks_all(self):
        assert not _node_is_activated("directive", "dir-any",
                                      _pc(activated_directives=frozenset()))

    def test_empty_artifact_id_bypasses(self):
        """Malformed URN with empty ID → default-allow."""
        assert _node_is_activated("directive", "",
                                  _pc(activated_directives=frozenset({"dir-only"})))

    def test_unknown_kind_not_gated(self):
        assert _node_is_activated("unknown_kind", "some-id", _pc())
```

**`TestFilterGraphByActivationPerArtifactId`** (2 tests — must NOT be skipped at done time):
- A directive node whose ID is absent from `activated_directives` is removed from the filtered graph
- `activated_directives=None` preserves all directive nodes

Before writing these graph-construction tests, read
`tests/charter/test_activation_filtered_drg.py` to learn the DRG builder API used by
existing tests. Follow that exact pattern. It is acceptable to use `pytest.skip`
scaffolding during T034 while the API is unknown; both skips must be replaced with
real assertions before marking this WP done.

Also update `tests/charter/test_context.py` (if it exists) for any function whose
signature changed in T035–T036. Updated tests must pass `pack_context` explicitly.

---

## Definition of Done

- [ ] `grep -r "filter_graph_by_activation" src/ --include="*.py" | grep -v "__all__" | grep -v "def filter_graph_by_activation"` returns ≥ 4 lines
- [ ] `_node_is_activated` has both kind-level and per-artifact-ID gate; `_SINGULAR_TO_PER_KIND_FIELD` lists all 8 kinds
- [ ] Both `TestFilterGraphByActivationPerArtifactId` tests pass without `pytest.skip`
- [ ] All 6 `TestNodeIsActivatedPerArtifactIdGate` tests pass
- [ ] `pytest tests/charter/ -x` passes (no stale mocks, no signature mismatches)
- [ ] `ruff check src/charter/drg.py src/charter/context.py src/charter/reference_resolver.py src/charter/compiler.py src/specify_cli/mission_step_contracts/executor.py` passes
- [ ] `python -m mypy src/charter/drg.py --strict` passes (or no new errors introduced)
- [ ] No new `from doctrine` import appears in `src/charter/` files

---

## Risks

- **DRG builder API**: read `tests/charter/test_activation_filtered_drg.py` before
  writing graph-construction tests. Use `pytest.skip` as a placeholder until confirmed.
- **PackContext threading depth**: prefer threading through existing parameters over
  constructing a new `PackContext` inside a deep helper (risks double-loading config).
- **None guard is intentional**: `if pack_context is not None:` allows callers that
  pass `None` to remain unbroken until they are migrated.
- **Stale mocks**: search `tests/charter/` for patches of the 4 wired functions and
  update any that use old signatures.

---

## Reviewer Guidance

1. `grep -r "filter_graph_by_activation" src/ --include="*.py" | grep -v "__all__" | grep -v "def filter_graph"` — must return lines in all 4 target files.
2. `_node_is_activated` in `drg.py` — two distinct `if` gates must be visible.
3. `_SINGULAR_TO_PER_KIND_FIELD` — must list all 8 kinds. Missing entries mean silent pass-through.
4. `grep -r "from doctrine" src/charter/ --include="*.py"` — must return zero new lines from this WP.
5. Both graph-construction tests in `test_drg_filtering.py` — must have real assertions, not `pytest.skip`.
6. `pytest tests/charter/ -x` — must exit 0.
