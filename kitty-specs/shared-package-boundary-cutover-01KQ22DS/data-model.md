# Data Model: Shared Package Boundary Cutover

**Mission**: `shared-package-boundary-cutover-01KQ22DS`
**Date**: 2026-04-25

This document models the structural state of the cutover: what exists pre-cutover,
what exists post-cutover, and the call-graph between CLI modules and external
packages. There is no on-disk data-schema change in this mission — every model below
is a Python-import / module-graph model.

---

## 1. Package boundaries

### 1.1 Pre-cutover (current state on `main`)

```
+--------------------------------------------------------------+
|                          spec-kitty CLI                      |
|                                                              |
|  src/specify_cli/                                            |
|  ├── next/                                                   |
|  │   ├── runtime_bridge.py  ──┐                              |
|  │   └── ...                  │                              |
|  ├── cli/commands/            │ from spec_kitty_runtime ...  |
|  │   └── next_cmd.py        ──┘                              |
|  ├── decisions/                                              |
|  │   └── emit.py     ──┐                                     |
|  ├── glossary/         │ from specify_cli.spec_kitty_events  |
|  │   └── events.py     │ (vendored copy)                     |
|  ├── sync/             │                                     |
|  │   └── diagnose.py  ─┘                                     |
|  ├── tracker/          ──> from spec_kitty_tracker ... (PyPI)|
|  │                                                           |
|  └── spec_kitty_events/      <-- VENDORED COPY in production |
|       ├── models.py             package path                 |
|       ├── decisionpoint.py                                   |
|       └── ... (full events tree)                             |
+--------------------------------------------------------------+
                             │
                             │  RUNTIME-ONLY DEPENDENCY
                             │  (not in pyproject.toml,
                             │   but required at import time)
                             ▼
+--------------------------------------------------------------+
|       spec-kitty-runtime  (standalone PyPI package, retiring)|
|       0.4.3                                                  |
|                                                              |
|       spec_kitty_runtime.{engine, planner, schema, ...}      |
+--------------------------------------------------------------+

Other PyPI packages used:
- spec-kitty-events 4.0.0  (committed via [tool.uv.sources] editable = true,
                             but vendored copy is the actual import target)
- spec-kitty-tracker 0.4.2  (consumed correctly via spec_kitty_tracker.*)
```

**Hybrid-state failure modes (the reasons PR #779 was rejected):**

1. `pyproject.toml` does not list `spec-kitty-runtime`, but production code
   imports it. CI in a clean venv fails with `ModuleNotFoundError`.
2. `[tool.uv.sources]` for events makes local installs work via an editable
   path, but published wheels do not have that override; users get a different
   resolution.
3. The vendored events tree is the actual runtime target, but the public PyPI
   package is also pinned in `pyproject.toml`. Two different events surfaces
   coexist; nothing guarantees they agree.
4. `constraints.txt` paper-overs a transitive pin conflict between
   `spec-kitty-runtime`'s `spec-kitty-events<4.0` and the CLI's `==4.0.0`.

### 1.2 Post-cutover (target state)

```
+--------------------------------------------------------------+
|                          spec-kitty CLI                      |
|                                                              |
|  src/specify_cli/                                            |
|  ├── next/                                                   |
|  │   ├── _internal_runtime/         <-- NEW, CLI-OWNED       |
|  │   │    ├── __init__.py           re-exports public surface|
|  │   │    ├── models.py                                      |
|  │   │    ├── emitter.py                                     |
|  │   │    ├── lifecycle.py                                   |
|  │   │    ├── engine.py                                      |
|  │   │    ├── planner.py                                     |
|  │   │    └── schema.py                                      |
|  │   ├── runtime_bridge.py   <-- imports _internal_runtime   |
|  │   └── ...                                                 |
|  ├── cli/commands/                                           |
|  │   └── next_cmd.py         <-- imports _internal_runtime   |
|  ├── decisions/                                              |
|  │   └── emit.py        ──┐                                  |
|  ├── glossary/            │ from spec_kitty_events.* (PyPI)  |
|  │   └── events.py        │                                  |
|  ├── sync/                │                                  |
|  │   └── diagnose.py    ──┘                                  |
|  └── tracker/             ──> from spec_kitty_tracker.* (PyPI)|
|                                                              |
|  (src/specify_cli/spec_kitty_events/  <-- DELETED)           |
+--------------------------------------------------------------+
        │                                          │
        │ external PyPI dep                        │ external PyPI dep
        ▼                                          ▼
+----------------------------+         +-------------------------------+
|  spec-kitty-events         |         |  spec-kitty-tracker           |
|  >=4.0.0,<5.0.0  (PyPI)    |         |  >=0.4,<0.5  (PyPI)           |
|                            |         |                               |
|  spec_kitty_events.*       |         |  spec_kitty_tracker.*         |
+----------------------------+         +-------------------------------+

NO dependency on spec-kitty-runtime.  Nothing in the CLI imports it.
```

**Post-cutover invariants:**

1. `pip install spec-kitty-cli` in a fresh venv installs everything needed.
   `spec-kitty next` runs against a fixture mission without any pre-install of
   `spec-kitty-runtime`.
2. There are no `[tool.uv.sources]` editable / path entries committed in
   `pyproject.toml` for events, tracker, or runtime.
3. There is no `src/specify_cli/spec_kitty_events/` tree on disk.
4. `pyproject.toml` lists events / tracker via compatibility ranges, not exact
   pins. Exact pins live only in `uv.lock`.
5. `constraints.txt` is removed.

---

## 2. Module rewrites

### 2.1 Production source files modified

| File | Change | Reference |
|------|--------|-----------|
| `src/specify_cli/next/runtime_bridge.py` | Replace lines 28..38 (top-level imports) and 4 lazy imports (lines 560, 736, 737, 858) — `from spec_kitty_runtime ...` → `from specify_cli.next._internal_runtime ...` | FR-001, FR-002 |
| `src/specify_cli/cli/commands/next_cmd.py` | Replace 1 lazy import (line 227) — `from spec_kitty_runtime.engine import _read_snapshot` → `from specify_cli.next._internal_runtime.engine import _read_snapshot` | FR-002 |
| `src/specify_cli/decisions/emit.py` | Replace 2 imports (lines 34, 40) — `from specify_cli.spec_kitty_events.decisionpoint import ...` and `from specify_cli.spec_kitty_events.decision_moment import ...` → `from spec_kitty_events.decisionpoint ...` and `from spec_kitty_events.decision_moment ...` | FR-004, FR-018 |
| `src/specify_cli/glossary/events.py` | Replace any `from specify_cli.spec_kitty_events ...` imports with `from spec_kitty_events ...` | FR-004, FR-018 |
| `src/specify_cli/sync/diagnose.py` | Replace 1 import (line 20) — `from specify_cli.spec_kitty_events.models import Event` → `from spec_kitty_events import Event` | FR-004, FR-018 |

### 2.2 Production source paths deleted

| Path | Reason |
|------|--------|
| `src/specify_cli/spec_kitty_events/` (entire tree) | Vendored events copy; replaced by external PyPI package consumption (FR-003). |

### 2.3 Production source paths added

| Path | Purpose |
|------|---------|
| `src/specify_cli/next/_internal_runtime/__init__.py` | Public re-export surface — what `runtime_bridge.py` and `next_cmd.py` import. |
| `src/specify_cli/next/_internal_runtime/models.py` | `DiscoveryContext`, `MissionPolicySnapshot`, `MissionRunRef`, `NextDecision`. |
| `src/specify_cli/next/_internal_runtime/emitter.py` | `NullEmitter` and the runtime emitter Protocol. |
| `src/specify_cli/next/_internal_runtime/lifecycle.py` | `next_step`, `provide_decision_answer`, `start_mission_run`. |
| `src/specify_cli/next/_internal_runtime/engine.py` | `_read_snapshot` and snapshot persistence. |
| `src/specify_cli/next/_internal_runtime/planner.py` | `plan_next` and the DAG planner. |
| `src/specify_cli/next/_internal_runtime/schema.py` | `ActorIdentity`, `load_mission_template_file`, `MissionRuntimeError`. |

### 2.4 Test files rewritten

| File | Change |
|------|--------|
| `tests/next/test_runtime_bridge_unit.py` | Imports of `spec_kitty_runtime` (lines 14, 305, 306, 343, 344, 426, 583) rewritten to `specify_cli.next._internal_runtime`. Behavior expectations unchanged. |
| `tests/next/test_decision_unit.py` | Imports (lines 120, 121, 163) rewritten. |
| `tests/next/test_next_command_integration.py` | Imports (lines 164, 165, 202, 593) rewritten. |
| `tests/specify_cli/cli/commands/test_charter_decision_integration.py` | `specify_cli.spec_kitty_events.*` imports rewritten to `spec_kitty_events.*`. |
| `tests/specify_cli/decisions/test_emit.py` | Same as above. |
| `tests/contract/test_handoff_fixtures.py` | Same as above. |

### 2.5 Test files added

| Path | Purpose |
|------|---------|
| `tests/architectural/test_shared_package_boundary.py` | `pytestarch` rules enforcing C-001 (no `spec_kitty_runtime` production imports), C-002 (no vendored events tree), and C-005 (no committed editable sources for events / tracker). |
| `tests/contract/spec_kitty_events_consumer/test_consumer_contract.py` | Pins the events public-surface subset CLI uses; fails on upstream contract change. |
| `tests/contract/spec_kitty_tracker_consumer/test_consumer_contract.py` | Pins the tracker public-surface subset CLI uses; fails on upstream contract change. |
| `tests/contract/test_packaging_no_vendored_events.py` | Builds the wheel and asserts no `specify_cli/spec_kitty_events/` paths in it. |
| `tests/integration/test_clean_install_next.py` | `@pytest.mark.distribution`-gated local-runnable clean-install test. |

### 2.6 Test fixtures added

| Path | Purpose |
|------|---------|
| `tests/fixtures/runtime_parity/` | Golden JSON snapshots from `spec-kitty-runtime` 0.4.3 against the reference fixture mission, captured during WP01. |
| `tests/fixtures/clean_install_fixture_mission/` | Smallest possible mission scaffold for the clean-install verification job. |

### 2.7 Configuration files modified

| File | Change |
|------|--------|
| `pyproject.toml` | (a) Replace `spec-kitty-events==4.0.0` with `spec-kitty-events>=4.0.0,<5.0.0`. (b) Replace `spec-kitty-tracker==0.4.2` with `spec-kitty-tracker>=0.4,<0.5`. (c) Remove the explanatory comment about `spec-kitty-runtime` not being listed (now that there is no vendored events tree, the constraint no longer needs explanation). (d) Remove `[tool.uv.sources]` editable entry for `spec-kitty-events`. |
| `uv.lock` | Regenerated against new `pyproject.toml`. |
| `constraints.txt` | Deleted. |
| `.github/workflows/ci-quality.yml` | New `clean-install-verification` job. |
| `.github/workflows/protect-main.yml` | Add `clean-install-verification` to required checks. |
| `.github/workflows/check-spec-kitty-events-alignment.yml` | Drift checks updated to reflect new compatible-range model (no exact-pin gate). |
| `CHANGELOG.md` | Operator-facing entry documenting the cutover. |
| `README.md` | Install instructions updated; remove any "also install spec-kitty-runtime" guidance. |
| `CLAUDE.md` | Note that the CLI owns its runtime; events / tracker are external PyPI deps. |
| `docs/development/mission-next-compatibility.md` | Marked historical; cross-link to migration doc. |
| `docs/development/mutation-testing-findings.md` | References to "transitive `spec-kitty-runtime`" updated. |
| `docs/migration/shared-package-boundary-cutover.md` | New operator runbook (created by WP10). |
| `docs/development/local-overrides.md` | New: how to use editable cross-package work without committing overrides. |

---

## 3. Call graph (post-cutover)

```
spec-kitty next --agent <name> --mission <handle>
        │
        ▼
specify_cli.cli.commands.next_cmd
        │ imports
        ▼
specify_cli.next.runtime_bridge
        │ imports
        ▼
specify_cli.next._internal_runtime
        ├── lifecycle.next_step
        ├── lifecycle.start_mission_run
        ├── engine._read_snapshot
        ├── planner.plan_next
        └── schema.{ActorIdentity, load_mission_template_file}
                │
                │ persists snapshot
                ▼
        .kittify/runtime/runs/<run_id>/

For event emission:
specify_cli.{decisions, glossary, sync}.* ──> spec_kitty_events.* (PyPI)
For tracker integration:
specify_cli.tracker.* ──> spec_kitty_tracker.* (PyPI)
```

No production code path imports `spec_kitty_runtime`.

---

## 4. State transitions

The cutover is an atomic landing on `main`. The intermediate states the WP graph
moves through are deliberately *not* visible on `main`:

```
state-0  pre-cutover (current main)
   │
   │ WP01 lands on lane A (internalized runtime exists alongside spec_kitty_runtime imports)
   ▼
state-1  WP01 done, lane A pre-cutover
   │
   │ WP02 lands on lane A (cutover of imports)
   ▼
state-2  lane A complete; lane B WPs may run in parallel
   │
   │ WP04..WP06 land on lane B (events cutover)
   ▼
state-3  both lanes complete
   │
   │ WP07..WP10 land sequentially
   ▼
state-4  POST-CUTOVER (target main)
```

State-1 / state-2 / state-3 only exist on the per-WP feature branches. The single
landing PR collapses them all to state-4 atomically against `main`. C-007 is
enforced by lane discipline + the merge preflight check.

---

## 5. Negative-space invariants (what must NOT exist post-cutover)

These are the assertions the new architectural test enforces:

| ID | Invariant | Enforcement |
|----|-----------|-------------|
| NS-1 | No production module under `src/` imports any symbol from `spec_kitty_runtime` (top-level, sub-module, lazy). | `pytestarch` rule in `tests/architectural/test_shared_package_boundary.py` |
| NS-2 | The path `src/specify_cli/spec_kitty_events/` does not exist. | `tests/contract/test_packaging_no_vendored_events.py` (filesystem assertion) and the same `pytestarch` test (no module references `specify_cli.spec_kitty_events`). |
| NS-3 | `pyproject.toml` `[project.dependencies]` does not list `spec-kitty-runtime`. | A `tests/architectural/test_pyproject_shape.py` assertion (added in WP08). |
| NS-4 | `pyproject.toml` `[tool.uv.sources]` does not list a `path` or `editable` entry for `spec-kitty-events` or `spec-kitty-tracker`. | Same `pyproject_shape` assertion. |
| NS-5 | The built wheel does not contain `specify_cli/spec_kitty_events/`. | `tests/contract/test_packaging_no_vendored_events.py` (wheel ZIP scan). |
| NS-6 | Running `pip install` of the built wheel in a fresh venv does not install `spec-kitty-runtime` as a transitive dep. | Clean-install CI job in `ci-quality.yml`. |

---

## 6. References

- `spec.md` — functional and non-functional requirements.
- `research.md` — architectural decisions.
- `contracts/internal_runtime_surface.md` — exact symbol-level contract for the
  internalized runtime.
- `contracts/events_consumer_surface.md` — exact symbol-level contract CLI uses
  from events.
- `contracts/tracker_consumer_surface.md` — exact symbol-level contract CLI
  uses from tracker.
- `quickstart.md` — how to verify the cutover locally.
