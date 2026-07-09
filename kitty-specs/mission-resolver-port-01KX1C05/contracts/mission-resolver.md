# Contract — `MissionResolver` seam

This is an internal Python interface contract (no HTTP/RPC surface). It binds the behavior every
`MissionResolver` adapter must honor and the wiring the shell must use.

## Interface

```python
class MissionResolver(Protocol):
    def resolve(self, handle: str) -> ResolvedMission: ...
    def all_missions(self) -> list[ResolvedMission]: ...
```

## Behavioral contract

| # | Guarantee | Verified by |
|---|-----------|-------------|
| CT-1 | `resolve(handle)` returns the unique `ResolvedMission` for a full ULID, mid8/partial-mid8 prefix, numbered slug, human slug, or numeric prefix (the existing priority ladder). | resolver unit tests |
| CT-2 | Ambiguous handle → raises `AmbiguousHandleError`/`MissionSelectorAmbiguous`. **Never** first-match-wins. | NFR-005 test |
| CT-3 | Cold-miss → raises `MissionNotFoundError` whose message names `spec-kitty migrate backfill-identity`. **No** `is None`/`or slug` silent fallback (ADR `2026-07-01-1`). | NFR-005 test |
| CT-4 | `all_missions()` returns every mission with a valid `mission_id`; `mission_id`-less / non-dict-meta dirs are silently skipped (matches `_build_index` today). | resolver unit tests |
| CT-5 | `FakeMissionResolver` satisfies CT-1…CT-4 with **zero filesystem access**, constructed from in-memory canonical-shaped `ResolvedMission` fixtures. | NFR-001 FS-free builder test |
| CT-6 | No adapter instance is stored on the frozen `MissionExecutionContext`; the port is injected at `_assemble_core_fragments`, and `build_execution_context` takes no resolver and performs no FS I/O. | `test_mission_runtime_surface.py` + builder test |
| CT-7 | No module/process-level cache; a second `resolve` after a mission is created/merged in the same process (new resolver instance) reflects the new state. | resolver cache-absence test |

## Wiring contract (shell)

```python
def _assemble_core_fragments(repo_root, *, resolver: MissionResolver | None = None, ...):
    resolver = resolver or FsMissionResolver(repo_root)
```
- Default-param DI only (`x or Default()`); no DI container shared with the Clock/InstalledVersion seams (C-006).

## Structural contract (new arch-gate — FR-007)

`tests/architectural/test_mission_resolver_walker_gate.py`:
- **G-1**: no `src/` code performs a raw `iterdir()`/`glob()`/`scandir()` enumeration of the `kitty-specs/`
  dir except `FsMissionResolver` and a token-keyed allowlist of legacy walkers being strangled.
- **G-2**: the allowlist is keyed on module/symbol tokens, never line numbers.
- **G-3**: the gate derives its scan scope from `src/` (cannot silently go blind to an unscanned root).
