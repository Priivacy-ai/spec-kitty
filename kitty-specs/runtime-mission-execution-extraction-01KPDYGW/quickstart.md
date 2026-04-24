# Quickstart: Navigating `src/runtime/`

**Mission**: `runtime-mission-execution-extraction-01KPDYGW`
**Audience**: Contributors opening `src/runtime/` for the first time after the extraction

---

## What Moved Where

| Old path (deprecated) | New canonical path | Purpose |
|---|---|---|
| `specify_cli.next.decision` | `runtime.decisioning.decision` | `decide_next`, `Decision`, `DecisionKind` |
| `specify_cli.next.runtime_bridge` | `runtime.bridge.runtime_bridge` | `RuntimeBridge`, mission orchestration |
| `specify_cli.next.prompt_builder` | `runtime.prompts.builder` | Prompt assembly for agent handoff |
| `specify_cli.runtime.home` | `runtime.discovery.home` | `get_kittify_home`, `get_package_asset_root` |
| `specify_cli.runtime.resolver` | `runtime.discovery.resolver` | `resolve_mission`, `resolve_command`, `resolve_template` |
| `specify_cli.runtime.agent_commands` | `runtime.agents.commands` | Agent command dispatch |
| `specify_cli.runtime.agent_skills` | `runtime.agents.skills` | Skill resolution |
| `specify_cli.runtime.bootstrap` | `runtime.orchestration.bootstrap` | `ensure_runtime`, `check_version_pin` |
| `specify_cli.runtime.doctor` | `runtime.orchestration.doctor` | Diagnostics |
| `specify_cli.runtime.merge` | `runtime.orchestration.merge` | Merge orchestration |
| `specify_cli.runtime.migrate` | `runtime.orchestration.migrate` | Migration orchestration |
| `specify_cli.runtime.show_origin` | `runtime.orchestration.show_origin` | `OriginEntry`, `collect_origins` |

The old paths still work (via deprecation shim) until 3.4.0. Use the canonical paths for all new code.

---

## Package Layout

```
src/runtime/
├── __init__.py           ← public API: PresentationSink, StepContractExecutor, ProfileInvocationExecutor
├── seams/                ← Protocol interfaces (no impl)
│   ├── presentation_sink.py        ← output abstraction (FR-013)
│   ├── step_contract_executor.py   ← Phase 6 seam (FR-010)
│   ├── profile_invocation_executor.py  ← Phase 4 boundary alias (FR-009)
│   └── _null_sink.py               ← no-op for tests
├── decisioning/          ← state-transition decisioning (was next/decision.py)
│   └── decision.py
├── bridge/               ← runtime orchestration bridge (was next/runtime_bridge.py)
│   └── runtime_bridge.py
├── prompts/              ← prompt composition (was next/prompt_builder.py)
│   └── builder.py
├── discovery/            ← mission/asset discovery (was runtime/home.py + resolver.py)
│   ├── home.py
│   └── resolver.py
├── agents/               ← agent dispatch + skill resolution
│   ├── commands.py
│   └── skills.py
└── orchestration/        ← merge/migrate/bootstrap/doctor/origin
    ├── bootstrap.py
    ├── doctor.py
    ├── merge.py
    ├── migrate.py
    └── show_origin.py
```

---

## Dependency Rules

`src/runtime/` **must not** import from:
- `specify_cli.cli.*` — CLI layer; no presentation logic in runtime
- `rich.*` — use `PresentationSink` instead
- `typer.*` — CLI framework; not a runtime concern

`src/runtime/` **may** import from:
- `charter.*` — governance context retrieval
- `doctrine.*` — doctrine artifact access
- `specify_cli.status.*` — lane state reading
- `specify_cli.invocation.*` — profile invocation (via the seam alias)
- `specify_cli.glossary.*` — terminology validation

These rules are enforced by `tests/architectural/test_layer_rules.py::TestRuntimeBoundary`.

---

## Adding a New Runtime Feature

1. Identify which subpackage owns the new feature (decisioning / bridge / discovery / agents / orchestration).
2. Add your module to the appropriate subpackage. Update the subpackage `__init__.py`.
3. If the feature surfaces output to the user: inject `PresentationSink` as a parameter with `NullSink()` default — never import Rich directly.
4. Add the new symbol to `src/runtime/__init__.py` if it is part of the public API.
5. Run `mypy --strict src/runtime/` and `pytest tests/architectural/` before opening a PR.

---

## Migrating Old Imports

```python
# Old (deprecated — works until 3.4.0 via shim, emits DeprecationWarning):
from specify_cli.next.decision import decide_next
from specify_cli.runtime.home import get_kittify_home

# New (canonical):
from runtime.decisioning.decision import decide_next
from runtime.discovery.home import get_kittify_home
```

See `docs/migration/runtime-extraction.md` for the full translation table.
