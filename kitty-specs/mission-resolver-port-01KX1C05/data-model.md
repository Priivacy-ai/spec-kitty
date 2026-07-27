# Phase 1 — Data Model

Mission `mission-resolver-port-01KX1C05` · #2173 Phase-2. No persistent data model changes — this is a
DI seam over existing reads. The "entities" here are the port interface and the value objects it moves.

## Value objects (existing, reused unchanged)

### `ResolvedMission` (`context/mission_resolver.py:51`, frozen)
| Field | Type | Meaning |
|-------|------|---------|
| `mission_id` | `str` | 26-char ULID from `meta.json` |
| `mission_slug` | `str` | `kitty-specs/` directory name |
| `feature_dir` | `Path` | absolute mission directory |
| `mid8` | `str` | first 8 chars of `mission_id` |

### `MissionExecutionContext` (`mission_runtime/context.py:262`, frozen) — renamed from `ExecutionContext` (FR-012)
The pure composite the builder mints. **Invariant: never carries an adapter** (C-006). This mission
renames the class from `ExecutionContext` to `MissionExecutionContext` (DDD ubiquitous language; also
disambiguates from `core/context_validation.py::ExecutionContext(StrEnum)`, which is NOT renamed) and
makes its builder injectable at the shell.

## New port interface

### `MissionResolver` (Protocol) — **defined in `mission_runtime`** (shell owns its port)
Lives in `mission_runtime/mission_resolver_port.py` so the shell references a local type and **no new
`mission_runtime → specify_cli.context` layer-ledger edge** is created (D-Q2 revised). Adapters import it
downward via `specify_cli → mission_runtime` (package root).
```python
class MissionResolver(Protocol):
    def resolve(self, handle: str) -> ResolvedMission: ...
    def all_missions(self) -> list[ResolvedMission]: ...
```
- `resolve(handle)` — the identity resolution currently in `resolve_mission`; **fail-closed-loud**:
  ambiguity → `AmbiguousHandleError`/`MissionSelectorAmbiguous`, cold-miss → `MissionNotFoundError`
  naming `spec-kitty migrate backfill-identity`. **No** `is None`/`or slug` fallback (D-05).
- `all_missions()` — the enumeration currently in `_build_index`, for the resolve-by-identity consumers
  (`doctrine_synthesizer/apply.py`, `vcs/detection.py`) that scan for a matching `mission_id`.
- Bound to a `repo_root` at construction (adapter concern), so callers pass only the handle.

### `FsMissionResolver` — real adapter
- Wraps the existing `_build_index(repo_root)` walk + the `resolve_mission` priority ladder.
- **Request-scoped**; instance-lifetime memoization only, **no** module/process cache (C-005).
- Silently skips `mission_id`-less / non-dict-meta missions exactly as `_build_index` does today (so the
  anti-fold `identity_audit.py` consumer keeps its own walk — C-001).

### `FakeMissionResolver` — stub adapter
- Constructed from an in-memory `list[ResolvedMission]` (canonical-shaped fixtures — D-05).
- Zero filesystem access → enables the FS-free builder test (NFR-001).
- Same fail-closed contract: unknown handle → `MissionNotFoundError`; ambiguous → `AmbiguousHandleError`.

## Injection seam (REVISED — thread from callers, not inside the assembler)

The seam is at the **callers** of `_resolve_mission_slug` (it runs before `_assemble_core_fragments` and
feeds it), threaded through the canonicalizer chain to the single walk. The free `resolve_mission` gains
an optional `resolver` param so no path bypasses it. Default constructed at the CLI/`specify_cli` boundary.
```python
# specify_cli/context/mission_resolver.py — the ONE walk, now injectable
def resolve_mission(handle: str, repo_root: Path, *, resolver: MissionResolver | None = None) -> ResolvedMission:
    return (resolver or FsMissionResolver(repo_root)).resolve(handle)

# mission_runtime/resolution.py — shell threads a Protocol-typed resolver down (no context import)
def resolve_action_context(..., *, resolver: MissionResolver | None = None):
    slug = _resolve_mission_slug(..., resolver=resolver)   # → canonicalizer → resolve_mission(resolver=...)
    return _assemble_core_fragments(..., resolver=resolver)
# _resolve_mission_id keeps its legacy-<slug> bootstrap carve-out (D-07), NOT routed through resolve().
# build_execution_context(...) stays FS-free and takes NO resolver.
```
**NFR-001 scope**: the FS-free test drives the *identity-resolution leg* via the Fake; the assembler's
other FS legs (`get_main_repo_root`, `_resolve_coordination_branch`, `_resolve_status_surface_dir`,
topology) are separate ports deferred to later #2173 phases (D-09).

## Out-of-model (anti-fold — NOT routed through the port)
- `status/identity_audit.py` — needs to *see* `mission_id`-less missions the resolver skips (C-001).
- `merge/ordering.py` — `max(mission_number)` aggregate over a caller-supplied non-primary scan root under the merge lock (C-002).
- `core/paths.py:816/835` — best-effort swallow-and-degrade error listing (C-003).
- migration-time walks (C-004).
