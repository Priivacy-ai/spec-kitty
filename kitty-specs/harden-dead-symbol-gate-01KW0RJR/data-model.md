# Data Model: Harden the Dead-Symbol Gate

No domain/persisted entities. The "model" here is the gate's internal AST data structures and the
per-symbol disposition set. Recorded for implementation precision.

## Gate data structures (existing — reuse, don't rebuild)

| Structure | Source | Shape | Use by new detectors |
|-----------|--------|-------|----------------------|
| `path_to_tree` | `_walk_modules` (L951–977) | `dict[Path, ast.Module]` — whole-src AST corpus, parsed once | The detectors `ast.walk` these cached trees (zero new I/O) |
| `path_to_dotted` | `_walk_modules` | `dict[Path, str]` | Attribute a found reference back to its containing module |
| `decls` | `_walk_modules` | `dict[str, frozenset[str]]` (module → `__all__`) | The symbols under test |
| `per_symbol` | `_imports_by_target` (L980–1007) | `dict[str, set[str]]` (target module → imported names) | **Widen this** with non-import edges so `_symbol_has_caller`'s re-export rules apply |
| `star_targets` | `_imports_by_target` | `set[str]` | Existing star-import short-circuit |
| `submodule_index` | `_submodule_index` (L1051) | `dict[str, list[str]]` (prefix → submodules) | Existing parent/submodule re-export rules |

## New structure: per-tree import-alias map (the anchor for C-001)

`alias_map: dict[str, str]` per file — local name → resolved dotted module — built from `ast.Import`
(`alias.asname or alias.name`) and `ast.ImportFrom` with `asname` (`from pkg import mod as m` →
`pkg.mod`). **This is the no-false-negative anchor**: a `<name>.<attr>` or `getattr(<name>, "x")` only
counts as a caller after `<name>` resolves through this map to the *exact declaring module*.

## Detector rules (FR-002 — what each adds to proof-of-life)

| Detector | Trigger AST | Binds to | Adds edge |
|----------|-------------|----------|-----------|
| (a) module-style | `ast.Attribute(value=Name(id in alias_map), attr=N)` | `alias_map[id]` | `per_symbol[module].add(N)` |
| (c) Typer (free) | same `ast.Attribute` inside `app.command()(…)` Call arg | via (a) | — (subsumed) |
| (d-getattr) | `Call(func=Name("getattr"), args=[Name(id in alias_map), Constant(str=N)])` | `alias_map[id]` | `per_symbol[module].add(N)` |
| (b) facade | module with `FunctionDef("__getattr__")` + dict-literal `{… : (submodule, "N")}` | submodule | mark submodule's `N` live |

After widening `per_symbol`, the existing `_symbol_has_caller` (direct/parent/submodule) is unchanged.

## Disposition set (per-symbol outcomes)

| Disposition | Symbols | Action | Net effect on `__all__` / allowlist |
|-------------|---------|--------|--------------------------------------|
| DETECT-LIVE | ~the 119 wave minus the residue below | recognized by FR-002 detectors | 0 allowlist entries |
| DELETE | `sync.owner::_daemon_root` | remove re-export + `__all__` entry | −1 symbol |
| DEMOTE | FR-004 set (7) + register-arg (`migrate_v1_to_v2`, `_orchestrator_api_predicate`, `_mission_state_predicate`) + residual annotation-only/test-only | drop from `__all__`, keep def | symbols leave public surface; no allowlist growth |
| WIRE-LIVE | `orchestrator_api.envelope::BANNED_FLAGS` | FR-005 enforces it → becomes a live referenced constant | no disposition needed |
| ALLOWLIST-DEFERRED | `auth.transport::{get_client, get_async_client, reset_clients}` | 1 justified allowlist entry (SaaS migration wave) | +1 entry (deferred, not false-positive) |

**Invariant (NFR-003):** post-mission `category_a_slice_f_deferred` + `category_b_grandfathered_legacy`
frozenset entry counts ≤ their pre-mission base (the only addition is the deferred auth trio; everything
else is detected-live or demoted/deleted). Re-confirm vs #2159/#2152 merge state (C-003).

## The no-false-negative guard (NFR-001)

A regression test: construct a synthetic module with a symbol in `__all__` that has NO caller of any
recognized kind (no import, no `alias.symbol`, no `getattr`, no facade tuple, no registration) and assert
the gate STILL flags it. This proves the detectors widened vision without blinding the gate.
