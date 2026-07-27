# Contract — `resolve_handle_to_read_path` (the single read-side seam)

**Module**: `src/specify_cli/missions/_read_path_resolver.py`
**Lifted from**: `orchestrator_api/commands.py:_resolve_mission_dir` + `_read_primary_meta` (the working prototype).

```
def resolve_handle_to_read_path(repo_root: Path, handle: str) -> Path
```

### Behavioral contract
1. `assert_safe_path_segment(handle)` — reject traversal BEFORE any join (FR-004).
2. `(meta, declares_coordination) = _read_primary_meta(repo_root, handle)` — primary-anchored read.
3. `mid8 = resolve_declared_mid8(meta, handle)` — meta.mid8 → mission_id[:8] → mid8_from_slug.
4. **Fail-closed**: `if not mid8 and declares_coordination: raise <typed refusal>`.
5. **Return** `resolve_mission_read_path(repo_root, handle, mid8)` (worktree-existence-gated). NEVER `resolve_status_surface_with_anchor`.

### Equivalence guarantees (the proofs)
- `<slug>-<mid8>` / full-id handles: resolved dir UNCHANGED vs pre-mission (NFR-002).
- bare-slug × coord-fresh/coord-behind: resolves the COORD dir (SC-001 cells flip; SC-002 per-CLI e2e).
- declared-but-unmaterialized coord (any handle): resolves PRIMARY (SC-005, #1718).
- traversal `handle`: rejected at step 1 (FR-004).
- ambiguous handle: `MISSION_AMBIGUOUS_SELECTOR` propagated (no silent pick).

### Selection-authority guard (FR-006)
After adoption, every read path reaches the resolver THROUGH this seam. A new direct
`resolve_mission_read_path` call or bespoke `resolve_mid8` cascade outside the seam allowlist
fails the AST ratchet; an empty-mid8-against-declared-coord fails the runtime gate.
