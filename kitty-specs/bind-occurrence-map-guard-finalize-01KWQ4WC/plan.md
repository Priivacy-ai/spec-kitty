# Implementation Plan: Bind Occurrence-Map Guard at Finalize

**Branch**: `feat/bind-occurrence-map-guard-finalize` | **Date**: 2026-07-04 | **Spec**: [spec.md](./spec.md)
**Input**: Mission specification from `kitty-specs/bind-occurrence-map-guard-finalize-01KWQ4WC/spec.md`

## Summary

Make a bulk-edit mission fail at the **plan-completion / pre-implement boundary** (not at the first `implement WP##`) when its `occurrence_map.yaml` is missing, schema-invalid, or inadmissible — by **reusing the existing `ensure_occurrence_classification_ready` check** (no new validation logic), conditioned on stored `change_mode == "bulk_edit"`. Implement-time enforcement remains as a backstop.

### Surface Decision (resolves spec C-005)

A dedicated code-truth investigation (evidence in [research.md](./research.md)) established that the enforcement surface the issue *implies* does not exist and the one it *names* is dead:

- **`mission.yaml` transition `conditions` (the naïve "bind the guard" reading) is a DEAD surface.** The only interpreter of those conditions is `evaluate_guards` (`src/runtime/next/decision.py:204-266`), explicitly documented as "no longer called by `decide_next`" (`decision.py:14-16`). The whole `mission_v1` `GUARD_REGISTRY` / `compile_guards` / registered `occurrence_map_complete` path has **no live (non-test) consumer**. The live `decide_next` delegates to `runtime_bridge.decide_next_via_runtime`, which enforces step boundaries with **hand-rolled** per-step guards (`_check_cli_guards` `:1065-1112`, `_check_composed_action_guard` `:1508-1637`).
- **`finalize-tasks` is the correct command surface.** `finalize_tasks()` (`src/specify_cli/cli/commands/agent/mission_finalize.py:1520+`) runs a linear phase pipeline after tasks are authored and before implement, and already has a `--validate-only` "report finalization blockers" mode — the natural home for a blocking bulk-edit gate.
- **The live `next`-loop uses different guards.** An agent driven purely by `spec-kitty next` may never invoke the `finalize-tasks` command; its live pre-implement guards are `_check_composed_action_guard` (`action == "tasks"`, `runtime_bridge.py:1622-1637`) and `_check_cli_guards` (`runtime_bridge.py:1091-1108`).

**Decision:** deliver the gate by **reusing `ensure_occurrence_classification_ready` at both live pre-implement surfaces** — the `finalize-tasks` command (IC-01) and the `next`-loop tasks guard (IC-02) — so the "fail before implement" gate is non-vacuous across both execution paths. Do **not** touch the dead `mission.yaml` transition-condition surface or the `mission_v1` guard machinery.

## Technical Context

**Language/Version**: Python 3.11 (repo `requires-python = ">=3.11"`, pinned `3.11.15`)
**Primary Dependencies**: typer, rich (existing `bulk_edit.gate.ensure_occurrence_classification_ready` / `render_gate_failure`; `mission_metadata.load_meta`)
**Storage**: filesystem — `meta.json` (`change_mode`) and `occurrence_map.yaml` in the mission feature dir; no database
**Testing**: pytest (`tests/tasks/`, `tests/specify_cli/bulk_edit/`, `tests/next/`); parallel `--dist loadfile`; `mypy --strict`; `ruff` (zero-issue gate, complexity ceiling 15)
**Target Platform**: cross-platform CLI (Linux, macOS, Windows 10+)
**Project Type**: single project (CLI)
**Performance Goals**: on the non-bulk path the gate adds exactly one `meta.json` read and returns (NFR-001: added wall-time < 20 ms, no new filesystem scan)
**Constraints**: reuse the single existing enforcement function (no new validation logic, C-001); gate must be read-only to preserve the `--validate-only` zero-mutation invariant (C-004); condition strictly on stored `change_mode` (C-003)
**Scale/Scope**: 2 production files touched (`mission_finalize.py`, `runtime_bridge.py`), one reused function, ~30 production LOC + focused tests

## Charter Check

*GATE: must pass before task decomposition. Re-checked after design.*

- **Single canonical authority** — one enforcement function (`ensure_occurrence_classification_ready`) reused at every gate; no duplicated validation. ✅
- **ATDD-first** — acceptance scenarios (spec US1–US3) drive red tests first, then the call is wired. ✅
- **Locality of change (DIR-024)** — edits land in the two modules that *own* the live pre-implement boundaries; no new subsystem. ✅
- **Non-vacuous gate (standing order)** — the gate fires on the live command path (IC-01) *and* the live autonomous `next` path (IC-02); implement-time backstop remains. A gate the framework's own driver bypassed would be vacuous — IC-02 exists to prevent exactly that. ✅
- **Quality gates (DIR-006/DIR-030)** — `mypy --strict` + `ruff` zero-issue, no new suppressions; new branches covered by focused tests (NFR-002/NFR-003). ✅
- **Canonical sources** — reuse `bulk_edit.gate`; do not resurrect the dead `mission_v1` guard path. ✅

No violations → Complexity Tracking not required.

## Project Structure

### Documentation (this mission)

```
kitty-specs/bind-occurrence-map-guard-finalize-01KWQ4WC/
├── spec.md              # Mission spec (committed)
├── plan.md              # This file
├── research.md          # C-005 surface investigation (evidence)
└── tasks.md             # Created by /spec-kitty.tasks
```

### Source Code (repository root)

```
src/specify_cli/
├── cli/commands/agent/mission_finalize.py   # IC-01: add _validate_occurrence_map_ready helper + call in finalize_tasks
└── bulk_edit/gate.py                         # reused unchanged (ensure_occurrence_classification_ready, render_gate_failure)
src/runtime/next/
└── runtime_bridge.py                         # IC-02: fold the gate into the tasks/finalize branches of the live next-loop guards

tests/
├── tasks/test_finalize_tasks_occurrence_gate.py   # IC-01 integration tests (new)
├── next/                                            # IC-02 next-loop guard tests
└── specify_cli/bulk_edit/test_gate.py              # reused unchanged (gate-logic coverage already exists)
```

**Structure Decision**: single-project CLI. No new packages or modules; the change is two call-site additions plus one small read-only helper, all reusing `bulk_edit.gate`.

## Implementation Concern Map

> Concerns are NOT work packages. `/spec-kitty.tasks` translates these into executable WPs.

### IC-01 — Finalize-tasks command gate (the literal ask)

- **Purpose**: block a bulk-edit mission at the `finalize-tasks` command when `occurrence_map.yaml` is missing/schema-invalid/inadmissible, before any implement step.
- **Relevant requirements**: FR-001, FR-002, FR-003; SC-001, SC-002.
- **Affected surfaces**: `src/specify_cli/cli/commands/agent/mission_finalize.py` — add a read-only `_validate_occurrence_map_ready(planning_dir, *, json_output)` helper (mirrors `implement.py:1239-1244`: call `ensure_occurrence_classification_ready`, on failure emit JSON or `render_gate_failure` then `typer.Exit(1)`), and call it inside `finalize_tasks` **before the `if validate_only:` split** so it fires in both modes. Fail-fast placement (early in the pipeline) so a missing map is rejected before expensive bootstrap work.
- **Sequencing/depends-on**: none.
- **Risks**: must preserve the `--validate-only` zero-mutation invariant (the gate is read-only: `load_meta` + `load_occurrence_map` only) — the `tests/specify_cli/cli/commands/test_finalize_tasks_validate_only_readonly.py` invariant must still pass; placement ordering relative to other `typer.Exit(1)` validators (choose fail-fast).

### IC-02 — Live `next`-loop pre-implement coverage (non-vacuousness)

- **Purpose**: ensure the autonomous `spec-kitty next` loop also blocks at the tasks→implement boundary, so the gate is not bypassed by the framework's dominant execution path (charter non-vacuous-gate order). Without this, `next`-driven missions would only catch the bad map at implement-time.
- **Relevant requirements**: FR-001 (intent: "fail before implement"), non-vacuous-gate standing order; SC-001.
- **Affected surfaces**: `src/runtime/next/runtime_bridge.py`. Add **one shared helper** (e.g. `_occurrence_gate_failures(feature_dir) -> list[str]`) that calls `ensure_occurrence_classification_ready(feature_dir)` and returns `result.errors` (empty for non-bulk/valid — self-conditioning). Call that single helper from **both tasks-finalize guard sites** so the new logic cannot diverge: `_check_cli_guards` at the `elif step_id == "tasks_finalize"` branch (~`:1091`) and `_check_composed_action_guard` at the tasks-finalize / composition-terminal block of the `action == "tasks"` branch (~`:1640`) — **not** the `tasks_outline` / `tasks_packages` substeps and **not** the branch head. Fold the returned errors into each site's existing `failures` list.
- **Sequencing/depends-on**: none (independent of IC-01; both reuse the same underlying function).
- **Risks**: (a) *Drift* — the two guard enumerators are near-duplicates (`_check_composed_action_guard` docstring: "Mirrors `_check_cli_guards` semantics"); routing both through the single shared helper prevents the new gate from diverging across paths. (b) *Double-report* — the two guards fire on different execution paths (composed vs. legacy DAG), not both for the same advance; a parity regression test must assert identical gate behavior and no duplicate error at the tasks→implement boundary on both dispatch paths. (c) Scope slightly exceeds the issue's literal "finalize-tasks" text — post-plan squad confirmed `minor`; IC-02 retained for non-vacuousness. The gate stays conditioned on `change_mode == "bulk_edit"` via its own `load_meta`. The fold-in is a single branchless statement, so it adds no new `# noqa`/suppression and does not raise the target functions' cyclomatic complexity (NFR-002).

### Residual risks the tasks phase must carry (from C-005 investigation)

1. **Backstop preserved (FR-004)**: the implement-time call sites (`implement.py:1241`, `agent/workflow.py:2371`) remain unchanged — direct `implement WP01` without finalize is still gated. Do not remove them.
2. **Two `mission.yaml` copies exist** (`src/doctrine/...` and `src/specify_cli/missions/...`); this mission touches neither — it must not "fix" the dead transition-condition surface here.
3. **Admissibility is part of "valid"**: `ensure_occurrence_classification_ready` rejects on presence, schema, AND admissibility (`check_admissibility`, `MIN_ADMISSIBLE_CATEGORIES = 3`); tests must cover the inadmissible branch, not just schema-invalid.
4. **Known debt — out of scope, track separately**: the registered declarative guard `occurrence_map_complete` (`mission_v1/guards.py:277`) is dead (no live consumer), and this mission adds enforcement at hand-rolled call sites rather than reviving the declarative surface. That is consistent with locality-of-change, but leaves the root dead-registry debt. **Do not fix it in this mission**; recommend a follow-up issue to either wire or retire the `mission_v1` guard registry so the declarative surface stops accumulating dead guards.
