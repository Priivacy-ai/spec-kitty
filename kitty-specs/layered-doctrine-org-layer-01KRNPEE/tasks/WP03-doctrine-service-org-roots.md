---
work_package_id: WP03
title: DoctrineService Org Roots
dependencies:
- WP02
requirement_refs:
- C-004
- FR-001
- FR-018
- FR-019
- NFR-002
- NFR-006
planning_base_branch: feat/org-doctrine-layer
merge_target_branch: feat/org-doctrine-layer
branch_strategy: Planning artifacts for this mission were generated on feat/org-doctrine-layer. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/org-doctrine-layer unless the human explicitly redirects the landing branch.
subtasks:
- T011
- T012
- T013
- T014
- T015
agent: codex
history:
- date: '2026-05-15'
  event: created
agent_profile: python-pedro
authoritative_surface: src/doctrine/service.py
execution_mode: code_change
owned_files:
- src/doctrine/service.py
- src/charter/compiler.py
- src/charter/reference_resolver.py
- tests/doctrine/test_service_org_layer.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load python-pedro
```

---

## Objective

Add `org_roots: list[Path]` to `DoctrineService`, wire `org_dir` into all 8 repository
property factories, add a `_resolve_org_root()` helper to `_drg_helpers.py`, and update
`compiler.py` and `reference_resolver.py` to use `load_graph_or_dir` for their inline DRG
loads. After this WP, `DoctrineService` correctly exposes three-layer resolution; callers
pass `org_roots=[]` (empty) until WP05 wires in the config-resolved path.

---

## Context

`DoctrineService` (in `src/doctrine/service.py`) is the lazy aggregation service. It
constructs each artifact repository on first access via a property. Currently:

```python
def __init__(self, shipped_root, project_root, active_languages):
    self._shipped_root = shipped_root
    self._project_root = project_root
    ...

def _shipped_dir(self, artifact): return self._shipped_root / artifact / "shipped"
def _project_dir(self, artifact): return self._project_root / artifact  # if project_root

@property
def directives(self):
    if "directives" not in self._cache:
        self._cache["directives"] = DirectiveRepository(
            shipped_dir=self._shipped_dir("directives"),
            project_dir=self._project_dir("directives"),
        )
    return cast(DirectiveRepository, self._cache["directives"])
```

This WP adds `_org_dir()` and threads it through every property.

`compiler.py` and `reference_resolver.py` each have their own inline DRG load that bypasses
`_drg_helpers.py`. Those are cleaned up here, routing through `load_graph_or_dir`.

---

## Branch Strategy

- **Planning/base branch**: `feat/org-doctrine-layer`
- **Merge target**: `feat/org-doctrine-layer`
- **Implement command**: `spec-kitty agent action implement WP03 --agent codex`

---

## Subtask T011 — Add `org_roots` to `DoctrineService` and add `_org_dir()`

**File**: `src/doctrine/service.py`

```python
def __init__(
    self,
    shipped_root: Path | None = None,
    project_root: Path | None = None,
    org_roots: list[Path] | None = None,
    active_languages: list[str] | tuple[str, ...] | None = None,
) -> None:
    self._shipped_root = shipped_root
    self._project_root = project_root
    self._org_roots = org_roots or []
    ...
```

Add helper:

```python
def _org_dir(self, artifact: str) -> Path | None:
    # Use only the first org root for now; multi-root support is internal
    if not self._org_roots:
        return None
    return self._org_roots[0] / artifact
```

`org_roots: list[Path]` is the internal representation; the config and CLI expose a single
`org_root: Path | None`. The list is future-proof for multi-org without exposing that in
the config.

---

## Subtask T012 — Pass `org_dir` through all 8 repository property factories

**File**: `src/doctrine/service.py`

Update all 8 `@property` methods to pass `org_dir=self._org_dir(artifact_key)`.

Example for `directives`:

```python
@property
def directives(self) -> DirectiveRepository:
    if "directives" not in self._cache:
        self._cache["directives"] = DirectiveRepository(
            shipped_dir=self._shipped_dir("directives"),
            org_dir=self._org_dir("directives"),
            project_dir=self._project_dir("directives"),
        )
    return cast(DirectiveRepository, self._cache["directives"])
```

Apply to all 8 properties: `directives`, `tactics`, `styleguides`, `toolguides`,
`paradigms`, `procedures`, `mission_step_contracts`, `agent_profiles`.

Note: some properties also pass `active_languages`; preserve that.

The artifact directory key for each repository:

| Repository | Key passed to `_shipped_dir` / `_org_dir` / `_project_dir` |
|---|---|
| `directives` | `"directives"` |
| `tactics` | `"tactics"` |
| `styleguides` | `"styleguides"` |
| `toolguides` | `"toolguides"` |
| `paradigms` | `"paradigms"` |
| `procedures` | `"procedures"` |
| `mission_step_contracts` | `"mission_step_contracts"` |
| `agent_profiles` | `"agent_profiles"` |

---

## Subtask T013 — Update `compiler.py` and `reference_resolver.py`

**Files**: `src/charter/compiler.py`, `src/charter/reference_resolver.py`

Both files have an inline `graph_path = doctrine_root / "graph.yaml"` → `load_graph(graph_path)`
call that bypasses `_drg_helpers.py`. Replace these with `load_graph_or_dir(doctrine_root)`
(shipped layer only — these paths don't have project or org overlays in their current call
context).

`compiler.py` line 489:
```python
# Before
graph_path = doctrine_root / "graph.yaml"
graph = load_graph(graph_path)

# After
from doctrine.drg.loader import load_graph_or_dir
graph = load_graph_or_dir(doctrine_root)
```

Apply the same change to `reference_resolver.py` line 38.

---

## Subtask T014 — Add `_resolve_org_root()` to `_drg_helpers.py`

**File**: `src/charter/_drg_helpers.py`

Add a helper that reads `DoctrineOrgConfig` from `config.yaml` and returns the org snapshot
path if configured and present:

```python
def _resolve_org_root(repo_root: Path) -> Path | None:
    """Return the configured org doctrine snapshot path, or None if absent.

    Reads ``doctrine.org.local_path`` from ``.kittify/config.yaml``. Returns
    ``None`` if not configured, or if the path does not exist on disk.
    """
    try:
        from specify_cli.doctrine.config import load_doctrine_org_config
        config = load_doctrine_org_config(repo_root)
        if config and config.local_path and config.local_path.exists():
            return config.local_path
    except Exception:
        pass
    return None
```

The `try/except` is intentional: `_drg_helpers` is in the `charter` package which may be
imported without the full `specify_cli` CLI layer. The graceful fallback ensures DRG
loading never fails due to missing config module.

Also update `load_validated_graph()` to use this helper for the org layer:

```python
def load_validated_graph(repo_root: Path, org_root: Path | None = None) -> DRGGraph:
    doctrine_root = resolve_doctrine_root()
    if org_root is None:
        org_root = _resolve_org_root(repo_root)
    shipped = load_graph_or_dir(doctrine_root)
    org = load_graph_or_dir(org_root) if org_root and org_root.exists() else None
    project_dir = repo_root / ".kittify" / "doctrine"
    project = load_graph_or_dir(project_dir) if project_dir.exists() else None
    merged = merge_layers(merge_layers(shipped, org), project)
    assert_valid(merged)
    return merged
```

---

## Subtask T015 — Unit tests for `DoctrineService` with `org_roots`

**File**: `tests/doctrine/test_service_org_layer.py` (new file)

**Test cases**:

| Test | `org_roots` | Expected |
|---|---|---|
| `test_no_org_root` | `[]` | All repositories have `org_dir=None`; shipped + project only |
| `test_single_org_root` | `[tmp_path / "org"]` | `_org_dir("directives")` returns `tmp_path / "org" / "directives"` |
| `test_org_root_missing_on_disk` | Path that doesn't exist | Repositories load without error (org dir just doesn't contribute) |
| `test_org_root_artifacts_resolved` | Org dir with valid directive | `service.directives.get("org-id")` returns the org artifact |
| `test_determinism` | Same inputs twice | Both calls return identical resolved sets |

---

## Definition of Done

- [ ] `DoctrineService.__init__` accepts `org_roots: list[Path] | None`
- [ ] `_org_dir()` helper returns correct path for each artifact type
- [ ] All 8 property factories pass `org_dir`
- [ ] `compiler.py` and `reference_resolver.py` use `load_graph_or_dir` (no `"graph.yaml"` literal)
- [ ] `_resolve_org_root()` added to `_drg_helpers.py`
- [ ] `load_validated_graph()` performs three-layer DRG merge
- [ ] `test_service_org_layer.py` all tests pass
- [ ] All existing `DoctrineService` tests pass

## Risks

- `DoctrineService` is instantiated in several places outside `specify_cli`; find all with
  `grep -r "DoctrineService(" src/`. Pass `org_roots=[]` at those sites for now; WP05
  will replace `[]` with the config-resolved path.
- The `_resolve_org_root()` import of `specify_cli.doctrine.config` creates a cross-package
  dependency from `charter` to `specify_cli`. Wrap in `try/except` as shown to prevent
  import failures in contexts where `specify_cli` is not available.

## Reviewer Guidance

1. Confirm `org_roots=[]` (empty) produces identical behavior to today (two-layer resolution).
2. Confirm `load_validated_graph()` with org layer produces a validated graph (no dangling edges).
3. Check that the `_resolve_org_root()` graceful fallback doesn't swallow genuine errors
   silently — add a debug log line inside the `except` block.
