# kernel

Zero-dependency shared utilities for the spec-kitty ecosystem.

## What it is

`kernel` is a minimal, self-contained Python package that provides low-level utilities used by multiple modules in the spec-kitty stack:

- `specify_cli` — the main CLI tool
- `charter` — project governance and context building
- `doctrine` — agent profiles and mission configuration

Currently it contains:

- **`kernel.atomic`** — `atomic_write(path, content, *, mkdir=False)`: writes files atomically via a temp file + rename, preventing partial writes on crashes or power loss.
- **`kernel.glossary_types`** — canonical glossary primitive value types (`Strictness`, `ExtractedTerm`, `SemanticConflict`, `ScopeRef`, `GlossaryScope`); re-exported by `specify_cli.glossary` and `doctrine.shared`.
- **`kernel.paths`** — `get_kittify_home()` and `get_package_asset_root()`: path resolution utilities used by both `specify_cli` and `charter`. `specify_cli.runtime.home` re-exports these for backward compatibility.
- **`kernel.glossary_runner`** — plugin registry for the glossary runner. Defines `GlossaryRunnerProtocol`, `register()`, `get_runner()`, and `clear_registry()` (test-only). `specify_cli.glossary` registers the concrete `GlossaryAwarePrimitiveRunner` at import time; `doctrine` calls `get_runner()` without importing `specify_cli`.

## Why it exists

The spec-kitty codebase is structured as several distinct Python packages (`specify_cli`, `charter`, `doctrine`). These packages share common utilities, but none of them should depend on each other — that would create cyclic imports and tight coupling between layers that have different stability and deployment requirements.

`kernel` breaks this cycle by acting as a dependency floor: it has **no imports from any other spec-kitty package**, and every package that needs shared utilities imports from `kernel` instead of from each other.

```
        specify_cli
           ↓
        charter
           ↓
        doctrine
           ↓
        kernel    ← no spec-kitty imports here
```

## Preventing cyclic dependencies

The rule is simple: **`kernel` must never import from `specify_cli`, `charter`, or `doctrine`**.

If you find yourself needing to import from a higher-level package inside `kernel`, that is a signal that the utility belongs in the higher-level package, not in `kernel`. Keep `kernel` as a leaf node in the import graph.

## Stability contract

Because `kernel` is used by all layers of the stack, it is held to a higher stability standard than the packages that depend on it:

- All public functions must have full test coverage (`tests/kernel/`)
- The public API should remain stable across minor versions
- Breaking changes require bumping the major version

## Adding utilities

Only add to `kernel` if the utility:
1. Has no spec-kitty-specific dependencies
2. Is used (or will be used) by more than one package in the stack
3. Is general-purpose enough to be considered infrastructure
