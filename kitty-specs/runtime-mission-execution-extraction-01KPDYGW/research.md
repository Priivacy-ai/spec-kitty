# Research — Runtime Mission Execution Extraction

**Mission**: `runtime-mission-execution-extraction-01KPDYGW`
**Phase**: 0 — Outline & Research
**Date**: 2026-04-17

This document resolves the five open questions raised in `spec.md` section *Open Questions*. Each decision is grounded in filesystem evidence and cross-referenced to the pinned FRs and constraints.

---

## Q1 — Final canonical runtime package path

### Decision

The canonical runtime package lives at **`src/runtime/`** (top-level, sibling to `src/specify_cli/` and `src/charter/`).

### Rationale

- **Consistency with the charter exemplar (FR-016)**: `src/charter/` is a top-level package and is the pattern this mission mirrors.
- **Ownership-map discipline (#610)**: the upstream ownership map assigns one slice per top-level package. Nesting runtime inside `specify_cli/` would conflate the execution core with the CLI layer, which is exactly the coupling this mission removes.
- **Dependency rules enforcement (FR-008)**: `tests/architectural/test_layer_rules.py` already uses the top-level-package-as-layer convention (`kernel`, `doctrine`, `charter`, `specify_cli`). Adding `runtime` as a peer layer is a one-line change to the landscape fixture. If runtime were nested, pytestarch rules would need new scope semantics.
- **Baseline evidence**: `src/specify_cli/runtime/` already exists as a subpackage (10 modules, 1,842 lines). That path is **part of the extraction scope** — it becomes a deprecation shim when the canonical content moves to top-level `src/runtime/`.

### Alternatives considered

- **Keep `src/specify_cli/runtime/` as canonical** — rejected. Violates the ownership-map top-level-slice convention and leaves runtime tangled with the CLI layer. Also conflicts with FR-001 ("top-level package" language).
- **Use `src/execution/` or `src/core_runtime/`** — rejected. No precedent in the codebase; the term "runtime" is already used in the spec, the #461 epic, and the #610 ownership map.
- **Defer path decision to #610's merge** — rejected. The ownership-map mission plan is being authored in parallel. Both plans pin `src/runtime/` as the working candidate. If #610 ratifies a different path, A1 in the spec covers the amendment and this mission's `occurrence_map.yaml` is patched accordingly before implementation starts.

### Supporting evidence

```
$ ls src/
charter    doctrine    kernel    specify_cli
```

No conflict with existing top-level packages. `src/runtime/` is an unused name.

---

## Q2 — Full enumeration of shim locations

### Decision

Two shim packages, matching the two extraction sources:

1. **`src/specify_cli/next/`** — 4 modules become pure re-export shims:
   - `__init__.py` (17 lines today) — becomes shim `__init__` with `__deprecated__` attributes and `warnings.warn` at module level.
   - `decision.py` (472 lines) — becomes shim that re-exports from `runtime.decisioning.decision`.
   - `prompt_builder.py` (342 lines) — becomes shim that re-exports from `runtime.prompts.builder`.
   - `runtime_bridge.py` (1,087 lines) — becomes shim that re-exports from `runtime.bridge.runtime_bridge`.

2. **`src/specify_cli/runtime/`** — 10 modules become pure re-export shims:
   - `__init__.py` — becomes shim `__init__` with `__deprecated__` attributes and `warnings.warn`.
   - `agent_commands.py` → `runtime.agents.commands`
   - `agent_skills.py` → `runtime.agents.skills`
   - `bootstrap.py` → `runtime.orchestration.bootstrap`
   - `doctor.py` → `runtime.orchestration.doctor`
   - `home.py` → `runtime.discovery.home`
   - `merge.py` → `runtime.orchestration.merge`
   - `migrate.py` → `runtime.orchestration.migrate`
   - `resolver.py` → `runtime.discovery.resolver`
   - `show_origin.py` → `runtime.orchestration.show_origin`

### CLI command modules do NOT become shims

Spec FR-004 says CLI command modules under `src/specify_cli/cli/commands/agent/` and `src/specify_cli/next/` are reduced to thin adapters. The `specify_cli/next/` path is already covered by shim #1 above. For `src/specify_cli/cli/commands/*.py` and `src/specify_cli/cli/commands/agent/*.py`, the import path **persists** (they remain at `specify_cli.cli.commands.*`) — only their bodies shrink. No shim is needed because no import path is deprecated.

### Rationale

- Shims exist to preserve **external Python importers** during the deprecation window. A file whose import path does not move does not need a shim.
- `src/specify_cli/cli/commands/*` paths are owned by the CLI router (`specify_cli.cli.*`). They stay. Their bodies lose decisioning logic (FR-004) but the module paths remain registered in the Typer app.
- `src/specify_cli/next/*` and `src/specify_cli/runtime/*` are the two paths that external scripts, tests, and the community may have imported. Both need shims with `DeprecationWarning` per FR-005.

### Registry entries (FR-006)

Two rows in `architecture/2.x/shim-registry.yaml`:

```yaml
shims:
  - legacy_path: specify_cli.next
    canonical_path: runtime
    removal_release: 3.3.0          # one minor cycle after this mission lands
    owner: runtime-mission-execution-extraction-01KPDYGW
    registered: 2026-04-17
  - legacy_path: specify_cli.runtime
    canonical_path: runtime
    removal_release: 3.3.0
    owner: runtime-mission-execution-extraction-01KPDYGW
    registered: 2026-04-17
```

Actual schema is owned by #615; the keys above mirror what the charter mission installed for `specify_cli.charter`.

### Alternatives considered

- **One consolidated shim under a new `src/specify_cli/_legacy_runtime/`** — rejected. Breaks every existing `from specify_cli.next import …` import site. The charter exemplar kept separate shim files per legacy module; we mirror that.
- **Shim individual CLI command modules** — rejected. Those paths are not being moved; no external importer depends on them as a stable API.

### Supporting evidence

```
$ grep -rn "from specify_cli.next\|import specify_cli.next" src/ tests/ | wc -l
119
```

(109 matches across 9 test files + 10 matches in 3 src files inside `specify_cli/next/` itself. Internal src self-imports get rewritten to relative imports; external test imports migrate via `occurrence_map.yaml` `tests_fixtures: rename`.)

---

## Q3 — Protocol shapes (PresentationSink, ProfileInvocationExecutor, StepContractExecutor)

### Decision

Three Protocols, all in `src/runtime/seams/`, use `typing.Protocol` and `@runtime_checkable`. Full IDL in `contracts/`:

- `contracts/presentation_sink.md` — `PresentationSink` Protocol (FR-013)
- `contracts/profile_invocation_executor.md` — `ProfileInvocationExecutor` Protocol (FR-009)
- `contracts/step_contract_executor.md` — `StepContractExecutor` Protocol (FR-010)

Rough shapes (authoritative version in contracts/):

```python
# src/runtime/seams/presentation_sink.py
from typing import Protocol, runtime_checkable, Mapping, Any

@runtime_checkable
class PresentationSink(Protocol):
    def emit(self, payload: Mapping[str, Any], *, level: str = "info") -> None: ...
    def emit_json(self, payload: Mapping[str, Any]) -> None: ...
    def emit_error(self, message: str, *, exit_code: int = 1) -> None: ...

# src/runtime/seams/profile_invocation_executor.py
from typing import Protocol, runtime_checkable
from runtime.seams.types import ProfileRef, InvocationContext, InvocationResult

@runtime_checkable
class ProfileInvocationExecutor(Protocol):
    def invoke(
        self,
        profile_ref: ProfileRef,
        context: InvocationContext,
    ) -> InvocationResult: ...

# src/runtime/seams/step_contract_executor.py
from typing import Protocol, runtime_checkable
from runtime.seams.types import StepContract, ExecutionContext, StepResult

@runtime_checkable
class StepContractExecutor(Protocol):
    def execute(
        self,
        contract: StepContract,
        context: ExecutionContext,
    ) -> StepResult: ...
```

Supporting type definitions (`ProfileRef`, `InvocationContext`, `InvocationResult`, `StepContract`, `ExecutionContext`, `StepResult`) are declared in `src/runtime/seams/types.py` as `TypedDict`s or frozen `dataclass`es. Data-model document (`data-model.md`) lists their fields.

### Rationale

- **`PresentationSink` (FR-013, C-009)**: runtime needs a way to surface messages without importing `rich.*`. Three methods cover the observed call sites in `specify_cli/next/runtime_bridge.py` (payload emission, JSON emission, error with exit code). `@runtime_checkable` lets CLI adapters `isinstance(sink, PresentationSink)` verify the injection at startup.
- **Seams as Protocols, not ABCs**: charter exemplar uses a mix; Protocol is chosen here because the seam implementers (#461 Phase 4/6) are downstream missions that should not inherit from runtime — they implement in their own packages. Protocol enables structural typing.
- **No implementations in this mission (C-002)**: only Protocol definitions and a minimal stub (for typechecking validation per SC-5) ship. Real implementations land in #461 Phase 4 and Phase 6.

### Alternatives considered

- **Abstract base classes (`abc.ABC`)** — rejected. Forces inheritance, couples downstream missions to runtime.
- **Single `ExecutorProtocol` with discriminated union** — rejected. Blurs the profile-vs-step-contract distinction that #461 Phase 4/6 split.
- **Bundling seams inside `runtime/__init__.py`** — rejected. `seams/` as a subpackage makes the surface explicit and importable as `from runtime.seams import PresentationSink` without pulling the rest of runtime.

### Supporting evidence

```
$ grep -rn "from rich\|import rich" src/specify_cli/next/
(no matches)

$ grep -rn "from rich\|import rich" src/specify_cli/runtime/
(no matches)
```

Runtime subtrees currently have **zero** direct Rich imports. The `PresentationSink` injection seam is therefore a cheap and low-risk install — no existing code has to be unwound.

---

## Q4 — Dependency-rules enforcement (formerly: #395 import-graph infrastructure)

### Decision

**Use existing pytestarch infrastructure.** Extend `tests/architectural/test_layer_rules.py` — no new test file, no new dependency. The closed issue #395 (fragile layer matching) tracked the predecessor problem; its concern is resolved by the pytestarch setup already in the repo and is now an AC of this mission.

### Evidence

```
$ ls tests/architectural/
__init__.py  conftest.py  test_layer_rules.py
```

`tests/architectural/test_layer_rules.py` lines 16-19:

```python
from pytestarch import LayerRule
pytestmark = pytest.mark.architectural

# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# Layer coverage guards (pytestarch — see AC in FR-008)
# ---------------------------------------------------------------------------
```

The file:
- imports `pytestarch.LayerRule` — **#395 import-graph tooling is the already-adopted route**.
- defines `_DEFINED_LAYERS: frozenset = frozenset(["kernel", "doctrine", "charter", "specify_cli"])`.
- has a `landscape` fixture in `conftest.py` (referenced at line 43).
- enforces the documented dependency direction `kernel <- doctrine <- charter <- specify_cli`.

### Decision implications

- Add `"runtime"` to `_DEFINED_LAYERS` in both `conftest.py` and `test_layer_rules.py`.
- Add new `LayerRule` assertions:
  - `runtime` must not import from `specify_cli.cli.*`
  - `runtime` must not import from `rich.*`
  - `runtime` must not import from `typer.*`
  - `runtime` is allowed to import from `kernel`, `doctrine`, `charter` per the ownership-map slice rules.
- Per FR-007, the exact allow/forbid list is published in the #610 ownership map's runtime slice entry. This mission mirrors that list as-is.

### Note on on-disk spelling

Spec section **Requirements FR-008** and **Key Entities** say `tests/architecture/`. Current on-disk path is `tests/architectural/`. This plan uses the existing spelling (`tests/architectural/`) and adds a note to the migration doc for the cleanup to happen later under a grooming mission. Renaming the directory is out of scope here.

### Alternatives considered

- **Write a new `tests/architecture/test_runtime_dependencies.py` standalone pytest** — rejected. Duplicates existing infrastructure. The existing file is the canonical home for layer rules.
- **Use `grimp` or `pydeps` directly** — rejected. `pytestarch` already wraps `grimp` under the hood and is the adopted convention.

---

## Q5 — Runtime-dependent CLI commands needing regression snapshots

### Decision

Four commands get JSON snapshots under `tests/regression/runtime/fixtures/snapshots/`:

1. `spec-kitty next --agent <name> --mission <handle> --json`
2. `spec-kitty implement <WP_ID> --json` (maps to `agent action implement`)
3. `spec-kitty agent action review <WP_ID> --json`
4. `spec-kitty merge <handle> --json`

These are spec-pinned (FR-011).

### Audit of additional commands

| Command module | Invokes `runtime.*` decisioning? | Snapshot needed? |
|---|---|---|
| `cli/commands/next_cmd.py` | Yes (`decide_next`, `query_current_state`, `get_or_start_run`) | Yes (spec-pinned) |
| `cli/commands/implement.py` | Yes | Yes (spec-pinned) |
| `cli/commands/agent/workflow.py` | Yes (`answer_decision_via_runtime`) | Yes (spec-pinned — covers `review` action) |
| `cli/commands/merge.py` | Yes | Yes (spec-pinned) |
| `cli/commands/accept.py` | No — delegates to `status.emit` directly | No |
| `cli/commands/agent/mission.py` (finalize-tasks, setup-plan) | No — uses `tasks_support`, `status.bootstrap` | No |
| `cli/commands/agent/status.py` (tasks status) | No — read-only via `status.reducer` | No |
| `cli/commands/agent/context.py` | No — context resolution, not decisioning | No |
| `cli/commands/dashboard.py` | No | No |
| `cli/commands/doctor.py` | No (diagnostics wrapper; runtime.doctor is data access, not decisioning) | No |
| `cli/commands/sync.py` | No | No |
| `cli/commands/research.py`, `tasks.py`, `materialize.py`, `charter.py`, etc. | No | No |

**Verdict**: the four spec-pinned commands cover the entire decisioning surface. No additional snapshots are required.

### Rationale

Only the four commands that invoke `decide_next()` or the state-transition bridge (`runtime_bridge.answer_decision_via_runtime`, `runtime_bridge.get_or_start_run`) exercise the runtime logic this mission moves. Read-only commands (status, context, dashboard) and setup commands (research, tasks, materialize) go through `status.*` or `tasks_support.*` modules that are not part of the runtime slice.

### Alternatives considered

- **Snapshot every CLI command** — rejected. Over-scopes the regression harness, balloons CI runtime (NFR-001 caps at 30s), and tests modules this mission does not touch.
- **Skip `merge` snapshot** — rejected. Merge is inside the runtime scope (`runtime/merge.py` moves) and exercises execution-layer orchestration. Spec-pinned.

---

## Ancillary notes

### `src/specify_cli/cli/commands/agent/` vs `src/specify_cli/cli/commands/`

The spec says "CLI command modules under `src/specify_cli/cli/commands/agent/` and `src/specify_cli/next/`". The `agent/` subdirectory contains `workflow.py` (where the `review` action lives) plus `mission.py`, `status.py`, `context.py`, `tasks.py`, `config.py`, `tests.py`, `release.py`. Only `workflow.py` embeds runtime decisioning; the others are thin already. So FR-004 touches `workflow.py` + the four top-level command files (`next_cmd.py`, `implement.py`, `merge.py`, plus whichever thin shim lives at `accept.py` if it touches runtime — audit during implementation confirms).

### Bulk-edit scope

`occurrence_map.yaml` enumerates 3 category actions that actually rewrite: `import_paths`, `code_symbols`, `tests_fixtures`. The other 5 categories stay as `do_not_change` or `manual_review`. Exceptions protect the shim files (`src/specify_cli/next/*`, `src/specify_cli/runtime/*`), the migration doc (which intentionally quotes the deprecated paths), and the mission's own planning artefacts (which quote `specify_cli.next` / `specify_cli.runtime` as the subject of the rename).

### `runtime_bridge.py` size

At 1,087 lines, `runtime_bridge.py` is the largest file being moved. Plan keeps it as a single module at `runtime/bridge/runtime_bridge.py` during this mission (move, not split). A follow-up grooming mission may split it; that is out of scope here (C-001: no semantic changes).

### Existing tests that reference `specify_cli.next`

109 occurrences across 9 test files. All migrate via `occurrence_map.yaml` `tests_fixtures: rename`. Exceptions:

- Any test that specifically verifies shim behaviour (e.g., `test_shim_deprecation.py` — to be created in WP under Phase 4) imports via the legacy path **by design** and is added to `occurrence_map.yaml` exceptions list.

---

## Summary

All five plan-phase open questions resolved. No NEEDS CLARIFICATION markers remain. Phase 1 (data model, contracts, quickstart) proceeds on the basis of these decisions.
