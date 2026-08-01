# Contract: `resolve_pack_root(tier)`

**Module**: `src/doctrine/pack_paths.py` (doctrine layer — must not import charter/specify_cli, C-004).

## Signature

```python
def resolve_pack_root(tier: Literal["built-in", "org", "project"], *, org_root: Path | None = None,
                      project_root: Path | None = None) -> Path: ...
```

## Resolution order (built-in)

1. `SPEC_KITTY_PACKS_ROOT` env → `<env>/built-in` if it exists.
2. Editable: nearest ancestor of `__file__` containing `packs/built-in/`.
3. Installed: `files("doctrine")`.parent / `packs` / `built-in` if it exists.
4. Else raise `PackRootNotFound("built-in")`.

`org`/`project`: return the caller-supplied `org_root` / `project_root` (unchanged semantics — the
seam is shared, the tier inputs differ).

## Guarantees (tested — FR-006 two-layout matrix)

- **Editable**: from a repo checkout, returns repo-root `packs/built-in/`.
- **Installed**: from a clean-venv wheel install (no repo `src/` on path), returns the site-packages
  `packs/built-in/`.
- **Fail-closed**: never returns a path inside `src/doctrine/`; never falls open to an arbitrary tree.
- **Idempotent / pure**: no mutation; same inputs → same path.

## Consumers repointed (FR-003/FR-004)

- `built_in_graph_source()` → `resolve_pack_root("built-in")`.
- each repository `built_in_dir` default → `resolve_pack_root("built-in") / <kind>`.
- the enumerated moved-tree readers + the `specify_cli` hardcoded string path.

## Non-goals (C-002)

- Does **not** unify the *loader* or *schema* (built-in stays a `DRGGraph`/14-fragment reader; org
  stays `OrgDRGFragment`). This contract unifies the **path**, not the load mechanism.
