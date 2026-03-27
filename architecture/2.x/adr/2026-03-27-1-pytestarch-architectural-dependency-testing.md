# ADR: PyTestArch for Architectural Dependency Testing

**Date**: 2026-03-27
**Status**: Accepted
**Scope**: CI enforcement of package boundary invariants across `kernel`, `doctrine`, `constitution`, and `specify_cli`

---

## Context

The 2.x architecture defines four peer containers with a strict dependency direction:

```
kernel          (zero outgoing dependencies — the true root)
  ^
doctrine        (depends on kernel only)
  ^
constitution    (depends on doctrine + kernel, may import specify_cli.runtime)
  ^
specify_cli     (depends on all three)
```

These invariants are documented in `architecture/2.x/00_landscape/` and enforced by convention. However, violations can be introduced silently:

- **Lazy imports** inside method bodies (e.g., `from specify_cli.runtime.resolver import resolve` inside a `doctrine` class method) pass mypy, pass import-time checks, but violate the boundary at runtime. This was discovered during the mission 058 architectural review (AR-1).
- **Accidental imports** during refactoring — a developer moving code between packages may inadvertently introduce a backward dependency.
- **Transitive violations** — module A imports module B which imports module C, creating an indirect dependency chain that's hard to spot in code review.

There is no automated CI gate that catches these violations today.

## Decision

Adopt **PyTestArch** (v4.0.1, Apache 2.0, [github.com/zyskarch/pytestarch](https://github.com/zyskarch/pytestarch)) as a dev dependency for architectural dependency testing.

### Why PyTestArch

| Criterion | Assessment |
|-----------|-----------|
| **API fit** | `LayeredArchitecture` + `LayerRule` maps 1:1 to our C4 containers |
| **Detection method** | AST parsing — sees ALL import statements including lazy/conditional imports inside method bodies |
| **Granularity** | Sub-module rules express "constitution may import `specify_cli.runtime` but not `specify_cli.cli`" |
| **pytest native** | Session-scoped fixture, `assert_applies()`, standard pytest assertions |
| **Performance** | One-time AST parse per session; graph traversal per rule. ~500 source files is well within bounds |
| **Maintenance** | Active (255 commits, 27 releases, 153 stars). Python 3.9-3.13 supported |
| **License** | Apache 2.0 — compatible with our MIT license |

### What it catches

- Direct imports across package boundaries (both module-level and lazy)
- Transitive dependency violations via graph traversal
- Regressions introduced by refactoring

### What it does not catch

- `importlib.import_module()` dynamic imports (rare in our codebase)
- Non-Python dependency references (YAML cross-references, etc.)
- Circular dependency cycles (no built-in API; addressable via networkx separately)

### Alternatives considered

| Alternative | Why not |
|-------------|---------|
| Manual `grep` in CI | Fragile, misses transitive violations, no graph semantics |
| `import-linter` | Less expressive rule API, no layer abstraction, less active maintenance |
| Custom AST walker | Maintenance burden, reinvents what PyTestArch already provides |
| mypy plugin | mypy checks types not architectural boundaries; wrong tool for the job |

## Implementation

### Test structure

```
tests/
  architectural/
    conftest.py          # session fixtures: evaluable, landscape
    test_layer_rules.py  # invariant tests
```

### Core invariants encoded

1. **kernel imports nothing** from doctrine, constitution, or specify_cli
2. **doctrine imports only kernel** — never specify_cli or constitution
3. **constitution does not import specify_cli** (except `specify_cli.runtime`, which is permitted)
4. **No reverse dependencies** — specify_cli does not import from itself through doctrine or constitution

### CI placement

Tests are marked `@pytest.mark.architectural` and run at the same priority as kernel tests: fast, every PR, fail-fast. A single violation blocks the PR.

## Consequences

**Positive**:
- Package boundary violations are caught before merge, not during architectural review
- New contributors get immediate feedback on dependency direction
- The invariants are executable documentation, not just prose in `00_landscape/`
- Session-scoped fixture means near-zero overhead added to test suite

**Negative**:
- One new dev dependency (`pytestarch`)
- AST parsing treats lazy imports the same as module-level imports — this is intentional for our use case but means a legitimate lazy import pattern (if one were ever needed) would require an explicit exclusion in the test

**Neutral**:
- The evaluable architecture is rebuilt per test session. If the codebase grows significantly (>5000 files), the session fixture may need `level_limit` tuning.
