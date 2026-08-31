# C-6 — Charter Ownership Invariant Contract

**Kind**: Test harness contract
**Covers**: FR-001, FR-002, SC-001

## Statement

A pytest module at `tests/charter/test_charter_ownership_invariant.py` MUST enforce that for each canonical function in the registry, there is exactly one `FunctionDef` AST node across all Python files under `src/`, located in the canonical file.

### Initial registry

```python
CANONICAL_OWNERS: dict[str, str] = {
    "build_charter_context":       "src/charter/context.py",
    "ensure_charter_bundle_fresh": "src/charter/sync.py",
}
```

### Scan rules

- Walk `src/**/*.py` (exclude `__pycache__`, `tests/`, `.worktrees/`).
- For each file, parse via `ast.parse(file.read_text(), filename=str(file))`.
- Count top-level and nested `FunctionDef` / `AsyncFunctionDef` nodes whose `node.name` is in the registry.
- The invariant is satisfied when, for each registry key:
  - Exactly one file contains a matching FunctionDef.
  - That file's repo-relative path equals the registry value.

### Failure output contract

On violation, the test MUST name:

- The function that failed the invariant.
- Every file that contains a definition of that function (not just the extras).
- The expected canonical location.

Example:

```
Charter ownership invariant violated for 'build_charter_context':
  canonical location: src/charter/context.py
  definitions found in:
    src/charter/context.py            (canonical)
    src/legacy/charter_helper.py:42  (DUPLICATE — remove or rename)
```

## Machine-enforced assertion

```python
# tests/charter/test_charter_ownership_invariant.py (skeleton)
import ast
from pathlib import Path

CANONICAL_OWNERS = {
    "build_charter_context": "src/charter/context.py",
    "ensure_charter_bundle_fresh": "src/charter/sync.py",
}

def _find_defs(repo_root: Path, name: str) -> list[Path]:
    hits = []
    for py in repo_root.joinpath("src").rglob("*.py"):
        if any(part in {"__pycache__"} for part in py.parts):
            continue
        try:
            tree = ast.parse(py.read_text(encoding="utf-8"), filename=str(py))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
                hits.append(py.relative_to(repo_root))
    return hits

def test_charter_ownership_invariant(repo_root):
    violations = []
    for fn_name, canonical in CANONICAL_OWNERS.items():
        found = _find_defs(repo_root, fn_name)
        if len(found) != 1 or str(found[0]) != canonical:
            violations.append(f"{fn_name}: expected single def at {canonical}, found {found}")
    assert not violations, "\n".join(violations)
```

## Non-contract

- Methods with the same name on classes (e.g., `Foo.build_charter_context`) are NOT counted — the invariant is module-level free functions only.
- Adding new names to `CANONICAL_OWNERS` is a per-mission decision; this contract establishes the mechanism, not a fixed registry.

## Breakage response

A failing invariant test means the mission's hard success criterion (SC-001) has regressed. Fix is always to consolidate back to the canonical location, never to add an exception to the test.
