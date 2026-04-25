# Implementation Plan: Resolver and Bootstrap Consolidation

**Branch**: `kitty/mission-runtime-mission-execution-extraction-01KPDYGW`
**Date**: 2026-04-24
**Spec**: [`spec.md`](./spec.md)

## Summary

Pay down duplication debt introduced by the runtime-extraction mission:

1. Route `src/runtime/discovery/resolver.py` through a new **charter asset-resolver gateway** (`src/charter/asset_resolver.py`) that delegates to `doctrine.resolver`. Preserve `runtime.discovery.resolver` as a module with local `get_kittify_home` / `get_package_asset_root` attributes so the ~15 existing `patch("runtime.discovery.resolver.get_kittify_home", …)` test sites keep working. Collapse the resolver function bodies from ~250 lines to ≤ ~50.
2. Apply the same pattern to `src/runtime/discovery/home.py` ↔ `src/kernel/paths.py` *only if* the SonarCloud duplicated-lines metric for that file remains ≥ 100 after (1) lands.
3. Extract `_run_version_locked_bootstrap(version_filename, lock_filename, work)` into `src/runtime/orchestration/bootstrap.py`. Refactor `ensure_global_agent_commands` and `ensure_global_agent_skills` into thin callers.

All work lands on `kitty/mission-runtime-mission-execution-extraction-01KPDYGW`. No new branch. No new worktree.

## Technical Context

**Language/Version**: Python 3.12 (runtime minimum declared in `pyproject.toml`).
**Primary Dependencies**: None new. Uses existing stdlib + `pytest` + `ruff` + `mypy`.
**Storage**: N/A (no data model changes).
**Testing**: pytest with existing fixtures. Monkeypatch preservation is a first-class concern (NFR-003). No new test frameworks.
**Target Platform**: Linux / macOS / Windows. Windows parity is NFR-004.
**Project Type**: Single project (src-layout Python package).
**Performance Goals**: Zero regression. The extracted helpers are thin wrappers; call-site semantics unchanged.
**Constraints**: Must land on the parent mission branch without creating a new branch or worktree (C-001). Must not touch deprecation shims under `src/specify_cli/{next,runtime}/` (C-002). Must preserve all public symbols in the affected packages (C-003).
**Scale/Scope**: Three production files touched (`charter/asset_resolver.py` new; `runtime/discovery/resolver.py` body rewrite; `runtime/orchestration/bootstrap.py` add helper + migrate two callers). Potentially a fourth (`runtime/discovery/home.py`) if FR-003 triggers. Zero test files renamed or assertions modified; monkeypatch-target migrations only if unavoidable.

## Charter Check

**Gate**: This mission is a scope-increase on a parent mission that has already passed its Charter Check on the runtime-extraction issue (#612). No new charter concerns introduced.

- ✅ **Paradigm alignment** — refactor serves the "single source of truth" paradigm already live in the charter.
- ✅ **Dependency direction** — `kernel → doctrine → charter → runtime → specify_cli` preserved; the new charter module imports from doctrine only (NFR-002).
- ✅ **Specification fidelity (directive 010)** — no functional change; AC spells out behaviour preservation.
- ✅ **Locality (directive 024)** — three files plus one new module; no drive-by edits.

Re-check after Phase 1 design is not required for this mission — it is pure internal refactor with no new surface area.

## Project Structure

### Documentation (this feature)

```
kitty-specs/resolver-and-bootstrap-consolidation-01KPZS0A/
├── spec.md                  # Done
├── plan.md                  # This file
├── tasks.md                 # Next (via /spec-kitty.tasks)
├── tasks/WP*.md             # Next (via /spec-kitty.tasks-packages)
└── status.json, meta.json   # Runtime state
```

No `research.md`, `data-model.md`, `contracts/`, or `quickstart.md` needed — this is a behaviour-preserving refactor, not a new feature. If the implementer finds something that warrants `research.md` (e.g. Windows-path-resolution edge case for FR-003), they can add it during the relevant WP.

### Source Code (repository root)

```
src/
├── charter/
│   └── asset_resolver.py         # NEW — gateway to doctrine.resolver (WP01)
├── runtime/
│   ├── discovery/
│   │   ├── resolver.py           # REWRITE body; keep monkeypatch attributes (WP02)
│   │   └── home.py               # CONDITIONAL — only if Sonar still flags ≥ 100 lines (WP03)
│   └── orchestration/
│       └── bootstrap.py          # ADD _run_version_locked_bootstrap helper (WP05)
│   └── agents/
│       ├── commands.py           # REFACTOR ensure_global_agent_commands to call helper (WP05)
│       └── skills.py             # REFACTOR ensure_global_agent_skills to call helper (WP05)

tests/
├── charter/
│   └── test_asset_resolver.py    # NEW — unit tests for gateway (WP01)
├── runtime/
│   ├── test_resolver_unit.py               # RUN UNCHANGED — monkeypatch smoke (WP02)
│   ├── test_home_unit.py                   # RUN UNCHANGED (WP03 if triggered)
│   ├── test_global_runtime_convergence_unit.py  # RUN UNCHANGED — 15+ monkeypatch sites (WP02)
│   └── test_agent_skills.py                # RUN UNCHANGED (WP05)
└── specify_cli/runtime/
    └── test_agent_commands_routing.py      # RUN UNCHANGED (WP05)
```

Only one new source file (`charter/asset_resolver.py`) and one new test file (`tests/charter/test_asset_resolver.py`).

## Architecture & Design

### Dependency direction (target)

```
kernel  ←  doctrine  ←  charter  ←  runtime  ←  specify_cli
              ↑              ↑            ↑
              └── asset_resolver.py (NEW) ┘
                     gateway, re-exports doctrine symbols
```

- `charter/asset_resolver.py` imports only from `doctrine.resolver` — no upstream deps.
- `runtime/discovery/resolver.py` imports from `charter.asset_resolver` (function bodies only). Keeps its own `get_kittify_home` attribute imported from `runtime.discovery.home` at module scope so existing test monkeypatches remain effective.
- No change to `kernel` or `doctrine`.

### Monkeypatch-seam preservation strategy (Option A, per spec §Risks R1)

Concrete pattern for `resolve_template`:

```python
# src/runtime/discovery/resolver.py — AFTER refactor

from runtime.discovery.home import get_kittify_home, get_package_asset_root
from charter.asset_resolver import resolve_template as _charter_resolve_template

def resolve_template(name: str, project_dir: Path, mission: str) -> ResolutionResult:
    # Pass module-local seams in so `patch("runtime.discovery.resolver.get_kittify_home", ...)`
    # still intercepts every lookup through this function.
    return _charter_resolve_template(
        name, project_dir, mission,
        home_provider=get_kittify_home,
        asset_root_provider=get_package_asset_root,
    )
```

This requires the **charter gateway functions to accept injected providers** — they cannot transparently call `doctrine.resolver.resolve_template` without parametrising the path helpers, because doctrine's resolver resolves them at its module scope.

**Two gateway implementations are in scope for WP01**:

- **Gateway-A (preferred)**: charter gateway defines its own thin `resolve_*` functions that accept `home_provider` / `asset_root_provider` parameters and implement the 4-tier chain directly (reusing `doctrine.resolver.ResolutionTier` / `ResolutionResult` types only). This is ~50 lines of gateway code, but no doctrine-side changes.
- **Gateway-B (alternative)**: charter gateway re-exports `doctrine.resolver.resolve_*` directly; but *doctrine's resolver functions must first be parametrised to accept providers*. That's a doctrine-side change and expands the blast radius.

**Decision**: Gateway-A. Keeps doctrine unchanged. WP01 contracts the gateway API; WP02 wires runtime to it.

### Bootstrap helper shape

```python
# src/runtime/orchestration/bootstrap.py — ADDED

def _run_version_locked_bootstrap(
    version_filename: str,
    lock_filename: str,
    work: Callable[[], None],
) -> None:
    """Idempotent user-global install flow: fast-path, exclusive lock, re-check, work, write-version."""
    kittify_home = get_kittify_home()
    kittify_home.mkdir(parents=True, exist_ok=True)
    cache_dir = kittify_home / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)

    version_file = cache_dir / version_filename
    cli_version = _get_cli_version()
    if version_file.exists() and version_file.read_text().strip() == cli_version:
        return

    lock_path = cache_dir / lock_filename
    with open(lock_path, "w") as lock_fd:
        _lock_exclusive(lock_fd)
        if version_file.exists() and version_file.read_text().strip() == cli_version:
            return
        work()
        version_file.write_text(cli_version)
```

Callers become:

```python
# commands.py
def ensure_global_agent_commands() -> None:
    templates_dir = _get_command_templates_dir()
    if templates_dir is None:
        return
    def _do_sync() -> None:
        script_type = _resolve_script_type()
        for agent_key in AGENT_COMMAND_CONFIG:
            try: _sync_agent_commands(agent_key, templates_dir, script_type)
            except Exception: logger.warning(...)
    _run_version_locked_bootstrap(_VERSION_FILENAME, _LOCK_FILENAME, _do_sync)
```

## Parallel Work Organization

### Dependency graph

```
        ┌──────────┐
        │   WP01   │  charter/asset_resolver.py + tests
        │ (lane A) │  independent, green-field
        └────┬─────┘
             │
             ▼
        ┌──────────┐
        │   WP02   │  runtime/discovery/resolver.py delegate
        │ (lane A) │  depends on WP01
        └────┬─────┘
             │
             ▼ (conditional)
        ┌──────────┐
        │   WP03   │  runtime/discovery/home.py consolidation
        │ (lane A) │  depends on WP02; triggered by Sonar metric
        └──────────┘

        ┌──────────┐
        │   WP05   │  bootstrap helper + both agent callers
        │ (lane B) │  fully independent of Block 1
        └──────────┘

        ┌──────────┐
        │   WP04   │  Sonar metric validation
        │ (lane A) │  depends on WP02 (and WP03 if triggered)
        └──────────┘
```

### Execution layout

- **Lane A (Block 1)**: `WP01 → WP02 → [WP03] → WP04`. Sequential; each unlocks the next.
- **Lane B (Block 2)**: `WP05`. Standalone. Can run concurrently with any WP in Lane A.
- **Agent assignment**: All WPs are Python refactors matching python-pedro's profile. No architectural decisions remain; the planner has chosen Gateway-A and Option A.

### Phase gates

- **Before WP01**: This plan + tasks breakdown merged or at least reviewed by a second maintainer.
- **Between WP02 and WP03**: `curl .../api/duplications/show?key=...:src/runtime/discovery/home.py` to check if Sonar still flags it. If `duplicated_lines < 100`, skip WP03 and go straight to WP04.
- **Before WP04**: All WP01/02/[03] and WP05 merged; manual SonarCloud re-scan triggered if CI doesn't auto-scan on the branch.

## Risk notes (informing task sequencing)

- **R1 mitigation in WP02**: First change in WP02 must include one new monkeypatch test verifying that `patch("runtime.discovery.resolver.get_kittify_home", ...)` intercepts the provider injection. This guards against silent no-ops.
- **R3 mitigation in WP03**: If WP03 runs, include a Windows-simulation unit test pinning `_is_windows → True` and verifying `get_kittify_home()` resolves to `%LOCALAPPDATA%`.
- **WP04 scope**: Purely observational. If Sonar metric doesn't drop to target by merge time, file a follow-up issue rather than holding the mission.

## Definition of Done

- Spec's SC-001 through SC-005 all green.
- `status.events.jsonl` shows `done` or `approved` on every WP.
- No new failing tests on the parent mission branch's CI.
- No drive-by edits unrelated to the FRs/AC.
- `resolver-consolidation-mission-draft.md` at repo root deleted (it was the scaffolding input; superseded by `spec.md`).
