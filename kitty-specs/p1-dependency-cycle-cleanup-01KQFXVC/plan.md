# Implementation Plan: P1 Dependency Cycle Cleanup

**Branch**: `main` | **Date**: 2026-04-30 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/kitty-specs/p1-dependency-cycle-cleanup-01KQFXVC/spec.md`
**Mission**: `p1-dependency-cycle-cleanup-01KQFXVC` (mid8: `01KQFXVC`)

## Summary

Remove two P1 circular import cycles identified in GitHub issue #862. P1.2 relocates the `ProjectIdentity` dataclass from `specify_cli.sync.project_identity` into the existing `specify_cli.identity` leaf package (with a shim kept at the original path for backward compatibility) and extracts the `generate_node_id` pure utility to `specify_cli.core`. P1.3 introduces a lightweight fan-out callback registry in `specify_cli.status.fan_out` so that `status/emit.py` calls registered handlers instead of lazy-importing from `specify_cli.sync`; the sync package registers its own handlers at startup, reversing the dependency direction to the clean `sync → status.fan_out` shape. Both changes are pure structural refactors with no behavioral impact and are backed by new architectural guard tests.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: pytest, mypy (strict), ast (stdlib — used by existing architectural tests), ruamel.yaml (existing)
**Storage**: Filesystem only (no database)
**Testing**: pytest 90%+ coverage for new modules, mypy --strict, integration tests for affected CLI commands
**Target Platform**: Linux/macOS (CLI tool)
**Performance Goals**: No regression — refactoring only; no hot-path changes
**Constraints**: No behavioral changes to sync, dossier drift detection, tracker binding, SaaS fan-out, body upload, or status persistence; backward-compatible shim required at `sync.project_identity`; no feature flags; no new external dependencies

## Charter Check

Charter policy (from `.kittify/charter/charter.md`):
- **typer** — CLI framework ✅ not affected
- **rich** — console output ✅ not affected
- **ruamel.yaml** — YAML parsing ✅ not affected
- **pytest with 90%+ test coverage** for new code ✅ required; addressed in each WP
- **mypy --strict** must pass ✅ required; addressed in each WP
- **Integration tests** for CLI commands ✅ existing CLI commands unaffected; test suites verified as part of acceptance

No charter violations. No Complexity Tracking required.

## Project Structure

### Documentation (this feature)

```
kitty-specs/p1-dependency-cycle-cleanup-01KQFXVC/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── contracts/
│   └── fan_out_handler.md   # Fan-out handler callback contract
└── tasks.md             # Phase 2 output (/spec-kitty.tasks command)
```

### Source Code (affected paths)

```
src/specify_cli/
├── identity/                        # EXISTING leaf package — gains new module
│   ├── __init__.py                  # re-export ProjectIdentity for convenience
│   ├── aliases.py                   # existing, unchanged
│   └── project.py                   # NEW: canonical home for ProjectIdentity
│                                    #   generate_node_id logic inlined (no sync dep)
│
├── sync/
│   ├── project_identity.py          # MODIFIED: becomes backward-compat re-export shim
│   ├── clock.py                     # unchanged (keeps its own generate_node_id copy)
│   └── dossier_pipeline.py          # unchanged (TYPE_CHECKING import satisfied by shim)
│
├── dossier/
│   └── drift_detector.py            # MODIFIED: one import line updated to identity.project
│
├── status/
│   ├── emit.py                      # MODIFIED: replace lazy sync imports with adapters calls
│   └── adapters.py                  # NEW: callback registry (no sync imports)
│
└── tests/
    └── architectural/
        └── test_import_boundary_cycles.py  # NEW: guards dossier→sync and status→sync
```

**Structure Decision**: Single-project Python CLI. All changes are within `src/specify_cli/`. No new top-level packages or core modules needed. `specify_cli/identity/` is already a leaf package; `generate_node_id` is inlined in `identity/project.py` (eliminating the transitive `identity → sync` dependency). The sync package remains unchanged structurally; its `project_identity.py` becomes a shim.

## Phase 0: Research

*See [research.md](research.md) for full findings.*

Key resolved questions:

| Question | Decision | Rationale |
|----------|----------|-----------|
| Where does ProjectIdentity live? | `specify_cli/identity/project_identity.py` | `identity/` is already a self-described leaf package with no core/status deps; fits the ownership model |
| Where does generate_node_id go? | Inlined in `specify_cli/identity/project.py` | Pure 3-line stdlib function; inlining eliminates the transitive `identity → sync` dependency entirely; `sync/clock.py` keeps its own copy unchanged |
| Fan-out registry location? | `specify_cli/status/adapters.py` | Co-located with status; zero sync imports; two typed registries (dossier-sync + SaaS fan-out) |
| Registration trigger for P1.3? | `sync/__init__.py` or daemon startup imports `status.adapters` and registers | Ensures registration before first status event; no new bridge module needed |
| Shim retention policy? | Shim at `sync/project_identity.py` re-exports with `DeprecationWarning`; not removed until callers confirmed migrated | Per C-002: no shim removal until architecture guard proves zero remaining callers |

## Phase 1: Design

*See [data-model.md](data-model.md) and [contracts/fan_out_handler.md](contracts/fan_out_handler.md) for full artifacts.*

### P1.2 Change Set

1. **`specify_cli/identity/project.py`** (NEW) — Move `ProjectIdentity` dataclass and all helper functions (`ensure_identity`, `with_defaults`, `to_dict`, `from_dict`, `generate_project_uuid`, `generate_build_id`, `derive_project_slug`). Inline `generate_node_id` logic directly (3-line stdlib hash — eliminates transitive `identity → sync` dependency).
2. **`specify_cli/identity/__init__.py`** — Add re-export of `ProjectIdentity` for convenience.
3. **`specify_cli/sync/project_identity.py`** — Replace entire body with backward-compat re-export shim (`from specify_cli.identity.project import ProjectIdentity as ProjectIdentity  # noqa: F401`). All existing callers outside dossier continue to work unchanged.
4. **`specify_cli/dossier/drift_detector.py`** — Update one import line: `from specify_cli.identity.project import ProjectIdentity`. This is the **only dossier file** that needs changing (per research: single offending caller).
5. **Other callers** — `sync/client.py`, `sync/dossier_pipeline.py`, `sync/namespace.py`, `tracker/origin.py`, `cli/commands/tracker.py` all use `sync.project_identity` and are satisfied by the shim; no change required.

### P1.3 Change Set

1. **`specify_cli/status/adapters.py`** (NEW) — Lightweight callback registry with two typed registries: `DossierSyncHandler` and `SaasFanOutHandler`. Exposes `register_dossier_sync_handler`, `register_saas_fanout_handler`, `fire_dossier_sync`, `fire_saas_fanout`. Zero imports from `specify_cli.sync`.
2. **`specify_cli/status/emit.py`** — Remove both lazy `from specify_cli.sync.*` imports in `_saas_fan_out` and the dossier-sync trigger. Replace with calls to `fire_dossier_sync(...)` and `fire_saas_fanout(...)` from `specify_cli.status.adapters`.
3. **`sync/__init__.py` (or daemon startup)** — Import `specify_cli.status.adapters` and call `register_dossier_sync_handler(trigger_feature_dossier_sync_if_enabled)` and `register_saas_fanout_handler(emit_wp_status_changed_wrapper)`. This registration runs once at sync package initialization.

### Architectural Guard

**`tests/architectural/test_import_boundary_cycles.py`** (new file):
- Walk all `*.py` files under `src/specify_cli/dossier/`; assert no `import specify_cli.sync` or `from specify_cli.sync` appears — including inside `if TYPE_CHECKING` blocks and function bodies (full AST walk).
- Walk all `*.py` files under `src/specify_cli/status/`; apply same assertion for `specify_cli.sync`.
- These tests run in CI and would fail on both the pre-fix codebase and on any future regression.
