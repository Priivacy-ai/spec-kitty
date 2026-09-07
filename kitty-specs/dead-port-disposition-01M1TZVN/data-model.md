# Data Model: Dead-Port Disposition

**Mission**: `dead-port-disposition-01M1TZVN` · **Date**: 2026-09-06
**Scope**: this mission has no persistent data; its "entities" are the module inventory being retired/retained, the gate-pin ledger that must move in lockstep, and the residue table. All line numbers verified at HEAD `ba58652f0`.

## 1. `specify_cli.mission_v1` — module inventory (FULL extent, OD1)

| Module | LOC | Production importers | Disposition |
|---|---|---|---|
| `__init__.py` | 154 | (package) | **Rewrite**: drop eager imports `:20-29`; re-export `emit_event`, `read_events` only; delete `MissionProtocol`, `load_mission`, `load_mission_by_name` dispatch; new docstring (no DSL advertising). |
| `events.py` | 93 | `runtime/next/next_invocation_lifecycle.py:332` (`emit_event`), `runtime/next/decision.py:200` (`read_events`, until WP04) | **Keep unchanged.** |
| `compat.py` | 158 | none (`from transitions import Machine` `:23`) | **Delete.** |
| `runner.py` | 252 | none (`from transitions import …` `:15-16`) | **Delete.** |
| `guards.py` | 382 | none (docstring citations in `review/gate_registry.py:7,132`; fold-gate entry) | **Delete**; re-point docstrings at git history; drop fold-gate entry. |
| `schema.py` | 299 | tests only (`tests/research/test_research_plan_missions_integration.py:21`, `tests/missions/test_mission_software_dev_integration.py:21`); docstring mention in `skills/manifest_store.py:27` | **Delete**; trim the two tests' schema-validation halves; fix the docstring mention. |

**Invariant M-1**: after WP01, `grep -rn "^from transitions\|^import transitions\|from transitions import" src/` returns nothing.
**Invariant M-2** (NFR-001): subprocess `import specify_cli.mission_v1.events` ⇒ `transitions` ∉ `sys.modules` ∧ `six` ∉ `sys.modules`.

## 2. Gate-pin ledger (NFR-003 — every row moves in the same WP as its deletion)

| Gate | Location | Today | After |
|---|---|---|---|
| dead-symbol pins | `tests/architectural/test_no_dead_symbols.py:720-727` (`MissionProtocol`, `load_mission`, `load_mission_by_name`) | 3 pins | removed (WP01) |
| dead-symbol pin (drift D-1) | `test_no_dead_symbols.py:3278` (`mission_v1.schema::strip_v1_keys`) | 1 pin | removed (WP01) |
| coverage shard row | `tests/architectural/_gate_coverage.py:1456` (`"mission_v1": … ("tests/specify_cli/mission_v1",)`) | present | stays (dir keeps `test_mission_v1_events_unit.py` trimmed + new `test_import_hygiene.py`); verify the gate's directory-nonempty rule (WP01) |
| fold-gate entry | `tests/specify_cli/test_wp_frontmatter_fold.py:60` | `("specify_cli.mission_v1.guards", "read_wp_frontmatter")` | removed (WP01) |
| runtime ledger | `tests/architectural/test_layer_rules.py:194` (`"mission_v1"`) | present | **stays** (live edge via `next_invocation_lifecycle.py:332`) |
| stale exclusion | `tests/architectural/test_layer_rules.py:65-73` (`"constitution"`) | present | removed (WP03) |
| pyproject shape | `tests/architectural/test_pyproject_shape.py` | passes | passes (dependency line removed; wheel packages unchanged unless `team_projection` is listed — WP03 checks) |
| dead-symbol re-pins for demotions | `test_no_dead_symbols.py` (13 entries) | pinned as exports | re-pinned as demoted (WP03, out-of-map, after WP01) |
| parity oracle | `tests/runtime/test_bridge_parity.py:1131-1152` | asserts `sync_emitter` sink reached | **untouched** (shrunk variant) |

## 3. Pack DSL blocks (OD3)

| File | Block | Disposition |
|---|---|---|
| `packs/built-in/missions/software-dev/mission.yaml` | `states:` / `transitions:` | delete (WP01) |
| `packs/built-in/missions/plan/mission.yaml` | same | delete |
| `packs/built-in/missions/research/mission.yaml` | same | delete |
| `src/specify_cli/mission.py:59-67` `MISSION_COMPAT_IGNORED_FIELDS` + `:260-261` | tolerance for the keys | **keep**; comment names the retired DSL and the third-party-override rationale |

## 4. Glossary registration contract (OD5 (a))

| Site | Today (fiction) | After |
|---|---|---|
| `src/kernel/glossary_runner.py:14-16` | "`specify_cli` calls `register()` at import time" | "The consumer (`charter.offering.missions.glossary_hook`) lazily self-bootstraps: `get_runner()` → `None` → `import_module("glossary.attachment")` → `register(GlossaryAwarePrimitiveRunner)` → retry." |
| `src/kernel/glossary_runner.py:33-38` | provider usage block naming `specify_cli` | usage block shows the self-bootstrap; dependency diagram updated to `doctrine → kernel ← charter.offering (lazy) ← glossary` |
| `src/charter/offering/missions/glossary_hook.py:16-17` | "registered … by `specify_cli` at startup" | documents its own bootstrap at `:127-137`; `.. note::` for FR-020 |
| `src/kernel/README.md:18` | "`glossary` registers … at import time" | self-bootstrap sentence |
| `src/kernel/__init__.py:38-42` | same as README | same |

**Invariant G-1** (SC-004): `grep -n "at import time\|at startup\|registers the concrete" src/kernel/glossary_runner.py src/kernel/__init__.py src/kernel/README.md src/charter/offering/missions/glossary_hook.py` → zero matches describing registration-by-`specify_cli`/`glossary`.
**Invariant G-2** (FR-009): fresh process, `clear_registry()`, run `execute_with_glossary(...)` ⇒ `get_runner()` is a `GlossaryAwarePrimitiveRunner` instance.
**Degradation rule**: `execute_with_glossary` runs the primitive directly only when `import_module("glossary.attachment")` raises `ImportError`.

## 5. Residue table (OD8)

| Item | Files | Action | WP |
|---|---|---|---|
| `constitution` exclusion | `tests/architectural/test_layer_rules.py:65-73` | delete | WP03 |
| `team_projection/` tombstone | `src/specify_cli/team_projection/__init__.py` (only file) | delete package; bans at `test_no_retired_subsystems.py:39-40,99-100` and `pyproject.toml` TID251 stay (they assert absence) | WP03 |
| `ActionContext` alias | `src/mission_runtime/context.py:338,:342`; `src/mission_runtime/__init__.py:127,:139-142` | delete alias + `__all__` entry + `__getattr__` branch | WP03 |
| 13 test-only `__all__` exports | `src/mission_runtime/__init__.py` re-export set; `mission_runtime/lifecycle_phase.py::content_present_at_primary_tip`; `kernel/paths.py::get_packs_root_default` | **demote** from package `__all__` (never delete; in-package callers at `mission_runtime/resolution.py:52`, `kernel/env_expand.py:63`); re-pin in `test_no_dead_symbols.py` | WP03 |
| emitter docstring | `src/runtime/next/event_emitter.py:1-10` | point at the real E3 seam (`status/adapters.py:364-366`); no code change | WP03 |
| FR-011 record | `kitty-specs/dead-port-disposition-01M1TZVN/research/emitter-adr-inputs.md` | extract dossier §3 verbatim + verification log | WP03 |
| dead DSL readers | `src/runtime/next/decision.py:187-235` (`derive_mission_state`, `evaluate_guards`); `tests/next/test_decision_unit.py:28,189-219` | delete (after Mission A merges) | WP04 |

## 6. Externally visible events / behaviour changes

None. `emit_event` payloads, the `MissionNextInvoked` observability write, glossary execution semantics, and every emitter signature are unchanged. The only observable difference is the absence of `transitions`/`six` from `sys.modules` and from the installed dependency set.
