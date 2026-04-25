# Migration Guide: Runtime Extraction (3.2.x → 3.4.0)

## Why This Migration Exists

In mission `runtime-mission-execution-extraction-01KPDYGW`, the Spec Kitty execution core was
extracted from two internal sub-packages — `specify_cli.next` and `specify_cli.runtime` — into a
canonical top-level `runtime` package under `src/runtime/`. The motivation is architectural
clarity: the runtime layer must not depend on the CLI layer, and the old locations buried
mission-orchestration and decisioning logic inside the CLI package tree where presentation
concerns leaked in through `rich` imports.

**The API is identical.** No function signatures, class shapes, or type contracts changed.
Only the import path changed. If you see a `DeprecationWarning` from either of the legacy
namespaces, updating the import is the entire migration — no further code changes are required.
Legacy shim paths will continue to work throughout the 3.2.x and 3.3.x release lines; they are
removed in 3.4.0.

---

## What Changed

| Legacy import path | Canonical import path | What it exports |
|---|---|---|
| `specify_cli.next.decision` | `runtime.decisioning.decision` | `decide_next`, `Decision`, `DecisionKind` |
| `specify_cli.next.runtime_bridge` | `runtime.bridge.runtime_bridge` | `RuntimeBridge`, mission orchestration |
| `specify_cli.next.prompt_builder` | `runtime.prompts.builder` | `build_prompt` (prompt assembly for agent handoff) |
| `specify_cli.runtime.home` | `runtime.discovery.home` | `get_kittify_home`, `get_package_asset_root` |
| `specify_cli.runtime.resolver` | `runtime.discovery.resolver` | `resolve_mission`, `resolve_command`, `resolve_template`, `ResolutionResult`, `ResolutionTier` |
| `specify_cli.runtime.agent_commands` | `runtime.agents.commands` | Agent command dispatch (same public API) |
| `specify_cli.runtime.agent_skills` | `runtime.agents.skills` | Skill resolution (same public API) |
| `specify_cli.runtime.bootstrap` | `runtime.orchestration.bootstrap` | `ensure_runtime`, `check_version_pin` |
| `specify_cli.runtime.doctor` | `runtime.orchestration.doctor` | Diagnostics (same public API) |
| `specify_cli.runtime.merge` | `runtime.orchestration.merge` | Merge orchestration (same public API) |
| `specify_cli.runtime.migrate` | `runtime.orchestration.migrate` | `AssetDisposition`, `MigrationReport`, `classify_asset`, `execute_migration` |
| `specify_cli.runtime.show_origin` | `runtime.orchestration.show_origin` | `OriginEntry`, `collect_origins` |

---

## How to Migrate

### Quick search-and-replace

Run these in the root of your project to catch the most common patterns:

```bash
# Find all legacy imports
rg -n "from specify_cli\.(next|runtime)\." --type py

# Batch-replace the specify_cli.next namespace
sed -i 's/from specify_cli\.next\.decision/from runtime.decisioning.decision/g' $(rg -l "specify_cli.next.decision" --type py)
sed -i 's/from specify_cli\.next\.runtime_bridge/from runtime.bridge.runtime_bridge/g' $(rg -l "specify_cli.next.runtime_bridge" --type py)
sed -i 's/from specify_cli\.next\.prompt_builder/from runtime.prompts.builder/g' $(rg -l "specify_cli.next.prompt_builder" --type py)

# Batch-replace the specify_cli.runtime namespace
sed -i 's/from specify_cli\.runtime\.home/from runtime.discovery.home/g' $(rg -l "specify_cli.runtime.home" --type py)
sed -i 's/from specify_cli\.runtime\.resolver/from runtime.discovery.resolver/g' $(rg -l "specify_cli.runtime.resolver" --type py)
sed -i 's/from specify_cli\.runtime\.bootstrap/from runtime.orchestration.bootstrap/g' $(rg -l "specify_cli.runtime.bootstrap" --type py)
```

### Before / after examples

**Decisioning (most common call site):**

```python
# Before (deprecated — emits DeprecationWarning):
from specify_cli.next.decision import decide_next, Decision

# After (canonical):
from runtime.decisioning.decision import decide_next, Decision
```

**Home / asset discovery:**

```python
# Before:
from specify_cli.runtime.home import get_kittify_home, get_package_asset_root

# After:
from runtime.discovery.home import get_kittify_home, get_package_asset_root
```

**Mission resolution:**

```python
# Before:
from specify_cli.runtime.resolver import resolve_mission, ResolutionResult

# After:
from runtime.discovery.resolver import resolve_mission, ResolutionResult
```

**Bootstrap and doctor:**

```python
# Before:
from specify_cli.runtime.bootstrap import ensure_runtime, check_version_pin
from specify_cli.runtime.doctor import run_doctor_checks  # example symbol

# After:
from runtime.orchestration.bootstrap import ensure_runtime, check_version_pin
from runtime.orchestration.doctor import run_doctor_checks
```

---

## Deprecation Timeline

- **3.2.x (current)**: Legacy paths (`specify_cli.next.*`, `specify_cli.runtime.*`) emit a single
  `DeprecationWarning` per process on first import, pointing at the caller.
  `runtime.*` is the canonical path — use it for all new code.
- **3.3.x**: Shim paths remain; second and final warning cycle before removal.
- **3.4.0**: Legacy shim paths are removed entirely (governed by `shim-registry.yaml`
  `removal_release: "3.4.0"`). Imports from the old paths will raise `ModuleNotFoundError`.

**If you need to silence the warning temporarily while you migrate:**

```python
import warnings
warnings.filterwarnings(
    "ignore",
    message=r"specify_cli\.(next|runtime) is deprecated.*",
    category=DeprecationWarning,
)
```

Prefer migrating over filtering — the filter will stop working in 3.4.0 because the shim modules
will no longer exist.

---

## New in This Release: Seam Protocols

`src/runtime/seams/` provides three typed Protocol interfaces that govern the runtime boundary:

- **`PresentationSink`** — output abstraction with `write_line`, `write_status`, and `write_json`
  methods. Inject this instead of using `rich.*` directly inside runtime code; CLI adapters supply
  the Rich-backed implementation at call time.
- **`StepContractExecutor`** — Phase 6 execution seam (tracking issue [#461]). The Protocol
  shape is fixed now; the concrete implementation arrives in Phase 6.
- **`ProfileInvocationExecutor`** — boundary alias for the Phase 4 executor in
  `specify_cli.invocation.executor`; accessible via
  `src/runtime/seams/profile_invocation_executor.py`.

External callers almost never need to reference these Protocols directly — they exist so that
runtime internals can remain decoupled from Rich and Typer. If you are writing a custom runtime
adapter or a plugin that hooks into the execution layer, these are the interfaces to implement.

---

## Questions?

- Tracking issue: [#612](https://github.com/Priivacy-ai/spec-kitty/issues/612)
- Shim-registry contract: [#615](https://github.com/Priivacy-ai/spec-kitty/issues/615)
- Ownership map: `architecture/2.x/05_ownership_manifest.yaml`
- Architectural boundary tests: `tests/architectural/test_layer_rules.py::TestRuntimeBoundary`
