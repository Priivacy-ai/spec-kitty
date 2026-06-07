# Contract — `mission_runtime` public API

The canonical execution-state surface. Consumers import **only** from the package root.

## Public surface (`mission_runtime/__init__.py` `__all__`)

```python
__all__ = ["ExecutionContext", "ExecutionMode", "resolve_action_context", "ActionContextError"]
```

## `resolve_action_context`

```
resolve_action_context(
    repo_root: Path,
    mission: str,                 # mission_id | mid8 | mission_slug (never mission_number)
    wp_id: str | None = None,
    *,
    mode: ExecutionMode | None = None,   # inferred when None
) -> ExecutionContext
```

**Guarantees**
- CWD-invariant: identical result regardless of the caller's working directory (gated by the parity ratchet).
- Topology-aware: `feature_dir`/`read_dir`/`write_dir` resolved via mission topology, never raw-constructed.
- Mode-correct `target_branch` (FR-012); refuses to resolve mainline as a write target without explicit operator authorization (C-001).
- Raises `ActionContextError` on unresolvable context — no silent fallback.

**Forbidden for consumers**
- Importing relocated internals (`mission_runtime.resolution`, `mission_runtime.context`) directly — enforced by `tests/architectural/test_mission_runtime_surface.py` (FR-005).
- Constructing `main_repo_root / "kitty-specs" / mission_slug` independently (FR-009).

## Migration contract (Stage C)

- The façade delegates to today's resolver during migration; behavior is preserved (NFR-001).
- `core/execution_context.py` is a thin re-export shim during migration, removed when unreferenced (FR-003).
- Stage B (commit-owning operation service / CommitTarget) is **out of scope** (C-008) and not part of this contract.
